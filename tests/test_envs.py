"""Tests des environnements Gymnasium."""

import numpy as np
import gymnasium as gym
import pytest
from gymnasium.utils.env_checker import check_env

import mario_env  # noqa: F401  (enregistre les environnements)
from mario_env import RewardConfig, state_key
from mario_env.curriculum import PAPER_CONDITIONS


@pytest.mark.parametrize("kw", [
    dict(obs_type="tiles"),
    dict(obs_type="tiles", tile_view="mario"),
    dict(obs_type="vector", actions="complex"),
    dict(obs_type="paper", actions="paper", level="v3"),
    dict(obs_type="rgb", rgb_size=(84, 84), grayscale=True),
])
def test_nes_env_api(kw):
    env = gym.make("MarioNES-v0", **kw)
    check_env(env.unwrapped, skip_render_check=True)
    obs, info = env.reset(seed=1)
    assert env.observation_space.contains(obs)
    for _ in range(50):
        obs, r, term, trunc, info = env.step(env.action_space.sample())
        assert env.observation_space.contains(obs)
        if term or trunc:
            obs, info = env.reset()
    env.close()


@pytest.mark.parametrize("level", ["v1", "v2", "v3"])
def test_grid_env_api(level):
    env = gym.make("MarioGrid-v0", level=level)
    check_env(env.unwrapped, skip_render_check=True)
    obs, _ = env.reset(seed=0)
    expected = {"v1": 3, "v2": 59, "v3": 115}[level]
    assert obs.shape == (expected,)
    assert isinstance(state_key(obs), tuple)


def _scripted(env):
    c, r = env.col, env.row
    ahead = env._solid(r, c + 1) or env._solid(r, c + 2)
    gap = not env._solid(12, c + 1) or not env._solid(12, c + 2)
    enemy = any(e[4] and e[3] and 0 < e[0] - c <= 3 and abs(e[1] - r) <= 1
                for e in env.enemies)
    if env._solid(r + 1, c) and (ahead or gap or enemy):
        return 2
    return 1


@pytest.mark.parametrize("level", ["v1", "v2"])
def test_grid_level_is_winnable(level):
    env = mario_env.MarioGridEnv(level=level)
    env.reset()
    done = False
    total = 0.0
    while not done:
        _, r, term, trunc, info = env.step(_scripted(env))
        total += r
        done = term or trunc
    assert info["win"]
    assert total > 150          # ~ +100 drapeau + 0,5 x 195 cases


def test_grid_rewards_follow_paper_table():
    env = mario_env.MarioGridEnv(level="v1")
    env.reset()
    _, r, *_ = env.step(1)
    assert r == pytest.approx(0.5)
    _, r, *_ = env.step(0)
    assert r == pytest.approx(-0.1)
    custom = mario_env.MarioGridEnv(level="v1",
                                    reward={"progress_per_tile": 2.0})
    custom.reset()
    _, r, *_ = custom.step(1)
    assert r == pytest.approx(2.0)


def test_grid_determinism():
    a = mario_env.MarioGridEnv(level="v3")
    b = mario_env.MarioGridEnv(level="v3")
    rng = np.random.default_rng(3)
    oa, _ = a.reset()
    ob, _ = b.reset()
    for _ in range(300):
        act = int(rng.integers(3))
        oa, ra, ta, tra, _ = a.step(act)
        ob, rb, tb, trb, _ = b.step(act)
        assert np.array_equal(oa, ob) and ra == rb
        if ta or tra:
            oa, _ = a.reset()
            ob, _ = b.reset()


@pytest.mark.parametrize("name", list(PAPER_CONDITIONS))
def test_curriculum_conditions(name):
    env = mario_env.MarioGridEnv(level="v3",
                                 segment_order=PAPER_CONDITIONS[name])
    obs, _ = env.reset()
    assert len(env.enemies) == 17
    assert env.col == 3 and env._solid(12, 3)


def test_nes_env_rewards_and_clone():
    env = mario_env.MarioNESEnv(actions="right_only", level="v1")
    env.reset(seed=0)
    total = 0.0
    for _ in range(20):
        _, r, *_ = env.step(1)
        total += r
    assert total > 0
    s = env.clone_state()
    o1, *_ = env.step(2)
    env.restore_state(s)
    o2, *_ = env.step(2)
    assert np.array_equal(o1, o2)


def test_nes_env_start_col_and_render():
    env = mario_env.MarioNESEnv(render_mode="rgb_array")
    obs, info = env.reset(options={"start_col": 100})
    assert info["x"] == 1600
    frame = env.render()
    assert frame.shape == (240, 256, 3) and frame.dtype == np.uint8


def test_vector_env():
    envs = gym.vector.SyncVectorEnv(
        [lambda: gym.make("MarioNES-v0", obs_type="tiles") for _ in range(2)])
    obs, _ = envs.reset(seed=0)
    assert obs.shape == (2, 13, 16)
    obs, r, term, trunc, _ = envs.step(np.array([1, 2]))
    assert r.shape == (2,)
    envs.close()


def test_reward_presets():
    for name in ("paper", "progress", "score"):
        assert isinstance(RewardConfig.preset(name), RewardConfig)


def test_nes_env_multiple_lives():
    env = mario_env.MarioNESEnv(actions="right_only", lives=2)
    env.reset(seed=0)
    deaths = 0
    for _ in range(2000):
        _, r, term, trunc, info = env.step(1)
        if info["dead"]:
            deaths += 1
            assert r <= -50 + 1
        if term:
            break
    assert deaths == 2 and term


# ----------------------------------------------------------------------
# Vue complète (notre DQN)
# ----------------------------------------------------------------------
def _full_env_at(col, row=11):
    """Environnement en vue complète, Mario posé en (col, row) au sol."""
    from mario_env import MarioGridEnv
    env = MarioGridEnv(level="v3", obs="full")
    env.reset()
    env.col, env.row, env.phase = col, row, 0
    return env, env._obs_full()


def test_full_obs_shape_and_values():
    from mario_env import MarioGridEnv
    env = MarioGridEnv(level="v3", obs="full")
    obs, _ = env.reset()
    assert obs.shape == env.observation_space.shape == (6 * 14 * 28 + 10,)
    assert set(np.unique(obs)) <= {0, 1}


def test_full_obs_shows_pits_mario_and_enemies():
    env, obs = _full_env_at(85)
    ch = obs[:6 * 14 * 28].reshape(6, 14, 28)
    # Mario au milieu (colonne 14 de la vue), sur sa ligne
    assert np.argwhere(ch[5]).tolist() == [[11, 14]]
    # le trou des colonnes 86-88 : pas de sol juste devant Mario
    assert ch[0][12, 14] == 1 and ch[0][12, 15:18].sum() == 0
    assert ch[0][12, 18] == 1
    # ennemis : un seul calque par ennemi, selon sa direction
    left = env.col - 14
    for e in env.enemies:
        c = e[0] - left
        if e[4] and 0 <= c < 28:
            assert ch[3 if e[2] < 0 else 4, e[1], c] == 1
    # étape du saut (au sol) et rythme des ennemis : une seule case à 1
    assert obs[-10:-3].tolist() == [1, 0, 0, 0, 0, 0, 0]
    assert obs[-3:].sum() == 1


def test_paper_obs_unchanged_by_default():
    from mario_env import MarioGridEnv
    env = MarioGridEnv(level="v3")
    assert env.observation_space.shape == (115,)
