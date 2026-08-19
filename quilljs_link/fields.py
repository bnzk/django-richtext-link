from django import forms
from django.db import models

from quilljs_link.widgets import QuillWidget


class QuillFormField(forms.CharField):
    def __init__(self, *args, config_name="default", **kwargs):
        # force our widget, defeating the admin's formfield_overrides
        # (which would replace any widget set via QuillField.formfield)
        kwargs["widget"] = QuillWidget(config_name=config_name)
        super().__init__(*args, **kwargs)


class QuillField(models.TextField):
    def __init__(self, *args, config_name="default", **kwargs):
        self.config_name = config_name
        super().__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        if self.config_name != "default":
            kwargs["config_name"] = self.config_name
        return name, path, args, kwargs

    def formfield(self, **kwargs):
        defaults = {
            "form_class": QuillFormField,
            "config_name": self.config_name,
        }
        defaults.update(kwargs)
        return super().formfield(**defaults)
