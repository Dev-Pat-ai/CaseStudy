# Aswang Hunter

Game AI Case Study using Minimax with Alpha-Beta Pruning, built with Python and Pygame.

---

## Project Structure

```text
aswang-hunter/
|-- main.py                         Entry point
|-- requirements.txt                Python dependencies
|
|-- src/
|   |-- constants.py                Colors, grid sizes, gameplay values, enums, map data
|   |-- ai.py                       AIEngine: Minimax + Alpha-Beta Pruning
|   |-- game.py                     Game state, turn logic, room flow, win/loss logic
|   |-- hunter_sprite.py            Hunter sprite-sheet loader
|   |-- renderer.py                 Pygame renderer, HUD, overlays, title screen
|   `-- sprites.py                  Sprite drawing and PNG sprite loading
|
|-- assets/
|   |-- sprite/
|   |   |-- sprite_hunter.png       Hunter sprite sheet
|   |   |-- aswang_flying.png       Animated Aswang flying sheet
|   |   |-- aswang.png              Backup/static Aswang sprite
|   |   |-- garlic.png              Garlic item sprite
|   |   |-- holy_water.png          Holy water item sprite
|   |   |-- amulet.png              Amulet item sprite
|   |   `-- tile_floor.png          Optional generated tile asset
|   `-- sounds/                     Future sound effects/music
|
`-- tools/
    |-- generate_sprite_assets.py   Generates simple PNG placeholder assets
    `-- extract_aswang_sprite_sheet.py
                                      Extracts clean Aswang frames from a full reference sheet
```

---

## How to Run

```bash
pip install -r requirements.txt
python main.py
```

---

## Controls

| Key | Action |
|---|---|
| Arrow keys / WASD | Move the Hunter |
| SPACE | Use selected inventory item when adjacent to the Aswang |
| R | Ask to reset the game |
| Q | Ask to quit |
| Y | Confirm reset/quit prompt |
| N or ESC | Cancel reset/quit prompt |
| 1, 2, 3 | Select inventory slot during combat, or choose item when prompted |

---

## Visual Features

| Feature | Where |
|---|---|
| Fog of war | `Renderer._draw_fog()` |
| Blood moon sky | `Renderer._draw_sky()` |
| Smooth HP bars | `Renderer.display_hhp` and `Renderer.display_ahp` |
| Screen shake | `Renderer.shake` |
| Item pickup flash | `Renderer.item_flash_cells` |
| Animated hunter sprite | `src/hunter_sprite.py` and `draw_hunter()` |
| Animated Aswang flying sprite | `assets/sprite/aswang_flying.png` and `draw_aswang()` |
| Confirmation overlays | `Renderer._draw_confirm_overlay()` |

---

## Sprite Notes

The Aswang uses a cleaned sprite sheet at:

```text
assets/sprite/aswang_flying.png
```

If you have a new full Aswang reference sheet, regenerate the in-game flying sheet with:

```bash
python tools/extract_aswang_sprite_sheet.py C:/path/to/Aswang.png
```

The generated PNG assets are loaded first. If an asset is missing, the game falls back to procedural Pygame drawing so it can still run.

---

## Inventory Rules

The Hunter has 3 inventory slots.

| Rule | Behavior |
|---|---|
| Picking up an item | Adds it to inventory if there is space |
| Inventory full | Ground pickup stays on the map |
| Regular boss room pickups | 3 total pickups spawn at room start |
| Final boss room pickups | 2 total pickups spawn at room start |
| Mid-fight item respawn | Keeps at least 1 pickup on the map if inventory has space |
| Weapon Room reward | Adds the chosen item to inventory; if full, replaces the selected slot |
| Select item | Press `1`, `2`, or `3` during combat |
| Use item | Press `SPACE` while adjacent to the Aswang |
| Used item | Removed from inventory |
| No selected item | The first available item is selected automatically |

---

## AI Algorithm

The Aswang is controlled by `AIEngine` in `src/ai.py`.

Each Aswang turn calls `get_best_move(game)`, which searches possible future moves using Minimax with Alpha-Beta Pruning and chooses the move with the best heuristic score. The search now simulates Hunter movement, item pickup, and item use so the Aswang can react to inventory danger instead of only chasing directly.

Simplified heuristic idea:

```text
score = pathfinding_pressure
      + escape_route_pressure
      + hunter_damage_bonus
      - aswang_damage_penalty
      - hunter_inventory_danger
      - powerup_access_penalty
      - dazed_penalty
```

The AI uses pathfinding distance instead of plain Manhattan distance, checks how many safe escape routes the Hunter has, and values moves that contest nearby power-ups. Its current personality is aggressive: it strongly prefers closing distance and attacking, but it becomes more cautious when the Hunter has enough item damage to finish it.

`alpha` tracks the Aswang's best guaranteed value, while `beta` tracks the Hunter's best guaranteed value. Branches are skipped when they can no longer improve the result.

---

## Game Rules Summary

| | Hunter | Aswang |
|---|---:|---:|
| Starting HP | 100 | 100 |
| Final boss HP | 100 | 200 |
| Contact damage | -15 HP per Aswang attack | - |
| Garlic | - | -20 HP and slowed |
| Holy Water | - | -30 HP |
| Sacred Amulet | - | -40 HP and dazed |

Win by defeating all boss rooms, including the final Aswang. Losing in combat ends the run.

---

Built with Python 3 and Pygame 2.6.
