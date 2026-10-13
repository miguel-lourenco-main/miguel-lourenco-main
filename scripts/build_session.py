#!/usr/bin/env python3
"""assets/session.svg — "Recent work": a finished shell session, every line real, all of it visible at once.

  contributions (hourly)  data.py's fetcher (GraphQL with GITHUB_TOKEN, else the public jogruber API), always fresh
  repos (daily)           clones of the owner's public repos -> recent commits + lines by language, cached in
                          data/session.json; rescanned when the cache is >= 20 h old (or with --clone).
                          Reuses the art clones in $ART_WORK/repos (unshallowing them), else clones there.
                          Relative times and the git-log window are recomputed from the cache on every run.

No typing reveal, no staggered output: the base state is the whole session. Motion is limited to the block
cursor blinking at the last prompt and a one-second warm highlight on the newest commit line.

Writes the plain-text fallback between <!-- SESSION:START --> and <!-- SESSION:END --> in README.md; if the
markers are missing it changes nothing and prints the block to stdout.
Usage: build_session.py [--clone|--no-clone]          (REPOS=a,b,c overrides the repo list; ART_WORK=dir)"""
import collections, datetime as dt, json, os, re, subprocess, sys, zoneinfo
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from theme import *  # noqa
import data

ROOT = os.path.dirname(HERE)
args = sys.argv[1:]
CACHE = os.path.join(ROOT, "data", "session.json")
OUT = os.path.join(ROOT, "assets", "session.svg")
README = os.path.join(ROOT, "README.md")
NOW = dt.datetime.now(dt.timezone.utc)

W, FS, CW, LH, PAD_X, COLS = TERM_W, TERM_FS, TERM_CW, TERM_LH, TERM_PAD_X, TERM_COLS
MAX_LOG, PER_REPO, MIN_LOG = 8, 3, 4
WINDOWS = (30, 90, 180, 365)       # widen the git-log window until it holds MIN_LOG commits
NOISE = re.compile(r"comment-mirror|mirror|bump infra submodule|^Merge |\[skip ci\]", re.I)
BOT = re.compile(r"\[bot\]|bot@|github-actions|dependabot|renovate", re.I)

# ---------------------------------------------------------------- contributions (hourly, never cached)
def contrib_stats():
    days = data._fetch_contributions()
    by = {dt.date.fromisoformat(d): c for d, c in days}
    today = data.today()
    total = lambda k: sum(by.get(today - dt.timedelta(days=i), 0) for i in range(k))
    return {"today": by.get(today, 0), "week": total(7), "month": total(30), "year": total(365),
            "streak": data.streak(days)}

# ---------------------------------------------------------------- repos (daily, cached)
def git(path, *a):
    return subprocess.run(["git", "-C", path, *a], capture_output=True, text=True)


def checkout(r):
    """Full-history clone, reusing (and unshallowing) the art scripts' depth-1 clone when it exists."""
    dest = os.path.join(data.WORK, "repos", r["name"])
    if not os.path.isdir(dest):
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        subprocess.run(["git", "clone", "--quiet", "--no-tags", r["clone_url"], dest], check=True)
    elif git(dest, "rev-parse", "--is-shallow-repository").stdout.strip() == "true":
        subprocess.run(["git", "-C", dest, "fetch", "--quiet", "--no-tags", "--unshallow", "origin",
                        "+refs/heads/*:refs/remotes/origin/*"], check=True)
    return dest


def mine(name, email):
    who = (name + " " + email).lower()
    return not BOT.search(who) and (data.login.lower() in who.replace(" ", "-") or data.login.split("-")[0] in name.lower())


def commits(path, repo):
    log = git(path, "log", "--all", "--no-merges", "--format=%cI|%h|%an|%ae|%s").stdout
    for line in log.splitlines():
        iso, h, name, email, subj = line.split("|", 4)
        if mine(name, email) and not NOISE.search(subj):
            yield {"repo": repo, "iso": iso, "hash": h, "subject": subj.strip()}


