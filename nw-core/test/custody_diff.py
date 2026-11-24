#!/usr/bin/env python3
"""Differential harness: tasks/custody.elisa vs the real
neural_workshop/custody.py.

Drives the ACTUAL module: GRADES, `gap`, `generate`, `fresh_boxes` and a
twelve-step belt replay through `step_belt`.

The belt is the real test. Jams are unpicked by repeated passes over the riding
boxes sorted by slot DESCENDING, with a once-per-step guard so a box cannot be
carried round twice in one step -- the reference measured a box crossing five
or six slots without it, which put it past the claw every time. Getting the
sort direction, the pass loop or the guard wrong still shuffles boxes around
plausibly, so only a per-step trace of every box catches it.

The stream order is four shuffles and one randrange off one stream:
placement's shuffle, the Core's randrange, then free/places/looks in
fresh_boxes. `places` is `sorted(free[:boxes])` and is then shuffled AGAIN --
the first shuffle picks which slots, the sort orders them, and the second
decides which box gets which.
"""
from pathlib import Path
import random
import subprocess
import sys

APP = str(Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced")
sys.path.insert(0, APP)

from neural_workshop import custody as ref  # noqa: E402

KIND_ID = {ref.CHARGER: 0, ref.COOLER: 1, ref.PAINTER: 2, None: -1}


def row(*values):
    return ",".join(str(v) for v in values)


def grade_lines(out):
    for level in (-2, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 40):
        g = ref.GRADES[max(0, min(len(ref.GRADES) - 1, level - 1))]
        out.append(row("grd", level, g.boxes, g.looks, g.width, g.chargers,
                       g.coolers, g.painters, g.need_charge, g.max_heat,
                       g.decay, int(g.moving), g.budget))


def gap_lines(out):
    for slots in (10, 12, 14, 16, 18, 20):
        for one in (0, 1, 5, 9, 13):
            for other in (0, 3, 7, 11, 17):
                out.append(row("gap", slots, one, other,
                               ref.gap(one, other, slots)))


def deal_lines(out):
    for level in range(1, 11):
        for seed in (0, 1, 7, 42, 1234):
            rng = random.Random(seed)
            layout = ref.generate(level, rng=rng)
            boxes = ref.fresh_boxes(layout, rng)
            flat = [KIND_ID[ref.machine_at(layout, s)]
                    for s in range(layout.slots)]
            for box in boxes:
                flat += [box.look, box.slot]
            out.append(row("deal", level, seed, layout.slots, layout.bay,
                           layout.core, *flat))


def belt_lines(out):
    for level in (3, 5, 6, 7, 9, 10):
        for seed in (1, 7, 1234):
            rng = random.Random(seed)
            layout = ref.generate(level, rng=rng)
            boxes = ref.fresh_boxes(layout, rng)
            flat = []
            for _step in range(12):
                ref.step_belt(boxes, layout)
                for box in boxes:
                    flat += [box.slot, box.look, box.charge]
            out.append(row("belt", level, seed, *flat))


def claw_lines(out):
    """Exercise the mutable claw/objective half of the task."""
    for level in (1, 4, 5, 10):
        for seed in (0, 7, 1234):
            rng = random.Random(seed)
            layout = ref.generate(level, rng=rng)
            boxes = ref.fresh_boxes(layout, rng)
            values = [layout.core, ref.rivals(boxes, layout),
                      int(ref.rivals_expected(layout.boxes, layout.looks) * 1000000),
                      len(ref.loose(boxes))]
            box_slot = boxes[0].slot
            values += [box_slot, boxes.index(ref.box_at(boxes, box_slot)),
                       ref.grab(boxes, box_slot).latent,
                       -1 if ref.box_at(boxes, box_slot) is None else
                       ref.box_at(boxes, box_slot).latent,
                       ref.potential(boxes[0], box_slot, layout)]

            occupied = boxes[1].slot if len(boxes) > 1 else -1
            values.append(int(len(boxes) > 1 and
                             ref.put_down(boxes[0], boxes, occupied, layout)))

            machines = [m for m in layout.machines]
            target = machines[0].slot if machines else layout.bay
            next_target = ref.next_target(boxes[0], layout, box_slot)
            values += [next_target, target,
                       KIND_ID[ref.machine_at(layout, target)],
                       int(ref.put_down(boxes[0], boxes, target, layout)),
                       boxes[0].charge, boxes[0].heat, boxes[0].look,
                       int(boxes[0].stalled), int(ref.wanted(boxes[0], layout)),
                       ref.potential(boxes[0], target, layout)]
            grabbed_again = ref.grab(boxes, target)
            if grabbed_again is None:
                values += [-1, 0]
            else:
                values += [grabbed_again.latent,
                           int(ref.put_down(grabbed_again, boxes,
                                            layout.bay, layout))]
            values += [int(boxes[0].delivered), boxes[0].slot,
                       ref.rivals(boxes, layout)]
            for kind in (ref.CHARGER, ref.COOLER, ref.PAINTER):
                slots = ref.slots_of(layout, kind)
                values += [len(slots), slots[0] if slots else -1]
            out.append(row("claw", level, seed, *values))


def python_lines():
    out = []
    grade_lines(out)
    gap_lines(out)
    deal_lines(out)
    belt_lines(out)
    claw_lines(out)
    return out


def main():
    got = [ln for ln in subprocess.run([sys.argv[1]], capture_output=True,
                                       text=True, check=True
                                       ).stdout.splitlines() if ln.strip()]
    want = python_lines()
    if len(got) != len(want):
        print(f"FAIL: line count {len(got)} vs {len(want)}")
        for g, w in list(zip(got, want))[:6]:
            print(f"  elisa:  {g[:180]}\n  python: {w[:180]}")
        return 1
    bad = [(i, g, w) for i, (g, w) in enumerate(zip(got, want)) if g != w]
    for i, g, w in bad[:6]:
        print(f"MISMATCH line {i}\n  elisa:  {g[:240]}\n  python: {w[:240]}")
    if bad:
        print(f"FAIL: {len(bad)}/{len(want)} mismatches")
        return 1
    print(f"PASS: {len(want)} cases identical")
    return 0


if __name__ == "__main__":
    sys.exit(main())
