from django.core.management.base import BaseCommand

from quilljs_link.link_index import index
from quilljs_link.link_index.models import LinkIndexEntry


class Command(BaseCommand):
    help = "Wipe and rebuild the quilljs_link link index."

    def handle(self, *args, **options):
        LinkIndexEntry.objects.all().delete()
        object_count = 0
        for model, fields in index.indexed_models().items():
            for instance in model._default_manager.all().iterator():
                index.update_index_for_instance(instance, fields)
                object_count += 1
        entry_count = LinkIndexEntry.objects.count()
        self.stdout.write(
            f"Indexed {entry_count} link(s) from {object_count} object(s)."
        )
