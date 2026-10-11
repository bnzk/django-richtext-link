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
