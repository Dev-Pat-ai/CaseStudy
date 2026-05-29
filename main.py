"""
main.py
Entry point for Aswang Hunter — Enhanced Edition.

Run from the project root:
    python main.py
"""

import pygame
import sys

from src.constants import SCREEN_W, SCREEN_H, FPS, GameState
from src.game     import Game
from src.renderer import Renderer, title_screen, tutorial_screen


CONFIRM_RESET = "reset"
CONFIRM_QUIT = "quit"


def reset_game(game, renderer):
    game.reset()
    # Snap the smooth HP display to the reset values immediately.
    renderer.display_hhp = float(game.hhp)
    renderer.display_ahp = float(game.ahp)
    renderer.shake       = 0
    renderer.particles   = []
    renderer.item_flash_cells = {}


def main():
    pygame.init()
    pygame.display.set_caption("Aswang Hunter — Enhanced Edition  |  Game AI Case Study")
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H), pygame.RESIZABLE)
    clock  = pygame.time.Clock()

    # Show splash/title screen
    title_screen(screen, clock)
    tutorial_screen(screen, clock)

    game     = Game()
    renderer = Renderer(screen)
    pending_command = None

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.VIDEORESIZE:
                screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
                renderer.update_screen(screen)

            if event.type == pygame.KEYDOWN:
                if pending_command:
                    if event.key == pygame.K_y:
                        if pending_command == CONFIRM_QUIT:
                            pygame.quit()
                            sys.exit()

                        reset_game(game, renderer)
                        game.msg = "Game restarted."
                        pending_command = None
                    elif event.key in (pygame.K_n, pygame.K_ESCAPE):
                        game.msg = "Command canceled."
                        pending_command = None
                    elif event.key == pygame.K_r:
                        pending_command = CONFIRM_RESET
                        game.msg = "Reset game? Press Y to reset or N to cancel."
                    elif event.key == pygame.K_q:
                        pending_command = CONFIRM_QUIT
                        game.msg = "Quit game? Press Y to quit or N to cancel."
                    continue

                if event.key == pygame.K_q:
                    pending_command = CONFIRM_QUIT
                    game.msg = "Quit game? Press Y to quit or N to cancel."
                    continue

                if event.key == pygame.K_r:
                    pending_command = CONFIRM_RESET
                    game.msg = "Reset game? Press Y to reset or N to cancel."
                    continue

                if game.state in (GameState.PLAYING, GameState.ROOM_CHOICE):
                    if game.state == GameState.PLAYING and event.key == pygame.K_1:
                        game.select_inventory_slot(0)
                    elif game.state == GameState.PLAYING and event.key == pygame.K_2:
                        game.select_inventory_slot(1)
                    elif game.state == GameState.PLAYING and event.key == pygame.K_3:
                        game.select_inventory_slot(2)
                    elif event.key in (pygame.K_UP,    pygame.K_w): game.move_hunter(-1,  0)
                    elif event.key in (pygame.K_DOWN,  pygame.K_s): game.move_hunter( 1,  0)
                    elif event.key in (pygame.K_LEFT,  pygame.K_a): game.move_hunter( 0, -1)
                    elif event.key in (pygame.K_RIGHT, pygame.K_d): game.move_hunter( 0,  1)
                    elif game.state == GameState.PLAYING and event.key == pygame.K_SPACE:
                        game.use_item()
                elif game.state == GameState.WEAPON_CHOICE:
                    if event.key == pygame.K_1: game.choose_weapon(0)
                    elif event.key == pygame.K_2: game.choose_weapon(1)
                    elif event.key == pygame.K_3: game.choose_weapon(2)

        renderer.draw(game, pending_command)
        clock.tick(FPS)


if __name__ == "__main__":
    main()

