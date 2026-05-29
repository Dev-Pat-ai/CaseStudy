"""
renderer.py
Renderer — handles all Pygame drawing.

Enhanced features over the original single-file version:
  1. Fog of War          — only cells near the Hunter are revealed
  2. Blood Moon Sky      — animated gradient sky with pulsing red moon
  3. Smooth HP Bars      — display HP interpolates toward the real value
  4. Screen Shake        — camera shakes on damage events
  5. Item Pickup Flash   — golden flash on the cell when an item is collected
"""

import pygame
import sys
import math
import random

from .constants import (
    GRID_COLS, GRID_ROWS, CELL, HUD_W, GRID_W, SCREEN_W, SCREEN_H, GRID_H,
    FPS, FOG_RADIUS,
    HUNTER_MAX_HP, ASWANG_MAX_HP, HEAL_AMOUNT, REGULAR_BOSSES,
    C_BG, C_TILE_A, C_TILE_B, C_TILE_C, C_GRID,
    C_HUNTER, C_HUNTER2, C_ASWANG, C_ASWANG2,
    C_GARLIC, C_WATER, C_AMULET,
    C_HUD_BG, C_HUD_BORD,
    C_GOLD, C_SILVER, C_WHITE, C_BLACK,
    C_RED_HP, C_YEL_HP, C_GRN_HP,
    C_LOG, C_DIM,
    Cell, GameState, RoomType,
)
from .sprites import (
    draw_glow, draw_tree,
    draw_hunter, load_hunter_sprite,
    draw_aswang,
    draw_garlic, draw_water, draw_amulet,
)


# ─────────────────────────────────────────────
#  FLOOR-TILE CACHE  (module-level helper)
# ─────────────────────────────────────────────
def _make_floor_tile(variant: int) -> pygame.Surface:
    """Pre-bake a randomised floor tile for fast blitting."""
    surf = pygame.Surface((CELL, CELL))
    base = [C_TILE_A, C_TILE_B, C_TILE_C][variant % 3]
    surf.fill(base)
    rng = random.Random(variant * 997 + 13)
    for _ in range(12):
        x     = rng.randint(0, CELL - 1)
        y     = rng.randint(0, CELL - 1)
        r     = rng.randint(1, 3)
        shade = rng.randint(-6, 6)
        c     = tuple(max(0, min(255, base[i] + shade)) for i in range(3))
        pygame.draw.circle(surf, c, (x, y), r)
    return surf


