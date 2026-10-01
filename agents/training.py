"""Boucle d'entraînement et test glouton, communes à tous les agents tabulaires.

Vocabulaire :
* un *pas* = une action de Mario (un appel à ``env.step``) ;
* un *épisode* = une partie, du départ jusqu'au drapeau, à la mort ou à la
  limite de 1000 pas ;
* epsilon (ε) = probabilité de jouer au hasard.  Il part de 1 (100 % hasard)
  et est multiplié par 0.999 après chaque épisode, sans descendre sous 0.01.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, asdict
from typing import Optional

from mario_env import MarioGridEnv, state_key

from .qlearning import QLearningAgent

# Ce qu'on note à la fin de chaque épisode (une colonne de history.csv chacun)
HISTORY_FIELDS = ("return", "win", "dead", "timeout", "steps", "max_col",
                  "epsilon", "bricks", "qblocks", "enemies", "jumps",
                  "n_states")


@dataclass
class TrainConfig:
    """Tous les réglages d'un entraînement (valeurs par défaut = article)."""
    level: str = "v1"
    episodes: int = 3000
    seed: int = 42
    alpha: float = 0.1
    gamma: float = 0.99
    eps_start: float = 1.0
    eps_decay: float = 0.999
    eps_min: float = 0.01
    max_steps: int = 1000
    eval_every: int = 100          # un test glouton tous les N épisodes
    segments: Optional[str] = None  # ordre des segments A-F (None = normal)
    log_every: int = 500

    def as_dict(self):
        return asdict(self)


def make_env(cfg):
    return MarioGridEnv(level=cfg.level, max_steps=cfg.max_steps,
                        segment_order=cfg.segments)


def play_episode(env, choose, learn=None):
    """Joue un épisode complet et renvoie son résumé.

    ``choose(état) -> action`` décide des actions ; ``learn(s, a, r, s2,
    terminated)``, s'il est donné, est appelé après chaque pas.
    """
    obs, info = env.reset()
    s = state_key(obs)
    total = 0.0
    max_col = info["col"]
    while True:
        a = choose(s)
        obs, r, terminated, truncated, info = env.step(a)
        s2 = state_key(obs)
        if learn is not None:
            learn(s, a, r, s2, terminated)
        total += r
        s = s2
        if info["col"] > max_col:
            max_col = info["col"]
        if terminated or truncated:
            break
    st = info["stats"]
    return {"return": total, "win": int(info["win"]), "dead": int(info["dead"]),
            "timeout": int(truncated), "steps": info["t"], "max_col": max_col,
            "bricks": st["bricks_broken"], "qblocks": st["qblocks_hit"],
            "enemies": st["enemies_killed"], "jumps": st["jumps"]}


def greedy_test(env, agent, seed=0):
    """Test glouton : une partie avec epsilon = 0, sans apprendre.

    L'environnement est déterministe, donc une seule partie suffit : elle
    montre exactement ce que l'agent a retenu (sans le bruit de l'exploration).
    """
    return play_episode(env, agent.greedy_policy(seed))


def train_qlearning(cfg: TrainConfig, log=print):
    """Entraîne un agent Q-Learning et renvoie (agent, historique, tests)."""
    env = make_env(cfg)
    env.reset(seed=cfg.seed)
    agent = QLearningAgent(env.action_space.n, cfg.alpha, cfg.gamma, cfg.seed)
    history = {k: [] for k in HISTORY_FIELDS}
    tests = []
    eps = cfg.eps_start
    t0 = time.perf_counter()

    for ep in range(1, cfg.episodes + 1):
        # --- une partie d'entraînement : epsilon-greedy + mise à jour ---
        res = play_episode(env, lambda s: agent.act(s, eps), agent.update)
        res["epsilon"] = eps
        res["n_states"] = len(agent.q)
        for k in HISTORY_FIELDS:
            history[k].append(res[k])

        # --- moins d'exploration pour la partie suivante ---
        eps = max(cfg.eps_min, eps * cfg.eps_decay)

        if cfg.eval_every and ep % cfg.eval_every == 0:
            tests.append({"episode": ep, **greedy_test(env, agent, cfg.seed)})
        if log and cfg.log_every and ep % cfg.log_every == 0:
            n = min(100, ep)
            wins = sum(history["win"][-n:]) / n
            ret = sum(history["return"][-n:]) / n
            log(f"[graine {cfg.seed}] épisode {ep:>6}/{cfg.episodes} | "
                f"ε={history['epsilon'][-1]:.3f} | victoires (100 dern.) "
                f"{wins:6.1%} | retour moyen {ret:7.1f} | "
                f"états vus {len(agent.q):>7} | "
                f"{time.perf_counter() - t0:6.1f} s")

    final = greedy_test(env, agent, cfg.seed)
    seconds = time.perf_counter() - t0
    return agent, history, tests, final, seconds


def run_seed(cfg_dict):
    """Version « processus séparé » de train_qlearning (une graine).

    Utilisée par train_qlearning.py pour lancer plusieurs graines en même
    temps, une par cœur du processeur.
    """
    cfg = TrainConfig(**cfg_dict)
    agent, history, tests, final, seconds = train_qlearning(
        cfg, log=lambda msg: print(msg, flush=True))
    return cfg_dict, agent.q, history, tests, final, seconds
