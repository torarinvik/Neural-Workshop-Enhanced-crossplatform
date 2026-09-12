#!/usr/bin/env python3
"""The pyglet shell: the Elisa core's frames in a real window.

    python3 shells/python/app.py                    # a window; SPACE steps a trial
    python3 shells/python/app.py --screen menu      # the game-mode menu
    python3 shells/python/app.py --screen session   # the assembled workshop batch
    python3 shells/python/app.py --screen title     # the title screen
    python3 shells/python/app.py --screenshot out.png
    python3 shells/python/app.py --dump             # canonical frame text, no window

Frames come from the Elisa core itself. `nwcore.nback_session_frame()`,
`nwcore.batch_frame()`, `title_frame()` and `menu_frame()` each return one encoded display list as `bytes` (build them
with scripts/build_pymodule.sh);
renderer.py decodes and draws it. Nothing about the game's appearance is
decided here -- this file owns a window, a keyboard and a clock, and that is
the whole point of the display-list seam.

The n-back screen asks the Elisa session generator for a seeded trial. The
host still owns the window and clock; the core owns stimulus history and
randomness.
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
    """A rewindable view onto the core's seeded session generator."""

    def __init__(self, nback: int = 2, seed: int = 1, mode: int = 2) -> None:
        self.nback = nback
        self.seed = seed
        self.mode = mode
        self.trial = 1
        self.verdict = -1

    @property
    def state(self):
        return (self.trial, self.mode, self.nback, self.seed, self.verdict)

    def advance(self) -> None:
        self.trial += 1

    def back(self) -> None:
        self.trial = max(1, self.trial - 1)

    def seek(self, trial: int) -> None:
        self.trial = max(1, trial)

    def frame_bytes(self, core) -> bytes:
        return core.nback_session_frame(self.trial, self.nback, self.seed,
                                        self.mode, self.verdict)

    def describe(self, frame) -> str:
        return (f"trial {self.trial} - mode {self.mode} - n-back {self.nback} "
                f"- seed {self.seed} - verdict {frame.verdict_name}")


class MenuSession:
    """The game-mode menu, with the same edit/select controls as the app.

    The core owns the row layout and text formatting. The shell owns the
    provisional values until Enter applies them, because the real app's config
    object is not across this display-list boundary yet.
    """

    ROWS = 24                                   # selectable rows in gameselect
    SPACERS = frozenset((6, 8, 13, 17, 20, 22))
    BOOL_BITS = {0: 0, 1: 1, 2: 2, 3: 3, 4: 4, 5: 5,
                 7: 6, 9: 7, 10: 8, 11: 9, 21: 10}
    CYCLES = {
        12: (1, 2, 3, 4, 5, 6),
        14: (3, 4, 5, 6, 7, 8),
        15: (0, 2, 3, 4, 6, 8, 12, 16, 24, 32, 64),
        16: (1, 2, 5, 10, 16, 20, 25, 33, 50, 75, 100, 150, 200,
             250, 333, 500, 750, 1000, 1500, 2000, 2500, 3000, 4000, 5000),
        18: (1, 2, 3, 4),
        19: (0, 1),
        23: (0, 125, 250, 375, 500, 625, 750, 875, 1000),
    }
    NAMES = {
        0: "Use position", 1: "Use color", 2: "Use image", 3: "Use audio",
        4: "Use audio2", 5: "Use arithmetic", 7: "Combination N-back mode",
        9: "Use variable N-Back levels",
        10: "Crab-back mode (reverse order of sets of N stimuli)",
        11: "3D face-pattern mode", 12: "Cubes in 3D pattern",
        14: "2D grid size", 15: "Active 2D position cells",
        16: "Trial interval (ms)", 18: "Simultaneous visual stimuli",
        19: "Simultaneous stimuli differentiated by", 21: "Self-paced mode",
        23: "Interference (tricky stimulus generation)",
    }

    def __init__(self, black_background: bool = False) -> None:
        self.black_background = black_background
        self.index = 0
        self.applied = False
        self.values = {row: False for row in self.BOOL_BITS}
        self.values[0] = True
        self.values.update({row: choices[0] for row, choices in self.CYCLES.items()})

    @property
    def state(self):
        return (self.index, self.applied, self.bool_mask(), self.values[12],
                self.values[14], self.values[15], self.values[16],
                self.values[18], self.values[19], self.values[23])

    def bool_mask(self) -> int:
        mask = 0
        for row, bit in self.BOOL_BITS.items():
            if self.values[row]:
                mask |= 1 << bit
        return mask

    def _move(self, step: int) -> None:
        for _ in range(self.ROWS):
            self.index = (self.index + step) % self.ROWS
            if self.index not in self.SPACERS:
                self.applied = False
                return

    def advance(self) -> None:
        self._move(1)

    def back(self) -> None:
        self._move(-1)

    def seek(self, position: int) -> None:
        self.index = max(0, min(self.ROWS - 1, position - 1))
        if self.index in self.SPACERS:
            self._move(1 if position < self.ROWS else -1)
        self.applied = False

    def modify(self, step: int = 1) -> None:
        if self.index in self.SPACERS:
            return
        if self.index in self.BOOL_BITS:
            self.values[self.index] = not self.values[self.index]
        elif self.index in self.CYCLES:
            choices = self.CYCLES[self.index]
            current = choices.index(self.values[self.index])
            self.values[self.index] = choices[(current + (1 if step >= 0 else -1)) % len(choices)]
        self.applied = False

    def apply(self) -> None:
        self.applied = True

    def frame_bytes(self, core) -> bytes:
        return core.menu_state_frame(
            self.index, 1 if self.black_background else 0, self.bool_mask(),
            self.values[12], self.values[14], self.values[15], self.values[16],
            self.values[18], self.values[19], self.values[23])

    def describe(self, _frame) -> str:
        action = "applied" if self.applied else "editing"
        return f"menu · {action} · row {self.index + 1}/{self.ROWS} · {self.NAMES.get(self.index, 'spacer')}"


