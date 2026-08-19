from django.db import models
from django.urls import reverse

from quilljs_link.fields import QuillField
from quilljs_link.link_model.models import LinkBase


class TestModel(models.Model):
    title = models.CharField(
        max_length=255,
    )
    richtext = QuillField(default="", blank=True)
    richtext_second = QuillField(default="", blank=True)

    def __str__(self):
        return "%s" % self.title

    def get_absolute_url(self):
        return reverse("testmodel_detail", args=(self.id,))


class LinkModelBase(models.Model):
    external_url = models.CharField(
        max_length=255,
        blank=True,
        default="",
    )
    email = models.EmailField(
        blank=True,
        default="",
    )
    when = models.DateField(blank=True, null=True)
    testmodel = models.ForeignKey(
        TestModel,
        null=True,
        on_delete=models.CASCADE,
        default=None,
        blank=True,
    )
    target = models.CharField(
        max_length=255,
        blank=True,
        default="",
    )

    class Meta:
        abstract = True

    def __str__(self):
        return "LINK object: %s" % self.get_link()

    def get_link(self):
        if self.external_url:
            return self.external_url
        elif self.when:
            return self.when
        elif self.testmodel:
            return self.testmodel.get_absolute_url()
        elif self.target:
            return self.target
        else:
            return "http://no-link-given.com/"

    def get_link_target(self):
        return "_blank"

    def get_link_style(self):
        return "no-css-class"

    def get_link_attrs(self):
        return {"data-test": "abc"}


class LinkModel(LinkModelBase):
    pass


class ContribLinkModel(LinkBase):
    pass
