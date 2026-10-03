"""Entraîne un agent (Q-Learning, SARSA, Monte Carlo, DQN ou PPO).

Exemples :
    python train.py --algo qlearning --level v1 --episodes 3000 --seeds 42
    python train.py --algo sarsa --level v1 --episodes 6000 --seeds 42
    python train.py --algo sarsa --level v3 --episodes 10000 --seeds 42 43 44 45 46
    python train.py --algo ppo --level v3 --steps 3000000 --seeds 42 --keep-best

Q-Learning, SARSA, Monte Carlo et DQN jouent sur MarioGrid (l'environnement
de l'article) ; PPO joue sur le vrai jeu NES (--env nes, automatique).
Les méthodes à tableau peuvent aussi jouer sur le vrai jeu (--env nes).

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
from agents.training import (ALGO_NAMES, TrainConfig, make_env,
                             robustness_test, run_seed)


def build_parser():
    d = TrainConfig()
    p = argparse.ArgumentParser(
        description="Q-Learning / SARSA / Monte Carlo / DQN sur MarioGrid, "
                    "PPO sur le vrai jeu NES")
    p.add_argument("--algo", choices=sorted(ALGO_NAMES), default=d.algo,
                   help="algorithme (défaut : qlearning)")
    p.add_argument("--level", choices=["v1", "v2", "v3", "full"],
                   default=d.level,
                   help="full = jeu complet (vrai jeu NES seulement)")
    p.add_argument("--env", choices=["grid", "nes"], default=None,
                   help="grid = environnement de l'article, nes = vrai jeu "
                        "(défaut : nes pour PPO, grid sinon)")
    p.add_argument("--actions", default=None,
                   choices=["paper", "right_only", "right_down", "simple",
                            "complex"],
                   help="vrai jeu : boutons (défaut right_only ; right_down "
                        "= right_only + bas, pour le tuyau)")
    p.add_argument("--reward", choices=["paper", "route_a"], default="paper",
                   help="vrai jeu : récompense (paper = article ; route_a = "
                        "tuyau, salle bonus, pièces, champignon)")
    p.add_argument("--steps", type=int, default=3_000_000,
                   help="PPO : nombre total de pas (défaut 3000000)")
    p.add_argument("--n-envs", type=int, default=d.n_envs,
                   help="PPO : parties jouées en parallèle par graine")
    p.add_argument("--ent-coef", type=float, default=d.ent_coef,
                   help="PPO : bonus de curiosité (entropie), ex. 0.01")
    p.add_argument("--eval-steps", type=int, default=d.eval_steps,
                   help="PPO : test glouton tous les N pas")
    p.add_argument("--log-steps", type=int, default=d.log_steps,
                   help="PPO : un retour tous les N pas (ex. 10000) au lieu "
                        "de tous les --log-every épisodes")
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
    p.add_argument("--obs", choices=["paper", "full", "vector", "vector_plus"],
                   default=None,
                   help="vue de l'agent : paper (article), full (vue "
                        "complète, notre DQN), vector ou vector_plus (vrai "
                        "jeu, PPO ; vector_plus voit aussi pièces, objets, "
                        "blocs ? et tuyau)")
    p.add_argument("--variant", default=None,
                   help="étiquette de l'expérience, ex. E1 (ajoutée au nom)")
    p.add_argument("--double", action="store_true",
                   help="DQN : Double DQN (étape 2a)")
    p.add_argument("--n-step", type=int, default=d.n_step,
                   help="DQN : récompenses sur n pas (étape 2b, ex. 3)")
    p.add_argument("--grad-clip", type=float, default=None,
                   help="DQN : taille max d'une correction (étape 2c, ex. 10)")
    p.add_argument("--tau", type=float, default=None,
                   help="DQN : cible douce (étape 2d, ex. 0.005)")
    p.add_argument("--keep-best", action="store_true",
                   help="garder la meilleure version (étape 2e)")
    p.add_argument("--cnn", action="store_true",
                   help="DQN : réseau à loupes (étape 3, avec --obs full)")
    p.add_argument("--device", default="auto",
                   choices=["auto", "cpu", "cuda", "mps"],
                   help="où calculer (auto = carte NVIDIA si présente)")
    p.add_argument("--threads", type=int, default=1,
                   help="cœurs du processeur par graine (défaut 1)")
    p.add_argument("--buffer-size", type=int, default=d.buffer_size,
                   help="DQN : taille de la mémoire de replay (défaut 50000)")
    p.add_argument("--lr", type=float, default=None,
                   help="vitesse d'apprentissage (défaut : 0.0001 pour DQN, "
                        "0.0003 pour PPO)")
    p.add_argument("--carbon", action="store_true",
                   help="mesurer l'énergie et le CO2 avec CodeCarbon "
                        "(pip install codecarbon)")
    p.add_argument("--no-robust", action="store_true",
                   help="ne pas faire le test de robustesse final")
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


def resolve_defaults(parser, args):
    """Réglages qui dépendent de l'algorithme ou de l'environnement."""
    if args.env is None:
        args.env = "nes" if args.algo == "ppo" else "grid"
    if args.obs is None:
        args.obs = ("vector" if args.algo == "ppo" else "paper")
    if args.actions is None:
        args.actions = "right_only" if args.env == "nes" else "paper"
    if args.lr is None:
        args.lr = 3e-4 if args.algo == "ppo" else TrainConfig().lr
    if args.eps_min is None:
        args.eps_min = 0.05 if args.algo == "dqn" else 0.01
    if args.algo == "ppo" and args.env != "nes":
        parser.error("PPO joue sur le vrai jeu : --env nes")
    if args.algo == "ppo" and args.obs not in ("vector", "vector_plus"):
        parser.error("PPO : vue --obs vector ou vector_plus")
    if args.env != "nes" and (args.reward != "paper"
                              or args.obs == "vector_plus"):
        parser.error("--reward route_a et --obs vector_plus : vrai jeu "
                     "seulement (--env nes)")
    if args.algo == "dqn" and args.env == "nes":
        parser.error("DQN sur le vrai jeu : pas encore prévu (utiliser PPO)")
    if args.env == "nes" and args.algo != "ppo" and args.obs != "paper":
        parser.error("tableaux sur le vrai jeu : vue --obs paper")
    if args.env == "grid" and (args.level == "full" or args.obs == "vector"
                               or args.actions != "paper"):
        parser.error("--level full et --obs vector : vrai jeu seulement "
                     "(--env nes)")


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    resolve_defaults(parser, args)
    nes = args.env == "nes"
    configs = [TrainConfig(algo=args.algo, level=args.level,
                           episodes=args.episodes, seed=s,
                           alpha=args.alpha, gamma=args.gamma,
                           eps_start=args.eps_start, eps_decay=args.eps_decay,
                           eps_min=args.eps_min, max_steps=args.max_steps,
                           eval_every=args.eval_every, segments=args.segments,
                           obs=args.obs, variant=args.variant,
                           double=args.double, n_step=args.n_step,
                           grad_clip=args.grad_clip, tau=args.tau,
                           keep_best=args.keep_best, cnn=args.cnn,
                           device=args.device, threads=args.threads,
                           buffer_size=args.buffer_size, lr=args.lr,
                           log_every=args.log_every, env=args.env,
                           actions=args.actions, reward=args.reward,
                           steps=args.steps if args.algo == "ppo" else 0,
                           n_envs=args.n_envs,
                           eval_steps=args.eval_steps,
                           ent_coef=args.ent_coef,
                           log_steps=args.log_steps).as_dict()
               for s in args.seeds]
    if args.algo == "montecarlo":
        # Monte Carlo n'a pas d'alpha : chaque note est une moyenne (1/N)
        for c in configs:
            c["alpha"] = None
    alpha_txt = {"montecarlo": "1/N", "dqn": f"lr {args.lr:g} (Adam), "
                 f"mémoire {args.buffer_size}"}.get(args.algo, args.alpha)
    if args.algo in ("dqn", "ppo"):
        for c in configs:
            c["alpha"] = None
    seeds_txt = ", ".join(map(str, args.seeds))
    env_txt = (f"MarioNES {args.level} (vrai jeu, vue {args.obs}, boutons "
               f"{args.actions}, récompense {args.reward})" if nes
               else f"MarioGrid {args.level}")
    if args.algo == "ppo":
        print(f"PPO | {env_txt} | {args.steps} pas | graines {seeds_txt} | "
              f"lr {args.lr:g} (Adam) gamma={args.gamma} | {args.n_envs} "
              f"parties en parallèle par graine", flush=True)
    else:
        print(f"{ALGO_NAMES[args.algo]} | {env_txt} | "
              f"{args.episodes} épisodes | graines {seeds_txt} | "
              f"alpha={alpha_txt} gamma={args.gamma} | ε {args.eps_start} "
              f"-> x{args.eps_decay} -> {args.eps_min}", flush=True)
    tracker = None
    if args.carbon:
        # CodeCarbon mesure toute la machine PENDANT l'entraînement
        # (processeur, carte graphique NVIDIA, mémoire), puis convertit
        # en CO2 avec l'intensité carbone de l'électricité française
        try:
            from codecarbon import OfflineEmissionsTracker
        except ImportError:
            sys.exit("CodeCarbon manquant : pip install codecarbon")
        os.makedirs("runs", exist_ok=True)
        tracker = OfflineEmissionsTracker(
            country_iso_code="FRA", output_dir="runs", log_level="error",
            project_name=f"{args.algo}_{args.level}_{args.variant or ''}")
        tracker.start()
    t0 = time.perf_counter()
    workers = args.workers or min(len(configs), os.cpu_count() or 1)
    if workers <= 1:
        results = [run_seed(c) for c in configs]
    else:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            results = list(pool.map(run_seed, configs))

    carbon = None
    if tracker is not None:
        tracker.stop()
        d = tracker.final_emissions_data
        carbon = {"energy_kwh": d.energy_consumed, "co2_g": d.emissions * 1000,
                  "cpu_kwh": d.cpu_energy, "gpu_kwh": d.gpu_energy,
                  "ram_kwh": d.ram_energy, "duration_s": d.duration,
                  "country": "FRA", "seeds_in_run": len(configs),
                  "note": "mesure de toute la machine pour le run entier "
                          "(toutes les graines en parallèle)"}
        print(f"\nCodeCarbon : {carbon['energy_kwh']*1000:.3f} Wh, "
              f"{carbon['co2_g']:.3f} g de CO2 pour tout le run "
              f"({len(configs)} graine(s), {carbon['duration_s']/60:.1f} min)")
    all_metrics = []
    for cfg, agent, history, tests, final, seconds in results:
        m = article_metrics(history)
        all_metrics.append(m)
        print()
        print(f"=== graine {cfg['seed']} ({seconds:.1f} s) ===")
        print(format_metrics(m, cfg["level"], final, cfg["algo"]))
        robust = None
        if not args.no_robust:
            robust = robustness_test(make_env(TrainConfig(**cfg)), agent,
                                     cfg["seed"])
            print(f"Test de robustesse      : {robust['win_rate']:.0%} de "
                  f"victoires sur {robust['episodes']} parties avec "
                  f"{robust['epsilon']:.0%} de hasard (retour moyen "
                  f"{robust['avg_return']:.1f})")
            if cfg["level"] == "full":
                print(f"                          salle bonus "
                      f"{robust['bonus_rate']:.0%} des parties, "
                      f"{robust['avg_coins']:.1f} pièces en moyenne")
        if args.no_save:
            continue
        meta = dict(cfg, env="MarioNES-v0" if nes else "MarioGrid-v0",
                    robust=robust, carbon=carbon,
                    best_steps=getattr(agent, "best_steps", None),
                    best_episode=getattr(agent, "best_episode", None),
                    metrics=m, greedy=final,
                    train_seconds=round(seconds, 2))
        meta.pop("log_every", None)
        name = args.name if (args.name and len(configs) == 1) else None
        path = save_model(agent, meta, history, tests, name=name,
                          overwrite=args.overwrite)
        size = (f"{cfg['steps']:,} pas".replace(",", " ")
                if cfg["algo"] == "ppo" else f"{cfg['episodes']} épisodes")
        title = (f"{ALGO_NAMES[cfg['algo']]} · "
                 f"{'MarioNES' if nes else 'MarioGrid'} {cfg['level']} · "
                 f"graine {cfg['seed']} · {size}")
        plot_curves(history, tests, path / "curves.png", title,
                    epsilon=cfg["algo"] != "ppo")
        print(f"Modèle enregistré : {path}")

    if len(all_metrics) > 1:
        print()
        print(format_summary(all_metrics, args.level))
    print(f"\nDurée totale : {time.perf_counter() - t0:.1f} s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
