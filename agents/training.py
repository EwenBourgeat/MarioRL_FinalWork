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
from .sarsa import SarsaAgent
from .montecarlo import MonteCarloAgent

# Algorithmes disponibles : nom -> classe de l'agent
AGENT_CLASSES = {"qlearning": QLearningAgent, "sarsa": SarsaAgent,
                 "montecarlo": MonteCarloAgent}
ALGO_NAMES = {"qlearning": "Q-Learning", "sarsa": "SARSA",
              "montecarlo": "Monte Carlo", "dqn": "DQN"}


def agent_class(algo):
    """Classe de l'agent ; DQN n'est importé que si on s'en sert (PyTorch)."""
    if algo == "dqn":
        from .dqn import DQNAgent
        return DQNAgent
    if algo not in AGENT_CLASSES:
        raise ValueError(f"algorithme inconnu : {algo!r}")
    return AGENT_CLASSES[algo]


def table_size(agent):
    """États dans la Q-table (tableaux) ou pas en mémoire de replay (DQN)."""
    return len(agent.q) if hasattr(agent, "q") else agent.memory.size

# Ce qu'on note à la fin de chaque épisode (une colonne de history.csv chacun)
HISTORY_FIELDS = ("return", "win", "dead", "timeout", "steps", "max_col",
                  "epsilon", "bricks", "qblocks", "enemies", "jumps",
                  "n_states")


@dataclass
class TrainConfig:
    """Tous les réglages d'un entraînement (valeurs par défaut = article)."""
    algo: str = "qlearning"        # "qlearning", "sarsa", "montecarlo", "dqn"
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
    obs: str = "paper"             # "paper" (article) ou "full" (vue complète)
    # --- notre DQN, étape 2 (désactivé par défaut = DQN de l'article) ---
    double: bool = False           # 2a : Double DQN
    n_step: int = 1                # 2b : récompenses sur n pas
    grad_clip: Optional[float] = None  # 2c : taille max d'une correction
    tau: Optional[float] = None    # 2d : cible douce (ex. 0.005)
    keep_best: bool = False        # 2e : garder la meilleure version
    cnn: bool = False              # 3 : réseau à loupes (vue complète)
    device: str = "auto"           # auto / cpu / cuda / mps
    threads: int = 1               # cœurs du processeur par graine
    variant: Optional[str] = None  # étiquette de l'expérience (ex. "E1")
    log_every: int = 500

    def as_dict(self):
        return asdict(self)


def make_env(cfg):
    return MarioGridEnv(level=cfg.level, max_steps=cfg.max_steps,
                        segment_order=cfg.segments, obs=cfg.obs)


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
    return _summary(info, total, max_col, truncated)


def play_sarsa_episode(env, agent, epsilon):
    """Un épisode d'entraînement SARSA.

    Ordre propre à SARSA : on choisit l'action suivante a2 *avant* la mise à
    jour (elle sert dans la cible), puis on joue exactement a2 au pas suivant.
    """
    obs, info = env.reset()
    s = state_key(obs)
    a = agent.act(s, epsilon)
    total = 0.0
    max_col = info["col"]
    while True:
        obs, r, terminated, truncated, info = env.step(a)
        s2 = state_key(obs)
        a2 = None if terminated else agent.act(s2, epsilon)
        agent.update(s, a, r, s2, a2, terminated)
        total += r
        if info["col"] > max_col:
            max_col = info["col"]
        if terminated or truncated:
            break
        s, a = s2, a2
    return _summary(info, total, max_col, truncated)


def play_montecarlo_episode(env, agent, epsilon):
    """Un épisode Monte Carlo : on joue toute la partie en notant
    (situation, bouton, récompense), puis on apprend une seule fois à la fin."""
    obs, info = env.reset()
    s = state_key(obs)
    trajectory = []
    total = 0.0
    max_col = info["col"]
    while True:
        a = agent.act(s, epsilon)
        obs, r, terminated, truncated, info = env.step(a)
        trajectory.append((s, a, r))
        total += r
        if info["col"] > max_col:
            max_col = info["col"]
        if terminated or truncated:
            break
        s = state_key(obs)
    agent.update_episode(trajectory)
    return _summary(info, total, max_col, truncated)


def play_dqn_episode(env, agent, epsilon):
    """Un épisode DQN : chaque pas va dans la mémoire de replay, et le réseau
    apprend sur un paquet de souvenirs tous les 4 pas (voir dqn.py)."""
    obs, info = env.reset()
    total = 0.0
    max_col = info["col"]
    while True:
        a = agent.act(obs, epsilon)
        obs2, r, terminated, truncated, info = env.step(a)
        agent.observe(obs, a, r, obs2, terminated, terminated or truncated)
        total += r
        if info["col"] > max_col:
            max_col = info["col"]
        if terminated or truncated:
            break
        obs = obs2
    return _summary(info, total, max_col, truncated)


def _summary(info, total, max_col, truncated):
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


