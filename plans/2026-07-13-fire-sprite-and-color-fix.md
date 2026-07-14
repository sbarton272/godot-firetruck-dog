# Fire Sprite + Color Exposure Fix Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (or superpowers:executing-plans) to implement this plan task-by-task.

**Goal:** Fix the washed-out lighting so the muted palette reads correctly, and replace the two compute-heavy `CPUParticles3D` fire/smoke emitters with one cheap animated flame sprite (smoke baked into its frames).

**Architecture:** Lower the environment light/ambient energy in `GameEnvironment.tscn`. Generate a small looping flame-with-smoke flipbook PNG via a committed `uv run` (PEP 723 + pillow) script. Rewrite `FireSmoke.tscn` to a single billboarded `AnimatedSprite3D` driven by a `SpriteFrames` built from that flipbook — keeping the scene's `uid` so `Main.tscn` is untouched.

**Tech Stack:** Godot 4.7 (GL Compatibility), GDScript scenes (`.tscn` text format), Python via `uv` + Pillow for asset generation. No unit-test framework — verification is by headless Web export + in-browser screenshot (the loop already used in this repo).

## Global Constraints

- Godot 4.7, GL Compatibility renderer. Verify any `.tscn`/API detail against https://docs.godotengine.org/en/4.7/ .
- `FireSmoke.tscn` MUST keep `uid="uid://c1f2i3r4e5s6m"` in its `[gd_scene ...]` header — `Main.tscn:4` references it by that uid.
- Do NOT export into `github-pages/` during verification (that would create a new published version). Export to a throwaway dir like `/tmp/fx-test/`.
- Run Godot/uv from a `direnv allow`'d checkout (or via `direnv exec .`) so `godot`, `uv` resolve.
- Keep the three pieces as separate commits (exposure, asset, scene) — this is game content, distinct from the publishing commits on the branch.

---

### Task 1: Fix washed-out exposure

**Files:**
- Modify: `scenes/env/GameEnvironment.tscn`

**Step 1: Lower the directional light energy**

In `scenes/env/GameEnvironment.tscn`, change the `DirectionalLight3D` line:
```
light_energy = 1.1
```
to:
```
light_energy = 0.85
```

**Step 2: Lower the ambient energy**

In the `[sub_resource type="Environment" id="Environment_1"]` block, change:
```
ambient_light_energy = 0.6
```
to:
```
ambient_light_energy = 0.3
```
Leave `tonemap_mode = 2`, the `Sky` colors, and the light direction/color unchanged.

**Step 3: Verify the scene still parses (headless import)**

Run:
```bash
direnv exec . godot --headless --path . --quit-after 200 2>&1 | grep -iE 'error|SCRIPT ERROR|Failed' || echo "no load errors"
```
Expected: `no load errors` (a clean scan; ignore any non-error INFO lines). If `--quit-after` is unavailable in this build, skip — the export in Task 3 is the real check.

**Step 4: Commit**

```bash
git add scenes/env/GameEnvironment.tscn
git commit -m "$(cat <<'EOF'
Reduce scene exposure so the muted palette reads (not blown out)

Directional light 1.1->0.85 and ambient 0.6->0.3; the over-lighting was
clipping the intended low-poly colors toward white.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

(Fine-tuning of the exact energies happens in Task 4 against a real render; commit these starting values now.)

---

### Task 2: Generate the flame flipbook asset

**Files:**
- Create: `tools/gen_fire_flipbook.py`
- Create (generated): `art/effects/fire_flipbook.png`

**Step 1: Write the generator script**

Create `tools/gen_fire_flipbook.py`:
```python
#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.9"
# dependencies = ["pillow>=10"]
# ///
"""Generate a simple looping flame-with-smoke flipbook as a horizontal sprite
sheet PNG for the burning-building effect. Tweak the constants and re-run to
adjust the look."""
import math
import pathlib

from PIL import Image, ImageDraw

FRAMES = 6
FW, FH = 64, 96  # per-frame width, height

# Flame layers, outer -> core: (RGBA, width_scale, height_scale)
LAYERS = [
    ((214, 78, 18, 255), 1.00, 1.00),   # deep orange
    ((242, 140, 30, 255), 0.72, 0.86),  # orange
    ((255, 205, 70, 255), 0.46, 0.66),  # yellow
    ((255, 244, 200, 255), 0.24, 0.42),  # pale core
]


