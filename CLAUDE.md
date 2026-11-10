# CLAUDE.md - northwoods-area-events

A live, always-current list of events across the Northwoods, for anyone in the area: northern
Wisconsin, the western U.P., Duluth and the Arrowhead (the county list lives in `scan-sources.md`,
"Coverage area"). Each reader picks a home town and sees real drive miles from it. TOWNS `mi` is
still measured from Ashland, WI, and is the fallback when no home town is set.

## Structure
- `index.html` is the whole app - single file, no build step. Event data lives inline in
  the `EVENTS` and `RECURRING` arrays, with `LAST_SCAN` holding the refresh date. The file
  also carries the `cowork-artifact-meta` block that keeps the Cowork artifact
  (id `northwoods-area-events`) in sync.
- `scan-sources.md` is **gitignored and local-only** - it is the source of truth for the
  weekly scan and deliberately never committed. The watch-list `.md`/`.json` files hold the
  concert and YouTube artist lists.

## The weekly scan
The weekly scheduled task re-fetches every source in `scan-sources.md`, drops past events,
refreshes the arrays, sets `LAST_SCAN`, and updates the Cowork artifact from `index.html`.
**A scan edits data only**: `LAST_SCAN`, `EVENTS`, `RECURRING` and `TOWNS`. It never touches
the page head, the CSS, the markup or anything below the `// ===== render` line, and it keeps
the category set and `CATMETA` as they are. Do not redesign the page during a scan. `My Bands`
(touring acts from Adam's watch-list) is a distinct category from `Concert` (local venue shows).

Categories: Festival, Concert, My Bands, Theater, Convention, Local, Classes & Talks,
Outdoors & Fitness, Family & Kids, Community, Water Park, Gaming, Fishing, Zoo, Beach, Casino.
For what used to be one big "Local" bucket:
- `Classes & Talks` - classes, workshops, lectures, author events, book clubs, Science on Tap.
- `Outdoors & Fitness` - hikes, runs and walks, bike and ATV rides, ski and fat-bike events, yoga
  and exercise classes, open skate, trap shooting.
- `Family & Kids` - story times, kids' and teen programs, trunk-or-treats, family days.
- `Community` - farmers markets and craft markets, community meals and fundraiser dinners,
  support groups, public meetings, blood drives, clinics and food pantries.
- `Local` - only what fits none of these (exhibits, parades, haunted attractions, spectator
  sports, parties). When a row fits two, it stays `Local`.

### Data shape (names and shape are fixed; the render code depends on them)
- `LAST_SCAN = "YYYY-MM-DD"` - the scan date.
- `EVENTS` - one object per line: `start`, optional `end`, optional `dates`, `title`, `place`,
  optional `town`, `region`, `cat`, `url`, `desc`.
  - `dates:["YYYY-MM-DD", ...]` - for an event that happens on separate days (a monthly group,
    a weekly class). Sorted, past days trimmed each scan, and `start` must equal `dates[0]` and
    `end` must equal the last date. A continuous run (an exhibit, a festival) has no `dates`.
    Only list dates read off the source; never compute them from "first Friday" prose.
  - `desc` - 1-2 sentences for readers. No scan bookkeeping ("Recurring listing: ...",
    "after four blank scans") and no mileage - distance comes from `TOWNS`.
  - `url` - the event's own page, `https:` only. The page renders any other scheme without a
    link. A monthly calendar page is a fallback; roll it to the current month each scan.
  - optional `time`: "HH:MM" or "HH:MM-HH:MM", 24-hour, local Central time (America/Chicago). Only a time
    read off the source; never guessed and never parsed out of prose. Left off when unknown, and on a `dates`
    event whose dates have different times. On a span it means daily hours. The weekly scan starts writing
    `time` only when its prompt includes that step (scan prompt draft 3, applied by Adam); until then it leaves
    the field off.
- `RECURRING` - weekly rows: `day`, `title`, `place`, optional `town`, `region`, `cat`,
  optional `url`, optional `seasonStart` / `seasonEnd`, `note`, optional `time` (same format and rules as on
  `EVENTS`; the day is `day`, so `time` is the time on that day).
- `TOWNS` - keyed `"Town, ST"`: `{lat, lon, mi, src}`. `lat`/`lon` from the US Census Gazetteer
  (USGS GNIS populated place where Census has none), `mi` = OSRM driving miles from Ashland, WI,
  `src` names both and says when the route uses a ferry or a seasonal ice road. `town` on a row must be a key
  here. A town that cannot be sourced is left off the row (it sorts last as "distance unknown");
  never guess a town, coordinates or miles.
- No `</script` and no `<!--` anywhere in the data - either one ends the page's script.

### Home towns and the drive table (render side - the scan never edits it)
- Just below the `// ===== render` line sit two constants: `HOMES` (the pickable home towns, grouped by
  area, `[name, lat, lon]`, hand-kept; a shared key must match its `TOWNS` key exactly) and `DRIVE`
  (OSRM driving miles from every home town to every `TOWNS` key, with the build date and source).
- `tools/drive-table.py` rebuilds the single `const DRIVE = ...;` line from `HOMES` + `TOWNS`. Run it
  from the repo root after any scan that adds or changes a `TOWNS` key (`python tools\drive-table.py`
  on Windows, `python3 tools/drive-table.py` elsewhere), then stage `index.html`. Standard library only.
  It fails loud: any OSRM error or missing marker exits non-zero and leaves the file untouched.
- `tools/add-town.py "Town, ST" [...] --write` adds `TOWNS` rows from named sources only: Census 2024
  Gazetteer place file, else county-subdivision file, plus OSRM miles to the Ashland anchor, with both
  in `src`. Exit 2 lists any town it could not resolve (GNIS-only, ambiguous) - leave `town` off those
  rows. Run `tools/drive-table.py` after it. Added 2026-11-08 so the scan never hand-types a town.
- `tools/my-bands.py` covers the private My Bands watch-list: `match <venue text files>` checks every
  act against saved venue calendars at once; `next N` / `mark` / `status` rotate per-act searches,
  with state in the gitignored `.my-bands-state.json`. It never writes `index.html`.
- A town missing from `DRIVE` shows straight-line miles, labelled ("≈12 mi", "no road distance yet"), plus a
  console warning and a red line in About. Never silent; the fix is to re-run the script.
- To add a home town: add it to `HOMES` (Census Gazetteer coordinates, or its `TOWNS` row), then re-run the script.

### The four tabs (render side)
Bottom tabs on a phone, a left rail at 960px and wider: **Tonight, Upcoming, Weekly, Saved**. "Today" is
America/Chicago everywhere in the app.
- **Tonight** covers the whole area (no region filter), sorted by drive miles from the home town (Ashland
  when none is set), then by time, in bands: Close by (<15 mi), Short drive (15-44), Worth the drive
  (45-89), Farther (90+), Distance unknown. It includes:
  - a single-day event whose `time` starts at 17:00 or later, or whose end is still ahead (an event that
    starts before 17:00 with no end time is not "tonight"; it still shows on Upcoming under Today);
  - an event with no `time`, listed as "Time not listed";
  - a `dates[]` event with today in `dates`;
  - a continuous run of 14 days or less that covers today.
  Runs over 14 days are not on Tonight; they sit in Upcoming's collapsed "Running now" list.
- **Upcoming** is the day list from today on, with a sticky date strip, search (`q`), the kind filter and
  Regions. Core regions are on by default: Chequamegon Bay, Duluth / Superior, Hurley / Iron County,
  Northwoods, Wider Northwoods, Hayward (including "Hayward / Sawyer County"), Western U.P. Every other
  region is under "Farther away" and off until turned on. The choice is saved in `ev_regions` and also
  applies to Weekly. Only the default is code: a saved `ev_regions` is never migrated or overwritten.
- **Weekly** has day chips Mon-Sun plus Other (Monthly, Season, Varies...). It ignores `q` and the kind
  filter; Regions apply.
- **Saved** is the reader's saved list.
- The kind filter (Tonight and Upcoming) groups categories for readers; the `cat` URL key still carries
  category names. My Bands stays its own group, hidden unless `ev_mybands` is on.

### Render-side changes: the invariant
Any future render-side change must leave these byte-identical to `main`: the data region (from
`const LAST_SCAN` up to the `// ===== render` marker), the marker line itself, and `HOMES` and `DRIVE`.
`.github/scripts/validate_scan.py` splits on that marker. Head, CSS, markup and the render JS may change.
Check with `git diff main -- index.html` that no hunk falls inside the data region.

### Reader settings and URL keys
- On the device only (`localStorage`, every access guarded): `ev_home` (the home town; never in the URL),
  `ev_theme`, `ev_mybands` (`1` shows My Bands; hidden by default), `ev_hello` (`off` once the first-run
  card is dismissed), `ev_regions` (the Regions selection on Upcoming and Weekly; see "The four tabs"),
  plus the Saved list.
- URL keys: `mode` (`tonight`, `upcoming`, `weekly`, `saved`), `sort`, `when` (a range key or a
  `YYYY-MM-DD` date), `cat` (repeatable; category names), `dist`, `town` (a `TOWNS` key: "More in
  <Town>"), `q`, `day` (Weekly only: `Mon`..`Sun` or `Other`), `ev`. Old links keep loading.
  - A bare URL (no `mode`) opens Tonight. `mode=tonight` is written explicitly only when Tonight has a
    kind selection, so `?mode=tonight&cat=Concert` survives a reload and a shared link.
  - Old-link rule: no `mode` plus any of `when`, `sort`, `cat`, `dist`, `town`, `q` opens Upcoming with
    those applied. An old link with no `when` keeps the 7-day window it implied (a removable applied chip).
  - Which keys each tab writes: Tonight `cat`; Upcoming `sort`, `when`, `cat`, `dist`, `town`, `q`;
    Weekly `day`; Saved none. `ev` opens the event sheet on any tab.
- **My Bands is hidden by default** on the public app: gone from lists, counts, Filters, search and `cat=`
  links until a reader turns on "Show My Bands" in About. A direct `?ev=` link still opens. The scan still
  writes My Bands rows as before.

## Installable app (manifest + service worker)
- `manifest.webmanifest` (linked in the head) and `icon-192.png`, `icon-512.png`,
  `icon-maskable-512.png` (rendered from `favicon.svg`) let Android Chrome install the site as an app.
- `sw.js` is the service worker. It is registered at the bottom of the script, only when the host
  ends in `github.io` (the same `index.html` also runs as a Cowork artifact).
- **`sw.js` must stay NETWORK-FIRST for the page.** The weekly scan rewrites `index.html`; a
  cache-first page would keep showing friends last week's events. The cached page is only an
  offline fallback. Google Fonts are cache-first; nothing else is intercepted. Bump `VERSION` in
  `sw.js` when its logic changes (on activate, only this site's old `nwe-` caches are deleted).
- Cache Storage is shared by every app on `buildwithbaker.github.io` (Baker's Recipe List, the old
  Wren copy), so this worker and its kill switch must never touch a cache that does not start with `nwe-`.
- A service worker stays on phones after a bad deploy, so changes to `sw.js` need sign-off.
- **Kill switch** if a bad worker ships: replace `sw.js` with the version below and merge. Each phone
  picks it up on its next visit, and the worker deletes its own `nwe-` caches and unregisters itself.
  ```js
  self.addEventListener("install", () => self.skipWaiting());
  self.addEventListener("activate", (e) => e.waitUntil((async () => {
    for (const k of await caches.keys()) if (k.startsWith("nwe-")) await caches.delete(k);
    await self.registration.unregister();
    for (const c of await self.clients.matchAll({ type: "window" })) c.navigate(c.url);
  })()));
  ```
- The weekly scan never touches any of these files.
- `og.png` (1200x630) and `screenshots/events-light.png` / `events-dark.png` (780x1688, the sizes in the
  manifest) are rendered from the live UI. Re-render them when the UI changes visibly.

## Deploy
GitHub Pages serves this repo as a project site at
https://buildwithbaker.github.io/northwoods-area-events/. Since 2026-11-08 the Pages source is
**GitHub Actions**, not "deploy from a branch": `.github/workflows/pages.yml` runs the same Jekyll
build on every push to `main` (a human merge) and on `workflow_dispatch`.

**Weekly scan PRs merge themselves.** `.github/workflows/scan-automerge.yml` runs on any PR from a
`weekly-scan-YYYY-MM-DD` branch opened by `buildwithbaker`. It runs `.github/scripts/validate_scan.py`
from `main`, squash-merges only if every check passes, then dispatches `pages.yml` (a merge made with
the workflow's own token starts no other workflow, so it has to ask). The scan must never run
`gh pr merge` itself. A failed check leaves the PR open and fails the run - fix the cause, push to the
same branch, and the workflow re-runs. Changing the validator or either workflow is a normal PR that a
human merges.

## Branching (main is protected - PR only)

`main` is protected: direct pushes are rejected. **Never run `git push origin main`.**

1. `git checkout main && git pull origin main` - start from an up-to-date main
2. `git checkout -b <type>/<slug>` - branch BEFORE staging, so local `main` never diverges
3. edit, then `git add -- <explicit paths>` - never `git add -A`
4. `git commit -m "<message>"`
5. `git push -u origin <branch>`
6. `gh pr create --base main --fill`
7. `gh pr checks <branch> --watch` - wait for the required checks
8. `gh pr merge <branch> --squash --delete-branch`
9. `git checkout main && git pull origin main`

Never merge while a required check is failing or pending, and never disable a check to
force a merge through - stop and report instead.

Stage `index.html` explicitly. **Never commit `scan-sources.md`** - it holds personal notes
that must stay out of the public repo.
