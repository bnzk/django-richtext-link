import contextlib
import importlib
import json

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.serializers.json import DjangoJSONEncoder
from django.urls import reverse_lazy
from django.utils.encoding import force_str
from django.utils.functional import Promise

from richtext_link import conf

# what we write: the marker attribute carries the json encoded link data,
# e.g. data-richtext-link='{"link_type":"page","page":"1"}'. legacy formats
# (one data-* attribute per field, marker value "true" - with any of the
# marker names: data-quilljs-link is django-quilljs-link 0.1.0,
# data-ckeditor-link is django-ckeditor-link) are read forever - legacy
# content keeps working and is upgraded on the next editor save.
MARKER_ATTRIBUTE = "data-richtext-link"
MARKER_ATTRIBUTES = (MARKER_ATTRIBUTE, "data-quilljs-link", "data-ckeditor-link")


class LazyEncoder(DjangoJSONEncoder):
    def default(self, o):
        if isinstance(o, Promise):
            return force_str(o)
        return super().default(o)


def get_link_model(*, silent=False):
    """
    Resolve RICHTEXT_LINK_MODEL lazily, per call - so override_settings works,
    without any module reloading.
    """
    path = conf.get_link_model_path()
    link_model = None
    if path:
        module_name, class_name = path.rsplit(".", 1)
        with contextlib.suppress(ImportError):
            module = importlib.import_module(module_name)
            link_model = getattr(module, class_name, None)
    if link_model is None and not silent and settings.DEBUG:
        msg = f"RICHTEXT_LINK_MODEL ({path}) could not be imported!?"
        raise ImproperlyConfigured(msg)
    return link_model


def get_default_dialog_urls(link_model=None):
    """
    (iframe_url, verify_url) of the link model's admin, as lazy urls.
    """
    if link_model is None:
        link_model = get_link_model(silent=True)
    if link_model is None:
        return None, None
    meta = link_model._meta
    return (
        reverse_lazy(f"admin:{meta.app_label}_{meta.model_name}_add"),
        reverse_lazy(f"admin:{meta.app_label}_{meta.model_name}_verify"),
    )


def parse_html_fragment(html):
    # lxml is not a dependency, but needed for link parsing/rendering.
    from lxml.html import fragment_fromstring

    return fragment_fromstring("<div>" + html + "</div>")


def serialize_html_fragment(fragment):
    """Serialize the children of the wrapper div, without the wrapper itself."""
    from lxml.html import tostring

    result = fragment.text or ""
    for child in fragment:
        result += tostring(child, encoding="unicode")
    return result


def iter_link_elements(fragment):
    """Yield all <a> elements carrying one of our marker attributes."""
    for link in fragment.cssselect("a"):
        if any(link.get(marker) for marker in MARKER_ATTRIBUTES):
            yield link


def serialize_link_data(data):
    """
    The canonical marker payload: sorted keys, empty values omitted, compact,
    non-ascii kept literal - byte identical with the editors'
    RichtextLink.serializeLinkData.
    """
    cleaned = {
        key: force_str(value) for key, value in data.items() if value not in (None, "")
    }
    return json.dumps(
        cleaned, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )


def link_kwargs_from_element(link, link_model, *, pop_attrs=False):
    """
    Build kwargs for an unsaved link model instance from an <a> element's
    link data. With pop_attrs=True, the marker attributes and (legacy format)
    consumed data attributes are removed from the element (render time).
    """
    kwargs = {}
    dummy_link = link_model()
    data = link_data_from_element(link)
    if pop_attrs:
        for marker in MARKER_ATTRIBUTES:
            link.attrib.pop(marker, None)
    for key, value in data.items():
        new_key = key
        new_value = value
        if hasattr(dummy_link, new_key):
            if hasattr(dummy_link, new_key + "_id"):
                # set fk directly
                new_key = new_key + "_id"
                if not new_value:
                    new_value = None
            kwargs[new_key] = new_value
            if pop_attrs:
                # legacy format leftovers; the json format has no per field
                # attributes to clean up
                link.attrib.pop("data-" + key, None)
    for key, formatted_string in conf.get_attr_modifiers().items():
        with contextlib.suppress(KeyError):
            # this error is an option, we dont know at all how our link is/was
            # built, maybe ages ago
            kwargs[key] = formatted_string.format(**kwargs)
    return kwargs


def lost_link_data(old_html, new_html):
    """
    Marker links of old_html whose data vanished in new_html while their
    anchor survived as a plain link (same text) - the signature of a
    stripping sanitizer or editor, as opposed to a deliberate link removal
    (anchor gone) or a dialog edit (marker still there, payload changed).
    Returns [(link_text, lost_payload), ...].
    """
    old_fragment = parse_html_fragment(old_html or "")
    new_fragment = parse_html_fragment(new_html or "")
    new_payloads = [
        serialize_link_data(link_data_from_element(link))
        for link in iter_link_elements(new_fragment)
    ]
    plain_texts = {
        " ".join(link.text_content().split())
        for link in new_fragment.cssselect("a")
        if not any(link.get(marker) for marker in MARKER_ATTRIBUTES)
    }
    lost = []
    for link in iter_link_elements(old_fragment):
        payload = serialize_link_data(link_data_from_element(link))
        if payload in new_payloads:
            new_payloads.remove(payload)
            continue
        text = " ".join(link.text_content().split())
        if text in plain_texts:
            lost.append((text, payload))
    return lost


def link_data_from_element(link):
    """
    The link data of a marker <a> element: the marker's json payload (current
    format), or all data attributes with the prefix stripped and markers
    excluded (legacy formats).
    """
    marker_value = link.get(MARKER_ATTRIBUTE) or ""
    if marker_value.startswith("{"):
        # defensive: mangled payloads fall back to the legacy format
        with contextlib.suppress(ValueError):
            parsed = json.loads(marker_value)
            if isinstance(parsed, dict):
                return {
                    key: "" if value is None else force_str(value)
                    for key, value in parsed.items()
                }
    return {
        key.replace("data-", "", 1): value
        for key, value in link.items()
        if key.startswith("data-") and key not in MARKER_ATTRIBUTES
    }
