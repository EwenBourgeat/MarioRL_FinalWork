"""Environnement Gymnasium sur le moteur fidèle au jeu NES.

Exemple ::

    import gymnasium as gym
    import mario_env  # enregistre les environnements

    env = gym.make("MarioNES-v0", obs_type="tiles", actions="simple")
    obs, info = env.reset(seed=0)
    obs, reward, terminated, truncated, info = env.step(env.action_space.sample())
"""

from __future__ import annotations

import numpy as np
import gymnasium as gym
from gymnasium import spaces

from .. import constants as C
from .. import level_data as L
from ..game import Game, GameConfig
from .common import (
    LEVEL_VERSIONS, TILE_TO_OBS, TILE_TO_PAPER, RewardConfig, resolve_actions,
    resolve_reward,
)

OBS_TYPES = ("tiles", "rgb", "vector", "vector_plus", "paper")
SOLID_NP = np.asarray(C.SOLID_LUT, dtype=bool)
N_ENEMY_FEATURES = 5
AHEAD = 16
# vue « vector_plus » (route A) : objet le plus proche, pièces, bloc ?
# devant, distance au tuyau de la salle bonus
N_COIN_FEATURES = 5
ITEM_CODE = {"mushroom": 0.25, "flower": 0.5, "star": 0.75, "1up": 1.0}
QBLOCK_LUT = np.zeros(256, dtype=bool)
QBLOCK_LUT[[C.QBLOCK_COIN, C.QBLOCK_POWERUP]] = True
# milieu de la fenêtre où « bas » fait entrer dans le tuyau (x de 916 à 924)
WARP_X = L.WARP_PIPE_COL * C.TILE + 8
# dans la salle bonus : Mario contre l'embouchure du tuyau de sortie (col. 13)
BONUS_EXIT_X = 13 * C.TILE - 8
N_PLUS_FEATURES = 4 + 3 * N_COIN_FEATURES + 4 + 1


