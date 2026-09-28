"""Environnement discret « article » (Ponnock & Ho, 2026, section 2.1).

Le niveau 1-1 est une grille de 212 x 14 cases (rangée 0 en haut, sol sur
les rangées 12-13).  Mario occupe une case, se déplace d'une case par pas,
et saute selon un arc fixe de 6 phases (-2, -3, -4, -4, -3, -2 cases par
rapport à la rangée de départ).  Trois actions : 0 = rien, 1 = droite,
2 = saut (seulement au sol).  Trois versions :

* v1 : terrain seul (sol, trous, tuyaux, escaliers) ;
* v2 : + briques (cassables, +1) et blocs ? (+3) ;
* v3 : + 17 ennemis (16 Goombas et 1 Koopa traités pareil) qui avancent
  d'une case tous les 3 pas (1/3 de la vitesse de Mario), tombent dans
  les trous, sont activés par groupe et meurent si Mario leur saute dessus.

Les données du niveau viennent du même fichier que le moteur NES, donc les
positions sont identiques dans les deux environnements.

Les points non précisés par l'article (chute après l'arc, rebond après un
écrasement, activation des ennemis...) sont documentés ci-dessous et
réglables par paramètre.
"""

from __future__ import annotations

import numpy as np
import gymnasium as gym
from gymnasium import spaces

from .. import constants as C
from .. import level_data as L
from .common import TILE_TO_PAPER, resolve_reward, RewardConfig

JUMP_OFFSETS = (-2, -3, -4, -4, -3, -2)
N_ROWS = 14
FLAG_COL = L.FLAGPOLE_COL
SPAWN_COL = 3
SPAWN_ROW = 11
PIT_ROW = 13
PAPER_SOLID = np.zeros(C.N_PAPER_CODES, dtype=bool)
for _c in (C.P_GROUND, C.P_STEP, C.P_PIPE, C.P_BRICK, C.P_QBLOCK, C.P_USED):
    PAPER_SOLID[_c] = True
_SOLID_LIST = PAPER_SOLID.tolist()


def paper_grid(level="v3", segment_order=None):
    """Grille (14 x 212) des codes de l'article pour une version donnée."""
    nes = L.build_overworld()
    for col, row, kind in L.BLOCKS:
        if kind == C.HIDDEN_1UP or level == "v1":
            nes[row, col] = C.EMPTY
    if segment_order and "".join(segment_order).upper() != L.SEGMENT_ORDER:
        nes = L.permute_grid(nes, segment_order)
    return TILE_TO_PAPER[nes[1:15]].astype(np.int8)


