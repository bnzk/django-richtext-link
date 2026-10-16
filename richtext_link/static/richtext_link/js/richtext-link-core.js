/*
 * django-richtext-link core: editor agnostic pieces shared by the editor
 * adapters (richtext-link-quill.js, richtext-link-tiptap.js) - marker
 * handling, link data mapping, and the iframe dialog that renders the link
 * model's django admin form and validates it via the verify endpoint.
 */
(function (global) {
  "use strict";

  // what we write: the marker attribute carries the json encoded link data,
  // e.g. data-richtext-link='{"link_type":"page","page":"1"}'. legacy formats
  // (one data-* attribute per field, marker value "true" - and the older
  // marker names below) are read forever and upgraded on the next save.
  var MARKER = "data-richtext-link";
  var LEGACY_MARKERS = ["data-quilljs-link", "data-ckeditor-link"];
  var MARKERS = [MARKER].concat(LEGACY_MARKERS);

  function hasMarker(domNode) {
    return MARKERS.some(function (marker) {
      return domNode.hasAttribute(marker);
    });
  }

  function parseLinkData(domNode) {
    // current format: the marker value is the json encoded link data
    var markerValue = domNode.getAttribute(MARKER);
    if (markerValue && markerValue.charAt(0) === "{") {
      try {
        var parsed = JSON.parse(markerValue);
        if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
          return parsed;
        }
      } catch (e) {
        // fall through to the legacy format (defensive: mangled content)
      }
    }
    // legacy formats (any marker generation): one data-* attribute per field
    var attrs = {};
    Array.prototype.forEach.call(domNode.attributes, function (attribute) {
      if (
        attribute.name.indexOf("data-") === 0 &&
        MARKERS.indexOf(attribute.name) < 0
      ) {
        attrs[attribute.name.slice("data-".length)] = attribute.value;
      }
    });
    return attrs;
  }

  function serializeLinkData(data) {
    // canonical marker payload: sorted keys, empty values omitted - keeps
    // saves deterministic across editors (matches utils.serialize_link_data)
    var sorted = {};
    Object.keys(data || {})
      .sort()
      .forEach(function (key) {
        var value = data[key];
        if (value === null || value === undefined || value === "") {
          return;
        }
        sorted[key] = String(value);
      });
    return JSON.stringify(sorted);
  }

  function prefillData(domNode, fallbackField) {
    if (!domNode) {
      return {};
    }
    var data = parseLinkData(domNode);
    if (!hasMarker(domNode) && domNode.getAttribute("href") && fallbackField) {
      // plain link (pre django-link content): prefill the fallback field
      data[fallbackField] = domNode.getAttribute("href");
    }
    return data;
  }

  function dialogUrl(iframeUrl, data) {
    var params = new URLSearchParams(data);
    params.set("_popup", "1");
    return (
      iframeUrl + (iframeUrl.indexOf("?") >= 0 ? "&" : "?") + params.toString()
    );
  }

  function attrsFromVerifyData(json) {
    var data = json.data || {};
    var attrs = {};
    Object.keys(data).forEach(function (key) {
      var value = data[key];
      if (value === null || value === undefined || value === "") {
        return; // empty fields are left out of the stored payload
      }
      attrs[key] = String(value);
    });
    return {
      href: json.link_value ? String(json.link_value) : "",
      attrs: attrs,
    };
  }

  function collectLinkData(html) {
    // canonical payloads of all marker links in an html string, format aware
    if (!html) {
      return [];
    }
    var doc = new DOMParser().parseFromString(html, "text/html");
    var payloads = [];
    Array.prototype.forEach.call(doc.querySelectorAll("a"), function (a) {
      if (hasMarker(a)) {
        payloads.push(serializeLinkData(parseLinkData(a)));
      }
    });
    return payloads;
  }

  function checkContentRoundTrip(originalHtml, serializedHtml, label) {
    // the editor is a sanitizer too: every link payload of the loaded
    // content must survive its parse/serialize round trip. Legacy formats
    // come back upgraded - payloads are compared canonically, so only real
    // data loss counts. Returns the lost payloads, loudly.
    var expected = collectLinkData(originalHtml);
    if (!expected.length) {
      return [];
    }
    var actual = collectLinkData(serializedHtml);
    var lost = [];
    expected.forEach(function (payload) {
      var found = actual.indexOf(payload);
      if (found < 0) {
        lost.push(payload);
      } else {
        actual.splice(found, 1);
      }
    });
    if (lost.length) {
      global.console.error(
        "richtext-link: " +
          (label || "editor") +
          " LOSES LINK DATA - " +
          lost.length +
          " link payload(s) of the loaded content did not survive the " +
          "editor round trip. Saving would destroy these links. Check " +
          "RICHTEXT_LINK_CONFIGS and your editor build/plugins. Lost: " +
          lost.join(" "),
      );
    }
    return lost;
  }

  var defaults = {
    fallbackField: "external",
    linkText: "link",
    okLabel: "OK",
    cancelLabel: "Cancel",
    errorMessage:
      "Something went wrong. Maybe your session expired - try reloading the page.",
  };

  function createDialog(options) {
    var doc = global.document;
    var dialog = doc.createElement("dialog");
    dialog.className = "richtext-link-dialog";

    var body = doc.createElement("div");
    body.className = "richtext-link-dialog__body";
    var iframe = doc.createElement("iframe");
    body.appendChild(iframe);

    var message = doc.createElement("div");
    message.className = "richtext-link-dialog__message";

    var buttons = doc.createElement("div");
    buttons.className = "richtext-link-dialog__buttons";
    var cancelButton = doc.createElement("button");
    cancelButton.type = "button";
    cancelButton.className = "button";
    cancelButton.textContent = options.cancelLabel || defaults.cancelLabel;
    var okButton = doc.createElement("button");
    okButton.type = "button";
    okButton.className = "button default";
    okButton.textContent = options.okLabel || defaults.okLabel;
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
          .fetch(options.verifyUrl, {
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
              message.textContent =
                options.errorMessage || defaults.errorMessage;
              return;
            }
            if (json.valid !== "true") {
              renderErrors(form, json.errors || {});
              return;
            }
            api.close();
            options.onApply(json);
          })
          .catch(function () {
            message.textContent = options.errorMessage || defaults.errorMessage;
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

  global.RichtextLink = {
    MARKER: MARKER,
    LEGACY_MARKERS: LEGACY_MARKERS,
    MARKERS: MARKERS,
    hasMarker: hasMarker,
    parseLinkData: parseLinkData,
    serializeLinkData: serializeLinkData,
    collectLinkData: collectLinkData,
    checkContentRoundTrip: checkContentRoundTrip,
    prefillData: prefillData,
    dialogUrl: dialogUrl,
    attrsFromVerifyData: attrsFromVerifyData,
    defaults: defaults,
    createDialog: createDialog,
  };
})(window);
