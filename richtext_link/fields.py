from django import forms
from django.db import models

from richtext_link.widgets import RichtextWidget


class RichtextFormField(forms.CharField):
    def __init__(self, *args, config_name="default", **kwargs):
        # force our widget, defeating the admin's formfield_overrides
        # (which would replace any widget set via RichtextField.formfield)
        kwargs["widget"] = RichtextWidget(config_name=config_name)
        super().__init__(*args, **kwargs)


class RichtextField(models.TextField):
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
            "form_class": RichtextFormField,
            "config_name": self.config_name,
        }
        defaults.update(kwargs)
        return super().formfield(**defaults)
