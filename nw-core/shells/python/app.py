#!/usr/bin/env python3
"""The pyglet shell for the current port boundary.

    python3 shells/python/app.py                    # open the title screen
    python3 shells/python/app.py --screen title     # explicit title screen
    python3 shells/python/app.py --screen you-are-here  # native 3D Maze
    python3 shells/python/app.py --screen sokoban       # native Sokoban
    python3 shells/python/app.py --screen monkey-ladder # native Monkey Ladder
    python3 shells/python/app.py --screen tetris       # native Freeform Tetris
    python3 shells/python/app.py --screen count        # native Count
    python3 shells/python/app.py --screen mr-time      # native Mr. Time
    python3 shells/python/app.py --screen graph-mapping # native Graph Mapping
    python3 shells/python/app.py --screen matrix-reasoning # native Matrix Reasoning
    python3 shells/python/app.py --screen nback3d      # native 3D N-Back
    python3 shells/python/app.py --screen marble       # native Marble controller/fallback
    python3 shells/python/app.py --screenshot out.png
    python3 shells/python/app.py --dump             # canonical frame text

The browser remains the authority for the complete task registry. The native
Python shell exposes the shared title contract and its implemented subset of
source-backed controllers, including Sudoku and Jigsaw. Sudoku accepts
``--sudoku-level``, ``--sudoku-puzzles``, ``--sudoku-no-clashes``, and
``--sudoku-no-adaptive``; Jigsaw accepts the corresponding ``--jigsaw-*``
settings. Other task routes remain unavailable until they have the same real
state and lifecycle implementation.
"""
from __future__ import annotations

import argparse
import json
import tempfile
import uuid
import math
import os
import sys
import time
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parents[1]                       # nw-core/
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from renderer import Renderer, SOURCE_FONT_FAMILIES, Viewport, decode

BUILD_HINT = ("nwcore is not built: run scripts/build_pymodule.sh "
              f"(expected {_ROOT / 'build' / 'pymod'})")


def load_core(entry: str = "title_frame"):
    """Load the Elisa display-list extension and require one safe entry point."""
    pymod = Path(os.environ.get("ELISA_PYMODULE_DIR", _ROOT / "build" / "pymod"))
    if str(pymod) not in sys.path:
        sys.path.insert(0, str(pymod))
    try:
        import nwcore
    except ImportError as error:
        raise SystemExit(f"{BUILD_HINT} ({error})") from error
    if not hasattr(nwcore, entry):
        raise SystemExit(f"nwcore has no {entry}(); rebuild with "
                         "scripts/build_pymodule.sh")
    return nwcore


class TitleSession:
    """The port title screen, walked through its banner variants."""

    BANNERS = 4

    def __init__(self, black_background: bool = False) -> None:
        self.black_background = black_background
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
        # The source title renderer's Jaeggi/clinical presentation omits the
        # original-only accelerator block. Use it deliberately for the port
        # shell so the native title cannot advertise unavailable routes.
        return core.title_frame(self.banner, 1 if self.black_background else 0,
                                1, 1)

    def describe(self, _frame) -> str:
        return f"title banner {self.banner}"


class NBack3DSession:
    """Native Python adapter for the port-scoped 3D-only N-Back."""
    ACTION_START, ACTION_MATCH, ACTION_TICK = 0, 1, 2
    ACTION_PAUSE, ACTION_RESTART = 3, 4
    INFO_PHASE, INFO_TRIAL, INFO_HITS, INFO_MISSES = 0, 2, 9, 10

    def __init__(self, core, args) -> None:
        self.core = core
        self.handle = core.nback3d_create(
            2, 1, 24, 3000, 500, 200, args.seed)
        if self.handle <= 0:
            raise SystemExit("native 3D N-Back rejected its options")
        self.black_background = args.black_background

    @property
    def state(self):
        return tuple(self.core.nback3d_info(self.handle, field)
                     for field in range(20))

    def frame_bytes(self, _core, width=912, height=684) -> bytes:
        return self.core.nback3d_frame(
            self.handle, 1 if self.black_background else 0, width, height)

    def describe(self, _frame) -> str:
        current = self.state
        return (f"3D N-Back · phase {current[self.INFO_PHASE]} · "
                f"trial {current[self.INFO_TRIAL]} · hits {current[self.INFO_HITS]}"
                f" · misses {current[self.INFO_MISSES]}")

    def action(self, action: int, now_ms: int = 0) -> None:
        self.core.nback3d_action(self.handle, action, now_ms)

    def tick(self, now_ms: int) -> None:
        self.core.nback3d_advance(self.handle, now_ms)

    def key(self, symbol, key) -> None:
        if symbol in (key.SPACE, key.RETURN):
            self.action(self.ACTION_START)
        elif symbol == key.A:
            self.action(self.ACTION_MATCH)
        elif symbol == key.P:
            self.action(self.ACTION_PAUSE, int(time.monotonic() * 1000))
        elif symbol == key.R:
            self.action(self.ACTION_RESTART, int(time.monotonic() * 1000))

    def close(self) -> None:
        if self.handle > 0:
            self.core.nback3d_destroy(self.handle)
            self.handle = 0


class MarbleMazeSession:
    """Native Marble controller, MuJoCo and source-board lifecycle adapter."""
    ACTION_START, ACTION_RESTART, ACTION_LEVEL = 0, 1, 2
    ACTION_REPORT, ACTION_BOARD_READY = 3, 4
    ACTION_NEXT = 5
    ACTION_HOLD_NORTH, ACTION_HOLD_EAST = 6, 7
    ACTION_HOLD_SOUTH, ACTION_HOLD_WEST = 8, 9
    ACTION_SCORE, ACTION_SYNC_SETTLE_TIME, ACTION_RECORD_RESULT = 10, 11, 12
    INFO_PHASE, INFO_RUNG, INFO_TRIAL, INFO_TOTAL_TRIALS = 0, 1, 2, 3
    INFO_BOARD_GENERATION, INFO_BOARD_SEED = 4, 5
    INFO_ELAPSED = 6
    INFO_REMAINING, INFO_VERDICT, INFO_HELD = 7, 8, 11

    def __init__(self, core, args) -> None:
        self.core = core
        self.handle = core.marble_create(
            getattr(args, "marble_start_rung", 1),
            args.trials,
            1 if args.adaptive else 0,
                                         2600, 0, args.seed)
        if self.handle <= 0:
            raise SystemExit("native Marble Maze rejected its options")
        self.black_background = args.black_background
        self.last_ms = time.monotonic() * 1000.0
        self.physics = None
        self.board = None
        self.grain_seed = 0.0
        self.board_generation = -1
        self.native_physics = False
        self.held_directions: set[str] = set()

    def enable_native_physics(self) -> None:
        """Select the real native MuJoCo path for the visible Pyglet shell."""
        self.native_physics = True
        self._sync_board()

    def _sync_board(self) -> None:
        state = self.state
        phase = state[self.INFO_PHASE]
        if phase not in (1, 2, 3):
            return
        generation = state[self.INFO_BOARD_GENERATION]
        if generation != self.board_generation:
            self._dispose_physics()
            from marble_mujoco import MuJoCoMarblePhysics, decode_board
            self.board = decode_board(self.board_bytes)
            self.physics = MuJoCoMarblePhysics(self.board)
            self.grain_seed = float(self.core.marble_grain_seed(self.handle))
            if not 0.0 <= self.grain_seed < 4.0:
                self._dispose_physics()
                raise RuntimeError("Marble Maze grain-seed ABI returned an invalid value")
            self.board_generation = generation
        if phase == 3:
            status = self.core.marble_action(self.handle, self.ACTION_BOARD_READY, 0, 0)
            if status != 1:
                raise RuntimeError(f"Marble Maze board-ready action failed ({status})")

    def _dispose_physics(self) -> None:
        if self.physics is not None:
            self.physics.close()
        self.physics = None
        self.board = None
        self.grain_seed = 0.0

    def _commit_result(self) -> None:
        if self.physics is None:
            raise RuntimeError("Marble Maze cannot commit a result without physics")
        status = self.core.marble_action(
            self.handle, self.ACTION_RECORD_RESULT,
            self.physics.home, self.physics.lost)
        if status != 1:
            raise RuntimeError(f"Marble Maze result-history action failed ({status})")

    def _report_settled(self) -> None:
        if self.physics is None or self.board is None:
            return
        elapsed_ms = max(0, min(600050, round(self.physics.elapsed * 1000)))
        status = self.core.marble_action(
            self.handle, self.ACTION_SYNC_SETTLE_TIME, elapsed_ms, 0)
        if status != 1:
            raise RuntimeError(f"Marble Maze settle-time synchronization failed ({status})")
        result_bits = (1 if self.physics.won else 0) | (2 if self.physics.lost == 0 else 0)
        par_ms = round((self.board.route / 0.25 + 2.5 * len(self.physics.marbles)) * 1000)
        status = self.core.marble_action(self.handle, self.ACTION_REPORT, result_bits, par_ms)
        if status != 1:
            raise RuntimeError(f"Marble Maze physical result action failed ({status})")
        self.held_directions.clear()
        self._commit_result()

    def _commit_timeout_score(self) -> None:
        if self.physics is None:
            return
        elapsed_ms = max(0, min(600050, round(self.physics.elapsed * 1000)))
        status = self.core.marble_action(
            self.handle, self.ACTION_SYNC_SETTLE_TIME, elapsed_ms, 0)
        if status != 1:
            raise RuntimeError(f"Marble Maze timeout-time synchronization failed ({status})")
        status = self.core.marble_action(
            self.handle, self.ACTION_SCORE, 1 if self.physics.lost == 0 else 0, 0)
        if status != 1:
            raise RuntimeError(f"Marble Maze timeout score action failed ({status})")
        self.held_directions.clear()
        self._commit_result()

    @property
    def state(self):
        return tuple(self.core.marble_info(self.handle, field)
                     for field in range(13))

    @property
    def board_bytes(self) -> bytes:
        current = self.state
        return self.core.marble_board(current[self.INFO_RUNG],
                                      current[self.INFO_BOARD_SEED])

    def frame_bytes(self, _core, width=912, height=684) -> bytes:
        return self.core.marble_frame(self.handle, 1 if self.black_background else 0,
                                      width, height)

    def describe(self, _frame) -> str:
        current = self.state
        names = ("ready", "running", "feedback", "preparing", "done")
        phase = current[self.INFO_PHASE]
        name = names[phase] if 0 <= phase < len(names) else "unknown"
        return (f"Marble Maze {name} · rung {current[self.INFO_RUNG]}"
                f" · tray {current[self.INFO_TRIAL]}/{current[self.INFO_TOTAL_TRIALS]}"
                f" · {'MuJoCo 3D' if self.native_physics else '2D fallback'}")

    def action(self, action: int, value: int = 0, aux: int = 0) -> None:
        self.core.marble_action(self.handle, action, value, aux)

    def tick(self, now_ms: float, physics_dt: float | None = None) -> None:
        previous_ms = self.last_ms
        elapsed = max(0, now_ms - self.last_ms)
        self.last_ms = now_ms
        elapsed_controller_ms = max(
            0, math.floor(now_ms) - math.floor(previous_ms)
        )
        if not self.native_physics:
            if elapsed_controller_ms:
                self.core.marble_advance(self.handle, elapsed_controller_ms)
            return

        phase_before = self.state[self.INFO_PHASE]
        if phase_before == 1:
            self._sync_board()
            if self.physics is None:
                return
            dt = elapsed / 1000.0 if physics_dt is None else physics_dt
            self.physics.advance(min(max(dt, 0.0), 0.05), self.held_directions)
            if self.physics.settled:
                self._report_settled()
            else:
                source_elapsed_ms = math.floor(self.physics.elapsed * 1000.0)
                controller_elapsed_ms = self.state[self.INFO_ELAPSED]
                if source_elapsed_ms > controller_elapsed_ms:
                    self.core.marble_advance(
                        self.handle, source_elapsed_ms - controller_elapsed_ms)
                if self.state[self.INFO_PHASE] == 2:
                    self._commit_timeout_score()
        elif phase_before == 2:
            if elapsed_controller_ms:
                self.core.marble_advance(self.handle, elapsed_controller_ms)
            self._sync_board()
        elif phase_before == 3:
            self._sync_board()

    def key(self, symbol, key) -> None:
        phase = self.state[self.INFO_PHASE]
        if symbol == key.SPACE:
            self.action(self.ACTION_NEXT if phase == 2 else self.ACTION_START)
            self.last_ms = time.monotonic() * 1000.0
            if self.native_physics:
                self._sync_board()
        elif symbol == key.UP:
            self.action(self.ACTION_HOLD_NORTH)
            self.held_directions.add("N")
        elif symbol == key.RIGHT:
            self.action(self.ACTION_HOLD_EAST)
            self.held_directions.add("E")
        elif symbol == key.DOWN:
            self.action(self.ACTION_HOLD_SOUTH)
            self.held_directions.add("S")
        elif symbol == key.LEFT:
            self.action(self.ACTION_HOLD_WEST)
            self.held_directions.add("W")
        elif symbol == key.L:
            self.action(self.ACTION_LEVEL)
            if self.physics is not None:
                self.physics.level()
        elif symbol == key.R:
            self.action(self.ACTION_RESTART)
            self.last_ms = time.monotonic() * 1000.0
            self.held_directions.clear()
            if self.physics is not None:
                self.physics.reset()

    def release(self, symbol, key) -> None:
        release_codes = {key.UP: 4, key.RIGHT: 5, key.DOWN: 6, key.LEFT: 3}
        if symbol in release_codes:
            self.core.marble_release(self.handle, release_codes[symbol])
            self.held_directions.discard({key.UP: "N", key.RIGHT: "E",
                                          key.DOWN: "S", key.LEFT: "W"}[symbol])

    def release_all(self) -> None:
        for code in (3, 4, 5, 6):
            self.core.marble_release(self.handle, code)
        if hasattr(self, "held_directions"):
            self.held_directions.clear()

    def close(self) -> None:
        self._dispose_physics()
        if self.handle > 0:
            self.core.marble_destroy(self.handle)
            self.handle = 0


class YouAreHereSession:
    """Native Python adapter for the source-backed 3D Maze controller."""

    ACTION_START = 0
    ACTION_AHEAD = 1
    ACTION_BACK = 2
    ACTION_LEFT = 3
    ACTION_RIGHT = 4
    ACTION_RESTART = 5

    INFO_PHASE = 0
    INFO_FACING = 5
    INFO_STEPS = 6

    def __init__(self, core, args) -> None:
        self.core = core
        self.handle = core.you_are_here_create(
            args.trial, args.trials, 1 if args.adaptive else 0,
            1 if args.show_marks else 0, args.seed)
        if self.handle <= 0:
            raise SystemExit("native 3D Maze rejected its options")
        self.black_background = args.black_background

    @property
    def state(self):
        return (self.core.you_are_here_info(self.handle, self.INFO_PHASE),
                self.core.you_are_here_info(self.handle, self.INFO_STEPS),
                self.core.you_are_here_info(self.handle, self.INFO_FACING))

    def frame_bytes(self, _core, width=912, height=684) -> bytes:
        return self.core.you_are_here_frame(
            self.handle, 1 if self.black_background else 0, width, height)

    def describe(self, _frame) -> str:
        phase, steps, facing = self.state
        names = ("ready", "walking", "solved", "done", "unavailable")
        label = names[phase] if 0 <= phase < len(names) else str(phase)
        return f"3D Maze {label} · steps {steps} · facing {facing}"

    def action(self, action, now_ms=0) -> None:
        self.core.you_are_here_action(self.handle, action, now_ms)

    def key(self, symbol, key) -> None:
        phase = self.core.you_are_here_info(self.handle, self.INFO_PHASE)
        if symbol in (key.SPACE, key.RETURN):
            self.action(self.ACTION_START)
        elif symbol == key.UP:
            self.action(self.ACTION_AHEAD if phase == 1 else self.ACTION_START)
        elif symbol == key.DOWN:
            self.action(self.ACTION_BACK)
        elif symbol == key.LEFT:
            self.action(self.ACTION_LEFT)
        elif symbol == key.RIGHT:
            self.action(self.ACTION_RIGHT)
        elif symbol == key.R:
            self.action(self.ACTION_RESTART)

    def close(self) -> None:
        if self.handle > 0:
            self.core.you_are_here_destroy(self.handle)
            self.handle = 0


class SokobanSession:
    """Native Python adapter for the source-backed Sokoban controller."""

    ACTION_SPACE = 0
    # The native task hub calls the first lifecycle action ACTION_START across
    # controllers; Sokoban's source vocabulary calls the same Space action
    # ACTION_SPACE. Keep both names so dump/lifecycle tooling cannot bypass the
    # real controller because of an adapter-only naming mismatch.
    ACTION_START = ACTION_SPACE
    ACTION_UP = 1
    ACTION_DOWN = 2
    ACTION_LEFT = 3
    ACTION_RIGHT = 4
    ACTION_UNDO = 5
    ACTION_RESTART = 6

    INFO_PHASE = 0
    INFO_TRIAL = 2
    INFO_TOTAL_TRIALS = 3
    INFO_PUSHES = 5
    INFO_MOVES = 6
    INFO_WIDTH = 8
    INFO_HEIGHT = 9

    def __init__(self, core, args) -> None:
        self.core = core
        self.handle = core.sokoban_create(
            args.trial, args.trials, 1 if args.adaptive else 0,
            1 if args.show_traps else 0, args.seed)
        if self.handle <= 0:
            raise SystemExit("native Sokoban rejected its options")
        self.black_background = args.black_background

    @property
    def state(self):
        return (self.core.sokoban_info(self.handle, self.INFO_PHASE),
                self.core.sokoban_info(self.handle, self.INFO_PUSHES),
                self.core.sokoban_info(self.handle, self.INFO_MOVES))

    def frame_bytes(self, _core, width=912, height=684) -> bytes:
        return self.core.sokoban_frame(
            self.handle, 1 if self.black_background else 0, width, height)

    def action(self, action: int, now_ms: int = 0) -> None:
        self.core.sokoban_action(self.handle, action, now_ms)

    def key(self, symbol, key) -> None:
        if symbol in (key.SPACE, key.RETURN):
            self.action(self.ACTION_SPACE)
        elif symbol == key.UP:
            self.action(self.ACTION_UP)
        elif symbol == key.DOWN:
            self.action(self.ACTION_DOWN)
        elif symbol == key.LEFT:
            self.action(self.ACTION_LEFT)
        elif symbol == key.RIGHT:
            self.action(self.ACTION_RIGHT)
        elif symbol == key.U:
            self.action(self.ACTION_UNDO)
        elif symbol == key.R:
            self.action(self.ACTION_RESTART)

    def close(self) -> None:
        if self.handle > 0:
            self.core.sokoban_destroy(self.handle)
            self.handle = 0


class MonkeyLadderSession:
    """Native Python adapter for the source-backed timed Monkey Ladder."""
    ACTION_START, ACTION_TICK, ACTION_SELECT = 0, 1, 2
    ACTION_UP, ACTION_DOWN, ACTION_LEFT, ACTION_RIGHT, ACTION_COMMIT = 3, 4, 5, 6, 7
    INFO_PHASE, INFO_LEVEL, INFO_LENGTH, INFO_DEADLINE = 0, 2, 4, 11

    def __init__(self, core, args) -> None:
        self.core = core
        self.handle = core.monkey_ladder_create(5, 2, 1, 300, 120, 1, args.seed)
        if self.handle <= 0:
            raise SystemExit("native Monkey Ladder rejected its options")
        self.black_background = args.black_background

    @property
    def state(self):
        return (self.core.monkey_ladder_info(self.handle, self.INFO_PHASE),
                self.core.monkey_ladder_info(self.handle, self.INFO_LEVEL),
                self.core.monkey_ladder_info(self.handle, self.INFO_LENGTH))

    def frame_bytes(self, _core, width=912, height=684) -> bytes:
        return self.core.monkey_ladder_frame(self.handle, 1 if self.black_background else 0, width, height)

    def describe(self, _frame) -> str:
        return f"Monkey Ladder · phase {self.state[0]} · length {self.state[2]}"

    def action(self, action: int, value: int = 0, now_ms: int = 0) -> None:
        self.core.monkey_ladder_action(self.handle, action, value, now_ms)

    def tick(self, now_ms: int) -> None:
        self.action(self.ACTION_TICK, now_ms=now_ms)

    def key(self, symbol, key) -> None:
        if symbol in (key.SPACE, key.RETURN):
            phase = self.state[0]
            self.action(self.ACTION_COMMIT if phase == 2 else self.ACTION_START)
        elif symbol == key.UP: self.action(self.ACTION_UP)
        elif symbol == key.DOWN: self.action(self.ACTION_DOWN)
        elif symbol == key.LEFT: self.action(self.ACTION_LEFT)
        elif symbol == key.RIGHT: self.action(self.ACTION_RIGHT)

    def close(self) -> None:
        if self.handle > 0:
            self.core.monkey_ladder_destroy(self.handle)
            self.handle = 0


