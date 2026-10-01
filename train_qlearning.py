"""Entraîne Q-Learning sur MarioGrid (environnement de l'article).

Exemples :
    python train_qlearning.py --level v1 --episodes 3000 --seeds 42
    python train_qlearning.py --level v1 --episodes 10000 --seeds 42 43 44 45 46

Pour chaque graine, le modèle est enregistré dans models/<nom>/ (Q-table,
mesures, historique, courbes) et apparaît dans le menu MODELES du jeu.
Plusieurs graines tournent en parallèle (une par cœur du processeur).
"""

import argparse
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor

from agents.metrics import (article_metrics, format_metrics, format_summary,
                            plot_curves)
from agents.qlearning import QLearningAgent
from agents.registry import save_model
from agents.training import TrainConfig, run_seed


def build_parser():
    d = TrainConfig()
    p = argparse.ArgumentParser(description="Q-Learning sur MarioGrid")
    p.add_argument("--level", choices=["v1", "v2", "v3"], default=d.level)
    p.add_argument("--episodes", type=int, default=d.episodes)
    p.add_argument("--seeds", type=int, nargs="+", default=[d.seed],
                   help="une ou plusieurs graines, ex. 42 43 44 45 46")
    p.add_argument("--alpha", type=float, default=d.alpha,
                   help="taux d'apprentissage")
    p.add_argument("--gamma", type=float, default=d.gamma,
                   help="facteur d'actualisation")
    p.add_argument("--eps-start", type=float, default=d.eps_start)
    p.add_argument("--eps-decay", type=float, default=d.eps_decay,
                   help="epsilon est multiplié par ce nombre après chaque "
                        "épisode")
    p.add_argument("--eps-min", type=float, default=d.eps_min)
    p.add_argument("--max-steps", type=int, default=d.max_steps,
                   help="limite de pas par épisode")
    p.add_argument("--eval-every", type=int, default=d.eval_every,
                   help="test glouton tous les N épisodes (0 = jamais)")
    p.add_argument("--segments", default=None,
                   help="ordre des segments A-F, ex. FEDCBA")
    p.add_argument("--log-every", type=int, default=d.log_every)
    p.add_argument("--workers", type=int, default=0,
                   help="processus en parallèle (0 = automatique)")
    p.add_argument("--name", default=None,
                   help="nom du dossier du modèle (une seule graine)")
    p.add_argument("--overwrite", action="store_true",
                   help="remplacer un modèle du même nom")
    p.add_argument("--no-save", action="store_true",
                   help="ne rien enregistrer dans models/")
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    configs = [TrainConfig(level=args.level, episodes=args.episodes, seed=s,
                           alpha=args.alpha, gamma=args.gamma,
                           eps_start=args.eps_start, eps_decay=args.eps_decay,
                           eps_min=args.eps_min, max_steps=args.max_steps,
                           eval_every=args.eval_every, segments=args.segments,
                           log_every=args.log_every).as_dict()
               for s in args.seeds]
    print(f"Q-Learning | MarioGrid {args.level} | {args.episodes} épisodes | "
          f"graines {', '.join(map(str, args.seeds))} | alpha={args.alpha} "
          f"gamma={args.gamma} | ε {args.eps_start} -> x{args.eps_decay} "
          f"-> {args.eps_min}", flush=True)
    t0 = time.perf_counter()
    workers = args.workers or min(len(configs), os.cpu_count() or 1)
    if workers <= 1:
        results = [run_seed(c) for c in configs]
    else:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            results = list(pool.map(run_seed, configs))

    all_metrics = []
    for cfg, q, history, tests, final, seconds in results:
        m = article_metrics(history)
        all_metrics.append(m)
        print()
        print(f"=== graine {cfg['seed']} ({seconds:.1f} s) ===")
        print(format_metrics(m, cfg["level"], final))
        if args.no_save:
            continue
        agent = QLearningAgent(3, cfg["alpha"], cfg["gamma"], cfg["seed"])
        agent.q = q
        meta = dict(cfg, algo="qlearning", env="MarioGrid-v0",
                    reward="paper", metrics=m, greedy=final,
                    train_seconds=round(seconds, 2))
        meta.pop("log_every", None)
        name = args.name if (args.name and len(configs) == 1) else None
        path = save_model(agent, meta, history, tests, name=name,
                          overwrite=args.overwrite)
        title = (f"Q-Learning · MarioGrid {cfg['level']} · graine "
                 f"{cfg['seed']} · {cfg['episodes']} épisodes")
        plot_curves(history, tests, path / "curves.png", title)
        print(f"Modèle enregistré : {path}")

    if len(all_metrics) > 1:
        print()
        print(format_summary(all_metrics, args.level))
    print(f"\nDurée totale : {time.perf_counter() - t0:.1f} s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
