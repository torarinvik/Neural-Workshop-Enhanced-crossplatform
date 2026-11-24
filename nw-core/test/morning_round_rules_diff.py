"""Replay Morning Round's generated rulebooks and street rejection rules."""
from random import Random
import subprocess
import sys

from morning_round_diff import compare, morninground as model


def nodes(rule, out):
    op, *args = rule
    code = ("atom", "not", "and", "or", "opp", "alt", "same").index(op)
    left = right = 0
    if op == "atom":
        left = (model.BASIC + model.NUMBERS + ("church", "sign")).index(args[0])
    elif args:
        left = nodes(args[0], out)
        if len(args) > 1:
            right = nodes(args[1], out)
    index = len(out)
    out.append((code, left, right))
    return index


def main(binary):
    rows = iter(subprocess.check_output([binary], text=True).splitlines())
    accepted = rejected = 0
    for rung in (1, 4, 5, 6, 7, 9, 10, 11, 12, 13, 16, 20, 25, 30, 40, 60, 100):
        compare(rows, "rung", (rung,), rung)
        draw = Random(17)
        for sample in range(75):
            where = (rung, sample)
            street = model.build(model.grade(rung), draw)
            compare(rows, "valid", (int(street is not None),), where)
            if street is None:
                rejected += 1
                continue
            accepted += 1
            compare(rows, "street", (street.papers, street.seconds, len(street.things)), where)
            for value in street.active:
                compare(rows, "active", (value,), where)
            for h, want in zip(street.houses, street.want):
                compare(rows, "house", (int(h.sign), int(want)), where)
            for rule in street.deck:
                flat = []
                nodes(rule, flat)
                compare(rows, "rule", (len(flat),), where)
                for node in flat:
                    compare(rows, "node", node, where)
                for vote in model.truth(rule, street.houses, street.landmarks):
                    compare(rows, "vote", (int(vote),), where)
            for t in street.things:
                compare(rows, "thing", (*t[:3], ("cone", "bin", "car", "cyclist").index(t.kind), t.v), where)
        compare(rows, "draw", (draw.random(),), rung)
    assert next(rows, None) is None
    print(f"PASS: {accepted + rejected} Morning Round candidates match Python ({accepted} accepted, {rejected} rejected)")


if __name__ == "__main__":
    main(sys.argv[1])
