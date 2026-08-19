import contextlib
import importlib

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.serializers.json import DjangoJSONEncoder
from django.urls import reverse_lazy
from django.utils.encoding import force_str
from django.utils.functional import Promise

from quilljs_link import conf

# data-quilljs-link is what we write, data-ckeditor-link is recognized for
# django-ckeditor-link content compatibility (upgraded on next editor save).
MARKER_ATTRIBUTES = ("data-quilljs-link", "data-ckeditor-link")


class LazyEncoder(DjangoJSONEncoder):
    def default(self, o):
        if isinstance(o, Promise):
            return force_str(o)
        return super().default(o)


def get_link_model(*, silent=False):
    """
    Resolve QUILLJS_LINK_MODEL lazily, per call - so override_settings works,
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
        msg = f"QUILLJS_LINK_MODEL ({path}) could not be imported!?"
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


def link_kwargs_from_element(link, link_model, *, pop_attrs=False):
    """
    Build kwargs for an unsaved link model instance from an <a> element's
    data attributes. With pop_attrs=True, consumed data attributes and the
    marker attributes are removed from the element (used at render time).
    """
    kwargs = {}
    dummy_link = link_model()
    if pop_attrs:
        for marker in MARKER_ATTRIBUTES:
            link.attrib.pop(marker, None)
    for key, value in list(link.items()):
        if not key.startswith("data-"):
            continue
        new_key = key.replace("data-", "", 1)
        new_value = value
        if hasattr(dummy_link, new_key):
            if hasattr(dummy_link, new_key + "_id"):
                # set fk directly
                new_key = new_key + "_id"
                if not new_value:
                    new_value = None
            kwargs[new_key] = new_value
            if pop_attrs:
                link.attrib.pop(key)
    for key, formatted_string in conf.get_attr_modifiers().items():
        with contextlib.suppress(KeyError):
            # this error is an option, we dont know at all how our link is/was
            # built, maybe ages ago
            kwargs[key] = formatted_string.format(**kwargs)
    return kwargs


def link_data_from_element(link):
    """All data attributes of an <a> element, markers excluded, prefix stripped."""
    return {
        key.replace("data-", "", 1): value
        for key, value in link.items()
        if key.startswith("data-") and key not in MARKER_ATTRIBUTES
    }
