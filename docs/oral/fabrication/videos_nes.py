"""Vidéos du VRAI jeu NES pour l'oral : un modèle PPO joue seul (test
glouton, sans hasard), avec les graphismes du jeu, à la vraie vitesse
(60 images/s), drapeau et château compris.

    python docs/oral/fabrication/videos_nes.py ppo_nes_v3_s42_3m 03_ppo_nes_v3.mp4
    python docs/oral/fabrication/videos_nes.py ppo_nes_full_a_s43_3m_b 04_ppo_route_a.mp4
"""

import json
import sys
from collections import deque
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from videos_grid import Encoder                          # noqa: E402

OUT = ROOT / "docs" / "oral" / "videos"
SCALE = 3                       # 256 x 240 -> 768 x 720, pixels nets


def nes_video(model, out_name, fps=60, end_limit=330):
    from agents.ppo import make_nes_env
    from agents.registry import load_agent
    from mario_env.envs.common import state_key

    path = ROOT / "models" / model
    meta = json.load(open(path / "meta.json", encoding="utf-8"))
    meta["path"] = str(path)
    agent = load_agent(meta)
    env = make_nes_env(level=meta["level"], obs=meta.get("obs", "vector"),
                       actions=meta.get("actions", "right_only"),
                       max_steps=meta.get("max_steps", 1000),
                       segments=meta.get("segments"),
                       reward=meta.get("reward", "paper"))
    nes = env.unwrapped
    frames = deque()
    nes.frame_hook = lambda: frames.append(nes.renderer.render().copy())
    policy = agent.greedy_policy(meta.get("seed", 0))
    obs, _ = env.reset()
    enc = Encoder(OUT / out_name, 256 * SCALE, 240 * SCALE, fps)
    k = np.ones((SCALE, SCALE, 1), dtype=np.uint8)

    def emit(img, times=1):
        enc.add(np.kron(img, k), times)

    emit(nes.renderer.render(), int(fps * 0.5))
    steps, info, done = 0, {}, False
    while not done:
        obs, r, term, trunc, info = env.step(policy(state_key(obs)))
        steps += 1
        while frames:
            emit(frames.popleft())
        done = term or trunc
    # animation de fin : drapeau puis château (ou chute de Mario)
    game, n = nes.game, 0
    while n < end_limit and ((game.level_complete and not game.finished)
                             or game.mode == "dying"):
        game.step(0)
        n += 1
        emit(nes.renderer.render())
    emit(nes.renderer.render(), int(fps * 1.0))
    enc.close()
    g = meta["greedy"]
    print(model, "->", out_name, "| ici : win", info.get("win"), "pas", steps,
          "pièces", info.get("stats", {}).get("coins"),
          "| attendu (Mac) : win", g["win"], "pas", g["steps"],
          "pièces", g.get("coins"))


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    nes_video(sys.argv[1], sys.argv[2])
