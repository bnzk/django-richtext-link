"""
The djangocms-text bridge (richtext_link.contrib.djangocms_text). Python side
only - the js is exercised against a real djangocms-text project. Runs when
djangocms-text is installed, skipped otherwise (it is not a test dependency:
it pulls in django-cms).
"""

import unittest

from django.test import TestCase

try:
    import djangocms_text  # noqa: F401

    HAS_DJANGOCMS_TEXT = True
except ImportError:
    HAS_DJANGOCMS_TEXT = False


@unittest.skipUnless(HAS_DJANGOCMS_TEXT, "djangocms-text not installed")
class RTEConfigTests(TestCase):
    def _config(self, **kwargs):
        from richtext_link.contrib.djangocms_text import RichtextLinkRTEConfig

        return RichtextLinkRTEConfig(**kwargs)

    def test_default_assets(self):
        config = self._config()
        self.assertIn("djangocms_text/bundles/bundle.tiptap.min.js", config.js)
        self.assertIn("richtext_link/js/richtext-link-core.js", config.js)
        self.assertIn(
            "richtext_link/js/richtext-link-djangocms-text.js", config.js
        )
        # core before the bridge
        self.assertLess(
            config.js.index("richtext_link/js/richtext-link-core.js"),
            config.js.index("richtext_link/js/richtext-link-djangocms-text.js"),
        )
        self.assertIn("richtext_link/css/richtext_link.css", config.css["all"])

    def test_project_assets_appended(self):
        config = self._config(
            js=("myproject/extra.js",), css={"all": ("myproject/rte.css",)}
        )
        self.assertEqual(config.js[-1], "myproject/extra.js")
        self.assertEqual(config.css["all"][-1], "myproject/rte.css")
        # defaults still in place
        self.assertIn("richtext_link/js/richtext-link-djangocms-text.js", config.js)

    def test_configuration_derives_dialog_urls(self):
        import copy
        import json

        from django.core.serializers.json import DjangoJSONEncoder
        from django.utils.encoding import force_str

        config = self._config()
        djangolink = config.configuration["richtextLink"]
        self.assertIn("/linkmodel/add/", force_str(djangolink["iframeUrl"]))
        self.assertIn("/linkmodel/verify/", force_str(djangolink["verifyUrl"]))
        # must survive what the widget does: deepcopy + json dump. the urls
        # stay lazy on purpose - widgets can be instantiated at import time,
        # an eager reverse there freezes a half-populated admin urlconf.
        dumped = json.dumps(
            copy.deepcopy(config.configuration), cls=DjangoJSONEncoder
        )
        self.assertIn("/linkmodel/verify/", dumped)

    def test_configuration_overrides(self):
        config = self._config(
            djangolink={"iframeUrl": "/custom/", "fallbackField": "free_url"},
            configuration={"someKey": True},
        )
        djangolink = config.configuration["richtextLink"]
        self.assertEqual(djangolink["iframeUrl"], "/custom/")
        self.assertEqual(djangolink["fallbackField"], "free_url")
        # verifyUrl still derived
        self.assertIn("/linkmodel/verify/", djangolink["verifyUrl"])
        self.assertTrue(config.configuration["someKey"])

    def test_configuration_does_not_resolve_urls(self):
        # djangocms-text widgets can be instantiated at import time (an
        # HTMLFormField on a module level form), where resolving would freeze
        # a half-populated admin urlconf. accessing configuration (and the
        # widget's deepcopy of it) must leave the urls lazy.
        import copy
        from unittest import mock

        from django.utils.functional import lazy

        def boom():
            raise AssertionError("url resolved too early")

        poison = lazy(boom, str)
        with mock.patch(
            "richtext_link.utils.get_default_dialog_urls",
            return_value=(poison(), poison()),
        ):
            config = self._config()
            copy.deepcopy(config.configuration)  # what the widget does

    def test_configuration_returns_fresh_dict(self):
        config = self._config()
        first = config.configuration
        first["richtextLink"]["iframeUrl"] = "mutated"
        self.assertNotEqual(
            config.configuration["richtextLink"]["iframeUrl"], "mutated"
        )
