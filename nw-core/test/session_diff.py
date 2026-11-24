#!/usr/bin/env python3
"""Differential harness: session.elisa vs the real neural_workshop/session.py.

Every row below comes from the ACTUAL reference module. session.py reads three
mutable module singletons -- ``state.cfg``, ``state.mode`` and
``state.stats.session`` -- so the harness builds a real :class:`DotDict`, a real
:class:`gamemode.Mode` (which brings the real mode tables with it) and a
stand-in stats object with the same session dict ``stats.initialize_session``
would have made, assigns them onto the imported ``state`` module, and then calls
``session.generate_stimulus()`` itself. Nothing here re-implements it.

Two of generate_stimulus's steps are replaced with no-ops: ``_queue_audio``
drives pyglet media players and ``_spawn_visuals`` drives sprites, neither of
which exists outside a built application -- and, crucially, neither of which
touches the random stream, so stubbing them shifts nothing. They are the two
functions session.elisa deliberately does not port.

WHAT THIS ACTUALLY TESTS
------------------------

A whole session, trial by trial: every field of ``mode.current_stim``, the
chosen arithmetic operation, ``_real_back()`` and ``_current_variable_back()``.
Then, once the session ends, a 32-bit draw off the shared generator -- which
only matches if BOTH sides consumed the Mersenne Twister exactly the same number
of times. That last number is the real prize: a port that produced the right
stimuli by luck while drawing a different number of times would pass every trial
row and fail here.
"""
from pathlib import Path
import subprocess
import sys
import types

