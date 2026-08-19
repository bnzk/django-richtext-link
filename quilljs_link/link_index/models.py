from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.translation import gettext_lazy as _


class LinkIndexEntry(models.Model):
    """
    One entry per link target per <a> tag found in indexed richtext content.
    Links without an object target (external, mailto, ...) get an entry with
    an empty target. Derived data - rebuildable at any time with the
    rebuild_quilljs_link_index management command.
    """

    source_content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        related_name="+",
    )
    source_object_id = models.CharField(max_length=255)
    source_field = models.CharField(max_length=255)
    target_content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        related_name="+",
        null=True,
        blank=True,
    )
    target_object_id = models.CharField(max_length=255, blank=True, default="")
    link_data = models.JSONField(default=dict, blank=True)
    href = models.CharField(max_length=2000, blank=True, default="")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Link index entry")
        verbose_name_plural = _("Link index entries")
        indexes = [
            models.Index(fields=["source_content_type", "source_object_id"]),
            models.Index(fields=["target_content_type", "target_object_id"]),
        ]

    def __str__(self):
        return (
            f"{self.source_content_type}#{self.source_object_id}"
            f".{self.source_field} -> {self.href}"
        )

    @property
    def source(self):
        return self._get_object(self.source_content_type, self.source_object_id)

    @property
    def target(self):
        return self._get_object(self.target_content_type, self.target_object_id)

    def _get_object(self, content_type, object_id):
        if content_type is None or not object_id:
            return None
        model = content_type.model_class()
        if model is None:
            return None
        return model._default_manager.filter(pk=object_id).first()
