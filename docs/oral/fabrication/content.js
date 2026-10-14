// Contenu de l'oral (chiffres, textes, notes de l'orateur).
// Sources : docs/RESULTATS.md, docs/resultats_v3.csv, models/*/meta.json,
// l'article (Ponnock & Ho, 2026) et la page Craft du projet.

// Notes de l'orateur : phrases courtes, comme un élève qui explique à des
// débutants. Format : [durée], « À l'écran : », « On dit : » + tirets,
// « Transition : ». export_notes.py en fait Notes_oral.md.
const NOTES = {
  title: `[0:20]
À l'écran : le titre, nos trois prénoms.
On dit :
- Bonjour à tous, nous sommes Chris, Ewen et Chloé.
- Notre sujet, c'est un article de recherche sorti en juin 2026 : il fait apprendre à des IA à jouer à Super Mario.
- On ne s'est pas contentés de le lire : on a refait le jeu, on a refait leurs expériences, et on est allés un peu plus loin.
Transition : Voici notre parcours.`,

  agenda: `[0:30]
À l'écran : les 4 mondes.
On dit :
- On a découpé la présentation en 4 parties, comme les mondes du jeu.
- Monde 1-1 : ce que dit l'article, et ce qu'on en pense.
- Monde 1-2 : on compare les algorithmes sur le même niveau.
- Monde 1-3 : on passe au vrai jeu NES.
- Monde 1-4 : on prend du recul, avec l'énergie consommée et nos limites.
Transition : On commence par l'article.`,

  d1: `[0:05]
On dit :
- Premier monde : la veille, c'est-à-dire l'article.`,

  article: `[0:50]
À l'écran : la référence de l'article et ses deux questions.
On dit :
- Beaucoup de gens disent que le premier niveau de Mario est très bien fait : il apprend au joueur à jouer, petit à petit.
- Les auteurs veulent le vérifier avec des IA.
- Première question : quel algorithme apprend le mieux ce niveau ?
- Deuxième question : est-ce que l'ordre du niveau aide l'IA à apprendre plus vite ?
- Ils font 120 entraînements au total.
- Attention : c'est une prépublication. L'article n'a pas encore été relu par d'autres chercheurs.
Transition : Pour comprendre d'où il vient, voici une petite frise.`,

  veille: `[0:30]
À l'écran : la frise de 1992 à 2026.
On dit :
- L'article réutilise des méthodes connues : Q-Learning en 1992, DQN en 2015, PPO en 2017.
- Il s'appuie aussi sur une idée de 2009 : on apprend mieux en allant du plus facile au plus difficile.
- Ce qui est nouveau, c'est d'utiliser ces IA pour juger si un niveau de jeu est bien construit.
Transition : Voyons maintenant le terrain de jeu.`,

  terrain: `[1:15]
À l'écran : le niveau en entier, puis les 4 algorithmes.
On dit :
- Le niveau est découpé en une grille de cases. Mario avance case par case.
- Il n'a que 3 boutons : ne rien faire, avancer, sauter.
- Il gagne des points : +100 au drapeau, -50 s'il meurt, et un peu à chaque pas vers la droite.
- Il existe 3 versions du niveau. La plus difficile, la v3, a 17 ennemis. C'est celle qu'on étudie.
- Quatre algorithmes s'affrontent.
- Q-Learning et SARSA apprennent à chaque pas. SARSA est un peu plus prudent.
- Monte Carlo attend la fin de la partie pour apprendre.
- Ces trois-là remplissent un grand tableau de notes : une note pour chaque situation et chaque bouton.
- DQN, lui, utilise un réseau de neurones à la place du tableau.
Transition : Qu'est-ce que l'article a trouvé ?`,

  findings: `[1:15]
À l'écran : à gauche le classement, à droite l'effet de l'ordre.
On dit :
- À gauche : sur la v3, Monte Carlo gagne le plus souvent, presque 95 % des parties.
- DQN est le dernier, avec 76 %.
- À droite : les auteurs coupent le niveau en 6 morceaux et changent leur ordre.
- Avec l'ordre normal, Monte Carlo gagne 94,7 % des parties.
- Avec l'ordre inversé, il tombe à 48,5 %.
- Leur conclusion : l'ordre du niveau 1-1 aide vraiment à apprendre.
Transition : On a lu l'article avec un œil critique.`,

  critique: `[1:00]
À l'écran : forces, erreurs, faiblesses.
On dit :
- Ce qui est bien : la question est originale, et ils ont codé tout le jeu eux-mêmes.
- Mais on a trouvé des erreurs. Par exemple, le texte donne 94,7 % pour l'ordre inversé, alors que leur propre tableau dit 48,5 %.
- Il y a aussi des faiblesses : ils testent seulement 10 ordres sur 720 possibles, et ils ne publient pas leur code.
- Et surtout : si une IA apprend vite, ça ne prouve pas qu'un humain apprend vite aussi.
Transition : C'est pour ça qu'on a voulu vérifier nous-mêmes.`,

  d2: `[0:05]
On dit :
- Deuxième monde : le duel des algorithmes sur la v3.`,

  protocole: `[1:00]
À l'écran : notre jeu, et les 4 règles du protocole.
On dit :
- D'abord, on a refait le niveau 1-1 en Python, avec la même physique que sur la console NES.
- Ensuite, on a donné exactement les mêmes conditions à tous les algorithmes.
- Même niveau, la v3. Même durée : 6000 parties. Et 5 essais avec des tirages au hasard différents : on appelle ça des graines.
- On a ajouté un test : 50 parties où on appuie au hasard sur 2 % des boutons. On l'appelle le test de robustesse.
- C'est le même test pour tout le monde, donc c'est le plus juste pour comparer.
Transition : Commençons par les trois méthodes à tableau.`,

  tableaux: `[1:15]
À l'écran : la vidéo (à lancer), et les 3 scores.
On dit :
- (Lancer la vidéo.) Ici, c'est la même IA, Q-Learning, filmée à 4 moments de son apprentissage.
- Au début, elle tombe dans le premier trou. Puis dans le deuxième. Puis elle meurt presque à la fin.
- Après 6000 parties, elle atteint le drapeau.
- Les trois méthodes à tableau gagnent entre 94 et 96 % des parties.
- Détail amusant : Monte Carlo attend que les Goombas arrivent pour leur sauter dessus. Ses parties durent deux fois plus longtemps.
Transition : Et DQN, alors ?`,

  dqn: `[1:30]
À l'écran : la vidéo (à lancer), et le graphique des étapes.
On dit :
- (Lancer la vidéo.) Quand on refait le DQN de l'article, il gagne seulement 40 % des parties, contre 76 % dans l'article.
- Dans la vidéo, il meurt colonne 154. Notre version, elle, atteint le drapeau.
- Pourquoi ? Le DQN de l'article ne voit presque rien : 4 lignes de l'écran et son numéro de case. Il ne voit même pas les trous.
- On l'a donc amélioré étape par étape, avec l'aide de Claude, une IA qui aide à coder.
- La grande amélioration, c'est de lui montrer tout l'écran : +38 points d'un coup.
- Les autres changements n'apportent presque rien. Les derniers réglages le rendent juste plus stable : 94,5 %.
- Ce qu'on retient : ce que l'IA voit compte plus que la taille de son réseau.
Transition : On met maintenant tout le monde dans un seul tableau.`,

  tableau_final: `[1:30]
À l'écran : le tableau final.
On dit :
- Chaque ligne est un algorithme, et chaque chiffre est une moyenne sur 5 essais.
- La colonne la plus importante, c'est la robustesse, parce que c'est le même test pour tous.
- Les trois méthodes à tableau sont à 88,8 %.
- Notre DQN est à 94,4 % : c'est le plus robuste, et c'est aussi celui qui apprend le plus vite.
- Le DQN de l'article est loin derrière.
- Par rapport à l'article, on retrouve les mêmes tendances. Nos scores sont un peu plus hauts, sûrement parce que nos ennemis sont plus faciles à écraser.
Transition : Tout ça, c'était sur une version simplifiée du jeu. Passons au vrai jeu.`,

  d3: `[0:05]
On dit :
- Troisième monde : le vrai jeu NES.`,

  vrai_jeu: `[1:00]
À l'écran : la grille comparée au vrai jeu, et PPO.
On dit :
- Dans l'article, le jeu est simplifié : Mario avance d'une case à la fois, et son saut est toujours le même.
- Dans le vrai jeu, Mario prend de l'élan, peut courir, et son saut dépend de sa vitesse.
- Une méthode à tableau n'y arrive plus : elle plafonne autour de 35 % de victoires.
- On a donc utilisé PPO, un algorithme publié par OpenAI en 2017.
- PPO a deux parties : un « acteur » qui choisit le bouton, et un « critique » qui juge si la situation est bonne.
- Ses réglages ont aussi été optimisés avec Claude.
Transition : Voyons ce que ça donne.`,

  ppo: `[1:15]
À l'écran : la vidéo (à lancer), et les 4 chiffres.
On dit :
- (Lancer la vidéo.) Voici PPO qui joue au vrai jeu, sans aucun hasard.
- Il gagne 81 % des parties pendant son entraînement.
- Quand on l'empêche de jouer au hasard, il gagne à chaque fois, avec les 5 graines.
- Il lui faut environ 11 minutes d'entraînement par graine.
- Son point faible : la robustesse, 60 %. Si on change un bouton au hasard, il a du mal à se rattraper.
Transition : On a ensuite essayé de le faire jouer comme un vrai joueur.`,

  route_a: `[1:45]
À l'écran : la vidéo (à lancer), les 4 chiffres, et le tableau des corrections.
On dit :
- (Lancer la vidéo.) On a voulu que l'IA joue comme un humain qui connaît le jeu.
- Elle doit prendre le champignon, puis la fleur, passer par le tuyau secret et ramasser les pièces de la salle cachée.
- On a appris une leçon importante : l'IA fait ce qu'on récompense, pas ce qu'on veut.
- Par exemple, elle restait dans la salle cachée jusqu'à la fin du temps. On a donc ajouté une pénalité de temps.
- Elle restait aussi bloquée contre un tuyau. On a ajouté une règle : si rien ne se passe pendant trop longtemps, la partie est perdue.
- Il a fallu une dizaine d'essais pour trouver les bons réglages.
- Résultat : elle gagne 91 % des parties, et prend le champignon et la fleur presque à chaque fois.
Transition : Dernier monde : on prend du recul.`,

  d4: `[0:05]
On dit :
- Quatrième monde : le recul.`,

  energie: `[1:15]
À l'écran : le tableau des coûts et 3 chiffres.
On dit :
- On a mesuré l'énergie consommée avec un outil qui s'appelle CodeCarbon.
- Une méthode à tableau s'entraîne en 16 secondes. Ça consomme presque rien.
- Notre DQN consomme 88 fois plus qu'un Q-Learning.
- Au total, tous nos entraînements font 113 wattheures. C'est à peu près l'énergie pour faire bouillir un litre d'eau.
- Mais un seul test, le gros réseau sur carte graphique, représente 75 % de ce total. Et il donnait un moins bon résultat.
- Ce qu'on retient : un modèle plus gros n'est pas forcément meilleur.
Transition : Maintenant, nos propres limites.`,

  autocritique: `[1:15]
À l'écran : nos limites, l'usage de l'IA, ce qu'on ferait ensuite.
On dit :
- Notre travail a des limites. On a fait 6000 parties au lieu de 10 000, pour que tout tourne sur un ordinateur portable.
- On n'a pas refait l'expérience sur l'ordre du niveau.
- On a dû deviner les règles des ennemis, car l'article ne les donne pas.
- Notre DQN a été réglé et testé sur les mêmes graines, ce qui l'avantage un peu.
- L'énergie est estimée, pas mesurée par un vrai capteur.
- Sur l'IA comme outil : Claude nous a fait gagner beaucoup de temps, mais on a vérifié chaque choix.
- Avec plus de temps, on referait l'expérience de l'ordre, et on testerait avec de vrais joueurs.
Transition : Pour finir, ce qu'on retient.`,

  conclusion: `[1:00]
À l'écran : 3 messages.
On dit :
- Un : sur un niveau simple, les méthodes à tableau suffisent. 95 % de victoires en 16 secondes.
- Deux : ce que voit l'IA compte plus que la taille du réseau. Notre DQN passe de 40 à 94 %.
- Trois : sur le vrai jeu, il faut des réseaux de neurones, et c'est la récompense qui décide du comportement.
- Sur l'article : ses grandes idées tiennent, mais ses chiffres dépendent de détails qu'il ne publie pas.`,

  merci: `[0:10]
On dit :
- Merci pour votre écoute.`,

  questions: `Questions probables, avec une réponse courte :
- Pourquoi le DQN de l'article échoue-t-il ? Il ne voit presque rien de l'écran, donc il doit apprendre le niveau par cœur.
- Pourquoi Monte Carlo attend-il les Goombas ? Quand il gagne une partie, il récompense tous les coups joués, même les attentes.
- Pourquoi DQN ne sent pas l'ordre du niveau ? Il apprend sur des souvenirs tirés au hasard : pour lui, l'ordre des parties disparaît.
- Est-ce que votre travail change la conclusion de l'article ? Les tendances tiennent, mais un DQN qui voit tout l'écran devient le meilleur.
- Pourquoi vos chiffres sont-ils différents ? Moins de parties (6000), et des règles d'ennemis que l'article ne précise pas.
- Pourquoi regarder la robustesse ? C'est le seul test identique pour tous les algorithmes.`,
};

