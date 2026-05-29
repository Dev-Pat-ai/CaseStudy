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
from typing import Optional, Tuple

from .constants import GRID_ROWS, GRID_COLS, Cell, AI_DEPTH, ASWANG_ATTACK_DMG


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
            snap = game._snap()
            game.apos = move
            if game.apos == game.hpos:
                game.hhp -= ASWANG_ATTACK_DMG

            depth = getattr(game, "ai_depth", AI_DEPTH)
            value = self._minimax(game, depth - 1, alpha, beta, is_maximizing=False)
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
            for move in game.moves(game.apos):
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
            for move in game.moves(game.hpos):
                snap      = game._snap()
                game.hpos = move
                if game.hpos == game.apos:
                    game.hhp -= ASWANG_ATTACK_DMG

                value = self._minimax(game, depth - 1, alpha, beta, True)
                best  = min(best, value)
                beta  = min(beta, value)
                game._restore(snap)

                if beta <= alpha:
                    break               # α-cutoff (alpha pruning)
            return best

    # ── Heuristic evaluation ──────────────────────────────────────────
    def _evaluate(self, game) -> float:
        """
        Score a leaf/terminal state from the Aswang's perspective.

        Higher score  → better for the Aswang.
        Lower score   → better for the Hunter.

        Higher values favor the Aswang:
        close distance, low Hunter HP, healthy Aswang HP, fewer nearby
        Hunter power-ups, and no active Aswang debuffs.
        """
        distance = (
            abs(game.apos[0] - game.hpos[0])
            + abs(game.apos[1] - game.hpos[1])
        )

        nearby_powerups = sum(
            1
            for r in range(GRID_ROWS)
            for c in range(GRID_COLS)
            if game.grid[r][c] in (Cell.GARLIC, Cell.WATER, Cell.AMULET)
            and abs(r - game.hpos[0]) + abs(c - game.hpos[1]) <= 3
        )

        aswang_max = getattr(game, "aswang_max_hp", 100)
        return (
            8 * (10 - distance)
            + 2 * (100 - game.hhp)
            - 2 * (aswang_max - game.ahp)
            - 6 * nearby_powerups
            - (18 if game.dazed > 0 else 0)
            - (12 if game.slowed > 0 else 0)
        )
