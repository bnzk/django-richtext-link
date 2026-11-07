"""
djangocms-text integration: richtext-link's model based link dialog inside
djangocms-text's TipTap editor.

Usage (settings)::

    TEXT_EDITOR = "richtext_link.contrib.djangocms_text.rte_config"

or, to add project assets, instantiate your own::

    # myproject/editor_config.py
    from richtext_link.contrib.djangocms_text import RichtextLinkRTEConfig

    my_tiptap = RichtextLinkRTEConfig(
        js=("myproject/js/tiptap_extra.js",),
        css={"all": ("myproject/css/rte.css",)},
    )

    # settings: TEXT_EDITOR = "myproject.editor_config.my_tiptap"

The bridge JS preserves richtext-link data on the link mark (djangocms-text's
own schema would strip it on save; legacy data-ckeditor-link/data-quilljs-link
markers are read and upgraded), and routes the toolbar Link button and clicks
on links to richtext-link's dialog instead of djangocms-text's built-in link
form. Rendering stays yours: run the output through the
``richtext_link_add_links`` template filter, as with any richtext-link field
(djangocms-text's render pipeline does not do that for you).

Dialog urls are derived from the link model's admin, like everywhere else in
richtext-link; override via the ``djangolink`` argument
(``{"iframeUrl": ..., "verifyUrl": ..., "fallbackField": ..., ...}``).

NOTE: djangocms-text's inline editing builds its editor settings from the
global settings, which carry no custom configuration - the dialog only opens
in field editors (plugin modal, HTMLField). Inline editors still get the data
preservation.

This module imports djangocms_text - only import it when djangocms-text is
installed.
"""

from djangocms_text.editors import RTEConfig

from richtext_link import utils

BRIDGE_JS = (
    "richtext_link/js/richtext-link-core.js",
    "richtext_link/js/richtext-link-djangocms-text.js",
)
BRIDGE_CSS = ("richtext_link/css/richtext_link.css",)


class RichtextLinkRTEConfig(RTEConfig):
    def __init__(
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
