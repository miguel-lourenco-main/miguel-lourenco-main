#!/usr/bin/env python3
"""assets/constellation.svg — public repos as a star field.

Each repo is a star; its size is sqrt(lines of code). Repos whose main language is the same are joined into a
constellation (minimum spanning tree, faint lines) named after that language in the legend. Positions are
deterministic: seeded by a hash of the repo name, then relaxed so stars and labels never overlap, with a weak pull
toward their constellation. The two most recently committed repos pulse. Usage: draw_constellation.py [out]"""
import datetime as dt, hashlib, math, os, random, sys
sys.path.insert(0, os.path.dirname(__file__))
from theme import *  # noqa
import data

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "..", "assets", "constellation.svg")
W, H = 1200, 420
FX0, FY0, FX1, FY1 = 56, 64, 870, 316      # star field
LEG_X = 905                                  # legend column
LANG_COLOR = {"TypeScript": WINDOW, "OCaml": COOL, "JavaScript": PAPER}
CHAR_W = 7.8                                 # mono 13px advance


def seed(name):
    h = hashlib.sha256(name.encode()).digest()
    return h[0] / 255, h[1] / 255


def kloc(v):
    return f"{v / 1000:.1f}k"


def layout(stars, lang_order):
    """Each constellation gets its own band of sky (width by star count), so constellation lines never cross.
    Inside the band a star starts at a position hashed from its name, then boxes (star + label) are pushed apart."""
    counts = {l: sum(1 for s in stars if s["lang"] == l) for l in lang_order}
    weights = {l: counts[l] + 1.2 for l in lang_order}
    x, band = FX0, {}
    for l in lang_order:
        w = (FX1 - FX0) * weights[l] / sum(weights.values())
        band[l] = (x, x + w); x += w
    for s in stars:
        u, v = seed(s["name"])
        s["lw"] = 10 + CHAR_W * max(len(s["name"]), 6)  # label to the right of the star
        bx0, bx1 = band[s["lang"]]
        s["x0"], s["x1"] = bx0 + s["r"] + 6, max(bx0 + s["r"] + 6, bx1 - s["lw"] - 6)
        s["x"] = s["x0"] + u * (s["x1"] - s["x0"])
        s["y"] = FY0 + v * (FY1 - FY0)

    def box(s, pad=16):
        return (s["x"] - s["r"] - pad, s["y"] - max(s["r"], 14) - pad, s["x"] + s["r"] + s["lw"] + pad, s["y"] + max(s["r"], 16) + pad)

    for it in range(800):
        moved = False
        for i, a in enumerate(stars):
            for b in stars[i + 1:]:
                ax0, ay0, ax1, ay1 = box(a); bx0, by0, bx1, by1 = box(b)
                ox, oy = min(ax1, bx1) - max(ax0, bx0), min(ay1, by1) - max(ay0, by0)
                if ox > 0 and oy > 0:
                    moved = True
                    if ox < oy:
                        d = (ox / 2 + .5) * (1 if a["x"] < b["x"] else -1); a["x"] -= d; b["x"] += d
                    else:
                        d = (oy / 2 + .5) * (1 if a["y"] <= b["y"] else -1); a["y"] -= d; b["y"] += d
        for s in stars:
            s["x"] = min(max(s["x"], s["x0"]), s["x1"])
            s["y"] = min(max(s["y"], FY0), FY1)
        if not moved: break
    return band


def mst(group):
    """Prim's minimum spanning tree over Euclidean distance."""
    if len(group) < 2: return []
    inside, edges = {0}, []
    while len(inside) < len(group):
        best = min(((math.dist((group[i]["x"], group[i]["y"]), (group[j]["x"], group[j]["y"])), i, j)
                    for i in inside for j in range(len(group)) if j not in inside))
        edges.append((group[best[1]], group[best[2]])); inside.add(best[2])
    return edges


def star(s, delay, pulse):
    c = LANG_COLOR.get(s["lang"], DIM)
    r = s["r"]
    spikes = ""
    if r > 6:
        L = r * 2.4
        spikes = (f'<path d="M{n(s["x"] - L)} {n(s["y"])}H{n(s["x"] + L)}M{n(s["x"])} {n(s["y"] - L)}V{n(s["y"] + L)}" '
                  f'stroke="{c}" stroke-width=".7" opacity=".55"/>')
    halo = f'<circle{" class=\"pl\"" if pulse else ""} cx="{n(s["x"])}" cy="{n(s["y"])}" r="{n(r * 3.2)}" fill="url(#halo-{s["lang"]})"/>'
    core = (f'<circle cx="{n(s["x"])}" cy="{n(s["y"])}" r="{n(r)}" fill="{c}"/>'
            f'<circle cx="{n(s["x"])}" cy="{n(s["y"])}" r="{n(max(1.2, r * .45))}" fill="#fffaf0"/>')
    tx = s["x"] + r + 8
    label = (f'<text x="{n(tx)}" y="{n(s["y"] - 1)}" font-family="{MONO}" font-size="13" fill="{PAPER}">{esc(s["name"])}</text>'
             f'<text x="{n(tx)}" y="{n(s["y"] + 14)}" font-family="{MONO}" font-size="11" fill="{DIM}">{kloc(s["loc"])} lines</text>')
    return f'<g>{fade(delay, 1.2)}{halo}{spikes}{core}{label}</g>'


