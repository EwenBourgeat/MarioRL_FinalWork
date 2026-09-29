"""Vérifie le niveau contre les données d'origine du jeu NES.

Les octets ci-dessous sont les données du niveau 1-1 telles qu'elles
figurent dans le désassemblage de Super Mario Bros. (« SMBDIS », labels
``L_GroundArea6`` pour le décor et ``E_GroundArea6`` pour les ennemis).
Le test les décode avec les règles du moteur NES et vérifie que la carte
construite par ``level_data`` est identique, case par case.

Format d'un objet décor (2 octets) : ``XXXXYYYY PTTTLLLL``
X = colonne dans la page de 256 px, Y = rangée (0-11 = objets, 12-15 =
objets spéciaux), P = passer à la page suivante, T = type, L = longueur.
Les rangées du jeu commencent 32 px sous le haut de l'écran (HUD), d'où le
décalage de +2 avec les rangées d'écran utilisées dans ``level_data``.
"""

import numpy as np

from mario_env import constants as C
from mario_env import level_data as L

L_GROUND_AREA_6 = bytes.fromhex(
    "0781 4724 5700 6301 7701"
    "c971 68f2 e773 97fb 0683"
    "5c01 d722 e700 03a7 6c02"
    "b322 e301 e707 47a0 5706"
    "a701 d300 d701 0781 6720"
    "9322 03a3 1c61 1721 6f33"
    "c763 d862 e961 fa60 4fb3"
    "8763 9c01 b763 c862 d961"
    "ea60 39f1 8721 a701 b720"
    "39f1 5f38 6dc1 af26"
    "fd".replace(" ", ""))

E_GROUND_AREA_6 = bytes.fromhex(
    "1ec200 6b06 8b86 63b7 0f05"
    "0306 2306 4bb7 bb00 5bb7"
    "fb37 3bb7 0f0b 1b37"
    "ff".replace(" ", ""))

# Petits objets (type 0, rangées 0-11) utilisés dans 1-1
SMALL_OBJECTS = {0: C.QBLOCK_POWERUP, 1: C.QBLOCK_COIN, 3: C.HIDDEN_1UP,
                 4: C.BRICK_POWERUP, 6: C.BRICK_STAR, 7: C.BRICK_COIN}


def decode_area(data, width=L.LEVEL_COLS):
    grid = np.zeros((C.ROWS, width), dtype=np.uint8)
    grid[13:15, :] = C.GROUND                 # sol par défaut (en-tête $50 $21)
    warp_pipes = []
    page = 0
    i = 0
    while data[i] != 0xFD:
        b1, b2 = data[i], data[i + 1]
        i += 2
        if b2 & 0x80:
            page += 1
        col = page * 16 + (b1 >> 4)
        y = b1 & 0x0F
        kind = (b2 >> 4) & 0x07
        length = b2 & 0x0F
        row = y + 2                             # rangée du jeu -> rangée écran
        if y <= 11:
            if kind == 0:
                grid[row, col] = SMALL_OBJECTS[length]
            elif kind == 2:                     # rangée de briques
                grid[row, col:col + length + 1] = C.BRICK
            elif kind == 6:                     # colonne de blocs durs
                grid[row:row + length + 1, col] = C.STAIR
            elif kind == 7:                     # tuyau vertical
                h = (length & 0x07) + 1
                grid[row, col:col + 2] = (C.PIPE_TL, C.PIPE_TR)
                grid[row + 1:row + h, col] = C.PIPE_L
                grid[row + 1:row + h, col + 1] = C.PIPE_R
                if length & 0x08:
                    warp_pipes.append(col)
            else:
                raise AssertionError(f"objet non géré : {b1:02x} {b2:02x}")
        elif y == 12:
            if kind == 0:                       # trou
                grid[13:15, col:col + length + 1] = C.EMPTY
            elif kind == 6:                     # rangée de blocs ? (haute)
                grid[5, col:col + length + 1] = C.QBLOCK_COIN
            else:
                raise AssertionError(f"objet non géré : {b1:02x} {b2:02x}")
        elif y == 13:
            assert b2 & 0x40 and b2 & 0x3F == 0x01   # mât du drapeau
            grid[2, col] = C.FLAG_BALL
            grid[3:12, col] = C.FLAGPOLE
            grid[12, col] = C.STAIR
        elif y == 15:
            if kind == 3:                       # escalier (hauteurs 1..8, 8)
                controls = range(8, 8 - (length + 1), -1)
                heights = (8, 8, 7, 6, 5, 4, 3, 2, 1)
                for k, ctrl in enumerate(controls):
                    h = heights[ctrl]
                    grid[13 - h:13, col + k] = C.STAIR
            elif kind == 2:                     # château (décor)
                castle_col = col
            else:
                raise AssertionError(f"objet non géré : {b1:02x} {b2:02x}")
    return grid, warp_pipes, castle_col


def decode_enemies(data):
    """Renvoie [(type, colonne, y, nombre)] ; y = ordonnée NES d'apparition."""
    names = {0x00: "koopa", 0x06: "goomba"}
    out = []
    page = 0
    i = 0
    while data[i] != 0xFF:
        b1, b2 = data[i], data[i + 1]
        y = b1 & 0x0F
        if y == 0x0E:                           # pointeur de zone (tuyau)
            if b2 & 0x80:
                page += 1
            i += 3
            continue
        i += 2
        if y == 0x0F:                           # saut de page
            page = b2 & 0x3F
            continue
        if b2 & 0x80:
            page += 1
        col = page * 16 + (b1 >> 4)
        ident = b2 & 0x3F
        if ident == 0x37:                       # groupe de 2 Goombas au sol
            out.append(("goomba", col, 0xB0, 2))
        else:
            out.append((names[ident], col, y * 16, 1))
    return out


def test_area_data_matches_level():
    grid, warps, castle = decode_area(L_GROUND_AREA_6)
    ours = L.build_overworld()
    diff = np.argwhere(grid != ours)
    assert len(diff) == 0, f"cases différentes (rangée, colonne) : {diff[:10]}"
    assert warps == [L.WARP_PIPE_COL]
    assert castle == L.CASTLE_COL


def test_flagpole_distance_from_final_staircase():
    grid, _, _ = decode_area(L_GROUND_AREA_6)
    stair_cols = [c for c in range(212) if (grid[:13, c] == C.STAIR).any()]
    last_step = max(c for c in stair_cols if c < L.FLAGPOLE_COL)
    assert last_step == 189 and L.FLAGPOLE_COL == 198
    # 8 colonnes vides entre la dernière marche et le mât
    assert all((grid[:13, c] == C.EMPTY).all() for c in range(190, 198))


def test_enemy_data_matches_level():
    decoded = decode_enemies(E_GROUND_AREA_6)
    ours = [(e.kind, e.col, e.y, e.count) for e in L.ENEMIES]
    assert decoded == ours
    n_goombas = sum(n for k, _, _, n in decoded if k == "goomba")
    assert n_goombas == 16
