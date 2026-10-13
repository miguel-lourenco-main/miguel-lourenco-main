#!/usr/bin/env python3
"""Stamps the time of the last redraw into README.md between <!-- REDRAW:START --> and <!-- REDRAW:END -->.
Plain text, so it can never render as a broken image. Usage: update_colophon.py [readme]"""
import datetime as dt, os, re, sys

README = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "..", "README.md")
stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
text = open(README, encoding="utf-8").read()
new, count = re.subn(r"(<!-- REDRAW:START -->).*?(<!-- REDRAW:END -->)", lambda m: m.group(1) + stamp + m.group(2), text, flags=re.S)
if not count:
    raise SystemExit("REDRAW markers not found in " + README)
if new != text:
    open(README, "w", encoding="utf-8").write(new)
print("colophon:", stamp)
