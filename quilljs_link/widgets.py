import copy

from django import forms
from django.utils.encoding import force_str
from django.utils.functional import Promise

from quilljs_link import conf, utils


def _force_lazy(value):
    """Recursively force lazy strings, so json_script can serialize the config."""
    if isinstance(value, Promise):
        return force_str(value)
    if isinstance(value, dict):
        return {key: _force_lazy(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_force_lazy(item) for item in value]
    return value


class QuillWidget(forms.Textarea):
    template_name = "quilljs_link/widget.html"

    def __init__(self, attrs=None, config_name="default"):
        self.config_name = config_name
        default_attrs = {"data-quilljs-link-widget": "1"}
        if attrs:
            default_attrs.update(attrs)
        super().__init__(default_attrs)

    def get_config(self):
        configs = conf.get_configs()
        config = copy.deepcopy(
            configs.get(self.config_name, conf.QUILLJS_LINK_DEFAULT_CONFIG)
        )
        modules = config.setdefault("modules", {})
        djangolink = modules.get("djangolink", None)
        if isinstance(djangolink, dict) and (
            not djangolink.get("iframeUrl") or not djangolink.get("verifyUrl")
        ):
            # fill missing dialog urls from the link model's admin
            iframe_url, verify_url = utils.get_default_dialog_urls()
            if iframe_url and not djangolink.get("iframeUrl"):
                djangolink["iframeUrl"] = iframe_url
            if verify_url and not djangolink.get("verifyUrl"):
                djangolink["verifyUrl"] = verify_url
        return _force_lazy(config)

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        widget_id = context["widget"]["attrs"].get("id", f"id_{name}")
        context["widget"]["config"] = self.get_config()
        context["widget"]["config_id"] = f"{widget_id}_quilljs_config"
        return context

    class Media:
        css = {
            "all": (
                "quilljs_link/vendor/quill/quill.snow.css",
                "quilljs_link/css/quilljs_link.css",
            ),
        }
        js = (
            "quilljs_link/vendor/quill/quill.js",
            "quilljs_link/js/quilljs-link.js",
            "quilljs_link/js/widget-init.js",
        )
