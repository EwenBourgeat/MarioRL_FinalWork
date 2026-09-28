"""Vérifie que le niveau reproduit bien la carte de 1-1."""

import numpy as np

from mario_env import constants as C
from mario_env import level_data as L


def test_dimensions():
    grid = L.build_overworld()
    assert grid.shape == (15, 212)


def test_gaps_match_paper():
    grid = L.build_overworld()
    holes = [c for c in range(212) if grid[13, c] == C.EMPTY]
    assert holes == [69, 70, 86, 87, 88, 153, 154]


def test_pipes_positions_and_heights():
    grid = L.build_overworld()
    pipes = {}
    for c in range(211):
        col = grid[:, c]
        if C.PIPE_TL in col:
            top = int(np.where(col == C.PIPE_TL)[0][0])
            pipes[c] = 13 - top
    assert pipes == {28: 2, 38: 3, 46: 4, 57: 4, 163: 2, 179: 2}


def test_blocks():
    kinds = [k for _, _, k in L.BLOCKS]
    assert kinds.count(C.QBLOCK_COIN) + kinds.count(C.QBLOCK_POWERUP) == 13
    assert kinds.count(C.QBLOCK_POWERUP) == 3
    assert kinds.count(C.HIDDEN_1UP) == 1
    assert kinds.count(C.BRICK_STAR) == 1
    assert kinds.count(C.BRICK_COIN) == 1


def test_enemies_16_goombas_1_koopa():
    kinds = [e.kind for e in L.ENEMIES]
    assert kinds.count("goomba") == 16
    assert kinds.count("koopa") == 1
    # colonnes utilisées dans l'article (figure 2), arrondies vers le haut
    cols = sorted(-(-e.x // 16) for e in L.ENEMIES)
    assert cols == [22, 40, 51, 53, 80, 82, 97, 99, 107, 114, 116, 124,
                    126, 128, 130, 174, 176]


def test_final_staircase_and_flag():
    grid = L.build_overworld()
    heights = [int((grid[:13, c] == C.STAIR).sum()) for c in range(181, 190)]
    assert heights == [1, 2, 3, 4, 5, 6, 7, 8, 8]
    assert grid[3, 198] == C.FLAGPOLE and grid[12, 198] == C.STAIR


def test_segment_permutation_preserves_content():
    grid = L.build_overworld()
    for order in ("ABCDEF", "FEDCBA", "BECDFA"):
        g2 = L.permute_grid(grid, order)
        assert g2.shape == grid.shape
        for t in (C.BRICK, C.QBLOCK_COIN, C.PIPE_TL):
            assert (g2 == t).sum() == (grid == t).sum()
        en = L.permute_enemies(L.ENEMIES, order)
        assert len(en) == 17
    assert L.segment_columns("ABCDEF") == list(range(212))


def test_bonus_room_has_19_coins():
    room = L.build_bonus_room()
    assert (room == C.COIN).sum() == 19
