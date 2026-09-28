"""Jouer au niveau 1-1 au clavier (ou à la manette) avec pygame.

    python -m mario_env.play            # ou : python play.py

Touches : flèches (ou WASD / ZQSD) pour bouger, X / K / Espace = saut (A),
Z / J / W-shift = courir / boule de feu (B), Entrée = pause, Échap = quitter.
Flèche bas sur le 4e tuyau pour entrer dans la salle bonus.
"""

import argparse
import os
import sys

from . import constants as C
from .game import Game, GameConfig
from .renderer import Renderer

INTERMISSION_FRAMES = 150
GAMEOVER_FRAMES = 240


def _buttons_from_keys(pygame, keys, joy):
    b = 0
    k = pygame
    if keys[k.K_RIGHT] or keys[k.K_d]:
        b |= C.BTN_RIGHT
    if keys[k.K_LEFT] or keys[k.K_a] or keys[k.K_q]:
        b |= C.BTN_LEFT
    if keys[k.K_DOWN] or keys[k.K_s]:
        b |= C.BTN_DOWN
    if keys[k.K_UP] or keys[k.K_w]:
        b |= C.BTN_UP
    if keys[k.K_x] or keys[k.K_k] or keys[k.K_SPACE]:
        b |= C.BTN_A
    if keys[k.K_c] or keys[k.K_j] or keys[k.K_LSHIFT] or keys[k.K_RSHIFT] \
            or keys[k.K_z]:
        b |= C.BTN_B
    if joy is not None:
        try:
            hx, hy = joy.get_hat(0) if joy.get_numhats() else (0, 0)
            ax = joy.get_axis(0) if joy.get_numaxes() else 0.0
            ay = joy.get_axis(1) if joy.get_numaxes() > 1 else 0.0
            if hx > 0 or ax > 0.5:
                b |= C.BTN_RIGHT
            if hx < 0 or ax < -0.5:
                b |= C.BTN_LEFT
            if hy < 0 or ay > 0.5:
                b |= C.BTN_DOWN
            if joy.get_numbuttons() > 0 and joy.get_button(0):
                b |= C.BTN_A
            if joy.get_numbuttons() > 2 and (joy.get_button(2)
                                             or joy.get_button(1)):
                b |= C.BTN_B
        except Exception:
            pass
    return b


