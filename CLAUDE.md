# CLAUDE.md - northwoods-area-events

A live, always-current list of events around Ashland/Bayfield, the Chequamegon Bay,
Hayward, Duluth, and the Wisconsin Dells. Anchor town: Ashland, WI.

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
the category set (including Conventions and Theater) and `CATMETA` as they are. Do not
redesign the page during a scan. `My Bands` (touring acts from Adam's watch-list) is a
distinct category from `Concert` (local venue shows).

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
- `RECURRING` - weekly rows: `day`, `title`, `place`, optional `town`, `region`, `cat`,
  optional `url`, optional `seasonStart` / `seasonEnd`, `note`.
- `TOWNS` - keyed `"Town, ST"`: `{lat, lon, mi, src}`. `lat`/`lon` from the US Census Gazetteer
  (USGS GNIS populated place where Census has none), `mi` = OSRM driving miles from Ashland, WI,
  `src` names both and says when the route uses a ferry or a seasonal ice road. `town` on a row must be a key
  here. A town that cannot be sourced is left off the row (it sorts last as "distance unknown");
  never guess a town, coordinates or miles.
- No `</script` and no `<!--` anywhere in the data - either one ends the page's script.

## Deploy
GitHub Pages serves this repo as a project site at
https://buildwithbaker.github.io/northwoods-area-events/. No build step - merging a PR
into `main` publishes it.

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