class TetrisSession:
    """Native Python adapter for source-backed Freeform Tetris."""
    ACTION_SPACE, ACTION_LEFT, ACTION_RIGHT = 0, 1, 2
    ACTION_ROTATE, ACTION_DROP, ACTION_RESTART = 3, 4, 5
    ACTION_SELECT_BASE = 6
    INFO_PHASE, INFO_RUNG, INFO_PIECE, INFO_SCORE = 0, 1, 2, 3
    INFO_SELECTED, INFO_QUARTER, INFO_COLUMN, INFO_ROW = 4, 5, 6, 7
    INFO_REMAINDER = 8

    def __init__(self, core, args) -> None:
        self.core = core
        self.handle = core.tetris_create(1, 25, 5, args.seed)
        if self.handle <= 0:
            raise SystemExit("native Freeform Tetris rejected its options")
        self.black_background = args.black_background

    @property
    def state(self):
        return tuple(self.core.tetris_info(self.handle, field)
                     for field in range(self.INFO_REMAINDER + 1))

    def frame_bytes(self, _core, width=912, height=684) -> bytes:
        return self.core.tetris_frame(
            self.handle, 1 if self.black_background else 0, width, height)

    def describe(self, _frame) -> str:
        phase = ("ready", "playing", "done")
        current = self.state
        name = phase[current[self.INFO_PHASE]] if 0 <= current[self.INFO_PHASE] < len(phase) else "unknown"
        return (f"Freeform Tetris {name} · piece {current[self.INFO_PIECE]}"
                f"/{current[self.INFO_PIECE] + current[self.INFO_REMAINDER]}"
                f" · score {current[self.INFO_SCORE]} · slot {current[self.INFO_SELECTED] + 1}")

    def action(self, action: int) -> None:
        self.core.tetris_action(self.handle, action)

    def key(self, symbol, key) -> None:
        if symbol in (key.SPACE, key.RETURN): self.action(self.ACTION_SPACE)
        elif symbol == key.LEFT: self.action(self.ACTION_LEFT)
        elif symbol == key.RIGHT: self.action(self.ACTION_RIGHT)
        elif symbol == key.UP: self.action(self.ACTION_ROTATE)
        elif symbol == key.DOWN: self.action(self.ACTION_DROP)
        elif symbol == key.R: self.action(self.ACTION_RESTART)
        elif key._1 <= symbol <= key._6:
            self.action(self.ACTION_SELECT_BASE + symbol - key._1)

    def close(self) -> None:
        if self.handle > 0:
            self.core.tetris_destroy(self.handle)
            self.handle = 0


class CountSession:
    """Native Python adapter for the source-backed Count controller."""
    ACTION_START, ACTION_DIGIT, ACTION_BACKSPACE, ACTION_SUBMIT = 0, 1, 2, 3
    INFO_PHASE, INFO_KIND, INFO_COUNT, INFO_TRIAL = 0, 1, 2, 3
    INFO_TOTAL_TRIALS, INFO_CORRECT = 4, 5

    def __init__(self, core, args) -> None:
        self.core = core
        count_trials = args.trials if args.trials in (5, 10, 15, 20, 30, 50, 80, 100) else 5
        self.handle = core.count_create(0, 8, count_trials, 200, 1, 1,
                                        args.seed)
        if self.handle <= 0:
            raise SystemExit("native Count rejected its options")
        self.black_background = args.black_background

    @property
    def state(self):
        return tuple(self.core.count_info(self.handle, field)
                     for field in range(16))

    def frame_bytes(self, _core, width=912, height=684) -> bytes:
        return self.core.count_frame(
            self.handle, 1 if self.black_background else 0, width, height)

    def describe(self, _frame) -> str:
        current = self.state
        phase = ("ready", "showing", "hidden", "feedback", "done")
        name = phase[current[self.INFO_PHASE]] if 0 <= current[self.INFO_PHASE] < len(phase) else "unknown"
        return (f"Count {name} · trial {current[self.INFO_TRIAL]}"
                f"/{current[self.INFO_TOTAL_TRIALS]} · right {current[self.INFO_CORRECT]}")

    def action(self, action: int, value: int = 0, now_ms: int = 0) -> None:
        self.core.count_action(self.handle, action, value, now_ms)

    def tick(self, now_ms: int) -> None:
        self.core.count_advance(self.handle, now_ms)

    def key(self, symbol, key) -> None:
        now_ms = int(time.monotonic() * 1000)
        if symbol in (key.SPACE, key.RETURN) and self.state[self.INFO_PHASE] in (0, 4):
            self.action(self.ACTION_START, now_ms=now_ms)
        elif symbol == key.RETURN:
            self.action(self.ACTION_SUBMIT, now_ms=now_ms)
        elif symbol == key.BACKSPACE:
            self.action(self.ACTION_BACKSPACE, now_ms=now_ms)
        else:
            digits = {getattr(key, f"_{digit}"): digit for digit in range(10)}
            if symbol in digits:
                self.action(self.ACTION_DIGIT, digits[symbol], now_ms)

    def close(self) -> None:
        if self.handle > 0:
            self.core.count_destroy(self.handle)
            self.handle = 0


class MrTimeSession:
    """Native Python adapter for the source-backed Mr. Time controller."""
    ACTION_START, ACTION_DIGIT, ACTION_POINT = 0, 1, 2
    ACTION_BACKSPACE, ACTION_SUBMIT, ACTION_ACT = 3, 4, 5
    INFO_PHASE, INFO_TRIAL, INFO_TOTAL_TRIALS, INFO_CORRECT = 0, 4, 5, 6
    PHASE_ASKING = 3

    def __init__(self, core, args) -> None:
        self.core = core
        self.handle = core.mr_time_create(0, 1, 15, 3000, 400, 1, args.seed)
        if self.handle <= 0:
            raise SystemExit("native Mr. Time rejected its options")
        self.black_background = args.black_background

    @property
    def state(self):
        return tuple(self.core.mr_time_info(self.handle, field)
                     for field in range(20))

    def frame_bytes(self, _core, width=912, height=684) -> bytes:
        return self.core.mr_time_frame(
            self.handle, 1 if self.black_background else 0, width, height)

    def describe(self, _frame) -> str:
        current = self.state
        names = ("ready", "showing", "waiting", "asking", "counting",
                 "feedback", "done")
        phase = current[self.INFO_PHASE]
        name = names[phase] if 0 <= phase < len(names) else "unknown"
        return (f"Mr. Time {name} · trial {current[self.INFO_TRIAL]}"
                f"/{current[self.INFO_TOTAL_TRIALS]} · right {current[self.INFO_CORRECT]}")

    def action(self, action: int, value: int = 0, now_ms: int = 0) -> None:
        self.core.mr_time_action(self.handle, action, value, now_ms)

    def tick(self, now_ms: int) -> None:
        self.core.mr_time_advance(self.handle, now_ms)

    def key(self, symbol, key) -> None:
        now_ms = int(time.monotonic() * 1000)
        if symbol in (key.SPACE, key.RETURN):
            self.action(self.ACTION_SUBMIT if self.state[self.INFO_PHASE] == self.PHASE_ASKING
                        else self.ACTION_START, now_ms=now_ms)
        elif symbol == key.BACKSPACE:
            self.action(self.ACTION_BACKSPACE, now_ms=now_ms)
        elif symbol in (getattr(key, "PERIOD", -1),
                        getattr(key, "NUM_DECIMAL", -1)):
            self.action(self.ACTION_POINT, now_ms=now_ms)
        else:
            digits = {getattr(key, f"_{digit}"): digit for digit in range(10)}
            if symbol in digits:
                self.action(self.ACTION_DIGIT, digits[symbol], now_ms)

    def close(self) -> None:
        if self.handle > 0:
            self.core.mr_time_destroy(self.handle)
            self.handle = 0


class GraphMappingSession:
    """Native Python adapter for the source-backed Graph Mapping controller."""
    ACTION_START, ACTION_SAME, ACTION_DIFFERENT = 0, 1, 2
    INFO_PHASE, INFO_TRIAL, INFO_TOTAL_TRIALS, INFO_CORRECT = 0, 4, 5, 6

    def __init__(self, core, args) -> None:
        self.core = core
        self.handle = core.graph_mapping_create(4, 0, 5, 3000, 1, 0, args.seed)
        if self.handle <= 0:
            raise SystemExit("native Graph Mapping rejected its options")
        self.black_background = args.black_background

    @property
    def state(self):
        return tuple(self.core.graph_mapping_info(self.handle, field)
                     for field in range(22))

    def frame_bytes(self, _core, width=912, height=684) -> bytes:
        return self.core.graph_mapping_frame(
            self.handle, 1 if self.black_background else 0, width, height)

    def describe(self, _frame) -> str:
        current = self.state
        names = ("ready", "asking", "hidden", "feedback", "done")
        phase = current[self.INFO_PHASE]
        name = names[phase] if 0 <= phase < len(names) else "unknown"
        return (f"Graph Mapping {name} · trial {current[self.INFO_TRIAL]}"
                f"/{current[self.INFO_TOTAL_TRIALS]} · right {current[self.INFO_CORRECT]}")

    def action(self, action: int, now_ms: int = 0) -> None:
        self.core.graph_mapping_action(self.handle, action, now_ms)

    def tick(self, now_ms: int) -> None:
        self.core.graph_mapping_advance(self.handle, now_ms)

    def key(self, symbol, key) -> None:
        now_ms = int(time.monotonic() * 1000)
        if symbol in (key.SPACE, key.RETURN):
            self.action(self.ACTION_START, now_ms)
        elif symbol in (key.Y, key.S):
            self.action(self.ACTION_SAME, now_ms)
        elif symbol in (key.N, key.D):
            self.action(self.ACTION_DIFFERENT, now_ms)
        elif symbol == key.LEFT:
            self.action(self.ACTION_SAME, now_ms)
        elif symbol == key.RIGHT:
            self.action(self.ACTION_DIFFERENT, now_ms)

    def close(self) -> None:
        if self.handle > 0:
            self.core.graph_mapping_destroy(self.handle)
            self.handle = 0


class MatrixReasoningSession:
    """Native Python adapter for source-backed Matrix Reasoning."""

    ACTION_START, ACTION_ANSWER = 0, 1
    INFO_PHASE, INFO_TRIAL, INFO_TOTAL_TRIALS = 0, 2, 3
    INFO_CHOICES, INFO_CORRECT, INFO_VERDICT = 5, 8, 9
    INFO_ANSWER = 6

    def __init__(self, core, args) -> None:
        self.core = core
        # Source defaults: level one, five trials, no exposure, feedback and
        # colour enabled. Explanation is disabled in the default shell route.
        self.handle = core.matrix_reasoning_create(1, 5, 0, 1, 1, 1, args.seed)
        if self.handle <= 0:
            raise SystemExit("native Matrix Reasoning rejected its options")
        self.black_background = args.black_background

    @property
    def state(self):
        return tuple(self.core.matrix_reasoning_info(self.handle, field)
                     for field in range(22))

    def frame_bytes(self, _core, width=912, height=684) -> bytes:
        return self.core.matrix_reasoning_frame(
            self.handle, 1 if self.black_background else 0, width, height)

    def describe(self, _frame) -> str:
        state = self.state
        names = ("ready", "asking", "hidden", "feedback", "done")
        phase = state[self.INFO_PHASE]
        name = names[phase] if 0 <= phase < len(names) else "unknown"
        return (f"Matrix Reasoning {name} · trial {state[self.INFO_TRIAL]}"
                f"/{state[self.INFO_TOTAL_TRIALS]} · right {state[self.INFO_CORRECT]}")

    def action(self, action: int, value: int = 0, now_ms: int = 0) -> None:
        self.core.matrix_reasoning_action(self.handle, action, value, now_ms)

    def tick(self, now_ms: int) -> None:
        self.core.matrix_reasoning_advance(self.handle, now_ms)

    def key(self, symbol, key) -> None:
        now_ms = int(time.monotonic() * 1000)
        if symbol in (key.SPACE, key.RETURN):
            self.action(self.ACTION_START, 0, now_ms)
        elif key._1 <= symbol <= key._8:
            self.action(self.ACTION_ANSWER, symbol - key._1, now_ms)

    def close(self) -> None:
        if self.handle > 0:
            self.core.matrix_reasoning_destroy(self.handle)
            self.handle = 0


class InTheDarkSession:
    """Native Python adapter for the source-backed In the Dark controller."""
    ACTION_START, ACTION_ANSWER_0 = 0, 1
    INFO_PHASE, INFO_TRIAL, INFO_TOTAL_TRIALS = 0, 2, 3
    INFO_ROOMS, INFO_ASKS, INFO_RIGHT = 11, 22, 10
    PHASE_ASKING = 2

    def __init__(self, core, args) -> None:
        self.core = core
        self.handle = core.in_the_dark_create(1, args.trials, 1000,
                                               1 if args.adaptive else 0,
                                               args.seed)
        if self.handle <= 0:
            raise SystemExit("native In the Dark rejected its options")
        self.black_background = args.black_background

    @property
    def state(self):
        return tuple(self.core.in_the_dark_info(self.handle, field)
                     for field in range(23))

    def frame_bytes(self, _core, width=912, height=684) -> bytes:
        return self.core.in_the_dark_frame(
            self.handle, 1 if self.black_background else 0, width, height)

    def describe(self, _frame) -> str:
        state = self.state
        names = ("ready", "walking", "asking", "scored", "done")
        phase = state[self.INFO_PHASE]
        name = names[phase] if 0 <= phase < len(names) else "unknown"
        return (f"In the Dark {name} · trial {state[self.INFO_TRIAL]}"
                f"/{state[self.INFO_TOTAL_TRIALS]} · right {state[self.INFO_RIGHT]}")

    def action(self, action: int, value: int = 0, now_ms: int = 0) -> None:
        self.core.in_the_dark_action(self.handle, action, value, now_ms)

    def tick(self, now_ms: int) -> None:
        self.core.in_the_dark_advance(self.handle, now_ms)

    def key(self, symbol, key) -> None:
        now_ms = int(time.monotonic() * 1000)
        phase = self.state[self.INFO_PHASE]
        if symbol in (key.SPACE, key.RETURN) and phase != self.PHASE_ASKING:
            self.action(self.ACTION_START, now_ms=now_ms)
        elif key._1 <= symbol <= key._5 and phase == self.PHASE_ASKING:
            self.action(self.ACTION_ANSWER_0 + symbol - key._1,
                        now_ms=now_ms)

    def close(self) -> None:
        if self.handle > 0:
            self.core.in_the_dark_destroy(self.handle)
            self.handle = 0


class FogOfWarSession:
    """Native Python adapter for the source-backed Fog of War controller."""
    ACTION_START, ACTION_STAY = 0, 1
    ACTION_UP, ACTION_DOWN, ACTION_LEFT, ACTION_RIGHT = 2, 3, 4, 5
    INFO_PHASE, INFO_TRIAL, INFO_TOTAL_TRIALS = 0, 1, 2
    INFO_WALKER, INFO_MOVES, INFO_MOVES_ALLOWED = 3, 4, 5

    def __init__(self, core, args) -> None:
        self.core = core
        self.handle = core.fog_create(2, 100, args.trials, 1, args.seed)
        if self.handle <= 0:
            raise SystemExit("native Fog of War rejected its options")
        self.black_background = args.black_background

    @property
    def state(self):
        return tuple(self.core.fog_info(self.handle, field)
                     for field in range(20))

    def frame_bytes(self, _core, width=912, height=684) -> bytes:
        return self.core.fog_frame(
            self.handle, 1 if self.black_background else 0, width, height)

    def describe(self, _frame) -> str:
        state = self.state
        names = ("ready", "exploring", "finished", "done")
        phase = state[self.INFO_PHASE]
        name = names[phase] if 0 <= phase < len(names) else "unknown"
        return (f"Fog of War {name} · world {state[self.INFO_TRIAL]}"
                f"/{state[self.INFO_TOTAL_TRIALS]} · moves {state[self.INFO_MOVES]}"
                f"/{state[self.INFO_MOVES_ALLOWED]}")

    def action(self, action: int) -> None:
        self.core.fog_action(self.handle, action)

    def key(self, symbol, key) -> None:
        if symbol in (key.SPACE, key.RETURN):
            self.action(self.ACTION_START)
        elif symbol == key.UP:
            self.action(self.ACTION_UP)
        elif symbol == key.DOWN:
            self.action(self.ACTION_DOWN)
        elif symbol == key.LEFT:
            self.action(self.ACTION_LEFT)
        elif symbol == key.RIGHT:
            self.action(self.ACTION_RIGHT)

    def close(self) -> None:
        if self.handle > 0:
            self.core.fog_destroy(self.handle)
            self.handle = 0


class RemovalsSession:
    """Native Python adapter for the source-backed Removals controller."""
    ACTION_START, ACTION_ANSWER_0 = 0, 1
    INFO_PHASE, INFO_TRIAL, INFO_TOTAL_TRIALS = 0, 2, 3
    INFO_ASKS, INFO_RIGHT = 13, 14
    PHASE_ASKING = 2

    def __init__(self, core, args) -> None:
        self.core = core
        self.handle = core.removals_create(1, args.trials, 1000,
                                            1 if args.adaptive else 0,
                                            args.seed)
        if self.handle <= 0:
            raise SystemExit("native Removals rejected its options")
        self.black_background = args.black_background

    @property
    def state(self):
        return tuple(self.core.removals_info(self.handle, field)
                     for field in range(21))

    def frame_bytes(self, _core, width=912, height=684) -> bytes:
        return self.core.removals_frame(
            self.handle, 1 if self.black_background else 0, width, height)

    def describe(self, _frame) -> str:
        state = self.state
        names = ("ready", "moving", "asking", "scored", "done")
        phase = state[self.INFO_PHASE]
        name = names[phase] if 0 <= phase < len(names) else "unknown"
        return (f"Removals {name} · trial {state[self.INFO_TRIAL]}"
                f"/{state[self.INFO_TOTAL_TRIALS]} · right {state[self.INFO_RIGHT]}")

    def action(self, action: int, value: int = 0, now_ms: int = 0) -> None:
        self.core.removals_action(self.handle, action, value, now_ms)

    def tick(self, now_ms: int) -> None:
        self.core.removals_advance(self.handle, now_ms)

    def key(self, symbol, key) -> None:
        now_ms = int(time.monotonic() * 1000)
        phase = self.state[self.INFO_PHASE]
        if symbol in (key.SPACE, key.RETURN) and phase != self.PHASE_ASKING:
            self.action(self.ACTION_START, now_ms=now_ms)
        elif key._1 <= symbol <= key._5 and phase == self.PHASE_ASKING:
            self.action(self.ACTION_ANSWER_0 + symbol - key._1,
                        symbol - key._1, now_ms)

    def close(self) -> None:
        if self.handle > 0:
            self.core.removals_destroy(self.handle)
            self.handle = 0


