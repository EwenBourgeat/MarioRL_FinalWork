# Oral final : notes de l'orateur

Texte à dire pour chaque diapo de `Oral_RL_Mario.pptx`, avec la durée visée entre crochets (environ 19 minutes pour les diapos 1 à 21). Les mêmes notes sont dans le PowerPoint.

Durée totale des diapos minutées : 18 min 50 s.

## Diapo 1 : REINFORCEMENT LEARNING

[0:20] Bonjour à tous. Nous sommes Chris, Ewen et Chloé. Notre veille porte sur un article publié en juin 2026 : « Reinforcement Learning in Super Mario Bros », de Ponnock et Ho. On ne s'est pas contentés de le lire : on a recréé le niveau 1-1, on a refait leurs expériences, puis on est allés plus loin, jusqu'au vrai jeu NES.

## Diapo 2 : LE PARCOURS

[0:30] Notre parcours suit quatre mondes, comme dans le jeu.
Monde 1-1 : la veille, c'est-à-dire l'article, ses résultats et notre lecture critique.
Monde 1-2 : le duel des algorithmes sur le niveau v3, avec notre tableau final.
Monde 1-3 : le vrai jeu NES, où nos meilleurs modèles jouent avec la vraie physique.
Monde 1-4 : le recul, avec l'énergie consommée, notre auto-critique et la conclusion.

## Diapo 3 : WORLD 1-1

[0:05] Commençons par la veille : l'article.

## Diapo 4 : L'ARTICLE

[1:15] L'article part d'une idée connue des game designers : le niveau 1-1 serait une leçon cachée. Il commence par un sol plat et un seul ennemi, introduit ensuite les tuyaux et les trous, et garde les groupes d'ennemis pour la fin.
Les auteurs, de Johns Hopkins, se demandent si on peut le mesurer avec des IA. Deux questions : quel algorithme apprend le mieux ce niveau, et est-ce que ça dépend de sa difficulté ? Et est-ce que l'ordre d'origine des morceaux du niveau accélère l'apprentissage ? En tout, 120 entraînements.
Pour situer l'article (frise en bas) : il s'appuie sur des méthodes classiques, Q-Learning, SARSA, DQN, et sur le curriculum learning de Bengio en 2009, l'idée qu'on apprend mieux du plus simple au plus difficile. Attention : c'est une prépublication arXiv, pas encore relue par des pairs.

## Diapo 5 : LE TERRAIN ET LES JOUEURS

[1:15] Le terrain : le niveau est une grille de 212 colonnes sur 14 lignes, en trois versions : v1 avec le terrain seul, v2 avec les blocs, v3 avec 17 ennemis. C'est la v3 qui nous intéresse.
Mario n'a que trois boutons : rien, avancer, sauter. Les récompenses : +100 au drapeau, -50 à la mort, +0,5 par pas vers la droite, plus des bonus pour les blocs et les Goombas.
Quatre joueurs s'affrontent. Q-Learning et SARSA corrigent leur tableau de notes à chaque pas ; SARSA tient compte du coup qu'il va vraiment jouer, hasard compris, donc il est plus prudent. Monte Carlo attend la fin de la partie pour tout corriger d'un coup. DQN remplace le tableau par un réseau de neurones, avec une mémoire des 50 000 derniers coups.

## Diapo 6 : CE QUE TROUVE L'ARTICLE

[1:15] Sur la v3, Monte Carlo gagne : près de 95 % de victoires, devant Q-Learning, SARSA, et DQN à 76 %. DQN s'effondre en v1 (10 %) puis remonte à 93 % en v2 : sans blocs à frapper, il ne reçoit presque que des morts. Les auteurs parlent de densité de récompense.
Deuxième question : l'ordre. Ils découpent la v3 en 6 morceaux et les mélangent. Avec l'ordre d'origine, Monte Carlo atteint 94,7 % ; avec l'ordre inversé, 48,5 %, et 4 entraînements sur 10 échouent complètement. Pour DQN, l'ordre ne change rien : sa mémoire mélange toutes les parties.
Leur conclusion : le 1-1 a une vraie structure pédagogique.

## Diapo 7 : NOTRE LECTURE CRITIQUE

[1:00] Notre lecture critique. De vraies forces : une question originale, un environnement codé de zéro, et une expérience de contrôle avec DQN qui isole bien le rôle de la mémoire.
Mais on a relevé cinq erreurs factuelles. Exemple : le texte donne 94,7 % pour l'ordre inversé, alors que leur propre tableau dit 48,5 %.
Et des faiblesses de méthode : 10 ordres testés sur 720 possibles, des effectifs inégaux, un effet géant (d = 7) calculé sur 5 graines, aucun code publié.
Surtout : une IA qui apprend plus vite ne prouve pas qu'un humain apprend mieux. C'est pour ça qu'on a voulu vérifier par nous-mêmes.

## Diapo 8 : WORLD 1-2

[0:05] Place au duel sur la v3.

## Diapo 9 : NOTRE MARIO, NOTRE PROTOCOLE

