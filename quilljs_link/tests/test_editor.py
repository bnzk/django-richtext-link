"""
Selenium editor tests - few and focused, they are slow and inherently flaky.
Skipped when selenium/geckodriver is not available.
"""
from django.urls import reverse

from quilljs_link.tests.utils.selenium_utils import (
    SeleniumTestCase,
    skip_unless_selenium,
)


@skip_unless_selenium
class QuillEditorTests(SeleniumTestCase):
    fixtures = [
        "test_app.json",
    ]

    def open_change_form(self, pk):
        self.login()
        self.open(reverse("admin:test_app_testmodel_change", args=[pk]))
        self.webdriver.wait_for_css(".ql-editor")

    def get_textarea_value(self, field="richtext"):
        value = self.webdriver.execute_script(
            f'return document.getElementById("id_{field}").value;'
        )
        # quill's getSemanticHTML encodes spaces as &nbsp; - normalize for asserts
        return value.replace("&nbsp;", " ")

    def switch_to_dialog_iframe(self):
        iframe = self.webdriver.wait_for_css(".quilljs-link-dialog[open] iframe")
        self.webdriver.switch_to.frame(iframe)

    def test_editor_renders(self):
        self.open_change_form(2)
        self.webdriver.find_css(".ql-toolbar button.ql-djangolink")
        # fixture links survived the html -> delta -> dom round trip
        links = self.webdriver.find_css(".ql-editor a[data-quilljs-link]")
        if not isinstance(links, list):
            links = [links]
        self.assertTrue(len(links) >= 1)

    def test_dialog_opens_validates_and_applies(self):
        self.open_change_form(2)
        # place the cursor in the first editor
        editors = self.webdriver.find_css(".ql-editor")
        editors[0].click()
        buttons = self.webdriver.find_css(".ql-toolbar button.ql-djangolink")
        buttons[0].click()
        # invalid input -> errorlist inside the iframe
        self.switch_to_dialog_iframe()
        email_input = self.webdriver.wait_for_css("#id_email")
        email_input.send_keys("no-email")
        self.webdriver.switch_to.default_content()
        self.webdriver.find_css(".quilljs-link-dialog__buttons button.default").click()
        self.switch_to_dialog_iframe()
        self.webdriver.wait_for_css(".field-email .errorlist")
        # fix it -> link applied, dialog closed
        email_input = self.webdriver.find_css("#id_email")
        email_input.clear()
        email_input.send_keys("test@bnzk.ch")
        self.webdriver.switch_to.default_content()
        self.webdriver.find_css(".quilljs-link-dialog__buttons button.default").click()
        self.webdriver.wait_for_css(".ql-editor a[data-quilljs-link='true']")
        self.assertIn("data-quilljs-link", self.get_textarea_value())
        self.assertIn('data-email="test@bnzk.ch"', self.get_textarea_value())

    def test_legacy_link_upgraded(self):
        self.open_change_form(3)
        # the blot re-created the legacy node with the new marker
        self.webdriver.find_css(".ql-editor a[data-quilljs-link]")
        # after an edit, the synced html carries the new marker only
        editors = self.webdriver.find_css(".ql-editor")
        editor = editors[0] if isinstance(editors, list) else editors
        editor.click()
        editor.send_keys("x")
        value = self.get_textarea_value()
        self.assertIn("data-quilljs-link", value)
        self.assertNotIn("data-ckeditor-link", value)

    def test_dialog_quick_search(self):
        self.open_change_form(2)
        editors = self.webdriver.find_css(".ql-editor")
        editors[0].click()
        buttons = self.webdriver.find_css(".ql-toolbar button.ql-djangolink")
        buttons[0].click()
        self.switch_to_dialog_iframe()
        search_input = self.webdriver.wait_for_css(".quilljs-link-search input")
        search_input.send_keys("Legacy")
        self.webdriver.wait_for_css(".quilljs-link-search__item").click()
        selected = self.webdriver.execute_script(
            'return document.getElementById("id_testmodel").value;'
        )
        self.assertEqual(selected, "3")
        self.webdriver.switch_to.default_content()
        self.webdriver.find_css(".quilljs-link-dialog__buttons button.default").click()
        self.webdriver.wait_for_css(".ql-editor a[data-quilljs-link='true']")
        self.assertIn('data-testmodel="3"', self.get_textarea_value())

    def test_two_editors_independent(self):
        self.open_change_form(2)
        editors = self.webdriver.find_css(".ql-editor")
        self.assertEqual(len(editors), 2)
        second_before = self.get_textarea_value("richtext_second")
        editors[0].click()
        editors[0].send_keys("hello first editor")
        self.assertIn("hello first editor", self.get_textarea_value("richtext"))
        self.assertEqual(second_before, self.get_textarea_value("richtext_second"))
