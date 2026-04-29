"""
game.py
Core game logic: state management, turn sequencing, collision,
power-up handling, and win/loss conditions.

The Game class is deliberately UI-free — it only mutates data.
The Renderer reads game state and draws it; the AIEngine reads and
temporarily mutates game state during look-ahead (using snap/restore).
"""

import random

from .constants import (
    GRID_ROWS, GRID_COLS, BASE, SPAWN, DIRS,
    Cell, GameState,
    HUNTER_MAX_HP, ASWANG_MAX_HP,
    ASWANG_ATTACK_DMG,
    GARLIC_DMG, WATER_DMG, AMULET_DMG,
    GARLIC_SLOW_TURNS, AMULET_DAZE_TURNS,
    SCORE_PER_TURN, SCORE_ITEM_PICKUP, SCORE_ITEM_USE, SCORE_WIN_BONUS,
)
from .ai import AIEngine


class Game:
    """
    Holds the complete, authoritative game state and exposes
    move_hunter(), use_item(), and reset() as the public API.
    """

    def __init__(self):
        self.ai = AIEngine()
        self.reset()

    # ─────────────────────────────────────────────
    #  INITIALISATION
    # ─────────────────────────────────────────────
    def reset(self):
        """Restore every attribute to its starting value."""
        self.grid = [[Cell.EMPTY] * GRID_COLS for _ in range(GRID_ROWS)]
        for r in range(GRID_ROWS):
            for c in range(GRID_COLS):
                if BASE[r][c]:
                    self.grid[r][c] = Cell.OBSTACLE

        self.hpos  = (0, 0)            # Hunter position  (row, col)
        self.apos  = (9, 9)            # Aswang position  (row, col)
        self.hhp   = HUNTER_MAX_HP
        self.ahp   = ASWANG_MAX_HP
        self.item  = None              # Currently held power-up

        self.turn   = 0
        self.score  = 0
        self.slowed = 0               # Turns the Aswang is slowed
        self.dazed  = 0               # Turns the Aswang is dazed (random move)

        self.state     = GameState.PLAYING
        self.msg       = "Find and defeat the Aswang!"
        self.dmg_flash = 0            # Countdown for damage visual flash (renderer)
        self.item_flash = None        # (r, c) cell just picked up (renderer reads & clears)

        # ── Hunter facing direction (used by renderer for sprite animation) ──
        self.facing = "down"          # "down" | "up" | "left" | "right"

        self._spawn()

    def _spawn(self):
        """Scatter power-ups across valid SPAWN cells."""
        pool = [Cell.GARLIC, Cell.WATER, Cell.AMULET] * 3
        random.shuffle(pool)
        candidates = [
            cell for cell in SPAWN
            if self.grid[cell[0]][cell[1]] == Cell.EMPTY
            and cell != self.hpos
            and cell != self.apos
        ]
        random.shuffle(candidates)
        for i, cell in enumerate(candidates[: len(pool)]):
            self.grid[cell[0]][cell[1]] = pool[i]

    # ─────────────────────────────────────────────
    #  UTILITY
    # ─────────────────────────────────────────────
    def valid(self, r: int, c: int) -> bool:
        return (
            0 <= r < GRID_ROWS
            and 0 <= c < GRID_COLS
            and self.grid[r][c] != Cell.OBSTACLE
        )

    def moves(self, pos: tuple) -> list:
        r, c = pos
        return [(r + dr, c + dc) for dr, dc in DIRS if self.valid(r + dr, c + dc)]

    def dist(self, a: tuple, b: tuple) -> int:
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    def _count_pups(self) -> int:
        return sum(
            1 for r in range(GRID_ROWS) for c in range(GRID_COLS)
            if self.grid[r][c] in (Cell.GARLIC, Cell.WATER, Cell.AMULET)
        )

    # ─────────────────────────────────────────────
    #  PLAYER ACTIONS
    # ─────────────────────────────────────────────
    def move_hunter(self, dr: int, dc: int):
        """Move the Hunter one step; trigger the AI turn afterwards."""
        if self.state != GameState.PLAYING:
            return

        nr, nc = self.hpos[0] + dr, self.hpos[1] + dc
        if not self.valid(nr, nc):
            self.msg = "Blocked by an obstacle!"
            return

        # ── Update facing direction based on movement ──
        if dr == -1 and dc == 0:
            self.facing = "up"
        elif dr == 1 and dc == 0:
            self.facing = "down"
        elif dr == 0 and dc == -1:
            self.facing = "left"
        elif dr == 0 and dc == 1:
            self.facing = "right"

        self.hpos   = (nr, nc)
        self.score += SCORE_PER_TURN

        # Pick up power-up if present
        cell = self.grid[nr][nc]
        names = {
            Cell.GARLIC: "Garlic Clove",
            Cell.WATER:  "Holy Water",
            Cell.AMULET: "Sacred Amulet",
        }
        if cell in names:
            self.item       = cell
            self.grid[nr][nc] = Cell.EMPTY
            self.item_flash = (nr, nc)          # signal renderer
            self.msg        = f"Picked up {names[cell]}!"
            self.score     += SCORE_ITEM_PICKUP

        # Contact damage
        if self.hpos == self.apos:
            self.hhp       -= ASWANG_ATTACK_DMG
            self.msg        = f"The Aswang attacks! -{ASWANG_ATTACK_DMG} HP"
            self.dmg_flash  = 8

        self._check()
        if self.state == GameState.PLAYING:
            self._ai_turn()

    def use_item(self):
        """Use the currently held item against the Aswang (must be adjacent)."""
        if self.state != GameState.PLAYING:
            return
        if not self.item:
            self.msg = "No item to use!"
            return
        if self.dist(self.hpos, self.apos) > 1:
            self.msg = "Must be adjacent to the Aswang!"
            return

        it         = self.item
        self.item  = None
        self.score += SCORE_ITEM_USE

        if it == Cell.GARLIC:
            self.ahp    -= GARLIC_DMG
            self.slowed  = GARLIC_SLOW_TURNS
            self.msg     = f"Garlic! -{GARLIC_DMG} HP. Aswang slowed {GARLIC_SLOW_TURNS} turns!"
        elif it == Cell.WATER:
            self.ahp -= WATER_DMG
            self.msg  = f"Holy Water! -{WATER_DMG} HP to the Aswang!"
        elif it == Cell.AMULET:
            self.ahp   -= AMULET_DMG
            self.dazed  = AMULET_DAZE_TURNS
            self.msg    = f"Sacred Amulet! -{AMULET_DMG} HP! Dazed {AMULET_DAZE_TURNS} turns!"

        self._check()
        if self.state == GameState.PLAYING:
            self._ai_turn()

    # ─────────────────────────────────────────────
    #  AI TURN
    # ─────────────────────────────────────────────
    def _ai_turn(self):
        self.turn += 1

        if self.slowed > 0:
            self.slowed -= 1
            return                              # Aswang skips this turn

        if self.dazed > 0:
            self.dazed -= 1
            mv = self.moves(self.apos)
            if mv:
                self.apos = random.choice(mv)  # Dazed: random movement
        else:
            best = self.ai.get_best_move(self)
            if best:
                self.apos = best

        # Contact damage (Aswang lands on Hunter)
        if self.apos == self.hpos:
            self.hhp       -= ASWANG_ATTACK_DMG
            self.msg        = f"The Aswang found you! -{ASWANG_ATTACK_DMG} HP"
            self.dmg_flash  = 8

        # Re-spawn items if the board is running low
        if self._count_pups() < 3:
            self._spawn()

        self._check()

    # ─────────────────────────────────────────────
    #  WIN / LOSS CHECK
    # ─────────────────────────────────────────────
    def _check(self):
        self.hhp = max(0, self.hhp)
        self.ahp = max(0, self.ahp)

        if self.hhp <= 0 and self.ahp <= 0:
            self.state = GameState.DRAW
        elif self.ahp <= 0:
            self.state  = GameState.WIN
            self.score += SCORE_WIN_BONUS
        elif self.hhp <= 0:
            self.state = GameState.LOSE

    # ─────────────────────────────────────────────
    #  STATE SNAPSHOT  (used by AIEngine during look-ahead)
    # ─────────────────────────────────────────────
    def _snap(self) -> dict:
        return {
            "hhp":  self.hhp,
            "ahp":  self.ahp,
            "hpos": self.hpos,
            "apos": self.apos,
            "sl":   self.slowed,
            "dz":   self.dazed,
        }

    def _restore(self, snap: dict):
        self.hhp    = snap["hhp"]
        self.ahp    = snap["ahp"]
        self.hpos   = snap["hpos"]
        self.apos   = snap["apos"]
        self.slowed = snap["sl"]
        self.dazed  = snap["dz"]