/*
 * django-quilljs-link: model based links for Quill 2.
 *
 * Registers (via QuilljsLink.register(Quill), or automatically when window.Quill
 * exists at load time):
 *  - a link blot replacing the stock "link" format. Value is polymorphic:
 *    string = plain link (stock behavior), object {href, attrs} = django link
 *    (data-* attributes + data-quilljs-link marker, resolved at render time
 *    by the quilljs_link_add_links template filter).
 *  - a "djangolink" module: toolbar button + dblclick editing, opening the
 *    link model's django admin form in an iframe dialog.
 *
 * Module options: iframeUrl, verifyUrl, fallbackField, linkText, okLabel,
 * cancelLabel, errorMessage, suppressStockTooltip.
 */
(function (global) {
  "use strict";

  var MARKER = "data-quilljs-link";
  // recognized for django-ckeditor-link content, upgraded to MARKER on save
  var LEGACY_MARKER = "data-ckeditor-link";

  function hasMarker(domNode) {
    return domNode.hasAttribute(MARKER) || domNode.hasAttribute(LEGACY_MARKER);
  }

  function parseDataAttributes(domNode) {
    var attrs = {};
    Array.prototype.forEach.call(domNode.attributes, function (attribute) {
      if (
        attribute.name.indexOf("data-") === 0 &&
        attribute.name !== MARKER &&
        attribute.name !== LEGACY_MARKER
      ) {
        attrs[attribute.name.slice("data-".length)] = attribute.value;
      }
    });
    return attrs;
  }

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
        node.removeAttribute(LEGACY_MARKER);
        var attrs = value.attrs || {};
        Object.keys(attrs).forEach(function (key) {
          node.setAttribute("data-" + key, attrs[key]);
        });
        node.setAttribute(MARKER, "true");
      }

      static formats(domNode) {
        if (hasMarker(domNode)) {
          return {
            href: domNode.getAttribute("href") || "",
            attrs: parseDataAttributes(domNode),
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

  function buildDialog(module) {
    var doc = global.document;
    var dialog = doc.createElement("dialog");
    dialog.className = "quilljs-link-dialog";

    var body = doc.createElement("div");
    body.className = "quilljs-link-dialog__body";
    var iframe = doc.createElement("iframe");
    body.appendChild(iframe);

    var message = doc.createElement("div");
    message.className = "quilljs-link-dialog__message";

    var buttons = doc.createElement("div");
    buttons.className = "quilljs-link-dialog__buttons";
    var cancelButton = doc.createElement("button");
    cancelButton.type = "button";
    cancelButton.className = "button";
    cancelButton.textContent = module.options.cancelLabel;
    var okButton = doc.createElement("button");
    okButton.type = "button";
    okButton.className = "button default";
    okButton.textContent = module.options.okLabel;
    buttons.appendChild(cancelButton);
    buttons.appendChild(okButton);

    dialog.appendChild(body);
    dialog.appendChild(message);
    dialog.appendChild(buttons);
    doc.body.appendChild(dialog);

    function getForm() {
      var iframeDocument = null;
      try {
        iframeDocument = iframe.contentDocument;
      } catch (e) {
        return null;
      }
      if (!iframeDocument) {
        return null;
      }
      return (
        iframeDocument.querySelector("#content-main form") ||
        iframeDocument.querySelector("form")
      );
    }

    function renderErrors(form, errors) {
      var iframeDocument = form.ownerDocument;
      Array.prototype.forEach.call(
        form.querySelectorAll("ul.errorlist"),
        function (errorList) {
          errorList.remove();
        },
      );
      Array.prototype.forEach.call(
        form.querySelectorAll(".form-row.errors"),
        function (row) {
          row.classList.remove("errors");
        },
      );
      Object.keys(errors).forEach(function (fieldName) {
        var errorList = iframeDocument.createElement("ul");
        errorList.className = "errorlist";
        (errors[fieldName] || []).forEach(function (errorMessage) {
          var item = iframeDocument.createElement("li");
          item.textContent = errorMessage;
          errorList.appendChild(item);
        });
        var row = form.querySelector(".form-row.field-" + fieldName);
        if (row) {
          row.classList.add("errors");
          row.insertBefore(errorList, row.firstChild);
        } else {
          form.insertBefore(errorList, form.firstChild);
        }
      });
    }

    var api = {
      open: function (src) {
        message.textContent = "";
        iframe.onload = function () {
          var form = getForm();
          if (!form) {
            return;
          }
          form.addEventListener("submit", function (event) {
            // enter in the form triggers ok, form never really submits
            event.preventDefault();
            api.ok();
          });
          var firstInput = form.querySelector(
            "input:not([type=hidden]), select, textarea",
          );
          if (firstInput) {
            firstInput.focus();
          }
          form.ownerDocument.documentElement.scrollTop = 0;
        };
        iframe.src = src;
        dialog.showModal();
      },
      ok: function () {
        var form = getForm();
        if (!form) {
          api.close();
          return;
        }
        global
          .fetch(module.options.verifyUrl, {
            method: "POST",
            body: new FormData(form),
            credentials: "same-origin",
            headers: { "X-Requested-With": "XMLHttpRequest" },
          })
          .then(function (response) {
            return response.json().catch(function () {
              return null;
            });
          })
          .then(function (json) {
            if (!json || typeof json.valid === "undefined") {
              // login html instead of json: probably an expired session
              message.textContent = module.options.errorMessage;
              return;
            }
            if (json.valid !== "true") {
              renderErrors(form, json.errors || {});
              return;
            }
            api.close();
            module.apply(json);
          })
          .catch(function () {
            message.textContent = module.options.errorMessage;
          });
      },
      close: function () {
        dialog.close();
        iframe.src = "about:blank";
      },
    };

    cancelButton.addEventListener("click", function () {
      api.close();
    });
    okButton.addEventListener("click", function () {
      api.ok();
    });
    dialog.addEventListener("cancel", function () {
      // esc key: reset iframe, dialog closes on its own
      iframe.src = "about:blank";
    });

    return api;
  }

  function buildModule(Quill) {
    var DEFAULTS = {
      iframeUrl: "",
      verifyUrl: "",
      fallbackField: "external",
      linkText: "link",
      okLabel: "OK",
      cancelLabel: "Cancel",
      errorMessage:
        "Something went wrong. Maybe your session expired - try reloading the page.",
      suppressStockTooltip: true,
    };

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
          this.dialog = buildDialog(this);
        }
        return this.dialog;
      }

      open(domNode) {
        if (!this.options.iframeUrl || !this.options.verifyUrl) {
          global.console.warn(
            "quilljs-link: iframeUrl/verifyUrl not configured.",
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
        var data = this.parseLinkAttributes(domNode);
        var params = new URLSearchParams(data);
        params.set("_popup", "1");
        var url = this.options.iframeUrl;
        url += (url.indexOf("?") >= 0 ? "&" : "?") + params.toString();
        this.getDialog().open(url);
      }

      parseLinkAttributes(domNode) {
        var data = {};
        if (!domNode) {
          return data;
        }
        data = parseDataAttributes(domNode);
        if (!hasMarker(domNode) && domNode.getAttribute("href")) {
          // plain link (pre django-link content): prefill the fallback field
          if (this.options.fallbackField) {
            data[this.options.fallbackField] = domNode.getAttribute("href");
          }
        }
        return data;
      }

      apply(json) {
        var quill = this.quill;
        var data = json.data || {};
        var attrs = {};
        Object.keys(data).forEach(function (key) {
          var value = data[key];
          // prevent attributes with "null" values
          attrs[key] =
            value === null || value === undefined ? "" : String(value);
        });
        var value = {
          href: json.link_value ? String(json.link_value) : "",
          attrs: attrs,
        };
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

  var QuilljsLink = {
    register: function (Quill) {
      if (Quill.__quilljsLinkRegistered) {
        return;
      }
      Quill.__quilljsLinkRegistered = true;
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
    },
  };

  if (global.Quill) {
    QuilljsLink.register(global.Quill);
  }
  global.QuilljsLink = QuilljsLink;
})(window);
