from django.test import TestCase, override_settings

from richtext_link import checks, utils

# sanitizer callables for the probe round trip (referenced by dotted path)


def keeping_sanitizer(html):
    return html


def stripping_sanitizer(html):
    # a sanitizer without the data-richtext-link exception: attribute gone
    fragment = utils.parse_html_fragment(html)
    for link in fragment.cssselect("a"):
        link.attrib.pop(utils.MARKER_ATTRIBUTE, None)
    return utils.serialize_html_fragment(fragment)


def mangling_sanitizer(html):
    # keeps the attribute but destroys the json payload
    fragment = utils.parse_html_fragment(html)
    for link in fragment.cssselect("a"):
        if link.get(utils.MARKER_ATTRIBUTE):
            link.set(utils.MARKER_ATTRIBUTE, "{sanitized}")
    return utils.serialize_html_fragment(fragment)


def raising_sanitizer(html):
    raise RuntimeError("nope")


THIS = "richtext_link.tests.test_checks"


class SanitizerCheckTests(TestCase):
    def check_ids(self):
        return [message.id for message in checks.check_sanitizer(None)]

    def test_no_sanitizer_configured(self):
        self.assertEqual(self.check_ids(), [])

    @override_settings(RICHTEXT_LINK_SANITIZER=f"{THIS}.keeping_sanitizer")
    def test_surviving_payload_passes(self):
        self.assertEqual(self.check_ids(), [])

    @override_settings(RICHTEXT_LINK_SANITIZER=f"{THIS}.no_such_callable")
    def test_import_error(self):
        self.assertEqual(self.check_ids(), ["richtext_link.E001"])

    @override_settings(RICHTEXT_LINK_SANITIZER=f"{THIS}.raising_sanitizer")
    def test_raising_sanitizer(self):
        self.assertEqual(self.check_ids(), ["richtext_link.E002"])

    @override_settings(RICHTEXT_LINK_SANITIZER=f"{THIS}.stripping_sanitizer")
    def test_stripped_marker_fails(self):
        self.assertEqual(self.check_ids(), ["richtext_link.E003"])

    @override_settings(RICHTEXT_LINK_SANITIZER=f"{THIS}.mangling_sanitizer")
    def test_mangled_payload_fails(self):
        self.assertEqual(self.check_ids(), ["richtext_link.E004"])


class EditorConfigCheckTests(TestCase):
    def check_ids(self):
        return [message.id for message in checks.check_editor_configs(None)]

    def test_shipped_test_configs_pass(self):
        self.assertEqual(self.check_ids(), [])

    @override_settings(RICHTEXT_LINK_CONFIGS={"default": {"editor": "tinymce"}})
    def test_unknown_editor(self):
        self.assertEqual(self.check_ids(), ["richtext_link.E005"])

    @override_settings(RICHTEXT_LINK_CONFIGS={"default": "not a dict"})
    def test_config_not_a_dict(self):
        self.assertEqual(self.check_ids(), ["richtext_link.E005"])

    @override_settings(
        RICHTEXT_LINK_CONFIGS={
            "ck": {
                "editor": "ckeditor5",
                "ckeditor": {
                    "htmlSupport": {
                        "allow": [{"name": "a", "attributes": ["data-whatever"]}],
                    },
                },
            },
        }
    )
    def test_ckeditor5_htmlsupport_allow_data_attrs(self):
        self.assertEqual(self.check_ids(), ["richtext_link.E006"])

    @override_settings(
        RICHTEXT_LINK_CONFIGS={
            "ck": {
                "editor": "ckeditor5",
                "ckeditor": {
                    "htmlSupport": {
                        "disallow": [{"name": "a", "attributes": True}],
                    },
                },
            },
        }
    )
    def test_ckeditor5_htmlsupport_disallow_all_attrs(self):
        self.assertEqual(self.check_ids(), ["richtext_link.E006"])

    @override_settings(
        RICHTEXT_LINK_CONFIGS={
            "ck": {
                "editor": "ckeditor5",
                "ckeditor": {
                    "htmlSupport": {
                        # class/style on p stays fine (the Style feature setup)
                        "allow": [{"name": "p", "attributes": ["class"]}],
                    },
                },
            },
        }
    )
    def test_ckeditor5_htmlsupport_unrelated_rules_pass(self):
        self.assertEqual(self.check_ids(), [])
