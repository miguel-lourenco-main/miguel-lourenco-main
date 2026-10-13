#!/usr/bin/env python3
"""Data for the artworks. Everything is the owner's own public data.

contributions()  -> [(date, count)] for roughly the last 80 weeks (GraphQL with GITHUB_TOKEN, else the public
                    jogruber contributions API).
repo_stars()     -> [{name, loc, lang, langs, last}] for public, non-fork repos (API, or REPOS=a,b,c override), lines of code
                    counted on shallow clones with the same counter as the signature variant's rhythm card.
Results are cached per run in $ART_WORK (default /tmp/data-art-work) so the three drawings share one fetch."""
import collections, datetime as dt, json, os, subprocess, sys, urllib.request, zoneinfo
sys.path.insert(0, os.path.dirname(__file__))
from theme import LOGIN, TZ

login = os.environ.get("LOGIN") or LOGIN
WORK = os.environ.get("ART_WORK") or "/tmp/data-art-work"
TOKEN = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")

LANGS = {".ts": "TypeScript", ".tsx": "TypeScript", ".js": "JavaScript", ".jsx": "JavaScript", ".mjs": "JavaScript",
         ".py": "Python", ".ml": "OCaml", ".mli": "OCaml", ".css": "CSS", ".scss": "CSS", ".html": "HTML",
         ".sql": "SQL", ".sh": "Shell", ".go": "Go", ".rs": "Rust"}
SKIP_DIRS = {"node_modules", ".git", "dist", "build", ".next", "out", "coverage", "vendor", "_build", ".turbo", "public", "static", "generated", "__generated__"}
SKIP_FILES = ("lock", ".min.", "-lock.", ".map", ".worker.", "worker.", "vendor", "bundle", ".chunk.", "polyfill")
MAX_FILE_LINES = 4000  # hand-written source files are never this long; above it, it is generated or vendored
COUNTED = {"TypeScript", "JavaScript", "Python", "OCaml", "CSS", "HTML", "SQL", "Shell", "Go", "Rust"}


def today():
    return dt.datetime.now(zoneinfo.ZoneInfo(TZ)).date()


def _get(url, data=None, headers=None):
    h = {"User-Agent": "data-art", **(headers or {})}
    req = urllib.request.Request(url, data=data, headers=h)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def _cached(name, fn):
    os.makedirs(WORK, exist_ok=True)
    path = os.path.join(WORK, name + ".json")
    if os.path.exists(path) and os.environ.get("ART_CACHE", "1") == "1":
        return json.load(open(path))
    val = fn()
    json.dump(val, open(path, "w"))
    return val


def _graphql(frm, to):
    q = """query($login:String!,$from:DateTime!,$to:DateTime!){ user(login:$login){
             contributionsCollection(from:$from,to:$to){ contributionCalendar{ weeks{ contributionDays{ date contributionCount } } } } } }"""
    body = json.dumps({"query": q, "variables": {"login": login, "from": frm.isoformat() + "T00:00:00Z", "to": to.isoformat() + "T23:59:59Z"}}).encode()
    weeks = _get("https://api.github.com/graphql", body, {"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json"})[
        "data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    return [(d["date"], d["contributionCount"]) for w in weeks for d in w["contributionDays"]]


def _fetch_contributions():
    t = today()
    if TOKEN:  # a collection may span at most one year: ask for two windows
        a = t - dt.timedelta(days=364)
        days = dict(_graphql(a, t))
        days.update(dict(_graphql(a - dt.timedelta(days=364), a - dt.timedelta(days=1))))
    else:
        raw = _get(f"https://github-contributions-api.jogruber.de/v4/{login}?y=all")["contributions"]
        days = {d["date"]: d["count"] for d in raw}
    return sorted((d, c) for d, c in days.items() if d <= t.isoformat())


def contributions():
    """All known days up to today, oldest first; days before the account existed are simply absent (= 0)."""
    return [tuple(x) for x in _cached("contributions", _fetch_contributions)]


def series(days, n_days, end=None):
    """Exactly n_days counts ending at `end` (default today), zero-filled."""
    end = end or today()
    by = {dt.date.fromisoformat(d): c for d, c in days}
    return [(end - dt.timedelta(days=i), by.get(end - dt.timedelta(days=i), 0)) for i in range(n_days - 1, -1, -1)]


def streak(days):
    t = today()
    by = {dt.date.fromisoformat(d): c for d, c in days}
    cur, cursor = 0, t if by.get(t, 0) > 0 else t - dt.timedelta(days=1)
    while by.get(cursor, 0) > 0:
        cur += 1; cursor -= dt.timedelta(days=1)
    return cur


def _repos():
    if os.environ.get("REPOS"):
        return [{"name": n, "clone_url": f"https://github.com/{login}/{n}.git"} for n in os.environ["REPOS"].split(",") if n]
    out, page = [], 1
    hdr = {"Authorization": f"bearer {TOKEN}"} if TOKEN else {}
    while True:
        batch = _get(f"https://api.github.com/users/{login}/repos?per_page=100&type=owner&page={page}", headers=hdr)
        out += [r for r in batch if not r["fork"] and not r["archived"] and r["name"].lower() != login.lower()]
        if len(batch) < 100: return out
        page += 1


def loc(path):
    counts = collections.Counter()
    for root, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            lang = LANGS.get(os.path.splitext(f)[1].lower())
            if not lang or lang not in COUNTED or any(k in f for k in SKIP_FILES): continue
            try:
                with open(os.path.join(root, f), "rb") as fh:
                    n_lines = sum(1 for line in fh if line.strip())
                    if n_lines <= MAX_FILE_LINES: counts[lang] += n_lines
            except OSError: pass
    return counts


def _fetch_repo_stars():
    root = os.path.join(WORK, "repos")
    os.makedirs(root, exist_ok=True)
    stars = []
    for r in _repos():
        dest = os.path.join(root, r["name"])
        if not os.path.isdir(dest):
            try:
                subprocess.run(["git", "clone", "--quiet", "--no-tags", "--depth", "1", r["clone_url"], dest], check=True)
            except subprocess.CalledProcessError:
                continue
        c = loc(dest)
        if not c: continue
        last = subprocess.run(["git", "-C", dest, "log", "-1", "--format=%cI"], capture_output=True, text=True).stdout.strip()
        stars.append({"name": r["name"], "loc": sum(c.values()), "lang": c.most_common(1)[0][0], "langs": dict(c), "last": last})
    return stars


def repo_stars():
    return _cached("repos", _fetch_repo_stars)


if __name__ == "__main__":
    days = contributions()
    s = repo_stars()
    print(json.dumps({"days": len(days), "last365": sum(c for _, c in series(days, 365)), "streak": streak(days),
                      "repos": s}, indent=1))
