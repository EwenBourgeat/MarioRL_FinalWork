"""Données du niveau 1-1 de Super Mario Bros. (NES).

Coordonnées : colonnes de 16 px depuis le début du niveau, rangées d'écran
de 16 px (0 = haut de l'écran, les rangées 0-1 sont sous le HUD, le sol
occupe les rangées 13 et 14).  Les positions reprennent la carte du niveau
original et correspondent aux colonnes utilisées dans l'article
(Ponnock & Ho, 2026) : tuyaux en 28/38/46/57/163/179, trous en 69-70,
86-88 et 153-154, drapeau en 198.
"""

from dataclasses import dataclass, field

import numpy as np

from .constants import (
    BRICK, BRICK_COIN, BRICK_STAR, COIN, EMPTY, FLAG_BALL, FLAGPOLE, GROUND,
    HIDDEN_1UP, LEVEL_COLS, PIPE_L, PIPE_R, PIPE_TL, PIPE_TR, QBLOCK_COIN,
    QBLOCK_POWERUP, ROWS, SPIPE_BOT_MOUTH, SPIPE_JOIN_BOT,
    SPIPE_JOIN_TOP, SPIPE_TOP_MOUTH, STAIR, TILE, UG_BRICK,
    UG_GROUND,
)

# ---------------------------------------------------------------------------
# Monde extérieur
# ---------------------------------------------------------------------------
GAPS = ((69, 70), (86, 88), (153, 154))          # colonnes sans sol (incluses)

# (colonne gauche, hauteur en blocs au-dessus du sol)
PIPES = ((28, 2), (38, 3), (46, 4), (57, 4), (163, 2), (179, 2))
WARP_PIPE_COL = 57          # tuyau menant à la salle bonus
EXIT_PIPE_COL = 163         # tuyau par lequel Mario ressort

LOW_ROW = 9                 # rangée des blocs « bas »
HIGH_ROW = 5                # rangée des blocs « hauts »

BLOCKS = (
    (16, LOW_ROW, QBLOCK_COIN),
    (20, LOW_ROW, BRICK), (21, LOW_ROW, QBLOCK_POWERUP), (22, LOW_ROW, BRICK),
    (23, LOW_ROW, QBLOCK_COIN), (24, LOW_ROW, BRICK),
    (22, HIGH_ROW, QBLOCK_COIN),
    (64, 8, HIDDEN_1UP),
    (77, LOW_ROW, BRICK), (78, LOW_ROW, QBLOCK_POWERUP), (79, LOW_ROW, BRICK),
    *((c, HIGH_ROW, BRICK) for c in range(80, 88)),
    (91, HIGH_ROW, BRICK), (92, HIGH_ROW, BRICK), (93, HIGH_ROW, BRICK),
    (94, HIGH_ROW, QBLOCK_COIN),
    (94, LOW_ROW, BRICK_COIN),
    (100, LOW_ROW, BRICK), (101, LOW_ROW, BRICK_STAR),
    (106, LOW_ROW, QBLOCK_COIN), (109, LOW_ROW, QBLOCK_COIN),
    (112, LOW_ROW, QBLOCK_COIN), (109, HIGH_ROW, QBLOCK_POWERUP),
    (118, LOW_ROW, BRICK),
    (121, HIGH_ROW, BRICK), (122, HIGH_ROW, BRICK), (123, HIGH_ROW, BRICK),
    (128, HIGH_ROW, BRICK), (129, HIGH_ROW, QBLOCK_COIN),
    (130, HIGH_ROW, QBLOCK_COIN), (131, HIGH_ROW, BRICK),
    (129, LOW_ROW, BRICK), (130, LOW_ROW, BRICK),
    (168, LOW_ROW, BRICK), (169, LOW_ROW, BRICK), (170, LOW_ROW, QBLOCK_COIN),
    (171, LOW_ROW, BRICK),
)

