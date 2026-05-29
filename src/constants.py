"""
constants.py
All game-wide constants, colour palette, enums, and static map data.
"""

from enum import Enum

# ─────────────────────────────────────────────
#  DISPLAY
# ─────────────────────────────────────────────
GRID_COLS  = 10
GRID_ROWS  = 10
CELL       = 68
HUD_W      = 260
GRID_W     = GRID_COLS * CELL
SCREEN_W   = GRID_W + HUD_W
SCREEN_H   = GRID_ROWS * CELL
GRID_H     = GRID_ROWS * CELL
FPS        = 30

# ─────────────────────────────────────────────
#  AI
# ─────────────────────────────────────────────
AI_DEPTH       = 4
FINAL_AI_DEPTH = 6

# ─────────────────────────────────────────────
#  VISUAL EFFECTS
# ─────────────────────────────────────────────
FOG_RADIUS = 4          # Manhattan-distance vision radius for the hunter

# ─────────────────────────────────────────────
#  GAMEPLAY NUMBERS
# ─────────────────────────────────────────────
HUNTER_MAX_HP      = 100
ASWANG_MAX_HP      = 100
FINAL_ASWANG_MAX_HP = 200
ASWANG_ATTACK_DMG  = 15

GARLIC_DMG         = 20
WATER_DMG          = 30
AMULET_DMG         = 40

GARLIC_SLOW_TURNS  = 2
AMULET_DAZE_TURNS  = 3

SCORE_PER_TURN     = 5
SCORE_ITEM_PICKUP  = 10
SCORE_ITEM_USE     = 0
SCORE_WIN_BONUS    = 100
SCORE_FINAL_BONUS  = 250

HEAL_AMOUNT        = 30
REGULAR_BOSSES     = 3

# ─────────────────────────────────────────────
#  COLOUR PALETTE
# ─────────────────────────────────────────────
C_BG        = ( 28,  38,  28)
C_TILE_A    = ( 24,  34,  24)
C_TILE_B    = ( 20,  30,  20)
C_TILE_C    = ( 18,  28,  18)
C_GRID      = ( 60, 100,  60)
C_TREE_TRK  = ( 45,  28,  12)
C_TREE_TOP  = ( 20,  55,  20)
C_TREE_TOP2 = ( 15,  45,  15)
C_TREE_SHD  = (  8,  20,   8)

C_HUNTER    = (100, 210, 130)
C_HUNTER2   = ( 60, 160,  90)
C_ASWANG    = (210,  50,  50)
C_ASWANG2   = (160,  20,  20)
C_EYE       = (255, 220,  80)

C_GARLIC    = (230, 235, 130)
C_WATER     = ( 90, 180, 255)
C_AMULET    = (210,  90, 255)

C_HUD_BG    = (  6,  10,   6)
C_HUD_BORD  = (120, 180, 120)
C_GOLD      = (255, 210,  60)
C_SILVER    = (210, 220, 230)
C_WHITE     = (255, 255, 255)
C_BLACK     = (  0,   0,   0)
C_RED_HP    = (220,  55,  55)
C_YEL_HP    = (220, 190,  55)
C_GRN_HP    = ( 55, 200,  80)
C_LOG       = (220, 240, 220)
C_DIM       = (210, 225, 225)

# ─────────────────────────────────────────────
#  ENUMS
# ─────────────────────────────────────────────
class Cell(Enum):
    EMPTY    = 0
    OBSTACLE = 1
    GARLIC   = 2
    WATER    = 3
    AMULET   = 4
    WEAPON_PORTAL = 5
    HEALING_PORTAL = 6

class GameState(Enum):
    PLAYING       = 0
    ROOM_CHOICE   = 1
    WEAPON_CHOICE = 2
    WIN           = 3
    LOSE          = 4
    DRAW          = 5

class RoomType(Enum):
    HEALING = 0
    WEAPON  = 1

# ─────────────────────────────────────────────
#  STATIC MAP DATA
# ─────────────────────────────────────────────
BASE = [
    [0, 0, 0, 0, 1, 0, 0, 0, 0, 0],
    [0, 1, 0, 0, 0, 0, 1, 0, 1, 0],
    [0, 1, 0, 1, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 1, 0, 1, 0, 1, 0, 0],
    [0, 0, 1, 0, 0, 0, 0, 1, 0, 0],
    [0, 0, 1, 0, 1, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 1, 0, 1, 0, 0],
    [0, 1, 0, 1, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 1, 0, 1, 0],
    [0, 0, 0, 0, 1, 0, 0, 0, 0, 0],
]

SPAWN = [
    (0, 2), (0, 7), (1, 4), (2, 5), (2, 8), (3, 2), (4, 4), (5, 5),
    (6, 3), (7, 5), (8, 1), (8, 6), (9, 1), (9, 6), (9, 8),
]

DIRS = [(-1, 0), (1, 0), (0, -1), (0, 1)]
