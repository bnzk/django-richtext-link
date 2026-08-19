import json

from django import forms
from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from quilljs_link.fields import QuillFormField
from quilljs_link.tests.test_app.models import TestModel
from quilljs_link.widgets import QuillWidget


class TestModelForm(forms.ModelForm):
    class Meta:
        model = TestModel
        fields = ["title", "richtext", "richtext_second"]


class QuillWidgetTests(TestCase):
    def test_model_form_uses_quill_widget(self):
        form = TestModelForm()
        self.assertIsInstance(form.fields["richtext"], QuillFormField)
        self.assertIsInstance(form.fields["richtext"].widget, QuillWidget)

    def test_widget_renders_textarea_and_config(self):
        form = TestModelForm()
        html = str(form["richtext"])
        self.assertIn("data-quilljs-link-widget", html)
        self.assertIn('id="id_richtext_quilljs_config"', html)
        self.assertIn('type="application/json"', html)

    def test_config_contains_derived_urls(self):
        widget = QuillWidget()
        config = widget.get_config()
        djangolink = config["modules"]["djangolink"]
        self.assertEqual(
            djangolink["iframeUrl"], reverse("admin:test_app_linkmodel_add")
        )
        self.assertEqual(
            djangolink["verifyUrl"], reverse("admin:test_app_linkmodel_verify")
        )
        # must be json serializable (no lazy objects left)
        json.dumps(config)

    def test_two_fields_two_configs(self):
        form = TestModelForm()
        html = str(form)
        self.assertIn('id="id_richtext_quilljs_config"', html)
        self.assertIn('id="id_richtext_second_quilljs_config"', html)

    def test_media(self):
        form = TestModelForm()
        media = str(form.media)
        self.assertIn("quilljs_link/vendor/quill/quill.js", media)
        self.assertIn("quilljs_link/vendor/quill/quill.snow.css", media)
        self.assertIn("quilljs_link/js/quilljs-link.js", media)
        self.assertIn("quilljs_link/js/widget-init.js", media)
        self.assertIn("quilljs_link/css/quilljs_link.css", media)

    @override_settings(
        QUILLJS_LINK_CONFIGS={
            "default": {"theme": "snow", "modules": {"toolbar": [["bold"]]}},
            "minimal": {"theme": "snow", "modules": {"toolbar": False}},
        }
    )
    def test_config_name_plumbing(self):
        widget = QuillWidget(config_name="minimal")
        config = widget.get_config()
        self.assertEqual(config["modules"]["toolbar"], False)
        # no djangolink module configured: none injected
        self.assertNotIn("djangolink", config["modules"])

    def test_admin_add_form_uses_widget(self):
        user = User.objects.create_superuser("admin", "admin@bnzk.ch", "admin")
        self.client.force_login(user)
        response = self.client.get(reverse("admin:test_app_testmodel_add"))
        self.assertEqual(response.status_code, 200)
        # formfield_overrides must not have replaced our widget
        self.assertContains(response, "data-quilljs-link-widget")
        self.assertContains(response, "quilljs_link/vendor/quill/quill.js")
