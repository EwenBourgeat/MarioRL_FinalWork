"""Outils partagés par les environnements : actions, récompenses, codes."""

from dataclasses import dataclass, field, asdict
from typing import Callable, Optional, Sequence, Tuple, Union

import numpy as np

from .. import constants as C

# ---------------------------------------------------------------------------
# Jeux d'actions (mêmes conventions que gym-super-mario-bros)
# ---------------------------------------------------------------------------
_BTN = {
    "NOOP": 0, "right": C.BTN_RIGHT, "left": C.BTN_LEFT, "down": C.BTN_DOWN,
    "up": C.BTN_UP, "A": C.BTN_A, "B": C.BTN_B,
}

ACTION_SETS = {
    # 3 actions de l'article : rien, droite, saut
    "paper": [["NOOP"], ["right"], ["A"]],
    "right_only": [["NOOP"], ["right"], ["right", "A"], ["right", "B"],
                   ["right", "A", "B"]],
    # right_only + bas (entrer dans le tuyau de la salle bonus)
    "right_down": [["NOOP"], ["right"], ["right", "A"], ["right", "B"],
                   ["right", "A", "B"], ["down"]],
    # right_down + gauche et gauche+saut : reculer d'un pas pour sauter sur
    # la fleur posée sur son bloc (elle ne bouge pas, contrairement au
    # champignon)
    "right_down_left": [["NOOP"], ["right"], ["right", "A"], ["right", "B"],
                        ["right", "A", "B"], ["down"], ["left"],
                        ["left", "A"]],
    "simple": [["NOOP"], ["right"], ["right", "A"], ["right", "B"],
               ["right", "A", "B"], ["A"], ["left"]],
    "complex": [["NOOP"], ["right"], ["right", "A"], ["right", "B"],
                ["right", "A", "B"], ["A"], ["left"], ["left", "A"],
                ["left", "B"], ["left", "A", "B"], ["down"], ["up"]],
}


def buttons_of(combo: Sequence[str]) -> int:
    b = 0
    for name in combo:
        if name not in _BTN:
            raise ValueError(f"bouton inconnu : {name!r} ({list(_BTN)})")
        b |= _BTN[name]
    return b


def resolve_actions(actions) -> Tuple[list, list]:
    """Renvoie (liste de combinaisons, liste de masques de boutons NES)."""
    if isinstance(actions, str):
        if actions not in ACTION_SETS:
            raise ValueError(f"jeu d'actions inconnu : {actions!r} "
                             f"(choix : {list(ACTION_SETS)})")
        combos = ACTION_SETS[actions]
    else:
        combos = [list(c) if not isinstance(c, str) else [c] for c in actions]
    return combos, [buttons_of(c) for c in combos]


# ---------------------------------------------------------------------------
# Récompenses
# ---------------------------------------------------------------------------
@dataclass
class RewardConfig:
    """Pondération des événements (toutes les valeurs sont modifiables).

    La valeur par défaut reproduit le tableau 2 de l'article :
    +100 drapeau, -50 mort, +0.5 par case gagnée vers la droite,
    -0.1 à l'arrêt, +1 brique cassée, +3 bloc ?, +5 ennemi vaincu.
    """
    progress_per_tile: float = 0.5   # par colonne (16 px) gagnée / perdue
    only_new_progress: bool = False  # ne récompenser que les nouvelles cases
    stand_still: float = -0.1        # si Mario n'a pas bougé pendant le pas
    win: float = 100.0
    death: float = -50.0
    brick: float = 1.0
    qblock: float = 3.0
    enemy: float = 5.0
    coin: float = 0.0
    powerup: float = 0.0
    one_up: float = 0.0
    bonus_room: float = 0.0          # entrée dans la salle bonus (tuyau)
    powerup_block: float = 0.0       # bloc ? power-up frappé (objet sorti)
    item_approach: float = 0.0       # par case gagnée vers le champignon /
                                     # la fleur visible (guidage)
    score_scale: float = 0.0         # multiplie la variation du score NES
    time_penalty: float = 0.0        # par seconde de chrono écoulée
    stuck_steps: int = 0             # partie finie (comme une mort) après N
                                     # pas sans rien de neuf (0 = jamais)
    clip: Optional[Tuple[float, float]] = None

    @classmethod
    def preset(cls, name: str) -> "RewardConfig":
        if name == "paper":
            return cls()
        if name == "progress":
            # style gym-super-mario-bros (Kautenja) : dx - temps - mort
            return cls(progress_per_tile=16.0, stand_still=0.0, win=15.0,
                       death=-15.0, brick=0.0, qblock=0.0, enemy=0.0,
                       time_penalty=-1.0, clip=(-15.0, 15.0))
        if name == "route_a":
            # route « collectionneur » : tuyau, salle bonus, pièces,
            # champignon.  L'avancée est comptée sur la position la plus à
            # droite atteinte : sinon le raccourci du tuyau (colonne 57 ->
            # 163) ne rapporte rien et le détour fait perdre des points.
            # Pénalité de temps (-0,5 par seconde du chrono, ~ -0,08 par
            # pas) : sans elle, rester dans la salle bonus jusqu'à la limite
            # de pas ne coûte rien (essai : 1/3 des parties bloquées ainsi).
            return cls(only_new_progress=True, coin=10.0, bonus_room=200.0,
                       powerup=50.0, time_penalty=-0.5)
        if name == "route_a2":
            # route_a + champignon et fleur très motivés : +150 chacun, et
            # +25 pour frapper un bloc ? power-up (chaque bloc ne se frappe
            # qu'une fois) ; à utiliser avec le niveau « full_a »
            # + guidage : +2 par case gagnée vers le champignon ou la fleur
            # visible (-2 en s'en éloignant), sinon Mario fonce à droite et
            # le champignon du bloc 21 passe derrière lui
            # + règle du blocage : 150 pas sans rien de neuf = partie perdue
            # (-50).  Sans elle, Mario restait coincé contre un tuyau jusqu'à
            # la limite de pas (rester bloqué ne coûtait presque rien) ; les
            # parties gagnées ne font jamais de pause de plus de ~90 pas
            return cls(only_new_progress=True, coin=10.0, bonus_room=200.0,
                       powerup=150.0, powerup_block=25.0, time_penalty=-0.5,
                       item_approach=2.0, stuck_steps=150)
        if name == "score":
            return cls(progress_per_tile=0.0, stand_still=0.0, win=0.0,
                       death=0.0, brick=0.0, qblock=0.0, enemy=0.0,
                       score_scale=0.01)
        raise ValueError(f"préréglage de récompense inconnu : {name!r}")

    def as_dict(self):
        return asdict(self)


