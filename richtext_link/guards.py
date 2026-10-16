"""
The last safety net: whatever stripped link data - a sanitizer in a save
path the checks never saw, a foreign admin form, an api - the loss becomes
visible when the stripped content is saved over the old value. A pre_save
comparison of the stored value logs an error for every link whose data
vanished while its anchor survived (utils.lost_link_data: deliberate link
removals stay silent). Wire the "richtext_link" logger to your error
reporting and nothing is lost silently. Disable with
RICHTEXT_LINK_SAVE_GUARD = False.
"""
import contextlib
import logging

from django.db.models.signals import pre_save

logger = logging.getLogger("richtext_link")

_fields_cache = {}


def _richtext_fields(model):
    if model not in _fields_cache:
        from richtext_link.fields import RichtextField

        _fields_cache[model] = tuple(
            field.name
            for field in model._meta.get_fields()
            if isinstance(field, RichtextField)
        )
    return _fields_cache[model]


def check_lost_link_data(sender, instance, **kwargs):
    from richtext_link import conf, utils

    if kwargs.get("raw") or instance.pk is None or not conf.get_save_guard():
        return
    fields = _richtext_fields(sender)
    if not fields:
        return

    old = sender._default_manager.filter(pk=instance.pk).values(*fields).first()
    if old is None:
        return
    for field in fields:
        # the guard must never break a save: no lxml (or content lxml
        # chokes on) means no guard, nothing else
        with contextlib.suppress(Exception):
            lost = utils.lost_link_data(
                old[field] or "", getattr(instance, field, "") or ""
            )
            for text, payload in lost:
                logger.error(
                    "richtext-link: link data lost on save of %s.%s pk=%s: "
                    'link "%s" kept its anchor but lost its payload %s - a '
                    "sanitizer or editor in this save path strips the "
                    "%s attribute.",
                    sender._meta.label,
                    field,
                    instance.pk,
                    text,
                    payload,
                    utils.MARKER_ATTRIBUTE,
                )


def connect():
    # always connected, the setting is honored per save (testable, and not
    # sensitive to settings configuration order)
    pre_save.connect(check_lost_link_data, dispatch_uid="richtext_link_save_guard")
