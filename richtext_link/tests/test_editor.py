"""
Selenium editor tests - few and focused, they are slow and inherently flaky.
Skipped when selenium/geckodriver is not available. The CKEditor 5 tests
additionally need `richtext_link/tests/get_ckeditor5.sh` run once (CKEditor 5
is GPL licensed and not shipped).
"""
import os
import unittest

from django.test import override_settings
from django.urls import reverse

from richtext_link.tests.utils.selenium_utils import (
    HAS_SELENIUM,
    SeleniumTestCase,
    skip_unless_selenium,
)

if HAS_SELENIUM:
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.support.ui import Select

CKEDITOR5_UMD = os.path.join(
    os.path.dirname(__file__),
    "test_app",
    "static",
    "test_ckeditor5",
    "ckeditor5.umd.js",
)
HAS_CKEDITOR5 = os.path.exists(CKEDITOR5_UMD)

CKEDITOR5_ENTER_BR_CONFIGS = {
    # other fields fall back to the shipped default config (tiptap)
    "ckeditor": {
        "editor": "ckeditor5",
        "assets": {
            "js": "test_ckeditor5/ckeditor5.umd.js",
            "css": "test_ckeditor5/ckeditor5.css",
        },
        "enterMode": "br",
        "ckeditor": {"toolbar": ["bold"]},
    },
}

ENTER_BR_CONFIGS = {
    "default": {
        "editor": "tiptap",
        "toolbar": [["bold"], ["djangolink"]],
        "enterMode": "br",
        "djangolink": {},
    },
    "quill": {
        "editor": "quilljs",
        "theme": "snow",
        "modules": {"toolbar": [["bold"]], "djangolink": {}},
    },
}


class EditorTestCase(SeleniumTestCase):
    fixtures = [
        "test_app.json",
    ]

    def open_change_form(self, pk, wait_for):
        self.login()
        self.open(reverse("admin:test_app_testmodel_change", args=[pk]))
        self.webdriver.wait_for_css(wait_for)

    def get_textarea_value(self, field="richtext"):
        value = self.webdriver.execute_script(
            f'return document.getElementById("id_{field}").value;'
        )
        # quill's getSemanticHTML encodes spaces as &nbsp; - normalize for asserts
        return value.replace("&nbsp;", " ")

    def get_link_data_list(self, field="richtext"):
        """The link data bags of all marker links in the field's html."""
        from richtext_link import utils

        fragment = utils.parse_html_fragment(self.get_textarea_value(field))
        return [
            utils.link_data_from_element(link)
            for link in utils.iter_link_elements(fragment)
        ]

    def switch_to_dialog_iframe(self):
        iframe = self.webdriver.wait_for_css(".richtext-link-dialog[open] iframe")
        self.webdriver.switch_to.frame(iframe)

    def click_dialog_ok(self):
        self.webdriver.switch_to.default_content()
        self.webdriver.find_css(
            ".richtext-link-dialog[open] .richtext-link-dialog__buttons button.default"
        ).click()


