# Data contract: what the builders read

Point the scripts at the model output folder (or its parent: a `model_output/` subfolder is found automatically).
The model is assumed to rank a set of **products** (any items or offers, one `lbl_*` label each) for every **customer** (one scored row).
A **segment** is a customer-level category that changes base rates (e.g. channel, plan or region), and a **group** is the unit
whose own history feeds a baseline offset (e.g. store, branch, partner or account manager). Use the user's own words for these in the copy.

Only the first file is required. Each optional file unlocks slides, and a missing one drops those slides quietly, so a partial run still builds.

| File | Needed for | Columns used |
|---|---|---|
| `rate_by_segment_pct.csv` | **required**: the product list, the segment grid and the favourites slide | `segment` plus one `lbl_*` column per product, in percent |
| `metrics_summary.csv` | summary, "vs today", "holds up", group-share slides | `fold`, `model`, `n_rows`, `n_rows_scored`, `p@1`, `r@3`, `ndcg@3`, `mean_candidates`, `mask_violation_pct`, `group_share`, `customer_share`, `within_group_auc_fx` |
| `per_label_metrics_<fold>.csv` | report card, product KPIs, cover star sizes | `label`, `n_eligible`, `n_pos`, `pos_rate_pct`, `auc`, `avg_precision` |
| `per_label_within_group_auc_<fold>.csv` | "within one group" columns | `label`, `within_group_auc`, `n_groups` |
| `shap/shap_mean_abs_<label>.csv` | driver map, families, product constellations | two columns: feature, mean \|SHAP\| (header row ignored) |
| `shap/shap_beeswarm_<label>.png` | analyst beeswarm drawer or slide; the source for exec "more likely when" bullets | image |
| `shap/categorical_code_maps_<label>.json` | reading beeswarm colours for categorical features | `{feature: {code: value}}` |

**Headline fold.** The builders use `oot` (out-of-time) when it exists, else `test`. Every headline number comes from that fold, and the deck says which one it used.

**Model rows in `metrics_summary.csv`** (expected naming). The builders show whichever exist:

| model | Analyst meaning | Exec wording |
|---|---|---|
| `catboost` | served score, sigmoid(group offset + f(x)) | "our model" / the deck title |
| `group_baseline` | sigmoid(offset): the group's history alone | "the group's usual mix" |
| `popularity` | segment uptake rate | "the most popular product for the segment" |
| `catboost_avg_group` | logit(p_global) + f(x): portable to new groups | "our model at an average group" |
| `catboost_residual` | f(x) alone: departure from the group norm, not a preference | analyst only |

**Segments.** Segments in the rate file that are all zero (typically `UNKNOWN`) are left off the charts, and the footnote says so.

**Product order and families.** `init_story.py` assigns each product the curated family of its top SHAP driver (see `family_of_feature` in `assets/known_products.json`). Families are ordered by total purchases. Edit `story.json` to regroup or rename. The map's separators and labels follow the story order.

**Influence %.** Influence is `mean |SHAP| of a feature ÷ sum over all features`, per product. That makes it comparable across products and readable as a share ("customer tenure drives 36% of the Product A recommendation"). Analyst decks also show the raw mean |SHAP|.

## Sanity checks before writing any copy
- Read what `init_story.py` prints: products, segments, models found, top drivers and any MISSING files.
- If a number in the story text disagrees with the CSV, the CSV wins. Copy never states a figure the data does not contain. Fill a missing figure with a bracketed placeholder and tell the user.
