"""Compare the seven seeded Loading Dock voices and live orders with Python."""
from random import Random
import subprocess
import sys

from loading_dock_diff import dock
from neural_workshop import drshape


def windows(patches):
    notes = [drshape.Note(0.6 * voice, 0.15, 330.0 + 110.0 * voice, (voice - 3) / 3, (voice - 3) / 3,
                          0.4, 0.4, 0.8, voice, voice + 1, -1)
             for voice in range(7)]
    for index in range(48):
        begin = index * 0.1 - 0.04
        yield drshape.synth(notes, begin, begin + 0.099, patches)
    for rung, seed in ((13, 1), (16, 2), (30, 3)):
        job = dock.deal(rung, seed)
        run = dock.Run(job)
        frame = 0
        while run.result is None:
            begin = run.t
            ports = dock.autopilot(run)
            port = ports[0] if ports else None
            if port in dock.EVENTS:
                dock.act(run, port)
                port = None
            run.step(1 / 60, port)
            if frame % 37 == 0:
                yield drshape.synth(run.notes, begin, begin + 1 / 60, patches)
            frame += 1


if __name__ == "__main__":
    patches = [drshape.make_patch(name, Random(k + 1)) for k, name in enumerate(dock.PATCHES)]
    lines = iter(subprocess.check_output([sys.argv[1]], text=True, timeout=60).splitlines())
    count = 0
    for count, pcm in enumerate(windows(patches), 1):
        native = bytes.fromhex(next(lines))
        assert native == pcm, (count, len(native), len(pcm))
    assert next(lines, None) is None
    print(f"PASS: {count} Loading Dock stereo windows matched byte for byte across all seven voices")