@skip_unless_selenium
class TiptapEditorTests(EditorTestCase):
    def find_editors(self):
        editors = self.webdriver.find_css(".richtext-link-tiptap .tiptap")
        return editors if isinstance(editors, list) else [editors]

    def test_editor_renders(self):
        self.open_change_form(2, ".richtext-link-tiptap .tiptap")
        # richtext + richtext_second are tiptap
        self.assertEqual(len(self.find_editors()), 2)
        buttons = self.webdriver.find_css(
            ".richtext-link-toolbar button[data-item='djangolink']"
        )
        if not isinstance(buttons, list):
            buttons = [buttons]
        self.assertEqual(len(buttons), 2)
        # fixture links survived the html -> schema -> dom round trip
        self.webdriver.find_css(".tiptap a[data-richtext-link]")

    def test_dialog_opens_validates_and_applies(self):
        self.open_change_form(2, ".richtext-link-tiptap .tiptap")
        self.find_editors()[0].click()
        buttons = self.webdriver.find_css(
            ".richtext-link-toolbar button[data-item='djangolink']"
        )
        buttons[0].click()
        # invalid input -> errorlist inside the iframe
        self.switch_to_dialog_iframe()
        email_input = self.webdriver.wait_for_css("#id_email")
        email_input.send_keys("no-email")
        self.click_dialog_ok()
        self.switch_to_dialog_iframe()
        self.webdriver.wait_for_css(".field-email .errorlist")
        # fix it -> link applied, dialog closed
        email_input = self.webdriver.find_css("#id_email")
        email_input.clear()
        email_input.send_keys("test@bnzk.ch")
        self.click_dialog_ok()
        self.webdriver.wait_for_css(".tiptap a[data-richtext-link]")
        # the marker carries the json payload (quotes html escaped)
        self.assertIn('data-richtext-link="{', self.get_textarea_value())
        datas = self.get_link_data_list()
        self.assertTrue(any(d.get("email") == "test@bnzk.ch" for d in datas))

    def test_legacy_link_upgraded(self):
        self.open_change_form(3, ".richtext-link-tiptap .tiptap")
        # the legacy data-ckeditor-link fixture link got re-rendered with the
        # new marker in the editor dom
        self.webdriver.find_css(".tiptap a[data-richtext-link]")
        editor = self.find_editors()[0]
        editor.click()
        editor.send_keys("x")
        value = self.get_textarea_value()
        # upgraded to the current format: json payload in the marker
        self.assertIn('data-richtext-link="{', value)
        self.assertNotIn("data-ckeditor-link", value)
        self.assertTrue(
            any(d.get("testmodel") == "1" for d in self.get_link_data_list())
        )
        # the plain link stays plain
        self.assertIn('<a href="https://www.example.com/">', value)

    def test_block_class_select(self):
        self.open_change_form(2, ".richtext-link-tiptap .tiptap")
        editor = self.find_editors()[0]
        editor.click()
        selects = self.webdriver.find_css("select[data-item='blockClass']")
        if not isinstance(selects, list):
            selects = [selects]
        Select(selects[0]).select_by_value("intro")
        value = self.get_textarea_value()
        self.assertIn('<p class="intro">', value)
        Select(selects[0]).select_by_value("")
        value = self.get_textarea_value()
        self.assertNotIn('class="intro"', value)

    @override_settings(RICHTEXT_LINK_CONFIGS=ENTER_BR_CONFIGS)
    def test_enter_mode_br(self):
        self.open_change_form(1, ".richtext-link-tiptap .tiptap")
        editor = self.find_editors()[0]
        editor.click()
        editor.send_keys(Keys.END)
        editor.send_keys(Keys.ENTER)
        editor.send_keys("x")
        value = self.get_textarea_value()
        self.assertIn("<br", value)
        self.assertEqual(value.count("<p>"), 1)

    def test_two_editors_independent(self):
        self.open_change_form(2, ".richtext-link-tiptap .tiptap")
        editors = self.find_editors()
        second_before = self.get_textarea_value("richtext_second")
        editors[0].click()
        editors[0].send_keys("hello first editor")
        self.assertIn("hello first editor", self.get_textarea_value("richtext"))
        self.assertEqual(second_before, self.get_textarea_value("richtext_second"))

    def test_dialog_quick_search(self):
        self.open_change_form(2, ".richtext-link-tiptap .tiptap")
        self.find_editors()[0].click()
        buttons = self.webdriver.find_css(
            ".richtext-link-toolbar button[data-item='djangolink']"
        )
        buttons[0].click()
        self.switch_to_dialog_iframe()
        search_input = self.webdriver.wait_for_css(".richtext-link-search input")
        search_input.send_keys("Legacy")
        self.webdriver.wait_for_css(".richtext-link-search__item").click()
        selected = self.webdriver.execute_script(
            'return document.getElementById("id_testmodel").value;'
        )
        self.assertEqual(selected, "3")
        self.click_dialog_ok()
        self.webdriver.wait_for_css(".tiptap a[data-richtext-link]")
        self.assertTrue(
            any(d.get("testmodel") == "3" for d in self.get_link_data_list())
        )


