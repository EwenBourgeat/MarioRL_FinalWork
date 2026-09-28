"""Super Mario Bros. niveau 1-1 : jeu jouable + environnements RL.

* :class:`mario_env.game.Game` : moteur fidèle au jeu NES (sans affichage).
* ``gym.make("MarioNES-v0")`` : environnement Gymnasium sur ce moteur.
* ``gym.make("MarioGrid-v0")`` : environnement discret de l'article
  (Ponnock & Ho, 2026) avec les versions v1 / v2 / v3.
* ``python -m mario_env.play`` : jouer au clavier.
"""

from .game import Game, GameConfig
from .envs import (ACTION_SETS, LEVEL_VERSIONS, MarioGridEnv, MarioNESEnv,
                   RewardConfig, state_key)

__version__ = "1.0.0"

try:
    from gymnasium.envs.registration import register, registry

    if "MarioNES-v0" not in registry:
        register(id="MarioNES-v0", entry_point="mario_env.envs:MarioNESEnv")
    if "MarioGrid-v0" not in registry:
        register(id="MarioGrid-v0", entry_point="mario_env.envs:MarioGridEnv")
except Exception:  # pragma: no cover - gymnasium absent
    pass

__all__ = ["Game", "GameConfig", "MarioNESEnv", "MarioGridEnv",
           "RewardConfig", "ACTION_SETS", "LEVEL_VERSIONS", "state_key"]
