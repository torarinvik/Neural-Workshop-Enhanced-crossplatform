#!/usr/bin/env python3
"""The pyglet shell: the Elisa core's frames in a real window.

    python3 shells/python/app.py                    # a window; SPACE steps a trial
    python3 shells/python/app.py --screen menu      # the game-mode menu
    python3 shells/python/app.py --screen title     # the title screen
    python3 shells/python/app.py --screenshot out.png
    python3 shells/python/app.py --dump             # canonical frame text, no window

Frames come from the Elisa core itself. `nwcore.nback_frame()`, `title_frame()`
and `menu_frame()` each return one encoded display list as `bytes` (build them
with scripts/build_pymodule.sh);
renderer.py decodes and draws it. Nothing about the game's appearance is
decided here -- this file owns a window, a keyboard and a clock, and that is
the whole point of the display-list seam.

The trial walk is byte-for-byte the same deterministic sequence shells/web/
index.html uses, so the two shells can be put side by side on the same frame.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parents[1]                       # nw-core/
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from renderer import Renderer, Viewport, decode  # noqa: E402

BUILD_HINT = ("nwcore is not built: run scripts/build_pymodule.sh "
              f"(expected {_ROOT / 'build' / 'pymod'})")


def load_core(entry: str = "nback_frame"):
    """The Elisa core, as a CPython extension."""
    pymod = _ROOT / "build" / "pymod"
    if str(pymod) not in sys.path:
        sys.path.insert(0, str(pymod))
    try:
        import nwcore                                              # noqa: PLC0415
    except ImportError as error:
        raise SystemExit(f"{BUILD_HINT}\n  ({error})") from error
    if not hasattr(nwcore, entry):
        raise SystemExit(f"nwcore has no {entry}(); rebuild with "
                         "scripts/build_pymodule.sh")
    return nwcore


class Session:
    """The deterministic walk index.html uses, with a history so it can rewind.

    Not the real session engine -- that lands when scheduling and stimulus are
    wired together. It exists so the shell shows the board CHANGING, and so a
    given trial number names the same frame in every shell.
    """

    def __init__(self, nback: int = 2) -> None:
        self.nback = nback
        self.states = [(1, 4, -1)]              # (trial, position, verdict)
        self.index = 0

    @property
    def state(self):
        return self.states[self.index]

    def advance(self) -> None:
        if self.index + 1 < len(self.states):
            self.index += 1
            return
        trial, position, _verdict = self.state
        trial += 1
        position = 1 + ((position * 3 + trial) % 8)
        verdict = -1 if trial % 4 == 0 else trial % 3
        self.states.append((trial, position, verdict))
        self.index += 1

    def back(self) -> None:
        self.index = max(0, self.index - 1)

    def seek(self, trial: int) -> None:
        while self.state[0] < trial:
            self.advance()
        while self.state[0] > trial and self.index:
            self.back()

    def frame_bytes(self, core) -> bytes:
        trial, position, verdict = self.state
        return core.nback_frame(trial, self.nback, position, verdict)

    def describe(self, frame) -> str:
        trial, position, _verdict = self.state
        return f"trial {trial} - position {position} - verdict {frame.verdict_name}"


class MenuSession:
    """The game-mode menu, walked one selectable row at a time.

    The core owns the row list; all this holds is which row the marker is on,
    and it wraps rather than clamps so the walk cannot get stuck at an end.
    """

    ROWS = 24                                   # selectable rows in gameselect

    def __init__(self, black_background: bool = False) -> None:
        self.black_background = black_background
        self.index = 0

    @property
    def state(self):
        return (self.index,)

    def advance(self) -> None:
        self.index = (self.index + 1) % self.ROWS

    def back(self) -> None:
        self.index = (self.index - 1) % self.ROWS

    def seek(self, position: int) -> None:
        self.index = max(0, min(self.ROWS - 1, position - 1))

    def frame_bytes(self, core) -> bytes:
        return core.menu_frame(self.index, 1 if self.black_background else 0)

    def describe(self, _frame) -> str:
        return f"row {self.index + 1}/{self.ROWS}"


class TitleSession:
    """The title screen, walked through its banner variants."""

    BANNERS = 4

    def __init__(self, black_background: bool = False, jaeggi: bool = False,
                 clinical: bool = False) -> None:
        self.black_background = black_background
        self.jaeggi = jaeggi
        self.clinical = clinical
        self.banner = 0

    @property
    def state(self):
        return (self.banner,)

    def advance(self) -> None:
        self.banner = (self.banner + 1) % self.BANNERS

    def back(self) -> None:
        self.banner = (self.banner - 1) % self.BANNERS

    def seek(self, position: int) -> None:
        self.banner = max(0, min(self.BANNERS - 1, position - 1))

    def frame_bytes(self, core) -> bytes:
        return core.title_frame(self.banner, 1 if self.black_background else 0,
                                1 if self.jaeggi else 0, 1 if self.clinical else 0)

    def describe(self, _frame) -> str:
        return f"banner {self.banner}"


SCREENS = {"nback": ("nback_frame", lambda args: Session(args.nback)),
           "menu": ("menu_frame", lambda args: MenuSession(args.black_background)),
           "title": ("title_frame", lambda args: TitleSession(args.black_background))}


def dump(core, session: Session, trials: int) -> int:
    """Print each frame in the canonical text form the tests diff on."""
    from display_decode import canonical                            # noqa: PLC0415
    for _ in range(trials):
        blob = session.frame_bytes(core)
        print(f"# state={session.state} bytes={len(blob)}")
        for line in canonical(decode(blob)):
            print("  " + line)
        session.advance()
    return 0


def run_window(core, session, width: int, height: int,
               screenshot: str | None, screen: str = "nback") -> int:
    import pyglet                                                   # noqa: PLC0415
    from pyglet.window import key                                   # noqa: PLC0415

    window = pyglet.window.Window(width=width, height=height, resizable=True,
                                  caption=f"Neural Workshop - {screen} - pyglet shell")
    # The letterbox bars, not the field: the display list paints its own black
    # background over the 912x684 area, so anything visible here is outside it.
    pyglet.gl.glClearColor(0.08, 0.086, 0.102, 1.0)

    renderer = Renderer(Viewport.from_window(window))
    hud = pyglet.text.Label("", x=8, y=8, font_size=11, color=(154, 164, 178, 255))

    def draw_frame():
        blob = session.frame_bytes(core)
        frame = renderer.render_bytes(blob)
        viewport = renderer.viewport
        # The HUD is the shell's own chrome, not the core's, but it still has to
        # follow the display: on a 2x screen window coordinates are physical
        # pixels, so a fixed 11pt label would come out half the size it looks
        # like here.
        hud.font_size = max(9.0, 11.0 * viewport.pixel_ratio)
        hud.x = hud.y = 8.0 * viewport.pixel_ratio
        hud.text = (f"{session.describe(frame)} - {len(frame.ops)} ops - "
                    f"{len(blob)} bytes - scale {viewport.scale:.3f} "
                    f"- dpr {viewport.pixel_ratio:g}")
        return frame

    draw_frame()

    @window.event
    def on_draw():
        window.clear()
        renderer.draw()
        hud.draw()

    @window.event
    def on_resize(new_width, new_height):
        # Straight from the window: dragging between a Retina and a non-Retina
        # display changes the ratio as well as the size.
        renderer.viewport = Viewport.from_window(window)
        draw_frame()

    @window.event
    def on_key_press(symbol, _modifiers):
        if symbol in (key.SPACE, key.RIGHT, key.RETURN, key.DOWN):
            session.advance()
            draw_frame()
        elif symbol in (key.LEFT, key.UP):
            session.back()
            draw_frame()
        elif symbol == key.ESCAPE:
            window.close()

    if screenshot:
        # One frame, saved, then out -- so this shell can produce an artefact to
        # diff against the browser without a human at the keyboard. The save
        # happens after a draw and a flip, or the colour buffer is still empty.
        def shoot(_dt):
            window.switch_to()
            window.dispatch_event("on_draw")
            window.flip()
            pyglet.image.get_buffer_manager().get_color_buffer().save(screenshot)
            print(f"wrote {screenshot}")
            pyglet.app.exit()
        pyglet.clock.schedule_once(shoot, 0.3)

    pyglet.app.run()
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--width", type=int, default=912)
    parser.add_argument("--height", type=int, default=684)
    parser.add_argument("--screen", choices=sorted(SCREENS), default="nback",
                        help="which screen the core should draw")
    parser.add_argument("--nback", type=int, default=2)
    parser.add_argument("--black-background", action="store_true",
                        help="the dark theme, for the screens that have one")
    parser.add_argument("--trial", type=int, default=1,
                        help="start here: trial number, or menu row / banner")
    parser.add_argument("--screenshot", metavar="PNG",
                        help="render one frame to PNG and exit")
    parser.add_argument("--dump", action="store_true",
                        help="print frames as canonical text; opens no window")
    parser.add_argument("--trials", type=int, default=1,
                        help="how many frames --dump prints")
    args = parser.parse_args(argv)

    entry, build_session = SCREENS[args.screen]
    core = load_core(entry)
    session = build_session(args)
    session.seek(args.trial)

    if args.dump:
        return dump(core, session, args.trials)
    return run_window(core, session, args.width, args.height, args.screenshot,
                      args.screen)


if __name__ == "__main__":
    sys.exit(main())
