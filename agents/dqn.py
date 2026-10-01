"""Agent DQN (Deep Q-Network, Mnih et al. 2015), réglé comme l'article (2.2.4).

DQN = Q-Learning dont la Q-table est remplacée par un réseau de neurones.
La cible reste celle de Q-Learning :  r + gamma * max_a' Q_cible(s', a').

Trois ingrédients (réglages de l'article) :

* le RÉSEAU : 115 entrées (ce que voit Mario en v3) -> 128 -> 128 -> 3 notes,
  activations ReLU.  Il devine les notes au lieu de les stocker ;
* la MÉMOIRE DE REPLAY : les 50 000 derniers pas ; le réseau apprend sur des
  paquets de 64 souvenirs tirés au hasard, une fois tous les 4 pas ;
* le RÉSEAU CIBLE : une copie figée qui calcule les cibles, recopiée tous
  les 500 apprentissages.

Vitesse d'apprentissage 0,0001 (Adam).  Plancher de epsilon : 0,05.

Détails que l'article ne précise pas (nos choix, standards) :
* entrées ramenées entre 0 et 1 (chaque nombre divisé par sa valeur max) ;
* erreur de Huber (comme le DQN d'origine) ;
* apprentissage seulement quand la mémoire contient au moins 1000 pas.
"""

from __future__ import annotations

import random

import numpy as np

try:
    import torch
    from torch import nn
except ImportError as exc:                      # PyTorch absent
    raise ImportError(
        "DQN a besoin de PyTorch : pip install -r requirements-dqn.txt") from exc


class ReplayMemory:
    """Carnet circulaire des derniers pas (le plus ancien est effacé)."""

    def __init__(self, capacity, obs_size, rng):
        self.capacity = capacity
        self.s = np.zeros((capacity, obs_size), dtype=np.float32)
        self.a = np.zeros(capacity, dtype=np.int64)
        self.r = np.zeros(capacity, dtype=np.float32)
        self.s2 = np.zeros((capacity, obs_size), dtype=np.float32)
        self.done = np.zeros(capacity, dtype=np.float32)
        self.i = 0
        self.size = 0
        self.rng = rng

    def add(self, s, a, r, s2, terminated):
        i = self.i
        self.s[i], self.a[i], self.r[i] = s, a, r
        self.s2[i], self.done[i] = s2, float(terminated)
        self.i = (i + 1) % self.capacity
        self.size = min(self.size + 1, self.capacity)

    def sample(self, n):
        idx = self.rng.integers(0, self.size, size=n)
        return (self.s[idx], self.a[idx], self.r[idx], self.s2[idx],
                self.done[idx])


def make_network(n_inputs, n_actions, hidden=128):
    return nn.Sequential(nn.Linear(n_inputs, hidden), nn.ReLU(),
                         nn.Linear(hidden, hidden), nn.ReLU(),
                         nn.Linear(hidden, n_actions))


class DQNAgent:
    FILENAME = "dqn.pt"

    def __init__(self, obs_high, n_actions=3, gamma=0.99, seed=42, lr=1e-4,
                 buffer_size=50_000, batch_size=64, train_every=4,
                 target_every=500, learning_starts=1000, hidden=128):
        torch.manual_seed(seed)
        self.n_actions = n_actions
        self.gamma = gamma
        self.batch_size = batch_size
        self.train_every = train_every
        self.target_every = target_every
        self.learning_starts = learning_starts
        self.hidden = hidden
        self.lr = lr
        # pour ramener chaque nombre observé entre 0 et 1
        self.obs_high = np.maximum(np.asarray(obs_high, dtype=np.float32), 1)
        n_in = len(self.obs_high)
        self.net = make_network(n_in, n_actions, hidden)
        self.target = make_network(n_in, n_actions, hidden)
        self.target.load_state_dict(self.net.state_dict())
        self.opt = torch.optim.Adam(self.net.parameters(), lr=lr)
        self.loss_fn = nn.SmoothL1Loss()                    # erreur de Huber
        self.rng = random.Random(seed)                      # epsilon-greedy
        self.memory = ReplayMemory(buffer_size, n_in,
                                   np.random.default_rng(seed))
        self.steps = 0
        self.updates = 0

    # ------------------------------------------------------------------
    def normalize(self, obs):
        return np.asarray(obs, dtype=np.float32) / self.obs_high

    def q_values(self, obs):
        with torch.no_grad():
            x = torch.from_numpy(self.normalize(obs)).unsqueeze(0)
            return self.net(x)[0].numpy()

    def best_action(self, state, rng=None):
        """Action la mieux notée par le réseau (``state`` = tuple ou tableau)."""
        q = self.q_values(state)
        best = np.flatnonzero(q == q.max())
        if len(best) == 1:
            return int(best[0])
        return int((rng or self.rng).choice(best.tolist()))

    def act(self, state, epsilon):
        if self.rng.random() < epsilon:
            return self.rng.randrange(self.n_actions)
        return self.best_action(state)

    def greedy_policy(self, seed=0):
        rng = random.Random(seed)
        return lambda state: self.best_action(state, rng)

    # ------------------------------------------------------------------
    def observe(self, s, a, r, s2, terminated):
        """Note un pas dans la mémoire, et apprend tous les 4 pas."""
        self.memory.add(self.normalize(s), a, r, self.normalize(s2),
                        terminated)
        self.steps += 1
        if (self.memory.size >= self.learning_starts
                and self.steps % self.train_every == 0):
            self.learn()

    def learn(self):
        s, a, r, s2, done = (torch.from_numpy(x) for x in
                             self.memory.sample(self.batch_size))
        q = self.net(s).gather(1, a.unsqueeze(1)).squeeze(1)
        with torch.no_grad():
            # cible de Q-Learning, calculée avec le réseau cible figé ;
            # pas de suite si la partie est vraiment finie (done = 1)
            target = r + self.gamma * (1 - done) * self.target(s2).max(1)[0]
        loss = self.loss_fn(q, target)
        self.opt.zero_grad()
        loss.backward()
        self.opt.step()
        self.updates += 1
        if self.updates % self.target_every == 0:
            self.target.load_state_dict(self.net.state_dict())
        return float(loss)

    # ------------------------------------------------------------------
    def save(self, path):
        torch.save({"net": self.net.state_dict(),
                    "obs_high": self.obs_high.tolist(),
                    "n_actions": self.n_actions, "gamma": self.gamma,
                    "hidden": self.hidden, "lr": self.lr}, path)

    @classmethod
    def load(cls, path, seed=0):
        data = torch.load(path, map_location="cpu", weights_only=True)
        agent = cls(data["obs_high"], data["n_actions"], data["gamma"], seed,
                    lr=data["lr"], hidden=data["hidden"], buffer_size=1)
        agent.net.load_state_dict(data["net"])
        agent.target.load_state_dict(data["net"])
        agent.net.eval()
        return agent
