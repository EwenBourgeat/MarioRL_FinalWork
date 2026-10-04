# Résumé du projet MarioRL_FinalWork (pour reprendre dans un nouveau chat)

État au 4 octobre 2026. Dépôt privé `EwenBourgeat/MarioRL_FinalWork`, branche de travail
`claude/clever-davinci-nvz48s` (dernier commit : `1613f97`, les 5 modèles route A finaux
entraînés sur le Mac).

---

## 1. Le projet en deux phrases

Projet éducatif en français : on a recréé le niveau 1-1 de Super Mario Bros (NES) en Python et
on y entraîne des IA par apprentissage par renforcement. Le but de départ était de **reproduire
l'article** de Ponnock & Ho (2026) sur l'apprentissage par renforcement dans Super Mario Bros
(Q-Learning, SARSA, Monte Carlo, DQN). Ensuite, on est allé plus loin avec **PPO sur le vrai
jeu NES** et la « **Route A** » (tuyau secret, salle bonus, champignon et fleur).

## 2. Comment travailler avec l'utilisateur

| Règle | Détail |
|---|---|
| Langue | Toujours en **français** |
| Niveau | **Débutant** : expliquer simplement, avec des **tableaux** courts. Il préfère peu de tableaux bien choisis (ex. 4 tableaux maximum pour un bilan) |
| Décisions | Il participe aux choix : proposer, recommander, puis laisser décider quand c'est structurant |
| Machines | Entraînements finaux sur son **MacBook Air M4** (10 cœurs : 4 performance + 6 efficacité, sans ventilateur). Les **essais pilotes** (2 graines, 2 M de pas) se font dans le cloud |
| Git | Committer et pousser sur `claude/clever-davinci-nvz48s`. **Ne jamais créer de pull request** sans demande |
| Commits | Message clair en anglais, terminé par les lignes d'attribution demandées par le système |
| Pushs de l'utilisateur | Deux fois, son push n'est pas arrivé sur GitHub. Si on ne voit rien de nouveau, lui demander `git status`, `git log --oneline -3` puis `git push origin claude/clever-davinci-nvz48s` |
| Ses exigences pour la route A | Mario doit passer souvent par le **tuyau** (à garder absolument), aller chercher le **champignon puis la fleur** tôt dans le niveau, et prendre la fleur **volontairement**, pas parce qu'il « saute là par habitude » |

## 3. Organisation du dépôt

| Chemin | Rôle |
|---|---|
| `mario_env/game.py` | Moteur du jeu fidèle à la NES (physique, blocs, ennemis, objets, salle bonus). `GameConfig(extra_blocks, flower_blocks, ...)` |
| `mario_env/envs/common.py` | `ACTION_SETS`, `RewardConfig` et ses préréglages (`paper`, `route_a`, `route_a2`...), `LEVEL_VERSIONS` (`v1`, `v2`, `v3`, `full`, `full_a`) |
| `mario_env/envs/nes_env.py` | `MarioNES-v0` : le vrai jeu en environnement Gymnasium (vues `vector` / `vector_plus`, récompenses, règle du blocage) |
| `mario_env/envs/` (autres fichiers) | `MarioGrid` : l'environnement simplifié de l'article (grille, 3 actions) |
| `mario_env/play.py`, `play.py` | Jeu humain et menu **MODELES** pour regarder un agent jouer (graphismes NES pour PPO) |
| `agents/` | `training.py` (`TrainConfig`, `train`, tests glouton et de robustesse), `ppo.py` (PPO via Stable-Baselines3), DQN, Q-Learning, SARSA, Monte Carlo, `metrics.py`, `registry.py` (noms et sauvegarde des modèles) |
| `train.py` | Script en ligne de commande pour tout entraîner (`--algo`, `--level`, `--obs`, `--actions`, `--reward`, `--steps`, `--seeds`, `--carbon`, `--variant`...) |
| `models/` | Modèles entraînés (`meta.json`, `history.csv`, `curves.png`, `ppo.zip` ou Q-table / réseau) |
| `docs/RESULTATS.md`, `docs/resultats_v3.csv` | Récapitulatif chiffré (sections 1 à 7) |
| `README.md` | Documentation utilisateur complète, avec la Route A |
| `tests/` | 103 tests, tous verts (`python -m pytest -q`) |
| `requirements.txt`, `requirements-dqn.txt` | Dépendances. Le second ajoute torch et `stable-baselines3>=2.3` |

Variable utile : `MARIO_MODELS_DIR=...` pour sauvegarder les modèles ailleurs que dans `models/`.
Les noms de modèles sont du type `ppo_nes_full_a_s42_3m_b` (algo, vrai jeu, niveau, graine, pas,
variante). Le menu coupe les étiquettes à 24 caractères, d'où des `--variant` courts (`A`, `B`...).

