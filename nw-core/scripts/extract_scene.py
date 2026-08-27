"""Read one of the ORIGINAL's scenes and normalise it to reference space.

Run with the original's own interpreter -- it needs pyglet and a GL context:

    <original>/.venv/bin/python scripts/extract_scene.py <task-id> [options]

    --seed N        seed every generator before the task is built (default 0)
    --start         call the task's start_run(), which is what Space does
    --ticks N       drive N ticks after launching, capturing after each
    --out PATH      write the JSON here instead of stdout (a scene may hold
                    text in any language, and a pipe is not the place to find
                    out which)
    --black         BLACK_BACKGROUND
    --size W H      window size in reference units (default 912 684)
    --recorder DIR  where test/framerec.py lives

A note on the scale that is easy to get wrong and expensive to get wrong.

The numbers here are divided by the window's measured scale, so they are in
reference space -- but the reference COMPUTED them at physical resolution, and
some of its layout truncates. `int(x * window.width)` at 1824 is not twice
`int(x * window.width)` at 912. So a port that lays out in 912x684 and a port
that lays out in 1824x1368 and divides are not the same program, and only the
second one is this one. The scene code takes the PIXEL size, exactly as
`Geometry::from_width_center(width, offset)` already does, and the division
happens once at the end -- here and in the sweep, in the same place.

This is the general form of `extract_title.py` and `extract_menu.py`. Those
each read one screen by naming its widgets; there are forty-three more screens
and naming every widget of each is forty-three more chances to name one wrong.
So this names none of them: `test/framerec.py` wraps the drawing classes
themselves, and what comes out is whatever the scene actually built.

The two traps the older extractors document apply here unchanged:

  * The window pyglet hands back is retina-doubled, so every number lays out at
    twice its written value. The scale is MEASURED off the window rather than
    assumed, and framerec divides by it.
  * A flag is set and the scene rebuilt, rather than reasoned about.

SPDX-License-Identifier: GPL-2.0-or-later
"""
import json
import random
import sys

sys.path.insert(0, "tests")

# Must be installed before the application is built, which uisupport does on
# import -- the widgets are made once and then mutated, so a recorder that
# arrives afterwards sees an empty frame.
if "--recorder" in sys.argv:
    sys.path.insert(0, sys.argv[sys.argv.index("--recorder") + 1])
import framerec                                                    # noqa: E402
framerec.install()

import uisupport                                                   # noqa: E402

if uisupport.UI_IMPORT_ERROR is not None:
    print("UI_IMPORT_ERROR: %s" % (uisupport.UI_IMPORT_ERROR,), file=sys.stderr)
    raise SystemExit(2)

from neural_workshop import display, geometry, state                # noqa: E402
from neural_workshop.ui.taskhub import launch_task                  # noqa: E402


def flag(name, fallback=None):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else fallback


task = sys.argv[1]
seed = int(flag("--seed", 0))
ticks = int(flag("--ticks", 0))
width = 912.0
height = 684.0
if "--size" in sys.argv:
    at = sys.argv.index("--size")
    width, height = float(sys.argv[at + 1]), float(sys.argv[at + 2])

state.cfg.BLACK_BACKGROUND = "--black" in sys.argv
if state.cfg.BLACK_BACKGROUND:
    state.cfg.COLOR_TEXT = state.cfg.COLOR_TEXT_BLK

geometry.set_window_size(width, height)
display.relayout()

physical_w, physical_h = geometry._width(), geometry._height()
framerec.set_scale(physical_w / width, physical_h / height)

# Everything the scene deals comes off the module-level generator, so seeding
# it here is what makes a frame repeatable. The port seeds its own the same way.
random.seed(seed)

# n-back has no overlay: it IS the main screen, drawn out of `state.batch` by
# `events.on_draw`. Every other task builds its own widgets on top, so their
# frames start from nothing and n-back's starts from what bootstrap laid out.
main_screen = task == "nback"
if not main_screen:
    framerec.forget()

launch_task(task)


def live():
    """The task's overlay, or None for a screen that has no overlay."""
    open_now = display.open_overlays()
    return open_now[-1] if open_now else None


overlay = live()
if "--start" in sys.argv and overlay is not None:
    begin = getattr(overlay, "start_run", None)
    if begin is not None:
        begin()

frames = [framerec.capture()]
for _each in range(ticks):
    overlay = live()
    if overlay is not None:
        # Every task carries one of these two and no task carries both under
        # different meanings: `update` for the ones that animate, `step` for
        # the two grid walkers. Checked across all forty-four rather than
        # assumed from a handful.
        drive = getattr(overlay, "update", None) or getattr(overlay, "step", None)
        if drive is not None:
            drive(1.0 / 60.0)
    frames.append(framerec.capture())

payload = json.dumps({
    "task": task,
    "seed": seed,
    "started": "--start" in sys.argv,
    "reference": [width, height],
    "physical": [physical_w, physical_h],
    "frames": frames,
})
where = flag("--out")
if where:
    with open(where, "w", encoding="utf-8") as handle:
        handle.write(payload)
else:
    print(payload)
