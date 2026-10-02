# Résultats du projet — récapitulatif

Niveau **v3** (terrain + blocs + 17 ennemis) sauf mention contraire. Mesures
de l'article (section 2.3.3) calculées sur les **500 derniers épisodes**
d'entraînement ; « robustesse » = 50 parties sans apprendre avec 2 % de
boutons au hasard (même test pour tout le monde) ; « test glouton » = une
partie sans aucun hasard.

Tous les modèles v3 ont été entraînés sur **la même machine** (MacBook Air
M4) avec CodeCarbon, sauf l'étape 3 (CNN, PC Legion avec carte graphique).

## 1. Comparaison des algorithmes (v3, 6000 épisodes, moyenne ± écart-type)

| Algorithme | Graines | ε final | Victoires | **Robustesse** | Test glouton gagné | Retour moyen | → 50 % | → 80 % | Morts |
|---|---|---|---|---|---|---|---|---|---|
| Q-Learning | 5 | 0,01 | 94,5 ± 1,5 % | 88,8 ± 2,7 % | 5 / 5 | 231,4 ± 11,6 | 2819 ± 62 | 3522 ± 68 | 5,5 % |
| SARSA | 5 | 0,01 | **96,2 ± 1,2 %** | 88,8 ± 3,0 % | 5 / 5 | 241,3 ± 5,4 | 2753 ± 107 | 3354 ± 100 | 3,8 % |
| Monte Carlo | 5 | 0,01 | **96,2 ± 0,7 %** | 88,8 ± 2,3 % | 5 / 5 | 258,1 ± 13,3 | 2862 ± 129 | 3450 ± 108 | 3,7 % |
| DQN de l'article (refait) | 5 | 0,05 | 39,7 ± 6,7 % | 58,4 ± 33,3 % | 3 / 5 | 120,7 ± 17,7 | 5188 ± 454 | jamais | 59,9 % |
| **Notre DQN (étape 4)** | 5 | 0,02 | 93,7 ± 1,4 % | **94,4 ± 3,0 %** | 5 / 5 | **273,8 ± 4,1** | **2051 ± 165** | **2955 ± 129** | 6,3 % |

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
| DQN de l'article | 6,02 | 2,20 | 5,09 | 205 | 628 ± 194 |
| Notre DQN (étape 4) | **12,58** | **4,98** | **7,07** | 246 | 632 ± 117 |

## 3. Comparaison avec l'article (v3)

| Algorithme | Victoires (nous / article) | Retour (nous / article) | → 50 % (nous / article) | → 80 % (nous / article) | Ennemis (nous / article) |
|---|---|---|---|---|---|
| Q-Learning | 94,5 % / 86,5 ± 2,7 % | 231 / 173 | 2819 / 3157 | 3522 / 4029 | 6,1 / 3,8 |
| SARSA | 96,2 % / 84,4 ± 5,6 % | 241 / 167 | 2753 / 3510 | 3354 / 4446 | 6,9 / 3,8 |
| Monte Carlo | 96,2 % / 94,9 ± 1,5 % | 258 / 174 | 2862 / 2816 | 3450 / 3493 | 12,1 / 3,3 |
| DQN (article) | 39,7 % / 76,4 ± 3,4 % | 121 / 159 | 5188 / 2643 | jamais / 4016 | 6,0 / 1,4 |

Article : 10 000 épisodes, 5 graines. Nous : 6000 épisodes, 5 graines.
Nos agents écrasent 2 à 4 fois plus d'ennemis : l'article ne précise pas les
règles des ennemis (activation, rebond, chute), nos choix les rendent
probablement plus faciles à écraser, ce qui gonfle aussi le retour.

## 4. Coût de l'entraînement (par graine, mesuré par CodeCarbon)

| Algorithme | Machine | Lancement | Durée | Énergie | CO₂ | Taille du modèle |
|---|---|---|---|---|---|---|
| Q-Learning | Mac M4 | 5 graines × 1 thread | 16 s | 0,028 Wh | 0,0015 g | Q-table ≈ 58 000 états × 3 |
| SARSA | Mac M4 | 5 graines × 1 thread | 16 s | 0,026 Wh | 0,0014 g | Q-table ≈ 61 000 états × 3 |
| Monte Carlo | Mac M4 | 5 graines × 1 thread | 33 s | 0,047 Wh | 0,0026 g | Q-table ≈ 82 000 états × 3 (+ compteurs) |
| DQN de l'article | Mac M4 | 5 graines × 1 thread | 2,6 min | 0,24 Wh | 0,014 g | réseau 31 747 poids |
| DQN étape 1 | Mac M4 | 2 graines × 2 threads | 7,3 min | 0,83 Wh | 0,047 g | réseau 319 363 poids |
| DQN étape 2 | Mac M4 | 2 graines × 2 threads | 9,1 min | 1,06 Wh | 0,059 g | réseau 319 363 poids |
| DQN étape 3 (CNN) | Legion (RTX 3060) | 2 graines, carte graphique | 51 min | 42,6 Wh | 2,4 g | réseau 1 629 475 poids |
| Notre DQN étape 4 | Mac M4 | 5 graines × 2 threads | 28 min * | 3,2 Wh * | 0,18 g * | réseau 319 363 poids |

