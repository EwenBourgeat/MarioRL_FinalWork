"""Mesures de l'article (section 2.3.3) et courbes d'apprentissage.

* Taux de victoire : part des épisodes gagnés (drapeau) sur les 500 derniers.
* Retour moyen : somme des récompenses d'un épisode (sans gamma), moyennée
  sur les 500 derniers épisodes.
* Vitesse de convergence : premier épisode où le taux de victoire lissé
  (moyenne glissante sur 100 épisodes) atteint 50 %, puis 80 %.
* Interactions (v2/v3) : briques cassées, blocs ? frappés et ennemis vaincus
  par épisode, en moyenne sur les 500 derniers épisodes.
"""

from __future__ import annotations

import math

import numpy as np

LAST = 500
WINDOW = 100


def rolling_mean(x, window=WINDOW):
    """Moyenne glissante sur des fenêtres *complètes*.

    La valeur d'indice i est la moyenne des épisodes i+1 à i+window, donc
    elle correspond à l'épisode numéro i + window.
    """
    x = np.asarray(x, dtype=float)
    if len(x) < window:
        return np.zeros(0)
    c = np.cumsum(np.insert(x, 0, 0.0))
    return (c[window:] - c[:-window]) / window


def episodes_to(wins, threshold, window=WINDOW):
    """Premier épisode où la moyenne glissante atteint ``threshold`` (ou None)."""
    r = rolling_mean(wins, window)
    hit = np.nonzero(r >= threshold - 1e-12)[0]
    return int(hit[0]) + window if len(hit) else None


def article_metrics(history, last=LAST, window=WINDOW):
    n = len(history["win"])
    k = min(last, n)
    tail = {key: np.asarray(v[-k:], dtype=float) for key, v in history.items()}
    first_win = next((i + 1 for i, w in enumerate(history["win"]) if w), None)
    return {
        "episodes": n,
        "last": k,
        "win_rate": float(tail["win"].mean()),
        "avg_return": float(tail["return"].mean()),
        "to_50": episodes_to(history["win"], 0.5, window),
        "to_80": episodes_to(history["win"], 0.8, window),
        "bricks": float(tail["bricks"].mean()),
        "qblocks": float(tail["qblocks"].mean()),
        "enemies": float(tail["enemies"].mean()),
        "death_rate": float(tail["dead"].mean()),
        "timeout_rate": float(tail["timeout"].mean()),
        "avg_steps": float(tail["steps"].mean()),
        "first_win": first_win,
        "epsilon_end": float(history["epsilon"][-1]),
        "n_states": int(history["n_states"][-1]),
        # vrai jeu NES (PPO) : pièces, salle bonus, power-ups
        **({"coins": float(tail["coins"].mean()),
            "bonus_rate": float((tail["bonus"] > 0).mean()),
            "powerups": float(tail["powerups"].mean())}
           if "coins" in history else {}),
        **({"mushroom_rate": float((tail["mushrooms"] > 0).mean()),
            "flower_rate": float((tail["flowers"] > 0).mean())}
           if "mushrooms" in history else {}),
    }


def _ep(v):
    return "N/A (jamais)" if v is None else f"{v}"


