"""Compare Dr Shape's difficulty ladder and turtle geometry with the original."""
import math
from pathlib import Path
import random
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced"))
from neural_workshop import drshape

FAMILIES = ("polygon", "star", "spiral", "space", "coil", "branch", "curve", "prism", "pyramid", "solid")
OPS = ("F", "Y", "P", "R", "[", "]")


def compare_floats(actual, expected, where):
    assert len(actual) == len(expected) and all(
        math.isclose(float(a), b, abs_tol=1e-12, rel_tol=0)
        for a, b in zip(actual, expected)
    ), (where, actual, expected)


def compare_form(lines, form, where):
    assert tuple(map(int, next(lines).split())) == (len(form.segs), len(form.faces)), where
    for tint, (a, b) in zip(form.tints, form.segs):
        row = next(lines).split()
        assert int(row[0]) == tint, where
        compare_floats(row[1:], a + b, where)
    for vertices, tint in form.faces:
        assert tuple(map(int, next(lines).split())) == (len(vertices), tint), where
        for point in vertices:
            compare_floats(next(lines).split(), point, where)


def compare(binary):
    with subprocess.Popen([binary], stdout=subprocess.PIPE, text=True) as process:
        lines = iter(process.stdout)
        for rung in range(-2, 55):
            g = drshape.grade(rung)
            row = next(lines).split()
            assert tuple(map(int, row[:13])) == (
                g.rung, g.candidates, ("none", "plane", "space").index(g.turn),
                g.colours, len(g.instruments), g.keep, g.mirror, g.near, g.echo_key,
                g.echo_voice, g.floor, g.each_side, g.tumble + 2 * g.chorus,
            ), (rung, row, g)
            compare_floats(row[13:], (g.overload, g.wild, g.choose, g.tempo), rung)
            assert tuple(map(int, next(lines).split())) == tuple(map(FAMILIES.index, g.families))
            modes = next(lines).split()
            assert tuple(map(int, modes[::2])) == tuple(drshape.MODES.index(mode) for mode, _ in g.modes)
            compare_floats(modes[1::2], [weight for _, weight in g.modes], rung)
            rng = random.Random(17)
            assert tuple(map(int, next(lines).split())) == tuple(
                drshape.MODES.index(drshape._pick_mode(g, rng)) for _ in range(64)
            )

        for family in FAMILIES[:6]:
            for seed in range(40):
                rng = random.Random(seed)
                base = drshape.make_program(family, rng)
                for bent, program in enumerate((base, drshape.bend(base, rng))):
                    where = (family, seed, bent)
                    assert int(next(lines)) == len(program), where
                    for op in program:
                        kind, value = next(lines).split()
                        assert OPS[int(kind)] == op[0], where
                        compare_floats([value], [op[1] if len(op) > 1 else 0.0], where)
                    strokes = drshape.trace(program)
                    assert int(next(lines)) == len(strokes), where
                    for a, b in strokes:
                        compare_floats(next(lines).split(), a + b, where)
        for family in FAMILIES[6:]:
            for seed in range(40):
                rng = random.Random(seed)
                base = drshape.draw_params(family, rng)
                for bent, params in enumerate((base, drshape.nudge(family, base, rng))):
                    where = (family, seed, bent)
                    form = drshape.build(family, params)
                    compare_form(lines, form, where)
                style = (None, "runs", "cycle", "random")[seed % 4]
                painted = drshape.colour(form, 3, rng, style)
                compare_form(lines, painted, (family, seed, style))
                compare_form(lines, drshape.recoloured(painted, rng), (family, seed, "recoloured"))
        for rung in (1, 4, 7, 11, 16, 19, 30):
            level = drshape.grade(rung)
            for mode in drshape.MODES[:4]:
                for seed in range(4):
                    where = (rung, mode, seed)
                    expected = drshape._build(level, random.Random(seed), seed, mode)
                    count, answer = map(int, next(lines).split())
                    if expected is None:
                        assert count == 0, where
                        continue
                    assert (count, answer) == (len(expected.candidates), expected.answer), where
                    compare_form(lines, expected.form, where)
                    compare_floats(next(lines).split(), sum(expected.view, ()), where)
                    for card in expected.candidates:
                        compare_form(lines, card.form, where)
                        compare_floats(next(lines).split(), sum(card.view, ()), where)
                        compare_floats(next(lines).split(), (*card.spin, card.size, card.depth, card.side), where)
                    notes, deadlines, end = drshape.sing(expected.form, expected.view, 0.4,
                        level.tempo, lambda tint, _: tint + 3, pan_shift=0.3, pan_width=0.8,
                        gain=0.55, transpose=-7, who=2, distance=5.3)
                    compare_floats(next(lines).split(), (len(notes), end), where)
                    for note, deadline in zip(notes, deadlines):
                        compare_floats(next(lines).split(), (*note, deadline), where)
        for rung in range(20, 26):
            level = drshape.grade(rung)
            for mode in drshape.MODES[4:]:
                for seed in range(6):
                    where = (rung, mode, seed)
                    scene = drshape._build_scene(level, mode, random.Random(seed), seed)
                    count, answer = map(int, next(lines).split())
                    if scene is None:
                        assert count == 0, where
                        continue
                    assert (count, answer) == (len(scene.candidates), scene.answer), where
                    compare_floats(next(lines).split(), (len(scene.things), scene.look), where)
                    for place in scene.layout:
                        compare_floats(next(lines).split(), place, where)
                    compare_floats(next(lines).split(), sum(drshape.eye(scene.look)[1], ()), where)
                    for i, thing in enumerate(scene.things):
                        compare_form(lines, thing.form, where)
                        compare_floats(next(lines).split(), sum(thing.turn, ()), where)
                        _, lift = drshape.rest(thing.form, thing.turn, drshape.OBJECT)
                        compare_floats(next(lines).split(), (lift,), where)
                        if i < 3:
                            _, x, z = scene.layout[i]
                            compare_floats(next(lines).split(), drshape.seen_from(scene.look, (x, lift, z)), where)
                    for card in scene.candidates:
                        compare_floats(next(lines).split(), (card.look,), where)
                        for place in card.layout:
                            compare_floats(next(lines).split(), place, where)
        assert next(lines, None) is None
        assert process.wait() == 0
    print("PASS: Dr Shape Python parity across 57 grades, 1,120 forms, 112 candidate and note replays, and 72 platform scenes")


if __name__ == "__main__":
    compare(sys.argv[1])
