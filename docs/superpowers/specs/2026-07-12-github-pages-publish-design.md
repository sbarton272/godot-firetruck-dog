# Publish to GitHub Pages — Design

## Goal

Let the user share playable web builds of the game as it progresses. Each deliberately-published "major version" gets its own permanent URL, and an index page lists all published versions newest-first with a short human-written summary of that version's state.

## Non-goals

- No CI/CD (GitHub Actions). Godot already runs locally on the developer's machine; nothing needs to be installed or version-pinned in the cloud.
- No `gh-pages` branch or artifact mirroring step. GitHub Pages serves directly from `main`.
- No automatic/every-commit publishing. Publishing a version is a deliberate, human-curated action (you choose when a state is share-worthy and write the summary).
- No multiplayer/server component — this is a static HTML/WASM/PCK export, same as any Godot Web export.

## Architecture

```
github-pages/
  index.html         # generated — do not hand-edit
  versions.json       # source of truth for published versions
  v1/                 # self-contained Godot Web export
    index.html
    index.js
    index.wasm
    index.pck
    ...
  v2/
    ...
```

- `github-pages/` lives in `main` and is committed like any other repo content.
- **GitHub Pages setting** (one-time, in repo Settings → Pages): Deploy from branch `main`, folder `/github-pages`. No Action, no separate branch.
- `versions.json` is a JSON array, ordered oldest→newest:
  ```json
  [
    { "version": "v1", "date": "2026-07-12", "summary": "First drivable prototype: drift physics, damage system, win condition.", "dir": "v1" }
  ]
  ```
- `index.html` is fully regenerated from `versions.json` every time a version is published (never hand-edited) — newest-first list, each entry showing date + summary + a "Play" link to `vN/index.html`.

## Publish flow

Fully manual, single script — no git hook. Publishing only ever happens when you deliberately run it:

**`tools/publish-version.sh "<summary text>"`**
- Verifies prerequisites up front, aborting with a clear message if missing:
  - `godot` is on `PATH`.
  - `export_presets.cfg` exists at repo root and defines a preset named `Web`.
  - Godot Web export templates for the installed engine version are present (`~/Library/Application Support/Godot/export_templates/`).
- Reads `github-pages/versions.json` (creates `[]` if missing); computes next version `v<count+1>`.
- Runs `godot --headless --export-release "Web" github-pages/vN/index.html`.
- Appends `{ version, date: today (YYYY-MM-DD), summary, dir: version }` to `versions.json`.
- Regenerates `github-pages/index.html` from `versions.json`.
- `git add`s `github-pages/versions.json`, `github-pages/vN/`, and `github-pages/index.html`.
- Prints a reminder to review the diff and run `git commit` — the script never commits on its own.

## One-time setup (not automatable)

1. In the Godot editor: Editor → Manage Export Templates → download/install templates matching the installed engine version (4.7.stable).
2. In the Godot editor: Project → Export → Add → Web. Leave **Thread Support disabled** (the default) — required so the build runs on GitHub Pages' plain static hosting without cross-origin-isolation headers (COOP/COEP), which GitHub Pages does not set. Save; this writes `export_presets.cfg` at repo root, which is committed normally (Godot's own docs describe this file as safe/intended to commit).
3. In the GitHub repo settings: Settings → Pages → Source: Deploy from a branch → Branch `main`, folder `/github-pages`.

## Error handling

- Missing `godot` on `PATH`, missing export preset, or missing export templates: `publish-version.sh` aborts before touching any files, with a specific, actionable message naming which prerequisite is missing.
- Godot export command exits non-zero: script aborts and surfaces Godot's own error output; nothing is staged.
- Script run twice in a row: second run publishes a second version (`v2`, `v3`, ...); this is expected — each run is a deliberate new publish.

## Testing / verification

- Manually run `tools/publish-version.sh "test version"` and confirm:
  - `github-pages/v1/` contains a working Godot Web export.
  - `github-pages/index.html` lists the new version with correct summary/date and a working play link.
  - `git status` shows `github-pages/versions.json`, `github-pages/v1/`, and `github-pages/index.html` staged, and nothing else.
  - Serving `github-pages/` locally (e.g. `python3 -m http.server` from that folder) loads and plays the game in a browser without COOP/COEP-related console errors.
- After committing, pushing to `main` with GitHub Pages configured, confirm the live Pages URL serves the updated `index.html` and the new version is playable.

## Open questions / follow-ups (not blocking)

- Repo history will accumulate Web export binaries (WASM/PCK, likely single-digit MB per version) each time a version is published. Acceptable given publishing is rare/deliberate; revisit only if this becomes a real repo-size problem.