[1:00] Pour vérifier, il fallait le jeu. On a recréé le niveau 1-1 en Python, avec la physique NES au sous-pixel près ; la carte et les ennemis sont vérifiés case par case contre les données du jeu d'origine. Deux environnements : la grille de l'article et le vrai jeu. Un menu permet de regarder jouer nos IA.
Ensuite le protocole : pour une comparaison juste, tous les algorithmes ont eu les mêmes conditions : v3, 6000 épisodes, 5 graines, la même machine, l'énergie mesurée avec CodeCarbon.
On a ajouté deux tests absents de l'article : une partie sans aucun hasard, et un test de robustesse, 50 parties avec 2 % de boutons au hasard. Le même pour tout le monde.

## Diapo 10 : LES TABLEAUX APPRENNENT VITE

[1:15] (Lancer la vidéo.) Voici la même IA, Q-Learning, à quatre moments de son entraînement. Épisode 100 : elle tombe dans le premier trou. Épisode 1000 : dans le deuxième. Épisode 2200 : elle meurt presque au bout. Épisode 6000 : drapeau.
Les trois méthodes à tableau gagnent 94 à 96 % des parties, et réussissent toutes la partie sans hasard.
Elles n'ont pas le même style : Monte Carlo met presque deux fois plus de pas, parce qu'il attend que les Goombas arrivent pour leur sauter dessus. C'est sa logique : dans une partie gagnée, tous les coups sont récompensés, même les attentes inutiles. Et c'est une stratégie sûre : il meurt peu.

## Diapo 11 : DQN : DE 40 % À 94 %

[1:30] (Lancer la vidéo.) Le DQN de l'article, lui, échoue chez nous : 40 % de victoires au lieu de 76. Sur la même graine, il meurt colonne 154, le nôtre atteint le drapeau.
Pourquoi ? Le DQN de l'article ne voit que 4 lignes de l'écran et son numéro de colonne : ni les trous, ni le sens des ennemis. Il doit apprendre le niveau par cœur.
On a donc amélioré DQN étape par étape, avec l'aide de Claude, un assistant d'IA, en mesurant chaque étape. Ce qui change tout, c'est la vue complète : +38 points. Les améliorations connues de DQN ou un réseau convolutif n'apportent rien de plus. Les derniers réglages apportent la stabilité : 94,5 %.

## Diapo 12 : LE TABLEAU FINAL

[1:30] Le tableau final, sur 5 graines. Attention à la 1re colonne : les victoires sont mesurées pendant l'entraînement, avec une part de hasard différente selon l'algorithme. La colonne à comparer, c'est la robustesse, le même test pour tous.
Les trois tableaux sont à 88,8 %, notre DQN à 94,4 % : le plus robuste, le plus rapide à atteindre 80 %, celui qui marque le plus de points. Le DQN de l'article est loin derrière et très instable d'une graine à l'autre.
Face à l'article : les tendances tiennent (Monte Carlo au moins aussi bon que les autres, leur DQN sous les tableaux), mais nos victoires sont plus hautes : l'article ne précise pas les règles des ennemis, et nos agents en écrasent 2 à 4 fois plus.

## Diapo 13 : WORLD 1-3

[0:05] Et maintenant, le vrai jeu.

## Diapo 14 : PASSER AU VRAI JEU

[1:00] La grille de l'article simplifie énormément : un pas égale une case, le saut est toujours le même. Dans le vrai jeu, Mario a de l'élan, il accélère, il peut courir, et son saut dépend de sa vitesse. Un tableau ne peut plus tout retenir case par case : un Q-Learning de l'article plafonne vers 35 %.
Il faut une IA qui généralise. On a choisi PPO, publié par OpenAI en 2017 : un acteur donne la probabilité de chaque bouton, un critique juge si la situation est bonne, et il s'améliore par petits pas, d'où « proximal ». Comme pour DQN, ses réglages ont été optimisés avec Claude.

## Diapo 15 : PPO SUR LE VRAI NIVEAU

[1:15] (Lancer la vidéo.) Sur le vrai niveau, PPO gagne 81 % des parties, et la partie sans hasard est gagnée par les 5 graines. Il apprend en 3 millions de pas, environ 9 500 parties, en 11 minutes par graine.
La courbe plafonne vers 80 % dès 2 millions de pas : pendant l'entraînement, il tire ses boutons au sort. Son point faible, c'est la robustesse, 60 % : quand on perturbe un bouton, il rattrape mal l'erreur.
Ces chiffres ne se comparent pas directement à la grille : le vrai jeu est beaucoup plus difficile.

## Diapo 16 : ROUTE A : JOUER COMME UN HUMAIN

