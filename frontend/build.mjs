import * as esbuild from "esbuild";

await esbuild.build({
    entryPoints: ["tiptap-entry.js"],
    bundle: true,
    minify: true,
    format: "iife",
    globalName: "RichtextLinkTiptap",
    target: ["es2018"],
    outfile:
        "../richtext_link/static/richtext_link/vendor/tiptap/tiptap-bundle.js",
    logLevel: "info",
});
