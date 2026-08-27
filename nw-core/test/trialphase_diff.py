#!/usr/bin/env python3
"""Differential harness for src/trialphase.elisa against the REAL machine.

`neural_workshop.events.trial_tick` is called here -- not a transliteration of
it -- so every branch, every comparison and every off-by-one in the phase
machine is the module's own.

What is replaced is the six things the machine CALLS OUT to: saving the last
trial's input, generating the next stimulus, resetting the input, hiding the
visuals, refreshing the feedback labels and ending the session. Each becomes a
recorder, and what the two sides compare is which of them fired on which tick.
That is exactly the seam the port draws -- `trialphase.elisa` returns those six
as effects rather than performing them -- so replacing them here is not a
convenience, it IS the thing under test. Nothing in the machine's own body is
touched.

`plan_current_trial_phases` is replaced too, because the real one reads the
live config and the sweep names the four durations directly. It is replaced
with a call to `bwaccel.plan_trial_phases` on those four numbers, which is the
same function the config path would have reached.

SPDX-License-Identifier: GPL-2.0-or-later
"""
import subprocess
import sys

import scenediff

scenediff.reexec()

import bwaccel                                                      # noqa: E402
from neural_workshop import events, state                           # noqa: E402

PHASE_NAMES = {-1: None, 0: 'stimulus', 1: 'blank', 2: 'feedback', 3: 'done'}
PHASE_CODES = {value: key for key, value in PHASE_NAMES.items()}

#: Which callout fired during the tick being recorded.
FIRED = {}
EFFECT_ORDER = ("save_input", "end_session", "generate_stimulus", "reset_input",
                "hide_visuals", "update_input_labels", "update_trials_remaining")


def _record(name):
    def fired(*args, **kwargs):
        FIRED[name] = True
    return fired


class _Visual:
    """One stand-in visual: `hide()` is the effect, and it is all the machine
    asks of it."""

    def hide(self):
        FIRED["hide_visuals"] = True


class _Stats:
    def save_input(self):
        FIRED["save_input"] = True


class _Label:
    def update(self):
        FIRED["update_trials_remaining"] = True


def install(spec):
    """Point every callout at a recorder, and the plan at the spec's numbers."""
    plan = bwaccel.plan_trial_phases(spec["trial_ms"], spec["stimulus_ms"],
                                     spec["feedback_ms"], spec["tick_ms"])
    events.plan_current_trial_phases = lambda: plan
    events.generate_stimulus = _record("generate_stimulus")
    events.reset_input = _record("reset_input")
    events.end_session = _record("end_session")
    events.update_input_labels = _record("update_input_labels")
    state.stats = _Stats()
    state.trials_remaining_label = _Label()
    state.visuals = [_Visual()]

    mode = state.mode
    mode.started = bool(spec["started"])
    mode.paused = bool(spec["paused"])
    mode.step_mode = bool(spec["step_mode"])
    mode.tick = spec["first_tick"]
    mode.num_trials_total = spec["total_trials"]
    mode.trial_number = 0
    mode.phase = None
    mode.phase_elapsed = 0
    mode.show_missed = False
    mode.session_done = False
    mode.ticks_per_trial = 6
    mode.flags = {mode.mode: {'selfpaced': bool(spec["selfpaced"])}}
    return mode


def row(mode, changed):
    cells = [PHASE_CODES[changed], 1 if changed else 0,
             PHASE_CODES[mode.phase], mode.phase_elapsed, mode.tick,
             mode.trial_number, mode.ticks_per_trial,
             1 if mode.show_missed else 0, 1 if mode.session_done else 0]
    cells.extend(1 if FIRED.get(name) else 0 for name in EFFECT_ORDER)
    cells.append(1 if events.response_window_open() else 0)
    # The two gates inside `_on_key_in_session`, restated here because the
    # handler around them is key plumbing and cannot be called without a
    # pyglet key symbol and a config binding for it.
    cells.append(1 if (mode.tick != 0 and mode.trial_number > 0) else 0)
    cells.append(1 if (mode.flags[mode.mode]['selfpaced']
                       and mode.phase in ('stimulus', 'blank', None)) else 0)
    return "|".join(str(one) for one in cells)


