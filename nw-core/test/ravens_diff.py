#!/usr/bin/env python3
"""Differential harness for tasks/ravens.elisa against the ravens package.

The whole package -- geometry, palette, figures, layouts, rules, matrix --
imports without pyglet, so nothing is lifted or transcribed here: the reference
is imported and run as itself. The only thing reached into is `matrix._explain`,
which is wrapped to record WHICH rule ran on which attribute of which component
alongside the sentence it builds, because the port hands back the fact and
leaves the sentence to the shell.

Values cross the boundary as integers. A rule's rungs are ladder elements on
both sides; the logic rule's frozensets of places are bitmasks, which is exact
because nothing ever walks one -- see the module note in tasks/ravens.elisa.
"""
import math
import random
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "original-neural-workshop-enhanced"))

from neural_workshop.ravens import figures, geometry, layouts, matrix, palette, rules  # noqa: E402

SHAPE_ID = {name: index for index, name in enumerate(figures.SHAPES)}
FILL_ID = {'white': 0, 'grey-light': 1, 'grey-mid': 2, 'grey-dark': 3,
           'black': 4, 'yellow': 5, 'sky': 6, 'vermilion': 7, 'blue': 8}
ATTR_ID = {'shape': 0, 'size': 1, 'colour': 2, 'number': 3, 'angle': 4}
OPS = ('or', 'and', 'xor')

LAYOUT_ORDER = (layouts.CENTRE, layouts.LEFT_RIGHT, layouts.UP_DOWN,
                layouts.INSIDE_OUTSIDE, layouts.GRID_FOUR, layouts.GRID_NINE,
                layouts.TRIPTYCH)
LAYOUT_ID = {one.name: index for index, one in enumerate(LAYOUT_ORDER)}

LADDERS = (figures.SIZES, matrix.COARSE_SIZES, matrix.FINE_SIZES,
           layouts.LATTICE_SIZES)

ALLOW = {'progression': 1, 'distribute three': 2, 'arithmetic': 4,
         'second order': 8, 'constant': 16, 'logic': 32}


def kind_of(rule):
    if isinstance(rule, rules.Progression):
        return 1, rule.step
    if isinstance(rule, rules.DistributeThree):
        return 2, 0
    if isinstance(rule, rules.Arithmetic):
        return 3, rule.sign
    if isinstance(rule, rules.SecondOrder):
        return 4, rule.delta
    if isinstance(rule, rules.Logic):
        return 5, OPS.index(rule.op)
    return 0, 0


STRUCTURED = []
_real_explain = matrix._explain


def _spy_explain(layout, dealt):
    """`_explain`'s own walk, recording the fact under each sentence."""
    del STRUCTURED[:]
    for part, attributes in enumerate(dealt):
        for attribute in attributes:
            if isinstance(attribute.rule, rules.Constant):
                continue
            kind, param = kind_of(attribute.rule)
            STRUCTURED.append((part, ATTR_ID[attribute.name], kind, param))
    return _real_explain(layout, dealt)


matrix._explain = _spy_explain


def micro(value):
    return int(round(value * 1000000.0))


def mask_of(held):
    total = 0
    for place in held:
        total |= 1 << place
    return total


def tee():
    """A concave outline, so ear clipping is exercised and not merely the fan."""
    return [geometry.Point(x, y) for x, y in
            ((0.0, 0.0), (6.0, 0.0), (6.0, 2.0), (4.0, 2.0),
             (4.0, 6.0), (2.0, 6.0), (2.0, 2.0), (0.0, 2.0))]


def outline_row(tag, spec, outline):
    row = [tag, spec, len(outline)]
    low_x, low_y, high_x, high_y = geometry.bounds(outline)
    row.extend((micro(low_x), micro(low_y), micro(high_x), micro(high_y)))
    row.append(micro(geometry.signed_area(outline)))
    row.append(1 if geometry.is_convex(outline) else 0)
    cut = geometry.triangulate(outline)
    row.append(len(cut))
    for triangle in cut:
        for point in triangle:
            row.extend((micro(point.x), micro(point.y)))
    for point in outline:
        row.extend((micro(point.x), micro(point.y)))
    return row


def figure_row(tag, spec, figure):
    return [tag, spec, SHAPE_ID[figure.shape], micro(figure.centre.x),
            micro(figure.centre.y), micro(figure.radius),
            FILL_ID[figure.fill.name], figure.angle, figure.component]


