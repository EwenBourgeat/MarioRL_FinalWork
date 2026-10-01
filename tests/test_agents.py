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


def test_sarsa_update_uses_the_next_chosen_action():
    from agents.sarsa import SarsaAgent

    s, s2 = (1, 2, 3), (4, 5, 6)
    agent = SarsaAgent(3, alpha=0.1, gamma=0.99, seed=0)
    agent.q[s2] = [-5.0, 10.0, 2.0]
    # a' = droite (1) : cible = 0.5 + 0.99 * 10 = 10.4, comme Q-Learning
    assert agent.update(s, 1, 0.5, s2, 1, False) == pytest.approx(10.4)
    # a' = rien (0), tiré au hasard : cible = 0.5 + 0.99 * (-5) = -4.45
    agent.q[s] = [0.0, 0.0, 0.0]
    assert agent.update(s, 1, 0.5, s2, 0, False) == pytest.approx(-4.45)
    # fin de partie : pas d'action suivante, cible = r
    agent.q[s] = [0.0, 0.0, 0.0]
    agent.update(s, 2, -50.0, s2, None, True)
    assert agent.q[s][2] == pytest.approx(-5.0)


def test_sarsa_training_and_registry(tmp_path):
    from agents.sarsa import SarsaAgent
    from agents.training import train

    cfg = TrainConfig(algo="sarsa", level="v1", episodes=300, seed=3,
                      eval_every=0, log_every=0)
    a1, h1, _, g1, _ = train(cfg, log=None)
    a2, h2, _, g2, _ = train(cfg, log=None)
    assert h1 == h2 and a1.q == a2.q and g1 == g2
    assert isinstance(a1, SarsaAgent)
    meta = dict(cfg.as_dict(), metrics=article_metrics(h1), greedy=g1)
    path = save_model(a1, meta, h1, [], root=tmp_path)
    assert path.name == "sarsa_v1_s3_300ep"
    (model,) = list_models(tmp_path)
    assert model["algo"] == "sarsa" and model["label"] == "SARSA V1 S3 300"
    back = load_agent(model)
    assert isinstance(back, SarsaAgent) and back.q == a1.q


def test_unknown_algorithm_is_refused():
    from agents.training import train

    with pytest.raises(ValueError):
        train(TrainConfig(algo="nope", episodes=1), log=None)


def test_montecarlo_first_visit_average():
    from agents.montecarlo import MonteCarloAgent

    agent = MonteCarloAgent(3, gamma=0.5, seed=0)
    A, B = (1,), (2,)
    # partie : A/droite (+1) -> B/saut (0) -> A/droite (+4, fin)
    agent.update_episode([(A, 1, 1.0), (B, 2, 0.0), (A, 1, 4.0)])
    # G depuis la fin : 4 ; 0 + 0.5*4 = 2 ; 1 + 0.5*2 = 2
    assert agent.q[B][2] == pytest.approx(2.0)
    assert agent.q[A][1] == pytest.approx(2.0)      # première visite seulement
    assert agent.n[A][1] == 1 and agent.n[B][2] == 1
    # deuxième partie : A/droite rapporte 10 -> moyenne (2 + 10) / 2 = 6
    agent.update_episode([(A, 1, 10.0)])
    assert agent.q[A][1] == pytest.approx(6.0) and agent.n[A][1] == 2


def test_montecarlo_training_save_load(tmp_path):
    from agents.montecarlo import MonteCarloAgent
    from agents.training import train

    cfg = TrainConfig(algo="montecarlo", level="v1", episodes=200, seed=4,
                      eval_every=0, log_every=0, alpha=None)
    a1, h1, _, g1, _ = train(cfg, log=None)
    a2, h2, _, _, _ = train(cfg, log=None)
    assert h1 == h2 and a1.q == a2.q and a1.n == a2.n
    meta = dict(cfg.as_dict(), metrics=article_metrics(h1), greedy=g1)
    path = save_model(a1, meta, h1, [], root=tmp_path)
    back = load_agent(path)
    assert isinstance(back, MonteCarloAgent)
    assert back.q == a1.q and back.n == a1.n


def test_dqn_learns_target_and_saves(tmp_path):
    pytest.importorskip("torch")
    from agents.dqn import DQNAgent
    from agents.training import train

    # petit entraînement (v1, peu d'épisodes) : il doit tourner, être
    # reproductible et se recharger à l'identique
    cfg = TrainConfig(algo="dqn", level="v1", episodes=30, seed=1,
                      eval_every=0, log_every=0, alpha=None, eps_min=0.05)
    a1, h1, _, g1, _ = train(cfg, log=None)
    a2, h2, _, g2, _ = train(cfg, log=None)
    assert isinstance(a1, DQNAgent) and h1 == h2 and g1 == g2
    assert a1.updates > 0                       # le réseau a appris
    meta = dict(cfg.as_dict(), metrics=article_metrics(h1), greedy=g1)
    path = save_model(a1, meta, h1, [], root=tmp_path)
    assert (path / "dqn.pt").exists()
    (model,) = list_models(tmp_path)
    back = load_agent(model)
    obs = make_env(cfg).reset()[0]
    assert np.allclose(back.q_values(obs), a1.q_values(obs))
    assert greedy_test(make_env(cfg), back, cfg.seed) == g1