# (colonne, hauteur) des blocs durs des escaliers
STAIRS = (
    (134, 1), (135, 2), (136, 3), (137, 4),
    (140, 4), (141, 3), (142, 2), (143, 1),
    (148, 1), (149, 2), (150, 3), (151, 4), (152, 4),
    (155, 4), (156, 3), (157, 2), (158, 1),
    (181, 1), (182, 2), (183, 3), (184, 4), (185, 5), (186, 6), (187, 7),
    (188, 8), (189, 8),
)

FLAGPOLE_COL = 198
CASTLE_COL = 202            # château : colonnes 202 à 206, rangées 8 à 12
CASTLE_DOOR_COL = 204

START_X = 40                # position de départ de Mario (pixels)
START_Y = 176               # Mario debout sur le sol (haut d'une boîte 32 px)
HALFWAY_PAGE = 5            # point de reprise (page de 256 px)


@dataclass(frozen=True)
class EnemySpawn:
    kind: str        # "goomba" ou "koopa"
    x: int           # position x (px) du bord gauche
    row: int         # rangée sur laquelle il se tient (dessus du bloc = row*16)
    spawn_x: int     # abscisse qui déclenche l'apparition (chef de groupe)


def _group(kind, col, count, row=13):
    base = col * TILE
    # Les groupes NES espacent leurs membres de 24 px (1,5 bloc).
    return [EnemySpawn(kind, base + i * 24, row, base) for i in range(count)]


# 16 Goombas + 1 Koopa Troopa (vert), comme dans l'original.
ENEMIES = tuple(
    _group("goomba", 22, 1)
    + _group("goomba", 40, 1)
    + _group("goomba", 51, 2)
    + _group("goomba", 80, 2, row=HIGH_ROW)      # sur la rangée de briques
    + _group("goomba", 97, 2)
    + _group("koopa", 107, 1)
    + _group("goomba", 114, 2)
    + _group("goomba", 124, 2)
    + _group("goomba", 128, 2)
    + _group("goomba", 174, 2)
)

# ---------------------------------------------------------------------------
# Décor d'arrière-plan (se répète toutes les 48 colonnes, cf. BackSceneryData)
# (décalage, type, rangée du haut, largeur en colonnes)
# ---------------------------------------------------------------------------
SCENERY_PERIOD = 48
SCENERY_PATTERN = (
    (0, "hill_big", 10, 5),
    (8, "cloud", 3, 3),
    (11, "bush", 12, 5),
    (16, "hill_small", 11, 3),
    (19, "cloud", 2, 3),
    (23, "bush", 12, 3),
    (27, "cloud", 3, 5),
    (36, "cloud", 2, 4),
    (41, "bush", 12, 4),
)


def overworld_scenery(width=LEVEL_COLS):
    """Liste (colonne, type, rangée, largeur) des éléments de décor."""
    out = []
    for start in range(0, width, SCENERY_PERIOD):
        for off, kind, row, w in SCENERY_PATTERN:
            col = start + off
            if col < width:
                out.append((col, kind, row, w))
    return out


def build_overworld():
    """Construit la grille (ROWS x LEVEL_COLS, uint8) du monde 1-1."""
    grid = np.zeros((ROWS, LEVEL_COLS), dtype=np.uint8)
    grid[13:15, :] = GROUND
    for a, b in GAPS:
        grid[13:15, a:b + 1] = EMPTY
    for col, h in PIPES:
        top = 13 - h
        grid[top, col] = PIPE_TL
        grid[top, col + 1] = PIPE_TR
        grid[top + 1:13, col] = PIPE_L
        grid[top + 1:13, col + 1] = PIPE_R
    for col, row, kind in BLOCKS:
        grid[row, col] = kind
    for col, h in STAIRS:
        grid[13 - h:13, col] = STAIR
    grid[2, FLAGPOLE_COL] = FLAG_BALL
    grid[3:12, FLAGPOLE_COL] = FLAGPOLE
    grid[12, FLAGPOLE_COL] = STAIR
    return grid


# Château : tuiles de décor (non solides), table CastleMetatiles du jeu.
CASTLE_LAYOUT = (
    (None, "top", "top", "top", None),
    (None, "win_r", "brick", "win_l", None),
    ("top", "top_fill", "top_fill", "top_fill", "top"),
    ("brick", "brick", "door_top", "brick", "brick"),
    ("brick", "brick", "door", "brick", "brick"),
)
CASTLE_TOP_ROW = 8

