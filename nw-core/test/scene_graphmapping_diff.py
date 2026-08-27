#!/usr/bin/env python3
"""Differential harness for src/scene_graphmapping.elisa against the REAL screen.

Two groups, and the buttons are SPLIT across them: the filled rectangle goes
in the line group and its label in the node group. So the frame comes out as
the divider, both graphs' edges, both buttons' rectangles, both graphs' nodes,
and only then both buttons' labels -- which is nothing like the order the
reference writes it in, and is what pyglet draws.

The layout is built upwards from the buttons rather than down from the top,
because they are filled in the accent blue and have to clear the band the
verdict reader owns.

SPDX-License-Identifier: GPL-2.0-or-later
"""
import sys

import scenediff

scenediff.reexec()

from neural_workshop import display, geometry, state                # noqa: E402
from neural_workshop.ui.graphmapping import GraphMapping            # noqa: E402

PHASES = {0: "ready", 1: "asking", 2: "hidden", 3: "feedback", 4: "done"}


class Graph:
    def __init__(self, size, edges):
        self.size = size
        self.edges = edges


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
    screen = GraphMapping()
    nodes, edges = spec["nodes"], spec["edges"]
    screen.graphs = [
        Graph(nodes, [(one % nodes, (one * 3 + 1) % nodes)
                      for one in range(edges)]),
        Graph(nodes, [((one * 2) % nodes, (one + 2) % nodes)
                      for one in range(edges)]),
    ]
    screen.spots = [
        [(0.09 + 0.1 * (node % 9), 0.11 + 0.09 * (node % 8))
         for node in range(nodes)],
        [(0.13 + 0.08 * (node % 7), 0.17 + 0.11 * (node % 6))
         for node in range(nodes)],
    ]
    screen.trial = spec["trial"]
    screen.total_trials = spec["total_trials"]
    screen.correct = spec["right"]
    screen.phase = PHASES[spec["phase"]]
    screen.message = 'The same network?'
    if spec["verdict"] >= 0:
        screen.verdict_shown = (bool(spec["verdict"]),
                                'Right' if spec["verdict"] else 'No')
    return screen, screen._build_chrome


if __name__ == "__main__":
    sys.exit(scenediff.main(build))
