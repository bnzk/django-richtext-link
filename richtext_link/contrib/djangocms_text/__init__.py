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

The real implementation lives in ``config`` (which imports djangocms_text);
this package import stays safe without djangocms-text installed, so test
discovery and plain projects never trip over the optional dependency.
"""

try:
    import djangocms_text  # noqa: F401
except ImportError:
    _HAS_DJANGOCMS_TEXT = False
else:
    _HAS_DJANGOCMS_TEXT = True

if _HAS_DJANGOCMS_TEXT:
    from richtext_link.contrib.djangocms_text.config import (  # noqa: F401
        RichtextLinkRTEConfig,
        rte_config,
    )
else:

    def __getattr__(name):
        # AttributeError, not ImportError: getattr(package, ..., default)
        # (unittest discovery probes load_tests) must keep working
        msg = (
            f"richtext_link.contrib.djangocms_text.{name} requires "
            f"djangocms-text: pip install djangocms-text"
        )
        raise AttributeError(msg)
