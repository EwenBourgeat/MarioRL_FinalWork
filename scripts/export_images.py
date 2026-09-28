"""Exporte des images du niveau (pour le rapport / la présentation).

    python scripts/export_images.py [dossier]

Crée : carte complète du niveau NES, salle bonus, et les cartes des
versions v1/v2/v3 de l'environnement de l'article (style figure 1).
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame  # noqa: E402

from mario_env.envs.grid_env import MarioGridEnv  # noqa: E402
from mario_env.game import Game  # noqa: E402
from mario_env.renderer import Renderer  # noqa: E402


def save(arr, path, scale=1):
    surf = pygame.surfarray.make_surface(arr.swapaxes(0, 1))
    if scale != 1:
        surf = pygame.transform.scale(
            surf, (arr.shape[1] * scale, arr.shape[0] * scale))
    pygame.image.save(surf, path)
    print("écrit :", path)


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "images"
    os.makedirs(out, exist_ok=True)
    g = Game()
    r = Renderer(g)
    save(r.render_level_map(), os.path.join(out, "niveau_1-1.png"))
    save(r.render_level_map("bonus"), os.path.join(out, "salle_bonus.png"), 2)
    g.step(0)
    save(r.render(), os.path.join(out, "ecran_depart.png"), 3)
    for lvl in ("v1", "v2", "v3"):
        env = MarioGridEnv(level=lvl)
        save(env.render_level(style="flat", cell=8),
             os.path.join(out, f"article_{lvl}.png"))
        save(env.render_level(style="sprites"),
             os.path.join(out, f"article_{lvl}_sprites.png"))


if __name__ == "__main__":
    main()
