import json

from django import forms
from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from richtext_link import conf
from richtext_link.fields import RichtextFormField
from richtext_link.tests.test_app.models import TestModel
from richtext_link.widgets import RichtextWidget


class TestModelForm(forms.ModelForm):
    class Meta:
        model = TestModel
        fields = [
            "title",
            "richtext",
            "richtext_second",
            "richtext_quill",
            "richtext_ckeditor",
        ]


class RichtextWidgetTests(TestCase):
    def test_model_form_uses_richtext_widget(self):
        form = TestModelForm()
        self.assertIsInstance(form.fields["richtext"], RichtextFormField)
        self.assertIsInstance(form.fields["richtext"].widget, RichtextWidget)

    def test_widget_renders_textarea_and_config(self):
        form = TestModelForm()
        html = str(form["richtext"])
        self.assertIn("data-richtext-link-widget", html)
        self.assertIn('id="id_richtext_richtext_config"', html)
        self.assertIn('type="application/json"', html)

    def test_two_fields_two_configs(self):
        form = TestModelForm()
        html = str(form)
        self.assertIn('id="id_richtext_richtext_config"', html)
        self.assertIn('id="id_richtext_second_richtext_config"', html)

    def test_tiptap_config_contains_derived_urls(self):
        widget = RichtextWidget()
        config = widget.get_config()
        self.assertEqual(config["editor"], "tiptap")
        djangolink = config["djangolink"]
        self.assertEqual(
            djangolink["iframeUrl"], reverse("admin:test_app_linkmodel_add")
        )
        self.assertEqual(
            djangolink["verifyUrl"], reverse("admin:test_app_linkmodel_verify")
        )
        # must be json serializable (no lazy objects left)
        json.dumps(config)

    def test_quill_config_contains_derived_urls(self):
        widget = RichtextWidget(config_name="quill")
        config = widget.get_config()
        self.assertEqual(config["editor"], "quilljs")
        djangolink = config["modules"]["djangolink"]
        self.assertEqual(
            djangolink["iframeUrl"], reverse("admin:test_app_linkmodel_add")
        )
        self.assertEqual(
            djangolink["verifyUrl"], reverse("admin:test_app_linkmodel_verify")
        )
        json.dumps(config)

    def test_tiptap_media(self):
        media = str(RichtextWidget().media)
        self.assertIn("richtext_link/vendor/tiptap/tiptap-bundle.js", media)
        self.assertIn("richtext_link/js/richtext-link-core.js", media)
        self.assertIn("richtext_link/js/richtext-link-tiptap.js", media)
        self.assertIn("richtext_link/js/widget-init.js", media)
        self.assertIn("richtext_link/css/richtext_link.css", media)
        self.assertNotIn("quill", media)

    def test_quill_media(self):
        media = str(RichtextWidget(config_name="quill").media)
        self.assertIn("richtext_link/vendor/quill/quill.js", media)
        self.assertIn("richtext_link/vendor/quill/quill.snow.css", media)
        self.assertIn("richtext_link/js/richtext-link-core.js", media)
        self.assertIn("richtext_link/js/richtext-link-quill.js", media)
        self.assertIn("richtext_link/js/widget-init.js", media)
        self.assertNotIn("tiptap", media)

    def test_mixed_form_media(self):
        # tiptap, quill and ckeditor5 fields on one form: all asset sets, no dupes
        media = str(TestModelForm().media)
        self.assertIn("richtext_link/vendor/tiptap/tiptap-bundle.js", media)
        self.assertIn("richtext_link/vendor/quill/quill.js", media)
        self.assertIn("richtext_link/js/richtext-link-ckeditor5.js", media)
        self.assertEqual(media.count("widget-init.js"), 1)
        self.assertEqual(media.count("richtext-link-core.js"), 1)

    def test_ckeditor5_media_with_assets(self):
        media = str(RichtextWidget(config_name="ckeditor").media)
        # relative asset paths from the test config go through static()
        self.assertIn("/static/test_ckeditor5/ckeditor5.umd.js", media)
        self.assertIn("/static/test_ckeditor5/ckeditor5.css", media)
        self.assertIn("richtext_link/js/richtext-link-core.js", media)
        self.assertIn("richtext_link/js/richtext-link-ckeditor5.js", media)
        self.assertIn("richtext_link/js/widget-init.js", media)
        # nothing vendored is loaded for ckeditor5
        self.assertNotIn("tiptap", media)
        self.assertNotIn("quill", media)
        self.assertNotIn("richtext_link/vendor", media)

    @override_settings(
        RICHTEXT_LINK_CONFIGS={
            "bare": {"editor": "ckeditor5", "djangolink": {}},
            "cdn": {
                "editor": "ckeditor5",
                "assets": {
                    "js": "https://cdn.example.com/ckeditor5.umd.js",
                    "css": "https://cdn.example.com/ckeditor5.css",
                },
            },
        }
    )
    def test_ckeditor5_media_assets_variants(self):
        # no assets configured: bring your own, only our files
        media = str(RichtextWidget(config_name="bare").media)
        self.assertNotIn("umd.js", media)
        self.assertIn("richtext_link/js/richtext-link-ckeditor5.js", media)
        # absolute urls pass through untouched, ordered before our files
        media = str(RichtextWidget(config_name="cdn").media)
        self.assertIn('src="https://cdn.example.com/ckeditor5.umd.js"', media)
        self.assertIn('href="https://cdn.example.com/ckeditor5.css"', media)
        self.assertLess(
            media.find("cdn.example.com/ckeditor5.umd.js"),
            media.find("richtext-link-ckeditor5.js"),
        )

    def test_ckeditor5_config_contains_derived_urls(self):
        widget = RichtextWidget(config_name="ckeditor")
        config = widget.get_config()
        self.assertEqual(config["editor"], "ckeditor5")
        djangolink = config["djangolink"]
        self.assertEqual(
            djangolink["iframeUrl"], reverse("admin:test_app_linkmodel_add")
        )
        self.assertEqual(
            djangolink["verifyUrl"], reverse("admin:test_app_linkmodel_verify")
        )
        json.dumps(config)

    @override_settings(RICHTEXT_LINK_CONFIGS={"bare": {"editor": "ckeditor5"}})
    def test_ckeditor5_no_djangolink_no_injection(self):
        config = RichtextWidget(config_name="bare").get_config()
        self.assertNotIn("djangolink", config)

    def test_missing_editor_key_defaults_to_tiptap(self):
        with override_settings(
            RICHTEXT_LINK_CONFIGS={"default": {"toolbar": [["bold"]]}}
        ):
            widget = RichtextWidget()
            self.assertEqual(widget.get_editor(), "tiptap")
            self.assertEqual(widget.get_config()["editor"], "tiptap")

    def test_unknown_config_name_falls_back_to_shipped_default(self):
        widget = RichtextWidget(config_name="nosuchconfig")
        config = widget.get_config()
        self.assertEqual(config["editor"], "tiptap")
        self.assertEqual(
            config["toolbar"], conf.RICHTEXT_LINK_DEFAULT_CONFIG["toolbar"]
        )

    @override_settings(
        RICHTEXT_LINK_CONFIGS={
            "minimal": {"editor": "quilljs", "theme": "snow", "modules": {}},
        }
    )
    def test_no_djangolink_config_no_injection(self):
        config = RichtextWidget(config_name="minimal").get_config()
        self.assertNotIn("djangolink", config["modules"])

    def test_admin_add_form_uses_widget(self):
        user = User.objects.create_superuser("admin", "admin@bnzk.ch", "admin")
        self.client.force_login(user)
        response = self.client.get(reverse("admin:test_app_testmodel_add"))
        self.assertEqual(response.status_code, 200)
        # formfield_overrides must not have replaced our widget
        self.assertContains(response, "data-richtext-link-widget")
        # both editors on the change form (richtext* tiptap, richtext_quill quill)
        self.assertContains(response, "richtext_link/vendor/tiptap/tiptap-bundle.js")
        self.assertContains(response, "richtext_link/vendor/quill/quill.js")
        self.assertContains(response, "richtext_link/js/richtext-link-ckeditor5.js")
