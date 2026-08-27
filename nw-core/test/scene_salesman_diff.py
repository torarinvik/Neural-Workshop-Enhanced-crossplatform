#!/usr/bin/env python3
"""Differential harness for src/scene_salesman.elisa against the REAL screen.

The route length is swept from empty to the full tour because the three ends
of it draw differently: an empty route starts from no city at all (so no
circle is the bigger one), a one-city route has no closing edge even once the
tour is finished, and a full one has every edge and every circle recoloured.

`route[at] = (at * 3) % count` and not the identity, so an off-by-one in which
pair of cities an edge joins is visible rather than being the same picture.

SPDX-License-Identifier: GPL-2.0-or-later
"""
import sys

import scenediff

scenediff.reexec()

from neural_workshop import display, geometry, state                # noqa: E402
from neural_workshop.ui.salesman import TravelingSalesman           # noqa: E402

PHASES = {0: "ready", 1: "touring", 2: "toured", 3: "done"}


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
    screen = TravelingSalesman()
    count = spec["cities"]
    screen.cities = [(0.05 + 0.9 * ((index * 37) % 100) / 100.0,
                      0.05 + 0.9 * ((index * 61) % 100) / 100.0)
                     for index in range(count)]
    screen.route = [(at * 3) % count for at in range(count)][:spec["steps"]]
    screen.best_order = list(range(count))[::-1]
    screen.show_best = bool(spec["show_best"])
    screen.round = spec["round"]
    screen.total_rounds = spec["total_rounds"]
    screen.trial_cities = count
    screen.phase = PHASES[spec["phase"]]
    screen.message = 'Eight cities'
    if spec["verdict"] >= 0:
        screen.verdict_shown = (bool(spec["verdict"]),
                                'Right' if spec["verdict"] else 'No')
    return screen, screen._build_chrome


if __name__ == "__main__":
    sys.exit(scenediff.main(build))
