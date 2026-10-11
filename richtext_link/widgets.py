import copy

from django import forms
from django.utils.encoding import force_str
from django.utils.functional import Promise

from richtext_link import conf, utils


def _force_lazy(value):
    """Recursively force lazy strings, so json_script can serialize the config."""
    if isinstance(value, Promise):
        return force_str(value)
    if isinstance(value, dict):
        return {key: _force_lazy(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_force_lazy(item) for item in value]
    return value


class RichtextWidget(forms.Textarea):
    template_name = "richtext_link/widget.html"

    def __init__(self, attrs=None, config_name="default"):
        self.config_name = config_name
        default_attrs = {"data-richtext-link-widget": "1"}
        if attrs:
            default_attrs.update(attrs)
        super().__init__(default_attrs)

    def _resolve_config(self):
        configs = conf.get_configs()
        return copy.deepcopy(
            configs.get(self.config_name, conf.RICHTEXT_LINK_DEFAULT_CONFIG)
        )

    def get_editor(self, config=None):
        if config is None:
            config = self._resolve_config()
        return config.get("editor", "tiptap")

    def get_config(self):
        config = self._resolve_config()
        config["editor"] = self.get_editor(config)
        # the djangolink options live editor dependent:
        # quill in modules.djangolink, tiptap/ckeditor5 top level
        if config["editor"] == "quilljs":
            djangolink = config.get("modules", {}).get("djangolink")
        else:
            djangolink = config.get("djangolink")
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
        context["widget"]["config_id"] = f"{widget_id}_richtext_config"
        return context

    @property
    def media(self):
        config = self._resolve_config()
        editor = self.get_editor(config)
        css = ["richtext_link/css/richtext_link.css"]
        if editor == "quilljs":
            css.insert(0, "richtext_link/vendor/quill/quill.snow.css")
            js = [
                "richtext_link/vendor/quill/quill.js",
                "richtext_link/js/richtext-link-core.js",
                "richtext_link/js/richtext-link-quill.js",
            ]
        elif editor == "ckeditor5":
            # bring-your-own CKEditor 5 (nothing GPL is shipped): the optional
            # "assets" entries are loaded first - forms.Media leaves absolute
            # urls untouched and runs relative paths through static()
            js = [
                "richtext_link/js/richtext-link-core.js",
                "richtext_link/js/richtext-link-ckeditor5.js",
            ]
            assets = config.get("assets") or {}
            if assets.get("js"):
                js.insert(0, force_str(assets["js"]))
            if assets.get("css"):
                css.insert(0, force_str(assets["css"]))
        else:
            js = [
                "richtext_link/vendor/tiptap/tiptap-bundle.js",
                "richtext_link/js/richtext-link-core.js",
                "richtext_link/js/richtext-link-tiptap.js",
            ]
        js.append("richtext_link/js/widget-init.js")
        return forms.widgets.Media(css={"all": css}, js=js)
