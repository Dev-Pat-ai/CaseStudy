"""
sprites.py
Procedural sprite-drawing helpers.
Every function receives a pygame Surface as its first argument so that
they can be used on any surface (grid_surf, screen, HUD panel, etc.).
"""

import pygame
import math
from typing import Optional

from .constants import (
    C_TREE_TRK, C_TREE_TOP, C_TREE_TOP2, C_TREE_SHD,
    C_HUNTER, C_HUNTER2, C_ASWANG, C_ASWANG2, C_EYE,
    C_GARLIC, C_WATER, C_AMULET,
    C_GOLD, C_WHITE,
)
from .hunter_sprite import HunterSprite


# ─────────────────────────────────────────────
#  HUNTER SPRITE  (module-level singleton)
# ─────────────────────────────────────────────
_hunter_sprite: Optional[HunterSprite] = None


def load_hunter_sprite(sheet_path: str, frame_w: int, frame_h: int, scale: float = 0.25):
    """
    Call this ONCE during game initialisation (after pygame.init()).
    Example:
        load_hunter_sprite("assets/sprite/sprite_hunter.png", 313, 282, 0.25)
    """
    global _hunter_sprite
    _hunter_sprite = HunterSprite(sheet_path, frame_w, frame_h, scale)


# ─────────────────────────────────────────────
#  UTILITY
# ─────────────────────────────────────────────
def draw_glow(surf, color, center, radius, alpha=80):
    """Radial soft-glow centred on *center* with the given *radius*."""
    if radius < 1:
        return
    glow = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
    for r in range(radius, 0, -4):
        a = int(alpha * (1 - r / radius))
        pygame.draw.circle(glow, (*color, a), (radius, radius), r)
    surf.blit(glow, (center[0] - radius, center[1] - radius))


