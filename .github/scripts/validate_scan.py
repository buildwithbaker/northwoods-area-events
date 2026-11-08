#!/usr/bin/env python3
"""Gate for the weekly-scan auto-merge (added 2026-11-08).

The weekly Northwoods scan opens a PR from a branch named weekly-scan-YYYY-MM-DD.
The scan-automerge workflow runs this script and merges the PR ONLY if every check
passes. It replaces the merge the scan used to attempt itself, which the Claude
Code auto-mode classifier refuses unattended ("Merge Without Review").

It never executes anything from the PR. It reads the two index.html blobs with git
and syntax-checks the data block with `node --check`, which parses without running.

Env: BASE_SHA, HEAD_SHA, HEAD_REF. Exit 0 = safe to merge, 1 = do not merge.
"""
import datetime
import os
import re
import subprocess
import sys
import tempfile

BASE = os.environ["BASE_SHA"]
HEAD = os.environ["HEAD_SHA"]
REF = os.environ["HEAD_REF"]

MAX_SHRINK = 0.40   # same threshold as the scan's own step 5 purge check
MAX_AGE_DAYS = 14   # a scan branch older than this is stale, not this week's run
fails = []


def git(*args):
    return subprocess.run(["git", *args], capture_output=True, text=True,
                          encoding="utf-8", check=True).stdout


def split(html, label):
    """Return (pre, data, post) around the scan's data-only region."""
    i = html.find("const LAST_SCAN")
    j = html.find("// ===== render")
    if i < 0 or j < 0 or j < i:
        fails.append(f"{label}: cannot find the LAST_SCAN line and the render marker")
        return None
    i = html.rfind("\n", 0, i) + 1
    return html[:i], html[i:j], html[j:]


def last_scan(data):
    m = re.search(r'^const LAST_SCAN\s*=\s*"(\d{4}-\d{2}-\d{2})";', data, re.M)
    return m.group(1) if m else None


def event_rows(data):
    a = data.find("const EVENTS = [")
    b = data.find("const RECURRING")
    if a < 0 or b < 0:
        return None
    return len(re.findall(r"^\s*\{\s*start\s*:", data[a:b], re.M))


def drop_drive(post):
    # tools/drive-table.py is the one thing allowed to rewrite the DRIVE line
    return "\n".join(l for l in post.split("\n") if not l.startswith("const DRIVE ="))


m = re.fullmatch(r"weekly-scan-(\d{4}-\d{2}-\d{2})", REF)
if not m:
    print(f"FAIL: branch '{REF}' is not weekly-scan-YYYY-MM-DD")
    sys.exit(1)
branch_date = m.group(1)

changed = [l for l in git("diff", "--name-only", f"{BASE}...{HEAD}").splitlines() if l]
if changed != ["index.html"]:
    fails.append(f"changed files must be exactly ['index.html'], got {changed}")

base_html = git("show", f"{BASE}:index.html")
head_html = git("show", f"{HEAD}:index.html")
b = split(base_html, "base")
h = split(head_html, "head")

if b and h:
    if b[0] != h[0]:
        fails.append("page head/CSS/markup above LAST_SCAN changed - a scan edits data only")
    if drop_drive(b[2]) != drop_drive(h[2]):
        fails.append("render code below the render marker changed (other than the DRIVE line)")

    base_scan, head_scan = last_scan(b[1]), last_scan(h[1])
    if head_scan != branch_date:
        fails.append(f"LAST_SCAN {head_scan!r} does not match the branch date {branch_date}")
    if base_scan and head_scan and head_scan <= base_scan:
        fails.append(f"LAST_SCAN {head_scan} is not newer than main's {base_scan}")

    today = datetime.datetime.now(datetime.timezone.utc).date()
    try:
        d = datetime.date.fromisoformat(branch_date)
        if d > today + datetime.timedelta(days=1):
            fails.append(f"branch date {branch_date} is in the future (UTC today {today})")
        if d < today - datetime.timedelta(days=MAX_AGE_DAYS):
            fails.append(f"branch date {branch_date} is older than {MAX_AGE_DAYS} days")
    except ValueError:
        fails.append(f"branch date {branch_date} is not a real date")

    nb, nh = event_rows(b[1]), event_rows(h[1])
    if nb is None or nh is None:
        fails.append("cannot find the EVENTS block")
    elif nb and nh < nb * (1 - MAX_SHRINK):
        fails.append(f"EVENTS shrank {nb} -> {nh}, more than {int(MAX_SHRINK*100)}% - needs Adam")
    print(f"EVENTS rows: main {nb} -> PR {nh}")

    if "</script" in h[1].lower():
        fails.append("'</script' inside the data block would end the script tag early")

    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
        f.write(h[1])
        tmp = f.name
    r = subprocess.run(["node", "--check", tmp], capture_output=True, text=True)
    os.unlink(tmp)
    if r.returncode != 0:
        fails.append("data block is not valid JavaScript: " + (r.stderr.strip().splitlines() or ["?"])[-1])

if fails:
    print("FAIL - not merging:")
    for f in fails:
        print("  - " + f)
    sys.exit(1)
print(f"PASS - {REF} is safe to merge")
