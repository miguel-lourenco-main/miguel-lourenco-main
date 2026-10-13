"""Single source of truth for the data-art look. Every drawing script imports this."""
LOGIN = "miguel-lourenco-main"
NAME = "Miguel Lourenço"
TZ = "Europe/Lisbon"

INK = "#0e0f14"        # night sky / card background
INK2 = "#161822"       # slightly lifted ink (ground, haze)
INK3 = "#232634"       # faint structure: building bodies, grid
LINE = "#2c3040"       # hairlines
WINDOW = "#ffd27a"     # warm light: lit windows, the moon, highlights
PAPER = "#f5e9d0"      # warm paper: captions, labels
DIM = "#8a8577"        # muted paper for secondary text
COOL = "#6fb3ff"       # the one cool accent: this week, the current marker

SANS = "-apple-system,'Segoe UI',Helvetica,Arial,sans-serif"
SERIF = "Georgia,'Iowan Old Style','Times New Roman',serif"
MONO = "ui-monospace,'SF Mono',Menlo,Consolas,'Liberation Mono',monospace"

REDUCED_MOTION = "@media (prefers-reduced-motion: reduce){*{animation:none!important}}"
RADIUS = 12

# ---- terminal "recent work" panel (build_session.py). Namespaced TERM_* so the draw_*.py star-imports are untouched.
# The panel itself uses INK / LINE / RADIUS like the artworks; the warm terminal palette lives inside it.
TERM_BG = "#1b1b1b"       # the terminal variant's own body colour (kept for reference; the panel uses INK)
TERM_BAR = "#14151c"      # title bar, a step above INK
TERM_FG = "#e6e1cf"       # default text
TERM_PROMPT = "#f29e74"   # prompt glyph, newest-commit highlight
TERM_DIM = "#7f7b72"      # secondary text (hashes, times, separators)
TERM_ACCENT = "#95e6cb"   # repo names, numbers
TERM_DOTS = ("#f28779", "#ffd173", "#95e6cb")
# character grid: every <text> carries textLength=len*TERM_CW, so columns hold in any monospace font
TERM_W = 1200
TERM_FS = 15
TERM_CW = 9.0             # 0.6em
TERM_LH = 23
TERM_PAD_X = 36
TERM_COLS = int((TERM_W - 2 * TERM_PAD_X) // TERM_CW)   # 125


def reveal(attr: str, frm, to, begin: float, dur: float, spline: str = ".2 .7 .3 1") -> str:
    """SMIL entrance that starts at load time and holds `frm` until `begin`, then eases to `to`.
    The element's own attribute must already be the final value: renderers without SMIL show the finished picture,
    and with SMIL there is no flash of the final state before the animation starts."""
    total = begin + dur
    k = begin / total if total else 0
    return (f'<animate attributeName="{attr}" values="{frm};{frm};{to}" keyTimes="0;{k:.3f};1" dur="{total:.2f}s" '
            f'begin="0.05s" fill="freeze" calcMode="spline" keySplines="0 0 1 1;{spline}"/>')


def fade(begin: float, dur: float = 0.8) -> str:
    """Fade-in for an element that is fully opaque by default (see reveal)."""
    return reveal("opacity", 0, 1, begin, dur, ".4 0 .6 1")


def esc(s) -> str:
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def frame(w: int, h: int, body: str, label: str, style: str = "", defs: str = "") -> str:
    """Self-contained card: own dark background and rounded corners, so it reads in both GitHub themes."""
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{esc(label)}">
<style>{style}{REDUCED_MOTION}</style>
<defs><clipPath id="card"><rect width="{w}" height="{h}" rx="{RADIUS}"/></clipPath>{defs}</defs>
<g clip-path="url(#card)">
<rect width="{w}" height="{h}" fill="{INK}"/>
{body}
</g>
<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="{RADIUS}" fill="none" stroke="{LINE}"/>
</svg>
'''


def n(x: float) -> str:
    """Compact number for SVG coordinates."""
    s = f"{x:.1f}"
    return s[:-2] if s.endswith(".0") else s