def leap_row(mode, reached):
    """`trial_advance_significant` returns the phase it reached, and the
    effects of EVERY tick it ran to get there -- not just the last one's."""
    cells = [PHASE_CODES[reached], mode.phase_elapsed, mode.tick,
             mode.trial_number, 1 if mode.session_done else 0]
    cells.extend(1 if FIRED.get(name) else 0 for name in
                 ("save_input", "end_session", "generate_stimulus",
                  "hide_visuals"))
    return "|".join(str(one) for one in cells)


#: modality_code()'s table, so a button crosses the boundary as a number.
MODALITY_NAMES = ['position1', 'position2', 'position3', 'position4', 'color',
                  'image', 'vis1', 'vis2', 'vis3', 'vis4', 'visvis',
                  'visaudio', 'audiovis', 'audio', 'audio2', 'arithmetic']


class _Window:
    visible = True


class _Prompt:
    """`pulsate` writes a colour onto the prompt's label and reads nothing
    else off it."""

    class _Label:
        color = (0, 0, 0, 255)

    def __init__(self):
        self.label = _Prompt._Label()

    def update(self):
        pass


class _Flashing:
    """A label the adjustments poke. Which of them it is does not matter --
    none of the three reads anything back off it."""

    def flash(self):
        pass

    def update(self):
        pass


class _Mouse:
    """pyglet's own button constants, so the real handler is the one deciding
    what LEFT and RIGHT mean."""


def mouse_codes(mode_number):
    """`on_mouse_press` through the real handler: left, right, and left again
    with the session not started."""
    import pyglet
    mode = state.mode
    mode.mode = mode_number
    out = []
    for button, started in ((pyglet.window.mouse.LEFT, True),
                            (pyglet.window.mouse.RIGHT, True),
                            (pyglet.window.mouse.LEFT, False)):
        mode.started = started
        for name in MODALITY_NAMES[:15]:
            mode.inputs[name] = False
        events.on_mouse_press(0, 0, button, 0)
        reported = [name for name in MODALITY_NAMES[:15] if mode.inputs[name]]
        # 15 is `arithmetic`, which this can never report, so it stands for
        # "no button meant anything here".
        out.append(MODALITY_NAMES.index(reported[0]) if reported else 15)
    mode.started = True
    return out