## 4. Les deux environnements

| | MarioGrid (article) | MarioNES-v0 (vrai jeu) |
|---|---|---|
| Physique | Grille simplifiée, comme l'article | Physique NES réelle, 4 images par pas (`frame_skip` 4) |
| Niveaux | `v1`, `v2`, `v3` (segments A à F) | `v3`, `full` (jeu complet + salle bonus), `full_a` (full + 2 blocs ajoutés) |
| Vues | `paper`, `full` | `vector` (62 nombres), `vector_plus` (91 nombres) |
| Boutons | `paper` (3 : rien, droite, saut) | `right_only` (5), `right_down` (6), **`right_down_left` (8)**, `simple`, `complex` |
| Récompenses | Tableau 2 de l'article | `paper`, `route_a`, **`route_a2`** |

`vector_plus` = `vector` + 29 nombres :
- l'objet le plus proche (4) ;
- les 5 pièces les plus proches (15) ;
- le prochain bloc ? (4) ;
- la distance au tuyau d'entrée (dehors) ;
- la distance au tuyau de sortie (dans la salle bonus) ;
- les boutons appuyés au pas précédent (droite, saut, course, bas : 4). Ils sont nécessaires, car la NES ne relance un saut que sur un nouvel appui.

Repères du niveau :

| Élément | Position |
|---|---|
| Tuyaux | colonnes 28, 38, 46, 57 |
| Tuyau de la salle bonus | colonne 57 : appuyer sur bas, centré sur le tuyau (x 916 à 924) |
| Salle bonus | 19 pièces, sortie en colonne 163 |
| Drapeau | colonne 198 |
| Fleurs d'origine | blocs 78 et 109, sautés par le raccourci |

La caméra ne recule jamais.

## 5. Résultats déjà acquis (détails dans `docs/RESULTATS.md`)

| Modèle (v3, 5 graines) | Victoires | Robustesse | Coût par graine (Mac M4) |
|---|---|---|---|
| Q-Learning | 94,5 ± 1,5 % | 88,8 % | 16 s, 0,028 Wh |
| SARSA | 96,2 ± 1,2 % | 88,8 % | 16 s, 0,026 Wh |
| Monte Carlo | 96,2 ± 0,7 % | 88,8 % | 33 s, 0,047 Wh |
| DQN de l'article (refait) | 39,7 ± 6,7 % | 58,4 % | 2,6 min, 0,24 Wh |
| Notre DQN (étape 4) | 93,7 ± 1,4 % | **94,4 %** | 24 min, 2,4 Wh |
| PPO sur le vrai jeu NES (3 M de pas) | 81,4 ± 5,6 % | 59,6 ± 14,1 % | 10,7 min, 0,90 Wh |

Déterminisme :
- Les méthodes à tableau donnent **exactement** les mêmes résultats sur le cloud et sur le Mac.
- Un modèle PPO rejoue à l'identique sur une autre machine.
- Le DQN change selon le processeur et le nombre de threads.

Tous ces modèles ont été refaits sur le Mac avec CodeCarbon (`--carbon`, `--overwrite`).

## 6. La Route A : historique des essais et des décisions

**Demande initiale :** Mario passe par le tuyau, ramasse toutes les pièces de la salle bonus,
prend le champignon et la fleur, tue plus d'ennemis, et apprend « bas » et les boules de feu.

**Problème :** ces objectifs se contredisent. Le tuyau 57 → 163 saute les blocs de fleur
(78, 109) et 11 des 17 ennemis. L'utilisateur a choisi la Route A (tuyau + pièces + objets).
Tuer tous les ennemis n'est pas compatible avec ce raccourci.

**Pourquoi PPO :** c'est la méthode qui marchait déjà sur le vrai jeu. Réglages : réseaux
64×64, `n_steps` 512, `batch_size` 256, 10 epochs, `lr` 3e-4, 2 environnements par graine,
`--ent-coef 0.01` (bonus de curiosité, il aide à découvrir le tuyau).

### Étape 1 : niveau `full`, récompense `route_a` (tuyau et salle bonus)

| Problème observé | Correction |
|---|---|
| Le raccourci du tuyau ne rapportait rien | L'avancée est comptée sur la **position la plus à droite atteinte** (`only_new_progress`) |
| 1 partie sur 3 restait dans la salle bonus jusqu'à la limite | Pénalité de temps −0,5 par seconde du chrono |
| Mario appuyait 866 fois sur « bas » près de la sortie | Deux cases séparées dans la vue : tuyau d'entrée et tuyau de sortie |
| Mario restait collé au tuyau 28 en tenant droite+saut | Boutons du pas précédent ajoutés dans la vue |
| `--keep-best` gardait une version chanceuse trop tôt | Abandonné pour PPO |