def format_metrics(m, level, greedy=None, algo=None):
    """Tableau texte des mesures (en français)."""
    a, b = m["episodes"] - m["last"] + 1, m["episodes"]
    lines = [
        f"Mesures de l'article (épisodes {a} à {b}) :",
        f"  Taux de victoire        : {m['win_rate']:.1%}",
        f"  Retour moyen            : {m['avg_return']:.1f}",
        f"  Épisodes pour 50 %      : {_ep(m['to_50'])}",
        f"  Épisodes pour 80 %      : {_ep(m['to_80'])}",
    ]
    if level == "v1":
        lines.append("  Briques / blocs ? / ennemis : — (absents en v1)")
    else:
        lines.append(f"  Briques cassées / épisode   : {m['bricks']:.2f}")
        lines.append(f"  Blocs ? frappés / épisode   : {m['qblocks']:.2f}")
        if level in ("v3", "full", "full_a"):
            lines.append(f"  Ennemis vaincus / épisode   : {m['enemies']:.2f}")
    if "coins" in m and level.startswith("full"):
        lines += [
            f"  Pièces / épisode            : {m['coins']:.2f}",
            f"  Passages par la salle bonus : {m['bonus_rate']:.1%}",
            f"  Champignons/fleurs/étoiles  : {m['powerups']:.2f} / épisode",
        ]
    if "mushroom_rate" in m and level.startswith("full"):
        lines += [
            f"  Parties avec champignon     : {m['mushroom_rate']:.1%}",
            f"  Parties avec fleur          : {m['flower_rate']:.1%}",
        ]
    lines += [
        "Autres repères :",
        f"  Première victoire       : épisode {_ep(m['first_win'])}",
        f"  Morts / temps écoulé    : {m['death_rate']:.1%} / "
        f"{m['timeout_rate']:.1%}",
        f"  Pas par épisode         : {m['avg_steps']:.1f}",
    ]
    if algo == "ppo":
        # PPO n'a pas d'epsilon : il tire ses boutons au sort selon sa
        # politique ; pas de Q-table ni de mémoire de replay
        lines.append(f"  Pas d'entraînement      : {m['n_states']}")
    else:
        lines += [
            f"  Epsilon final           : {m['epsilon_end']:.3f}",
            (f"  Pas en mémoire (replay) : {m['n_states']}" if algo == "dqn"
             else f"  États dans la Q-table   : {m['n_states']}"),
        ]
    if greedy is not None:
        verdict = ("VICTOIRE" if greedy["win"] else
                   "mort" if greedy["dead"] else "temps écoulé")
        line = (f"Test glouton (ε = 0)    : {verdict} en {greedy['steps']} "
                f"pas, retour {greedy['return']:.1f}, colonne "
                f"{greedy['max_col']}")
        if "coins" in m and level.startswith("full"):
            line += (f", salle bonus {'oui' if greedy.get('bonus') else 'non'}"
                     f", {greedy.get('coins', 0)} pièces, "
                     f"champignon {'oui' if greedy.get('mushrooms') else 'non'}"
                     f", fleur {'oui' if greedy.get('flowers') else 'non'}")
        lines.append(line)
    return "\n".join(lines)


def mean_std(values):
    vals = [v for v in values if v is not None]
    if not vals:
        return None, None, 0
    mean = sum(vals) / len(vals)
    std = (math.sqrt(sum((v - mean) ** 2 for v in vals) / (len(vals) - 1))
           if len(vals) > 1 else 0.0)
    return mean, std, len(vals)


def format_summary(metrics_list, level):
    """Moyenne ± écart-type sur plusieurs graines (comme le tableau 3)."""
    n = len(metrics_list)
    rows = [("Taux de victoire", "win_rate", "pct"),
            ("Retour moyen", "avg_return", "f1"),
            ("Épisodes pour 50 %", "to_50", "int"),
            ("Épisodes pour 80 %", "to_80", "int")]
    if level != "v1":
        rows += [("Briques / épisode", "bricks", "f2"),
                 ("Blocs ? / épisode", "qblocks", "f2")]
    if level in ("v3", "full", "full_a"):
        rows.append(("Ennemis / épisode", "enemies", "f2"))
    if level.startswith("full") and all("coins" in m for m in metrics_list):
        rows += [("Pièces / épisode", "coins", "f2"),
                 ("Salle bonus", "bonus_rate", "pct"),
                 ("Power-ups / épisode", "powerups", "f2")]
    if level.startswith("full") and all("mushroom_rate" in m
                                        for m in metrics_list):
        rows += [("Champignon", "mushroom_rate", "pct"),
                 ("Fleur", "flower_rate", "pct")]
    lines = [f"Résumé sur {n} graines (moyenne ± écart-type) :"]
    for label, key, fmt in rows:
        mean, std, k = mean_std([m[key] for m in metrics_list])
        if mean is None:
            s = "N/A"
        elif fmt == "pct":
            s = f"{mean:.1%} ± {std:.1%}"
        elif fmt == "int":
            s = f"{mean:.0f} ± {std:.0f}"
        else:
            d = int(fmt[1])
            s = f"{mean:.{d}f} ± {std:.{d}f}"
        if k < n and mean is not None:
            s += f"  (seuil non atteint pour {n - k} graine(s))"
        lines.append(f"  {label:<20}: {s}")
    return "\n".join(lines)


# ----------------------------------------------------------------------
# Courbes
# ----------------------------------------------------------------------
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"
SURFACE = "#fcfcfb"
SERIES_1 = "#2a78d6"
SERIES_2 = "#eb6834"


def _style(ax, title, ylabel):
    ax.set_facecolor(SURFACE)
    ax.set_title(title, loc="left", fontsize=11, color=INK, pad=8)
    ax.set_ylabel(ylabel, color=INK_2, fontsize=9)
    ax.set_xlabel("épisode", color=INK_2, fontsize=9)
    ax.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(AXIS)
    ax.tick_params(colors=INK_2, labelsize=8)


