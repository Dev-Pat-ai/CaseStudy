"""
Extract the playable Aswang flying animation from the full reference sheet.

Usage:
    python tools/extract_aswang_sprite_sheet.py C:/path/to/Aswang.png

The source sheet has labels and blue panel backgrounds. This script crops the
IDLE - FLYING row, removes the connected panel background, trims each sprite,
and packs the frames into assets/sprite/aswang_flying.png.
"""

from collections import deque
from pathlib import Path
import sys

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "sprite" / "aswang_flying.png"
FRAME_W = 128
FRAME_H = 96

# x, y, width, height for the four IDLE - FLYING panels.
IDLE_PANELS = [
    (17, 60, 239, 154),
    (272, 60, 231, 154),
    (520, 60, 231, 154),
    (767, 60, 240, 154),
]


def is_background(pixel):
    r, g, b, _ = pixel
    return b > 70 and b > r + 34 and b > g + 18 and r < 85 and g < 95


def remove_connected_background(img):
    pixels = img.load()
    width, height = img.size
    seen = set()
    queue = deque()

    for x in range(width):
        queue.append((x, 0))
        queue.append((x, height - 1))
    for y in range(height):
        queue.append((0, y))
        queue.append((width - 1, y))

    while queue:
        x, y = queue.popleft()
        if (x, y) in seen or not (0 <= x < width and 0 <= y < height):
            continue
        seen.add((x, y))
        if not is_background(pixels[x, y]):
            continue

        pixels[x, y] = (0, 0, 0, 0)
        queue.extend(((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)))

    return img


def trim_alpha(img, padding=4):
    alpha = img.getchannel("A")
    bbox = alpha.getbbox()
    if bbox is None:
        return img

    left, top, right, bottom = bbox
    left = max(0, left - padding)
    top = max(0, top - padding)
    right = min(img.width, right + padding)
    bottom = min(img.height, bottom + padding)
    return img.crop((left, top, right, bottom))


def fit_frame(sprite):
    sprite = trim_alpha(sprite)
    scale = min((FRAME_W - 8) / sprite.width, (FRAME_H - 8) / sprite.height)
    new_size = (max(1, int(sprite.width * scale)), max(1, int(sprite.height * scale)))
    sprite = sprite.resize(new_size, Image.Resampling.NEAREST)

    frame = Image.new("RGBA", (FRAME_W, FRAME_H), (0, 0, 0, 0))
    x = (FRAME_W - sprite.width) // 2
    y = (FRAME_H - sprite.height) // 2
    frame.alpha_composite(sprite, (x, y))
    return frame


def extract(source_path):
    source = Image.open(source_path).convert("RGBA")
    sheet = Image.new("RGBA", (FRAME_W * len(IDLE_PANELS), FRAME_H), (0, 0, 0, 0))

    for index, rect in enumerate(IDLE_PANELS):
        x, y, width, height = rect
        panel = source.crop((x, y, x + width, y + height))
        panel = remove_connected_background(panel)
        frame = fit_frame(panel)
        sheet.alpha_composite(frame, (index * FRAME_W, 0))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(OUT)
    return OUT


def main():
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python tools/extract_aswang_sprite_sheet.py C:/path/to/Aswang.png")

    out = extract(Path(sys.argv[1]))
    print(out)


if __name__ == "__main__":
    main()