Résultat (2 M de pas, graines 42 et 43) : 76 à 79 % de victoires, salle bonus 86 à 88 %,
13 à 14 pièces par partie, **champignon 0 %**.

### Étape 2 : champignon et fleur tôt, niveau `full_a`, récompense `route_a2`

`route_a2` = `route_a` + :
- champignon et fleur à **+150** chacun ;
- +25 par bloc ? power-up frappé ;
- guidage de +2 par case gagnée vers l'objet visible ;
- **règle du blocage** (voir variante J).

| Variante | Essai | Résultat | Leçon |
|---|---|---|---|
| (bloc 21 d'origine) | Champignon du vrai niveau | Jamais attrapé : il roule jusqu'au tuyau 28 et revient | Il faut l'attendre ~45 pas, l'IA ne le découvre pas |
| B | Bloc power-up normal en colonne 34 | Champignon 87 à 91 %, fleur 0 % | Le bloc 34 marche pour le champignon |
| C | Bloc 34 qui ne donne que la fleur | Champignon 0 % | Mauvaise idée |
| D, E | Départ varié en colonne 18 (+ guidage) pour le bloc 21 | Champignon 0 % | Abandonné |
| F | 34 normal + **bloc de fleur** (seulement pour Mario grand) en colonne 43 | Champignon 75 à 79 %, fleur 0 à 1 % | Mario grand saute par-dessus (bloc frappé 3 %) |
| — | Colonne 37 envisagée | Bloc cogné par habitude dans 70 % des parties (saut vers le tuyau 38) | **Refusé** : la fleur doit être prise volontairement |
| G | Bloc de fleur en **colonne 36** (cogné par habitude 0 fois sur 120) | Champignon 84 à 97 %, fleur 0 %, victoires 55 à 60 % | Le bloc n'est jamais découvert |
| H | G + départ varié « déjà grand » en colonne 35, 30 % du temps (`--start-big`) | Pire : champignon 2 à 16 %, fleur 0 % | Abandonné (l'option reste) |
| — | Test au hasard : la fleur est immobile, posée sur le bloc | Prise après 0,6 % des coups de tête sans bouton gauche, 5,2 % **avec** | Sans « gauche », il faut une manœuvre très précise |
| I | G + **bouton gauche** (`right_down_left`) | Fleur 62 à 67 %, mais 0 % de victoires et 0 % de salle bonus | Mario reste coincé contre le tuyau 46 (droite+saut tenu) jusqu'à la limite de pas |
| **J** | I + **règle du blocage** : 150 pas sans rien de neuf = partie perdue (−50) | **94 / 79 % de victoires, salle bonus 95 / 78 %, champignon 98 / 95 %, fleur 98 / 95 %** | ✅ Solution retenue |

Choix du seuil de 150 pas : dans les parties gagnées, la plus longue pause « sans rien de neuf »
mesurée est de ~90 pas.

« Rien de neuf » veut dire : aucun de ces événements pendant le pas :
- nouvelle case la plus à droite ;
- changement de zone ;
- pièce, objet ou bloc ;
- ennemi vaincu ;
- rapprochement d'un objet visible.

**Preuve que la fleur est volontaire :** 90 à 98 % des appuis sur « gauche » ont lieu entre
les colonnes 33 et 37, juste devant le bloc de fleur.

### Configuration finale (dans le code, poussée)

- **Niveau `full_a`** :
  - bloc power-up normal en (34, 9) : champignon pour Mario petit ;
  - **bloc de fleur en (36, 9)** : il ne s'ouvre que pour Mario grand, rien pour Mario petit.
- **Boutons `right_down_left`** :
  - rien, droite, droite+saut, droite+course, droite+saut+course ;
  - bas ;
  - gauche, gauche+saut.
- **Récompense `route_a2`** (`stuck_steps=150`) :
  - pièce +10, salle bonus +200 ;
  - champignon ou fleur +150, bloc power-up +25, guidage +2 par case ;
  - −0,5 par seconde du chrono, mort ou blocage −50, drapeau +100.

## 7. Résultats finaux de la Route A (Mac M4, 5 graines, 3 M de pas, variante B)

Commande lancée par l'utilisateur :

```bash
python train.py --algo ppo --level full_a --obs vector_plus \
    --actions right_down_left --reward route_a2 --ent-coef 0.01 \
    --steps 3000000 --seeds 42 43 44 45 46 --carbon --variant B \
    --log-steps 250000
```

Les 4 dernières colonnes portent sur les 500 dernières parties de l'entraînement.

| Graine | Victoires | Salle bonus | Pièces | Champignon | Fleur | Robustesse | Test glouton | Bloquées | Morts |
|---|---|---|---|---|---|---|---|---|---|
| 42 | 87,4 % | 90,4 % | 17,1 | 97,6 % | 91,4 % | 66 % | gagné, 295 pas, 19 pièces | 4,6 % | 8,0 % |
| 43 | 89,8 % | 92,0 % | 18,3 | 95,6 % | 93,6 % | 78 % | gagné, 291 pas, 21 pièces | 3,2 % | 7,0 % |
| 44 | 95,8 % | 96,2 % | 17,7 | 98,2 % | 97,8 % | 78 % | gagné, 346 pas, 20 pièces | 1,2 % | 2,8 % |
| 45 | 93,6 % | 95,6 % | 17,7 | 99,2 % | 96,6 % | 92 % | gagné, 300 pas, 19 pièces | 0,2 % | 6,2 % |
| 46 | 89,4 % | 95,0 % | 18,5 | 95,8 % | 85,8 % | 88 % | gagné, 283 pas, 20 pièces | 2,2 % | 8,4 % |
| **Moyenne** | **91,2 ± 3,4 %** | **93,8 %** | **17,9** | **97,3 %** | **93,0 %** | **80,4 ± 10,1 %** | **5 / 5 gagnés** (salle bonus + champignon + fleur) | 2,3 % | 6,5 % |

- **Test glouton** = une partie sans hasard. Les 5 sont gagnées par la salle bonus, avec champignon et fleur.
- **Robustesse** = 50 parties avec 2 % de boutons au hasard.
- **Coût mesuré par CodeCarbon :** 12,6 min pour les 5 graines lancées en parallèle (757 s), 5,6 Wh au total (~1,1 Wh par graine) et 0,31 g de CO₂. C'est la mesure de toute la machine pour le run entier.
- **Comparaison avec le PPO « article » sur v3 :** la route A gagne plus souvent (91 % contre 81 %) et elle est plus robuste (80 % contre 60 %), tout en faisant le détour.

## 8. Où on en est / ce qui reste à faire

| Fait | À faire (non commencé) |
|---|---|
| Code, tests (103 verts), README à jour pour la route A (commande et essai cloud) | Vérifier rapidement les 5 modèles `models/ppo_nes_full_a_s4*_3m_b` (relecture des `meta.json` faite, chiffres ci-dessus) |
| 5 modèles finaux entraînés sur le Mac et poussés (commit `1613f97`) | Ajouter une **section 8 « Route A »** dans `docs/RESULTATS.md` et une ligne dans `docs/resultats_v3.csv` avec ces chiffres |
| | Mettre à jour le paragraphe « Essai dans le cloud » du README avec les résultats du Mac |
| | Idées possibles si l'utilisateur le demande : lancer des boules de feu (bouton B déjà dans les actions avec la course), tuer plus d'ennemis (contradictoire avec le raccourci), comparer avec/sans bouton gauche |

## 9. Commandes utiles

```bash
python -m pytest -q                         # 103 tests
python play.py                              # menu ; MODELES -> PPO pour regarder un modèle
python train.py --help                      # toutes les options
# essai pilote dans le cloud (2 graines, 2 M de pas)
MARIO_MODELS_DIR=/chemin/temporaire python train.py --algo ppo --level full_a \
    --obs vector_plus --actions right_down_left --reward route_a2 --ent-coef 0.01 \
    --steps 2000000 --seeds 42 --variant X --log-steps 250000
```

Ordres de grandeur pour la route A :
- **Cloud :** environ 1640 pas/s par graine, avec 2 graines en parallèle sur 4 cœurs, soit ~21 min pour 2 M de pas.
- **Mac M4 :** 3 M de pas × 5 graines en 12,6 min.

## 10. Pièges connus

- Le conteneur cloud peut redémarrer et tuer les entraînements en arrière-plan. Pour les pilotes, mieux vaut des boucles d'attente de moins de 10 minutes.
- Éviter `pkill -f` : il a déjà tué son propre shell.
- Dans le moteur, `p.status` vaut 0 pour petit, 1 pour grand et 2 pour feu. Dans `info["status"]`, ces états s'appellent `small`, `tall` et `fireball`.
- Option de départ varié (`--start-col`, `--start-prob`, `--start-big`) : elle ne s'applique qu'à l'entraînement. Les tests partent toujours du début.
- Avant la règle du blocage, un « temps écoulé » en test glouton voulait souvent dire que Mario était bloqué. Maintenant, le verdict « bloqué (150 pas sans rien de neuf) » s'affiche.
