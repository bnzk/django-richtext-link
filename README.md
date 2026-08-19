# django-quilljs-link

[![CI](https://img.shields.io/github/actions/workflow/status/bnzk/django-quilljs-link/ci.yml?style=flat-square&logo=github "CI")](https://github.com/bnzk/django-quilljs-link/actions/workflows/ci.yml)
[![Version](https://img.shields.io/pypi/v/django-quilljs-link.svg?style=flat-square "Version")](https://pypi.python.org/pypi/django-quilljs-link/)
[![Licence](https://img.shields.io/github/license/bnzk/django-quilljs-link.svg?style=flat-square "Licence")](https://pypi.python.org/pypi/django-quilljs-link/)
[![PyPI Downloads](https://img.shields.io/pypi/dm/django-quilljs-link.svg?style=flat-square "PyPI Downloads")](https://pypi.python.org/pypi/django-quilljs-link/)

Model based linking for the [Quill 2](https://quilljs.com) rich text editor in
Django - the spiritual successor of
[django-ckeditor-link](https://github.com/bnzk/django-ckeditor-link).

The link dialog is a plain Django admin form: **your link model defines the
fields**, its validation, its widgets. Nothing is ever saved to the link table -
links are stored as `data-*` attributes on the `<a>` tag, and the real `href`
is resolved at render time. Links to objects (fk to a page, a file, whatever)
stay correct when the target moves.

Included:

- a Quill 2 widget (`QuillWidget`), form field (`QuillFormField`) and model
  field (`QuillField`), storing **plain HTML** - Quill 2.x is bundled, no
  further dependencies
- the `djangolink` Quill module + link blot (vanilla JS, usable with your own
  Quill build)
- `DjangoLinkAdmin`, rendering your link model's admin form in an iframe
  dialog, with an ajax `verify/` endpoint
- the `quilljs_link_add_links` template filter, resolving stored links at
  render time
- optional: abstract link model base (`quilljs_link.link_model`)
- optional: a rebuildable link index (`quilljs_link.link_index`) - "what links
  here?", link reports, advisory delete protection
- content compatible with django-ckeditor-link: legacy `data-ckeditor-link`
  markers are recognized everywhere, and upgraded on the next editor save

## Quickstart

Install:

```bash
pip install django-quilljs-link
# lxml + cssselect are needed for the template filter (and the link index):
pip install django-quilljs-link[templatetag]
```

Settings:

```python
INSTALLED_APPS = [
    ...
    "quilljs_link",
    # optional, the link index ("what links here?"):
    "quilljs_link.link_index",
]

QUILLJS_LINK_MODEL = "my_app.models.LinkModel"

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
(`quilljs_link.link_model.models.LinkBase`, with free/external/mailto/phone
fields and a `link_type` dispatcher).

Register it with `DjangoLinkAdmin` (this also adds the `verify/` endpoint,
no urls.py include needed):

```python
from quilljs_link.admin import DjangoLinkAdmin

@admin.register(LinkModel)
class LinkModelAdmin(DjangoLinkAdmin):
    pass  # a custom form/widgets? just set form = ...
```

Use the field on your models:

```python
from quilljs_link.fields import QuillField

class Article(models.Model):
    body = QuillField(default="", blank=True)
```

The editor's dialog urls are derived from `QUILLJS_LINK_MODEL`'s admin
automatically. Render the content with resolved links:

```django
{% load quilljs_link_tags %}
{{ article.body|quilljs_link_add_links|safe }}
```

## Settings

| Setting | Default | Description |
|---|---|---|
| `QUILLJS_LINK_MODEL` | `None` | Dotted path to your link model class. |
| `QUILLJS_LINK_CONFIGS` | see below | Editor configs, passed to `new Quill(el, config)` as is. |
| `QUILLJS_LINK_ATTR_MODIFIERS` | `{}` | `{field: format_string}` - recombine data attributes at render time, mostly for MultiWidget fields (e.g. `{"cms_page": "{cms_page_2}"}`). |
| `QUILLJS_LINK_INDEX_PROTECT` | `False` | link_index: raise when deleting a link target. |

`QUILLJS_LINK_CONFIGS` mirrors the django-ckeditor `CKEDITOR_CONFIGS` idea -
a dict of named configs, `QuillField(config_name="...")` picks one, `"default"`
is the default:

```python
QUILLJS_LINK_CONFIGS = {
    "default": {
        "theme": "snow",
        "modules": {
            "toolbar": [
                ["bold", "italic", "underline"],
                [{"list": "ordered"}, {"list": "bullet"}],
                ["djangolink", "clean"],
            ],
            # iframeUrl/verifyUrl are auto derived from QUILLJS_LINK_MODEL's
            # admin when not set:
            "djangolink": {},
        },
    },
}
```

`djangolink` module options: `iframeUrl`, `verifyUrl`, `fallbackField`
(default `"external"` - where a plain `<a href>`'s url lands when editing
pre-django-link content), `linkText` (default `"link"` - inserted when
nothing is selected), `okLabel`, `cancelLabel`, `errorMessage`,
`suppressStockTooltip` (default `true`).

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
`quilljs_link.link_model.admin.LinkBaseAdmin` applies it automatically when
installed (and is a plain `DjangoLinkAdmin` when not):

```bash
pip install django-quilljs-link[linkmodel]
```

```python
INSTALLED_APPS = [
    ...
    "formfieldstash",  # so its static files are served
]
```

```python
from quilljs_link.link_model.admin import LinkBaseAdmin

@admin.register(LinkModel)
class LinkModelAdmin(LinkBaseAdmin):
    pass
```

## Using your own Quill build

The Django side does not care where Quill comes from. Load
`quilljs_link/js/quilljs-link.js` (or copy it into your bundle), then:

```js
import Quill from "quill";
window.QuilljsLink.register(Quill); // link blot + "djangolink" module + icon

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

Sync `quill.getSemanticHTML()` into your form field - or use
`quilljs_link/js/widget-init.js` as a reference.

## Link index: what links here?

With `quilljs_link.link_index` in `INSTALLED_APPS` (and a `migrate`), an index
of all links in `QuillField` contents is maintained on every save - browsable
in the admin (read only), queryable in code:

```python
from quilljs_link.link_index.index import get_inbound_links, register

get_inbound_links(some_page)  # queryset of LinkIndexEntry targeting some_page
```

- the index is **derived data**: rebuild it anytime with
  `./manage.py rebuild_quilljs_link_index` (also needed after `loaddata`,
  fixtures are skipped on purpose, and after `queryset.update()`, which
  bypasses signals)
- models using `QuillField` are picked up automatically; for plain
  `TextField` + `QuillWidget` combinations, call
  `register(MyModel, ["my_field"])` (e.g. in `AppConfig.ready`)
- `QUILLJS_LINK_INDEX_PROTECT = True` raises
  `LinkedObjectProtectedError` when a link target is deleted - advisory
  protection, based on the index

## Migrating from django-ckeditor-link

Content works unchanged: the editor and the template filter both recognize
`data-ckeditor-link` markers. Links are upgraded to `data-quilljs-link` the
next time an editor saves them - the filter accepts both, forever.

- rename settings: `CKEDITOR_LINK_MODEL` → `QUILLJS_LINK_MODEL`,
  `CKEDITOR_LINK_ATTR_MODIFIERS` → `QUILLJS_LINK_ATTR_MODIFIERS`
- template filter: `ckeditor_link_add_links` → `quilljs_link_add_links`
- replace `RichTextField` with `QuillField`, drop the `CKEDITOR_CONFIGS`
  wiring (dialog urls are now derived automatically)
- keep `X_FRAME_OPTIONS = "SAMEORIGIN"`
- pre-django-link plain links: the `fallbackField` module option prefills
  a field of your choice with the old `href` when such a link is edited

One heads-up that applies to both packages: the stored `data-*` attributes are
your link model's **field names**. Renaming a link model field silently orphans
that attribute in existing content - migrate your content when renaming.

## Development / running the test project

```bash
git clone https://github.com/bnzk/django-quilljs-link.git
cd django-quilljs-link
pip install -r requirements_dev.txt
./manage.py migrate
./manage.py createsuperuser
./manage.py loaddata test_app
./manage.py rebuild_quilljs_link_index
./manage.py runserver
```

Then check `/admin/test_app/testmodel/2/change/` (editor + dialog) and
`/testmodel/2/` (rendered output). Tests: `./manage.py test` (the Selenium
editor tests need Firefox + geckodriver and are skipped otherwise; set
`QUILLJS_LINK_SKIP_SELENIUM=1` to skip them explicitly), or `tox`.

Quill 2.x is vendored unmodified, see
`quilljs_link/static/quilljs_link/vendor/quill/VENDOR.md`. django-quilljs-link
is MIT licensed, the bundled Quill is BSD-3-Clause.
