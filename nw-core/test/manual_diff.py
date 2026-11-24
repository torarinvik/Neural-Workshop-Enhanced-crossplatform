"""Compare Manual's grades, deals, procedures, follow(), ports and play with Python."""
from pathlib import Path
from random import Random
from types import SimpleNamespace
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced"))
from neural_workshop import manual  # noqa: E402
from neural_workshop.ui import manual as ui  # noqa: E402

KINDS = ("set", "flip", "knob", "press", "if", "count", "copy", "until", "recall", "skip")
COLOURS = {colour: index for index, colour in enumerate(manual.COLOURS)}


def compare(rows, tag, expected, where):
    kind, *fields = next(rows).split()
    assert kind == tag and len(fields) == len(expected), (where, tag, kind, fields, expected)
    for i, (field, value) in enumerate(zip(fields, expected)):
        actual = float(field) if isinstance(value, float) else int(field)
        assert actual == value, (where, tag, i, actual, value)


def compare_text(rows, expected, where):
    actual = bytes.fromhex(next(rows)).decode()
    assert actual == expected, (where, actual, expected)


def panel_fields(panel):
    return ([*map(int, panel.switches), *panel.knobs, *panel.presses]
            + [COLOURS[panel.lamp(i)] for i in range(panel.level.lamps)] + [panel.display()])


def log_code(action):
    kind = ("switch", "knob", "press").index(action[0])
    return kind * 64 + action[1] * 2 + (1 if len(action) > 2 and action[2] > 0 else 0)


def mistakes(have, want):
    task = SimpleNamespace(panel=have, wanted=want)
    return ", ".join(ui.Manual.mistakes(task))


def steer(panel, dealt, port):
    switches, knobs, buttons = dealt.layout
    if port < ui.KNOB:
        return port < len(switches) and panel.toggle(switches[port])
    if port < ui.BUTTON:
        slot, way = divmod(port - ui.KNOB, 2)
        return slot < len(knobs) and panel.turn(knobs[slot], 1 if way else -1)
    if port < ui.FINISH:
        return port - ui.BUTTON < len(buttons) and panel.press(buttons[port - ui.BUTTON])
    return False


def play(rows, dealt, seed, want, where):
    panel = dealt.panel()
    rolling = seed % 2147483648
    moved_any = 0
    for step in range(40):
        rolling = (rolling * 1103515245 + 12345) % 2147483648
        draw = rolling // 128
        kind, index = draw % 4, (draw // 4) % 8 - 1
        if kind == 0:
            moved = panel.toggle(index)
        elif kind == 1:
            moved = panel.turn(index, 1 if (draw // 32) % 2 else -1)
        elif kind == 2:
            moved = panel.press(index)
        else:
            moved = steer(panel, dealt, (draw // 4) % ui.PORTS)
        compare(rows, "hand", [kind, index, int(bool(moved))], (where, step))
        compare(rows, "panel", panel_fields(panel), (where, step))
        moved_any += bool(moved)
    compare_text(rows, mistakes(panel, want), where)
    return moved_any


def main(binary):
    rows = iter(subprocess.check_output([binary], text=True).splitlines())
    cases = steps = moves = reference = 0
    kinds, shuffled = set(), 0
    for header in rows:
        tag, rung, seed, from_run = header.split()
        assert tag == "case", header
        rung, seed, from_run = int(rung), int(seed), int(from_run)
        where = (rung, seed, from_run)
        if from_run:
            run = Random(seed)
            dealt = manual.deal(rung, rng=run)
            compare(rows, "after", [run.random()], where)
        else:
            dealt = manual.deal(rung, seed=seed)
        g = dealt.level
        compare(rows, "grade", [g.rung, g.switches, g.knobs, g.buttons, g.lamps, g.steps, int(g.shuffled),
                                *(KINDS.index(kind) for kind in g.kinds)], where)
        compare(rows, "deal", [dealt.seed, *(w for row in dealt.wiring.lamps for w in row), *dealt.wiring.display,
                               *map(int, dealt.switches), *dealt.knobs, *dealt.layout[0], *dealt.layout[1],
                               *dealt.layout[2]], where)
        compare_text(rows, "\n".join("%d.  %s" % (n + 1, step.words) for n, step in enumerate(dealt.steps)), where)
        want = manual.follow(dealt)
        compare(rows, "follow", panel_fields(want), where)
        compare(rows, "log", [len(want.log), *map(log_code, want.log)], where)
        ports = ui.reference_ports(SimpleNamespace(deal=dealt))
        compare(rows, "reference", [len(ports), *ports], where)
        replay = dealt.panel()
        for port in ports:
            steer(replay, dealt, port)
        assert replay.state() == want.state(), where
        compare(rows, "replayed", panel_fields(replay), where)
        compare_text(rows, "", where)
        moves += play(rows, dealt, seed * 31 + rung, want, where)
        assert next(rows) == "end", where
        cases += 1
        steps += len(dealt.steps)
        reference += len(ports)
        shuffled += g.shuffled
        kinds.update(step.words.split(" ")[0] for step in dealt.steps)
    assert cases == 33 * 5 + 18 and shuffled, (cases, shuffled)
    print(f"PASS: {cases} Manual deals match Python ({steps} steps, {reference:,} reference ports, "
          f"{moves:,} moves in play, {shuffled} shuffled panels)")


if __name__ == "__main__":
    main(sys.argv[1])