def paper_enemies(segment_order=None):
    """Liste (colonne, rangée, groupe) des 17 ennemis en coordonnées article."""
    spawns = L.ENEMIES
    if segment_order and "".join(segment_order).upper() != L.SEGMENT_ORDER:
        spawns = L.permute_enemies(spawns, segment_order)
    out = []
    for sp in spawns:
        col = -(-sp.x // C.TILE)            # 51 et 52,5 -> 51 et 53
        out.append((col, sp.row - 2, sp.spawn_x // C.TILE))
    return out


class MarioGridEnv(gym.Env):
    """Environnement tabulaire de l'article, rapide et 100 % déterministe.

    Paramètres
    ----------
    level : "v1", "v2" ou "v3" (défaut).
    reward : "paper" (défaut, tableau 2 de l'article), dict ou RewardConfig.
        Clés utilisées : progress_per_tile, stand_still, win, death, brick,
        qblock, enemy.
    max_steps : troncature de l'épisode (défaut 1000).
    segment_order : ordre des segments A-F (ex. "FEDCBA"), None = canonique.
    viewport, block_rows, enemy_rows : forme de l'observation (défauts de
        l'article : 28 colonnes, rangées 4 et 8, ennemis rangées 7 et 11).
    enemy_period : un déplacement d'ennemi tous les N pas (3 = 1/3).
    activation_distance : un groupe d'ennemis s'active quand Mario est à
        moins de N colonnes de son premier membre (14 = demi-écran).
    """

    metadata = {"render_modes": ["human", "rgb_array"], "render_fps": 12}

    def __init__(self, level="v3", render_mode=None, reward="paper",
                 max_steps=1000, segment_order=None, viewport=28,
                 block_rows=(4, 8), enemy_rows=(7, 11), enemy_period=3,
                 activation_distance=14, jump_offsets=JUMP_OFFSETS,
                 render_style="sprites"):
        super().__init__()
        if level not in ("v1", "v2", "v3"):
            raise ValueError("level doit valoir 'v1', 'v2' ou 'v3'")
        self.level = level
        self.render_mode = render_mode
        rc = resolve_reward(reward)
        if not isinstance(rc, RewardConfig):
            raise TypeError("MarioGridEnv attend un RewardConfig/dict/nom")
        self.rc = rc
        self.max_steps = max_steps
        self.segment_order = segment_order
        self.viewport = int(viewport)
        self.block_rows = tuple(block_rows) if level != "v1" else ()
        self.enemy_rows = tuple(enemy_rows) if level == "v3" else ()
        self.enemy_period = int(enemy_period)
        self.activation_distance = int(activation_distance)
        self.jump_offsets = tuple(jump_offsets)
        self.render_style = render_style
        self._window = None
        self._build_level()

        self.action_space = spaces.Discrete(3)
        nvec = [L.LEVEL_COLS, N_ROWS, len(self.jump_offsets) + 1]
        nvec += [C.N_PAPER_CODES] * (self.viewport * len(self.block_rows))
        nvec += [C.P_GOOMBA + 1] * (self.viewport * len(self.enemy_rows))
        self.observation_space = spaces.MultiDiscrete(
            np.array(nvec, dtype=np.int64))
        self.reset()

    # ------------------------------------------------------------------
    def _build_level(self):
        self.base_grid = paper_grid(self.level, self.segment_order)
        self.W = self.base_grid.shape[1]
        self.base_enemies = (paper_enemies(self.segment_order)
                             if self.level == "v3" else [])

    def set_segment_order(self, order):
        """Change l'ordre des segments (prend effet au prochain reset)."""
        self.segment_order = order
        self._build_level()

    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)
        options = options or {}
        if "segment_order" in options:
            self.set_segment_order(options["segment_order"])
        half = self.viewport // 2
        self.pad = half
        W = self.W
        # grille entourée de colonnes vides pour extraire la viewport vite
        self.grid = np.zeros((N_ROWS, W + 2 * half), dtype=np.int8)
        self.grid[:, half:half + W] = self.base_grid
        self.occ = np.zeros((N_ROWS, W + 2 * half), dtype=np.int8)
        self._rows = [row for row in self.grid]            # accès rapide
        self._occ_rows = [row for row in self.occ]
        self.col = SPAWN_COL
        self.row = SPAWN_ROW
        self.phase = 0
        self.origin = SPAWN_ROW
        self.t = 0
        self.total_reward = 0.0
        # ennemi = [colonne, rangée, direction, actif, vivant, groupe]
        self.enemies = [[c, r, -1, False, True, g]
                        for c, r, g in self.base_enemies]
        for e in self.enemies:
            self._occ_set(e, 1)
        self.stats = {"bricks_broken": 0, "qblocks_hit": 0,
                      "enemies_killed": 0, "jumps": 0}
        self.done = False
        self.win = False
        self.dead = False
        self._activate()
        if self.render_mode == "human":
            self.render()
        return self._obs(), self._info()

    # ------------------------------------------------------------------
    def _solid(self, row, col):
        if row < 0:
            return False
        if row >= N_ROWS or col < 0 or col >= self.W:
            return col < 0
        return _SOLID_LIST[self._rows[row][col + self.pad]]

    def _occ_set(self, e, v):
        c, r = e[0], e[1]
        if 0 <= r < N_ROWS and 0 <= c < self.W:
            self.occ[r, c + self.pad] += 1 if v else -1

    def _enemy_at(self, row, col):
        if not (0 <= row < N_ROWS and 0 <= col < self.W):
            return None
        if not self._occ_rows[row][col + self.pad]:
            return None
        for e in self.enemies:
            if e[4] and e[0] == col and e[1] == row:
                return e
        return None

    def _activate(self):
        for e in self.enemies:
            if e[4] and not e[3] and e[5] - self.col <= self.activation_distance:
                e[3] = True

    def _hit_block(self, row, col, events):
        code = self._rows[row][col + self.pad]
        if code == C.P_BRICK and self.level != "v1":
            self._rows[row][col + self.pad] = C.P_EMPTY
            events["brick"] += 1
            self.stats["bricks_broken"] += 1
        elif code == C.P_QBLOCK:
            self._rows[row][col + self.pad] = C.P_USED
            events["qblock"] += 1
            self.stats["qblocks_hit"] += 1

    def _kill_enemy(self, e, events):
        self._occ_set(e, 0)
        e[4] = False
        events["enemy"] += 1
        self.stats["enemies_killed"] += 1

    # ------------------------------------------------------------------
    def step(self, action):
        if self.done:
            raise RuntimeError("épisode terminé : appelez reset()")
        a = int(action)
        rc = self.rc
        events = {"brick": 0, "qblock": 0, "enemy": 0}
        start_col = self.col
        start_row = self.row
        self.t += 1
        died = False
        won = False
        bounce = False

        grounded = self._solid(self.row + 1, self.col)
        if a == 2 and self.phase == 0 and grounded:
            self.phase = 1
            self.origin = self.row
            self.stats["jumps"] += 1

        # --- déplacement horizontal ---
        if a == 1:
            nc = self.col + 1
            if nc >= FLAG_COL:
                self.col = FLAG_COL
                won = True
            elif not self._solid(self.row, nc):
                self.col = nc
                e = self._enemy_at(self.row, nc)
                if e is not None:
                    died = True

        # --- déplacement vertical ---
        if not won and not died:
            if self.phase > 0:
                target = self.origin + self.jump_offsets[self.phase - 1]
                while self.row != target:
                    d = -1 if target < self.row else 1
                    nr = self.row + d
                    if self._solid(nr, self.col):
                        if d < 0:
                            self._hit_block(nr, self.col, events)
                        self.phase = -1          # l'arc s'arrête
                        break
                    e = self._enemy_at(nr, self.col)
                    if e is not None:
                        if d > 0:
                            self._kill_enemy(e, events)
                            bounce = True
                            break
                        died = True
                        break
                    self.row = nr
                if self.phase == -1:
                    self.phase = 0
                elif self.phase > 0:
                    self.phase += 1
                    if self.phase > len(self.jump_offsets):
                        self.phase = 0
            elif not self._solid(self.row + 1, self.col):
                nr = self.row + 1
                e = self._enemy_at(nr, self.col)
                if e is not None:
                    self._kill_enemy(e, events)
                    bounce = True
                else:
                    self.row = nr
            if bounce:
                self.origin = self.row + 2
                self.phase = 4
            if self.row >= PIT_ROW:
                died = True

        # --- ennemis ---
        if not died and not won and self.enemies:
            self._activate()
            move = self.t % self.enemy_period == 0
            for e in self.enemies:
                if not e[4] or not e[3]:
                    continue
                c, r = e[0], e[1]
                if not self._solid(r + 1, c) and self._enemy_at(r + 1, c) is None:
                    self._occ_set(e, 0)
                    e[1] = r + 1
                    if e[1] >= PIT_ROW:
                        e[4] = False
                        continue
                    self._occ_set(e, 1)
                elif move:
                    nc = c + e[2]
                    if (nc < 0 or nc >= self.W or self._solid(r, nc)
                            or self._enemy_at(r, nc) is not None):
                        e[2] = -e[2]
                    else:
                        self._occ_set(e, 0)
                        e[0] = nc
                        self._occ_set(e, 1)
                if e[4] and e[0] == self.col and e[1] == self.row:
                    died = True
                    break

        # --- récompense ---
        r = 0.0
        r += rc.progress_per_tile * (self.col - start_col)
        if a == 0:
            r += rc.stand_still
        r += rc.brick * events["brick"] + rc.qblock * events["qblock"]
        r += rc.enemy * events["enemy"]
        terminated = False
        if died:
            r += rc.death
            terminated = True
            self.dead = True
        elif won:
            r += rc.win
            terminated = True
            self.win = True
        truncated = (not terminated and self.max_steps is not None
                     and self.t >= self.max_steps)
        self.done = terminated or truncated
        self.total_reward += r
        if self.render_mode == "human":
            self.render()
        return self._obs(), float(r), terminated, truncated, self._info()

    # ------------------------------------------------------------------
    def _obs(self):
        parts = [np.array([self.col, min(max(self.row, 0), N_ROWS - 1),
                           self.phase], dtype=np.int64)]
        a = self.col + self.pad - self.viewport // 2
        b = a + self.viewport
        for r in self.block_rows:
            parts.append(self.grid[r, a:b].astype(np.int64))
        for r in self.enemy_rows:
            parts.append((self.occ[r, a:b] > 0).astype(np.int64) * C.P_GOOMBA)
        return np.concatenate(parts)

    def _info(self):
        return {"col": self.col, "row": self.row, "phase": self.phase,
                "t": self.t, "win": self.win, "flag_get": self.win,
                "dead": self.dead, "total_reward": self.total_reward,
                "stats": dict(self.stats),
                "enemies_alive": sum(1 for e in self.enemies if e[4])}

    def clone_state(self):
        import copy
        keep = ("grid", "occ", "col", "row", "phase", "origin", "t",
                "total_reward", "enemies", "stats", "done", "win", "dead")
        return {k: copy.deepcopy(getattr(self, k)) for k in keep}

    def restore_state(self, state):
        import copy
        for k, v in state.items():
            setattr(self, k, copy.deepcopy(v))
        self._rows = [row for row in self.grid]
        self._occ_rows = [row for row in self.occ]

    # ------------------------------------------------------------------
    # Rendu (sprites NES ou cases colorées comme la figure 1 de l'article)
    # ------------------------------------------------------------------
    FLAT_COLORS = {
        C.P_EMPTY: (99, 145, 234), C.P_GROUND: (139, 90, 43),
        C.P_STEP: (160, 110, 60), C.P_PIPE: (34, 139, 34),
        C.P_BRICK: (210, 105, 30), C.P_QBLOCK: (240, 200, 40),
        C.P_USED: (120, 80, 40), C.P_FLAG: (99, 145, 234),
    }

    def render_level(self, style=None, cell=16, window=None):
        """Image du niveau (entier ou colonnes ``window=(a, b)``)."""
        from .. import sprites as S
        from ..renderer import blit, draw
        style = style or self.render_style
        a, b = window if window else (0, self.W)
        n = b - a
        img = np.zeros((N_ROWS * cell, n * cell, 3), dtype=np.uint8)
        grid = self.grid[:, self.pad + a:self.pad + b]
        if style == "flat":
            for code, color in self.FLAT_COLORS.items():
                m = np.kron(grid == code, np.ones((cell, cell), dtype=bool))
                img[m] = color
            # trous en noir
            for c in range(n):
                if grid[N_ROWS - 1, c] == C.P_EMPTY:
                    img[(N_ROWS - 2) * cell:, c * cell:(c + 1) * cell] = 12
            for e in self.enemies:
                if e[4] and a <= e[0] < b:
                    x, y = (e[0] - a) * cell, e[1] * cell
                    img[y + 3:y + cell - 3, x + 3:x + cell - 3] = (255, 0, 255)
            x, y = (self.col - a) * cell, self.row * cell
            if 0 <= self.col - a < n and 0 <= self.row < N_ROWS:
                img[y + 1:y + cell - 1, x + 1:x + cell - 1] = (0, 0, 255)
            return img
        img[:] = C.NES_PALETTE[C.SKY_COLOR]
        for r in range(N_ROWS):
            for c in range(n):
                code = int(grid[r, c])
                x, y = c * 16, r * 16
                if code == C.P_GROUND:
                    draw(img, "ground", "ground", x, y)
                elif code == C.P_STEP:
                    draw(img, "stair", "ground", x, y)
                elif code == C.P_BRICK:
                    draw(img, "brick", "ground", x, y)
                elif code == C.P_QBLOCK:
                    draw(img, "qblock", "qblock", x, y)
                elif code == C.P_USED:
                    draw(img, "used", "used", x, y)
                elif code == C.P_FLAG:
                    draw(img, "pole", "pole", x, y)
                elif code == C.P_PIPE:
                    top = r == 0 or grid[r - 1, c] != C.P_PIPE
                    left = self._pipe_left(self.grid[:, self.pad:], r, a + c)
                    im, mk = S.get("pipe_top" if top else "pipe_body", "pipe")
                    off = 0 if left else 16
                    blit(img, im[:, off:off + 16], mk[:, off:off + 16], x, y)
        for e in self.enemies:
            if e[4] and a <= e[0] < b:
                draw(img, "goomba", "goomba", (e[0] - a) * 16, e[1] * 16)
        if 0 <= self.col - a < n:
            name = "small_jump" if self.phase > 0 else "small_stand"
            if self.dead:
                name = "small_death"
            draw(img, name, "mario", (self.col - a) * 16, self.row * 16)
        return img

    @staticmethod
    def _pipe_left(grid, r, c):
        # un tuyau fait 2 colonnes : on compte les colonnes de tuyau à gauche
        k = 0
        while c - k - 1 >= 0 and grid[r, c - k - 1] == C.P_PIPE:
            k += 1
        return k % 2 == 0

    def render(self):
        if self.render_mode is None:
            return None
        cam = min(max(self.col - 7, 0), self.W - 16)
        frame = self.render_level(window=(cam, cam + 16))
        if self.render_mode == "rgb_array":
            return frame
        import os
        os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
        import pygame
        if self._window is None:
            pygame.display.init()
            self._window = pygame.display.set_mode((16 * 16 * 3, N_ROWS * 16 * 3))
            pygame.display.set_caption("Mario 1-1 - environnement de l'article")
            self._clock = pygame.time.Clock()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.close()
                return None
        surf = pygame.surfarray.make_surface(frame.swapaxes(0, 1))
        pygame.transform.scale(surf, self._window.get_size(), self._window)
        pygame.display.flip()
        self._clock.tick(self.metadata["render_fps"])
        return None

    def close(self):
        if self._window is not None:
            import pygame
            pygame.display.quit()
            self._window = None