[1:45] (Lancer la vidéo.) Pour finir, on a voulu que l'IA joue comme un humain qui connaît le jeu : champignon, fleur, tuyau secret et pièces de la salle bonus.
Leçon la plus importante du projet : l'IA fait ce qu'on récompense, pas ce qu'on veut. Elle restait dans la salle bonus jusqu'à la fin du temps. Elle appuyait 866 fois sur « bas » devant la sortie. Elle restait collée à un tuyau en tenant droite et saut. À chaque fois, il a fallu corriger la récompense ou ce qu'elle voit : une dizaine de variantes en tout.
Résultat : 91 % de victoires, la salle bonus dans 94 % des parties, le champignon et la fleur dans plus de 93 %. Dans la vidéo, sans aucun hasard, elle fait tout le parcours.

## Diapo 17 : WORLD 1-4

[0:05] Dernier monde : prendre du recul.

## Diapo 18 : L'ÉNERGIE CONSOMMÉE

[1:15] Combien tout cela coûte-t-il ? Mesuré avec CodeCarbon, une graine de Q-Learning, c'est 16 secondes et 0,03 Wh, une ampoule LED allumée 10 secondes. Notre DQN consomme 88 fois plus, pour 5 points de robustesse en plus.
Au total, tous nos entraînements finaux font 113 Wh : l'énergie pour faire bouillir un litre d'eau, environ 7 charges de smartphone, 6 grammes de CO2 avec l'électricité française.
C'est peu. Mais une seule expérience, le réseau convolutif sur carte graphique, représente 75 % de ce total, pour un moins bon résultat. Plus gros n'est pas mieux.

## Diapo 19 : NOTRE AUTO-CRITIQUE

[1:15] Notre auto-critique. Nos limites : 6000 épisodes au lieu de 10 000, pour tout faire tourner sur un portable. Nous n'avons pas refait l'expérience sur l'ordre du niveau. Les règles des ennemis sont devinées, ce qui gonfle nos scores. Notre DQN a été réglé sur les graines 42 et 43, gardées ensuite pour l'évaluer, et on garde sa meilleure version, ce qui l'avantage au test de robustesse. L'énergie est estimée, pas mesurée par un capteur. La Route A est façonnée à la main.
L'IA comme outil : Claude nous a fait gagner énormément de temps sur DQN et PPO, mais il fallait comprendre et vérifier chaque choix ; c'est pour ça qu'on a avancé étape par étape.
Avec plus de temps : refaire l'expérience de l'ordre avec Q-Learning et SARSA, et tester avec de vrais joueurs.

## Diapo 20 : CE QU'ON RETIENT

[1:00] Trois choses à retenir. Un : sur un niveau discret, les méthodes à tableau suffisent, 95 % en 16 secondes, reproductible à l'identique. Deux : ce que voit l'IA compte plus que la taille du réseau, notre DQN passe de 40 à 94 % grâce à la vue complète. Trois : sur le vrai jeu, le deep learning prend le relais, et c'est la récompense qui décide du comportement.
Et pour l'article : ses grandes tendances tiennent, mais ses chiffres dépendent de détails qu'il ne publie pas.

## Diapo 21 : MERCI POUR VOTRE ÉCOUTE

[0:10] Merci pour votre écoute.

## Diapo 22 : AVEZ-VOUS DES QUESTIONS ?

Questions probables (réponses courtes) :
- Pourquoi DQN échoue en v1 ? Récompenses rares : sa mémoire se remplit de morts (-50), il ne voit presque jamais de coups positifs.
- Pourquoi Monte Carlo prend plus de blocs et attend les Goombas ? Il crédite tous les coups d'une partie gagnée avec le score final, y compris les détours et les attentes.
- Pourquoi la mémoire de rejeu efface l'effet de l'ordre ? DQN apprend sur des souvenirs tirés au hasard parmi 50 000 : une partie de l'épisode 1 et une de l'épisode 5000 se ressemblent pour lui.
- Notre travail change-t-il la conclusion de l'article ? Les tendances tiennent, mais « DQN est moins bon » dépend surtout de ce qu'on lui montre (vue complète : 94 %).
- Pourquoi nos chiffres diffèrent ? 6000 épisodes au lieu de 10 000, règles des ennemis non précisées, détails du DQN absents.
- Pourquoi la robustesse plutôt que les victoires ? Les victoires sont mesurées avec des parts de hasard différentes (1 %, 2 %, 5 %) ; la robustesse est le même test pour tous.

## Diapo 23 : COMPORTEMENT EN JEU

Annexe : à montrer si le jury demande pourquoi nos retours sont plus élevés que ceux de l'article.

## Diapo 24 : LES RÉGLAGES

Annexe : réglages de l'article et de notre DQN.

## Diapo 25 : CE QUE VOIT LE DQN DE L'ARTICLE

Annexe : pourquoi le DQN de l'article apprend le niveau par cœur.

## Diapo 26 : NOTRE DQN, ÉTAPE PAR ÉTAPE

Annexe : détail de l'étude étape par étape de notre DQN.

## Diapo 27 : PPO PAR GRAINE

Annexe : détail de PPO par graine.

## Diapo 28 : ROUTE A : LES RÉGLAGES

Annexe : réglages de la Route A.

## Diapo 29 : RÉFÉRENCES

Annexe : références citées.
