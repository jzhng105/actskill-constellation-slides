"""Optional local preview of a built Slides deck: stitches project/slides/*.html into one scrollable page.

    python preview_deck.py <root> [slide_id ...]   -> writes <root>/preview.html (all slides, or only those named)

Approximates the Slides renderer closely enough to spot overflow or overlap before publishing;
/_blob/ images will not load locally (they show as alt boxes).
"""
import json, sys
from pathlib import Path

root = Path(sys.argv[1])
deck = json.loads((root / "project" / "deck.json").read_text(encoding="utf-8"))
links = "".join(f'<link rel="stylesheet" href="{f["href"]}">' for f in deck["faces"].values() if f.get("href"))
parts = []
for sid in (sys.argv[2:] or deck["order"]):
    h = (root / "project" / "slides" / f"{sid}.html").read_text(encoding="utf-8")
    h = h.replace('style="', 'style="position:relative;width:1920px;height:1080px;box-sizing:border-box;overflow:hidden;', 1)
    h = h.split("<aside>")[0] + "</section>" if "<aside>" in h else h
    parts.append(f'<div class="f"><div class="s">{h}</div><p>{sid}</p></div>')
page = f"""<!doctype html><meta charset="utf-8"><title>{deck['title']} preview</title>{links}
<style>body{{margin:0;background:#222;font-family:sans-serif}}.f{{width:768px;height:452px;margin:16px auto}}.s{{width:1920px;height:1080px;transform:scale(.4);transform-origin:0 0}}
.f p{{color:#aaa;margin:4px 0 0}}section *{{margin:0;box-sizing:border-box}}section ul{{padding-left:1.2em}}img{{outline:1px dashed #888}}</style>{''.join(parts)}"""
(root / "preview.html").write_text(page, encoding="utf-8")
print(root / "preview.html")