class CustodySession:
    """Native Python adapter for source-backed Chain of Custody."""
    ACTION_START, ACTION_LEFT, ACTION_RIGHT, ACTION_GRAB = 0, 1, 2, 3
    INFO_PHASE, INFO_TRIAL, INFO_TOTAL_TRIALS = 0, 2, 3
    INFO_RUNG, INFO_CLAW, INFO_HELD, INFO_SPENT = 1, 8, 9, 10
    PHASE_RUNNING = 2

    def __init__(self, core, args) -> None:
        self.core = core
        self.handle = core.custody_create(1, args.trials, 900, 1200,
                                           1 if args.adaptive else 0,
                                           args.seed)
        if self.handle <= 0:
            raise SystemExit("native Chain of Custody rejected its options")
        self.black_background = args.black_background

    @property
    def state(self):
        return tuple(self.core.custody_info(self.handle, field)
                     for field in range(23))

    def frame_bytes(self, _core, width=912, height=684) -> bytes:
        return self.core.custody_frame(
            self.handle, 1 if self.black_background else 0, width, height)

    def describe(self, _frame) -> str:
        state = self.state
        names = ("ready", "marking", "running", "scored", "done")
        phase = state[self.INFO_PHASE]
        name = names[phase] if 0 <= phase < len(names) else "unknown"
        return (f"Chain of Custody {name} · trial {state[self.INFO_TRIAL]}"
                f"/{state[self.INFO_TOTAL_TRIALS]} · rung {state[self.INFO_RUNG]}"
                f" · actions {state[self.INFO_SPENT]}")

    def action(self, action: int, value: int = 0, now_ms: int = 0) -> None:
        self.core.custody_action(self.handle, action, value, now_ms)

    def tick(self, now_ms: int) -> None:
        self.core.custody_advance(self.handle, now_ms)

    def key(self, symbol, key) -> None:
        now_ms = int(time.monotonic() * 1000)
        phase = self.state[self.INFO_PHASE]
        if symbol in (key.SPACE, key.RETURN):
            self.action(self.ACTION_START, now_ms=now_ms)
        elif symbol == key.LEFT and phase == self.PHASE_RUNNING:
            self.action(self.ACTION_LEFT, now_ms=now_ms)
        elif symbol == key.RIGHT and phase == self.PHASE_RUNNING:
            self.action(self.ACTION_RIGHT, now_ms=now_ms)
        elif symbol == key.Z and phase == self.PHASE_RUNNING:
            self.action(self.ACTION_GRAB, now_ms=now_ms)

    def close(self) -> None:
        if self.handle > 0:
            self.core.custody_destroy(self.handle)
            self.handle = 0


class ConcentrationSession:
    """Native Python adapter for source-backed Concentration."""
    ACTION_START, ACTION_SELECT, ACTION_CURSOR = 0, 1, 2
    INFO_PHASE, INFO_COUNT, INFO_CURSOR = 0, 2, 9

    def __init__(self, core, args) -> None:
        self.core = core
        self.handle = core.concentration_create(4, 0, 0, 900, 1, 1,
                                                args.seed)
        if self.handle <= 0:
            raise SystemExit("native Concentration rejected its options")
        self.black_background = args.black_background

    @property
    def state(self):
        return tuple(self.core.concentration_info(self.handle, field)
                     for field in range(16))

    def frame_bytes(self, _core, width=912, height=684) -> bytes:
        return self.core.concentration_frame(
            self.handle, 1 if self.black_background else 0, width, height)

    def describe(self, _frame) -> str:
        state = self.state
        names = ("ready", "peek", "playing", "done")
        phase = state[self.INFO_PHASE]
        name = names[phase] if 0 <= phase < len(names) else "unknown"
        return (f"Concentration {name} · cursor {state[self.INFO_CURSOR]}"
                f" · pairs {state[7]}/{state[1]} · turns {state[4]}")

    def action(self, action: int, value: int = 0, now_ms: int = 0) -> None:
        self.core.concentration_action(self.handle, action, value, now_ms)

    def tick(self, now_ms: int) -> None:
        self.core.concentration_advance(self.handle, now_ms)

    def key(self, symbol, key) -> None:
        now_ms = int(time.monotonic() * 1000)
        phase = self.state[self.INFO_PHASE]
        if symbol in (key.SPACE, key.RETURN) and phase in (0, 3):
            self.action(self.ACTION_START, now_ms=now_ms)
        elif symbol == key.RETURN and phase == 2:
            self.action(self.ACTION_SELECT, self.state[self.INFO_CURSOR], now_ms)
        elif symbol == key.LEFT:
            self.action(self.ACTION_CURSOR, max(0, self.state[self.INFO_CURSOR] - 1), now_ms)
        elif symbol == key.RIGHT:
            self.action(self.ACTION_CURSOR, min(self.state[self.INFO_COUNT] - 1,
                                                self.state[self.INFO_CURSOR] + 1), now_ms)
        elif symbol == key.UP:
            self.action(self.ACTION_CURSOR, max(0, self.state[self.INFO_CURSOR] - 4), now_ms)
        elif symbol == key.DOWN:
            self.action(self.ACTION_CURSOR, min(self.state[self.INFO_COUNT] - 1,
                                                self.state[self.INFO_CURSOR] + 4), now_ms)

    def close(self) -> None:
        if self.handle > 0:
            self.core.concentration_destroy(self.handle)
            self.handle = 0


class RecognitionSession:
    """Native Python adapter for source-backed Seen It Before?."""
    ACTION_START, ACTION_SEEN, ACTION_NEW = 0, 1, 2

    def __init__(self, core, args) -> None:
        self.core = core
        recognition_trials = args.trials if args.trials in (10, 20, 30, 40, 60, 80, 100, 150, 200, 300, 500) else 10
        self.handle = core.recognition_create(recognition_trials, 0, 40, 4, 500,
                                              1, args.seed)
        if self.handle <= 0:
            raise SystemExit("native Seen It Before? rejected its options")
        self.black_background = args.black_background

    @property
    def state(self):
        return tuple(self.core.recognition_info(self.handle, field)
                     for field in range(19))

    def frame_bytes(self, _core, width=912, height=684) -> bytes:
        return self.core.recognition_frame(
            self.handle, 1 if self.black_background else 0, width, height)

    def describe(self, _frame) -> str:
        state = self.state
        names = ("ready", "showing", "hidden", "feedback", "done")
        phase = state[0]
        name = names[phase] if 0 <= phase < len(names) else "unknown"
        return (f"Seen It Before? {name} · trial {state[2]}/{state[1]}"
                f" · hits {state[13]} · misses {state[14]}")

    def action(self, action: int, now_ms: int = 0) -> None:
        self.core.recognition_action(self.handle, action, 0, now_ms)

    def tick(self, now_ms: int) -> None:
        self.core.recognition_advance(self.handle, now_ms)

    def key(self, symbol, key) -> None:
        now_ms = int(time.monotonic() * 1000)
        phase = self.state[0]
        if symbol in (key.SPACE, key.RETURN) and phase in (0, 4):
            self.action(self.ACTION_START, now_ms)
        elif symbol == key.LEFT and phase in (1, 2):
            self.action(self.ACTION_SEEN, now_ms)
        elif symbol == key.RIGHT and phase in (1, 2):
            self.action(self.ACTION_NEW, now_ms)

    def close(self) -> None:
        if self.handle > 0:
            self.core.recognition_destroy(self.handle)
            self.handle = 0


class TriviaSession:
    """Native Python adapter for source-backed Trivia."""
    ACTION_START, ACTION_UP, ACTION_DOWN = 0, 1, 2
    ACTION_SUBMIT, ACTION_CHOOSE_0, ACTION_ADVANCE = 3, 4, 12

    def __init__(self, core, args) -> None:
        self.core = core
        self.handle = core.trivia_create(1, args.trials, 1,
                                         1 if args.adaptive else 0,
                                         args.seed)
        if self.handle <= 0:
            raise SystemExit("native Trivia rejected its options")
        self.black_background = args.black_background

    @property
    def state(self):
        return tuple(self.core.trivia_info(self.handle, field)
                     for field in range(17))

    def frame_bytes(self, _core, width=912, height=684) -> bytes:
        return self.core.trivia_frame(
            self.handle, 1 if self.black_background else 0, width, height)

    def describe(self, _frame) -> str:
        state = self.state
        names = ("ready", "asking", "judged", "done")
        phase = state[0]
        name = names[phase] if 0 <= phase < len(names) else "unknown"
        return (f"Trivia {name} · trial {state[3]}/{state[4]}"
                f" · level {state[2]} · right {state[10]}")

    def action(self, action: int, value: int = 0) -> None:
        self.core.trivia_action(self.handle, action, value)

    def key(self, symbol, key) -> None:
        phase = self.state[0]
        if symbol in (key.SPACE, key.RETURN):
            if phase in (0, 3):
                self.action(self.ACTION_START)
            elif phase == 1:
                self.action(self.ACTION_SUBMIT)
            elif phase == 2:
                self.action(self.ACTION_ADVANCE)
        elif symbol == key.UP and phase == 1:
            self.action(self.ACTION_UP)
        elif symbol == key.DOWN and phase == 1:
            self.action(self.ACTION_DOWN)
        elif key._1 <= symbol <= key._8 and phase == 1:
            self.action(self.ACTION_CHOOSE_0 + symbol - key._1)

    def close(self) -> None:
        if self.handle > 0:
            self.core.trivia_destroy(self.handle)
            self.handle = 0


class ReflexSession:
    """Native Python adapter for source-backed Reflex."""
    ACTION_START = 0

    def __init__(self, core, args) -> None:
        self.core = core
        self.handle = core.reflex_create(10, 1200, 400, 3, 100,
                                         1 if args.adaptive else 0,
                                         args.seed)
        if self.handle <= 0:
            raise SystemExit("native Reflex rejected its options")
        self.black_background = args.black_background

    @property
    def state(self):
        return tuple(self.core.reflex_info(self.handle, field)
                     for field in range(19))

    def frame_bytes(self, _core, width=912, height=684) -> bytes:
        return self.core.reflex_frame(
            self.handle, 1 if self.black_background else 0, width, height)

    def describe(self, _frame) -> str:
        state = self.state
        names = ("ready", "running", "done")
        phase = state[0]
        name = names[phase] if 0 <= phase < len(names) else "unknown"
        return (f"Reflex {name} · targets {state[2]}/{state[1]}"
                f" · hits {state[9]} · misses {state[10]}")

    def action(self, action: int, now_ms: int = 0) -> None:
        self.core.reflex_action(self.handle, action, 0, now_ms)

    def tick(self, now_ms: int) -> None:
        self.core.reflex_advance(self.handle, now_ms)

    def pointer(self, x: float, y: float, width: int, height: int) -> None:
        now_ms = int(time.monotonic() * 1000)
        self.core.reflex_pointer(
            self.handle, int(x * 1_000_000 / width),
            int(y * 1_000_000 / height), now_ms)

    def key(self, symbol, key) -> None:
        if symbol in (key.SPACE, key.RETURN):
            self.action(self.ACTION_START, int(time.monotonic() * 1000))

    def close(self) -> None:
        if self.handle > 0:
            self.core.reflex_destroy(self.handle)
            self.handle = 0


class AlgebraSession:
    """Native Python adapter for source-backed typed Algebra."""
    ACTION_START, ACTION_WRITE, ACTION_BACKSPACE, ACTION_SUBMIT = 0, 1, 2, 3
    INFO_PHASE, INFO_LEVEL, INFO_TRIAL, INFO_TOTAL = 0, 1, 2, 3
    INFO_ASKED, INFO_TYPED, INFO_TYPED_LENGTH = 4, 5, 6
    INFO_VERDICT, INFO_RIGHT = 7, 8

    def __init__(self, core, args) -> None:
        self.core = core
        self.args = args
        saved = read_algebra_settings()
        self.options = [getattr(args, 'algebra_level', None) or saved[0],
                        getattr(args, 'algebra_trials', None) or saved[1],
                        saved[2] if getattr(args, 'algebra_no_working', None) is None else int(not args.algebra_no_working),
                        saved[3] if getattr(args, 'algebra_no_adaptive', None) is None else int(not args.algebra_no_adaptive)]
        self.options_draft = None
        self.options_selection = 0
        self.options_from_hub = False
        self.handle = core.algebra_create_options(*self.options, args.seed)
        if self.handle <= 0:
            raise SystemExit("native Algebra rejected its options")
        self.black_background = args.black_background

    @property
    def state(self):
        return tuple(self.core.algebra_info(self.handle, field)
                     for field in range(10))

    def frame_bytes(self, _core, width=912, height=684) -> bytes:
        if self.options_draft is not None:
            return self.core.algebra_options_frame(int(self.black_background), self.options_selection, *self.options_draft)
        return self.core.algebra_frame(
            self.handle, 1 if self.black_background else 0, width, height)

    def describe(self, _frame) -> str:
        current = self.state
        names = ("ready", "working", "judged", "done")
        phase = current[self.INFO_PHASE]
        name = names[phase] if 0 <= phase < len(names) else "unknown"
        return (f"Algebra {name} · trial {current[self.INFO_TRIAL]}"
                f"/{current[self.INFO_TOTAL]} · right {current[self.INFO_RIGHT]}"
                f" · typed {current[self.INFO_TYPED]}")

    def action(self, action: int, value: int = 0) -> None:
        phase = self.state[self.INFO_PHASE]
        self.core.algebra_action(self.handle, action, value, int(time.monotonic() * 1000))
        if phase != 1 and self.state[self.INFO_PHASE] == 1:
            self.core.algebra_action(self.handle, 4, 0, int(time.monotonic() * 1000))

    def modify_option(self, delta):
        choices = (tuple(range(1, 13)), ALGEBRA_TRIALS, (0, 1), (0, 1))
        values = choices[self.options_selection]
        current = self.options_draft[self.options_selection]
        self.options_draft[self.options_selection] = values[(values.index(current) + delta) % len(values)]

    def key(self, symbol, key) -> None:
        if self.options_draft is not None:
            if symbol == key.ESCAPE: self.options_draft = None
            elif symbol == key.UP: self.options_selection = max(0, self.options_selection - 1)
            elif symbol == key.DOWN: self.options_selection = min(3, self.options_selection + 1)
            elif symbol in (key.LEFT, key.RIGHT, key.SPACE): self.modify_option(-1 if symbol == key.LEFT else 1)
            elif symbol == key.RETURN:
                new_handle = self.core.algebra_create_options(*self.options_draft, self.args.seed)
                if new_handle > 0:
                    self.core.algebra_destroy(self.handle)
                    self.handle = new_handle
                    self.options = list(self.options_draft)
                    level, trials, working, adaptive = self.options
                    self.args.algebra_level, self.args.algebra_trials = level, trials
                    self.args.algebra_no_working = not working
                    self.args.algebra_no_adaptive = not adaptive
                    write_algebra_settings(self.options)
                self.options_draft = None
            return
        phase = self.state[self.INFO_PHASE]
        if symbol == key.O and phase != 1:
            self.options_draft = list(self.options)
            self.options_selection = 0
        elif symbol == key.SPACE and phase != 1: self.action(self.ACTION_START)
        elif symbol == key.RETURN and phase == 1: self.action(self.ACTION_SUBMIT)
        elif symbol in (key.BACKSPACE, key.DELETE): self.action(self.ACTION_BACKSPACE)

    def pointer(self, x, y, width, height, button=0, _motion=False):
        if self.options_draft is not None:
            if button == 0:
                row = round((474 - y * 684 / height) / 48)
                if 0 <= row < 4 and abs(y * 684 / height - (474 - row * 48)) <= 18:
                    if row == self.options_selection: self.modify_option(1)
                    else: self.options_selection = row
        elif self.state[self.INFO_PHASE] != 1:
            self.action(self.ACTION_START)

    def text(self, text: str) -> None:
        if self.options_draft is None and self.state[self.INFO_PHASE] == 1:
            for char in text:
                self.action(self.ACTION_WRITE, ord(char))

    def paste(self) -> None:
        if self.options_draft is None and self.state[self.INFO_PHASE] == 1:
            self.text(read_scramble_clipboard())

    def close(self) -> None:
        if self.handle > 0:
            self.core.algebra_destroy(self.handle)
            self.handle = 0


SYLLOGISM_TRIALS = (1, 2, 3, 5, 6, 8, 10, 15)


def syllogism_settings_path() -> Path:
    override = os.environ.get("NW_SYLLOGISM_SETTINGS_PATH")
    if override:
        return Path(override).expanduser()
    if sys.platform == "win32":
        return Path(os.environ.get("APPDATA", str(Path.home()))) / "Neural Workshop" / "syllogism-options"
    return Path.home() / ".neural-workshop" / "syllogism-options"


def read_syllogism_settings() -> tuple[int, int, int, int, int]:
    try:
        fields = tuple(map(int, syllogism_settings_path().read_text(encoding="ascii").split()))
        if len(fields) == 5 and 1 <= fields[0] <= 12 and fields[1] in SYLLOGISM_TRIALS and all(value in (0, 1) for value in fields[2:]):
            return fields
    except (OSError, UnicodeError, ValueError):
        pass
    return (3, 6, 1, 1, 1)


def write_syllogism_settings(values) -> bool:
    path = syllogism_settings_path()
    temporary = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(mode="w", encoding="ascii", dir=path.parent, delete=False) as output:
            temporary = Path(output.name)
            output.write("%d %d %d %d %d\n" % tuple(values))
        os.replace(temporary, path)
        return True
    except OSError as error:
        print(f"Could not save Syllogism settings: {error}", file=sys.stderr)
        return False
    finally:
        if temporary is not None:
            try: temporary.unlink(missing_ok=True)
            except OSError: pass


class SyllogismSession:
    """Python host for the shared generated Syllogisms controller."""
    ACTION_START = 0
    def __init__(self, core, args) -> None:
        self.core, self.args = core, args
        saved = read_syllogism_settings()
        self.options = [getattr(args, 'syllogism_level', None) or saved[0],
                        getattr(args, 'syllogism_trials', None) or saved[1],
                        saved[2] if getattr(args, 'syllogism_no_working', None) is None else int(not args.syllogism_no_working),
                        saved[3] if getattr(args, 'syllogism_no_adaptive', None) is None else int(not args.syllogism_no_adaptive),
                        saved[4] if getattr(args, 'syllogism_invented_words', None) is None else int(not args.syllogism_invented_words)]
        self.handle = core.syllogism_create(*self.options, args.seed)
        if self.handle <= 0: raise SystemExit("native Syllogism rejected its options")
        self.black_background = args.black_background
        self.options_draft = None
        self.options_selection = 0
        self.options_from_hub = False

    @property
    def state(self):
        return tuple(self.core.syllogism_info(self.handle, field) for field in range(14))

    def frame_bytes(self, _core, width=912, height=684):
        if self.options_draft is not None:
            return self.core.syllogism_options_frame(int(self.black_background), self.options_selection, *self.options_draft)
        return self.core.syllogism_frame(self.handle, int(self.black_background), width, height)

    def describe(self, _frame):
        state = self.state
        phase = ("ready", "asking", "judged", "done")[state[0]] if 0 <= state[0] < 4 else "unknown"
        return f"Syllogisms {phase} · question {state[2]}/{state[3]} · right {state[8]}"

    def action(self, action, value=0):
        self.core.syllogism_action(self.handle, action, value, int(time.monotonic() * 1000))

    def modify_option(self, delta):
        choices = (tuple(range(1, 13)), SYLLOGISM_TRIALS, (0, 1), (0, 1), (0, 1))
        row = self.options_selection
        values = choices[row]
        self.options_draft[row] = values[(values.index(self.options_draft[row]) + delta) % len(values)]

    def key(self, symbol, key):
        if self.options_draft is not None:
            if symbol == key.ESCAPE: self.options_draft = None
            elif symbol == key.UP: self.options_selection = max(0, self.options_selection - 1)
            elif symbol == key.DOWN: self.options_selection = min(4, self.options_selection + 1)
            elif symbol in (key.LEFT, key.RIGHT, key.SPACE): self.modify_option(-1 if symbol == key.LEFT else 1)
            elif symbol == key.RETURN: self.apply_options()
            return
        phase = self.state[0]
        if symbol == key.O and phase != 1:
            self.options_draft = list(self.options); self.options_selection = 0
        elif symbol == key.SPACE:
            self.action(1 if phase == 1 else 0)
        elif symbol == key.RETURN and phase == 1: self.action(1)
        elif phase == 1 and symbol in (key.LEFT, key.UP): self.action(2 if symbol == key.LEFT else 4)
        elif phase == 1 and symbol in (key.RIGHT, key.DOWN): self.action(3 if symbol == key.RIGHT else 5)
        elif phase == 1 and key._1 <= symbol <= key._9: self.action(6, symbol - key._1)

    def apply_options(self):
        if self.options_draft is None: return
        fresh = self.core.syllogism_create(*self.options_draft, self.args.seed)
        if fresh > 0:
            self.core.syllogism_destroy(self.handle); self.handle = fresh
            self.options = list(self.options_draft)
            (self.args.syllogism_level, self.args.syllogism_trials) = self.options[:2]
            self.args.syllogism_no_working = not self.options[2]
            self.args.syllogism_no_adaptive = not self.options[3]
            self.args.syllogism_invented_words = not self.options[4]
            write_syllogism_settings(self.options)
        self.options_draft = None

    def pointer(self, x, y, width, height, button=0, _motion=False):
        if button != 0: return
        if self.options_draft is not None:
            viewport = Viewport(width, height)
            rx, ry = (x - viewport.offset_x) / viewport.scale, (y - viewport.offset_y) / viewport.scale
            if 94 <= ry <= 132 and 170 <= rx <= 360:
                self.options_draft = None
                return
            if 94 <= ry <= 132 and 552 <= rx <= 742:
                self.apply_options()
                return
            row = round((474 - ry) / 48)
            if 102 <= rx <= 810 and 0 <= row < 5 and abs(ry - (474 - row * 48)) <= 18:
                if row == self.options_selection: self.modify_option(1)
                else: self.options_selection = row
        elif self.state[0] != 1: self.action(0)

    def close(self):
        if self.handle > 0:
            self.core.syllogism_destroy(self.handle); self.handle = 0