# ---------------------------------------------------------------------------
# Salle bonus souterraine (pièces), atteinte par le tuyau de la colonne 57
# ---------------------------------------------------------------------------
BONUS_COLS = 16
BONUS_ENTRY_X = 40
BONUS_ENTRY_Y = -16


def build_bonus_room():
    grid = np.zeros((ROWS, BONUS_COLS), dtype=np.uint8)
    grid[13:15, :] = UG_GROUND
    grid[2:13, 0] = UG_BRICK                      # mur de gauche
    grid[2, 4:11] = UG_BRICK                      # plafond
    grid[10:13, 4:11] = UG_BRICK                  # bloc de briques central
    for c in range(4, 11):                         # 19 pièces
        grid[9, c] = COIN
        grid[7, c] = COIN
    for c in range(5, 10):
        grid[5, c] = COIN
    # Tuyau de sortie : embouchure horizontale (13) raccordée au tuyau
    # vertical (14-15) qui monte jusqu'au plafond.
    grid[11, 13] = SPIPE_TOP_MOUTH
    grid[12, 13] = SPIPE_BOT_MOUTH
    grid[11, 14] = SPIPE_JOIN_TOP
    grid[12, 14] = SPIPE_JOIN_BOT
    grid[2:11, 14] = PIPE_L
    grid[2:13, 15] = PIPE_R
    return grid


# ---------------------------------------------------------------------------
# Segments A-F de l'article (expérience de curriculum, Figure 2)
# ---------------------------------------------------------------------------
SEGMENTS = {
    "A": (0, 28),       # Intro : sol plat, 1 Goomba, premiers blocs
    "B": (28, 69),      # Tuyaux
    "C": (69, 90),      # Trous + blocs
    "D": (90, 134),     # « Enemy gauntlet »
    "E": (134, 163),    # Escaliers
    "F": (163, 198),    # Approche finale
}
SEGMENT_ORDER = "ABCDEF"


def segment_columns(order=SEGMENT_ORDER):
    """Colonnes d'origine dans l'ordre donné (nouvelle colonne -> ancienne).

    Les six segments couvrent les colonnes 0 à 197 ; la fin du niveau
    (drapeau en 198 + château) reste toujours à sa place, comme dans
    l'article.
    """
    order = "".join(order).upper()
    if sorted(order) != sorted(SEGMENT_ORDER):
        raise ValueError(f"ordre de segments invalide : {order!r}")
    cols = []
    for s in order:
        a, b = SEGMENTS[s]
        cols.extend(range(a, b))
    cols.extend(range(FLAGPOLE_COL, LEVEL_COLS))
    return cols


def permute_grid(grid, order, spawn_col=START_X // TILE):
    """Réordonne les segments d'une grille (ROWS x LEVEL_COLS).

    Une zone d'atterrissage de 3 colonnes autour du point de départ est
    dégagée (sol plein, rien au-dessus), comme dans l'article.
    """
    cols = segment_columns(order)
    new = grid[:, cols].copy()
    a, b = spawn_col - 1, spawn_col + 2
    new[:13, a:b] = EMPTY
    new[13:15, a:b] = GROUND
    return new


def permute_enemies(enemies, order):
    cols = segment_columns(order)
    inv = {old: new for new, old in enumerate(cols)}
    out = []
    for e in enemies:
        oc, off = divmod(e.x, TILE)
        sc, soff = divmod(e.spawn_x, TILE)
        out.append(EnemySpawn(e.kind, inv[oc] * TILE + off, e.row,
                              inv[sc] * TILE + soff))
    out.sort(key=lambda s: (s.spawn_x, s.x))
    return tuple(out)


def random_segment_order(seed):
    """Permutation aléatoire reproductible des segments A-F."""
    rng = np.random.default_rng(seed)
    return "".join(rng.permutation(list(SEGMENT_ORDER)))
