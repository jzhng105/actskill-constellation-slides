"""Build the static constellation deck for the claude.ai "Slides" Artifact type (exports to PPTX/PDF).

    python build_deck.py <model_output_dir> --story story.json --root <folder> [--assets assets.json] [--theme theme.json]

Writes <root>/project/deck.json and <root>/project/slides/<id>.html in the Slides slide format
(1920x1080 sections, inline styles only). Images in that format must be uploaded assets, so pass
--assets with {"logo": "/_blob/..", "lbl_product_a": "/_blob/..", ...} from the asset-upload step;
anything missing is simply left out. See references/slides-deck.md for the publishing calls.
"""
import argparse, datetime, json, math, random
from pathlib import Path
from common import load_model_dir, load_theme, merge

ap = argparse.ArgumentParser()
ap.add_argument("model_dir")
ap.add_argument("--story", required=True)
ap.add_argument("--root", required=True)
ap.add_argument("--assets", help="JSON map: 'logo' and label keys -> uploaded /_blob/ urls")
ap.add_argument("--theme", help="theme JSON (default: assets/theme.json)")
a = ap.parse_args()

# ---------- palette & type from the theme ----------
TH = load_theme(a.theme)
_c = TH["colors"]
DEEP, BRAND, BLUE2, LBLUE, ACCENT = _c["bg"], _c["panel"], _c["deep"], _c["secondary"], _c["accent"]
WHITE, SOFT, MUTE, GOOD, BORDER = _c["text"], _c["soft"], _c["mute"], _c["good"], _c["border"]
HEAD = f"'{TH['fonts']['head']}', Arial, sans-serif"
BODY = f"'{TH['fonts']['body']}', Arial, sans-serif"
BG_A = f"radial-gradient(ellipse at 80% 15%, {BRAND} 0%, {DEEP} 62%)"
BG_B = f"radial-gradient(ellipse at 15% 85%, {BRAND} 0%, {DEEP} 60%)"

story = json.loads(Path(a.story).read_text(encoding="utf-8"))
D = merge(load_model_dir(a.model_dir), story, TH)
ASSETS = json.loads(Path(a.assets).read_text(encoding="utf-8")) if a.assets else {}
EX = D["audience"] != "analyst"
P, M, FOLD, SEG, FN, ST = D["products"], D["metrics"], D["fold"], D["segments"], D["featureNames"], D["story"]
MF = M.get(FOLD, {})
cb, gb, pp, avg, res = (MF.get(k) for k in ("catboost", "group_baseline", "popularity", "catboost_avg_group", "catboost_residual"))
FAM = {f["name"]: f for f in D["families"]}
t = lambda ex, an: ex if EX else an
esc = lambda s: str(s or "").replace("&", "&amp;").replace("<", "&lt;")
fname = lambda f: esc(FN.get(f, f)) if EX else esc(f)
pc = lambda v: f"{v * 100:.1f}%"
pc0 = lambda v: f"{round(v * 100)}%"
grade = lambda auc: "Excellent" if auc >= .9 else "Strong" if auc >= .8 else "Good" if auc >= .7 else "Fair"
FOLDN = {"train": t("Customers it learned from", "Train"), "test": t("Held-back customers", "Test"), "oot": t("Newer customers", "Out-of-time")}
FOLDS = [f for f in D["folds"] if M.get(f, {}).get("catboost")]
has_pl = all(p.get("oot") for p in P)
has_wd = all(p.get("wd") for p in P)
has_shap = all(p.get("share") for p in P)

# ---------- building blocks ----------
def starfield(seed, n=150, w=1920, h=1080):
    rnd = random.Random(seed)
    c = "".join(f'<circle cx="{rnd.uniform(0, w):.0f}" cy="{rnd.uniform(0, h):.0f}" r="{rnd.choice([.7, .9, 1.1, 1.4, 1.8, 2.3])}" fill="{rnd.choice([WHITE, WHITE, WHITE, SOFT, ACCENT])}" fill-opacity="{rnd.uniform(.18, .75):.2f}"/>' for _ in range(n))
    return f'<svg aria-label="Starfield" width="{w}" height="{h}" viewBox="0 0 {w} {h}" style="position:absolute;left:0px;top:0px;width:{w}px;height:{h}px">{c}</svg>'

def logo():
    return (f'<img src="{ASSETS["logo"]}" alt="{esc(TH["logo_alt"])}" style="position:absolute;right:88px;top:28px;width:188px;height:64px;object-fit:contain">'
            if ASSETS.get("logo") else "")

def section(sid, body, bg=BG_A, notes="", stars=True, extra=""):
    st = f"background:{bg};color:{WHITE};font-family:{BODY};padding:128px 128px 160px;display:flex;flex-direction:column;gap:40px;{extra}"
    return (f'<section id="{sid}" data-transition="fade" style="{st}">\n{starfield(sid) if stars else ""}\n{logo()}\n{body}\n'
            + (f"<aside>{esc(notes)[:3900]}</aside>\n" if notes else "") + "</section>\n")

def footer(left, sid, color=MUTE):
    n = ORDER.index(sid) + 1
    return (f'<p style="position:absolute;left:128px;bottom:64px;width:1400px;font-size:24px;color:{color};line-height:1.3">{left}</p>'
            f'<p style="position:absolute;right:128px;bottom:64px;width:200px;font-size:24px;color:{color};text-align:right;line-height:1.3">{n} / {len(ORDER)}</p>')

def h2(x, color=WHITE):
    return f'<h2 style="font-family:{HEAD};font-size:64px;font-weight:700;line-height:1.1;color:{color}">{x}</h2>'

