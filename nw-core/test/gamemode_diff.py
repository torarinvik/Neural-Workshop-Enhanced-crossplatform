#!/usr/bin/env python3
"""Differential harness: gamemode.elisa vs the real neural_workshop/gamemode.py.

Every row below comes from the ACTUAL reference module. gamemode.py reads one
mutable module singleton, ``state.cfg``, so the harness builds a real
:class:`DotDict` -- the same class the running program uses, with the same
``key in cfg`` / ``cfg['key']`` semantics -- and assigns it onto the imported
``state`` module before each call. Nothing here re-implements the reference.

``gamemode._`` is pinned to the identity for the run. There is no compiled
message catalogue in the tree (``res/i18n`` carries a .po and no .mo), so
gettext already falls back to the msgids; pinning it makes that independent of
the machine's locale, and the port carries the msgids for the same reason.
"""
from pathlib import Path
import subprocess
import sys

APP = str(Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced")
sys.path.insert(0, APP)

from neural_workshop import gamemode, state  # noqa: E402
from neural_workshop.config import DotDict  # noqa: E402

gamemode._ = lambda message: message

MODALITY_CODE = {
    'position1': 0, 'position2': 1, 'position3': 2, 'position4': 3,
    'color': 4, 'image': 5,
    'vis1': 6, 'vis2': 7, 'vis3': 8, 'vis4': 9,
    'visvis': 10, 'visaudio': 11, 'audiovis': 12,
    'audio': 13, 'audio2': 14, 'arithmetic': 15,
}

STIM_FIELD_CODE = {
    'position1': 0, 'position2': 1, 'position3': 2, 'position4': 3,
    'color': 4, 'vis': 5,
    'vis1': 6, 'vis2': 7, 'vis3': 8, 'vis4': 9,
    'audio': 10, 'audio2': 11, 'number': 12,
}

ARITH_OP_CODE = {'none': 0, 'add': 1, 'subtract': 2, 'multiply': 3, 'divide': 4}
PHASE_CODE = {None: -1, 'stimulus': 0, 'blank': 1, 'feedback': 2, 'done': 3}

# Mirrors make_cfg() / back_overrides() / ticks_overrides() in the sweep.
PROFILES = [
    dict(GAME_MODE=2, BACK_DEFAULT=2, TICKS_DEFAULT=30, BONUS_TICKS_CRAB=0,
         BONUS_TICKS_MULTI_2=5, BONUS_TICKS_MULTI_3=10, BONUS_TICKS_MULTI_4=15,
         NUM_TRIALS=20, NUM_TRIALS_FACTOR=1, NUM_TRIALS_EXPONENT=2,
         MANUAL=False, HIDE_TEXT=False, SKIP_TITLE_SCREEN=False,
         BLACK_BACKGROUND=False,
         BACK_4=1, BACK_5=1, BACK_6=1, BACK_7=1, BACK_8=1, BACK_9=1,
         TICKS_4=35, TICKS_5=35, TICKS_6=35,
         TICKS_7=40, TICKS_8=40, TICKS_9=40),
    dict(GAME_MODE=2, BACK_DEFAULT=3, TICKS_DEFAULT=25, BONUS_TICKS_CRAB=7,
         BONUS_TICKS_MULTI_2=2, BONUS_TICKS_MULTI_3=4, BONUS_TICKS_MULTI_4=6,
         NUM_TRIALS=15, NUM_TRIALS_FACTOR=2, NUM_TRIALS_EXPONENT=3,
         MANUAL=True, HIDE_TEXT=True, SKIP_TITLE_SCREEN=True,
         BLACK_BACKGROUND=True),
    dict(GAME_MODE=2, BACK_DEFAULT=1, TICKS_DEFAULT=45, BONUS_TICKS_CRAB=3,
         BONUS_TICKS_MULTI_2=5, BONUS_TICKS_MULTI_3=10, BONUS_TICKS_MULTI_4=15,
         NUM_TRIALS=25, NUM_TRIALS_FACTOR=1, NUM_TRIALS_EXPONENT=1,
         MANUAL=False, HIDE_TEXT=False, SKIP_TITLE_SCREEN=True,
         BLACK_BACKGROUND=False,
         BACK_2=5, BACK_130=9, BACK_258=4, BACK_1154=6,
         TICKS_130=11, TICKS_514=99, TICKS_1026=77),
    dict(GAME_MODE=107, BACK_DEFAULT=4, TICKS_DEFAULT=0, BONUS_TICKS_CRAB=1,
         BONUS_TICKS_MULTI_2=0, BONUS_TICKS_MULTI_3=0, BONUS_TICKS_MULTI_4=0,
         NUM_TRIALS=0, NUM_TRIALS_FACTOR=0, NUM_TRIALS_EXPONENT=0,
         MANUAL=False, HIDE_TEXT=True, SKIP_TITLE_SCREEN=False,
         BLACK_BACKGROUND=True),
]

EXTRA_MODES = [0, 1, 13, 19, 29, 99, 108, 126, 127, 128, 129, 142, 255, 256,
               257, 383, 384, 511, 512, 640, 768, 769, 895, 1023, 1024, 1025,
               1151, 1152, 1279, 1280, 1408, 1791, 1792, 2047]

STOCK_COLORS = {
    1: (0, 0, 255, 255), 2: (0, 255, 255, 255), 3: (0, 255, 0, 255),
    4: (48, 48, 48, 255), 5: (255, 0, 255, 255), 6: (255, 0, 0, 255),
    7: (208, 208, 208, 255), 8: (255, 255, 0, 255),
}
STOCK_BLK = {4: (255, 255, 255, 255), 7: (64, 64, 64, 255)}

# Palette 1 drops COLOR_8 and COLOR_4_BLK so the sweep also covers the indices
# where the reference's cfg[...] subscript raises KeyError.
SPARSE_COLORS = {k: v for k, v in STOCK_COLORS.items() if k != 8}
SPARSE_BLK = {7: STOCK_BLK[7]}


def install(profile, **overrides):
    cfg = DotDict(PROFILES[profile])
    cfg.update(overrides)
    state.cfg = cfg
    return cfg


def install_palette(profile, colors, blk):
    cfg = install(profile)
    for index, rgba in colors.items():
        cfg['COLOR_%i' % index] = rgba
    for index, rgba in blk.items():
        cfg['COLOR_%i_BLK' % index] = rgba
    return cfg


def ticks_cells(value):
    """``ticks,is_float`` for a default_ticks() result.

    The reference returns a float for every variant mode (true division in the
    crab-bonus expression) although both the annotation and the caller say int.
    The value is always integral, so an exact i64 comparison is legitimate --
    but only after checking that here.
    """
    if float(value) != int(value):
        return "999999,9"
    return "%d,%d" % (int(value), 1 if isinstance(value, float) else 0)


def table_rows(tables):
    out = []
    for index, mode in enumerate(tables.short_names):
        flags = tables.flags[mode]
        mods = tables.modalities[mode]
        codes = ''.join(':%d' % MODALITY_CODE[name] for name in mods)
        out.append("mo,%d,%d,%d,%d,%d,%d%s|%s|%s" % (
            index, mode, flags['crab'], flags['multi'], flags['selfpaced'],
            len(mods), codes, tables.short_names[mode], tables.long_names[mode]))
    return out


def order_rows():
    out = []
    for index, name in enumerate(gamemode.INPUT_MODALITIES):
        out.append("im,%d,%d" % (index, MODALITY_CODE[name]))
    for index, name in enumerate(gamemode.STIMULUS_FIELDS):
        out.append("sf,%d,%d" % (index, STIM_FIELD_CODE[name]))
    return out


def default_rows(mode_keys):
    out = []
    modes = list(mode_keys) + EXTRA_MODES
    for profile in range(len(PROFILES)):
        install(profile)
        for mode in modes:
            out.append("nb,%d,%d,%d" % (profile, mode,
                                        gamemode.default_nback_mode(mode)))
            out.append("tk,%d,%d,%s" % (profile, mode,
                                        ticks_cells(gamemode.default_ticks(mode))))
    return out


def color_rows():
    out = []
    palettes = [(STOCK_COLORS, STOCK_BLK), (SPARSE_COLORS, SPARSE_BLK)]
    for which, (colors, blk) in enumerate(palettes):
        for black in (0, 1):
            install_palette(0, colors, blk)
            state.cfg.BLACK_BACKGROUND = bool(black)
            for color in range(11):
                try:
                    rgba = gamemode.get_color(color)
                    cells = "1,%d,%d,%d,%d" % tuple(rgba)
                except KeyError:
                    # cfg[...] is a plain dict subscript; an unconfigured
                    # colour index raises rather than reading as None.
                    cells = "0,0,0,0,0"
                out.append("gc,%d,%d,%d,%s" % (which, black, color, cells))
    for color in range(-12, 21):
        out.append("c3,%d,%d,%d,%d,%d" % ((color,) + tuple(gamemode.get_3d_color(color))))
    return out


def label(game, mode, back):
    return game.short_name(mode, back) if mode in game.short_mode_names else ''


def mode_rows(mode_keys):
    out = []
    for profile in range(len(PROFILES)):
        for selector in range(16):
            selected = mode_keys[selector * 14] if selector < 15 else 1152
            install(profile, GAME_MODE=selected)
            game = gamemode.Mode()
            out.append("md,%d,%d,%d,%s,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d|%s" % (
                profile, game.mode, game.back, ticks_cells(game.ticks_per_trial),
                game.num_trials, game.num_trials_factor, game.num_trials_exponent,
                game.num_trials_total, 1 if game.manual else 0,
                1 if game.hide_text else 0, 1 if game.title_screen else 0,
                game.session_number, game.trial_number,
                ARITH_OP_CODE[game.current_operation], PHASE_CODE[game.phase],
                label(game, game.mode, game.back)))

            switched = 2 if selected != 2 else 107
            game.mode = switched
            game.session_number = 7
            game.back = 42
            game.enforce_standard_mode()
            out.append("es,%d,%d,%d,%s,%d,%d|%s" % (
                profile, game.mode, game.back, ticks_cells(game.ticks_per_trial),
                game.num_trials_total, game.session_number,
                label(game, game.mode, game.back)))
    return out


def initial_state_rows():
    install(0)
    game = gamemode.Mode()
    out = []
    for index, name in enumerate(gamemode.INPUT_MODALITIES):
        out.append("in,%d,%d,%d" % (index, 1 if game.inputs[name] else 0,
                                    int(game.input_rts[name] * 100000.0)))
    for index, name in enumerate(gamemode.STIMULUS_FIELDS):
        out.append("cs,%d,%d" % (index, game.current_stim[name]))
    return out


def lookup_rows(tables):
    probes = [2, 3, 107, 130, 258, 514, 770, 1026, 1154, 2025, 0, 1, 13, 128,
              1152, 2047]
    return ["mi,%d,%d" % (mode, 1 if mode in tables.short_names else 0)
            for mode in probes]


def python_lines():
    install(0)
    tables = gamemode.ModeTables()
    mode_keys = list(tables.short_names)
    out = table_rows(tables)
    out += order_rows()
    out += default_rows(mode_keys)
    out += color_rows()
    out += mode_rows(mode_keys)
    out += initial_state_rows()
    out += lookup_rows(tables)
    return out


def main():
    got = [ln for ln in subprocess.run([sys.argv[1]], capture_output=True, text=True,
                                       check=True).stdout.splitlines() if ln.strip()]
    want = python_lines()
    if len(got) != len(want):
        print(f"FAIL: line count {len(got)} vs {len(want)}")
        for g, w in list(zip(got, want))[:6]:
            print(f"  elisa:  {g}\n  python: {w}")
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
