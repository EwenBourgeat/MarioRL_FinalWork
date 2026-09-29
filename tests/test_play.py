"""Tests de l'écran titre et de l'enchaînement des modes (sans fenêtre)."""

import os

import numpy as np
import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
pygame = pytest.importorskip("pygame")

from mario_env.game import Game, GameConfig  # noqa: E402
from mario_env.play import App, build_parser  # noqa: E402
from mario_env.renderer import Renderer  # noqa: E402


def make_app(script, max_frames=3000, extra=()):
    args = build_parser().parse_args(
        ["--fps", "0", "--scale", "1", "--max-frames", str(max_frames),
         *extra])
    pygame.display.init()
    screen = pygame.display.set_mode((256, 240))
    return App(args, pygame, screen, None, script)


def test_title_screen_renders():
    r = Renderer(Game(GameConfig(enemies=False)))
    frame = r.render_title(["VERSION NES", "VERSION SIMPLIFIEE V3",
                            "QUITTER"], 0, top_score=12300)
    assert frame.shape == (240, 256, 3) and frame.dtype == np.uint8
    # panneau du titre : brun NES au centre
    assert tuple(frame[100, 40]) == (0xC8, 0x4C, 0x0C)


def test_menu_quit_option():
    k = pygame
    app = make_app({5: [k.K_DOWN], 6: [k.K_DOWN], 7: [k.K_RETURN]})
    app.run_title()
    assert app.closed and app.frames < 20 and app.visited == []


def test_menu_nes_then_back_then_simplified_then_quit():
    k = pygame
    script = {
        5: [k.K_RETURN],            # VERSION NES
        300: [k.K_ESCAPE],          # retour à l'écran titre
        310: [k.K_TAB],             # SELECT : curseur sur la version simplifiée
        311: [k.K_LEFT],            # V3 -> V2
        312: [k.K_RETURN],
        600: [k.K_ESCAPE],
        610: [k.K_DOWN],            # curseur sur QUITTER
        611: [k.K_RETURN],
    }
    app = make_app(script)
    app.run_title()
    assert app.visited == ["nes", "grid_v2"]
    assert app.closed and app.frames < 700


class _HoldRight:
    """Remplace pygame.key.get_pressed : seule la flèche droite est tenue."""

    def __getitem__(self, key):
        return key == pygame.K_RIGHT


def test_game_over_returns_to_title(monkeypatch):
    monkeypatch.setattr(pygame.key, "get_pressed", lambda: _HoldRight())
    app = make_app({5: [pygame.K_RETURN]}, max_frames=1500,
                   extra=["--lives", "1"])
    app.run_title()                 # Mario fonce dans le 1er Goomba
    assert app.visited == ["nes", "gameover"]
    # de retour sur l'écran titre : le panneau brun est affiché
    assert tuple(app.last_frame[100, 40]) == (0xC8, 0x4C, 0x0C)