# ─────────────────────────────────────────────
#  ENVIRONMENT
# ─────────────────────────────────────────────
def draw_tree(surf, cx, cy, tick, shade=False):
    """Animated swaying tree with trunk and three canopy layers."""
    tw = 8
    r_off = 10 if shade else 0
    g_off = 5  if shade else 0
    trunk_col = (
        max(0, C_TREE_TRK[0] - r_off),
        max(0, C_TREE_TRK[1] - g_off),
        0,
    )
    pygame.draw.rect(surf, trunk_col, (cx - tw // 2, cy + 6, tw, 18))

    layers = [
        (22, -4,  C_TREE_TOP),
        (18, -12, C_TREE_TOP2),
        (12, -20, C_TREE_TOP),
    ]
    for i, (rad, yoff, col) in enumerate(layers):
        sway = int(math.sin(tick * 0.03 + cx * 0.1) * 1.5)
        c = (max(0, col[0] - i * 5), min(255, col[1] + i * 2), 0)
        pygame.draw.circle(surf, C_TREE_SHD, (cx + sway + 2, cy + yoff + 2), rad)
        pygame.draw.circle(surf, c,           (cx + sway,     cy + yoff),     rad)


# ─────────────────────────────────────────────
#  CHARACTERS
# ─────────────────────────────────────────────
def draw_hunter(surf, cx, cy, tick, direction="down"):
    """
    Draw the hunter using the sprite sheet if loaded,
    otherwise fall back to the original procedural drawing.
    """
    if _hunter_sprite is not None:
        frame = _hunter_sprite.get_frame(direction, tick)
        x = cx - _hunter_sprite.frame_w // 2
        y = cy - _hunter_sprite.frame_h // 2
        surf.blit(frame, (x, y))
        return

    # ── Fallback: original procedural hunter ──
    draw_glow(surf, (255, 180, 60), (cx, cy), 38, 60)
    pts = [(cx, cy - 28), (cx - 13, cy + 10), (cx + 13, cy + 10)]
    pygame.draw.polygon(surf, C_HUNTER2, pts)
    pygame.draw.polygon(surf, C_HUNTER,  pts, 2)
    pygame.draw.circle(surf, C_HUNTER,  (cx, cy - 30), 11)
    pygame.draw.circle(surf, C_HUNTER2, (cx, cy - 30), 11, 2)
    sw = int(math.sin(tick * 0.15) * 2)
    pygame.draw.line(surf, C_GOLD,  (cx + 10, cy - 10), (cx + 22 + sw, cy + 4), 3)
    pygame.draw.line(surf, C_WHITE, (cx + 10, cy - 10), (cx + 14,      cy - 6), 1)
    hat = [(cx - 14, cy - 34), (cx + 14, cy - 34), (cx, cy - 48)]
    pygame.draw.polygon(surf, (90, 55, 20),  hat)
    pygame.draw.polygon(surf, (120, 75, 30), hat, 1)


def draw_aswang(surf, cx, cy, tick, disabled=False):
    """
    The Aswang sprite: bat-winged shadow creature with glowing eyes.
    *disabled* = True when the creature is dazed (Sacred Amulet effect).
    """
    sway    = int(math.sin(tick * 0.12) * 3)
    gcol    = (100, 30, 30) if disabled else (200, 30, 30)
    draw_glow(surf, gcol, (cx + sway, cy), 42, 90)

    # Body
    body_col = (100, 15, 15) if disabled else C_ASWANG2
    outline  = (150, 40, 40) if disabled else C_ASWANG
    pygame.draw.ellipse(surf, body_col, (cx - 16 + sway, cy - 22, 32, 44))
    pygame.draw.ellipse(surf, outline,  (cx - 16 + sway, cy - 22, 32, 44), 2)

    # Bat wings
    wing_col = (70, 10, 10) if disabled else (160, 25, 25)
    for side in (-1, 1):
        wpts = [
            (cx + sway,             cy - 5),
            (cx + side * 34 + sway, cy - 18 + int(math.sin(tick * 0.1) * 4)),
            (cx + side * 20 + sway, cy + 8),
        ]
        pygame.draw.polygon(surf, wing_col, wpts)

    # Glowing eyes
    eye_col = (80, 80, 80) if disabled else C_EYE
    pulse   = abs(math.sin(tick * 0.1)) * 3
    for ex in (cx - 6 + sway, cx + 6 + sway):
        pygame.draw.circle(surf, eye_col, (ex, cy - 8), int(5 + pulse))
        pygame.draw.circle(surf, C_WHITE, (ex, cy - 8), 2)

    # Horns
    for side in (-1, 1):
        hx = cx + side * 8 + sway
        pygame.draw.line(surf, (60, 10, 10), (hx, cy - 22), (hx + side * 6, cy - 34), 3)


# ─────────────────────────────────────────────
#  POWER-UPS
# ─────────────────────────────────────────────
def draw_garlic(surf, cx, cy, tick):
    """Pulsing garlic clove power-up."""
    pulse = abs(math.sin(tick * 0.07)) * 3
    draw_glow(surf, C_GARLIC, (cx, cy), int(22 + pulse), 70)
    pygame.draw.ellipse(surf, (200, 210, 100), (cx - 10, cy - 6, 20, 18))
    pygame.draw.ellipse(surf, C_GARLIC,        (cx - 10, cy - 6, 20, 18), 2)
    pygame.draw.line(surf, (160, 170,  80), (cx, cy - 6),  (cx, cy - 16), 3)
    pygame.draw.line(surf, (120, 160,  60), (cx, cy - 14), (cx - 7, cy - 22), 2)
    pygame.draw.line(surf, (120, 160,  60), (cx, cy - 14), (cx + 7, cy - 22), 2)


def draw_water(surf, cx, cy, tick):
    """Pulsing holy-water vial power-up."""
    pulse = abs(math.sin(tick * 0.07)) * 3
    draw_glow(surf, C_WATER, (cx, cy), int(22 + pulse), 70)
    pygame.draw.rect(surf, (60,  130, 200), (cx - 7, cy - 12, 14, 20), border_radius=4)
    pygame.draw.rect(surf, C_WATER,         (cx - 7, cy - 12, 14, 20), 2, border_radius=4)
    pygame.draw.rect(surf, (80,  150, 220), (cx - 4, cy - 20, 8,  10))
    pygame.draw.rect(surf, (160, 110,  60), (cx - 5, cy - 24, 10,  6), border_radius=2)
    pygame.draw.line(surf, (180, 220, 255), (cx - 3, cy - 10), (cx - 3, cy), 2)


def draw_amulet(surf, cx, cy, tick):
    """Pulsing sacred amulet (cross with gems) power-up."""
    pulse = abs(math.sin(tick * 0.07)) * 3
    draw_glow(surf, C_AMULET, (cx, cy), int(22 + pulse), 80)
    pygame.draw.rect(surf, C_AMULET,       (cx - 3,  cy - 16, 6,  32), border_radius=2)
    pygame.draw.rect(surf, C_AMULET,       (cx - 12, cy - 7,  24,  6), border_radius=2)
    pygame.draw.rect(surf, (230, 150, 255), (cx - 2,  cy - 15, 4,  30), border_radius=1)
    pygame.draw.rect(surf, (230, 150, 255), (cx - 11, cy - 6,  22,  4), border_radius=1)
    for gx, gy in ((cx, cy - 12), (cx, cy + 8), (cx - 10, cy - 2), (cx + 10, cy - 2)):
        pygame.draw.circle(surf, (255, 200, 255), (gx, gy), 3)