def eyebrow(x, color=ACCENT):
    return f'<p style="font-family:{HEAD};font-size:24px;font-weight:700;letter-spacing:4px;text-transform:uppercase;color:{color};line-height:1.4">{x}</p>'

def card(inner, flex="1", pad=40):
    return f'<div style="flex:{flex};display:flex;flex-direction:column;gap:16px;padding:{pad}px;border:1px solid {BORDER};border-radius:16px;background:{BRAND}">{inner}</div>'

def big(x, color=ACCENT, size=96):
    return f'<p style="font-family:{HEAD};font-size:{size}px;font-weight:700;line-height:1;color:{color}">{x}</p>'

def para(x, size=32, color=SOFT):
    return f'<p style="font-size:{size}px;line-height:1.4;color:{color}">{x}</p>'

# ---------- constellation layout (collision-free labels) ----------
def seg_hits_rect(p, q, r, pad=4):
    for i in range(41):
        k = i / 40; x, y = p[0] + (q[0] - p[0]) * k, p[1] + (q[1] - p[1]) * k
        if r[0] - pad <= x <= r[2] + pad and r[1] - pad <= y <= r[3] + pad:
            return True
    return False

def place_labels(pts, radii, edges, sizes, W, H, x0=0, y0=0):
    placed = []
    for i, ((x, y), r, (w, h)) in enumerate(zip(pts, radii, sizes)):
        cands = [("right", (x + r + 14, y - h / 2, x + r + 14 + w, y + h / 2)), ("left", (x - r - 14 - w, y - h / 2, x - r - 14, y + h / 2)),
                 ("below", (x - w / 2, y + r + 10, x + w / 2, y + r + 10 + h)), ("above", (x - w / 2, y - r - 10 - h, x + w / 2, y - r - 10))]
        best = None
        for k, (side, rc) in enumerate(cands):
            pen = k * .1 + (100 if rc[0] < x0 or rc[1] < y0 or rc[2] > W or rc[3] > H else 0)
            pen += 10 * sum(seg_hits_rect(pts[u], pts[v], rc) for u, v in edges)
            pen += 20 * sum(math.hypot(pc_[0] - min(max(pc_[0], rc[0]), rc[2]), pc_[1] - min(max(pc_[1], rc[1]), rc[3])) < pr + 6
                            for j, (pc_, pr) in enumerate(zip(pts, radii)) if j != i)
            pen += 50 * sum(not (rc[2] + 8 <= q[0] or q[2] + 8 <= rc[0] or rc[3] + 8 <= q[1] or q[3] + 8 <= rc[1]) for _, q, _ in placed)
            if best is None or pen < best[0]:
                best = (pen, side, rc)
        placed.append((best[1], best[2], best[0]))
    return placed

def mst(pts):
    inn, out = {0}, []
    while len(inn) < len(pts):
        _, u, v = min((math.dist(pts[u], pts[v]), u, v) for u in inn for v in range(len(pts)) if v not in inn)
        inn.add(v); out.append((u, v))
    return out

def search_layout(radii, sizes, W, H, x0, y0, seed, trials=1500, min_d=170):
    rnd, best = random.Random(seed), None
    for trial in range(trials):
        pts, tries = [], 0
        while len(pts) < len(radii) and tries < 400:
            tries += 1
            pad = max(30, radii[len(pts)] * 1.7 + 4)  # keep the whole glow (and the top star's spike) on the canvas
            p = (rnd.uniform(x0 + pad, W - pad), rnd.uniform(y0 + pad, H - pad))
            if all(math.dist(p, q) >= min_d for q in pts):
                pts.append(p)
        if len(pts) < len(radii):
            continue
        edges = mst(pts)
        extra = sorted((math.dist(pts[u], pts[v]), u, v) for u in range(len(pts)) for v in range(u + 1, len(pts)) if (u, v) not in edges and (v, u) not in edges)
        if extra:
            edges.append(extra[0][1:])
        lab = place_labels(pts, radii, edges, sizes, W, H, x0, y0)
        pen = sum(x[2] for x in lab)
        score = pen - (max(x for x, _ in pts) - min(x for x, _ in pts)) * .001
        if best is None or score < best[0]:
            best = (score, pts, edges, lab)
        if pen < 1 and trial > 300:
            break
    if best is None:
        raise SystemExit("could not place constellation stars; lower min_d")
    return best[1], best[2], [(s, r) for s, r, _ in best[3]]

def constellation_svg(pts, radii, edges, W, H, label, pos=""):
    o = [f'<line x1="{pts[u][0]:.0f}" y1="{pts[u][1]:.0f}" x2="{pts[v][0]:.0f}" y2="{pts[v][1]:.0f}" stroke="{ACCENT}" stroke-opacity="0.5" stroke-width="2"/>' for u, v in edges]
    for i, ((x, y), r) in enumerate(zip(pts, radii)):
        col = ACCENT if i == 0 else WHITE
        if i == 0:
            s, k = 2.3 * r, .22 * r
            o.append(f'<path d="M{x:.1f} {y - s:.1f} L{x + k:.1f} {y - k:.1f} L{x + s:.1f} {y:.1f} L{x + k:.1f} {y + k:.1f} L{x:.1f} {y + s:.1f} L{x - k:.1f} {y + k:.1f} L{x - s:.1f} {y:.1f} L{x - k:.1f} {y - k:.1f} Z" fill="{ACCENT}" fill-opacity="0.55"/>')
        o.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r * 1.9:.1f}" fill="{col}" fill-opacity="0.14"/><circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" fill="{col}"/><circle cx="{x:.1f}" cy="{y:.1f}" r="{max(r * .35, 2):.1f}" fill="#ffffff"/>')
    return f'<svg aria-label="{esc(label)}" width="{W}" height="{H}" viewBox="0 0 {W} {H}" style="{pos}width:{W}px;height:{H}px">{"".join(o)}</svg>'

