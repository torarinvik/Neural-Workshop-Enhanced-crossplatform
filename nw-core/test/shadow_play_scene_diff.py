"""Compare the shared Shadow Play display list with Python's projection math."""

import math
from pathlib import Path
import runpy
import subprocess
import sys

REFERENCE = Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced"
sys.path.insert(0, str(REFERENCE))
from neural_workshop import shadowplay as model

Lens = runpy.run_path(str(REFERENCE / "neural_workshop/ui/lens.py"))["Lens"]


def compare(binary):
    lines = iter(subprocess.check_output([binary], text=True).splitlines())

    def near(expected, tolerance=1e-9):
        actual = tuple(map(float, next(lines).split()))
        assert len(actual) == len(expected)
        assert all(math.isclose(a, b, rel_tol=0, abs_tol=tolerance)
                   for a, b in zip(actual, expected)), (actual, expected)

    for rung in (1, 10, 16, 27):
        setup = model.deal(rung, 17)
        for sample in range(4):
            t = sample * 0.6 if sample != 3 else setup.level.seconds
            fitted = sample in (1, 2)
            lens = Lens((0.5, 0.7, 5.6), (0, -0.35, -1), 1, 0, 0)
            lens.fit(((-3.4, 2.4, -3), (3.4, 2.4, -3), (-3.4, -2.2, 1.8), (3.4, -2.2, 1.8)),
                     27.36, 199, 857.28, 369, margin=0.02)
            near((lens.focal, lens.cx, lens.cy))
            target = model.target_at(setup, t)
            rotation = target if fitted else setup.start
            lamp = model.wall_light(setup.level.swing, t)
            copper = []
            for first, last in setup.rod:
                pa, pb = model.app(rotation, first), model.app(rotation, last)
                a, b = lens.see(pa), lens.see(pb)
                direction = model._norm(tuple(y - x for x, y in zip(pa, pb)))
                light = abs(model._dot(direction, lamp))
                copper.append((a[0], a[1], b[0], b[1], (a[2] + b[2]) / 2, light))
            for line in sorted(copper, key=lambda line: -line[4]):
                near(line)
            for layer in range(3):
                colour = (0xffce5a3c, 0xffce5adc, 0x285a32be if fitted else 0x281e2eaf)[layer]
                for floor in (False, True) if setup.level.floor else (False,):
                    for first, last in setup.rod:
                        turn = rotation if layer == 2 else target
                        pa, pb = model.app(turn, first), model.app(turn, last)
                        project = model.on_floor if floor else lambda point: model.on_wall(point, lamp)
                        a, b = lens.see(project(pa)), lens.see(project(pb))
                        width = (lens.size(0.16, a[2]) * 2.2, max(2.0, lens.size(0.16, a[2]) * 0.4),
                                 lens.size(0.11, a[2]))[layer]
                        near((colour, a[0], a[1], b[0], b[1], width), 5e-5)
            near((18, 32 if fitted else 0, int(sample == 2), int(sample == 3)), 0)
    assert next(lines, None) is None
    print("PASS: 16 Shadow Play scenes match Python's camera, outlines, shadows, and copper depth order")


if __name__ == "__main__":
    compare(sys.argv[1])