def numberology_page_at(x: float, y: float) -> int:
    if not 342 <= y <= 388:
        return 0
    if 170 <= x <= 360:
        return 4
    if 552 <= x <= 742:
        return 5
    return 0


def numberology_results_dir() -> Path:
    override = os.environ.get("NW_NUMBEROLOGY_RESULTS_DIR")
    return Path(override).expanduser() if override else numberology_settings_path().parent / "results" / "numberology"


def write_numberology_result(record) -> bool:
    """Atomically replace one session record; never truncate an existing result."""
    directory = numberology_results_dir()
    temporary = None
    try:
        directory.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=directory, delete=False) as output:
            temporary = Path(output.name)
            json.dump(record, output, ensure_ascii=False, separators=(",", ":"))
            output.write("\n")
        os.replace(temporary, directory / (record["id"] + ".json"))
        return True
    except OSError as error:
        print(f"Could not save Numberology result: {error}", file=sys.stderr)
        return False
    finally:
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass


class NumberologySession:
    """Native Python adapter for source-backed Numberology."""
    ACTION_START, ACTION_WRITE, ACTION_BACKSPACE, ACTION_SUBMIT = 0, 1, 2, 3
    ACTION_PREVIOUS_PAGE, ACTION_NEXT_PAGE = 4, 5
    INFO_PHASE, INFO_LEVEL, INFO_TRIAL, INFO_TOTAL = 0, 1, 2, 3
    INFO_SHOWN, INFO_TYPED, INFO_TYPED_LENGTH = 4, 5, 6
    INFO_VERDICT, INFO_RIGHT = 8, 10

    def __init__(self, core, args) -> None:
        self.core = core
        self.args = args
        saved = read_numberology_settings()
        self.options = [getattr(args, 'numberology_level', None) or saved[0],
                        getattr(args, 'numberology_trials', None) or saved[1],
                        saved[2] if getattr(args, 'numberology_no_adaptive', None) is None
                        else int(not args.numberology_no_adaptive)]
        self.options_draft = None
        self.options_selection = 0
        self.options_from_hub = False
        self.level_editing = False
        self.level_edit_value = 0
        self.result_record = None
        self.result_pending = False
        self.failed_results = []
        self.handle = core.numberology_create(*self.options, args.seed)
        if self.handle <= 0:
            raise SystemExit("native Numberology rejected its options")
        self.black_background = args.black_background

    @property
    def state(self):
        return tuple(self.core.numberology_info(self.handle, field)
                     for field in range(14))

    def frame_bytes(self, _core, width=912, height=684) -> bytes:
        if self.options_draft is not None:
            return self.core.numberology_options_frame(int(self.black_background), self.options_selection, *self.options_draft)
        return self.core.numberology_frame(
            self.handle, 1 if self.black_background else 0, width, height)

    def describe(self, _frame) -> str:
        current = self.state
        names = ("ready", "working", "judged", "done")
        phase = current[self.INFO_PHASE]
        name = names[phase] if 0 <= phase < len(names) else "unknown"
        return (f"Numberology {name} · trial {current[self.INFO_TRIAL]}"
                f"/{current[self.INFO_TOTAL]} · right {current[self.INFO_RIGHT]}"
                f" · level {current[self.INFO_LEVEL]}")

    def action(self, action: int, value: int = 0) -> None:
        phase = self.state[self.INFO_PHASE]
        self.core.numberology_action(self.handle, action, value, 0)
        current = self.state
        if phase in (0, 3) and current[self.INFO_PHASE] == 1:
            if self.result_pending and self.result_record is not None:
                self.failed_results.append(self.result_record)
            self.result_record = {"id": "numberology-" + uuid.uuid4().hex, "task": "numberology",
                                  "started_at": time.time(), "options": list(self.options),
                                  "results": [], "completed": False}
            self.result_pending = False
        if phase == 1 and current[self.INFO_PHASE] == 2 and self.result_record is not None:
            self.result_record["results"].append({"trial": current[self.INFO_TRIAL],
                                                  "level": str(current[self.INFO_LEVEL]),
                                                  "correct": current[self.INFO_VERDICT] == 1,
                                                  "judged_at": time.time()})
            self.result_pending = True
        if phase != 3 and current[self.INFO_PHASE] == 3 and self.result_record is not None:
            self.result_record["completed"] = True
            self.result_record["right"] = current[self.INFO_RIGHT]
            self.result_pending = True
        if self.result_pending:
            self.result_pending = not write_numberology_result(self.result_record)
        self.failed_results = [record for record in self.failed_results
                               if not write_numberology_result(record)]
        if phase != 3 and current[self.INFO_PHASE] == 3 and self.options[2]:
            next_level = current[13]
            if next_level > self.options[0]:
                self.options[0] = next_level
                self.args.numberology_level = next_level
                write_numberology_settings(self.options)

    def modify_option(self, delta):
        row = self.options_selection
        if row == 0:
            self.options_draft[0] = max(1, min(NUMBEROLOGY_MAX_LEVEL, self.options_draft[0] + delta))
            self.level_editing = False
        elif row == 1:
            index = NUMBEROLOGY_TRIALS.index(self.options_draft[1])
            self.options_draft[1] = NUMBEROLOGY_TRIALS[(index + delta) % len(NUMBEROLOGY_TRIALS)]
        else:
            self.options_draft[2] = 1 - self.options_draft[2]

    def key(self, symbol, key) -> None:
        if self.options_draft is not None:
            if symbol == key.ESCAPE:
                self.options_draft = None
            elif symbol == key.UP:
                self.options_selection = max(0, self.options_selection - 1)
                self.level_editing = False
            elif symbol == key.DOWN:
                self.options_selection = min(2, self.options_selection + 1)
                self.level_editing = False
            elif symbol in (key.LEFT, key.RIGHT, key.SPACE):
                self.modify_option(-1 if symbol == key.LEFT else 1)
            elif symbol in (key.BACKSPACE, key.DELETE) and self.options_selection == 0:
                current = self.level_edit_value if self.level_editing else self.options_draft[0]
                self.level_edit_value = current // 10
                self.options_draft[0] = max(1, self.level_edit_value)
                self.level_editing = True
            elif symbol == key.RETURN:
                fresh = self.core.numberology_create(*self.options_draft, self.args.seed)
                if fresh > 0:
                    self.core.numberology_destroy(self.handle)
                    self.handle = fresh
                    self.options = list(self.options_draft)
                    self.args.numberology_level, self.args.numberology_trials = self.options[:2]
                    self.args.numberology_no_adaptive = not self.options[2]
                    write_numberology_settings(self.options)
                self.options_draft = None
            return
        phase = self.state[self.INFO_PHASE]
        if symbol == key.O and phase != 1:
            self.options_draft = list(self.options)
            self.options_selection = 0
            self.level_editing = False
        elif symbol == key.PAGEUP: self.action(self.ACTION_PREVIOUS_PAGE)
        elif symbol == key.PAGEDOWN: self.action(self.ACTION_NEXT_PAGE)
        elif symbol == key.SPACE and phase != 1: self.action(self.ACTION_START)
        elif symbol == key.RETURN and phase == 1: self.action(self.ACTION_SUBMIT)
        elif symbol in (key.BACKSPACE, key.DELETE): self.action(self.ACTION_BACKSPACE)

    def text(self, text: str) -> None:
        if self.options_draft is not None:
            if self.options_selection == 0:
                for character in text:
                    if character in '0123456789':
                        value = (self.level_edit_value if self.level_editing else 0) * 10 + int(character)
                        if value <= NUMBEROLOGY_MAX_LEVEL:
                            self.level_edit_value = value
                            self.options_draft[0] = max(1, value)
                            self.level_editing = True
            return
        if self.state[self.INFO_PHASE] == 1:
            for character in text:
                self.action(self.ACTION_WRITE, ord(character))

    def paste(self) -> None:
        if self.options_draft is None and self.state[self.INFO_PHASE] == 1:
            self.text(read_scramble_clipboard())

    def pointer(self, x, y, width, height, button=0, _motion=False):
        if button != 0:
            return
        if self.options_draft is not None:
            row = round((474 - y * 684 / height) / 48)
            if 102 <= x * 912 / width <= 810 and 0 <= row < 3 and abs(y * 684 / height - (474 - row * 48)) <= 18:
                if row == self.options_selection: self.modify_option(1)
                else: self.options_selection = row
        else:
            phase = self.state[self.INFO_PHASE]
            viewport = Viewport(width, height)
            page = numberology_page_at((x - viewport.offset_x) / viewport.scale,
                                       (y - viewport.offset_y) / viewport.scale)
            if phase in (1, 2) and self.core.numberology_info(self.handle, 22) > 1 and page:
                self.action(page)
            elif phase != 1:
                self.action(self.ACTION_START)

    def close(self) -> None:
        if self.result_pending:
            self.result_pending = not write_numberology_result(self.result_record)
        self.failed_results = [record for record in self.failed_results
                               if not write_numberology_result(record)]
        if self.handle > 0:
            self.core.numberology_destroy(self.handle)
            self.handle = 0


class JigsawSession:
    """Native Python adapter for source-backed Jigsaw Puzzle."""
    ACTION_START, ACTION_PICK, ACTION_TICK = 0, 1, 2
    INFO_PHASE, INFO_SIDE, INFO_TRIAL_SIDE, INFO_PUZZLE = 0, 1, 2, 3
    INFO_TOTAL, INFO_PAR, INFO_SWAPS, INFO_PICKED = 4, 5, 6, 7
    INFO_VERDICT, INFO_RESULTS = 8, 9
    INFO_MARK_PLACED = 14

    def __init__(self, core, args) -> None:
        self.core = core
        self.handle = core.jigsaw_create_options(
            args.jigsaw_side, args.jigsaw_puzzles,
            1 if args.jigsaw_adaptive else 0,
            1 if args.jigsaw_preview else 0,
            1 if args.jigsaw_mark_placed else 0, args.seed)
        if self.handle <= 0:
            raise SystemExit("native Jigsaw rejected its options")
        self.black_background = args.black_background

    @property
    def state(self):
        return tuple(self.core.jigsaw_info(self.handle, field) for field in range(15))

    def frame_bytes(self, _core, width=912, height=684) -> bytes:
        return self.core.jigsaw_frame(
            self.handle, 1 if self.black_background else 0, width, height)

    def describe(self, _frame) -> str:
        current = self.state
        names = ("ready", "solving", "solved", "done")
        phase = current[self.INFO_PHASE]
        name = names[phase] if 0 <= phase < len(names) else "unknown"
        return (f"Jigsaw {name} · puzzle {current[self.INFO_PUZZLE]}"
                f"/{current[self.INFO_TOTAL]} · swaps {current[self.INFO_SWAPS]}")

    def action(self, action: int, value: int = 0, now_ms: int = 0) -> None:
        self.core.jigsaw_action(self.handle, action, value, now_ms)

    def pointer(self, x: float, y: float, width: int, height: int) -> None:
        self.core.jigsaw_pointer(self.handle, int(x * 1000000 / width),
                                 int(y * 1000000 / height), width, height, 0)

    def key(self, symbol, key) -> None:
        phase = self.state[self.INFO_PHASE]
        if symbol in (key.SPACE, key.RETURN):
            self.action(self.ACTION_START if phase in (0, 3) else self.ACTION_TICK)
        else:
            digits = {getattr(key, f"_{digit}"): digit for digit in range(10)}
            if symbol in digits and phase == 1:
                self.action(self.ACTION_PICK, digits[symbol])

    def close(self) -> None:
        if self.handle > 0:
            self.core.jigsaw_destroy(self.handle)
            self.handle = 0


class SudokuSession:
    """Native Python adapter for source-backed Sudoku."""
    ACTION_START, ACTION_UP, ACTION_DOWN, ACTION_LEFT = 0, 1, 2, 3
    ACTION_RIGHT, ACTION_WRITE, ACTION_ERASE, ACTION_PENCIL = 4, 5, 6, 7
    INFO_PHASE, INFO_SIZE, INFO_CURSOR, INFO_PENCIL = 0, 5, 7, 8

    def __init__(self, core, args) -> None:
        self.core = core
        self.handle = core.sudoku_create(
            args.sudoku_level, args.sudoku_puzzles,
            0 if args.sudoku_no_clashes else 1,
            0 if args.sudoku_no_adaptive else 1, args.seed)
        if self.handle <= 0:
            raise SystemExit("native Sudoku rejected its options")
        self.black_background = args.black_background

    @property
    def state(self):
        return tuple(self.core.sudoku_info(self.handle, field) for field in range(21))

    def frame_bytes(self, _core, width=912, height=684) -> bytes:
        return self.core.sudoku_frame(
            self.handle, 1 if self.black_background else 0, width, height)

    def describe(self, _frame) -> str:
        state = self.state
        names = ("ready", "solving", "solved", "done")
        phase = state[self.INFO_PHASE]
        name = names[phase] if 0 <= phase < len(names) else "unknown"
        return (f"Sudoku {name} · cursor {state[self.INFO_CURSOR]}"
                f" · mistakes {state[9]}")

    def action(self, action: int, value: int = 0) -> None:
        self.core.sudoku_action(self.handle, action, value, 0)

    def key(self, symbol, key) -> None:
        state = self.state
        phase = state[self.INFO_PHASE]
        if symbol in (key.SPACE, key.RETURN):
            self.action(self.ACTION_START)
        elif phase == 1 and symbol == key.UP:
            self.action(self.ACTION_UP)
        elif phase == 1 and symbol == key.DOWN:
            self.action(self.ACTION_DOWN)
        elif phase == 1 and symbol == key.LEFT:
            self.action(self.ACTION_LEFT)
        elif phase == 1 and symbol == key.RIGHT:
            self.action(self.ACTION_RIGHT)
        elif phase == 1 and symbol in (key.BACKSPACE, key.DELETE,
                                       key._0, key.NUM_0):
            self.action(self.ACTION_ERASE)
        elif phase == 1 and symbol == key.N:
            self.action(self.ACTION_PENCIL)
        elif phase == 1:
            if symbol == key.C and state[self.INFO_SIZE] < 12:
                return
            digits = {getattr(key, f"_{digit}"): digit for digit in range(1, 10)}
            digits.update({getattr(key, f"NUM_{digit}"): digit for digit in range(1, 10)})
            digits.update({getattr(key, letter): value
                           for value, letter in enumerate("ABCDEFG", start=10)})
            if symbol in digits:
                self.action(self.ACTION_WRITE, digits[symbol])

    def close(self) -> None:
        if self.handle > 0:
            self.core.sudoku_destroy(self.handle)
            self.handle = 0


class GoSession:
    """Native Python adapter for source-backed winning-move Go."""
    ACTION_START, ACTION_ANSWER, ACTION_NEXT = 0, 1, 2
    ACTION_UP, ACTION_DOWN, ACTION_LEFT, ACTION_RIGHT = 3, 4, 5, 6
    ACTION_LEVEL = 7
    INFO_PHASE, INFO_SIZE, INFO_CURSOR_X, INFO_CURSOR_Y = 0, 4, 5, 6

    def __init__(self, core, args) -> None:
        self.core = core
        self.handle = core.go_create(args.go_level, args.go_trials, args.seed)
        if self.handle <= 0:
            raise SystemExit("native Go rejected its options")
        self.black_background = args.black_background

    @property
    def state(self):
        return tuple(self.core.go_info(self.handle, field) for field in range(13))

    def frame_bytes(self, _core, width=912, height=684) -> bytes:
        return self.core.go_frame(self.handle, 1 if self.black_background else 0,
                                  width, height)

    def describe(self, _frame) -> str:
        state = self.state
        names = ("ready", "solving", "judged", "done")
        phase = state[self.INFO_PHASE]
        name = names[phase] if 0 <= phase < len(names) else "unknown"
        return f"Go {name} · trial {state[2]}/{state[3]} · correct {state[7]}"

    def action(self, action: int, value: int = 0) -> None:
        self.core.go_action(self.handle, action, value, 0)

    def pointer(self, x: float, y: float, width: int, height: int) -> None:
        self.core.go_pointer(self.handle, int(x * 1000000 / width),
                             int(y * 1000000 / height), width, height, 0)

    def key(self, symbol, key) -> None:
        phase = self.state[self.INFO_PHASE]
        if symbol in (key.SPACE, key.RETURN):
            if phase in (0, 3):
                self.action(self.ACTION_START)
            elif phase == 1:
                state = self.state
                self.action(self.ACTION_ANSWER,
                            state[self.INFO_CURSOR_Y] * state[self.INFO_SIZE] +
                            state[self.INFO_CURSOR_X])
            elif phase == 2:
                self.action(self.ACTION_NEXT)
        elif phase == 1 and symbol == key.UP:
            self.action(self.ACTION_UP)
        elif phase == 1 and symbol == key.DOWN:
            self.action(self.ACTION_DOWN)
        elif phase == 1 and symbol == key.LEFT:
            self.action(self.ACTION_LEFT)
        elif phase == 1 and symbol == key.RIGHT:
            self.action(self.ACTION_RIGHT)
        elif phase in (0, 3):
            digits = {getattr(key, f"_{digit}"): digit for digit in range(1, 10)}
            digits.update({getattr(key, f"NUM_{digit}"): digit for digit in range(1, 10)})
            digits.update({key._0: 10, key.NUM_0: 10})
            if symbol in digits:
                self.action(self.ACTION_LEVEL, digits[symbol])

    def close(self) -> None:
        if self.handle > 0:
            self.core.go_destroy(self.handle)
            self.handle = 0


CROSSWORD_TRIALS = (1, 2, 3, 5, 8, 10)


def crossword_settings_path() -> Path:
    override = os.environ.get("NW_CROSSWORD_SETTINGS_PATH")
    if override:
        return Path(override).expanduser()
    if sys.platform == "win32":
        return Path(os.environ.get("APPDATA", str(Path.home()))) / "Neural Workshop" / "crossword-options"
    return Path.home() / ".neural-workshop" / "crossword-options"


def read_crossword_settings() -> tuple[int, int, int, int]:
    defaults = (2, 3, 1, 1)
    try:
        fields = tuple(map(int, crossword_settings_path().read_text(encoding="ascii").split()))
        if len(fields) == 4 and 1 <= fields[0] <= 10 and fields[1] in CROSSWORD_TRIALS and all(x in (0, 1) for x in fields[2:]):
            return fields
    except (OSError, UnicodeError, ValueError):
        pass
    return defaults


def write_crossword_settings(values) -> None:
    path = crossword_settings_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        # Write a sibling first so interrupted writes do not corrupt settings.
        import tempfile
        with tempfile.NamedTemporaryFile(mode="w", encoding="ascii", dir=path.parent, delete=False) as output:
            temporary = Path(output.name)
            output.write("%d %d %d %d\n" % tuple(values))
        try:
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)
    except OSError as error:
        print(f"Could not save Crossword settings: {error}", file=sys.stderr)


SCRABBLE_TRIALS = (1, 2, 3, 5, 8, 10, 15)


def scrabble_settings_path() -> Path:
    override = os.environ.get("NW_SCRABBLE_SETTINGS_PATH")
    if override:
        return Path(override).expanduser()
    if sys.platform == "win32":
        return Path(os.environ.get("APPDATA", str(Path.home()))) / "Neural Workshop" / "scrabble-options"
    return Path.home() / ".neural-workshop" / "scrabble-options"


def read_scrabble_settings() -> tuple[int, int, int, int]:
    defaults = (3, 5, 1, 1)
    try:
        fields = tuple(map(int, scrabble_settings_path().read_text(encoding="ascii").split()))
        if len(fields) == 4 and 1 <= fields[0] <= 10 and fields[1] in SCRABBLE_TRIALS and all(x in (0, 1) for x in fields[2:]):
            return fields
    except (OSError, UnicodeError, ValueError):
        pass
    return defaults


