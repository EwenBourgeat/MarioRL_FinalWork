"""Tests du moteur NES (physique, mécaniques, sauvegardes)."""

import pytest

from mario_env import constants as C
from mario_env.game import Game, GameConfig


def run(g, buttons, n):
    for _ in range(n):
        g.step(buttons)


def test_walk_and_run_max_speeds():
    g = Game(GameConfig(enemies=False))
    run(g, C.BTN_RIGHT, 80)
    assert g.p.x_speed == 0x18          # 1,5 px/image
    g = Game(GameConfig(enemies=False))
    run(g, C.BTN_RIGHT | C.BTN_B, 80)
    assert g.p.x_speed == 0x28          # 2,5 px/image


def test_jump_heights():
    g = Game(GameConfig(enemies=False))
    y0 = g.p.y
    top = y0
    g.step(C.BTN_A)
    while True:
        g.step(C.BTN_A)
        top = min(top, g.p.y)
        if g.p.state == 0:
            break
    assert 60 <= y0 - top <= 72         # ~4 blocs en tenant A
    g = Game(GameConfig(enemies=False))
    g.step(C.BTN_A)
    top = y0
    while True:
        g.step(0)
        top = min(top, g.p.y)
        if g.p.state == 0:
            break
    assert y0 - top < 40                # saut court si A relâché


def test_determinism_and_save_states():
    seq = [C.BTN_RIGHT, C.BTN_RIGHT | C.BTN_A, C.BTN_RIGHT | C.BTN_B, 0] * 60
    a, b = Game(), Game()
    for btn in seq:
        a.step(btn)
        b.step(btn)
    assert (a.p.x, a.p.y, a.score, a.frame) == (b.p.x, b.p.y, b.score, b.frame)
    state = a.get_state()
    run(a, C.BTN_RIGHT, 100)
    a.set_state(state)
    assert (a.p.x, a.p.y, a.frame) == (b.p.x, b.p.y, b.frame)
    run(a, C.BTN_RIGHT, 10)
    run(b, C.BTN_RIGHT, 10)
    assert (a.p.x, a.p.y) == (b.p.x, b.p.y)


def test_question_block_gives_mushroom_and_growth():
    g = Game(GameConfig(enemies=False))
    g.p.x = 21 * 16
    g.cam_x = 21 * 16 - 100
    run(g, C.BTN_A, 30)
    assert g.grid[9, 21] == C.USED
    assert any(e.kind == "mushroom" for e in g.enemies)
    run(g, 0, 70)
    m = next(e for e in g.enemies if e.kind == "mushroom")
    for _ in range(300):
        g.step(C.BTN_RIGHT if g.p.x < m.x else C.BTN_LEFT)
        if g.p.status == 1:
            break
    assert g.p.status == 1


def test_small_mario_cannot_break_bricks_big_can():
    g = Game(GameConfig(enemies=False))
    g.p.x = 20 * 16
    g.cam_x = 20 * 16 - 100
    run(g, C.BTN_A, 30)
    assert g.grid[9, 20] == C.BRICK
    g = Game(GameConfig(enemies=False, start_status=1))
    g.p.x = 20 * 16
    g.cam_x = 20 * 16 - 100
    run(g, C.BTN_A, 30)
    assert g.grid[9, 20] == C.EMPTY
    assert g.stats["bricks_broken"] == 1


def test_goomba_contact_kills_small_mario():
    g = Game()
    for _ in range(600):
        g.step(C.BTN_RIGHT)
        if g.dead:
            break
    assert g.dead and g.death_cause == "enemy"


def test_pit_death():
    g = Game(GameConfig(enemies=False))
    g.p.x = 67 * 16
    g.cam_x = 67 * 16 - 100
    for _ in range(300):
        g.step(C.BTN_RIGHT)
        if g.dead:
            break
    assert g.dead and g.death_cause == "pit"


def test_bonus_room_round_trip():
    g = Game(GameConfig(enemies=False))
    g.p.x = 57 * 16 + 4
    g.p.y = 112
    g.cam_x = 57 * 16 - 100
    run(g, 0, 5)
    run(g, C.BTN_DOWN, 60)
    assert g.area == "bonus"
    run(g, 0, 80)
    run(g, C.BTN_RIGHT | C.BTN_A, 40)
    run(g, C.BTN_RIGHT, 200)
    assert g.area == "overworld"
    run(g, 0, 60)
    assert g.mode == "play" and 162 * 16 <= g.p.x <= 170 * 16
    assert g.coins > 0


def test_flagpole_and_end_sequence():
    g = Game(GameConfig(enemies=False))
    g.p.x = 191 * 16
    g.cam_x = 191 * 16 - 100
    for i in range(300):
        g.step(C.BTN_RIGHT | C.BTN_B | (C.BTN_A if 30 < i < 60 else 0))
        if g.level_complete:
            break
    assert g.level_complete
    for _ in range(3000):
        g.step(0)
        if g.finished:
            break
    assert g.finished and g.timer == 0 and g.score > 0


def test_lives_and_respawn():
    g = Game(GameConfig(lives=2))
    for _ in range(600):
        g.step(C.BTN_RIGHT)
        if g.dead:
            break
    assert g.lives == 1
    run(g, 0, 250)
    assert g.mode == "play" and g.p.x == 40


@pytest.mark.parametrize("order", ["FEDCBA", "BECDFA"])
def test_permuted_levels_run(order):
    g = Game(GameConfig(segment_order=order))
    run(g, C.BTN_RIGHT, 200)
    assert g.frame == 200
