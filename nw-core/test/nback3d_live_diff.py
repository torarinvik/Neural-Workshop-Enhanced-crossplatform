#!/usr/bin/env python3
"""Differential test for the port-scoped 3D N-Back live controller.

The original application is the oracle for the generated position/color
stream and for the position-only scoring rule.  The companion Node runner
drives the public versioned WASM API with the same action schedule and
returns the controller's visible stimulus, feedback verdict, and counters.

This deliberately covers only mode 10 with ``GRID_3D`` enabled.  The other
N-Back modes remain outside the port scope.
"""

from __future__ import annotations

import json
import random
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
ORIGINAL = ROOT / "original-neural-workshop-enhanced"
sys.path.insert(0, str(ORIGINAL))

from neural_workshop import gamemode, runtime, session, state  # noqa: E402
from neural_workshop.config import DotDict  # noqa: E402
from neural_workshop.stats import _EXTRA_STREAMS, _TRACKED_STIMULI  # noqa: E402


runtime.DEBUG = False
session._queue_audio = lambda: None
session._spawn_visuals = lambda multi, variable: None

CFG = dict(
    GAME_MODE=10,
    BACK_DEFAULT=2,
    TICKS_DEFAULT=30,
    BONUS_TICKS_CRAB=0,
    BONUS_TICKS_MULTI_2=5,
    BONUS_TICKS_MULTI_3=10,
    BONUS_TICKS_MULTI_4=15,
    NUM_TRIALS=4,
    NUM_TRIALS_FACTOR=0,
    NUM_TRIALS_EXPONENT=2,
    MANUAL=True,
    HIDE_TEXT=False,
    SKIP_TITLE_SCREEN=True,
    BLACK_BACKGROUND=False,
    CHANCE_OF_GUARANTEED_MATCH=0.125,
    CHANCE_OF_INTERFERENCE=0.125,
    VARIABLE_NBACK=0,
    JAEGGI_MODE=0,
    MULTI_MODE="color",
    VISUAL_COLORS=[1, 3, 8, 6],
    ARITHMETIC_USE_ADDITION=True,
    ARITHMETIC_USE_SUBTRACTION=True,
    ARITHMETIC_USE_MULTIPLICATION=True,
    ARITHMETIC_USE_DIVISION=True,
    ARITHMETIC_USE_NEGATIVES=False,
    ARITHMETIC_MAX_NUMBER=12,
    ARITHMETIC_ACCEPTABLE_DECIMALS=[
        "0.1", "0.2", "0.3", "0.4", "0.5", "0.6", "0.7", "0.8",
        "0.9", "0.125", "0.25", "0.375", "0.625", "0.75", "0.875",
        "0.15", "0.35", "0.45", "0.55", "0.65", "0.85", "0.95",
    ],
    GRID_SIZE=3,
    GRID_SIZE_MIN=2,
    GRID_SIZE_MAX=32,
    GRID_INCLUDE_CENTER=False,
    GRID_3D=True,
    GRID_3D_CUBES=1,
    ACTIVE_POSITION_CELLS=0,
    POSITION_CELL_COUNT=0,
)


def fresh_session() -> dict[str, list[Any]]:
    out: dict[str, list[Any]] = {}
    for name in _TRACKED_STIMULI:
        out[name] = []
        out[f"{name}_input"] = []
        out[f"{name}_rt"] = []
    for name in _EXTRA_STREAMS:
        out[name] = []
    return out


def source_case(seed: int, nback: int, cubes: int, total: int,
                presses: list[bool]) -> dict[str, Any]:
    cfg = DotDict(CFG)
    cfg.GRID_3D_CUBES = cubes
    state.cfg = cfg
    game = gamemode.Mode()
    game.back = nback
    game.trial_number = 0
    game.num_trials_total = total
    state.mode = game
    state.stats = type("Stats", (), {})()
    state.stats.session = fresh_session()

    random.seed(seed)
    trials: list[dict[str, int | bool]] = []
    for index in range(total):
        if game.trial_number > 0:
            for key, value in game.current_stim.items():
                stream = "numbers" if key == "number" else key
                state.stats.session[stream].append(value)
                if key == "vis":
                    state.stats.session["image"].append(value)
        game.trial_number += 1
        session.generate_stimulus()
        position = int(game.current_stim["position1"])
        color = int(game.current_stim["color"])
        match = index >= nback and position == int(
            state.stats.session["position1"][index - nback]
        )
        pressed = bool(presses[index])
        if match and pressed:
            verdict = "hit"
        elif match:
            verdict = "miss"
        elif pressed:
            verdict = "false_alarm"
        else:
            verdict = "correct_rejection"
        trials.append({
            "position": position,
            "color": color,
            "match": match,
            "pressed": pressed,
            "verdict": verdict,
        })

    counts = {
        "hits": sum(row["verdict"] == "hit" for row in trials),
        "misses": sum(row["verdict"] == "miss" for row in trials),
        "false_alarms": sum(row["verdict"] == "false_alarm" for row in trials),
        "correct_rejections": sum(
            row["verdict"] == "correct_rejection" for row in trials
        ),
    }
    # The source scorer exposes right/wrong totals rather than the four-way
    # UI counters.  Keep both forms in the oracle so the test checks them.
    counts["rights"] = counts["hits"]
    counts["wrongs"] = counts["misses"] + counts["false_alarms"]
    return {
        "seed": seed,
        "nback": nback,
        "cubes": cubes,
        "total": total,
        "presses": presses,
        "trials": trials,
        "counts": counts,
    }


def main() -> int:
    cases = [
        source_case(1, 1, 1, 8, [True, False, True, False, True, False, True, False]),
        source_case(17, 2, 1, 8, [True, True, False, False, True, False, False, True]),
        source_case(12345, 2, 2, 8, [False, True, True, False, True, False, True, False]),
        source_case(7, 3, 3, 8, [True, False, False, True, False, True, True, False]),
        source_case(99, 2, 6, 8, [False, False, True, True, False, True, False, True]),
    ]
    runner = ROOT / "nw-core/test/nback3d_live_runner.mjs"
    completed = subprocess.run(
        ["node", str(runner)],
        input=json.dumps(cases),
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        print(completed.stdout, end="")
        print(completed.stderr, end="", file=sys.stderr)
        return completed.returncode
    try:
        got = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        print(f"FAIL: Node runner did not return JSON: {exc}", file=sys.stderr)
        print(completed.stdout, file=sys.stderr)
        return 1
    if got != cases:
        for index, (want, actual) in enumerate(zip(cases, got)):
            if want != actual:
                print(f"FAIL: first mismatch at case {index}")
                print(f"  source: {json.dumps(want, sort_keys=True)}")
                print(f"  wasm:   {json.dumps(actual, sort_keys=True)}")
                return 1
        print(f"FAIL: case count {len(got)} vs {len(cases)}")
        return 1
    print(f"PASS: {len(cases)} live 3D N-Back cases identical")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
