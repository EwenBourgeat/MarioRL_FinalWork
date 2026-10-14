# Oral final : ce qu'on dit

Pour chaque diapo : ce qu'on voit à l'écran, les phrases à dire, puis la phrase pour passer à la suivante.
Durée prévue : 18 min 55 s (entre parenthèses, le temps de chaque diapo).

Conseils : parler lentement, montrer l'écran du doigt, et lancer les vidéos quand c'est indiqué.

## Introduction

### Diapo 1 · Reinforcement learning  (0:20)

**À l'écran** : le titre, nos trois prénoms.

**On dit** :
- Bonjour à tous, nous sommes Chris, Ewen et Chloé.
- Notre sujet, c'est un article de recherche sorti en juin 2026 : il fait apprendre à des IA à jouer à Super Mario.
- On ne s'est pas contentés de le lire : on a refait le jeu, on a refait leurs expériences, et on est allés un peu plus loin.

> ➜ Voici notre parcours.

### Diapo 2 · Le parcours  (0:30)

**À l'écran** : les 4 mondes.

**On dit** :
- On a découpé la présentation en 4 parties, comme les mondes du jeu.
- Monde 1-1 : ce que dit l'article, et ce qu'on en pense.
- Monde 1-2 : on compare les algorithmes sur le même niveau.
- Monde 1-3 : on passe au vrai jeu NES.
- Monde 1-4 : on prend du recul, avec l'énergie consommée et nos limites.

> ➜ On commence par l'article.

## Monde 1-1 : la veille

### Diapo 3 · World 1-1  (0:05)

**On dit** :
- Premier monde : la veille, c'est-à-dire l'article.

### Diapo 4 · Le niveau 1-1 est-il une vraie leçon ?  (0:50)

**À l'écran** : la référence de l'article et ses deux questions.

**On dit** :
- Beaucoup de gens disent que le premier niveau de Mario est très bien fait : il apprend au joueur à jouer, petit à petit.
- Les auteurs veulent le vérifier avec des IA.
- Première question : quel algorithme apprend le mieux ce niveau ?
- Deuxième question : est-ce que l'ordre du niveau aide l'IA à apprendre plus vite ?
- Ils font 120 entraînements au total.
- Attention : c'est une prépublication. L'article n'a pas encore été relu par d'autres chercheurs.

> ➜ Pour comprendre d'où il vient, voici une petite frise.

### Diapo 5 · D'où vient l'article  (0:30)

**À l'écran** : la frise de 1992 à 2026.

**On dit** :
- L'article réutilise des méthodes connues : Q-Learning en 1992, DQN en 2015, PPO en 2017.
- Il s'appuie aussi sur une idée de 2009 : on apprend mieux en allant du plus facile au plus difficile.
- Ce qui est nouveau, c'est d'utiliser ces IA pour juger si un niveau de jeu est bien construit.

> ➜ Voyons maintenant le terrain de jeu.

### Diapo 6 · Le terrain et les 4 algorithmes  (1:15)

**À l'écran** : le niveau en entier, puis les 4 algorithmes.

**On dit** :
- Le niveau est découpé en une grille de cases. Mario avance case par case.
- Il n'a que 3 boutons : ne rien faire, avancer, sauter.
- Il gagne des points : +100 au drapeau, -50 s'il meurt, et un peu à chaque pas vers la droite.
- Il existe 3 versions du niveau. La plus difficile, la v3, a 17 ennemis. C'est celle qu'on étudie.
- Quatre algorithmes s'affrontent.
- Q-Learning et SARSA apprennent à chaque pas. SARSA est un peu plus prudent.
- Monte Carlo attend la fin de la partie pour apprendre.
- Ces trois-là remplissent un grand tableau de notes : une note pour chaque situation et chaque bouton.
- DQN, lui, utilise un réseau de neurones à la place du tableau.

> ➜ Qu'est-ce que l'article a trouvé ?

