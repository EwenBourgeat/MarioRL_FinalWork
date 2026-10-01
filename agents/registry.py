"""Dossier ``models/`` : un sous-dossier par modèle entraîné.

    models/qlearning_v1_s42_3000ep/
        meta.json     réglages, mesures de l'article, test glouton
        qtable.npz    la Q-table (états + notes), format numpy
        history.csv   une ligne par épisode (retour, victoire, epsilon...)
        curves.png    les courbes d'apprentissage

Le menu MODELES du jeu (python play.py) liste ces dossiers.
"""

from __future__ import annotations

import csv
import json
import os
from datetime import datetime
from pathlib import Path

MODELS_DIR = Path(__file__).resolve().parent.parent / "models"


def models_dir(path=None):
    return Path(path or os.environ.get("MARIO_MODELS_DIR") or MODELS_DIR)


# Algorithmes du projet, dans l'ordre du menu MODELES (nom interne, affiché)
ALGORITHMS = (("qlearning", "Q-LEARNING"), ("sarsa", "SARSA"),
              ("montecarlo", "MONTE CARLO"), ("dqn", "DQN"))


def short_label(meta):
    """Nom affiché dans la liste d'un algorithme (sans l'algorithme)."""
    s = f"{meta['level']} graine {meta['seed']} {meta['episodes']} ep".upper()
    if meta.get("segments"):
        s += " " + meta["segments"].upper()
    return s


def default_name(algo, level, seed, episodes, segments=None):
    name = f"{algo}_{level}_s{seed}_{episodes}ep"
    if segments:
        name += "_" + "".join(segments).upper()
    return name


def label(meta):
    """Nom court affiché dans le menu (majuscules, police NES)."""
    s = (f"{meta['algo']} {meta['level']} s{meta['seed']} "
         f"{meta['episodes']}").upper()
    if meta.get("segments"):
        s += " " + meta["segments"].upper()
    return s


def save_model(agent, meta, history, tests, root=None, name=None,
               overwrite=False):
    root = models_dir(root)
    name = name or default_name(meta["algo"], meta["level"], meta["seed"],
                                meta["episodes"], meta.get("segments"))
    path = root / name
    if path.exists() and not overwrite:
        i = 2
        while (root / f"{name}_{i}").exists():
            i += 1
        path = root / f"{name}_{i}"
    path.mkdir(parents=True, exist_ok=True)
    meta = dict(meta, name=path.name,
                created=datetime.now().isoformat(timespec="seconds"))
    meta["label"] = label(meta)
    meta["tests"] = tests
    agent.save(path / "qtable.npz")
    with open(path / "meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)
    keys = list(history)
    with open(path / "history.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["episode"] + keys)
        for i, row in enumerate(zip(*(history[k] for k in keys)), 1):
            w.writerow([i] + [round(v, 6) if isinstance(v, float) else v
                              for v in row])
    return path


def list_models(root=None):
    """Métadonnées de tous les modèles, triés par nom."""
    root = models_dir(root)
    out = []
    if not root.is_dir():
        return out
    for meta_file in sorted(root.glob("*/meta.json")):
        try:
            with open(meta_file, encoding="utf-8") as f:
                meta = json.load(f)
        except (OSError, ValueError):
            continue
        if not (meta_file.parent / "qtable.npz").exists():
            continue
        meta["path"] = str(meta_file.parent)
        meta.setdefault("label", label(meta))
        out.append(meta)
    return out


def load_agent(meta_or_path):
    """Recharge l'agent d'un modèle (dict de list_models ou chemin)."""
    from .training import AGENT_CLASSES

    if isinstance(meta_or_path, dict):
        path = Path(meta_or_path["path"])
        meta = meta_or_path
    else:
        path = Path(meta_or_path)
        with open(path / "meta.json", encoding="utf-8") as f:
            meta = json.load(f)
    algo = meta.get("algo", "qlearning")
    if algo not in AGENT_CLASSES:
        raise ValueError(f"algorithme non pris en charge : {algo}")
    return AGENT_CLASSES[algo].load(path / "qtable.npz",
                                    seed=meta.get("seed", 0))
