/*
 * django-quilljs-link widget bootstrap: initializes a Quill editor for every
 * textarea rendered by quilljs_link.widgets.QuillWidget, syncing the editor's
 * html back into the (hidden) textarea. Handles admin inlines (formset:added).
 */
(function (global) {
  "use strict";

  function isEmpty(quill) {
    return quill.getLength() <= 1 && quill.getText().trim() === "";
  }

  function initOne(textarea) {
    if (textarea.dataset.quilljsInitialized) {
      return;
    }
    if (textarea.closest(".empty-form")) {
      // django admin inline template row
      return;
    }
    var Quill = global.Quill;
    if (!Quill || !global.QuilljsLink) {
      global.console.warn("quilljs-link: Quill not loaded.");
      return;
    }
    global.QuilljsLink.register(Quill);

    var config = {};
    var configScript = document.getElementById(textarea.id + "_quilljs_config");
    if (configScript) {
      config = JSON.parse(configScript.textContent);
    }

    var editorContainer = document.createElement("div");
    editorContainer.className = "quilljs-link-editor";
    textarea.insertAdjacentElement("afterend", editorContainer);
    textarea.style.display = "none";
    textarea.dataset.quilljsInitialized = "1";

    var quill = new Quill(editorContainer, config);
    if (textarea.value) {
      quill.setContents(
        quill.clipboard.convert({ html: textarea.value }),
        "silent",
      );
    }
    quill.on("text-change", function () {
      // getSemanticHTML, not root.innerHTML: no ql-ui/data-list leakage
      textarea.value = isEmpty(quill) ? "" : quill.getSemanticHTML();
    });
  }

  function initAll(root) {
    var textareas = root.querySelectorAll("textarea[data-quilljs-link-widget]");
    Array.prototype.forEach.call(textareas, initOne);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () {
      initAll(document);
    });
  } else {
    initAll(document);
  }
  // django admin inlines (CustomEvent since django 4.1)
  document.addEventListener("formset:added", function (event) {
    if (event.target && event.target.querySelectorAll) {
      initAll(event.target);
    }
  });
})(window);