def write_scrabble_settings(values) -> None:
    path = scrabble_settings_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        # Write a sibling first so interrupted writes do not corrupt settings.
        import tempfile
        with tempfile.NamedTemporaryFile(mode="w", encoding="ascii", dir=path.parent, delete=False) as output:
            temporary = Path(output.name)
            output.write("%d %d %d %d\n" % tuple(values))
        try:
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)
    except OSError as error:
        print(f"Could not save Scrabble settings: {error}", file=sys.stderr)


NUMBEROLOGY_TRIALS = (1, 2, 3, 5, 6, 8, 10, 15)
NUMBEROLOGY_MAX_LEVEL = (1 << 63) - 1


def parse_numberology_level(text: str) -> int:
    try:
        value = int(text)
    except ValueError as error:
        raise argparse.ArgumentTypeError("level must be a positive integer") from error
    if not 1 <= value <= NUMBEROLOGY_MAX_LEVEL:
        raise argparse.ArgumentTypeError("level is outside the supported integer range")
    return value


def numberology_settings_path() -> Path:
    override = os.environ.get("NW_NUMBEROLOGY_SETTINGS_PATH")
    if override:
        return Path(override).expanduser()
    if sys.platform == "win32":
        return Path(os.environ.get("APPDATA", str(Path.home()))) / "Neural Workshop" / "numberology-options"
    return Path.home() / ".neural-workshop" / "numberology-options"


def read_numberology_settings() -> tuple[int, int, int]:
    try:
        fields = tuple(map(int, numberology_settings_path().read_text(encoding="ascii").split()))
        if len(fields) == 3 and 1 <= fields[0] <= NUMBEROLOGY_MAX_LEVEL and fields[1] in NUMBEROLOGY_TRIALS and fields[2] in (0, 1):
            return fields
    except (OSError, UnicodeError, ValueError):
        pass
    return (1, 6, 1)


def write_numberology_settings(values) -> None:
    path = numberology_settings_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        import tempfile
        with tempfile.NamedTemporaryFile(mode="w", encoding="ascii", dir=path.parent, delete=False) as output:
            temporary = Path(output.name)
            output.write("%d %d %d\n" % tuple(values))
        try:
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)
    except OSError as error:
        print(f"Could not save Numberology settings: {error}", file=sys.stderr)


ALGEBRA_TRIALS = (1, 2, 3, 5, 6, 8, 10, 15)

def algebra_settings_path() -> Path:
    override = os.environ.get("NW_ALGEBRA_SETTINGS_PATH")
    if override:
        return Path(override).expanduser()
    if sys.platform == "win32":
        return Path(os.environ.get("APPDATA", str(Path.home()))) / "Neural Workshop" / "algebra-options"
    return Path.home() / ".neural-workshop" / "algebra-options"


def read_algebra_settings() -> tuple[int, int, int, int]:
    defaults = (3, 6, 1, 1)
    try:
        fields = tuple(map(int, algebra_settings_path().read_text(encoding="ascii").split()))
        if len(fields) == 4 and 1 <= fields[0] <= 12 and fields[1] in ALGEBRA_TRIALS and all(x in (0, 1) for x in fields[2:]):
            return fields
    except (OSError, UnicodeError, ValueError):
        pass
    return defaults


def write_algebra_settings(values) -> None:
    path = algebra_settings_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        # Write a sibling first so interrupted writes do not corrupt settings.
        import tempfile
        with tempfile.NamedTemporaryFile(mode="w", encoding="ascii", dir=path.parent, delete=False) as output:
            temporary = Path(output.name)
            output.write("%d %d %d %d\n" % tuple(values))
        try:
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)
    except OSError as error:
        print(f"Could not save Algebra settings: {error}", file=sys.stderr)


def scramble_settings_path() -> Path:
    override = os.environ.get("NW_SCRAMBLE_SETTINGS_PATH")
    if override:
        return Path(override).expanduser()
    if sys.platform == "win32":
        return Path(os.environ.get("APPDATA", str(Path.home()))) / "Neural Workshop" / "scramble-options"
    return Path.home() / ".neural-workshop" / "scramble-options"


def read_scramble_settings() -> tuple[int, int, int, int]:
    defaults = (3, 5, 1, 1)
    try:
        fields = tuple(map(int, scramble_settings_path().read_text(encoding="ascii").split()))
        if len(fields) == 4 and 1 <= fields[0] <= 12 and fields[1] in SCRABBLE_TRIALS and all(x in (0, 1) for x in fields[2:]):
            return fields
    except (OSError, UnicodeError, ValueError):
        pass
    return defaults


def write_scramble_settings(values) -> None:
    path = scramble_settings_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        # Write a sibling first so interrupted writes do not corrupt settings.
        import tempfile
        with tempfile.NamedTemporaryFile(mode="w", encoding="ascii", dir=path.parent, delete=False) as output:
            temporary = Path(output.name)
            output.write("%d %d %d %d\n" % tuple(values))
        try:
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)
    except OSError as error:
        print(f"Could not save Scramble settings: {error}", file=sys.stderr)


def read_scramble_clipboard() -> str:
    """Read text only in response to the user's native paste shortcut."""
    if sys.platform == 'win32':
        try:
            import ctypes
            from ctypes import wintypes
            user32, kernel32 = ctypes.windll.user32, ctypes.windll.kernel32
            user32.GetClipboardData.restype = wintypes.HANDLE
            kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]
            kernel32.GlobalLock.restype = ctypes.c_void_p
            kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
            if not user32.OpenClipboard(None): return ''
            try:
                handle = user32.GetClipboardData(13)  # CF_UNICODETEXT
                if not handle: return ''
                pointer = kernel32.GlobalLock(handle)
                if not pointer: return ''
                try: return ctypes.wstring_at(pointer)
                finally: kernel32.GlobalUnlock(handle)
            finally:
                user32.CloseClipboard()
        except (OSError, AttributeError):
            return ''
    import shutil
    import subprocess
    candidates = ([('pbpaste',)] if sys.platform == 'darwin' else
                  [('wl-paste', '--no-newline'), ('xclip', '-selection', 'clipboard', '-o'),
                   ('xsel', '--clipboard', '--output')])
    for command in candidates:
        if shutil.which(command[0]):
            try:
                result = subprocess.run(command, capture_output=True, text=True, timeout=2, check=True)
                return result.stdout
            except (OSError, UnicodeError, subprocess.SubprocessError):
                continue
    try:
        import tkinter
        root = tkinter.Tk()
        root.withdraw()
        try: return root.clipboard_get()
        finally: root.destroy()
    except (ImportError, RuntimeError, OSError):
        pass
    except Exception as error:
        # Tk can be installed without an available display or clipboard.
        if error.__class__.__name__ != 'TclError': raise
    return ''


class ScrambleSession:
    """Native text input and lifecycle for the source-backed Scramble game."""
    def __init__(self, core, args):
        self.core = core
        self.args = args
        self.black_background = args.black_background
        self.options = [getattr(args, 'scramble_level', 3), getattr(args, 'scramble_trials', 5),
                        int(not getattr(args, 'scramble_no_count', False)), int(not getattr(args, 'scramble_no_adaptive', False))]
        self.options_draft = None
        self.options_selection = 0
        self.options_from_hub = False
        self.handle = core.scramble_create(getattr(args, 'scramble_level', 3),
            getattr(args, 'scramble_trials', 5), int(not getattr(args, 'scramble_no_count', False)),
            int(not getattr(args, 'scramble_no_adaptive', False)), args.seed)
        if self.handle <= 0:
            raise SystemExit('native Scramble rejected its options')
        self.suppress_space = False
        if sys.platform == 'darwin':
            data_dir = Path.home() / 'Library/Application Support/Brain Workshop/data/words'
        elif sys.platform == 'win32':
            data_dir = Path(os.environ.get('APPDATA', str(Path.home()))) / 'Brain Workshop/data/words'
        else:
            data_dir = Path.home() / '.brainworkshop/data/words'
        index_arg = getattr(args, 'scramble_index', None)
        sentences_arg = getattr(args, 'scramble_sentences', None)
        index_path = Path(index_arg).expanduser() if index_arg else data_dir / 'lexicon.tsv'
        sentence_path = Path(sentences_arg).expanduser() if sentences_arg else data_dir / 'sentences.txt'
        try:
            if index_arg and not index_path.is_file(): raise FileNotFoundError(index_path)
            if sentences_arg and not sentence_path.is_file(): raise FileNotFoundError(sentence_path)
            index = index_path.read_bytes() if index_path.is_file() else b''
            has_sentences = sentence_path.is_file() and (bool(sentences_arg) or sentence_path.stat().st_size > 4096)
            sentences = sentence_path.read_bytes() if has_sentences else b''
            if index or sentences:
                if core.scramble_set_corpus(self.handle, index, sentences) != 0:
                    raise ValueError('invalid or oversized corpus')
        except (OSError, ValueError) as error:
            self.close()
            raise SystemExit(f'Cannot load Scramble corpus: {error}') from error

    @property
    def state(self):
        return tuple(self.core.scramble_info(self.handle, field) for field in range(17))

    def frame_bytes(self, _core, width=912, height=684):
        if self.options_draft is not None:
            return self.core.scramble_options_frame(int(self.black_background), self.options_selection, *self.options_draft)
        return self.core.scramble_frame(self.handle, int(self.black_background), width, height)

    def describe(self, _frame):
        state = self.state
        return f'Scramble · line {state[2]}/{state[3]} · right {state[7]}'

    def action(self, action, value=0):
        phase = self.core.scramble_info(self.handle, 0)
        result = self.core.scramble_action(self.handle, action, value, int(time.monotonic() * 1000))
        if phase != 1 and self.core.scramble_info(self.handle, 0) == 1:
            self.core.scramble_action(self.handle, 5, 0, int(time.monotonic() * 1000))
        return result

    def key(self, symbol, key):
        if self.options_draft is not None:
            if symbol == key.ESCAPE:
                self.options_draft = None
            elif symbol == key.UP:
                self.options_selection = max(0, self.options_selection - 1)
            elif symbol == key.DOWN:
                self.options_selection = min(3, self.options_selection + 1)
            elif symbol in (key.LEFT, key.RIGHT, key.SPACE):
                self.modify_option(-1 if symbol == key.LEFT else 1)
            elif symbol == key.RETURN:
                level, trials, count, adaptive = self.options_draft
                packed = level | (SCRABBLE_TRIALS.index(trials) << 4) | (count << 7) | (adaptive << 8)
                if self.action(4, packed) == 1:
                    self.options = list(self.options_draft)
                    self.args.scramble_level, self.args.scramble_trials = level, trials
                    self.args.scramble_no_count = not count
                    self.args.scramble_no_adaptive = not adaptive
                    write_scramble_settings(self.options)
                self.options_draft = None
            return
        phase = self.state[0]
        if symbol == key.O and phase != 1:
            self.options_draft = list(self.options)
            self.options_selection = 0
        elif symbol == key.SPACE and phase != 1:
            self.action(0)
            self.suppress_space = True
        elif symbol in (key.RETURN, getattr(key, 'NUM_ENTER', key.RETURN)):
            self.action(3)
        elif symbol in (key.BACKSPACE, key.DELETE):
            self.action(2)

    def text(self, text):
        if self.options_draft is not None:
            return
        for char in text:
            if self.suppress_space and char == ' ':
                self.suppress_space = False
                continue
            self.suppress_space = False
            value = 26 if char == ' ' else ord(char.lower()) - 97 if char.isascii() and char.isalpha() else 27
            self.action(1, value)

    def paste(self):
        if self.options_draft is None and self.state[0] == 1:
            self.text(read_scramble_clipboard())

    def modify_option(self, delta):
        choices = (tuple(range(1, 13)), SCRABBLE_TRIALS, (0, 1), (0, 1))
        values = choices[self.options_selection]
        current = self.options_draft[self.options_selection]
        self.options_draft[self.options_selection] = values[(values.index(current) + delta) % len(values)]

    def pointer(self, x, y, width, height, button=0, _motion=False):
        if self.options_draft is not None:
            if button == 0:
                row = round((474 - y * 684 / height) / 48)
                if 0 <= row < 4 and abs(y * 684 / height - (474 - row * 48)) <= 18:
                    if row == self.options_selection: self.modify_option(1)
                    else: self.options_selection = row
            return
        if self.state[0] != 1:
            self.action(0)

    def close(self):
        if self.handle:
            self.core.scramble_destroy(self.handle)
            self.handle = 0


class ScrabbleSession:
    """Native adapter for the source-backed Scrabble controller."""
    ACTION_START = 0

    def __init__(self, core, args):
        self.core = core
        self.black_background = args.black_background
        self.args = args
        self.options = [args.scrabble_level, args.scrabble_trials,
                        int(not args.scrabble_no_premiums), int(not args.scrabble_no_adaptive)]
        self.options_draft = None
        self.options_selection = 0
        self.options_from_hub = False
        self.handle = core.scrabble_create(args.scrabble_level, args.scrabble_trials,
            int(not args.scrabble_no_premiums), int(not args.scrabble_no_adaptive), args.seed)
        if self.handle <= 0:
            raise SystemExit("native Scrabble rejected its options")
        if args.scrabble_lexicon:
            path = Path(args.scrabble_lexicon).expanduser()
        elif sys.platform == "darwin":
            path = Path.home() / "Library/Application Support/Brain Workshop/data/words/lexicon.tsv"
        elif sys.platform == "win32":
            path = Path(os.environ.get("APPDATA", str(Path.home()))) / "Brain Workshop/data/words/lexicon.tsv"
        else:
            path = Path.home() / ".brainworkshop/data/words/lexicon.tsv"
        try:
            if path.is_file():
                if core.scrabble_set_lexicon(self.handle, path.read_bytes()) != 0:
                    raise ValueError("the index is invalid or exceeds the supported capacity")
            elif args.scrabble_lexicon:
                raise FileNotFoundError(path)
        except (OSError, ValueError) as error:
            self.close()
            raise SystemExit(f"Cannot load Scrabble lexicon {path}: {error}") from error

    @property
    def state(self):
        return tuple(self.core.scrabble_info(self.handle, field) for field in range(19))

    def frame_bytes(self, _core, width=912, height=684):
        if self.options_draft is not None:
            return self.core.scrabble_options_frame(int(self.black_background), self.options_selection, *self.options_draft)
        return self.core.scrabble_frame(self.handle, int(self.black_background), width, height)

    def describe(self, _frame):
        state = self.state
        return f"Scrabble · board {state[2]}/{state[3]} · score {state[5]}"

    def action(self, action, value=0):
        phase = self.core.scrabble_info(self.handle, 0)
        result = self.core.scrabble_action(self.handle, action, value, int(time.monotonic() * 1000))
        if phase != 1 and self.core.scrabble_info(self.handle, 0) == 1:
            self.core.scrabble_action(self.handle, 10, 0, int(time.monotonic() * 1000))
        return result

    def pointer(self, x, y, width, height, button=0, motion=False):
        if self.options_draft is not None:
            if not motion and button == 0:
                row = round((474 - y * 684 / height) / 48)
                if 0 <= row < 4 and abs(y * 684 / height - (474 - row * 48)) <= 18:
                    if row == self.options_selection: self.modify_option(1)
                    else: self.options_selection = row
            return
        phase = self.core.scrabble_info(self.handle, 0)
        result = self.core.scrabble_pointer(self.handle, int(x * 1000000 / width),
            int(y * 1000000 / height), width, height, button, int(motion), int(time.monotonic() * 1000))
        if phase != 1 and self.core.scrabble_info(self.handle, 0) == 1:
            self.core.scrabble_action(self.handle, 10, 0, int(time.monotonic() * 1000))
        return result

    def modify_option(self, delta):
        choices = (tuple(range(1, 11)), SCRABBLE_TRIALS, (0, 1), (0, 1))
        values = choices[self.options_selection]
        current = self.options_draft[self.options_selection]
        self.options_draft[self.options_selection] = values[(values.index(current) + delta) % len(values)]

    def key(self, symbol, key):
        if self.options_draft is not None:
            if symbol == key.ESCAPE: self.options_draft = None
            elif symbol == key.UP: self.options_selection = max(0, self.options_selection - 1)
            elif symbol == key.DOWN: self.options_selection = min(3, self.options_selection + 1)
            elif symbol in (key.LEFT, key.RIGHT, key.SPACE): self.modify_option(-1 if symbol == key.LEFT else 1)
            elif symbol == key.RETURN:
                level, trials, premiums, adaptive = self.options_draft
                packed = level | (SCRABBLE_TRIALS.index(trials) << 4) | (premiums << 7) | (adaptive << 8)
                if self.action(9, packed) == 1:
                    self.options = self.options_draft
                    self.args.scrabble_level, self.args.scrabble_trials = level, trials
                    self.args.scrabble_no_premiums = not premiums
                    self.args.scrabble_no_adaptive = not adaptive
                    write_scrabble_settings(self.options)
                self.options_draft = None
            return
        if symbol in (key.O, key.C):
            self.options_draft = self.options.copy()
            self.options_selection = 0
            return
        phase = self.state[0]
        if symbol == key.SPACE and phase in (0, 2, 3):
            self.action(0)
        elif phase == 1:
            actions = {key.RETURN: 1, key.LEFT: 2, key.RIGHT: 3, key.TAB: 4,
                       key.UP: 5, key.DOWN: 6, key.BACKSPACE: 8, key.DELETE: 8}
            if symbol in actions:
                self.action(actions[symbol])
            else:
                for slot in range(7):
                    if symbol in (getattr(key, f"_{slot + 1}"), getattr(key, f"NUM_{slot + 1}")):
                        self.action(7, slot)
                        break

    def close(self):
        if self.handle > 0:
            self.core.scrabble_destroy(self.handle)
            self.handle = 0


class CrosswordSession:
    """Native adapter for the source-backed Crossword controller."""
    ACTION_START = 0

    def __init__(self, core, args) -> None:
        self.core = core
        self.handle = core.crossword_create(
            args.crossword_level, args.crossword_trials,
            int(not args.crossword_no_mistakes), int(not args.crossword_no_adaptive), args.seed)
        if self.handle <= 0:
            raise SystemExit("native Crossword rejected its options")
        self.black_background = args.black_background
        self.args = args
        self.options = [args.crossword_level, args.crossword_trials,
                        int(not args.crossword_no_mistakes), int(not args.crossword_no_adaptive)]
        self.options_draft = None
        self.options_selection = 0
        if args.crossword_lexicon:
            path = Path(args.crossword_lexicon).expanduser()
        elif sys.platform == "darwin":
            path = Path.home() / "Library/Application Support/Brain Workshop/data/words/lexicon.tsv"
        elif sys.platform == "win32":
            path = Path(os.environ.get("APPDATA", str(Path.home()))) / "Brain Workshop/data/words/lexicon.tsv"
        else:
            path = Path.home() / ".brainworkshop/data/words/lexicon.tsv"
        try:
            if path.is_file():
                if core.crossword_set_lexicon(self.handle, path.read_bytes()) != 0:
                    raise ValueError("the index is invalid or exceeds the supported capacity")
            elif args.crossword_lexicon:
                raise FileNotFoundError(path)
        except (OSError, ValueError) as error:
            self.close()
            raise SystemExit(f"Cannot load Crossword lexicon {path}: {error}") from error

    @property
    def state(self):
        return tuple(self.core.crossword_info(self.handle, field) for field in range(20))

    def frame_bytes(self, _core, width=912, height=684) -> bytes:
        if self.options_draft is not None:
            return self.core.crossword_options_frame(int(self.black_background),
                self.options_selection, *self.options_draft)
        return self.core.crossword_frame(self.handle, int(self.black_background), width, height)

    def describe(self, _frame) -> str:
        state = self.state
        return f"Crossword · puzzle {state[2]}/{state[3]} · solved {state[9]}"

    def action(self, action, value=0):
        return self.core.crossword_action(self.handle, action, value, int(time.monotonic() * 1000))

    def pointer(self, x, y, width, height, button=0):
        if self.options_draft is not None:
            if button == 0:
                row = round((474 - y * 684 / height) / 48)
                if 0 <= row < 4 and abs(y * 684 / height - (474 - row * 48)) <= 18:
                    if row == self.options_selection:
                        self.modify_option(1)
                    else:
                        self.options_selection = row
            return
        return self.core.crossword_pointer(self.handle, int(x * 1000000 / width),
            int(y * 1000000 / height), width, height, button, int(time.monotonic() * 1000))

    def modify_option(self, delta):
        choices = (tuple(range(1, 11)), (1, 2, 3, 5, 8, 10), (0, 1), (0, 1))
        values = choices[self.options_selection]
        current = self.options_draft[self.options_selection]
        self.options_draft[self.options_selection] = values[(values.index(current) + delta) % len(values)]

    def key(self, symbol, key):
        if self.options_draft is not None:
            if symbol == key.ESCAPE:
                self.options_draft = None
            elif symbol == key.UP:
                self.options_selection = max(0, self.options_selection - 1)
            elif symbol == key.DOWN:
                self.options_selection = min(3, self.options_selection + 1)
            elif symbol in (key.LEFT, key.RIGHT, key.SPACE):
                self.modify_option(-1 if symbol == key.LEFT else 1)
            elif symbol == key.RETURN:
                level, trials, mistakes, adaptive = self.options_draft
                packed = level | ((1, 2, 3, 5, 8, 10).index(trials) << 4) | (mistakes << 7) | (adaptive << 8)
                if self.action(10, packed) == 1:
                    self.options = self.options_draft
                    self.args.crossword_level, self.args.crossword_trials = level, trials
                    self.args.crossword_no_mistakes = not mistakes
                    self.args.crossword_no_adaptive = not adaptive
                    write_crossword_settings(self.options)
                self.options_draft = None
            return
        phase = self.state[0]
        if symbol == key.O and phase != 1:
            self.options_draft = self.options.copy()
            self.options_selection = 0
            return
        if symbol == key.SPACE and phase in (0, 2, 3):
            self.action(0)
        elif phase == 1:
            actions = {key.LEFT: 2, key.RIGHT: 3, key.UP: 4, key.DOWN: 5,
                       key.TAB: 6, key.BACKSPACE: 8, key.DELETE: 8}
            if symbol in actions:
                self.action(actions[symbol])
            else:
                for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
                    if symbol == getattr(key, letter):
                        self.action(7, ord(letter) - ord("A"))
                        break

    def close(self):
        if self.handle > 0:
            self.core.crossword_destroy(self.handle)
            self.handle = 0


