#!/usr/bin/env python3
"""Compose the Work grid cards: a real screenshot of each live product inside a browser-window frame in the
profile's palette, saved as WebP. Needs Pillow (`pip install pillow`); screenshots come from capture_screenshots.sh.
Usage: make_work_cards.py [screenshots-dir] [out-dir]"""
import os, sys
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.dirname(__file__))
from theme import INK, LINE, WINDOW, PAPER, DIM, COOL, TERM_BAR  # noqa

SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "..", "data", "screenshots")
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(__file__), "..", "assets", "work")
W, H, BAR, R = 960, 600, 44, 22
PROJECTS = [  # slug, url shown in the bar, screenshot file (None = designed placeholder)
    ("o-guardanapo", "o-guardanapo.site", "o-guardanapo.png"),
    ("job-hunt-hub", "job-hunt-hub · demo soon", None),
    ("agentic-hub", "agentichub-64abdc.gitlab.io", "agentic-hub.png"),
    ("sonora", "sonora-d09e63.gitlab.io", "sonora.png"),
    ("ui-components", "ui-components-5218c2.gitlab.io", "ui-components.png"),
    ("claude-skills", "claude-skills · private", None),
]
PLACEHOLDER_TEXT = {
    "job-hunt-hub": ("demo soon", "AI-augmented job-search workspace · source on request"),
    "claude-skills": ("private", "a marketplace of Claude Code plugins and skills · 16 plugins"),
}


def font(size, mono=True, bold=False):
    for p in ([f"/usr/share/fonts/truetype/dejavu/DejaVuSansMono{'-Bold' if bold else ''}.ttf"] if mono else
              [f"/usr/share/fonts/truetype/dejavu/DejaVuSans{'-Bold' if bold else ''}.ttf"]):
        if os.path.exists(p): return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def rounded_mask(size, r):
    m = Image.new("L", size, 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, size[0] - 1, size[1] - 1), r, fill=255); return m


def placeholder(slug="job-hunt-hub"):
    im = Image.new("RGB", (W, H), INK); d = ImageDraw.Draw(im)
    # a sparse grid of "windows" like the skyline, mostly unlit
    import random; rng = random.Random(42)
    for gx in range(24, W - 24, 18):
        for gy in range(40, H - 40, 18):
            if rng.random() < 0.10: d.rectangle((gx, gy, gx + 7, gy + 7), fill=WINDOW if rng.random() < 0.7 else COOL)
            else: d.rectangle((gx, gy, gx + 7, gy + 7), fill="#171923")
    f1, f2 = font(44, mono=True, bold=True), font(20, mono=True)
    big, small = PLACEHOLDER_TEXT.get(slug, ("", ""))
    tw = max(d.textlength(big, font=f1), d.textlength(small, font=f2)) + 80
    d.rounded_rectangle((W / 2 - tw / 2, H / 2 - 78, W / 2 + tw / 2, H / 2 + 62), 16, fill=INK, outline=LINE, width=2)
    d.text((W / 2, H / 2 - 30), big, fill=PAPER, font=f1, anchor="mm")
    d.text((W / 2, H / 2 + 22), small, fill=DIM, font=f2, anchor="mm")
    return im


def card(slug, url, shot):
    canvas = Image.new("RGB", (W, H + BAR), INK)
    d = ImageDraw.Draw(canvas)
    d.rectangle((0, 0, W, BAR), fill=TERM_BAR)
    for i, c in enumerate(("#ff5f57", "#febc2e", "#28c840")):
        d.ellipse((18 + i * 20, BAR / 2 - 6, 30 + i * 20, BAR / 2 + 6), fill=c)
    d.text((W / 2, BAR / 2), url, fill=DIM, font=font(15), anchor="mm")
    if shot and os.path.exists(os.path.join(SRC, shot)):
        im = Image.open(os.path.join(SRC, shot)).convert("RGB")
        im = im.resize((W, round(im.height * W / im.width)), Image.LANCZOS).crop((0, 0, W, H))
    else:
        im = placeholder(slug)
    canvas.paste(im, (0, BAR))
    d.line((0, BAR, W, BAR), fill=LINE)
    out = Image.new("RGBA", canvas.size, (0, 0, 0, 0)); out.paste(canvas, (0, 0), rounded_mask(canvas.size, R))
    ImageDraw.Draw(out).rounded_rectangle((0, 0, W - 1, H + BAR - 1), R, outline=LINE, width=2)
    return out


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for slug, url, shot in PROJECTS:
        p = os.path.join(OUT, f"{slug}.webp"); card(slug, url, shot).save(p, "WEBP", quality=82, method=6)
        print(slug, os.path.getsize(p) // 1024, "KB")
