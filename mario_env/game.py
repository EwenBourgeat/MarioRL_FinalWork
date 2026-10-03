"""Moteur de jeu fidèle au Super Mario Bros. NES (niveau 1-1).

Une image (frame) = un appel à :meth:`Game.step`.  Le moteur est
entièrement déterministe, sans dépendance graphique (numpy seulement) et
peut donc tourner « headless » pour l'apprentissage par renforcement.

La logique du joueur reprend les routines du jeu original :
``PlayerPhysicsSub``, ``ImposeFriction``, ``MoveObjectHorizontally``,
``ImposeGravity``, ``PlayerBGCollision``, ``ImpedePlayerMove``,
``ScrollHandler``… avec la même arithmétique en virgule fixe (sous-pixels).
"""

from __future__ import annotations

import copy

import numpy as np

from . import constants as C
from . import level_data as L
from .constants import (
    BTN_A, BTN_B, BTN_DOWN, BTN_LEFT, BTN_RIGHT, BTN_UP, TILE,
)
from .entities import BlockBump, Effect, Enemy, Fireball, Player

# Valeurs de score des « nombres flottants » (index NES FloateyNum)
FLOATEY_POINTS = (0, 100, 200, 400, 500, 800, 1000, 2000, 4000, 5000, 8000)
ONE_UP = -1


class GameConfig:
    """Options du moteur (toutes les mécaniques sont activables séparément)."""

    def __init__(self, lives=3, blocks=True, enemies=True, powerups=True,
                 bonus_room=True, hidden_1up=True, start_status=0,
                 halfway=True, end_sequence=True, timer=True,
                 segment_order=None, timer_frames=C.GAME_TIMER_TICK,
                 scroll_back=False, extra_blocks=()):
        self.lives = lives              # nombre de vies (3 comme l'original)
        self.blocks = blocks            # briques / blocs ? (v2 de l'article)
        self.enemies = enemies          # Goombas + Koopa (v3 de l'article)
        self.powerups = powerups        # champignon, fleur, étoile, 1-UP
        self.bonus_room = bonus_room    # tuyau 57 -> salle bonus
        self.hidden_1up = hidden_1up
        self.start_status = start_status  # 0 petit, 1 super, 2 feu
        self.halfway = halfway          # point de reprise à la page 5
        self.end_sequence = end_sequence  # animation drapeau + château
        self.timer = timer              # chrono de 400
        # ordre des segments A-F (expérience de curriculum de l'article) ;
        # None ou "ABCDEF" = niveau original
        self.segment_order = segment_order
        # images par unité du chrono : 24 sur NES (1 unité ≈ 0,4 s),
        # 60 pour un chrono en vraies secondes
        self.timer_frames = timer_frames
        # la caméra suit aussi Mario vers la gauche (absent du jeu NES)
        self.scroll_back = scroll_back
        # blocs ajoutés au niveau original : ((colonne, rangée, tuile), ...)
        # ex. un bloc ? power-up tôt dans le niveau (niveau « full_a »)
        self.extra_blocks = tuple(extra_blocks)


