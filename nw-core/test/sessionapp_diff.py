#!/usr/bin/env python3
"""Differential harness for the port's 3D-only N-Back preview."""
import random
import subprocess
import sys
import types

APP = ("/Users/torarinvikbjarko/Documents/Coding Projects/Python Projects/"
       "neural-workshop-enhanced")
sys.path.insert(0, APP)

from bwaccel import fallback  # noqa: E402
from neural_workshop import gamemode, runtime, session, state  # noqa: E402
from neural_workshop.config import DotDict  # noqa: E402
from neural_workshop.stats import _EXTRA_STREAMS, _TRACKED_STIMULI  # noqa: E402

runtime.DEBUG = False
session._queue_audio = lambda: None
session._spawn_visuals = lambda multi, variable: None

FIELDS = list(gamemode.STIMULUS_FIELDS)
OP = {'none': 0, 'add': 1, 'subtract': 2, 'multiply': 3, 'divide': 4}

CFG = dict(
    GAME_MODE=2, BACK_DEFAULT=2, TICKS_DEFAULT=10, BONUS_TICKS_CRAB=0,
    BONUS_TICKS_MULTI_2=5, BONUS_TICKS_MULTI_3=10, BONUS_TICKS_MULTI_4=15,
    NUM_TRIALS=20, NUM_TRIALS_FACTOR=1, NUM_TRIALS_EXPONENT=2,
    MANUAL=True, HIDE_TEXT=False, SKIP_TITLE_SCREEN=True,
    BLACK_BACKGROUND=False, CHANCE_OF_GUARANTEED_MATCH=0.125,
    CHANCE_OF_INTERFERENCE=0.125, VARIABLE_NBACK=0, JAEGGI_MODE=0,
    MULTI_MODE='color', VISUAL_COLORS=[1, 3, 8, 6],
    ARITHMETIC_USE_ADDITION=True, ARITHMETIC_USE_SUBTRACTION=True,
    ARITHMETIC_USE_MULTIPLICATION=True, ARITHMETIC_USE_DIVISION=True,
    ARITHMETIC_USE_NEGATIVES=False, ARITHMETIC_MAX_NUMBER=12,
    ARITHMETIC_ACCEPTABLE_DECIMALS=[
        '0.1', '0.2', '0.3', '0.4', '0.5', '0.6', '0.7', '0.8', '0.9',
        '0.125', '0.25', '0.375', '0.625', '0.75', '0.875',
        '0.15', '0.35', '0.45', '0.55', '0.65', '0.85', '0.95'],
    GRID_SIZE=3, GRID_SIZE_MIN=2, GRID_SIZE_MAX=32,
    GRID_INCLUDE_CENTER=False, GRID_3D=False, GRID_3D_CUBES=1,
    ACTIVE_POSITION_CELLS=0, POSITION_CELL_COUNT=0)

BACKS = [1, 2, 3, 5]
SEEDS = [1, 7, 12345]
TRIALS = [1, 2, 5, 11, 18]


def fresh_session():
    out = {}
    for name in _TRACKED_STIMULI:
        out[name] = []
        out[f'{name}_input'] = []
        out[f'{name}_rt'] = []
    for name in _EXTRA_STREAMS:
        out[name] = []
    return out


def one(case, seed, trial, mode, back, grid_3d=False, cubes=1,
        reported_mode=None):
    cfg = DotDict(CFG)
    cfg.GAME_MODE = mode
    cfg.GRID_3D = grid_3d
    cfg.GRID_3D_CUBES = cubes
    state.cfg = cfg
    game = gamemode.Mode()
    game.back = back
    game.trial_number = 0
    game.num_trials_total = trial
    state.mode = game
    state.stats = types.SimpleNamespace(session=fresh_session())
    random.seed(seed)
    outcome = (0, 0, 0)
    for _ in range(trial):
        if game.trial_number > 0:
            for key, value in game.current_stim.items():
                state.stats.session['numbers' if key == 'number' else key].append(value)
                if key == 'vis':
                    state.stats.session['image'].append(value)
        game.trial_number += 1
        try:
            session.generate_stimulus()
            outcome = (0, session._real_back(), session._current_variable_back())
        except (IndexError, ValueError):
            outcome = (1, 0, 0)
            break
    values = [game.current_stim[key] for key in FIELDS]
    return [
        'case', case, seed, trial,
        mode if reported_mode is None else reported_mode, back, outcome[0], values[0],
        values[4], values[5], values[10], values[11], values[12],
        OP[game.current_operation], outcome[1], outcome[2],
        random.getrandbits(32)]


def python_lines():
    out = []
    case = 0
    # Port scope: mode 10 with the source's 3D face-pattern field. Encode the
    # cube-count in the reported mode column so the line schema distinguishes
    # each option case without generating any other N-Back mode.
    for cubes in (1, 2, 3, 6):
        for back in (1, 2, 5):
            for seed in (1, 7, 17, 12345):
                for trial in (1, 4, 10):
                    out.append('|'.join(str(x) for x in one(
                        case, seed, trial, 10, back, True, cubes,
                        1000 + cubes)))
                    case += 1
    return out


def main():
    got = [line for line in subprocess.run(
        [sys.argv[1]], capture_output=True, text=True, check=True
    ).stdout.splitlines() if line and not line.startswith('names|')]
    want = python_lines()
    if got != want:
        for index, (a, b) in enumerate(zip(got, want)):
            if a != b:
                print(f'FAIL: first mismatch at {index}\n  elisa:  {a}\n  python: {b}')
                break
        if len(got) != len(want):
            print(f'FAIL: line count {len(got)} vs {len(want)}')
        return 1
    print(f'PASS: {len(want)} session assembly cases identical')
    return 0


if __name__ == '__main__':
    sys.exit(main())
