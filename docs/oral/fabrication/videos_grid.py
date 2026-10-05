"""Vidéos « course » pour l'oral : plusieurs parties jouées en même temps,
une ligne par partie, sur TOUT le niveau v3 (MarioGrid, environnement de
l'article).  On voit d'un coup d'œil jusqu'où va Mario à chaque étape.

    python docs/oral/fabrication/videos_grid.py progression   # Q-Learning, ép. 100 -> 6000
    python docs/oral/fabrication/videos_grid.py dqn           # DQN article vs notre DQN

Images : rendu du jeu (numpy) ; vidéo : ffmpeg (H.264, 30 images/s).
"""

import os
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from mario_env import MarioGridEnv, state_key           # noqa: E402
from mario_env.renderer import _glyph_mask               # noqa: E402

OUT = ROOT / "docs" / "oral" / "videos"
W_OUT = 1920
SKY = (90, 153, 237)            # bleu du diaporama (#5A99ED)
SHADOW = (46, 27, 91)           # ombre violette des titres (#2E1B5B)
YELLOW = (255, 199, 3)
RED = (230, 57, 70)
GREEN = (68, 183, 7)
WHITE = (255, 255, 255)


def draw_text(img, s, x, y, k=3, color=WHITE, shadow=SHADOW):
    """Police 8x8 du jeu, agrandie k fois (pixels nets), avec ombre."""
    for dx, dy, col in ((k // 2 + 1, k // 2 + 1, shadow), (0, 0, color)):
        if col is None:
            continue
        cx = x + dx
        for ch in s:
            if ch != " ":
                try:
                    m = _glyph_mask(ch)
                except KeyError:
                    cx += 8 * k
                    continue
                big = np.kron(m, np.ones((k, k), dtype=bool))
                h, w = big.shape
                region = img[y + dy:y + dy + h, cx:cx + w]
                region[big[:region.shape[0], :region.shape[1]]] = col
            cx += 8 * k


def text_width(s, k=3):
    return 8 * k * len(s)


class Encoder:
    def __init__(self, path, w, h, fps=30):
        self.w, self.h = w, h
        self.p = subprocess.Popen(
            ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo",
             "-pix_fmt", "rgb24", "-s", f"{w}x{h}", "-r", str(fps), "-i", "-",
             "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20",
             "-preset", "slow", "-movflags", "+faststart", str(path)],
            stdin=subprocess.PIPE)

    def add(self, frame, times=1):
        b = np.ascontiguousarray(frame, dtype=np.uint8).tobytes()
        for _ in range(times):
            self.p.stdin.write(b)

    def close(self):
        self.p.stdin.close()
        self.p.wait()


def race(rows, path, steps_per_s=15, fps=30, hold_s=3.0, k_text=3):
    """rows : liste de dict(label=..., env=..., policy=...).

    Toutes les parties avancent d'un pas à chaque image ; une partie finie
    reste figée avec son résultat (drapeau, mort, temps écoulé)."""
    n_cols = rows[0]["env"].W
    scale = W_OUT / (n_cols * 16)
    top = 3                         # 3 lignes de ciel vide coupées en haut
    lvl_h = int(round((14 - top) * 16 * scale))
    band = 8 * k_text + 12
    bar = 10
    gap = 18
    row_h = band + lvl_h + bar + gap
    H = row_h * len(rows) + 10
    H += H % 2
    enc = Encoder(path, W_OUT, H, fps)
    for r in rows:
        r["obs"], info = r["env"].reset()
        r["done"] = False
        r["max_col"] = info["col"]
        r["result"] = None
        r["steps"] = 0
    dup = max(1, fps // steps_per_s)

    def frame():
        img = np.empty((H, W_OUT, 3), dtype=np.uint8)
        img[:] = SKY
        for i, r in enumerate(rows):
            y0 = 10 + i * row_h
            draw_text(img, r["label"], 12, y0 + 4, k_text)
            if r["result"]:
                txt, col = r["result"]
                draw_text(img, txt, W_OUT - 12 - text_width(txt, k_text),
                          y0 + 4, k_text, color=col)
            lvl = r["env"].render_level(window=(0, n_cols))[top * 16:]
            lvl = np.asarray(Image.fromarray(lvl).resize(
                (W_OUT, lvl_h), Image.BOX)).copy()
            # repère au-dessus de Mario (il est petit à cette échelle)
            env = r["env"]
            mx = int((env.col + 0.5) * 16 * scale)
            my = int((env.row - top) * 16 * scale) - 6
            mcol = YELLOW
            if r["result"]:
                mcol = GREEN if r["result"][1] == GREEN else RED
            for i in range(9):
                y = my - 9 + i
                if 0 <= y < lvl_h:
                    lvl[y, max(0, mx - (8 - i)):mx + (8 - i) + 1] = mcol
            img[y0 + band:y0 + band + lvl_h] = lvl
            yb = y0 + band + lvl_h + 2
            img[yb:yb + bar] = (40, 60, 120)
            x = int(W_OUT * (r["max_col"] + 1) / n_cols)
            col = YELLOW
            if r["result"]:
                col = GREEN if r["result"][1] == GREEN else RED
            img[yb:yb + bar, :x] = col
        return img

    enc.add(frame(), int(fps * 1.0))
    while not all(r["done"] for r in rows):
        for r in rows:
            if r["done"]:
                continue
            obs, _, term, trunc, info = r["env"].step(
                r["policy"](state_key(r["obs"])))
            r["obs"] = obs
            r["steps"] += 1
            r["max_col"] = max(r["max_col"], info["col"])
            if term or trunc:
                r["done"] = True
                if info["win"]:
                    r["result"] = (f"DRAPEAU ! {r['steps']} PAS", GREEN)
                elif info["dead"]:
                    r["result"] = (f"PERDU COLONNE {r['max_col']}", RED)
                else:
                    r["result"] = (f"TEMPS ECOULE COLONNE {r['max_col']}",
                                   RED)
        enc.add(frame(), dup)
    enc.add(frame(), int(fps * hold_s))
    enc.close()
    return [(r["label"], r["result"][0]) for r in rows]


# ----------------------------------------------------------------------
# 1. Progression de Q-Learning (graine 42, v3) : épisodes 100 -> 6000
# ----------------------------------------------------------------------
def progression(seed=42, snaps=(100, 1000, 2200, 6000)):
    from agents.qlearning import QLearningAgent
    from agents.training import TrainConfig, greedy_test, play_episode

    cfg = TrainConfig(algo="qlearning", level="v3", episodes=max(snaps),
                      seed=seed)
    env = MarioGridEnv(level="v3", max_steps=cfg.max_steps, obs="paper")
    env.reset(seed=seed)
    agent = QLearningAgent(env.action_space.n, cfg.alpha, cfg.gamma, seed)
    eps = cfg.eps_start
    saved = {}
    for ep in range(1, cfg.episodes + 1):
        play_episode(env, lambda s: agent.act(s, eps), agent.update)
        eps = max(cfg.eps_min, eps * cfg.eps_decay)
        if ep % cfg.eval_every == 0:
            t = greedy_test(env, agent, seed)       # comme dans train()
            if ep in snaps:
                print(f"épisode {ep}: test glouton win={t['win']} "
                      f"dead={t['dead']} col={t['max_col']} pas={t['steps']}")
        if ep in snaps:
            saved[ep] = agent.snapshot()
    rows = []
    for ep in snaps:
        a = QLearningAgent(env.action_space.n, cfg.alpha, cfg.gamma, seed)
        a.restore(saved[ep])
        rows.append(dict(label=f"EPISODE {ep}",
                         env=MarioGridEnv(level="v3", max_steps=1000,
                                          obs="paper"),
                         policy=a.greedy_policy(seed)))
    return race(rows, OUT / "01_qlearning_progression.mp4")


# ----------------------------------------------------------------------
# 2. DQN de l'article vs notre DQN (même graine)
# ----------------------------------------------------------------------
def dqn(seed=44):
    from agents.registry import load_agent
    rows = []
    for name, lab in ((f"dqn_v3_s{seed}_6000ep", "DQN DE L ARTICLE"),
                      (f"dqn_v3_s{seed}_6000ep_e4", "NOTRE DQN")):
        path = ROOT / "models" / name
        import json
        meta = json.load(open(path / "meta.json", encoding="utf-8"))
        meta["path"] = str(path)
        agent = load_agent(meta)
        rows.append(dict(label=f"{lab} - GRAINE {seed}",
                         env=MarioGridEnv(level="v3", max_steps=1000,
                                          obs=meta.get("obs", "paper")),
                         policy=agent.greedy_policy(seed),
                         expected=meta["greedy"]))
    res = race(rows, OUT / "02_dqn_article_vs_notre.mp4")
    for r in rows:
        g = r["expected"]
        print("attendu (Mac) :", r["label"], "win", g["win"], "dead",
              g["dead"], "col", g["max_col"], "pas", g["steps"])
    return res


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    what = sys.argv[1] if len(sys.argv) > 1 else "progression"
    print({"progression": progression, "dqn": dqn}[what]())
