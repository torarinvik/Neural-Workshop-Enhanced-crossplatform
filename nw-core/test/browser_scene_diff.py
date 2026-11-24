"""Compare Browser's game flow and drawn window with ui/browser.py.

The shop is drawn by the reference's own ``_draw_shop``, ``_element``,
``_scrollbar`` and ``_pointer``; only the pyglet calls underneath are
recorded instead of made. Text width uses the port's estimate (pyglet's
real font metrics are not available headless), so the shrink-to-fit
sizes are compared under that same estimate.
"""
import math
from pathlib import Path
from random import Random
import subprocess
import sys
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced"))
from neural_workshop import browser, state  # noqa: E402

state.window = SimpleNamespace(width=912, height=684)
from neural_workshop.ui import browser as ui  # noqa: E402
from neural_workshop.ui import taskoptions  # noqa: E402

READY, PLAYING, JUDGED, DONE = range(4)
LIVE, BOUGHT, OVER_PAR, WRONG = range(4)
ANCHORS = {"left": 3, "center": 4}


def packed(colour):
    red, green, blue, *alpha = colour
    return (red << 24) | (green << 16) | (blue << 8) | (alpha[0] if alpha else 255)


class Label:
    def __init__(self, words, size):
        self.words, self.font_size = words, size

    @property
    def content_width(self):
        return len(self.words) * math.floor(self.font_size * 0.8 + 0.5)


class Recorder(ui.Browser):
    """ui.Browser's drawing, writing down what it would draw."""

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


ui.pyglet.shapes.Line = line
ui.pyglet.shapes.Triangle = triangle
LEFT, TOP, SCALE = object.__new__(ui.Browser)._frame()


class Game:
    """BrowserGame: RungTask's run with Browser's trials."""

    def __init__(self, rung, total, seed):
        self.rng = Random(seed)
        self.start_rung = self.rung = rung
        self.total, self.trial, self.wins, self.best = total, 0, 0, 0
        self.phase, self.verdict, self.session, self.par, self.deadline = READY, LIVE, None, 0, 0.0

    def start(self, now):
        self.rung, self.trial, self.wins, self.best = self.start_rung, 0, 0, 0
        self.next_trial(now)

    def next_trial(self, now):
        if self.trial >= self.total:
            self.phase = DONE
            return
        dealt = browser.deal(self.rung, rng=self.rng)
        self.session, self.par, self.verdict = browser.Session(dealt), browser.par(dealt), LIVE
        self.trial += 1
        self.phase = PLAYING

    def checkout(self, now):
        right = self.session.right()
        passed = right and self.session.clicks <= self.par
        self.verdict = BOUGHT if passed else OVER_PAR if right else WRONG
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
            self.session.move(dx * browser.STEPS[port % 3], dy * browser.STEPS[port % 3])
        elif port == ui.CLICK:
            self.session.click()
        else:
            self.session.wheel(-1 if port == ui.SCROLL_UP else 1)
        if self.session.checked_out:
            self.checkout(now)

    def click(self, x, y, now):
        mx, my = (x - LEFT) / SCALE, (TOP - y) / SCALE
        if self.phase == PLAYING and 0 <= mx <= browser.SCREEN_W and 0 <= my <= browser.SCREEN_H:
            self.session.click(mx, my)
            if self.session.checked_out:
                self.checkout(now)

    def back(self):
        if self.phase == PLAYING:
            self.session.clicks += 1
            self.session.do(("back",))

    def advance(self, now):
        if self.phase == JUDGED and now >= self.deadline:
            self.next_trial(now)

    def message(self):
        if self.phase == READY:
            return "Press Space or click to start"
        if self.phase == DONE:
            return "%d of %d passed   highest rung passed %d" % (self.wins, self.trial, self.best)
        if self.phase == JUDGED:
            clicks = self.session.clicks
            if self.verdict == BOUGHT:
                return "Bought the right things in %d clicks (par %d)" % (clicks, self.par)
            if self.verdict == OVER_PAR:
                return "The right things, but %d clicks against a par of %d" % (clicks, self.par)
            return "Not what the list asked for (%d clicks, par %d)" % (clicks, self.par)
        return browser.goal_words(self.session.deal)


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


