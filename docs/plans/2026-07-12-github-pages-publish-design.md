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
  .nojekyll           # disables GitHub Pages' Jekyll processing of this folder
  .gdignore           # keeps the Godot editor from importing the build output
  index.html          # generated — do not hand-edit
  versions.json       # source of truth for published versions
  v1/                 # self-contained Godot Web export
    index.html
    index.js
    index.wasm
    index.pck
    index.png         # boot splash
    ...
  v2/
    ...
```

- `.nojekyll` is required because GitHub Pages runs Jekyll over branch-served
  folders by default, which can filter/mangle a static asset dump like a Godot
  Web export.
- `.gdignore` is required because the export is written inside the Godot project
  (`res://github-pages/`); without it the editor would import the build's assets
  (e.g. the `.png` boot splash), cluttering the project with `.import` files. Both
  files are created/ensured by the publish script and committed once.

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
  - `jq` and `uv` are on `PATH` (provided by the mise toolchain — see Dev environment below).
  - `export_presets.cfg` exists at repo root and defines a preset named `Web`.
  - Godot Web export templates for the installed engine version are present (`~/Library/Application Support/Godot/export_templates/`).
- Reads `github-pages/versions.json` (creates `[]` if missing); computes next version `v<count+1>`.
- Runs `godot --headless --export-release "Web" github-pages/vN/index.html`.
- Appends `{ version, date: today (YYYY-MM-DD), summary, dir: version }` to `versions.json` (via `jq`).
- Regenerates `github-pages/index.html` from `versions.json` (via `uv run tools/generate_index.py`).
- `git add`s `github-pages/versions.json`, `github-pages/vN/`, `github-pages/index.html`, `github-pages/.nojekyll`, and `github-pages/.gdignore`.
- Prints a reminder to review the diff and run `git commit` — the script never commits on its own.

## Dev environment (direnv + mise)

The Python/CLI toolchain is pinned and provisioned reproducibly so the publish
script has the tools it needs:

- **`mise.toml`** pins `python`, `uv`, and `jq` to exact versions and `mise`
  installs them on demand.
- **`.envrc`** (direnv) runs `mise install` + `eval "$(mise env)"` to put the
  pinned tools on `PATH`, prepends mise's shims so the pinned copies win over any
  system/brew copies, and asserts a compatible **Godot 4.7.x** is on `PATH`
  (Godot itself is a GUI app installed separately, e.g. `brew install --cask godot`,
  not managed by mise).
- The index generator runs under **`uv`** (`uv run tools/generate_index.py`); the
  script carries PEP 723 inline metadata (`requires-python`, no third-party deps).

Per-checkout activation: run `direnv allow` once. Without direnv, the publish
script still works as long as `godot`, `jq`, and `uv` are otherwise on `PATH`.

## One-time setup (not automatable)

1. Install [direnv](https://direnv.net) and [mise](https://mise.jdx.dev), then run `direnv allow` in the checkout. This installs the pinned `python`/`uv`/`jq` and activates them.
2. In the Godot editor: Editor → Manage Export Templates → download/install templates matching the installed engine version (4.7.stable).
3. In the Godot editor: Project → Export → Add → Web (single-threaded). Rename the preset to exactly `Web`. Single-threaded is required so the build runs on GitHub Pages' plain static hosting without cross-origin-isolation headers (COOP/COEP), which GitHub Pages does not set. Save; this writes `export_presets.cfg` at repo root, which is committed normally (Godot's own docs describe this file as safe/intended to commit).
4. In the GitHub repo settings: Settings → Pages → Source: Deploy from a branch → Branch `main`, folder `/github-pages`.

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