def resolve_reward(reward) -> Union[RewardConfig, Callable]:
    if reward is None:
        return RewardConfig()
    if isinstance(reward, RewardConfig) or callable(reward):
        return reward
    if isinstance(reward, str):
        return RewardConfig.preset(reward)
    if isinstance(reward, dict):
        return RewardConfig(**reward)
    raise TypeError("reward doit être un nom, un dict, un RewardConfig "
                    "ou une fonction (prev_info, info) -> float")


def state_key(obs) -> tuple:
    """Clé hashable d'une observation discrète (pour une Q-table dict)."""
    return tuple(np.asarray(obs).ravel().tolist())


# ---------------------------------------------------------------------------
# Correspondance tuiles NES -> codes d'observation
# ---------------------------------------------------------------------------
TILE_TO_OBS = np.zeros(C.N_TILE_TYPES, dtype=np.uint8)
for _t in (C.GROUND, C.STAIR, C.PIPE_TL, C.PIPE_TR, C.PIPE_L, C.PIPE_R,
           C.USED, C.UG_GROUND, C.SPIPE_TOP_MOUTH, C.SPIPE_TOP_BODY,
           C.SPIPE_BOT_MOUTH, C.SPIPE_BOT_BODY, C.SPIPE_JOIN_TOP,
           C.SPIPE_JOIN_BOT):
    TILE_TO_OBS[_t] = C.OBS_SOLID
for _t in (C.BRICK, C.BRICK_COIN, C.BRICK_STAR, C.BRICK_POWERUP, C.UG_BRICK):
    TILE_TO_OBS[_t] = C.OBS_BRICK
for _t in (C.QBLOCK_COIN, C.QBLOCK_POWERUP):
    TILE_TO_OBS[_t] = C.OBS_QBLOCK
TILE_TO_OBS[C.COIN] = C.OBS_COIN
TILE_TO_OBS[C.FLAGPOLE] = C.OBS_FLAG
TILE_TO_OBS[C.FLAG_BALL] = C.OBS_FLAG

TILE_TO_PAPER = np.zeros(C.N_TILE_TYPES, dtype=np.uint8)
TILE_TO_PAPER[C.GROUND] = C.P_GROUND
TILE_TO_PAPER[C.UG_GROUND] = C.P_GROUND
TILE_TO_PAPER[C.STAIR] = C.P_STEP
for _t in (C.PIPE_TL, C.PIPE_TR, C.PIPE_L, C.PIPE_R):
    TILE_TO_PAPER[_t] = C.P_PIPE
for _t in (C.BRICK, C.BRICK_COIN, C.BRICK_STAR, C.BRICK_POWERUP, C.UG_BRICK):
    TILE_TO_PAPER[_t] = C.P_BRICK
for _t in (C.QBLOCK_COIN, C.QBLOCK_POWERUP):
    TILE_TO_PAPER[_t] = C.P_QBLOCK
TILE_TO_PAPER[C.USED] = C.P_USED
TILE_TO_PAPER[C.FLAGPOLE] = C.P_FLAG
TILE_TO_PAPER[C.FLAG_BALL] = C.P_FLAG

LEVEL_VERSIONS = {
    # v1-v3 : les trois niveaux de complexité de l'article
    "v1": dict(blocks=False, enemies=False, powerups=False, bonus_room=False,
               hidden_1up=False),
    "v2": dict(blocks=True, enemies=False, powerups=False, bonus_room=False,
               hidden_1up=False),
    "v3": dict(blocks=True, enemies=True, powerups=False, bonus_room=False,
               hidden_1up=False),
    # jeu complet (power-ups, salle bonus, 1-UP caché)
    "full": dict(blocks=True, enemies=True, powerups=True, bonus_room=True,
                 hidden_1up=True),
    # jeu complet + 2 blocs tôt, bien avant le tuyau de la salle bonus
    # (colonne 57) :
    # * colonne 34 (entre les tuyaux 28 et 38) : bloc ? power-up normal
    #   (champignon pour Mario petit) : celui du bloc 21 d'origine est très
    #   rarement attrapé par l'IA (le champignon passe derrière Mario) ;
    # * colonne 36 (2 blocs après) : « bloc de fleur », qui ne s'ouvre que
    #   pour Mario grand.  Mario y est déjà grand mais ne le frappe pas par
    #   habitude (0 / 120 parties avec les anciens modèles) : il doit le
    #   viser exprès.  En colonne 37, il le cognait en sautant sur le tuyau
    #   38 (70 % des parties) ; en colonne 35, il n'était pas encore grand
    "full_a": dict(blocks=True, enemies=True, powerups=True,
                   bonus_room=True, hidden_1up=True,
                   extra_blocks=((34, 9, C.QBLOCK_POWERUP),
                                 (36, 9, C.QBLOCK_POWERUP)),
                   flower_blocks=((36, 9),)),
}
