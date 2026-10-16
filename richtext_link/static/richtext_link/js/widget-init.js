/*
 * django-richtext-link widget bootstrap: initializes an editor (tiptap or
 * quilljs, per config) for every textarea rendered by
 * richtext_link.widgets.RichtextWidget, syncing the editor's html back into
 * the (hidden) textarea. Handles admin inlines (formset:added).
 */
(function (global) {
  "use strict";

  function quillIsEmpty(quill) {
    return quill.getLength() <= 1 && quill.getText().trim() === "";
  }

  function scheduleRoundTripCheck(
    textarea,
    editorContainer,
    originalHtml,
    getSerialized,
  ) {
    // the editor is a sanitizer too: verify the loaded content's link data
    // survives its round trip, before anything can be saved. The result is
    // marked on the textarea (data-richtext-link-checked), for the
    // richtext_link_editor_check management command.
    global.setTimeout(function () {
      var lost = global.RichtextLink.checkContentRoundTrip(
        originalHtml,
        getSerialized(),
        "the editor for #" + textarea.id,
      );
      if (lost.length) {
        textarea.dataset.richtextLinkChecked = "lost";
        var warning = document.createElement("div");
        warning.className = "richtext-link-check-warning";
        warning.textContent =
          "richtext-link: this editor configuration loses link data (" +
          lost.length +
          " link(s)) - saving would destroy links. Details in the browser " +
          "console.";
        editorContainer.insertAdjacentElement("afterend", warning);
      } else {
        textarea.dataset.richtextLinkChecked = "ok";
      }
    }, 0);
  }

  function initQuill(textarea, editorContainer, config) {
    var Quill = global.Quill;
    if (!Quill || !global.RichtextLink || !global.RichtextLink.quill) {
      global.console.warn(
        "richtext-link: Quill (or the quill adapter) not loaded.",
      );
      return false;
    }
    global.RichtextLink.quill.register(Quill);
    delete config.editor; // ours, not a Quill option
    var initialValue = textarea.value;
    var quill = new Quill(editorContainer, config);
    if (initialValue) {
      quill.setContents(
        quill.clipboard.convert({ html: initialValue }),
        "silent",
      );
    }
    quill.on("text-change", function () {
      // getSemanticHTML, not root.innerHTML: no ql-ui/data-list leakage
      textarea.value = quillIsEmpty(quill) ? "" : quill.getSemanticHTML();
    });
    scheduleRoundTripCheck(
      textarea,
      editorContainer,
      initialValue,
      function () {
        return quillIsEmpty(quill) ? "" : quill.getSemanticHTML();
      },
    );
    return true;
  }

  function initTiptap(textarea, editorContainer, config) {
    if (
      !global.RichtextLinkTiptap ||
      !global.RichtextLink ||
      !global.RichtextLink.tiptap
    ) {
      global.console.warn(
        "richtext-link: tiptap bundle (or the tiptap adapter) not loaded.",
      );
      return false;
    }
    var initialValue = textarea.value;
    var editor = global.RichtextLink.tiptap.createEditor(
      editorContainer,
      config,
      {
        content: initialValue,
        onUpdate: function (editor) {
          textarea.value = editor.isEmpty ? "" : editor.getHTML();
        },
      },
    );
    scheduleRoundTripCheck(
      textarea,
      editorContainer,
      initialValue,
      function () {
        return editor.isEmpty ? "" : editor.getHTML();
      },
    );
    return true;
  }

  function initCkeditor5(textarea, editorContainer, config) {
    if (
      !global.CKEDITOR ||
      !global.RichtextLink ||
      !global.RichtextLink.ckeditor5
    ) {
      global.console.warn(
        "richtext-link: CKEditor 5 (window.CKEDITOR) or the ckeditor5 " +
          "adapter not loaded - load the UMD build yourself or set the " +
          "config 'assets' key.",
      );
      return false;
    }
    var initialValue = textarea.value;
    global.RichtextLink.ckeditor5
      .createEditor(editorContainer, config, {
        content: initialValue,
        onUpdate: function (editor) {
          textarea.value = editor.getData();
        },
      })
      .then(function (editor) {
        scheduleRoundTripCheck(
          textarea,
          editorContainer,
          initialValue,
          function () {
            return editor.getData();
          },
        );
      })
      .catch(function (error) {
        // async failure (bad licenseKey, bad plugin config): surface it and
        // restore the plain textarea so content stays editable
        global.console.error(
          "richtext-link: ckeditor5 failed to initialize.",
          error,
        );
        editorContainer.remove();
        textarea.style.display = "";
        textarea.dataset.richtextLinkChecked = "failed";
        delete textarea.dataset.richtextLinkInitialized;
      });
    return true;
  }

  function initOne(textarea) {
    if (textarea.dataset.richtextLinkInitialized) {
      return;
    }
    if (textarea.closest(".empty-form")) {
      // django admin inline template row
      return;
    }
    var config = {};
    var configScript = document.getElementById(
      textarea.id + "_richtext_config",
    );
    if (configScript) {
      config = JSON.parse(configScript.textContent);
    }

    var editorContainer = document.createElement("div");
    editorContainer.className = "richtext-link-editor";
    textarea.insertAdjacentElement("afterend", editorContainer);

    var initialized;
    var editorKind = config.editor || "tiptap";
    if (editorKind === "quilljs") {
      initialized = initQuill(textarea, editorContainer, config);
    } else if (editorKind === "ckeditor5") {
      initialized = initCkeditor5(textarea, editorContainer, config);
    } else {
      initialized = initTiptap(textarea, editorContainer, config);
    }
    if (!initialized) {
      editorContainer.remove();
      textarea.dataset.richtextLinkChecked = "failed";
      return;
    }
    textarea.style.display = "none";
    textarea.dataset.richtextLinkInitialized = "1";
  }

  function initAll(root) {
    var textareas = root.querySelectorAll(
      "textarea[data-richtext-link-widget]",
    );
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
