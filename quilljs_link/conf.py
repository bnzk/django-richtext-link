from django.conf import settings

QUILLJS_LINK_DEFAULT_CONFIG = {
    "theme": "snow",
    "modules": {
        "toolbar": [
            ["bold", "italic", "underline"],
            [{"list": "ordered"}, {"list": "bullet"}],
            ["djangolink", "clean"],
        ],
        # iframeUrl/verifyUrl are auto derived from the link model's admin,
        # see quilljs_link.widgets.QuillWidget.get_config
        "djangolink": {},
    },
}


def get_link_model_path():
    """Dotted path to the link model class, e.g. "my_app.models.LinkModel"."""
    return getattr(settings, "QUILLJS_LINK_MODEL", None)


def get_attr_modifiers():
    """
    dict of {field_name: format_string} - format_string is formatted with all
    link kwargs, and the result assigned to field_name. mostly needed for
    MultiWidget fields (e.g. {"cms_page": "{cms_page_2}"}).
    """
    return getattr(settings, "QUILLJS_LINK_ATTR_MODIFIERS", {})


def get_configs():
    """Editor configs, passed to `new Quill(el, config)` as is."""
    return getattr(
        settings,
        "QUILLJS_LINK_CONFIGS",
        {"default": QUILLJS_LINK_DEFAULT_CONFIG},
    )
