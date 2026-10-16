/*
 * django-richtext-link CKEditor 5 adapter. Needs richtext-link-core.js and a
 * CKEditor 5 UMD build exposing window.CKEDITOR (BRING YOUR OWN: CKEditor 5
 * is GPL-2.0+ or commercially licensed and NOT shipped with this MIT
 * package - self-host the `ckeditor5` npm package's dist/browser files, or
 * point the config "assets" key at them).
 *
 * Config schema (JSON, from RICHTEXT_LINK_CONFIGS):
 *   editor: "ckeditor5"
 *   assets: {js: "<url or static path>", css: "..."} - optional, the widget
 *           loads them for you; omit = load CKEditor 5 yourself
 *   licenseKey: "GPL" (default) | "<your commercial key>"
 *   plugins: ["Essentials", "Paragraph", ...] - names resolved against
 *            window.CKEDITOR; add "Style", "GeneralHtmlSupport" for styles
 *   enterMode: "p" (default) | "br" (enter inserts <br>)
 *   djangolink: {iframeUrl, verifyUrl, fallbackField, linkText, okLabel,
 *                cancelLabel, errorMessage} - omit the key = no link feature
 *   ckeditor: {toolbar, heading, style, htmlSupport, ...} - native CKEditor 5
 *             config, passed through as is (merged last, wins)
 */
