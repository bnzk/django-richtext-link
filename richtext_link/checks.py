"""
Django system checks guarding the stored link format.

Link data lives in the content markup (data-richtext-link='{json}'), so a
sanitizer or editor configuration that strips the marker attribute silently
destroys link data on the next save. What is detectable is checked here, as
check framework errors - they abort runserver/migrate at startup, on purpose:

- RICHTEXT_LINK_SANITIZER (optional dotted path to the project's html
  sanitize callable) lets this module round trip a probe link through the
  real sanitizer and fail loudly when the payload does not survive.
- RICHTEXT_LINK_CONFIGS is inspected for unknown editors and for ckeditor5
  htmlSupport (GeneralHtmlSupport) rules touching our marker attribute.

Not detectable from here: a sanitizer the project never declares, or content
edited by an editor without this package's adapters. The link_index contrib
is the tripwire for those - rebuild it after sanitizer/editor changes and
watch the link count.
"""
from django.core import checks
from django.utils.module_loading import import_string

from richtext_link import conf, utils

KNOWN_EDITORS = ("tiptap", "quilljs", "ckeditor5")

PROBE_DATA = {"probe_field": "probe value"}
# single quoted attribute: the payload itself only contains double quotes
PROBE_HTML = (
    '<p>probe <a href="#" '
    f"{utils.MARKER_ATTRIBUTE}='{utils.serialize_link_data(PROBE_DATA)}'>"
    "link</a></p>"
)
# content written before the json format - checked while
# RICHTEXT_LINK_LEGACY_CHECK is on (the default)
LEGACY_PROBE_HTML = {
    "attr format (richtext-link 0.2)": (
        '<p><a href="#" data-richtext-link="true" '
        'data-probe_field="probe value">link</a></p>'
    ),
    "data-quilljs-link": (
        '<p><a href="#" data-quilljs-link="true" '
        'data-probe_field="probe value">link</a></p>'
    ),
    "data-ckeditor-link": (
        '<p><a href="#" data-ckeditor-link="true" '
        'data-probe_field="probe value">link</a></p>'
    ),
}

SURVIVAL_HINT = (
    "The data-richtext-link attribute carries the whole link payload: if a "
    "sanitizer or editor strips it, link data is silently destroyed on the "
    "next save. Allow exactly <a href data-richtext-link> in the sanitizer."
)


@checks.register()
def check_sanitizer(app_configs, **kwargs):
    path = conf.get_sanitizer_path()
    if not path:
        return []
    message = _sanitizer_probe_message(path)
    if not message and conf.get_legacy_check():
        message = _sanitizer_legacy_message(path)
    return [message] if message else []


def _sanitizer_probe_message(path):
    """Round trip the probe link through the configured sanitizer."""
    try:
        sanitize = import_string(path)
    except ImportError:
        return checks.Error(
            f"RICHTEXT_LINK_SANITIZER ({path}) could not be imported.",
            hint="Use a dotted path to a callable taking and returning html.",
            id="richtext_link.E001",
        )
    try:
        result = sanitize(PROBE_HTML)
    except Exception as exc:  # - report whatever the host raises
        return checks.Error(
            f"RICHTEXT_LINK_SANITIZER ({path}) raised on the probe "
            f"fragment: {exc!r}",
            id="richtext_link.E002",
        )
    try:
        fragment = utils.parse_html_fragment(result)
    except ImportError:
        return checks.Warning(
            "RICHTEXT_LINK_SANITIZER is set but lxml is not installed - "
            "the sanitizer round trip cannot be verified.",
            hint='pip install "django-richtext-link[templatetag]"',
            id="richtext_link.W001",
        )
    links = list(utils.iter_link_elements(fragment))
    if not links:
        return checks.Error(
            f"Improperly configured sanitizer: RICHTEXT_LINK_SANITIZER "
            f"({path}) strips the {utils.MARKER_ATTRIBUTE} marker (or the "
            f"whole link) from richtext content.",
            hint=SURVIVAL_HINT,
            id="richtext_link.E003",
        )
    if utils.link_data_from_element(links[0]) != PROBE_DATA:
        return checks.Error(
            f"Improperly configured sanitizer: RICHTEXT_LINK_SANITIZER "
            f"({path}) mangles the {utils.MARKER_ATTRIBUTE} json payload.",
            hint=SURVIVAL_HINT,
            id="richtext_link.E004",
        )
    return None


