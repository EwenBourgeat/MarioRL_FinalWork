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


def test_dqn_full_view_variant_and_robustness(tmp_path):
    pytest.importorskip("torch")
    from agents.training import robustness_test, train

    cfg = TrainConfig(algo="dqn", level="v3", episodes=10, seed=2,
                      eval_every=0, log_every=0, alpha=None, eps_min=0.05,
                      obs="full", variant="E1")
    agent, h, _, g, _ = train(cfg, log=None)
    assert agent.obs_high.shape == (2362,)
    meta = dict(cfg.as_dict(), metrics=article_metrics(h), greedy=g)
    path = save_model(agent, meta, h, [], root=tmp_path)
    assert path.name == "dqn_v3_s2_10ep_e1"
    (model,) = list_models(tmp_path)
    from agents.registry import short_label
    assert short_label(model) == "V3 GRAINE 2 10 EP E1"
    back = load_agent(model)
    # le menu recrée l'environnement avec la vue enregistrée dans le modèle
    env = make_env(TrainConfig(**{k: model[k] for k in ("level", "obs")}))
    assert greedy_test(env, back, cfg.seed) == g
    r = robustness_test(env, back, cfg.seed, episodes=3)
    assert r["episodes"] == 3 and 0 <= r["win_rate"] <= 1


# ----------------------------------------------------------------------
# Notre DQN, étape 2
# ----------------------------------------------------------------------
def test_dqn_n_step_returns():
    pytest.importorskip("torch")
    from agents.dqn import DQNAgent

    ag = DQNAgent(np.ones(2), gamma=0.5, n_step=3)
    o = np.zeros(2)
    for r, end in [(1, False), (2, False), (3, False), (4, True)]:
        ag.observe(o, 0, r, o, end, end)
    m = ag.memory
    # 1 + .5*2 + .25*3 ; puis, en fin de partie : 2+.5*3+.25*4, 3+.5*4, 4
    assert m.r[:m.size].tolist() == [2.75, 4.5, 5.0, 4.0]
    assert m.done[:m.size].tolist() == [0, 1, 1, 1]
    assert m.disc[0] == pytest.approx(0.125)        # gamma^3


def test_dqn_soft_target_and_options_learn():
    torch = pytest.importorskip("torch")
    from agents.dqn import DQNAgent

    ag = DQNAgent(np.ones(4), learning_starts=8, batch_size=8, double=True,
                  n_step=3, grad_clip=10, tau=0.005)
    rng = np.random.default_rng(0)
    for i in range(40):
        o = rng.integers(0, 2, 4)
        ag.observe(o, i % 3, 1.0, o, i % 10 == 9, i % 10 == 9)
    before = ag.target[0].weight.detach().clone()
    gap = (ag.net[0].weight - before).detach()
    ag.learn()
    moved = (ag.target[0].weight - before).detach()
    # la cible a fait 0,5 % du chemin vers le réseau (après sa correction)
    gap2 = (ag.net[0].weight.detach() - before)
    assert torch.allclose(moved, 0.005 * gap2, atol=1e-7)
    assert gap.abs().max() > 0


def test_keep_best_restores_best_version():
    from agents.training import train

    cfg = TrainConfig(level="v1", episodes=400, seed=3, eval_every=50,
                      log_every=0, keep_best=True)
    agent, h, tests, final, _ = train(cfg, log=None)
    if any(t["win"] for t in tests):
        assert final["win"] == 1
        assert agent.best_episode in [t["episode"] for t in tests if t["win"]]


def test_dqn_step2_train_save_load(tmp_path):
    pytest.importorskip("torch")
    from agents.training import train

    cfg = TrainConfig(algo="dqn", level="v1", episodes=20, seed=4,
                      eval_every=10, log_every=0, alpha=None, eps_min=0.05,
                      double=True, n_step=3, grad_clip=10.0, tau=0.005,
                      keep_best=True, variant="E2")
    a1, h1, _, g1, _ = train(cfg, log=None)
    a2, h2, _, g2, _ = train(cfg, log=None)
    assert h1 == h2 and g1 == g2                     # reproductible
    meta = dict(cfg.as_dict(), metrics=article_metrics(h1), greedy=g1)
    path = save_model(a1, meta, h1, [], root=tmp_path)
    back = load_agent(path)
    assert greedy_test(make_env(cfg), back, cfg.seed) == g1


# ----------------------------------------------------------------------
# Notre DQN, étape 3 : CNN
# ----------------------------------------------------------------------
def test_cnn_network_shapes_and_requires_full_view():
    torch = pytest.importorskip("torch")
    from agents.dqn import CNNQNet

    net = CNNQNet(6 * 14 * 28 + 10, 3)
    assert net(torch.zeros(5, 6 * 14 * 28 + 10)).shape == (5, 3)
    with pytest.raises(ValueError):
        CNNQNet(115, 3)                  # vue de l'article : refusée


def test_dqn_cnn_train_save_load(tmp_path):
    pytest.importorskip("torch")
    from agents.training import train

    cfg = TrainConfig(algo="dqn", level="v3", episodes=6, seed=5,
                      eval_every=3, log_every=0, alpha=None, eps_min=0.05,
                      obs="full", cnn=True, grad_clip=10.0, keep_best=True,
                      device="cpu", variant="E3")
    a1, h1, _, g1, _ = train(cfg, log=None)
    meta = dict(cfg.as_dict(), metrics=article_metrics(h1), greedy=g1)
    path = save_model(a1, meta, h1, [], root=tmp_path)
    back = load_agent(path)
    assert back.cnn
    obs = make_env(cfg).reset()[0]
    assert np.allclose(back.q_values(obs), a1.q_values(obs), atol=1e-6)


def test_run_seed_returns_dqn_on_cpu_without_memory():
    """Graines en parallèle : le réseau doit revenir sur le processeur (un
    réseau resté sur la carte graphique arriverait vide, que des zéros)."""
    torch = pytest.importorskip("torch")
    from agents.training import run_seed

    cfg = TrainConfig(algo="dqn", level="v3", episodes=3, seed=6,
                      eval_every=0, log_every=0, alpha=None, eps_min=0.05,
                      obs="full", cnn=True, device="cpu").as_dict()
    _, agent, _, _, final, _ = run_seed(cfg)
    assert agent.device == torch.device("cpu") and agent.memory is None
    assert all(p.device.type == "cpu" for p in agent.net.parameters())
    assert any(p.abs().sum() > 0 for p in agent.net.parameters())
    assert greedy_test(make_env(TrainConfig(**cfg)), agent, 6) == final