class CrossedWiresSession:
    """Native Python adapter for source-backed Crossed Wires."""
    ACTION_START, ACTION_PRESS = 0, 1
    INFO_PHASE, INFO_RUNG, INFO_TRIAL, INFO_TOTAL_TRIALS = 0, 1, 2, 3
    INFO_KEYS, INFO_REACHED, INFO_TARGETS, INFO_RIGHT = 4, 16, 12, 19
    TRIAL_CHOICES = (1, 2, 3, 5, 8, 10, 15, 20)

    def __init__(self, core, args) -> None:
        self.core = core
        self.handle = core.crossed_wires_create(
            args.crossed_wires_level, args.crossed_wires_rounds,
            0 if args.crossed_wires_no_adaptive else 1,
            0 if args.crossed_wires_no_grid else 1, args.seed)
        if self.handle <= 0:
            raise SystemExit("native Crossed Wires rejected its options")
        self.black_background = args.black_background

    @property
    def state(self):
        return tuple(self.core.crossed_wires_info(self.handle, field)
                     for field in range(27))

    def frame_bytes(self, _core, width=912, height=684) -> bytes:
        return self.core.crossed_wires_frame(
            self.handle, 1 if self.black_background else 0, width, height)

    def describe(self, _frame) -> str:
        state = self.state
        names = ("ready", "playing", "scored", "done")
        phase = state[self.INFO_PHASE]
        name = names[phase] if 0 <= phase < len(names) else "unknown"
        return (f"Crossed Wires {name} · round {state[self.INFO_TRIAL]}/"
                f"{state[self.INFO_TOTAL_TRIALS]} · targets "
                f"{state[self.INFO_REACHED]}/{state[self.INFO_TARGETS]} · "
                f"right {state[self.INFO_RIGHT]}")

    def action(self, action: int, value: int = 0) -> None:
        self.core.crossed_wires_action(
            self.handle, action, value, int(time.monotonic() * 1000))

    @staticmethod
    def _key_symbols(key):
        aliases = (
            ((key.UP, key.W, key.NUM_8),
             (key.RIGHT, key.D, key.NUM_6),
             (key.DOWN, key.S, key.NUM_2),
             (key.LEFT, key.A, key.NUM_4)),
            ((key.W, key.NUM_8, key.UP), (key.E, key.NUM_9),
             (key.D, key.NUM_6, key.RIGHT), (key.C, key.NUM_3),
             (key.X, key.NUM_2, key.DOWN), (key.Z, key.NUM_1),
             (key.A, key.NUM_4, key.LEFT), (key.Q, key.NUM_7)),
        )
        return aliases

    def key(self, symbol, key) -> None:
        phase = self.state[self.INFO_PHASE]
        if symbol == key.SPACE:
            if phase in (0, 3) or phase == 2:
                self.action(self.ACTION_START)
            return
        if symbol in (key.O, key.F11):
            # The source O settings dialog is not part of the Python shell;
            # startup options remain available through the CLI.
            return
        keys = self._key_symbols(key)[1 if self.state[self.INFO_KEYS] == 8 else 0]
        for index, aliases in enumerate(keys):
            if symbol in aliases:
                self.action(self.ACTION_PRESS, index)
                return
        if symbol == key.C and len(keys) == 4:
            return

    def close(self) -> None:
        if self.handle > 0:
            self.core.crossed_wires_destroy(self.handle)
            self.handle = 0


class TrackingSession:
    """Native Python adapter for source-backed Moving Targets."""
    ACTION_START = 0
    INFO_PHASE, INFO_BALLS, INFO_TRACKED = 0, 1, 7

    def __init__(self, core, args) -> None:
        self.core = core
        self.handle = core.tracking_create(8, 2, 3, 30, 5, 1, args.seed)
        if self.handle <= 0:
            raise SystemExit("native Moving Targets rejected its options")
        self.black_background = args.black_background

    @property
    def state(self):
        return tuple(self.core.tracking_info(self.handle, field) for field in range(19))

    def frame_bytes(self, _core, width=912, height=684) -> bytes:
        return self.core.tracking_frame(self.handle, 1 if self.black_background else 0,
                                        width, height)

    def describe(self, _frame) -> str:
        names = ("ready", "cueing", "tracking", "picking", "revealing", "done")
        phase = self.state[self.INFO_PHASE]
        name = names[phase] if 0 <= phase < len(names) else "unknown"
        return f"Moving Targets {name} · round {self.state[8]}/{self.state[5]}"

    def action(self, action: int, value: int = 0) -> None:
        self.core.tracking_action(self.handle, action, value, 0)

    def tick(self, now_ms: int) -> None:
        self.core.tracking_advance(self.handle, now_ms)

    def pointer(self, x: float, y: float, width: int, height: int) -> None:
        self.core.tracking_pointer(self.handle, int(x * 1000000 / width),
                                   int(y * 1000000 / height), 0)

    def key(self, symbol, key) -> None:
        if symbol in (key.SPACE, key.RETURN) and self.state[self.INFO_PHASE] in (0, 5):
            self.action(self.ACTION_START)

    def close(self) -> None:
        if self.handle > 0:
            self.core.tracking_destroy(self.handle)
            self.handle = 0


class LookoutSession:
    """Native Python adapter for source-backed Lookout."""
    ACTION_START, ACTION_COLOR, ACTION_FORM = 0, 1, 2
    INFO_PHASE, INFO_WATCHING, INFO_CUE_NUMBER, INFO_TOTAL_CUES = 0, 1, 8, 6
    INFO_HITS, INFO_MISSES, INFO_FALSE_ALARMS = 11, 12, 13

    def __init__(self, core, args) -> None:
        self.core = core
        self.handle = core.lookout_create(8, 2, 30, 1200, 10, 1, args.seed)
        if self.handle <= 0:
            raise SystemExit("native Lookout rejected its options")
        self.black_background = args.black_background

    @property
    def state(self):
        return tuple(self.core.lookout_info(self.handle, field) for field in range(21))

    def frame_bytes(self, _core, width=912, height=684) -> bytes:
        return self.core.lookout_frame(self.handle, 1 if self.black_background else 0,
                                       width, height)

    def describe(self, _frame) -> str:
        names = ("ready", "watching", "feedback", "done")
        state = self.state
        phase = state[self.INFO_PHASE]
        name = names[phase] if 0 <= phase < len(names) else "unknown"
        return (f"Lookout {name} · cue {state[self.INFO_CUE_NUMBER]}/"
                f"{state[self.INFO_TOTAL_CUES]} · hits {state[self.INFO_HITS]} · "
                f"misses {state[self.INFO_MISSES]} · false alarms {state[self.INFO_FALSE_ALARMS]}")

    def action(self, action: int) -> None:
        self.core.lookout_action(self.handle, action, 0, 0)

    def tick(self, now_ms: int) -> None:
        self.core.lookout_advance(self.handle, now_ms)

    def key(self, symbol, key) -> None:
        phase = self.state[self.INFO_PHASE]
        if symbol in (key.SPACE, key.RETURN) and phase in (0, 3):
            self.action(self.ACTION_START)
        elif phase == 1 and symbol == key.J:
            self.core.lookout_action(self.handle, self.ACTION_COLOR, 0, 0)
        elif phase == 1 and symbol == key.F:
            self.core.lookout_action(self.handle, self.ACTION_FORM, 0, 0)

    def close(self) -> None:
        if self.handle > 0:
            self.core.lookout_destroy(self.handle)
            self.handle = 0


class PursuitSession:
    """Native Python adapter for source-backed Pursuit."""
    ACTION_START, ACTION_UP, ACTION_DOWN, ACTION_LEFT, ACTION_RIGHT = 0, 1, 2, 3, 4
    INFO_PHASE, INFO_ROUND, INFO_TOTAL_ROUNDS = 0, 11, 9
    INFO_ON_PERCENT, INFO_VERDICT = 20, 18

    def __init__(self, core, args) -> None:
        self.core = core
        self.handle = core.pursuit_create(20, 40, 400, 90, 16, 0, args.seed)
        if self.handle <= 0:
            raise SystemExit("native Pursuit rejected its options")
        self.black_background = args.black_background

    @property
    def state(self):
        return tuple(self.core.pursuit_info(self.handle, field) for field in range(25))

    def frame_bytes(self, _core, width=912, height=684) -> bytes:
        return self.core.pursuit_frame(self.handle, 1 if self.black_background else 0,
                                       width, height)

    def describe(self, _frame) -> str:
        names = ("ready", "chasing", "feedback", "done")
        state = self.state
        phase = state[self.INFO_PHASE]
        name = names[phase] if 0 <= phase < len(names) else "unknown"
        return (f"Pursuit {name} · round {state[self.INFO_ROUND]}/"
                f"{state[self.INFO_TOTAL_ROUNDS]} · on target {state[self.INFO_ON_PERCENT]}%")

    def action(self, action: int) -> None:
        self.core.pursuit_action(self.handle, action, 0, 0)

    def tick(self, now_ms: int) -> None:
        self.core.pursuit_advance(self.handle, now_ms)

    def pointer(self, x: float, y: float, width: int, height: int) -> None:
        self.core.pursuit_pointer(self.handle, int(x * 1000000 / width),
                                  int(y * 1000000 / height))

    def key(self, symbol, key) -> None:
        phase = self.state[self.INFO_PHASE]
        if symbol in (key.SPACE, key.RETURN) and phase in (0, 3):
            self.action(self.ACTION_START)
        elif phase == 1:
            actions = {key.UP: self.ACTION_UP, key.DOWN: self.ACTION_DOWN,
                       key.LEFT: self.ACTION_LEFT, key.RIGHT: self.ACTION_RIGHT}
            if symbol in actions:
                self.action(actions[symbol])

    def close(self) -> None:
        if self.handle > 0:
            self.core.pursuit_destroy(self.handle)
            self.handle = 0


class OutOfSightSession:
    """Native Python adapter for source-backed Out of Sight."""
    ACTION_START, ACTION_MINE, ACTION_NOT_MINE = 0, 1, 2
    INFO_PHASE, INFO_ROUND, INFO_TOTAL_ROUNDS = 0, 10, 9
    INFO_HELD, INFO_HITS, INFO_WRONG, INFO_LATE = 11, 12, 13, 14

    def __init__(self, core, args) -> None:
        self.core = core
        # packed_extra uses source option indices: width=9, probes=6,
        # rounds=3, adaptive=1.
        packed = 2 + (2 * 6) + (2 * 6 * 7) + (1 * 6 * 7 * 8)
        self.handle = core.out_of_sight_create(8, 2, 30, 1200, 2, packed, args.seed)
        if self.handle <= 0:
            raise SystemExit("native Out of Sight rejected its options")
        self.black_background = args.black_background

    @property
    def state(self):
        return tuple(self.core.out_of_sight_info(self.handle, field) for field in range(30))

    def frame_bytes(self, _core, width=912, height=684) -> bytes:
        return self.core.out_of_sight_frame(self.handle, 1 if self.black_background else 0,
                                            width, height)

    def describe(self, _frame) -> str:
        names = ("ready", "cueing", "tracking", "revealing", "done")
        state = self.state
        phase = state[self.INFO_PHASE]
        name = names[phase] if 0 <= phase < len(names) else "unknown"
        return (f"Out of Sight {name} · round {state[self.INFO_ROUND]}/"
                f"{state[self.INFO_TOTAL_ROUNDS]} · held {state[self.INFO_HELD]} · "
                f"hits {state[self.INFO_HITS]} · wrong {state[self.INFO_WRONG]}")

    def action(self, action: int) -> None:
        self.core.out_of_sight_action(self.handle, action, 0, 0)

    def tick(self, now_ms: int) -> None:
        self.core.out_of_sight_advance(self.handle, now_ms)

    def key(self, symbol, key) -> None:
        phase = self.state[self.INFO_PHASE]
        if symbol in (key.SPACE, key.RETURN) and phase in (0, 4):
            self.action(self.ACTION_START)
        elif phase == 2 and symbol == key.J:
            self.action(self.ACTION_MINE)
        elif phase == 2 and symbol == key.F:
            self.action(self.ACTION_NOT_MINE)

    def close(self) -> None:
        if self.handle > 0:
            self.core.out_of_sight_destroy(self.handle)
            self.handle = 0


class BuzzWireSession:
    """Native Python adapter for source-backed Buzz Wire."""
    ACTION_START, ACTION_PRESS, ACTION_RELEASE = 0, 1, 2
    INFO_PHASE, INFO_TRIAL, INFO_TOTAL_TRIALS = 0, 3, 4
    INFO_BUZZES, INFO_TOUCHES_ALLOWED, INFO_ALONG = 7, 6, 8

    def __init__(self, core, args) -> None:
        self.core = core
        self.handle = core.buzz_wire_create(1, args.trials, 1, 1, 1, 1, args.seed)
        if self.handle <= 0:
            raise SystemExit("native Buzz Wire rejected its options")
        self.black_background = args.black_background

    @property
    def state(self):
        return tuple(self.core.buzz_wire_info(self.handle, field) for field in range(29))

    def frame_bytes(self, _core, width=912, height=684) -> bytes:
        return self.core.buzz_wire_frame(self.handle, 1 if self.black_background else 0,
                                         width, height)

    def describe(self, _frame) -> str:
        names = ("ready", "running", "feedback", "done")
        state = self.state
        phase = state[self.INFO_PHASE]
        name = names[phase] if 0 <= phase < len(names) else "unknown"
        return (f"Buzz Wire {name} · trial {state[self.INFO_TRIAL]}/"
                f"{state[self.INFO_TOTAL_TRIALS]} · along {state[self.INFO_ALONG]}% · "
                f"buzzes {state[self.INFO_BUZZES]}/{state[self.INFO_TOUCHES_ALLOWED]}")

    def action(self, action: int, value: int = 0, now_ms: int = 0) -> None:
        self.core.buzz_wire_action(self.handle, action, value, now_ms)

    def tick(self, now_ms: int) -> None:
        self.core.buzz_wire_advance(self.handle, now_ms)

    def key(self, symbol, key) -> None:
        phase = self.state[self.INFO_PHASE]
        if symbol in (key.SPACE, key.RETURN) and phase in (0, 2, 3):
            self.action(self.ACTION_START, now_ms=int(time.monotonic() * 1000))
            return
        if phase != 1:
            return
        ports = {key.UP: 0, key.DOWN: 1, key.LEFT: 2, key.RIGHT: 3,
                 key.W: 4, key.S: 5, key.I: 6, key.K: 7, key.J: 8, key.L: 9,
                 key.LSHIFT: 10, key.RSHIFT: 10}
        if symbol in ports:
            self.action(self.ACTION_PRESS, ports[symbol], int(time.monotonic() * 1000))

    def release(self, symbol, key) -> None:
        ports = {key.UP: 0, key.DOWN: 1, key.LEFT: 2, key.RIGHT: 3,
                 key.W: 4, key.S: 5, key.I: 6, key.K: 7, key.J: 8, key.L: 9,
                 key.LSHIFT: 10, key.RSHIFT: 10}
        if symbol in ports:
            self.action(self.ACTION_RELEASE, ports[symbol], int(time.monotonic() * 1000))

    def close(self) -> None:
        if self.handle > 0:
            self.core.buzz_wire_destroy(self.handle)
            self.handle = 0


class DonkeySession:
    """Native Python adapter for source-backed Donkey."""
    ACTION_START, ACTION_SWITCH = 0, 1
    INFO_PHASE, INFO_TRIAL, INFO_TOTAL_TRIALS = 0, 2, 3
    INFO_ROAD_ROWS, INFO_DONKEYS, INFO_CAR_AT = 4, 6, 7
    INFO_CAR_PASSED, INFO_HIT, INFO_VERDICT = 11, 12, 13

    def __init__(self, core, args) -> None:
        self.core = core
        self.handle = core.donkey_create(1, args.trials, 180, 400, 1, 0, args.seed)
        if self.handle <= 0:
            raise SystemExit("native Donkey rejected its options")
        self.black_background = args.black_background

    @property
    def state(self):
        return tuple(self.core.donkey_info(self.handle, field) for field in range(27))

    def frame_bytes(self, _core, width=912, height=684) -> bytes:
        return self.core.donkey_frame(self.handle, 1 if self.black_background else 0,
                                      width, height)

    def describe(self, _frame) -> str:
        state = self.state
        phase = state[self.INFO_PHASE]
        names = ("ready", "setting", "running", "scored", "done")
        name = names[phase] if 0 <= phase < len(names) else "unknown"
        return (f"Donkey {name} · trial {state[self.INFO_TRIAL]}/"
                f"{state[self.INFO_TOTAL_TRIALS]} · road {state[self.INFO_ROAD_ROWS]} rows · "
                f"passed {state[self.INFO_CAR_PASSED]} · hits {state[self.INFO_HIT]}")

    def action(self, action: int, now_ms: int = 0) -> None:
        self.core.donkey_action(self.handle, action, 0, now_ms)

    def tick(self, now_ms: int) -> None:
        self.core.donkey_advance(self.handle, now_ms)

    def key(self, symbol, key) -> None:
        phase = self.state[self.INFO_PHASE]
        now_ms = int(time.monotonic() * 1000)
        if symbol in (key.SPACE, key.RETURN) and phase in (0, 3, 4):
            self.action(self.ACTION_START, now_ms)
        elif phase == 2 and symbol in (key.LEFT, key.RIGHT, key.SPACE):
            self.action(self.ACTION_SWITCH, now_ms)

    def close(self) -> None:
        if self.handle > 0:
            self.core.donkey_destroy(self.handle)
            self.handle = 0


