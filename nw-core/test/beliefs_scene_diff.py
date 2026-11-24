"""Compare Who Knows What? display geometry to calls made by Python's UI."""

from math import floor, isclose
from pathlib import Path
from random import Random
import subprocess
import sys
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced"))
from neural_workshop import beliefs, state
from neural_workshop.ui.beliefs import WhoKnowsWhat

RECT, BOX, CIRCLE = 1, 3, 4


def rgba(colour):
    r, g, b = colour[:3]
    return (r << 24) | (g << 16) | (b << 8) | 255


class Recorder(WhoKnowsWhat):
    """Record the source scene's actual draw calls without opening a window."""

    def __init__(self, puzzle, dark, phase):
        self.puzzle = puzzle
        self.dark = dark
        self.phase = "judged" if phase == 2 else "playing"
        self.chosen = (puzzle.answer + 1) % len(puzzle.choices)
        self.ink = (255, 255, 255) if dark else (0, 0, 0)
        self.textcolor = (*self.ink, 255)
        self.top_group = None
        self.hits = []
        self.shapes, self.text, self.captions = [], [], []

    def _box(self, x, y, w, h, colour, border=None, group=None, thickness=2):
        self.shapes.append((RECT, rgba(colour), x, y, w, h, 0.0))
        if border is not None:
            self.shapes.append((BOX, rgba(border), x, y, w, h, thickness))

    def _circle(self, x, y, r, colour, group=None):
        self.shapes.append((CIRCLE, rgba(colour), x, y, r, 0.0, 0.0))

    def _text(self, words, x, y, size, anchor="center", bold=False, colour=None,
              width=None, anchor_y="center", group=None):
        size = max(6, size)
        text = (rgba(colour or self.textcolor), x, y, size, words)
        if width is None:
            self.text.append(text)
        else:
            self.captions.append((*text, int(width)))
        return SimpleNamespace(content_width=len(words) * floor(size * 0.8 + 0.5), font_size=size)


def matches(actual, expected):
    return all(isclose(a, b, abs_tol=0.0001) if isinstance(a, float) else a == b
               for a, b in zip(actual, expected, strict=True))


def remove_matching(rows, expected):
    for i, actual in enumerate(rows):
        if matches(actual, expected):
            del rows[i]
            return
    raise AssertionError(f"Missing draw command {expected}")


def compare(binary):
    rows = iter(subprocess.check_output([binary], text=True).splitlines())
    previous_window = state.window
    state.window = SimpleNamespace(width=912, height=684)
    try:
        for rung, seed in [(1, 17), (6, 17), (13, 17), (21, 17), (25, 17), (25, 222)]:
            puzzle = beliefs.deal(rung, rng=Random(seed))
            if seed == 222:
                assert len(puzzle.events) == 16 and any(e.kind == "peek" for e in puzzle.events)
            for dark in (0, 1):
                for phase in (1, 2, 4):
                    assert next(rows) == f"frame {rung} {seed} {dark} {phase} 4"
                    assert [next(rows) for _ in puzzle.choices] == [f"hit {i}" for i in range(len(puzzle.choices))]
                    assert next(rows) == "miss -1"
                    shapes, labels = [], []
                    while (row := next(rows)) != "end":
                        if row.startswith("shape "):
                            _, kind, colour, *coords = row.split()
                            shapes.append((int(kind), int(colour), *map(float, coords)))
                        else:
                            _, colour, x, y, size, text = row.split(maxsplit=5)
                            labels.append((int(colour), float(x), float(y), float(size), text))
                    source = Recorder(puzzle, dark, phase)
                    source._draw(*source._area())
                    for expected in source.shapes:
                        remove_matching(shapes, expected)
                    assert not shapes
                    for expected in source.text:
                        remove_matching(labels, expected)
                    for colour, x, top, size, caption, width in source.captions:
                        parts = [label for label in labels if label[0] == colour
                                 and isclose(label[1], x, abs_tol=0.0001)
                                 and isclose(label[3], size, abs_tol=0.0001)
                                 and label[2] <= top + 0.0001]
                        lines, current = [], ""
                        for part in parts:
                            candidate = f"{current} {part[-1]}" if current else part[-1]
                            if not caption.startswith(candidate):
                                continue
                            lines.append(part)
                            current = candidate
                            if current == caption:
                                break
                        assert current == caption, (rung, caption, current)
                        assert isclose(lines[0][2], top, abs_tol=0.0001)
                        assert all(len(line[-1]) * floor(size * 0.8 + 0.5) <= width for line in lines)
                        for line in lines:
                            labels.remove(line)
                    status = puzzle.question if phase != 2 else f"No: {puzzle.choices[puzzle.answer]}"
                    assert any(text == status for *_, text in labels)
                    if phase == 2:
                        assert any(colour == 0xFF4040FF and text == status for colour, *_, text in labels)
                    elif phase == 4:
                        assert any(colour == 0xFF4040FF and text == "Out of time" for colour, *_, text in labels)
        assert next(rows, None) is None
    finally:
        state.window = previous_window
    print("PASS: 36 Who Knows What? scenes matched Python panel geometry, labels, hit boxes, and verdicts")


if __name__ == "__main__":
    compare(sys.argv[1])
