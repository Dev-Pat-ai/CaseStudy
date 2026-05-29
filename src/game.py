"""
game.py
Core game logic: state management, room progression, turn sequencing,
collision, power-up handling, and win/loss conditions.

The Game class is UI-free. Renderer reads game state and draws it; AIEngine
reads and temporarily mutates game state during look-ahead with snap/restore.
"""

import random

from .constants import (
    GRID_ROWS, GRID_COLS, BASE, SPAWN, DIRS,
    Cell, GameState, RoomType,
    HUNTER_MAX_HP, ASWANG_MAX_HP, FINAL_ASWANG_MAX_HP,
    ASWANG_ATTACK_DMG,
    GARLIC_DMG, WATER_DMG, AMULET_DMG,
    GARLIC_SLOW_TURNS, AMULET_DAZE_TURNS,
    SCORE_PER_TURN, SCORE_ITEM_PICKUP, SCORE_ITEM_USE, SCORE_WIN_BONUS,
    SCORE_FINAL_BONUS, HEAL_AMOUNT, REGULAR_BOSSES, INVENTORY_SIZE,
    POWERUPS_PER_ROOM, FINAL_POWERUPS_PER_ROOM, MIN_POWERUPS_ON_MAP,
    AI_DEPTH, FINAL_AI_DEPTH,
)
from .ai import AIEngine


