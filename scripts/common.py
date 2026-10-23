"""Shared loader: reads a model output folder and a theme, and merges them with a story.json.

The CSVs supply every number; the story supplies every word a person wrote (names, descriptions,
families, "more likely when" bullets, the closing story). Nothing here invents a figure.
"""
import csv, importlib.util, json, sys
from pathlib import Path

try:  # Windows consoles default to cp1252; keep status prints from crashing on non-ASCII names
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass

SKILL = Path(__file__).resolve().parent.parent
KNOWN = json.loads((SKILL / "assets" / "known_products.json").read_text(encoding="utf-8"))
SEGMENT_ORDER = []  # optional preferred segment order; others follow in file order
DEFAULT_THEME = SKILL / "assets" / "theme.json"
THEME_COLORS = ("bg", "panel", "deep", "secondary", "accent", "text", "soft", "mute", "good", "border", "line")


def load_theme(path=None):
    """Read a theme file; the logo path is resolved against the theme file's folder. Missing keys fall back to the default theme."""
    base = json.loads(DEFAULT_THEME.read_text(encoding="utf-8"))
    path = Path(path) if path else DEFAULT_THEME
    th = json.loads(path.read_text(encoding="utf-8")) if path != DEFAULT_THEME else base
    th = {**base, **th, "colors": {**base["colors"], **th.get("colors", {})}, "fonts": {**base["fonts"], **th.get("fonts", {})}}
    logo = Path(th["logo"])
    th["logo_file"] = logo if logo.is_absolute() else (path.parent / logo).resolve()
    if not th["logo_file"].exists():
        raise SystemExit(f"theme logo not found: {th['logo_file']}")
    bad = [k for k in THEME_COLORS if not str(th["colors"].get(k, "")).startswith("#") or len(th["colors"][k]) != 7]
    if bad:
        raise SystemExit(f"theme colours must be #rrggbb: {bad}")
    return th


def load_extensions():
    """Optional extensions: each scripts/ext/<name>.py is a module that may define
    extend(D, story, story_path)  -> adds data the page or deck needs (both builders call it), and
    deck_slides(D)                -> [(slide_id, after_slide_id, build(api) -> html), ...] for build_deck.py;
    each assets/ext/<name>.js is inlined into the three.js page and may push {init, frame, slides} onto window.CS_EXT.
    The free edition ships none."""
    mods = []
    for f in sorted((SKILL / "scripts" / "ext").glob("*.py")):
        spec = importlib.util.spec_from_file_location(f"cs_ext_{f.stem}", f)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        mods.append(m)
    return mods


def extension_js():
    """The assets/ext/*.js sources, in name order, as <script> blocks (empty when there are none)."""
    return "\n".join(f"<script>\n{f.read_text(encoding='utf-8')}\n</script>" for f in sorted((SKILL / "assets" / "ext").glob("*.js")))


def rgb(hex_):
    """#rrggbb -> 'r,g,b' for rgba() in CSS."""
    return ",".join(str(int(hex_[i:i + 2], 16)) for i in (1, 3, 5))


