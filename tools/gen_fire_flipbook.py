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
