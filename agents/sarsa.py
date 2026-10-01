"""Agent SARSA tabulaire (Rummery & Niranjan, 1994), comme dans l'article (2.2.2).

SARSA ressemble à Q-Learning : même Q-table, même epsilon-greedy, mêmes
réglages.  Une seule chose change, la *cible* de la mise à jour :

    Q-Learning : cible = r + gamma * max_a' Q(s', a')   (le MEILLEUR bouton)
    SARSA      : cible = r + gamma * Q(s', a')          (le bouton a' que
                                                          l'agent va VRAIMENT
                                                          jouer, hasard compris)

Le nom vient des cinq éléments utilisés : State, Action, Reward, State',
Action' (situation, action, récompense, situation suivante, action suivante).

Conséquence : SARSA tient compte de ses propres erreurs d'exploration.  Si,
au bord d'un trou, une action tirée au hasard peut le tuer, la note de cette
situation baisse ; il apprend donc des chemins plus prudents.  On dit que
SARSA est « on-policy » (il apprend la valeur de la façon dont il joue
réellement) et Q-Learning « off-policy » (il apprend la valeur du jeu parfait).
"""

from __future__ import annotations

from .qlearning import QLearningAgent


class SarsaAgent(QLearningAgent):
    """Tout est hérité de QLearningAgent sauf la mise à jour.

    Différence pratique dans la boucle d'entraînement : il faut choisir
    l'action suivante a' AVANT de mettre à jour, puis jouer exactement cette
    action au pas suivant (voir ``training.play_sarsa_episode``).
    """

    def update(self, s, a, r, s2, a2, terminated):
        """Une mise à jour SARSA ; renvoie l'erreur (cible - ancienne note).

        ``a2`` = action déjà choisie (epsilon-greedy) pour la situation s2.
        Si l'épisode est vraiment terminé (drapeau ou mort), il n'y a pas
        d'après : la cible vaut juste r.  Si la partie est seulement coupée
        (1000 pas), on garde gamma * Q(s2, a2), avec a2 tiré comme d'habitude.
        """
        values = self.q.get(s)
        if values is None:
            values = self.q[s] = [0.0] * self.n_actions
        if terminated:
            target = r
        else:
            nxt = self.q.get(s2)
            target = r + self.gamma * (nxt[a2] if nxt is not None else 0.0)
        error = target - values[a]
        values[a] += self.alpha * error
        return error
