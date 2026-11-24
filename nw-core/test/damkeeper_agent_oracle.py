"""Build deterministic stepped Dam Keeper replays from the Python model."""
import json
import math
from pathlib import Path
import random
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced"))
from neural_workshop import damkeeper


FRAME_HZ = 10
SEED = 222


def replay(use_pilot):
    run = damkeeper.Run(damkeeper.deal(1, rng=random.Random(SEED)))
    actions = []
    now = 0.0
    for tick in range(1, 1001):
        ports = damkeeper.autopilot(run) if use_pilot else ([4] if tick == 1 else [])
        if ports:
            actions.append([tick, ports[0]])
            damkeeper.act(run, ports[0])
        last = now
        now += 1 / FRAME_HZ
        dt = min(0.1, now - last)
        substeps = max(1, math.ceil(dt / (1 / 30)))
        for _ in range(substeps):
            run.step(dt / substeps)
            if run.result is not None:
                won, message = run.result
                return {"actions": actions, "ticks": tick, "scalar": 1 if won else -1, "verdict": message}
    raise AssertionError("The Python valley did not settle")


def fixture():
    return {"frameHz": FRAME_HZ, "seed": SEED, "runs": [replay(False), replay(True)]}


if __name__ == "__main__":
    print(json.dumps(fixture()))
