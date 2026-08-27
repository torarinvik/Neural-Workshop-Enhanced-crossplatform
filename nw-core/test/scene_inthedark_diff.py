#!/usr/bin/env python3
"""Differential harness for src/scene_inthedark.elisa against the REAL screen.

Four room kinds and four diagrams, and the only difference between a swap and
a copy is whether the arrow between two sockets has a head on both ends -- so
all four are swept, and the arrowheads are Triangles, which the recorder reads
back off the constructor rather than off pyglet's own getter.

`given` is swept shorter than `asked` because a scored round can still have
the last lamp unanswered: the row for it is skipped and the row NUMBER still
advances, so the truth stays on the lower row rather than moving up.

SPDX-License-Identifier: GPL-2.0-or-later
"""
import sys

import scenediff

scenediff.reexec()

from neural_workshop import display, geometry, state                # noqa: E402
from neural_workshop.inthedark import COPY, PAINT, SWAP, TURN       # noqa: E402
from neural_workshop.ui.inthedark import InTheDark                  # noqa: E402

PHASES = {0: "ready", 1: "walking", 2: "asking", 3: "scored", 4: "done"}
KINDS = (PAINT, TURN, SWAP, COPY)


class Chamber:
    def __init__(self, kind, lamp, other):
        self.kind = kind
        self.lamp = lamp
        self.other = other


class Bout:
    """Only what `_redraw` and its four helpers read off a Round."""

    def __init__(self, lamps, colours, rooms, kind, lamp, other, cursor,
                 asked, answers):
        self.lamps = lamps
        self.colours = colours
        # Only the room under the cursor is ever drawn, so the rest are
        # placeholders that keep the count honest for the status line.
        self.rooms = [Chamber(kind, lamp, other) for _ in range(rooms)]
        self.asked = asked
        self.answers = answers


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
    screen = InTheDark()
    lamps, colours = spec["lamps"], spec["colours"]
    asked = [(one * 2 + 1) % lamps for one in range(spec["asked"])]
    answers = [(one * 3) % colours for one in range(spec["asked"])]
    bout = Bout(lamps, colours, spec["rooms"], KINDS[spec["kind"]],
                spec["room_lamp"], spec["room_other"], spec["cursor"],
                asked, answers)
    screen.round = bout if spec["has_round"] else None
    screen.cursor = spec["cursor"]
    screen.given = [(one * 3 + one % 2) % colours
                    for one in range(spec["given"])]
    screen.asking_at = spec["asking_at"]
    screen.trial = spec["trial"]
    screen.total_trials = spec["total_trials"]
    screen.phase = PHASES[spec["phase"]]
    screen.message = 'Rung 3 - three rooms'
    if spec["verdict"] >= 0:
        screen.verdict_shown = (bool(spec["verdict"]),
                                'Right' if spec["verdict"] else 'No')
    return screen, screen._build_chrome


if __name__ == "__main__":
    sys.exit(scenediff.main(build))
