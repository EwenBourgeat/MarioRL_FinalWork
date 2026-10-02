# Résultats du projet — récapitulatif

Niveau **v3** (terrain + blocs + 17 ennemis) sauf mention contraire. Mesures
de l'article (section 2.3.3) calculées sur les **500 derniers épisodes**
d'entraînement ; « robustesse » = 50 parties sans apprendre avec 2 % de
boutons au hasard (même test pour tout le monde) ; « test glouton » = une
partie sans aucun hasard.

## 1. Comparaison des algorithmes (v3, 6000 épisodes, moyenne ± écart-type)

| Algorithme | Graines | ε final | Victoires | **Robustesse** | Test glouton gagné | Retour moyen | → 50 % | → 80 % | Morts |
|---|---|---|---|---|---|---|---|---|---|
| Q-Learning | 5 | 0,01 | 94,5 ± 1,5 % | 88,8 ± 2,7 % | 5 / 5 | 231,4 ± 11,6 | 2819 ± 62 | 3522 ± 68 | 5,5 % |
| SARSA | 5 | 0,01 | **96,2 ± 1,2 %** | 88,8 ± 3,0 % | 5 / 5 | 241,3 ± 5,4 | 2753 ± 107 | 3354 ± 100 | 3,8 % |
| Monte Carlo | 5 | 0,01 | **96,2 ± 0,7 %** | 88,8 ± 2,3 % | 5 / 5 | 258,1 ± 13,3 | 2862 ± 129 | 3450 ± 108 | 3,7 % |
| DQN de l'article (refait) | 5 | 0,05 | 41,5 ± 12,5 % | 59,6 ± 37,7 % | 3 / 5 | 124,9 ± 30,3 | 5224 ± 499 | jamais | 58,4 % |
| **Notre DQN (étape 4)** | 5 | 0,02 | 93,9 ± 1,5 % | **94,0 ± 2,8 %** | 5 / 5 | **275,5 ± 3,2** | **2095 ± 129** | **2959 ± 116** | 6,1 % |

Les « victoires » ne sont pas mesurées avec le même ε (part de hasard pendant
l'entraînement) : 1 % pour les tableaux, 5 % pour le DQN de l'article, 2 %
pour notre DQN. **La robustesse, elle, est mesurée pareil pour tous** : c'est
la colonne à comparer pour savoir qui joue le mieux.

## 2. Comportement en jeu (v3, par partie, 500 derniers épisodes)

| Algorithme | Ennemis écrasés | Briques cassées | Blocs ? frappés | Pas par partie | 1re victoire (épisode) |
|---|---|---|---|---|---|
| Q-Learning | 6,10 | 2,87 | 4,29 | 268 | 1322 ± 356 |
| SARSA | 6,89 | 3,62 | 4,75 | 266 | 1178 ± 293 |
| Monte Carlo | 12,06 | 4,88 | 5,34 | **503** (attend les ennemis) | 1108 ± 443 |
| DQN de l'article | 6,01 | 2,02 | 5,07 | 203 | 572 ± 170 |
| Notre DQN (étape 4) | **12,86** | **5,20** | **6,91** | 248 | 665 ± 123 |

## 3. Comparaison avec l'article (v3)

| Algorithme | Victoires (nous / article) | Retour (nous / article) | → 50 % (nous / article) | → 80 % (nous / article) | Ennemis (nous / article) |
|---|---|---|---|---|---|
| Q-Learning | 94,5 % / 86,5 ± 2,7 % | 231 / 173 | 2819 / 3157 | 3522 / 4029 | 6,1 / 3,8 |
| SARSA | 96,2 % / 84,4 ± 5,6 % | 241 / 167 | 2753 / 3510 | 3354 / 4446 | 6,9 / 3,8 |
| Monte Carlo | 96,2 % / 94,9 ± 1,5 % | 258 / 174 | 2862 / 2816 | 3450 / 3493 | 12,1 / 3,3 |
| DQN (article) | 41,5 % / 76,4 ± 3,4 % | 125 / 159 | 5224 / 2643 | jamais / 4016 | 6,0 / 1,4 |

Article : 10 000 épisodes, 5 graines. Nous : 6000 épisodes, 5 graines.
Nos agents écrasent 2 à 4 fois plus d'ennemis : l'article ne précise pas les
règles des ennemis (activation, rebond, chute), nos choix les rendent
probablement plus faciles à écraser, ce qui gonfle aussi le retour.

## 4. Coût de l'entraînement (par graine)

| Algorithme | Machine | Durée | Énergie | CO₂ | Taille du modèle | Type de mesure |
|---|---|---|---|---|---|---|
| Q-Learning | cloud (CPU) | 38 s | 0,08 Wh | 0,004 g | Q-table ≈ 58 000 états × 3 | CodeCarbon (estimé) |
| SARSA | cloud (CPU) | 37 s | 0,08 Wh | 0,004 g | Q-table ≈ 61 000 états × 3 | CodeCarbon (estimé) |
| Monte Carlo | cloud (CPU) | 81 s | 0,17 Wh | 0,010 g | Q-table ≈ 82 000 états × 3 (+ compteurs) | CodeCarbon (estimé) |
| DQN de l'article | cloud (CPU) | 7 min | ≈ 1 Wh | ≈ 0,05 g | réseau 31 747 poids | extrapolé de la puissance mesurée |
| DQN étape 1 | cloud (CPU) | 65 min | ≈ 7 Wh | ≈ 0,4 g | réseau 319 363 poids | extrapolé |
| DQN étape 2 | cloud (CPU) | 79 min | ≈ 9 Wh | ≈ 0,5 g | réseau 319 363 poids | extrapolé |
| DQN étape 3 (CNN) | Legion (RTX 3060) | 51 min | 42,6 Wh | 2,4 g | réseau 1 629 475 poids | CodeCarbon (carte graphique mesurée) |
| **Notre DQN étape 4** | **Mac M4 (CPU)** | **8,5 à 14 min** | **1,2 Wh** | **0,07 g** | réseau 319 363 poids | CodeCarbon (estimé) |

Électricité française (≈ 56 g de CO₂ par kWh). Les durées dépendent beaucoup
de la machine (le Mac M4 est environ 7 fois plus rapide que le cloud pour
DQN) : comparer l'énergie entre machines donne un ordre de grandeur, pas une
mesure exacte.

Notre DQN étape 4 a été lancé en deux fois sur le Mac : graines 42-43
(2 × 2 threads, 8,5 min, 1,88 Wh, soit 0,94 Wh par graine) puis 44-46
(3 × 3 threads, 14 min, 4,13 Wh, soit 1,38 Wh par graine). Total 5 graines :
6,0 Wh et 0,34 g de CO₂. La façon de lancer (combien de graines et de threads
en même temps) change donc la mesure par graine.

## 5. Étude par étapes de notre DQN (v3, graines 42 et 43, 6000 épisodes)

| Étape | Changement | Victoires | Robustesse | → 50 % | → 80 % |
|---|---|---|---|---|---|
| 0 | DQN de l'article (vue de l'article) | 37,1 % | 44 % / 82 % | 5284 | jamais |
| 1 | + vue complète (14 × 28 cases, 6 calques) | 81,1 ± 1,8 % | 94 % / 92 % | 2004 | 2837 |
| 2 | 1 + Double DQN, 3 pas, cible douce, limitation, meilleure version | 80,6 ± 4,0 % | 92 % / 86 % | 2648 | 3194 |
| 3 | 1 + CNN, limitation, meilleure version | 76,6 ± 8,5 % | — (poids perdus) | 2210 | 3351 |
| 4 | 1 + ε plancher 0,02, mémoire 100 000, limitation, meilleure version | **94,5 ± 1,8 %** | **94 % / 94 %** | 1959 | 3022 |

