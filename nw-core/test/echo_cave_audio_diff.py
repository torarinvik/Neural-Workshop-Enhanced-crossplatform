"""Compare live Echo Cave stereo output to the Python synthesizer."""
from pathlib import Path
from random import Random
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced"))
from neural_workshop import drshape, echocave


def expected_windows():
    patches = [drshape.make_patch(name, Random(i + 1)) for i, name in enumerate(echocave.PATCHES)]
    for rung in (1, 10, 20):
        run = echocave.Run(echocave.deal(rung, 17))
        for index in range(1320):
            begin = run.t
            ports = echocave.autopilot(run)
            if echocave.CLICK in ports:
                run.click()
            run.step(1 / 60, [port for port in ports if port != echocave.CLICK])
            if index % 9 == 0:
                yield drshape.synth(run.notes, begin, run.t, patches)
            if run.result:
                break


if __name__ == "__main__":
    actual = subprocess.check_output([sys.argv[1]], text=True, timeout=30).splitlines()
    expected = list(expected_windows())
    assert len(actual) == len(expected)
    for index, (line, pcm) in enumerate(zip(actual, expected)):
        assert bytes.fromhex(line) == pcm, index
    print(f"Echo Cave matched {len(expected)} live Python PCM windows byte for byte")
