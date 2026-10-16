from django.test import TestCase, override_settings

from richtext_link.tests.test_app.models import TestModel

MARKED = (
    '<p><a data-richtext-link=\'{"external_url":"http://x.com/"}\' '
    'href="#">my link</a></p>'
)
LEGACY_MARKED = (
    '<p><a data-ckeditor-link="true" data-external_url="http://x.com/" '
    'href="#">my link</a></p>'
)
STRIPPED = '<p><a href="#">my link</a></p>'


class SaveGuardTests(TestCase):
    def create(self, richtext=MARKED):
        return TestModel.objects.create(title="guarded", richtext=richtext)

    def test_stripped_link_logs_error(self):
        obj = self.create()
        obj.richtext = STRIPPED
        with self.assertLogs("richtext_link", "ERROR") as logs:
            obj.save()
        self.assertIn("my link", logs.output[0])
        self.assertIn("lost its payload", logs.output[0])

    def test_deliberate_removal_is_silent(self):
        obj = self.create()
        obj.richtext = "<p>no link anymore</p>"
        with self.assertNoLogs("richtext_link", "ERROR"):
            obj.save()

    def test_unchanged_save_is_silent(self):
        obj = self.create()
        with self.assertNoLogs("richtext_link", "ERROR"):
            obj.save()

    def test_legacy_upgrade_is_silent(self):
        # legacy format resaved in the json format: same canonical payload
        obj = self.create(richtext=LEGACY_MARKED)
        obj.richtext = MARKED
        with self.assertNoLogs("richtext_link", "ERROR"):
            obj.save()

    def test_dialog_edit_is_silent(self):
        # marker still there, payload changed: a deliberate edit
        obj = self.create()
        obj.richtext = MARKED.replace("x.com", "y.com")
        with self.assertNoLogs("richtext_link", "ERROR"):
            obj.save()

    def test_create_is_silent(self):
        with self.assertNoLogs("richtext_link", "ERROR"):
            self.create()

    @override_settings(RICHTEXT_LINK_SAVE_GUARD=False)
    def test_guard_disabled(self):
        obj = self.create()
        obj.richtext = STRIPPED
        with self.assertNoLogs("richtext_link", "ERROR"):
            obj.save()
