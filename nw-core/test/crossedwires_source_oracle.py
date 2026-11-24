#!/usr/bin/env python3
"""Emit a deterministic replay from the original Crossed Wires UI and Env."""
from __future__ import annotations

import importlib.util
import json
import os
import random
import sys
import types
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
ORIGINAL = Path(os.environ.get("NW_ORIGINAL_SOURCE_ROOT", "")) if os.environ.get(
    "NW_ORIGINAL_SOURCE_ROOT") else None
if ORIGINAL is None:
    candidates = (
        ROOT.parent / "original-neural-workshop-enhanced",
        ROOT.parents[2] / "Python Projects" / "neural-workshop-enhanced",
    )
    ORIGINAL = next((candidate for candidate in candidates if candidate.is_dir()), None)
if ORIGINAL is None:
    raise SystemExit("set NW_ORIGINAL_SOURCE_ROOT to the original source checkout")

# The replay calls only the original controller and kernel. Stub window chrome
# and optional UI services so it stays deterministic and requires no display.
neural_workshop = types.ModuleType("neural_workshop")
neural_workshop.__path__ = [str(ORIGINAL / "neural_workshop")]
sys.modules[neural_workshop.__name__] = neural_workshop

display = types.ModuleType("neural_workshop.display")
for name in ("register_overlay", "unregister_overlay", "ensure_laid_out"):
    setattr(display, name, lambda *_args, **_kwargs: None)
sys.modules[display.__name__] = display
neural_workshop.display = display

state = types.ModuleType("neural_workshop.state")
state.cfg = SimpleNamespace(BLACK_BACKGROUND=False)
state.window = SimpleNamespace(width=912, height=684)
sys.modules[state.__name__] = state
neural_workshop.state = state

constants = types.ModuleType("neural_workshop.constants")
constants.FONTLIST = None
sys.modules[constants.__name__] = constants

geometry = types.ModuleType("neural_workshop.geometry")
geometry.calc_fontsize = lambda value: value
geometry.from_bottom_edge = lambda value: value
geometry.from_top_edge = lambda value: value
geometry.width_center = lambda: 456
sys.modules[geometry.__name__] = geometry

ui_package = types.ModuleType("neural_workshop.ui")
ui_package.__path__ = [str(ORIGINAL / "neural_workshop" / "ui")]
sys.modules[ui_package.__name__] = ui_package
neural_workshop.ui = ui_package
cursor = types.ModuleType("neural_workshop.ui.cursor")
cursor.acquire = cursor.release = lambda: None
sys.modules[cursor.__name__] = cursor
taskoptions = types.ModuleType("neural_workshop.ui.taskoptions")
taskoptions.CROSSED_WIRES = object()
taskoptions.settings = lambda _spec: {
    "WIRES_LEVEL": 4, "WIRES_ROUNDS": 3,
    "WIRES_ADAPTIVE": True, "WIRES_GRID": True,
}
taskoptions.open_task_options = lambda *_args, **_kwargs: None
sys.modules[taskoptions.__name__] = taskoptions
# The controller replay bypasses construction and redraw, so the
# decoration module does not need to import the OpenGL-backed Group class.
polish = types.ModuleType("neural_workshop.ui.polish")
sys.modules[polish.__name__] = polish
ui_package.polish = polish
ui_package.cursor = cursor
ui_package.taskoptions = taskoptions

class FakeVerdict:
    shown = None

    def clear(self):
        self.shown = None

    def show(self, good, message):
        self.shown = (good, message)


verdict = types.ModuleType("neural_workshop.ui.verdict")
verdict.VerdictLabel = FakeVerdict
sys.modules[verdict.__name__] = verdict
i18n = types.ModuleType("neural_workshop.i18n")
i18n._ = lambda value: value
sys.modules[i18n.__name__] = i18n

pyglet = types.ModuleType("pyglet")
pyglet.__path__ = []
window = types.ModuleType("pyglet.window")
key = SimpleNamespace(
    SPACE=1, ESCAPE=2, F11=3, O=4,
    UP=10, RIGHT=11, DOWN=12, LEFT=13,
    W=14, D=15, S=16, A=17, E=18, C=19, X=20, Z=21, Q=22,
    NUM_1=31, NUM_2=32, NUM_3=33, NUM_4=34, NUM_5=35,
    NUM_6=36, NUM_7=37, NUM_8=38, NUM_9=39,
)
window.key = key
pyglet.window = window
pyglet.event = SimpleNamespace(EVENT_HANDLED=1)
sys.modules["pyglet"] = pyglet
sys.modules["pyglet.window"] = window

def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


kernel = load_module("neural_workshop.crossedwires",
                     ORIGINAL / "neural_workshop" / "crossedwires.py")
crossed_ui = load_module("neural_workshop.ui.crossedwires",
                         ORIGINAL / "neural_workshop" / "ui" / "crossedwires.py")

nwenv = types.ModuleType("nwenv")
nwenv.__path__ = [str(ORIGINAL / "nwenv")]
sys.modules["nwenv"] = nwenv
taskenv = types.ModuleType("nwenv.taskenv")


class TaskEnv:
    @classmethod
    def verifier(cls):
        return lambda *_args, **_kwargs: None

    def drive(self, task, port):
        getattr(task, self.action)(port)


taskenv.TaskEnv = TaskEnv
sys.modules[taskenv.__name__] = taskenv
source_env = load_module("nwenv.crossedwires", ORIGINAL / "nwenv" / "crossedwires.py")

SEED, LEVEL, TRIALS = 17, 4, 3


