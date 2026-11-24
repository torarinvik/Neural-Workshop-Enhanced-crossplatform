"""Compare Cricket Hunt's live sound with crickethunt.mix, byte for byte."""
from pathlib import Path
from random import Random
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced"))
from neural_workshop import crickethunt as model


def check(binary):
    rows = iter(subprocess.check_output([binary], text=True).splitlines())
    windows = loud = 0
    for rung, seed, grabs in ((1, 17, False), (4, 17, False), (8, 17, False), (10, 17, False), (2, 3, True)):
        run = model.Run(model.deal(rung, rng=Random(seed)))
        n = 0
        while run.result is None:
            ports = model.autopilot(run)
            port = ports[0] if ports else -1
            if grabs:
                port = model.GRAB if n % 20 == 10 else model.RIGHT
            if port == model.GRAB:
                model.act(run, port)
            run.step(1 / 30.0, None if port in (-1, model.GRAB) else port)
            n += 1
        marker, *values = next(rows).split()
        assert marker == "run" and values[:3] == [str(rung), str(seed), str(int(grabs))], values
        assert float(values[4]) == run.t and int(values[5]) == len(run.notes), (values, run.t)
        starts = [(-0.15, 0.1), (0.0, 0.1), (0.37, 0.25), (run.t / 2.0, 0.1)] + \
            [(note.t - 0.05, 0.4) for note in run.notes] + [(run.t - 0.1, 0.5), (run.t + 0.2, 0.1), (1.0 / 3.0, 1.0)]
        for start, width in starts:
            marker, a, b = next(rows).split()
            assert marker == "audio" and float(a) == start and float(b) == width, (a, b, start, width)
            expected = model.mix(run, start, start + width)
            actual = bytes.fromhex(next(rows))
            assert actual == expected, (rung, seed, start, len(actual), len(expected),
                                        next((k for k in range(min(len(actual), len(expected))) if actual[k] != expected[k]), None))
            windows += 1
            loud += any(expected)
    assert next(rows, None) is None
    print(f"PASS: {windows} windows ({loud} with sound) of Cricket Hunt's gated chirps, panned and brightened as they "
          f"are heard, the hum and its noise, and the notes byte for byte match crickethunt.mix")


if __name__ == "__main__":
    check(sys.argv[1])