def robustness_test(env, agent, seed=0, episodes=50, epsilon=0.02):
    """Test de robustesse : 50 parties avec 2 % de hasard, sans apprendre.

    Le test glouton n'est qu'UNE partie parfaite.  Ici, quelques boutons
    tirés au hasard perturbent Mario : un modèle solide doit quand même
    gagner presque toujours.
    """
    import random
    rng = random.Random(seed + 1000)

    def choose(s):
        if rng.random() < epsilon:
            return rng.randrange(agent.n_actions)
        return agent.best_action(s, rng)

    res = [play_episode(env, choose) for _ in range(episodes)]
    n = len(res)
    return {"episodes": n, "epsilon": epsilon,
            "win_rate": sum(r["win"] for r in res) / n,
            "avg_return": sum(r["return"] for r in res) / n,
            "death_rate": sum(r["dead"] for r in res) / n}


def train(cfg: TrainConfig, log=print):
    """Entraîne un agent (Q-Learning, SARSA ou Monte Carlo selon ``cfg.algo``).

    Renvoie (agent, historique, tests gloutons, test final, durée en s).
    """
    cls = agent_class(cfg.algo)
    env = make_env(cfg)
    env.reset(seed=cfg.seed)
    if cfg.algo == "dqn":
        import torch
        torch.set_num_threads(cfg.threads)   # cœurs du processeur
        agent = cls(env.observation_space.nvec - 1, env.action_space.n,
                    cfg.gamma, cfg.seed, double=cfg.double,
                    n_step=cfg.n_step, grad_clip=cfg.grad_clip, tau=cfg.tau,
                    cnn=cfg.cnn, device=cfg.device)
        if log:
            log(f"[graine {cfg.seed}] calcul sur : {agent.device}")
    else:
        agent = cls(env.action_space.n, cfg.alpha, cfg.gamma, cfg.seed)
    history = {k: [] for k in HISTORY_FIELDS}
    tests = []
    best = None                         # (score, épisode, copie)
    eps = cfg.eps_start
    t0 = time.perf_counter()

    for ep in range(1, cfg.episodes + 1):
        # --- une partie d'entraînement : epsilon-greedy + mise à jour ---
        if cfg.algo == "sarsa":
            res = play_sarsa_episode(env, agent, eps)
        elif cfg.algo == "montecarlo":
            res = play_montecarlo_episode(env, agent, eps)
        elif cfg.algo == "dqn":
            res = play_dqn_episode(env, agent, eps)
        else:
            res = play_episode(env, lambda s: agent.act(s, eps), agent.update)
        res["epsilon"] = eps
        res["n_states"] = table_size(agent)
        for k in HISTORY_FIELDS:
            history[k].append(res[k])

        # --- moins d'exploration pour la partie suivante ---
        eps = max(cfg.eps_min, eps * cfg.eps_decay)

        if cfg.eval_every and ep % cfg.eval_every == 0:
            test = greedy_test(env, agent, cfg.seed)
            tests.append({"episode": ep, **test})
            if cfg.keep_best and test["win"]:
                # 2e. version candidate : mini-test de robustesse (30
                # parties) sur d'AUTRES parties que le test final (graine
                # différente).  À score égal, on garde la plus RÉCENTE
                # (>=) : elle a appris plus longtemps.
                mini = robustness_test(env, agent, cfg.seed + 500,
                                       episodes=30)
                score = (mini["win_rate"],)
                if best is None or score >= best[0]:
                    best = (score, ep, agent.snapshot())
        if log and cfg.log_every and ep % cfg.log_every == 0:
            n = min(100, ep)
            wins = sum(history["win"][-n:]) / n
            ret = sum(history["return"][-n:]) / n
            log(f"[graine {cfg.seed}] épisode {ep:>6}/{cfg.episodes} | "
                f"ε={history['epsilon'][-1]:.3f} | victoires (100 dern.) "
                f"{wins:6.1%} | retour moyen {ret:7.1f} | "
                f"{'mémoire' if cfg.algo == 'dqn' else 'états vus'} "
                f"{table_size(agent):>7} | "
                f"{time.perf_counter() - t0:6.1f} s")

    if cfg.keep_best and best is not None:
        agent.restore(best[2])           # on recharge la meilleure version
        agent.best_episode = best[1]
        if log:
            log(f"[graine {cfg.seed}] meilleure version gardée : épisode "
                f"{best[1]} (mini-test {best[0][0]:.0%})")
    final = greedy_test(env, agent, cfg.seed)
    seconds = time.perf_counter() - t0
    return agent, history, tests, final, seconds


def train_qlearning(cfg: TrainConfig, log=print):
    """Ancien nom de ``train`` (Q-Learning par défaut)."""
    return train(cfg, log)


def run_seed(cfg_dict):
    """Version « processus séparé » de train (une graine).

    Utilisée par train.py pour lancer plusieurs graines en même temps, une
    par cœur du processeur.
    """
    cfg = TrainConfig(**cfg_dict)
    agent, history, tests, final, seconds = train(
        cfg, log=lambda msg: print(msg, flush=True))
    if hasattr(agent, "detach_for_transfer"):
        # DQN : réseau ramené sur le processeur avant de quitter ce
        # processus (sinon, depuis la carte graphique, on perd les poids)
        agent.detach_for_transfer()
    return cfg_dict, agent, history, tests, final, seconds