def input_rows(sweep):
    """The input path and the three adjustments, through the REAL functions."""
    from neural_workshop import session, timing
    events.update_input_labels = _record("update_input_labels")
    state.space_label = _Prompt()
    state.angle = 0
    state.game_mode_label = _Flashing()
    state.session_info_label = _Flashing()

    mode = state.mode
    out = []
    for line in sweep:
        cells = line.split("|")
        tag, step = cells[0], int(cells[1])
        if tag == "input":
            wanted = int(cells[2])
            mode.mode = wanted
            names = events.action_button_names()
            out.append("|".join(["input", str(step), str(wanted)]
                                + [str(one) for one in mouse_codes(wanted)]
                                + [str(len(names))]
                                + [str(MODALITY_NAMES.index(one))
                                   for one in names]))
        elif tag == "press":
            buttons = [MODALITY_NAMES[slot] for slot in range(15)
                       if (slot + step) % 3 == 0]
            buttons.append('arithmetic')
            mode.trial_starttime = 100.0
            now = 100.0 + (step % 5) * 0.25 - 0.5
            for name in MODALITY_NAMES[:15]:
                mode.inputs[name] = False
                mode.input_rts[name] = 0.0
            FIRED.clear()
            pressed = events.inject_match_action(buttons, now=now)
            out.append("|".join(["press", str(step), str(len(pressed)),
                                 "1" if FIRED.get("update_input_labels") else "0"]
                                + [str(MODALITY_NAMES.index(one))
                                   for one in pressed]))
            row = ["state", str(step)]
            row += ["1" if mode.inputs[name] else "0"
                    for name in MODALITY_NAMES[:15]]
            row += [str(int(mode.input_rts[name] * 1000000.0))
                    for name in MODALITY_NAMES[:15]]
            out.append("|".join(row))
        elif tag == "pulse":
            # `pulsate` returns early on a hidden window, and the real one is
            # not visible under a headless run -- so it gets a stand-in that
            # says it is. Nothing else about the window is read.
            state.window = _Window()
            mode.started = False
            events.pulsate(0.0)
            out.append("|".join(["pulse", str(step), str(state.angle),
                                 str(state.space_label.label.color[2])]))
        elif tag == "adjust":
            mode.back = 1 + step % 4
            mode.num_trials = 15 + step % 7
            mode.num_trials_factor = 1
            mode.num_trials_exponent = 2
            events._adjust_level((step % 5) - 2)
            events._adjust_trials((step % 7) - 3)
            interval = 400 + step % 9 * 700
            tick_ms = 50 + step % 3 * 50
            state.cfg.TICK_DURATION_MS = tick_ms
            speeds = []
            for faster in (True, False):
                state.cfg.TRIAL_INTERVAL_MS = interval
                events._adjust_speed(faster)
                speeds.append(int(state.cfg.TRIAL_INTERVAL_MS))
            out.append("|".join(["adjust", str(step), str(mode.back),
                                 str(mode.num_trials), str(mode.num_trials_total),
                                 str(interval), str(tick_ms)]
                                + [str(one) for one in speeds]))
    return out


def parse(binary):
    got = subprocess.run([binary], capture_output=True, text=True, check=True)
    names, specs, runs, current = None, [], [], None
    tail = []
    for line in got.stdout.splitlines():
        if not line.strip():
            continue
        if line.split("|")[0] in ("input", "press", "state", "adjust", "pulse"):
            tail.append(line)
            continue
        if line.startswith("names|"):
            names = line.split("|")[1:]
        elif line.startswith("spec|"):
            specs.append(dict(zip(names, (int(one) for one in
                                          line.split("|")[1:]))))
            current = []
        elif line == "end":
            runs.append(current)
            current = None
        elif current is not None:
            current.append(line)
    if not specs:
        raise SystemExit("sweep printed no specs at all")
    return specs, runs, tail


def main():
    specs, mine, tail = parse(sys.argv[1])
    bad = 0
    for spec, ours in zip(specs, mine):
        mode = install(spec)
        theirs = []
        for _ in range(spec["ticks"]):
            FIRED.clear()
            changed = events.trial_tick()
            theirs.append(row(mode, changed))
        mode = install(spec)
        for _ in range(spec["jumps"]):
            FIRED.clear()
            theirs.append(leap_row(mode, events.trial_advance_significant()))
        if ours == theirs:
            continue
        bad += 1
        if bad > 3:
            continue
        print("MISMATCH spec %s" % (
            " ".join("%s=%s" % pair for pair in sorted(spec.items())),))
        for at, (a, b) in enumerate(zip(ours, theirs)):
            if a != b:
                print("  first differing tick %d" % at)
                print("    elisa:  %s" % a)
                print("    python: %s" % b)
                break
    theirs = input_rows(tail)
    for at, (a, b) in enumerate(zip(tail, theirs)):
        if a != b:
            bad += 1
            if bad <= 4:
                print("MISMATCH input row %d" % at)
                print("    elisa:  %s" % a)
                print("    python: %s" % b)
    if len(tail) != len(theirs):
        print("input rows: elisa %d, python %d" % (len(tail), len(theirs)))
        bad += 1
    if bad:
        print("FAIL: %d differences" % bad)
        return 1
    print("PASS: %d runs, %d ticks and %d input rows identical"
          % (len(mine), sum(len(run) for run in mine), len(tail)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
