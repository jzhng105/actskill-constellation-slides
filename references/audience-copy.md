# Writing for the audience

The look comes from the theme (ZNSTARS by default) and never changes with the audience. What changes is the words.
The templates already switch every built-in label on `story.audience`. Your job is the parts only a person can write, all in `story.json`.

## The two audiences

**exec** (C-suite, leadership, sales leaders, "plain language", "no jargon", "for the board")
- Name things by what a business reader recognises: "how often our #1 suggestion was bought", not "P@1"; "model score out of 100", not "AUC"; "share of influence", not "mean |SHAP|"; "newer customers the model never saw", not "out-of-time fold".
- Lead with the decision-relevant comparison: our model vs. the group's usual mix vs. the most popular product.
- Round in prose (78%, +9 pts). Tables and KPIs keep one decimal where it matters.
- Technical terms live only in speaker notes, as "if asked" answers.
- Feature names come from `feature_names` (Customer tenure, Price paid, Recent activity…). Honour the user's own terms: if they renamed one, put it in `story.feature_names`.

**analyst** (data science, model review, "walk through the metrics/SHAP", "for the modelling team")
- Use the metric and column names: P@1, R@3, NDCG@3, AUC, AP, within-group AUC, `tenure_months`, mean |SHAP|.
- Keep three decimals on metrics. Show all model variants, the fold table, group/customer variance shares and the beeswarm per label.
- Point out the risks: generalisation drops, weak within-group labels, mask violations.

If the request does not say who the audience is, ask once. The two decks differ a lot, and guessing wrong wastes the user's time.

## story.json fields you write

```json
{
  "audience": "exec",
  "title": "ML Model",
  "tagline": "Recommending the right product for every customer",
  "eyebrow": "Executive briefing · October 2026",
  "intro": "One sentence on what the model does.",
  "brand_tag": "Product recommendation engine",
  "products": [{"key": "lbl_product_a", "short": "Product A", "long": "Product A", "desc": "…", "family": "Driven by the customer", "why": ["…"]}],
  "families": [{"name": "Driven by the customer", "short": "The customer", "why": "Who the customer is and how long they have been with us…"}],
  "feature_names": {"tenure_months": "Customer tenure"},
  "driver_map_rows": 10,
  "close": {
    "takeaways": null,
    "next": {"eyebrow": "Next phase", "title": "…", "text": "…"},
    "notes": "speaker notes for the closing slide"
  }
}
```

- `products` order is deck order. Keep products of a family together.
- `desc`: one plain sentence. The defaults are generic placeholder definitions, so tell the user to check them against their own product terms.
- `close.takeaways`: leave it `null` to auto-generate four data-driven takeaways, or give `[["title", "sentence"], …]` (max 4) when the user has a story to tell.
- `close.next`: the "what happens next" box. It is project knowledge, so never invent it. Use what the user said in this conversation, or ask. For example: *"Roll the model into the team's dashboard and pilot it with a small group of users, then compare their results with a control group before a wider launch."* Re-use a story like that only when the user confirms it still holds.

## "More likely to buy when…" bullets (exec decks)

These are the most valuable exec content and the easiest to get wrong. Write 3–4 per product from the beeswarm PNG:

1. Open `shap/shap_beeswarm_<label>.png` and `shap/categorical_code_maps_<label>.json` together.
2. A beeswarm row is a feature. Dots right of zero raise the product's score. Colour runs from blue (low value) to red (high value), and grey means missing.
3. For **numeric** features, read the colour at the right-hand tail: red on the right means "higher X → more likely".
4. For **categorical** features, colour is the integer code scaled from low to high. Map codes through the JSON: blue is code 0, red is the highest code. With `segment {0: ONLINE, 1: PHONE, 2: STORE}`, red on the right means STORE raises it, and purple on the right means PHONE. With `is_new_customer {0: NO, 1: YES}`, blue on the right means existing customers. When there are many codes (region, product line, postcode), say "varies by region" or leave it out. Don't guess.
5. Only state patterns that are clear and large. A grey-vs-colour split usually means "data recorded vs. missing". Treat it as a data-quality artefact: phrase it carefully or leave it out.
6. Phrase from the customer's side, in plain words: "They have been a customer for longer (the strongest signal)", "They spend more per order", "They bought recently", "They come through the store rather than online", "They already hold a related product".
7. The slide already notes that these are patterns, not causes. Don't add certainty the chart doesn't show.

Example (Product A, illustrative): longer tenure → strongest; higher spend per order; more recent activity; store rather than online.

## Words to avoid in exec copy
SHAP, log-odds, logit, AUC, AP, P@k, R@k, NDCG, fold, OOT, residual, offset, covariance, variance share, mask, label, positive class, f(x), feature, CatBoost.
Use instead: driver analysis, score, accuracy, newer customers, group habits, customer & context details, signal, product.