def scan_repos():
    langs, found, n = collections.Counter(), [], 0
    for r in data._repos():
        try: path = checkout(r)
        except subprocess.CalledProcessError: continue
        n += 1
        langs += data.loc(path)            # the hardened counter: skips public/, vendored, >4000-line files
        found += commits(path, r["name"])
    found.sort(key=lambda c: dt.datetime.fromisoformat(c["iso"]), reverse=True)
    horizon = NOW - dt.timedelta(days=max(WINDOWS))
    keep, seen = [], set()
    for c in found:                        # newest first, one per subject (rebased branches carry copies)
        if dt.datetime.fromisoformat(c["iso"]) < horizon or c["subject"].lower() in seen: continue
        seen.add(c["subject"].lower()); keep.append(c)
    out = {"generated": NOW.isoformat(timespec="seconds"), "repos": n, "commits": keep[:80], "loc": dict(langs.most_common())}
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    json.dump(out, open(CACHE, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    return out


def repo_data():
    if os.path.exists(CACHE) and "--clone" not in args:
        d = json.load(open(CACHE, encoding="utf-8"))
        if "--no-clone" in args or NOW - dt.datetime.fromisoformat(d["generated"]) < dt.timedelta(hours=20):
            return d
    return scan_repos()


def pick(all_commits):
    """(window_days, commits): the narrowest window holding MIN_LOG commits, at most PER_REPO per repo."""
    for days in WINDOWS:
        since = NOW - dt.timedelta(days=days)
        out, per = [], collections.Counter()
        for c in all_commits:
            if dt.datetime.fromisoformat(c["iso"]) < since: break
            if per[c["repo"]] >= PER_REPO: continue
            per[c["repo"]] += 1; out.append(c)
            if len(out) == MAX_LOG: break
        if len(out) >= MIN_LOG or days == WINDOWS[-1]:
            return days, out


def ago(iso):
    s = (NOW - dt.datetime.fromisoformat(iso)).total_seconds()
    m, h, d = s / 60, s / 3600, s / 86400
    return (f"{int(m)}m ago" if m < 60 else f"{int(h)}h ago" if h < 24 else f"{int(d)}d ago" if d < 14
            else f"{int(d // 7)}w ago" if d < 60 else f"{int(d // 30)}mo ago")

# ---------------------------------------------------------------- the session (lines = lists of (col, text, colour))
def runs(segs, col=0):
    """[(text, colour), ...] -> [(col, text, colour), ...]; SVG collapses edge spaces, so spaces become offsets."""
    out = []
    for text, c in segs:
        lead = len(text) - len(text.lstrip(" "))
        if text.strip(): out.append((col + lead, text.strip(" "), c))
        col += len(text)
    return out


def session(cs, rd):
    days, picked = pick(rd["commits"])
    log = []
    for c in picked:
        when = ago(c["iso"])
        room = COLS - 25 - len(when) - 3
        subj = c["subject"] if len(c["subject"]) <= room else c["subject"][:room - 1].rstrip() + "…"
        log.append([(0, c["hash"][:7], TERM_DIM), (9, c["repo"], TERM_ACCENT), (25, subj, TERM_FG),
                    (COLS - len(when), when, TERM_DIM)])
    if not log:
        log = [[(0, f"(no public commits in the last {days} days)", TERM_DIM)]]
    num = lambda label, v: [(label + " ", TERM_DIM), (v, TERM_ACCENT)]
    sep = [(" · ", TERM_DIM)]
    contrib = (num("today", str(cs["today"])) + sep + num("this week", str(cs["week"])) + sep
               + num("last 30 days", f"{cs['month']:,}") + sep + num("streak", f"{cs['streak']}d") + sep
               + [(f"{cs['year']:,}", TERM_ACCENT), (" in the last year", TERM_DIM)])
    total = sum(rd["loc"].values())
    wc = [(f"{total:,}", TERM_ACCENT), (" lines", TERM_DIM)]
    for name, v in sorted(rd["loc"].items(), key=lambda kv: -kv[1])[:5]:
        wc += sep + [(name + " ", TERM_FG), (f"{v / 1000:.1f}k", TERM_ACCENT)]
    author = data.login.split("-")[0]
    return [
        (f'git log --since="{days} days ago" --oneline --author={author}', log),
        ("contributions --today", [runs(contrib)]),
        ("wc -l --by-language ~/src", [runs(wc)]),
    ]

# ---------------------------------------------------------------- render
TOP = 40          # title bar
GAP = 10          # extra space before each prompt after the first
PROMPT_COLS = 4   # "~ $ "


def t(col, y, s, color):
    return (f'<text x="{n(PAD_X + col * CW)}" y="{y}" fill="{color}" textLength="{n(len(s) * CW)}" '
            f'lengthAdjust="spacing">{esc(s)}</text>')


def prompt(y):
    return t(0, y, "~", TERM_DIM) + t(2, y, "$", TERM_PROMPT)


def render(steps, stamp):
    y = TOP + 34
    els, first_out = [], None
    for k, (cmd, out) in enumerate(steps):
        if k: y += GAP
        els.append(prompt(y) + t(PROMPT_COLS, y, cmd, TERM_FG)); y += LH
        for line in out:
            if first_out is None: first_out = y
            els.append("".join(t(c, y, s, col) for c, s, col in line)); y += LH
    final = y + GAP
    H = final + 26
    # newest commit: one soft warm wash, base opacity 0 (= the finished state), gone after a second
    hl = (f'<rect x="{PAD_X - 10}" y="{first_out - LH + 6}" width="{W - 2 * PAD_X + 20}" height="{LH}" rx="4" '
          f'fill="{TERM_PROMPT}" opacity="0"><animate attributeName="opacity" values="0;.18;0" keyTimes="0;.3;1" '
          f'begin=".15s" dur="1s" fill="freeze"/></rect>')
    cx = PAD_X + PROMPT_COLS * CW
    cursor = (f'<rect x="{n(cx)}" y="{final - LH + 7}" width="{n(CW)}" height="{LH - 4}" fill="{TERM_FG}" opacity=".85">'
              f'<animate attributeName="opacity" calcMode="discrete" values=".85;0" keyTimes="0;.5" dur="1.06s" '
              f'repeatCount="indefinite"/></rect>')
    dots = "".join(f'<circle cx="{24 + i * 20}" cy="{TOP / 2}" r="6" fill="{c}"/>' for i, c in enumerate(TERM_DOTS))
    body = f'''<g font-family="{MONO}" font-size="{FS}">
<rect width="{W}" height="{TOP}" fill="{TERM_BAR}"/><line x1="0" y1="{TOP - .5}" x2="{W}" y2="{TOP - .5}" stroke="{LINE}"/>
{dots}
<text x="{W / 2}" y="{TOP / 2 + 4.5}" fill="{TERM_DIM}" font-size="13" text-anchor="middle">recent work — zsh</text>
<text x="{W - 24}" y="{TOP / 2 + 4.5}" fill="{TERM_DIM}" font-size="12" text-anchor="end">{esc(stamp)}</text>
{hl}
{chr(10).join(els)}
{prompt(final)}
{cursor}
</g>'''
    summary = "; ".join(f"$ {cmd}: " + " / ".join(" ".join(s for _, s, _ in line) for line in out) for cmd, out in steps)
    svg = frame(W, H, body, ("Recent work, as a shell session. " + summary).replace('"', "'"))  # esc() leaves quotes
    return H, svg.replace("<style>", f"<title>{esc(NAME)} — recent work</title>\n<style>", 1)


def plain(steps):
    rows = []
    for cmd, out in steps:
        rows.append("$ " + cmd)
        for line in out:
            s = ""
            for c, txt, _ in line:
                s = s.ljust(c) + txt
            rows.append(s)
    rows.append("$")
    return "\n".join(rows)


def update_readme(text):
    block = (f"<!-- SESSION:START -->\n<details><summary>plain text</summary>\n\n```console\n{text}\n```\n\n"
             f"</details>\n<!-- SESSION:END -->")
    md = open(README, encoding="utf-8").read() if os.path.exists(README) else ""
    if "<!-- SESSION:START -->" not in md or "<!-- SESSION:END -->" not in md:
        print("SESSION markers not found in README.md; place this block yourself:\n" + block)
        return
    new = re.sub(r"<!-- SESSION:START -->.*?<!-- SESSION:END -->", lambda _: block, md, flags=re.S)
    if new != md:
        open(README, "w", encoding="utf-8").write(new)


def main():
    cs = contrib_stats()
    rd = repo_data()
    steps = session(cs, rd)
    for cmd, out in steps:
        assert PROMPT_COLS + len(cmd) <= COLS, cmd
        for line in out:
            assert max(c + len(s) for c, s, _ in line) <= COLS, line
    stamp = NOW.astimezone(zoneinfo.ZoneInfo(TZ)).strftime("%a %d %b %Y")
    H, svg = render(steps, stamp)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, "w", encoding="utf-8").write(svg)
    update_readme(plain(steps))
    print(json.dumps({**cs, "repos": rd["repos"], "loc": sum(rd["loc"].values()), "height": H,
                      "bytes": len(svg.encode())}), "->", OUT, file=sys.stderr)


if __name__ == "__main__":
    main()