// ---------------------------------------------------------------------------
// Tableaux de résultats (v3, 6000 épisodes, 5 graines, moyenne ± écart-type)
// ---------------------------------------------------------------------------
const PERF = [
  // nom, clé couleur, victoires, robustesse, glouton, retour, ->80 %, morts
  ['Q-Learning', 'ql', '94,5 ± 1,5 %', '88,8 ± 2,7 %', '5 / 5', '231 ± 12', '3522', '5,5 %'],
  ['SARSA', 'sarsa', '96,2 ± 1,2 %', '88,8 ± 3,0 %', '5 / 5', '241 ± 5', '3354', '3,8 %'],
  ['Monte Carlo', 'mc', '96,2 ± 0,7 %', '88,8 ± 2,3 %', '5 / 5', '258 ± 13', '3450', '3,7 %'],
  ["DQN de l'article", 'dqn', '39,7 ± 6,7 %', '58,4 ± 33,3 %', '3 / 5', '121 ± 18', 'jamais', '59,9 %'],
  ['Notre DQN', 'ours', '93,7 ± 1,4 %', '94,4 ± 3,0 %', '5 / 5', '274 ± 4', '2955', '6,3 %'],
];
// cellules mises en avant (ligne, colonne de données 0..5)
const PERF_BEST = [[1, 0], [2, 0], [4, 1], [4, 3], [4, 4], [2, 5]];

const COST = [
  // nom, clé, durée / graine, énergie / graine, CO2 / graine, × Q-Learning
  ['Q-Learning', 'ql', '16 s', '0,028 Wh', '0,002 g', '×1'],
  ['SARSA', 'sarsa', '16 s', '0,026 Wh', '0,001 g', '×0,9'],
  ['Monte Carlo', 'mc', '33 s', '0,047 Wh', '0,003 g', '×1,7'],
  ["DQN de l'article", 'dqn', '2,6 min', '0,24 Wh', '0,014 g', '×9'],
  ['Notre DQN', 'ours', '24 min', '2,4 Wh', '0,14 g', '×88'],
  ['PPO, vrai jeu', 'ppo', '10,7 min', '0,90 Wh', '0,050 g', '×32'],
  ['PPO, Route A', 'ppo', '12,5 min', '1,1 Wh', '0,062 g', '×40'],
];

module.exports = { NOTES, PERF, PERF_BEST, COST };
