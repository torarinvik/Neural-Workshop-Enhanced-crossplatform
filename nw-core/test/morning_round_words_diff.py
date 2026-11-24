"""Compare the original wording for each generated Morning Round rule."""
from random import Random
import subprocess
import sys

from morning_round_diff import morninground as model


def main(binary):
    rows = iter(subprocess.check_output([binary], text=True).splitlines())
    count = 0
    for rung in (1, 4, 6, 10, 12, 16, 25, 40, 100):
        draw = Random(17)
        for index in range(75):
            street = model.build(model.grade(rung), draw)
            if street is None:
                continue
            for rule in street.deck:
                assert next(rows) == model.say(rule), (rung, index, rule)
                count += 1
    assert next(rows, None) is None
    print(f"PASS: {count} Morning Round rulebook descriptions match Python")


if __name__ == "__main__":
    main(sys.argv[1])
