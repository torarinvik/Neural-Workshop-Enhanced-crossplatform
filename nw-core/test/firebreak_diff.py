"""Compare Firebreak's seeded lands with the Python generator."""
from math import isclose
from pathlib import Path
from random import Random
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced"))
from neural_workshop import firebreak


def compare(rows, name, values, where, tolerance=0.0):
    label, *fields = next(rows).split()
    assert label == name and len(fields) == len(values), (where, label, fields, values)
    for field, value in zip(fields, values):
        if isinstance(value, float):
            assert isclose(float(field), value, rel_tol=0.0, abs_tol=tolerance), (where, name, field, value)
        else:
            assert int(field) == value, (where, name, field, value)


rows = iter(subprocess.check_output([sys.argv[1]], text=True).splitlines())
for rung in (0, 1, 4, 7, 10, 13, 16, 19, 20, 25, 30, 60):
    for index in range(5):
        seed = 17 + index * 31337
        land = firebreak.deal(rung, rng=Random(seed)) if index % 2 else firebreak.deal(rung, seed=-seed)
        where = rung, seed
        compare(rows, "grade", land.level, where)
        shift = land.winds[1] if land.level.shift else (0.0, 0.0)
        compare(rows, "wind", (land.winds[0][1], *shift), where, tolerance=6e-14)
        compare(rows, "supply", (land.shovels, firebreak._reaches_town(land)), where)
        for fire in land.fires:
            compare(rows, "fire", (fire,), where)
        for cell in land.town:
            compare(rows, "town", (cell,), where)
        for cell, values in enumerate(zip(land.terrain, land.rough, land.ember_draw)):
            compare(rows, "cell", values, (*where, cell))
assert next(rows, None) is None
print("PASS: 60 Firebreak lands and 34,200 terrain cells match Python, including fires, town, wind, and shovels")