def label_ps(lab, texts, colors, font=BODY, ox=0, oy=0):
    return "".join(f'<p style="position:absolute;left:{r[0] + ox:.0f}px;top:{r[1] + oy:.0f}px;width:{r[2] - r[0]:.0f}px;font-family:{font};font-size:24px;line-height:1.25;color:{c};'
                   f'text-align:{"right" if side == "left" else ("center" if side in ("above", "below") else "left")}">{tx}</p>' for (side, r), tx, c in zip(lab, texts, colors))

# ---------- slides ----------
ORDER = ["cover"]
if cb: ORDER.append("summary")
ORDER += ["segments", "favorites"]
if cb and (gb or pp): ORDER.append("vs-today")
if len(FOLDS) > 1: ORDER.append("holds-up")
if cb and cb.get("group_share") is not None: ORDER.append("group-share")
if has_pl: ORDER.append("report-card")
if has_shap: ORDER += ["driver-map", "families"]
ORDER += [f"p-{p['key'].replace('lbl_', '')}" for p in P] + ["close"]
S = {}
src = lambda x: t("", f"Source: {x}")

# cover
weights = [p["oot"]["n_pos"] if p.get("oot") else max(p["rate"].values()) for p in P]
radii = [6 + 22 * math.sqrt(w / max(weights)) for w in weights]
order_idx = sorted(range(len(P)), key=lambda i: -weights[i])
sizes = [(len(P[i]["short"]) * .58 * 24 + 8, 32) for i in order_idx]
pts, edges, lab = search_layout([radii[i] for i in order_idx], sizes, 1800, 960, 1000, 130, seed=11, trials=800, min_d=140)
S["cover"] = section("cover", f'''{constellation_svg(pts, [radii[i] for i in order_idx], edges, 1920, 1080, "The products as a constellation", "position:absolute;left:0px;top:0px;")}
<div style="width:820px;display:flex;flex-direction:column;gap:24px">
{eyebrow(esc(ST.get("eyebrow")))}
<h1 style="font-family:{HEAD};font-size:112px;font-weight:700;line-height:1.02;color:{WHITE}">{esc(ST.get("title") or "ML Model")}</h1>
<p style="font-family:{HEAD};font-size:40px;font-weight:600;line-height:1.25;color:{ACCENT}">{esc(ST.get("tagline"))}</p>
{para(esc(ST.get("intro"))) if ST.get("intro") else ""}
{para(esc(ST.get("sample_note")), 24, MUTE) if ST.get("sample_note") else ""}
</div>
{label_ps(lab, [esc(P[i]["short"]) for i in order_idx], [ACCENT if k == 0 else SOFT for k in range(len(P))])}''',
    notes=t(f"{ST.get('title')} ranks our {len(P)} products for each customer.", "Walkthrough of the model run: uptake rates, ranking metrics, decomposition and SHAP drivers."),
    extra="justify-content:center;padding:128px")

if cb:
    tiles = []
    if EX:
        tiles.append((pc0(cb["p@1"]), "of the time, our <b>#1 recommendation</b> was a product the customer bought", ACCENT))
        if gb: tiles.append((f"+{round((cb['p@1'] - gb['p@1']) * 100)} pts", f"better than the group's <b>usual mix</b> ({pc0(gb['p@1'])})", WHITE))
        elif pp: tiles.append((f"+{round((cb['p@1'] - pp['p@1']) * 100)} pts", f"better than the <b>most popular product</b> ({pc0(pp['p@1'])})", WHITE))
        if cb.get("r@3") is not None: tiles.append((pc0(cb["r@3"]), "of purchased products are in our <b>top three</b>", WHITE))
    else:
        tiles.append((pc(cb["p@1"]), "<b>P@1</b>", ACCENT))
        if gb: tiles.append((f"+{(cb['p@1'] - gb['p@1']) * 100:.1f}", f"pts over <b>group_baseline</b> ({pc(gb['p@1'])})", WHITE))
        if pp: tiles.append((f"+{(cb['p@1'] - pp['p@1']) * 100:.1f}", f"pts over <b>popularity</b> ({pc(pp['p@1'])})", WHITE))
        if cb.get("within_group_auc_fx") is not None: tiles.append((f"{cb['within_group_auc_fx']:.3f}", "<b>within-group AUC</b> of f(x)", WHITE))
    note = t(f"Measured on about {round(cb.get('n_rows_scored', 0) / 1000):,},000 {FOLDN.get(FOLD, FOLD).lower()} with at least one product sold.", f"metrics_summary.csv · fold {FOLD} · {int(cb.get('n_rows_scored', 0)):,} scored customers")
    S["summary"] = section("summary", f'''{eyebrow(t("The bottom line", "Headline metrics"))}{h2(t("It picks the right product more often than today's approach" if gb else "It picks the right product most of the time", "Ranking quality at a glance"))}
<div style="display:flex;gap:32px">{"".join(card(big(b, c) + para(x)) for b, x, c in tiles)}</div>
{footer(note, "summary")}''', bg=BG_B, notes=t("Headline: top-pick accuracy on customers the model had not seen.", "P@1, lifts over baselines and within-group AUC for the served score."))

