#!/usr/bin/env python3
"""assets/skyline.svg — a city built from the last 365 days of contributions.

One building per day (oldest on the left, today on the right). Height = sqrt(contributions), so a single huge day
does not flatten the rest. Every lit window is one contribution (windows fill a building's floors at random,
seeded by the date). Zero days are empty lots. The moon's phase is the current streak: a sliver for one day,
full at 30 days. Usage: draw_skyline.py [out]"""
import datetime as dt, math, os, random, sys
sys.path.insert(0, os.path.dirname(__file__))
from theme import *  # noqa
import data

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "..", "assets", "skyline.svg")
W, H = 1200, 360
X0, X1 = 36, 1164            # street extent
GROUND = 292                 # y of the street
MAXH = 204                   # tallest building
FLOOR = 4.0                  # floor pitch (px)
WIN_H = 1.8                  # window height
FULL_MOON_STREAK = 30


def moon(cx, cy, r, k):
    """Lit part of a disk with illuminated fraction k (0..1), waxing (lit on the right)."""
    rx = r * abs(1 - 2 * k)
    sweep = 0 if k < .5 else 1
    return (f'<circle cx="{n(cx)}" cy="{n(cy)}" r="{n(r)}" fill="{INK2}" stroke="{LINE}" stroke-width=".8"/>'
            f'<path d="M{n(cx)} {n(cy - r)}A{n(r)} {n(r)} 0 0 1 {n(cx)} {n(cy + r)}A{n(rx)} {n(r)} 0 0 {sweep} {n(cx)} {n(cy - r)}Z" fill="{WINDOW}"/>')


