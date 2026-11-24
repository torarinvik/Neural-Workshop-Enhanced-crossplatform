"""Compare seeded Gunslinger duels and public action traces against Python."""
import math
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced"))
from neural_workshop import gunslinger as gun

VERDICTS = ("", "You were the quicker", "His hat is off and so is he",
            "You fired first", "You shot the wrong man", "The notice said his hat",
            "Too slow: he shot you")


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


def compare_duel(rows, duel, case):
    level = duel.level
    check(rows, "duel", (level.men, duel.foe, int(duel.part == "hat"), duel.seed,
                         duel.draw_at, level.quick, level.sway, level.pace), case)
    assert next(rows) == f"notice {duel.notice}", case
    for man in duel.men:
        check(rows, "man", (man.hat, man.x, man.z, man.stride, man.rate, man.phase), case)
    for reach in duel.reaches:
        check(rows, "reach", (reach.who, int(reach.real), reach.t), case)


def scripted(run, frame, mode):
    hand = gun.H
    if mode == 0:
        ports = gun.autopilot(run)
        return ports[0] if ports else -1
    if mode == 1 and frame == 0:
        return hand.PRESS
    if mode == 2 and run.drawn() and not run.shots:
        if not run.cocked and not run.hand.down:
            return gun.COCK if frame % 2 == 0 else hand.PRESS
        if run.hand.down:
            return hand.RELEASE
        run.hand.x = run.hand.y = 0.0
        return hand.PRESS
    if mode in (3, 4) and run.drawn():
        if run.hand.down:
            return hand.RELEASE
        if not run.cocked:
            return gun.COCK
        k = (run.duel.foe + 1) % run.level.men if mode == 3 else run.duel.foe
        _hat, (left, bottom, right, top) = run.boxes(k)
        sx, sy = run.sway()
        run.hand.x = (left + right) / 2 - sx
        run.hand.y = (bottom + top) / 2 - sy
        return hand.PRESS
    return -1


def replay(rows, duel, mode, case):
    run = gun.Run(duel)
    check(rows, "mode", (mode,), case)
    states = frame = 0
    while run.result is None:
        port = scripted(run, frame, mode)
        if port >= 0:
            gun.act(run, port)
        run.step(1 / 60)
        if frame % 43 == 0 or run.result is not None:
            result = VERDICTS.index(run.result[1]) if run.result else 0
            hatless = sum(1 << k for k in run.hatless)
            check(rows, "state", (frame, port, result, int(run.cocked), run.bullets,
                                  -1 if run.fell is None else run.fell, hatless, run.reach_no,
                                  run.t, *run.aim(), run.fell_at, float(run.dust())), (*case, mode, frame))
            for k in range(run.level.men):
                x, _, z = run.stands(k)
                hat, body = run.boxes(k)
                check(rows, "target", (x, z, run.arm(k), run.hat_at.get(k, 0.0), *hat, *body), case)
            states += 1
        frame += 1
    assert next(rows) == f"verdict {run.result[1]}", case
    for shot in run.shots:
        check(rows, "shot", shot, case)
    for cue in run.notes:
        check(rows, "cue", (cue.voice, cue.seed, cue.t, cue.dur, cue.freq, cue.gain, cue.pan), case)
    return states, len(run.notes), run.result[1]


def main(binary):
    rows = iter(subprocess.check_output([binary], text=True, timeout=120).splitlines())
    duels = states = cues = 0
    verdicts = set()
    for rung in (-1, 1, 4, 7, 10, 13, 16, 19, 20, 25, 30, 70):
        for seed in range(-1, 5):
            case = rung, seed
            try:
                duel = gun.deal(rung, seed)
            except RuntimeError:
                duel = None
            check(rows, "case", (*case, int(duel is not None)), case)
            if duel is None:
                continue
            compare_duel(rows, duel, case)
            duels += 1
            modes = [0]
            if seed == 0:
                modes.extend((1, 2))
            if duel.level.men > 1 and seed < 2:
                modes.append(3)
            if duel.part == "hat":
                modes.append(4)
            for mode in modes:
                ns, nc, verdict = replay(rows, duel, mode, case)
                states += ns
                cues += nc
                verdicts.add(verdict)
    assert next(rows, None) is None
    assert verdicts == set(VERDICTS[1:]), verdicts
    print(f"PASS: {duels} Gunslinger duels, {states} replay states, {cues} audio cues, and all six verdicts")


if __name__ == "__main__":
    main(sys.argv[1])
