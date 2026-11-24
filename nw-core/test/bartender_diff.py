"""Compare the Bartender reference player, orders, verdicts, and PCM with Python."""
from math import isclose
from pathlib import Path
from random import Random
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced"))
from neural_workshop import bartender, drshape


def close(actual, expected):
    actual = tuple(map(float, actual))
    assert len(actual) == len(expected) and all(
        isclose(a, b, abs_tol=2e-12, rel_tol=2e-12) for a, b in zip(actual, expected)
    ), (actual, expected)


def orders(rows, night):
    for order in night.orders:
        close(next(rows).split(), order[:-1])
        assert next(rows) == order.text


def setup(run, mode):
    if mode == 0:
        return
    order = run.night.orders[0]
    if mode != 5:
        run.strikes = run.level.strikes - 1
    if mode == 2:
        run.hand.to(*bartender.VIEW.see(run.glass())[:2])
        run.hand.down = True
        run.held = ("bottle", 0)
        run.level_in = 1.04
    elif mode == 3:
        run.glass_x = bartender.END
        run.sliding = (bartender.END + 1, 3)
    elif mode in (4, 5):
        run.t = order.leave
    else:
        if mode == 6:
            run.t = order.arrive
        run.glass_x = bartender.SEATS[order.seat]
        run.sliding = (run.glass_x, 3)


def check(binary):
    rows = iter(subprocess.check_output([binary], text=True).splitlines())
    for rung in range(81):
        marker, *values = next(rows).split()
        assert marker == "grade"
        close(values, bartender.grade(rung))
    large_night = bartender.build(bartender.grade(1000), Random(19))
    orders(rows, large_night)
    patches = [drshape.make_patch(voice, Random(i + 1)) for i, voice in enumerate(bartender.PATCHES)]
    verdicts = ("", "Last orders: a good night", "Too much spilt", "Too many glasses on the floor",
                "Too many customers walked out", "Not everyone got their drink", "Too many wrong drinks",
                "Too many drinks sent to nobody")
    cases = [(0, rung, 17) for rung in (1, 4, 7, 10, 13, 16, 20, 25, 30)]
    cases += [(mode, 1, 19) for mode in range(2, 8)]
    steps = cues = 0
    for mode, rung, seed in cases:
        draw = Random(seed)
        night = bartender.deal(rung, rng=draw)
        marker, *values = next(rows).split()
        assert marker == "night", (marker, values)
        close(values, (mode, rung, seed, night.seed, draw.getrandbits(32)))
        orders(rows, night)
        run = bartender.Run(night)
        setup(run, mode)
        while run.result is None:
            ports = bartender.autopilot(run) if mode == 0 else []
            port = ports[0] if ports and ports[0] is not None else -1
            if port >= 0:
                bartender.act(run, port)
            run.step(1 / 60)
            result = verdicts.index(run.result[1]) if run.result is not None else 0
            held = -1 if run.held is None else 5 if run.held[0] == "glass" else run.held[1]
            expected = (port, result, run.hand.x, run.hand.y, run.hand.down, run.t, sum(run.served), sum(run.gone),
                        run.strikes, run.glass_x, run.level_in, run.drink, run.ice, held, run.was(),
                        run.sliding is not None, *(run.sliding or ()))
            try:
                close(next(rows).split(), expected)
            except (AssertionError, ValueError) as error:
                raise AssertionError((mode, rung, run.t, error)) from error
            steps += 1
        assert result == (mode or 1)
        assert next(rows) == f"notes {len(run.notes)}"
        for note in run.notes:
            close(next(rows).split(), (note.seed, note.voice, note.t, note.dur, note.freq, note.gain, note.pan))
            cues += 1
        for _ in range(3):
            marker, stamp = next(rows).split()
            assert marker == "audio"
            begin = float(stamp)
            assert bytes.fromhex(next(rows)) == drshape.synth(run.notes, begin, begin + 0.1, patches), (rung, mode, begin)
    assert next(rows, None) is None
    print(f"PASS: {82 + len(cases)} Bartender cases, {len(large_night.orders)} high-rung orders, "
          f"{steps} steps, {cues} cues, and {3 * len(cases)} stereo PCM windows match Python")


if __name__ == "__main__":
    check(sys.argv[1])
