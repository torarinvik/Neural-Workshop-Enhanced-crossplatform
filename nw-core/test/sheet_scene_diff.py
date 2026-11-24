"""Compare Spreadsheet's game flow and drawn sheet with ui/sheet.py.

The sheet is drawn by the reference's own ``_draw`` and Browser's
``_rect``, ``_words`` and ``_pointer``; only the pyglet calls underneath
are recorded instead of made. Text width uses the port's estimate, as
browser_scene_diff.py explains.
"""
import math
from pathlib import Path
from random import Random
import subprocess
import sys
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced"))
from neural_workshop import browser, sheet, state  # noqa: E402

state.window = SimpleNamespace(width=912, height=684)
from neural_workshop.ui import browser as shopui  # noqa: E402
from neural_workshop.ui import sheet as ui  # noqa: E402
from neural_workshop.ui import taskoptions  # noqa: E402

READY, PLAYING, JUDGED, DONE = range(4)
LIVE, RIGHT, OVER_PAR, WRONG = range(4)
ANCHORS = {"left": 3, "center": 4, "right": 5}


def packed(colour):
    red, green, blue, *alpha = colour
    return (red << 24) | (green << 16) | (blue << 8) | (alpha[0] if alpha else 255)


class Label:
    def __init__(self, words, size):
        self.words, self.font_size = words, size

    @property
    def content_width(self):
        return len(self.words) * math.floor(self.font_size * 0.8 + 0.5)


class Recorder(ui.Spreadsheet):
    """ui.Spreadsheet's drawing, writing down what it would draw."""

    def __init__(self):
        self.calls, self.drawn = [], []
        self.batch = self.text_group = self.top_group = None

    def _box(self, x, y, w, h, colour, border=None, group=None, thickness=2.0):
        if border is None:
            self.calls.append(("rect", packed(colour), x, y, w, h))
        else:
            self.calls.append(("bordered", packed(colour), x, y, w, h, packed(border), float(thickness)))

    def _text(self, words, x, y, size, anchor="center", bold=False, colour=None, width=None, anchor_y="center",
              group=None):
        label = Label(words, max(6.0, size))
        self.calls.append(("text", label, x, y, bool(bold), ANCHORS[anchor], packed(colour)))
        return label


def line(x, y, x2, y2, thickness=1, color=None, batch=None, group=None):
    Recorder.current.calls.append(("line", packed(color), x, y, x2, y2, float(thickness)))


def triangle(x, y, x2, y2, x3, y3, color=None, batch=None, group=None):
    Recorder.current.calls.append(("triangle", packed(color), x, y, x2, y2, x3, y3))


shopui.pyglet.shapes.Line = line
shopui.pyglet.shapes.Triangle = triangle
LEFT, TOP, SCALE = object.__new__(ui.Spreadsheet)._frame()


