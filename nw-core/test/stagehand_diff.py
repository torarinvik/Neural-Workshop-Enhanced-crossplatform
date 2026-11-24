"""Compare seeded Stagehand shows and reference performances."""
from pathlib import Path
import subprocess
import sys

from safecracker_diff import check

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced"))
from neural_workshop import stagehand

KINDS = ("move", "key", "spot")
WAITS = ("", "bell", "actor", "drum")


def mark_code(mark):
    return mark[0] * stagehand.ROWS + mark[1]


def compare_show(rows, show, case):
    check(next(rows), [len(show.props), len(show.lines), len(show.cuts), show.seconds], case)
    assert int(next(rows)) == show.seed, case
    for kind, mark in zip(show.props, show.marks):
        check(next(rows), [kind, mark_code(mark)], case)
    for line in show.lines:
        check(next(rows), [KINDS.index(line.kind), line.prop, mark_code(line.mark), line.key,
                           WAITS.index(line.wait), line.count, line.decoy, line.to, line.via], case)
        assert next(rows) == line.text, (case, line)
    for cut in show.cuts:
        check(next(rows), cut, case)


def replay(rows, show, case):
    run = stagehand.Run(show)
    frame = states = 0
    while run.result is None:
        ports = stagehand.autopilot(run)
        port = ports[0] if ports else -1
        if port >= 0:
            stagehand.act(run, port)
        run.step(1 / 60)
        if frame % 61 == 0 or run.result is not None:
            check(next(rows), [frame, port, int(run.result is not None), run.line_no, run.cam,
                               -1 if run.drag is None else run.drag, -1 if run.lit is None else run.lit,
                               sum(1 << i for i, on in enumerate(run.on) if on), run.t,
                               -1 if run.opens is None else run.opens, run.due, run.hand.x, run.hand.y,
                               *run.actor, *run.held_at], (case, frame))
            check(next(rows), list(map(mark_code, run.at)), (case, frame, "marks"))
            states += 1
        frame += 1
    assert next(rows).split() == ["cues", str(len(run.notes))], case
    for note in run.notes:
        check(next(rows), [note.t, note.dur, note.voice, note.freq, note.gain, note.seed], case)
    return states, len(run.notes)


def main(executable):
    rows = iter(subprocess.check_output([executable], text=True, timeout=120).splitlines())
    shows = states = cues = 0
    for header in rows:
        rung, seed, valid = map(int, header.split())
        case = rung, seed
        show = stagehand.deal(rung, seed)
        assert valid, case
        compare_show(rows, show, case)
        samples, notes = replay(rows, show, case)
        shows += 1
        states += samples
        cues += notes
    assert shows == 60
    print(f"PASS: {shows} Stagehand shows against Python, {states} performance states and {cues} audio cues")


if __name__ == "__main__":
    main(sys.argv[1])