def main():
    days = data.contributions()
    year = data.series(days, 365)
    streak = data.streak(days)
    total = sum(c for _, c in year)
    peak_day, peak = max(year, key=lambda t: (t[1], t[0]))
    peak = peak or 1
    step = (X1 - X0) / len(year)
    bw = step - .52            # ~2.6 px building, ~0.5 px alley

    # ---- buildings, grouped by ISO week so each week can rise on its own (staggered SMIL clip) ----
    weeks, order = {}, []
    for i, (d, c) in enumerate(year):
        key = d - dt.timedelta(days=d.weekday())
        if key not in weeks: weeks[key] = []; order.append(key)
        weeks[key].append((i, d, c))
    defs, groups, twinkles = [], [], []
    rng_tw = random.Random(f"twinkle-{year[-1][0]}")
    for wi, key in enumerate(order):
        members = weeks[key]
        gx0 = X0 + members[0][0] * step - .3
        gx1 = X0 + members[-1][0] * step + bw + .3
        begin = .15 + wi * .035
        top = GROUND - MAXH - 30
        defs.append(f'<clipPath id="w{wi}"><rect x="{n(gx0)}" y="{top}" width="{n(gx1 - gx0)}" height="{MAXH + 30}">'
                    + reveal("y", GROUND, top, begin, .9) + '</rect></clipPath>')  # the rect slides up; below the street there is nothing to show
        bodies, dark, lit = [], [], []
        for i, d, c in members:
            if c == 0: continue
            h = max(7.0, MAXH * math.sqrt(c / peak))
            x = X0 + i * step
            bodies.append(f"M{n(x)} {GROUND}v-{n(h)}h{n(bw)}v{n(h)}z")
            floors = int((h - 3) // FLOOR)
            wx = x + bw / 2
            dark.append(f"M{n(wx)} {n(GROUND - 2)}v-{n(floors * FLOOR)}")
            rng = random.Random(d.isoformat())
            on = sorted(rng.sample(range(floors), min(c, floors)))
            runs, start, prev = [], None, None
            for f in on:
                if start is None: start = prev = f
                elif f == prev + 1: prev = f
                else: runs.append((start, prev)); start = prev = f
            if start is not None: runs.append((start, prev))
            for a, b in runs:
                lit.append(f"M{n(wx)} {n(GROUND - 2 - a * FLOOR)}v-{n((b - a + 1) * FLOOR)}")
            if on and rng_tw.random() < .05 and len(twinkles) < 18:
                f = rng_tw.choice(on)
                twinkles.append(f'<rect class="tw" style="animation-delay:{rng_tw.uniform(0, 6):.1f}s;animation-duration:{rng_tw.uniform(3, 7):.1f}s" '
                                f'x="{n(x + .3)}" y="{n(GROUND - 2 - (f + 1) * FLOOR + (FLOOR - WIN_H))}" width="{n(bw - .6)}" height="{WIN_H}" fill="#fff4d6"/>')
        if not bodies: continue
        dash = f'stroke-dasharray="{WIN_H} {FLOOR - WIN_H}" stroke-width="{n(bw - .9)}"'
        groups.append(f'<g clip-path="url(#w{wi})"><path d="{"".join(bodies)}" fill="url(#bld)"/>'
                      f'<path d="{"".join(dark)}" stroke="#1b1d27" {dash} fill="none"/>'
                      + (f'<path d="{"".join(lit)}" stroke="{WINDOW}" {dash} fill="none"/>' if lit else "") + "</g>")

    # today: a cool beacon on the last building (or the street if today is empty)
    tc = year[-1][1]
    th = max(7.0, MAXH * math.sqrt(tc / peak)) if tc else 0
    tx = X0 + (len(year) - 1) * step + bw / 2
    beacon = (f'<g>{fade(2.2)}<line x1="{n(tx)}" y1="{n(GROUND - th)}" x2="{n(tx)}" y2="{n(GROUND - 150)}" stroke="{COOL}" stroke-width=".8" stroke-dasharray="2 2"/>'
              f'<circle class="pulse" cx="{n(tx)}" cy="{n(GROUND - 151)}" r="2.2" fill="{COOL}"/>'
              f'<text x="{n(tx + 2)}" y="{n(GROUND - 160)}" font-family="{MONO}" font-size="12" fill="{COOL}" text-anchor="end">today · {tc}</text></g>')

    # tallest day: a small warm tag above the roof
    pi = next(i for i, (d, _) in enumerate(year) if d == peak_day)
    px = X0 + pi * step + bw / 2
    peak_tag = (f'<g>{fade(2.0)}<line x1="{n(px)}" y1="{GROUND - MAXH - 2}" x2="{n(px)}" y2="{GROUND - MAXH - 12}" stroke="{DIM}" stroke-width=".8"/>'
                f'<text x="{n(px)}" y="{GROUND - MAXH - 17}" font-family="{MONO}" font-size="12" fill="{PAPER}" text-anchor="middle">{peak_day:%d %b} · {peak}</text></g>')

    # month street signs on the pavement
    signs = []
    for i, (d, _) in enumerate(year):
        if d.day == 1 or (i == 0 and d.day < 20):
            x = X0 + i * step
            lbl = d.strftime("%b").upper() + (f" {d:%y}" if d.month == 1 or i == 0 else "")
            wdt = 8 + 7.2 * len(lbl)
            signs.append(f'<line x1="{n(x)}" y1="{GROUND}" x2="{n(x)}" y2="{GROUND + 9}" stroke="{DIM}" stroke-width=".8"/>'
                         f'<rect x="{n(x)}" y="{GROUND + 9}" width="{n(wdt)}" height="15" rx="2" fill="{INK3}" stroke="{LINE}" stroke-width=".6"/>'
                         f'<text x="{n(x + 4)}" y="{GROUND + 20.5}" font-family="{MONO}" font-size="11" fill="{PAPER}" letter-spacing=".4">{lbl}</text>')

    # sky: a few faint stars, deterministic per day
    srng = random.Random(f"sky-{year[-1][0]}")
    stars = "".join(f'<circle cx="{n(srng.uniform(20, W - 20))}" cy="{n(srng.uniform(14, 120))}" r="{srng.choice([.5, .6, .8, 1])}" fill="{PAPER}" opacity="{srng.uniform(.15, .5):.2f}"/>' for _ in range(60))

    k = .06 + .94 * min(streak, FULL_MOON_STREAK) / FULL_MOON_STREAK
    mx, my, mr = 96, 62, 20
    moon_g = (f'<g>{fade(.4, 1.6)}<circle cx="{mx}" cy="{my}" r="{mr + 16}" fill="url(#glow)"/>{moon(mx, my, mr, k)}'
              f'<text x="{mx + mr + 12}" y="{my + 4}" font-family="{MONO}" font-size="12" fill="{DIM}">moon = streak · {streak} day{"s" if streak != 1 else ""}</text></g>')

    caption = (f'<text x="{X0}" y="{H - 20}" font-family="{MONO}" font-size="15" fill="{PAPER}">{total:,} contributions'
               f'<tspan fill="{DIM}"> · </tspan>tallest day {peak_day.isoformat()} ({peak})</text>'
               f'<text x="{X1}" y="{H - 20}" font-family="{MONO}" font-size="13" fill="{DIM}" text-anchor="end">one building per day · {year[0][0]:%d %b %Y} → {year[-1][0]:%d %b %Y}</text>')

    style = (".tw{animation:tw 5s ease-in-out infinite;opacity:0}@keyframes tw{0%,100%{opacity:0}45%,55%{opacity:1}}"
             ".pulse{animation:pl 2.4s ease-in-out infinite}@keyframes pl{0%,100%{opacity:1}50%{opacity:.25}}")
    defs_s = (f'<linearGradient id="sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{INK}"/><stop offset=".6" stop-color="#12141c"/><stop offset="1" stop-color="#26212a"/></linearGradient>'
              f'<linearGradient id="bld" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#3b4057"/><stop offset="1" stop-color="#252837"/></linearGradient>'
              f'<radialGradient id="glow"><stop offset="0" stop-color="{WINDOW}" stop-opacity=".18"/><stop offset="1" stop-color="{WINDOW}" stop-opacity="0"/></radialGradient>'
              + "".join(defs))
    body = (f'<rect width="{W}" height="{GROUND}" fill="url(#sky)"/>{stars}{moon_g}'
            f'<rect y="{GROUND}" width="{W}" height="{H - GROUND}" fill="{INK}"/>'
            f'<line x1="{X0 - 12}" y1="{GROUND + .5}" x2="{X1 + 12}" y2="{GROUND + .5}" stroke="{LINE}"/>'
            + "".join(groups) + "".join(twinkles) + peak_tag + beacon + "".join(signs) + caption)
    label = (f"A city skyline: one building per day over the last 365 days, height by contributions. {total:,} contributions; "
             f"tallest day {peak_day.isoformat()} with {peak}; current streak {streak} day(s), shown as the moon's phase.")
    svg = frame(W, H, body, label, style, defs_s)
    os.makedirs(os.path.dirname(os.path.abspath(OUT)), exist_ok=True)
    open(OUT, "w", encoding="utf-8").write(svg)
    print(f"skyline: {total} contributions, peak {peak_day} ({peak}), streak {streak}, {len(svg) / 1024:.1f} KB -> {OUT}")
    return {"total": total, "peak_day": peak_day.isoformat(), "peak": peak, "streak": streak}


if __name__ == "__main__":
    main()
