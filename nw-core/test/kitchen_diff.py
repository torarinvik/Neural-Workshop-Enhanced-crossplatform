"""Compare seeded shifts, cook decisions, and frame state with Python."""
from math import isclose
from pathlib import Path
from random import Random
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced"))
from neural_workshop import kitchen


STAGES = (kitchen.RAW, kitchen.CHOPPED, kitchen.COOKED, kitchen.BURNT)
FLASH_WORDS = ("served!", "no such ticket", "binned")


def part(food, stage):
    return sorted(kitchen.FOODS).index(food) * 4 + STAGES.index(stage) + 1


def dish(parts):
    return [len(parts), *(part(*item) for item in parts)]


def compare(rows, tag, expected, where, tolerant=False):
    kind, *fields = next(rows).split()
    assert kind == tag and len(fields) == len(expected), (where, tag, kind, fields, expected)
    for i, (field, value) in enumerate(zip(fields, expected)):
        if isinstance(value, float):
            actual = float(field)
            matches = isclose(actual, value, rel_tol=0, abs_tol=1e-12) if tolerant else actual == value
        else:
            actual = int(field)
            matches = actual == value
        assert matches, (where, tag, i, actual, value)


def compare_shift(rows, shift, where):
    compare(rows, "grade", shift.level, where, tolerant=True)
    for station in shift.stations:
        food = kitchen.FOODS.index(station.food) if station.food else -1
        compare(rows, "station", [station.port, station.x, station.y, food], where, tolerant=True)
    for ticket in shift.tickets:
        compare(rows, "ticket", [ticket.due, ticket.patience, *dish(ticket.parts)], where, tolerant=True)


def replay(rows, shift, mode, where):
    run = kitchen.Run(shift)
    for tick in range(18000):
        if mode == 1:
            orders = kitchen.autopilot(run)
            port = orders[0] if orders else -1
        elif mode == 2:
            port = (tick // 49 * 5) % kitchen.PORTS if tick % 49 == 0 else -1
        else:
            port = {0: 0, 60: 4, 120: 4, 150: 6, 480: 6, 510: 12}.get(tick, -1)
        run.send(port)
        run.step(1 / 30)
        target = -1 if run.target is None else run.target.port
        chopping = -1 if run.chopping is None else run.chopping
        result = 0 if run.result is None else 1 if run.result[0] else 2
        held_part = part(*run.held) if run.held and run.held[0] != "plate" else 0
        held_dish = run.held[1] if run.held and run.held[0] == "plate" else ()
        values = [port, run.t, run.x, run.y, target, held_part, chopping, run.arrived,
                  len(run.served), len(run.lapsed), result, run.burnt, *dish(held_dish)]
        for board in run.boards.values():
            values.extend([part(board[0], kitchen.CHOPPED), board[1]] if board else [0, 0.0])
        for pan in run.stoves.values():
            values.extend([part(pan.food, kitchen.CHOPPED), pan.since] if pan else [0, 0.0])
        for plate in run.plates.values():
            values.extend(dish(plate))
        for k in range(len(shift.tickets)):
            values.append(1 if k in run.open else 2 if k in run.served else 3 if k in run.lapsed else 0)
        values.append(len(run.flash))
        for time, message, _, _ in run.flash:
            station = kitchen.BIN if message == "binned" else kitchen.PASS
            values.extend([FLASH_WORDS.index(message) + 1, run.station(station).port, time])
        compare(rows, "tick", values, (*where, tick), tolerant=True)
        if mode == 3 and tick == 600:
            assert run.burnt == 1 and any(message == "binned" for _, message, _, _ in run.flash)
        if result:
            return tick + 1, result
    raise AssertionError(("shift did not finish", where))


def main(binary):
    rows = iter(subprocess.check_output([binary], text=True).splitlines())
    candidates = ticks = wins = losses = 0
    for header in rows:
        tag, rung, seed, mode = header.split()
        assert tag == "case", header
        rung, seed, mode = map(int, (rung, seed, mode))
        where = rung, seed, mode
        if mode == 0:
            draw = Random(seed)
            for attempt in range(3):
                compare_shift(rows, kitchen._build(kitchen.grade(rung), draw), (*where, attempt))
                candidates += 1
        else:
            shift = kitchen.deal(rung, seed=seed)
            compare_shift(rows, shift, where)
            count, result = replay(rows, shift, mode, where)
            ticks += count
            wins += result == 1
            losses += result == 2
        assert next(rows) == "end", where
    assert candidates == 99 and wins + losses == 11 and wins and losses
    print(f"PASS: {candidates + wins + losses} Kitchen cases match Python "
          f"({candidates} candidates and {ticks:,} ticks in {wins} wins and {losses} losses)")


if __name__ == "__main__":
    main(sys.argv[1])
