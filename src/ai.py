"""
ai.py
AIEngine — Minimax with Alpha-Beta Pruning.

The engine is intentionally decoupled from the Game class:
it receives a Game instance only as a read/write context during search,
using Game._snap() / Game._restore() to undo simulated moves so the
real game state is never permanently modified during look-ahead.
"""

import math
import random
from collections import deque
from typing import Optional, Tuple

from .constants import (
    GRID_ROWS, GRID_COLS, DIRS,
    Cell, AI_DEPTH, ASWANG_ATTACK_DMG, INVENTORY_SIZE,
    GARLIC_DMG, WATER_DMG, AMULET_DMG,
    GARLIC_SLOW_TURNS, AMULET_DAZE_TURNS,
)


POWERUPS = (Cell.GARLIC, Cell.WATER, Cell.AMULET)


class AIEngine:
    """
    Drives the Aswang's decision-making each turn.

    Usage
    -----
    engine = AIEngine()
    best_move = engine.get_best_move(game)   # returns (row, col) or None
    """

    # ── Public interface ──────────────────────────────────────────────
    def get_best_move(self, game) -> Optional[Tuple[int, int]]:
        """
        Return the best adjacent cell for the Aswang to move to,
        or None if no moves are available.

        Iterates over all legal Aswang moves, runs Minimax from each
        resulting state, and returns the move with the highest evaluation.
        Alpha-Beta pruning is applied from the root.
        """
        moves = game.moves(game.apos)
        if not moves:
            return None

        best_move  = moves[0]
        best_value = -math.inf
        alpha      = -math.inf
        beta       =  math.inf

        for move in moves:
            if move == game.hpos:
                return move

            snap = game._snap()
            game.apos = move
            if game.apos == game.hpos:
                game.hhp -= ASWANG_ATTACK_DMG

            depth = getattr(game, "ai_depth", AI_DEPTH)
            value = self._minimax(game, depth - 1, alpha, beta, is_maximizing=False)
            value += self._root_aggression_bonus(game, move)
            game._restore(snap)

            if value > best_value:
                best_value = value
                best_move  = move

            alpha = max(alpha, value)
            # No beta cut at root level; we need to evaluate all children
            # to guarantee the globally best move is found.

        return best_move

    # ── Minimax core ──────────────────────────────────────────────────
    def _minimax(self, game, depth: int, alpha: float, beta: float,
                 is_maximizing: bool) -> float:
        """
        Recursive Minimax with Alpha-Beta Pruning.

        Parameters
        ----------
        game          : current (possibly simulated) game state
        depth         : remaining look-ahead plies
        alpha         : best value the Maximizer (Aswang) can guarantee
        beta          : best value the Minimizer (Hunter) can guarantee
        is_maximizing : True on the Aswang's ply, False on the Hunter's
        """
        if depth == 0 or game.hhp <= 0 or game.ahp <= 0:
            return self._evaluate(game)

        if is_maximizing:                       # ── Aswang's turn ──
            best = -math.inf
            for move in self._ordered_aswang_moves(game):
                snap      = game._snap()
                game.apos = move
                if game.apos == game.hpos:
                    game.hhp -= ASWANG_ATTACK_DMG

                value = self._minimax(game, depth - 1, alpha, beta, False)
                best  = max(best, value)
                alpha = max(alpha, value)
                game._restore(snap)

                if beta <= alpha:
                    break               # β-cutoff (beta pruning)
            return best

        else:                                   # ── Hunter's turn ──
            best = math.inf
            actions = self._hunter_actions(game)
            if not actions:
                return self._evaluate(game)

            for action, move in actions:
                snap = game._snap()
                if action == "use":
                    self._simulate_hunter_item_use(game)
                else:
                    self._simulate_hunter_move(game, move)

                value = self._minimax(game, depth - 1, alpha, beta, True)
                best  = min(best, value)
                beta  = min(beta, value)
                game._restore(snap)

                if beta <= alpha:
                    break               # α-cutoff (alpha pruning)
            return best

    # ── Heuristic evaluation ──────────────────────────────────────────
    def _ordered_aswang_moves(self, game) -> list:
        moves = game.moves(game.apos)
        random.shuffle(moves)
        return sorted(moves, key=lambda move: self._path_distance(game, move, game.hpos))

    def _root_aggression_bonus(self, game, move) -> float:
        old_distance = self._path_distance(game, game.apos, game.hpos)
        new_distance = self._path_distance(game, move, game.hpos)
        bonus = 0
        if new_distance < old_distance:
            bonus += 35
        if new_distance <= 2:
            bonus += 45
        if new_distance <= 1:
            bonus += 90
        if new_distance > old_distance:
            bonus -= 55
        return bonus

    def _hunter_actions(self, game) -> list:
        actions = []
        if game.inventory and self._path_distance(game, game.hpos, game.apos) <= 1:
            actions.append(("use", None))
        actions.extend(("move", move) for move in game.moves(game.hpos))
        return actions

    def _simulate_hunter_move(self, game, move):
        game.hpos = move
        cell = game.grid[move[0]][move[1]]
        if cell in POWERUPS and len(game.inventory) < INVENTORY_SIZE:
            game.inventory.append(cell)
            game.grid[move[0]][move[1]] = Cell.EMPTY
        if game.hpos == game.apos:
            game.hhp -= ASWANG_ATTACK_DMG

    def _simulate_hunter_item_use(self, game):
        if not game.inventory:
            return
        index = max(0, min(getattr(game, "selected_item_index", 0), len(game.inventory) - 1))
        item = game.inventory.pop(index)
        if item == Cell.GARLIC:
            game.ahp -= GARLIC_DMG
            game.slowed = GARLIC_SLOW_TURNS
        elif item == Cell.WATER:
            game.ahp -= WATER_DMG
        elif item == Cell.AMULET:
            game.ahp -= AMULET_DMG
            game.dazed = AMULET_DAZE_TURNS
        if not game.inventory:
            game.selected_item_index = 0
        else:
            game.selected_item_index = max(0, min(index, len(game.inventory) - 1))

    def _evaluate(self, game) -> float:
        """
        Score a leaf/terminal state from the Aswang's perspective.

        Higher score  → better for the Aswang.
        Lower score   → better for the Hunter.

        Higher values favor the Aswang:
        close distance, low Hunter HP, healthy Aswang HP, fewer nearby
        Hunter power-ups, and no active Aswang debuffs.
        """
        aswang_distances = self._path_distances(game, game.apos)
        hunter_distances = self._path_distances(game, game.hpos)
        distance = aswang_distances.get(game.hpos, 99)
        if distance == 99:
            distance = game.dist(game.apos, game.hpos) + 8

        hunter_moves = game.moves(game.hpos)
        safe_escape_count = sum(
            1 for move in hunter_moves
            if aswang_distances.get(move, 99) > 1
        )
        best_escape_distance = max(
            [aswang_distances.get(move, 99) for move in hunter_moves] or [distance]
        )

        powerup_threat = 0
        for r in range(GRID_ROWS):
            for c in range(GRID_COLS):
                if game.grid[r][c] not in POWERUPS:
                    continue
                pos = (r, c)
                hdist = hunter_distances.get(pos, 99)
                adist = aswang_distances.get(pos, 99)
                if hdist <= 3:
                    powerup_threat += 14
                if hdist < adist:
                    powerup_threat += 9
                elif adist <= hdist:
                    powerup_threat -= 4

        inventory_danger = len(getattr(game, "inventory", [])) * 4
        item_kill_risk = 0
        max_item_damage = self._max_inventory_damage(game)
        if game.inventory and distance <= 1 and max_item_damage >= game.ahp:
            item_kill_risk = 65
        elif game.inventory and distance <= 1:
            item_kill_risk = 8
        elif game.inventory and distance == 2:
            item_kill_risk = 4

        aswang_max = getattr(game, "aswang_max_hp", 100)
        return (
            28 * (12 - distance)
            + (140 if distance <= 1 else 0)
            + (55 if distance == 2 else 0)
            - 7 * safe_escape_count
            - 2 * best_escape_distance
            + 3 * (100 - game.hhp)
            - 2 * (aswang_max - game.ahp)
            - powerup_threat
            - inventory_danger
            - item_kill_risk
            - (35 if game.dazed > 0 else 0)
            - (24 if game.slowed > 0 else 0)
        )

    def _max_inventory_damage(self, game) -> int:
        damage = 0
        for item in getattr(game, "inventory", []):
            if item == Cell.GARLIC:
                damage = max(damage, GARLIC_DMG)
            elif item == Cell.WATER:
                damage = max(damage, WATER_DMG)
            elif item == Cell.AMULET:
                damage = max(damage, AMULET_DMG)
        return damage

    def _path_distance(self, game, start: tuple, goal: tuple) -> int:
        return self._path_distances(game, start).get(goal, 99)

    def _path_distances(self, game, start: tuple) -> dict:
        if not game.valid(start[0], start[1]):
            return {}

        distances = {start: 0}
        queue = deque([start])
        while queue:
            r, c = queue.popleft()
            for dr, dc in DIRS:
                nr, nc = r + dr, c + dc
                nxt = (nr, nc)
                if nxt in distances or not game.valid(nr, nc):
                    continue
                distances[nxt] = distances[(r, c)] + 1
                queue.append(nxt)
        return distances
