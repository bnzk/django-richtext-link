from django.contrib import admin

from .models import LinkIndexEntry


@admin.register(LinkIndexEntry)
class LinkIndexEntryAdmin(admin.ModelAdmin):
    """Read only - the index is derived data, browse & report only."""

    list_display = (
        "source_content_type",
        "source_object_id",
        "source_field",
        "target_content_type",
        "target_object_id",
        "href",
        "updated_at",
    )
    list_filter = (
        "source_content_type",
        "target_content_type",
        "source_field",
    )
    search_fields = (
        "source_object_id",
        "target_object_id",
        "href",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
