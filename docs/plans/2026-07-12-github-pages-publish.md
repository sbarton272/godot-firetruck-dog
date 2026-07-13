# Publish to GitHub Pages Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let the developer publish deliberately-curated, versioned web builds of the game to GitHub Pages, each linked from an index page with a short human-written summary.

**Architecture:** A `github-pages/` folder on `main` (served directly by GitHub Pages, no `gh-pages` branch, no CI, no git hooks) holds `versions.json` (source of truth), a generated `index.html`, and one `vN/` folder per published Godot Web export. Publishing is a single manual script, `tools/publish-version.sh "<summary>"`, run only when the developer deliberately decides a state is share-worthy. It verifies prerequisites, runs `godot --headless --export-release`, bumps `versions.json`, regenerates `index.html`, and stages everything — the developer reviews the diff and commits themselves.

**Tech Stack:** Bash (the publish script), Python 3 (HTML generation, for safe escaping), `jq` (JSON editing), Godot 4.7 CLI (`godot --headless --export-release`).

## Global Constraints

- Engine version: Godot 4.7 (GL Compatibility renderer) — per `CLAUDE.md`.
- Automation scripts live under `tools/`, never under `scripts/` (that path is reserved for GDScript source at `res://scripts/`).
- Web export must keep **Thread Support disabled** (Godot's default) so the build runs on GitHub Pages' plain static hosting, which does not set COOP/COEP headers.
- `export_presets.cfg` is safe and intended to be committed to version control (per Godot's own docs).
- Publishing is fully manual — no git hooks of any kind. `tools/publish-version.sh` stages files but never commits.
- No GitHub Action, no `gh-pages` branch. GitHub Pages is configured (one-time, manual) to serve `main` branch, `/github-pages` folder.

---

### Task 1: One-time Godot export setup (MANUAL — requires a human at the Godot editor)

This task cannot be automated: it requires interactive use of the Godot editor GUI. If you are an agentic worker executing this plan, **stop here and ask the user to perform these steps**, then verify before continuing.

**Files:**
- Create (by the Godot editor, not by hand): `export_presets.cfg` at repo root.

**Interfaces:**
- Produces: `export_presets.cfg` containing a preset section with `name="Web"` — consumed by Task 3 (`publish-version.sh`) and Task 4 (integration test), both of which run `godot --headless --export-release "Web" ...`.

- [ ] **Step 1: Ask the user to install Web export templates**

Tell the user: "Open the Godot editor for this project, go to **Editor → Manage Export Templates**, and download/install the templates matching the installed engine version (4.7.stable). Let me know when that's done."

Wait for confirmation.

- [ ] **Step 2: Ask the user to add a Web export preset**

Tell the user: "In the Godot editor, go to **Project → Export → Add → Web**. Leave **Thread Support** disabled (it's off by default — leave it that way). Click **Close** to save. This writes `export_presets.cfg` at the repo root. Let me know when that's done."

Wait for confirmation.

- [ ] **Step 3: Verify `export_presets.cfg` exists and defines a Web preset**

Run: `test -f export_presets.cfg && grep -c 'name="Web"' export_presets.cfg`
Expected: file exists, output is `1` (exactly one preset named "Web").

If this fails, do not proceed — ask the user to redo Step 2.

- [ ] **Step 4: Verify export templates are installed**

Run: `ls -A ~/Library/Application\ Support/Godot/export_templates/`
Expected: at least one non-empty subdirectory (e.g. `4.7.stable` or similar). If empty, ask the user to redo Step 1.

- [ ] **Step 5: Commit `export_presets.cfg`**

```bash
git add export_presets.cfg
git commit -m "$(cat <<'EOF'
Add Web export preset for GitHub Pages publishing

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: `tools/generate_index.py` — regenerate index.html from versions.json

**Files:**
- Create: `tools/generate_index.py`
- Test: manual run against a fixture (no formal test framework in this repo; verify via direct invocation and `grep`/`diff` on output, per steps below).

**Interfaces:**
- Consumes: a JSON file shaped like `[{"version": "v1", "date": "2026-07-12", "summary": "...", "dir": "v1"}, ...]`.
- Produces: `python3 tools/generate_index.py [versions_json_path] [output_html_path]` — both args optional, defaulting to `github-pages/versions.json` and `github-pages/index.html` relative to the repo root (found via `git rev-parse --show-toplevel`). Writes a static HTML file listing versions newest-first. Consumed by Task 3 (`publish-version.sh` calls it with no args).

- [ ] **Step 1: Write a fixture versions.json to verify against**

```bash
mkdir -p /tmp/gh-pages-test
cat > /tmp/gh-pages-test/versions.json <<'EOF'
[
  {"version": "v1", "date": "2026-07-01", "summary": "First prototype", "dir": "v1"},
  {"version": "v2", "date": "2026-07-12", "summary": "Added <drift> physics & \"damage\" system", "dir": "v2"}
]
EOF
```

- [ ] **Step 2: Run the not-yet-created script against the fixture to confirm it fails**

Run: `python3 tools/generate_index.py /tmp/gh-pages-test/versions.json /tmp/gh-pages-test/index.html`
Expected: FAIL — `can't open file '.../tools/generate_index.py': [Errno 2] No such file or directory`

- [ ] **Step 3: Write `tools/generate_index.py`**

```python
#!/usr/bin/env python3
"""Regenerate github-pages/index.html from github-pages/versions.json."""
import html
import json
import pathlib
import subprocess
import sys


def repo_root() -> pathlib.Path:
    out = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True, text=True, check=True,
    )
    return pathlib.Path(out.stdout.strip())


PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Firetruck Dog</title>
<style>
  body {{ font-family: -apple-system, sans-serif; max-width: 640px; margin: 40px auto; padding: 0 16px; }}
  h1 {{ margin-bottom: 4px; }}
  ul {{ list-style: none; padding: 0; }}
  li {{ border: 1px solid #ddd; border-radius: 8px; padding: 12px 16px; margin-bottom: 12px; }}
  .version {{ font-weight: bold; }}
  .date {{ color: #666; font-size: 0.9em; }}
  a.play {{ display: inline-block; margin-top: 8px; }}
</style>
</head>
<body>
<h1>Firetruck Dog</h1>
<p>Published versions, newest first.</p>
<ul>
{entries}
</ul>
</body>
</html>
"""

ENTRY_TEMPLATE = """  <li>
    <div class="version">{version}</div>
    <div class="date">{date}</div>
    <p>{summary}</p>
    <a class="play" href="{dir}/index.html">Play {version}</a>
  </li>"""


def render(versions: list[dict]) -> str:
    entries = [
        ENTRY_TEMPLATE.format(
            version=html.escape(v["version"]),
            date=html.escape(v["date"]),
            summary=html.escape(v["summary"]),
            dir=html.escape(v["dir"]),
        )
        for v in reversed(versions)
    ]
    return PAGE_TEMPLATE.format(entries="\n".join(entries))


def main(argv: list[str]) -> int:
    root = repo_root()
    versions_path = pathlib.Path(argv[0]) if len(argv) > 0 else root / "github-pages" / "versions.json"
    output_path = pathlib.Path(argv[1]) if len(argv) > 1 else root / "github-pages" / "index.html"

    versions = json.loads(versions_path.read_text()) if versions_path.exists() else []
    output_path.write_text(render(versions))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
```

- [ ] **Step 4: Run it against the fixture and verify output**

Run: `python3 tools/generate_index.py /tmp/gh-pages-test/versions.json /tmp/gh-pages-test/index.html && cat /tmp/gh-pages-test/index.html`
Expected: valid HTML; `v2` (newest) appears before `v1`; the summary `Added <drift> physics & "damage" system` appears HTML-escaped as `Added &lt;drift&gt; physics &amp; &quot;damage&quot; system`; both `v1/index.html` and `v2/index.html` appear as `href` values.

- [ ] **Step 5: Verify missing versions.json produces an empty-but-valid list**

Run: `python3 tools/generate_index.py /tmp/gh-pages-test/does-not-exist.json /tmp/gh-pages-test/empty.html && grep -c '<li>' /tmp/gh-pages-test/empty.html`
Expected: command succeeds, output `0` (no `<li>` entries, no crash).

- [ ] **Step 6: Clean up fixture and commit**

```bash
rm -rf /tmp/gh-pages-test
git add tools/generate_index.py
git commit -m "$(cat <<'EOF'
Add tools/generate_index.py to render github-pages/index.html

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: `tools/publish-version.sh` — manual publish script

**Files:**
- Create: `tools/publish-version.sh`

**Interfaces:**
- Consumes: `tools/generate_index.py` (Task 2, invoked with no args so it uses the real repo paths), `export_presets.cfg` (Task 1).
- Produces: `tools/publish-version.sh "<summary text>"` — the single entry point for publishing. Builds the Web export, appends to `github-pages/versions.json`, regenerates `github-pages/index.html`, ensures `github-pages/.nojekyll` (GitHub Pages) and `github-pages/.gdignore` (Godot editor) exist, and `git add`s all of them. Never commits. Exercised for real in Task 4.

- [ ] **Step 1: Confirm the script doesn't exist yet**

Run: `test -f tools/publish-version.sh && echo exists || echo "missing (expected)"`
Expected: `missing (expected)`

- [ ] **Step 2: Write `tools/publish-version.sh`**

```bash
#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 || -z "$1" ]]; then
  echo "Usage: tools/publish-version.sh \"<summary of this version>\"" >&2
  exit 1
fi

SUMMARY="$1"
REPO_ROOT="$(git rev-parse --show-toplevel)"
GITHUB_PAGES_DIR="$REPO_ROOT/github-pages"
VERSIONS_JSON="$GITHUB_PAGES_DIR/versions.json"

if ! command -v godot >/dev/null 2>&1; then
  echo "ERROR: 'godot' not found on PATH. Install Godot 4.7 to publish a version." >&2
  exit 1
fi

if [[ ! -f "$REPO_ROOT/export_presets.cfg" ]] || ! grep -q 'name="Web"' "$REPO_ROOT/export_presets.cfg"; then
  echo "ERROR: No 'Web' export preset found in export_presets.cfg." >&2
  echo "Open the project in the Godot editor: Project > Export > Add > Web, then retry." >&2
  exit 1
fi

TEMPLATES_DIR="$HOME/Library/Application Support/Godot/export_templates"
if [[ -z "$(ls -A "$TEMPLATES_DIR" 2>/dev/null)" ]]; then
  echo "ERROR: No Godot export templates installed." >&2
  echo "In the Godot editor: Editor > Manage Export Templates > Download and Install, then retry." >&2
  exit 1
fi

mkdir -p "$GITHUB_PAGES_DIR"
if [[ ! -f "$VERSIONS_JSON" ]]; then
  echo "[]" > "$VERSIONS_JSON"
fi

# GitHub Pages serves this folder directly; disable Jekyll so it doesn't filter
# or mangle the exported build's files/folders.
touch "$GITHUB_PAGES_DIR/.nojekyll"
# The export is written inside the Godot project (res://github-pages/); a .gdignore
# stops the editor from importing the build output (e.g. the .png boot splash),
# which would otherwise clutter the project with .import files on every publish.
touch "$GITHUB_PAGES_DIR/.gdignore"

COUNT=$(jq 'length' "$VERSIONS_JSON")
NEXT_VERSION="v$((COUNT + 1))"
TODAY=$(date +%Y-%m-%d)
BUILD_DIR="$GITHUB_PAGES_DIR/$NEXT_VERSION"
BUILD_INDEX="$BUILD_DIR/index.html"

echo "Building $NEXT_VERSION..."
mkdir -p "$BUILD_DIR"
godot --headless --path "$REPO_ROOT" --export-release "Web" "$BUILD_INDEX"

jq --arg version "$NEXT_VERSION" \
   --arg date "$TODAY" \
   --arg summary "$SUMMARY" \
   --arg dir "$NEXT_VERSION" \
   '. + [{version: $version, date: $date, summary: $summary, dir: $dir}]' \
   "$VERSIONS_JSON" > "$VERSIONS_JSON.tmp"
mv "$VERSIONS_JSON.tmp" "$VERSIONS_JSON"

python3 "$REPO_ROOT/tools/generate_index.py"

git -C "$REPO_ROOT" add "$VERSIONS_JSON" "$BUILD_DIR" "$GITHUB_PAGES_DIR/index.html" \
  "$GITHUB_PAGES_DIR/.nojekyll" "$GITHUB_PAGES_DIR/.gdignore"

echo "Published $NEXT_VERSION: \"$SUMMARY\""
echo "Review the diff and run 'git commit' to finish publishing."
```

```bash
chmod +x tools/publish-version.sh
```

- [ ] **Step 3: Test the missing-preset error path in an isolated scratch repo (no Godot invocation yet)**

```bash
rm -rf /tmp/gh-pages-publish-test
mkdir -p /tmp/gh-pages-publish-test/tools
cp tools/publish-version.sh /tmp/gh-pages-publish-test/tools/publish-version.sh
cd /tmp/gh-pages-publish-test
git init -q
git config user.email test@example.com
git config user.name Test
bash tools/publish-version.sh "test"; echo "exit=$?"
```
Expected: if `godot` is on `PATH`, stderr shows `ERROR: No 'Web' export preset found in export_presets.cfg.` (no `export_presets.cfg` exists in this scratch repo) and `exit=1`. Nothing under `github-pages/` is created.

- [ ] **Step 4: Verify the usage error path**

Run: `bash tools/publish-version.sh; echo "exit=$?"`
Expected: prints `Usage: tools/publish-version.sh "<summary of this version>"` to stderr, `exit=1`.

- [ ] **Step 5: Clean up scratch repo**

```bash
cd -
rm -rf /tmp/gh-pages-publish-test
```

- [ ] **Step 6: Commit**

```bash
git add tools/publish-version.sh
git commit -m "$(cat <<'EOF'
Add tools/publish-version.sh as the manual publish entry point

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: Integration — publish real v1 and enable Pages

**Files:**
- Modify: none new; produces real content under `github-pages/` in this repo (`versions.json`, `index.html`, `v1/*`).

**Interfaces:**
- Consumes: everything from Tasks 1–3, exercised together for the first time end-to-end.
- Produces: the first real published version, live on GitHub Pages once pushed.

> **Note (import cache):** The headless export relies on Godot's `.godot/` import cache, which is gitignored and per-checkout. Run this publish from a checkout that has been opened at least once in the Godot editor (so resources are imported). If the export produces an empty/broken build on a never-opened worktree, open the project in the editor once (let it finish importing), then re-run. The `export_presets.cfg` from Task 1 is shared via git, but the import cache is not.

- [ ] **Step 1: Publish the first version**

Run: `bash tools/publish-version.sh "First drivable prototype: drift physics, damage system, win condition."`
Expected: `Building v1...`, then the real Godot export runs, then `Published v1: "First drivable prototype: ..."` and the commit reminder. If it fails with a missing-preset or missing-templates error, stop and re-verify Task 1 was completed correctly.

- [ ] **Step 2: Verify the build output and staged files**

Run: `ls github-pages/v1/ && cat github-pages/index.html && git status --short`
Expected: `github-pages/v1/` contains at least `index.html`, `index.js`, `index.wasm`, `index.pck` (and a `.png` boot splash); `github-pages/index.html` shows a `v1` entry with the summary text and a link to `v1/index.html`; `git status --short` shows `github-pages/versions.json`, `github-pages/v1/`, `github-pages/index.html`, `github-pages/.nojekyll`, and `github-pages/.gdignore` staged (`A` or `M`), and nothing else.

- [ ] **Step 3: Serve locally and verify it plays in a browser**

```bash
cd github-pages && python3 -m http.server 8765 &
```
Open `http://localhost:8765/` in a browser — confirm the index page lists v1 with its summary, click through to `v1/index.html`, confirm the game loads and is playable, and confirm the browser console has no COOP/COEP or SharedArrayBuffer errors. Then stop the server:
```bash
kill %1
cd -
```

- [ ] **Step 4: Commit the published version**

```bash
git commit -m "$(cat <<'EOF'
Publish v1: first drivable prototype

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

- [ ] **Step 5: Enable GitHub Pages (requires user confirmation before touching repo settings)**

Ask the user: "Ready to enable GitHub Pages for this repo — Settings → Pages → Source: Deploy from a branch → Branch `main`, folder `/github-pages`. This makes the site publicly accessible at `https://sbarton272.github.io/godot-firetruck-dog/`. Want me to set this via `gh api`, or will you do it yourself in the GitHub UI?"

If the user approves doing it via API:
```bash
gh api repos/sbarton272/godot-firetruck-dog/pages -X POST -f "source[branch]=main" -f "source[path]=/github-pages"
```

- [ ] **Step 6: Push and confirm the live site**

Ask the user before pushing (pushing to `main` is visible to others). Once approved:
```bash
git push
```
Then check `https://sbarton272.github.io/godot-firetruck-dog/` after GitHub Pages finishes its first build (may take a minute or two) and confirm v1 is playable there too.
