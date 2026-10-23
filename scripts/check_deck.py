"""Check built Slides files against the parts of the Slides format the builder can get wrong.

    python check_deck.py <root>        (the --root given to build_deck.py)

Flags tags and CSS properties outside the Slides subset, styled <li> (lists take plain items),
em/rem/vw/vh units, text under 24px, more than 200 elements or more than one <section> per slide,
SVGs over 52 KB or holding <text>, and constellation stars whose glow runs off their canvas.
Exits 1 when anything is found. It is a guard for edits to build_deck.py, not a full validator.
"""
import re, sys
from pathlib import Path

ALLOWED = set("""position left top right bottom width height min-width min-height max-width max-height display
flex-direction flex-wrap gap align-items justify-content justify-items align-self justify-self flex flex-grow
flex-shrink flex-basis grid-template-columns grid-template-rows grid-column grid-row aspect-ratio padding overflow
font-family font-size font-weight font-style font line-height letter-spacing text-align text-transform white-space
text-decoration font-variant-numeric -webkit-text-stroke color background background-clip -webkit-text-fill-color
border border-top border-right border-bottom border-left border-radius box-shadow text-shadow opacity transform
filter backdrop-filter mix-blend-mode object-fit""".split())
TAGS = set("section h1 h2 h3 p ul ol li br b i u a span div img table tr th td svg hr x-shape x-icon x-connector x-embed aside".split())

slides = sorted((Path(sys.argv[1]) / "project" / "slides").glob("*.html"))
problems = []
for f in slides:
    h = f.read_text(encoding="utf-8")
    svgs = re.findall(r"<svg.*?</svg>", h, flags=re.S)
    flat = re.sub(r"<svg.*?</svg>", "<svg></svg>", h, flags=re.S)
    say = lambda msg: problems.append(f"{f.name}: {msg}")
    if h.count("<section") != 1:
        say(f"{h.count('<section')} <section> elements (need exactly 1)")
    if len(re.findall(r"<[a-zA-Z]", flat)) > 200:
        say(f"{len(re.findall(r'<[a-zA-Z]', flat))} elements (max 200)")
    for tag, attrs in re.findall(r"<([a-zA-Z][\w-]*)([^>]*)>", flat):
        tag = tag.lower()
        if tag not in TAGS:
            say(f"tag <{tag}> is not in the Slides subset")
        style = re.search(r'style="([^"]*)"', attrs)
        if not style:
            continue
        if tag == "li":
            say("styled <li>: put the style on the <ul>/<ol>")
        for decl in style.group(1).split(";"):
            if ":" not in decl:
                continue
            k, v = (x.strip() for x in decl.split(":", 1))
            if k.lower() not in ALLOWED:
                say(f"CSS property '{k}' on <{tag}> is not in the Slides subset")
            if re.search(r"\d(em|rem|vw|vh)\b", v):
                say(f"unit not allowed in '{k}:{v}'")
            if k == "font-size" and float(re.sub(r"[^\d.]", "", v) or 0) < 24:
                say(f"font-size {v} is under 24px")
    for s in svgs:
        if len(s.encode()) > 52000:
            say(f"svg of {len(s.encode()):,} bytes (max 52 KB)")
        if "<text" in s:
            say("svg holds <text> (labels go in <p> over it)")
        m = re.match(r'<svg aria-label="([^"]*)" width="(\d+)" height="(\d+)"', s)
        if m and m.group(1) != "Starfield":
            W, H = int(m.group(2)), int(m.group(3))
            for cx, cy, r in re.findall(r'<circle cx="([\d.]+)" cy="([\d.]+)" r="([\d.]+)" fill="[^"]*" fill-opacity="0.14"', s):
                cx, cy, r = float(cx), float(cy), float(r)
                if cx - r < 0 or cy - r < 0 or cx + r > W or cy + r > H:
                    say(f"star glow at ({cx:.0f},{cy:.0f}) runs off the {m.group(1)!r} canvas")

for p in dict.fromkeys(problems):
    print(p)
print(f"{len(slides)} slides checked, {len(set(problems))} problems")
sys.exit(1 if problems else 0)
