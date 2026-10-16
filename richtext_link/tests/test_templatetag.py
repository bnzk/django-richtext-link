from django.template import Context, Template
from django.test import Client, TestCase
from django.urls import reverse

from richtext_link.tests.test_app.models import TestModel


def render_filter(html):
    template = Template(
        "{% load richtext_link_tags %}{{ html|richtext_link_add_links|safe }}"
    )
    return template.render(Context({"html": html}))


class RichtextLinkTemplateTagTests(TestCase):
    fixtures = [
        "test_app.json",
    ]

    def setUp(self):
        self.test_object = TestModel.objects.get(pk=2)
        self.test_object_not_existing_fk = TestModel.objects.get(pk=1)
        self.test_object_legacy = TestModel.objects.get(pk=3)

    def get_response(self, obj):
        client = Client()
        url = reverse("testmodel_detail", args=[obj.id])
        response = client.get(url)
        self.assertEqual(response.status_code, 200)
        return response

    def test_tag_link_target_class_value(self):
        """
        does it transform everything as it should?
        """
        response = self.get_response(self.test_object)
        # fk link resolved to the testmodel's absolute url
        self.assertContains(response, 'href="/testmodel/1/"')
        self.assertContains(response, 'class="no-css-class"')
        # markers and consumed data attributes are gone
        self.assertNotContains(response, "data-richtext-link")
        self.assertNotContains(response, "data-quilljs-link")
        self.assertNotContains(response, "data-testmodel")
        self.assertNotContains(response, "data-external_url")

    def test_get_link_attrs(self):
        """
        can it output correct link attrs
        """
        response = self.get_response(self.test_object)
        self.assertContains(response, 'data-test="abc"')

    def test_tag_attr_modifiers(self):
        """
        do attr modifiers work?
        has data-target="targetvalue", needs <a href="targetvalue--xy"
        """
        response = self.get_response(self.test_object)
        self.assertContains(response, 'href="targetvalue--xy"')

    def test_not_existing_foreign_key_value(self):
        """
        can it handle no more existing foreign key values set in links?
        """
        response = self.get_response(self.test_object_not_existing_fk)
        self.assertEqual(response.status_code, 200)

    def test_legacy_ckeditor_marker(self):
        """
        data-ckeditor-link content renders exactly like data-richtext-link content
        """
        response = self.get_response(self.test_object_legacy)
        self.assertContains(response, 'href="/testmodel/1/"')
        self.assertContains(response, 'target="_blank"')
        self.assertNotContains(response, "data-ckeditor-link")
        self.assertNotContains(response, "data-testmodel")

    def test_plain_links_untouched(self):
        """
        normal existing <a href="xx"> should not be tinkered with
        """
        response = self.get_response(self.test_object_legacy)
        self.assertContains(response, 'href="https://www.example.com/"')

    def test_no_wrapper_div_leaked(self):
        result = render_filter("<p>hello</p>")
        self.assertEqual(result, "<p>hello</p>")

    def test_text_outside_tags_kept(self):
        result = render_filter("before <p>hello</p>")
        self.assertEqual(result, "before <p>hello</p>")

    def test_json_format(self):
        """
        the current format: the marker attribute carries the json payload
        """
        result = render_filter(
            '<p><a data-richtext-link=\'{"external_url":"http://x.com/"}\'>x</a></p>'
        )
        self.assertIn('href="http://x.com/"', result)
        self.assertNotIn("data-richtext-link", result)

    def test_json_format_fk(self):
        result = render_filter(
            '<p><a data-richtext-link=\'{"testmodel":"2"}\'>x</a></p>'
        )
        self.assertIn('href="/testmodel/2/"', result)
        self.assertNotIn("data-richtext-link", result)
        self.assertNotIn("data-testmodel", result)

    def test_json_format_mangled_payload(self):
        """
        a broken json payload degrades to the legacy attr format reading
        """
        result = render_filter(
            "<p><a data-richtext-link='{\"external_url\": broken' "
            'data-external_url="http://x.com/">x</a></p>'
        )
        self.assertIn('href="http://x.com/"', result)
        self.assertNotIn("data-richtext-link", result)

    def test_target_from_get_link_target(self):
        """
        legacy attr format (django-richtext-link 0.2): marker "true" plus one
        data-* attribute per field - read forever
        """
        result = render_filter(
            '<p><a data-richtext-link="true" data-external_url="http://x.com/">x</a></p>'
        )
        self.assertIn('href="http://x.com/"', result)
        self.assertIn('target="_blank"', result)

    def test_legacy_quilljs_marker(self):
        """
        data-quilljs-link content (django-quilljs-link 0.1.0) renders
        exactly like data-richtext-link content
        """
        result = render_filter(
            '<p><a data-quilljs-link="true" data-external_url="http://x.com/">x</a></p>'
        )
        self.assertIn('href="http://x.com/"', result)
        self.assertNotIn("data-quilljs-link", result)

    def test_unknown_data_attrs_stay(self):
        result = render_filter(
            '<p><a data-richtext-link="true" data-nosuchfield="keepme" '
            'data-external_url="http://x.com/">x</a></p>'
        )
        self.assertIn('data-nosuchfield="keepme"', result)
        self.assertNotIn("data-richtext-link", result)
