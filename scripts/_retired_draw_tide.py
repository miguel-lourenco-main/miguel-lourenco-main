#!/usr/bin/env python3
"""assets/tide.svg — commit tide: contributions per calendar week (Mon–Sun) for the last 52 weeks as a smooth
filled wave, with a thin second wave showing the 52 weeks that ended half a year earlier (shifted back 26 weeks),
and a tide mark on this week. Heights use a sqrt scale. The wave "breathes" between two Catmull-Rom tensions.
Usage: draw_tide.py [out]"""
import datetime as dt, math, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from theme import *  # noqa
import data

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "..", "assets", "tide.svg")
W, H = 1200, 200
X0, X1 = 36, 1164
BASE, TOP = 140, 44
WEEKS, OFFSET = 52, 26


def weekly(days, n_weeks, end_monday):
    by = {dt.date.fromisoformat(d): c for d, c in days}
    out = []
    for k in range(n_weeks - 1, -1, -1):
        mon = end_monday - dt.timedelta(weeks=k)
        out.append((mon, sum(by.get(mon + dt.timedelta(days=i), 0) for i in range(7))))
    return out


def catmull(pts, t, base):
    """Catmull-Rom spline through pts as one cubic path; t is the tension (1 = classic). Controls never dip below base."""
    p = [pts[0]] + pts + [pts[-1]]
    d = [f"M{n(pts[0][0])} {n(pts[0][1])}"]
    for i in range(1, len(p) - 2):
        (x0, y0), (x1, y1), (x2, y2), (x3, y3) = p[i - 1], p[i], p[i + 1], p[i + 2]
        c1 = (x1 + (x2 - x0) / 6 * t, min(base, y1 + (y2 - y0) / 6 * t))
        c2 = (x2 - (x3 - x1) / 6 * t, min(base, y2 - (y3 - y1) / 6 * t))
        d.append(f"C{n(c1[0])} {n(c1[1])} {n(c2[0])} {n(c2[1])} {n(x2)} {n(y2)}")
    return "".join(d)


