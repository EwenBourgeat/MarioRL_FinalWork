"""Agent Monte Carlo « première visite » (article, section 2.2.3).

Différence avec Q-Learning et SARSA : l'agent ne corrige RIEN pendant la
partie.  Il note tout ce qui se passe (situation, bouton, récompense), puis,
une fois la partie finie, il donne à chaque choix les points obtenus depuis
ce choix jusqu'à la fin (G), et fait la moyenne avec ce qu'il avait déjà vu :

    Q(s, a) <- Q(s, a) + (1 / N(s, a)) * [ G - Q(s, a) ]

* G = r1 + gamma * r2 + gamma^2 * r3 + ...  (calculé en remontant depuis la fin)
* N(s, a) = nombre de fois où ce choix a été fait dans cette situation :
  1/N remplace alpha et rend Q égal à la moyenne exacte de tous les G vus.
* « Première visite » : si Mario repasse par la même situation et refait le
  même choix dans une partie, seul le premier passage compte.

Ce n'est pas du deep learning : comme Q-Learning et SARSA, tout est rangé
dans un tableau (la Q-table), plus le tableau N des passages.
"""

from __future__ import annotations

import numpy as np

from .qlearning import QLearningAgent


class MonteCarloAgent(QLearningAgent):
    """Q-table + compteurs N ; mise à jour en fin de partie."""

    def __init__(self, n_actions=3, alpha=None, gamma=0.99, seed=42):
        # alpha n'est pas utilisé (remplacé par 1/N) ; gardé pour l'interface
        super().__init__(n_actions, 0.0 if alpha is None else alpha, gamma,
                         seed)
        self.n = {}

    def update_episode(self, trajectory):
        """Met à jour Q à partir d'une partie complète.

        ``trajectory`` = liste de (situation, action, récompense), dans
        l'ordre où ils ont été joués.  Si la partie a été coupée (1000 pas),
        on la garde telle quelle : G ne contient que les points obtenus.
        """
        # premier passage de chaque (situation, action) dans la partie
        first = {}
        for t, (s, a, _) in enumerate(trajectory):
            first.setdefault((s, a), t)
        g = 0.0
        for t in range(len(trajectory) - 1, -1, -1):       # de la fin au début
            s, a, r = trajectory[t]
            g = r + self.gamma * g
            if first[(s, a)] != t:
                continue                    # pas la première visite : ignoré
            values = self.q.get(s)
            if values is None:
                values = self.q[s] = [0.0] * self.n_actions
                self.n[s] = [0] * self.n_actions
            counts = self.n[s]
            counts[a] += 1
            values[a] += (g - values[a]) / counts[a]     # moyenne des G

    # sauvegarde : Q-table + compteurs N
    def save(self, path):
        states, values = self.to_arrays()
        counts = (np.array([self.n[tuple(s)] for s in states.tolist()],
                           dtype=np.int64) if len(states) else
                  np.zeros((0, self.n_actions), dtype=np.int64))
        np.savez_compressed(path, states=states, values=values, counts=counts,
                            params=np.array([self.alpha, self.gamma]))

    @classmethod
    def load(cls, path, seed=0):
        agent = super().load(path, seed)
        data = np.load(path, allow_pickle=False)
        if "counts" in data:
            agent.n = {tuple(s): list(c) for s, c in
                       zip(data["states"].tolist(), data["counts"].tolist())}
        return agent