(function (global) {
  "use strict";

  var RichtextLink = global.RichtextLink;

  var DEFAULT_PLUGINS = [
    "Essentials",
    "Paragraph",
    "Heading",
    "Bold",
    "Italic",
    "List",
    // LinkEditing only, not the Link glue plugin: no LinkUI = no stock
    // balloon interfering with the django link dialog
    "LinkEditing",
  ];

  var DEFAULT_TOOLBAR = [
    "heading",
    "|",
    "bold",
    "italic",
    "|",
    "bulletedList",
    "numberedList",
    "|",
    "djangolink",
  ];

  // ckeditor's IconView parses this with DOMParser as image/svg+xml, so the
  // xmlns is mandatory; the explicit fill="none" per element keeps the lark
  // theme's `:not([fill]) {fill: currentColor}` from filling the stroke paths
  var linkIcon =
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 18 18" fill="none" stroke="currentColor" stroke-width="1.4">' +
    '<line x1="7" x2="11" y1="7" y2="11" fill="none"></line>' +
    '<path fill="none" d="M8.9,4.577a3.476,3.476,0,0,1,.36,4.679A3.476,3.476,0,0,1,4.577,8.9C3.185,7.5,2.035,6.4,4.217,4.217S7.5,3.185,8.9,4.577Z"></path>' +
    '<path fill="none" d="M13.423,9.1a3.476,3.476,0,0,0-4.679-.36,3.476,3.476,0,0,0,.36,4.679c1.392,1.392,2.5,2.542,4.679.36S14.815,10.5,13.423,9.1Z"></path>' +
    '<circle cx="15" cy="3.5" r="2" fill="currentColor" stroke="none"></circle>' +
    "</svg>";

  // local fallback for CKEDITOR.findAttributeRange
  function findAttributeRangeFallback(position, attributeName, value, model) {
    var start = position;
    while (
      start.nodeBefore &&
      start.nodeBefore.getAttribute &&
      start.nodeBefore.getAttribute(attributeName) === value
    ) {
      start = model.createPositionBefore(start.nodeBefore);
    }
    var end = position;
    while (
      end.nodeAfter &&
      end.nodeAfter.getAttribute &&
      end.nodeAfter.getAttribute(attributeName) === value
    ) {
      end = model.createPositionAfter(end.nodeAfter);
    }
    return model.createRange(start, end);
  }

  function getAttributeRange(CK, position, attributeName, value, model) {
    if (typeof CK.findAttributeRange === "function") {
      return CK.findAttributeRange(position, attributeName, value, model);
    }
    return findAttributeRangeFallback(position, attributeName, value, model);
  }

  function buildDjangoLinkPlugin(CK, djangolinkOptions) {
    var options = Object.assign(
      { iframeUrl: "", verifyUrl: "" },
      RichtextLink.defaults,
      djangolinkOptions || {},
    );

    class DjangoLink extends CK.Plugin {
      static get pluginName() {
        return "DjangoLink";
      }

      init() {
        this.dialog = null;
        this._defineSchema();
        this._defineConverters();
        this._addToolbarButton();
        this._bindDblClick();
      }

      afterInit() {
        this._suppressLinkBalloon();
      }

      _defineSchema() {
        var schema = this.editor.model.schema;
        schema.extend("$text", { allowAttributes: ["linkDjangoAttrs"] });
        schema.setAttributeProperties("linkDjangoAttrs", {
          copyOnEnter: false,
          isFormatting: false,
        });
      }

      _defineConverters() {
        var conversion = this.editor.conversion;

        // upcast: read all marker formats, strip the markers - legacy
        // content is upgraded to the json payload on the next save
        conversion.for("upcast").add(function (dispatcher) {
          dispatcher.on(
            "element:a",
            function (evt, data, conversionApi) {
              var viewItem = data.viewItem;
              var markers = RichtextLink.MARKERS.filter(function (marker) {
                return viewItem.hasAttribute(marker);
              });
              if (!markers.length) {
                return; // plain link: stock handling
              }
              var attrs = null;
              var consumed = markers.slice();
              var markerValue = viewItem.getAttribute(RichtextLink.MARKER);
              if (markerValue && markerValue.charAt(0) === "{") {
                // current format: json payload in the marker attribute
                try {
                  attrs = JSON.parse(markerValue);
                } catch (e) {
                  attrs = null; // defensive: mangled content
                }
              }
              if (!attrs || typeof attrs !== "object") {
                // legacy formats: one data-* attribute per field
                attrs = {};
                for (var key of viewItem.getAttributeKeys()) {
                  if (
                    key.indexOf("data-") === 0 &&
                    RichtextLink.MARKERS.indexOf(key) < 0
                  ) {
                    attrs[key.slice("data-".length)] =
                      viewItem.getAttribute(key);
                    consumed.push(key);
                  }
                }
              }
              conversionApi.consumable.consume(viewItem, {
                attributes: consumed,
              });
              if (!data.modelRange) {
                // marker link without href: convert children ourselves
                Object.assign(
                  data,
                  conversionApi.convertChildren(viewItem, data.modelCursor),
                );
              }
              conversionApi.writer.setAttribute(
                "linkDjangoAttrs",
                attrs,
                data.modelRange,
              );
            },
            { priority: "low" },
          );
        });

        // downcast: write the marker with its json payload; priority 5
        // merges with LinkEditing's <a linkHref> into one element
        conversion.for("downcast").attributeToElement({
          model: "linkDjangoAttrs",
          view: function (value, conversionApi) {
            if (!value) {
              return undefined;
            }
            var attributes = {};
            attributes[RichtextLink.MARKER] =
              RichtextLink.serializeLinkData(value);
            return conversionApi.writer.createAttributeElement(
              "a",
              attributes,
              { priority: 5 },
            );
          },
        });
      }

      _addToolbarButton() {
        var self = this;
        var editor = this.editor;
        editor.ui.componentFactory.add("djangolink", function (locale) {
          var view = new CK.ButtonView(locale);
          view.set({
            label: "Link",
            icon: linkIcon,
            tooltip: true,
            class: "richtext-link-ckeditor5-djangolink",
          });
          var linkCommand = editor.commands.get("link");
          if (linkCommand) {
            view.bind("isEnabled").to(linkCommand, "isEnabled");
            view.bind("isOn").to(linkCommand, "value", function (value) {
              return !!value;
            });
          }
          view.on("execute", function () {
            self.open();
          });
          return view;
        });
      }

      _bindDblClick() {
        var self = this;
        var editor = this.editor;
        editor.ui.on("ready", function () {
          var editable = editor.ui.view.editable
            ? editor.ui.view.editable.element
            : null;
          if (!editable) {
            return;
          }
          editable.addEventListener("dblclick", function (event) {
            var anchor =
              event.target && event.target.closest
                ? event.target.closest("a")
                : null;
            if (anchor && editable.contains(anchor)) {
              event.preventDefault();
              // ckeditor has already placed the selection inside the link
              self.open();
            }
          });
        });
      }

      _suppressLinkBalloon() {
        // only relevant when the host opts into LinkUI ("Link" glue plugin);
        // the default plugin set has no balloon at all
        var editor = this.editor;
        if (
          !editor.plugins.has("LinkUI") ||
          !editor.plugins.has("ContextualBalloon")
        ) {
          return;
        }
        var balloon = editor.plugins.get("ContextualBalloon");
        balloon.on(
          "set:visibleView",
          function (evt) {
            var selection = editor.model.document.selection;
            if (selection.getAttribute("linkDjangoAttrs")) {
              evt.stop();
            }
          },
          { priority: "high" },
        );
      }

      getDialog() {
        if (!this.dialog) {
          var self = this;
          this.dialog = RichtextLink.createDialog({
            verifyUrl: options.verifyUrl,
            okLabel: options.okLabel,
            cancelLabel: options.cancelLabel,
            errorMessage: options.errorMessage,
            onApply: function (json) {
              self.apply(json);
            },
          });
        }
        return this.dialog;
      }

      open() {
        if (!options.iframeUrl || !options.verifyUrl) {
          global.console.warn(
            "richtext-link: iframeUrl/verifyUrl not configured.",
          );
          return;
        }
        var selection = this.editor.model.document.selection;
        var attrs = selection.getAttribute("linkDjangoAttrs");
        var href = selection.getAttribute("linkHref");
        var data = {};
        if (attrs) {
          data = attrs;
        } else if (href && options.fallbackField) {
          // plain link (pre django-link content): prefill the fallback field
          data[options.fallbackField] = href;
        }
        this.getDialog().open(RichtextLink.dialogUrl(options.iframeUrl, data));
      }

      apply(json) {
        var value = RichtextLink.attrsFromVerifyData(json);
        var editor = this.editor;
        var model = editor.model;
        model.change(function (writer) {
          var selection = model.document.selection;
          if (selection.isCollapsed) {
            var position = selection.getFirstPosition();
            var href = selection.getAttribute("linkHref");
            if (href !== undefined) {
              // caret inside an existing link: re-apply over the whole link
              var range = getAttributeRange(
                CK,
                position,
                "linkHref",
                href,
                model,
              );
              writer.setAttribute("linkHref", value.href, range);
              writer.setAttribute("linkDjangoAttrs", value.attrs, range);
              writer.setSelection(range);
            } else {
              // nothing selected: insert linkText carrying the link
              var text = writer.createText(options.linkText, {
                linkHref: value.href,
                linkDjangoAttrs: value.attrs,
              });
              var insertRange = model.insertContent(text, position);
              writer.setSelection(insertRange);
            }
          } else {
            for (var selectedRange of selection.getRanges()) {
              writer.setAttribute("linkHref", value.href, selectedRange);
              writer.setAttribute(
                "linkDjangoAttrs",
                value.attrs,
                selectedRange,
              );
            }
          }
        });
        editor.editing.view.focus();
      }
    }

    return DjangoLink;
  }

  function installEnterBr(editor) {
    editor.editing.view.document.on(
      "enter",
      function (evt, data) {
        if (data.isSoft) {
          return; // shift+enter: stock soft break
        }
        // lists keep their enter behavior, like the tiptap adapter
        var block = editor.model.document.selection.getFirstPosition().parent;
        if (block && String(block.name).indexOf("listItem") >= 0) {
          return;
        }
        editor.execute("shiftEnter");
        editor.editing.view.scrollToTheSelection();
        data.preventDefault();
        evt.stop();
      },
      { priority: "high" },
    );
  }

  function resolvePlugins(CK, config) {
    var names = config.plugins || DEFAULT_PLUGINS;
    var plugins = [];
    names.forEach(function (name) {
      if (CK[name]) {
        plugins.push(CK[name]);
      } else {
        global.console.warn("richtext-link: unknown ckeditor5 plugin " + name);
      }
    });
    if (config.djangolink) {
      plugins.push(buildDjangoLinkPlugin(CK, config.djangolink));
    }
    return plugins;
  }

  function buildConfig(CK, config, content) {
    var editorConfig = Object.assign(
      {
        licenseKey: config.licenseKey || "GPL",
        toolbar: DEFAULT_TOOLBAR,
      },
      config.ckeditor || {},
    );
    editorConfig.plugins = resolvePlugins(CK, config);
    editorConfig.initialData = content || "";
    return editorConfig;
  }

  function createEditor(mountElement, config, options) {
    var CK = global.CKEDITOR;
    mountElement.classList.add("richtext-link-ckeditor5");
    var contentElement = document.createElement("div");
    contentElement.className = "richtext-link-content";
    mountElement.appendChild(contentElement);
    return CK.ClassicEditor.create(
      contentElement,
      buildConfig(CK, config, options.content),
    ).then(function (editor) {
      editor.model.document.on("change:data", function () {
        options.onUpdate(editor);
      });
      if (config.enterMode === "br") {
        installEnterBr(editor);
      }
      return editor;
    });
  }

  RichtextLink.ckeditor5 = {
    createEditor: createEditor,
    buildConfig: buildConfig,
    buildDjangoLinkPlugin: buildDjangoLinkPlugin,
  };
})(window);