# customer-type grid
rate_max = max(p["rate"][c] for p in P for c, _ in SEG)
rowh = min(58, int(600 / len(P)))
colw = min(230, int(900 / len(SEG)))
hdr = "".join(f'<p style="width:{colw}px;font-family:{HEAD};font-size:24px;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:{SOFT};line-height:1.4">{esc(n)}</p>' for _, n in SEG)
rows = []
for p in P:
    vals = [p["rate"][c] for c, _ in SEG]; peak = max(vals)
    cells = ""
    for v in vals:
        d = 6 + (rowh - 8) * math.sqrt(v / rate_max) if v > 0 else 0
        col = ACCENT if v == peak else WHITE
        dot = f'<div style="width:{d:.0f}px;height:{d:.0f}px;border-radius:50%;background:{col};opacity:{1 if v == peak else .8}"></div>' if d else ""
        cells += (f'<div style="width:{colw}px;display:flex;flex-direction:row;align-items:center;gap:14px"><div style="width:{rowh}px;height:{rowh}px;display:flex;align-items:center;justify-content:center">{dot}</div>'
                  f'<p style="font-size:28px;line-height:1.2;color:{col};font-weight:{700 if v == peak else 400}">{v:.1f}%</p></div>')
    rows.append(f'<div style="display:flex;flex-direction:row;align-items:center;height:{rowh}px"><p style="width:280px;font-size:28px;line-height:1.2;color:{WHITE}">{esc(p["short"])}</p>{cells}</div>')
ins = []
for c, n in SEG:
    r = sorted(P, key=lambda p: -p["rate"][c])
    line = " · ".join(f"{esc(q['short'])} {q['rate'][c]:.1f}%" for q in r[:2])
    ins.append(f'<div style="display:flex;flex-direction:column;gap:6px;padding:0px 0px 0px 24px;border-left:4px solid {ACCENT}">'
               f'{eyebrow(esc(n) + t(" customers", ""))}{para(line, 28, WHITE)}</div>')
dropped = D["droppedSegments"]
S["segments"] = section("segments", f'''{h2(t("What customers buy, by segment", "Uptake rate by segment"))}
<div style="display:flex;flex-direction:row;gap:64px">
<div style="display:flex;flex-direction:column"><div style="display:flex;flex-direction:row;align-items:end;height:48px"><p style="width:280px;font-size:24px;color:{SOFT};line-height:1.4">{t("Product", "Label")}</p>{hdr}</div>{"".join(rows)}</div>
<div style="flex:1;display:flex;flex-direction:column;gap:32px;justify-content:center">{para(t("Bigger star = bought more often. Gold = the segment where each product sells best.", "Star area ∝ uptake rate; accent = peak segment per label."), 24)}{"".join(ins)}</div></div>
{footer(t("Share of customers that bought each product.", "Source: rate_by_segment_pct.csv (train fold)") + (f" {', '.join(dropped)} {t('customers had no purchases and are not shown.', 'omitted (all zero).')}" if dropped else ""), "segments")}''',
    notes=t("Historical purchase rates by segment.", "Train-fold uptake rate by segment; also the popularity baseline."))

def sig(c, n):
    r = sorted(P, key=lambda p: -p["rate"][c])
    kv = "".join(f'<div style="display:flex;flex-direction:row;justify-content:space-between;border-top:1px solid {BORDER};padding:8px 0px 0px 0px"><p style="font-size:28px;line-height:1.3;color:{WHITE}">{esc(p["short"])}</p><p style="font-size:28px;line-height:1.3;color:{WHITE}">{p["rate"][c]:.1f}%</p></div>' for p in r[1:4])
    return card(eyebrow(esc(n) + t(" customers", "")) + big(f"{r[0]['rate'][c]:.1f}%", ACCENT, 104) + para(f"<b>{esc(r[0]['short'])}</b> {t('sells best', 'is the top label')}", 28, WHITE) + kv
                + para(f"{t('Least likely', 'Lowest')}: {esc(r[-1]['short'])} {r[-1]['rate'][c]:.1f}%", 24, MUTE))
S["favorites"] = section("favorites", f'''{h2(t("Each segment has a clear favourite", "Top labels per segment"))}<div style="display:flex;gap:32px">{"".join(sig(c, n) for c, n in SEG)}</div>
{footer(t("Share of customers of each type that bought the product.", "Source: rate_by_segment_pct.csv"), "favorites")}''', bg=BG_B)

def bars(rows_, scale=760):
    out = ""
    for name, sub, v, col in rows_:
        out += (f'<div style="display:flex;flex-direction:row;align-items:center;gap:24px"><div style="width:420px;display:flex;flex-direction:column"><p style="font-size:30px;line-height:1.25;color:{WHITE}">{name}</p>'
                + (f'<p style="font-size:24px;line-height:1.25;color:{MUTE}">{sub}</p>' if sub else "") + '</div>'
                f'<div style="width:{v * scale:.0f}px;height:44px;border-radius:0px 22px 22px 0px;background:{col}"></div><p style="font-family:{HEAD};font-size:32px;font-weight:700;line-height:1.3;color:{WHITE}">{pc0(v) if EX else pc(v)}</p></div>')
    return out