class Game:
    """État complet d'une partie sur le niveau 1-1."""

    def __init__(self, config: GameConfig | None = None):
        self.cfg = config or GameConfig()
        self.lives = self.cfg.lives
        self.score = 0
        self.coins = 0
        self.frame = 0
        self.halfway_reached = False
        self.stats = self._new_stats()
        self._load_level(start_at_halfway=False)

    # ------------------------------------------------------------------
    # Chargement / sauvegarde
    # ------------------------------------------------------------------
    @staticmethod
    def _new_stats():
        return {
            "bricks_broken": 0, "qblocks_hit": 0, "blocks_bumped": 0,
            "coins": 0, "enemies_killed": 0, "stomps": 0, "goombas_killed": 0,
            "koopas_killed": 0, "powerups": 0, "one_ups": 0, "deaths": 0,
            "shells_kicked": 0, "fireballs": 0, "bonus_room": 0,
            "flag_points": 0, "jumps": 0, "hidden_blocks": 0,
            "mushrooms": 0, "flowers": 0, "powerup_blocks": 0,
        }

    def _build_grid(self, area):
        if area == "overworld":
            grid = L.build_overworld()
            if self._permuted():
                grid = L.permute_grid(grid, self.cfg.segment_order)
            if not self.cfg.blocks:
                for col, row, _ in L.BLOCKS:
                    grid[row, col] = C.EMPTY
            elif not self.cfg.hidden_1up or not self.cfg.powerups:
                for col, row, kind in L.BLOCKS:
                    if kind == C.HIDDEN_1UP:
                        grid[row, col] = C.EMPTY
            if self.cfg.blocks:
                for col, row, kind in self.cfg.extra_blocks:
                    grid[row, col] = kind
        else:
            grid = L.build_bonus_room()
        return grid

    def _permuted(self):
        order = self.cfg.segment_order
        return bool(order) and "".join(order).upper() != L.SEGMENT_ORDER

    def _set_area(self, area):
        self.area = area
        self.grid = self.grids[area]
        self.W = self.grid.shape[1]
        # bytearray partagé avec la vue numpy : lecture rapide en Python pur
        self.buf = self.bufs[area]
        self.cam_max = max(0, self.W * TILE - C.SCREEN_W)

    def _load_level(self, start_at_halfway):
        if self._permuted():
            self.enemy_spawns = L.permute_enemies(L.ENEMIES,
                                                  self.cfg.segment_order)
        else:
            self.enemy_spawns = L.ENEMIES
        self.grids = {}
        self.bufs = {}
        for area in ("overworld", "bonus"):
            g = self._build_grid(area)
            b = bytearray(g.tobytes())
            self.bufs[area] = b
            self.grids[area] = np.frombuffer(b, dtype=np.uint8).reshape(g.shape)
        self._set_area("overworld")

        status = self.cfg.start_status
        start_x = L.START_X
        self.cam_x = 0
        if start_at_halfway:
            self.cam_x = L.HALFWAY_PAGE * 256
            start_x = self.cam_x + L.START_X
        self.p = Player(start_x, L.START_Y, status)
        self.enemies = []
        self.fireballs = []
        self.bumps = []
        self.effects = []
        self.spawned = set()
        self.enemy_uid = 0
        self.mode = "play"
        self.mode_timer = 0
        self.timer = C.GAME_TIMER_START
        self.timer_tick = self.cfg.timer_frames
        self.scroll_lock = False
        self.block_bounce_timer = 0
        self.brick_coin_timers = {}
        self.stomp_chain = 0
        self.prev_buttons = 0
        self.buttons = 0
        self.flag_y = 56
        self.flag_score_idx = 4
        self.flag_score_y = 0
        self.castle_flag = 0
        self.fireworks = 0
        self.firework_t = 0
        self.dead = False             # vrai à l'image où Mario meurt
        self.death_cause = None
        self.level_complete = False   # vrai quand Mario touche le mât
        self.game_over = False
        self.finished = False         # séquence de fin terminée
        self.freeze = 0               # gel du monde (transformations)
        self.freeze_kind = None
        self.enemy_pairs = set()
        self.max_x = start_x

    def reset(self):
        """Nouvelle partie complète (vies, score et pièces réinitialisés)."""
        self.__init__(self.cfg)

    def restart_level(self):
        """Recharge le niveau en conservant score, pièces, vies et stats."""
        keep = (self.lives, self.score, self.coins, self.stats, self.frame)
        self._load_level(start_at_halfway=False)
        self.lives, self.score, self.coins, self.stats, self.frame = keep

    def get_state(self):
        """Copie profonde de l'état (sauvegarde instantanée)."""
        return copy.deepcopy(self.__dict__)

    def set_state(self, state):
        """Restaure un état obtenu avec :meth:`get_state`."""
        self.__dict__.update(copy.deepcopy(state))
        # les vues numpy doivent pointer sur les nouveaux bytearray
        for area, b in self.bufs.items():
            shape = self.grids[area].shape
            self.grids[area] = np.frombuffer(b, dtype=np.uint8).reshape(shape)
        self._set_area(self.area)

    # ------------------------------------------------------------------
    # Accès aux tuiles
    # ------------------------------------------------------------------
    def tile(self, px, py):
        r = py >> 4
        c = px >> 4
        if 0 <= r < C.ROWS and 0 <= c < self.W:
            return self.buf[r * self.W + c]
        return 0

    def set_tile(self, col, row, value):
        self.buf[row * self.W + col] = value

    def solid(self, px, py):
        return C.SOLID_LUT[self.tile(px, py)]

    # ------------------------------------------------------------------
    # Boucle principale : une image
    # ------------------------------------------------------------------
    def step(self, buttons: int = 0):
        """Avance le jeu d'une image avec les boutons ``buttons`` (bits NES)."""
        if buttons & BTN_LEFT and buttons & BTN_RIGHT:
            buttons &= ~(BTN_LEFT | BTN_RIGHT)
        if buttons & BTN_UP and buttons & BTN_DOWN:
            buttons &= ~(BTN_UP | BTN_DOWN)
        self.prev_buttons = self.buttons
        self.buttons = buttons
        self.dead = False
        self.frame += 1
        mode = self.mode

        if self.freeze > 0:
            self._update_freeze()
        elif mode == "play":
            self._play_frame()
        elif mode == "dying":
            self._update_dying()
        elif mode == "pipe_down":
            self._update_pipe_down()
        elif mode == "pipe_side":
            self._update_pipe_side()
        elif mode == "pipe_up":
            self._update_pipe_up()
        elif mode in ("flag", "flag_turn", "end_walk", "castle"):
            self._update_end_sequence()
        self._update_effects()

    def _play_frame(self):
        p = self.p
        self._tick_frame_timers()
        self._player_control(self.buttons, self.prev_buttons)
        if self.mode != "play" or self.freeze:
            return
        self._update_fireballs()
        self._spawn_enemies()
        self._update_enemies()
        self._update_bumps()
        if self.mode == "play":
            self._check_pit()
            self._tick_game_timer()
        if p.x > self.max_x:
            self.max_x = p.x
            if (not self.halfway_reached and self.area == "overworld"
                    and p.x >= L.HALFWAY_PAGE * 256):
                self.halfway_reached = True

    def _tick_frame_timers(self):
        p = self.p
        if p.running_timer:
            p.running_timer -= 1
        if p.side_timer:
            p.side_timer -= 1
        if p.jump_timer:
            p.jump_timer -= 1
        if p.star_timer:
            p.star_timer -= 1
        if p.injury_timer:
            p.injury_timer -= 1
        if p.fire_anim:
            p.fire_anim -= 1
        if self.block_bounce_timer:
            self.block_bounce_timer -= 1
        for key in list(self.brick_coin_timers):
            if self.brick_coin_timers[key] > 0:
                self.brick_coin_timers[key] -= 1

    def _tick_game_timer(self):
        if not self.cfg.timer:
            return
        self.timer_tick -= 1
        if self.timer_tick <= 0:
            self.timer_tick = self.cfg.timer_frames
            if self.timer > 0:
                self.timer -= 1
                if self.timer == 0:
                    self._kill_player("time")

    # ------------------------------------------------------------------
    # Joueur : contrôle et physique (PlayerCtrlRoutine)
    # ------------------------------------------------------------------
    def _player_control(self, buttons, prev):
        p = self.p
        a_b = buttons & (BTN_A | BTN_B)
        lr = buttons & (BTN_LEFT | BTN_RIGHT)
        ud = buttons & (BTN_UP | BTN_DOWN)
        if ud & BTN_DOWN and p.state == 0 and lr:
            lr = 0
            ud = 0
        self._ud = ud

        # PlayerMovementSubs : accroupissement (grand Mario au sol)
        if p.small:
            p.crouch = False
        elif p.state == 0:
            p.crouch = bool(ud & BTN_DOWN)

        self._player_physics(a_b, lr, prev)

        if p.state == 0:
            self._get_player_anim_speed(buttons)
            if lr:
                p.facing = lr
            self._impose_friction(lr)
            p.x_scroll = self._move_player_x()
        else:
            if p.state == 1:
                if p.y_speed >= 0:
                    p.vforce = p.vforce_down
                elif not ((a_b & BTN_A) and (prev & BTN_A)):
                    if (p.jump_origin - p.y) >= p.diff_to_halt:
                        p.vforce = p.vforce_down
            else:
                p.vforce = p.vforce_down
            if lr:
                self._impose_friction(lr)
            p.x_scroll = self._move_player_x()
            self._move_player_y(p.vforce, C.PLAYER_MAX_FALL)

        if p.x_speed > 0:
            p.moving_dir = 1
        elif p.x_speed < 0:
            p.moving_dir = 2

        # tir de boule de feu (bouton B nouvellement pressé)
        if (p.status == 2 and buttons & BTN_B and not prev & BTN_B
                and not p.crouch and self.cfg.powerups):
            self._shoot_fireball()

        self._scroll_handler()
        self._player_bg_collision()
        self._update_player_anim(lr)

    def _player_physics(self, a_b, lr, prev):
        """PlayerPhysicsSub : départ du saut puis paramètres horizontaux."""
        p = self.p
        if a_b & BTN_A and not prev & BTN_A and p.state == 0:
            p.jump_timer = 0x20
            p.y_dummy = 0
            p.y_force = 0
            p.jump_origin = p.y
            p.state = 1
            idx = 0
            for thr in C.JUMP_SPEED_THRESHOLDS:
                if p.x_abs >= thr:
                    idx += 1
                else:
                    break
            p.diff_to_halt = 1
            p.vforce = C.JUMP_MFORCE[idx]
            p.vforce_down = C.FALL_MFORCE[idx]
            p.y_force = C.JUMP_INIT_MFORCE[idx]
            p.y_speed = C.JUMP_Y_SPEED[idx]
            self.stats["jumps"] += 1

        # X_Physics
        y = 0
        t = 0
        fast = False
        if p.state != 0:
            fast = p.x_abs >= C.AIR_RUN_THRESHOLD
        elif lr == p.moving_dir and a_b & BTN_B:
            p.running_timer = C.RUNNING_TIMER_RESET
            fast = True
        elif lr == p.moving_dir and p.running_timer:
            fast = True
        if not fast:
            y = 1
            t = 1
            if p.running_speed or p.x_abs >= C.FAST_FRICTION_THRESHOLD:
                t = 2
        self._max_left = C.MAX_LEFT_SPEED[y]
        self._max_right = C.MAX_RIGHT_SPEED[y]
        f = C.FRICTION[t]
        if p.facing != p.moving_dir:
            f <<= 1
        self._fric_lo = f & 0xFF
        self._fric_hi = f >> 8

    def _get_player_anim_speed(self, buttons):
        """GetPlayerAnimSpeed : vitesse d'animation, dérapage, demi-tour."""
        p = self.p
        a = p.x_abs
        if a >= C.RUN_ANIM_THRESHOLD:
            p.running_speed = a
            idx = 0
        else:
            idx = 1 if a >= C.WALK_ANIM_THRESHOLD else 2
            joy = buttons & 0x7F
            if joy:
                if (joy & 0x03) == p.moving_dir:
                    p.running_speed = 0
                elif a < C.SKID_TURN_SPEED:
                    p.moving_dir = p.facing
                    p.x_speed = 0
                    p.x_force = 0
        p.anim_set = C.PLAYER_ANIM_TIMER[idx]

    def _impose_friction(self, lr):
        p = self.p
        masked = lr & p.collision_bits
        if masked == 0:
            if p.x_speed == 0:
                p.x_abs = 0
                return
            add = p.x_speed < 0
        else:
            add = bool(masked & BTN_RIGHT)
        if add:
            s = p.x_force + self._fric_lo
            p.x_force = s & 0xFF
            p.x_speed += self._fric_hi + (s >> 8)
            if p.x_speed >= self._max_right:
                p.x_speed = self._max_right
        else:
            s = p.x_force - self._fric_lo
            borrow = 1 if s < 0 else 0
            p.x_force = s & 0xFF
            p.x_speed -= self._fric_hi + borrow
            if p.x_speed < self._max_left:
                p.x_speed = self._max_left
        p.x_abs = -p.x_speed if p.x_speed < 0 else p.x_speed

    def _move_player_x(self):
        """MoveObjectHorizontally appliqué au joueur ; renvoie les px parcourus."""
        p = self.p
        sp = p.x_speed & 0xFF
        lo = (sp << 4) & 0xFF
        hi = sp >> 4
        if hi >= 8:
            hi -= 16
        s = p.x_force + lo
        p.x_force = s & 0xFF
        moved = hi + (s >> 8)
        p.x += moved
        return moved

    def _move_player_y(self, force, max_speed):
        """ImposeGravity (virgule fixe 8.8) appliqué au joueur."""
        p = self.p
        s = p.y_dummy + p.y_force
        p.y_dummy = s & 0xFF
        p.y += p.y_speed + (s >> 8)
        s = p.y_force + force
        p.y_force = s & 0xFF
        p.y_speed += s >> 8
        if p.y_speed >= max_speed and p.y_force >= 0x80:
            p.y_speed = max_speed
            p.y_force = 0

    def _scroll_handler(self):
        p = self.p
        rel = p.x - self.cam_x
        if not self.scroll_lock and rel >= 0x50 and p.side_timer == 0:
            xs = p.x_scroll
            if xs > 0:
                amount = xs - 1 if xs >= 2 else xs
                if rel >= 0x70:
                    amount = xs
                self.cam_x = min(self.cam_x + amount, self.cam_max)
        elif (self.cfg.scroll_back and not self.scroll_lock
              and p.x_scroll < 0 and rel < 0x60):
            self.cam_x = max(0, self.cam_x + p.x_scroll)
        if p.x < self.cam_x:
            p.x = self.cam_x
            if p.x_speed < 0:
                p.x_speed = 0
        right = self.cam_x + C.SCREEN_W - 16
        if p.x > right:
            p.x = right
            if p.x_speed > 0:
                p.x_speed = 0

    # ------------------------------------------------------------------
    # Collisions joueur / décor (PlayerBGCollision)
    # ------------------------------------------------------------------
    def _player_bg_collision(self):
        p = self.p
        if p.state == 0 or p.state == 3:
            p.state = 2
        if not 0 <= p.y <= 255:
            return
        p.collision_bits = 0xFF
        if p.y >= 0xCF:
            return
        smallbox = p.small or p.crouch
        pts = C.COLL_SMALL if smallbox else C.COLL_BIG
        upper_extent = 0x10 if smallbox else 0x20

        # --- tête ---
        if p.y >= upper_extent:
            hx = p.x + pts[0][0]
            hy = p.y + pts[0][1]
            t = self.tile(hx, hy)
            if t:
                if t == C.COIN:
                    self._collect_tile_coin(hx >> 4, hy >> 4)
                    return
                if p.y_speed < 0 and (hy & 0x0F) >= 4:
                    if t in C.BUMPABLE_TILES:
                        if self.block_bounce_timer:
                            p.y_speed = 1
                        else:
                            self._head_hit(hx >> 4, hy >> 4, t)
                    elif C.SOLID_LUT[t]:
                        p.y_speed = 1

        # --- pieds ---
        fy = p.y + 32
        tl = self.tile(p.x + 3, fy)
        if tl == C.COIN:
            self._collect_tile_coin((p.x + 3) >> 4, fy >> 4)
            return
        tr = self.tile(p.x + 12, fy)
        mt = tl if tl else tr
        if not tl and tr == C.COIN:
            self._collect_tile_coin((p.x + 12) >> 4, fy >> 4)
            return
        if mt and mt not in C.CLIMB_TILES and p.y_speed >= 0 \
                and mt != C.HIDDEN_1UP and C.SOLID_LUT[mt]:
            if (fy & 0x0F) >= 5:
                self._impede(p.moving_dir)
            else:
                p.y &= ~0x0F
                if self._check_pipe_entry(tl, tr):
                    return
                p.y_speed = 0
                p.y_force = 0
                self.stomp_chain = 0
                p.state = 0

        # --- côtés (gauche puis droite) ---
        for side, ia, ib in ((2, 3, 4), (1, 5, 6)):
            if p.y >= 0x20:
                if p.y >= 0xE4:
                    return
                ax = p.x + pts[ia][0]
                ay = p.y + pts[ia][1]
                t = self.tile(ax, ay)
                if t and t != C.SPIPE_TOP_MOUTH and t not in C.CLIMB_TILES:
                    self._check_side_tile(t, side, ax, ay)
                    return
            if p.y < 8 or p.y >= 0xD0:
                return
            bx = p.x + pts[ib][0]
            by = p.y + pts[ib][1]
            t = self.tile(bx, by)
            if t:
                self._check_side_tile(t, side, bx, by)
                return

    def _check_side_tile(self, t, side, px, py):
        p = self.p
        if t == C.HIDDEN_1UP:
            return
        if t in C.CLIMB_TILES:
            low = px & 0x0F
            if 6 <= low < 10:
                self._grab_flagpole()
            return
        if t == C.COIN:
            self._collect_tile_coin(px >> 4, py >> 4)
            return
        if not C.SOLID_LUT[t]:
            return
        if (p.state == 0 and p.facing == 1 and t == C.SPIPE_BOT_MOUTH
                and self.area == "bonus"):
            self._enter_side_pipe()
            return
        self._impede(side)

    def _impede(self, side):
        """ImpedePlayerMove : repousse Mario d'1 px hors du mur."""
        p = self.p
        if side == 2:        # mur à gauche
            bit = 2
            if p.x_speed < 1:
                p.side_timer = 0x10
                p.x_speed = 0
                p.x += 1
        else:                # mur à droite
            bit = 1
            if p.x_speed >= 0:
                p.side_timer = 0x10
                p.x_speed = 0
                p.x -= 1
        p.collision_bits &= ~bit & 0xFF

    def _check_pit(self):
        if self.p.y >= 256 and self.mode == "play":
            self._kill_player("pit")

    # ------------------------------------------------------------------
    # Animation du joueur (choix de la frame à afficher)
    # ------------------------------------------------------------------
    def _update_player_anim(self, lr):
        p = self.p
        p.skidding = False
        if p.state == 0:
            if p.x_speed == 0:
                p.anim_frame = 0
                p.anim_timer = 0
            else:
                if lr and lr != p.moving_dir and p.x_abs >= C.SKID_TURN_SPEED:
                    p.skidding = True
                if p.anim_timer <= 0:
                    p.anim_timer = p.anim_set
                    p.anim_frame = (p.anim_frame % 3) + 1
                else:
                    p.anim_timer -= 1

    # ------------------------------------------------------------------
    # Mouvements génériques (virgule fixe NES)
    # ------------------------------------------------------------------
    @staticmethod
    def _move_x(o):
        sp = o.x_speed & 0xFF
        lo = (sp << 4) & 0xFF
        hi = sp >> 4
        if hi >= 8:
            hi -= 16
        s = o.x_force + lo
        o.x_force = s & 0xFF
        moved = hi + (s >> 8)
        o.x += moved
        return moved

    @staticmethod
    def _move_y(o, force, max_speed):
        s = o.y_dummy + o.y_force
        o.y_dummy = s & 0xFF
        o.y += o.y_speed + (s >> 8)
        s = o.y_force + force
        o.y_force = s & 0xFF
        o.y_speed += s >> 8
        if o.y_speed >= max_speed and o.y_force >= 0x80:
            o.y_speed = max_speed
            o.y_force = 0

    # ------------------------------------------------------------------
    # Score, pièces, vies
    # ------------------------------------------------------------------
    def _add_score(self, points, x=None, y=None):
        if points == ONE_UP:
            self._add_life()
            if x is not None:
                self.effects.append(Effect("score", x, y, value=ONE_UP))
            return
        self.score += points
        if x is not None:
            self.effects.append(Effect("score", x, y, value=points))

    def _add_life(self):
        self.lives += 1
        self.stats["one_ups"] += 1

    def _add_coin(self):
        self.coins += 1
        self.stats["coins"] += 1
        if self.coins >= 100:
            self.coins -= 100
            self._add_life()

    def _collect_tile_coin(self, col, row):
        self.set_tile(col, row, C.EMPTY)
        self._add_coin()
        self._add_score(200)

    # ------------------------------------------------------------------
    # Blocs frappés par dessous
    # ------------------------------------------------------------------
    def _head_hit(self, col, row, t):
        p = self.p
        self.stats["blocks_bumped"] += 1
        self.block_bounce_timer = C.BLOCK_BOUNCE_FRAMES
        if t in C.BREAKABLE_TILES and not p.small:
            # BrickShatter : la brique explose, Mario continue de monter
            self.set_tile(col, row, C.EMPTY)
            self._hit_objects_on_block(col, row)
            self._spawn_debris(col, row)
            p.y_speed = C.BRICK_BREAK_Y_SPEED
            self._add_score(50)
            self.stats["bricks_broken"] += 1
            return
        # BumpBlock
        p.y_speed = 0
        final = t
        if t == C.BRICK_COIN:
            key = (self.area, col, row)
            if key not in self.brick_coin_timers:
                self.brick_coin_timers[key] = C.BRICK_COIN_TIME
            elif self.brick_coin_timers[key] == 0:
                final = C.USED
            self._block_coin(col, row)
        elif t == C.QBLOCK_COIN:
            final = C.USED
            self.stats["qblocks_hit"] += 1
            self._block_coin(col, row)
        elif t in (C.QBLOCK_POWERUP, C.BRICK_POWERUP):
            final = C.USED
            self.stats["powerup_blocks"] += 1
            if t == C.QBLOCK_POWERUP:
                self.stats["qblocks_hit"] += 1
            if self.cfg.powerups:
                self._spawn_item("mushroom" if p.small else "flower", col, row)
            else:
                self._block_coin(col, row)
        elif t == C.BRICK_STAR:
            final = C.USED
            if self.cfg.powerups:
                self._spawn_item("star", col, row)
            else:
                self._block_coin(col, row)
        elif t == C.HIDDEN_1UP:
            final = C.USED
            self.stats["hidden_blocks"] += 1
            self._spawn_item("1up", col, row)
        self.set_tile(col, row, final)
        self.bumps.append(BlockBump(col, row, final))
        self._hit_objects_on_block(col, row)

    def _block_coin(self, col, row):
        self._add_coin()
        self.score += 200
        self.effects.append(Effect("coin", col * TILE, row * TILE - 16,
                                   vy=-5.0, value=200))

    def _spawn_debris(self, col, row):
        x = col * TILE
        y = row * TILE
        for dx, dy, vx, vy in ((0, 0, -1.0, -6.0), (8, 0, 1.0, -6.0),
                               (0, 8, -1.0, -4.0), (8, 8, 1.0, -4.0)):
            self.effects.append(Effect("debris", x + dx, y + dy, vx, vy))

    def _hit_objects_on_block(self, col, row):
        """Tue les ennemis / fait sauter les objets posés sur le bloc frappé."""
        top = row * TILE
        x0 = col * TILE
        for e in self.enemies:
            if not e.alive or e.state in ("dead", "flat", "rise"):
                continue
            feet = e.y + 24
            if abs(feet - top) > 4 or e.x + 16 <= x0 or e.x >= x0 + 16:
                continue
            if e.is_item:
                if e.kind != "flower":
                    e.y_speed = -3
                    e.y_force = 0
                    e.falling = True
                    center = e.x + 8 - (x0 + 8)
                    sp = abs(e.x_speed) or C.POWERUP_SPEED
                    e.x_speed = sp if center >= 0 else -sp
                    e.moving_dir = 1 if e.x_speed > 0 else 2
            else:
                self._defeat_enemy(e, 100 if e.kind == "goomba" else 200)

    def _update_bumps(self):
        keep = []
        for b in self.bumps:
            b.t += 1
            t = b.t
            b.offset = -((t * (16 - t) * 6) // 64) if t < 16 else 0
            if t < 16:
                keep.append(b)
        self.bumps = keep

    # ------------------------------------------------------------------
    # Objets bonus
    # ------------------------------------------------------------------
    def _spawn_item(self, kind, col, row):
        self.enemy_uid += 1
        e = Enemy(kind, col * TILE, row * TILE - 8, 0, uid=1000 + self.enemy_uid)
        e.state = "rise"
        e.rise = 0
        self.enemies.append(e)

    def _update_item(self, e):
        if e.state == "rise":
            if self.frame & 3 == 0:
                e.y -= 1
                e.rise += 1
                if e.rise >= 16:
                    e.state = "walk"
                    if e.kind != "flower":
                        e.x_speed = C.POWERUP_SPEED
                        e.moving_dir = 1
                    if e.kind == "star":
                        e.falling = True
                        e.y_speed = -4
                        e.y_force = 0x80
            return
        if e.kind == "flower":
            return
        self._move_x(e)
        if e.falling:
            grav = 0x20 if e.kind == "star" else C.ENEMY_GRAVITY
            self._move_y(e, grav, C.ENEMY_MAX_FALL)
        self._object_bg(e)

    def _collect_item(self, e):
        e.alive = False
        p = self.p
        cx, cy = e.x, e.y
        if e.kind == "1up":
            self._add_score(ONE_UP, cx, cy)
            return
        self.stats["powerups"] += 1
        if e.kind in ("mushroom", "flower"):
            self.stats[e.kind + "s"] += 1
        self._add_score(1000, cx, cy)
        if e.kind == "star":
            p.star_timer = C.STAR_DURATION
        elif p.status == 0:
            p.status = 1
            p.crouch = False
            self.freeze = C.GROW_FRAMES
            self.freeze_kind = "grow"
        elif p.status == 1:
            p.status = 2
            self.freeze = C.FIRE_FRAMES
            self.freeze_kind = "fire"

    # ------------------------------------------------------------------
    # Ennemis
    # ------------------------------------------------------------------
    def _spawn_enemies(self):
        """ProcessEnemyData : traite au plus un objet ennemi par image.

        L'objet suivant est chargé quand sa colonne arrive à moins de 48 px
        du bord droit de l'écran.  S'il est déjà dans l'écran (retour de la
        salle bonus, départ en cours de niveau) il est ignoré, comme sur NES.
        Un ennemi seul apparaît à sa colonne ; un groupe apparaît au bord
        droit de l'écran, ses membres espacés de 24 px.  Le jeu n'a que
        5 emplacements d'ennemis.
        """
        if not self.cfg.enemies or self.area != "overworld":
            return
        right = self.cam_x + 255
        limit = (right + C.ENEMY_SPAWN_MARGIN) & ~0x0F
        for i, sp in enumerate(self.enemy_spawns):
            if i in self.spawned:
                continue
            cx = sp.col * TILE
            if cx > limit:
                return
            used = sum(1 for e in self.enemies if e.alive and not e.is_item)
            free = L.MAX_ENEMIES - used
            if cx >= right and free <= 0 and not sp.group:
                return                      # pas de place : on réessaie
            self.spawned.add(i)
            if cx < right:
                return                      # déjà à l'écran : ignoré
            if sp.group:
                xs = [right + L.GROUP_SPACING * k for k in range(sp.count)]
                xs = xs[:max(free, 0)]
            else:
                xs = [cx]
            for k, x in enumerate(xs):
                e = Enemy(sp.kind, x, sp.y, C.ENEMY_SPEED, uid=i * 10 + k)
                e.falling = True            # apparaît 8 px au-dessus du sol
                self.enemies.append(e)
            return

    def _update_enemies(self):
        cam = self.cam_x
        for e in self.enemies:
            if not e.alive:
                continue
            e.anim += 1
            if e.is_item:
                self._update_item(e)
            else:
                st = e.state
                if st == "dead":
                    self._move_x(e)
                    self._move_y(e, C.ENEMY_GRAVITY, 4)
                elif st == "flat":
                    e.timer -= 1
                    if e.timer <= 0:
                        e.alive = False
                elif st == "shell":
                    e.timer -= 1
                    if e.falling:
                        self._move_y(e, C.ENEMY_GRAVITY, C.ENEMY_MAX_FALL)
                    self._object_bg(e)
                    if e.timer <= 0:
                        e.state = "walk"
                        e.x_speed = C.REVIVED_SPEEDS[self.frame & 1]
                        e.moving_dir = 1 if e.x_speed > 0 else 2
                        e.coll_flag = False
                else:          # walk / shell_move
                    self._move_x(e)
                    if e.falling:
                        self._move_y(e, C.ENEMY_GRAVITY, C.ENEMY_MAX_FALL)
                    self._object_bg(e)
            if (e.x < cam - C.ENEMY_DESPAWN_MARGIN
                    or e.x > cam + C.SCREEN_W + C.ENEMY_DESPAWN_MARGIN
                    or e.y > 256):
                e.alive = False
                # caméra arrière : un ennemi sorti par la droite réapparaîtra
                # (quand tous les membres de son objet ont disparu)
                if (self.cfg.scroll_back and e.uid < 1000 and e.state == "walk"
                        and e.x > cam + C.SCREEN_W):
                    idx = e.uid // 10
                    if not any(o.alive and o.uid // 10 == idx
                               for o in self.enemies if o.uid < 1000):
                        self.spawned.discard(idx)
        if self.frame & 1 == 0:
            self._player_enemy_collisions()
        self._enemy_enemy_collisions()
        self.enemies = [e for e in self.enemies if e.alive]

    def _object_bg(self, e):
        """Collisions ennemi/objet avec le décor (sol, murs, trous)."""
        fy = e.y + 24
        t = self.tile(e.x + 8, fy)
        on_solid = C.SOLID_LUT[t]
        if e.falling:
            if e.y_speed >= 0 and on_solid:
                e.y = (fy & ~0x0F) - 24
                e.y_speed = 0
                e.y_force = 0
                e.falling = False
                if e.kind == "star":
                    e.falling = True
                    e.y_speed = -4
                    e.y_force = 0x80
        elif not on_solid:
            e.falling = True
            e.y_speed = 0
            e.y_force = 0
        if e.x_speed == 0 or e.y < 0x20 - 24:
            return
        sx = e.x + 16 if e.x_speed > 0 else e.x
        if C.SOLID_LUT[self.tile(sx, e.y + 20)]:
            e.x_speed = -e.x_speed
            e.moving_dir = 3 - e.moving_dir

    def _enemy_box(self, e):
        b = C.BBOX_GOOMBA if e.kind == "goomba" else C.BBOX_KOOPA
        return e.x + b[0], e.y + b[1], e.x + b[2], e.y + b[3]

    def _player_box(self):
        p = self.p
        if p.crouch:
            b = C.BBOX_CROUCH
        elif p.small:
            b = C.BBOX_SMALL
        else:
            b = C.BBOX_BIG
        return p.x + b[0], p.y + b[1], p.x + b[2], p.y + b[3]

    def _player_enemy_collisions(self):
        p = self.p
        if self.mode != "play" or p.y >= 224 or p.y < -32:
            return
        px1, py1, px2, py2 = self._player_box()
        cam = self.cam_x
        for e in self.enemies:
            if not e.alive or e.state in ("dead", "flat"):
                continue
            if e.x + 16 < cam or e.x > cam + C.SCREEN_W:
                continue
            if e.is_item:
                bx = C.BBOX_POWERUP
                ex1, ey1, ex2, ey2 = (e.x + bx[0], e.y + bx[1],
                                      e.x + bx[2], e.y + bx[3])
            else:
                ex1, ey1, ex2, ey2 = self._enemy_box(e)
            if px2 < ex1 or px1 > ex2 or py2 < ey1 or py1 > ey2:
                e.coll_flag = False
                continue
            if e.is_item:
                self._collect_item(e)
                continue
            if p.star_timer:
                self._defeat_enemy(e, 100 if e.kind == "goomba" else 200)
                continue
            if e.coll_flag:
                continue
            e.coll_flag = True
            if e.kind == "koopa" and e.state == "shell":
                self._kick_shell(e)
                continue
            if p.y_speed > 0:
                self._stomp(e)
                continue
            if p.injury_timer:
                continue
            if p.x < e.x:
                if e.moving_dir == 1:
                    e.x_speed = -e.x_speed
                    e.moving_dir = 2
            elif e.moving_dir == 2:
                e.x_speed = -e.x_speed
                e.moving_dir = 1
            self._injure_player()
            if self.mode != "play":
                return

    def _stomp(self, e):
        p = self.p
        self.stomp_chain += 1
        idx = self.stomp_chain
        pts = FLOATEY_POINTS[idx] if idx <= 10 else ONE_UP
        self._add_score(pts, e.x, e.y)
        self.stats["stomps"] += 1
        if e.kind == "goomba":
            e.state = "flat"
            e.timer = C.GOOMBA_FLAT_TIME
            e.x_speed = 0
            self.stats["enemies_killed"] += 1
            self.stats["goombas_killed"] += 1
        else:
            if e.state == "walk":
                self.stats["enemies_killed"] += 1
                self.stats["koopas_killed"] += 1
            e.state = "shell"
            e.timer = C.KOOPA_REVIVE
            e.x_speed = 0
        p.y_speed = C.STOMP_BOUNCE_SPEED

    def _kick_shell(self, e):
        p = self.p
        e.state = "shell_move"
        e.chain = 0
        if e.x - p.x >= 0:
            e.x_speed = C.SHELL_SPEED
            e.moving_dir = 1
        else:
            e.x_speed = -C.SHELL_SPEED
            e.moving_dir = 2
        idx = min(3 + self.stomp_chain, 10)
        self._add_score(FLOATEY_POINTS[idx], e.x, e.y)
        self.stats["shells_kicked"] += 1

    def _defeat_enemy(self, e, points=100):
        """Ennemi retourné (boule de feu, étoile, carapace, bloc frappé)."""
        if e.state in ("dead", "flat") or not e.alive:
            return
        was_walking = e.state == "walk"
        e.state = "dead"
        e.flip = True
        e.y_speed = -3
        e.y_force = 0
        e.falling = True
        e.x_speed = 0x08 if e.x_speed >= 0 else -0x08
        if points:
            self._add_score(points, e.x, e.y)
        if was_walking or e.kind == "goomba":
            self.stats["enemies_killed"] += 1
            key = "goombas_killed" if e.kind == "goomba" else "koopas_killed"
            self.stats[key] += 1

    def _enemy_enemy_collisions(self):
        act = [e for e in self.enemies
               if e.alive and not e.is_item
               and e.state in ("walk", "shell", "shell_move")]
        n = len(act)
        if n < 2:
            self.enemy_pairs.clear()
            return
        touching = set()
        for i in range(n):
            a = act[i]
            for j in range(i + 1, n):
                b = act[j]
                if abs(a.x - b.x) >= 16 or abs(a.y - b.y) >= 16:
                    continue
                if not (a.alive and b.alive):
                    continue
                if a.state in ("dead",) or b.state in ("dead",):
                    continue
                if a.state == "shell_move" or b.state == "shell_move":
                    shell, victim = (a, b) if a.state == "shell_move" else (b, a)
                    if victim.state == "shell_move":
                        self._defeat_enemy(a, 0)
                        self._defeat_enemy(b, 0)
                        continue
                    k = min(shell.chain, len(C.SHELL_CHAIN_POINTS) - 1)
                    shell.chain += 1
                    self._defeat_enemy(victim, C.SHELL_CHAIN_POINTS[k])
                    continue
                key = (min(a.uid, b.uid), max(a.uid, b.uid))
                touching.add(key)
                if key in self.enemy_pairs:
                    continue
                for e in (a, b):
                    if e.state == "walk":
                        e.x_speed = -e.x_speed
                        e.moving_dir = 3 - e.moving_dir
        self.enemy_pairs = touching

    # ------------------------------------------------------------------
    # Dégâts et mort du joueur
    # ------------------------------------------------------------------
    def _injure_player(self):
        p = self.p
        if p.injury_timer:
            return
        if p.status == 0:
            self._kill_player("enemy")
            return
        p.status = 0
        p.crouch = False
        p.injury_timer = C.INJURY_DURATION
        self.freeze = C.SHRINK_FRAMES
        self.freeze_kind = "shrink"

    def _kill_player(self, cause):
        if self.mode == "dying":
            return
        p = self.p
        self.dead = True
        self.death_cause = cause
        self.stats["deaths"] += 1
        self.lives -= 1
        self.mode = "dying"
        self.mode_timer = 0
        p.x_speed = 0
        p.star_timer = 0
        if cause != "pit":
            p.status = 0
            p.y_speed = 0
            p.y_force = 0

    def _update_dying(self):
        p = self.p
        self.mode_timer += 1
        t = self.mode_timer
        if self.death_cause != "pit":
            if t == C.DEATH_PAUSE:
                p.y_speed = -4
                p.y_force = 0
            elif t > C.DEATH_PAUSE and p.y < 300:
                self._move_y(p, 0x28, 4)
        if t >= 200:
            if self.lives > 0:
                keep = (self.lives, self.score, self.coins, self.stats,
                        self.halfway_reached, self.frame)
                half = self.halfway_reached and self.cfg.halfway
                self._load_level(start_at_halfway=half)
                (self.lives, self.score, self.coins, self.stats,
                 self.halfway_reached, self.frame) = keep
            else:
                self.game_over = True
                self.mode = "gameover"

    def _update_freeze(self):
        self.freeze -= 1
        if self.freeze <= 0:
            self.freeze = 0
            self.freeze_kind = None

    # ------------------------------------------------------------------
    # Boules de feu
    # ------------------------------------------------------------------
    def _shoot_fireball(self):
        active = sum(1 for f in self.fireballs if f.alive and not f.explode)
        if active >= 2:
            return
        p = self.p
        right = p.facing == 1
        fx = p.x + (8 if right else 0)
        f = Fireball(fx, p.y + 8,
                     C.FIREBALL_SPEED if right else -C.FIREBALL_SPEED)
        self.fireballs.append(f)
        p.fire_anim = 8
        self.stats["fireballs"] += 1

    def _update_fireballs(self):
        if not self.fireballs:
            return
        cam = self.cam_x
        for f in self.fireballs:
            if not f.alive:
                continue
            f.anim += 1
            if f.explode:
                f.explode -= 1
                if f.explode == 0:
                    f.alive = False
                continue
            self._move_x(f)
            self._move_y(f, C.FIREBALL_GRAVITY, C.FIREBALL_MAX_FALL)
            if f.x < cam - 8 or f.x > cam + C.SCREEN_W or f.y > 240:
                f.alive = False
                continue
            front = f.x + 8 if f.x_speed > 0 else f.x
            if C.SOLID_LUT[self.tile(front, f.y + 4)]:
                f.explode = 12
                continue
            by = f.y + 8
            if f.y_speed >= 0 and C.SOLID_LUT[self.tile(f.x + 4, by)]:
                f.y = (by & ~0x0F) - 8
                f.y_speed = C.FIREBALL_BOUNCE
                f.y_force = 0
            for e in self.enemies:
                if (not e.alive or e.is_item
                        or e.state in ("dead", "flat")):
                    continue
                ex1, ey1, ex2, ey2 = self._enemy_box(e)
                if f.x + 8 < ex1 or f.x > ex2 or f.y + 8 < ey1 or f.y > ey2:
                    continue
                self._defeat_enemy(e, 100 if e.kind == "goomba" else 200)
                f.explode = 12
                break
        self.fireballs = [f for f in self.fireballs if f.alive]

    # ------------------------------------------------------------------
    # Tuyaux et salle bonus
    # ------------------------------------------------------------------
    def _check_pipe_entry(self, tl, tr):
        if (not self.cfg.bonus_room or self.area != "overworld"
                or self._permuted()):
            return False
        if not self._ud & BTN_DOWN:
            return False
        p = self.p
        if tl == C.PIPE_TL and tr == C.PIPE_TR \
                and ((p.x + 3) >> 4) == L.WARP_PIPE_COL:
            self.mode = "pipe_down"
            self.mode_timer = 0
            p.state = 0
            p.x_speed = 0
            p.y_speed = 0
            p.y_force = 0
            p.behind_bg = True
            p.crouch = False
            return True
        return False

    def _update_pipe_down(self):
        p = self.p
        self.mode_timer += 1
        p.y += 1
        self._tick_game_timer()
        if self.mode_timer >= C.PIPE_ENTRY_FRAMES:
            self._set_area("bonus")
            self.cam_x = 0
            self.enemies = []
            self.fireballs = []
            self.bumps = []
            p.x = L.BONUS_ENTRY_X
            p.y = L.BONUS_ENTRY_Y
            p.state = 2
            p.y_speed = 0
            p.y_force = 0
            p.behind_bg = False
            self.mode = "play"
            self.stats["bonus_room"] += 1

    def _enter_side_pipe(self):
        p = self.p
        self.mode = "pipe_side"
        self.mode_timer = 0
        p.x_speed = 0
        p.facing = 1
        p.behind_bg = True

    def _update_pipe_side(self):
        p = self.p
        self.mode_timer += 1
        if self.mode_timer & 1:
            p.x += 1
        p.anim_set = 4
        if p.anim_timer <= 0:
            p.anim_timer = p.anim_set
            p.anim_frame = (p.anim_frame % 3) + 1
        else:
            p.anim_timer -= 1
        self._tick_game_timer()
        if self.mode_timer >= 40:
            self._set_area("overworld")
            self.cam_x = min(10 * 256, self.cam_max)
            self.enemies = []
            self.fireballs = []
            self.bumps = []
            p.x = L.EXIT_PIPE_COL * TILE + 8
            p.y = (13 - 2) * TILE          # haut du tuyau (hauteur 2)
            p.x_speed = 0
            p.state = 0
            p.behind_bg = True
            p.anim_frame = 0
            self.mode = "pipe_up"
            self.mode_timer = 0

    def _update_pipe_up(self):
        p = self.p
        self.mode_timer += 1
        self._tick_game_timer()
        target = (13 - 2) * TILE - 32
        if p.y > target:
            p.y -= 1
        else:
            p.behind_bg = False
            p.state = 0
            p.y_speed = 0
            self.mode = "play"

    # ------------------------------------------------------------------
    # Drapeau, château et fin de niveau
    # ------------------------------------------------------------------
    def _grab_flagpole(self):
        if self.mode != "play" or self.area != "overworld":
            return
        p = self.p
        self.level_complete = True
        idx = 4
        while idx > 0 and p.y < C.FLAGPOLE_Y_DATA[idx]:
            idx -= 1
        self.flag_score_idx = idx
        self.stats["flag_points"] = C.FLAGPOLE_POINTS[idx]
        self.scroll_lock = True
        self.fireworks = {1: 1, 3: 3, 6: 6}.get(self.timer % 10, 0)
        p.state = 3
        p.x_speed = 0
        p.y_speed = 0
        p.y_force = 0
        p.facing = 1
        p.star_timer = 0
        p.x = L.FLAGPOLE_COL * TILE - 7
        self.enemies = [e for e in self.enemies if e.is_item]
        self.fireballs = []
        self.mode = "flag"
        self.mode_timer = 0
        self.flag_score_y = 184
        if not self.cfg.end_sequence:
            self._add_score(C.FLAGPOLE_POINTS[idx])
            self.finished = True
            self.mode = "complete"

    def _update_end_sequence(self):
        p = self.p
        self.mode_timer += 1
        mode = self.mode
        if mode == "flag":
            bottom = 160
            if p.y < bottom:
                p.y = min(p.y + 2, bottom)
            if self.flag_y < 176:
                self.flag_y += 2
                self.flag_score_y -= 2
            elif p.y >= bottom:
                self._add_score(C.FLAGPOLE_POINTS[self.flag_score_idx])
                self.mode = "flag_turn"
                self.mode_timer = 0
                p.x = L.FLAGPOLE_COL * TILE + 9
                p.facing = 2
        elif mode == "flag_turn":
            if self.mode_timer >= 20:
                self.mode = "end_walk"
                self.mode_timer = 0
                p.facing = 1
                p.state = 2
                self.scroll_lock = False
        elif mode == "end_walk":
            self._player_control(BTN_RIGHT, BTN_RIGHT)
            self.mode = "end_walk"
            if p.x >= L.CASTLE_DOOR_COL * TILE:
                p.visible = False
                self.mode = "castle"
                self.mode_timer = 0
        elif mode == "castle":
            if self.timer > 0:
                step = min(self.timer, 1)
                self.timer -= step
                self.score += 50 * step
                self.mode_timer = 0
            elif self.castle_flag < 16:
                self.castle_flag += 1
                self.mode_timer = 0
            elif self.fireworks > 0:
                if self.mode_timer >= 30:
                    self.fireworks -= 1
                    self.score += 500
                    self.mode_timer = 0
                    fx = (L.CASTLE_COL + 1 + (self.fireworks % 3)) * TILE
                    self.effects.append(Effect("firework", fx,
                                               64 + 16 * (self.fireworks % 2)))
            elif self.mode_timer >= 90:
                self.finished = True
                self.mode = "complete"

    # ------------------------------------------------------------------
    # Effets visuels
    # ------------------------------------------------------------------
    def _update_effects(self):
        if not self.effects:
            return
        keep = []
        for fx in self.effects:
            fx.t += 1
            k = fx.kind
            if k == "debris":
                fx.x += fx.vx
                fx.y += fx.vy
                fx.vy += 0.4
                if fx.y < 260:
                    keep.append(fx)
            elif k == "coin":
                fx.y += fx.vy
                fx.vy += 0.3
                if fx.t < 32:
                    keep.append(fx)
                else:
                    keep.append(Effect("score", fx.x, fx.y, value=fx.value))
            elif k == "score":
                if fx.t < 48:
                    fx.y -= 1
                    keep.append(fx)
            elif k == "firework":
                if fx.t < 24:
                    keep.append(fx)
        self.effects = keep

    # ------------------------------------------------------------------
    # Requêtes utiles (observations RL)
    # ------------------------------------------------------------------
    @property
    def mario_x(self):
        return self.p.x

    @property
    def mario_screen_y(self):
        """Ordonnée des pieds de Mario (px, 208 = sur le sol)."""
        return self.p.y + 32

    def mario_tile(self):
        """(colonne, rangée) NES de la case où se trouvent les pieds de Mario.

        Mario debout sur le sol est en rangée 12 (le sol occupe 13-14).
        """
        p = self.p
        return (p.x + 8) >> 4, (p.y + 31) >> 4

    def info(self):
        p = self.p
        col, row = self.mario_tile()
        return {
            "x": p.x, "y": p.y + 32, "x_speed": p.x_speed,
            "y_speed": p.y_speed, "col": col, "row": row,
            "status": ("small", "tall", "fireball")[p.status],
            "state": p.state, "on_ground": p.state == 0,
            "area": self.area, "camera_x": self.cam_x,
            "score": self.score, "coins": self.coins, "lives": self.lives,
            "time": self.timer, "frame": self.frame, "mode": self.mode,
            "flag_get": self.level_complete, "dead": self.dead,
            "death_cause": self.death_cause, "max_x": self.max_x,
            "star": p.star_timer > 0, "stats": dict(self.stats),
        }
