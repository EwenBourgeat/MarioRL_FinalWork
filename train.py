"""Entraîne un agent tabulaire (Q-Learning, SARSA ou Monte Carlo) sur MarioGrid.

Exemples :
    python train.py --algo qlearning --level v1 --episodes 3000 --seeds 42
    python train.py --algo sarsa --level v1 --episodes 6000 --seeds 42
    python train.py --algo sarsa --level v3 --episodes 10000 --seeds 42 43 44 45 46

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
from agents.registry import save_model
from agents.training import ALGO_NAMES, TrainConfig, run_seed


def build_parser():
    d = TrainConfig()
    p = argparse.ArgumentParser(description="Q-Learning / SARSA / Monte Carlo sur MarioGrid")
    p.add_argument("--algo", choices=sorted(ALGO_NAMES), default=d.algo,
                   help="algorithme (défaut : qlearning)")
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
    p.add_argument("--eps-min", type=float, default=None,
                   help="plancher de epsilon (défaut : 0.01, 0.05 pour DQN)")
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
    if args.eps_min is None:
        args.eps_min = 0.05 if args.algo == "dqn" else 0.01
    configs = [TrainConfig(algo=args.algo, level=args.level,
                           episodes=args.episodes, seed=s,
                           alpha=args.alpha, gamma=args.gamma,
                           eps_start=args.eps_start, eps_decay=args.eps_decay,
                           eps_min=args.eps_min, max_steps=args.max_steps,
                           eval_every=args.eval_every, segments=args.segments,
                           log_every=args.log_every).as_dict()
               for s in args.seeds]
    if args.algo == "montecarlo":
        # Monte Carlo n'a pas d'alpha : chaque note est une moyenne (1/N)
        for c in configs:
            c["alpha"] = None
    alpha_txt = {"montecarlo": "1/N", "dqn": "lr 0.0001 (Adam)"}.get(
        args.algo, args.alpha)
    if args.algo == "dqn":
        for c in configs:
            c["alpha"] = None
    print(f"{ALGO_NAMES[args.algo]} | MarioGrid {args.level} | "
          f"{args.episodes} épisodes | "
          f"graines {', '.join(map(str, args.seeds))} | alpha={alpha_txt} "
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
    for cfg, agent, history, tests, final, seconds in results:
        m = article_metrics(history)
        all_metrics.append(m)
        print()
        print(f"=== graine {cfg['seed']} ({seconds:.1f} s) ===")
        print(format_metrics(m, cfg["level"], final, cfg["algo"]))
        if args.no_save:
            continue
        meta = dict(cfg, env="MarioGrid-v0",
                    reward="paper", metrics=m, greedy=final,
                    train_seconds=round(seconds, 2))
        meta.pop("log_every", None)
        name = args.name if (args.name and len(configs) == 1) else None
        path = save_model(agent, meta, history, tests, name=name,
                          overwrite=args.overwrite)
        title = (f"{ALGO_NAMES[cfg['algo']]} · MarioGrid {cfg['level']} · graine "
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