def draw_flame(draw: ImageDraw.ImageDraw, ox: int, phase: float) -> None:
    base_y = FH - 6
    cx = FW // 2
    for color, ws, hs in LAYERS:
        w = FW * 0.42 * ws
        h = FH * 0.80 * hs
        tip_dx = math.sin(phase * math.tau) * 6 * (1.3 - hs)
        top_y = base_y - h
        draw.ellipse(
            [ox + cx - w / 2, base_y - w, ox + cx + w / 2, base_y + w * 0.15],
            fill=color,
        )
        draw.polygon(
            [
                (ox + cx - w / 2, base_y - w * 0.5),
                (ox + cx + w / 2, base_y - w * 0.5),
                (ox + cx + tip_dx, top_y),
            ],
            fill=color,
        )


def draw_smoke(draw: ImageDraw.ImageDraw, ox: int, phase: float) -> None:
    for k in range(2):
        t = (phase + k * 0.5) % 1.0
        y = 30 - t * 26
        r = 7 + t * 6
        alpha = int(70 * (1.0 - t))
        x = FW // 2 + math.sin((phase + k) * math.tau) * 5
        draw.ellipse([ox + x - r, y - r, ox + x + r, y + r], fill=(90, 90, 95, alpha))


def main() -> None:
    sheet = Image.new("RGBA", (FW * FRAMES, FH), (0, 0, 0, 0))
    draw = ImageDraw.Draw(sheet)
    for i in range(FRAMES):
        phase = i / FRAMES
        ox = i * FW
        draw_smoke(draw, ox, phase)   # smoke behind
        draw_flame(draw, ox, phase)   # flame in front
    out = pathlib.Path(__file__).resolve().parent.parent / "art" / "effects" / "fire_flipbook.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)
    print(f"wrote {out} ({sheet.size[0]}x{sheet.size[1]}, {FRAMES} frames of {FW}x{FH})")


if __name__ == "__main__":
    main()
```

**Step 2: Generate the PNG**

Run:
```bash
direnv exec . uv run tools/gen_fire_flipbook.py
```
Expected: prints `wrote .../art/effects/fire_flipbook.png (384x96, 6 frames of 64x96)`; the file exists.

**Step 3: Sanity-check the image**

Run:
```bash
direnv exec . uv run --with pillow python -c "from PIL import Image; im=Image.open('art/effects/fire_flipbook.png'); print(im.size, im.mode); print('has_alpha', im.getextrema()[3])"
```
Expected: `(384, 96) RGBA` and a non-trivial alpha range (e.g. `(0, 255)`) — confirms transparency and drawn pixels.

**Step 4: Commit the generator + asset**

```bash
git add tools/gen_fire_flipbook.py art/effects/fire_flipbook.png
git commit -m "$(cat <<'EOF'
Add flame flipbook asset + generator (uv/pillow)

A small 6-frame fire+smoke sprite sheet for the burning-building effect,
reproducible via tools/gen_fire_flipbook.py.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: Replace particles with an AnimatedSprite3D

**Files:**
- Rewrite: `scenes/effects/FireSmoke.tscn`

**Step 1: Rewrite `FireSmoke.tscn`**

Replace the ENTIRE file with the following. Note the preserved `uid`, and the texture referenced by path (Godot resolves + adds its own uid on first import):

```
[gd_scene load_steps=9 format=3 uid="uid://c1f2i3r4e5s6m"]

[ext_resource type="Texture2D" path="res://art/effects/fire_flipbook.png" id="1_flame"]

[sub_resource type="AtlasTexture" id="Atlas_0"]
atlas = ExtResource("1_flame")
region = Rect2(0, 0, 64, 96)

[sub_resource type="AtlasTexture" id="Atlas_1"]
atlas = ExtResource("1_flame")
region = Rect2(64, 0, 64, 96)

[sub_resource type="AtlasTexture" id="Atlas_2"]
atlas = ExtResource("1_flame")
region = Rect2(128, 0, 64, 96)

[sub_resource type="AtlasTexture" id="Atlas_3"]
atlas = ExtResource("1_flame")
region = Rect2(192, 0, 64, 96)

[sub_resource type="AtlasTexture" id="Atlas_4"]
atlas = ExtResource("1_flame")
region = Rect2(256, 0, 64, 96)

[sub_resource type="AtlasTexture" id="Atlas_5"]
atlas = ExtResource("1_flame")
region = Rect2(320, 0, 64, 96)

[sub_resource type="SpriteFrames" id="SpriteFrames_fire"]
animations = [{
"frames": [{
"duration": 1.0,
"texture": SubResource("Atlas_0")
}, {
"duration": 1.0,
"texture": SubResource("Atlas_1")
}, {
"duration": 1.0,
"texture": SubResource("Atlas_2")
}, {
"duration": 1.0,
"texture": SubResource("Atlas_3")
}, {
"duration": 1.0,
"texture": SubResource("Atlas_4")
}, {
"duration": 1.0,
"texture": SubResource("Atlas_5")
}],
"loop": true,
"name": &"default",
"speed": 10.0
}]

[node name="FireSmoke" type="Node3D"]

[node name="Flame" type="AnimatedSprite3D" parent="."]
transform = Transform3D(1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0.5, 0)
billboard = 1
pixel_size = 0.012
sprite_frames = SubResource("SpriteFrames_fire")
autoplay = "default"
```

