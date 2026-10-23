"""Build the interactive three.js constellation presentation.

    python build_threejs.py <model_output_dir> --story story.json --out <folder>/index.html [--theme theme.json]

Writes index.html plus img/ (the theme's logo and each label's SHAP beeswarm) next to it. The page is
an Artifact-ready fragment (no <html>/<head>): publish index.html with the img/ files as supporting
files, or open it locally in a browser. Pass --standalone for a full HTML document to host on a website. Re-run after every story.json edit; it is cheap.
"""
import argparse, html as htmlmod, json, shutil
from pathlib import Path
from common import SKILL, extension_js, load_extensions, load_model_dir, load_theme, merge, rgb

ap = argparse.ArgumentParser()
ap.add_argument("model_dir")
ap.add_argument("--story", required=True)
ap.add_argument("--out", required=True, help="path of the html file to write")
ap.add_argument("--theme", help="theme JSON (default: assets/theme.json)")
ap.add_argument("--standalone", action="store_true", help="write a complete HTML document (doctype, lang, viewport) for self-hosting")
a = ap.parse_args()

story = json.loads(Path(a.story).read_text(encoding="utf-8"))
data = load_model_dir(a.model_dir)
TH = load_theme(a.theme)
D = merge(data, story, TH)
C = TH["colors"]
D["theme"] = {"name": TH["name"], "colors": C}
EXTS = load_extensions()
for x in EXTS:
    if hasattr(x, "extend"):
        x.extend(D, story, Path(a.story))

out = Path(a.out)
img = out.parent / "img"
img.mkdir(parents=True, exist_ok=True)
logo = f"img/logo{TH['logo_file'].suffix.lower()}"
shutil.copyfile(TH["logo_file"], out.parent / logo)
files = {logo: str(out.parent / logo)}
for p in D["products"]:
    if p.get("beeswarm"):
        name = f"beeswarm_{p['key']}.png"
        shutil.copyfile(p["beeswarm"], img / name)
        p["img"] = f"img/{name}"
        files[p["img"]] = str(img / name)
    for k in ("beeswarm", "code_maps"):
        p.pop(k, None)

title = (story.get("title") or "ML Model") + (" Briefing" if D["audience"] == "exec" else " Model Review")
payload = json.dumps(D, separators=(",", ":"), ensure_ascii=False).replace("</", "<\\/")
html = (SKILL / "assets" / "threejs_template.html").read_text(encoding="utf-8")
theme_css = (":root{" + "".join(f"--{v}:{C[k]};" for k, v in (("bg", "bg"), ("panel", "brand"), ("deep", "blue2"), ("secondary", "lblue"), ("accent", "accent"),
             ("text", "white"), ("soft", "soft"), ("mute", "mute"), ("good", "good")))
             + f"--bg-rgb:{rgb(C['bg'])};--panel-rgb:{rgb(C['panel'])};--accent-rgb:{rgb(C['accent'])};--line-rgb:{rgb(C['line'])};"
             + f"--head:'{TH['fonts']['head']}', Arial, Helvetica, sans-serif;--body:'{TH['fonts']['body']}', Arial, Helvetica, sans-serif;}}")
html = (html.replace("__TITLE__", htmlmod.escape(title)).replace("__THEME_CSS__", theme_css).replace("__FONTS_HREF__", htmlmod.escape(TH["fonts"]["href"]))
        .replace("__LOGO_ALT__", htmlmod.escape(TH["logo_alt"])).replace("__LOGO__", logo).replace("__EXT__", extension_js()).replace("__DATA__", payload))
if a.standalone:
    html = ('<!DOCTYPE html>\n<html lang="en">\n' + html.replace('<meta charset="utf-8">', '<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">', 1) + '\n</html>\n')
out.write_text(html, encoding="utf-8")

(out.parent / "artifact_files.json").write_text(json.dumps(files, indent=1), encoding="utf-8")
print(f"wrote {out} ({len(html):,} bytes), audience={D['audience']}, {len(D['products'])} products, fold={D['fold']}, theme={TH['name']}" + (f", extensions={[x.__name__.removeprefix('cs_ext_') for x in EXTS]}" if EXTS else ""))
print(f"supporting files for publishing: {out.parent / 'artifact_files.json'}")
missing_why = [p["short"] for p in D["products"] if D["audience"] == "exec" and not p.get("why")]
if missing_why:
    print(f"note: no 'why' bullets yet for {missing_why} (exec decks read better with them; see references/audience-copy.md)")
if not (story.get("close") or {}).get("next"):
    print("note: story.close.next is empty, so the closing slide has no 'next phase' box")