if "vs-today" in ORDER:
    mods = [("catboost", t(ST.get("title") or "Our model", "catboost (served)"), "", ACCENT), ("group_baseline", t("Group's usual mix", "group_baseline"), t("What each group takes up most", "sigmoid(offset)"), LBLUE),
            ("catboost_avg_group", t("At an average group", "catboost_avg_group"), "", LBLUE), ("catboost_residual", "catboost_residual", "f(x) only", BLUE2),
            ("popularity", t("Most popular product", "popularity"), t("For the segment", "segment uptake rate"), BLUE2)]
    rows_ = [(n, s, MF[m]["p@1"], c) for m, n, s, c in mods if MF.get(m) and (not EX or m in ("catboost", "group_baseline", "popularity"))]
    stats = ""
    if gb: stats += card(big(f"+{round((cb['p@1'] - gb['p@1']) * 100) if EX else round((cb['p@1'] - gb['p@1']) * 100, 1)} pts") + para(t(f'<span style="color:{GOOD}"><b>✓ Better</b></span> than each group\'s usual mix', "P@1 over group_baseline"), 28, WHITE), pad=32)
    if pp: stats += card(big(f"+{round((cb['p@1'] - pp['p@1']) * 100) if EX else round((cb['p@1'] - pp['p@1']) * 100, 1)} pts", WHITE) + para(t(f'<span style="color:{GOOD}"><b>✓ Better</b></span> than the most popular product', "P@1 over popularity"), 28, WHITE), pad=32)
    S["vs-today"] = section("vs-today", f'''{eyebrow(t("How well it works", f"P@1 · {FOLD}"))}{h2(t("Our top pick beats today's approaches", "Served model vs. baselines"))}
<div style="display:flex;flex-direction:row;gap:64px;align-items:center;flex:1"><div style="flex:1;display:flex;flex-direction:column;gap:28px">{para(t("How often the #1 suggestion was bought", "P@1"), 24, MUTE)}{bars(rows_)}</div>
<div style="width:500px;display:flex;flex-direction:column;gap:24px">{stats}</div></div>
{footer(t(f"{FOLDN.get(FOLD, FOLD)} the model had never seen.", f"Source: metrics_summary.csv, fold {FOLD}"), "vs-today")}''')

if "holds-up" in ORDER:
    if EX:
        body = bars([(FOLDN.get(f, f), "", M[f]["catboost"]["p@1"], ACCENT if f == FOLD else LBLUE) for f in FOLDS])
        body = f'<div style="display:flex;flex-direction:column;gap:28px">{body}</div>' + para(f"A small, expected dip from {pc0(M[FOLDS[0]]['catboost']['p@1'])} to {pc0(cb['p@1'])} on {FOLDN.get(FOLD, FOLD).lower()}.", 32, WHITE)
    else:
        g = lambda r, k, f: (f(r[k]) if r.get(k) is not None else "–")
        trs = "".join(f'<tr><td>{FOLDN.get(f, f)}</td><td style="text-align:right">{g(M[f]["catboost"], "n_rows", lambda v: f"{int(v):,}")}</td><td style="text-align:right">{g(M[f]["catboost"], "p@1", lambda v: f"{v:.3f}")}</td>'
                      f'<td style="text-align:right">{g(M[f]["catboost"], "r@3", lambda v: f"{v:.3f}")}</td><td style="text-align:right">{g(M[f]["catboost"], "ndcg@3", lambda v: f"{v:.3f}")}</td><td style="text-align:right">{g(M[f]["catboost"], "within_group_auc_fx", lambda v: f"{v:.3f}")}</td></tr>' for f in FOLDS)
        body = (f'<table style="font-size:30px;color:{WHITE};width:1664px;padding:14px 20px"><tr style="background:{BRAND}"><th style="width:22%;text-align:left">Fold</th><th style="width:16%;text-align:right">Customers</th><th style="width:14%;text-align:right">P@1</th>'
                f'<th style="width:14%;text-align:right">R@3</th><th style="width:16%;text-align:right">NDCG@3</th><th style="width:18%;text-align:right">In-group AUC</th></tr>{trs}</table>')
    S["holds-up"] = section("holds-up", f'''{eyebrow(t("How well it works", "Generalisation"))}{h2(t("It holds up on customers it has never seen", "Across folds"))}{body}
{footer(t("How often the #1 suggestion was bought.", "Source: metrics_summary.csv, model = catboost"), "holds-up")}''', bg=BG_B)

if "group-share" in ORDER:
    d, c = cb["group_share"], cb["customer_share"]; x = max(0, 1 - d - c)
    seg = lambda w, bg, fg, txt: f'<div style="width:{w * 100:.1f}%;background:{bg};display:flex;align-items:center;padding:0px 20px"><p style="font-family:{HEAD};font-size:26px;font-weight:700;color:{fg};line-height:1.2">{txt}</p></div>'
    stack = (f'<div style="width:1664px;display:flex;flex-direction:row;height:80px;border-radius:12px;overflow:hidden">{seg(d, ACCENT, DEEP, t(f"{pc0(d)} Group habits", f"group {pc(d)}"))}'
             f'{seg(c, WHITE, BRAND, t(f"{pc0(c)} Customer &amp; context", f"customer {pc(c)}"))}<div style="width:{x * 100:.1f}%;background:{MUTE}"></div></div>')
    calls = ""
    if avg and pp: calls += card(big(pc0(avg["p@1"]) if EX else pc(avg["p@1"])) + para(t(f"<b>Works for new groups.</b> With no group history it is right {pc0(avg['p@1'])} of the time vs {pc0(pp['p@1'])} for the most popular product.", f"<b>catboost_avg_group</b> P@1 vs {pc(pp['p@1'])} popularity."), 28, WHITE))
    if res and gb and not EX: calls += card(big(pc(res["p@1"]), WHITE) + para(f"<b>catboost_residual</b> P@1, below group_baseline ({pc(gb['p@1'])}): f(x) alone ranks departure from the group norm.", 28, WHITE))
    S["group-share"] = section("group-share", f'''{eyebrow(t("How well it works", f"Share of logit variance · {FOLD}"))}{h2(t("About half of each recommendation reflects the group", "Group vs. customer share"))}{stack}
<div style="display:flex;gap:32px">{calls}</div>
{footer(t("Grey: where group habits and customer details overlap.", "Grey = 2 × covariance · metrics_summary.csv"), "group-share")}''')

