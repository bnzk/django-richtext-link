# CHANGELOG

## 0.3.0 (unreleased)

- CKEditor 5 adapter, **bring your own build** (CKEditor 5 is GPL/commercial
  and not bundled with this MIT package): `editor: "ckeditor5"` configs with
  an `assets` convenience (widget loads your CKE5 urls), `licenseKey`
  (default "GPL"), native config passthrough (`ckeditor` key), djangolink
  dialog via the shared core, three-marker legacy upgrade, `enterMode: "br"`,
  block classes via CKEditor's native Style feature (passthrough)
- default plugin set uses LinkEditing without LinkUI (no stock balloon);
  balloon suppressed for django links when hosts opt into LinkUI

## 0.2.0 (2026-10-11)

- renamed: django-quilljs-link → **django-richtext-link** (package
  `richtext_link`), hard break - see README "Migrating from
  django-quilljs-link 0.1.0" (settings `RICHTEXT_LINK_*`, filter
  `richtext_link_add_links`, fields `RichtextField`/`RichtextFormField`/
  `RichtextWidget`, command `rebuild_richtext_link_index`, link_index app
  label `richtext_link_index` + regenerated migration)
- **TipTap 3.x editor** added and made the default - vendored as our own
  esbuild bundle (TipTap ships no browser build), rebuilt via `frontend/`
- per-config `editor` key (`"tiptap"` / `"quilljs"`), widget media loads
  only the configured editor's assets
- TipTap: per block **classes** on paragraphs/headings (`blockClasses`
  config + toolbar select), `enterMode: "p" | "br"`, vanilla JS toolbar
- new content marker `data-richtext-link`; `data-quilljs-link` and
  `data-ckeditor-link` are read forever (filter, editors, link index) and
  upgraded on the next editor save
- shared editor agnostic dialog/core extracted
  (`window.RichtextLink` namespace, `richtext-link-core.js`)
- quill configs unchanged otherwise (passthrough to `new Quill()`)

## 0.1.0 (2026-08-19) - as django-quilljs-link

- initial release
- Quill 2.x widget (`QuillWidget`), form field (`QuillFormField`) and model
  field (`QuillField`), storing plain HTML
- model based link dialog: `DjangoLinkAdmin` with `verify/` endpoint, rendered as
  Django admin form in an iframe dialog (ported from django-ckeditor-link)
- render time link resolution via `quilljs_link_add_links` template filter
- reads legacy `data-ckeditor-link` markers (django-ckeditor-link content
  compatible), writes `data-quilljs-link`
- optional `quilljs_link.link_model` contrib: abstract `LinkBase`, plus
  `LinkBaseAdmin` (uses django-formfieldstash when installed: only the
  selected link_type's field is shown)
- quick search in the link dialog: searches all fk link targets at once,
  based on each target admin's `search_fields`
- optional `quilljs_link.link_index` contrib: rebuildable "what links here?" index,
  with `rebuild_quilljs_link_index` management command and advisory delete
  protection (`QUILLJS_LINK_INDEX_PROTECT`)
