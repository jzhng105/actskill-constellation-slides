---
name: constellation-slides
description: Build constellation-style presentations of machine learning model results (per-product recommendation / ranking models), in the ZNSTARS theme or a client theme. Two outputs share one story file. The default is an interactive three.js fly-through (a themed night sky, one 3D constellation per product, hover values, speaker notes, SHAP beeswarm drawer); the alternative is a static claude.ai Slides deck that exports to PPTX/PDF. Both are generated from a model output folder (rate_by_segment_pct.csv, metrics_summary.csv, per_label_metrics_*.csv, SHAP mean-abs CSVs and beeswarm PNGs), with wording for either executives (plain language) or analysts (metric names, SHAP values). Use this skill whenever the user asks for slides, a deck, a presentation, a briefing, a walkthrough or a "three.js"/"constellation" view of model outputs, uptake rates by segment, ranking metrics (P@1, AUC, lift over baselines) or SHAP drivers per product, for leadership or the modelling team, even if they don't say "constellation" or name the files.
---

# Constellation slides

A presentation of a per-product recommendation model. Every number comes from the model's CSVs; every sentence a person would write lives in an editable `story.json`. The look comes from a theme file: `assets/theme.json` (ZNSTARS: night sky, nebula blue, star gold, Sora + Inter, constellation logo) unless the user supplies a client theme with `--theme`. Don't restyle the template per request; change the theme file instead. Only the content changes with the audience.

```
scripts/init_story.py   model dir -> starter story.json + data summary
scripts/build_threejs.py model dir + story -> index.html + img/   (interactive, default)
scripts/build_deck.py    model dir + story -> Slides project files (PPTX/PDF route)
scripts/check_page.py    syntax-check a built index.html (needs node)
scripts/check_deck.py    check built Slides files against the Slides format
scripts/preview_deck.py  local preview of Slides files
assets/                  theme.json, three.js template, logo, product/feature defaults
examples/                synthetic demo: make_demo_data.py, demo_model_output/, demo_story.json
references/              data-contract.md, audience-copy.md, slides-deck.md
```

Run the scripts with the system Python (standard library only). The paths below use `<skill>` for this folder: when installed as a plugin that is `${CLAUDE_PLUGIN_ROOT}`; as a plain skill, it is the folder this file is in.

## Workflow

### 1. Pin down the inputs
- **Model folder.** Use the one the user names. A repo root containing `model_output/` also works. If several output folders exist (v7, v8, `_offset`…), ask which one.
- **Audience:** `exec` or `analyst`. See `references/audience-copy.md`. If the request doesn't say, ask once, because the two decks differ in almost every sentence.
- **Format.** Default to the three.js page. Use the Slides deck when the user wants PowerPoint/PDF, editable slides, an attachment, or says "Slides artifact". Build both when asked.
- **Theme.** ZNSTARS by default. If the deck is for a client in their own branding, see "Themes" below.
- **Closing story.** Find out what happens next for the project (rollout, next data, decisions needed). Use what the user already said in the conversation, or ask. Never invent it.

### 2. Start the story
Create a working folder: the user's presentation folder if they have one, else the scratchpad.
```bash
python <skill>/scripts/init_story.py <model_dir> --audience exec --title "ML Model" --out <work>/story.json
```
Read the printed summary: products, segments, models present, top drivers per product, and any MISSING files. Missing optional files drop their slides automatically (`references/data-contract.md`); mention which ones to the user.

