/*
 * django-richtext-link bridge for djangocms-text's TipTap editor.
 *
 * Registers, through djangocms-text's contrib registry
 * (window.CMS_Editor.tiptap):
 *
 * 1. a tiptap extension that
 *    - preserves richtext-link data on the "link" mark: the marker attribute
 *      (current json format and all legacy formats, data-ckeditor-link
 *      included) is parsed on load and re-rendered in the current format on
 *      save - djangocms-text's own link mark would otherwise strip it
 *    - intercepts clicks on links and opens richtext-link's dialog instead
 *      of djangocms-text's built-in link form
 * 2. a "Link" toolbar item override, so the stock toolbar button opens the
 *    richtext-link dialog too (icon + title keep coming from djangocms-text's
 *    lang pack).
 *
 * Needs richtext-link-core.js (global.RichtextLink) loaded before this file.
 * The tiptap bundle itself may load before or after - registration is queued
 * either way.
 *
 * Dialog options (iframeUrl, verifyUrl, fallbackField, linkText, ...) are
 * read from the editor settings json, key "richtextLink" - put there by
 * richtext_link.contrib.djangocms_text's RTEConfig. NOTE: inline editing
 * builds its settings from djangocms-text's global settings, which carry no
 * custom configuration - the dialog options reach field editors (plugin
 * modal, HTMLField) only. Inline editors still get the data preservation.
 */
(function (global) {
  "use strict";

  var RichtextLink = global.RichtextLink;
  if (!RichtextLink) {
    global.console.error(
      "richtext-link: richtext-link-core.js must be loaded first.",
    );
    return;
  }

  // djangocms-text's registry - or its queueing bootstrap stub, which we
  // replicate in case this file loads before any djangocms-text script.
  global.CMS_Editor = global.CMS_Editor || {};
  if (!global.CMS_Editor.tiptap) {
    global.CMS_Editor.tiptap = {
      _bootstrap: true,
      _queue: [],
      register: function () {
        this._queue.push(["register", Array.prototype.slice.call(arguments)]);
      },
      registerToolbarItem: function () {
        this._queue.push([
          "registerToolbarItem",
          Array.prototype.slice.call(arguments),
        ]);
      },
    };
  }
  var registry = global.CMS_Editor.tiptap;

  function dialogOptions(editor) {
    // RTEConfig.configuration ends up in the widget's settings json script
    // (id in the field's data-settings attribute), under options.richtextLink
    var el = editor.options.el || {};
    var script = null;
    if (el.dataset && el.dataset.settings) {
      script = global.document.getElementById(el.dataset.settings);
    }
    if (!script) {
      script = global.document.getElementById("cms-editor-cfg");
    }
    var settings = {};
    if (script) {
      try {
        settings = JSON.parse(script.textContent) || {};
      } catch (e) {
        settings = {};
      }
    }
    var options =
      (settings.options || {}).richtextLink || settings.richtextLink || {};
    return Object.assign({}, RichtextLink.defaults, options);
  }

  var dialog = null;
  var dialogEditor = null; // the editor the open dialog will apply to

  function applyToEditor(editor, json) {
    var value = RichtextLink.attrsFromVerifyData(json);
    var attrs = {
      href: value.href || "",
      target: null,
      // clear djangocms-text's own dynamic link attribute - it would
      // re-resolve the href at render time and override ours
      "data-cms-href": null,
      richtextLink: value.attrs,
    };
    if (editor.state.selection.empty && !editor.isActive("link")) {
      editor
        .chain()
        .focus()
        .insertContent({
          type: "text",
          text: dialogOptions(editor).linkText,
          marks: [{ type: "link", attrs: attrs }],
        })
        .run();
    } else {
      editor
        .chain()
        .focus()
        .extendMarkRange("link")
        .setMark("link", attrs)
        .run();
    }
  }

  function openDialog(editor) {
    var options = dialogOptions(editor);
    if (!options.iframeUrl || !options.verifyUrl) {
      global.console.warn(
        "richtext-link: iframeUrl/verifyUrl not configured - is the " +
          "richtext_link.contrib.djangocms_text RTEConfig active?",
      );
      return;
    }
    if (!dialog) {
      dialog = RichtextLink.createDialog({
        verifyUrl: options.verifyUrl,
        okLabel: options.okLabel,
        cancelLabel: options.cancelLabel,
        errorMessage: options.errorMessage,
        onApply: function (json) {
          if (dialogEditor) {
            applyToEditor(dialogEditor, json);
          }
        },
      });
    }
    dialogEditor = editor;
    if (editor.isActive("link")) {
      editor.chain().extendMarkRange("link").run();
    }
    var linkAttrs = editor.getAttributes("link");
    var data = {};
    if (linkAttrs.richtextLink) {
      data = linkAttrs.richtextLink;
    } else if (linkAttrs.href && options.fallbackField) {
      // plain link (built-in form or pre django-link content):
      // prefill the fallback field
      data[options.fallbackField] = linkAttrs.href;
    }
    dialog.open(RichtextLink.dialogUrl(options.iframeUrl, data));
  }

  function openForAnchor(editor, anchor) {
    var position = editor.view.posAtDOM(anchor, 0);
    if (position == null || position < 0) {
      return;
    }
    editor
      .chain()
      .focus()
      .setTextSelection(position + 1)
      .extendMarkRange("link")
      .run();
    openDialog(editor);
  }

  registry.register("richtextLink", function (api) {
    return api.Extension.create({
      name: "richtextLink",
      // before djangocms-text's link mark, so our click handler wins
      priority: 1000,

      addGlobalAttributes: function () {
        return [
          {
            types: ["link"],
            attributes: {
              richtextLink: {
                default: null,
                parseHTML: function (element) {
                  return RichtextLink.hasMarker(element)
                    ? RichtextLink.parseLinkData(element)
                    : null;
                },
                renderHTML: function (attrs) {
                  if (!attrs.richtextLink) {
                    return {};
                  }
                  var rendered = {};
                  rendered[RichtextLink.MARKER] = RichtextLink.serializeLinkData(
                    attrs.richtextLink,
                  );
                  return rendered;
                },
              },
            },
          },
        ];
      },

      addProseMirrorPlugins: function () {
        var editor = this.editor;
        function handleClick(view, event) {
          var target =
            event.target && event.target.closest
              ? event.target.closest("a")
              : null;
          if (target && view.dom.contains(target)) {
            event.preventDefault();
            global.setTimeout(function () {
              openForAnchor(editor, target);
            }, 0);
            return true;
          }
          return false;
        }
        return [
          new api.pm.Plugin({
            props: {
              handleDOMEvents: {
                click: handleClick,
                dblclick: handleClick,
              },
            },
          }),
        ];
      },
    });
  });

  // the stock toolbar button opens our dialog instead of the built-in form.
  // no `form`/`formAction` keys: nothing may route this item through
  // djangocms-text's openCmsForm.
  registry.registerToolbarItem("Link", {
    action: function (editor) {
      openDialog(editor);
    },
    enabled: function (editor) {
      return "link" in editor.schema.marks;
    },
    active: function (editor) {
      return editor.isActive("link");
    },
    type: "mark",
  });
})(window);
