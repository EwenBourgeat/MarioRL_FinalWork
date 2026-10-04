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


def test_ppo_logs_every_n_steps():
    pytest.importorskip("stable_baselines3")
    logs = []
    train(ppo_config(log_steps=256, eval_steps=0), log=logs.append)
    assert len(logs) == 4                     # 1024 pas / 256
    assert " 256/1024 " in logs[0] and "pas/s" in logs[0]


# ---------------------------------------------------------------------------
# Route A : tuyau, salle bonus, pièces, champignon
# ---------------------------------------------------------------------------
def _route_a_env():
    from mario_env.envs.nes_env import MarioNESEnv
    return MarioNESEnv(level="full", obs_type="vector_plus",
                       actions="right_down", reward="route_a",
                       max_episode_steps=3000)


def test_route_a_buttons_view_and_pipe_reward():
    env = _route_a_env()
    obs, _ = env.reset(seed=0, options={"start_col": 57})
    assert env.action_space.n == 6 and obs.shape == (91,)
    env.game.p.x = 918                  # centré sur le tuyau de la colonne 57
    o = env._obs()
    assert abs(o[-6]) < 0.1 and o[-5] == 0   # entrée ~ 0, pas de sortie
    assert list(o[-4:]) == [0, 0, 0, 0]      # aucun bouton appuyé
    total = 0.0
    for a in [0, 5, 5, 5] + [0] * 20:   # bas : on entre dans le tuyau
        obs, r, term, trunc, info = env.step(a)
        total += r
    assert info["area"] == "bonus" and info["stats"]["bonus_room"] == 1
    assert total > 190                  # +200 pour l'entrée
    assert list(obs[-4:]) == [0, 0, 0, 0]    # dernier bouton : rien
    coins = obs[66:81].reshape(5, 3)
    assert coins[:, 2].sum() == 5       # 5 pièces visibles dans la salle
    assert obs[-6] == 0 and obs[-5] > 1  # dans la salle : la sortie, à droite
    obs, _, _, _, _ = env.step(4)       # droite + saut + course
    assert list(obs[-4:]) == [1, 1, 1, 0]
    k = 0
    while info["area"] == "bonus" and k < 800:
        obs, r, term, trunc, info = env.step(2 if k % 10 < 7 else 1)
        total += r
        k += 1
    exit_reward = 0.0
    for _ in range(40):                 # sortie par le tuyau de la colonne 163
        obs, r, term, trunc, info = env.step(0)
        exit_reward += r
    assert info["x"] // 16 == 163 and info["stats"]["coins"] > 5
    # l'avancée sautée par le tuyau est comptée (position max) : ~ +53
    assert exit_reward > 40
    assert total + exit_reward > 200 + 10 * info["stats"]["coins"]


def test_route_a_metrics_and_cli():
    pytest.importorskip("stable_baselines3")
    import train as cli
    from agents.metrics import format_summary
    cfg = ppo_config(level="full", obs="vector_plus", actions="right_down",
                     reward="route_a", eval_steps=0)
    agent, history, tests, final, _ = train(cfg, log=None)
    assert {"coins", "bonus", "powerups"} <= set(history)
    m = article_metrics(history)
    assert {"coins", "bonus_rate", "powerups"} <= set(m)
    assert "Passages par la salle bonus" in format_metrics(m, "full", final,
                                                          "ppo")
    assert "Salle bonus" in format_summary([m, m], "full")
    assert "salle bonus" in format_metrics(m, "full", final, "ppo")
    parser = cli.build_parser()
    args = parser.parse_args(["--algo", "ppo", "--level", "full", "--obs",
                              "vector_plus", "--actions", "right_down",
                              "--reward", "route_a", "--ent-coef", "0.01"])
    cli.resolve_defaults(parser, args)
    assert args.env == "nes" and args.ent_coef == 0.01
    for bad in (["--algo", "qlearning", "--reward", "route_a"],
                ["--algo", "sarsa", "--actions", "right_down"]):
        with pytest.raises(SystemExit):
            cli.resolve_defaults(parser, parser.parse_args(bad))


def test_full_a_flower_block_and_route_a2_reward():
    from mario_env.envs.nes_env import MarioNESEnv
    import mario_env.constants as C
    full = MarioNESEnv(level="full").game.grid
    assert full[9, 34] == C.EMPTY and full[9, 36] == C.EMPTY
    # bloc 34 : normal (champignon / fleur) ; bloc 36 : bloc de fleur
    for col, status, kind, final in ((34, 0, "mushroom", "tall"),
                                     (34, 1, "flower", "fireball"),
                                     (36, 1, "flower", "fireball")):
        env = MarioNESEnv(level="full_a", obs_type="vector_plus",
                          actions="right_down", reward="route_a2")
        env.reset(seed=0, options={"start_col": col - 1})
        g = env.game
        assert g.grid[9, col] == C.QBLOCK_POWERUP    # le bloc ajouté
        g.p.status = status
        hit = 0.0
        for a in [2] * 3 + [0] * 17 + [2] * 4 + [0] * 6:
            obs, r, term, trunc, info = env.step(a)
            hit += r
        assert info["stats"]["powerup_blocks"] == 1 and hit > 15   # +25
        [item] = [e for e in g.enemies if e.is_item]
        assert item.kind == kind
        g.p.x, g.p.y = item.x, item.y - 16           # Mario sur l'objet
        got = sum(env.step(0)[1] for _ in range(5))
        assert info["stats"][kind + "s"] == 0
        assert env.game.stats[kind + "s"] == 1 and got > 140   # +150
        assert env.game.info()["status"] == final


