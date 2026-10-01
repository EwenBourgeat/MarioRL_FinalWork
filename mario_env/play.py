"""Jouer au niveau 1-1 au clavier (ou à la manette) avec pygame.

    python play.py            # ou : python -m mario_env.play

Le jeu s'ouvre sur l'écran titre de Super Mario Bros. :
    VERSION NES              le vrai jeu (physique NES)
    VERSION SIMPLIFIEE V3    l'environnement discret de l'article (← → : V1/V2/V3)
    MODELES                  regarder jouer un agent entraîné (dossier models/)
    QUITTER
↑ / ↓ ou Tab (SELECT) pour déplacer le champignon, Entrée (START) pour valider.
Pendant qu'un modèle joue : → / ← pour accélérer / ralentir (x1 à x8).

En jeu : flèches (ou ZQSD / WASD) pour bouger, X / K / Espace = saut (A),
C / J / Z / Maj = courir / boule de feu (B), Entrée = pause,
Échap = retour à l'écran titre.  ↓ sur le 4e tuyau pour la salle bonus.
"""

import argparse
import os
import sys

import numpy as np

from . import constants as C
from .game import Game, GameConfig
from .renderer import MODELS_VISIBLE, Renderer, text

INTERMISSION_FRAMES = 150
GAMEOVER_FRAMES = 240
GRID_STEP_FRAMES = 8            # un pas de l'environnement simplifié = 8 images
GRID_END_FRAMES = 180
GRID_LEVELS = ("v1", "v2", "v3")
MENU_NES, MENU_GRID, MENU_MODELS, MENU_QUIT = range(4)
WATCH_SPEEDS = (1, 2, 4, 8)     # vitesses du menu MODELES (x1 = 7,5 pas/s)

# Manettes : SELECT / START selon les modèles (Xbox, génériques USB)
JOY_SELECT = (6, 8)
JOY_START = (7, 9)


def _buttons_from_keys(pygame, keys, joy):
    b = 0
    k = pygame
    if keys[k.K_RIGHT] or keys[k.K_d]:
        b |= C.BTN_RIGHT
    if keys[k.K_LEFT] or keys[k.K_a] or keys[k.K_q]:
        b |= C.BTN_LEFT
    if keys[k.K_DOWN] or keys[k.K_s]:
        b |= C.BTN_DOWN
    if keys[k.K_UP] or keys[k.K_w]:
        b |= C.BTN_UP
    if keys[k.K_x] or keys[k.K_k] or keys[k.K_SPACE]:
        b |= C.BTN_A
    if keys[k.K_c] or keys[k.K_j] or keys[k.K_LSHIFT] or keys[k.K_RSHIFT] \
            or keys[k.K_z]:
        b |= C.BTN_B
    if joy is not None:
        try:
            hx, hy = joy.get_hat(0) if joy.get_numhats() else (0, 0)
            ax = joy.get_axis(0) if joy.get_numaxes() else 0.0
            ay = joy.get_axis(1) if joy.get_numaxes() > 1 else 0.0
            if hx > 0 or ax > 0.5:
                b |= C.BTN_RIGHT
            if hx < 0 or ax < -0.5:
                b |= C.BTN_LEFT
            if hy < 0 or ay > 0.5:
                b |= C.BTN_DOWN
            if joy.get_numbuttons() > 0 and joy.get_button(0):
                b |= C.BTN_A
            if joy.get_numbuttons() > 2 and (joy.get_button(2)
                                             or joy.get_button(1)):
                b |= C.BTN_B
        except Exception:
            pass
    return b


