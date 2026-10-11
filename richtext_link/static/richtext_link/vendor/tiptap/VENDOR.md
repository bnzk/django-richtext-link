# Vendored: TipTap

- Version: **3.31.4** (`@tiptap/core`, `@tiptap/starter-kit`,
  `@tiptap/extension-link`, `@tiptap/pm`)
- License: MIT (überdosis)
- `tiptap-bundle.js` is OUR build of UNMODIFIED TipTap packages: TipTap 3.x
  ships ESM/CJS only (no UMD), so `frontend/` at the repo root bundles the
  public surface into this single IIFE file (`window.RichtextLinkTiptap`),
  via esbuild. See `frontend/tiptap-entry.js` for what is exported.

All of django-richtext-link's own TipTap logic lives readable and unbundled
in `../../js/richtext-link-tiptap.js` - this file contains library code only.

To update:

```
cd frontend
# bump versions in package.json, then:
npm install
npm run build
```

Bump the versions above, test, note it in CHANGELOG.md.
