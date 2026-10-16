from django.test import TestCase

from richtext_link import utils


def first_link(html):
    fragment = utils.parse_html_fragment(html)
    return next(utils.iter_link_elements(fragment))


class SerializeLinkDataTests(TestCase):
    def test_canonical_output(self):
        # sorted keys, compact, empties omitted, non-ascii literal, values
        # stringified - must match the editors' RichtextLink.serializeLinkData
        self.assertEqual(
            utils.serialize_link_data(
                {"zebra": 1, "alpha": "ä", "empty": "", "none": None}
            ),
            '{"alpha":"ä","zebra":"1"}',
        )

    def test_round_trip(self):
        data = {"link_type": "testmodel", "testmodel": "3"}
        html = (
            f"<p><a data-richtext-link='{utils.serialize_link_data(data)}'>"
            f"x</a></p>"
        )
        self.assertEqual(utils.link_data_from_element(first_link(html)), data)


class LinkDataFromElementTests(TestCase):
    def test_json_format(self):
        link = first_link(
            '<p><a data-richtext-link=\'{"cms_page":"3"}\' '
            'data-unrelated="kept">x</a></p>'
        )
        # the json payload wins; unrelated data-* attrs are not ours
        self.assertEqual(utils.link_data_from_element(link), {"cms_page": "3"})

    def test_legacy_attr_format(self):
        link = first_link('<p><a data-richtext-link="true" data-cms_page="3">x</a></p>')
        self.assertEqual(utils.link_data_from_element(link), {"cms_page": "3"})

    def test_legacy_markers(self):
        for marker in ("data-quilljs-link", "data-ckeditor-link"):
            link = first_link(f'<p><a {marker}="true" data-email="a@b.ch">x</a></p>')
            self.assertEqual(utils.link_data_from_element(link), {"email": "a@b.ch"})

    def test_mangled_json_falls_back_to_attrs(self):
        link = first_link(
            "<p><a data-richtext-link='{broken' data-email=\"a@b.ch\">x</a></p>"
        )
        self.assertEqual(utils.link_data_from_element(link), {"email": "a@b.ch"})

    def test_json_null_values_become_empty_strings(self):
        link = first_link("<p><a data-richtext-link='{\"testmodel\":null}'>x</a></p>")
        self.assertEqual(utils.link_data_from_element(link), {"testmodel": ""})