class TwoHandsSession:
    """Native Python adapter for source-backed Two Hands."""
    ACTION_START, ACTION_PORT = 0, 1
    INFO_PHASE, INFO_TRIAL, INFO_TOTAL_TRIALS = 0, 2, 3
    INFO_CAR_AT, INFO_CAR_HIT, INFO_POINTS = 7, 15, 20

    def __init__(self, core, args) -> None:
        self.core = core
        self.handle = core.two_hands_create(3, args.trials, 400, 1200, 1, 0, args.seed)
        if self.handle <= 0:
            raise SystemExit("native Two Hands rejected its options")
        self.black_background = args.black_background

    @property
    def state(self):
        return tuple(self.core.two_hands_info(self.handle, field) for field in range(36))

    def frame_bytes(self, _core, width=912, height=684) -> bytes:
        return self.core.two_hands_frame(self.handle, 1 if self.black_background else 0,
                                         width, height)

    def describe(self, _frame) -> str:
        state = self.state
        phase = state[self.INFO_PHASE]
        names = ("ready", "setting", "running", "scored", "done")
        name = names[phase] if 0 <= phase < len(names) else "unknown"
        return (f"Two Hands {name} · trial {state[self.INFO_TRIAL]}/"
                f"{state[self.INFO_TOTAL_TRIALS]} · road {state[4]} rows · "
                f"points {state[self.INFO_POINTS]} · hit {state[self.INFO_CAR_HIT]}")

    def action(self, action: int, value: int = 0, now_ms: int = 0) -> None:
        self.core.two_hands_action(self.handle, action, value, now_ms)

    def tick(self, now_ms: int) -> None:
        self.core.two_hands_advance(self.handle, now_ms)

    def key(self, symbol, key) -> None:
        phase = self.state[self.INFO_PHASE]
        now_ms = int(time.monotonic() * 1000)
        if symbol in (key.SPACE, key.RETURN) and phase in (0, 3, 4):
            self.action(self.ACTION_START, now_ms=now_ms)
            return
        if phase != 2:
            return
        ports = {key.LEFT: 1, key.RIGHT: 2, key.UP: 4, key.DOWN: 5,
                 key.W: 1, key.D: 2, key.S: 3, key.A: 1,
                 key.I: 6, key.L: 7, key.O: 8, key.K: 9, key.SPACE: 10}
        if symbol in ports:
            self.action(self.ACTION_PORT, ports[symbol], now_ms)

    def pointer(self, x: float, y: float, pressed: bool = False) -> None:
        self.core.two_hands_pointer(self.handle, int(x * 1000000),
                                    int(y * 1000000), 1 if pressed else 0,
                                    int(time.monotonic() * 1000))

    def close(self) -> None:
        if self.handle > 0:
            self.core.two_hands_destroy(self.handle)
            self.handle = 0


class OverrunSession:
    """Native Python adapter for source-backed Overrun typing."""
    ACTION_START, ACTION_WRITE, ACTION_ERASE = 0, 1, 2
    INFO_PHASE, INFO_TRIAL, INFO_TOTAL = 0, 2, 3
    INFO_CLEARED, INFO_TYPED, INFO_LIVES, INFO_VERDICT = 7, 8, 10, 15

    def __init__(self, core, args) -> None:
        self.core = core
        self.handle = core.overrun_create(1, args.trials if args.trials in (3, 5, 8, 12, 20, 30) else 3,
                                          1 if args.adaptive else 0, 0, 0, 0, args.seed)
        if self.handle <= 0:
            raise SystemExit("native Overrun rejected its options")
        self.black_background = args.black_background

    @property
    def state(self):
        return tuple(self.core.overrun_info(self.handle, field) for field in range(21))

    def frame_bytes(self, _core, width=912, height=684) -> bytes:
        return self.core.overrun_frame(self.handle, 1 if self.black_background else 0,
                                       width, height)

    def describe(self, _frame) -> str:
        state = self.state
        names = ("ready", "typing", "settled", "done")
        phase = state[self.INFO_PHASE]
        name = names[phase] if 0 <= phase < len(names) else "unknown"
        return (f"Overrun {name} · wave {state[self.INFO_TRIAL]}/{state[self.INFO_TOTAL]} · "
                f"cleared {state[self.INFO_CLEARED]} · lives {state[self.INFO_LIVES]}")

    def action(self, action: int, value: int = 0, now_ms: int = 0) -> None:
        self.core.overrun_action(self.handle, action, value, now_ms)

    def tick(self, now_ms: int) -> None:
        self.core.overrun_advance(self.handle, now_ms)

    def key(self, symbol, key) -> None:
        now_ms = int(time.monotonic() * 1000)
        phase = self.state[self.INFO_PHASE]
        if symbol in (key.SPACE, key.RETURN) and phase in (0, 3):
            self.action(self.ACTION_START, now_ms=now_ms)
            return
        if phase != 1:
            return
        if symbol == key.BACKSPACE:
            self.action(self.ACTION_ERASE, now_ms=now_ms)
            return
        letters = {
            key.A: 0, key.B: 1, key.C: 2, key.D: 3, key.E: 4, key.F: 5,
            key.G: 6, key.H: 7, key.I: 8, key.J: 9, key.K: 10, key.L: 11,
            key.M: 12, key.N: 13, key.O: 14, key.P: 15, key.Q: 16, key.R: 17,
            key.S: 18, key.T: 19, key.U: 20, key.V: 21, key.W: 22, key.X: 23,
            key.Y: 24, key.Z: 25,
        }
        if symbol in letters:
            self.action(self.ACTION_WRITE, letters[symbol], now_ms)

    def close(self) -> None:
        if self.handle > 0:
            self.core.overrun_destroy(self.handle)
            self.handle = 0


class NCupMonteSession:
    """Native Python adapter for source-backed N-Cup Monte."""
    ACTION_START, ACTION_CHOOSE = 0, 1
    INFO_PHASE, INFO_CUPS = 0, 1

    def __init__(self, core, args) -> None:
        self.core = core
        self.handle = core.ncup_monte_create(3, 10, 1, 4, 160, 750, args.seed)
        if self.handle <= 0:
            raise SystemExit("native N-Cup Monte rejected its options")
        self.black_background = args.black_background

    @property
    def state(self):
        return tuple(self.core.ncup_monte_info(self.handle, field) for field in range(21))

    def frame_bytes(self, _core, width=912, height=684) -> bytes:
        return self.core.ncup_monte_frame(self.handle, 1 if self.black_background else 0,
                                          width, height)

    def describe(self, _frame) -> str:
        names = ("ready", "reveal", "shuffle", "guess", "result")
        phase = self.state[self.INFO_PHASE]
        name = names[phase] if 0 <= phase < len(names) else "unknown"
        return f"N-Cup Monte {name} · cups {self.state[self.INFO_CUPS]}"

    def action(self, action: int, value: int = 0) -> None:
        self.core.ncup_monte_action(self.handle, action, value, 0)

    def tick(self, now_ms: int) -> None:
        self.core.ncup_monte_advance(self.handle, now_ms)

    def pointer(self, x: float, y: float, width: int, height: int) -> None:
        self.core.ncup_monte_pointer(self.handle, int(x * 1000000 / width),
                                     int(y * 1000000 / height), 0)

    def key(self, symbol, key) -> None:
        if symbol in (key.SPACE, key.RETURN) and self.state[self.INFO_PHASE] in (0, 4):
            self.action(self.ACTION_START)

    def close(self) -> None:
        if self.handle > 0:
            self.core.ncup_monte_destroy(self.handle)
            self.handle = 0


class TaskHubSession:
    """Native menu with explicit handoffs only for implemented controllers."""

    CATEGORIES = (
        ("Working memory", ("3D N-Back", "Monkey Ladder", "In the Dark", "Fog of War", "Removals", "Chain of Custody")),
        ("Long-term memory", ("Concentration", "Seen It Before?", "Trivia")),
        ("Attention", ("Reflex", "N-Cup Monte", "Moving Targets", "Lookout", "Pursuit", "Buzz Wire", "Out of Sight", "Donkey", "Two Hands", "Overrun", "Marble Maze")),
        ("Perception", ("Count", "Mr. Time")),
        ("Reasoning", ("Graph Mapping", "Matrix Reasoning", "Jigsaw Puzzle", "Sudoku", "Find the Winning Move", "Crossed Wires", "Crossword", "Scrabble", "Scramble", "Algebra", "Numberology", "Syllogisms", "Winning Move", "Verbal Reasoning")),
        ("Planning", ("Tower of Hanoi", "Traveling Salesman", "Sokoban", "Maze", "3D Maze", "3D Sokoban", "Freeform Tetris", "N-in-a-row")),
        ("Self-control", ("Cookie Thief",)),
    )

    def __init__(self, core, args) -> None:
        self.core = core
        self.black_background = args.black_background
        self.category = 0
        self.selected = 0
        self.child: NBack3DSession | MarbleMazeSession | YouAreHereSession | SokobanSession | MonkeyLadderSession | TetrisSession | CountSession | MrTimeSession | GraphMappingSession | InTheDarkSession | FogOfWarSession | RemovalsSession | CustodySession | ConcentrationSession | RecognitionSession | TriviaSession | ReflexSession | AlgebraSession | NumberologySession | SyllogismSession | JigsawSession | SudokuSession | GoSession | CrossedWiresSession | CrosswordSession | ScrabbleSession | NCupMonteSession | TrackingSession | LookoutSession | PursuitSession | OutOfSightSession | BuzzWireSession | DonkeySession | TwoHandsSession | OverrunSession | None = None
        self.args = args

    @property
    def state(self):
        return (self.category, self.selected,
                1 if self.child is not None else 0)

    def frame_bytes(self, _core, width=912, height=684) -> bytes:
        if self.child is not None:
            return self.child.frame_bytes(self.core, width, height)
        return self.core.taskhub_frame(self.category, self.selected,
                                        1 if self.black_background else 0,
                                        width, height)

    def describe(self, _frame) -> str:
        if self.child is not None:
            return self.child.describe(_frame)
        name, tasks = self.CATEGORIES[self.category]
        return f"task menu · {name} · {tasks[self.selected]}"

    def key(self, symbol, key) -> None:
        if self.child is not None:
            if symbol == key.ESCAPE and not (isinstance(self.child, (CrosswordSession, ScrabbleSession, ScrambleSession, AlgebraSession, NumberologySession, SyllogismSession)) and self.child.options_draft is not None):
                self.child.close()
                self.child = None
            else:
                self.child.key(symbol, key)
                if isinstance(self.child, (ScrabbleSession, ScrambleSession, AlgebraSession, NumberologySession, SyllogismSession)) and self.child.options_from_hub and self.child.options_draft is None:
                    self.child.close()
                    self.child = None
            return
        if symbol == key.C and self.category == 4 and self.selected == 11:
            self.child = SyllogismSession(self.core, self.args)
            self.child.options_from_hub = True
            self.child.key(key.O, key)
            return
        if symbol == key.C and self.category == 4 and self.selected == 10:
            self.child = NumberologySession(self.core, self.args)
            self.child.options_from_hub = True
            self.child.key(key.O, key)
            return
        if symbol == key.C and self.category == 4 and self.selected == 9:
            self.child = AlgebraSession(self.core, self.args)
            self.child.options_from_hub = True
            self.child.key(key.O, key)
            return
        if symbol == key.C and self.category == 4 and self.selected == 7:
            self.child = ScrabbleSession(self.core, self.args)
            self.child.options_from_hub = True
            self.child.key(key.C, key)
            return
        if symbol == key.C and self.category == 4 and self.selected == 8:
            self.child = ScrambleSession(self.core, self.args)
            self.child.options_from_hub = True
            self.child.key(key.O, key)
            return
        if symbol == key.LEFT:
            self.category = (self.category - 1) % len(self.CATEGORIES)
            self.selected = 0
        elif symbol == key.RIGHT:
            self.category = (self.category + 1) % len(self.CATEGORIES)
            self.selected = 0
        elif symbol == key.UP:
            count = len(self.CATEGORIES[self.category][1])
            self.selected = (self.selected - 1) % count
        elif symbol == key.DOWN:
            count = len(self.CATEGORIES[self.category][1])
            self.selected = (self.selected + 1) % count
        elif symbol in (key.SPACE, key.RETURN):
            if self.category == 5 and self.selected == 2:
                self.child = SokobanSession(self.core, self.args)
            elif self.category == 5 and self.selected == 4:
                self.child = YouAreHereSession(self.core, self.args)
            elif self.category == 0 and self.selected == 1:
                self.child = MonkeyLadderSession(self.core, self.args)
            elif self.category == 5 and self.selected == 6:
                self.child = TetrisSession(self.core, self.args)
            elif self.category == 3 and self.selected == 0:
                self.child = CountSession(self.core, self.args)
            elif self.category == 3 and self.selected == 1:
                self.child = MrTimeSession(self.core, self.args)
            elif self.category == 4 and self.selected == 0:
                self.child = GraphMappingSession(self.core, self.args)
            elif self.category == 4 and self.selected == 1:
                self.child = MatrixReasoningSession(self.core, self.args)
            elif self.category == 0 and self.selected == 0:
                self.child = NBack3DSession(self.core, self.args)
            elif self.category == 0 and self.selected == 2:
                self.child = InTheDarkSession(self.core, self.args)
            elif self.category == 0 and self.selected == 3:
                self.child = FogOfWarSession(self.core, self.args)
            elif self.category == 0 and self.selected == 4:
                self.child = RemovalsSession(self.core, self.args)
            elif self.category == 0 and self.selected == 5:
                self.child = CustodySession(self.core, self.args)
            elif self.category == 1 and self.selected == 0:
                self.child = ConcentrationSession(self.core, self.args)
            elif self.category == 1 and self.selected == 1:
                self.child = RecognitionSession(self.core, self.args)
            elif self.category == 1 and self.selected == 2:
                self.child = TriviaSession(self.core, self.args)
            elif self.category == 2 and self.selected == 0:
                self.child = ReflexSession(self.core, self.args)
            elif self.category == 4 and self.selected == 9:
                self.child = AlgebraSession(self.core, self.args)
            elif self.category == 4 and self.selected == 10:
                self.child = NumberologySession(self.core, self.args)
            elif self.category == 4 and self.selected == 11:
                self.child = SyllogismSession(self.core, self.args)
            elif self.category == 4 and self.selected == 2:
                self.child = JigsawSession(self.core, self.args)
            elif self.category == 4 and self.selected == 3:
                self.child = SudokuSession(self.core, self.args)
            elif self.category == 4 and self.selected == 4:
                self.child = GoSession(self.core, self.args)
            elif self.category == 4 and self.selected == 5:
                self.child = CrossedWiresSession(self.core, self.args)
            elif self.category == 4 and self.selected == 6:
                self.child = CrosswordSession(self.core, self.args)
            elif self.category == 4 and self.selected == 7:
                self.child = ScrabbleSession(self.core, self.args)
            elif self.category == 4 and self.selected == 8:
                self.child = ScrambleSession(self.core, self.args)
            elif self.category == 2 and self.selected == 1:
                self.child = NCupMonteSession(self.core, self.args)
            elif self.category == 2 and self.selected == 2:
                self.child = TrackingSession(self.core, self.args)
            elif self.category == 2 and self.selected == 3:
                self.child = LookoutSession(self.core, self.args)
            elif self.category == 2 and self.selected == 4:
                self.child = PursuitSession(self.core, self.args)
            elif self.category == 2 and self.selected == 6:
                self.child = OutOfSightSession(self.core, self.args)
            elif self.category == 2 and self.selected == 7:
                self.child = DonkeySession(self.core, self.args)
            elif self.category == 2 and self.selected == 8:
                self.child = TwoHandsSession(self.core, self.args)
            elif self.category == 2 and self.selected == 9:
                self.child = OverrunSession(self.core, self.args)
            elif self.category == 2 and self.selected == 5:
                self.child = BuzzWireSession(self.core, self.args)
            elif self.category == 2 and self.selected == 10:
                self.child = MarbleMazeSession(self.core, self.args)

    def close(self) -> None:
        if self.child is not None:
            self.child.close()
            self.child = None


SCREENS = {
    "title": ("title_frame", lambda args: TitleSession(args.black_background)),
    "taskhub": ("taskhub_frame", None),
    "nback3d": ("nback3d_create", None),
    "marble": ("marble_create", None),
    "you-are-here": ("you_are_here_create", None),
    "sokoban": ("sokoban_create", None),
    "monkey-ladder": ("monkey_ladder_create", None),
    "tetris": ("tetris_create", None),
    "count": ("count_create", None),
    "mr-time": ("mr_time_create", None),
    "graph-mapping": ("graph_mapping_create", None),
    "matrix-reasoning": ("matrix_reasoning_create", None),
    "in-the-dark": ("in_the_dark_create", None),
    "fog-of-war": ("fog_create", None),
    "removals": ("removals_create", None),
    "chain-of-custody": ("custody_create", None),
    "concentration": ("concentration_create", None),
    "recognition": ("recognition_create", None),
    "trivia": ("trivia_create", None),
    "reflex": ("reflex_create", None),
    "algebra": ("algebra_create", None),
    "numberology": ("numberology_create", None),
    "syllogism": ("syllogism_create", None),
    "jigsaw": ("jigsaw_create", None),
    "sudoku": ("sudoku_create", None),
    "go": ("go_create", None),
    "crossed-wires": ("crossed_wires_create", None),
    "crossword": ("crossword_create", None),
    "scrabble": ("scrabble_create", None),
    "scramble": ("scramble_create", None),
    "ncup-monte": ("ncup_monte_create", None),
    "moving-targets": ("tracking_create", None),
    "lookout": ("lookout_create", None),
    "pursuit": ("pursuit_create", None),
    "out-of-sight": ("out_of_sight_create", None),
    "buzz-wire": ("buzz_wire_create", None),
    "donkey": ("donkey_create", None),
    "two-hands": ("two_hands_create", None),
    "overrun": ("overrun_create", None),
}


def dump(core, session: TitleSession, trials: int) -> int:
    """Print each title frame in the canonical text form used by the tests."""
    from display_decode import canonical
    for _ in range(trials):
        blob = session.frame_bytes(core)
        print(f"# state={session.state} bytes={len(blob)}")
        for line in canonical(decode(blob)):
            print("  " + line)
        if isinstance(session, (NBack3DSession, MarbleMazeSession, YouAreHereSession, SokobanSession, MonkeyLadderSession, CountSession, MrTimeSession, GraphMappingSession, MatrixReasoningSession, InTheDarkSession, FogOfWarSession, RemovalsSession, CustodySession, ConcentrationSession, RecognitionSession, TriviaSession, ReflexSession, AlgebraSession, NumberologySession, SyllogismSession, JigsawSession, SudokuSession, GoSession, CrossedWiresSession, CrosswordSession, ScrabbleSession, NCupMonteSession, TrackingSession, LookoutSession, PursuitSession, OutOfSightSession, BuzzWireSession, DonkeySession, TwoHandsSession, OverrunSession)):
            session.action(session.ACTION_START)
        elif isinstance(session, TetrisSession):
            session.action(session.ACTION_SPACE)
        elif isinstance(session, TitleSession):
            session.advance()
    return 0


