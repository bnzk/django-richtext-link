from django import forms

from quilljs_link.admin import DjangoLinkAdmin
from quilljs_link.link_model.conf import (
    QUILLJS_LINK_STYLE_CHOICES,
    QUILLJS_LINK_TYPE_CHOICES,
)

try:
    from formfieldstash.admin import FormFieldStashMixin
except ImportError:  # soft dependency: pip install django-formfieldstash

    class FormFieldStashMixin:
        pass


class LinkBaseAdmin(FormFieldStashMixin, DjangoLinkAdmin):
    """
    Admin for LinkBase style link models: link_type/link_style render as
    selects (the model fields are plain charfields), and with
    django-formfieldstash installed (+ "formfieldstash" in INSTALLED_APPS),
    only the field of the selected link_type is shown in the dialog form.
    """

    single_formfield_stash = ("link_type",)

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name == "link_type" and not db_field.choices:
            kwargs["widget"] = forms.Select(choices=QUILLJS_LINK_TYPE_CHOICES)
        if db_field.name == "link_style" and not db_field.choices:
            kwargs["widget"] = forms.Select(choices=QUILLJS_LINK_STYLE_CHOICES)
        return super().formfield_for_dbfield(db_field, request, **kwargs)