### 3. Write the words (edit story.json)
- Check product `short`/`long` names and the one-line `desc`. The defaults are generic placeholder definitions; flag them for the user to confirm.
- Review `family` grouping (auto from each product's top SHAP driver) and the family `why` lines.
- Add `feature_names` overrides for any terms the user prefers.
- **Exec decks:** write the 3–4 "More likely to buy when…" bullets per product by reading each beeswarm with its categorical code map. Follow the reading rules in `references/audience-copy.md`. This is the slowest step and the one execs value most, so do it carefully and only state clear patterns.
- Fill `close.next` with the confirmed next-phase story. Leave `close.takeaways` null for data-driven takeaways, unless the user has specific messages.
- Update `eyebrow` (audience · month) and `tagline` if the user gave a framing.

### 4. Build
Three.js page:
```bash
python <skill>/scripts/build_threejs.py <model_dir> --story <work>/story.json --out <work>/<name>/index.html [--theme <theme.json>]
python <skill>/scripts/check_page.py <work>/<name>/index.html
```
It writes `index.html`, an `img/` folder (logo + beeswarms) and `artifact_files.json`, which lists the supporting files for publishing. Re-run after every story edit; it takes seconds.

Slides deck: follow `references/slides-deck.md` (create deck → upload logo/beeswarms → `build_deck.py` → publish).

### 5. Look once, then deliver
- To see the three.js page, serve the folder with `python -m http.server <port> --bind 127.0.0.1` in the background and open `http://127.0.0.1:<port>/<name>/index.html` in the browser pane. The pane shows `file://` pages only as static snapshots.
- The page writes `#sN` into the URL on every slide, which interrupts the browser key tool. Click the "Next slide" button instead, or load `index.html#s12` directly.
- Check one or two slides of each kind (grid, driver map, families, a product, the close) and the console. Fix what is visibly broken, then stop.
- **Publish** as an Artifact (private by default): `file_path` = the `index.html`, `files` = the mapping in `artifact_files.json`, `icon: "slides"`, and a one-sentence `description`. To update a deck published earlier, publish the same file path in the same conversation, or pass its `url` from another one (read it first). Tell the user that others can't open the link until they share it.
- If the user wants files instead (e.g. into `presentation/<name>/`), copy `index.html` and `img/` there. The page also opens locally over a simple HTTP server. For hosting on a website, build with `--standalone` so the page is a complete HTML document.

### 6. Report back
Give the link or location, the audience and fold used, and what the user should verify:
- product descriptions
- the beeswarm-derived bullets (they describe patterns, not causes)
- any slides dropped for missing files
- any placeholder you had to leave

Keep it short.

## Themes (client branding)
`assets/theme.json` holds everything visual: `name`, `logo` (path relative to the theme file), `logo_alt`, eleven `colors`
(`bg` page, `panel` cards, `deep`/`secondary` second-tier bars and nebulae, `accent` highlights and top stars, `text`, `soft`
secondary text, `mute` captions, `good` positive ticks, `border` card edges, `line` hairlines), six `family_colors`, and
`fonts` (`head`, `body`, and one Google Fonts `href` that loads both). Every colour is `#rrggbb`.

For a client: copy `assets/theme.json` next to their logo (light on transparent, about 800×272), change the values, and pass
`--theme <file>` to `build_threejs.py` and `build_deck.py`. Missing keys fall back to ZNSTARS. Keep text readable: the page is
always dark, so `bg` and `panel` must be dark and `text`/`soft` light. Check one slide of each kind after switching themes.

## Extensions
Both builders load optional extensions: `scripts/ext/*.py` (may define `extend(D, story, story_path)` to add data, and
`deck_slides(D, order)` to add Slides-deck slides) and `assets/ext/*.js` (inlined into the 3D page; each pushes
`{init, frame, slides}` onto `window.CS_EXT`). The free edition ships none; the Pro edition uses them for its extra
modules. If extensions are present, the build prints their names; mention any extension slides to the user.

## Demo (synthetic data)
`examples/` has a complete synthetic run for a fictional subscription business (6 products, 3 segments, all folds, beeswarms),
for showing the skill to prospects or testing changes. `python <skill>/examples/make_demo_data.py` regenerates the data, then:
```bash
python <skill>/scripts/build_threejs.py <skill>/examples/demo_model_output --story <skill>/examples/demo_story.json --out <work>/demo/index.html
```
The demo story sets `sample_note`, which the cover shows so nobody mistakes the figures for real ones. Set `sample_note` in any
story built on illustrative data.

## What the deck contains (built automatically from the data)
Cover (products as a constellation) → bottom line → how it works / model design → what sells by segment (3D star grid) → each segment's favourite → model vs. baselines → generalisation across folds → group vs. customer share → report card (sortable) → driver map (features × products) → buyer-signal families (stars regroup) → one slide per product (its top drivers as a constellation, KPIs, signals, bullets or beeswarm) → close (takeaways + next phase). Slides whose inputs are missing are skipped.

## Things that went wrong before (and are handled; keep them handled if you edit the template)
- **Frozen CSS transitions** left panels at 20% opacity in some viewers. Panels get a `.settled` class after 1.3 s that pins the final state; bar animations are pinned the same way.
- **Morph tied to frame rate** never finished on throttled tabs. The family regrouping is a timed tween.
- **Missing charset** showed "Â·" locally. The template starts with `<meta charset="utf-8">`.
- **Label collisions** in static constellations. `build_deck.py` searches star layouts and reserves room for the top star's glow.
- **Hard-coded story.** The closing story and families are data/story driven. A generic placeholder ending reads as filler; the real next-phase plan must come from the user, which is why `close.next` is never invented.