### Diapo 7 · Ce que trouve l'article  (1:15)

**À l'écran** : à gauche le classement, à droite l'effet de l'ordre.

**On dit** :
- À gauche : sur la v3, Monte Carlo gagne le plus souvent, presque 95 % des parties.
- DQN est le dernier, avec 76 %.
- À droite : les auteurs coupent le niveau en 6 morceaux et changent leur ordre.
- Avec l'ordre normal, Monte Carlo gagne 94,7 % des parties.
- Avec l'ordre inversé, il tombe à 48,5 %.
- Leur conclusion : l'ordre du niveau 1-1 aide vraiment à apprendre.

> ➜ On a lu l'article avec un œil critique.

### Diapo 8 · Notre lecture critique  (1:00)

**À l'écran** : forces, erreurs, faiblesses.

**On dit** :
- Ce qui est bien : la question est originale, et ils ont codé tout le jeu eux-mêmes.
- Mais on a trouvé des erreurs. Par exemple, le texte donne 94,7 % pour l'ordre inversé, alors que leur propre tableau dit 48,5 %.
- Il y a aussi des faiblesses : ils testent seulement 10 ordres sur 720 possibles, et ils ne publient pas leur code.
- Et surtout : si une IA apprend vite, ça ne prouve pas qu'un humain apprend vite aussi.

> ➜ C'est pour ça qu'on a voulu vérifier nous-mêmes.

## Monde 1-2 : le duel sur v3

### Diapo 9 · World 1-2  (0:05)

**On dit** :
- Deuxième monde : le duel des algorithmes sur la v3.

### Diapo 10 · Le même protocole pour tous  (1:00)

**À l'écran** : notre jeu, et les 4 règles du protocole.

**On dit** :
- D'abord, on a refait le niveau 1-1 en Python, avec la même physique que sur la console NES.
- Ensuite, on a donné exactement les mêmes conditions à tous les algorithmes.
- Même niveau, la v3. Même durée : 6000 parties. Et 5 essais avec des tirages au hasard différents : on appelle ça des graines.
- On a ajouté un test : 50 parties où on appuie au hasard sur 2 % des boutons. On l'appelle le test de robustesse.
- C'est le même test pour tout le monde, donc c'est le plus juste pour comparer.

> ➜ Commençons par les trois méthodes à tableau.

### Diapo 11 · Les méthodes à tableau apprennent vite  (1:15)

**À l'écran** : la vidéo (à lancer), et les 3 scores.

**On dit** :
- (Lancer la vidéo.) Ici, c'est la même IA, Q-Learning, filmée à 4 moments de son apprentissage.
- Au début, elle tombe dans le premier trou. Puis dans le deuxième. Puis elle meurt presque à la fin.
- Après 6000 parties, elle atteint le drapeau.
- Les trois méthodes à tableau gagnent entre 94 et 96 % des parties.
- Détail amusant : Monte Carlo attend que les Goombas arrivent pour leur sauter dessus. Ses parties durent deux fois plus longtemps.

> ➜ Et DQN, alors ?

### Diapo 12 · DQN : de 40 % à 94 % de victoires  (1:30)

**À l'écran** : la vidéo (à lancer), et le graphique des étapes.

**On dit** :
- (Lancer la vidéo.) Quand on refait le DQN de l'article, il gagne seulement 40 % des parties, contre 76 % dans l'article.
- Dans la vidéo, il meurt colonne 154. Notre version, elle, atteint le drapeau.
- Pourquoi ? Le DQN de l'article ne voit presque rien : 4 lignes de l'écran et son numéro de case. Il ne voit même pas les trous.
- On l'a donc amélioré étape par étape, avec l'aide de Claude, une IA qui aide à coder.
- La grande amélioration, c'est de lui montrer tout l'écran : +38 points d'un coup.
- Les autres changements n'apportent presque rien. Les derniers réglages le rendent juste plus stable : 94,5 %.
- Ce qu'on retient : ce que l'IA voit compte plus que la taille de son réseau.

