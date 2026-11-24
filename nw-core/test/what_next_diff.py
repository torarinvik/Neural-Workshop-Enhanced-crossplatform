"""Compare clip choices, rejection, random draws and playback against Python."""
from math import isclose
from pathlib import Path
from random import Random
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced"))
from neural_workshop import whatnext


def clip(length, seed, size, still=False):
    if still:
        return [bytes([64] * size) for _ in range(length)]
    return [bytes((seed * 37 + frame * 6 + at * 3) % 256 for at in range(size))
            for frame in range(length)]


def compare(rows, rung, scenario):
    header = next(rows).split()
    seed = (rung + 2) * 13 + scenario
    assert tuple(map(int, header[:3])) == (rung, scenario, seed)
    level = whatnext.grade(rung)
    kind_ids = (*whatnext.KINDS, "truth")
    assert int(header[3]) == level.choices
    assert int(header[4]) == sum(1 << kind_ids.index(kind) for kind in level.kinds)
    assert isclose(float(header[5]), level.context, rel_tol=0, abs_tol=1e-16)

    length = {1: 9, 2: 27}.get(scenario, 120)
    base = clip(length, 0, 600, still=scenario == 3)
    others = [clip(12 if scenario == 4 and at < 2 else 100,
                   3 if scenario == 6 else at + 3,
                   400 if at % 2 == 0 else 600)
              for at in range(0 if scenario in (3, 5) else 6)]
    rng = Random(seed)
    puzzle = whatnext.build(base, others, level, rng)
    assert int(header[-1]) == rng.getrandbits(32), (rung, scenario, "RNG draw")
    count, answer, opening_start = map(int, header[6:9])
    if puzzle is None:
        assert count == 0, (rung, scenario, "rejected")
        return False
    assert (count, answer) == (len(puzzle.options), puzzle.answer), (rung, scenario, "answer")
    identity = {id(frame): (source, index)
                for source, video in enumerate([base, *others])
                for index, frame in enumerate(video)}
    for kind, option in zip(puzzle.kinds, puzzle.options):
        source, start = identity[id(option[0])]
        step = identity[id(option[1])][1] - start
        actual = tuple(map(int, next(rows).split()))
        assert actual == (kind_ids.index(kind), source, start, len(option), step), (rung, scenario, kind, actual, (source, start, len(option), step))
    opened = int(next(rows))
    assert (opening_start, opened) == (identity[id(puzzle.opening[0])][1], len(puzzle.opening))
    piece = len(puzzle.options[0])
    for tick in range(opened + piece + 2):
        at = tick % (opened + piece)
        frames = [puzzle.opening[min(at, opened - 1)]]
        frames.extend(option[max(0, at - opened)] for option in puzzle.options)
        assert [int(next(rows)) for _ in frames] == [identity[id(frame)][1] for frame in frames], (
            rung, scenario, tick)
    return True


def main(executable):
    rows = iter(subprocess.check_output([executable], text=True).splitlines())
    built = sum(compare(rows, rung, scenario) for rung in range(-1, 36) for scenario in range(7))
    assert next(rows, None) is None
    assert 0 < built < 259
    print(f"PASS: 259 What Happens Next clip cases ({built} playable)")


if __name__ == "__main__":
    main(sys.argv[1])
