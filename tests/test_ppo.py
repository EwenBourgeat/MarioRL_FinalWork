"""PPO sur le vrai jeu NES (Stable-Baselines3)."""

import pickle

import numpy as np
import pytest

from agents.metrics import article_metrics, format_metrics, plot_curves
from agents.ppo import make_nes_env
from agents.registry import default_name, list_models, load_agent, save_model
from agents.training import TrainConfig, run_seed, train


def ppo_config(**kw):
    base = dict(algo="ppo", env="nes", obs="vector", actions="right_only",
                level="v3", steps=1024, n_envs=2, eval_steps=512,
                log_every=0, lr=3e-4, seed=42)
    base.update(kw)
    return TrainConfig(**base)


def test_nes_env_for_agents_has_project_info_keys():
    env = make_nes_env()
    obs, info = env.reset(seed=0)
    assert obs.shape == (62,) and env.action_space.n == 5
    assert info["win"] is False and info["t"] == 0 and "col" in info
    calls = []
    env.unwrapped.frame_hook = lambda: calls.append(1)
    obs, r, term, trunc, info = env.step(1)          # droite
    assert len(calls) == 4                           # 4 images NES par pas
    assert info["t"] == 1 and "bricks_broken" in info["stats"]


def test_ppo_trains_saves_and_reloads(tmp_path):
    pytest.importorskip("stable_baselines3")
    cfg = ppo_config(keep_best=True)
    agent, history, tests, final, seconds = train(cfg, log=None)
    n = len(history["win"])
    assert n > 0 and tests and tests[0]["train_steps"] >= 512
    # pas d'entraînement cumulés, pas d'epsilon pour PPO
    assert history["n_states"] == sorted(history["n_states"])
    assert set(history["epsilon"]) == {0.0}
    m = article_metrics(history)
    text = format_metrics(m, "v3", final, "ppo")
    assert "Pas d'entraînement" in text and "Epsilon" not in text
    plot_curves(history, tests, tmp_path / "curves.png", "PPO", epsilon=False)
    assert (tmp_path / "curves.png").stat().st_size > 0

    meta = dict(cfg.as_dict(), env="MarioNES-v0", episodes=n, metrics=m,
                greedy=final)
    path = save_model(agent, meta, history, tests, root=tmp_path)
    assert path.name == "ppo_nes_v3_s42_1024"
    assert (path / "ppo.zip").exists()
    [listed] = list_models(tmp_path)
    again = load_agent(listed)
    obs, _ = make_nes_env().reset(seed=0)
    for _ in range(3):
        assert again.best_action(tuple(obs)) == agent.best_action(obs)
        obs = obs + 0.1


def test_run_seed_returns_a_picklable_ppo_agent():
    pytest.importorskip("stable_baselines3")
    cfg_dict, agent, history, tests, final, _ = run_seed(
        ppo_config(eval_steps=0).as_dict())
    assert cfg_dict["episodes"] == len(history["win"])
    assert agent.model is None                # modèle sérialisé
    agent = pickle.loads(pickle.dumps(agent))
    obs, _ = make_nes_env().reset(seed=0)
    assert 0 <= agent.best_action(obs) < 5    # rechargé à la demande


def test_train_cli_defaults_for_ppo():
    import train as cli
    parser = cli.build_parser()
    args = parser.parse_args(["--algo", "ppo"])
    cli.resolve_defaults(parser, args)
    assert (args.env, args.obs, args.actions, args.lr) == (
        "nes", "vector", "right_only", 3e-4)
    args = parser.parse_args(["--algo", "sarsa"])
    cli.resolve_defaults(parser, args)
    assert (args.env, args.obs, args.lr) == ("grid", "paper", 1e-4)
    for bad in (["--algo", "dqn", "--env", "nes"],
                ["--algo", "ppo", "--env", "grid"],
                ["--algo", "qlearning", "--level", "full"]):
        args = parser.parse_args(bad)
        with pytest.raises(SystemExit):
            cli.resolve_defaults(parser, args)


def test_tabular_agent_runs_on_the_real_game():
    cfg = TrainConfig(algo="qlearning", env="nes", obs="paper",
                      actions="right_only", level="v3", episodes=3,
                      eval_every=0, log_every=0, max_steps=200)
    agent, history, tests, final, _ = train(cfg, log=None)
    assert len(history["win"]) == 3 and len(agent.q) > 0
    assert default_name("qlearning", "v3", 42, 3, nes=True) == (
        "qlearning_nes_v3_s42_3ep")
    assert np.isfinite(final["return"])
