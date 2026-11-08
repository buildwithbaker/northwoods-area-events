#!/usr/bin/env python3
"""Add a town to TOWNS in index.html from named sources (added 2026-11-08).

Scan rule 6a says a TOWNS row may only come from sources you can name: lat/lon from
the US Census 2024 Gazetteer (place file, else county-subdivision file) and `mi` from
OSRM driving distance to the Ashland anchor. This script does exactly that, the same
way every time, so a scan never hand-types coordinates or skips the lookup.

    py tools\\add-town.py "Frederic, WI" "Moose Lake, MN"           # print rows only
    py tools\\add-town.py "Frederic, WI" "Moose Lake, MN" --write   # also insert into TOWNS

Standard library only. Downloads the two Gazetteer zips once into the temp folder.
Exit 0 = every town resolved (or already present). Exit 2 = at least one town was not
found or was ambiguous - nothing is written for it, and the scan must leave `town` off
those rows and list them. Exit 1 = a network or file error; nothing is written at all.
Not handled: USGS GNIS (towns Census has neither as a place nor a county subdivision)
and ferry or ice-road routes (La Pointe) - both need a human, and the script says so.
After --write, run tools/drive-table.py (scan rule 6j).
"""
import datetime
import io
import json
import os
import re
import sys
import tempfile
import urllib.request
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
INDEX = os.path.join(HERE, "..", "index.html")
GAZ = "https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2024_Gazetteer/"
FILES = {"place": "2024_Gaz_place_national", "cousub": "2024_Gaz_cousubs_national"}
ANCHOR = (-90.871898, 46.58176)  # Ashland, WI - the TOWNS mi:0 anchor
OSRM = "https://router.project-osrm.org/route/v1/driving/{},{};{},{}?overview=false"
SUFFIX = re.compile(r"\s+(city and borough|charter township|unorganized territory|"
                    r"municipality|township|borough|village|city|town|CDP|CCD|UT)$", re.I)
UA = {"User-Agent": "northwoods-area-events add-town.py"}


def die(msg, code=1):
    print("ERROR: " + msg, file=sys.stderr)
    sys.exit(code)


def fetch(url, timeout=60):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
        return r.read()


def gazetteer(kind):
    cache = os.path.join(tempfile.gettempdir(), "nwe-gazetteer-2024")
    os.makedirs(cache, exist_ok=True)
    path = os.path.join(cache, FILES[kind] + ".txt")
    if not os.path.exists(path):
        data = fetch(GAZ + FILES[kind] + ".zip", timeout=120)
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            z.extract(FILES[kind] + ".txt", cache)
    rows = []
    with open(path, encoding="utf-8", errors="replace") as f:
        head = [h.strip() for h in f.readline().split("\t")]
        for line in f:
            rows.append(dict(zip(head, [c.strip() for c in line.split("\t")])))
    return rows


def lookup(town, st, tables):
    want = town.strip().lower()
    for kind in ("place", "cousub"):
        hits = [r for r in tables[kind]
                if r["USPS"] == st and SUFFIX.sub("", r["NAME"]).strip().lower() == want]
        if len(hits) == 1:
            r = hits[0]
            return kind, r["GEOID"], float(r["INTPTLAT"]), float(r["INTPTLONG"]), None
        if len(hits) > 1:
            return None, None, None, None, f"ambiguous in {kind} file: " + \
                "; ".join(f'{h["NAME"]} ({h["GEOID"]})' for h in hits)
    return None, None, None, None, "not in the Census 2024 place or cousub file - needs a USGS GNIS lookup by hand"


def osrm_miles(lat, lon):
    d = json.loads(fetch(OSRM.format(ANCHOR[0], ANCHOR[1], lon, lat), timeout=30))
    if d.get("code") != "Ok" or not d.get("routes"):
        raise RuntimeError(f"OSRM returned {d.get('code')}: {d.get('message', '')}")
    return round(d["routes"][0]["distance"] / 1609.344)


def main(argv):
    write = "--write" in argv
    names = [a for a in argv if not a.startswith("--")]
    if not names:
        die('usage: add-town.py "Town, ST" [...] [--write]')
    html = open(INDEX, encoding="utf-8", newline="").read()
    a = html.find("const TOWNS = {")
    b = html.find("\n};", a)
    if a < 0 or b < 0:
        die("cannot find the TOWNS block in index.html")
    existing = set(re.findall(r'^\s*"([^"]+)"\s*:\s*\{', html[a:b], re.M))
    today = datetime.date.today().isoformat()  # NEO runs on Central time
    try:
        tables = {k: gazetteer(k) for k in FILES}
    except Exception as e:
        die(f"Gazetteer download failed: {e}")
    new_rows, problems = [], []
    for key in names:
        m = re.fullmatch(r"\s*(.+?),\s*([A-Z]{2})\s*", key)
        if not m:
            problems.append(f'{key}: not in "Town, ST" form')
            continue
        town, st = m.group(1), m.group(2)
        key = f"{town}, {st}"
        if key in existing:
            print(f"ALREADY  {key}")
            continue
        kind, geoid, lat, lon, err = lookup(town, st, tables)
        if err:
            problems.append(f"{key}: {err}")
            continue
        try:
            mi = osrm_miles(lat, lon)
        except Exception as e:
            die(f"OSRM failed for {key}: {e}")
        row = f'  "{key}":{{lat:{lat},lon:{lon},mi:{mi},src:"Census 2024 Gazetteer {kind} {geoid}; OSRM {today}"}}'
        print("ADD      " + row.strip())
        new_rows.append(row)
        existing.add(key)
    if write and new_rows:
        block = html[a:b].rstrip()
        if not block.endswith(","):
            block += ","
        html = html[:a] + block + "\n" + ",\n".join(new_rows) + html[b:]
        with open(INDEX, "w", encoding="utf-8", newline="") as f:
            f.write(html)
        print(f"WROTE    {len(new_rows)} row(s) into TOWNS - now run tools/drive-table.py")
    for p in problems:
        print("NOT ADDED " + p)
    sys.exit(2 if problems else 0)


if __name__ == "__main__":
    main(sys.argv[1:])