def reference():
    out = []

    # --- geometry ---------------------------------------------------------
    for spec in range(6):
        width = 1.0 + spec * 0.5
        height = 2.0 - spec * 0.25
        segments = 4 + spec * 3
        out.append(outline_row("ellipse", spec,
                               geometry.ellipse_outline(width, height, segments)))
    out.append(outline_row("ellipse", 6,
                           geometry.ellipse_outline(3.0, 3.0)))
    out.append(outline_row("tee", 0, tuple(tee())))
    out.append(outline_row("tee", 1, tuple(reversed(tee()))))
    for spec in range(6):
        moved = geometry.transformed(tee(), 0.5 + spec * 0.3, spec * 37,
                                     geometry.Point(spec * 1.5, -spec))
        out.append(outline_row("moved", spec, moved))

    # --- the palettes -----------------------------------------------------
    for which, pool in enumerate(palette.PALETTES):
        row = ["palette", which, len(pool.fills)]
        for fill in pool.fills:
            row.append(FILL_ID[fill.name])
            row.extend(fill.color)
        out.append(row)

    # --- the figures ------------------------------------------------------
    for shape in figures.SHAPES:
        ladder = figures.turn_ladder(shape)
        row = ["turns", SHAPE_ID[shape], figures.POLYGONS[shape][0],
               micro(figures.POLYGONS[shape][1]), len(ladder)]
        row.extend(ladder)
        out.append(row)
    for shape in figures.SHAPES:
        for spec in range(3):
            centre = geometry.Point(0.4 + spec * 0.1, 0.6 - spec * 0.15)
            angle = (0, 37, 90)[spec]
            outline = figures.polygon(shape, 0.3 + spec * 0.05, centre, angle)
            out.append(outline_row("polygon", SHAPE_ID[shape] * 3 + spec,
                                   outline))

    # --- the size ladders -------------------------------------------------
    for which, ladder in enumerate(LADDERS):
        out.append(["ladder", which, len(ladder)]
                   + [micro(one) for one in ladder])

    # --- the layouts ------------------------------------------------------
    for which, layout in enumerate(LAYOUT_ORDER):
        row = ["layout", which, len(layout.components)]
        for component in layout.components:
            row.extend((len(component.slots), len(component.counts),
                        1 if component.varies_in_number else 0,
                        -1 if component.sizes is None
                        else LADDERS.index(component.sizes)))
            for slot in component.slots:
                row.extend((micro(slot.centre.x), micro(slot.centre.y),
                            micro(slot.radius)))
            row.extend(component.counts)
            for count in component.counts:
                places = component.places(count)
                row.append(len(places))
                for slot in places:
                    row.append(component.slots.index(slot))
        out.append(row)

    # --- the rules --------------------------------------------------------
    for across in (2, 3, 4):
        for length in range(1, 10):
            ladder = tuple(range(length))
            for allow_arithmetic in (False, True):
                for named in (None, ('progression',),
                              ('progression', 'distribute three'),
                              ('progression', 'distribute three', 'arithmetic')):
                    choices = rules.rule_choices(ladder, allow_arithmetic,
                                                 named, across)
                    row = ["choices", across, length,
                           1 if allow_arithmetic else 0,
                           -1 if named is None
                           else sum(ALLOW[one] for one in named),
                           len(choices)]
                    for rule in choices:
                        kind, param = kind_of(rule)
                        row.extend((kind, param, rule.across))
                    out.append(row)

    made = [(rules.Progression, 1), (rules.Progression, -1),
            (rules.Progression, 2), (rules.Progression, -2),
            (rules.Arithmetic, 1), (rules.Arithmetic, -1),
            (rules.SecondOrder, 1), (rules.SecondOrder, -1)]
    for across in (2, 3, 4):
        for length in (3, 4, 5, 7, 9):
            for seed in range(1, 3):
                for spec, (cls, param) in enumerate(made):
                    rule = cls(param)
                    rule.across = across
                    ladder = tuple(range(1, length + 1))
                    rng = random.Random(across * 1000 + length * 10 + seed)
                    values = rules.apply_rule(rule, ladder, rng)
                    kind, held = kind_of(rule)
                    row = ["rows", across, length, seed, spec, kind, held,
                           rng.randrange(1000000)]
                    for line in values:
                        row.extend(line)
                    out.append(row)
                for spec, cls in enumerate((rules.DistributeThree,
                                            rules.Constant)):
                    rule = cls()
                    rule.across = across
                    ladder = tuple(range(1, length + 1))
                    rng = random.Random(across * 1000 + length * 10 + seed + 7)
                    values = rules.apply_rule(rule, ladder, rng)
                    kind, held = kind_of(rule)
                    row = ["rows", across, length, seed, 8 + spec, kind, held,
                           rng.randrange(1000000)]
                    for line in values:
                        row.extend(line)
                    out.append(row)

    for across in (2, 3, 4):
        for places in (4, 9):
            for op in OPS:
                for seed in range(1, 4):
                    rule = rules.Logic(op)
                    rule.across = across
                    ladder = tuple(range(places))
                    rng = random.Random(across * 100 + places * 10 + seed)
                    values = rules.apply_rule(rule, ladder, rng)
                    row = ["logic", across, places, OPS.index(op), seed,
                           rng.randrange(1000000)]
                    for line in values:
                        for held in line:
                            row.append(mask_of(held)
                                       if isinstance(held, frozenset) else -held - 1)
                    out.append(row)

    # --- the grades -------------------------------------------------------
    for level in range(0, 15):
        grade = matrix.GRADES[max(0, min(len(matrix.GRADES) - 1, level - 1))]
        row = ["grade", level, grade.across, grade.choices, grade.active,
               -1 if grade.rules is None
               else sum(ALLOW[one] for one in grade.rules),
               LADDERS.index(grade.sizes), micro(grade.turn_chance),
               1 if grade.logic else 0, len(grade.layouts)]
        row.extend(LAYOUT_ID[one.name] for one in grade.layouts)
        out.append(row)

    # --- whole puzzles ----------------------------------------------------
    for level in range(1, 13):
        for seed in range(1, 5):
            for pool in (1, 2):
                # `generate` makes its own generator from the seed, so the
                # sweep drives it the way the shell does: one call, one seed.
                built = matrix.generate(
                    level, seed=level * 100 + seed * 10 + pool,
                    palettes=palette.PALETTES[:pool])
                row = ["puzzle", level, seed, pool,
                       LAYOUT_ID[built.layout.name],
                       palette.PALETTES.index(built.palette), built.across,
                       built.answer, len(built.choices), len(STRUCTURED)]
                for fact in STRUCTURED:
                    row.extend(fact)
                for line in built.panels:
                    for panel in line:
                        row.append(len(panel))
                        for figure in panel:
                            row.extend((SHAPE_ID[figure.shape],
                                        micro(figure.centre.x),
                                        micro(figure.centre.y),
                                        micro(figure.radius),
                                        FILL_ID[figure.fill.name],
                                        figure.angle, figure.component))
                for panel in built.choices:
                    row.append(len(panel))
                    for figure in panel:
                        row.extend((SHAPE_ID[figure.shape],
                                    micro(figure.centre.x),
                                    micro(figure.centre.y),
                                    micro(figure.radius),
                                    FILL_ID[figure.fill.name],
                                    figure.angle, figure.component))
                out.append(row)
    return [",".join(str(one) for one in row) for row in out]


def main():
    got = subprocess.run([sys.argv[1]], capture_output=True, text=True, check=True)
    mine = [line for line in got.stdout.splitlines() if line.strip()]
    want = reference()
    if len(mine) != len(want):
        print("MISMATCH line count: elisa %d, python %d" % (len(mine), len(want)))
        for index, (a, b) in enumerate(zip(mine, want)):
            if a != b:
                print("  first differing line %d" % index)
                print("  elisa:  %s" % a[:170])
                print("  python: %s" % b[:170])
                break
        return 1
    for index, (a, b) in enumerate(zip(mine, want)):
        if a != b:
            for at, (x, y) in enumerate(zip(a.split(","), b.split(","))):
                if x != y:
                    print("MISMATCH line %d cell %d: elisa %s, python %s"
                          % (index, at, x, y))
                    break
            print("  elisa:  %s" % a[:170])
            print("  python: %s" % b[:170])
            return 1
    print("PASS: %d cases identical" % len(want))
    return 0


if __name__ == "__main__":
    sys.exit(main())
