# Vendored: Quill

- Version: **2.0.3**
- Source: npm package `quill`, `dist/` folder, files unmodified
  (fetched via https://cdn.jsdelivr.net/npm/quill@2.0.3/dist/)
- License: BSD 3-Clause (see notice in the bundled files / LICENSE in this repo)

Files:

- `quill.js` (+ `quill.js.map`, only loaded by browser devtools)
- `quill.min.js` (not referenced by the widget, for hosts that prefer it)
- `quill.snow.css` (includes core styles)

To update: replace the files with the new `dist/` versions
(`curl -O https://cdn.jsdelivr.net/npm/quill@<version>/dist/<file>`),
bump the version above, test, note it in CHANGELOG.md.