if has_pl:
    rows_ = sorted(P, key=lambda p: -p["oot"]["pos_rate"])
    if EX:
        head = f'<tr style="background:{BRAND}"><th style="width:24%;text-align:left">Product</th><th style="width:15%;text-align:right">Buy rate</th><th style="width:16%;text-align:right">Score</th><th style="width:15%">Grade</th>' + (f'<th style="width:15%;text-align:right">In one group</th><th style="width:15%">Grade</th>' if has_wd else "") + "</tr>"
        trs = "".join(f'<tr><td>{esc(p["short"])}</td><td style="text-align:right">{p["oot"]["pos_rate"]:.1f}%</td><td style="text-align:right">{round(p["oot"]["auc"] * 100)}</td><td>{grade(p["oot"]["auc"])}</td>'
                      + (f'<td style="text-align:right">{round(p["wd"]["auc"] * 100)}</td><td>{grade(p["wd"]["auc"])}</td>' if has_wd else "") + "</tr>" for p in rows_)
    else:
        head = f'<tr style="background:{BRAND}"><th style="width:22%;text-align:left">Label</th><th style="width:18%;text-align:right">Eligible</th><th style="width:15%;text-align:right">Uptake</th><th style="width:15%;text-align:right">AUC</th><th style="width:15%;text-align:right">AP</th>' + (f'<th style="width:15%;text-align:right">In-group</th>' if has_wd else "") + "</tr>"
        trs = "".join(f'<tr><td>{esc(p["short"])}</td><td style="text-align:right">{p["oot"]["n_eligible"]:,}</td><td style="text-align:right">{p["oot"]["pos_rate"]:.1f}%</td><td style="text-align:right">{p["oot"]["auc"]:.3f}</td>'
                      f'<td style="text-align:right">{(p["oot"]["ap"] or 0):.3f}</td>' + (f'<td style="text-align:right">{p["wd"]["auc"]:.3f}</td>' if has_wd else "") + "</tr>" for p in rows_)
    S["report-card"] = section("report-card", f'''{h2(t("Product report card", "Per-label metrics"))}<table style="font-size:24px;color:{WHITE};width:1664px;padding:9px 18px">{head}{trs}</table>
{footer(t("Score out of 100: 50 = coin flip, 100 = perfect. Excellent 90+, Strong 80–89, Good 70–79, Fair below 70.", f"Source: per_label_metrics_{FOLD}.csv, per_label_within_group_auc_{FOLD}.csv"), "report-card")}''', bg=BG_B)

if has_shap:
    feats = D["atlas"]; NP, NR = len(P), len(feats)
    COLW, ROWH, LABW = min(138, int((1664 - 260) / NP)), min(46, int(560 / NR)), 260
    vmax = max(p["share"][0][1] for p in P)
    seps = [ci for ci in range(1, NP) if P[ci]["family"] != P[ci - 1]["family"]]
    grid_rows = ""
    for ri, f in enumerate(feats):  # one strip per feature row, so the label and its stars share a flex row
        circ = [f'<line x1="{ci * COLW}" y1="0" x2="{ci * COLW}" y2="{ROWH}" stroke="{MUTE}" stroke-width="1" stroke-dasharray="4 6"/>' for ci in seps]
        for ci, p in enumerate(P):
            v = dict(p["share"]).get(f, 0); top = p["share"][0][0] == f
            r = (ROWH / 2 - 2) * math.sqrt(v / vmax); cx_, cy_ = ci * COLW + COLW / 2, ROWH / 2
            if top: circ.append(f'<circle cx="{cx_:.0f}" cy="{cy_:.0f}" r="{min(r * 1.7, ROWH / 2):.1f}" fill="{ACCENT}" fill-opacity="0.2"/>')
            circ.append(f'<circle cx="{cx_:.0f}" cy="{cy_:.0f}" r="{max(r, 2.5):.1f}" fill="{ACCENT if top else WHITE}" fill-opacity="{1 if top else .82}"/>')
        grid_rows += (f'<div style="display:flex;flex-direction:row;align-items:center;height:{ROWH}px"><p style="width:{LABW}px;font-size:24px;line-height:1.2;color:{SOFT}">{fname(f)}</p>'
                      f'<svg aria-label="{fname(f)} by product" width="{COLW * NP}" height="{ROWH}" viewBox="0 0 {COLW * NP} {ROWH}" style="width:{COLW * NP}px;height:{ROWH}px">{"".join(circ)}</svg></div>')
    # headers alternate between two lines so long names in neighbouring columns never touch
    colhdr = "".join(f'<div style="width:{COLW}px;height:68px;display:flex;flex-direction:column;justify-content:{"end" if ci % 2 == 0 else "start"}">'
                     f'<p style="width:{COLW * 2}px;transform:translateX(-{COLW // 2}px);white-space:nowrap;font-size:24px;line-height:1.15;color:{WHITE};text-align:center">{esc(p["short"])}</p></div>' for ci, p in enumerate(P))
    S["driver-map"] = section("driver-map", f'''{h2(t("The signals behind each product", "SHAP atlas"))}
<div style="display:flex;flex-direction:column;gap:8px"><div style="display:flex;flex-direction:row;height:68px"><div style="width:{LABW}px"></div>{colhdr}</div><div style="display:flex;flex-direction:column">{grid_rows}</div></div>
{footer(t("Bigger star = more influence. Gold = the product's #1 signal. Patterns in past customers, not causes.", "Star area ∝ share of mean |SHAP| · accent = top feature · shap_mean_abs_lbl_*.csv"), "driver-map")}''')

    fc = "".join(card(f'<div style="width:20px;height:20px;border-radius:50%;background:{f["color"]}"></div><h3 style="font-family:{HEAD};font-size:36px;font-weight:700;line-height:1.15;color:{WHITE}">{esc(f["name"])}</h3>'
                      + para(" · ".join(esc(p["short"]) for p in P if p["family"] == f["name"]), 28, WHITE) + (para(esc(f["why"]), 24) if f.get("why") else ""), pad=36) for f in D["families"])
    S["families"] = section("families", f'''{h2(t(f"{len(D['families'])} kinds of buyer signals", "Label families by top driver"))}
{para(t("Products that respond to the same signals group together.", "Grouped by top one or two SHAP features."))}<div style="display:flex;flex-direction:row;gap:28px;flex:1">{fc}</div>
{footer(t("Grouped by each product's strongest signals.", "Source: shap_mean_abs_lbl_*.csv"), "families", SOFT)}''', bg=BRAND, stars=False)

