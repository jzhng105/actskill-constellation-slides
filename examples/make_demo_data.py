"""Write a synthetic model output folder for demos: a fictional subscription business ranking 6 products.

    python make_demo_data.py [out_dir]        (default: demo_model_output/ next to this script)

Every figure is made up but internally consistent, so both builders exercise every slide. Standard
library only; the SHAP beeswarm PNGs are drawn with Pillow when it is installed and skipped otherwise.
"""
import csv, json, math, random, sys
from pathlib import Path

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent / "demo_model_output"
SEGMENTS = ["ONLINE", "APP", "STORE", "UNKNOWN"]

# categorical codes are scaled low->high like numeric values (STORE, PHONE and December are the high codes)
# label -> uptake % by segment (UNKNOWN stays all zero, so the builders drop it), oot per-label metrics, drivers
PRODUCTS = {
    "lbl_premium_plan":     {"rate": [18.4, 24.9, 11.2], "auc": .874, "ap": .512, "wd": .741,
                             "shap": [("avg_order_value", .412, 1), ("tenure_months", .268, 1), ("visits_30d", .201, 1), ("segment", .133, 0),
                                      ("discount_pct", .094, -1), ("age_band", .071, 1), ("email_engagement", .052, 1), ("sale_month", .031, 0)]},
    "lbl_annual_upgrade":   {"rate": [12.1, 9.7, 15.8], "auc": .842, "ap": .401, "wd": .702,
                             "shap": [("tenure_months", .389, 1), ("prior_purchases", .244, 1), ("discount_pct", .197, 1), ("avg_order_value", .118, 1),
                                      ("segment", .102, 0), ("days_since_last_purchase", .077, -1), ("income_band", .049, 1), ("sale_dow", .022, 0)]},
    "lbl_family_bundle":    {"rate": [6.3, 8.8, 14.6], "auc": .813, "ap": .338, "wd": .688,
                             "shap": [("num_products_held", .356, 1), ("age_band", .287, 1), ("segment", .171, 1), ("income_band", .126, 1),
                                      ("tenure_months", .089, 1), ("price", .064, -1), ("region", .047, 0), ("has_email", .021, 1)]},
    "lbl_cloud_storage":    {"rate": [21.7, 27.3, 4.9], "auc": .905, "ap": .588, "wd": .776,
                             "shap": [("visits_30d", .447, 1), ("device_type", .259, 1), ("email_engagement", .183, 1), ("segment", .151, 0),
                                      ("tenure_months", .082, 1), ("days_since_last_purchase", .061, -1), ("age_band", .039, -1), ("sale_month", .018, 0)]},
    "lbl_priority_support": {"rate": [5.2, 3.9, 9.4], "auc": .781, "ap": .246, "wd": .652,
                             "shap": [("support_contacts", .398, 1), ("avg_order_value", .231, 1), ("tenure_months", .164, 1), ("num_products_held", .122, 1),
                                      ("segment", .087, 0), ("age_band", .058, 1), ("visits_30d", .041, 1), ("has_phone", .019, 1)]},
    "lbl_gift_card":        {"rate": [3.1, 1.8, 7.7], "auc": .796, "ap": .207, "wd": .669,
                             "shap": [("sale_month", .421, 1), ("segment", .233, 1), ("prior_purchases", .171, 1), ("avg_order_value", .102, 1),
                                      ("age_band", .074, 1), ("region", .051, 0), ("discount_pct", .043, 1), ("sale_dow", .028, 0)]},
}
CODE_MAPS = {"segment": {"0": "APP", "1": "ONLINE", "2": "STORE"}, "device_type": {"0": "DESKTOP", "1": "TABLET", "2": "PHONE"},
             "region": {"0": "NORTH", "1": "SOUTH", "2": "EAST", "3": "WEST"}}
FOLDS = {  # fold -> (rows, catboost p@1, r@3, ndcg@3, within-group AUC of f(x))
    "train": (1_240_000, .512, .846, .712, .713), "test": (310_000, .497, .838, .703, .694), "oot": (286_000, .481, .829, .694, .671)}
BASELINES = {"group_baseline": .402, "popularity": .318, "catboost_avg_group": .436, "catboost_residual": .291}


