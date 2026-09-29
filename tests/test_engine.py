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


def test_timer_frames_option():
    g = Game(GameConfig(enemies=False, timer_frames=60))
    run(g, 0, 120)
    assert g.timer == 398
    g = Game(GameConfig(enemies=False))
    run(g, 0, 120)
    assert g.timer == 395


def test_scroll_back_option():
    for back in (False, True):
        g = Game(GameConfig(enemies=False, scroll_back=back))
        run(g, C.BTN_RIGHT, 150)
        run(g, C.BTN_LEFT, 30)         # fin du dérapage
        cam = g.cam_x
        run(g, C.BTN_LEFT, 120)
        if back:
            assert g.cam_x < cam and g.p.x >= g.cam_x
        else:
            assert g.cam_x == cam


def _flag_jump(jump_frame, speed=0x28, run=True):
    """Mario court sur le haut de l'escalier final (col. 188) et saute."""
    g = Game(GameConfig(enemies=False))
    g.p.x, g.p.y, g.p.state = 188 * 16, 80 - 32, 0
    g.p.x_speed = g.p.x_abs = speed
    g.cam_x = g.p.x - 112
    base = C.BTN_RIGHT | (C.BTN_B if run else 0)
    for f in range(200):
        g.step(base | (C.BTN_A if f >= jump_frame else 0))
        if g.level_complete:
            return C.FLAGPOLE_POINTS[g.flag_score_idx]
        if f > jump_frame + 2 and g.p.state == 0 and g.p.y > 150:
            return None                     # retombé avant le mât
    return None


def test_flagpole_top_needs_full_speed_jump_at_the_edge():
    # à pleine vitesse, un saut au tout dernier moment donne 5000 points
    results = [_flag_jump(k) for k in range(12)]
    assert 5000 in results
    assert results[0] == 2000               # sauter trop tôt : 2000
    # en marchant, on ne peut pas atteindre le mât depuis l'escalier
    assert all(_flag_jump(k, 0x18, run=False) is None for k in range(12))


def test_goomba_groups_appear_at_screen_edge():
    g = Game(GameConfig(timer=False))
    first = {}
    for _ in range(900):
        g.p.star_timer = 100
        g.p.x = min(g.p.x + 2, 45 * 16)     # avance sans obstacle
        g.cam_x = max(g.cam_x, g.p.x - 112)
        g.step(0)
        for e in g.enemies:
            first.setdefault(e.uid, (e.x, g.cam_x))
    x, cam = first[20]                      # objet 2 = groupe de la colonne 54
    assert x == cam + 255 - 1 or x == cam + 255
    x2, _ = first[21]
    assert x2 - x == 24
