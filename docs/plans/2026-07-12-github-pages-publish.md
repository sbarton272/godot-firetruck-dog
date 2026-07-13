# Publish to GitHub Pages Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let the developer publish deliberately-curated, versioned web builds of the game to GitHub Pages, each linked from an index page with a short human-written summary.

**Architecture:** A `github-pages/` folder on `main` (served directly by GitHub Pages, no `gh-pages` branch, no CI) holds `versions.json` (source of truth), a generated `index.html`, and one `vN/` folder per published Godot Web export. Publishing is two steps: `tools/new-version.sh "<summary>"` stages a metadata bump (fast, no Godot), then `git commit` triggers a `pre-commit` hook that — only when `versions.json` is staged and the new version's build is missing — runs the actual `godot --headless --export-release` and folds the build output into the same commit.

**Tech Stack:** Bash (scripts + git hook), Python 3 (HTML generation, for safe escaping), `jq` (JSON editing), Godot 4.7 CLI (`godot --headless --export-release`).

## Global Constraints

- Engine version: Godot 4.7 (GL Compatibility renderer) — per `CLAUDE.md`.
- Automation scripts live under `tools/`, never under `scripts/` (that path is reserved for GDScript source at `res://scripts/`).
- Web export must keep **Thread Support disabled** (Godot's default) so the build runs on GitHub Pages' plain static hosting, which does not set COOP/COEP headers.
- `export_presets.cfg` is safe and intended to be committed to version control (per Godot's own docs).
- `.git/hooks` is not tracked by git — every clone/worktree needs `tools/install-hooks.sh` run once.
- No GitHub Action, no `gh-pages` branch. GitHub Pages is configured (one-time, manual) to serve `main` branch, `/github-pages` folder.

---

### Task 1: One-time Godot export setup (MANUAL — requires a human at the Godot editor)

This task cannot be automated: it requires interactive use of the Godot editor GUI. If you are an agentic worker executing this plan, **stop here and ask the user to perform these steps**, then verify before continuing.

**Files:**
- Create (by the Godot editor, not by hand): `export_presets.cfg` at repo root.

**Interfaces:**
- Produces: `export_presets.cfg` containing a preset section with `name="Web"` — consumed by Task 4 (pre-commit hook) and Task 6 (integration test), both of which run `godot --headless --export-release "Web" ...`.

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
- Produces: `python3 tools/generate_index.py [versions_json_path] [output_html_path]` — both args optional, defaulting to `github-pages/versions.json` and `github-pages/index.html` relative to the repo root (found via `git rev-parse --show-toplevel`). Writes a static HTML file listing versions newest-first. Consumed by Task 4 (pre-commit hook calls it with no args).

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

### Task 3: `tools/new-version.sh` — stage a new version entry

**Files:**
- Create: `tools/new-version.sh`

**Interfaces:**
- Consumes: nothing from earlier tasks (independent of Task 2's script).
- Produces: `tools/new-version.sh "<summary text>"` — appends `{version, date, summary, dir}` to `github-pages/versions.json` (creating it if missing) and `git add`s it. Consumed by Task 6 (used to create the real `v1` entry) and referenced by Task 4's hook (which reacts to `versions.json` being staged).

- [ ] **Step 1: Set up an isolated scratch git repo to test against (do not touch the real repo's github-pages/ yet)**

```bash
rm -rf /tmp/gh-pages-repo-test
mkdir -p /tmp/gh-pages-repo-test
cd /tmp/gh-pages-repo-test
git init -q
git config user.email test@example.com
git config user.name "Test"
```

- [ ] **Step 2: Run the not-yet-created script to confirm it fails**

Run (from the real repo root): `bash tools/new-version.sh "test" ` won't work yet since the script doesn't exist. Confirm:
`test -f tools/new-version.sh && echo exists || echo "missing (expected)"`
Expected: `missing (expected)`

- [ ] **Step 3: Write `tools/new-version.sh`**

```bash
#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 || -z "$1" ]]; then
  echo "Usage: tools/new-version.sh \"<summary of this version>\"" >&2
  exit 1
fi

SUMMARY="$1"
REPO_ROOT="$(git rev-parse --show-toplevel)"
GITHUB_PAGES_DIR="$REPO_ROOT/github-pages"
VERSIONS_JSON="$GITHUB_PAGES_DIR/versions.json"

mkdir -p "$GITHUB_PAGES_DIR"
if [[ ! -f "$VERSIONS_JSON" ]]; then
  echo "[]" > "$VERSIONS_JSON"
fi

COUNT=$(jq 'length' "$VERSIONS_JSON")
NEXT_VERSION="v$((COUNT + 1))"
TODAY=$(date +%Y-%m-%d)

jq --arg version "$NEXT_VERSION" \
   --arg date "$TODAY" \
   --arg summary "$SUMMARY" \
   --arg dir "$NEXT_VERSION" \
   '. + [{version: $version, date: $date, summary: $summary, dir: $dir}]' \
   "$VERSIONS_JSON" > "$VERSIONS_JSON.tmp"
mv "$VERSIONS_JSON.tmp" "$VERSIONS_JSON"

git -C "$REPO_ROOT" add "$VERSIONS_JSON"

echo "Staged $NEXT_VERSION: \"$SUMMARY\""
echo "Run 'git commit' to build and publish this version."
```

```bash
chmod +x tools/new-version.sh
```

- [ ] **Step 4: Copy the script into the scratch repo and run it there**

```bash
mkdir -p /tmp/gh-pages-repo-test/tools
cp tools/new-version.sh /tmp/gh-pages-repo-test/tools/new-version.sh
cd /tmp/gh-pages-repo-test
git add tools/new-version.sh
git commit -q -m "add script"
bash tools/new-version.sh "First drivable prototype"
```

Expected output: `Staged v1: "First drivable prototype"` followed by the commit reminder line.

- [ ] **Step 5: Verify the staged content**

Run (still in `/tmp/gh-pages-repo-test`):
```bash
cat github-pages/versions.json
git diff --cached --name-only
```
Expected: `versions.json` contains one entry with `"version": "v1"`, today's date, the summary text, `"dir": "v1"`; `git diff --cached --name-only` lists `github-pages/versions.json`.

- [ ] **Step 6: Run it a second time and verify version increments**

Run: `bash tools/new-version.sh "Second version"`
Expected: `Staged v2: "Second version"`. Confirm with `jq length github-pages/versions.json` → `2`.

- [ ] **Step 7: Verify the usage error path**

Run: `bash tools/new-version.sh; echo "exit=$?"`
Expected: prints `Usage: tools/new-version.sh "<summary of this version>"` to stderr, `exit=1`.

- [ ] **Step 8: Clean up scratch repo and commit the real script**

```bash
cd -
rm -rf /tmp/gh-pages-repo-test
git add tools/new-version.sh
git commit -m "$(cat <<'EOF'
Add tools/new-version.sh to stage new published-version metadata

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: `tools/hooks/pre-commit` — build gate

**Files:**
- Create: `tools/hooks/pre-commit`

**Interfaces:**
- Consumes: `github-pages/versions.json` (Task 3's output shape), `tools/generate_index.py` (Task 2, invoked with no args so it uses the real repo paths), `export_presets.cfg` (Task 1).
- Produces: when installed as `.git/hooks/pre-commit` (Task 5), intercepts `git commit` — no-ops unless `github-pages/versions.json` is staged and the newest version's build folder doesn't exist yet, in which case it runs `godot --headless --export-release "Web" ...`, regenerates `index.html`, and stages the new build output. Exercised for real in Task 6.

- [ ] **Step 1: Confirm the hook file doesn't exist yet**

Run: `test -f tools/hooks/pre-commit && echo exists || echo "missing (expected)"`
Expected: `missing (expected)`

- [ ] **Step 2: Write `tools/hooks/pre-commit`**

```bash
#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
GITHUB_PAGES_DIR="$REPO_ROOT/github-pages"
VERSIONS_JSON="$GITHUB_PAGES_DIR/versions.json"

STAGED=$(git diff --cached --name-only)
if ! grep -qxF "github-pages/versions.json" <<< "$STAGED"; then
  exit 0
fi

LATEST_DIR=$(jq -r '.[-1].dir' "$VERSIONS_JSON")
LATEST_VERSION=$(jq -r '.[-1].version' "$VERSIONS_JSON")
BUILD_DIR="$GITHUB_PAGES_DIR/$LATEST_DIR"
BUILD_INDEX="$BUILD_DIR/index.html"

if [[ -f "$BUILD_INDEX" ]]; then
  exit 0
fi

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

echo "Building $LATEST_VERSION ($LATEST_DIR)..."
mkdir -p "$BUILD_DIR"
godot --headless --path "$REPO_ROOT" --export-release "Web" "$BUILD_INDEX"

python3 "$REPO_ROOT/tools/generate_index.py"

git -C "$REPO_ROOT" add "$BUILD_DIR" "$GITHUB_PAGES_DIR/index.html"

echo "Published $LATEST_VERSION."
```

```bash
mkdir -p tools/hooks
chmod +x tools/hooks/pre-commit
```

- [ ] **Step 3: Test the no-op path (versions.json not staged)**

```bash
rm -rf /tmp/gh-pages-hook-test
mkdir -p /tmp/gh-pages-hook-test/github-pages
cd /tmp/gh-pages-hook-test
git init -q
git config user.email test@example.com
git config user.name Test
echo "[]" > github-pages/versions.json
git add github-pages/versions.json
git commit -q -m init
echo "hi" > README.md
git add README.md
bash "$OLDPWD/tools/hooks/pre-commit"; echo "exit=$?"
```
Expected: `exit=0`, no other output (versions.json isn't in this commit's staged diff, only README.md is).

- [ ] **Step 4: Test the already-built no-op path**

```bash
mkdir -p github-pages/v1
touch github-pages/v1/index.html
cat > github-pages/versions.json <<'EOF'
[{"version": "v1", "date": "2026-07-12", "summary": "test", "dir": "v1"}]
EOF
git add github-pages/versions.json
bash "$OLDPWD/tools/hooks/pre-commit"; echo "exit=$?"
```
Expected: `exit=0`, no "Building..." output (build already exists at `github-pages/v1/index.html`).

- [ ] **Step 5: Test the missing-preset error path**

```bash
rm github-pages/v1/index.html
rmdir github-pages/v1
bash "$OLDPWD/tools/hooks/pre-commit"; echo "exit=$?"
```
Expected: stderr contains `ERROR: No 'Web' export preset found in export_presets.cfg.` (no `export_presets.cfg` exists in this scratch repo), `exit=1`.

- [ ] **Step 6: Clean up scratch repo**

```bash
cd -
rm -rf /tmp/gh-pages-hook-test
```

- [ ] **Step 7: Commit**

```bash
git add tools/hooks/pre-commit
git commit -m "$(cat <<'EOF'
Add pre-commit hook to build and publish new versions

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 5: `tools/install-hooks.sh` — install the hook per clone/worktree

**Files:**
- Create: `tools/install-hooks.sh`

**Interfaces:**
- Consumes: `tools/hooks/pre-commit` (Task 4).
- Produces: `tools/install-hooks.sh` — copies the hook into the correct git hooks directory (resolved via `git rev-parse --git-path hooks`, which correctly targets the shared hooks dir even when run from a worktree, since this repo uses git worktrees per `README.md`). Run manually once per clone/worktree in Task 6 and by future contributors.

- [ ] **Step 1: Confirm the script doesn't exist yet**

Run: `test -f tools/install-hooks.sh && echo exists || echo "missing (expected)"`
Expected: `missing (expected)`

- [ ] **Step 2: Write `tools/install-hooks.sh`**

```bash
#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
SRC="$REPO_ROOT/tools/hooks/pre-commit"
HOOKS_DIR="$(git rev-parse --git-path hooks)"

mkdir -p "$HOOKS_DIR"
cp "$SRC" "$HOOKS_DIR/pre-commit"
chmod +x "$HOOKS_DIR/pre-commit"

echo "Installed pre-commit hook to $HOOKS_DIR/pre-commit"
```

```bash
chmod +x tools/install-hooks.sh
```

- [ ] **Step 3: Test in a plain (non-worktree) scratch repo**

```bash
rm -rf /tmp/gh-pages-install-test
mkdir -p /tmp/gh-pages-install-test/tools/hooks
cp tools/hooks/pre-commit /tmp/gh-pages-install-test/tools/hooks/pre-commit
cp tools/install-hooks.sh /tmp/gh-pages-install-test/tools/install-hooks.sh
cd /tmp/gh-pages-install-test
git init -q
bash tools/install-hooks.sh
diff tools/hooks/pre-commit .git/hooks/pre-commit && echo "IDENTICAL"
test -x .git/hooks/pre-commit && echo "EXECUTABLE"
```
Expected: `Installed pre-commit hook to .../.git/hooks/pre-commit`, then `IDENTICAL`, then `EXECUTABLE`.

- [ ] **Step 4: Test in a worktree (mirrors this project's actual setup)**

```bash
cd /tmp/gh-pages-install-test
git commit -q --allow-empty -m init
git branch feature
git worktree add /tmp/gh-pages-install-test-wt feature -q
cd /tmp/gh-pages-install-test-wt
mkdir -p tools/hooks
cp /tmp/gh-pages-install-test/tools/hooks/pre-commit tools/hooks/pre-commit
cp /tmp/gh-pages-install-test/tools/install-hooks.sh tools/install-hooks.sh
bash tools/install-hooks.sh
git rev-parse --git-path hooks
```
Expected: the install script succeeds and prints an installed-hook path pointing into the **shared** `.git/hooks` dir under `/tmp/gh-pages-install-test/.git/hooks/pre-commit` (not a worktree-local path), confirming the hook applies repo-wide across worktrees.

- [ ] **Step 5: Clean up scratch repos**

```bash
cd -
git -C /tmp/gh-pages-install-test worktree remove /tmp/gh-pages-install-test-wt --force 2>/dev/null || true
rm -rf /tmp/gh-pages-install-test /tmp/gh-pages-install-test-wt
```

- [ ] **Step 6: Commit**

```bash
git add tools/install-hooks.sh
git commit -m "$(cat <<'EOF'
Add tools/install-hooks.sh to install the publish pre-commit hook

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 6: Integration — publish real v1 and enable Pages

**Files:**
- Modify: none new; produces real content under `github-pages/` in this repo (`versions.json`, `index.html`, `v1/*`).

**Interfaces:**
- Consumes: everything from Tasks 1–5, exercised together for the first time end-to-end.
- Produces: the first real published version, live on GitHub Pages once pushed.

- [ ] **Step 1: Install the hook in this working copy**

Run: `bash tools/install-hooks.sh`
Expected: `Installed pre-commit hook to <path>/.git/hooks/pre-commit`.

- [ ] **Step 2: Stage the first version**

Run: `bash tools/new-version.sh "First drivable prototype: drift physics, damage system, win condition."`
Expected: `Staged v1: "First drivable prototype: ..."` and the commit reminder.

- [ ] **Step 3: Commit — this triggers the real Godot export via the hook**

```bash
git commit -m "$(cat <<'EOF'
Publish v1: first drivable prototype

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```
Expected: hook output shows `Building v1 (v1)...` then `Published v1.`, and the commit succeeds. If it fails with a missing-preset or missing-templates error, stop and re-verify Task 1 was completed correctly.

- [ ] **Step 4: Verify the build output**

Run: `ls github-pages/v1/ && cat github-pages/index.html`
Expected: `github-pages/v1/` contains at least `index.html`, `index.js`, `index.wasm`, `index.pck`; `github-pages/index.html` shows a `v1` entry with the summary text and a link to `v1/index.html`.

- [ ] **Step 5: Serve locally and verify it plays in a browser**

```bash
cd github-pages && python3 -m http.server 8765 &
```
Open `http://localhost:8765/` in a browser — confirm the index page lists v1 with its summary, click through to `v1/index.html`, confirm the game loads and is playable, and confirm the browser console has no COOP/COEP or SharedArrayBuffer errors. Then stop the server:
```bash
kill %1
cd -
```

- [ ] **Step 6: Verify the hook no-ops on an unrelated commit**

```bash
echo "" >> README.md
git add README.md
git commit -m "test: confirm hook no-ops on non-publish commits"
```
Expected: commit completes instantly with no "Building..." output (README.md doesn't touch `github-pages/versions.json`). Then revert this throwaway change:
```bash
git revert --no-edit HEAD
```

- [ ] **Step 7: Enable GitHub Pages (requires user confirmation before touching repo settings)**

Ask the user: "Ready to enable GitHub Pages for this repo — Settings → Pages → Source: Deploy from a branch → Branch `main`, folder `/github-pages`. This makes the site publicly accessible at `https://sbarton272.github.io/godot-firetruck-dog/`. Want me to set this via `gh api`, or will you do it yourself in the GitHub UI?"

If the user approves doing it via API:
```bash
gh api repos/sbarton272/godot-firetruck-dog/pages -X POST -f "source[branch]=main" -f "source[path]=/github-pages"
```

- [ ] **Step 8: Push and confirm the live site**

Ask the user before pushing (pushing to `main` is visible to others). Once approved:
```bash
git push
```
Then check `https://sbarton272.github.io/godot-firetruck-dog/` after GitHub Pages finishes its first build (may take a minute or two) and confirm v1 is playable there too.