def main(argv=None):
    parser = argparse.ArgumentParser(description="Super Mario Bros. 1-1")
    parser.add_argument("--scale", type=int, default=3,
                        help="facteur d'agrandissement de la fenêtre")
    parser.add_argument("--lives", type=int, default=3)
    parser.add_argument("--status", choices=["small", "big", "fire"],
                        default="small", help="état de départ de Mario")
    parser.add_argument("--no-enemies", action="store_true")
    parser.add_argument("--no-blocks", action="store_true")
    parser.add_argument("--no-powerups", action="store_true")
    parser.add_argument("--fps", type=int, default=C.FPS)
    parser.add_argument("--nes-timer", action="store_true",
                        help="chrono du jeu NES (1 unité = 24 images ≈ 0,4 s) "
                             "au lieu de vraies secondes")
    parser.add_argument("--nes-camera", action="store_true",
                        help="caméra du jeu NES (ne revient jamais en arrière)")
    parser.add_argument("--grid", choices=["v1", "v2", "v3"], default=None,
                        help="jouer à l'environnement discret de l'article")
    parser.add_argument("--segments", default=None,
                        help="ordre des segments A-F, ex. FEDCBA")
    parser.add_argument("--max-frames", type=int, default=0,
                        help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.grid:
        return play_grid(args)

    os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
    import pygame

    pygame.display.init()
    pygame.font.init()
    pygame.display.set_caption("Super Mario Bros. - World 1-1")
    scale = max(1, args.scale)
    screen = pygame.display.set_mode((C.SCREEN_W * scale, C.SCREEN_H * scale))
    clock = pygame.time.Clock()
    pygame.joystick.init()
    joy = pygame.joystick.Joystick(0) if pygame.joystick.get_count() else None

    cfg = GameConfig(
        segment_order=args.segments,
        timer_frames=C.GAME_TIMER_TICK if args.nes_timer else C.FPS,
        scroll_back=not args.nes_camera,
        lives=args.lives,
        enemies=not args.no_enemies,
        blocks=not args.no_blocks,
        powerups=not args.no_powerups,
        start_status={"small": 0, "big": 1, "fire": 2}[args.status],
    )
    game = Game(cfg)
    renderer = Renderer(game)
    surf = pygame.Surface((C.SCREEN_W, C.SCREEN_H))

    phase = "intermission"
    phase_timer = INTERMISSION_FRAMES
    paused = False
    last_mode = game.mode
    frame = None

    running = True
    n_frames = 0
    while running:
        n_frames += 1
        if args.max_frames and n_frames > args.max_frames:
            break
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key in (pygame.K_RETURN, pygame.K_p) \
                        and phase == "play":
                    paused = not paused
        keys = pygame.key.get_pressed()
        buttons = _buttons_from_keys(pygame, keys, joy)

        if phase == "intermission":
            frame = renderer.render_message(None, lives=game.lives)
            phase_timer -= 1
            if phase_timer <= 0:
                phase = "play"
        elif phase == "gameover":
            frame = renderer.render_message("GAME OVER")
            phase_timer -= 1
            if phase_timer <= 0:
                game = Game(cfg)
                renderer = Renderer(game)
                phase = "intermission"
                phase_timer = INTERMISSION_FRAMES
        else:
            if not paused:
                game.step(buttons)
                frame = renderer.render()
                if last_mode == "dying" and game.mode == "play":
                    phase = "intermission"
                    phase_timer = INTERMISSION_FRAMES
                elif game.mode == "gameover":
                    phase = "gameover"
                    phase_timer = GAMEOVER_FRAMES
                elif game.finished:
                    game.restart_level()
                    phase = "intermission"
                    phase_timer = INTERMISSION_FRAMES
                last_mode = game.mode
            elif frame is None:
                frame = renderer.render()

        pygame.surfarray.blit_array(surf, frame.swapaxes(0, 1))
        if scale > 1:
            pygame.transform.scale(surf, screen.get_size(), screen)
        else:
            screen.blit(surf, (0, 0))
        if paused and phase == "play":
            font = pygame.font.Font(None, 16 * scale)
            label = font.render("PAUSE", True, (255, 255, 255))
            screen.blit(label, label.get_rect(center=screen.get_rect().center))
        pygame.display.flip()
        clock.tick(args.fps)

    pygame.quit()
    return 0


def play_grid(args):
    """Joue à MarioGridEnv : droite = avancer, saut = X/Espace, rien sinon."""
    os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
    import pygame
    from .envs.grid_env import MarioGridEnv

    env = MarioGridEnv(level=args.grid, segment_order=args.segments)
    pygame.display.init()
    pygame.font.init()
    scale = max(1, args.scale)
    screen = pygame.display.set_mode((256 * scale, 14 * 16 * scale + 24 * scale))
    pygame.display.set_caption(f"Mario 1-1 - article ({args.grid})")
    clock = pygame.time.Clock()
    font = pygame.font.Font(None, 10 * scale)
    env.reset()
    ret, n = 0.0, 0
    msg = ""
    while True:
        n += 1
        if args.max_frames and n > args.max_frames:
            break
        quit_ = False
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (
                    event.type == pygame.KEYDOWN
                    and event.key == pygame.K_ESCAPE):
                quit_ = True
        if quit_:
            break
        keys = pygame.key.get_pressed()
        if keys[pygame.K_x] or keys[pygame.K_SPACE] or keys[pygame.K_UP] \
                or keys[pygame.K_k]:
            action = 2
        elif keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            action = 1
        else:
            action = 0
        if env.done:
            if keys[pygame.K_RETURN] or keys[pygame.K_r]:
                env.reset()
                ret, msg = 0.0, ""
        else:
            _, r, term, trunc, info = env.step(action)
            ret += r
            if term or trunc:
                msg = ("GAGNÉ !" if info["win"] else "PERDU") + \
                    "  (Entrée pour rejouer)"
        cam = min(max(env.col - 7, 0), env.W - 16)
        frame = env.render_level(window=(cam, cam + 16))
        surf = pygame.surfarray.make_surface(frame.swapaxes(0, 1))
        screen.fill((0, 0, 0))
        screen.blit(pygame.transform.scale(surf, (256 * scale,
                                                  14 * 16 * scale)), (0, 0))
        hud = f"pas {env.t}  col {env.col}  rangée {env.row}  " \
              f"phase {env.phase}  retour {ret:.1f}  {msg}"
        screen.blit(font.render(hud, True, (255, 255, 255)),
                    (4 * scale, 14 * 16 * scale + 6 * scale))
        pygame.display.flip()
        clock.tick(8)
    pygame.quit()
    return 0


if __name__ == "__main__":
    sys.exit(main())