def test_flower_block_does_nothing_for_small_mario():
    from mario_env.envs.nes_env import MarioNESEnv
    import mario_env.constants as C
    env = MarioNESEnv(level="full_a", obs_type="vector_plus",
                      actions="right_down", reward="route_a2")
    env.reset(seed=0, options={"start_col": 35})
    g = env.game                                 # Mario petit
    total = 0.0
    for a in [2] * 3 + [0] * 17 + [2] * 4 + [0] * 6:
        total += env.step(a)[1]
    assert g.stats["blocks_bumped"] >= 1         # il a bien cogné le bloc
    assert g.stats["powerup_blocks"] == 0 and total < 15   # pas de +25
    assert g.grid[9, 36] == C.QBLOCK_POWERUP     # toujours disponible
    assert not [e for e in g.enemies if e.is_item]


def test_varied_start_only_in_training():
    from agents.ppo import VariedStart
    env = VariedStart(make_nes_env(level="full_a", obs="vector_plus",
                                   actions="right_down", reward="route_a2"),
                      18, 0.5, seed=0)
    cols = [env.reset(seed=i)[1]["col"] for i in range(40)]
    assert set(cols) == {cols[0], 18} or set(cols) >= {18}
    assert 8 <= cols.count(18) <= 32           # environ la moitié
    big = VariedStart(make_nes_env(level="full_a", obs="vector_plus",
                                   actions="right_down", reward="route_a2"),
                      35, 1.0, seed=0, big=True)
    _, info = big.reset(seed=0)
    assert info["col"] == 35 and info["status"] == "tall"
    pytest.importorskip("stable_baselines3")
    cfg = ppo_config(level="full_a", obs="vector_plus", actions="right_down",
                     reward="route_a2", start_col=18, start_prob=0.5,
                     eval_steps=512)
    agent, history, tests, final, _ = train(cfg, log=None)
    assert tests and final["steps"] > 0        # tests depuis le vrai début


def test_route_a2_guides_mario_towards_the_item():
    from mario_env.envs.nes_env import MarioNESEnv
    env = MarioNESEnv(level="full_a", obs_type="vector_plus",
                      actions="right_down", reward="route_a2")
    env.reset(seed=0, options={"start_col": 35})
    g = env.game
    g.p.status = 1
    for a in [2] * 3 + [0] * 17 + [2] * 4 + [0] * 6:   # fleur du bloc 36
        obs, r, term, trunc, info = env.step(a)
    assert info["item_dist"] is not None
    d0 = info["item_dist"]
    obs, r, term, trunc, info = env.step(0)      # on ne bouge pas
    assert abs(info["item_dist"] - d0) < 0.5


def test_flower_of_block_36_can_be_taken_without_going_left():
    # pas de bouton « gauche » : la fleur (immobile, posée sur le bloc) doit
    # pouvoir être prise en cognant le bloc puis en sautant vers la droite
    from mario_env.envs.nes_env import MarioNESEnv
    env = MarioNESEnv(level="full_a", obs_type="vector_plus",
                      actions="right_down", reward="route_a2")
    env.reset(seed=0, options={"start_col": 35})
    env.game.p.status = 1                        # Mario grand
    for a in [1, 0, 4, 2, 2, 3, 3, 4, 0, 0, 0, 0, 2, 4, 0]:
        env.step(a)
    assert env.game.stats["flowers"] == 1
    assert env.game.info()["status"] == "fireball"


def test_stuck_rule_ends_the_game_like_a_death():
    from mario_env.envs.common import RewardConfig
    from mario_env.envs.nes_env import MarioNESEnv
    assert RewardConfig.preset("route_a2").stuck_steps == 150
    env = MarioNESEnv(level="full_a", obs_type="vector_plus",
                      actions="right_down_left",
                      reward=RewardConfig(stuck_steps=20))
    assert env.action_space.n == 8
    env.reset(seed=0)
    for k in range(5):                           # il avance : rien à signaler
        _, _, term, _, info = env.step(1)
    assert info["idle_steps"] == 0 and not term
    for k in range(25):                          # il ne fait plus rien
        _, r, term, trunc, info = env.step(0)
        if term:
            break
    assert term and info["stuck"] and info["idle_steps"] == 20
    assert r < -40                               # pénalité de mort (-50)
