"""Compare Errands' game flow and drawn computer with ui/errands.py.

The computer is drawn by the reference's own ``_draw`` and Browser's
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
from neural_workshop import browser, errands, state  # noqa: E402

state.window = SimpleNamespace(width=912, height=684)
from neural_workshop.ui import browser as shopui  # noqa: E402
from neural_workshop.ui import errands as ui  # noqa: E402
from neural_workshop.ui import taskoptions  # noqa: E402

READY, PLAYING, JUDGED, DONE = range(4)
LIVE, ALL_DONE, OVER_PAR, NOT_DONE = range(4)
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


class Recorder(ui.Errands):
    """ui.Errands' drawing, writing down what it would draw."""

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
LEFT, TOP, SCALE = object.__new__(ui.Errands)._frame()


class Game:
    """ErrandsGame: RungTask's run with Errands' days."""

    def __init__(self, rung, total, seed):
        self.rng = Random(seed)
        self.start_rung = self.rung = rung
        self.total, self.trial, self.wins, self.best = total, 0, 0, 0
        self.phase, self.verdict, self.office, self.par, self.deadline = READY, LIVE, None, 0, 0.0
        self.words = ""

    def start(self, now):
        self.rung, self.trial, self.wins, self.best = self.start_rung, 0, 0, 0
        self.next_trial(now)

    def next_trial(self, now):
        if self.trial >= self.total:
            self.phase = DONE
            return
        dealt = errands.deal(self.rung, rng=self.rng)
        self.office, self.par, self.verdict = errands.Office(dealt), errands.par(dealt), LIVE
        self.trial += 1
        self.phase = PLAYING

    def after(self, now):
        office = self.office
        if not office.done:
            return
        wrong = office.mistakes()
        passed = not wrong and office.clicks <= self.par
        self.verdict = ALL_DONE if passed else OVER_PAR if not wrong else NOT_DONE
        if passed:
            self.words = "All done in %d clicks (par %d)" % (office.clicks, self.par)
        elif not wrong:
            self.words = "All done, but %d clicks against a par of %d" % (office.clicks, self.par)
        else:
            self.words = "Not done: %s" % "; ".join(wrong)
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
            self.office.move(dx * browser.STEPS[port % 3], dy * browser.STEPS[port % 3])
        elif port == ui.CLICK:
            self.office.click()
        else:
            self.office.wheel(-1 if port == ui.SCROLL_UP else 1)
        self.after(now)

    def click_at(self, x, y, now):
        mx, my = (LEFT + x * SCALE - LEFT) / SCALE, (TOP - (TOP - y * SCALE)) / SCALE
        if self.phase == PLAYING:
            self.office.click(mx, my)
            self.after(now)

    def click(self, rectangle, now):
        x, y, w, h = rectangle
        self.click_at(x + w / 2, y + h / 2, now)

    def scroll(self, way):
        if self.phase == PLAYING:
            self.office.wheel(way)

    def type_key(self, label, now):
        if self.phase == PLAYING and self.office.app == "expenses":
            self.office.clicks += 1
            self.office.do(("key", label))

    def advance(self, now):
        if self.phase == JUDGED and now >= self.deadline:
            self.next_trial(now)

    def message(self):
        if self.phase == READY:
            return "Press Space or click to start"
        if self.phase == DONE:
            return "%d of %d passed   highest rung passed %d" % (self.wins, self.trial, self.best)
        if self.phase == JUDGED:
            return self.words
        return "Do what the mail asks, then press Done"


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


def compare_computer(rows, game, where):
    recorder = Recorder()
    Recorder.current = recorder
    recorder.office = game.office
    recorder._draw(0, 0, 0, 0)
    for call in recorder.calls:
        compare_call(next(rows), call, where)
    assert next(rows) == "end", where
    return len(recorder.calls)


FOOTNOTE = "click   wheel or Up/Down: scroll   digits type into a claim   Esc: menu"


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
    compare_text(texts[0], "Errands", where)
    fields = compare_text(texts[1], message, where)
    close(fields[3], 614.0, where)
    compare_text(texts[2], FOOTNOTE, where)
    if game.phase in (PLAYING, JUDGED):
        compare_text(texts[3], "rung %d  %d/%d   clicks %d   par %d"
                     % (game.rung, game.trial, game.total, game.office.clicks, game.par), where)
        if game.phase == JUDGED:
            assert any(bytes.fromhex(t.split(" ", 7)[7]).decode() == message for t in texts[4:]), where
        assert row == "computer", (where, row)
        return compare_computer(rows, game, where)
    assert row == "end", (where, row)
    return 0


def wander(rows, game, now, where):
    calls = 0

    def press(rectangle):
        nonlocal calls
        game.click(rectangle, now)
        calls += compare_frame(rows, game, 2, where)

    office = game.office
    row = lambda i: (20, errands.INBOX_TOP + i * errands.ROW_H, 960, errands.ROW_H - 4)
    press(row(0))
    press((20, errands.STRIP + 14, 200, 30))
    press(row(len(office.deal.mails) - 1))
    if office.shop:
        press(errands.TABS["shop"])
        for way in (1, -1):
            game.scroll(way)
            calls += compare_frame(rows, game, 3, where)
    press(errands.TABS["expenses"])
    press(errands.SUBMIT)
    press(errands.FIELDS["amount"])
    for label in ("3", "0", "7", "del"):
        game.type_key(label, now)
        calls += compare_frame(rows, game, 4, where)
    press(errands.FIELDS["order"])
    for index in (0, 5, 10, 4):
        press(errands.keypad_rects()[index][1])
    press(errands.category_rects()[2][1])
    press(errands.SUBMIT)
    press(errands.TABS["mail"])
    press(errands.DONE)
    return calls


def main(binary):
    rows = iter(subprocess.check_output([binary], text=True).splitlines())
    runs = frames = calls = verdicts = notes = 0
    seen, apps = set(), set()
    for header in rows:
        if header.startswith("note "):
            _tag, rung, hexed = header.split()
            expected = taskoptions.errands_note({"ERRANDS_RUNG": int(rung)})
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
                calls += wander(rows, game, now, where)
            if trial == 2:
                for count in range(40):
                    game.click_at(500.0, 20.0, now)
                    if count % 10 == 0:
                        calls += compare_frame(rows, game, 5, where)
            if game.phase == PLAYING:
                ports = ui.reference_ports(SimpleNamespace(office=game.office))
                for index, port in enumerate(ports):
                    now += 0.25
                    game.steer(port, now)
                    if game.office:
                        apps.add(game.office.app)
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
    assert runs == 16 and {ALL_DONE, OVER_PAR, NOT_DONE} <= seen and len(apps) == 3, (runs, seen, apps)
    assert notes == 10, notes
    print(f"PASS: {runs} Errands runs match ui/errands.py ({frames} frames, {calls:,} drawing calls, "
          f"{verdicts} verdicts, {notes} options notes)")


if __name__ == "__main__":
    main(sys.argv[1])
