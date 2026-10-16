"""
The richtext_link_editor_check management command spawns its own probe page
server and headless browser - no database, but selenium/geckodriver needed.
"""
from io import StringIO

from django.core.management import CommandError, call_command
from django.test import SimpleTestCase, override_settings

from richtext_link.tests.utils.selenium_utils import skip_unless_selenium

HEALTHY_CONFIGS = {
    "default": {"editor": "tiptap", "toolbar": [["bold"]]},
    "quill": {"editor": "quilljs", "modules": {"toolbar": [["bold"]]}},
    # bring your own build: reported as skipped, not failed
    "ck_byo": {"editor": "ckeditor5"},
}

# a quill formats whitelist without "link" strips every link at load
BROKEN_CONFIGS = {
    "quill_broken": {
        "editor": "quilljs",
        "formats": ["bold"],
        "modules": {"toolbar": [["bold"]]},
    },
}


@skip_unless_selenium
class EditorCheckCommandTests(SimpleTestCase):
    @override_settings(RICHTEXT_LINK_CONFIGS=HEALTHY_CONFIGS)
    def test_command_passes(self):
        out = StringIO()
        call_command("richtext_link_editor_check", stdout=out)
        output = out.getvalue()
        self.assertIn("all editor round trips ok", output)
        self.assertIn("default: ok", output)
        self.assertIn("quill: ok", output)
        self.assertIn("skipped: ck_byo", output)

    @override_settings(RICHTEXT_LINK_CONFIGS=BROKEN_CONFIGS)
    def test_command_detects_link_data_loss(self):
        out = StringIO()
        with self.assertRaises(CommandError) as caught:
            call_command("richtext_link_editor_check", stdout=out)
        self.assertIn("quill_broken", str(caught.exception))
        self.assertIn("quill_broken: lost", out.getvalue())
