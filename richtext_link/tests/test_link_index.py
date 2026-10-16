from django.contrib.contenttypes.models import ContentType
from django.core.management import call_command
from django.test import TestCase, override_settings

from richtext_link.link_index import index
from richtext_link.link_index.index import LinkedObjectProtectedError
from richtext_link.link_index.models import LinkIndexEntry
from richtext_link.tests.test_app.models import TestModel

DJANGO_LINK_HTML = (
    '<p><a data-richtext-link=\'{{"testmodel":"{pk}"}}\' '
    'href="/testmodel/{pk}/">fk link</a> and '
    '<a data-richtext-link=\'{{"external_url":"http://x.com/"}}\' '
    'href="http://x.com/">external</a></p>'
)


class LinkIndexTests(TestCase):
    def setUp(self):
        self.target = TestModel.objects.create(title="target")

    def create_source(self, **kwargs):
        kwargs.setdefault("title", "source")
        kwargs.setdefault("richtext", DJANGO_LINK_HTML.format(pk=self.target.pk))
        return TestModel.objects.create(**kwargs)

    def test_entries_created_on_save(self):
        source = self.create_source()
        entries = LinkIndexEntry.objects.filter(source_object_id=str(source.pk))
        self.assertEqual(entries.count(), 2)
        fk_entry = entries.exclude(target_content_type=None).get()
        self.assertEqual(fk_entry.target_object_id, str(self.target.pk))
        self.assertEqual(fk_entry.source_field, "richtext")
        self.assertEqual(fk_entry.href, f"/testmodel/{self.target.pk}/")
        self.assertEqual(fk_entry.target, self.target)
        self.assertEqual(fk_entry.source, source)
        external_entry = entries.filter(target_content_type=None).get()
        self.assertEqual(external_entry.href, "http://x.com/")
        self.assertEqual(external_entry.link_data["external_url"], "http://x.com/")

    def test_entries_replaced_on_save(self):
        source = self.create_source()
        source.richtext = "<p>no more links</p>"
        source.save()
        self.assertEqual(
            LinkIndexEntry.objects.filter(source_object_id=str(source.pk)).count(),
            0,
        )

    def test_no_duplicates_on_repeated_save(self):
        source = self.create_source()
        source.save()
        source.save()
        self.assertEqual(
            LinkIndexEntry.objects.filter(source_object_id=str(source.pk)).count(),
            2,
        )

    def test_entries_removed_on_delete(self):
        source = self.create_source()
        source_pk = source.pk
        source.delete()
        self.assertEqual(
            LinkIndexEntry.objects.filter(source_object_id=str(source_pk)).count(),
            0,
        )

    def test_get_inbound_links(self):
        source = self.create_source()
        inbound = index.get_inbound_links(self.target)
        self.assertEqual(inbound.count(), 1)
        self.assertEqual(inbound.get().source_object_id, str(source.pk))
        self.assertEqual(index.get_inbound_links(source).count(), 0)

    def test_legacy_attr_format_indexed(self):
        """django-richtext-link 0.2 format: marker "true" + data-* attributes"""
        source = self.create_source(
            richtext=(
                f'<p><a data-richtext-link="true" '
                f'data-testmodel="{self.target.pk}" href="x">attr format</a></p>'
            )
        )
        self.assertEqual(index.get_inbound_links(self.target).count(), 1)
        self.assertEqual(
            index.get_inbound_links(self.target).get().source_object_id,
            str(source.pk),
        )

    def test_legacy_ckeditor_marker_indexed(self):
        source = self.create_source(
            richtext=(
                f'<p><a data-ckeditor-link="true" data-testmodel="{self.target.pk}"'
                ' href="x">legacy</a></p>'
            )
        )
        self.assertEqual(index.get_inbound_links(self.target).count(), 1)
        self.assertEqual(
            index.get_inbound_links(self.target).get().source_object_id,
            str(source.pk),
        )

    def test_legacy_quilljs_marker_indexed(self):
        source = self.create_source(
            richtext=(
                f'<p><a data-quilljs-link="true" data-testmodel="{self.target.pk}"'
                ' href="x">legacy</a></p>'
            )
        )
        self.assertEqual(index.get_inbound_links(self.target).count(), 1)
        self.assertEqual(
            index.get_inbound_links(self.target).get().source_object_id,
            str(source.pk),
        )

    def test_dangling_fk_indexed_with_empty_href(self):
        source = self.create_source(
            richtext='<p><a data-richtext-link="true" data-testmodel="4242" '
            'href="x">dangling</a></p>'
        )
        entry = LinkIndexEntry.objects.get(source_object_id=str(source.pk))
        self.assertEqual(entry.target_object_id, "4242")
        self.assertEqual(entry.href, "")
        self.assertIsNone(entry.target)

    def test_rebuild_command(self):
        source = self.create_source()
        LinkIndexEntry.objects.all().delete()
        call_command("rebuild_richtext_link_index", verbosity=0)
        self.assertEqual(
            LinkIndexEntry.objects.filter(source_object_id=str(source.pk)).count(),
            2,
        )

    def test_indexed_models_autodetection(self):
        self.assertIn(TestModel, index.indexed_models())
        self.assertEqual(
            index.indexed_models()[TestModel],
            ("richtext", "richtext_second", "richtext_quill", "richtext_ckeditor"),
        )

    @override_settings(RICHTEXT_LINK_INDEX_PROTECT=True)
    def test_protect_linked_target(self):
        self.create_source()
        with self.assertRaises(LinkedObjectProtectedError):
            self.target.delete()

    @override_settings(RICHTEXT_LINK_INDEX_PROTECT=True)
    def test_protect_allows_unlinked_delete(self):
        unlinked = TestModel.objects.create(title="unlinked")
        unlinked.delete()
        self.assertFalse(TestModel.objects.filter(title="unlinked").exists())

    def test_second_field_indexed(self):
        source = self.create_source(
            richtext="",
            richtext_second=DJANGO_LINK_HTML.format(pk=self.target.pk),
        )
        entries = LinkIndexEntry.objects.filter(source_object_id=str(source.pk))
        self.assertEqual(entries.count(), 2)
        self.assertEqual(entries.first().source_field, "richtext_second")

    def test_index_entry_content_types(self):
        self.create_source()
        entry = LinkIndexEntry.objects.exclude(target_content_type=None).get()
        testmodel_ct = ContentType.objects.get_for_model(TestModel)
        self.assertEqual(entry.source_content_type, testmodel_ct)
        self.assertEqual(entry.target_content_type, testmodel_ct)