# ─────────────────────────────────────────────
#  RENDERER
# ─────────────────────────────────────────────
class Renderer:
    """
    Draws every frame of the game.

    All game-world drawing goes to self.grid_surf (an off-screen surface
    the size of the grid area).  That surface is then blitted to the real
    screen with a shake offset so the HUD, which is drawn directly onto
    the screen, is never affected by camera shake.
    """

    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        pygame.font.init()

        # Fonts
        self.fxl    = pygame.font.SysFont("Arial Black", 52, bold=True)
        self.flg    = pygame.font.SysFont("Arial",  20, bold=True)
        self.fmd    = pygame.font.SysFont("Arial",  16, bold=True)
        self.fsm    = pygame.font.SysFont("Arial",  13)
        self.flog   = pygame.font.SysFont("Arial",  14, italic=True)

        self.tick   = 0

        # Pre-baked floor tiles
        self.tiles    = [_make_floor_tile(v) for v in range(6)]
        self.tile_map = [
            [random.randint(0, 5) for _ in range(GRID_COLS)]
            for _ in range(GRID_ROWS)
        ]

        # Off-screen game-world surface (shake applied here)
        self.grid_surf = pygame.Surface((GRID_W, GRID_H))

        # Radial vignette overlay for the grid area
        self.vignette = self._make_vignette()

        # ── Effect state ──────────────────────────
        self.shake = 0                          # pixels of camera shake remaining
        self.particles: list = []               # [x, y, vx, vy, life, max_life, color]
        self.item_flash_cells: dict = {}        # {(r, c): frames_remaining}

        # Smooth HP display values (interpolate toward real HP)
        self.display_hhp = float(HUNTER_MAX_HP)
        self.display_ahp = float(ASWANG_MAX_HP)

        # ── Load hunter sprite sheet ──────────────
        # If the sprite sheet layout doesn't match the expected grid,
        # HunterSprite will fall back to using the whole image as one frame.
        try:
            load_hunter_sprite(
                sheet_path="assets/sprite/sprite_hunter.png",
                frame_w=314,
                frame_h=280,
                scale=0.60,
            )
        except Exception as e:
            print("Warning: could not load hunter sprite:", e)

    def update_screen(self, screen: pygame.Surface):
        self.screen = screen

    # ─────────────────────────────────────────────
    #  VIGNETTE
    # ─────────────────────────────────────────────
    def _make_vignette(self) -> pygame.Surface:
        s   = pygame.Surface((GRID_W, GRID_H), pygame.SRCALPHA)
        cx  = GRID_W // 2
        cy  = GRID_H   // 2
        max_r = max(GRID_W, GRID_H) // 2
        for r in range(max_r, 0, -4):
            alpha = int(120 * (1 - r / max_r))
            if alpha > 2:
                pygame.draw.ellipse(s, (0, 0, 0, alpha), (cx - r, cy - r, r * 2, r * 2), 4)
        return s

    # ─────────────────────────────────────────────
    #  PARTICLES
    # ─────────────────────────────────────────────
    def _add_particles(self, x: int, y: int, color: tuple, n: int = 6):
        for _ in range(n):
            life = random.randint(12, 24)
            self.particles.append([
                float(x), float(y),
                random.uniform(-2.0, 2.0),
                random.uniform(-3.0, 0.0),
                life, life,
                color,
            ])

    def _update_particles(self):
        alive = []
        for p in self.particles:
            p[0] += p[2]        # x += vx
            p[1] += p[3]        # y += vy
            p[3] += 0.15        # gravity
            p[4] -= 1           # decay life
            if p[4] > 0:
                alive.append(p)
        self.particles = alive

    def _draw_particles(self):
        for p in self.particles:
            alpha = p[4] / p[5]
            r     = int(4 * alpha)
            if r < 1:
                continue
            c = tuple(int(ch * alpha) for ch in p[6])
            pygame.draw.circle(self.grid_surf, c, (int(p[0]), int(p[1])), r)

    # ─────────────────────────────────────────────
    #  BLOOD MOON SKY
    # ─────────────────────────────────────────────
    def _draw_sky(self):
        """Replace the flat background fill with a gradient sky + blood moon."""
        for y in range(GRID_H):
            t = y / GRID_H
            r = int(12 + t * 8)
            g = int(8  + t * 14)
            b = int(12 + t * 8)
            pygame.draw.line(self.grid_surf, (r, g, b), (0, y), (GRID_W, y))

        # Pulsing blood moon in the top-right corner
        pulse = int(abs(math.sin(self.tick * 0.02)) * 5)
        mx, my = GRID_W - 55, 45
        draw_glow(self.grid_surf, (180, 60, 40), (mx, my), 50 + pulse, 60)
        pygame.draw.circle(self.grid_surf, (130,  40, 25), (mx, my), 26 + pulse)
        pygame.draw.circle(self.grid_surf, (180,  70, 50), (mx, my), 22 + pulse)
        pygame.draw.circle(self.grid_surf, (210,  95, 65), (mx, my), 16)

    # ─────────────────────────────────────────────
    #  FLOOR & OBSTACLES
    # ─────────────────────────────────────────────
    def _draw_floor(self, game):
        for r in range(GRID_ROWS):
            for c in range(GRID_COLS):
                x, y = c * CELL, r * CELL
                if game.grid[r][c] == Cell.OBSTACLE:
                    pygame.draw.rect(self.grid_surf, C_TILE_C, (x, y, CELL, CELL))
                    draw_tree(self.grid_surf, x + CELL // 2, y + CELL - 10, self.tick)
                else:
                    self.grid_surf.blit(self.tiles[self.tile_map[r][c]], (x, y))

    def _draw_grid_lines(self):
        for r in range(GRID_ROWS + 1):
            pygame.draw.line(self.grid_surf, C_GRID, (0, r * CELL), (GRID_W, r * CELL), 1)
        for c in range(GRID_COLS + 1):
            pygame.draw.line(self.grid_surf, C_GRID, (c * CELL, 0), (c * CELL, GRID_H), 1)

    # ─────────────────────────────────────────────
    #  ITEM PICKUP FLASH
    # ─────────────────────────────────────────────
    def _draw_item_flashes(self):
        for (r, c), frames in self.item_flash_cells.items():
            alpha = int(200 * (frames / 15))
            flash = pygame.Surface((CELL, CELL), pygame.SRCALPHA)
            flash.fill((255, 255, 180, alpha))
            self.grid_surf.blit(flash, (c * CELL, r * CELL))

    # ─────────────────────────────────────────────
    #  POWER-UPS
    # ─────────────────────────────────────────────
    def _draw_powerups(self, game):
        for r in range(GRID_ROWS):
            for c in range(GRID_COLS):
                cell = game.grid[r][c]
                x = c * CELL + CELL // 2
                y = r * CELL + CELL // 2
                if   cell == Cell.GARLIC: draw_garlic(self.grid_surf, x, y, self.tick)
                elif cell == Cell.WATER:  draw_water (self.grid_surf, x, y, self.tick)
                elif cell == Cell.AMULET: draw_amulet(self.grid_surf, x, y, self.tick)
                elif cell == Cell.WEAPON_PORTAL:
                    self._draw_portal(x, y, C_AMULET, "W")
                elif cell == Cell.HEALING_PORTAL:
                    self._draw_portal(x, y, C_GRN_HP, "H")

    def _draw_portal(self, x: int, y: int, color: tuple, label: str):
        pulse = abs(math.sin(self.tick * 0.08)) * 8
        draw_glow(self.grid_surf, color, (x, y), int(34 + pulse), 95)
        pygame.draw.circle(self.grid_surf, color, (x, y), int(21 + pulse * 0.25), 3)
        pygame.draw.circle(self.grid_surf, C_BLACK, (x, y), 15)
        pygame.draw.circle(self.grid_surf, color, (x, y), 11, 2)
        text = self.fmd.render(label, True, C_WHITE)
        self.grid_surf.blit(text, text.get_rect(center=(x, y)))

    # ─────────────────────────────────────────────
    #  CHARACTERS
    # ─────────────────────────────────────────────
    def _draw_characters(self, game):
        hr, hc = game.hpos
        hx = hc * CELL + CELL // 2
        hy = hr * CELL + CELL // 2

        if game.state == GameState.ROOM_CHOICE:
            draw_hunter(self.grid_surf, hx, hy, self.tick, getattr(game, "facing", "down"))
            self._nametag(hx, hy + 26, "HUNTER", C_HUNTER)
            return

        ar, ac = game.apos
        ex = ac * CELL + CELL // 2
        ey = ar * CELL + CELL // 2

        # Get hunter facing direction from game state
        direction = getattr(game, "facing", "down")

        # Z-order: character in the lower row is drawn on top
        if ar >= hr:
            draw_hunter(self.grid_surf, hx, hy, self.tick, direction)
            draw_aswang(self.grid_surf, ex, ey, self.tick, game.dazed > 0)
        else:
            draw_aswang(self.grid_surf, ex, ey, self.tick, game.dazed > 0)
            draw_hunter(self.grid_surf, hx, hy, self.tick, direction)

        # Status badges above Aswang
        if game.slowed > 0:
            self._badge(ex, ey - 38, f"SLOWED {game.slowed}", C_GARLIC)
        if game.dazed > 0:
            self._badge(ex, ey - 38, f"DAZED {game.dazed}",  C_AMULET)

        # Name tags below characters
        self._nametag(hx, hy + 26, "HUNTER", C_HUNTER)
        self._nametag(ex, ey + 26, "ASWANG", C_ASWANG)

    def _badge(self, cx: int, cy: int, text: str, color: tuple):
        t   = self.fsm.render(text, True, C_BLACK)
        w, h = t.get_size()
        pad = 4
        bg  = pygame.Surface((w + pad * 2, h + pad * 2), pygame.SRCALPHA)
        bg.fill((*color, 200))
        self.grid_surf.blit(bg, (cx - w // 2 - pad, cy - h // 2 - pad))
        self.grid_surf.blit(t,  (cx - w // 2,        cy - h // 2))

    def _nametag(self, cx: int, cy: int, text: str, color: tuple):
        t = self.fsm.render(text, True, color)
        self.grid_surf.blit(t, t.get_rect(center=(cx, cy)))

    # ─────────────────────────────────────────────
    #  TEXT UTILITIES
    # ─────────────────────────────────────────────
    def _wrap_text(self, font: pygame.font.Font, text: str, max_width: int, max_lines: int = 2) -> list:
        """Wrap text to fit within max_width, returning list of lines."""
        if font.render(text, True, C_WHITE).get_width() <= max_width:
            return [text]

        lines = []
        words = text.split()
        current_line = []

        for word in words:
            test_line = " ".join(current_line + [word])
            if font.render(test_line, True, C_WHITE).get_width() <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(" ".join(current_line))
                    current_line = [word]
                else:
                    lines.append(word)

                if len(lines) >= max_lines:
                    break

        if current_line and len(lines) < max_lines:
            lines.append(" ".join(current_line))

        return lines if lines else [text[:20] + "..."]

    def _render_text_with_shadow(self, surface: pygame.Surface, font: pygame.font.Font,
                                  text: str, color: tuple, pos: tuple,
                                  shadow_offset: int = 3, outline: bool = False):
        """Render text with shadow or outline for better readability."""
        if outline:
            shadow = font.render(text, True, (0, 0, 0))
            for dx in range(-2, 3):
                for dy in range(-2, 3):
                    if dx == 0 and dy == 0:
                        continue
                    surface.blit(shadow, (pos[0] + dx, pos[1] + dy))
        else:
            shadow = font.render(text, True, (0, 0, 0))
            surface.blit(shadow, (pos[0] + shadow_offset, pos[1] + shadow_offset))

        main = font.render(text, True, color)
        surface.blit(main, pos)

    # ─────────────────────────────────────────────
    #  FOG OF WAR
    # ─────────────────────────────────────────────
    def _draw_fog(self, game):
        """
        Overlay a darkness fog; cells within FOG_RADIUS (Manhattan) of
        the Hunter are gradually revealed.  The Aswang's cell always
        receives reduced fog so it stays partially visible.
        """
        fog = pygame.Surface((GRID_W, GRID_H), pygame.SRCALPHA)
        hr, hc = game.hpos
        ar, ac = game.apos

        for r in range(GRID_ROWS):
            for c in range(GRID_COLS):
                # Always partially reveal Aswang cell (danger hint)
                if (r, c) == (ar, ac):
                    pygame.draw.rect(fog, (0, 0, 0, 50), (c * CELL, r * CELL, CELL, CELL))
                    continue

                dist = abs(r - hr) + abs(c - hc)
                if dist == 0:
                    alpha = 0
                elif dist <= FOG_RADIUS:
                    alpha = int(210 * (dist / FOG_RADIUS) ** 1.8)
                else:
                    alpha = 215

                if alpha > 0:
                    pygame.draw.rect(fog, (0, 0, 0, alpha), (c * CELL, r * CELL, CELL, CELL))

        self.grid_surf.blit(fog, (0, 0))

    # ─────────────────────────────────────────────
    #  MASTER DRAW
    # ─────────────────────────────────────────────
    def draw(self, game, pending_command=None):
        self.tick += 1

        # ── Register item-pickup flash ──
        if game.item_flash:
            self.item_flash_cells[game.item_flash] = 15
            game.item_flash = None

        # ── Screen Shake trigger ──
        if game.dmg_flash > 0:
            game.dmg_flash -= 1
            self.shake = min(self.shake + 5, 8)
            hx = game.hpos[1] * CELL + CELL // 2
            hy = game.hpos[0] * CELL + CELL // 2
            self._add_particles(hx, hy, (220, 60, 60), 8)

        if self.shake > 0:
            self.shake -= 1

        # ── Smooth HP interpolation ──
        self.display_hhp += (game.hhp - self.display_hhp) * 0.12
        self.display_ahp += (game.ahp - self.display_ahp) * 0.12

        # ── Decay item-flash timers ──
        self.item_flash_cells = {
            k: v - 1 for k, v in self.item_flash_cells.items() if v > 1
        }

        # ── Draw game world onto grid_surf ──
        self._draw_sky()
        self._draw_floor(game)
        self._draw_grid_lines()
        self._draw_item_flashes()
        self._draw_powerups(game)
        self._draw_characters(game)
        self._update_particles()
        self._draw_particles()
        self.grid_surf.blit(self.vignette, (0, 0))
        self._draw_fog(game)

        # ── Blit grid_surf to screen with shake offset ──
        self.screen.fill(C_BG)
        center_x = (self.screen.get_width() - SCREEN_W) // 2
        center_y = (self.screen.get_height() - SCREEN_H) // 2
        ox = random.randint(-self.shake, self.shake) if self.shake > 0 else 0
        oy = random.randint(-self.shake, self.shake) if self.shake > 0 else 0
        self.screen.blit(self.grid_surf, (center_x + HUD_W + ox, center_y + oy))

        # ── HUD drawn directly on screen (no shake) ──
        self._draw_hud(game, center_x, center_y)

        if game.state == GameState.WEAPON_CHOICE:
            self._draw_choice_overlay(game, center_x, center_y)
        elif game.state not in (GameState.PLAYING, GameState.ROOM_CHOICE):
            self._draw_game_over(game, center_x, center_y)

        if pending_command:
            self._draw_confirm_overlay(pending_command, center_x, center_y)

        pygame.display.flip()

    # ─────────────────────────────────────────────
    #  HUD
    # ─────────────────────────────────────────────
    def _draw_hud(self, game, center_x=0, center_y=0):
        x = center_x + 5
        y = center_y + 5
        panel_w = HUD_W - 10
        panel_h = (GRID_H - 20) // 3

        # ── Status panel ──
        self._panel(x, y, panel_w, panel_h)
        self.screen.blit(self.flg.render("STATUS", True, C_GOLD), (x + 9, y + 10))
        aswang_max = getattr(game, "aswang_max_hp", ASWANG_MAX_HP)
        self._hp_bar(x + 9, y + 42, panel_w - 18, 18, self.display_hhp, HUNTER_MAX_HP, "Hunter", C_HUNTER)
        self._hp_bar(x + 9, y + 78, panel_w - 18, 18, self.display_ahp, aswang_max, "Aswang", C_ASWANG)
        self.screen.blit(self.flg.render(f"✦ SCORE: {game.score}", True, C_GOLD),   (x + 9, y + 116))
        self.screen.blit(self.fmd.render(f"TURN: {game.turn}",     True, C_SILVER), (x + 9, y + 142))
        cleared = getattr(game, "bosses_cleared", 0)
        room = "FINAL BOSS" if getattr(game, "is_final_boss", False) else f"BOSS {cleared + 1}/{REGULAR_BOSSES}"
        self.screen.blit(self.fsm.render(room, True, C_SILVER), (x + 9, y + 166))

        y += panel_h + 10

        # ── Held item panel ──
        self._panel(x, y, panel_w, panel_h)
        self.screen.blit(self.flg.render("INVENTORY", True, C_GOLD), (x + 9, y + 10))
        selected_item = game.selected_item() if hasattr(game, "selected_item") else None
        if selected_item:
            inames = {Cell.GARLIC: "Garlic Clove", Cell.WATER: "Holy Water", Cell.AMULET: "Sacred Amulet"}
            icols  = {Cell.GARLIC: C_GARLIC,       Cell.WATER: C_WATER,      Cell.AMULET: C_AMULET}
            ix = x + panel_w // 2
            iy = y + 92
            if   selected_item == Cell.GARLIC: draw_garlic(self.screen, ix, iy, self.tick)
            elif selected_item == Cell.WATER:  draw_water (self.screen, ix, iy, self.tick)
            elif selected_item == Cell.AMULET: draw_amulet(self.screen, ix, iy, self.tick)
            item_name = inames[selected_item]
            t1 = self.fmd.render(item_name, True, C_SILVER)
            slot_text = f"Slot {getattr(game, 'selected_item_index', 0) + 1}/{len(getattr(game, 'inventory', []))}"
            t0 = self.fsm.render(slot_text, True, C_GOLD)
            t2 = self.fsm.render("[1-3] select  [SPACE] use", True, C_SILVER)
            self.screen.blit(t0, t0.get_rect(center=(x + panel_w // 2, y + 62)))
            self.screen.blit(t1, t1.get_rect(center=(x + panel_w // 2, y + 40)))
            self.screen.blit(t2, t2.get_rect(center=(x + panel_w // 2, y + panel_h - 28)))
        else:
            t = self.fmd.render("— empty —", True, C_SILVER)
            self.screen.blit(t, t.get_rect(center=(x + panel_w // 2, y + panel_h // 2)))

        inv_names = {Cell.GARLIC: "Garlic", Cell.WATER: "Water", Cell.AMULET: "Amulet"}
        inventory = getattr(game, "inventory", [])
        slots = []
        for slot_index in range(3):
            if slot_index < len(inventory):
                marker = ">" if slot_index == getattr(game, "selected_item_index", 0) else " "
                slots.append(f"{marker}{slot_index + 1}:{inv_names[inventory[slot_index]]}")
            else:
                slots.append(f" {slot_index + 1}:Empty")
        slot_line = self.fsm.render("  ".join(slots), True, C_SILVER)
        self.screen.blit(slot_line, slot_line.get_rect(center=(x + panel_w // 2, y + panel_h - 52)))

        y += panel_h + 10

        # ── Items panel ──
        self._panel(x, y, panel_w, panel_h)
        self.screen.blit(self.flg.render("ITEMS", True, C_GOLD), (x + 9, y + 10))
        legend = [
            (C_GARLIC, "G  Garlic Clove  -20 HP  |  Slows"),
            (C_WATER,  "W  Holy Water    -30 HP"),
            (C_AMULET, "A  Sacred Amulet -40 HP  |  Dazes"),
        ]
        for i, (col, txt) in enumerate(legend):
            pygame.draw.circle(self.screen, col, (x + 13, y + 42 + i * 24), 5)
            self.screen.blit(self.fsm.render(txt, True, C_SILVER), (x + 26, y + 34 + i * 24))

        ctrl_lines = self._wrap_text(self.fsm, "Arrows/WASD Move | 1-3 Select | SPACE Use | R Reset? | Q Quit?", panel_w - 18)
        for i, line in enumerate(ctrl_lines):
            self.screen.blit(self.fsm.render(line, True, C_SILVER), (x + 9, y + panel_h - 36 + i * 16))

        msg_lines = self._wrap_text(self.flog, game.msg, panel_w - 18)
        for i, line in enumerate(msg_lines):
            self.screen.blit(self.flog.render(line, True, C_LOG), (x + 9, y + panel_h - 52 + i * 14))

    def _panel(self, x: int, y: int, w: int, h: int):
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        s.fill((30,  60,  30, 210))
        self.screen.blit(s, (x, y))
        pygame.draw.rect(self.screen, C_HUD_BORD, (x, y, w, h), 1)

    def _hp_bar(self, x: int, y: int, w: int, h: int,
                cur: float, mx: float, label: str, color: tuple):
        """Animated HP bar — *cur* is the smooth display value (float)."""
        cur_int = int(max(0, cur))
        mx_int  = int(mx)
        lbl = self.fsm.render(f"{label}  {cur_int}/{mx_int}", True, C_SILVER)
        self.screen.blit(lbl, (x, y - 1))
        by  = y + 14
        pct = max(0.0, cur / mx)
        bc  = C_GRN_HP if pct > 0.5 else (C_YEL_HP if pct > 0.25 else C_RED_HP)
        pygame.draw.rect(self.screen, (30, 30, 30), (x, by, w, h))
        pygame.draw.rect(self.screen, bc,            (x, by, int(w * pct), h))
        pygame.draw.rect(self.screen, color,         (x, by, w, h), 1)

    # ─────────────────────────────────────────────
    #  GAME-OVER SCREEN
    # ─────────────────────────────────────────────
    def _draw_choice_overlay(self, game, center_x=0, center_y=0):
        overlay = pygame.Surface((self.screen.get_width(), self.screen.get_height()), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 185))
        self.screen.blit(overlay, (0, 0))

        fw, fh = 560, 300
        fx = center_x + (SCREEN_W - fw) // 2
        fy = center_y + (SCREEN_H - fh) // 2
        frame = pygame.Surface((fw, fh), pygame.SRCALPHA)
        frame.fill((18, 28, 18, 235))
        self.screen.blit(frame, (fx, fy))
        pygame.draw.rect(self.screen, C_HUD_BORD, (fx, fy, fw, fh), 2)

        if game.state == GameState.ROOM_CHOICE:
            title = "CHOOSE NEXT ROOM"
            prompt = "Press 1 or 2"
            options = []
            for room in game.room_options:
                if room == RoomType.HEALING:
                    options.append(("Healing Room", f"Recover up to {HEAL_AMOUNT} HP."))
                else:
                    options.append(("Weapon Room", "Choose one Garlic, Holy Water, or Amulet."))
        else:
            title = "CHOOSE ONE ITEM"
            prompt = "Press 1, 2, or 3"
            names = {
                Cell.GARLIC: ("Garlic Clove", "-20 HP, slows Aswang for 2 turns."),
                Cell.WATER: ("Holy Water", "-30 HP damage to Aswang."),
                Cell.AMULET: ("Sacred Amulet", "-40 HP, random Aswang movement for 3 turns."),
            }
            options = [names[item] for item in game.weapon_options]

        title_surf = self.flg.render(title, True, C_GOLD)
        self.screen.blit(title_surf, title_surf.get_rect(center=(fx + fw // 2, fy + 34)))
        prompt_surf = self.fsm.render(prompt, True, C_SILVER)
        self.screen.blit(prompt_surf, prompt_surf.get_rect(center=(fx + fw // 2, fy + fh - 28)))

        start_y = fy + 82
        card_w = fw - 80
        for i, (name, desc) in enumerate(options):
            cy = start_y + i * 72
            pygame.draw.rect(self.screen, (28, 55, 30), (fx + 40, cy, card_w, 54))
            pygame.draw.rect(self.screen, C_HUD_BORD, (fx + 40, cy, card_w, 54), 1)
            key = self.flg.render(str(i + 1), True, C_GOLD)
            self.screen.blit(key, key.get_rect(center=(fx + 65, cy + 27)))
            self.screen.blit(self.fmd.render(name, True, C_WHITE), (fx + 92, cy + 8))
            self.screen.blit(self.fsm.render(desc, True, C_SILVER), (fx + 92, cy + 30))

    def _draw_game_over(self, game, center_x=0, center_y=0):
        overlay = pygame.Surface((self.screen.get_width(), self.screen.get_height()), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 210))
        self.screen.blit(overlay, (0, 0))

        fw, fh = 500, 280
        fx, fy = (SCREEN_W - fw) // 2, (SCREEN_H - fh) // 2

        frame = pygame.Surface((fw, fh), pygame.SRCALPHA)
        frame.fill((20, 10, 10, 230))
        self.screen.blit(frame, (center_x + fx, center_y + fy))

        for i in range(4):
            col_border = (60 + i * 20, 20, 20)
            pygame.draw.rect(
                self.screen,
                col_border,
                (center_x + fx - i, center_y + fy - i, fw + i * 2, fh + i * 2),
                2
            )

        if game.state == GameState.WIN:
            title, col, sub = "VICTORY",  (80, 220, 120), "The Aswang has been banished!"
        elif game.state == GameState.LOSE:
            title, col, sub = "DEFEATED", (220, 60, 60),  "The Aswang claimed your soul..."
        else:
            title, col, sub = "DRAW",     (220, 180, 60), "Both fell in the darkness..."

        cx = center_x + SCREEN_W // 2
        cy = center_y + SCREEN_H // 2

        float_y = int(math.sin(self.tick * 0.05) * 6)

        spacing = 8
        letters  = []
        total_w  = 0
        for ch in title:
            surf = self.fxl.render(ch, True, col)
            letters.append(surf)
            total_w += surf.get_width() + spacing

        lx     = cx - total_w // 2
        base_y = cy - 90

        for i in range(5):
            glow_alpha = 50 - i * 10
            ox = lx
            for surf in letters:
                glow = surf.copy()
                glow.set_alpha(glow_alpha)
                self.screen.blit(glow, (ox - i, base_y - i + float_y))
                ox += surf.get_width() + spacing

        ox = lx
        for surf in letters:
            self.screen.blit(surf, (ox, base_y + float_y))
            ox += surf.get_width() + spacing

        sub_lines = self._wrap_text(self.fmd, sub, 400)
        for i, line in enumerate(sub_lines):
            sub_surf   = self.fmd.render(line, True, (220, 220, 220))
            sub_shadow = self.fmd.render(line, True, (0, 0, 0))
            sub_rect   = sub_surf.get_rect(center=(cx, cy - 20 + i * 25))
            self.screen.blit(sub_shadow, (sub_rect.x + 2, sub_rect.y + 2))
            self.screen.blit(sub_surf,   sub_rect)

        score_text  = f"FINAL SCORE: {game.score}"
        score_lines = self._wrap_text(self.flg, score_text, 400)
        for i, line in enumerate(score_lines):
            score_surf   = self.flg.render(line, True, (255, 215, 0))
            score_shadow = self.flg.render(line, True, (0, 0, 0))
            score_rect   = score_surf.get_rect(center=(cx, cy + 30 + i * 30))
            self.screen.blit(score_shadow, (score_rect.x + 2, score_rect.y + 2))
            self.screen.blit(score_surf,   score_rect)

        if (self.tick // 30) % 2 == 0:
            instr_text  = "R Reset?   |   Q Quit?   |   Y Confirm / N Cancel"
            instr_lines = self._wrap_text(self.fsm, instr_text, 400)
            for i, line in enumerate(instr_lines):
                instr_surf   = self.fsm.render(line, True, (200, 200, 200))
                instr_shadow = self.fsm.render(line, True, (0, 0, 0))
                instr_rect   = instr_surf.get_rect(center=(cx, cy + 70 + i * 20))
                self.screen.blit(instr_shadow, (instr_rect.x + 2, instr_rect.y + 2))
                self.screen.blit(instr_surf,   instr_rect)

    def _draw_confirm_overlay(self, pending_command, center_x=0, center_y=0):
        overlay = pygame.Surface((self.screen.get_width(), self.screen.get_height()), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 175))
        self.screen.blit(overlay, (0, 0))

        fw, fh = 470, 170
        fx = center_x + (SCREEN_W - fw) // 2
        fy = center_y + (SCREEN_H - fh) // 2

        frame = pygame.Surface((fw, fh), pygame.SRCALPHA)
        frame.fill((18, 28, 18, 245))
        self.screen.blit(frame, (fx, fy))
        pygame.draw.rect(self.screen, C_HUD_BORD, (fx, fy, fw, fh), 2)

        is_quit = pending_command == "quit"
        title = "QUIT GAME?" if is_quit else "RESET GAME?"
        detail = "Your current run will be closed." if is_quit else "Your current run will start over."
        prompt = "Press Y to confirm   |   Press N or ESC to cancel"

        title_surf = self.flg.render(title, True, C_GOLD)
        detail_surf = self.fmd.render(detail, True, C_SILVER)
        prompt_surf = self.fsm.render(prompt, True, C_WHITE)

        self.screen.blit(title_surf, title_surf.get_rect(center=(fx + fw // 2, fy + 38)))
        self.screen.blit(detail_surf, detail_surf.get_rect(center=(fx + fw // 2, fy + 82)))
        self.screen.blit(prompt_surf, prompt_surf.get_rect(center=(fx + fw // 2, fy + 125)))


# ─────────────────────────────────────────────
#  TITLE SCREEN  (module-level function)
# ─────────────────────────────────────────────
def tutorial_screen(screen: pygame.Surface, clock: pygame.time.Clock):
    ftitle = pygame.font.SysFont("Arial Black", 42, bold=True)
    fhead  = pygame.font.SysFont("Arial", 24, bold=True)
    fbody  = pygame.font.SysFont("Arial", 18)
    fsmall = pygame.font.SysFont("Arial", 14)

    pages = [
        (
            "MOVE AND SURVIVE",
            [
                "Move the Hunter with ARROW KEYS or W A S D.",
                "The Aswang moves after you. If it reaches your cell, you lose HP.",
                "Use fog and obstacles to create space, but do not get cornered.",
            ],
            "movement",
        ),
        (
            "ITEMS AND INVENTORY",
            [
                "Pickups are stored in 3 inventory slots.",
                "Press 1, 2, or 3 to select an item slot.",
                "Press SPACE near the Aswang to use the selected item.",
            ],
            "items",
        ),
        (
            "BOSS ROOMS",
            [
                "Defeat each Aswang boss to open safe-room portals.",
                "Weapon Rooms add an item to inventory. Healing Rooms restore HP.",
                "Clear all regular bosses, then defeat the final Aswang.",
            ],
            "rooms",
        ),
    ]

    def draw_panel(rect):
        panel = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
        panel.fill((18, 32, 20, 230))
        screen.blit(panel, rect.topleft)
        pygame.draw.rect(screen, C_HUD_BORD, rect, 2)

    def draw_text_lines(lines, x, y, width, line_h=30):
        cy = y
        for text in lines:
            words = text.split()
            line = ""
            wrapped = []
            for word in words:
                test = f"{line} {word}".strip()
                if fbody.render(test, True, C_WHITE).get_width() <= width:
                    line = test
                else:
                    if line:
                        wrapped.append(line)
                    line = word
            if line:
                wrapped.append(line)

            for wrapped_line in wrapped:
                surf = fbody.render(wrapped_line, True, C_SILVER)
                screen.blit(surf, (x, cy))
                cy += line_h
            cy += 8

    def draw_demo(kind, rect, tick):
        cx = rect.centerx
        cy = rect.centery
        if kind == "movement":
            for row in range(3):
                for col in range(5):
                    tile = pygame.Rect(rect.x + 34 + col * 54, rect.y + 35 + row * 54, 54, 54)
                    pygame.draw.rect(screen, (22, 42, 24), tile)
                    pygame.draw.rect(screen, (60, 100, 60), tile, 1)
            draw_hunter(screen, rect.x + 34 + 54, rect.y + 35 + 54, tick, "right")
            draw_aswang(screen, rect.x + 34 + 54 * 3, rect.y + 35 + 54, tick)
            arrow = fhead.render("WASD / ARROWS", True, C_GOLD)
            screen.blit(arrow, arrow.get_rect(center=(cx, rect.bottom - 34)))
        elif kind == "items":
            slot_w = 82
            start_x = cx - slot_w * 3 // 2 - 10
            items = [Cell.GARLIC, Cell.WATER, Cell.AMULET]
            labels = ["Garlic", "Water", "Amulet"]
            for i, item in enumerate(items):
                sx = start_x + i * (slot_w + 10)
                box = pygame.Rect(sx, rect.y + 42, slot_w, 118)
                pygame.draw.rect(screen, (22, 42, 24), box)
                pygame.draw.rect(screen, C_GOLD if i == 0 else C_HUD_BORD, box, 2)
                key = fsmall.render(str(i + 1), True, C_GOLD)
                screen.blit(key, (sx + 8, rect.y + 48))
                ix, iy = sx + slot_w // 2, rect.y + 95
                if item == Cell.GARLIC:
                    draw_garlic(screen, ix, iy, tick)
                elif item == Cell.WATER:
                    draw_water(screen, ix, iy, tick)
                else:
                    draw_amulet(screen, ix, iy, tick)
                label = fsmall.render(labels[i], True, C_SILVER)
                screen.blit(label, label.get_rect(center=(ix, rect.y + 142)))
            prompt = fhead.render("1-3 SELECT   SPACE USE", True, C_GOLD)
            screen.blit(prompt, prompt.get_rect(center=(cx, rect.bottom - 34)))
        else:
            draw_glow(screen, C_AMULET, (cx - 70, cy), 42, 90)
            pygame.draw.circle(screen, C_AMULET, (cx - 70, cy), 24, 3)
            weapon = fbody.render("Weapon", True, C_WHITE)
            screen.blit(weapon, weapon.get_rect(center=(cx - 70, cy + 44)))
            draw_glow(screen, C_GRN_HP, (cx + 70, cy), 42, 90)
            pygame.draw.circle(screen, C_GRN_HP, (cx + 70, cy), 24, 3)
            heal = fbody.render("Healing", True, C_WHITE)
            screen.blit(heal, heal.get_rect(center=(cx + 70, cy + 44)))
            prompt = fhead.render("CHOOSE A PORTAL AFTER EACH BOSS", True, C_GOLD)
            screen.blit(prompt, prompt.get_rect(center=(cx, rect.bottom - 34)))

    page = 0
    tick = 0
    while True:
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_q:
                    pygame.quit(); sys.exit()
                if e.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_RIGHT):
                    page += 1
                    if page >= len(pages):
                        return
                elif e.key == pygame.K_LEFT:
                    page = max(0, page - 1)
                elif e.key == pygame.K_ESCAPE:
                    return

        for y in range(SCREEN_H):
            t = y / SCREEN_H
            pygame.draw.line(screen, (int(8 + t * 14), int(12 + t * 22), int(10 + t * 12)), (0, y), (SCREEN_W, y))

        for c in range(GRID_COLS):
            draw_tree(screen, c * CELL + CELL // 2, 95, tick, shade=True)

        fog = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        fog.fill((0, 0, 0, 115))
        screen.blit(fog, (0, 0))

        title, body, kind = pages[page]
        title_surf = ftitle.render("HOW TO PLAY", True, C_GOLD)
        screen.blit(title_surf, title_surf.get_rect(center=(SCREEN_W // 2, 70)))

        frame = pygame.Rect(95, 120, SCREEN_W - 190, 430)
        draw_panel(frame)

        head = fhead.render(title, True, C_WHITE)
        screen.blit(head, (frame.x + 32, frame.y + 26))
        draw_text_lines(body, frame.x + 32, frame.y + 76, 430)

        demo_rect = pygame.Rect(frame.right - 340, frame.y + 70, 290, 250)
        pygame.draw.rect(screen, (10, 18, 12), demo_rect)
        pygame.draw.rect(screen, C_HUD_BORD, demo_rect, 1)
        draw_demo(kind, demo_rect, tick)

        footer = fsmall.render(
            f"Page {page + 1}/{len(pages)}   ENTER/SPACE Next   LEFT Back   ESC Skip   Q Quit",
            True,
            C_SILVER,
        )
        screen.blit(footer, footer.get_rect(center=(SCREEN_W // 2, SCREEN_H - 42)))

        pygame.display.flip()
        clock.tick(FPS)
        tick += 1


def title_screen(screen: pygame.Surface, clock: pygame.time.Clock):
    fxl  = pygame.font.SysFont("Arial Black", 52, bold=True)
    fmd  = pygame.font.SysFont("Arial",  20, bold=True)
    fsm  = pygame.font.SysFont("Arial",  14)

    tick = 0
    fade = 0
    pending_quit = False

    while True:
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if e.type == pygame.KEYDOWN:
                if pending_quit:
                    if e.key == pygame.K_y:
                        pygame.quit(); sys.exit()
                    if e.key in (pygame.K_n, pygame.K_ESCAPE):
                        pending_quit = False
                    continue

                if e.key in (pygame.K_RETURN, pygame.K_SPACE):
                    return
                if e.key == pygame.K_q:
                    pending_quit = True

        # Animated background
        for y in range(SCREEN_H):
            t = y / SCREEN_H
            r = int(10 + t * 10)
            g = int(5 + t * 15)
            b = int(10 + t * 10)
            pygame.draw.line(screen, (r, g, b), (0, y), (SCREEN_W, y))

        # Blood moon
        mx, my = SCREEN_W - 100, 100
        pulse = int(abs(math.sin(tick * 0.03)) * 6)
        pygame.draw.circle(screen, (120, 30, 30), (mx, my), 40 + pulse)
        pygame.draw.circle(screen, (200, 60, 60), (mx, my), 30 + pulse)

        # Trees sway
        for c in range(GRID_COLS):
            offset = int(math.sin(tick * 0.03 + c) * 5)
            draw_tree(screen, c * CELL + CELL // 2 + offset, 90, tick)

        # Fog overlay
        fog = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        fog.fill((0, 0, 0, 90))
        screen.blit(fog, (0, 0))

        # Title
        title_text = "ASWANG HUNTER"
        spacing = 8
        letters = []
        total_width = 0
        color = (220, 70, 70)

        for ch in title_text:
            surf = fxl.render(ch, True, color)
            letters.append((ch, surf))
            total_width += surf.get_width() + spacing

        start_x = SCREEN_W // 2 - total_width // 2
        base_y = SCREEN_H // 2 - 80

        for i in range(5):
            glow_alpha = 50 - i * 10
            glow_offset = i * 2
            x = start_x
            for ch, surf in letters:
                glow = fxl.render(ch, True, (255, 80, 80))
                glow.set_alpha(glow_alpha)
                screen.blit(glow, (x - glow_offset, base_y - glow_offset))
                x += surf.get_width() + spacing

        float_y = int(math.sin(tick * 0.05) * 6)
        x = start_x
        for ch, surf in letters:
            screen.blit(surf, (x, base_y + float_y))
            x += surf.get_width() + spacing

        if fade < 255:
            fade += 3

        subtitle = fmd.render("A Filipino Folklore Game — Minimax AI", True, (200, 200, 200))
        subtitle.set_alpha(fade)
        screen.blit(subtitle, subtitle.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2)))

        if (tick // 30) % 2 == 0:
            prompt = fmd.render("Press ENTER to Start", True, (255, 215, 0))
            screen.blit(prompt, prompt.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2 + 60)))

        controls = fsm.render("Arrows/WASD Move | 1-3 Select | SPACE Use | R Reset? | Q Quit?", True, (220, 220, 220))
        screen.blit(controls, controls.get_rect(center=(SCREEN_W // 2, SCREEN_H - 30)))

        if pending_quit:
            overlay = pygame.Surface((screen.get_width(), screen.get_height()), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 175))
            screen.blit(overlay, (0, 0))

            fw, fh = 460, 150
            fx = (SCREEN_W - fw) // 2
            fy = (SCREEN_H - fh) // 2
            frame = pygame.Surface((fw, fh), pygame.SRCALPHA)
            frame.fill((18, 28, 18, 245))
            screen.blit(frame, (fx, fy))
            pygame.draw.rect(screen, C_HUD_BORD, (fx, fy, fw, fh), 2)

            title = fmd.render("QUIT GAME?", True, C_GOLD)
            detail = fsm.render("Press Y to confirm   |   Press N or ESC to cancel", True, C_WHITE)
            screen.blit(title, title.get_rect(center=(SCREEN_W // 2, fy + 48)))
            screen.blit(detail, detail.get_rect(center=(SCREEN_W // 2, fy + 96)))

        pygame.display.flip()
        clock.tick(FPS)
        tick += 1