W_, H_ = 1060, 380
for i, p in enumerate(P):
    sid = f"p-{p['key'].replace('lbl_', '')}"
    top = (p.get("share") or [])[: 6 if EX else 7]
    raw = dict(p.get("raw") or [])
    cons = ""
    if top:
        v1 = top[0][1]
        rr = [12 + 30 * math.sqrt(v / v1) for _, v in top]
        texts = [f"{fname(f)}<br><span style=\"color:{SOFT}\">{pc0(v)}</span>" if EX else f"{esc(f)}<br><span style=\"color:{SOFT}\">{raw.get(f, 0):.2f}</span>" for f, v in top]
        szs = [(max(len(FN.get(f, f) if EX else f), 6) * .6 * 24 + 6, 62) for f, _ in top]
        clear = [r * (2.0 if k == 0 else 1.15) for k, r in enumerate(rr)]  # leave room for the top star's spike and the glows
        pts, edges, lab = search_layout(clear, szs, W_, H_, 0, 0, seed=sum(map(ord, p["key"])), min_d=180)
        cons = f'<div style="position:relative;width:{W_}px;height:{H_}px">{constellation_svg(pts, rr, edges, W_, H_, p["short"] + " driver constellation")}{label_ps(lab, texts, [ACCENT if k == 0 else WHITE for k in range(len(top))])}</div>'
    kp = ""
    if p.get("oot"):
        best = max(SEG, key=lambda c: p["rate"][c[0]])
        items = ([("Bought by", f'{p["oot"]["pos_rate"]:.1f}%'), ("Model score", f'{round(p["oot"]["auc"] * 100)} · {grade(p["oot"]["auc"])}'), ("Sells best in", f'{best[1]}')] if EX else
                 [(f"Uptake ({FOLD})", f'{p["oot"]["pos_rate"]:.1f}%'), ("AUC", f'{p["oot"]["auc"]:.3f}'), ("In-group AUC", f'{p["wd"]["auc"]:.3f}' if p.get("wd") else "–")])
        kp = '<div style="display:flex;flex-direction:row;gap:16px">' + "".join(f'<div style="flex:1;display:flex;flex-direction:column;gap:4px;padding:16px 20px;border:1px solid {BORDER};border-radius:12px;background:{BRAND}"><p style="font-size:24px;line-height:1.3;color:{SOFT}">{a_}</p><p style="font-family:{HEAD};font-size:36px;font-weight:700;line-height:1.1;color:{WHITE}">{b_}</p></div>' for a_, b_ in items) + "</div>"
    right = ""
    if EX:
        sig_rows = "".join(f'<div style="display:flex;flex-direction:row;align-items:center;gap:12px"><p style="width:220px;font-size:24px;line-height:1.2;color:{WHITE}">{fname(f)}</p><div style="width:{max(8, v / top[0][1] * 150):.0f}px;height:12px;border-radius:0px 6px 6px 0px;background:{ACCENT if k == 0 else LBLUE}"></div><p style="font-size:24px;line-height:1.2;color:{SOFT}">{pc0(v)}</p></div>' for k, (f, v) in enumerate(top[:5]))
        why = "".join(f"<li>{esc(w)}</li>" for w in (p.get("why") or [])[:4])  # Slides lists take plain <li>; the <ul> carries the style
        right = (f'<div style="position:absolute;left:1236px;top:128px;width:556px;display:flex;flex-direction:column;gap:18px;padding:36px;border:1px solid {BORDER};border-radius:16px;background:{BRAND}">'
                 f'<h3 style="font-family:{HEAD};font-size:32px;font-weight:700;line-height:1.2;color:{WHITE}">Top signals</h3>{sig_rows}'
                 + (f'<h3 style="font-family:{HEAD};font-size:32px;font-weight:700;line-height:1.2;color:{WHITE}">More likely to buy when…</h3><ul style="font-size:24px;line-height:1.4;color:{WHITE}">{why}</ul>' if why else "") + "</div>")
    elif ASSETS.get(p["key"]):
        right = (f'<div style="position:absolute;left:1236px;top:128px;width:556px;height:792px;background:#ffffff;border-radius:16px;display:flex;align-items:center;justify-content:center">'
                 f'<img src="{ASSETS[p["key"]]}" alt="SHAP beeswarm for {esc(p["short"])}" style="width:532px;height:768px;object-fit:contain"></div>')
    lead = f'{fname(top[0][0])} {t("leads at", "leads at")} {pc0(top[0][1]) if EX else f"{raw.get(top[0][0], 0):.2f} mean |SHAP|"}' if top else ""
    S[sid] = section(sid, f'''<div style="width:1060px;display:flex;flex-direction:column;gap:16px">
{eyebrow(f'{t("Product", "Label")} {i + 1} of {len(P)} · {esc(p["family"])}')}
{h2(esc(p.get("long") or p["short"]))}
{para(esc(p["desc"]) if EX and p.get("desc") else lead, 30)}
{cons}{kp}</div>{right}
{footer(t("Influence = share of the model's driver analysis; patterns, not causes.", f"Source: shap_mean_abs_{p['key']}.csv · per_label_metrics_{FOLD}.csv"), sid)}''',
        bg=BG_A if i % 2 == 0 else BG_B,
        notes=f"{p['short']}. Top signals: " + ", ".join(f"{FN.get(f, f)} {v * 100:.1f}%" for f, v in top) + ".")

