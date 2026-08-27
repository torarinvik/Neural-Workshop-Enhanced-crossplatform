#!/usr/bin/env python3
"""Differential harness for src/scene_tetris.elisa against the REAL screen.

Five groups, and the order between them is the whole picture: the well and
its guides, the settled pile, the ghost of where the piece would land, the
piece in the air, and the tray. Never the order the reference writes them in.

The piece in the air is the one thing in the workshop that TURNS, so the
display list grew a rotation for it -- carried in a rectangle's `ref`, the
only field a RECT has left. The swept angles are not multiples of ninety, so
the turn is a real rotation rather than one that happens to line up.

The status and the readout are SENTENCES the controller assembles, so the
sweep names them and the reference is handed the same two strings. What is
under test is the SHRINK: two measured passes that scale the size down until
the line fits 96% of the window.

The board, the queue and the piece are the model's, and the model has a suite
of its own; what is set here is what it would have returned.

SPDX-License-Identifier: GPL-2.0-or-later
"""
import os
import re
import sys

import scenediff

scenediff.reexec()

from neural_workshop import display, geometry, state, tetris        # noqa: E402
from neural_workshop.ui import tetris as tetris_ui                  # noqa: E402
from neural_workshop.ui.tetris import FreeformTetris                # noqa: E402

PHASES = {0: "ready", 1: "falling", 2: "landed", 3: "done"}

SWEEP = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     "scene_tetris_sweep.elisa")
SOURCE = open(SWEEP).read()
SLOTS = int(re.search(r"const SLOTS: i64 = (\d+)", SOURCE).group(1))
STATUS = re.search(r'const STATUS: cstr = "((?:[^"\\]|\\.)*)"',
                   SOURCE).group(1)
READOUT = re.search(r'const READOUT: cstr = "((?:[^"\\]|\\.)*)"',
                    SOURCE).group(1)
FITS = [int(one) for one in
        re.findall(r"return (\d+)",
                   SOURCE.split("def fits_of(which: i64) -> i64:")[1]
                   .split("\n\n")[0])]
RECUT = [index in (1, 4) for index in range(SLOTS)]


class Board:
    def __init__(self, cols, rows, filled):
        self.cols = cols
        self.rows = rows
        self.cells = [[0] * cols for _ in range(rows)]
        for index in range(filled):
            self.cells[(index * 3) % rows][(index * 5) % cols] = 1 + index % 7


class Queue:
    """Only what `_paint_queue` reads off a Queue."""

    def __init__(self, piece_size):
        self.pieces = []
        for slot in range(SLOTS):
            count = piece_size + slot % 2
            cells = [(0, step) for step in range(count - 1)]
            cells.append((1, count - 2))
            self.pieces.append(tuple(sorted(cells)))
        self.fits = list(FITS)
        self.recut = list(RECUT)

    def __len__(self):
        return len(self.pieces)


def build(spec):
    import framerec
    geometry.set_window_size(912, spec["tall"] // 2)
    display.relayout()
    if (geometry._width(), geometry._height()) != (1824, spec["tall"]):
        raise SystemExit("asked for 1824x%d pixels, got %dx%d"
                         % (spec["tall"], geometry._width(), geometry._height()))
    framerec.set_scale(geometry._width() / 912.0,
                       geometry._height() / (spec["tall"] / 2.0))
    state.cfg.BLACK_BACKGROUND = bool(spec["black"])
    screen = FreeformTetris()
    cols, rows = spec["cols"], spec["rows"]
    screen.cols, screen.rows = cols, rows
    screen.board = Board(cols, rows, spec["cells"])
    screen.queue = Queue(spec["piece_size"])
    screen.armed = spec["armed"]
    screen.phase = PHASES[spec["phase"]]
    screen.show_ghost = True

    shadow = [((index * 7) % cols, (index * 2) % rows)
              for index in range(spec["ghost"])]
    air = [((index * 3) % cols + 0.5, (index * 5) % rows + 0.5)
           for index in range(spec["flying"])]
    if spec["flying"]:
        screen.piece = tuple((0, one) for one in range(spec["flying"]))
        screen.pose = tetris.Pose(spec["angle"], 0.0, 0.0)
    else:
        screen.piece = None
        screen.pose = None
    def sync_labels():
        screen._retext(screen.status,
                       STATUS if spec["status"] else '', screen.status_size)
        screen._retext(screen.readout,
                       READOUT if spec["readout"] else '',
                       screen.readout_size)
    screen._sync_labels = sync_labels

    if spec["verdict"] >= 0:
        screen.verdict_shown = (bool(spec["verdict"]),
                                'Right' if spec["verdict"] else 'No')

    # The four model calls are replaced only WHILE the screen lays out and
    # put back afterwards. They live on the shared module, and a run that left
    # them patched had the next spec's own Queue built against them -- which
    # is a different error, several frames later, about the wrong thing.
    names = ('settle', 'footprint', 'gaps_under', 'centres')
    stubs = {
        'settle': lambda _board, _piece, pose: pose,
        'footprint': lambda _piece, _pose: set(shadow),
        'gaps_under': lambda _board, _shadow, *rest: (
            0 if spec["clean"] else 2),
        'centres': lambda _piece, _pose: air,
    }

    def lay_out():
        held = {name: getattr(tetris, name) for name in names}
        for name in names:
            setattr(tetris, name, stubs[name])
        try:
            screen._build_chrome()
        finally:
            for name, was in held.items():
                setattr(tetris, name, was)
    return screen, lay_out


if __name__ == "__main__":
    sys.exit(scenediff.main(build))
