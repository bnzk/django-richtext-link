import contextlib

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.utils.encoding import force_str

from quilljs_link import utils

from .models import LinkIndexEntry


class LinkedObjectProtectedError(Exception):
    """Raised on delete of a link target when QUILLJS_LINK_INDEX_PROTECT is on."""

    def __init__(self, obj, inbound_links):
        self.obj = obj
        self.inbound_links = inbound_links
        super().__init__(
            f"Cannot delete {obj!r}: it is the target of "
            f"{inbound_links.count()} indexed link(s)."
        )


# explicitly registered models: {model_class: (field_name, ...)}
_registry = {}
# per model cache of indexed field names: {model_class: (field_name, ...)}
_fields_cache = {}


def register(model, fields):
    """Register a model with richtext fields the QuillField autodetection misses."""
    _registry[model] = tuple(fields)
    _fields_cache.pop(model, None)


def get_indexed_fields(model):
    if model not in _fields_cache:
        if model in _registry:
            _fields_cache[model] = _registry[model]
        else:
            from quilljs_link.fields import QuillField

            _fields_cache[model] = tuple(
                field.name
                for field in model._meta.get_fields()
                if isinstance(field, QuillField)
            )
    return _fields_cache[model]


def indexed_models():
    from django.apps import apps

    models = {}
    for model in apps.get_models():
        fields = get_indexed_fields(model)
        if fields:
            models[model] = fields
    return models


def get_inbound_links(obj):
    content_type = ContentType.objects.get_for_model(obj.__class__)
    return LinkIndexEntry.objects.filter(
        target_content_type=content_type,
        target_object_id=str(obj.pk),
    )


def update_index_for_instance(instance, fields=None):
    link_model = utils.get_link_model(silent=True)
    if link_model is None or instance.pk is None:
        return
    if fields is None:
        fields = get_indexed_fields(instance.__class__)
    if not fields:
        return
    source_content_type = ContentType.objects.get_for_model(instance.__class__)
    entries = []
    for field_name in fields:
        entries += _extract_entries(
            instance, field_name, link_model, source_content_type
        )
    with transaction.atomic():
        LinkIndexEntry.objects.filter(
            source_content_type=source_content_type,
            source_object_id=str(instance.pk),
            source_field__in=fields,
        ).delete()
        LinkIndexEntry.objects.bulk_create(entries)


def remove_index_for_instance(instance):
    source_content_type = ContentType.objects.get_for_model(instance.__class__)
    LinkIndexEntry.objects.filter(
        source_content_type=source_content_type,
        source_object_id=str(instance.pk),
    ).delete()


def _extract_entries(instance, field_name, link_model, source_content_type):
    html = getattr(instance, field_name, "") or ""
    entries = []
    if not html:
        return entries
    fragment = utils.parse_html_fragment(html)
    for link in utils.iter_link_elements(fragment):
        link_data = utils.link_data_from_element(link)
        kwargs = utils.link_kwargs_from_element(link, link_model)
        href = ""
        # dangling fk and the like - still index, href stays empty
        with contextlib.suppress(ValueError, ObjectDoesNotExist):
            href = force_str(link_model(**kwargs).get_link())
        base_kwargs = {
            "source_content_type": source_content_type,
            "source_object_id": str(instance.pk),
            "source_field": field_name,
            "link_data": link_data,
            "href": href,
        }
        targets = _extract_targets(kwargs, link_model)
        if targets:
            for target_content_type, target_object_id in targets:
                entries.append(
                    LinkIndexEntry(
                        target_content_type=target_content_type,
                        target_object_id=target_object_id,
                        **base_kwargs,
                    )
                )
        else:
            entries.append(LinkIndexEntry(**base_kwargs))
    return entries


def _extract_targets(link_kwargs, link_model):
    """
    (content_type, object_id) per foreign key field of the link model with a
    value - dangling references included, on purpose (broken link reports).
    """
    targets = []
    for field in link_model._meta.get_fields():
        if not (field.is_relation and field.many_to_one and field.related_model):
            continue
        value = link_kwargs.get(field.name + "_id")
        if value:
            content_type = ContentType.objects.get_for_model(field.related_model)
            targets.append((content_type, str(value)))
    return targets