def make_ui(seed=SEED, level=LEVEL, trials=TRIALS):
    ui = crossed_ui.CrossedWires.__new__(crossed_ui.CrossedWires)
    ui.rng = random.Random(seed)
    ui.start_rung = ui.rung = level
    ui.total_trials = trials
    ui.adaptive = True
    ui.show_grid = True
    ui.trial = 0
    ui.results = []
    ui.bench = None
    ui.phase = "ready"
    ui.message = "Press Space to start"
    ui.verdict_shown = None
    ui.verdict = FakeVerdict()
    ui._redraw = lambda: None
    ui.now_ms = 1000
    ui.clock = lambda: ui.now_ms / 1000.0
    return ui


PHASE = {"ready": 0, "playing": 1, "scored": 2, "done": 3}


def snapshot(ui):
    bench = ui.bench
    score = ui.score()
    # The source advances ui.rung as soon as a round settles, while the board
    # and its active key family remain the just-scored bout until Space.
    grade = bench.bout.grade if bench is not None else None
    goals = bench.bout.goals if bench is not None else ()
    verdict = -1 if ui.verdict_shown is None else int(bool(ui.verdict_shown[0]))
    return [
        PHASE[ui.phase], ui.rung, ui.trial, ui.total_trials,
        grade.keys if grade is not None else 0,
        grade.across if grade is not None else 0,
        grade.down if grade is not None else 0,
        bench.at[0] if bench is not None else 0,
        bench.at[1] if bench is not None else 0,
        bench.goal()[0] if bench is not None and goals else 0,
        bench.goal()[1] if bench is not None and goals else 0,
        bench.goal_at if bench is not None else 0,
        len(goals),
        bench.presses if bench is not None else 0,
        bench.left() if bench is not None else 0,
        bench.bout.budget if bench is not None else 0,
        bench.reached if bench is not None else 0,
        bench.wasted if bench is not None else 0,
        verdict, sum(hit == asked for _rung, hit, asked in ui.results),
        int(ui.adaptive), int(ui.show_grid),
        sum(hit for _rung, hit, _asked in ui.results),
        sum(asked for _rung, _hit, asked in ui.results),
        score["accuracy"], score["best_rung"], score["perfect"],
    ]


def oracle_port(bench):
    live = bench.wiring_now()
    for _cost, wanted in kernel._ranked(bench):
        for keyed, way in enumerate(live):
            if way == wanted:
                return keyed
    return 0


def run(seed=SEED, level=LEVEL, trials=TRIALS, policy="oracle"):
    ui = make_ui(seed, level, trials)
    env_ui = make_ui(seed, level, trials)
    env = source_env.CrossedWiresEnv.__new__(source_env.CrossedWiresEnv)
    env.action = "press"
    env.ports = 8
    env_ui.on_key_press(key.SPACE, 0)
    assert env_ui.phase == "playing"
    ui.on_key_press(key.SPACE, 0)
    assert snapshot(env_ui) == snapshot(ui), "source UI seeded deals diverged"
    trace = [{"action": "start", "value": 0, "now": 1000,
              "result": 1, "state": snapshot(ui), "message": ui.message, "verdict": ui.verdict_shown}]
    sequence = 0

    policy_rng = random.Random(seed * 71 + level)
    for _round in range(trials):
        while ui.phase == "playing":
            keyed = oracle_port(ui.bench) if policy == "oracle" else policy_rng.randrange(ui.grade().keys)
            symbols = (crossed_ui.EIGHT_KEYS if ui.grade().keys == 8
                       else crossed_ui.FOUR_KEYS)
            ui.now_ms += 1
            env_ui.now_ms = ui.now_ms
            ui.on_key_press(symbols[keyed][0], 0)
            source_env.CrossedWiresEnv.drive(env, env_ui, keyed)
            if ui.phase == "scored":
                # The contract is 800 ms. Round the fixture clock boundary to
                # its millisecond resolution so binary float noise cannot
                # turn an exact boundary into a one millisecond delay.
                ui.until = round(ui.until, 3)
                env_ui.until = round(env_ui.until, 3)
            expected = snapshot(ui)
            assert snapshot(env_ui) == expected, "UI key and Env port routes diverged"
            trace.append({"action": "press", "value": keyed,
                          "now": ui.now_ms, "result": 1, "state": expected,
                          "message": ui.message, "verdict": ui.verdict_shown})

        deadline_ms = int(round(ui.until * 1000))
        ui.now_ms = deadline_ms - 1
        ui.on_key_press(key.SPACE, 0)
        env_ui.now_ms = ui.now_ms
        env_ui.on_key_press(key.SPACE, 0)
        expected = snapshot(ui)
        assert snapshot(env_ui) == expected
        trace.append({"action": "start", "value": 0,
                      "now": ui.now_ms, "result": 2, "state": expected,
                      "message": ui.message, "verdict": ui.verdict_shown})

        ui.now_ms = deadline_ms
        ui.on_key_press(key.SPACE, 0)
        env_ui.now_ms = ui.now_ms
        env_ui.on_key_press(key.SPACE, 0)
        expected = snapshot(ui)
        assert snapshot(env_ui) == expected
        trace.append({"action": "start", "value": 0,
                      "now": ui.now_ms, "result": 1, "state": expected,
                      "message": ui.message, "verdict": ui.verdict_shown})
        sequence += 1

    return {"seed": seed, "level": level, "trials": trials, "policy": policy,
            "trace": trace, "rounds": ui.results, "score": ui.score(),
            "message": ui.message}


if __name__ == "__main__":
    print(json.dumps({"replays": [
        run(),
        run(seed=100, level=2, trials=1, policy="random"),
        run(seed=0, level=4, trials=1, policy="random"),
    ]}))
