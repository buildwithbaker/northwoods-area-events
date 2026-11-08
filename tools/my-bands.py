#!/usr/bin/env python3
"""My Bands coverage for the weekly scan (added 2026-11-08).

The watch-list (concert-watchlist-bands.md, BANDS section, 181 acts) is too long to
search act by act every week - the 2026-11-05 run reached about 30. Two halves:

  1. VENUE SWEEP, every run. Save the text of each Duluth / Twin Cities venue calendar
     from scan-sources.md to a file, then:
         py tools\\my-bands.py match <venue-text-file> [...]
     Every act is checked against every saved venue page at once. Each hit prints with
     the line it came from - confirm the date and venue before adding a row.
  2. PER-ACT ROTATION, for shows outside those venues (tour pages, Bandsintown, Songkick):
         py tools\\my-bands.py next 40          # the 40 least recently searched acts
         py tools\\my-bands.py mark "Act" ...   # after searching them; or: mark --stdin
         py tools\\my-bands.py status           # coverage summary for the run summary
     At 40 a week every act is searched about every 5 weeks.

State lives in .my-bands-state.json beside the watch-list (gitignored, like the list).
Names match case-sensitively as written in the list, or in ALL CAPS, on word
boundaries, so short or common-word names ("Aborted", "Attila") do not match prose.
Exit 1 on any error - an unknown act name in `mark`, a missing list, an unreadable file.
"""
import datetime
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
LIST = os.path.join(ROOT, "concert-watchlist-bands.md")
STATE = os.path.join(ROOT, ".my-bands-state.json")


def die(msg):
    print("ERROR: " + msg, file=sys.stderr)
    sys.exit(1)


def acts():
    if not os.path.exists(LIST):
        die(f"watch-list not found: {LIST}")
    out, inside = [], False
    for line in open(LIST, encoding="utf-8"):
        if line.startswith("## "):
            inside = line.upper().startswith("## BANDS")
            continue
        m = re.match(r"-\s+(.+?)\s+\((\d+)\)(?:\s+\*\(.*\)\*)?\s*$", line) if inside else None
        if m:
            out.append((m.group(1), int(m.group(2))))
    if not out:
        die("no acts found under the '## BANDS' heading")
    declared = next((int(m.group(1)) for m in [re.search(r"^## BANDS.*\((\d+)\)", open(LIST, encoding="utf-8").read(), re.M)] if m), None)
    if declared is not None and declared != len(out):
        die(f"parsed {len(out)} acts but the BANDS heading says {declared} - a list line is in a format this script does not read")
    return out


def load():
    if not os.path.exists(STATE):
        return {}
    try:
        return json.load(open(STATE, encoding="utf-8"))
    except Exception as e:
        die(f"{STATE} is unreadable ({e}) - fix or delete it; it will not be overwritten")


def save(state):
    tmp = STATE + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(state, f, indent=1, sort_keys=True, ensure_ascii=False)
    os.replace(tmp, STATE)


def cmd_next(n):
    state = load()
    # never-searched first, then oldest; among equals, acts on more playlists first
    order = sorted(acts(), key=lambda a: (state.get(a[0], ""), -a[1], a[0].lower()))
    for name, _ in order[:n]:
        print(name)


def cmd_mark(names):
    known = {a for a, _ in acts()}
    unknown = [n for n in names if n not in known]
    if unknown:
        die("not on the watch-list (nothing marked): " + "; ".join(unknown))
    state = load()
    today = datetime.date.today().isoformat()  # NEO runs on Central time
    for n in names:
        state[n] = today
    save(state)
    print(f"marked {len(names)} act(s) searched on {today}")


def cmd_status():
    lst, state = acts(), load()
    today = datetime.date.today()
    dates = [state.get(a) for a, _ in lst]
    never = sum(d is None for d in dates)
    recent = sum(d is not None and (today - datetime.date.fromisoformat(d)).days <= 35 for d in dates)
    oldest = min((d for d in dates if d), default="none")
    print(f"my-bands: {len(lst)} acts | searched in the last 5 weeks: {recent} | never searched: {never} | oldest search: {oldest}")


def cmd_match(files):
    pats = []
    for name, _ in acts():
        for form in {name, name.upper()}:
            pats.append((name, re.compile(r"(?<![\w])" + re.escape(form) + r"(?![\w])")))
    hits = 0
    for path in files:
        try:
            text = open(path, encoding="utf-8", errors="replace").read()
        except OSError as e:
            die(f"cannot read {path}: {e}")
        seen = set()
        for line in text.splitlines():
            for name, rx in pats:
                if rx.search(line) and (name, line) not in seen:
                    seen.add((name, line))
                    hits += 1
                    print(f"{name} | {os.path.basename(path)} | {line.strip()[:160]}")
    print(f"match: {hits} hit(s) across {len(files)} file(s)", file=sys.stderr)


def main(a):
    if not a:
        die("usage: my-bands.py next N | mark ACT... | mark --stdin | status | match FILE...")
    c = a[0]
    if c == "next":
        cmd_next(int(a[1]) if len(a) > 1 else 40)
    elif c == "mark":
        names = [l.strip() for l in sys.stdin if l.strip()] if a[1:] == ["--stdin"] else a[1:]
        if not names:
            die("mark needs at least one act name")
        cmd_mark(names)
    elif c == "status":
        cmd_status()
    elif c == "match":
        if len(a) < 2:
            die("match needs at least one text file")
        cmd_match(a[1:])
    else:
        die(f"unknown command {c}")


if __name__ == "__main__":
    main(sys.argv[1:])