Électricité française (≈ 56 g de CO₂ par kWh). CodeCarbon mesure toute la
machine pendant tout le lancement ; on divise par le nombre de graines. Sur
le Mac, l'énergie est **estimée** à partir de la charge du processeur (pas
de capteur lu) ; comme tout a été fait sur le même Mac, la comparaison entre
algorithmes reste juste. L'étape 3 vient d'une autre machine : ordre de
grandeur seulement.

\* **Mesure faussée par la surcharge du Mac.** 5 graines × 2 threads = 10
calculs en même temps pour 10 cœurs (dont 6 cœurs lents), sur un Mac sans
ventilateur : chaque graine a mis 28 min au lieu de 8,5 min. Le même calcul
lancé en 2 graines × 2 threads (graines 42 et 43, modèles identiques au bit
près) avait coûté **0,94 Wh par graine**, comme l'étape 1. C'est l'ordre de
grandeur réel ; un nouveau lancement avec 1 thread par graine (comme les
autres lancements à 5 graines) donnera la mesure propre.

Vitesse du Mac M4 par rapport au cloud (même calcul) : environ 2,5 fois plus
rapide pour les tableaux et le petit DQN, environ 9 fois pour les gros DQN
(étapes 1 et 2).

## 5. Étude par étapes de notre DQN (v3, graines 42 et 43, 6000 épisodes)

| Étape | Changement | Victoires | Robustesse (42 / 43) | → 50 % | → 80 % |
|---|---|---|---|---|---|
| 0 | DQN de l'article (vue de l'article) | 44,2 ± 6,8 % | 62 % / 74 % | 5047 | jamais |
| 1 | + vue complète (14 × 28 cases, 6 calques) | 81,8 ± 0,0 % | 96 % / 78 % | 1999 | 2900 |
| 2 | 1 + Double DQN, 3 pas, cible douce, limitation, meilleure version | 78,2 ± 9,6 % | 80 % / 90 % | 2730 | 4330 |
| 3 | 1 + CNN, limitation, meilleure version (Legion) | 76,6 ± 8,5 % | — (poids perdus) | 2210 | 3351 |
| 4 | 1 + ε plancher 0,02, mémoire 100 000, limitation, meilleure version | **94,5 ± 1,8 %** | **94 % / 94 %** | 1959 | 3022 |

Ce qui compte : **la vue complète** (+38 points). Les améliorations connues
de DQN (étape 2) et le CNN (étape 3) n'apportent rien ici ; l'étape 4 apporte
surtout de la stabilité (moins de hasard en fin d'entraînement, meilleure
version gardée).

Sur les 5 graines (42 à 46), l'étape 4 donne 93,7 ± 1,4 % de victoires et
94,4 ± 3,0 % de robustesse (90 à 98 % selon la graine).

Les DQN refaits sur le Mac ne donnent pas exactement les mêmes chiffres que
dans le cloud (étape 0 : 37,1 → 44,2 % ; étape 1 : 81,1 → 81,8 % ; étape 2 :
80,6 → 78,2 %) : les calculs d'un réseau de neurones ne tombent pas
identiques au bit près d'un processeur à l'autre, ni quand on change le
nombre de threads, et DQN amplifie ces petites différences. Les conclusions
ne changent pas. Les méthodes à tableau, elles, donnent exactement les mêmes
résultats sur les deux machines.

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
   voire mieux** (94 à 96 % de victoires), coûtent presque rien (16 à 33 s
   et moins de 0,05 Wh par graine sur le Mac), et sont parfaitement
   reproductibles : refaites sur une autre machine, elles donnent
   exactement les mêmes résultats.
2. **Le DQN de l'article, refait à l'identique, échoue chez nous** (39,7 %
   contre 76,4 %) : DQN est très sensible aux détails que l'article ne donne
   pas, et instable d'une graine à l'autre (une graine à 0 % de robustesse,
   dans le cloud comme sur le Mac).
3. **Notre DQN est le meilleur modèle à hasard égal** (94 % de robustesse
   contre 89 % pour les tableaux), grâce à une seule chose : **lui montrer
   tout l'écran** (trous, direction des ennemis).
4. **Plus gros n'est pas mieux** : le CNN sur carte graphique a coûté environ
   50 fois plus d'énergie par graine que l'étape 1 sur le Mac, pour un moins
   bon résultat.
5. **Mesurer l'énergie demande un protocole** : même machine, même façon de
   lancer. Trop de calculs en même temps sur le Mac a rendu chaque graine de
   l'étape 4 trois fois plus lente et trois fois plus coûteuse.
