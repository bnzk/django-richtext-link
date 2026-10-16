/*
 * django-richtext-link Quill 2 adapter. Needs richtext-link-core.js.
 *
 * Registers (via RichtextLink.quill.register(Quill), or automatically when
 * window.Quill exists at load time):
 *  - a link blot replacing the stock "link" format. Value is polymorphic:
 *    string = plain link (stock behavior), object {href, attrs} = django link
 *    (data-* attributes + data-richtext-link marker, resolved at render time
 *    by the richtext_link_add_links template filter).
 *  - a "djangolink" module: toolbar button + dblclick editing, opening the
 *    link model's django admin form in an iframe dialog.
 *
 * Module options: iframeUrl, verifyUrl, fallbackField, linkText, okLabel,
 * cancelLabel, errorMessage, suppressStockTooltip.
 */
(function (global) {
  "use strict";

  var RichtextLink = global.RichtextLink;

  function buildLinkBlot(Quill) {
    var Link = Quill.import("formats/link");

    class DjangoLink extends Link {
      static create(value) {
        if (!value || typeof value === "string") {
          return super.create(value);
        }
        var node = super.create(this.sanitize(value.href || ""));
        DjangoLink.applyDataAttributes(node, value);
        return node;
      }

      static applyDataAttributes(node, value) {
        // target/class are set at render time by the template filter
        node.removeAttribute("target");
        node.removeAttribute("rel");
        RichtextLink.LEGACY_MARKERS.forEach(function (marker) {
          node.removeAttribute(marker);
        });
        node.setAttribute(
          RichtextLink.MARKER,
          RichtextLink.serializeLinkData(value.attrs || {}),
        );
      }

      static formats(domNode) {
        if (RichtextLink.hasMarker(domNode)) {
          return {
            href: domNode.getAttribute("href") || "",
            attrs: RichtextLink.parseLinkData(domNode),
          };
        }
        return super.formats(domNode);
      }

      format(name, value) {
        if (
          name === this.statics.blotName &&
          value &&
          typeof value === "object"
        ) {
          // re-applied on an existing link: refresh href + data attributes
          var node = this.domNode;
          Array.prototype.slice
            .call(node.attributes)
            .forEach(function (attribute) {
              if (attribute.name.indexOf("data-") === 0) {
                node.removeAttribute(attribute.name);
              }
            });
          node.setAttribute("href", this.statics.sanitize(value.href || ""));
          DjangoLink.applyDataAttributes(node, value);
        } else {
          super.format(name, value);
        }
      }
    }

    return DjangoLink;
  }

  function buildModule(Quill) {
    var DEFAULTS = Object.assign(
      {
        iframeUrl: "",
        verifyUrl: "",
        suppressStockTooltip: true,
      },
      RichtextLink.defaults,
    );

    class DjangoLinkModule {
      constructor(quill, options) {
        this.quill = quill;
        this.options = Object.assign({}, DEFAULTS, options || {});
        this.dialog = null;
        this.savedRange = null;

        quill.root.addEventListener("dblclick", (event) => {
          var anchor =
            event.target && event.target.closest
              ? event.target.closest("a")
              : null;
          if (anchor && quill.root.contains(anchor)) {
            event.preventDefault();
            this.open(anchor);
          }
        });

        this.suppressStockTooltip();
      }

      suppressStockTooltip() {
        // the snow theme tooltip previews the link format value, which is an
        // object for django links - suppress it there, keep it for plain links
        var tooltip = this.quill.theme && this.quill.theme.tooltip;
        if (
          !tooltip ||
          !this.options.suppressStockTooltip ||
          typeof tooltip.show !== "function"
        ) {
          return;
        }
        var quill = this.quill;
        var originalShow = tooltip.show.bind(tooltip);
        tooltip.show = function () {
          var range = quill.getSelection();
          if (range) {
            var formats = quill.getFormat(range);
            if (formats.link && typeof formats.link === "object") {
              return;
            }
          }
          return originalShow();
        };
      }

      getDialog() {
        if (!this.dialog) {
          this.dialog = RichtextLink.createDialog({
            verifyUrl: this.options.verifyUrl,
            okLabel: this.options.okLabel,
            cancelLabel: this.options.cancelLabel,
            errorMessage: this.options.errorMessage,
            onApply: (json) => this.apply(json),
          });
        }
        return this.dialog;
      }

      open(domNode) {
        if (!this.options.iframeUrl || !this.options.verifyUrl) {
          global.console.warn(
            "richtext-link: iframeUrl/verifyUrl not configured.",
          );
          return;
        }
        var quill = this.quill;
        var Link = Quill.import("formats/link");
        var range = quill.getSelection(true);
        var blot = null;
        if (domNode) {
          blot = Quill.find(domNode);
        } else {
          var found = quill.scroll.descendant(Link, range.index);
          blot = found[0];
          if (blot) {
            domNode = blot.domNode;
          }
        }
        if (blot) {
          // always expand to the full link, prevents nested/partial links
          range = {
            index: blot.offset(quill.scroll),
            length: blot.length(),
          };
        }
        this.savedRange = range;
        var data = RichtextLink.prefillData(
          domNode,
          this.options.fallbackField,
        );
        this.getDialog().open(
          RichtextLink.dialogUrl(this.options.iframeUrl, data),
        );
      }

      apply(json) {
        var quill = this.quill;
        var value = RichtextLink.attrsFromVerifyData(json);
        var range = this.savedRange || quill.getSelection(true);
        if (range.length === 0) {
          var text = this.options.linkText;
          quill.insertText(range.index, text, { link: value }, "user");
          quill.setSelection(range.index, text.length, "silent");
        } else {
          quill.formatText(range.index, range.length, "link", value, "user");
          quill.setSelection(range.index, range.length, "silent");
        }
        this.savedRange = null;
      }

      removeLink() {
        var range = this.savedRange || this.quill.getSelection(true);
        if (range) {
          this.quill.formatText(
            range.index,
            range.length,
            "link",
            false,
            "user",
          );
        }
      }
    }

    DjangoLinkModule.DEFAULTS = DEFAULTS;
    return DjangoLinkModule;
  }

  var icon =
    '<svg viewBox="0 0 18 18">' +
    '<line class="ql-stroke" x1="7" x2="11" y1="7" y2="11"></line>' +
    '<path class="ql-even ql-stroke" d="M8.9,4.577a3.476,3.476,0,0,1,.36,4.679A3.476,3.476,0,0,1,4.577,8.9C3.185,7.5,2.035,6.4,4.217,4.217S7.5,3.185,8.9,4.577Z"></path>' +
    '<path class="ql-even ql-stroke" d="M13.423,9.1a3.476,3.476,0,0,0-4.679-.36,3.476,3.476,0,0,0,.36,4.679c1.392,1.392,2.5,2.542,4.679.36S14.815,10.5,13.423,9.1Z"></path>' +
    '<circle class="ql-fill" cx="15" cy="3.5" r="2.5"></circle>' +
    "</svg>";

  function register(Quill) {
    if (Quill.__richtextLinkRegistered) {
      return;
    }
    Quill.__richtextLinkRegistered = true;
    Quill.register(buildLinkBlot(Quill), true);
    Quill.register("modules/djangolink", buildModule(Quill), true);
    Quill.import("ui/icons")["djangolink"] = icon;
    // default toolbar handler, present before any toolbar attaches
    var Toolbar = Quill.import("modules/toolbar");
    Toolbar.DEFAULTS.handlers.djangolink = function () {
      var module = this.quill.getModule("djangolink");
      if (module) {
        module.open();
      }
    };
  }

  RichtextLink.quill = { register: register };

  if (global.Quill) {
    register(global.Quill);
  }
})(window);