> ➜ On met maintenant tout le monde dans un seul tableau.

### Diapo 13 · Le tableau final  (1:30)

**À l'écran** : le tableau final.

**On dit** :
- Chaque ligne est un algorithme, et chaque chiffre est une moyenne sur 5 essais.
- La colonne la plus importante, c'est la robustesse, parce que c'est le même test pour tous.
- Les trois méthodes à tableau sont à 88,8 %.
- Notre DQN est à 94,4 % : c'est le plus robuste, et c'est aussi celui qui apprend le plus vite.
- Le DQN de l'article est loin derrière.
- Par rapport à l'article, on retrouve les mêmes tendances. Nos scores sont un peu plus hauts, sûrement parce que nos ennemis sont plus faciles à écraser.

> ➜ Tout ça, c'était sur une version simplifiée du jeu. Passons au vrai jeu.

## Monde 1-3 : le vrai jeu NES

### Diapo 14 · World 1-3  (0:05)

**On dit** :
- Troisième monde : le vrai jeu NES.

### Diapo 15 · Passer au vrai jeu : PPO  (1:00)

**À l'écran** : la grille comparée au vrai jeu, et PPO.

**On dit** :
- Dans l'article, le jeu est simplifié : Mario avance d'une case à la fois, et son saut est toujours le même.
- Dans le vrai jeu, Mario prend de l'élan, peut courir, et son saut dépend de sa vitesse.
- Une méthode à tableau n'y arrive plus : elle plafonne autour de 35 % de victoires.
- On a donc utilisé PPO, un algorithme publié par OpenAI en 2017.
- PPO a deux parties : un « acteur » qui choisit le bouton, et un « critique » qui juge si la situation est bonne.
- Ses réglages ont aussi été optimisés avec Claude.

> ➜ Voyons ce que ça donne.

### Diapo 16 · PPO gagne 81 % des parties  (1:15)

**À l'écran** : la vidéo (à lancer), et les 4 chiffres.

**On dit** :
- (Lancer la vidéo.) Voici PPO qui joue au vrai jeu, sans aucun hasard.
- Il gagne 81 % des parties pendant son entraînement.
- Quand on l'empêche de jouer au hasard, il gagne à chaque fois, avec les 5 graines.
- Il lui faut environ 11 minutes d'entraînement par graine.
- Son point faible : la robustesse, 60 %. Si on change un bouton au hasard, il a du mal à se rattraper.

> ➜ On a ensuite essayé de le faire jouer comme un vrai joueur.

### Diapo 17 · Route A : jouer comme un humain  (1:45)

**À l'écran** : la vidéo (à lancer), les 4 chiffres, et le tableau des corrections.

**On dit** :
- (Lancer la vidéo.) On a voulu que l'IA joue comme un humain qui connaît le jeu.
- Elle doit prendre le champignon, puis la fleur, passer par le tuyau secret et ramasser les pièces de la salle cachée.
- On a appris une leçon importante : l'IA fait ce qu'on récompense, pas ce qu'on veut.
- Par exemple, elle restait dans la salle cachée jusqu'à la fin du temps. On a donc ajouté une pénalité de temps.
- Elle restait aussi bloquée contre un tuyau. On a ajouté une règle : si rien ne se passe pendant trop longtemps, la partie est perdue.
- Il a fallu une dizaine d'essais pour trouver les bons réglages.
- Résultat : elle gagne 91 % des parties, et prend le champignon et la fleur presque à chaque fois.

> ➜ Dernier monde : on prend du recul.

## Monde 1-4 : le recul

### Diapo 18 · World 1-4  (0:05)

**On dit** :
- Quatrième monde : le recul.

### Diapo 19 · L'énergie consommée  (1:15)

**À l'écran** : le tableau des coûts et 3 chiffres.

