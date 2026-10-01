"""Tests de l'agent Q-Learning, des mesures et du dossier models/."""

import json

import numpy as np
import pytest

from agents.metrics import article_metrics, episodes_to, rolling_mean
from agents.qlearning import QLearningAgent
from agents.registry import list_models, load_agent, save_model
from agents.training import TrainConfig, greedy_test, make_env, train_qlearning


def test_update_formula():
    agent = QLearningAgent(3, alpha=0.1, gamma=0.99, seed=0)
    s, s2 = (1, 2, 3), (4, 5, 6)
    agent.q[s2] = [0.0, 10.0, 2.0]
    # cible = r + gamma * max Q(s', .) = 1 + 0.99 * 10 = 10.9
    err = agent.update(s, 1, 1.0, s2, terminated=False)
    assert err == pytest.approx(10.9)
    assert agent.q[s] == pytest.approx([0.0, 1.09, 0.0])
    # état terminal : pas de bootstrap, cible = r
    agent.update(s, 0, -50.0, s2, terminated=True)
    assert agent.q[s][0] == pytest.approx(-5.0)


def test_ties_are_broken_at_random():
    agent = QLearningAgent(3, seed=1)
    picks = {agent.best_action((0,)) for _ in range(100)}
    assert picks == {0, 1, 2}
    agent.q[(0,)] = [0.0, 1.0, 1.0]
    assert {agent.best_action((0,)) for _ in range(100)} == {1, 2}


def test_epsilon_extremes():
    agent = QLearningAgent(3, seed=0)
    agent.q[(0,)] = [0.0, 0.0, 5.0]
    assert all(agent.act((0,), 0.0) == 2 for _ in range(50))
    assert len({agent.act((0,), 1.0) for _ in range(200)}) == 3


def test_save_load_roundtrip(tmp_path):
    agent = QLearningAgent(3, alpha=0.2, gamma=0.9, seed=0)
    agent.q = {(1, 2, 3): [0.5, -1.0, 2.0], (4, 5, 0): [0.0, 0.0, 0.1]}
    agent.save(tmp_path / "q.npz")
    back = QLearningAgent.load(tmp_path / "q.npz")
    assert back.q == agent.q
    assert (back.alpha, back.gamma) == (0.2, 0.9)


def test_rolling_and_convergence():
    wins = [0] * 100 + [1] * 100
    r = rolling_mean(wins, 100)
    assert len(r) == 101 and r[0] == 0 and r[-1] == 1
    # 50 victoires sur les 100 derniers épisodes à l'épisode 150
    assert episodes_to(wins, 0.5) == 150
    assert episodes_to(wins, 0.8) == 180
    assert episodes_to([0] * 300, 0.5) is None


def test_training_is_reproducible_and_learns():
    cfg = TrainConfig(level="v1", episodes=400, seed=7, eval_every=0,
                      log_every=0)
    a1, h1, _, g1, _ = train_qlearning(cfg, log=None)
    a2, h2, _, g2, _ = train_qlearning(cfg, log=None)
    assert h1 == h2 and a1.q == a2.q and g1 == g2
    m = article_metrics(h1)
    assert m["episodes"] == 400 and m["last"] == 400
    # dès 400 épisodes, Mario va plus loin qu'au hasard au début
    assert np.mean(h1["max_col"][-100:]) > np.mean(h1["max_col"][:100])
    # le test glouton est déterministe
    assert greedy_test(make_env(cfg), a1, cfg.seed) == g1


def test_registry_roundtrip(tmp_path):
    cfg = TrainConfig(level="v1", episodes=50, seed=3, eval_every=25,
                      log_every=0)
    agent, history, tests, final, _ = train_qlearning(cfg, log=None)
    meta = dict(cfg.as_dict(), algo="qlearning",
                metrics=article_metrics(history), greedy=final)
    p1 = save_model(agent, meta, history, tests, root=tmp_path)
    p2 = save_model(agent, meta, history, tests, root=tmp_path)
    assert p1.name == "qlearning_v1_s3_50ep"
    assert p2.name == "qlearning_v1_s3_50ep_2"
    models = list_models(tmp_path)
    assert [m["name"] for m in models] == [p1.name, p2.name]
    assert models[0]["label"] == "QLEARNING V1 S3 50"
    assert len(models[0]["tests"]) == 2
    assert load_agent(models[0]).q == agent.q
    lines = (p1 / "history.csv").read_text().splitlines()
    assert len(lines) == 51 and lines[0].startswith("episode,return,win")
    json.loads((p1 / "meta.json").read_text())