def plot_curves(history, tests, path, title, flag_col=198, epsilon=True):
    """Quatre graphiques : victoires, retour, distance, epsilon (ou, pour
    PPO qui n'a pas d'epsilon, ``epsilon=False`` : taux de mort).

    Les trois premiers sont des moyennes glissantes sur 100 épisodes : un
    épisode seul est très bruité (l'exploration fait souvent mourir Mario).
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.ticker import PercentFormatter

    n = len(history["win"])
    ep = np.arange(1, n + 1)
    roll_ep = np.arange(WINDOW, n + 1)
    fig, axes = plt.subplots(2, 2, figsize=(11, 7.2), facecolor=SURFACE)
    fig.suptitle(title, x=0.06, ha="left", fontsize=13, color=INK)

    # 1) taux de victoire lissé + test glouton
    ax = axes[0, 0]
    _style(ax, "Taux de victoire", "victoires")
    for thr in (0.5, 0.8):
        ax.axhline(thr, color=MUTED, linewidth=0.8, linestyle=(0, (4, 3)))
        ax.text(n * 0.01, thr + 0.015, f"{thr:.0%}", color=INK_2, fontsize=8,
                ha="left", va="bottom")
    if len(roll_ep):
        roll = rolling_mean(history["win"])
        ax.plot(roll_ep, roll, color=SERIES_1, linewidth=2,
                label="moyenne sur 100 épisodes (avec exploration)")
        for thr in (0.5, 0.8):
            e = episodes_to(history["win"], thr)
            if e is not None:
                ax.scatter([e], [roll[e - WINDOW]], s=40, color=SERIES_1,
                           edgecolors=SURFACE, linewidths=2, zorder=4)
                ax.annotate(f"épisode {e}", (e, roll[e - WINDOW]),
                            xytext=(10, -12), textcoords="offset points",
                            fontsize=8, color=INK, va="top")
    if tests:
        ax.scatter([t["episode"] for t in tests], [t["win"] for t in tests],
                   s=22, color=SERIES_2, edgecolors=SURFACE, linewidths=1.5,
                   zorder=3, label="test glouton ε = 0 (1 = gagné, 0 = perdu)")
    ax.set_ylim(-0.05, 1.08)
    ax.yaxis.set_major_formatter(PercentFormatter(1.0))
    ax.legend(loc="lower right", fontsize=8, frameon=False, labelcolor=INK_2)

    # 2) retour moyen
    ax = axes[0, 1]
    _style(ax, "Retour moyen (100 épisodes)", "somme des récompenses")
    if len(roll_ep):
        ax.plot(roll_ep, rolling_mean(history["return"]), color=SERIES_1,
                linewidth=2)

    # 3) distance atteinte
    ax = axes[1, 0]
    _style(ax, "Distance atteinte moyenne (100 épisodes)",
           "colonne la plus à droite")
    ax.axhline(flag_col, color=MUTED, linewidth=0.8, linestyle=(0, (4, 3)))
    ax.text(n * 0.01, flag_col + 3, f"drapeau (colonne {flag_col})",
            color=INK_2, fontsize=8, ha="left", va="bottom")
    if len(roll_ep):
        ax.plot(roll_ep, rolling_mean(history["max_col"]), color=SERIES_1,
                linewidth=2)
    ax.set_ylim(0, flag_col + 22)

    # 4) exploration (ou taux de mort pour PPO)
    ax = axes[1, 1]
    if epsilon:
        _style(ax, "Exploration ε (probabilité de jouer au hasard)", "ε")
        ax.plot(ep, history["epsilon"], color=SERIES_1, linewidth=2)
        ax.text(n, history["epsilon"][-1] + 0.03,
                f"{history['epsilon'][-1]:.3f}", color=INK_2, fontsize=8,
                ha="right", va="bottom")
    elif "coins" in history and max(history["coins"], default=0) > 0:
        _style(ax, "Pièces ramassées (100 épisodes)", "pièces par partie")
        if len(roll_ep):
            ax.plot(roll_ep, rolling_mean(history["coins"]), color=SERIES_1,
                    linewidth=2)
    else:
        _style(ax, "Morts (100 épisodes)", "part des parties perdues")
        if len(roll_ep):
            ax.plot(roll_ep, rolling_mean(history["dead"]), color=SERIES_1,
                    linewidth=2)
        ax.yaxis.set_major_formatter(PercentFormatter(1.0))
    if epsilon or "coins" not in history or not max(history["coins"],
                                                    default=0):
        ax.set_ylim(0, 1.05)

    for ax in axes.flat:
        ax.set_xlim(0, n + 1)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(path, dpi=130, facecolor=SURFACE)
    plt.close(fig)
