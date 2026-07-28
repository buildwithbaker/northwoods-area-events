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
**Edit `index.html` in place - preserve the structure exactly**: dropdown views, the
category set (including Conventions and Theater), the 1-2 sentence description on every
event, day-grouped Weekly Events, icon and pill rows, and the specific event URL on each
entry. Do not redesign it during a scan. `My Bands` (touring acts from Adam's watch-list)
is a distinct category from `Concert` (local venue shows).

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
