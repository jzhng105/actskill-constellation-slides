"""Write a starter story.json for a model output folder.

    python init_story.py <model_output_dir> --audience exec|analyst --out story.json

Every field is a draft for Claude (or the user) to edit: product names and descriptions come from
assets/known_products.json, families from each product's top SHAP driver, and the "why" bullets
and closing "next" block are left empty because they need a human reading of the beeswarms and
of the project's plans. Prints a short data summary so the author can sanity-check the run.
"""
import argparse, datetime, json
from pathlib import Path
from common import KNOWN, load_model_dir, default_name, family_for

ap = argparse.ArgumentParser()
ap.add_argument("model_dir")
ap.add_argument("--audience", choices=["exec", "analyst"], default="exec")
ap.add_argument("--title", default="ML Model")
ap.add_argument("--out", default="story.json")
a = ap.parse_args()

data = load_model_dir(a.model_dir)
fn = KNOWN["feature_names"]
prods = []
for l in data["labels"]:
    p = data["products"][l]
    nm = default_name(l)
    prods.append({"key": l, **nm, "family": family_for(p.get("share", []), fn), "why": [],
                  "_top_drivers": [f for f, _ in p.get("share", [])[:3]],
                  "_buyers": p.get("oot", {}).get("n_pos", 0)})
fam_size = {}
for p in prods:
    fam_size[p["family"]] = fam_size.get(p["family"], 0) + p["_buyers"]
fam_rank = {f: i for i, f in enumerate(sorted(fam_size, key=lambda f: -fam_size[f]))}
prods.sort(key=lambda p: (fam_rank[p["family"]], -p["_buyers"]))
month = datetime.date.today().strftime("%B %Y")
story = {
    "audience": a.audience,
    "title": a.title,
    "tagline": "Recommending the right product for every customer" if a.audience == "exec"
               else "Ranking quality, the group/customer split and SHAP drivers per product",
    "eyebrow": ("Executive briefing · " if a.audience == "exec" else "Model review · ") + month,
    "intro": "A model that looks at each customer and ranks our products by how likely that customer is to buy them.",
    "brand_tag": "Product recommendation engine",
    "products": [{k: v for k, v in p.items() if k != "_buyers"} for p in prods],
    "families": [{"name": f, **KNOWN["families"].get(f, {"short": f.replace("Driven by ", "").capitalize(), "why": ""})}
                 for f in sorted(fam_size, key=lambda f: fam_rank[f])],
    "feature_names": {},
    "driver_map_rows": 10,
    "close": {"takeaways": None, "next": None},
}
Path(a.out).write_text(json.dumps(story, indent=2, ensure_ascii=False), encoding="utf-8")

m = data["metrics"].get(data["fold"], {})
cb = m.get("catboost", {})
print(f"wrote {a.out}  ({a.audience}, {len(prods)} products, segments {data['segments']}, headline fold '{data['fold']}')")
if data["dropped_segments"]:
    print(f"  segments with no purchases (left off the charts): {data['dropped_segments']}")
print(f"  models in metrics_summary: {sorted(m)}")
if cb:
    print(f"  catboost P@1 {cb.get('p@1')}, R@3 {cb.get('r@3')}, group_share {cb.get('group_share')}")
for p in prods:
    src = data["products"][p["key"]]
    missing = [n for n, ok in (("shap", "share" in src), ("beeswarm", src["beeswarm"]), ("per-label", "oot" in src), ("in-group", "wd" in src)) if not ok]
    print(f"  {p['short']:<14} {p['family']:<30} top: {', '.join(p['_top_drivers'])}" + (f"   MISSING {missing}" if missing else ""))
