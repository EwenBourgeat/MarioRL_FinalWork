"""Rendu de l'écran NES (256 x 240) dans un tableau numpy, sans pygame.

Utilisable sans affichage (observations pixels pour DQN, vidéos) ; la
fenêtre pygame de :mod:`mario_env.play` ne fait qu'afficher ce tableau.
"""

import numpy as np

from . import constants as C
from . import level_data as L
from . import sprites as S
from .constants import NES_PALETTE, TILE

SCREEN_W, SCREEN_H = C.SCREEN_W, C.SCREEN_H
# Sur NES, les sprites s'affichent une ligne plus bas que leur coordonnée
# (décalage de l'OAM) : les pieds de Mario et des ennemis recouvrent la
# première rangée (claire) des blocs de sol.
SPRITE_DY = 1

# Tuiles dessinées une fois pour toutes (elles ne changent jamais)
STATIC_TILES = {
    C.GROUND, C.STAIR, C.PIPE_TL, C.PIPE_TR, C.PIPE_L, C.PIPE_R,
    C.FLAGPOLE, C.FLAG_BALL, C.UG_GROUND, C.SPIPE_TOP_MOUTH,
    C.SPIPE_TOP_BODY, C.SPIPE_BOT_MOUTH, C.SPIPE_BOT_BODY,
    C.SPIPE_JOIN_TOP, C.SPIPE_JOIN_BOT,
}
DYNAMIC_LUT = np.zeros(C.N_TILE_TYPES, dtype=bool)
for _t in (C.BRICK, C.BRICK_COIN, C.BRICK_STAR, C.BRICK_POWERUP,
           C.QBLOCK_COIN, C.QBLOCK_POWERUP, C.USED, C.COIN, C.UG_BRICK):
    DYNAMIC_LUT[_t] = True

QBLOCK_CYCLE = ("qblock", "qblock", "qblock", "qblock2", "qblock3", "qblock2")
COIN_CYCLE = ("coin", "coin", "coin", "coin2", "coin3", "coin2")
STAR_CYCLE = ("mario", "star1", "star2", "star3")


def blit(frame, img, mask, x, y):
    """Copie une image masquée dans ``frame`` avec découpage aux bords."""
    h, w = mask.shape
    x0 = x if x > 0 else 0
    y0 = y if y > 0 else 0
    x1 = min(x + w, frame.shape[1])
    y1 = min(y + h, frame.shape[0])
    if x0 >= x1 or y0 >= y1:
        return
    m = mask[y0 - y:y1 - y, x0 - x:x1 - x]
    frame[y0:y1, x0:x1][m] = img[y0 - y:y1 - y, x0 - x:x1 - x][m]


def draw(frame, name, pal, x, y, flip=False, vflip=False):
    img, mask = S.get(name, pal, flip, vflip)
    blit(frame, img, mask, x, y)


def text(frame, s, x, y, pal="white"):
    for i, ch in enumerate(s):
        if ch == " ":
            continue
        key = "font_" + ch
        if key[5:] not in S.FONT:
            continue
        draw(frame, key, pal, x + 8 * i, y)


def _glyph_mask(ch):
    return np.array([[c == "X" for c in row] for row in S.FONT[ch]],
                    dtype=bool)


def _fill_mask(frame, mask, x, y, color):
    h, w = mask.shape
    x0, y0 = max(x, 0), max(y, 0)
    x1, y1 = min(x + w, frame.shape[1]), min(y + h, frame.shape[0])
    if x0 < x1 and y0 < y1:
        m = mask[y0 - y:y1 - y, x0 - x:x1 - x]
        frame[y0:y1, x0:x1][m] = color


def logo_text(frame, word, x, y, sx, sy, shadow):
    """Lettres agrandies du logo (face claire + ombre noire en bas à droite)."""
    face = NES_PALETTE[0x36]
    dark = NES_PALETTE[0x0F]
    cx = x
    for ch in word:
        if ch == " ":
            cx += 8
            continue
        m = np.kron(_glyph_mask(ch), np.ones((sy, sx), dtype=bool))
        for d in range(1, shadow + 1):
            _fill_mask(frame, m, cx + d, y + d, dark)
        _fill_mask(frame, m, cx, y, face)
        cx += m.shape[1]
    return cx


