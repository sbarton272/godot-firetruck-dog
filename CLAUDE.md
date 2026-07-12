# Firetruck Dog

A Godot game project. Engine version: **Godot 4.7** (GL Compatibility renderer).

## Project layout

- `project.godot` — Godot project config (engine version, features, renderer).
- `.godot/` — engine-generated cache, gitignored, never edit by hand.
- `docs/plans/` — implementation plans for multi-step features/changes go here (see `writing-plans` skill).
- `worktrees/` — git worktrees used for isolated feature work, gitignored.

## Godot documentation

When you need Godot API or engine behavior details, check docs in this order:

1. **Version-matched official docs**: https://docs.godotengine.org/en/4.7/ — this project targets 4.7, so always confirm any API/behavior against the 4.7 branch of the docs, not `stable`/`latest`, since APIs shift between minor versions.
2. **Class reference**: https://docs.godotengine.org/en/4.7/classes/ for GDScript/node API signatures (e.g. `CharacterBody2D`, `AnimationPlayer`).
3. **In-editor docs**: the Godot editor's built-in Script/Help search mirrors the class reference and is useful if working interactively in the editor.

Do not assume GDScript/API details from memory without verifying against the 4.7 docs — Godot's API has changed significantly across major versions (3.x vs 4.x), and even minor 4.x versions add/deprecate methods.

## Plans

Save implementation plans for non-trivial features to `docs/plans/` as markdown files before starting multi-step work.