Ce qui compte : **la vue complète** (+44 points). Les améliorations connues
de DQN (étape 2) et le CNN (étape 3) n'apportent rien ici ; l'étape 4 apporte
surtout de la stabilité (moins de hasard en fin d'entraînement, meilleure
version gardée).

Sur les 5 graines (42 à 46), l'étape 4 donne 93,9 ± 1,5 % de victoires et
94,0 ± 2,8 % de robustesse (90 à 98 % selon la graine).

## 6. Niveaux v1 et v2 (1 graine, 42)

| Algorithme | Niveau | Épisodes | Victoires (nous / article) | Retour (nous / article) | → 80 % (nous / article) |
|---|---|---|---|---|---|
| Q-Learning | v1 | 10 000 | 99,2 % / 98,8 % | 195,5 / 191,7 | 1368 / 2122 |
| Q-Learning | v2 | 10 000 | 99,2 % / 98,9 % | 213,2 / 205,5 | 1712 / 1964 |
| SARSA | v1 | 6000 | 100,0 % / 100,0 % | 197,4 / 193,9 | 1132 / 1553 |
| SARSA | v2 | 6000 | 100,0 % / 99,8 % | 212,2 / 207,6 | 1304 / 1645 |

Monte Carlo v1/v2 non entraîné (article : 99,1 % et 99,9 %).

## 7. À retenir

1. **Sur v3, les trois méthodes à tableau font aussi bien que l'article,
   voire mieux** (94 à 96 % de victoires), et coûtent presque rien
   (moins d'une minute, moins de 0,2 Wh par graine).
2. **Le DQN de l'article, refait à l'identique, échoue chez nous** (41,5 %
   contre 76,4 %) : DQN est très sensible aux détails que l'article ne donne
   pas, et instable d'une graine à l'autre (écart-type 12,5 points).
3. **Notre DQN est le meilleur modèle à hasard égal** (94 % de robustesse
   contre 89 % pour les tableaux), grâce à une seule chose : **lui montrer
   tout l'écran** (trous, direction des ennemis).
4. **Plus gros n'est pas mieux** : le CNN sur carte graphique a coûté environ
   35 fois plus d'énergie que notre meilleur modèle, pour un moins bon
   résultat.
