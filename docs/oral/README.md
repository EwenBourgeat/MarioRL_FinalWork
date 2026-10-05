# Oral final : le diaporama

| Fichier | Contenu |
|---|---|
| `Oral_RL_Mario.pptx` | Le diaporama : 23 diapos pour environ 20 minutes, puis 7 diapos d'annexe pour les questions du jury. Notes de l'orateur et vidéos incluses |
| `Notes_oral.md` | Le texte à dire, diapo par diapo, avec la durée de chacune (environ 19 minutes au total) |
| `videos/` | Les 4 vidéos, en MP4 |
| `fabrication/` | Les scripts qui fabriquent les vidéos, les images et le diaporama |

## Importer dans Canva

1. Dans Canva, importer `Oral_RL_Mario.pptx` (bouton d'import, ou glisser le fichier sur la page d'accueil).
2. Vérifier ces trois points :
   * **Polices.** Les titres sont en Arcade Gamer et le texte en Montserrat ; le sous-titre de la page de titre est en Disket Mono. Ce sont les polices du diaporama modèle. Si Canva en remplace une, la remettre depuis le menu des polices.
   * **Vidéos.** Canva ne garde pas toujours les vidéos d'un PowerPoint. Si une vidéo manque, l'image restée à sa place porte le nom du fichier : glisser le MP4 correspondant de `videos/` dessus.
   * **Notes.** Si elles manquent, elles sont dans `Notes_oral.md`.
3. Canva n'importe pas les tableaux PowerPoint. Les tableaux et les graphiques sont donc faits de formes et de zones de texte : chaque case se modifie directement.

## Les vidéos

Chaque partie rejoue exactement le test glouton enregistré dans `models/*/meta.json`.

| Fichier | Diapo | Ce qu'on voit |
|---|---|---|
| `01_qlearning_progression.mp4` | 10 | Q-Learning (graine 42) aux épisodes 100, 1000, 2200 et 6000, les quatre en même temps sur tout le niveau v3 |
| `02_dqn_article_vs_notre.mp4` | 11 | Graine 44 : le DQN de l'article meurt colonne 154, notre DQN atteint le drapeau en 244 pas |
| `03_ppo_nes_v3.mp4` | 15 | PPO (graine 42) sur le vrai jeu NES, sans hasard, à la vraie vitesse : drapeau en 336 pas |
| `04_ppo_route_a.mp4` | 16 | PPO Route A (graine 43) : champignon, fleur, tuyau, salle bonus, 21 pièces, drapeau |

## Tout regénérer

Il faut `pptxgenjs` (`npm install pptxgenjs` dans un dossier de travail), ainsi que `requirements.txt` et `requirements-dqn.txt` pour rejouer les modèles.

```bash
python docs/oral/fabrication/videos_grid.py progression
python docs/oral/fabrication/videos_grid.py dqn
python docs/oral/fabrication/videos_nes.py ppo_nes_v3_s42_3m 03_ppo_nes_v3.mp4
python docs/oral/fabrication/videos_nes.py ppo_nes_full_a_s43_3m_b 04_ppo_route_a.mp4
python docs/oral/fabrication/make_assets.py
NODE_PATH=<dossier node_modules> sh docs/oral/fabrication/build.sh
python docs/oral/fabrication/export_notes.py
```

Le contenu (chiffres, textes, notes) est dans `fabrication/content.js` et `fabrication/build_deck.js`. Les chiffres viennent de `docs/RESULTATS.md` et des `meta.json` des modèles.