@skip_unless_selenium
class QuillEditorTests(EditorTestCase):
    """Condensed coverage for the quill adapter (field richtext_quill)."""

    def test_editor_renders_and_upgrades_marker(self):
        self.open_change_form(2, ".ql-editor")
        self.webdriver.find_css(".ql-toolbar button.ql-djangolink")
        # the legacy data-quilljs-link fixture link got re-created with the
        # new marker by the blot
        self.webdriver.find_css(".ql-editor a[data-richtext-link]")
        editor = self.webdriver.find_css(".ql-editor")
        editor = editor[0] if isinstance(editor, list) else editor
        editor.click()
        editor.send_keys("x")
        value = self.get_textarea_value("richtext_quill")
        # upgraded to the current format: json payload in the marker
        self.assertIn('data-richtext-link="{', value)
        self.assertNotIn("data-quilljs-link", value)

    def test_dialog_applies(self):
        self.open_change_form(2, ".ql-editor")
        editor = self.webdriver.find_css(".ql-editor")
        editor = editor[0] if isinstance(editor, list) else editor
        editor.click()
        self.webdriver.find_css(".ql-toolbar button.ql-djangolink").click()
        self.switch_to_dialog_iframe()
        email_input = self.webdriver.wait_for_css("#id_email")
        email_input.send_keys("test@bnzk.ch")
        self.click_dialog_ok()
        self.webdriver.wait_for_css(".ql-editor a[data-richtext-link]")
        datas = self.get_link_data_list("richtext_quill")
        self.assertTrue(any(d.get("email") == "test@bnzk.ch" for d in datas))


@skip_unless_selenium
@unittest.skipUnless(
    HAS_CKEDITOR5, "no ckeditor5 umd build - run richtext_link/tests/get_ckeditor5.sh"
)
class Ckeditor5EditorTests(EditorTestCase):
    """Condensed coverage for the ckeditor5 adapter (field richtext_ckeditor)."""

    def find_editable(self):
        editable = self.webdriver.find_css(
            ".richtext-link-ckeditor5 .ck-editor__editable"
        )
        return editable[0] if isinstance(editable, list) else editable

    def test_editor_renders(self):
        self.open_change_form(2, ".richtext-link-ckeditor5 .ck-editor__editable")
        self.webdriver.find_css(".ck-toolbar .richtext-link-ckeditor5-djangolink")
        # fixture link survived the html -> model -> view round trip
        self.webdriver.find_css(".ck-editor__editable a[data-richtext-link]")

    def test_dialog_opens_validates_and_applies(self):
        self.open_change_form(2, ".richtext-link-ckeditor5 .ck-editor__editable")
        self.find_editable().click()
        self.webdriver.find_css(".richtext-link-ckeditor5-djangolink").click()
        self.switch_to_dialog_iframe()
        email_input = self.webdriver.wait_for_css("#id_email")
        email_input.send_keys("no-email")
        self.click_dialog_ok()
        self.switch_to_dialog_iframe()
        self.webdriver.wait_for_css(".field-email .errorlist")
        email_input = self.webdriver.find_css("#id_email")
        email_input.clear()
        email_input.send_keys("test@bnzk.ch")
        self.click_dialog_ok()
        self.webdriver.wait_for_css(".ck-editor__editable a[data-richtext-link]")
        self.assertIn(
            'data-richtext-link="{', self.get_textarea_value("richtext_ckeditor")
        )
        datas = self.get_link_data_list("richtext_ckeditor")
        self.assertTrue(any(d.get("email") == "test@bnzk.ch" for d in datas))

    def test_legacy_ckeditor_marker_upgraded(self):
        self.open_change_form(3, ".richtext-link-ckeditor5 .ck-editor__editable")
        # legacy data-ckeditor-link fixture link got the new marker in the view
        self.webdriver.find_css(".ck-editor__editable a[data-richtext-link]")
        editable = self.find_editable()
        editable.click()
        editable.send_keys("x")
        value = self.get_textarea_value("richtext_ckeditor")
        # upgraded to the current format: json payload in the marker
        self.assertIn('data-richtext-link="{', value)
        self.assertNotIn("data-ckeditor-link", value)
        # the plain link stays plain
        self.assertIn('<a href="https://www.example.com/">', value)

    @override_settings(RICHTEXT_LINK_CONFIGS=CKEDITOR5_ENTER_BR_CONFIGS)
    def test_enter_mode_br(self):
        self.open_change_form(1, ".richtext-link-ckeditor5 .ck-editor__editable")
        editable = self.find_editable()
        editable.click()
        editable.send_keys("x")
        editable.send_keys(Keys.ENTER)
        editable.send_keys("y")
        value = self.get_textarea_value("richtext_ckeditor")
        self.assertIn("<br", value)
        self.assertEqual(value.count("<p>"), 1)
