"""Images du diaporama tirées du jeu et des vidéos :
* assets/level_v3.png : le niveau v3 entier (environnement de l'article) ;
* assets/poster_*.png : image d'aperçu de chaque vidéo ;
* assets/fallback_*.png : la même avec le nom du fichier MP4 (image laissée
  à la place de la vidéo si Canva ne l'importe pas).

    python docs/oral/fabrication/make_assets.py      (après les vidéos)

Les sprites de assets/sprites/ viennent du diaporama modèle Canva du groupe
(export PDF, texte retiré, découpés un par un).
"""

import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image

BUILD = Path(__file__).resolve().parent
ROOT = BUILD.parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(BUILD))

from mario_env import MarioGridEnv                       # noqa: E402
from videos_grid import draw_text                         # noqa: E402

A = BUILD / "assets"
V = ROOT / "docs" / "oral" / "videos"
POSTERS = {"01_qlearning_progression.mp4": "end", "02_dqn_article_vs_notre.mp4": "end",
           "03_ppo_nes_v3.mp4": 9.5, "04_ppo_route_a.mp4": 13.0}


def main():
    A.mkdir(parents=True, exist_ok=True)
    for f in ("ecran_titre.png", "observation_v3.png"):
        shutil.copy(ROOT / "docs" / f, A / f)
    env = MarioGridEnv(level="v3")
    env.reset(seed=0)
    Image.fromarray(env.render_level(window=(0, env.W))[3 * 16:]).save(A / "level_v3.png")
    for name, t in POSTERS.items():
        base = name.replace(".mp4", "")
        out = A / f"poster_{base}.png"
        args = ["ffmpeg", "-y", "-loglevel", "error"]
        args += ["-sseof", "-0.5"] if t == "end" else ["-ss", str(t)]
        subprocess.run(args + ["-i", str(V / name), "-frames:v", "1", str(out)], check=True)
        im = np.array(Image.open(out).convert("RGB"))
        h, w, _ = im.shape
        k = 3 if w > 1000 else 2
        label = "VIDEO " + name.upper()
        bh = 8 * k + 16
        im[h - bh:h, 0:min(w, 8 * k * (len(label) + 2))] = (20, 24, 61)
        draw_text(im, label, 8, h - bh + 8, k, color=(255, 199, 3), shadow=None)
        Image.fromarray(im).save(A / f"fallback_{base}.png")
        print(name, "->", out.name)


if __name__ == "__main__":
    main()
