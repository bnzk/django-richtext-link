from django.apps import AppConfig
from django.db.models.signals import post_delete, post_save, pre_delete


class LinkIndexConfig(AppConfig):
    name = "richtext_link.link_index"
    label = "richtext_link_index"
    verbose_name = "Richtext link index"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        post_save.connect(update_index, dispatch_uid="richtext_link_index_update")
        post_delete.connect(remove_index, dispatch_uid="richtext_link_index_remove")
        pre_delete.connect(protect_targets, dispatch_uid="richtext_link_index_protect")


def update_index(sender, instance, **kwargs):
    from . import index

    if kwargs.get("raw"):
        # loaddata & co - use the rebuild_richtext_link_index command afterwards
        return
    fields = index.get_indexed_fields(sender)
    if fields:
        index.update_index_for_instance(instance, fields)


def remove_index(sender, instance, **kwargs):
    from . import index

    if index.get_indexed_fields(sender):
        index.remove_index_for_instance(instance)


def protect_targets(sender, instance, **kwargs):
    from . import conf, index
    from .models import LinkIndexEntry

    if not conf.get_index_protect() or sender is LinkIndexEntry:
        return
    inbound_links = index.get_inbound_links(instance)
    if inbound_links.exists():
        raise index.LinkedObjectProtectedError(instance, inbound_links)