class MarioNESEnv(gym.Env):
    """Super Mario Bros. 1-1 avec la physique NES (60 images/s).

    Paramètres principaux
    ---------------------
    obs_type : "tiles" (grille 13x16 de codes, défaut), "rgb" (pixels),
        "vector" (caractéristiques continues), "vector_plus" (vector + objet
        le plus proche, pièces, bloc ? devant, tuyau de la salle bonus) ou
        "paper" (tuple discret au format de l'article : colonne, rangée,
        phase de saut, viewport).
    actions : "simple" (7 actions, défaut), "right_only", "complex",
        "paper" (rien / droite / saut) ou liste de combinaisons de boutons.
    frame_skip : nombre d'images NES par pas (l'action est maintenue).
    level : "v1", "v2", "v3" (versions de l'article) ou "full" (défaut).
    reward : "paper" (défaut), "progress", "score", dict, RewardConfig
        ou fonction ``f(prev_info, info) -> float``.
    lives : 1 par défaut (l'épisode s'arrête à la première mort).
    segment_order : ordre des segments A-F (ex. "FEDCBA") pour le curriculum.
    """

    metadata = {"render_modes": ["human", "rgb_array"], "render_fps": 60}

    def __init__(self, render_mode=None, obs_type="tiles", actions="simple",
                 frame_skip=4, level="full", reward="paper", lives=1,
                 start_status="small", segment_order=None,
                 max_episode_steps=None, terminate_on_flag=True,
                 tile_view="screen", view_cols=(4, 12), rgb_size=None,
                 grayscale=False, paper_viewport=28,
                 paper_block_rows=(4, 8), paper_enemy_rows=(7, 11),
                 noop_max=0, timer=True, render_scale=3, **game_kwargs):
        super().__init__()
        if obs_type not in OBS_TYPES:
            raise ValueError(f"obs_type doit être dans {OBS_TYPES}")
        if level not in LEVEL_VERSIONS:
            raise ValueError(f"level doit être dans {list(LEVEL_VERSIONS)}")
        self.render_mode = render_mode
        self.obs_type = obs_type
        self.frame_skip = int(frame_skip)
        self.level = level
        self.combos, self._buttons = resolve_actions(actions)
        self.reward_cfg = resolve_reward(reward)
        self.lives = lives
        self.terminate_on_flag = terminate_on_flag
        self.max_episode_steps = max_episode_steps
        self.tile_view = tile_view
        self.view_cols = tuple(view_cols)
        self.rgb_size = rgb_size
        self.grayscale = grayscale
        self.paper_viewport = int(paper_viewport)
        self.paper_block_rows = tuple(paper_block_rows)
        self.paper_enemy_rows = tuple(paper_enemy_rows)
        self.noop_max = int(noop_max)
        self.render_scale = render_scale

        status = {"small": 0, "big": 1, "tall": 1, "fire": 2,
                  "fireball": 2}.get(start_status, start_status)
        opts = dict(LEVEL_VERSIONS[level])
        opts.update(game_kwargs)
        self.cfg = GameConfig(lives=lives, start_status=status,
                              segment_order=segment_order, timer=timer,
                              **opts)
        self.game = Game(self.cfg)
        self._renderer = None
        self._window = None
        self._clock = None
        self._steps = 0
        self._prev = None
        # fonction appelée après chaque image NES (ex. pour afficher une
        # partie image par image dans le menu MODELES)
        self.frame_hook = None

        self.action_space = spaces.Discrete(len(self._buttons))
        self.observation_space = self._make_obs_space()

    # ------------------------------------------------------------------
    def _make_obs_space(self):
        if self.obs_type == "tiles":
            w = 16 if self.tile_view == "screen" else sum(self.view_cols)
            return spaces.Box(0, C.N_OBS_CODES - 1, (13, w), dtype=np.uint8)
        if self.obs_type == "rgb":
            h, w = self.rgb_size if self.rgb_size else (C.SCREEN_H, C.SCREEN_W)
            shape = (h, w) if self.grayscale else (h, w, 3)
            return spaces.Box(0, 255, shape, dtype=np.uint8)
        if self.obs_type in ("vector", "vector_plus"):
            n = 10 + 4 * N_ENEMY_FEATURES + 2 * AHEAD
            if self.obs_type == "vector_plus":
                n += N_PLUS_FEATURES
            return spaces.Box(-4.0, 4.0, (n,), dtype=np.float32)
        vp = self.paper_viewport
        nvec = [L.LEVEL_COLS, 14, 3]
        nvec += [C.N_PAPER_CODES] * (vp * len(self.paper_block_rows))
        nvec += [C.P_GOOMBA + 1] * (vp * len(self.paper_enemy_rows))
        return spaces.MultiDiscrete(np.array(nvec, dtype=np.int64))

    @property
    def renderer(self):
        if self._renderer is None or self._renderer.game is not self.game:
            from ..renderer import Renderer
            self._renderer = Renderer(self.game)
        return self._renderer

    # ------------------------------------------------------------------
    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)
        options = options or {}
        if "segment_order" in options:
            self.cfg.segment_order = options["segment_order"]
        self.game = Game(self.cfg)
        if "start_x" in options or "start_col" in options:
            x = options.get("start_x")
            if x is None:
                x = int(options["start_col"]) * C.TILE
            self._teleport(int(x))
        self._steps = 0
        if self.noop_max:
            for _ in range(int(self.np_random.integers(0, self.noop_max + 1))):
                self.game.step(0)
        info = self._info()
        self._prev = info
        if self.render_mode == "human":
            self.render()
        return self._obs(), info

    def _teleport(self, x):
        """Place Mario à l'abscisse x (curriculum / départ intermédiaire)."""
        g = self.game
        col = x // C.TILE
        y = C.GROUND_ROW * C.TILE
        for r in range(2, C.ROWS):
            if C.SOLID_LUT[g.grid[r, col]] or C.SOLID_LUT[g.grid[r, col + 1]]:
                y = r * C.TILE
                break
        g.p.x = x
        g.p.y = y - 32
        g.p.state = 2
        g.cam_x = max(0, min(x - 80, g.cam_max))
        g.max_x = x

    def step(self, action):
        g = self.game
        buttons = self._buttons[int(action)]
        human = self.render_mode == "human"
        for _ in range(self.frame_skip):
            g.step(buttons)
            if human:
                self.render()
            if self.frame_hook is not None:
                self.frame_hook()
            if g.dead or g.level_complete:
                break
        died = g.dead
        cause = g.death_cause
        # mort avec des vies restantes : on saute l'animation
        if died and g.lives > 0 and g.mode == "dying":
            while g.mode == "dying":
                g.step(0)
        if g.level_complete and not self.terminate_on_flag:
            while not g.finished:
                g.step(0)
                if human:
                    self.render()
                if self.frame_hook is not None:
                    self.frame_hook()
        self._steps += 1
        info = self._info()
        info["dead"] = died
        info["death_cause"] = cause if died else None
        reward = self._reward(self._prev, info, int(action))
        self._prev = info
        terminated = bool(
            (died and g.lives <= 0) or g.game_over
            or (g.level_complete and (self.terminate_on_flag or g.finished)))
        truncated = bool(self.max_episode_steps is not None
                         and self._steps >= self.max_episode_steps
                         and not terminated)
        return self._obs(), reward, terminated, truncated, info

    # ------------------------------------------------------------------
    def _info(self):
        g = self.game
        info = g.info()
        info.update({
            "x_pos": info["x"], "y_pos": 240 - info["y"],
            "flag_get": g.level_complete, "life": g.lives, "world": 1,
            "stage": 1, "steps": self._steps,
        })
        return info

    def _reward(self, prev, info, action):
        rc = self.reward_cfg
        if callable(rc) and not isinstance(rc, RewardConfig):
            return float(rc(prev, info))
        r = 0.0
        if rc.only_new_progress:
            dx = info["max_x"] - prev["max_x"]
        else:
            dx = info["x"] - prev["x"] if info["area"] == prev["area"] else 0
        r += rc.progress_per_tile * dx / C.TILE
        if info["x"] == prev["x"] and not info["flag_get"]:
            r += rc.stand_still
        s0, s1 = prev["stats"], info["stats"]
        d = lambda k: s1.get(k, 0) - s0.get(k, 0)   # noqa: E731
        r += rc.brick * d("bricks_broken")
        r += rc.qblock * d("qblocks_hit")
        r += rc.enemy * d("enemies_killed")
        r += rc.coin * d("coins")
        r += rc.powerup * d("powerups")
        r += rc.one_up * d("one_ups")
        r += rc.bonus_room * d("bonus_room")
        r += rc.score_scale * (info["score"] - prev["score"])
        r += rc.time_penalty * max(0, prev["time"] - info["time"])
        if info["dead"]:
            r += rc.death
        if info["flag_get"] and not prev["flag_get"]:
            r += rc.win
        if rc.clip is not None:
            r = float(np.clip(r, rc.clip[0], rc.clip[1]))
        return float(r)

    # ------------------------------------------------------------------
    # Observations
    # ------------------------------------------------------------------
    def _obs(self):
        if self.obs_type == "tiles":
            return self._obs_tiles()
        if self.obs_type == "rgb":
            return self._obs_rgb()
        if self.obs_type == "vector":
            return self._obs_vector()
        if self.obs_type == "vector_plus":
            return self._obs_vector_plus()
        return self._obs_paper()

    def _entity_cells(self):
        """(rangée, colonne, code) des entités dans la grille du niveau."""
        g = self.game
        out = []
        for e in g.enemies:
            if not e.alive or e.state in ("dead", "rise"):
                continue
            if e.is_item:
                code = C.OBS_ITEM
            elif e.state in ("shell", "shell_move"):
                code = C.OBS_SHELL
            elif e.state == "flat":
                continue
            else:
                code = C.OBS_ENEMY
            out.append(((e.y + 16) >> 4, (e.x + 8) >> 4, code))
        for f in g.fireballs:
            out.append(((f.y + 4) >> 4, (f.x + 4) >> 4, C.OBS_FIREBALL))
        p = g.p
        mc = (p.x + 8) >> 4
        feet_row = (p.y + 31) >> 4
        out.append((feet_row, mc, C.OBS_MARIO))
        if not (p.small or p.crouch):
            out.append((feet_row - 1, mc, C.OBS_MARIO))
        return out

    def _obs_tiles(self):
        g = self.game
        if self.tile_view == "screen":
            c0 = g.cam_x >> 4
            w = 16
        else:
            back, ahead = self.view_cols
            c0 = ((g.p.x + 8) >> 4) - back
            w = back + ahead
        out = np.zeros((13, w), dtype=np.uint8)
        a, b = max(c0, 0), min(c0 + w, g.W)
        if a < b:
            out[:, a - c0:b - c0] = TILE_TO_OBS[g.grid[2:15, a:b]]
        for r, c, code in self._entity_cells():
            rr, cc = r - 2, c - c0
            if 0 <= rr < 13 and 0 <= cc < w:
                out[rr, cc] = code
        return out

    def _obs_rgb(self):
        frame = self.renderer.render()
        if self.grayscale:
            frame = (frame @ np.array([0.299, 0.587, 0.114])).astype(np.uint8)
        if self.rgb_size:
            h, w = self.rgb_size
            ys = (np.arange(h) * C.SCREEN_H // h)
            xs = (np.arange(w) * C.SCREEN_W // w)
            frame = frame[ys][:, xs]
        return np.ascontiguousarray(frame)

    def _obs_vector(self):
        g = self.game
        p = g.p
        v = [
            p.x / (L.LEVEL_COLS * C.TILE), (p.y + 32) / 240.0,
            p.x_speed / 40.0, (p.y_speed + p.y_force / 256.0) / 5.0,
            float(p.state == 0), p.status / 2.0, float(p.star_timer > 0),
            (p.x - g.cam_x) / 256.0, g.timer / 400.0,
            float(g.area == "bonus"),
        ]
        ens = []
        for e in g.enemies:
            if not e.alive or e.is_item or e.state in ("dead", "flat"):
                continue
            dx = (e.x - p.x) / 256.0
            dy = ((e.y + 24) - (p.y + 32)) / 240.0
            kind = 0.0 if e.kind == "goomba" else (
                1.0 if e.state in ("shell", "shell_move") else 0.5)
            ens.append((abs(dx), [dx, dy, kind, 1.0]))
        ens.sort(key=lambda t: t[0])
        for i in range(N_ENEMY_FEATURES):
            v.extend(ens[i][1] if i < len(ens) else [0.0, 0.0, 0.0, 0.0])
        # profil du terrain devant Mario : hauteur du sol et présence d'un
        # obstacle au niveau de Mario pour les AHEAD colonnes suivantes
        col = (p.x + 8) >> 4
        feet_row = (p.y + 31) >> 4
        block = np.zeros((13, AHEAD), dtype=np.uint8)
        a, b = col, min(col + AHEAD, g.W)
        if a < b:
            block[:, :b - a] = g.grid[2:15, a:b]
        solid = SOLID_NP[block]
        has = solid.any(axis=0)
        height = np.where(has, (13 - solid.argmax(axis=0)) / 13.0, 0.0)
        if 2 <= feet_row < 15:
            obst = solid[feet_row - 2].astype(np.float64)
        else:
            obst = np.zeros(AHEAD)
        v.extend(np.stack([height, obst], axis=1).ravel().tolist())
        return np.clip(np.asarray(v, dtype=np.float32), -4.0, 4.0)

    def _obs_vector_plus(self):
        """``vector`` + ce qu'il faut voir pour la route A (24 nombres)."""
        g = self.game
        p = g.p
        mx, my = p.x + 8, p.y + 24              # centre de Mario
        v = []
        # objet le plus proche (champignon, fleur, étoile, 1-UP)
        items = [e for e in g.enemies if e.alive and e.is_item]
        if items:
            e = min(items, key=lambda e: abs(e.x - p.x))
            v += [(e.x - p.x) / 256.0, ((e.y + 24) - (p.y + 32)) / 240.0,
                  ITEM_CODE[e.kind], 1.0]
        else:
            v += [0.0, 0.0, 0.0, 0.0]
        # on ne regarde qu'autour de Mario : 8 colonnes derrière, 16 devant
        col = (p.x + 8) >> 4
        a, b = max(col - 8, 0), min(col + AHEAD, g.W)
        window = g.grid[:, a:b]
        # les pièces les plus proches (salle bonus)
        rows, cols = np.nonzero(window == C.COIN)
        dx = ((cols + a) * C.TILE + 8 - mx) / 256.0
        dy = (rows * C.TILE + 8 - my) / 240.0
        order = np.argsort(dx * dx + dy * dy)[:N_COIN_FEATURES]
        for i in range(N_COIN_FEATURES):
            v += ([dx[order[i]], dy[order[i]], 1.0] if i < len(order)
                  else [0.0, 0.0, 0.0])
        # bloc ? le plus proche devant Mario (à partir d'1 colonne derrière)
        rows, cols = np.nonzero(QBLOCK_LUT[window])
        ahead = cols + a >= col - 1
        rows, cols = rows[ahead], cols[ahead]
        if len(cols):
            i = int(np.argmin(np.abs(cols + a - col)))
            r, c = rows[i], cols[i] + a
            v += [(c * C.TILE + 8 - mx) / 256.0,
                  (r * C.TILE + 8 - my) / 240.0,
                  float(window[r, cols[i]] == C.QBLOCK_POWERUP), 1.0]
        else:
            v += [0.0, 0.0, 0.0, 0.0]
        # distance au tuyau utile (unité : 64 pixels) : celui de la salle
        # bonus dehors, celui de la sortie dans la salle bonus
        target = WARP_X if g.area == "overworld" else BONUS_EXIT_X
        v.append((target - p.x) / 64.0)
        extra = np.clip(np.asarray(v, dtype=np.float32), -4.0, 4.0)
        return np.concatenate([self._obs_vector(), extra])

    def _obs_paper(self):
        g = self.game
        p = g.p
        col = min(max((p.x + 8) >> 4, 0), L.LEVEL_COLS - 1)
        row = min(max(((p.y + 31) >> 4) - 1, 0), 13)
        phase = 0 if p.state == 0 else (1 if p.y_speed < 0 else 2)
        vals = [col, row, phase]
        vp = self.paper_viewport
        c0 = col - vp // 2
        a, b = max(c0, 0), min(c0 + vp, g.W)
        for r in self.paper_block_rows:
            line = np.zeros(vp, dtype=np.int64)
            if a < b:
                line[a - c0:b - c0] = TILE_TO_PAPER[g.grid[r + 1, a:b]]
            vals.extend(line.tolist())
        enemy_cells = {(r - 1, c) for r, c, code in self._entity_cells()
                       if code in (C.OBS_ENEMY, C.OBS_SHELL)}
        for r in self.paper_enemy_rows:
            vals.extend(C.P_GOOMBA if (r, c) in enemy_cells else 0
                        for c in range(c0, c0 + vp))
        return np.asarray(vals, dtype=np.int64)

    # ------------------------------------------------------------------
    # Sauvegardes et rendu
    # ------------------------------------------------------------------
    def clone_state(self):
        return {"game": self.game.get_state(), "steps": self._steps,
                "prev": self._prev}

    def restore_state(self, state):
        self.game.set_state(state["game"])
        self._steps = state["steps"]
        self._prev = state["prev"]

    def render(self):
        if self.render_mode is None:
            return None
        frame = self.renderer.render()
        if self.render_mode == "rgb_array":
            return frame
        self._show(frame)
        return None

    def _show(self, frame):
        import os
        os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
        import pygame
        if self._window is None:
            pygame.display.init()
            s = self.render_scale
            self._window = pygame.display.set_mode(
                (C.SCREEN_W * s, C.SCREEN_H * s))
            pygame.display.set_caption("Super Mario Bros. 1-1 (RL)")
            self._clock = pygame.time.Clock()
            self._surf = pygame.Surface((C.SCREEN_W, C.SCREEN_H))
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.close()
                return
        pygame.surfarray.blit_array(self._surf, frame.swapaxes(0, 1))
        pygame.transform.scale(self._surf, self._window.get_size(),
                               self._window)
        pygame.display.flip()
        self._clock.tick(self.metadata["render_fps"])

    def close(self):
        if self._window is not None:
            import pygame
            pygame.display.quit()
            self._window = None
