"""PPO (Proximal Policy Optimization) sur le vrai jeu NES (MarioNES-v0).

PPO vient de la bibliothèque Stable-Baselines3 (pip install -r
requirements-dqn.txt).  Différences avec Q-Learning / DQN :

* au lieu de noter chaque bouton, PPO apprend directement une *politique* :
  la probabilité d'appuyer sur chaque bouton dans chaque situation (réseau
  « acteur »), plus un second réseau qui estime si la situation est bonne
  (réseau « critique ») ;
* il explore en tirant ses boutons au sort selon ces probabilités (pas
  d'epsilon) ;
* il joue un paquet de pas (ici 2 parties en parallèle x 512 pas), apprend
  dessus, puis les jette : pas de mémoire de replay (changer ``n_envs``
  change la taille du paquet : 2 est la valeur vérifiée) ;
* chaque mise à jour est bornée (« proximal ») : la politique ne peut pas
  trop changer d'un coup, ce qui rend l'apprentissage stable.

Réglages = ceux de notre essai dans le cloud (gagne dès ~1,25 million de
pas, vue « vector », 5 boutons, niveau v3).
"""

from __future__ import annotations

import copy
import io
import random
import time
from pathlib import Path

import gymnasium as gym
import numpy as np

from .training import (HISTORY_FIELDS, NES_FIELDS, _summary, greedy_test,
                       make_env, robustness_test)

FILENAME = "ppo.zip"

# Réglages PPO (Stable-Baselines3) : 512 pas par partie en parallèle avant
# chaque apprentissage, paquets de 256 pas, 10 passages sur les données,
# bornage à 20 % (clip), lissage des avantages (GAE) 0,95.  ent_coef = bonus
# de curiosité (entropie) : récompense le fait de garder des choix variés,
# réglable avec --ent-coef (0 par défaut)
PPO_SETTINGS = dict(n_steps=512, batch_size=256, n_epochs=10,
                    gae_lambda=0.95, clip_range=0.2, ent_coef=0.0)


# ---------------------------------------------------------------------------
# Environnement : le vrai jeu, avec les mêmes infos que MarioGrid
# ---------------------------------------------------------------------------
class AgentInfo(gym.Wrapper):
    """Ajoute à ``info`` les clés utilisées par nos boucles de test
    (``win`` = drapeau atteint, ``t`` = pas joués)."""

    def reset(self, **kwargs):
        obs, info = self.env.reset(**kwargs)
        return obs, self._fix(info)

    def step(self, action):
        obs, r, terminated, truncated, info = self.env.step(action)
        return obs, r, terminated, truncated, self._fix(info)

    @staticmethod
    def _fix(info):
        info["win"] = bool(info["flag_get"])
        info["t"] = info["steps"]
        return info


def make_nes_env(level="v3", obs="vector", actions="right_only",
                 max_steps=1000, segments=None, reward="paper", **kwargs):
    """MarioNES-v0 prêt pour nos agents.

    * ``obs="vector"`` : 62 nombres (position, vitesses, 5 ennemis les plus
      proches, relief des 16 colonnes devant Mario) ;
    * ``actions="right_only"`` : rien, droite, droite+saut, droite+course,
      droite+saut+course (avec les 3 boutons de l'article, Mario ne passe
      pas les grands tuyaux du vrai jeu) ;
    * ``max_steps=1000`` : sinon une partie coincée dure jusqu'à la fin du
      chrono (2400 pas) ;
    * route A : ``level="full"``, ``obs="vector_plus"``,
      ``actions="right_down"``, ``reward="route_a"``.
    """
    from mario_env.envs.nes_env import MarioNESEnv
    return AgentInfo(MarioNESEnv(level=level, obs_type=obs, actions=actions,
                                 max_episode_steps=max_steps,
                                 segment_order=segments, reward=reward,
                                 **kwargs))


class EpisodeRecorder(gym.Wrapper):
    """Note le résumé de chaque partie terminée dans ``sink`` (une liste)."""

    def __init__(self, env, sink):
        super().__init__(env)
        self.sink = sink
        self.total = 0.0
        self.max_col = 0

    def reset(self, **kwargs):
        obs, info = self.env.reset(**kwargs)
        self.total = 0.0
        self.max_col = info["col"]
        return obs, info

    def step(self, action):
        obs, r, terminated, truncated, info = self.env.step(action)
        self.total += r
        self.max_col = max(self.max_col, info["col"])
        if terminated or truncated:
            self.sink.append(_summary(info, self.total, self.max_col,
                                      truncated))
        return obs, r, terminated, truncated, info


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------
class PPOAgent:
    """Enveloppe d'un modèle PPO de Stable-Baselines3 avec l'interface de
    nos agents (best_action, greedy_policy, save / load...)."""

    FILENAME = FILENAME

    def __init__(self, model=None, n_actions=5, seed=0, blob=None):
        self.model = model
        self._blob = blob               # modèle sérialisé (entre processus)
        self.n_actions = int(n_actions)
        self.rng = random.Random(seed)

    def _ppo(self):
        if self.model is None:
            from stable_baselines3 import PPO
            self.model = PPO.load(io.BytesIO(self._blob), device="cpu")
            self._blob = None
        return self.model

    def best_action(self, state, rng=None):
        """Bouton le plus probable pour la politique (``state`` = tuple ou
        tableau de la vue « vector »)."""
        obs = np.asarray(state, dtype=np.float32)
        action, _ = self._ppo().predict(obs, deterministic=True)
        return int(action)

    def act(self, state, epsilon):
        if self.rng.random() < epsilon:
            return self.rng.randrange(self.n_actions)
        return self.best_action(state)

    def greedy_policy(self, seed=0):
        return lambda state: self.best_action(state)

    # --- meilleure version (comme l'étape 4 de notre DQN) ---
    def snapshot(self):
        return copy.deepcopy(self._ppo().policy.state_dict())

    def restore(self, snap):
        self._ppo().policy.load_state_dict(snap)

    def detach_for_transfer(self):
        """Sérialise le modèle pour le renvoyer au processus principal (le
        modèle contient les environnements, qui ne voyagent pas)."""
        buf = io.BytesIO()
        self._ppo().save(buf)
        self._blob = buf.getvalue()
        self.model = None

    def save(self, path):
        if self.model is None and self._blob is not None:
            Path(path).write_bytes(self._blob)
        else:
            self.model.save(path)

    @classmethod
    def load(cls, path, seed=0):
        from stable_baselines3 import PPO
        model = PPO.load(path, device="cpu")
        return cls(model, model.action_space.n, seed)