**On dit** :
- On a mesuré l'énergie consommée avec un outil qui s'appelle CodeCarbon.
- Une méthode à tableau s'entraîne en 16 secondes. Ça consomme presque rien.
- Notre DQN consomme 88 fois plus qu'un Q-Learning.
- Au total, tous nos entraînements font 113 wattheures. C'est à peu près l'énergie pour faire bouillir un litre d'eau.
- Mais un seul test, le gros réseau sur carte graphique, représente 75 % de ce total. Et il donnait un moins bon résultat.
- Ce qu'on retient : un modèle plus gros n'est pas forcément meilleur.

> ➜ Maintenant, nos propres limites.

### Diapo 20 · Notre auto-critique  (1:15)

**À l'écran** : nos limites, l'usage de l'IA, ce qu'on ferait ensuite.

**On dit** :
- Notre travail a des limites. On a fait 6000 parties au lieu de 10 000, pour que tout tourne sur un ordinateur portable.
- On n'a pas refait l'expérience sur l'ordre du niveau.
- On a dû deviner les règles des ennemis, car l'article ne les donne pas.
- Notre DQN a été réglé et testé sur les mêmes graines, ce qui l'avantage un peu.
- L'énergie est estimée, pas mesurée par un vrai capteur.
- Sur l'IA comme outil : Claude nous a fait gagner beaucoup de temps, mais on a vérifié chaque choix.
- Avec plus de temps, on referait l'expérience de l'ordre, et on testerait avec de vrais joueurs.

> ➜ Pour finir, ce qu'on retient.

### Diapo 21 · Ce qu'on retient  (1:00)

**À l'écran** : 3 messages.

**On dit** :
- Un : sur un niveau simple, les méthodes à tableau suffisent. 95 % de victoires en 16 secondes.
- Deux : ce que voit l'IA compte plus que la taille du réseau. Notre DQN passe de 40 à 94 %.
- Trois : sur le vrai jeu, il faut des réseaux de neurones, et c'est la récompense qui décide du comportement.
- Sur l'article : ses grandes idées tiennent, mais ses chiffres dépendent de détails qu'il ne publie pas.

## Fin

### Diapo 22 · Merci pour votre écoute  (0:10)

**On dit** :
- Merci pour votre écoute.

### Diapo 23 · Avez-vous des questions ?

Questions probables, avec une réponse courte :
- Pourquoi le DQN de l'article échoue-t-il ? Il ne voit presque rien de l'écran, donc il doit apprendre le niveau par cœur.
- Pourquoi Monte Carlo attend-il les Goombas ? Quand il gagne une partie, il récompense tous les coups joués, même les attentes.
- Pourquoi DQN ne sent pas l'ordre du niveau ? Il apprend sur des souvenirs tirés au hasard : pour lui, l'ordre des parties disparaît.
- Est-ce que votre travail change la conclusion de l'article ? Les tendances tiennent, mais un DQN qui voit tout l'écran devient le meilleur.
- Pourquoi vos chiffres sont-ils différents ? Moins de parties (6000), et des règles d'ennemis que l'article ne précise pas.
- Pourquoi regarder la robustesse ? C'est le seul test identique pour tous les algorithmes.

## Annexes (seulement si le jury pose une question)

### Diapo 24 · Comportement en jeu

Annexe : à montrer si le jury demande pourquoi nos retours sont plus élevés que ceux de l'article.

### Diapo 25 · Les réglages

Annexe : réglages de l'article et de notre DQN.

### Diapo 26 · Ce que voit le DQN de l'article

Annexe : pourquoi le DQN de l'article apprend le niveau par cœur.

### Diapo 27 · Notre DQN, étape par étape

Annexe : détail de l'étude étape par étape de notre DQN.

### Diapo 28 · PPO par graine

Annexe : détail de PPO par graine.

### Diapo 29 · Route A : les réglages

Annexe : réglages de la Route A.

### Diapo 30 · Références

Annexe : références citées.