class BatchSession(Session):
    """The complete field/HUD/readout/trial-UI composition."""

    def __init__(self, nback: int = 2, seed: int = 1, mode: int = 2,
                 black_background: bool = False) -> None:
        super().__init__(nback, seed, mode)
        self.black_background = black_background
        self.started = True
        self.hide_text = False
        self.paused = False
        self.grid_3d = False
        self.expanded = False
        self.gridlines = True
        self.old_style = False
        self.sharp_corners = False
        self.session_number = 0
        self.input_answer = 0

    @property
    def state(self):
        return (self.trial, self.mode, self.nback, self.seed,
                self.started, self.hide_text, self.paused, self.verdict)

    def frame_bytes(self, core) -> bytes:
        return core.batch_frame(
            self.trial, self.nback, self.seed, self.mode,
            1 if self.black_background else 0,
            1 if self.started else 0,
            1 if self.hide_text else 0,
            1 if self.paused else 0,
            1 if self.grid_3d else 0,
            1 if self.expanded else 0,
            1 if self.gridlines else 0,
            1 if self.old_style else 0,
            1 if self.sharp_corners else 0,
            self.session_number, self.verdict, self.input_answer)

    def describe(self, frame) -> str:
        return (f"batch trial {self.trial} - mode {self.mode} - n-back {self.nback} "
                f"- seed {self.seed} - verdict {frame.verdict_name}")


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


SCREENS = {"nback": ("nback_session_frame", lambda args: Session(args.nback, args.seed, args.mode)),
           "session": ("batch_frame", lambda args: BatchSession(args.nback, args.seed, args.mode, args.black_background)),
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
        if isinstance(session, MenuSession):
            if symbol == key.SPACE:
                session.modify()
                draw_frame()
            elif symbol in (key.RETURN, key.ENTER):
                session.apply()
                draw_frame()
            elif symbol == key.ESCAPE:
                window.close()
            return
        if symbol in (key.SPACE, key.RIGHT, key.RETURN, key.DOWN):
            session.advance()
            draw_frame()
        elif symbol in (key.LEFT, key.UP):
            session.back()
            draw_frame()
        elif symbol == key.ESCAPE:
            window.close()

    @window.event
    def on_text_motion(motion):
        if not isinstance(session, MenuSession):
            return
        if motion == key.MOTION_UP:
            session.back()
        elif motion == key.MOTION_DOWN:
            session.advance()
        elif motion == key.MOTION_PREVIOUS_PAGE:
            for _ in range(8):
                session.back()
        elif motion == key.MOTION_NEXT_PAGE:
            for _ in range(8):
                session.advance()
        elif motion == key.MOTION_LEFT:
            session.modify(-1)
        elif motion == key.MOTION_RIGHT:
            session.modify(1)
        else:
            return
        draw_frame()

    @window.event
    def on_mouse_press(x, y, _button, _modifiers):
        if not isinstance(session, MenuSession):
            return
        ref_x = (x - renderer.viewport.offset_x) / renderer.viewport.scale
        ref_y = (y - renderer.viewport.offset_y) / renderer.viewport.scale
        if ref_x < 0 or ref_x > 900:
            return
        row = round((547.2 - ref_y) / 18.0)
        if not 0 <= row < session.ROWS or row in session.SPACERS:
            return
        if row in session.SPACERS:
            return
        if row == session.index:
            session.modify()
        else:
            session.seek(row + 1)
        draw_frame()

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
    parser.add_argument("--mode", type=int, default=2,
                        help="core n-back mode (2 is position + audio)")
    parser.add_argument("--seed", type=int, default=1,
                        help="seed for the core session generator")
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
