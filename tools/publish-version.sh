#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 || -z "$1" ]]; then
  echo "Usage: tools/publish-version.sh \"<summary of this version>\"" >&2
  exit 1
fi

SUMMARY="$1"
REPO_ROOT="$(git rev-parse --show-toplevel)"
SITE_DIR="$REPO_ROOT/site"
VERSIONS_JSON="$SITE_DIR/versions.json"

if ! command -v godot >/dev/null 2>&1; then
  echo "ERROR: 'godot' not found on PATH. Install Godot 4.7 to publish a version." >&2
  exit 1
fi

if ! command -v jq >/dev/null 2>&1; then
  echo "ERROR: 'jq' not found on PATH. Install jq (e.g. 'brew install jq') to publish a version." >&2
  exit 1
fi

if ! command -v uv >/dev/null 2>&1; then
  echo "ERROR: 'uv' not found on PATH. Run 'direnv allow' (installs the pinned toolchain via mise), or install uv." >&2
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

mkdir -p "$SITE_DIR"
if [[ ! -f "$VERSIONS_JSON" ]]; then
  echo "[]" > "$VERSIONS_JSON"
fi

# GitHub Pages serves this folder directly; disable Jekyll so it doesn't filter
# or mangle the exported build's files/folders.
touch "$SITE_DIR/.nojekyll"
# The export is written inside the Godot project (res://site/); a .gdignore
# stops the editor from importing the build output (e.g. the .png boot splash),
# which would otherwise clutter the project with .import files on every publish.
touch "$SITE_DIR/.gdignore"

COUNT=$(jq 'length' "$VERSIONS_JSON")
NEXT_VERSION="v$((COUNT + 1))"
TODAY=$(date +%Y-%m-%d)
BUILD_DIR="$SITE_DIR/$NEXT_VERSION"
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

uv run "$REPO_ROOT/tools/generate_index.py"

git -C "$REPO_ROOT" add "$VERSIONS_JSON" "$BUILD_DIR" "$SITE_DIR/index.html" \
  "$SITE_DIR/.nojekyll" "$SITE_DIR/.gdignore"

echo "Published $NEXT_VERSION: \"$SUMMARY\""
echo "Review the diff and run 'git commit' to finish publishing."