# ---------------------------------------------------------------------------
# Entraînement
# ---------------------------------------------------------------------------
def train_ppo(cfg, log=print):
    """Entraîne PPO pendant ``cfg.steps`` pas.

    Renvoie (agent, historique, tests gloutons, test final, durée en s),
    comme ``training.train``.  Un test glouton (bouton le plus probable,
    sans hasard) a lieu tous les ``cfg.eval_steps`` pas ; avec
    ``cfg.keep_best``, on garde la meilleure version comme pour notre DQN.
    """
    import torch
    from stable_baselines3 import PPO
    from stable_baselines3.common.callbacks import BaseCallback
    from stable_baselines3.common.vec_env import DummyVecEnv

    torch.set_num_threads(cfg.threads)
    episodes = []                       # résumés des parties terminées

    def factory():
        return EpisodeRecorder(make_env(cfg), episodes)

    venv = DummyVecEnv([factory for _ in range(cfg.n_envs)])
    settings = dict(PPO_SETTINGS, ent_coef=cfg.ent_coef)
    model = PPO("MlpPolicy", venv, learning_rate=cfg.lr, gamma=cfg.gamma,
                seed=cfg.seed, device="cpu", verbose=0, **settings)
    agent = PPOAgent(model, venv.action_space.n, cfg.seed)
    test_env = make_env(cfg)
    tests = []
    best = None                         # (score, partie, pas, copie)
    t0 = time.perf_counter()

    class Progress(BaseCallback):
        # un retour tous les N pas (cfg.log_steps) ou tous les N épisodes
        next_log = cfg.log_steps or cfg.log_every
        next_eval = cfg.eval_steps

        def _on_step(self):
            n = len(episodes)
            every = cfg.log_steps or cfg.log_every
            done = self.num_timesteps if cfg.log_steps else n
            if log and every and done >= self.next_log:
                self.next_log += every
                self._log(n)
            if cfg.eval_steps and self.num_timesteps >= self.next_eval:
                self.next_eval += cfg.eval_steps
                self._evaluate(n)
            return True

        def _log(self, n):
            last = episodes[-100:] or [{"win": 0, "return": 0.0, "coins": 0,
                                        "bonus": 0, "mushrooms": 0,
                                        "flowers": 0}]
            sec = time.perf_counter() - t0
            extra = ""
            if cfg.level.startswith("full"):    # route A
                k = len(last)
                extra = (f" | pièces {sum(e['coins'] for e in last) / k:4.1f}"
                         f" | salle bonus "
                         f"{sum(e['bonus'] > 0 for e in last) / k:4.0%}"
                         f" | champi. "
                         f"{sum(e['mushrooms'] > 0 for e in last) / k:4.0%}"
                         f" | fleur "
                         f"{sum(e['flowers'] > 0 for e in last) / k:4.0%}")
            log(f"[graine {cfg.seed}] pas {self.num_timesteps:>9}/{cfg.steps} "
                f"| épisode {n:>6} | victoires (100 dern.) "
                f"{sum(e['win'] for e in last) / len(last):6.1%} | retour "
                f"moyen {sum(e['return'] for e in last) / len(last):7.1f}"
                f"{extra} | {sec:6.1f} s "
                f"({self.num_timesteps / sec:5.0f} pas/s)")

        def _evaluate(self, n):
            nonlocal best
            test = greedy_test(test_env, agent, cfg.seed)
            tests.append({"episode": n, "train_steps": self.num_timesteps,
                          **test})
            if cfg.keep_best and test["win"]:
                mini = robustness_test(test_env, agent, cfg.seed + 500,
                                       episodes=30)
                score = (mini["win_rate"],)
                if best is None or score >= best[0]:
                    best = (score, n, self.num_timesteps, agent.snapshot())

    model.learn(cfg.steps, callback=Progress())

    if cfg.keep_best and best is not None:
        agent.restore(best[3])
        agent.best_episode = best[1]
        agent.best_steps = best[2]
        if log:
            log(f"[graine {cfg.seed}] meilleure version gardée : épisode "
                f"{best[1]}, {best[2]} pas (mini-test {best[0][0]:.0%})")
    final = greedy_test(test_env, agent, cfg.seed)
    seconds = time.perf_counter() - t0

    history = {k: [] for k in HISTORY_FIELDS + NES_FIELDS}
    total = 0
    for e in episodes:
        total += e["steps"]
        e = dict(e, epsilon=0.0, n_states=total)   # PPO : pas d'epsilon
        for k in history:
            history[k].append(e[k])
    return agent, history, tests, final, seconds