# close
cl = ST.get("close") or {}
tk = cl.get("takeaways")
if not tk:
    tk = []
    if cb and gb: tk.append([t("Better recommendations than today", "Beats the group baseline"), t(f"Top pick right {pc0(cb['p@1'])} of the time, {round((cb['p@1'] - gb['p@1']) * 100)} points ahead of each group's usual mix.", f"P@1 {pc(cb['p@1'])} vs {pc(gb['p@1'])} group_baseline.")])
    tk.append([t("Segment sets the stage", "Segment drives the base rate"), "; ".join(f"{n} → {max(P, key=lambda p: p['rate'][c])['short']}" for c, n in SEG) + "."])
    if avg and pp: tk.append([t("Ready for new groups", "Portable customer term"), t(f"Without group history it still beats the most-popular approach ({pc0(avg['p@1'])} vs {pc0(pp['p@1'])}).", f"catboost_avg_group {pc(avg['p@1'])} vs popularity {pc(pp['p@1'])}.")])
    if has_shap: tk.append([t("Clear, explainable signals", "Driver families"), " · ".join(f["short"] for f in D["families"]) + "."])
tkh = "".join(f'<div style="display:flex;flex-direction:row;gap:24px;align-items:start"><p style="width:56px;font-family:{HEAD};font-size:56px;font-weight:700;line-height:1;color:{ACCENT}">{k + 1}</p>'
              f'<div style="flex:1;display:flex;flex-direction:column;gap:6px"><h3 style="font-family:{HEAD};font-size:36px;font-weight:700;line-height:1.2;color:{WHITE}">{esc(a_)}</h3>{para(esc(b_), 28)}</div></div>' for k, (a_, b_) in enumerate(tk[:4]))
nx = cl.get("next")
nxh = (f'<div style="width:520px;display:flex;flex-direction:column;gap:16px;padding:44px;border:2px solid {ACCENT};border-radius:16px;background:{BRAND}">{eyebrow(esc(nx.get("eyebrow") or "Next phase"))}'
       f'<h3 style="font-family:{HEAD};font-size:40px;font-weight:700;line-height:1.2;color:{WHITE}">{esc(nx.get("title"))}</h3>{para(esc(nx.get("text")), 28) if nx.get("text") else ""}</div>') if nx else ""
S["close"] = section("close", f'''{h2(t("What this means for us", "Summary"))}<div style="display:flex;flex-direction:row;gap:64px"><div style="flex:1;display:flex;flex-direction:column;gap:32px">{tkh}</div>{nxh}</div>
{footer(esc(ST.get("title") or ""), "close")}''', notes=cl.get("notes") or "")

# ---------- write ----------
root = Path(a.root) / "project"
(root / "slides").mkdir(parents=True, exist_ok=True)
for sid in ORDER:
    (root / "slides" / f"{sid}.html").write_text(S[sid], encoding="utf-8")
sections = {"s1": {"description": "Opening", "start": "cover"}, "s2": {"description": t("What sells today", "Uptake rates"), "start": "segments"}}
perf = next((s for s in ("vs-today", "holds-up", "group-share", "report-card") if s in ORDER), None)
if perf: sections["s3"] = {"description": t("How well it works", "Ranking performance"), "start": perf}
if has_shap: sections["s4"] = {"description": t("What drives each product", "SHAP drivers"), "start": "driver-map"}
sections["s5"] = {"description": t("Next steps", "Close"), "start": "close"}
deck = {"v": 4, "createdOnFiles": {"v": 1, "at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}, "lists": "css",
        "title": (ST.get("title") or "ML Model") + t(" Briefing", " Model Review"), "cover": "cover", "order": ORDER, "sections": sections,
        "faces": {f.lower().replace(" ", "-"): {"family": f, "href": TH["fonts"]["href"]} for f in dict.fromkeys((TH["fonts"]["head"], TH["fonts"]["body"]))},
        "designSystems": []}
(root / "deck.json").write_text(json.dumps(deck, indent=1), encoding="utf-8")
big_ = [sid for sid in ORDER if len(S[sid].encode()) > 60000]
print(f"wrote {len(ORDER)} slides + deck.json under {root}")
print("order:", ", ".join(ORDER))
if not ASSETS.get("logo"): print("note: no logo asset given, so slides carry no logo (upload the theme logo and pass --assets)")
if big_: print("warning: large slides:", big_)
