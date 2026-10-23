# The static Slides deck (PPTX / PDF export)

Use this route when the user wants something they can download as PowerPoint or PDF, edit slide by slide, email as an attachment, or when they say "slides artifact". It shows the same content as the three.js page, as 1920×1080 slides in the claude.ai **Slides** Artifact type: constellation SVGs in the theme's colours and fonts.

The Slides type's own instructions (returned when the deck is created) are authoritative. Follow them where they differ from this page.

## Steps

1. **Create the deck.** Call the Artifact tool with `action: "quickstart"` and `intent: "slides"`, then publish with the returned Slides `type_url`, a `title` and `auto_open: "after_first_write"`. Keep the returned deck `url`. Read the create result: it says how files are laid out and published.
2. **Upload the images as assets** in one call: `action: "publish"`, `url: <deck>`, `asset: true`, `file_paths: [...]`. Include:
   - the logo: the file named by the theme's `logo` (`<skill>/assets/img/znstars-white.png` for the default theme)
   - for analyst decks, each `shap/shap_beeswarm_<label>.png`

   Exec product slides show signals and bullets instead of beeswarms, so they only need the logo.
3. **Write `assets.json`** from the upload result, using the urls exactly as returned: `{"logo": "/_blob/…", "lbl_product_a": "/_blob/…", …}`.
4. **Build:**
   ```bash
   python <skill>/scripts/build_deck.py <model_dir> --story story.json --root <work>/deck --assets assets.json [--theme <theme.json>]
   ```
   This writes `<work>/deck/project/deck.json` and `project/slides/<id>.html`. Products without SHAP or per-label metrics still get a slide, without those parts.
5. **Check the files:** `python <skill>/scripts/check_deck.py <work>/deck` must report 0 problems (it flags anything the Slides format would drop or clip). Then an **optional local look** before publishing: `python <skill>/scripts/preview_deck.py <work>/deck cover p-product_a driver-map` writes `preview.html`. Serve the folder with `python -m http.server` and open it in the browser pane. The pane only shows `file://` pages as static snapshots, so it needs the server. Preview 2–3 slides at a time; the full deck is heavy to screenshot.
6. **Publish** as the type's instructions say:
   - First call: `url`, `root: <work>/deck`, `file_path: <work>/deck/project/deck.json`, `files: {"project/slides/cover.html": "project/slides/cover.html"}`.
   - Second call: every other slide file in `files`, with one of them as `file_path`.
   After publishing, do not read the deck back or re-render it unless the user asks; the Slides type asks for that.
7. **Revising** later: edit the slide files in `<work>/deck/project/slides/` (or re-run the builder) and publish only the changed files to the same `url`. Send `deck.json` only when the order, title or sections change.

## Format limits the builder already respects
- Inline styles only, from the Slides subset (px lengths, hex colours; no margin, z-index or em).
- No text under 24px. At most 200 elements per slide. Each SVG under 52 KB, with labels as `<p>` over it.
- Footer row pinned at `bottom:64px`, with slide padding `128px 128px 160px`.
- Images only as uploaded `/_blob/…` urls.

If you hand-edit a slide, keep to these limits.
