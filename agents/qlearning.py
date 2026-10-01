"""Agent Q-Learning tabulaire (Watkins, 1989), comme dans l'article (2.2.1).

L'idée en une phrase : l'agent remplit un grand tableau, la « Q-table », qui
donne pour chaque situation (un *état*) et chaque bouton (une *action*) une
note : la somme des récompenses qu'il pense obtenir s'il appuie sur ce bouton
puis joue au mieux ensuite.  Pour jouer, il prend le bouton le mieux noté,
sauf de temps en temps où il essaie un bouton au hasard (exploration).

Après chaque pas (état s, action a) -> récompense r, nouvel état s', il
corrige la note de (s, a) :

    Q(s, a) <- Q(s, a) + alpha * [ r + gamma * max_a' Q(s', a') - Q(s, a) ]
                                   \_________________________/
                                    « cible » : ce que ce pas vient de
                                    nous apprendre sur la valeur de (s, a)

* alpha (taux d'apprentissage, 0.1) : on ne fait que 10 % du chemin vers la
  cible, pour ne pas tout oublier à cause d'un seul pas malchanceux ;
* gamma (facteur d'actualisation, 0.99) : une récompense obtenue dans k pas
  vaut 0.99^k fois moins qu'une récompense immédiate ;
* max_a' Q(s', a') : la note du *meilleur* bouton dans le nouvel état, même
  si l'agent ne l'appuiera peut-être pas (exploration).  C'est ce qui fait de
  Q-Learning un algorithme « off-policy » (différence avec SARSA).
"""

from __future__ import annotations

import random

import numpy as np


class QLearningAgent:
    """Q-table stockée dans un dictionnaire {état: [Q(état, 0), Q(état, 1), ...]}.

    Un état est un tuple d'entiers (l'observation de l'environnement, voir
    ``mario_env.state_key``).  Un état jamais visité vaut [0, 0, 0] :
    c'est l'initialisation à 0 choisie ensemble.  On ne l'ajoute au
    dictionnaire qu'au moment de sa première mise à jour, ce qui économise
    beaucoup de mémoire quand les états sont nombreux (v3).
    """

    def __init__(self, n_actions=3, alpha=0.1, gamma=0.99, seed=42):
        self.n_actions = int(n_actions)
        self.alpha = float(alpha)
        self.gamma = float(gamma)
        self.q = {}
        # Générateur aléatoire *personnel* de l'agent : avec la même graine,
        # il tire exactement les mêmes nombres, donc l'entraînement est
        # reproductible à l'identique.
        self.rng = random.Random(seed)

    # ------------------------------------------------------------------
    # Choisir une action
    # ------------------------------------------------------------------
    def best_action(self, state, rng=None):
        """Action la mieux notée ; en cas d'égalité, tirage au sort.

        Le tirage au sort est important : au début toutes les notes valent 0,
        et « prendre la première » ferait toujours choisir l'action 0 (rien).
        """
        rng = rng or self.rng
        values = self.q.get(state)
        if values is None:                      # état jamais vu : 0, 0, 0
            return rng.randrange(self.n_actions)
        best = max(values)
        ties = [a for a, v in enumerate(values) if v == best]
        return ties[0] if len(ties) == 1 else rng.choice(ties)

    def act(self, state, epsilon):
        """Politique epsilon-greedy : hasard avec la probabilité epsilon."""
        if self.rng.random() < epsilon:
            return self.rng.randrange(self.n_actions)    # exploration
        return self.best_action(state)                   # exploitation

    def greedy_policy(self, seed=0):
        """Politique sans exploration (epsilon = 0) pour tester ou regarder.

        Elle a son propre générateur (graine ``seed``) pour départager les
        égalités : le test glouton donne donc toujours le même résultat, et
        la partie regardée dans le menu MODELES est identique au test.
        """
        rng = random.Random(seed)
        return lambda state: self.best_action(state, rng)

    # ------------------------------------------------------------------
    # Apprendre
    # ------------------------------------------------------------------
    def update(self, s, a, r, s2, terminated):
        """Une mise à jour Q-Learning ; renvoie l'erreur (cible - ancienne note).

        ``terminated`` = l'épisode s'est vraiment arrêté (drapeau ou mort) :
        il n'y a pas d'après, donc la cible vaut juste r.  Si l'épisode a été
        seulement *coupé* (limite de 1000 pas, « truncated »), Mario aurait pu
        continuer : on garde gamma * max Q(s', .) dans la cible.
        """
        values = self.q.get(s)
        if values is None:
            values = self.q[s] = [0.0] * self.n_actions
        if terminated:
            target = r
        else:
            nxt = self.q.get(s2)
            target = r + self.gamma * (max(nxt) if nxt is not None else 0.0)
        error = target - values[a]
        values[a] += self.alpha * error
        return error

    # ------------------------------------------------------------------
    # Sauvegarde (format numpy compressé, sans pickle)
    # ------------------------------------------------------------------
    def to_arrays(self):
        """(états, valeurs) : deux tableaux numpy, une ligne par état."""
        if not self.q:
            return (np.zeros((0, 0), dtype=np.int32),
                    np.zeros((0, self.n_actions)))
        states = np.array(list(self.q.keys()), dtype=np.int32)
        values = np.array(list(self.q.values()), dtype=np.float64)
        return states, values

    def save(self, path):
        states, values = self.to_arrays()
        np.savez_compressed(path, states=states, values=values,
                            params=np.array([self.alpha, self.gamma]))

    @classmethod
    def load(cls, path, seed=0):
        data = np.load(path, allow_pickle=False)
        values = data["values"]
        alpha, gamma = data["params"].tolist()
        agent = cls(values.shape[1], alpha, gamma, seed)
        agent.q = {tuple(s): list(v) for s, v in
                   zip(data["states"].tolist(), values.tolist())}
        return agent
