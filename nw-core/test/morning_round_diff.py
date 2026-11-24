"""Compare Morning Round's seeded roads, house attributes, and traffic."""
from random import Random
import subprocess
import sys

from crane_diff import compare
from neural_workshop import morninground


def main(binary):
    rows = iter(subprocess.check_output([binary], text=True).splitlines())
    count = 0
    for rung in (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 17, 24, 30, 60, 100):
        for seed in (0, 17, 42):
            draw = Random(seed)
            where = (rung, seed)
            compare(rows, "case", where, where)
            g = morninground.grade(rung)
            mode = ("marked", "told", "sign", "hidden").index(g.mode)
            compare(rows, "rung", (g.rung, mode, g.deck, g.atoms, len(g.pool), int(g.state), g.blocks,
                                    g.houses, g.speed, g.clutter, int(g.movers), int(g.memorise),
                                    g.brief, g.slack), where)
            houses, blocks, length = morninground._houses(g, draw)
            compare(rows, "layout", (len(houses), length), where)
            for h in houses:
                compare(rows, "house", (*h[:5], morninground.DOORS.index(h.door), *h[6:]), where)
            for start, end in blocks:
                landmark = draw.choice(morninground.LANDMARKS)
                compare(rows, "block", (start, end, morninground.LANDMARKS.index(landmark)), where)
            obstacles = morninground._things(g, length, draw)
            compare(rows, "count", (len(obstacles),), where)
            for t in obstacles:
                compare(rows, "thing", (*t[:3], ("cone", "bin", "car", "cyclist").index(t.kind), t.v), where)
            compare(rows, "draw", (draw.random(),), where)
            count += 1
    assert next(rows, None) is None
    print(f"PASS: {count} Morning Round street layouts, traffic, and RNG draws match Python")


if __name__ == "__main__":
    main(sys.argv[1])
