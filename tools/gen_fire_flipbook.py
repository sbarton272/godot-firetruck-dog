#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.9"
# dependencies = ["pillow>=10"]
# ///
"""Generate a looping, comically-large multi-tendril flame flipbook as a
horizontal sprite sheet PNG for the burning-building effect. Several wavy
flame tongues of varying height wobble over the loop, with a couple of faint
smoke puffs. Tweak the constants and re-run to adjust the look."""
import math
import pathlib

from PIL import Image, ImageDraw

FRAMES = 6
FW, FH = 128, 160  # per-frame width, height (roomy: many tall tendrils)

# Flame color layers, outer -> core: (RGBA, radius_scale)
LAYERS = [
    ((214, 78, 18, 255), 1.00),   # deep orange
    ((242, 140, 30, 255), 0.66),  # orange
    ((255, 205, 70, 255), 0.40),  # yellow
    ((255, 244, 200, 255), 0.18),  # pale core
]

# Tendrils: (base_x_frac, height_frac, base_radius_frac, wobble_px, phase_offset)
TENDRILS = [
    (0.24, 0.60, 0.15, 12, 0.00),
    (0.40, 0.98, 0.19, 18, 0.35),
    (0.53, 0.80, 0.16, 15, 0.62),
    (0.66, 1.00, 0.21, 20, 0.15),
    (0.80, 0.55, 0.13, 11, 0.80),
]


def draw_tendril(draw, ox, phase, bx, hf, brf, wob, poff):
    """Draw one wavy flame tongue as a tapering stack of layered circles."""
    base_y = FH - 8
    top_y = base_y - FH * 0.9 * hf
    base_r = FW * brf
    steps = 30
    for color, rs in LAYERS:
        for s in range(steps + 1):
            t = s / steps
            y = base_y + (top_y - base_y) * t
            r = max(1.0, base_r * rs * (1.0 - t) ** 0.7)
            # sway grows toward the tip and animates with the loop phase
            wave = math.sin((phase + poff + t * 1.3) * math.tau) * wob * (t ** 1.3)
            x = ox + FW * bx + wave
            draw.ellipse([x - r, y - r, x + r, y + r], fill=color)


def draw_base_glow(draw, ox, phase):
    """A wide low ember pool so the tendrils read as one fire."""
    base_y = FH - 8
    w = FW * 0.40
    h = FH * 0.12
    cx = ox + FW * 0.52
    draw.ellipse([cx - w, base_y - h, cx + w, base_y + h * 0.6], fill=(214, 78, 18, 255))
    draw.ellipse([cx - w * 0.6, base_y - h * 0.8, cx + w * 0.6, base_y + h * 0.3],
                 fill=(242, 140, 30, 255))


def draw_smoke(draw, ox, phase):
    for k in range(2):
        t = (phase + k * 0.5) % 1.0
        y = FH * 0.30 - t * FH * 0.28
        r = 10 + t * 12
        alpha = int(60 * (1.0 - t))
        x = ox + FW * 0.52 + math.sin((phase + k) * math.tau) * 8
        draw.ellipse([x - r, y - r, x + r, y + r], fill=(92, 92, 98, alpha))


def main() -> None:
    sheet = Image.new("RGBA", (FW * FRAMES, FH), (0, 0, 0, 0))
    draw = ImageDraw.Draw(sheet)
    for i in range(FRAMES):
        phase = i / FRAMES
        ox = i * FW
        draw_smoke(draw, ox, phase)          # smoke behind
        draw_base_glow(draw, ox, phase)
        # taller tendrils drawn first so shorter ones sit in front
        for bx, hf, brf, wob, poff in sorted(TENDRILS, key=lambda t: -t[1]):
            draw_tendril(draw, ox, phase, bx, hf, brf, wob, poff)
    out = pathlib.Path(__file__).resolve().parent.parent / "art" / "effects" / "fire_flipbook.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)
    print(f"wrote {out} ({sheet.size[0]}x{sheet.size[1]}, {FRAMES} frames of {FW}x{FH})")


if __name__ == "__main__":
    main()
