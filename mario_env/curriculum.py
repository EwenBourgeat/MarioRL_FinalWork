"""Conditions de l'expérience de curriculum (article, section 2.3.4).

Le niveau est découpé en six segments A-F (voir ``level_data.SEGMENTS``).
Chaque condition est un ordre de segments ; le drapeau reste en colonne 198
et une zone d'atterrissage de 3 cases est dégagée au départ.

    from mario_env.curriculum import PAPER_CONDITIONS
    env = gym.make("MarioGrid-v0", level="v3",
                   segment_order=PAPER_CONDITIONS["reversed"])
"""

from .level_data import SEGMENT_ORDER, SEGMENTS, random_segment_order

CANONICAL = SEGMENT_ORDER                    # A->B->C->D->E->F
REVERSED = SEGMENT_ORDER[::-1]               # F->E->D->C->B->A

# Les deux cartes citées explicitement dans l'article (section 3.2.5)
PAPER_MAP_3 = "BECDFA"                       # meilleure carte aléatoire
PAPER_MAP_6 = "BEDCFA"                       # carte avec un échec

# Graines d'ordre de l'article : 200-209.  L'article ne précise pas le
# générateur utilisé, les permutations ci-dessous (numpy default_rng) ne
# sont donc pas forcément identiques aux siennes.
ORDER_SEEDS = tuple(range(200, 210))


def random_orders(seeds=ORDER_SEEDS):
    return {f"random_{s}": random_segment_order(s) for s in seeds}


PAPER_CONDITIONS = {"canonical": CANONICAL, "reversed": REVERSED}
PAPER_CONDITIONS.update(random_orders())

__all__ = ["CANONICAL", "REVERSED", "PAPER_MAP_3", "PAPER_MAP_6",
           "ORDER_SEEDS", "PAPER_CONDITIONS", "SEGMENTS", "random_orders"]