def main():
    days = data.contributions()
    this_monday = data.today() - dt.timedelta(days=data.today().weekday())
    now = weekly(days, WEEKS, this_monday)
    then = weekly(days, WEEKS, this_monday - dt.timedelta(weeks=OFFSET))
    peak = max(max(c for _, c in now), max(c for _, c in then), 1)
    step = (X1 - X0) / (WEEKS - 1)
    y = lambda c: BASE - (BASE - TOP) * math.sqrt(c / peak)
    pts = [(X0 + i * step, y(c)) for i, (_, c) in enumerate(now)]
    gpts = [(X0 + i * step, y(c)) for i, (_, c) in enumerate(then)]
    close = f"L{X1} {BASE}L{X0} {BASE}Z"
    fa, fb = catmull(pts, 1.0, BASE) + close, catmull(pts, .55, BASE) + close
    la, lb = catmull(pts, 1.0, BASE), catmull(pts, .55, BASE)
    ga, gb = catmull(gpts, 1.0, BASE), catmull(gpts, .6, BASE)
    breathe = lambda a, b, dur: f'<animate attributeName="d" values="{a};{b};{a}" dur="{dur}s" repeatCount="indefinite" calcMode="spline" keySplines=".45 0 .55 1;.45 0 .55 1"/>'

    busiest = max(now, key=lambda t: (t[1], t[0]))
    lo = min(c for _, c in now[:-1])                    # the current week is still in progress
    quiet = [m for m, c in now[:-1] if c == lo]
    tw_mon, tw = now[-1]
    tx, ty = pts[-1]

    months, seen = [], set()
    for i, (m, _) in enumerate(now):
        key = (m + dt.timedelta(days=3)).strftime("%b %Y")    # month the week mostly falls in
        if key in seen or i == 0: seen.add(key); continue
        seen.add(key)
        if (m + dt.timedelta(days=3)).month != (m - dt.timedelta(days=4)).month:
            x = X0 + i * step
            months.append(f'<line x1="{n(x)}" y1="{BASE + 3}" x2="{n(x)}" y2="{BASE + 7}" stroke="{LINE}"/>'
                          f'<text x="{n(x)}" y="{BASE + 19}" font-family="{MONO}" font-size="11" fill="{DIM}" text-anchor="middle">{key[:3].upper()}</text>')

    bx = X0 + now.index(busiest) * step
    by = y(busiest[1])
    mark = (f'<g>{fade(1.8)}<line x1="{n(tx)}" y1="{TOP - 12}" x2="{n(tx)}" y2="{BASE}" stroke="{COOL}" stroke-width="1" stroke-dasharray="2 3"/>'
            f'<circle class="pl" cx="{n(tx)}" cy="{n(ty)}" r="3.2" fill="{COOL}"/>'
            f'<text x="{n(tx - 8)}" y="{TOP - 6}" font-family="{MONO}" font-size="12" fill="{COOL}" text-anchor="end">this week · {tw}</text></g>'
            f'<g>{fade(1.6)}<circle cx="{n(bx)}" cy="{n(by)}" r="2.6" fill="{PAPER}"/>'
            f'<text x="{n(bx)}" y="{n(by - 9)}" font-family="{MONO}" font-size="12" fill="{PAPER}" text-anchor="middle">{busiest[1]}</text></g>')

    hx = [X0, X0 + 236, X0 + 400, X0 + 512]   # 12px mono ≈ 7.2px per character
    head = (f'<text x="{hx[0]}" y="24" font-family="{MONO}" font-size="12" fill="{DIM}" letter-spacing="1.5">CONTRIBUTIONS PER WEEK</text>'
            f'<line x1="{hx[1]}" y1="20" x2="{hx[1] + 22}" y2="20" stroke="{WINDOW}" stroke-width="1.8"/>'
            f'<text x="{hx[1] + 28}" y="24" font-family="{MONO}" font-size="12" fill="{PAPER}">last 52 weeks</text>'
            f'<line x1="{hx[2]}" y1="20" x2="{hx[2] + 22}" y2="20" stroke="{PAPER}" stroke-width="1.2" stroke-dasharray="3 2" opacity=".7"/>'
            f'<text x="{hx[2] + 28}" y="24" font-family="{MONO}" font-size="12" fill="{DIM}">the same span, half a year earlier</text>')
    ties = f"; {len(quiet)} weeks tied" if len(quiet) > 1 else ""
    caption = (f'<text x="{X0}" y="{H - 14}" font-family="{MONO}" font-size="15" fill="{PAPER}">busiest week {busiest[0].isoformat()} ({busiest[1]})'
               f'<tspan fill="{DIM}"> · </tspan>quietest week {quiet[-1].isoformat()} ({lo}{ties})</text>'
               f'<text x="{X1}" y="{H - 14}" font-family="{MONO}" font-size="13" fill="{DIM}" text-anchor="end">weeks start on Monday · sqrt scale</text>')

    defs = (f'<linearGradient id="sea" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{WINDOW}" stop-opacity=".55"/>'
            f'<stop offset="1" stop-color="{WINDOW}" stop-opacity=".04"/></linearGradient>'
            f'<clipPath id="in"><rect x="0" y="0" width="{W}" height="{H}">{reveal("width", 0, W, .2, 2, ".3 .6 .3 1")}</rect></clipPath>')
    body = (head
            + f'<line x1="{X0}" y1="{BASE + .5}" x2="{X1}" y2="{BASE + .5}" stroke="{LINE}"/>'
            + f'<g clip-path="url(#in)">'
            f'<path d="{ga}" fill="none" stroke="{PAPER}" stroke-width="1" stroke-dasharray="3 2" opacity=".5">{breathe(ga, gb, 11)}</path>'
            f'<path d="{fa}" fill="url(#sea)">{breathe(fa, fb, 8)}</path>'
            f'<path d="{la}" fill="none" stroke="{WINDOW}" stroke-width="1.6">{breathe(la, lb, 8)}</path></g>'
            + "".join(months) + mark + caption)
    style = ".pl{animation:pl 2.4s ease-in-out infinite}@keyframes pl{0%,100%{opacity:1}50%{opacity:.3}}"
    label = (f"Commit tide: contributions per week for the last 52 weeks. Busiest week {busiest[0].isoformat()} ({busiest[1]}), "
             f"quietest week {quiet[-1].isoformat()} ({lo}), this week {tw} so far.")
    svg = frame(W, H, body, label, style, defs)
    os.makedirs(os.path.dirname(os.path.abspath(OUT)), exist_ok=True)
    open(OUT, "w", encoding="utf-8").write(svg)
    print(f"tide: busiest {busiest[0]} ({busiest[1]}), quietest {quiet[-1]} ({lo}, {len(quiet)} tied), this week {tw}, {len(svg) / 1024:.1f} KB -> {OUT}")


if __name__ == "__main__":
    main()