def compare_words(header, rows):
    """One _words case; true when the text had to shrink."""
    _tag, length, size, width, drawn = header.split()
    size, width = float(size), float(width)
    recorder = Recorder()
    label = recorder._words("w" * int(length), 100.0, 200.0, size, width=width or None)
    (call,) = recorder.calls
    compare_call(next(rows), call, header)
    close(drawn, label.content_width, header)
    return label.font_size < size * SCALE


def compare_shop(rows, game, where):
    recorder = Recorder()
    Recorder.current = recorder
    recorder._draw_shop(game.session)
    for call in recorder.calls:
        compare_call(next(rows), call, where)
    assert next(rows) == "end", where
    return len(recorder.calls)


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
    compare_text(texts[0], "Browser", where)
    fields = compare_text(texts[1], message, where)
    close(fields[3], 614.0, where)
    compare_text(texts[2], "click links and buttons   wheel or Up/Down: scroll   Backspace: back   Esc: menu", where)
    if game.phase in (PLAYING, JUDGED):
        session = game.session
        compare_text(texts[3], "rung %d  %d/%d   clicks %d   par %d"
                     % (game.rung, game.trial, game.total, session.clicks, game.par), where)
        if game.phase == JUDGED:
            assert any(bytes.fromhex(t.split(" ", 7)[7]).decode() == message for t in texts[4:]), where
        assert row == "shop", (where, row)
        return compare_shop(rows, game, where)
    assert row == "end", (where, row)
    return 0


def detour(rows, game, now, where):
    """Open the cart with a click on its toolbar button, then go Back."""
    (cx, cy, _w, _h), _action = game.session.chrome()[2]
    game.click(LEFT + (cx + 5.0) * SCALE, TOP - (cy + 5.0) * SCALE, now)
    calls = compare_frame(rows, game, 2, where + (2,))
    game.back()
    return calls + compare_frame(rows, game, 3, where + (3,))


def main(binary):
    rows = iter(subprocess.check_output([binary], text=True).splitlines())
    runs = frames = calls = verdicts = 0
    seen = set()
    shrunk = []
    notes = 0
    for header in rows:
        if header.startswith("words "):
            shrunk.append(compare_words(header, rows))
            continue
        if header.startswith("note "):
            _tag, rung, hexed = header.split()
            expected = taskoptions.browser_note({"BROWSER_RUNG": int(rung)})
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
            ports = []
            if trial == 1:
                ports.append(ui.SCROLL_DOWN)
                calls += detour(rows, game, now, (rung, seed, trial))
            if trial == 2 and seed == 11:
                for _ in range(game.par // 2 + 1):
                    calls += detour(rows, game, now, (rung, seed, trial))
            ports += ui.reference_ports(SimpleNamespace(session=game.session))
            if trial == 2 and seed != 11:
                game.steer(ui.CLICK, now)
                game.steer(ui.CLICK, now)
            for index, port in enumerate(ports):
                now += 0.25
                game.steer(port, now)
                if port >= ui.CLICK or index % 9 == 0:
                    calls += compare_frame(rows, game, 10, (rung, seed, trial, index))
                    frames += 1
                if game.phase != PLAYING:
                    break
            seen.add(game.verdict)
            verdicts += game.phase == JUDGED
            calls += compare_frame(rows, game, 4, (rung, seed, trial, 4))
            now += 3.0
            game.advance(now)
            calls += compare_frame(rows, game, 5, (rung, seed, trial, 5))
            frames += 4
        assert next(rows) == "over", (rung, seed)
        runs += 1
    assert runs == 18 and {LIVE, BOUGHT, OVER_PAR, WRONG} <= seen, (runs, seen)
    assert len(shrunk) == 36 and any(shrunk) and not all(shrunk), shrunk
    assert notes == 10, notes
    print(f"PASS: {runs} Browser runs match ui/browser.py ({frames} frames, {calls:,} drawing calls, "
          f"{verdicts} verdicts, {sum(shrunk)} of {len(shrunk)} fitted texts shrunk, {notes} options notes)")


if __name__ == "__main__":
    main(sys.argv[1])