APP = str(Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced")
sys.path.insert(0, APP)

import random  # noqa: E402

from bwaccel import fallback  # noqa: E402
from neural_workshop import gamemode, runtime, session, state  # noqa: E402
from neural_workshop.config import DotDict  # noqa: E402
from neural_workshop.stats import _EXTRA_STREAMS, _TRACKED_STIMULI  # noqa: E402

# The reference prints a trace under --debug; the core does no I/O, so the
# comparison is only honest with it off (it is off by default).
runtime.DEBUG = False

# _queue_audio() and _spawn_visuals() are the render/audio layers. They draw
# nothing from the random stream, which is why leaving them unported is safe.
session._queue_audio = lambda: None
session._spawn_visuals = lambda multi, variable: None

STIMULUS_FIELDS = list(gamemode.STIMULUS_FIELDS)
ARITH_OP_CODE = {'none': 0, 'add': 1, 'subtract': 2, 'multiply': 3, 'divide': 4}

STOCK_DECIMALS = ['0.1', '0.2', '0.3', '0.4', '0.5', '0.6', '0.7', '0.8', '0.9',
                  '0.125', '0.25', '0.375', '0.625', '0.75', '0.875',
                  '0.15', '0.35', '0.45', '0.55', '0.65', '0.85', '0.95']

BASE = dict(
    GAME_MODE=2, BACK_DEFAULT=2, TICKS_DEFAULT=30, BONUS_TICKS_CRAB=0,
    BONUS_TICKS_MULTI_2=5, BONUS_TICKS_MULTI_3=10, BONUS_TICKS_MULTI_4=15,
    NUM_TRIALS=20, NUM_TRIALS_FACTOR=1, NUM_TRIALS_EXPONENT=2,
    MANUAL=True, HIDE_TEXT=False, SKIP_TITLE_SCREEN=False,
    BLACK_BACKGROUND=False,
    CHANCE_OF_GUARANTEED_MATCH=0.125, CHANCE_OF_INTERFERENCE=0.125,
    VARIABLE_NBACK=0, JAEGGI_MODE=0, MULTI_MODE='color',
    VISUAL_COLORS=[1, 3, 8, 6],
    ARITHMETIC_USE_ADDITION=True, ARITHMETIC_USE_SUBTRACTION=True,
    ARITHMETIC_USE_MULTIPLICATION=True, ARITHMETIC_USE_DIVISION=True,
    ARITHMETIC_USE_NEGATIVES=False, ARITHMETIC_MAX_NUMBER=12,
    ARITHMETIC_ACCEPTABLE_DECIMALS=STOCK_DECIMALS,
    GRID_SIZE=3, GRID_SIZE_MIN=2, GRID_SIZE_MAX=32,
    GRID_INCLUDE_CENTER=False, GRID_3D=False, GRID_3D_CUBES=1,
    ACTIVE_POSITION_CELLS=0, POSITION_CELL_COUNT=0,
)


def profile(**overrides):
    merged = dict(BASE)
    merged.update(overrides)
    return merged


# Mirrored key for key by make_cfg() in session_sweep.elisa.
PROFILES = [
    # 0: stock config.ini on the classic 3x3 board.
    profile(),
    # 1: variable n-back, image multi-mode, a 5x5 board with its centre in
    #    play, negative arithmetic operands, and matches twice as likely.
    profile(CHANCE_OF_GUARANTEED_MATCH=0.5, CHANCE_OF_INTERFERENCE=0.5,
            VARIABLE_NBACK=1, MULTI_MODE='image',
            GRID_SIZE=5, GRID_INCLUDE_CENTER=True,
            ARITHMETIC_USE_NEGATIVES=True, ARITHMETIC_MAX_NUMBER=9),
    # 2: the 3D cube board (36 pattern ids, 64 colour ids), and division as
    #    the ONLY arithmetic operation -- so choice() runs over a single-item
    #    list, which still draws.
    profile(CHANCE_OF_GUARANTEED_MATCH=0.25, CHANCE_OF_INTERFERENCE=0.75,
            GRID_3D=True, GRID_3D_CUBES=2,
            ARITHMETIC_USE_ADDITION=False, ARITHMETIC_USE_SUBTRACTION=False,
            ARITHMETIC_USE_MULTIPLICATION=False,
            ARITHMETIC_USE_DIVISION=True),
    # 3: a board capped to three cells with matches almost always forced. The
    #    quad-stim modes then index `positions` past its end exactly as the
    #    reference does, which is what the `raised` column records.
    profile(CHANCE_OF_GUARANTEED_MATCH=0.9, CHANCE_OF_INTERFERENCE=0.9,
            GRID_SIZE=5, ACTIVE_POSITION_CELLS=3,
            ARITHMETIC_MAX_NUMBER=4),
    # 4: Jaeggi mode, which overwrites position1/audio from the fixed
    #    sequence after everything else has been decided. GRID_SIZE is below
    #    GRID_SIZE_MIN, so the board clamps up to 2x2.
    profile(JAEGGI_MODE=1, VARIABLE_NBACK=0,
            ARITHMETIC_USE_SUBTRACTION=False, ARITHMETIC_USE_DIVISION=False,
            GRID_SIZE=1),
    # 5: variable n-back on a board capped through the LEGACY key, with
    #    interference always on and guaranteed matches off -- so every planted
    #    lag comes from the shuffle in _interference_back. GRID_SIZE is above
    #    GRID_SIZE_MAX, so the board clamps down to 4x4.
    profile(CHANCE_OF_GUARANTEED_MATCH=0.0, CHANCE_OF_INTERFERENCE=1.0,
            VARIABLE_NBACK=1, GRID_SIZE=6, GRID_SIZE_MAX=4,
            POSITION_CELL_COUNT=5,
            MULTI_MODE='image', ARITHMETIC_MAX_NUMBER=7,
            ARITHMETIC_USE_NEGATIVES=True),
]

# Mirrored by session_sweep.elisa. Base modes, a crab variant, the three
# multi-stim widths of dual n-back, a multi variant that carries vis1 (so the
# reversal can pick the vis field), a crab-of-multi, and a self-paced one.
MODES = [2, 5, 7, 8, 9, 20, 21, 24, 100, 107, 130, 258, 514, 770, 276, 533,
         1026, 386]
BACKS = [1, 2, 3, 5]
SEEDS = [1, 7, 12345]
TRIALS = 18


def fresh_session():
    """The dict stats.initialize_session() builds."""
    out = {}
    for name in _TRACKED_STIMULI:
        out[name] = []
        out['%s_input' % name] = []
        out['%s_rt' % name] = []
    for name in _EXTRA_STREAMS:
        out[name] = []
    return out


def record(stats, mode):
    """The stimulus half of stats.save_input().

    The answer streams it also fills are irrelevant here: nothing in stimulus
    generation reads them.
    """
    for key, value in mode.current_stim.items():
        stats.session['numbers' if key == 'number' else key].append(value)
        if key == 'vis':
            stats.session['image'].append(value)


def bt_sequence(length):
    """A fixed Jaeggi sequence, built without touching the random stream.

    The real one comes out of ``bwaccel.compute_bt_sequence``, which runs on
    the C backend when it is available and so draws from a generator Python's
    ``random`` module cannot see. Injecting a deterministic sequence keeps the
    comparison about generate_stimulus's own draws; the constructive sequence
    builder itself is already covered by the `stimulus` suite.
    """
    return ([1 + (i * 3 + 1) % 8 for i in range(length)],
            [1 + (i * 5 + 2) % 8 for i in range(length)])


def install(index, mode, back):
    cfg = DotDict(PROFILES[index])
    cfg.GAME_MODE = mode
    state.cfg = cfg
    game = gamemode.Mode()
    game.back = back
    game.trial_number = 0
    game.num_trials_total = TRIALS
    state.mode = game
    state.stats = types.SimpleNamespace(session=fresh_session())
    return cfg, game


def run_case(case, index, mode, back, seed):
    cfg, game = install(index, mode, back)
    random.seed(seed)
    out = ["c,%d,%d,%d,%d,%d" % (case, index, mode, back, seed)]

    if cfg.VARIABLE_NBACK:
        # new_session() builds this off bwaccel; the pure-Python kernel is the
        # one src/stimulus.elisa is a port of, so both sides draw it from the
        # same seeded stream and the whole session stays one comparison.
        game.variable_list = fallback._variable_nback_list_py(
            TRIALS - back, back)
    if cfg.JAEGGI_MODE:
        game.bt_sequence = list(bt_sequence(TRIALS))

    done = 0
    for _ in range(TRIALS):
        if game.trial_number > 0:
            record(state.stats, game)
        game.trial_number += 1
        try:
            session.generate_stimulus()
            real_back = session._real_back()
            variable = session._current_variable_back()
        except (IndexError, ValueError):
            # The reference raises straight out of generate_stimulus and the
            # session dies with it. Recorded as an outcome both sides agree on
            # rather than a skipped row.
            out.append("t,%d,%d,1" % (case, game.trial_number))
            break
        cells = [game.current_stim[name] for name in STIMULUS_FIELDS]
        out.append("t,%d,%d,0,%s,%d,%d,%d" % (
            case, game.trial_number, ",".join(str(v) for v in cells),
            ARITH_OP_CODE[game.current_operation], real_back, variable))
        done += 1

    # The stream position after the whole session. This is the column that
    # catches a port which drew the right values the wrong number of times.
    out.append("s,%d,%d,%d" % (case, done, random.getrandbits(32)))
    return out


def python_lines():
    out = []
    case = 0
    for index in range(len(PROFILES)):
        for mode in MODES:
            for back in BACKS:
                for seed in SEEDS:
                    out += run_case(case, index, mode, back, seed)
                    case += 1
    return out


def main():
    got = [ln for ln in subprocess.run([sys.argv[1]], capture_output=True, text=True,
                                       check=True).stdout.splitlines() if ln.strip()]
    want = python_lines()
    if len(got) != len(want):
        print(f"FAIL: line count {len(got)} vs {len(want)}")
        for i, (g, w) in enumerate(zip(got, want)):
            if g != w:
                print(f"  first divergence at line {i}\n  elisa:  {g}\n  python: {w}")
                break
        return 1
    bad = [(i, g, w) for i, (g, w) in enumerate(zip(got, want)) if g != w]
    for i, g, w in bad[:8]:
        print(f"MISMATCH line {i}\n  elisa:  {g}\n  python: {w}")
    if bad:
        print(f"FAIL: {len(bad)}/{len(want)} mismatches")
        return 1
    print(f"PASS: {len(want)} cases identical")
    return 0


if __name__ == "__main__":
    sys.exit(main())
