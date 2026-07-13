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

Two steps, so the (slow) Godot export only runs when actually publishing, not on every commit:

1. **`tools/new-version.sh "<summary text>"`**
   - Reads `github-pages/versions.json` (creates `[]` if missing).
   - Next version = `v<count+1>`.
   - Appends `{ version, date: today (YYYY-MM-DD), summary, dir: version }`.
   - `git add github-pages/versions.json`.
   - Prints a reminder to run `git commit` to build and publish.
   - Does **not** invoke Godot. Fast, no build dependency.

2. **`git commit`** → **pre-commit hook** (`tools/hooks/pre-commit`, installed via `tools/install-hooks.sh`):
   - `git diff --cached --name-only` — if `github-pages/versions.json` is not staged, exit 0 immediately (no-op for ordinary commits).
   - Otherwise, read the last entry in the staged `versions.json`. If `github-pages/<dir>/index.html` already exists, exit 0 (already built — supports amending without rebuilding).
   - Verify prerequisites, aborting the commit with a clear message if missing:
     - `export_presets.cfg` exists at repo root and defines a preset named `Web`.
     - Godot Web export templates for the installed engine version are present (`~/Library/Application Support/Godot/export_templates/<version>/`).
   - Run: `godot --headless --export-release "Web" github-pages/<dir>/index.html`.
   - Regenerate `github-pages/index.html` from `versions.json`.
   - `git add github-pages/<dir>/ github-pages/index.html` so the build output joins the same commit.
   - Exit 0 to let the commit proceed.

## One-time setup (not automatable)

1. In the Godot editor: Editor → Manage Export Templates → download/install templates matching the installed engine version (4.7.stable).
2. In the Godot editor: Project → Export → Add → Web. Leave **Thread Support disabled** (the default) — required so the build runs on GitHub Pages' plain static hosting without cross-origin-isolation headers (COOP/COEP), which GitHub Pages does not set. Save; this writes `export_presets.cfg` at repo root, which is committed normally (Godot's own docs describe this file as safe/intended to commit).
3. Run `tools/install-hooks.sh` once per clone/worktree to install the pre-commit hook (`.git/hooks` is not tracked by git, so every checkout needs this run once).
4. In the GitHub repo settings: Settings → Pages → Source: Deploy from a branch → Branch `main`, folder `/github-pages`.

## Error handling

- Missing export preset or export templates: pre-commit hook aborts the commit with a specific, actionable message (which step above is missing) rather than a raw Godot stack trace.
- Godot export command exits non-zero: hook aborts the commit and surfaces Godot's own error output.
- `new-version.sh` run twice before committing: second run appends a second entry; harmless, but the user should just commit once per version (documented in the script's own output).

## Testing / verification

- Manually run `tools/new-version.sh "test version"`, then `git commit`, and confirm:
  - `github-pages/v1/` contains a working Godot Web export.
  - `github-pages/index.html` lists the new version with correct summary/date and a working play link.
  - Serving `github-pages/` locally (e.g. `python3 -m http.server` from that folder) loads and plays the game in a browser without COOP/COEP-related console errors.
- Confirm the pre-commit hook no-ops (fast, no Godot invocation) on a commit that doesn't touch `versions.json`.
- After pushing to `main` with GitHub Pages configured, confirm the live Pages URL serves the updated `index.html` and the new version is playable.

## Open questions / follow-ups (not blocking)

- Repo history will accumulate Web export binaries (WASM/PCK, likely single-digit MB per version) each time a version is published. Acceptable given publishing is rare/deliberate; revisit only if this becomes a real repo-size problem.
