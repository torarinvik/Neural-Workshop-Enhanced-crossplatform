"""Compare the seven seeded Field Manual voices and live orders with Python."""
from random import Random
import subprocess
import sys

from field_manual_diff import fieldmanual
from neural_workshop import drshape


def windows(patches):
    notes = [drshape.Note(0.6 * voice, 0.15, 330.0 + 110.0 * voice, 0.3, 0.3,
                          0.4, 0.4, 0.8, voice, voice + 1, -1)
             for voice in range(7)]
    for index in range(48):
        begin = index * 0.1 - 0.04
        yield drshape.synth(notes, begin, begin + 0.099, patches)
    for rung, seed in ((13, 1), (16, 2), (25, 4)):
        job = fieldmanual._build(fieldmanual.grade(rung), Random(seed))
        run = fieldmanual.Run(job)
        frame = 0
        while run.result is None:
            begin = run.t
            ports = fieldmanual.autopilot(run)
            port = ports[0] if ports else None
            if port in fieldmanual.EVENTS:
                fieldmanual.act(run, port)
                port = None
            run.step(1 / 60, port)
            if frame % 7 == 0:
                yield drshape.synth(run.notes, begin, begin + 1 / 60, patches)
            frame += 1


if __name__ == "__main__":
    patches = [drshape.make_patch(name, Random(k + 1)) for k, name in enumerate(fieldmanual.PATCHES)]
    lines = iter(subprocess.check_output([sys.argv[1]], text=True, timeout=60).splitlines())
    count = 0
    for count, pcm in enumerate(windows(patches), 1):
        native = bytes.fromhex(next(lines))
        assert native == pcm, (count, len(native), len(pcm))
    assert next(lines, None) is None
    print(f"Field Manual matched {count} stereo windows byte for byte across all seven voices")
