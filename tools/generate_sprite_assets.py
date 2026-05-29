"""
Generate project-local PNG sprites for the Pygame version of Aswang Hunter.

These assets are intentionally simple pixel-art-style placeholders. They give
the game real image files now and can be replaced later with downloaded art
using the same filenames.
"""

from pathlib import Path
import math

import pygame


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "sprite"


def surface(size):
    return pygame.Surface(size, pygame.SRCALPHA)


def glow(surf, center, color, radius, alpha=80):
    gx, gy = center
    for r in range(radius, 0, -3):
        a = int(alpha * (1 - r / radius))
        pygame.draw.circle(surf, (*color, a), (gx, gy), r)


def save(name, surf):
    pygame.image.save(surf, OUT / name)


def make_aswang():
    surf = surface((96, 96))
    glow(surf, (48, 50), (190, 30, 45), 42, 95)

    wing_dark = (55, 8, 15, 255)
    wing_red = (135, 18, 30, 255)
    body = (45, 8, 12, 255)
    outline = (210, 45, 55, 255)
    eye = (255, 225, 90, 255)

    for side in (-1, 1):
        pts = [
            (48, 42),
            (48 + side * 38, 22),
            (48 + side * 29, 50),
            (48 + side * 42, 68),
            (48 + side * 15, 60),
        ]
        pygame.draw.polygon(surf, wing_dark, pts)
        pygame.draw.lines(surf, wing_red, False, pts, 3)
        pygame.draw.line(surf, (95, 10, 18), (48, 45), (48 + side * 29, 50), 2)

    pygame.draw.ellipse(surf, body, (30, 22, 36, 56))
    pygame.draw.ellipse(surf, outline, (30, 22, 36, 56), 2)
    pygame.draw.polygon(surf, (45, 8, 12), [(36, 25), (41, 7), (46, 27)])
    pygame.draw.polygon(surf, (45, 8, 12), [(50, 27), (55, 7), (60, 25)])
    pygame.draw.lines(surf, outline, False, [(36, 25), (41, 7), (46, 27)], 2)
    pygame.draw.lines(surf, outline, False, [(50, 27), (55, 7), (60, 25)], 2)

    for x in (41, 55):
        pygame.draw.circle(surf, eye, (x, 40), 6)
        pygame.draw.circle(surf, (255, 255, 230), (x + 1, 39), 2)
    pygame.draw.arc(surf, outline, (38, 44, 20, 12), 0, math.pi, 2)

    for y in (59, 67):
        pygame.draw.line(surf, (100, 12, 18), (36, y), (28, y + 7), 2)
        pygame.draw.line(surf, (100, 12, 18), (60, y), (68, y + 7), 2)

    return surf


def make_garlic():
    surf = surface((64, 64))
    glow(surf, (32, 34), (230, 235, 130), 26, 75)
    stem = (100, 150, 60, 255)
    shell = (232, 226, 160, 255)
    shade = (178, 170, 95, 255)

    pygame.draw.line(surf, stem, (32, 23), (32, 9), 4)
    pygame.draw.line(surf, stem, (32, 14), (24, 5), 3)
    pygame.draw.line(surf, stem, (32, 14), (41, 6), 3)
    pygame.draw.ellipse(surf, shell, (18, 24, 28, 27))
    pygame.draw.ellipse(surf, (246, 240, 190), (24, 19, 18, 32))
    pygame.draw.ellipse(surf, shade, (18, 24, 28, 27), 2)
    pygame.draw.arc(surf, shade, (22, 24, 12, 27), math.pi * 0.5, math.pi * 1.5, 2)
    pygame.draw.arc(surf, shade, (31, 23, 10, 28), math.pi * 1.5, math.pi * 0.5, 2)
    pygame.draw.circle(surf, (255, 250, 215), (30, 28), 4)
    return surf


def make_holy_water():
    surf = surface((64, 64))
    glow(surf, (32, 35), (90, 180, 255), 26, 75)
    glass = (120, 205, 255, 180)
    water = (55, 145, 230, 235)
    outline = (190, 230, 255, 255)

    pygame.draw.rect(surf, (145, 85, 45), (25, 8, 14, 8), border_radius=2)
    pygame.draw.rect(surf, outline, (27, 15, 10, 8), 1)
    pygame.draw.rect(surf, glass, (20, 21, 24, 31), border_radius=6)
    pygame.draw.rect(surf, water, (22, 33, 20, 17), border_radius=4)
    pygame.draw.rect(surf, outline, (20, 21, 24, 31), 2, border_radius=6)
    pygame.draw.line(surf, (235, 250, 255), (26, 25), (26, 45), 2)
    pygame.draw.line(surf, (235, 250, 255), (31, 29), (38, 29), 2)
    pygame.draw.line(surf, (235, 250, 255), (35, 25), (35, 34), 2)
    return surf


def make_amulet():
    surf = surface((64, 64))
    glow(surf, (32, 32), (210, 90, 255), 29, 85)
    purple = (160, 40, 205, 255)
    light = (245, 170, 255, 255)
    gold = (245, 195, 75, 255)

    pygame.draw.circle(surf, gold, (32, 16), 9, 3)
    pygame.draw.rect(surf, purple, (28, 15, 8, 36), border_radius=3)
    pygame.draw.rect(surf, purple, (18, 27, 28, 8), border_radius=3)
    pygame.draw.rect(surf, light, (30, 17, 4, 32), border_radius=2)
    pygame.draw.rect(surf, light, (20, 29, 24, 4), border_radius=2)
    pygame.draw.rect(surf, gold, (27, 14, 10, 38), 2, border_radius=3)
    pygame.draw.rect(surf, gold, (17, 26, 30, 10), 2, border_radius=3)
    for pos in ((32, 22), (32, 43), (23, 31), (41, 31)):
        pygame.draw.circle(surf, (255, 230, 255), pos, 3)
    return surf


def make_floor_tile():
    surf = surface((68, 68))
    base = (23, 33, 24)
    surf.fill(base)

    for y in range(68):
        for x in range(68):
            noise = ((x * 17 + y * 29 + x * y * 3) % 19) - 9
            color = (
                max(0, min(255, base[0] + noise // 3)),
                max(0, min(255, base[1] + noise)),
                max(0, min(255, base[2] + noise // 2)),
            )
            surf.set_at((x, y), color)

    moss = (36, 57, 35)
    shadow = (14, 22, 16)
    for x, y, w, h in (
        (6, 9, 14, 7),
        (42, 7, 11, 5),
        (23, 31, 18, 8),
        (51, 43, 10, 6),
        (10, 53, 17, 7),
    ):
        pygame.draw.ellipse(surf, moss, (x, y, w, h))

    for x, y, w, h in (
        (31, 12, 19, 8),
        (5, 37, 12, 5),
        (41, 58, 18, 5),
    ):
        pygame.draw.ellipse(surf, shadow, (x, y, w, h))

    for x, y in ((13, 12), (48, 10), (30, 34), (55, 47), (17, 56)):
        pygame.draw.circle(surf, (51, 75, 48), (x, y), 1)

    return surf


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    pygame.init()
    save("aswang.png", make_aswang())
    save("garlic.png", make_garlic())
    save("holy_water.png", make_holy_water())
    save("amulet.png", make_amulet())
    save("tile_floor.png", make_floor_tile())


if __name__ == "__main__":
    main()