class Game:
    """SheetGame: RungTask's run with Spreadsheet's questions."""

    def __init__(self, rung, total, seed):
        self.rng = Random(seed)
        self.start_rung = self.rung = rung
        self.total, self.trial, self.wins, self.best = total, 0, 0, 0
        self.phase, self.verdict, self.sheet, self.par, self.deadline = READY, LIVE, None, 0, 0.0

    def start(self, now):
        self.rung, self.trial, self.wins, self.best = self.start_rung, 0, 0, 0
        self.next_trial(now)

    def next_trial(self, now):
        if self.trial >= self.total:
            self.phase = DONE
            return
        puzzle = sheet.deal(self.rung, rng=self.rng)
        self.sheet, self.par, self.verdict = sheet.Sheet(puzzle), sheet.par(puzzle), LIVE
        self.trial += 1
        self.phase = PLAYING

    def after(self, now):
        if self.sheet.submitted is None:
            return
        right = self.sheet.submitted == self.sheet.puzzle.answer
        passed = right and self.sheet.clicks <= self.par
        self.verdict = RIGHT if passed else OVER_PAR if right else WRONG
        if passed:
            self.wins += 1
            self.best = max(self.best, self.rung)
        self.rung = self.rung + 1 if passed else max(1, self.rung - 1)
        self.deadline = now + 2.5
        self.phase = JUDGED

    def steer(self, port, now):
        if self.phase != PLAYING:
            return
        if port < ui.CLICK:
            dx, dy = browser.DIRECTIONS[port // 3]
            self.sheet.move(dx * browser.STEPS[port % 3], dy * browser.STEPS[port % 3])
        elif port == ui.CLICK:
            self.sheet.click()
        else:
            self.sheet.wheel(-1 if port == ui.SCROLL_UP else 1)
        self.after(now)

    def click(self, rectangle, now):
        x, y, w, h = rectangle
        mx, my = (LEFT + (x + w / 2) * SCALE - LEFT) / SCALE, (TOP - (TOP - (y + h / 2) * SCALE)) / SCALE
        if self.phase == PLAYING:
            self.sheet.click(mx, my)
            self.after(now)

    def scroll(self, way):
        if self.phase == PLAYING:
            self.sheet.wheel(way)

    def type_key(self, action, now):
        if self.phase == PLAYING:
            self.sheet.clicks += 1
            self.sheet.do(action)
            self.after(now)

    def advance(self, now):
        if self.phase == JUDGED and now >= self.deadline:
            self.next_trial(now)

    def message(self):
        if self.phase == READY:
            return "Press Space or click to start"
        if self.phase == DONE:
            return "%d of %d passed   highest rung passed %d" % (self.wins, self.trial, self.best)
        if self.phase == JUDGED:
            answer, clicks = self.sheet.puzzle.answer, self.sheet.clicks
            if self.verdict == RIGHT:
                return "Right: %d, in %d clicks (par %d)" % (answer, clicks, self.par)
            if self.verdict == OVER_PAR:
                return "Right, but %d clicks against a par of %d" % (clicks, self.par)
            return "No: the answer was %d" % answer
        return self.sheet.puzzle.question


def close(actual, expected, where):
    assert math.isclose(float(actual), float(expected), rel_tol=1e-6, abs_tol=2e-3), (where, actual, expected)


def compare_text(row, expected_words, where):
    fields = row.split(" ", 7)
    assert fields[0] == "text", (where, row)
    actual = bytes.fromhex(fields[7]).decode()
    assert actual == expected_words, (where, actual, expected_words)
    return fields


def compare_call(row, call, where):
    kind = call[0]
    if kind == "text":
        label, x, y, bold, anchor, colour = call[1:]
        fields = compare_text(row, label.words, (where, call))
        assert int(fields[1]) == colour and int(fields[6]) == anchor and float(fields[5]) == float(bold), (where, row, call)
        for actual, expected in zip(fields[2:5], (x, y, label.font_size)):
            close(actual, expected, (where, row, call))
        return
    fields = row.split()
    assert fields[0] == kind and int(fields[1]) == call[1], (where, row, call)
    for actual, expected in zip(fields[2:], call[2:]):
        close(actual, expected, (where, row, call))


def compare_sheet(rows, game, where):
    recorder = Recorder()
    Recorder.current = recorder
    recorder.sheet = game.sheet
    recorder._draw(0, 0, 0, 0)
    for call in recorder.calls:
        compare_call(next(rows), call, where)
    assert next(rows) == "end", where
    return len(recorder.calls)


FOOTNOTE = "click   wheel or Up/Down: scroll   digits, Backspace, Enter: answer   Esc: menu"


def compare_frame(rows, game, label, where):
    expected = [label, game.phase, game.rung, game.trial, game.wins, game.best, game.verdict]
    header = next(rows).split()
    assert header[0] == "frame" and list(map(int, header[1:])) == expected, (where, header, expected)
    texts = []
    row = next(rows)
    while row.startswith("text "):
        texts.append(row)
        row = next(rows)
    message = game.message()
    compare_text(texts[0], "Spreadsheet", where)
    fields = compare_text(texts[1], message, where)
    close(fields[3], 614.0, where)
    compare_text(texts[2], FOOTNOTE, where)
    if game.phase in (PLAYING, JUDGED):
        compare_text(texts[3], "rung %d  %d/%d   clicks %d   par %d"
                     % (game.rung, game.trial, game.total, game.sheet.clicks, game.par), where)
        if game.phase == JUDGED:
            assert any(bytes.fromhex(t.split(" ", 7)[7]).decode() == message for t in texts[4:]), where
        assert row == "sheet", (where, row)
        return compare_sheet(rows, game, where)
    assert row == "end", (where, row)
    return 0


def header_rect(column):
    x, w = sheet.column_x()[column]
    return (x, sheet.HEAD_Y, w, sheet.HEAD_H)


def main(binary):
    rows = iter(subprocess.check_output([binary], text=True).splitlines())
    runs = frames = calls = verdicts = notes = 0
    seen, statuses = set(), set()
    for header in rows:
        if header.startswith("note "):
            _tag, rung, hexed = header.split()
            expected = taskoptions.spreadsheet_note({"SPREADSHEET_RUNG": int(rung)})
            assert bytes.fromhex(hexed).decode() == expected, (rung, bytes.fromhex(hexed).decode(), expected)
            notes += 1
            continue
        tag, rung, seed = header.split()
        assert tag == "run", header
        rung, seed = int(rung), int(seed)
        game = Game(rung, 3, seed)
        calls += compare_frame(rows, game, 0, (rung, seed, 0))
        game.start(0.0)
        calls += compare_frame(rows, game, 1, (rung, seed, 1))
        now = 0.0
        for trial in range(3):
            where = (rung, seed, trial)
            if trial == 1:
                game.scroll(1)
                calls += compare_frame(rows, game, 3, where)
                for _ in range(2):
                    game.click(header_rect("item" if seed == 3 else "category"), now)
                    calls += compare_frame(rows, game, 2, where)
                for _column, rectangle in sheet.sum_buttons():
                    game.click(rectangle, now)
                    calls += compare_frame(rows, game, 2, where)
                    statuses.add(game.sheet.stat)
                game.click(sheet.chips(game.sheet.puzzle.categories)[1][1], now)
                calls += compare_frame(rows, game, 2, where)
                game.type_key(("key", "7"), now)
                calls += compare_frame(rows, game, 4, where)
                game.type_key(("key", "del"), now)
                game.scroll(1)
                calls += compare_frame(rows, game, 4, where)
                game.click(sheet.chips(game.sheet.puzzle.categories)[0][1], now)
                calls += compare_frame(rows, game, 2, where)
            if trial == 2:
                game.type_key(("submit",), now)
                for digit in str(game.sheet.puzzle.answer + 1):
                    now += 0.25
                    game.type_key(("key", digit), now)
                    calls += compare_frame(rows, game, 5, where)
                game.type_key(("submit",), now)
            if game.phase == PLAYING:
                ports = ui.reference_ports(SimpleNamespace(sheet=game.sheet))
                for index, port in enumerate(ports):
                    now += 0.25
                    game.steer(port, now)
                    if port >= ui.CLICK or index % 9 == 0:
                        calls += compare_frame(rows, game, 10, where + (index,))
                        frames += 1
                    if game.phase != PLAYING:
                        break
            seen.add(game.verdict)
            verdicts += game.phase == JUDGED
            calls += compare_frame(rows, game, 6, where)
            now += 3.0
            game.advance(now)
            calls += compare_frame(rows, game, 7, where)
            frames += 2
        assert next(rows) == "over", (rung, seed)
        runs += 1
    assert runs == 16 and {RIGHT, OVER_PAR, WRONG} <= seen and len(statuses) == 3, (runs, seen, statuses)
    assert notes == 9, notes
    print(f"PASS: {runs} Spreadsheet runs match ui/sheet.py ({frames} frames, {calls:,} drawing calls, "
          f"{verdicts} verdicts, {notes} options notes)")


if __name__ == "__main__":
    main(sys.argv[1])