def main():
    stars = sorted(data.repo_stars(), key=lambda s: s["name"])
    if not stars:
        raise SystemExit("no repos with code found")
    top = max(s["loc"] for s in stars)
    for s in stars:
        s["r"] = 3 + 12 * math.sqrt(s["loc"] / top)
    recent = {s["name"] for s in sorted(stars, key=lambda s: s.get("last", ""), reverse=True)[:2]}

    langs = {}
    for s in stars: langs.setdefault(s["lang"], []).append(s)
    lang_order = sorted(langs, key=lambda l: -sum(s["loc"] for s in langs[l]))
    layout(stars, lang_order)

    lines = []
    for l in lang_order:
        c = LANG_COLOR.get(l, DIM)
        for a, b in mst(langs[l]):
            lines.append(f'<line x1="{n(a["x"])}" y1="{n(a["y"])}" x2="{n(b["x"])}" y2="{n(b["y"])}" stroke="{c}" stroke-width=".8" opacity=".32"/>')
    lines_g = f'<g>{fade(1.6, 1.6)}{"".join(lines)}</g>'

    order = sorted(stars, key=lambda s: -s["loc"])
    star_g = "".join(star(s, .2 + i * .12, s["name"] in recent) for i, s in enumerate(order))

    rng = random.Random("dust")
    dust = "".join(f'<circle cx="{n(rng.uniform(-20, LEG_X - 20))}" cy="{n(rng.uniform(-10, H + 10))}" r="{rng.choice([.4, .5, .6, .8])}" '
                   f'fill="{PAPER}" opacity="{rng.uniform(.12, .4):.2f}"/>' for _ in range(140))

    # legend: constellation names
    leg = [f'<line x1="{LEG_X - 20}" y1="40" x2="{LEG_X - 20}" y2="{H - 70}" stroke="{LINE}"/>',
           f'<text x="{LEG_X}" y="62" font-family="{MONO}" font-size="12" fill="{DIM}" letter-spacing="1.5">CONSTELLATIONS</text>']
    y = 104
    for l in lang_order:
        c = LANG_COLOR.get(l, DIM)
        g = langs[l]
        leg.append(f'<circle cx="{LEG_X + 5}" cy="{y - 5}" r="4" fill="{c}"/>'
                   f'<text x="{LEG_X + 20}" y="{y}" font-family="{SERIF}" font-style="italic" font-size="22" fill="{PAPER}">{esc(l)}</text>'
                   f'<text x="{LEG_X + 20}" y="{y + 20}" font-family="{MONO}" font-size="12" fill="{DIM}">{len(g)} star{"s" if len(g) != 1 else ""} · {kloc(sum(s["loc"] for s in g))} lines</text>')
        y += 60
    leg.append(f'<text x="{LEG_X}" y="{y + 4}" font-family="{MONO}" font-size="12" fill="{DIM}">'
               f'<tspan x="{LEG_X}">size = lines of code</tspan><tspan x="{LEG_X}" dy="17">pulsing = most recent commits</tspan></text>')

    total = sum(s["loc"] for s in stars)
    caption = (f'<text x="36" y="{H - 24}" font-family="{MONO}" font-size="15" fill="{PAPER}">{len(stars)} public repos'
               f'<tspan fill="{DIM}"> · </tspan>{total:,} lines of code'
               f'<tspan fill="{DIM}"> · lines join repos with the same main language</tspan></text>')

    defs = "".join(f'<radialGradient id="halo-{l}"><stop offset="0" stop-color="{LANG_COLOR.get(l, DIM)}" stop-opacity=".35"/>'
                   f'<stop offset=".4" stop-color="{LANG_COLOR.get(l, DIM)}" stop-opacity=".08"/><stop offset="1" stop-color="{LANG_COLOR.get(l, DIM)}" stop-opacity="0"/></radialGradient>'
                   for l in lang_order)
    defs += f'<radialGradient id="neb" cx=".35" cy=".45" r=".6"><stop offset="0" stop-color="#1a1d2b"/><stop offset="1" stop-color="{INK}"/></radialGradient>'
    style = ".pl{animation:pl 3.2s ease-in-out infinite}@keyframes pl{0%,100%{opacity:.5}50%{opacity:1}}"
    # drift: SMIL animateTransform on groups that have no transform attribute of their own
    body = (f'<rect width="{W}" height="{H}" fill="url(#neb)"/>'
            f'<g>{dust}<animateTransform attributeName="transform" type="translate" values="0 0;-14 6;0 0" dur="90s" repeatCount="indefinite"/></g>'
            f'<g>{lines_g}{star_g}<animateTransform attributeName="transform" type="translate" values="0 0;6 -3;0 0" dur="60s" repeatCount="indefinite"/></g>'
            + "".join(leg) + caption)
    label = (f"Star map of {len(stars)} public repos, star size by lines of code ({total:,} total), joined into constellations by main language: "
             + "; ".join(f"{l}: " + ", ".join(s['name'] for s in langs[l]) for l in lang_order))
    svg = frame(W, H, body, label, style, defs)
    os.makedirs(os.path.dirname(os.path.abspath(OUT)), exist_ok=True)
    open(OUT, "w", encoding="utf-8").write(svg)
    print(f"constellation: {len(stars)} repos, {total} lines, langs {lang_order}, pulsing {sorted(recent)}, {len(svg) / 1024:.1f} KB -> {OUT}")
    return {"repos": len(stars), "loc": total}


if __name__ == "__main__":
    main()
