# 🌑 Aswang Hunter — Enhanced Edition
### Game AI Case Study | Minimax with Alpha-Beta Pruning

---

## 📁 Project Structure

```
aswang-hunter/
│
├── main.py                 ← Entry point — run this
├── requirements.txt        ← pip dependencies
│
├── src/
│   ├── __init__.py
│   ├── constants.py        ← All colours, grid sizes, gameplay numbers, enums, map data
│   ├── sprites.py          ← Procedural sprite drawing functions (hunter, aswang, items)
│   ├── ai.py               ← AIEngine: Minimax + Alpha-Beta Pruning
│   ├── game.py             ← Game class: state, turn logic, win/loss
│   └── renderer.py         ← Renderer class + title_screen()
│
└── assets/
    ├── fonts/              ← Drop custom .ttf fonts here (future use)
    ├── sounds/             ← Drop BGM / SFX .ogg or .wav files here (future use)
    └── images/             ← Drop sprite sheets here (future use)
```

---

## 🚀 How to Run

```bash
# 1. Install dependency
pip install pygame==2.6.1

# 2. Run the game from the project root
python main.py
```

---

## 🎮 Controls

| Key | Action |
|---|---|
| ← ↑ ↓ → | Move the Hunter |
| SPACE | Use held item (must be adjacent to Aswang) |
| R | Restart the game |
| Q | Quit |

---

## ✨ Visual Enhancements (vs. original)

| # | Enhancement | Where implemented |
|---|---|---|
| 1 | **Fog of War** | `renderer._draw_fog()` — reveals cells within Manhattan distance 4 of the Hunter; Aswang's cell always partially visible |
| 2 | **Blood Moon Sky** | `renderer._draw_sky()` — animated gradient sky + pulsing red moon replaces flat background fill |
| 3 | **Smooth HP Bars** | `renderer.display_hhp/ahp` — display values interpolate toward real HP each frame (0.12 lerp factor) |
| 4 | **Screen Shake** | `renderer.shake` — grid surface blitted with random ±8 px offset for 8 frames on damage; HUD is unaffected |
| 5 | **Item Pickup Flash** | `renderer.item_flash_cells` — golden cell flash (15 frames) when the Hunter walks over a power-up |

---

## 🤖 AI Algorithm: Minimax with Alpha-Beta Pruning

### Overview
The Aswang is controlled by `AIEngine` in `src/ai.py`.  
Every turn it calls `get_best_move(game)`, which runs a depth-4 Minimax search
over all possible future positions and returns the cell that maximises the
heuristic evaluation score.

### Heuristic (`_evaluate`)
```
eval = (10 / distance(Aswang, Hunter))   ← closer = better for Aswang
     + (100 − Hunter_HP)                 ← lower Hunter HP = better
     − Aswang_HP                         ← lower Aswang HP = worse
     − 5 × powerups_near_hunter(r≤3)     ← nearby items help the Hunter
     − 5 × (1 if dazed)                  ← dazed state penalises Aswang
```

### Alpha-Beta Pruning
`alpha` tracks the Aswang's (Maximizer) best guaranteed value;
`beta` tracks the Hunter's (Minimizer) best guaranteed value.
A branch is pruned whenever `beta ≤ alpha`, skipping subtrees that
can never influence the final decision.

---

## 📊 Game Rules Summary

| | Hunter | Aswang |
|---|---|---|
| Starting HP | 100 | 80 |
| Contact damage | −15 HP per turn | — |
| Garlic | — | −20 HP + slowed 2 turns |
| Holy Water | — | −30 HP |
| Sacred Amulet | — | −40 HP + dazed 3 turns |

**Win** — Aswang HP reaches 0 first (+100 score bonus)  
**Lose** — Hunter HP reaches 0 first  
**Draw** — Both reach 0 simultaneously

---

*Built with Python 3.11+ and Pygame 2.6*