class Game:
    """
    Holds the authoritative game state and exposes player actions.

    A run contains multiple regular boss rooms, safe rooms between bosses,
    and one final boss room. Losing in combat ends the whole run.
    """

    def __init__(self):
        self.ai = AIEngine()
        self.reset()

    def reset(self):
        """Start a fresh permadeath run from Stage 1."""
        self.hhp = HUNTER_MAX_HP
        self.inventory = []
        self.selected_item_index = 0
        self.turn = 0
        self.score = 0
        self.bosses_cleared = 0
        self.is_final_boss = False
        self.ai_depth = AI_DEPTH
        self.room_options = []
        self.weapon_options = []
        self.dmg_flash = 0
        self.item_flash = None
        self.facing = "down"
        self._start_boss_room(final=False)

    def _start_boss_room(self, final: bool = False):
        """Create a randomized 10x10 boss room while preserving run state."""
        self.grid = [[Cell.EMPTY] * GRID_COLS for _ in range(GRID_ROWS)]
        for r in range(GRID_ROWS):
            for c in range(GRID_COLS):
                if BASE[r][c]:
                    self.grid[r][c] = Cell.OBSTACLE

        self.hpos = (0, 0)
        self.apos = (9, 9)
        self.aswang_max_hp = FINAL_ASWANG_MAX_HP if final else ASWANG_MAX_HP
        self.ahp = self.aswang_max_hp
        self.is_final_boss = final
        self.ai_depth = FINAL_AI_DEPTH if final else AI_DEPTH
        self.slowed = 0
        self.dazed = 0
        self.state = GameState.PLAYING
        self.item_flash = None
        self.dmg_flash = 0

        extra_obstacles = 5 if final else 3
        open_cells = [
            (r, c)
            for r in range(GRID_ROWS)
            for c in range(GRID_COLS)
            if self.grid[r][c] == Cell.EMPTY and (r, c) not in (self.hpos, self.apos)
        ]
        random.shuffle(open_cells)
        for r, c in open_cells[:extra_obstacles]:
            self.grid[r][c] = Cell.OBSTACLE

        if final:
            self.msg = "Final Boss Room: defeat the stronger Aswang!"
        else:
            stage = self.bosses_cleared + 1
            self.msg = f"Boss Room {stage}/{REGULAR_BOSSES}: defeat the Aswang!"

        self._spawn_initial_powerups()

    def _spawn_initial_powerups(self):
        """Scatter one-time power-ups across valid spawn cells."""
        count = FINAL_POWERUPS_PER_ROOM if self.is_final_boss else POWERUPS_PER_ROOM
        self._spawn_powerups(count)

    def _spawn_powerups(self, count: int):
        """Scatter up to count power-ups across valid spawn cells."""
        if count <= 0:
            return

        pool = [Cell.GARLIC, Cell.WATER, Cell.AMULET]
        random.shuffle(pool)
        candidates = [
            cell for cell in SPAWN
            if self.grid[cell[0]][cell[1]] == Cell.EMPTY
            and cell != self.hpos
            and cell != self.apos
        ]
        random.shuffle(candidates)
        for i, cell in enumerate(candidates[:count]):
            self.grid[cell[0]][cell[1]] = pool[i % len(pool)]

    def _maybe_respawn_powerup(self):
        if len(self.inventory) >= INVENTORY_SIZE:
            return
        if self._count_pups() >= MIN_POWERUPS_ON_MAP:
            return
        self._spawn_powerups(MIN_POWERUPS_ON_MAP - self._count_pups())

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

    def move_hunter(self, dr: int, dc: int):
        """Move the Hunter one step, then let the Aswang take its turn."""
        if self.state not in (GameState.PLAYING, GameState.ROOM_CHOICE):
            return

        nr, nc = self.hpos[0] + dr, self.hpos[1] + dc
        if not self.valid(nr, nc):
            self.msg = "Invalid move: blocked or outside the grid."
            return

        if dr == -1:
            self.facing = "up"
        elif dr == 1:
            self.facing = "down"
        elif dc == -1:
            self.facing = "left"
        elif dc == 1:
            self.facing = "right"

        self.hpos = (nr, nc)

        if self.state == GameState.ROOM_CHOICE:
            self._enter_portal_at_hunter()
            return

        self._collect_item_at_hunter()
        self._contact_damage("The Aswang attacks!")

        self._check()
        if self.state == GameState.PLAYING:
            self._ai_turn()

    def _collect_item_at_hunter(self):
        cell = self.grid[self.hpos[0]][self.hpos[1]]
        names = {
            Cell.GARLIC: "Garlic Clove",
            Cell.WATER: "Holy Water",
            Cell.AMULET: "Sacred Amulet",
        }
        if cell not in names:
            return

        if not self._add_item_to_inventory(cell):
            self.msg = f"Inventory full. {names[cell]} stays on the ground."
            return

        self.grid[self.hpos[0]][self.hpos[1]] = Cell.EMPTY
        self.item_flash = self.hpos
        self.score += SCORE_ITEM_PICKUP
        self.msg = f"Picked up {names[cell]}!"

    def use_item(self):
        """Use the held power-up if the Hunter is adjacent to/on the Aswang."""
        if self.state != GameState.PLAYING:
            return
        item_index = self._selected_item_index()
        if item_index is None:
            self.msg = "No item to use!"
            return
        if self.dist(self.hpos, self.apos) > 1:
            self.msg = "Must be adjacent to the Aswang!"
            return

        it = self.inventory.pop(item_index)
        self._clamp_selected_item_index()
        self.score += SCORE_ITEM_USE

        if it == Cell.GARLIC:
            self.ahp -= GARLIC_DMG
            self.slowed = GARLIC_SLOW_TURNS
            self.msg = f"Garlic Clove used: Aswang -{GARLIC_DMG} HP and slowed."
        elif it == Cell.WATER:
            self.ahp -= WATER_DMG
            self.msg = f"Holy Water used: Aswang -{WATER_DMG} HP."
        elif it == Cell.AMULET:
            self.ahp -= AMULET_DMG
            self.dazed = AMULET_DAZE_TURNS
            self.msg = f"Sacred Amulet used: Aswang -{AMULET_DMG} HP and dazed."

        self._check()
        if self.state == GameState.PLAYING:
            self._ai_turn()

    def _selected_item_index(self):
        if not self.inventory:
            return None
        self._clamp_selected_item_index()
        return self.selected_item_index

    def selected_item(self):
        index = self._selected_item_index()
        return None if index is None else self.inventory[index]

    def _clamp_selected_item_index(self):
        if not self.inventory:
            self.selected_item_index = 0
            return
        self.selected_item_index = max(0, min(self.selected_item_index, len(self.inventory) - 1))

    def _add_item_to_inventory(self, item, select_new: bool = False) -> bool:
        if len(self.inventory) >= INVENTORY_SIZE:
            return False

        was_empty = not self.inventory
        self.inventory.append(item)
        if was_empty or select_new:
            self.selected_item_index = len(self.inventory) - 1
        return True

    def select_inventory_slot(self, index: int):
        if self.state != GameState.PLAYING:
            return
        if 0 <= index < len(self.inventory):
            self.selected_item_index = index
            names = {
                Cell.GARLIC: "Garlic Clove",
                Cell.WATER: "Holy Water",
                Cell.AMULET: "Sacred Amulet",
            }
            self.msg = f"Selected slot {index + 1}: {names[self.inventory[index]]}."
        else:
            self.msg = f"Inventory slot {index + 1} is empty."

    def choose_room(self, index: int):
        """Resolve a safe-room choice after clearing a regular boss."""
        if self.state != GameState.ROOM_CHOICE or index >= len(self.room_options):
            return

        choice = self.room_options[index]
        self.room_options = []

        if choice == RoomType.HEALING:
            old_hp = self.hhp
            self.hhp = min(HUNTER_MAX_HP, self.hhp + HEAL_AMOUNT)
            self.msg = f"Healing Room: recovered {self.hhp - old_hp} HP."
            self._advance_after_safe_room()
            return

        items = [Cell.GARLIC, Cell.WATER, Cell.AMULET]
        random.shuffle(items)
        self.weapon_options = items[: random.randint(2, 3)]
        self.state = GameState.WEAPON_CHOICE
        self.msg = "Weapon Room: choose one item with 1, 2, or 3."

    def _enter_portal_at_hunter(self):
        cell = self.grid[self.hpos[0]][self.hpos[1]]
        if cell == Cell.HEALING_PORTAL:
            self._enter_safe_room(RoomType.HEALING)
        elif cell == Cell.WEAPON_PORTAL:
            self._enter_safe_room(RoomType.WEAPON)
        else:
            self.msg = "Choose a portal: Weapon or Healing."

    def _enter_safe_room(self, room_type: RoomType):
        self.room_options = []
        self.grid[self.hpos[0]][self.hpos[1]] = Cell.EMPTY

        if room_type == RoomType.HEALING:
            old_hp = self.hhp
            self.hhp = min(HUNTER_MAX_HP, self.hhp + HEAL_AMOUNT)
            self.msg = f"Healing Room: recovered {self.hhp - old_hp} HP."
            self._advance_after_safe_room()
            return

        items = [Cell.GARLIC, Cell.WATER, Cell.AMULET]
        random.shuffle(items)
        self.weapon_options = items[: random.randint(2, 3)]
        self.state = GameState.WEAPON_CHOICE
        self.msg = "Weapon Room: choose one item with 1, 2, or 3."

    def choose_weapon(self, index: int):
        """Add one offered weapon/power-up to inventory and advance to the next boss."""
        if self.state != GameState.WEAPON_CHOICE or index >= len(self.weapon_options):
            return

        selected = self.weapon_options[index]
        names = {
            Cell.GARLIC: "Garlic Clove",
            Cell.WATER: "Holy Water",
            Cell.AMULET: "Sacred Amulet",
        }
        self.weapon_options = []
        if self._add_item_to_inventory(selected, select_new=True):
            reward_msg = f"Added {names[selected]} to inventory."
        else:
            self._clamp_selected_item_index()
            replaced = self.inventory[self.selected_item_index]
            self.inventory[self.selected_item_index] = selected
            reward_msg = f"Inventory full: replaced selected {names[replaced]} with {names[selected]}."
        self._advance_after_safe_room()
        self.msg = f"{reward_msg} {self.msg}"

    def _advance_after_safe_room(self):
        final = self.bosses_cleared >= REGULAR_BOSSES
        self._start_boss_room(final=final)

    def _ai_turn(self):
        self.turn += 1

        if self.slowed > 0:
            self.slowed -= 1
            self._check()
            self._award_survival_points()
            return

        if self.dazed > 0:
            self.dazed -= 1
            moves = self.moves(self.apos)
            if moves:
                self.apos = random.choice(moves)
        else:
            best = self.ai.get_best_move(self)
            if best:
                self.apos = best

        self._contact_damage("The Aswang found you!")

        self._maybe_respawn_powerup()
        self._check()
        self._award_survival_points()

    def _contact_damage(self, prefix: str):
        if self.hpos != self.apos:
            return
        self.hhp -= ASWANG_ATTACK_DMG
        self.msg = f"{prefix} -{ASWANG_ATTACK_DMG} HP"
        self.dmg_flash = 8

    def _award_survival_points(self):
        if self.state == GameState.PLAYING:
            self.score += SCORE_PER_TURN

    def _check(self):
        self.hhp = max(0, self.hhp)
        self.ahp = max(0, self.ahp)

        if self.hhp <= 0 and self.ahp <= 0:
            self.state = GameState.DRAW
        elif self.ahp <= 0:
            self._clear_boss()
        elif self.hhp <= 0:
            self.state = GameState.LOSE
            self.msg = "Permadeath: the run is over."

    def _clear_boss(self):
        self.score += SCORE_WIN_BONUS

        if self.is_final_boss:
            self.score += SCORE_FINAL_BONUS
            self.state = GameState.WIN
            self.msg = "Run complete! The final Aswang has been banished."
            return

        self.bosses_cleared += 1
        self.room_options = []
        self._spawn_room_portals()
        self.state = GameState.ROOM_CHOICE
        self.msg = "Boss cleared! Enter a portal: Weapon or Healing."

    def _spawn_room_portals(self):
        for r in range(GRID_ROWS):
            for c in range(GRID_COLS):
                if self.grid[r][c] in (
                    Cell.GARLIC, Cell.WATER, Cell.AMULET,
                    Cell.WEAPON_PORTAL, Cell.HEALING_PORTAL,
                ):
                    self.grid[r][c] = Cell.EMPTY

        candidates = []
        for r in range(GRID_ROWS):
            for c in range(GRID_COLS):
                pos = (r, c)
                if pos == self.hpos or self.grid[r][c] != Cell.EMPTY:
                    continue
                distance = self.dist(self.hpos, pos)
                candidates.append((distance, pos))

        candidates.sort(key=lambda item: item[0])
        nearby = [pos for _, pos in candidates if self.dist(self.hpos, pos) <= 4]
        portal_cells = nearby[:2] if len(nearby) >= 2 else [pos for _, pos in candidates[:2]]

        if len(portal_cells) >= 2:
            self.grid[portal_cells[0][0]][portal_cells[0][1]] = Cell.WEAPON_PORTAL
            self.grid[portal_cells[1][0]][portal_cells[1][1]] = Cell.HEALING_PORTAL

    def _snap(self) -> dict:
        return {
            "hhp": self.hhp,
            "ahp": self.ahp,
            "hpos": self.hpos,
            "apos": self.apos,
            "sl": self.slowed,
            "dz": self.dazed,
            "depth": self.ai_depth,
            "amax": self.aswang_max_hp,
            "grid": [row[:] for row in self.grid],
            "inventory": self.inventory[:],
            "selected": self.selected_item_index,
        }

    def _restore(self, snap: dict):
        self.hhp = snap["hhp"]
        self.ahp = snap["ahp"]
        self.hpos = snap["hpos"]
        self.apos = snap["apos"]
        self.slowed = snap["sl"]
        self.dazed = snap["dz"]
        self.ai_depth = snap["depth"]
        self.aswang_max_hp = snap["amax"]
        self.grid = [row[:] for row in snap["grid"]]
        self.inventory = snap["inventory"][:]
        self.selected_item_index = snap["selected"]