def run_window(core, session: TitleSession, width: int, height: int,
               screenshot: str | None, screen: str = "title") -> int:
    import pyglet
    from pyglet.window import key

    window = pyglet.window.Window(width=width, height=height, resizable=True,
                                  caption=f"Neural Workshop - {screen} - pyglet shell")
    # Display-list scenes draw transparent text/shapes over the shell clear
    # color. Keep that backing in the same theme as the source task; a fixed
    # dark clear made every light-theme task render black text on charcoal.
    pyglet.gl.glClearColor(*window_background_rgba(session))

    renderer = Renderer(Viewport.from_window(window),
                        font_name=SOURCE_FONT_FAMILIES)
    marble_renderer = None

    def active_marble_session():
        if isinstance(session, MarbleMazeSession):
            return session
        if isinstance(session, TaskHubSession) and isinstance(
                session.child, MarbleMazeSession):
            return session.child
        return None
    hud = pyglet.text.Label("", x=8, y=8, font_size=11,
                            color=(154, 164, 178, 255))

    def draw_frame():
        nonlocal marble_renderer
        marble_session = active_marble_session()
        if marble_session is not None:
            if marble_renderer is None:
                from marble_native_renderer import MarbleNativeRenderer
                marble_renderer = MarbleNativeRenderer()
            if not marble_session.native_physics:
                marble_session.enable_native_physics()
        if isinstance(session, (NBack3DSession, MarbleMazeSession, YouAreHereSession, SokobanSession, MonkeyLadderSession, InTheDarkSession, FogOfWarSession, RemovalsSession, CustodySession, RecognitionSession, TriviaSession, ReflexSession, AlgebraSession, NumberologySession, SyllogismSession, JigsawSession, SudokuSession, GoSession, CrossedWiresSession, CrosswordSession, ScrabbleSession, NCupMonteSession, TrackingSession, LookoutSession, PursuitSession, OutOfSightSession, BuzzWireSession,
                                TetrisSession, CountSession, MrTimeSession, GraphMappingSession,
                                MatrixReasoningSession, DonkeySession, TwoHandsSession, OverrunSession, TaskHubSession)):
            blob = session.frame_bytes(core, window.width, window.height)
        else:
            blob = session.frame_bytes(core)
        frame = renderer.render_bytes(blob)
        viewport = renderer.viewport
        hud.font_size = max(9.0, 11.0 * viewport.pixel_ratio)
        hud.x = hud.y = 8.0 * viewport.pixel_ratio
        hud.text = (f"{session.describe(frame)} - {len(frame.ops)} ops - "
                    f"{len(blob)} bytes - scale {viewport.scale:.3f} "
                    f"- dpr {viewport.pixel_ratio:g}")
        return frame

    draw_frame()

    last_marble_draw_at = None

    @window.event
    def on_draw():
        nonlocal last_marble_draw_at
        marble_session = active_marble_session()
        if marble_session is not None:
            now = time.perf_counter()
            dt = 0.0 if last_marble_draw_at is None else max(
                0.0, now - last_marble_draw_at)
            last_marble_draw_at = now
            marble_session.tick(now * 1000.0, physics_dt=dt)
            draw_frame()
        window.clear()
        renderer.draw()
        if (marble_renderer is not None and marble_session is not None and
                marble_session.physics is not None):
            if marble_session.board is not None:
                marble_renderer.set_board(marble_session.board,
                                          marble_session.grain_seed)
            marble_renderer.draw(marble_session.physics, window.width,
                                 window.height, marble_session.black_background)
        if os.environ.get("NW_NATIVE_DEBUG_HUD") == "1":
            hud.draw()

    @window.event
    def on_resize(_new_width, _new_height):
        renderer.viewport = Viewport.from_window(window)
        draw_frame()

    @window.event
    def on_key_press(symbol, _modifiers):
        target = session.child if isinstance(session, TaskHubSession) else session
        if (isinstance(target, NumberologySession) and target.state[0] == 1
                and symbol == key.V and _modifiers & key.MOD_ACCEL):
            target.paste()
            draw_frame()
            return pyglet.event.EVENT_HANDLED
        if (isinstance(target, AlgebraSession) and target.options_draft is None and target.state[0] == 1
                and symbol == key.V and _modifiers & key.MOD_ACCEL):
            target.paste()
            draw_frame()
            return pyglet.event.EVENT_HANDLED
        if (isinstance(target, ScrambleSession) and target.options_draft is None and target.state[0] == 1
                and symbol == key.V and _modifiers & key.MOD_ACCEL):
            target.paste()
            draw_frame()
            return pyglet.event.EVENT_HANDLED
        if symbol == key.ESCAPE and isinstance(session, (ScrambleSession, AlgebraSession, NumberologySession, SyllogismSession)) and session.options_draft is None:
            window.close()
            return
        if isinstance(session, (NBack3DSession, MarbleMazeSession, YouAreHereSession, SokobanSession, MonkeyLadderSession, InTheDarkSession, FogOfWarSession, RemovalsSession, CustodySession, ConcentrationSession, RecognitionSession, TriviaSession, ReflexSession, AlgebraSession, NumberologySession, SyllogismSession, JigsawSession, SudokuSession, GoSession, CrossedWiresSession, CrosswordSession, ScrabbleSession, ScrambleSession, NCupMonteSession, TrackingSession, LookoutSession, PursuitSession, OutOfSightSession,
                                TetrisSession, DonkeySession, TwoHandsSession, OverrunSession, TaskHubSession)):
            session.key(symbol, key)
            draw_frame()
        elif symbol in (key.SPACE, key.RIGHT, key.RETURN, key.DOWN):
            session.advance()
            draw_frame()
        elif symbol in (key.LEFT, key.UP):
            session.back()
            draw_frame()
        elif symbol == key.ESCAPE:
            window.close()

    @window.event
    def on_text(text):
        target = session.child if isinstance(session, TaskHubSession) else session
        if isinstance(target, (ScrambleSession, AlgebraSession, NumberologySession)):
            if text not in ('\r', '\n', '\b', '\x7f'):
                target.text(text)
            draw_frame()

    @window.event
    def on_key_release(symbol, _modifiers):
        marble_session = active_marble_session()
        if marble_session is not None:
            marble_session.release(symbol, key)
            draw_frame()
        elif isinstance(session, BuzzWireSession):
            session.release(symbol, key)
            draw_frame()

    @window.event
    def on_deactivate():
        marble_session = active_marble_session()
        if marble_session is not None:
            marble_session.release_all()
            draw_frame()

    @window.event
    def on_mouse_press(x, y, _button, _modifiers):
        target = session.child if isinstance(session, TaskHubSession) else session
        if isinstance(target, (CrosswordSession, ScrabbleSession, ScrambleSession, AlgebraSession, NumberologySession, SyllogismSession)):
            target.pointer(x, y, window.width, window.height, 2 if _button == 4 else 0)
            if isinstance(session, TaskHubSession) and isinstance(target, SyllogismSession) and target.options_from_hub and target.options_draft is None:
                target.close()
                session.child = None
            draw_frame()
            return
        if isinstance(session, ReflexSession) or isinstance(session, JigsawSession) or isinstance(session, GoSession) or isinstance(session, NCupMonteSession) or isinstance(session, TrackingSession) or isinstance(session, PursuitSession):
            session.pointer(x, y, window.width, window.height)
            draw_frame()
        elif isinstance(session, TwoHandsSession):
            session.pointer(x / window.width, y / window.height)
            draw_frame()

    @window.event
    def on_mouse_motion(x, y, _dx, _dy):
        target = session.child if isinstance(session, TaskHubSession) else session
        if isinstance(target, ScrabbleSession):
            target.pointer(x, y, window.width, window.height, motion=True)
            draw_frame()

    @window.event
    def on_close():
        if marble_renderer is not None:
            marble_renderer.close()
        if hasattr(session, "close"):
            session.close()

    if isinstance(session, MonkeyLadderSession):
        def tick_monkey(_dt):
            session.tick(int(time.monotonic() * 1000))
            draw_frame()
        pyglet.clock.schedule_interval(tick_monkey, 1 / 30.0)

    if isinstance(session, NCupMonteSession):
        def tick_ncup(_dt):
            session.tick(int(time.monotonic() * 1000))
            draw_frame()
        pyglet.clock.schedule_interval(tick_ncup, 1 / 30.0)

    if isinstance(session, TrackingSession):
        def tick_tracking(_dt):
            session.tick(int(time.monotonic() * 1000))
            draw_frame()
        pyglet.clock.schedule_interval(tick_tracking, 1 / 30.0)

    if isinstance(session, LookoutSession):
        def tick_lookout(_dt):
            session.tick(int(time.monotonic() * 1000))
            draw_frame()
        pyglet.clock.schedule_interval(tick_lookout, 1 / 30.0)

    if isinstance(session, PursuitSession):
        def tick_pursuit(_dt):
            session.tick(int(time.monotonic() * 1000))
            draw_frame()
        pyglet.clock.schedule_interval(tick_pursuit, 1 / 30.0)

    if isinstance(session, OutOfSightSession):
        def tick_out_of_sight(_dt):
            session.tick(int(time.monotonic() * 1000))
            draw_frame()
        pyglet.clock.schedule_interval(tick_out_of_sight, 1 / 30.0)

    if isinstance(session, BuzzWireSession):
        def tick_buzz_wire(_dt):
            session.tick(int(time.monotonic() * 1000))
            draw_frame()
        pyglet.clock.schedule_interval(tick_buzz_wire, 1 / 30.0)

    if isinstance(session, (DonkeySession, TwoHandsSession)):
        def tick_lane_game(_dt):
            session.tick(int(time.monotonic() * 1000))
            draw_frame()
        pyglet.clock.schedule_interval(tick_lane_game, 1 / 30.0)

    if isinstance(session, OverrunSession):
        def tick_overrun(_dt):
            session.tick(int(time.monotonic() * 1000))
            draw_frame()
        pyglet.clock.schedule_interval(tick_overrun, 1 / 30.0)

    if isinstance(session, NBack3DSession):
        def tick_nback(_dt):
            session.tick(int(time.monotonic() * 1000))
            draw_frame()
        pyglet.clock.schedule_interval(tick_nback, 1 / 30.0)

    if isinstance(session, CountSession):
        def tick_count(_dt):
            session.tick(int(time.monotonic() * 1000))
            draw_frame()
        pyglet.clock.schedule_interval(tick_count, 1 / 30.0)

    if isinstance(session, MrTimeSession):
        def tick_mr_time(_dt):
            session.tick(int(time.monotonic() * 1000))
            draw_frame()
        pyglet.clock.schedule_interval(tick_mr_time, 1 / 30.0)

    if isinstance(session, GraphMappingSession):
        def tick_graph_mapping(_dt):
            session.tick(int(time.monotonic() * 1000))
            draw_frame()
        pyglet.clock.schedule_interval(tick_graph_mapping, 1 / 30.0)

    if isinstance(session, MatrixReasoningSession):
        def tick_matrix_reasoning(_dt):
            session.tick(int(time.monotonic() * 1000))
            draw_frame()
        pyglet.clock.schedule_interval(tick_matrix_reasoning, 1 / 30.0)

    if isinstance(session, InTheDarkSession):
        def tick_in_the_dark(_dt):
            session.tick(int(time.monotonic() * 1000))
            draw_frame()
        pyglet.clock.schedule_interval(tick_in_the_dark, 1 / 30.0)

    if isinstance(session, RemovalsSession):
        def tick_removals(_dt):
            session.tick(int(time.monotonic() * 1000))
            draw_frame()
        pyglet.clock.schedule_interval(tick_removals, 1 / 30.0)

    if isinstance(session, CustodySession):
        def tick_custody(_dt):
            session.tick(int(time.monotonic() * 1000))
            draw_frame()
        pyglet.clock.schedule_interval(tick_custody, 1 / 30.0)

    if isinstance(session, ConcentrationSession):
        def tick_concentration(_dt):
            session.tick(int(time.monotonic() * 1000))
            draw_frame()
        pyglet.clock.schedule_interval(tick_concentration, 1 / 30.0)

    if isinstance(session, RecognitionSession):
        def tick_recognition(_dt):
            session.tick(int(time.monotonic() * 1000))
            draw_frame()
        pyglet.clock.schedule_interval(tick_recognition, 1 / 30.0)

    if isinstance(session, ReflexSession):
        def tick_reflex(_dt):
            session.tick(int(time.monotonic() * 1000))
            draw_frame()
        pyglet.clock.schedule_interval(tick_reflex, 1 / 30.0)

    if screenshot:
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


def window_background_rgba(session) -> tuple[float, float, float, float]:
    """Return the source-matching backing color for a native session frame."""
    if getattr(session, "black_background", False):
        return (0.0, 0.0, 0.0, 1.0)
    return (1.0, 1.0, 1.0, 1.0)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--width", type=int, default=912)
    parser.add_argument("--height", type=int, default=684)
    parser.add_argument("--screen", choices=sorted(SCREENS), default="title",
                        help="native screen to open")
    parser.add_argument("--black-background", action="store_true",
                        help="the dark title theme")
    parser.add_argument("--trial", type=int, default=1,
                        help="title banner number, one-based")
    parser.add_argument("--seed", type=int, default=17,
                        help="seed for the native 3D Maze controller")
    parser.add_argument("--adaptive", action="store_true",
                        help="enable source adaptive 3D Maze rung changes")
    parser.add_argument("--show-marks", action="store_true",
                        help="show source 3D Maze map marks")
    parser.add_argument("--show-traps", action="store_true",
                        help="show source Sokoban trap cells")
    parser.add_argument("--screenshot", metavar="PNG",
                        help="render one frame to PNG and exit")
    parser.add_argument("--dump", action="store_true",
                        help="print frames as canonical text; opens no window")
    parser.add_argument("--trials", type=int, default=1,
                        help="3D Maze trial count, or title dump count")
    parser.add_argument("--jigsaw-side", type=int, choices=(2, 3, 4, 5, 6, 7, 8, 10),
                        default=3, help="Jigsaw starting grid side (source default: 3)")
    parser.add_argument("--jigsaw-puzzles", type=int, choices=(1, 2, 3, 5, 8, 12, 20),
                        default=3, help="Jigsaw puzzles per run (source default: 3)")
    parser.add_argument("--jigsaw-no-adaptive", action="store_false",
                        dest="jigsaw_adaptive", default=True,
                        help="keep the Jigsaw grid side fixed")
    parser.add_argument("--jigsaw-no-preview", action="store_false",
                        dest="jigsaw_preview", default=True,
                        help="hide the finished-picture preview in Jigsaw")
    parser.add_argument("--jigsaw-mark-placed", action="store_true",
                        help="outline correctly placed Jigsaw tiles")
    parser.add_argument("--sudoku-level", type=int, choices=tuple(range(1, 13)),
                        default=3, help="Sudoku starting level (source default: 3)")
    parser.add_argument("--sudoku-puzzles", type=int, choices=(1, 2, 3, 5, 8, 10),
                        default=3, help="Sudoku puzzles per run (source default: 3)")
    parser.add_argument("--sudoku-no-clashes", action="store_true",
                        help="do not mark digits that clash with peers")
    parser.add_argument("--sudoku-no-adaptive", action="store_true",
                        help="keep the Sudoku level fixed during the run")
    parser.add_argument("--go-level", type=int, choices=tuple(range(1, 11)),
                        default=1, help="Go starting level (source default: 1)")
    parser.add_argument("--go-trials", type=int, choices=(1, 3, 5, 8, 10, 15, 20, 30, 50),
                        default=10, help="Go positions per run (source default: 10)")
    parser.add_argument("--crossed-wires-level", type=int, choices=tuple(range(1, 13)),
                        default=3, help="Crossed Wires starting rung (source default: 3)")
    parser.add_argument("--crossed-wires-rounds", type=int, choices=(1, 2, 3, 5, 8, 10, 15, 20),
                        default=5, help="Crossed Wires rounds per run (source default: 5)")
    parser.add_argument("--crossed-wires-no-adaptive", action="store_true",
                        help="keep the Crossed Wires rung fixed during the run")
    parser.add_argument("--crossed-wires-no-grid", action="store_true",
                        help="hide the Crossed Wires background grid")
    parser.add_argument("--crossword-level", type=int, choices=range(1, 11))
    parser.add_argument("--crossword-trials", type=int, choices=CROSSWORD_TRIALS)
    parser.add_argument("--crossword-no-mistakes", action="store_true", default=None)
    parser.add_argument("--crossword-no-adaptive", action="store_true", default=None)
    parser.add_argument("--crossword-lexicon", metavar="PATH", help="clued Crossword lexicon.tsv")
    parser.add_argument("--scrabble-level", type=int, choices=range(1, 11))
    parser.add_argument("--syllogism-level", type=int, choices=range(1, 13))
    parser.add_argument("--syllogism-trials", type=int, choices=SYLLOGISM_TRIALS)
    parser.add_argument("--syllogism-no-working", action="store_true", default=None)
    parser.add_argument("--syllogism-no-adaptive", action="store_true", default=None)
    parser.add_argument("--syllogism-invented-words", action="store_true", default=None)
    parser.add_argument("--numberology-level", type=parse_numberology_level)
    parser.add_argument("--numberology-trials", type=int, choices=NUMBEROLOGY_TRIALS)
    parser.add_argument("--numberology-no-adaptive", action="store_true", default=None)
    parser.add_argument("--algebra-level", type=int, choices=range(1, 13))
    parser.add_argument("--algebra-trials", type=int, choices=ALGEBRA_TRIALS)
    parser.add_argument("--algebra-no-working", action="store_true", default=None)
    parser.add_argument("--algebra-no-adaptive", action="store_true", default=None)
    parser.add_argument("--scramble-level", type=int, choices=range(1, 13))
    parser.add_argument("--scramble-trials", type=int, choices=SCRABBLE_TRIALS)
    parser.add_argument("--scramble-no-count", action="store_true", default=None)
    parser.add_argument("--scramble-no-adaptive", action="store_true", default=None)
    parser.add_argument("--scramble-index", metavar="PATH", help="ranked Scramble lexicon.tsv")
    parser.add_argument("--scramble-sentences", metavar="PATH", help="Scramble sentences.txt")
    parser.add_argument("--scrabble-trials", type=int, choices=SCRABBLE_TRIALS)
    parser.add_argument("--scrabble-no-premiums", action="store_true", default=None)
    parser.add_argument("--scrabble-no-adaptive", action="store_true", default=None)
    parser.add_argument("--scrabble-lexicon", metavar="PATH", help="Scrabble lexicon.tsv")
    parser.add_argument("--marble-start-rung", type=int, default=1,
                        help="starting Marble Maze rung (1..16)")
    args = parser.parse_args(argv)
    saved_level, saved_trials, saved_count, saved_adaptive = read_scramble_settings()
    if args.scramble_level is None: args.scramble_level = saved_level
    if args.scramble_trials is None: args.scramble_trials = saved_trials
    if args.scramble_no_count is None: args.scramble_no_count = not saved_count
    if args.scramble_no_adaptive is None: args.scramble_no_adaptive = not saved_adaptive
    saved_level, saved_trials, saved_premiums, saved_adaptive = read_scrabble_settings()
    if args.scrabble_level is None: args.scrabble_level = saved_level
    if args.scrabble_trials is None: args.scrabble_trials = saved_trials
    if args.scrabble_no_premiums is None: args.scrabble_no_premiums = not saved_premiums
    if args.scrabble_no_adaptive is None: args.scrabble_no_adaptive = not saved_adaptive
    saved_level, saved_trials, saved_mistakes, saved_adaptive = read_crossword_settings()
    if args.crossword_level is None: args.crossword_level = saved_level
    if args.crossword_trials is None: args.crossword_trials = saved_trials
    if args.crossword_no_mistakes is None: args.crossword_no_mistakes = not saved_mistakes
    if args.crossword_no_adaptive is None: args.crossword_no_adaptive = not saved_adaptive

    entry, build_session = SCREENS[args.screen]
    core = load_core(entry)
    if args.screen == "taskhub":
        session = TaskHubSession(core, args)
    elif args.screen == "you-are-here":
        session = YouAreHereSession(core, args)
    elif args.screen == "sokoban":
        session = SokobanSession(core, args)
    elif args.screen == "monkey-ladder":
        session = MonkeyLadderSession(core, args)
    elif args.screen == "tetris":
        session = TetrisSession(core, args)
    elif args.screen == "nback3d":
        session = NBack3DSession(core, args)
    elif args.screen == "marble":
        session = MarbleMazeSession(core, args)
    elif args.screen == "lookout":
        session = LookoutSession(core, args)
    elif args.screen == "pursuit":
        session = PursuitSession(core, args)
    elif args.screen == "out-of-sight":
        session = OutOfSightSession(core, args)
    elif args.screen == "buzz-wire":
        session = BuzzWireSession(core, args)
    elif args.screen == "donkey":
        session = DonkeySession(core, args)
    elif args.screen == "two-hands":
        session = TwoHandsSession(core, args)
    elif args.screen == "overrun":
        session = OverrunSession(core, args)
    elif args.screen == "count":
        session = CountSession(core, args)
    elif args.screen == "mr-time":
        session = MrTimeSession(core, args)
    elif args.screen == "graph-mapping":
        session = GraphMappingSession(core, args)
    elif args.screen == "matrix-reasoning":
        session = MatrixReasoningSession(core, args)
    elif args.screen == "in-the-dark":
        session = InTheDarkSession(core, args)
    elif args.screen == "fog-of-war":
        session = FogOfWarSession(core, args)
    elif args.screen == "removals":
        session = RemovalsSession(core, args)
    elif args.screen == "chain-of-custody":
        session = CustodySession(core, args)
    elif args.screen == "concentration":
        session = ConcentrationSession(core, args)
    elif args.screen == "recognition":
        session = RecognitionSession(core, args)
    elif args.screen == "trivia":
        session = TriviaSession(core, args)
    elif args.screen == "reflex":
        session = ReflexSession(core, args)
    elif args.screen == "algebra":
        session = AlgebraSession(core, args)
    elif args.screen == "numberology":
        session = NumberologySession(core, args)
    elif args.screen == "syllogism":
        session = SyllogismSession(core, args)
    elif args.screen == "jigsaw":
        session = JigsawSession(core, args)
    elif args.screen == "sudoku":
        session = SudokuSession(core, args)
    elif args.screen == "go":
        session = GoSession(core, args)
    elif args.screen == "crossed-wires":
        session = CrossedWiresSession(core, args)
    elif args.screen == "crossword":
        session = CrosswordSession(core, args)
    elif args.screen == "scrabble":
        session = ScrabbleSession(core, args)
    elif args.screen == "scramble":
        session = ScrambleSession(core, args)
    elif args.screen == "ncup-monte":
        session = NCupMonteSession(core, args)
    elif args.screen == "moving-targets":
        session = TrackingSession(core, args)
    else:
        session = build_session(args)
        session.seek(args.trial)

    if args.dump:
        return dump(core, session, args.trials)
    return run_window(core, session, args.width, args.height, args.screenshot,
                      args.screen)


if __name__ == "__main__":
    sys.exit(main())