Notes for the implementer:
- `load_steps = 9` = 1 ext_resource + 6 AtlasTexture + 1 SpriteFrames + 1.
- `billboard = 1` is full billboard (faces camera). If the flame looks tilted/laid-back under the fixed top-down camera, try `billboard = 2` (fixed-Y, stays upright) during Task 4.
- `pixel_size = 0.012` → ~0.77 × 1.15 m. Adjust in Task 4 to match the old flame scale.
- `AnimatedSprite3D` defaults already give unshaded + transparent + double-sided, so no extra flags needed.

**Step 2: Confirm no particle nodes remain**

Run:
```bash
grep -c 'CPUParticles3D\|GPUParticles3D' scenes/effects/FireSmoke.tscn || true
```
Expected: `0` (grep prints `0` or exits non-zero with no matches — either way, no particle nodes).

Run:
```bash
grep -c 'AnimatedSprite3D' scenes/effects/FireSmoke.tscn
```
Expected: `1`.

**Step 3: Verify uid preserved (Main.tscn stays valid)**

Run:
```bash
head -1 scenes/effects/FireSmoke.tscn | grep -q 'uid://c1f2i3r4e5s6m' && echo "uid OK"
```
Expected: `uid OK`.

**Step 4: Commit**

```bash
git add scenes/effects/FireSmoke.tscn
git commit -m "$(cat <<'EOF'
Replace fire/smoke particles with a single AnimatedSprite3D flame

Swaps two CPUParticles3D emitters for one billboarded sprite flipbook to
cut per-frame compute (esp. on the Web export). Scene uid preserved so
Main.tscn's instance is unchanged.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: Verify end-to-end and tune

**Files:** none (verification + possible small re-tweaks to Task 1 values / Task 3 `billboard`,`pixel_size` / Task 2 constants).

**Step 1: Export to a throwaway dir (triggers asset import)**

```bash
rm -rf /tmp/fx-test && mkdir -p /tmp/fx-test
direnv exec . godot --headless --path . --export-release "Web" /tmp/fx-test/index.html 2>&1 | tail -20
```
Expected: an export that reports `savepack ... DONE` with no `ERROR`. The first run also imports `fire_flipbook.png`. If the very first run warns that the texture can't be found (import race), simply run the same command a second time — the `.import` now exists.

**Step 2: Serve and screenshot in-browser**

Start a server (foreground, in a background task so it stays up):
```bash
cd /tmp/fx-test && python3 -m http.server 8799
```
Then load `http://localhost:8799/` in the browser, wait ~6s for the engine to boot, and screenshot. Confirm:
- Buildings and ground render as their muted colors (sage ground, cream/varied buildings) — **not** near-white.
- At the goal/burning building there is an **animated flame** (cycles through frames) with a faint smoke wisp, facing the camera.
- Console shows no errors (`read_console_messages onlyErrors`), and still reports `single-threaded, no GDExtension support`.
Stop the server when done.

**Step 3: Tune if needed**

- Still washed out → lower `light_energy`/`ambient_light_energy` further in `GameEnvironment.tscn` (e.g. 0.75 / 0.2) and re-export.
- Too dark → nudge them back up.
- Flame tilted → set `billboard = 2` in `FireSmoke.tscn`. Wrong size → adjust `pixel_size`. Flame shape ugly → tweak constants in `tools/gen_fire_flipbook.py`, re-run it, re-export.
- Re-run Steps 1–2 after any change. Amend or add follow-up commits to the relevant task's commit as appropriate.

**Step 4: Final confirmation**

Capture a final screenshot showing corrected colors + animated flame, and note the final tuned values in the commit message(s). Do NOT publish a new `github-pages/vN` here — that is a separate, deliberate `tools/publish-version.sh` run the user chooses to do later.