def _rows(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def load_model_dir(model_dir):
    """Return everything the decks need from the model output folder. Missing optional files -> None."""
    md = Path(model_dir)
    if not (md / "rate_by_segment_pct.csv").exists() and (md / "model_output").is_dir():
        md = md / "model_output"
    need = md / "rate_by_segment_pct.csv"
    if not need.exists():
        raise SystemExit(f"rate_by_segment_pct.csv not found under {model_dir}")

    rate_rows = _rows(need)
    labels = [c for c in rate_rows[0].keys() if c.startswith("lbl_")]
    rate = {r["segment"]: {l: float(r[l]) for l in labels} for r in rate_rows}
    segments = [c for c in SEGMENT_ORDER if c in rate and any(rate[c].values())]
    segments += [c for c in rate if c not in segments and any(rate[c].values())]
    dropped = [c for c in rate if c not in segments]

    metrics = {}
    if (md / "metrics_summary.csv").exists():
        for r in _rows(md / "metrics_summary.csv"):
            metrics.setdefault(r["fold"], {})[r["model"]] = {
                k: _num(v) for k, v in r.items() if k not in ("fold", "model") and _num(v) is not None}
    folds = [f for f in ("train", "test", "oot") if f in metrics] + [f for f in metrics if f not in ("train", "test", "oot")]
    fold = "oot" if "oot" in metrics else ("test" if "test" in metrics else (folds[-1] if folds else None))

    def per_label(name):
        p = md / name
        return {r["label"]: r for r in _rows(p)} if p.exists() else {}

    pl = per_label(f"per_label_metrics_{fold}.csv") if fold else {}
    wd = per_label(f"per_label_within_group_auc_{fold}.csv") if fold else {}

    shap_dir = md / "shap"
    products = {}
    for l in labels:
        p = {"key": l, "rate": {c: rate[c][l] for c in segments}}
        f = shap_dir / f"shap_mean_abs_{l}.csv"
        if f.exists():
            with open(f, newline="", encoding="utf-8-sig") as fh:
                rr = [(a, float(b)) for a, b in list(csv.reader(fh))[1:] if a]
            tot = sum(v for _, v in rr) or 1.0
            rr = sorted((t for t in rr if t[1] > 0), key=lambda t: -t[1])
            p["raw"] = [[a, round(v, 5)] for a, v in rr]
            p["share"] = [[a, round(v / tot, 5)] for a, v in rr]
        bee = shap_dir / f"shap_beeswarm_{l}.png"
        p["beeswarm"] = str(bee) if bee.exists() else None
        cm = shap_dir / f"categorical_code_maps_{l}.json"
        p["code_maps"] = str(cm) if cm.exists() else None
        if l in pl:
            r = pl[l]
            p["oot"] = {"n_eligible": int(float(r["n_eligible"])), "n_pos": int(float(r["n_pos"])),
                        "pos_rate": float(r["pos_rate_pct"]), "auc": float(r["auc"]),
                        "ap": _num(r.get("avg_precision"))}
        if l in wd:
            p["wd"] = {"auc": float(wd[l]["within_group_auc"]), "n_groups": int(float(wd[l]["n_groups"]))}
        products[l] = p
    return {"model_dir": str(md), "labels": labels, "segments": segments, "dropped_segments": dropped,
            "metrics": metrics, "folds": folds, "fold": fold, "products": products}


def default_name(label):
    k = KNOWN["products"].get(label)
    if k:
        return dict(k)
    nice = label.replace("lbl_", "").replace("_", " ").title()
    return {"short": nice, "long": nice, "desc": ""}


def family_for(share, feature_names):
    """Family = the curated family of the product's top driver; falls back to the next driver, then to the driver's own name."""
    fam_of = KNOWN["family_of_feature"]
    for f, _ in share[:2]:
        if f in fam_of:
            return fam_of[f]
    top = share[0][0] if share else "other"
    return f"Driven by {feature_names.get(top, top).lower()}"


def merge(data, story, theme=None):
    """Combine loaded data, story and theme into the dict the templates read (D in the page)."""
    theme = theme or load_theme()
    fam_colors = theme["family_colors"]
    fn = {**KNOWN["feature_names"], **story.get("feature_names", {})}
    fam_meta = {f["name"]: f for f in story.get("families", [])}
    prods = []
    for sp in story["products"]:
        p = data["products"].get(sp["key"])
        if p is None:
            raise SystemExit(f"story lists {sp['key']} but the model output has no such label")
        prods.append({**p, **{k: sp.get(k) for k in ("short", "long", "desc", "family", "why")}})
    fam_order = []
    for p in prods:
        if p["family"] not in fam_order:
            fam_order.append(p["family"])
    families = []
    for i, name in enumerate(fam_order):
        m = fam_meta.get(name, {})
        known = KNOWN["families"].get(name, {})
        families.append({"name": name, "short": m.get("short") or known.get("short") or name.replace("Driven by ", "").capitalize(),
                         "why": m.get("why") or known.get("why") or "", "color": m.get("color") or fam_colors[i % len(fam_colors)]})
    # driver map rows: highest average share, making sure every product's #1 driver is present
    avg = {}
    for p in prods:
        for f, v in p.get("share", []):
            avg[f] = avg.get(f, 0) + v / len(prods)
    n_rows = int(story.get("driver_map_rows", 10))
    atlas = [f for f, _ in sorted(avg.items(), key=lambda t: -t[1])[:n_rows]]
    tops = [p["share"][0][0] for p in prods if p.get("share")]
    for t in tops:
        if t not in atlas:
            for j in range(len(atlas) - 1, -1, -1):
                if atlas[j] not in tops:
                    atlas[j] = t
                    break
    return {
        "audience": story.get("audience", "exec"),
        "story": {k: story.get(k) for k in ("title", "tagline", "eyebrow", "intro", "brand_tag", "close", "sample_note")},
        "products": prods, "families": families, "featureNames": fn, "atlas": atlas,
        "segments": [[c, KNOWN["segment_names"].get(c, c.title())] for c in data["segments"]],
        "droppedSegments": data["dropped_segments"],
        "metrics": data["metrics"], "fold": data["fold"], "folds": data["folds"],
    }
