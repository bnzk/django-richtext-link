from django.conf import settings
from django.utils.translation import gettext_lazy as _

RICHTEXT_LINK_STYLE_CHOICES = getattr(
    settings,
    "RICHTEXT_LINK_STYLE_CHOICES",
    (
        ("", _("Default")),
        ("button", _("Button")),
    ),
)

RICHTEXT_LINK_TYPE_CHOICES = getattr(
    settings,
    "RICHTEXT_LINK_TYPE_CHOICES",
    (
        ("", _("None")),
        ("free", _("Other / Free")),
        ("external", _("External URL")),
        ("mailto", _("E-Mail")),
        ("phone", _("Phone")),
    ),
)