def write_csv(path, header, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(header); w.writerows(rows)


def beeswarm(path, label, shap, seed):
    """A SHAP-style beeswarm: one row per feature, x = SHAP value, colour = feature value (blue low, red high)."""
    from PIL import Image, ImageDraw, ImageFont
    rnd = random.Random(seed)
    font_path = next((p for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "C:/Windows/Fonts/arial.ttf",
                                  "/System/Library/Fonts/Supplemental/Arial.ttf") if Path(p).exists()), None)
    font = lambda n: ImageFont.truetype(font_path, n) if font_path else ImageFont.load_default()
    W, H, L, R, T, B = 900, 1100, 250, 60, 70, 150
    im = Image.new("RGB", (W, H), "white"); d = ImageDraw.Draw(im)
    rows = shap[:8]; rh = (H - T - B) / len(rows); xmax = max(v for _, v, _ in rows) * 3.2
    X = lambda v: L + (v + xmax) / (2 * xmax) * (W - L - R)
    col = lambda z: (int(30 + 225 * z), int(136 - 136 * z * .7), int(229 - 148 * z))  # blue -> magenta-red
    d.line([(X(0), T - 10), (X(0), H - B + 10)], fill=(170, 170, 170), width=2)
    for i, (f, v, sign) in enumerate(rows):
        cy = T + rh * (i + .5)
        d.text((L - 16, cy), f, font=font(22), fill=(40, 40, 40), anchor="rm")
        d.line([(L, cy), (W - R, cy)], fill=(235, 235, 235), width=1)
        buckets = {}
        for _ in range(260):
            z = rnd.random()  # feature value, scaled 0..1
            effect = (z - .5) * 2 * (sign if sign else rnd.choice([-1, 1]))
            x = X(effect * v * 2.4 + rnd.gauss(0, v * .35))
            k = round(x / 5); n = buckets.get(k, 0); buckets[k] = n + 1
            y = cy + (n // 2 + 1) * 3.2 * (1 if n % 2 else -1)
            if abs(y - cy) < rh * .42:
                d.ellipse([x - 3.5, y - 3.5, x + 3.5, y + 3.5], fill=col(z))
    for v in (-xmax * .66, 0, xmax * .66):
        d.text((X(v), H - B + 22), f"{v:+.2f}" if v else "0", font=font(18), fill=(90, 90, 90), anchor="mt")
    d.text(((L + W - R) / 2, H - B + 58), "SHAP value (impact on model output)", font=font(22), fill=(40, 40, 40), anchor="mt")
    for k in range(200):  # colour bar
        d.line([(L + 120 + k * 2, H - 50), (L + 120 + k * 2, H - 34)], fill=col(k / 199), width=2)
    d.text((L + 110, H - 42), "Low", font=font(18), fill=(90, 90, 90), anchor="rm")
    d.text((L + 530, H - 42), "High", font=font(18), fill=(90, 90, 90), anchor="lm")
    d.text((L + 320, H - 58), "Feature value", font=font(18), fill=(90, 90, 90), anchor="mb")
    d.text((W / 2, 30), label, font=font(26), fill=(20, 20, 20), anchor="mm")
    im.save(path, optimize=True)


def main():
    (OUT / "shap").mkdir(parents=True, exist_ok=True)
    labels = list(PRODUCTS)
    write_csv(OUT / "rate_by_segment_pct.csv", ["segment", *labels],
              [[s, *[(PRODUCTS[l]["rate"][i] if i < 3 else 0) for l in labels]] for i, s in enumerate(SEGMENTS)])

    rows = []
    for fold, (n, p1, r3, nd, wd) in FOLDS.items():
        scored = round(n * .93)
        rows.append([fold, "catboost", n, scored, p1, r3, nd, 4.6, .8 if fold != "train" else .5, .412, .468, wd])
        if fold == "oot":
            for m, v in BASELINES.items():
                rows.append([fold, m, n, scored, v, round(r3 - (p1 - v) * .9, 3), round(nd - (p1 - v) * .8, 3), "", "", "", "", ""])
    write_csv(OUT / "metrics_summary.csv", ["fold", "model", "n_rows", "n_rows_scored", "p@1", "r@3", "ndcg@3", "mean_candidates",
                                            "mask_violation_pct", "group_share", "customer_share", "within_group_auc_fx"], rows)

    n_oot = FOLDS["oot"][0]
    pl, wdr = [], []
    for i, (l, p) in enumerate(PRODUCTS.items()):
        elig = round(n_oot * (.97 - .06 * i))
        rate = sum(p["rate"]) / 3
        pl.append([l, elig, round(elig * rate / 100), round(rate, 2), p["auc"], p["ap"]])
        wdr.append([l, p["wd"], 214])
        write_csv(OUT / "shap" / f"shap_mean_abs_{l}.csv", ["feature", "mean_abs_shap"], [[f, v] for f, v, _ in p["shap"]])
        maps = {f: CODE_MAPS[f] for f, _, _ in p["shap"] if f in CODE_MAPS}
        (OUT / "shap" / f"categorical_code_maps_{l}.json").write_text(json.dumps(maps, indent=1), encoding="utf-8")
        try:
            beeswarm(OUT / "shap" / f"shap_beeswarm_{l}.png", l, p["shap"], seed=i + 1)
        except ImportError:
            pass
    write_csv(OUT / "per_label_metrics_oot.csv", ["label", "n_eligible", "n_pos", "pos_rate_pct", "auc", "avg_precision"], pl)
    write_csv(OUT / "per_label_within_group_auc_oot.csv", ["label", "within_group_auc", "n_groups"], wdr)
    print(f"wrote demo model output to {OUT}")


if __name__ == "__main__":
    main()