def _sanitizer_legacy_message(path):
    """Round trip the legacy format probe links (the sanitizer must not
    destroy them - upgrading is the editors' job, on the next save)."""
    sanitize = import_string(path)
    failing = []
    for label, probe in LEGACY_PROBE_HTML.items():
        try:
            fragment = utils.parse_html_fragment(sanitize(probe))
            links = list(utils.iter_link_elements(fragment))
        except Exception:  # - any mangling counts as failure
            failing.append(label)
            continue
        if not links or utils.link_data_from_element(links[0]) != PROBE_DATA:
            failing.append(label)
    if failing:
        return checks.Error(
            f"Improperly configured sanitizer: RICHTEXT_LINK_SANITIZER "
            f"({path}) strips legacy format links ({', '.join(failing)}) - "
            f"content saved before the json format and never resaved would "
            f"lose its link data.",
            hint=(
                "Allow the legacy markers (data-quilljs-link, "
                "data-ckeditor-link) and data-* attributes on <a> until all "
                "content is resaved, then set "
                "RICHTEXT_LINK_LEGACY_CHECK = False."
            ),
            id="richtext_link.E008",
        )
    return None


def _attributes_touch_marker(attributes):
    """
    Best effort match of a GeneralHtmlSupport rule's "attributes" against our
    marker. True/data-* patterns count: GHS claiming (allow) or stripping
    (disallow) the marker both corrupt the round trip.
    """
    if attributes is True:
        return True
    if isinstance(attributes, str):
        attributes = [attributes]
    if isinstance(attributes, dict):
        attributes = list(attributes.keys())
    if not isinstance(attributes, list | tuple):
        return False
    for item in attributes:
        key = item.get("key", "") if isinstance(item, dict) else item
        if isinstance(key, str) and key.startswith("data-"):
            return True
    return False


@checks.register()
def check_editor_configs(app_configs, **kwargs):
    errors = []
    for name, config in conf.get_configs().items():
        if not isinstance(config, dict):
            errors.append(
                checks.Error(
                    f'RICHTEXT_LINK_CONFIGS["{name}"] is not a dict.',
                    id="richtext_link.E005",
                )
            )
            continue
        editor = config.get("editor", "tiptap")
        if editor not in KNOWN_EDITORS:
            errors.append(
                checks.Error(
                    f'RICHTEXT_LINK_CONFIGS["{name}"] has unknown editor '
                    f'"{editor}" (one of {", ".join(KNOWN_EDITORS)}).',
                    id="richtext_link.E005",
                )
            )
        elif editor == "quilljs":
            errors += _quill_config_messages(name, config)
        elif editor == "ckeditor5":
            errors += _ckeditor5_config_messages(name, config)
    return errors


def _quill_config_messages(name, config):
    # an explicit formats whitelist without "link" strips every link
    # (ours included) the moment content loads
    formats = config.get("formats")
    if isinstance(formats, list | tuple) and "link" not in formats:
        return [
            checks.Error(
                f'RICHTEXT_LINK_CONFIGS["{name}"] has a quill '
                f'"formats" whitelist without "link": the editor '
                f"strips all links (and their data) at load.",
                hint=SURVIVAL_HINT,
                id="richtext_link.E007",
            )
        ]
    return []


def _ckeditor5_config_messages(name, config):
    messages = []
    html_support = (config.get("ckeditor") or {}).get("htmlSupport") or {}
    for rules_key in ("allow", "disallow"):
        for rule in html_support.get(rules_key) or []:
            if not isinstance(rule, dict) or rule.get("name") != "a":
                continue
            if _attributes_touch_marker(rule.get("attributes")):
                messages.append(
                    checks.Error(
                        f'RICHTEXT_LINK_CONFIGS["{name}"] ckeditor.'
                        f'htmlSupport.{rules_key} has an "a" rule touching '
                        f"data-* attributes: GeneralHtmlSupport must not "
                        f"claim or strip {utils.MARKER_ATTRIBUTE} - the "
                        f"djangolink plugin owns it.",
                        hint=SURVIVAL_HINT,
                        id="richtext_link.E006",
                    )
                )
    return messages
