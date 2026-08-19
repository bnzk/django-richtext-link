# CHANGELOG

## 0.1.0 (2026-08-19)

- initial release
- Quill 2.x widget (`QuillWidget`), form field (`QuillFormField`) and model field
  (`QuillField`), storing plain HTML
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
