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
    app = make_app({5: [k.K_DOWN], 6: [k.K_DOWN], 7: [k.K_DOWN],
                    8: [k.K_RETURN]})
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
        610: [k.K_DOWN],            # MODELES
        611: [k.K_DOWN],            # QUITTER
        612: [k.K_RETURN],
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


def test_fullscreen_toggle_keeps_aspect():
    k = pygame
    app = make_app({3: [k.K_F11], 6: [k.K_F11], 8: [k.K_ESCAPE]})
    app.run_title()
    assert app.closed and app.fullscreen is False
    app.toggle_fullscreen()
    frame = app.title_renderer.render_title(app.menu_labels(), 0)
    app._present(frame, fps=0)
    app.toggle_fullscreen()
    assert app.screen.get_size() == (256, 240)


def _train_tiny_model(root):
    from agents.metrics import article_metrics
    from agents.registry import save_model
    from agents.training import TrainConfig, train_qlearning

    cfg = TrainConfig(level="v1", episodes=200, seed=5, eval_every=0,
                      log_every=0)
    agent, history, tests, final, _ = train_qlearning(cfg, log=None)
    meta = dict(cfg.as_dict(), algo="qlearning",
                metrics=article_metrics(history), greedy=final)
    return save_model(agent, meta, history, tests, root=root), final


def test_models_menu_watch_agent(tmp_path, monkeypatch):
    k = pygame
    path, final = _train_tiny_model(tmp_path)
    monkeypatch.setenv("MARIO_MODELS_DIR", str(tmp_path))
    script = {
        5: [k.K_UP, k.K_UP],        # VERSION NES -> QUITTER -> MODELES
        6: [k.K_RETURN],            # liste des algorithmes
        8: [k.K_RETURN],            # Q-LEARNING : liste de ses modèles
        10: [k.K_RETURN],           # le premier modèle joue
        12: [k.K_RETURN],           # passer l'écran WORLD 1-1
        14: [k.K_RIGHT, k.K_RIGHT, k.K_RIGHT],     # vitesse x8
    }
    app = make_app(script, max_frames=1400)
    app.run_title()
    expected = ("THANK YOU MARIO!" if final["win"] else
                "GAME OVER" if final["dead"] else "TIME UP")
    assert app.visited[:4] == ["models", "models_Q-LEARNING",
                               "watch_" + path.name, expected]
    # après la fin de partie : retour à la liste des modèles (panneau brun)
    assert tuple(app.last_frame[120, 30]) == (0xC8, 0x4C, 0x0C)


def test_models_menu_watch_ppo_on_the_real_game(tmp_path, monkeypatch):
    pytest.importorskip("stable_baselines3")
    from agents.metrics import article_metrics
    from agents.registry import save_model
    from agents.training import TrainConfig, train

    k = pygame
    cfg = TrainConfig(algo="ppo", env="nes", obs="vector",
                      actions="right_only", level="v3", steps=1024,
                      eval_steps=0, log_every=0, lr=3e-4, seed=42)
    agent, history, tests, final, _ = train(cfg, log=None)
    meta = dict(cfg.as_dict(), env="MarioNES-v0",
                episodes=len(history["win"]),
                metrics=article_metrics(history), greedy=final)
    path = save_model(agent, meta, history, tests, root=tmp_path)
    monkeypatch.setenv("MARIO_MODELS_DIR", str(tmp_path))
    script = {
        5: [k.K_UP, k.K_UP],        # MODELES
        6: [k.K_RETURN],
        8: [k.K_DOWN, k.K_DOWN, k.K_DOWN, k.K_DOWN],   # PPO
        9: [k.K_RETURN],
        11: [k.K_RETURN],           # le modèle joue sur le vrai jeu
        13: [k.K_RETURN],           # passer l'écran WORLD 1-1
        15: [k.K_RIGHT, k.K_RIGHT, k.K_RIGHT],     # vitesse x8
    }
    app = make_app(script, max_frames=2500)
    app.run_title()
    expected = ("THANK YOU MARIO!" if final["win"] else
                "GAME OVER" if final["dead"] else "TIME UP")
    assert app.visited[:4] == ["models", "models_PPO",
                               "watch_" + path.name, expected]
    assert tuple(app.last_frame[120, 30]) == (0xC8, 0x4C, 0x0C)


def test_models_menu_algorithms_without_models(tmp_path, monkeypatch):
    k = pygame
    monkeypatch.setenv("MARIO_MODELS_DIR", str(tmp_path / "vide"))
    script = {5: [k.K_UP, k.K_UP], 6: [k.K_RETURN],
              8: [k.K_DOWN], 9: [k.K_RETURN],      # SARSA : rien à ouvrir
              11: [k.K_ESCAPE],                    # retour à l'écran titre
              13: [k.K_ESCAPE]}
    app = make_app(script)
    app.run_title()
    assert app.visited == ["models"] and app.closed
