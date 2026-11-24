"""Replay Semaphore's code chart, grades, deals, play and sound against Python."""
from math import isclose
from pathlib import Path
from random import Random
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced"))
from neural_workshop import drshape, semaphore
from neural_workshop import hand as H

HELP = {"named": 0, "chart": 1, "peek": 2, "none": 3}
LETTERS = semaphore.LETTERS


def close(actual, expected):
    actual = tuple(map(float, actual))
    assert len(actual) == len(expected) and all(
        isclose(a, b, abs_tol=2e-12, rel_tol=2e-12) for a, b in zip(actual, expected)
    ), (actual, expected)


def pair(pose):
    return -1 if pose is None else pose[0] * 8 + pose[1]


def said(text):
    """The Elisa run keeps what went wrong as a kind; see `letter` below."""
    if not text:
        return 0
    if text == "Your flags do not match":
        return 1
    if text.startswith("That was "):
        return 2
    assert text.startswith("You let ") and text.endswith(" pass"), text
    return 3


def player(run, mode):
    if mode == 0:
        ports = semaphore.autopilot(run)
        return ports[0] if ports else None
    if mode == 1:
        return None
    if mode == 2:
        ports = semaphore.autopilot(run)
        port = ports[0] if ports else None
        if port is None or port < H.KEYS:
            return port
        return H.KEYS + (port - H.KEYS + 1) % 26
    k = run.index()
    if k is None or run.read[k] is not None:
        return None
    return H.KEYS + LETTERS.index(run.message.text[k])


def check(binary):
    rows = iter(subprocess.check_output([binary], text=True).splitlines())
    marker, *chart = next(rows).split()
    assert marker == "code"
    assert [int(v) for v in chart] == [a * 8 + b for a, b in (semaphore.CODE[c] for c in LETTERS)], chart
    for rung in range(81):
        marker, *values = next(rows).split()
        assert marker == "grade"
        g = semaphore.grade(rung)
        close(values, (g.rung, g.letters, g.hold, g.near, HELP[g.help], g.roll, g.turns, g.words, g.fog,
                       g.strikes, g.seconds))
    patches = [drshape.make_patch(voice, Random(i + 1)) for i, voice in enumerate(semaphore.PATCHES)]
    modes = [(0, rung, 17) for rung in (1, 4, 7, 10, 13, 16, 20, 25, 30)]
    modes += [(mode, 1, 19) for mode in range(1, 4)]
    steps = cues = strikes = 0
    for mode, rung, seed in modes:
        draw = Random(seed)
        message = semaphore.deal(rung, rng=draw)
        marker, *values = next(rows).split()
        assert marker == "message"
        expected = [mode, rung, seed, message.seed, True, draw.getrandbits(32), len(message.text)]
        for letter, turned in zip(message.text, message.turned):
            expected += [LETTERS.index(letter), turned]
        close(values, expected)
        run = semaphore.Run(message)
        kind, letter = 0, 0
        while run.result is None:
            before = list(run.read)
            port = player(run, mode)
            if port is not None:
                semaphore.act(run, port)
            run.step(1 / 60)
            result = 0 if run.result is None else 1 if run.result[0] else 2
            # The letter of the signal just struck: the one that said it.
            struck = [i for i, (a, b) in enumerate(zip(before, run.read)) if a is None and b is False]
            assert len(struck) <= 1, struck
            if struck:
                letter = LETTERS.index(run.message.text[struck[0]])
                kind = said(run.said)
                if kind == 2:
                    assert run.said == "That was " + run.message.text[struck[0]]
                if kind == 3:
                    assert run.said == "You let %s pass" % run.message.text[struck[0]]
            theirs = run.theirs()
            values = next(rows).split()
            read = values.pop()
            expected = (-1 if port is None else port, result, run.hand.x, run.hand.y, run.hand.down, run.t,
                        run.flags[0], run.flags[1], -1 if run.held is None else run.held, run.strikes,
                        kind, letter, run.rung_at, run.matched, -1 if run.index() is None else run.index(),
                        theirs[0], theirs[1], run.back(), HELP[run.helped()], run.fogged(), pair(run.pose()))
            try:
                close(values, expected)
                assert read == "".join("n" if r is None else "1" if r else "0" for r in run.read), read
            except (AssertionError, ValueError) as error:
                raise AssertionError((mode, rung, run.t, error)) from error
            steps += 1
        done = sum(1 for r in run.read if r)
        assert next(rows).split() == ["end", str(result), str(done)]
        assert result == (1 if mode == 0 else 2), (mode, run.result)
        strikes += run.strikes
        assert next(rows) == f"notes {len(run.notes)}"
        for note in run.notes:
            close(next(rows).split(), (note.seed, note.voice, note.t, note.dur, note.freq, note.gain, note.pan))
            cues += 1
        for _ in range(3):
            marker, stamp = next(rows).split()
            assert marker == "audio"
            t = float(stamp)
            assert bytes.fromhex(next(rows)) == drshape.synth(run.notes, t, t + 0.1, patches), (rung, mode, t)
    assert next(rows, None) is None
    print(f"PASS: {82 + len(modes)} Semaphore cases (the code chart, 81 grades, {len(modes)} runs), {steps} steps, "
          f"{strikes} strikes, {cues} cues, and {3 * len(modes)} stereo windows match Python")


if __name__ == "__main__":
    check(sys.argv[1])
