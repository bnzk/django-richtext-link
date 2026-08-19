from django import forms
from django.contrib import admin
from django.forms.widgets import SelectDateWidget

from quilljs_link.admin import DjangoLinkAdmin
from quilljs_link.link_model.admin import LinkBaseAdmin

from .models import ContribLinkModel, LinkModel, TestModel


class LinkModelForm(forms.ModelForm):
    when = forms.DateField(widget=SelectDateWidget, required=False)


@admin.register(TestModel)
class TestModelAdmin(admin.ModelAdmin):
    search_fields = ["title"]


@admin.register(LinkModel)
class LinkModelAdmin(DjangoLinkAdmin):
    form = LinkModelForm


@admin.register(ContribLinkModel)
class ContribLinkModelAdmin(LinkBaseAdmin):
    pass
