"""Mesure la vitesse des environnements (actions aléatoires, sans rendu).

    python scripts/benchmark.py
"""

import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import mario_env  # noqa: E402
from mario_env.game import Game  # noqa: E402


def bench_env(env, n_steps):
    rng = np.random.default_rng(0)
    env.reset(seed=0)
    n_act = env.action_space.n
    t = time.perf_counter()
    episodes = 0
    for _ in range(n_steps):
        _, _, term, trunc, _ = env.step(int(rng.integers(n_act)))
        if term or trunc:
            env.reset()
            episodes += 1
    dt = time.perf_counter() - t
    return n_steps / dt, episodes


def main():
    g = Game()
    t = time.perf_counter()
    n = 50_000
    for i in range(n):
        g.step(0x01 if i % 7 else 0x81)
        if g.dead or g.level_complete:
            g = Game()
    print(f"Moteur NES seul          : {n / (time.perf_counter() - t):>9,.0f} images/s")

    cases = [
        ("MarioNES tiles (skip 4)", mario_env.MarioNESEnv(obs_type="tiles")),
        ("MarioNES vector (skip 4)", mario_env.MarioNESEnv(obs_type="vector")),
        ("MarioNES paper (skip 4)", mario_env.MarioNESEnv(
            obs_type="paper", actions="paper", level="v3")),
        ("MarioNES rgb 84x84 gris", mario_env.MarioNESEnv(
            obs_type="rgb", rgb_size=(84, 84), grayscale=True)),
        ("MarioGrid v1", mario_env.MarioGridEnv(level="v1")),
        ("MarioGrid v2", mario_env.MarioGridEnv(level="v2")),
        ("MarioGrid v3", mario_env.MarioGridEnv(level="v3")),
    ]
    for name, env in cases:
        n = 5_000 if "rgb" in name else 20_000
        sps, eps = bench_env(env, n)
        print(f"{name:<25}: {sps:>9,.0f} pas/s  ({eps} épisodes)")


if __name__ == "__main__":
    main()