class App:
    """Fenêtre unique : écran titre, version NES et version simplifiée."""

    def __init__(self, args, pygame, screen, joy=None, script=None):
        self.args = args
        self.pg = pygame
        self.screen = screen
        self.fullscreen = False
        self.joy = joy
        self.clock = pygame.time.Clock()
        self.surf = pygame.Surface((C.SCREEN_W, C.SCREEN_H))
        self.script = script or {}
        self.frames = 0
        self.closed = False
        self.top_score = 0
        self.grid_level = args.grid or "v3"
        # partie « vitrine » pour l'écran titre (score et pièces affichés)
        self.title_game = Game(GameConfig(enemies=False))
        self.title_renderer = Renderer(self.title_game)
        self.last_frame = None
        self.visited = []               # modes lancés (utile pour les tests)

    # ------------------------------------------------------------------
    # Boucle commune
    # ------------------------------------------------------------------
    def _tick(self):
        """Passe à l'image suivante ; False si la fenêtre doit se fermer."""
        if self.closed:
            return False
        self.frames += 1
        if self.args.max_frames and self.frames > self.args.max_frames:
            self.closed = True
            return False
        for key in self.script.get(self.frames, ()):
            self.pg.event.post(self.pg.event.Event(self.pg.KEYDOWN, key=key))
        return True

    def _actions(self):
        """Événements du tour, traduits en actions de menu."""
        pg = self.pg
        out = []
        for event in pg.event.get():
            if event.type == pg.QUIT:
                self.closed = True
                out.append("quit")
            elif event.type == pg.KEYDOWN:
                k = event.key
                if k in (pg.K_RETURN, pg.K_KP_ENTER):
                    out.append("start")
                elif k == pg.K_TAB:
                    out.append("select")
                elif k in (pg.K_UP, pg.K_w):
                    out.append("up")
                elif k in (pg.K_DOWN, pg.K_s):
                    out.append("down")
                elif k in (pg.K_LEFT, pg.K_a, pg.K_q):
                    out.append("left")
                elif k in (pg.K_RIGHT, pg.K_d):
                    out.append("right")
                elif k == pg.K_F11 or (k == pg.K_f and event.mod
                                       & (pg.KMOD_META | pg.KMOD_CTRL)):
                    self.toggle_fullscreen()
                elif k == pg.K_ESCAPE:
                    out.append("back")
                elif k == pg.K_p:
                    out.append("pause")
                elif k in (pg.K_x, pg.K_k, pg.K_SPACE):
                    out.append("jump")
            elif event.type == pg.JOYBUTTONDOWN:
                if event.button in JOY_START:
                    out.append("start")
                elif event.button in JOY_SELECT:
                    out.append("select")
                elif event.button == 0:
                    out.append("jump")
            elif event.type == pg.JOYHATMOTION:
                hx, hy = event.value
                if hy > 0:
                    out.append("up")
                elif hy < 0:
                    out.append("down")
                elif hx < 0:
                    out.append("left")
                elif hx > 0:
                    out.append("right")
        return out

    def toggle_fullscreen(self):
        """Bascule plein écran / fenêtre (F11 ou Cmd+F / Ctrl+F)."""
        pg = self.pg
        self.fullscreen = not self.fullscreen
        if self.fullscreen:
            self.screen = pg.display.set_mode((0, 0), pg.FULLSCREEN)
        else:
            s = max(1, self.args.scale)
            self.screen = pg.display.set_mode((C.SCREEN_W * s, C.SCREEN_H * s))

    def _present(self, frame, fps=None):
        pg = self.pg
        self.last_frame = frame
        pg.surfarray.blit_array(self.surf, frame.swapaxes(0, 1))
        sw, sh = self.screen.get_size()
        if (sw, sh) == self.surf.get_size():
            self.screen.blit(self.surf, (0, 0))
        else:
            # agrandissement en gardant les proportions de l'écran NES
            # (bandes noires sur les côtés en plein écran)
            k = min(sw / C.SCREEN_W, sh / C.SCREEN_H)
            w, h = int(C.SCREEN_W * k), int(C.SCREEN_H * k)
            if (w, h) == (sw, sh):
                pg.transform.scale(self.surf, (sw, sh), self.screen)
            else:
                self.screen.fill((0, 0, 0))
                self.screen.blit(pg.transform.scale(self.surf, (w, h)),
                                 ((sw - w) // 2, (sh - h) // 2))
        pg.display.flip()
        self.clock.tick(self.args.fps if fps is None else fps)

    def _remember(self, score, coins):
        self.top_score = max(self.top_score, score)
        self.title_game.score = score
        self.title_game.coins = coins

    # ------------------------------------------------------------------
    # Écran titre
    # ------------------------------------------------------------------
    def menu_labels(self):
        return ["VERSION NES",
                f"VERSION SIMPLIFIEE {self.grid_level.upper()}",
                "MODELES",
                "QUITTER"]

    def run_title(self):
        cursor = MENU_NES
        n = len(self.menu_labels())
        while self._tick():
            for a in self._actions():
                if a in ("down", "select"):
                    cursor = (cursor + 1) % n
                elif a == "up":
                    cursor = (cursor - 1) % n
                elif a in ("left", "right") and cursor == MENU_GRID:
                    i = GRID_LEVELS.index(self.grid_level)
                    i = (i + (1 if a == "right" else -1)) % len(GRID_LEVELS)
                    self.grid_level = GRID_LEVELS[i]
                elif a == "start":
                    if cursor == MENU_NES:
                        self.run_nes()
                    elif cursor == MENU_GRID:
                        self.run_grid(self.grid_level)
                    elif cursor == MENU_MODELS:
                        self.run_models()
                    else:
                        self.closed = True
                    break
                elif a == "back":
                    self.closed = True
                    break
            if self.closed:
                return
            frame = self.title_renderer.render_title(
                self.menu_labels(), cursor, self.top_score, fc=self.frames)
            self._present(frame)

    # ------------------------------------------------------------------
    # Version NES
    # ------------------------------------------------------------------
    def nes_config(self):
        a = self.args
        return GameConfig(
            segment_order=a.segments,
            timer_frames=C.GAME_TIMER_TICK if a.nes_timer else C.FPS,
            scroll_back=not a.nes_camera,
            lives=a.lives,
            enemies=not a.no_enemies,
            blocks=not a.no_blocks,
            powerups=not a.no_powerups,
            start_status={"small": 0, "big": 1, "fire": 2}[a.status],
        )

    def run_nes(self):
        pg = self.pg
        self.visited.append("nes")
        game = Game(self.nes_config())
        renderer = Renderer(game)
        phase = "intermission"
        phase_timer = INTERMISSION_FRAMES
        paused = False
        last_mode = game.mode
        frame = None
        while self._tick():
            actions = self._actions()
            if "back" in actions or self.closed:
                break
            if phase == "play" and ("start" in actions or "pause" in actions):
                paused = not paused
            keys = pg.key.get_pressed()
            buttons = _buttons_from_keys(pg, keys, self.joy)

            if phase == "intermission":
                frame = renderer.render_message(None, lives=game.lives)
                phase_timer -= 1
                if phase_timer <= 0:
                    phase = "play"
            elif phase == "gameover":
                frame = renderer.render_message("GAME OVER")
                phase_timer -= 1
                if phase_timer <= 0:
                    self.visited.append("gameover")
                    break                       # retour à l'écran titre
            elif not paused:
                game.step(buttons)
                frame = renderer.render()
                if last_mode == "dying" and game.mode == "play":
                    phase = "intermission"
                    phase_timer = INTERMISSION_FRAMES
                elif game.mode == "gameover":
                    phase = "gameover"
                    phase_timer = GAMEOVER_FRAMES
                elif game.finished:
                    game.restart_level()
                    phase = "intermission"
                    phase_timer = INTERMISSION_FRAMES
                last_mode = game.mode
            if frame is None:
                frame = renderer.render()
            shown = frame
            if paused and phase == "play":
                shown = frame.copy()
                text(shown, "PAUSE", 108, 112)
            self._present(shown)
        self._remember(game.score, game.coins)

    # ------------------------------------------------------------------
    # Version simplifiée (environnement de l'article)
    # ------------------------------------------------------------------
    def grid_frame(self, env, ret, message=None, ai=None):
        frame = np.empty((C.SCREEN_H, C.SCREEN_W, 3), dtype=np.uint8)
        frame[:] = C.NES_PALETTE[C.SKY_COLOR]
        cam = min(max(env.col - 7, 0), env.W - 16)
        frame[16:] = env.render_level(window=(cam, cam + 16))
        text(frame, "RETOUR", 24, 16)
        text(frame, f"{ret:.1f}", 24, 24)
        text(frame, "NIVEAU", 136, 16)
        text(frame, env.level.upper(), 152, 24)
        text(frame, "PAS", 208, 16)
        text(frame, f"{env.t:03d}", 208, 24)
        if ai:                                  # (nom du modèle, vitesse)
            label, speed = ai
            text(frame, label[:22], 24, 40)
            text(frame, f"x{speed}", 216, 40)
        if message:
            text(frame, message, 128 - 4 * len(message), 88)
        return frame

    def run_grid(self, level):
        pg = self.pg
        from .envs.grid_env import MarioGridEnv

        self.visited.append("grid_" + level)
        env = MarioGridEnv(level=level, segment_order=self.args.segments)
        env.reset()
        ret = 0.0
        phase = "intermission"
        phase_timer = INTERMISSION_FRAMES
        jump_pressed = False
        message = None
        step_timer = 0
        while self._tick():
            actions = self._actions()
            if "back" in actions or self.closed:
                break
            if "jump" in actions:
                jump_pressed = True
            if phase == "intermission":
                self.title_game.frame = self.frames
                frame = self.title_renderer.render_message(None, lives=1)
                phase_timer -= 1
                if phase_timer <= 0:
                    phase = "play"
                self._present(frame)
                continue
            if phase == "play":
                step_timer += 1
                if step_timer >= GRID_STEP_FRAMES:
                    step_timer = 0
                    keys = pg.key.get_pressed()
                    buttons = _buttons_from_keys(pg, keys, self.joy)
                    if jump_pressed or buttons & C.BTN_A:
                        action = 2
                    elif buttons & C.BTN_RIGHT:
                        action = 1
                    else:
                        action = 0
                    jump_pressed = False
                    _, r, term, trunc, info = env.step(action)
                    ret += r
                    if term or trunc:
                        phase = "end"
                        phase_timer = GRID_END_FRAMES
                        if info["win"]:
                            message = "THANK YOU MARIO!"
                        elif info["dead"]:
                            message = "GAME OVER"
                        else:
                            message = "TIME UP"
            else:
                phase_timer -= 1
                if phase_timer <= 0 or "start" in actions:
                    break
            self._present(self.grid_frame(env, ret, message))

    # ------------------------------------------------------------------
    # Menu MODELES : regarder jouer un agent entraîné
    # ------------------------------------------------------------------
    @staticmethod
    def load_models():
        try:
            from agents.registry import list_models
        except ImportError:             # dossier agents/ absent
            return []
        return list_models()

    @staticmethod
    def model_info(meta):
        """Résumé sous la liste (mesures de l'article + test glouton)."""
        lines = []
        m = meta.get("metrics")
        if m:
            lines.append(f"VICTOIRES {100 * m['win_rate']:.1f}% "
                         f"RETOUR {m['avg_return']:.0f}")
            to = [("-" if m.get(k) is None else m[k]) for k in ("to_50",
                                                               "to_80")]
            lines.append(f"50% EP {to[0]}  80% EP {to[1]}")
        g = meta.get("greedy")
        if g:
            res = "GAGNE" if g.get("win") else "PERDU"
            lines.append(f"TEST GLOUTON {res} {g.get('steps', 0)} PAS")
        return lines

    def _list_menu(self, title, labels, info_for, on_start):
        """Liste NES (curseur champignon) terminée par RETOUR.

        ``info_for(i)`` : lignes d'infos de la ligne i ; ``on_start(i)`` :
        action sur Entrée.  Revient à l'appelant sur RETOUR ou Échap.
        """
        labels = list(labels) + ["RETOUR"]
        n = len(labels)
        cursor = 0
        first = 0
        while self._tick():
            for a in self._actions():
                if a in ("down", "select"):
                    cursor = (cursor + 1) % n
                elif a == "up":
                    cursor = (cursor - 1) % n
                elif a == "start":
                    if cursor == n - 1:
                        return
                    on_start(cursor)
                    break
                elif a == "back":
                    return
            if self.closed:
                return
            # défilement : la ligne du curseur reste visible
            first = min(max(first, cursor - MODELS_VISIBLE + 1), cursor)
            info = info_for(cursor) if cursor < n - 1 else []
            frame = self.title_renderer.render_model_list(
                labels, cursor, info, first, fc=self.frames, title=title)
            self._present(frame)

    def run_models(self):
        """MODELES : d'abord l'algorithme, puis ses modèles entraînés."""
        self.visited.append("models")
        try:
            from agents.registry import ALGORITHMS
        except ImportError:
            ALGORITHMS = ()
        models = self.load_models()
        models.sort(key=lambda m: (m.get("level", ""), m.get("episodes", 0),
                                   m.get("seed", 0), m.get("name", "")))
        by_algo = {key: [m for m in models if m.get("algo") == key]
                   for key, _ in ALGORITHMS}

        def info_for(i):
            k = len(by_algo[ALGORITHMS[i][0]])
            if k == 0:
                return ["PAS ENCORE DE MODELE"]
            return [f"{k} MODELE{'S' if k > 1 else ''} ENTRAINE"
                    f"{'S' if k > 1 else ''}"]

        def on_start(i):
            key, name = ALGORITHMS[i]
            if by_algo[key]:
                self.run_model_list(name, by_algo[key])

        self._list_menu("MODELES", [name for _, name in ALGORITHMS],
                        info_for, on_start)

    def run_model_list(self, title, models):
        """Les modèles d'un algorithme ; Entrée pour le regarder jouer."""
        from agents.registry import short_label

        self.visited.append("models_" + title)
        self._list_menu(title, [short_label(m) for m in models],
                        lambda i: self.model_info(models[i]),
                        lambda i: self.run_watch(models[i]))

    def run_watch(self, meta):
        """Le modèle joue seul, sans exploration (comme le test glouton)."""
        from agents.registry import load_agent
        from .envs.common import state_key
        from .envs.grid_env import MarioGridEnv

        self.visited.append("watch_" + meta["name"])
        agent = load_agent(meta)
        policy = agent.greedy_policy(meta.get("seed", 0))
        env = MarioGridEnv(level=meta["level"],
                           max_steps=meta.get("max_steps", 1000),
                           segment_order=meta.get("segments"))
        obs, _ = env.reset()
        label = meta.get("label", meta["name"]).upper()
        ret = 0.0
        speed = 0
        phase = "intermission"
        phase_timer = INTERMISSION_FRAMES
        message = None
        step_timer = 0
        while self._tick():
            actions = self._actions()
            if "back" in actions or self.closed:
                break
            if "right" in actions:
                speed = min(speed + 1, len(WATCH_SPEEDS) - 1)
            if "left" in actions:
                speed = max(speed - 1, 0)
            if phase == "intermission":
                frame = self.title_renderer.render_message(None, lives=1)
                phase_timer -= 1
                if phase_timer <= 0 or "start" in actions:
                    phase = "play"
                self._present(frame)
                continue
            if phase == "play":
                step_timer += 1
                if step_timer >= GRID_STEP_FRAMES // WATCH_SPEEDS[speed]:
                    step_timer = 0
                    obs, r, term, trunc, info = env.step(
                        policy(state_key(obs)))
                    ret += r
                    if term or trunc:
                        phase = "end"
                        phase_timer = GRID_END_FRAMES
                        if info["win"]:
                            message = "THANK YOU MARIO!"
                        elif info["dead"]:
                            message = "GAME OVER"
                        else:
                            message = "TIME UP"
                        self.visited.append(message)
            else:
                phase_timer -= 1
                if phase_timer <= 0 or "start" in actions:
                    break
            self._present(self.grid_frame(
                env, ret, message, ai=(label, WATCH_SPEEDS[speed])))


def build_parser():
    parser = argparse.ArgumentParser(description="Super Mario Bros. 1-1")
    parser.add_argument("--fullscreen", action="store_true",
                        help="plein écran (F11 ou Cmd+F pour basculer)")
    parser.add_argument("--scale", type=int, default=3,
                        help="facteur d'agrandissement de la fenêtre")
    parser.add_argument("--lives", type=int, default=3)
    parser.add_argument("--status", choices=["small", "big", "fire"],
                        default="small", help="état de départ de Mario")
    parser.add_argument("--no-enemies", action="store_true")
    parser.add_argument("--no-blocks", action="store_true")
    parser.add_argument("--no-powerups", action="store_true")
    parser.add_argument("--fps", type=int, default=C.FPS)
    parser.add_argument("--nes-timer", action="store_true",
                        help="chrono du jeu NES (1 unité = 24 images ≈ 0,4 s) "
                             "au lieu de vraies secondes")
    parser.add_argument("--nes-camera", action="store_true",
                        help="caméra du jeu NES (ne revient jamais en arrière)")
    parser.add_argument("--no-menu", action="store_true",
                        help="lancer directement la version NES")
    parser.add_argument("--grid", choices=GRID_LEVELS, default=None,
                        help="lancer directement la version simplifiée")
    parser.add_argument("--segments", default=None,
                        help="ordre des segments A-F, ex. FEDCBA")
    parser.add_argument("--max-frames", type=int, default=0,
                        help=argparse.SUPPRESS)
    return parser


def main(argv=None, script=None):
    args = build_parser().parse_args(argv)

    os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
    import pygame

    pygame.display.init()
    pygame.joystick.init()
    pygame.display.set_caption("Super Mario Bros.")
    scale = max(1, args.scale)
    screen = pygame.display.set_mode((C.SCREEN_W * scale, C.SCREEN_H * scale))
    joy = pygame.joystick.Joystick(0) if pygame.joystick.get_count() else None

    app = App(args, pygame, screen, joy, script)
    if args.fullscreen:
        app.toggle_fullscreen()
    if args.grid:
        app.run_grid(args.grid)
    elif args.no_menu:
        app.run_nes()
    if not app.closed:
        app.run_title()
    pygame.quit()
    return 0


if __name__ == "__main__":
    sys.exit(main())
