# Fire Sprite + Color Exposure Fix — Design

## Goal

Two game-visuals fixes for the burning-building effect and overall look:

1. The scene renders washed-out / overexposed — the intended muted low-poly palette
   clips toward white. Fix the lighting so the existing colors read properly.
2. The fire/smoke effect uses two `CPUParticles3D` emitters, which are too
   compute-heavy (especially on the Web export). Replace them with one cheap
   animated sprite of fire (with a little smoke baked in).

## Non-goals

- No new object/building palette. The per-object albedo colors (ground, buildings,
  obstacles) are already the intended muted tones and stay as-is.
- No shader work. A plain animated billboard sprite is sufficient.
- Not part of the GitHub Pages publishing feature — this is separate game content.
  It lands on the same branch (`cl/github-pages-publish-...`) per the user's choice,
  but as clearly-labeled separate commits so it can be disentangled if needed.

## Current state

- `scenes/env/GameEnvironment.tscn`: `DirectionalLight3D.light_energy = 1.1`,
  `Environment.ambient_light_energy = 0.6`, `ambient_light_source = 3` (Sky),
  `tonemap_mode = 2` (filmic). Combined energy pushes muted albedos (e.g. building
  `Color(0.82, 0.76, 0.62)`) up toward clipping, so surfaces render near-white.
- `scenes/effects/FireSmoke.tscn`: a `Node3D` root named `FireSmoke` containing two
  `CPUParticles3D` — `Fire` (amount 20) and `Smoke` (amount 14) — each a billboarded
  `QuadMesh` with an unshaded transparent material. Instanced into `Main.tscn` at the
  burning/goal building.
- No sprite/texture assets exist besides `icon.svg`.

## Design

### 1. Exposure fix — `scenes/env/GameEnvironment.tscn`

Reduce lighting energy so lit surfaces sit below clipping and the muted palette shows:

- `DirectionalLight3D.light_energy`: 1.1 → ~0.85 (tune during verification)
- `Environment.ambient_light_energy`: 0.6 → ~0.3 (tune during verification)
- Keep `tonemap_mode = 2` (filmic), the sky colors, and the light direction/color.

Final values are dialed in by eye against a test render; the starting points above
are the design intent (meaningfully less total light).

### 2. Flame flipbook asset

- A one-off generator script (committed) draws a small horizontal sprite sheet:
  ~6 frames of a stylized flame in the game's warm orange/yellow palette, with a
  faint smoke wisp baked into the upper portion of the frames, on a transparent
  background. Frames loop seamlessly.
- The script runs via `uv` with an inline PEP 723 `dependencies = ["pillow"]`, so
  the asset is reproducible/tweakable without adding a project-wide Python dep.
- Output committed as `art/effects/fire_flipbook.png` (a new `art/` dir), imported by
  Godot with filter off (crisp) or on (soft) — chosen during verification for best look.

### 3. Effect scene rework — `scenes/effects/FireSmoke.tscn`

- Remove both `CPUParticles3D` nodes and their particle sub-resources.
- Add a single `AnimatedSprite3D`:
  - `billboard` enabled (faces camera), `shaded` off, `shadow` off (no casting),
    `transparent` on, `alpha_cut` set so edges don't z-fight.
  - `SpriteFrames` resource with one looping animation built from the flipbook's
    frames as `AtlasTexture` regions, ~8–12 fps.
  - Positioned/scaled so the flame sits roughly where the old fire was and at a
    similar height.
- Root stays `Node3D` named `FireSmoke` so the instance point in `Main.tscn` is
  unchanged (no edits needed to `Main.tscn`).

### 4. Verification

- Export the game to a throwaway dir (e.g. `/tmp/fire-test/`) via
  `godot --headless --export-release "Web" /tmp/fire-test/index.html` — NOT into
  `github-pages/` (don't create a new published version).
- Serve it and screenshot in-browser; confirm:
  - Buildings/ground render as muted colors, not white.
  - The flame animates and faces the camera at the burning building.
  - No particle emitters remain (grep the scene) — compute cost is one sprite.
- Compare against the pre-change screenshot.

### 5. Commits

Separate, clearly-labeled commits: (a) exposure fix, (b) flame asset + generator,
(c) effect scene rework. Distinct from the publishing commits on the branch.

## Open questions / follow-ups

- Exact light energies and sprite fps/scale are tuning parameters finalized during
  verification, not fixed values in this design.
