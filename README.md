# django-richtext-link

[![CI](https://img.shields.io/github/actions/workflow/status/bnzk/django-richtext-link/ci.yml?style=flat-square&logo=github "CI")](https://github.com/bnzk/django-richtext-link/actions/workflows/ci.yml)
[![Version](https://img.shields.io/pypi/v/django-richtext-link.svg?style=flat-square "Version")](https://pypi.python.org/pypi/django-richtext-link/)
[![Licence](https://img.shields.io/github/license/bnzk/django-richtext-link.svg?style=flat-square "Licence")](https://pypi.python.org/pypi/django-richtext-link/)
[![PyPI Downloads](https://img.shields.io/pypi/dm/django-richtext-link.svg?style=flat-square "PyPI Downloads")](https://pypi.python.org/pypi/django-richtext-link/)

Model based linking for rich text editors in Django - **TipTap 3** (default),
**Quill 2**, and bring-your-own **CKEditor 5** - the spiritual successor of
[django-ckeditor-link](https://github.com/bnzk/django-ckeditor-link).

The link dialog is a plain Django admin form: **your link model defines the
fields**, its validation, its widgets. Nothing is ever saved to the link table -
the link data lives as a json payload in a single `data-richtext-link`
attribute on the `<a>` tag (see "Stored format"), and the real `href` is
resolved at render time. Links to objects (fk to a page, a file, whatever)
stay correct when the target moves.

Included:

- a widget (`RichtextWidget`), form field (`RichtextFormField`) and model
  field (`RichtextField`), storing **plain HTML** - TipTap 3.x and Quill 2.x
  are bundled, no further dependencies, the `editor` config key picks one;
  CKEditor 5 is supported bring-your-own (it is GPL/commercially licensed
  and not bundled)
- TipTap extras: per block **classes** on paragraphs/headings
  (`blockClasses`), `enterMode: "br"` (CKEditor ENTER_BR style)
- the django link dialog as editor modules/extensions (vanilla JS, usable
  with your own TipTap or Quill build)
- `DjangoLinkAdmin`, rendering your link model's admin form in an iframe
  dialog, with ajax `verify/` and `search/` endpoints (quick search over all
  fk link targets, based on each target admin's `search_fields`)
- the `richtext_link_add_links` template filter, resolving stored links at
  render time
- optional: abstract link model base (`richtext_link.link_model`)
- optional: a rebuildable link index (`richtext_link.link_index`) - "what
  links here?", link reports, advisory delete protection
- content compatible with django-ckeditor-link and django-quilljs-link:
  legacy `data-ckeditor-link` / `data-quilljs-link` markers are recognized
  everywhere, and upgraded to `data-richtext-link` on the next editor save

## Quickstart

Install:

```bash
pip install django-richtext-link
# lxml + cssselect are needed for the template filter (and the link index):
pip install django-richtext-link[templatetag]
```

Settings:

```python
INSTALLED_APPS = [
    ...
    "richtext_link",
    # optional, the link index ("what links here?"):
    "richtext_link.link_index",
]

RICHTEXT_LINK_MODEL = "my_app.models.LinkModel"

# the link dialog is an iframe:
X_FRAME_OPTIONS = "SAMEORIGIN"
```

Define your link model. It is never saved - it provides the dialog form and
the link resolution. `get_link()` is required, `get_link_target()`,
`get_link_style()` (css class) and `get_link_attrs()` (extra attributes) are
optional:

```python
class LinkModel(models.Model):
    external_url = models.URLField(blank=True, default="")
    page = models.ForeignKey(Page, null=True, blank=True, on_delete=models.CASCADE)

    def get_link(self):
        if self.external_url:
            return self.external_url
        if self.page:
            return self.page.get_absolute_url()
        return ""

    def get_link_target(self):
        return "_blank" if self.external_url else ""
```

Or start from the included abstract base
(`richtext_link.link_model.models.LinkBase`, with free/external/mailto/phone
fields and a `link_type` dispatcher).

Register it with `DjangoLinkAdmin` (this also adds the `verify/` and
`search/` endpoints, no urls.py include needed):

```python
from richtext_link.admin import DjangoLinkAdmin

@admin.register(LinkModel)
class LinkModelAdmin(DjangoLinkAdmin):
    pass  # a custom form/widgets? just set form = ...
```

Use the field on your models:

```python
from richtext_link.fields import RichtextField

class Article(models.Model):
    body = RichtextField(default="", blank=True)
```

The editor's dialog urls are derived from `RICHTEXT_LINK_MODEL`'s admin
automatically. Render the content with resolved links:

```django
{% load richtext_link_tags %}
{{ article.body|richtext_link_add_links|safe }}
```

## Settings

| Setting | Default | Description |
|---|---|---|
| `RICHTEXT_LINK_MODEL` | `None` | Dotted path to your link model class. |
| `RICHTEXT_LINK_CONFIGS` | see below | Editor configs; `RichtextField(config_name="...")` picks one. |
| `RICHTEXT_LINK_ATTR_MODIFIERS` | `{}` | `{field: format_string}` - recombine link data at render time, mostly for MultiWidget fields (e.g. `{"cms_page": "{cms_page_2}"}`). |
| `RICHTEXT_LINK_SANITIZER` | `None` | Dotted path to your html sanitize callable - a startup system check verifies the stored link format survives it (see "Stored format & sanitizers"). |
| `RICHTEXT_LINK_LEGACY_CHECK` | `True` | Checks also verify the legacy link formats survive (content never resaved since django-ckeditor-link / 0.1 / 0.2). Set `False` once no such content is left. |
| `RICHTEXT_LINK_SAVE_GUARD` | `True` | Logs an error (`richtext_link` logger) when a save loses link data the stored value had (see "Stored format & sanitizers"). |
| `RICHTEXT_LINK_INDEX_PROTECT` | `False` | link_index: raise when deleting a link target. |

## Editors

Each config in `RICHTEXT_LINK_CONFIGS` selects its editor via the `editor`
key: `"tiptap"` (the default) or `"quilljs"`. The widget only loads the
assets of the configured editor.

### TipTap (default)

TipTap configs use django-richtext-link's own schema (TipTap itself is
headless and not JSON-configurable):

```python
RICHTEXT_LINK_CONFIGS = {
    "default": {
        "editor": "tiptap",
        "toolbar": [
            ["bold", "italic"],
            ["h2", "h3", "p"],
            ["bulletList", "orderedList"],
            ["djangolink", "clear"],
        ],
        "headingLevels": [2, 3],
        "enterMode": "p",
        "blockClasses": {
            "paragraph": [["", "Default"], ["intro", "Intro"]],
            "heading": [["", "Default"], ["fancy", "Fancy"]],
        },
        # iframeUrl/verifyUrl are auto derived from RICHTEXT_LINK_MODEL's
        # admin when not set; omit the key entirely for no link feature:
        "djangolink": {},
    },
}
```

| key | default | description |
|---|---|---|
| `toolbar` | see above | button groups; items: `bold`, `italic`, `underline`, `strike`, `h1`…`h6`, `p`, `bulletList`, `orderedList`, `blockquote`, `djangolink`, `clear`, `undo`, `redo`, `blockClass` |
| `headingLevels` | `[2, 3]` | allowed heading levels |
| `enterMode` | `"p"` | `"p"`: Enter = new paragraph, Shift+Enter = `<br>`; `"br"`: Enter inserts `<br>` (CKEditor ENTER_BR style; lists/code keep their Enter behavior) |
| `blockClasses` | — | per node type `[value, label]` class choices, shown as a toolbar select; the `class` attribute round-trips through the stored HTML |
| `djangolink` | — | `{iframeUrl, verifyUrl, fallbackField, linkText, okLabel, cancelLabel, errorMessage}` |

`fallbackField` (default `"external"`) is where a plain `<a href>`'s url
lands when editing pre-django-link content; `linkText` (default `"link"`)
is inserted when nothing is selected.

### Quill

Quill configs are passed to `new Quill(el, config)` as is (minus our
`editor` key) - the `djangolink` module options live in `modules`:

```python
RICHTEXT_LINK_CONFIGS = {
    "default": { ... },  # tiptap, as above
    "legacy": {
        "editor": "quilljs",
        "theme": "snow",
        "modules": {
            "toolbar": [
                ["bold", "italic", "underline"],
                [{"list": "ordered"}, {"list": "bullet"}],
                ["djangolink", "clean"],
            ],
            "djangolink": {},
        },
    },
}
```

Note: Quill has no soft line breaks (`<br>`) and no per block classes -
that's why TipTap is the default.

### CKEditor 5 (bring your own)

django-richtext-link is MIT licensed and ships **no CKEditor code**:
CKEditor 5 is GPL-2.0-or-later (or commercially) licensed, and since v44
requires a `licenseKey` - `"GPL"` (the adapter's default, shows a small
"Powered by CKEditor" logo) or your commercial key. Self-host the official
`ckeditor5` npm package's `dist/browser/` files, or serve them via jsdelivr
(below); `cdn.ckeditor.com` is part of CKEditor's cloud plans.

```python
RICHTEXT_LINK_CONFIGS = {
    "default": { ... },  # tiptap, as above
    "ckeditor": {
        "editor": "ckeditor5",
        # optional: the widget loads these for you (absolute url or static
        # path); omit = load a build exposing window.CKEDITOR yourself
        "assets": {
            "js": "https://cdn.jsdelivr.net/npm/ckeditor5@48.3.1/dist/browser/ckeditor5.umd.js",
            "css": "https://cdn.jsdelivr.net/npm/ckeditor5@48.3.1/dist/browser/ckeditor5.css",
        },
        "licenseKey": "GPL",
        # plugin names resolved against window.CKEDITOR; default:
        # ["Essentials", "Paragraph", "Heading", "Bold", "Italic", "List",
        #  "LinkEditing"] - LinkEditing (not "Link") on purpose: no LinkUI
        # balloon interfering with the django link dialog
        # "plugins": [...],
        "enterMode": "p",  # or "br": enter inserts <br>
        "djangolink": {},  # urls auto derived, like tiptap
        "ckeditor": {      # native CKEditor 5 config, passed through as is
            "toolbar": ["heading", "|", "bold", "italic", "|",
                        "bulletedList", "numberedList", "|", "djangolink"],
        },
    },
}
```

Block classes work via CKEditor's native (free) **Style** feature - the
tiptap `blockClasses` equivalent is plain passthrough config: add `"Style"`
and `"GeneralHtmlSupport"` to `plugins`, `"style"` to the toolbar, and e.g.
`"style": {"definitions": [{"name": "Intro", "element": "p", "classes":
["intro"]}]}` to `ckeditor`. Do not `htmlSupport.allow` (or `disallow`)
`data-*` attributes on `a` - the adapter owns the marker attribute, and a
startup system check (`richtext_link.E006`) refuses such configs.

Links are edited via the `djangolink` toolbar button or double click.

## Stored format & sanitizers

A django link is stored as plain HTML with one attribute, the marker, whose
value is the json encoded link data (your link model's field values, sorted
keys, empty fields omitted):

```html
<a data-richtext-link='{"link_type":"page","page":"3"}'>read more</a>
```

The single attribute is the whole contract: whitelisting django links in a
sanitizer or html schema means allowing exactly `a[href, data-richtext-link]`
- e.g. nh3/bleach `attributes={"a": {"href", "data-richtext-link"}}`, or
DOMPurify `ADD_ATTR: ["data-richtext-link"]`.

Read forever, upgraded to the current format on the next editor save:

- `data-richtext-link="true"` plus one `data-<field>` attribute per field
  (django-richtext-link 0.2)
- the same attribute format with the `data-quilljs-link` marker
  (django-quilljs-link 0.1) or the `data-ckeditor-link` marker
  (django-ckeditor-link)

Two rules keep the format safe:

1. **Never assemble the attribute with string formatting** (f-strings in
   templates/migration scripts): a quote in a value breaks out of the
   attribute. Produce content through an editor or lxml, or escape the
   dumped json (`django.utils.html.escape`). From Python,
   `richtext_link.utils.serialize_link_data(data)` gives the canonical
   payload.
2. **Anything rewriting stored content must keep the marker attribute** - a
   sanitizer allowlist missing the exception silently destroys link data on
   the next save. Point `RICHTEXT_LINK_SANITIZER` at your sanitize callable
   and a Django system check round trips a probe link through it at startup:
   `runserver`/`migrate` refuse to start when the payload does not survive
   (`richtext_link.E001-E004`; editor configs are checked too, `E005/E006`).

```python
# settings.py - optional, strongly recommended when you sanitize content
RICHTEXT_LINK_SANITIZER = "myproject.utils.sanitize_richtext"
```

With `RICHTEXT_LINK_LEGACY_CHECK = True` (the default) the sanitizer probe
also covers the legacy formats - content saved before the json format and
never resaved must not lose its link data either. Set it to `False` once no
such content is left (the strict one-attribute allowlist is then enough).

**The editors are sanitizers too** - a strict Quill `formats` whitelist, a
CKEditor plugin setup or your own editor build can strip links the moment
content loads. Three guards cover that side:

- static config analysis at startup (part of the system checks above, e.g. a
  Quill `formats` whitelist without `"link"`)
- every widget verifies at editor init that the loaded content's link data
  survives the editor's parse/serialize round trip (legacy formats load
  upgraded, so only real loss counts) - on loss: a loud console error plus a
  visible warning under the editor, before anything can be saved
- `manage.py richtext_link_editor_check` - the same round trip with probe
  links (current + legacy formats), driven through every configured editor
  in headless firefox, exiting non-zero on loss. Run it in CI or predeploy,
  next to `manage.py check --deploy` (needs selenium + geckodriver;
  bring-your-own CKEditor configs without `assets` are reported as skipped)

**The last safety net** runs at save time, server side: a `pre_save`
comparison logs an error on the `richtext_link` logger whenever a saved
value lost link data the stored value had - specifically a link whose anchor
survived but whose payload vanished, the signature of a stripping sanitizer
or editor (deliberate link removals and dialog edits stay silent). Whatever
save path the other guards never saw - a foreign admin form, an api, a
custom sanitizer - the loss surfaces here. Wire the `richtext_link` logger
to your error reporting; `RICHTEXT_LINK_SAVE_GUARD = False` disables it.

What no check can see: content mangled outside of model saves (raw sql,
`queryset.update()`). The link index below is the tripwire for that -
`rebuild_richtext_link_index` after sanitizer or editor changes, and watch
the link count.

## Quick search in the link dialog

The dialog form gets a search field on top that searches **all foreign key
link targets at once** - every fk field of your link model whose target
model has a `ModelAdmin` with `search_fields`. Results are grouped per
field; picking one fills the fk field (and `link_type`, when your link model
has a matching one). No configuration needed - it appears as soon as there
is something searchable, and stays away otherwise.

On your `DjangoLinkAdmin` subclass: `link_search = False` disables it,
`link_search_limit` (default `10`) caps results per target. Permissions of
the target model admins are respected.

## Nicer link_type forms: django-formfieldstash

For `link_type` dispatcher style link models (like the contrib `LinkBase`),
[django-formfieldstash](https://github.com/bnzk/django-formfieldstash) makes
the dialog show only the field of the selected type. The contrib
`richtext_link.link_model.admin.LinkBaseAdmin` applies it automatically when
installed (and is a plain `DjangoLinkAdmin` when not):

```bash
pip install django-richtext-link[linkmodel]
```

```python
INSTALLED_APPS = [
    ...
    "formfieldstash",  # so its static files are served
]
```

```python
from richtext_link.link_model.admin import LinkBaseAdmin

@admin.register(LinkModel)
class LinkModelAdmin(LinkBaseAdmin):
    pass
```

## Using your own editor build

The Django side does not care where the editor comes from.

**TipTap**: load `richtext_link/js/richtext-link-core.js` and
`richtext_link/js/richtext-link-tiptap.js`, and expose your own
`@tiptap/*` imports as `window.RichtextLinkTiptap = {Editor, Extension,
Mark, Node, mergeAttributes, StarterKit, Link}` (what the vendored bundle
does, see `frontend/tiptap-entry.js`). Then either let
`RichtextLink.tiptap.createEditor(el, config, {content, onUpdate})` build
toolbar and all, or use `RichtextLink.tiptap.buildExtensions(config)` with
your own `Editor` setup.

**CKEditor 5**: anything exposing `window.CKEDITOR` with `ClassicEditor`,
`Plugin`, `ButtonView` and your plugins works (the UMD build does). Load
`richtext-link-core.js` + `richtext-link-ckeditor5.js`, then use
`RichtextLink.ckeditor5.createEditor(el, config, {content, onUpdate})`, or
`buildConfig`/`buildDjangoLinkPlugin` with your own `ClassicEditor.create`.

**Quill**: load `richtext-link-core.js` and `richtext-link-quill.js`, then:

```js
import Quill from "quill";
window.RichtextLink.quill.register(Quill); // link blot + "djangolink" module + icon

new Quill(el, {
  theme: "snow",
  modules: {
    toolbar: [["bold"], ["djangolink"]],
    djangolink: {
      iframeUrl: "/admin/my_app/linkmodel/add/",
      verifyUrl: "/admin/my_app/linkmodel/verify/",
    },
  },
});
```

Sync the editor's html into your form field - or use
`richtext_link/js/widget-init.js` as a reference.

## Link index: what links here?

With `richtext_link.link_index` in `INSTALLED_APPS` (and a `migrate`), an
index of all links in `RichtextField` contents is maintained on every save -
browsable in the admin (read only), queryable in code:

```python
from richtext_link.link_index.index import get_inbound_links, register

get_inbound_links(some_page)  # queryset of LinkIndexEntry targeting some_page
```

- the index is **derived data**: rebuild it anytime with
  `./manage.py rebuild_richtext_link_index` (also needed after `loaddata`,
  fixtures are skipped on purpose, and after `queryset.update()`, which
  bypasses signals)
- models using `RichtextField` are picked up automatically; for plain
  `TextField` + `RichtextWidget` combinations, call
  `register(MyModel, ["my_field"])` (e.g. in `AppConfig.ready`)
- `RICHTEXT_LINK_INDEX_PROTECT = True` raises
  `LinkedObjectProtectedError` when a link target is deleted - advisory
  protection, based on the index

## Migrating from django-quilljs-link 0.1.0

Hard rename, **content needs no migration** - `data-quilljs-link` markers
are read forever and upgraded on the next editor save. In code:

- `pip uninstall django-quilljs-link`, install `django-richtext-link`
- `INSTALLED_APPS`: `quilljs_link*` → `richtext_link*`
- settings: `QUILLJS_LINK_*` → `RICHTEXT_LINK_*`; `QUILLJS_LINK_CONFIGS`
  entries keep working as quill configs when you add `"editor": "quilljs"`
  (the new default editor is TipTap)
- fields/widgets: `QuillField/QuillFormField/QuillWidget` →
  `RichtextField/RichtextFormField/RichtextWidget`
- template filter: `{% load quilljs_link_tags %}` /
  `|quilljs_link_add_links` → `{% load richtext_link_tags %}` /
  `|richtext_link_add_links`
- link index: `./manage.py migrate` creates the new table, then run
  `./manage.py rebuild_richtext_link_index` once; the old
  `quilljs_link_index_linkindexentry` table stays behind - drop it manually
  or leave it

## Migrating from django-ckeditor-link

Content works unchanged: the editors and the template filter recognize
`data-ckeditor-link` markers, links upgrade to `data-richtext-link` on the
next editor save. Rename settings (`CKEDITOR_LINK_MODEL` →
`RICHTEXT_LINK_MODEL` etc.), swap `RichTextField` for `RichtextField`, use
the `richtext_link_add_links` filter, keep `X_FRAME_OPTIONS = "SAMEORIGIN"`.
Plain pre-django-link links: the `fallbackField` option prefills a field of
your choice with the old `href` when such a link is edited.

One heads-up that applies to all generations of this package: the stored
`data-*` attributes are your link model's **field names**. Renaming a link
model field silently orphans that attribute in existing content - migrate
your content when renaming.

## Development / running the test project

```bash
git clone https://github.com/bnzk/django-richtext-link.git
cd django-richtext-link
pip install -r requirements_dev.txt
./manage.py migrate
./manage.py createsuperuser
./manage.py loaddata test_app
./manage.py rebuild_richtext_link_index
./manage.py runserver
```

Then check `/admin/test_app/testmodel/2/change/` (TipTap + Quill + CKEditor
editors, dialog) and `/testmodel/2/` (rendered output). For the CKEditor 5
editor and its Selenium tests, run `richtext_link/tests/get_ckeditor5.sh`
once (downloads the GPL licensed build into a gitignored dir - it is not
part of this package). Tests: `./manage.py test`
(the Selenium editor tests need Firefox + geckodriver and are skipped
otherwise; set `RICHTEXT_LINK_SKIP_SELENIUM=1` to skip them explicitly), or
`tox`.

Vendored editors: Quill 2.x unmodified
(`richtext_link/static/richtext_link/vendor/quill/VENDOR.md`); TipTap 3.x as
our own esbuild bundle of unmodified packages
(`.../vendor/tiptap/VENDOR.md`) - TipTap ships no browser build, rebuild
with `cd frontend && npm ci && npm run build` (maintainers only, hosts
install nothing). django-richtext-link is MIT licensed, bundled Quill is
BSD-3-Clause, bundled TipTap is MIT.
