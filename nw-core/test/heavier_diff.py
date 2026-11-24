"""Compare Heavier's screened deals, motion, reference answers, and audio cues."""
from random import Random
import subprocess
import sys

from crane_diff import compare
from neural_workshop import heavier as model


def replay(rows, rung, seed, policy):
    where = rung, seed, policy
    rng = Random(seed)
    try:
        deal = model.deal(rung, rng=rng)
    except RuntimeError:
        compare(rows, "case", (*where, 0), where)
        return 0
    compare(rows, "case", (*where, 1), where)
    level = deal.level
    compare(rows, "level", (level.rung, level.crates, level.ratio, level.boards, level.seconds, level.weak,
                            int(level.floors), int(level.slippery), int(level.sizes), rng.random()), where)
    for board in deal.boards:
        compare(rows, "board", (int(board.ask == model.SLIPPERY), board.answer, board.force), where)
        for mass, grip, size in zip(board.mass, board.grip, board.size):
            compare(rows, "crate", (mass, grip, size), where)
    run = model.Run(deal)
    ticks = 0
    while run.result is None:
        if policy == 0:
            ports = model.autopilot(run)
            port = ports[0] if ports else -1
        elif policy == 1:
            port = 0
        else:
            port = model.PICK[(run.now.answer + 1) % level.crates]
        model.act(run, port)
        run.step(1 / 30, port)
        result = 0 if run.result is None else (1 if run.result[0] else
                     (3 if run.result[1].startswith("Out of time") else 2))
        compare(rows, "tick", (port, run.t, run.board, run.started, run.right, result, len(run.notes)),
                (*where, ticks))
        for values in zip(run.x, run.v, run.pushed):
            compare(rows, "motion", values, (*where, ticks))
        ticks += 1
    assert result == (1, 3, 2)[policy]
    if policy == 1:
        assert any(note.voice == 0 for note in run.notes)
    for note in run.notes:
        compare(rows, "cue", (note.t, note.dur, note.freq, note.voice, note.gain), where)
    return ticks


def main(binary):
    rows = iter(subprocess.check_output([binary], text=True).splitlines())
    cases = [(rung, seed, 0) for rung in (-1, 2, 3, 4, 6, 7, 9, 10, 12, 13, 16, 25, 30, 90)
             for seed in (0, 17, 107)]
    cases.extend(((1, 17, 1), (7, 17, 2)))
    counts = [replay(rows, *case) for case in cases]
    assert all(counts)
    assert next(rows, None) is None
    print(f"PASS: {len(cases)} Heavier replays matched Python across {sum(counts):,} ticks")


if __name__ == "__main__":
    main(sys.argv[1])
