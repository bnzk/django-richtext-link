"""Implementation of the djangocms-text bridge config - imports
djangocms_text, import only with djangocms-text installed (the package
__init__ guards this for test discovery / plain projects)."""

from djangocms_text.editors import RTEConfig

from richtext_link import utils

BRIDGE_JS = (
    "richtext_link/js/richtext-link-core.js",
    "richtext_link/js/richtext-link-djangocms-text.js",
)
BRIDGE_CSS = ("richtext_link/css/richtext_link.css",)


class RichtextLinkRTEConfig(RTEConfig):
    def __init__(  # noqa: PLR0913 - mirrors RTEConfig's signature + djangolink
        self,
        name="tiptap_richtext_link",
        config="TIPTAP",
        js=None,
        css=None,
        djangolink=None,
        **kwargs,
    ):
        self._djangolink = dict(djangolink or {})
        js = (
            ("djangocms_text/bundles/bundle.tiptap.min.js",)
            + BRIDGE_JS
            + tuple(js or ())
        )
        css = dict(css or {})
        css["all"] = (
            ("djangocms_text/css/bundle.tiptap.min.css",)
            + BRIDGE_CSS
            + tuple(css.get("all", ()))
        )
        kwargs.setdefault("admin_css", ("djangocms_text/css/tiptap.admin.css",))
        kwargs.setdefault("inline_editing", True)
        kwargs.setdefault("child_plugin_support", True)
        super().__init__(name=name, config=config, js=js, css=css, **kwargs)

    @property
    def configuration(self):
        # the urls MUST stay lazy: djangocms-text widgets can be instantiated
        # at import time (HTMLFormField on a module level form), where an
        # eager reverse() would freeze a half-populated admin urlconf. the
        # widget deepcopies this dict and json-dumps it with DjangoJSONEncoder
        # at render time - both handle lazy objects.
        djangolink = dict(self._djangolink)
        if not djangolink.get("iframeUrl") or not djangolink.get("verifyUrl"):
            iframe_url, verify_url = utils.get_default_dialog_urls()
            # `is not None`, never truthiness: bool() on a lazy url would
            # resolve it right here
            if iframe_url is not None and not djangolink.get("iframeUrl"):
                djangolink["iframeUrl"] = iframe_url
            if verify_url is not None and not djangolink.get("verifyUrl"):
                djangolink["verifyUrl"] = verify_url
        return dict(self._configuration, richtextLink=djangolink)

    @configuration.setter
    def configuration(self, value):
        self._configuration = dict(value or {})


rte_config = RichtextLinkRTEConfig()
