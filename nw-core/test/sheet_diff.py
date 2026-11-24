"""Compare Spreadsheet's deals, questions, par, reference ports and play with Python."""
from pathlib import Path
from random import Random
from types import SimpleNamespace
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced"))
from neural_workshop import browser, sheet  # noqa: E402
from neural_workshop.ui import sheet as ui  # noqa: E402

KINDS = ("lookup", "max", "sum", "count", "wrong", "fix")
COLUMNS = [key for key, _label, _width in sheet.COLUMNS]
ACTIONS = {"filter": 1, "sort": 2, "sum": 3, "key": 4, "submit": 5}


def code(action):
    kind = action[0]
    if kind == "filter":
        return [1, -1 if action[1] == "All" else sheet.CATEGORIES.index(action[1])]
    if kind in ("sort", "sum"):
        return [ACTIONS[kind], COLUMNS.index(action[1])]
    if kind == "key":
        return [4, 10 if action[1] == "del" else int(action[1])]
    return [5, 0]


def compare(rows, tag, expected, where):
    kind, *fields = next(rows).split()
    assert kind == tag and len(fields) == len(expected), (where, tag, kind, fields, expected)
    for i, (field, value) in enumerate(zip(fields, expected)):
        actual = float(field) if isinstance(value, float) else int(field)
        assert actual == value, (where, tag, i, actual, value)


def compare_text(rows, expected, where):
    actual = bytes.fromhex(next(rows)).decode()
    assert actual == expected, (where, actual, expected)


def compare_puzzle(rows, puzzle, where):
    g = sheet.grade(puzzle.rung)
    compare(rows, "grade", [g.rung, g.rows, g.categories, len(g.kinds), g.slack,
                            *[KINDS.index(kind) for kind in g.kinds]], where)
    tools = [value for tool in puzzle.tools for value in code(tool)]
    compare(rows, "puzzle", [KINDS.index(puzzle.kind), puzzle.answer, len(puzzle.tools), *tools,
                             *[sheet.CATEGORIES.index(name) for name in puzzle.categories]], where)
    for row in puzzle.rows:
        compare(rows, "row", [row.id, sheet.CATEGORIES.index(row.category), row.qty, row.price, row.total], where)
        compare_text(rows, row.item, where)
    compare_text(rows, puzzle.question, where)


def steer(state, port):
    if port < ui.CLICK:
        dx, dy = browser.DIRECTIONS[port // 3]
        state.move(dx * browser.STEPS[port % 3], dy * browser.STEPS[port % 3])
    elif port == ui.CLICK:
        state.click()
    elif port == ui.SCROLL_UP:
        state.wheel(-1)
    elif port == ui.SCROLL_DOWN:
        state.wheel(1)


def status(state):
    figures = state.stats()
    if figures is None:
        return "pick a Sum button to see the visible rows added up"
    label = dict((key, label) for key, label, _w in sheet.COLUMNS)[state.stat]
    return "%s of visible rows:  sum %d   count %d   largest %d" % ((label,) + figures)


def compare_state(rows, state, port, kind, where):
    figures = state.stats() or (0, len(state.visible_rows()), 0)
    sort_column, sort_down = state.sort if state.sort else (None, False)
    compare(rows, "step", [port, kind, -1 if state.filter == "All" else sheet.CATEGORIES.index(state.filter),
                           -1 if sort_column is None else COLUMNS.index(sort_column), int(sort_down), state.scroll,
                           -1 if state.stat is None else COLUMNS.index(state.stat), len(state.typed), state.clicks,
                           float(state.pointer[0]), float(state.pointer[1]), int(state.submitted is not None),
                           state.submitted or 0, state.max_scroll(), *figures,
                           *[row.id for row in state.visible_rows()]], where)
    compare_text(rows, state.typed, where)
    compare_text(rows, status(state), where)


def play(rows, puzzle, seed, where):
    state = sheet.Sheet(puzzle)
    rolling = seed % 2147483648
    steps = 0
    for _ in range(120):
        rolling = (rolling * 1103515245 + 12345) % 2147483648
        draw = rolling // 128
        pick = draw % 100
        port = (draw // 100) % 15
        kind = 0
        if pick < 30:
            steer(state, port)
        elif pick < 75:
            kind = 1
            targets = state.targets()
            port = (draw // 100) % (len(targets) + 2)
            if port < len(targets):
                x, y, w, h = targets[port][1]
                state.click(x + w / 2, y + h / 2)
            else:
                state.click(float((draw // 7) % 1000), float((draw // 11) % 640))
        else:
            kind = 2
            port = (draw // 100) % 12
            state.clicks += 1
            state.do(("submit",) if port == 11 else ("key", "del" if port == 10 else str(port)))
        compare_state(rows, state, port, kind, (where, steps))
        steps += 1
        if state.submitted is not None:
            break
    assert next(rows) == "played", where
    return steps, state.submitted is not None


def main(binary):
    rows = iter(subprocess.check_output([binary], text=True).splitlines())
    cases = steps = submits = reference_clicks = 0
    kinds = set()
    for header in rows:
        tag, rung, seed, from_run = header.split()
        assert tag == "case", header
        rung, seed, from_run = int(rung), int(seed), int(from_run)
        where = (rung, seed, from_run)
        if from_run:
            run = Random(seed)
            puzzle = sheet.deal(rung, rng=run)
            compare(rows, "after", [run.random()], where)
        else:
            puzzle = sheet.deal(rung, seed=seed)
        kinds.add(puzzle.kind)
        compare_puzzle(rows, puzzle, where)
        compare(rows, "par", [sheet.fewest(puzzle), sheet.par(puzzle)], where)
        for action in sheet.plan(puzzle):
            compare(rows, "plan", code(action), where)
        start = sheet.Sheet(puzzle)
        start.pointer = [float(seed % 1000), float(rung * 20 % 640)]
        ports = ui.reference_ports(SimpleNamespace(sheet=start))
        compare(rows, "reference", [len(ports), *ports], where)
        replay = sheet.Sheet(puzzle)
        replay.pointer = list(start.pointer)
        for port in ports:
            steer(replay, port)
        assert replay.submitted == puzzle.answer and replay.clicks == sheet.fewest(puzzle), where
        compare(rows, "replayed", [1, puzzle.answer, replay.clicks], where)
        reference_clicks += replay.clicks
        count, done = play(rows, puzzle, seed * 31 + rung, where)
        steps, submits = steps + count, submits + done
        if rung % 3 == 0:
            count, done = play(rows, puzzle, seed * 37 + rung + 1, where)
            steps, submits = steps + count, submits + done
        assert next(rows) == "end", where
        cases += 1
    assert cases == 206 and submits and kinds == set(KINDS), (cases, submits, kinds)
    print(f"PASS: {cases} Spreadsheet puzzles match Python (all six question kinds, {reference_clicks} reference "
          f"clicks, {steps:,} play steps, {submits} answers submitted)")


if __name__ == "__main__":
    main(sys.argv[1])
