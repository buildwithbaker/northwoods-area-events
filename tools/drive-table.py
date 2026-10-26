#!/usr/bin/env python3
"""Rebuild the DRIVE table in index.html: OSRM driving miles from every home town to every TOWNS key.

Run from the repo root after the weekly scan adds towns:  python tools/drive-table.py
Standard library only (Windows or Linux). Needs network access to router.project-osrm.org.

What it reads:  HOMES (the pickable home towns, hand-kept in the drive block) and TOWNS (scan-owned).
What it writes: only the single `const DRIVE = ...;` line inside the drive block. Nothing else in the
file changes, so the scan's data section and the render code stay byte-identical.

Failure is loud: any OSRM error, a missing marker, or an unparseable block exits non-zero with the
reason and leaves index.html untouched. A town OSRM cannot route to is stored as null and listed.
"""
import json, os, re, sys, time, urllib.request
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, "index.html")
OSRM = "https://router.project-osrm.org/table/v1/driving/"
BATCH = 5          # home towns per request; with ~95 towns that stays near the server's 100-coordinate limit
M_PER_MI = 1609.344


def die(msg):
    print("drive-table: FAILED - " + msg, file=sys.stderr)
    sys.exit(1)


def towns_from(src):
    try:
        block = src[src.index("const TOWNS = {"):src.index("const EVENTS = [")]
    except ValueError:
        die("could not find the TOWNS block")
    rows = re.findall(r'"([^"]+, [A-Z]{2})":\{lat:([-\d.]+),lon:([-\d.]+)', block)
    if not rows:
        die("TOWNS block parsed to zero towns")
    return [(k, float(a), float(b)) for k, a, b in rows]


def homes_from(src):
    m = re.search(r"const HOMES = (\[.*?\]);\s*\n", src, re.S)
    if not m:
        die("could not find `const HOMES = [...]`")
    try:
        groups = json.loads(m.group(1))
    except json.JSONDecodeError as e:
        die("HOMES is not valid JSON: %s" % e)
    homes = [(k, la, lo) for _, rows in groups for k, la, lo in rows]
    if len({k for k, _, _ in homes}) != len(homes):
        die("HOMES lists a town twice")
    return homes


def table(homes, towns):
    """Miles matrix: one list per home, in towns order."""
    out = {}
    for i in range(0, len(homes), BATCH):
        chunk = homes[i:i + BATCH]
        coords = [(lo, la) for _, la, lo in chunk] + [(lo, la) for _, la, lo in towns]
        url = (OSRM + ";".join("%.6f,%.6f" % c for c in coords)
               + "?annotations=distance&sources=" + ";".join(str(j) for j in range(len(chunk)))
               + "&destinations=" + ";".join(str(j) for j in range(len(chunk), len(coords))))
        for attempt in range(3):
            try:
                with urllib.request.urlopen(url, timeout=60) as r:
                    data = json.load(r)
                break
            except Exception as e:  # network blip or rate limit: back off, then fail loudly
                if attempt == 2:
                    die("OSRM request for %s failed: %s" % (chunk[0][0], e))
                time.sleep(5 * (attempt + 1))
        if data.get("code") != "Ok":
            die("OSRM answered %r for %s" % (data.get("code"), chunk[0][0]))
        for (k, _, _), row in zip(chunk, data["distances"]):
            out[k] = [None if d is None else round(d / M_PER_MI) for d in row]
        time.sleep(1)  # be polite to the public demo server
    return out


def main():
    src = open(PAGE, encoding="utf-8").read()
    towns, homes = towns_from(src), homes_from(src)
    line = re.search(r"^const DRIVE = .*;$", src, re.M)
    if not line:
        die("could not find the `const DRIVE = ...;` line")
    mi = table(homes, towns)
    drive = {"built": date.today().isoformat(), "src": "OSRM router.project-osrm.org, driving",
             "to": [k for k, _, _ in towns], "mi": mi}
    new = "const DRIVE = " + json.dumps(drive, separators=(",", ":")) + ";"
    if "</script" in new or "<!--" in new:
        die("generated DRIVE contains a sequence that would end the page script")
    out = src[:line.start()] + new + src[line.end():]
    tmp = PAGE + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="") as f:
        f.write(out)
    os.replace(tmp, PAGE)
    nulls = sorted({(h, towns[j][0]) for h, row in mi.items() for j, v in enumerate(row) if v is None})
    print("drive-table: wrote %d home towns x %d towns (%d bytes)" % (len(mi), len(towns), len(new)))
    if nulls:
        print("drive-table: no road route for %d pairs, shown as straight-line: %s"
              % (len(nulls), "; ".join("%s -> %s" % p for p in nulls[:10])))


if __name__ == "__main__":
    main()
