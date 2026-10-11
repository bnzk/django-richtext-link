/*
 * quick search on top of the link dialog form: searches all foreign key
 * link targets at once (each target admin's search_fields, via the
 * DjangoLinkAdmin search/ endpoint). a picked result fills the fk field,
 * and link_type when the link model has a matching one.
 */
(function () {
  "use strict";

  function debounce(fn, delay) {
    var timeout = null;
    return function () {
      var args = arguments;
      clearTimeout(timeout);
      timeout = setTimeout(function () {
        fn.apply(null, args);
      }, delay);
    };
  }

  function setSelectValue(select, id, text) {
    var value = String(id);
    var option = null;
    for (var i = 0; i < select.options.length; i++) {
      if (select.options[i].value === value) {
        option = select.options[i];
        break;
      }
    }
    if (!option) {
      // autocomplete/raw selects don't render all options
      option = new Option(text, value);
      select.appendChild(option);
    }
    if (
      window.django &&
      window.django.jQuery &&
      select.classList.contains("admin-autocomplete")
    ) {
      // select2 based admin autocomplete field
      window.django.jQuery(select).val(value).trigger("change");
    } else {
      select.value = value;
      select.dispatchEvent(new Event("change", { bubbles: true }));
    }
  }

  function init() {
    var form = document.querySelector("#content-main form");
    if (!form || form.querySelector(".richtext-link-search")) {
      return;
    }

    var container = document.createElement("div");
    container.className = "richtext-link-search";
    var input = document.createElement("input");
    input.type = "text";
    input.placeholder = "Search link targets ...";
    input.setAttribute("autocomplete", "off");
    var results = document.createElement("ul");
    results.className = "richtext-link-search__results";
    container.appendChild(input);
    container.appendChild(results);
    form.insertBefore(container, form.firstChild);

    function clearResults() {
      results.innerHTML = "";
    }

    function pick(fieldName, id, text) {
      var field = document.getElementById("id_" + fieldName);
      if (field) {
        if (field.tagName === "SELECT") {
          setSelectValue(field, id, text);
        } else {
          field.value = id;
          field.dispatchEvent(new Event("change", { bubbles: true }));
        }
      }
      // contrib LinkBase style link_type: select the matching type, if any
      var linkType = document.getElementById("id_link_type");
      if (linkType && linkType.tagName === "SELECT") {
        for (var i = 0; i < linkType.options.length; i++) {
          if (linkType.options[i].value === fieldName) {
            linkType.value = fieldName;
            linkType.dispatchEvent(new Event("change", { bubbles: true }));
            break;
          }
        }
      }
      input.value = text;
      clearResults();
    }

    function render(data) {
      clearResults();
      data.groups.forEach(function (group) {
        var header = document.createElement("li");
        header.className = "richtext-link-search__group";
        header.textContent = group.label;
        results.appendChild(header);
        group.items.forEach(function (item) {
          var element = document.createElement("li");
          element.className = "richtext-link-search__item";
          element.textContent = item.text;
          element.addEventListener("click", function () {
            pick(group.field, item.id, item.text);
          });
          results.appendChild(element);
        });
      });
      if (!data.groups.length && data.term) {
        var empty = document.createElement("li");
        empty.className = "richtext-link-search__empty";
        empty.textContent = "No results";
        results.appendChild(empty);
      }
    }

    var search = debounce(function (term) {
      if (term.length < 2) {
        clearResults();
        return;
      }
      // relative to .../add/ -> .../search/
      fetch("../search/?term=" + encodeURIComponent(term), {
        credentials: "same-origin",
        headers: { "X-Requested-With": "XMLHttpRequest" },
      })
        .then(function (response) {
          return response.json();
        })
        .then(function (data) {
          if (data.term === input.value.trim()) {
            // ignore stale responses
            render(data);
          }
        })
        .catch(function () {
          clearResults();
        });
    }, 250);

    input.addEventListener("input", function () {
      search(input.value.trim());
    });
    input.addEventListener("keydown", function (event) {
      if (event.key === "Escape") {
        clearResults();
      }
      if (event.key === "Enter") {
        // don't submit the form (would trigger the dialog's ok)
        event.preventDefault();
        var first = results.querySelector(".richtext-link-search__item");
        if (first) {
          first.click();
        }
      }
    });
    document.addEventListener("click", function (event) {
      if (!container.contains(event.target)) {
        clearResults();
      }
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