# Écran titre : panneau « SUPER MARIO BROS. » (palette du sol : pêche,
# brun, noir), options, curseur champignon et meilleur score.
TITLE_BOARD = (32, 32, 224, 112)          # x0, y0, x1, y1
TITLE_OPTION_X = 56
TITLE_OPTION_Y = 136
TITLE_TOP_Y = 184


def mini_text(frame, s, x, y):
    for i, ch in enumerate(s):
        if ch in S.MINI:
            draw(frame, "mini_" + ch, "white", x + 4 * i + (i and 1) * 0, y)


class Renderer:
    """Dessine l'état d'un :class:`mario_env.game.Game`."""

    def __init__(self, game):
        self.game = game
        self._static = {}
        self._fgmask = {}

    # ------------------------------------------------------------------
    def _tile_image(self, t, area):
        pal = "underground" if area == "bonus" else "ground"
        if t in (C.GROUND, C.UG_GROUND):
            return "ground", pal, 0, 0
        if t == C.STAIR:
            return "stair", "ground", 0, 0
        if t in (C.BRICK, C.BRICK_COIN, C.BRICK_STAR, C.BRICK_POWERUP):
            return "brick", "ground", 0, 0
        if t == C.UG_BRICK:
            return "brick", "underground", 0, 0
        if t == C.USED:
            return "used", "used", 0, 0
        return None

    def _build_static(self, area):
        g = self.game
        grid = g.grids[area]
        rows, cols = grid.shape
        w = cols * TILE
        bg = NES_PALETTE[C.SKY_COLOR] if area == "overworld" else (0, 0, 0)
        img = np.empty((SCREEN_H, w, 3), dtype=np.uint8)
        img[:] = bg
        fg = np.zeros((SCREEN_H, w), dtype=bool)
        if area == "overworld":
            for col, kind, row, width in L.overworld_scenery(cols):
                x = col * TILE
                if kind == "cloud":
                    draw(img, f"cloud{width - 2}", "cloud", x, row * TILE)
                elif kind == "bush":
                    draw(img, f"bush{width - 2}", "bush", x, row * TILE)
                elif kind == "hill_big":
                    draw(img, "hill_big", "hill", x, 13 * TILE - 48)
                elif kind == "hill_small":
                    draw(img, "hill_small", "hill", x, 13 * TILE - 32)
            for r, line in enumerate(L.CASTLE_LAYOUT):
                for c, part in enumerate(line):
                    if part:
                        draw(img, "castle_" + part, "ground",
                             (L.CASTLE_COL + c) * TILE,
                             (L.CASTLE_TOP_ROW + r) * TILE)
        for r in range(rows):
            for c in range(cols):
                t = int(grid[r, c])
                if t not in STATIC_TILES:
                    continue
                x, y = c * TILE, r * TILE
                self._draw_static_tile(img, fg, t, x, y, area)
        self._static[area] = img
        self._fgmask[area] = fg

    def _draw_static_tile(self, img, fg, t, x, y, area):
        def put(name, pal, sx=0, sy=0, w=16, h=16):
            im, m = S.get(name, pal)
            im = im[sy:sy + h, sx:sx + w]
            m = m[sy:sy + h, sx:sx + w]
            blit(img, im, m, x, y)
            fg[y:y + h, x:x + w] |= m

        pal = "underground" if area == "bonus" else "ground"
        if t in (C.GROUND, C.UG_GROUND):
            put("ground", pal)
        elif t == C.STAIR:
            put("stair", "ground")
        elif t == C.PIPE_TL:
            put("pipe_top", "pipe", 0)
        elif t == C.PIPE_TR:
            put("pipe_top", "pipe", 16)
        elif t == C.PIPE_L:
            put("pipe_body", "pipe", 0)
        elif t == C.PIPE_R:
            put("pipe_body", "pipe", 16)
        elif t == C.FLAGPOLE:
            put("pole", "pole")
        elif t == C.FLAG_BALL:
            put("ball", "pole")
        elif t == C.SPIPE_TOP_MOUTH:
            put("spipe_mouth", "pipe", 0, 0)
        elif t == C.SPIPE_BOT_MOUTH:
            put("spipe_mouth", "pipe", 0, 16)
        elif t in (C.SPIPE_TOP_BODY, C.SPIPE_JOIN_TOP):
            put("spipe_body", "pipe", 0, 0)
        elif t in (C.SPIPE_BOT_BODY, C.SPIPE_JOIN_BOT):
            put("spipe_body", "pipe", 0, 16)

    def invalidate(self):
        self._static.clear()
        self._fgmask.clear()

    # ------------------------------------------------------------------
    def render(self):
        """Renvoie l'image courante (240, 256, 3) uint8."""
        g = self.game
        if g.mode == "gameover":
            return self.render_message("GAME OVER")
        area = g.area
        if area not in self._static:
            self._build_static(area)
        static = self._static[area]
        cam = g.cam_x
        frame = static[:, cam:cam + SCREEN_W].copy()
        fc = g.frame

        # objets qui sortent d'un bloc : derrière les blocs
        for e in g.enemies:
            if e.state == "rise":
                self._draw_enemy(frame, e, cam, fc)

        # tuiles dynamiques
        c0 = cam // TILE
        c1 = min(c0 + 17, g.W)
        sub = g.grid[:, c0:c1]
        rows, cols = np.nonzero(DYNAMIC_LUT[sub])
        bumping = {(b.col, b.row) for b in g.bumps}
        qpal = QBLOCK_CYCLE[(fc // 8) % 6]
        cpal = COIN_CYCLE[(fc // 8) % 6]
        for r, c in zip(rows.tolist(), cols.tolist()):
            col = c + c0
            if (col, r) in bumping:
                continue
            t = int(sub[r, c])
            x = col * TILE - cam
            y = r * TILE
            if t in (C.QBLOCK_COIN, C.QBLOCK_POWERUP):
                draw(frame, "qblock", qpal, x, y)
            elif t == C.COIN:
                draw(frame, "coin_tile", cpal, x, y)
            else:
                name, pal, _, _ = self._tile_image(t, area)
                draw(frame, name, pal, x, y)
        for b in g.bumps:
            x = b.col * TILE - cam
            y = b.row * TILE + b.offset
            if b.tile in (C.QBLOCK_COIN, C.QBLOCK_POWERUP):
                draw(frame, "qblock", qpal, x, y)
            else:
                info = self._tile_image(b.tile, area)
                if info:
                    draw(frame, info[0], info[1], x, y)

        # drapeau du mât
        if area == "overworld":
            fx = L.FLAGPOLE_COL * TILE - 8 - cam
            if -16 < fx < SCREEN_W:
                draw(frame, "flag", "flag", fx, g.flag_y + SPRITE_DY)
                if g.mode == "flag":
                    pts = C.FLAGPOLE_POINTS[g.flag_score_idx]
                    mini_text(frame, str(pts), fx + 20, g.flag_score_y)
            if g.castle_flag:
                cfx = L.CASTLE_DOOR_COL * TILE - cam
                cfy = L.CASTLE_TOP_ROW * TILE - g.castle_flag
                img, mask = S.get("castle_flag", "castle_flag")
                h = g.castle_flag
                blit(frame, img[:h], mask[:h], cfx, cfy)

        for e in g.enemies:
            if e.state != "rise":
                self._draw_enemy(frame, e, cam, fc)
        self._draw_player(frame, cam, fc, area)
        for f in g.fireballs:
            if f.explode:
                i = min(2, 2 - (f.explode - 1) // 4)
                draw(frame, f"explosion{i}", "fireball", f.x - cam - 4,
                     f.y - 4 + SPRITE_DY)
            else:
                draw(frame, f"fireball{(f.anim // 4) % 4}", "fireball",
                     f.x - cam, f.y + SPRITE_DY)
        self._draw_effects(frame, cam, area)
        self.draw_hud(frame)
        return frame

    # ------------------------------------------------------------------
    def _draw_enemy(self, frame, e, cam, fc):
        x = e.x - cam
        if x < -16 or x > SCREEN_W:
            return
        k = e.kind
        dead = e.state == "dead"
        # un objet qui sort d'un bloc ne doit pas dépasser sous le bloc
        dy = 0 if e.state == "rise" else SPRITE_DY
        if k == "goomba":
            if e.state == "flat":
                draw(frame, "goomba_flat", "goomba", x, e.y + 16 + SPRITE_DY)
            else:
                draw(frame, "goomba", "goomba", x, e.y + 8 + SPRITE_DY,
                     flip=bool((fc // 8) & 1) and not dead, vflip=dead)
        elif k == "koopa":
            if e.state in ("shell", "shell_move") or dead:
                name = "shell"
                if e.state == "shell" and e.timer < 3 * C.INTERVAL \
                        and (fc // 4) & 1:
                    name = "shell_legs"
                draw(frame, name, "koopa", x, e.y + SPRITE_DY, vflip=dead)
            else:
                name = "koopa1" if (fc // 8) & 1 else "koopa2"
                draw(frame, name, "koopa", x, e.y + SPRITE_DY,
                     flip=e.moving_dir == 1)
        elif k in ("mushroom", "1up"):
            draw(frame, "mushroom", "mushroom" if k == "mushroom" else "1up",
                 x, e.y + 8 + dy)
        elif k == "flower":
            draw(frame, "flower", f"flower{(fc // 2) % 4 + 1}", x, e.y + 8 + dy)
        elif k == "star":
            draw(frame, "star", ("star_a", "star_b", "star_c", "star_d")[
                (fc // 2) % 4], x, e.y + 8 + dy)

    def _player_sprite(self, fc):
        g = self.game
        p = g.p
        big = p.status > 0
        if g.freeze_kind == "grow":
            big = ((C.GROW_FRAMES - g.freeze) // 4) % 2 == 1
        elif g.freeze_kind == "shrink":
            big = ((C.SHRINK_FRAMES - g.freeze) // 4) % 2 == 0
        size = "big" if big else "small"
        if g.mode == "dying" and g.death_cause != "pit":
            return "small_death", False
        if p.state == 3 or g.mode in ("flag", "flag_turn"):
            return size + "_climb", p.facing == 2
        if big and p.crouch:
            return "big_crouch", p.facing == 2
        if big and p.fire_anim:
            return "big_throw", p.facing == 2
        if p.state == 1:
            return size + "_jump", p.facing == 2
        if p.skidding:
            return size + "_skid", p.facing == 2
        f = p.anim_frame
        name = "stand" if f == 0 else f"walk{f}"
        return f"{size}_{name}", p.facing == 2

    def _draw_player(self, frame, cam, fc, area):
        g = self.game
        p = g.p
        if not p.visible:
            return
        if p.injury_timer and not g.freeze and (fc & 2):
            return
        name, flip = self._player_sprite(fc)
        if p.star_timer:
            speed = 1 if p.star_timer > 120 else 4
            pal = STAR_CYCLE[(fc // speed) % 4]
        elif g.freeze_kind == "fire":
            pal = STAR_CYCLE[(fc // 2) % 4]
        else:
            pal = "fire" if p.status == 2 else "mario"
        x = p.x - cam
        y = p.y + (16 if name.startswith("small") else 0) + SPRITE_DY
        draw(frame, name, pal, x, y, flip=flip)
        if p.behind_bg:
            fg = self._fgmask[area][:, cam:cam + SCREEN_W]
            st = self._static[area][:, cam:cam + SCREEN_W]
            y0, y1 = max(0, p.y - 2), min(SCREEN_H, p.y + 34)
            x0, x1 = max(0, x - 2), min(SCREEN_W, x + 18)
            if y0 < y1 and x0 < x1:
                m = fg[y0:y1, x0:x1]
                frame[y0:y1, x0:x1][m] = st[y0:y1, x0:x1][m]

    def _draw_effects(self, frame, cam, area):
        for fx in self.game.effects:
            x = int(fx.x) - cam
            y = int(fx.y) + SPRITE_DY
            if fx.kind == "debris":
                pal = "underground" if area == "bonus" else "ground"
                draw(frame, "debris", pal, x, y, flip=bool((fx.t // 4) & 1))
            elif fx.kind == "coin":
                draw(frame, f"coin_spin{(fx.t // 3) % 4}", "coin", x, y)
            elif fx.kind == "score":
                s = "1UP" if fx.value < 0 else str(fx.value)
                mini_text(frame, s, x, y)
            elif fx.kind == "firework":
                i = min(2, fx.t // 8)
                draw(frame, f"explosion{i}", "firework", x, y)

    # ------------------------------------------------------------------
    def draw_hud(self, frame, show_time=True, fc=None):
        g = self.game
        text(frame, "MARIO", 24, 16)
        text(frame, f"{g.score:06d}", 24, 24)
        cpal = COIN_CYCLE[((g.frame if fc is None else fc) // 8) % 6]
        draw(frame, "hud_coin", cpal, 88, 24)
        text(frame, "x", 96, 24)
        text(frame, f"{g.coins:02d}", 104, 24)
        text(frame, "WORLD", 144, 16)
        text(frame, "1-1", 152, 24)
        text(frame, "TIME", 200, 16)
        if show_time and g.mode not in ("intermission",):
            text(frame, f"{g.timer:03d}", 208, 24)

    def render_message(self, message, lives=None):
        """Écran noir d'intermède (WORLD 1-1 / GAME OVER / TIME UP)."""
        frame = np.zeros((SCREEN_H, SCREEN_W, 3), dtype=np.uint8)
        self.draw_hud(frame, show_time=False)
        if lives is not None:
            text(frame, "WORLD 1-1", 88, 80)
            draw(frame, "small_stand", "mario", 97, 104)
            text(frame, f"x  {lives}", 120, 112)
        else:
            text(frame, message, 128 - 4 * len(message), 112)
        return frame

    def render_title(self, options, cursor, top_score=0, fc=0):
        """Écran titre de Super Mario Bros. avec nos options de menu.

        Même composition que l'original : début du niveau 1-1 en fond, Mario
        au départ, HUD sans le chrono, panneau du titre, options et curseur
        champignon, puis « TOP- » et le meilleur score.
        """
        if "overworld" not in self._static:
            self._build_static("overworld")
        frame = self._static["overworld"][:, 0:SCREEN_W].copy()
        draw(frame, "small_stand", "mario", L.START_X,
             L.START_Y + 16 + SPRITE_DY)
        self.draw_hud(frame, show_time=False, fc=fc)
        self._draw_title_board(frame)
        for i, label in enumerate(options):
            text(frame, label, TITLE_OPTION_X, TITLE_OPTION_Y + 16 * i,
                 pal="peach")
        draw(frame, "cursor", "cursor", TITLE_OPTION_X - 16,
             TITLE_OPTION_Y + 16 * cursor)
        text(frame, f"TOP- {top_score:06d}", 96, TITLE_TOP_Y, pal="peach")
        return frame

    @staticmethod
    def _draw_title_board(frame):
        x0, y0, x1, y1 = TITLE_BOARD
        frame[y0:y1, x0:x1] = NES_PALETTE[0x0F]              # contour noir
        frame[y0 + 1:y1 - 1, x0 + 1:x1 - 1] = NES_PALETTE[0x36]  # liseré
        frame[y0 + 2:y1 - 2, x0 + 2:x1 - 2] = NES_PALETTE[0x17]  # panneau
        # ombre du panneau (bords bas et droit plus sombres)
        frame[y1 - 3:y1 - 1, x0 + 2:x1 - 1] = NES_PALETTE[0x0F]
        frame[y0 + 2:y1 - 1, x1 - 3:x1 - 1] = NES_PALETTE[0x0F]
        logo_text(frame, "SUPER", x0 + 12, y0 + 8, 2, 2, 1)
        logo_text(frame, "MARIO BROS.", x0 + 12, y0 + 28, 2, 3, 2)
        text(frame, "©1985 NINTENDO", x1 - 14 - 8 * 14, y1 - 18, pal="peach")

    def render_level_map(self, area="overworld", enemies=True):
        """Image du niveau complet (utile pour les rapports / figures)."""
        g = self.game
        if area not in self._static:
            self._build_static(area)
        img = self._static[area].copy()
        grid = g.grids[area]
        rows, cols = np.nonzero(DYNAMIC_LUT[grid])
        for r, c in zip(rows.tolist(), cols.tolist()):
            t = int(grid[r, c])
            if t in (C.QBLOCK_COIN, C.QBLOCK_POWERUP):
                draw(img, "qblock", "qblock", c * TILE, r * TILE)
            elif t == C.COIN:
                draw(img, "coin_tile", "coin", c * TILE, r * TILE)
            else:
                name, pal, _, _ = self._tile_image(t, area)
                draw(img, name, pal, c * TILE, r * TILE)
        if area == "overworld":
            draw(img, "flag", "flag", L.FLAGPOLE_COL * TILE - 8, g.flag_y)
            if enemies and g.cfg.enemies:
                for sp in g.enemy_spawns:
                    y = sp.y + 8                # après la petite chute initiale
                    for x in sp.visual_positions():
                        if sp.kind == "goomba":
                            draw(img, "goomba", "goomba", x, y + 8)
                        else:
                            draw(img, "koopa1", "koopa", x, y)
            p = g.p
            draw(img, "small_stand", "mario", L.START_X, L.START_Y + 16)
        return img
