"""Objets du jeu : joueur, ennemis, objets bonus, projectiles et effets.

Les classes sont de simples conteneurs (``__slots__``) : toute la logique est
dans :mod:`mario_env.game` pour garder une boucle rapide.
"""

from .constants import FALL_MFORCE, JUMP_MFORCE
from .level_data import START_X, START_Y


class Player:
    __slots__ = (
        "x", "x_force", "x_speed", "x_abs", "y", "y_speed", "y_force",
        "y_dummy", "state", "facing", "moving_dir", "status", "crouch",
        "running_timer", "running_speed", "vforce", "vforce_down",
        "jump_origin", "diff_to_halt", "collision_bits", "side_timer",
        "anim_timer", "anim_set", "anim_frame", "star_timer", "injury_timer",
        "x_scroll", "fire_anim", "visible", "jump_timer", "behind_bg",
        "skidding",
    )

    def __init__(self, x=START_X, y=START_Y, status=0):
        self.x = x
        self.x_force = 0          # sous-pixel horizontal (Player_X_MoveForce)
        self.x_speed = 0          # 1/16 px par image, signé
        self.x_abs = 0
        self.y = y                # haut d'une boîte de 32 px (coord. écran)
        self.y_speed = 0          # px par image, signé
        self.y_force = 0          # fraction de vitesse verticale (1/256)
        self.y_dummy = 0          # fraction de position verticale (1/256)
        self.state = 0            # 0 sol, 1 saut, 2 chute, 3 grimpe (mât)
        self.facing = 1           # 1 droite, 2 gauche
        self.moving_dir = 1
        self.status = status      # 0 petit, 1 super, 2 feu
        self.crouch = False
        self.running_timer = 0
        self.running_speed = 0
        self.vforce = JUMP_MFORCE[0]
        self.vforce_down = FALL_MFORCE[0]
        self.jump_origin = y
        self.diff_to_halt = 1
        self.collision_bits = 0xFF
        self.side_timer = 0
        self.anim_timer = 0
        self.anim_set = 7
        self.anim_frame = 0
        self.star_timer = 0
        self.injury_timer = 0
        self.x_scroll = 0
        self.fire_anim = 0
        self.visible = True
        self.jump_timer = 0
        self.behind_bg = False
        self.skidding = False

    @property
    def small(self):
        return self.status == 0


class Enemy:
    """Goomba, Koopa, champignons, fleur, étoile (tout ce qui marche/tombe).

    ``y`` suit la convention NES : haut d'une boîte de 24 px dont le bas est
    au niveau des pieds (un Goomba au sol a donc y = 184).
    """

    __slots__ = (
        "kind", "x", "x_force", "x_speed", "y", "y_speed", "y_force",
        "y_dummy", "state", "timer", "moving_dir", "falling", "coll_flag",
        "alive", "rise", "chain", "anim", "uid", "flip",
    )

    def __init__(self, kind, x, y, x_speed, uid=0):
        self.kind = kind          # goomba, koopa, mushroom, flower, star, 1up
        self.x = x
        self.x_force = 0
        self.x_speed = x_speed
        self.y = y
        self.y_speed = 0
        self.y_force = 0
        self.y_dummy = 0
        # walk | flat | shell | shell_move | dead | rise
        self.state = "walk"
        self.timer = 0
        self.moving_dir = 1 if x_speed > 0 else 2
        self.falling = False
        self.coll_flag = False
        self.alive = True
        self.rise = 0
        self.chain = 0            # compteur de victimes d'une carapace
        self.anim = 0
        self.uid = uid
        self.flip = False

    @property
    def is_item(self):
        return self.kind in ("mushroom", "flower", "star", "1up")


class Fireball:
    __slots__ = ("x", "y", "x_speed", "y_speed", "y_force", "y_dummy",
                 "x_force", "alive", "explode", "anim")

    def __init__(self, x, y, x_speed):
        self.x = x
        self.y = y
        self.x_speed = x_speed
        self.x_force = 0
        self.y_speed = 4
        self.y_force = 0
        self.y_dummy = 0
        self.alive = True
        self.explode = 0
        self.anim = 0


class BlockBump:
    """Bloc qui rebondit après un coup de tête (effet visuel + durée)."""
    __slots__ = ("col", "row", "tile", "t", "offset")

    def __init__(self, col, row, tile):
        self.col = col
        self.row = row
        self.tile = tile          # tuile affichée pendant le rebond
        self.t = 0
        self.offset = 0


class Effect:
    """Effets purement visuels : débris, pièce qui saute, score flottant."""
    __slots__ = ("kind", "x", "y", "vx", "vy", "t", "value")

    def __init__(self, kind, x, y, vx=0.0, vy=0.0, value=0):
        self.kind = kind
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.t = 0
        self.value = value
