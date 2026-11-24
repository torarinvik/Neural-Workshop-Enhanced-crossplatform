"""Replay the Python Loading Dock generator, pilot, and control traces."""
import math
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced"))
from neural_workshop import loadingdock as dock


def check(rows, label, fields, case):
    row = next(rows)
    cells = row.split()
    assert cells[0] == label and len(cells) == len(fields) + 1, (case, row, label, fields)
    for actual, expected in zip(cells[1:], fields):
        if isinstance(expected, float):
            assert math.isclose(float(actual), expected, abs_tol=1e-9, rel_tol=1e-12), (
                case, row, fields)
        else:
            assert int(actual) == expected, (case, row, fields)


def compare_dock(rows, board, case):
    check(rows, "dock", (board.seed, board.seconds), case)
    for colour, tag in board.shelf:
        check(rows, "kind", (3 * colour + tag,), case)
    for truck in board.trucks:
        check(rows, "truck", (dock.CITIES.index(truck.city), truck.bay, truck.arrive, truck.leave), case)
        assert next(rows) == f"order {truck.text}", case
        for need in truck.needs:
            check(rows, "need", need, case)
    for cut in board.cuts:
        check(rows, "cut", cut, case)


def compare_cameras(rows, board, case):
    arrived = [truck for truck in board.trucks if truck.arrive == 0.0]
    orders = [truck.text + ("   (ready: send it)" if i == 0 else "")
              for i, truck in enumerate(arrived)]
    for index, label in enumerate(("CAM 1", "CAM 2", "CAM 3", "OVERHEAD", "BEHIND THE SHELF")):
        labels = []
        row = next(rows)
        while row.startswith("text "):
            labels.append(row[5:])
            row = next(rows)
        assert row == f"camera {index}", case
        assert labels[-5:] == ["F", *orders, label, f"sent 0 of {len(board.trucks)}"], (
            case, index, labels)


def verdict(run):
    if run.result is None:
        return 0, -1
    passed, message = run.result
    if passed:
        return 1, -1
    failures = (
        " did not order that crate",
        " was sent without its order",
        " left without its order",
    )
    for index, truck in enumerate(run.dock.trucks):
        for reason, suffix in enumerate(failures, 2):
            if message == truck.city + suffix:
                return reason, index
    raise AssertionError(run.result)


def wrong_delivery(run, mode):
    truck = run.dock.trucks[0]
    target = run.lamp(0)
    if mode == 4:
        target = run.bed(0)
        run.p = (target[0], 5.0)
        run.carried.append(dock.Kind((truck.needs[0].colour + 1) % 4, 0))
    origin = run.fork() if mode == 4 else target
    run.hand.x, run.hand.y, _ = run.view().see(origin)
    run.press()
    run.hand.x, run.hand.y, _ = run.view().see(target)
    run.release()


def replay(rows, board, mode, case):
    run = dock.Run(board)
    check(rows, "replay", (mode,), case)
    states = frame = 0
    while run.result is None:
        ports = dock.autopilot(run) if mode == 0 else []
        if mode == 2:
            ports = ([dock.BACK] if frame < 90 else [dock.LEFT] if frame < 160
                     else [dock.FWD_RIGHT] if frame < 250 else [])
        if mode >= 3 and frame == 0:
            wrong_delivery(run, mode)
            assert verdict(run)[0] == (3 if mode == 3 else 2)
        port = ports[0] if ports else -1
        if port in dock.EVENTS:
            dock.act(run, port)
        run.step(1 / 60, port)
        if frame % 97 == 0 or run.result is not None:
            code, truck = verdict(run)
            drag = 0 if run.drag is None else 1 if run.drag[0] == "fork" else 2
            check(rows, "state", (frame, port, code, truck, run.cam, drag, len(run.carried),
                                  run.t, *run.p, run.heading, run.speed, run.hand.x, run.hand.y),
                  (*case, mode, frame))
            for met, sent, horned in zip(run.met, run.sent, run.horned):
                mask = sum(1 << i for i, loaded in enumerate(met) if loaded)
                check(rows, "cargo", (mask, int(sent), int(horned)), case)
            other = run.other()
            if other is not None:
                x, z, heading = other
                check(rows, "forklift", (x, z, heading), case)
            states += 1
        frame += 1
    assert next(rows) == f"verdict {run.result[1]}", case
    for note in run.notes:
        check(rows, "cue", (note.voice, note.seed, note.t, note.dur, note.freq, note.gain,
                            note.pan), case)
    return states, len(run.notes)


def main(binary):
    rows = iter(subprocess.check_output([binary], text=True).splitlines())
    boards = states = cues = 0
    for rung in (-1, 1, 4, 7, 10, 13, 16, 19, 20, 25, 30):
        for seed in range(-1, 3):
            case = (rung, seed)
            try:
                board = dock.deal(rung, seed)
            except RuntimeError:
                board = None
            check(rows, "case", (*case, int(board is not None)), case)
            if board is None:
                continue
            compare_dock(rows, board, case)
            if case == (16, 0):
                compare_cameras(rows, board, case)
            boards += 1
            modes = 5 if case == (1, 0) else 3 if seed == 0 else 1
            for mode in range(modes):
                new_states, new_cues = replay(rows, board, mode, case)
                states += new_states
                cues += new_cues
    assert next(rows, None) is None
    print(f"PASS: {boards} Loading Dock seeded docks matched, {states} replay states, and {cues} audio cues")


if __name__ == "__main__":
    main(sys.argv[1])
