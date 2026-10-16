from django.conf import settings

RICHTEXT_LINK_DEFAULT_CONFIG = {
    "editor": "tiptap",
    "toolbar": [
        ["bold", "italic"],
        ["h2", "h3", "p"],
        ["bulletList", "orderedList"],
        ["djangolink", "clear"],
    ],
    "headingLevels": [2, 3],
    "enterMode": "p",
    # iframeUrl/verifyUrl are auto derived from the link model's admin,
    # see richtext_link.widgets.RichtextWidget.get_config
    "djangolink": {},
}


def get_link_model_path():
    """Dotted path to the link model class, e.g. "my_app.models.LinkModel"."""
    return getattr(settings, "RICHTEXT_LINK_MODEL", None)


def get_sanitizer_path():
    """
    Optional dotted path to the project's html sanitize callable
    (html -> html). When set, a django system check verifies at startup that
    the sanitizer lets the data-richtext-link payload survive - see
    richtext_link.checks.
    """
    return getattr(settings, "RICHTEXT_LINK_SANITIZER", None)


def get_save_guard():
    """
    Default True: a pre_save comparison logs an error ("richtext_link"
    logger) when a saved richtext value lost link data that the old value
    had - see richtext_link.guards.
    """
    return getattr(settings, "RICHTEXT_LINK_SAVE_GUARD", True)


def get_legacy_check():
    """
    Default True: the startup checks (and the richtext_link_editor_check
    command) also verify that the legacy link formats survive - content saved
    by django-ckeditor-link, django-quilljs-link 0.1 or django-richtext-link
    0.2 that was never resaved. Set RICHTEXT_LINK_LEGACY_CHECK = False once
    no such content is left.
    """
    return getattr(settings, "RICHTEXT_LINK_LEGACY_CHECK", True)


def get_attr_modifiers():
    """
    dict of {field_name: format_string} - format_string is formatted with all
    link kwargs, and the result assigned to field_name. mostly needed for
    MultiWidget fields (e.g. {"cms_page": "{cms_page_2}"}).
    """
    return getattr(settings, "RICHTEXT_LINK_ATTR_MODIFIERS", {})


def get_configs():
    """
    Editor configs. The "editor" key selects the adapter: "tiptap" (our own
    config schema, the default - see README), "quilljs" (the dict is passed
    to `new Quill(el, config)` as is) or "ckeditor5" (bring your own
    CKEditor 5 build - see README, nothing GPL licensed is shipped).
    """
    return getattr(
        settings,
        "RICHTEXT_LINK_CONFIGS",
        {"default": RICHTEXT_LINK_DEFAULT_CONFIG},
    )
