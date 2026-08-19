from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.utils.translation import gettext_lazy as _

from .conf import QUILLJS_LINK_TYPE_CHOICES


class LinkBase(models.Model):
    link_type = models.CharField(
        max_length=20,
        blank=True,
        default="",
        verbose_name=_("Link type"),
    )
    link_style = models.CharField(
        max_length=64,
        blank=True,
        default="",
        verbose_name=_("Link Style"),
    )
    free = models.CharField(
        max_length=512,
        default="",
        blank=True,
        verbose_name=_("Internal / Other"),
    )
    external = models.URLField(
        blank=True,
        default="",
        verbose_name=_("External Address"),
    )
    mailto = models.EmailField(
        default="",
        blank=True,
        verbose_name=_("E-Mail"),
    )
    phone = models.CharField(
        max_length=64,
        default="",
        blank=True,
        verbose_name=_("Phone"),
    )

    class Meta:
        abstract = True

    def get_link(self):
        # if link type set, give priority!
        # this will alter your object!
        if self.link_type:
            for key, _display in QUILLJS_LINK_TYPE_CHOICES:
                if key and key != self.link_type:
                    setattr(self, key, None)
        # generic foreign key link check
        fk_link = self._check_link_for_foreign_key()
        if fk_link:
            return fk_link
        # other custom link types
        if self.free:
            return self.free
        elif self.external:
            link = self.external
            if not link.startswith("http"):
                link = "http://%s" % link
            return link
        elif self.mailto:
            return "mailto:%s" % self.mailto
        elif self.phone:
            return "tel:%s" % self.phone
        return ""

    def get_link_text(self):
        if getattr(self, "link_text", None):
            return self.link_text
        if getattr(self, "name", None):
            return self.name
        obj = None
        if self.link_type:
            obj = self._check_foreign_key_value()
        if obj is not None:
            return str(obj)
        return ""

    def get_link_type(self):
        return self.link_type

    def get_link_style(self):
        return self.link_style

    def get_link_target(self):
        if self.get_link_type() in ["file", "external"]:
            return "_blank"
        return ""

    def _check_foreign_key_value(self):
        """
        check if link type and it's value are a foreign key
        Returns: foreign key value, if available
        """
        try:
            return getattr(self, self.get_link_type(), None)
        except ObjectDoesNotExist:
            pass
        return None

    def _check_link_for_foreign_key(self):
        value = self._check_foreign_key_value()
        if value and getattr(value, "get_absolute_url", None):
            return value.get_absolute_url()
        return None
