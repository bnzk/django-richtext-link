#!/bin/sh
# fetch the CKEditor 5 UMD build for the selenium tests.
# CKEditor 5 is GPL-2.0+ (or commercially) licensed and deliberately NOT
# vendored with this MIT package - the download target is gitignored.
set -e
VERSION=48.3.1
DIR="$(dirname "$0")/test_app/static/test_ckeditor5"
mkdir -p "$DIR"
curl -fsSL -o "$DIR/ckeditor5.umd.js" "https://cdn.jsdelivr.net/npm/ckeditor5@$VERSION/dist/browser/ckeditor5.umd.js"
curl -fsSL -o "$DIR/ckeditor5.css" "https://cdn.jsdelivr.net/npm/ckeditor5@$VERSION/dist/browser/ckeditor5.css"
echo "ckeditor5 $VERSION downloaded to $DIR"
