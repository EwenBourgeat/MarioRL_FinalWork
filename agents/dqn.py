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
from collections import deque

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
        # facteur appliqué à la note de s2 : gamma (1 pas) ou gamma^k (k pas)
        self.disc = np.zeros(capacity, dtype=np.float32)
        self.i = 0
        self.size = 0
        self.rng = rng

    def add(self, s, a, r, s2, terminated, disc):
        i = self.i
        self.s[i], self.a[i], self.r[i] = s, a, r
        self.s2[i], self.done[i] = s2, float(terminated)
        self.disc[i] = disc
        self.i = (i + 1) % self.capacity
        self.size = min(self.size + 1, self.capacity)

    def sample(self, n):
        idx = self.rng.integers(0, self.size, size=n)
        return (self.s[idx], self.a[idx], self.r[idx], self.s2[idx],
                self.done[idx], self.disc[idx])


def make_network(n_inputs, n_actions, hidden=128):
    return nn.Sequential(nn.Linear(n_inputs, hidden), nn.ReLU(),
                         nn.Linear(hidden, hidden), nn.ReLU(),
                         nn.Linear(hidden, n_actions))


class DQNAgent:
    FILENAME = "dqn.pt"

    def __init__(self, obs_high, n_actions=3, gamma=0.99, seed=42, lr=1e-4,
                 buffer_size=50_000, batch_size=64, train_every=4,
                 target_every=500, learning_starts=1000, hidden=128,
                 double=False, n_step=1, grad_clip=None, tau=None):
        torch.manual_seed(seed)
        self.n_actions = int(n_actions)
        self.gamma = float(gamma)
        self.batch_size = batch_size
        self.train_every = train_every
        self.target_every = target_every
        self.learning_starts = learning_starts
        self.hidden = hidden
        self.lr = lr
        # --- améliorations de notre DQN (étape 2), toutes optionnelles ---
        self.double = bool(double)      # 2a : Double DQN
        self.n_step = int(n_step)       # 2b : récompenses sur n pas
        self.pending = deque()          # pas en attente (n-step)
        self.grad_clip = grad_clip      # 2c : taille max d'une correction
        self.tau = tau                  # 2d : cible douce (None = copie
                                        #      d'un coup tous les 500)
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
    def observe(self, s, a, r, s2, terminated, end=None):
        """Note un pas dans la mémoire, et apprend tous les 4 pas.

        ``end`` = la partie s'arrête ici (drapeau, mort OU limite de pas) ;
        sert à vider les pas en attente du n-step.
        """
        end = terminated if end is None else end
        # 2b. n-step : on garde les derniers pas en attente ; dès qu'il y
        # en a n, le plus ancien part en mémoire avec la somme de ses n
        # récompenses (r1 + g.r2 + g².r3) et la situation n pas plus tard
        self.pending.append((self.normalize(s), a, r))
        s2n = self.normalize(s2)
        if len(self.pending) == self.n_step:
            self._store_oldest(s2n, terminated)
        if end:                          # fin de partie : on range le reste
            while self.pending:
                self._store_oldest(s2n, terminated)
        self.steps += 1
        if (self.memory.size >= self.learning_starts
                and self.steps % self.train_every == 0):
            self.learn()

    def _store_oldest(self, s2n, terminated):
        """Range en mémoire le plus ancien pas en attente."""
        total, g = 0.0, 1.0
        for _, _, r in self.pending:     # r1 + gamma.r2 + gamma².r3 ...
            total += g * r
            g *= self.gamma
        s, a, _ = self.pending.popleft()
        # g vaut maintenant gamma^k (k = nombre de pas additionnés)
        self.memory.add(s, a, total, s2n, terminated, g)

    def learn(self):
        s, a, r, s2, done, disc = (torch.from_numpy(x) for x in
                                   self.memory.sample(self.batch_size))
        q = self.net(s).gather(1, a.unsqueeze(1)).squeeze(1)
        with torch.no_grad():
            if self.double:
                # 2a. Double DQN : le réseau principal CHOISIT le bouton
                # suivant, le réseau cible lui DONNE SA NOTE (évite de
                # toujours attraper les erreurs vers le haut avec le max)
                a2 = self.net(s2).argmax(1, keepdim=True)
                next_q = self.target(s2).gather(1, a2).squeeze(1)
            else:
                # DQN de l'article : meilleure note selon le réseau cible
                next_q = self.target(s2).max(1)[0]
            # cible de Q-Learning ; pas de suite si la partie est vraiment
            # finie (done = 1)
            # (disc = gamma pour 1 pas, gamma^3 pour 3 pas)
            target = r + disc * (1 - done) * next_q
        loss = self.loss_fn(q, target)
        self.opt.zero_grad()
        loss.backward()
        if self.grad_clip:
            # 2c. on rabote une correction trop grande, en gardant sa
            # direction : une mort (-50) ne dérègle pas tout le réseau
            nn.utils.clip_grad_norm_(self.net.parameters(), self.grad_clip)
        self.opt.step()
        self.updates += 1
        if self.tau:
            # 2d. cible douce : à chaque apprentissage, la copie devient
            # 99,5 % d'elle-même + 0,5 % du réseau principal (tau = 0,005)
            with torch.no_grad():
                for p_t, p in zip(self.target.parameters(),
                                  self.net.parameters()):
                    p_t.mul_(1 - self.tau).add_(p, alpha=self.tau)
        elif self.updates % self.target_every == 0:
            # DQN de l'article : copie complète tous les 500 apprentissages
            self.target.load_state_dict(self.net.state_dict())
        return loss.item()

    # ------------------------------------------------------------------
    def snapshot(self):
        """Copie des poids du réseau (pour garder la meilleure version)."""
        import copy
        return copy.deepcopy(self.net.state_dict())

    def restore(self, snap):
        self.net.load_state_dict(snap)
        self.target.load_state_dict(snap)

    # ------------------------------------------------------------------
    def save(self, path):
        # uniquement des types Python simples : le fichier se recharge en
        # mode sûr (weights_only), sans exécuter de code
        torch.save({"net": self.net.state_dict(),
                    "obs_high": [float(x) for x in self.obs_high],
                    "n_actions": int(self.n_actions),
                    "gamma": float(self.gamma), "hidden": int(self.hidden),
                    "lr": float(self.lr)}, path)

    @classmethod
    def load(cls, path, seed=0):
        data = torch.load(path, map_location="cpu", weights_only=True)
        agent = cls(data["obs_high"], data["n_actions"], data["gamma"], seed,
                    lr=data["lr"], hidden=data["hidden"], buffer_size=1)
        agent.net.load_state_dict(data["net"])
        agent.target.load_state_dict(data["net"])
        agent.net.eval()
        return agent
