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
from src.renderer import Renderer, title_screen


def main():
    pygame.init()
    pygame.display.set_caption("Aswang Hunter — Enhanced Edition  |  Game AI Case Study")
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H), pygame.RESIZABLE)
    clock  = pygame.time.Clock()

    # Show splash/title screen
    title_screen(screen, clock)

    game     = Game()
    renderer = Renderer(screen)

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.VIDEORESIZE:
                screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
                renderer.update_screen(screen)

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_q:
                    pygame.quit()
                    sys.exit()

                if event.key == pygame.K_r:
                    game.reset()
                    # Snap the smooth HP display to the reset values immediately
                    renderer.display_hhp = float(game.hhp)
                    renderer.display_ahp = float(game.ahp)
                    renderer.shake       = 0
                    renderer.particles   = []

                if game.state == GameState.PLAYING:
                    if   event.key in (pygame.K_UP,    pygame.K_w): game.move_hunter(-1,  0)
                    elif event.key in (pygame.K_DOWN,  pygame.K_s): game.move_hunter( 1,  0)
                    elif event.key in (pygame.K_LEFT,  pygame.K_a): game.move_hunter( 0, -1)
                    elif event.key in (pygame.K_RIGHT, pygame.K_d): game.move_hunter( 0,  1)
                    elif event.key == pygame.K_SPACE:                game.use_item()

        renderer.draw(game)
        clock.tick(FPS)


if __name__ == "__main__":
    main()

