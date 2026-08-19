from django.conf import settings
from django.utils.translation import gettext_lazy as _

QUILLJS_LINK_STYLE_CHOICES = getattr(
    settings,
    "QUILLJS_LINK_STYLE_CHOICES",
    (
        ("", _("Default")),
        ("button", _("Button")),
    ),
)

QUILLJS_LINK_TYPE_CHOICES = getattr(
    settings,
    "QUILLJS_LINK_TYPE_CHOICES",
    (
        ("", _("None")),
        ("free", _("Other / Free")),
        ("external", _("External URL")),
        ("mailto", _("E-Mail")),
        ("phone", _("Phone")),
    ),
)
