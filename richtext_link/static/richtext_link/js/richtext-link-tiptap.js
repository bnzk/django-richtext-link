/*
 * django-richtext-link TipTap 3 adapter. Needs richtext-link-core.js and the
 * vendored bundle (window.RichtextLinkTiptap) - or your own build exposing
 * the same shape: {Editor, Extension, Mark, Node, mergeAttributes,
 * StarterKit, Link}.
 *
 * Config schema (JSON, from RICHTEXT_LINK_CONFIGS):
 *   editor: "tiptap"
 *   toolbar: [["bold", "italic"], ["h2", "h3", "p"], ...] - see ITEMS below
 *   headingLevels: [2, 3]
 *   enterMode: "p" (default) | "br" (enter inserts <br>)
 *   blockClasses: {"paragraph": [["", "Default"], ["intro", "Intro"]], ...}
 *   djangolink: {iframeUrl, verifyUrl, fallbackField, linkText, okLabel,
 *                cancelLabel, errorMessage} - omit the key = no link feature
 */
(function (global) {
  "use strict";

  var RichtextLink = global.RichtextLink;

  function buildDjangoLink(T) {
    return T.Link.extend({
      addAttributes() {
        var parent = (this.parent ? this.parent() : {}) || {};
        return Object.assign({}, parent, {
          // the template filter owns target/class at render time:
          // suppress for django links, keep author-set values on plain links
          target: Object.assign({}, parent.target, {
            renderHTML: function (attrs) {
              if (attrs.djangoAttrs || !attrs.target) {
                return {};
              }
              return { target: attrs.target };
            },
          }),
          rel: Object.assign({}, parent.rel, {
            renderHTML: function (attrs) {
              if (attrs.djangoAttrs || !attrs.rel) {
                return {};
              }
              return { rel: attrs.rel };
            },
          }),
          djangoAttrs: {
            default: null,
            // reads all markers - legacy content loads fine and is
            // re-rendered with the new marker only (upgrade on save)
            parseHTML: function (element) {
              return RichtextLink.hasMarker(element)
                ? RichtextLink.parseDataAttributes(element)
                : null;
            },
            renderHTML: function (attrs) {
              if (!attrs.djangoAttrs) {
                return {};
              }
              var rendered = {};
              rendered[RichtextLink.MARKER] = "true";
              Object.keys(attrs.djangoAttrs).forEach(function (key) {
                rendered["data-" + key] = attrs.djangoAttrs[key];
              });
              return rendered;
            },
          },
        });
      },
    });
  }

  function buildBlockClass(T, blockClasses) {
    return T.Extension.create({
      name: "richtextLinkBlockClass",
      addGlobalAttributes() {
        return [
          {
            types: Object.keys(blockClasses),
            attributes: {
              class: {
                default: null,
                parseHTML: function (element) {
                  return element.getAttribute("class") || null;
                },
                renderHTML: function (attrs) {
                  return attrs.class ? { class: attrs.class } : {};
                },
              },
            },
          },
        ];
      },
    });
  }

  function buildEnterBr(T) {
    return T.Extension.create({
      name: "richtextLinkEnterBr",
      // beat the built-in enter keymaps
      priority: 1000,
      addKeyboardShortcuts() {
        var editor = this.editor;
        return {
          Enter: function () {
            return editor.commands.first(function (props) {
              return [
                function () {
                  return props.commands.newlineInCode();
                },
                function () {
                  return props.commands.splitListItem("listItem");
                },
                function () {
                  return props.commands.setHardBreak();
                },
              ];
            });
          },
        };
      },
    });
  }

  function buildExtensions(config) {
    var T = global.RichtextLinkTiptap;
    var extensions = [
      T.StarterKit.configure({
        link: false, // replaced by our extended link mark
        heading: { levels: config.headingLevels || [2, 3] },
      }),
      buildDjangoLink(T).configure({
        openOnClick: false,
        // no automatic target/rel - stored html stays clean, the template
        // filter decides at render time
        HTMLAttributes: { target: null, rel: null },
      }),
    ];
    if (config.blockClasses) {
      extensions.push(buildBlockClass(T, config.blockClasses));
    }
    if (config.enterMode === "br") {
      extensions.push(buildEnterBr(T));
    }
    return extensions;
  }

  function DjangoLinkController(editor, options) {
    this.editor = editor;
    this.options = Object.assign(
      { iframeUrl: "", verifyUrl: "" },
      RichtextLink.defaults,
      options || {},
    );
    this.dialog = null;
    var self = this;
    editor.view.dom.addEventListener("dblclick", function (event) {
      var anchor =
        event.target && event.target.closest ? event.target.closest("a") : null;
      if (anchor && editor.view.dom.contains(anchor)) {
        event.preventDefault();
        self.openForAnchor(anchor);
      }
    });
  }

  DjangoLinkController.prototype.getDialog = function () {
    if (!this.dialog) {
      var self = this;
      this.dialog = RichtextLink.createDialog({
        verifyUrl: this.options.verifyUrl,
        okLabel: this.options.okLabel,
        cancelLabel: this.options.cancelLabel,
        errorMessage: this.options.errorMessage,
        onApply: function (json) {
          self.apply(json);
        },
      });
    }
    return this.dialog;
  };

  DjangoLinkController.prototype.openForAnchor = function (anchor) {
    var position = this.editor.view.posAtDOM(anchor, 0) + 1;
    this.editor
      .chain()
      .setTextSelection(position)
      .extendMarkRange("link")
      .run();
    this.open();
  };

  DjangoLinkController.prototype.open = function () {
    if (!this.options.iframeUrl || !this.options.verifyUrl) {
      global.console.warn("richtext-link: iframeUrl/verifyUrl not configured.");
      return;
    }
    var editor = this.editor;
    if (editor.isActive("link")) {
      editor.chain().extendMarkRange("link").run();
    }
    var linkAttrs = editor.getAttributes("link");
    var data = {};
    if (linkAttrs.djangoAttrs) {
      data = linkAttrs.djangoAttrs;
    } else if (linkAttrs.href && this.options.fallbackField) {
      // plain link (pre django-link content): prefill the fallback field
      data[this.options.fallbackField] = linkAttrs.href;
    }
    this.getDialog().open(RichtextLink.dialogUrl(this.options.iframeUrl, data));
  };

  DjangoLinkController.prototype.apply = function (json) {
    var value = RichtextLink.attrsFromVerifyData(json);
    var attrs = {
      href: value.href || "",
      target: null,
      rel: null,
      djangoAttrs: value.attrs,
    };
    var editor = this.editor;
    if (editor.state.selection.empty && !editor.isActive("link")) {
      editor
        .chain()
        .focus()
        .insertContent({
          type: "text",
          text: this.options.linkText,
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
  };

  DjangoLinkController.prototype.removeLink = function () {
    this.editor.chain().focus().extendMarkRange("link").unsetLink().run();
  };

  var linkIcon =
    '<svg viewBox="0 0 18 18" width="15" height="15" fill="none" ' +
    'stroke="currentColor" stroke-width="1.4" aria-hidden="true">' +
    '<line x1="7" x2="11" y1="7" y2="11"></line>' +
    '<path d="M8.9,4.577a3.476,3.476,0,0,1,.36,4.679A3.476,3.476,0,0,1,4.577,8.9C3.185,7.5,2.035,6.4,4.217,4.217S7.5,3.185,8.9,4.577Z"></path>' +
    '<path d="M13.423,9.1a3.476,3.476,0,0,0-4.679-.36,3.476,3.476,0,0,0,.36,4.679c1.392,1.392,2.5,2.542,4.679.36S14.815,10.5,13.423,9.1Z"></path>' +
    '<circle cx="15" cy="3.5" r="2" fill="currentColor" stroke="none"></circle>' +
    "</svg>";

  function headingItem(level) {
    return {
      label: "H" + level,
      title: "Heading " + level,
      run: function (editor) {
        editor.chain().focus().toggleHeading({ level: level }).run();
      },
      active: function (editor) {
        return editor.isActive("heading", { level: level });
      },
    };
  }

  var ITEMS = {
    bold: {
      label: "B",
      title: "Bold",
      run: function (e) {
        e.chain().focus().toggleBold().run();
      },
      active: function (e) {
        return e.isActive("bold");
      },
    },
    italic: {
      label: "I",
      title: "Italic",
      run: function (e) {
        e.chain().focus().toggleItalic().run();
      },
      active: function (e) {
        return e.isActive("italic");
      },
    },
    underline: {
      label: "U",
      title: "Underline",
      run: function (e) {
        e.chain().focus().toggleUnderline().run();
      },
      active: function (e) {
        return e.isActive("underline");
      },
    },
    strike: {
      label: "S",
      title: "Strike",
      run: function (e) {
        e.chain().focus().toggleStrike().run();
      },
      active: function (e) {
        return e.isActive("strike");
      },
    },
    p: {
      label: "¶",
      title: "Paragraph",
      run: function (e) {
        e.chain().focus().setParagraph().run();
      },
      active: function (e) {
        return e.isActive("paragraph");
      },
    },
    h1: headingItem(1),
    h2: headingItem(2),
    h3: headingItem(3),
    h4: headingItem(4),
    h5: headingItem(5),
    h6: headingItem(6),
    bulletList: {
      label: "• –",
      title: "Bullet list",
      run: function (e) {
        e.chain().focus().toggleBulletList().run();
      },
      active: function (e) {
        return e.isActive("bulletList");
      },
    },
    orderedList: {
      label: "1. –",
      title: "Ordered list",
      run: function (e) {
        e.chain().focus().toggleOrderedList().run();
      },
      active: function (e) {
        return e.isActive("orderedList");
      },
    },
    blockquote: {
      label: "❝",
      title: "Blockquote",
      run: function (e) {
        e.chain().focus().toggleBlockquote().run();
      },
      active: function (e) {
        return e.isActive("blockquote");
      },
    },
    djangolink: {
      label: linkIcon,
      html: true,
      title: "Link",
      run: function (e, context) {
        context.controller.open();
      },
      active: function (e) {
        return e.isActive("link");
      },
    },
    clear: {
      label: "✕",
      title: "Clear formatting",
      run: function (e) {
        e.chain().focus().unsetAllMarks().clearNodes().run();
      },
      active: function () {
        return false;
      },
    },
    undo: {
      label: "↺",
      title: "Undo",
      run: function (e) {
        e.chain().focus().undo().run();
      },
      active: function () {
        return false;
      },
    },
    redo: {
      label: "↻",
      title: "Redo",
      run: function (e) {
        e.chain().focus().redo().run();
      },
      active: function () {
        return false;
      },
    },
  };

  function buildBlockClassSelect(editor, blockClasses) {
    var select = document.createElement("select");
    select.className = "richtext-link-blockclass";
    select.setAttribute("data-item", "blockClass");
    select.title = "Block class";
    var types = Object.keys(blockClasses);

    function activeType() {
      for (var index = 0; index < types.length; index++) {
        if (editor.isActive(types[index])) {
          return types[index];
        }
      }
      return null;
    }

    var lastType = null;

    function refresh() {
      if (document.activeElement === select) {
        // never rebuild the options under an open dropdown
        return;
      }
      var type = activeType();
      select.disabled = !type;
      if (!type) {
        lastType = null;
        select.innerHTML = "";
        return;
      }
      if (type !== lastType) {
        select.innerHTML = "";
        (blockClasses[type] || []).forEach(function (choice) {
          var option = document.createElement("option");
          option.value = choice[0];
          option.textContent = choice[1];
          select.appendChild(option);
        });
        lastType = type;
      }
      var current = editor.getAttributes(type).class || "";
      select.value = current;
      if (select.value !== current) {
        // current class not in the configured choices: show it anyway
        var extra = document.createElement("option");
        extra.value = current;
        extra.textContent = current;
        select.appendChild(extra);
        select.value = current;
      }
    }

    select.addEventListener("change", function () {
      var type = activeType();
      if (!type) {
        return;
      }
      var attrs = { class: select.value || null };
      editor.chain().focus().updateAttributes(type, attrs).run();
    });
    editor.on("transaction", refresh);
    editor.on("selectionUpdate", refresh);
    refresh();
    return select;
  }

  function buildToolbar(editor, config, context) {
    var toolbar = document.createElement("div");
    toolbar.className = "richtext-link-toolbar";
    var refreshers = [];
    var groups = config.toolbar || [];
    var hasBlockClassItem = false;

    groups.forEach(function (group) {
      var groupElement = document.createElement("span");
      groupElement.className = "richtext-link-toolbar__group";
      group.forEach(function (name) {
        if (name === "blockClass") {
          hasBlockClassItem = true;
          if (config.blockClasses) {
            groupElement.appendChild(
              buildBlockClassSelect(editor, config.blockClasses),
            );
          }
          return;
        }
        var item = ITEMS[name];
        if (!item) {
          global.console.warn("richtext-link: unknown toolbar item " + name);
          return;
        }
        if (name === "djangolink" && !context.controller) {
          return;
        }
        var button = document.createElement("button");
        button.type = "button";
        button.setAttribute("data-item", name);
        button.title = item.title;
        if (item.html) {
          button.innerHTML = item.label;
        } else {
          button.textContent = item.label;
        }
        button.addEventListener("click", function () {
          item.run(editor, context);
        });
        refreshers.push(function () {
          button.classList.toggle("is-active", item.active(editor));
        });
        groupElement.appendChild(button);
      });
      if (groupElement.children.length) {
        toolbar.appendChild(groupElement);
      }
    });

    if (config.blockClasses && !hasBlockClassItem) {
      var extraGroup = document.createElement("span");
      extraGroup.className = "richtext-link-toolbar__group";
      extraGroup.appendChild(
        buildBlockClassSelect(editor, config.blockClasses),
      );
      toolbar.appendChild(extraGroup);
    }

    function refresh() {
      refreshers.forEach(function (refresher) {
        refresher();
      });
    }
    editor.on("transaction", refresh);
    editor.on("selectionUpdate", refresh);
    refresh();
    return toolbar;
  }

  function createEditor(mountElement, config, options) {
    var T = global.RichtextLinkTiptap;
    mountElement.classList.add("richtext-link-tiptap");
    var contentElement = document.createElement("div");
    contentElement.className = "richtext-link-content";
    var editor = new T.Editor({
      element: contentElement,
      extensions: buildExtensions(config),
      content: options.content || "",
      onUpdate: function (props) {
        options.onUpdate(props.editor);
      },
    });
    var context = {};
    if (config.djangolink) {
      context.controller = new DjangoLinkController(editor, config.djangolink);
    }
    mountElement.appendChild(buildToolbar(editor, config, context));
    mountElement.appendChild(contentElement);
    return editor;
  }

  RichtextLink.tiptap = {
    createEditor: createEditor,
    buildExtensions: buildExtensions,
  };
})(window);
