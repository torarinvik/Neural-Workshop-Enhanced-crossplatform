"""Capture one frozen, seeded source Marble Maze frame and state manifest.

The source checkout is read-only input. Example:
  python test/marble_source_capture.py --source-root /path/to/neural-workshop-enhanced \
    --png output/playwright/marble-source.png \
    --metadata output/playwright/marble-source.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import random
import struct
import sys
from pathlib import Path

ASSET_NAMES = (
    "marble_colour.png", "marble_rough.png", "marble_normal.png",
)
MOVE_DIRECTIONS = frozenset(("N", "E", "S", "W"))


def capture_label_font(label) -> dict:
    """Resolve the same document font/DPI used by the source label layout.

    Record metrics, not font bytes; this does not modify the source UI or
    assume that the first requested fallback family was actually selected.
    """
    font = label.document.get_font(0, label.dpi)
    return {
        "text": label.text,
        "glyphAdvances": [float(glyph.advance)
                          for glyph in font.get_glyphs(label.text)[0]],
        "requestedFamilies": label.font_name,
        "resolvedFamily": font.name,
        "pointSize": float(font.size),
        "dpi": float(font.dpi),
        "pixelSize": float(font.size * font.dpi / 72.0),
        "weight": font.weight,
        "ascent": float(font.ascent),
        "descent": float(font.descent),
        "contentWidth": float(label.content_width),
        "contentHeight": float(label.content_height),
        "anchorX": label.anchor_x,
        "anchorY": label.anchor_y,
        "x": float(label.x),
        "y": float(label.y),
    }


def capture_elapsed_matches(elapsed: float, requested_ms: int) -> bool:
    """Allow only accumulated step roundoff, not a different capture time."""
    return math.isclose(elapsed, requested_ms / 1000.0,
                        rel_tol=0.0, abs_tol=1e-12)


def require_physical_terminal(task, outcome: str) -> None:
    expected = "won" if outcome == "done" else outcome
    if task.phase != expected or task.sim is None or not task.sim.settled:
        raise SystemExit(f"physical capture requires settled {expected}, got {task.phase!r}")


def validate_terminal_capture(rung: int, physical: bool, scripted: bool) -> None:
    """Only artificial terminal fixtures are restricted to the single-ball rung."""
    if not physical and (rung != 1 or scripted):
        raise SystemExit("forced terminal captures require rung 1 and no scripted motion")


def parse_capture_trace(trace, rung: int, seed: int) -> list[dict]:
    if not isinstance(trace, dict) or trace.get("rung") != rung or trace.get("runSeed") != seed:
        raise SystemExit("capture trace rung/runSeed differs from requested capture")
    trace_time_limit_seconds(trace)
    events = trace.get("events")
    if not isinstance(events, list) or not 1 <= len(events) <= 8000:
        raise SystemExit("capture trace requires 1..8000 input events")
    actions = []
    for event in events:
        if not isinstance(event, dict):
            raise SystemExit("capture trace event must be an object")
        if event.get("kind") == "level":
            actions.append({"kind": "level"})
        elif event.get("kind") == "frame":
            dt, held = event.get("dt"), event.get("held")
            if (isinstance(dt, bool) or not isinstance(dt, (int, float)) or
                    not math.isfinite(dt) or not 0 < dt <= 0.05 or
                    not isinstance(held, list) or
                    any(not isinstance(key, str) or key not in MOVE_DIRECTIONS for key in held) or
                    len(set(held)) != len(held)):
                raise SystemExit("capture trace has invalid frame dt/held keys")
            actions.append({"kind": "frame", "dt": dt, "held": held[:]})
        else:
            raise SystemExit("capture trace only supports frame and level inputs")
    return actions


def trace_time_limit_seconds(trace: dict) -> float:
    """Return the browser trace's configured trial limit, or zero if unset."""
    milliseconds = trace.get("timeLimitMs", 0)
    if (isinstance(milliseconds, bool) or not isinstance(milliseconds, int) or
            (milliseconds != 0 and not 15000 <= milliseconds <= 120000)):
        raise SystemExit("capture trace has invalid timeLimitMs")
    return milliseconds / 1000.0


def rebuild_float32_capture_board(task, simulation_type) -> None:
    """Rebuild a newly dealt fixture board without consuming its RNG identity."""
    task.tray = float32_abi_tray(task.tray)
    task.sim = simulation_type(task.tray)
    grain_seed = task.stage.grain_seed
    rng_state = task.rng.getstate()
    try:
        task._build_scene()
    finally:
        task.rng.setstate(rng_state)
        task.stage.grain_seed = grain_seed


def parse_move_stages(values: list[str]) -> list[dict[str, object]]:
    """Parse a bounded schedule such as E+W:12,E:20,none:1,W:40."""
    stages: list[dict[str, object]] = []
    total_frames = 0
    for value in values:
        directions_text, separator, frames_text = value.rpartition(":")
        if not separator or not directions_text:
            raise SystemExit(
                f"invalid --move-stage {value!r}; expected DIRECTIONS:FRAMES")
        if directions_text.lower() == "none":
            held: list[str] = []
        else:
            held = directions_text.split("+")
            if (not held or len(set(held)) != len(held) or
                    any(direction not in MOVE_DIRECTIONS for direction in held)):
                raise SystemExit(
                    f"invalid --move-stage directions {directions_text!r}; "
                    "use unique N/E/S/W directions joined by '+' or 'none' for neutral")
        try:
            frame_count = int(frames_text)
        except ValueError:
            frame_count = 0
        if not 1 <= frame_count <= 600:
            raise SystemExit(
                f"invalid --move-stage frame count {frames_text!r}; expected 1..600")
        total_frames += frame_count
        if total_frames > 600:
            raise SystemExit("combined --move-stage schedule may not exceed 600 frames")
        stages.append({"held": held, "frames": frame_count})
    return stages


def parse_resize_to(value: str) -> tuple[int, int]:
    width_text, separator, height_text = value.lower().partition("x")
    if not separator:
        raise argparse.ArgumentTypeError("resize target must look like 800x600")
    try:
        width, height = int(width_text), int(height_text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("resize dimensions must be integers") from exc
    if width < 640 or height < 480:
        raise argparse.ArgumentTypeError("resize target must be at least 640x480")
    return width, height


def float32_abi_value(value: float) -> float:
    """Round one source geometry value exactly as the WASM board ABI does."""
    return struct.unpack("=f", struct.pack("=f", float(value)))[0]


def float32_abi_tray(tray: object) -> object:
    """Return a source Tray whose transported geometry is exact Float32 data.

    This is an opt-in interaction-fixture mode, not a change to the original
    application or its ordinary Float64 reference captures. Keep topology and
    certification fields intact; only fields carried by the WASM board ABI are
    rounded.
    """
    return tray._replace(
        width=float32_abi_value(tray.width),
        depth=float32_abi_value(tray.depth),
        cell=float32_abi_value(tray.cell),
        thickness=float32_abi_value(tray.thickness),
        height=float32_abi_value(tray.height),
        walls=tuple(wall._replace(
            x0=float32_abi_value(wall.x0), y0=float32_abi_value(wall.y0),
            x1=float32_abi_value(wall.x1), y1=float32_abi_value(wall.y1))
            for wall in tray.walls),
        holes=tuple(hole._replace(
            x=float32_abi_value(hole.x), y=float32_abi_value(hole.y),
            radius=float32_abi_value(hole.radius)) for hole in tray.holes),
        starts=tuple(tuple(float32_abi_value(value) for value in start)
                     for start in tray.starts),
        home=tuple(float32_abi_value(value) for value in tray.home),
    )


def assets_digest(folder: Path) -> str:
    digest = hashlib.sha256()
    for name in ASSET_NAMES:
        path = folder / name
        if not path.is_file():
            raise SystemExit(f"source Marble Maze material asset is missing: {path}")
        digest.update(name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(bytes.fromhex(hashlib.sha256(path.read_bytes()).hexdigest()))
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--png", required=True, type=Path)
    parser.add_argument("--metadata", required=True, type=Path)
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument("--rung", type=int, default=1)
    parser.add_argument("--width", type=int, default=815)
    parser.add_argument("--height", type=int, default=611)
    parser.add_argument("--resize-to", type=parse_resize_to,
                        help="resize the live source window after replay and before capture")
    parser.add_argument("--roll", type=float, default=0.0,
                        help="static source Simulation roll, in radians")
    parser.add_argument("--pitch", type=float, default=0.0,
                        help="static source Simulation pitch, in radians")
    parser.add_argument("--move", choices=("N", "E", "S", "W"), action="append",
                        help="hold a source tilt key (repeat for simultaneous axes)")
    parser.add_argument("--move-frames", type=int, default=0,
                        help="number of 60 Hz source updates to hold --move")
    parser.add_argument("--move-stage", action="append", default=[], metavar="DIRECTIONS:FRAMES",
                        help="append an exact held-key stage, e.g. E+W:12, E:20, none:1, W:40")
    parser.add_argument("--release-frames", type=int, default=0,
                        help="number of 60 Hz source updates after releasing --move")
    parser.add_argument("--restart-after-move", action="store_true",
                        help="call the source UI's real restart() after the held/released replay")
    parser.add_argument("--post-restart-frames", type=int, default=0,
                        help="number of neutral 60 Hz source updates after --restart-after-move")
    parser.add_argument("--board-abi-f32", action="store_true",
                        help="round source board geometry through the browser WASM Float32 ABI before replay")
    parser.add_argument("--outcome", choices=("ready", "rolling", "won", "lost", "done", "timeout", "next-trial"),
                        default="rolling",
                        help="source UI phase to capture; next-trial advances a timed-out first tray through official feedback into tray 2")
    parser.add_argument("--trials", type=int, default=1,
                        help="configured run length (1..12); next-trial requires at least two")
    parser.add_argument("--require-physical-outcome", action="store_true",
                        help="terminal capture must be reached by replay, never force marble states")
    parser.add_argument("--input-trace", type=Path,
                        help="bounded frame/level input replay; recorded poses are ignored")
    parser.add_argument("--next-trial-elapsed-ms", type=int, default=0,
                        help="active time to simulate on tray 2 for a next-trial capture")
    parser.add_argument("--theme", choices=("light", "dark"), default="light",
                        help="original application's background/text theme")
    parser.add_argument("--timeout-seconds", type=float, default=15.0,
                        help="configured deterministic deadline for --outcome timeout")
    args = parser.parse_args()
    move_stages = parse_move_stages(args.move_stage)
    if move_stages and (args.move or args.move_frames or args.release_frames or
                        args.restart_after_move or args.post_restart_frames):
        raise SystemExit("--move-stage cannot be combined with --move/release/restart flags")
    scripted_move = bool(args.move or move_stages)
    trace_actions = []
    trace_time_limit = 0.0
    if args.input_trace:
        if not args.require_physical_outcome or not args.board_abi_f32 or scripted_move or args.release_frames or args.restart_after_move:
            raise SystemExit("input-trace requires physical outcome and Float32 board, without other motion")
        input_trace = json.loads(args.input_trace.read_text())
        trace_actions = parse_capture_trace(input_trace, args.rung, args.seed)
        trace_time_limit = trace_time_limit_seconds(input_trace)
    if args.require_physical_outcome and args.outcome not in ("won", "lost", "done"):
        raise SystemExit("--require-physical-outcome requires won, lost, or done")
    source_root = args.source_root.resolve()
    if not (source_root / "neural_workshop/ui/marblemaze.py").is_file():
        raise SystemExit(f"not an original Neural Workshop checkout: {source_root}")
    sys.path.insert(0, str(source_root / "tests"))

    # Importing uisupport builds the original application and its headless GL
    # window using the same fixture that owns the upstream UI tests.
    import uisupport
    if uisupport.UI_IMPORT_ERROR is not None:
        raise SystemExit(f"original Marble Maze UI is unavailable: {uisupport.UI_IMPORT_ERROR}")
    from neural_workshop import geometry, state
    from neural_workshop import marblemaze as marble_source
    from neural_workshop.marblemaze import MAX_TILT
    from neural_workshop.paths import get_res_dir
    from neural_workshop.ui.marblemaze import MarbleMaze
    from nwenv.frames import capture_rgba
    from pyglet import gl
    from pyglet.image import ImageData

    if not 1 <= args.rung <= 16 or args.width < 320 or args.height < 240:
        raise SystemExit("rung or capture dimensions are outside supported bounds")
    if not 1 <= args.trials <= 12:
        raise SystemExit("--trials must be between 1 and 12")
    if not 0 <= args.next_trial_elapsed_ms <= 15000:
        raise SystemExit("--next-trial-elapsed-ms must be between 0 and 15000")
    if args.next_trial_elapsed_ms and args.outcome != "next-trial":
        raise SystemExit("--next-trial-elapsed-ms is valid only with --outcome next-trial")
    if (not math.isfinite(args.timeout_seconds) or
            not 15.0 <= args.timeout_seconds <= 120):
        raise SystemExit("--timeout-seconds must be finite and between 15 and 120")
    if (not all(map(math.isfinite, (args.roll, args.pitch))) or
            max(abs(args.roll), abs(args.pitch)) > MAX_TILT):
        raise SystemExit(
            f"roll and pitch must be finite and within the {MAX_TILT} radian tilt limit")
    if not 0 <= args.move_frames <= 600 or bool(args.move_frames) != bool(args.move):
        raise SystemExit("--move and --move-frames must be supplied together (1..600 frames)")
    if not 0 <= args.release_frames <= 600 or (args.release_frames and not args.move):
        raise SystemExit("--release-frames must be in 0..600 and requires --move")
    if (not 0 <= args.post_restart_frames <= 600 or
            (args.restart_after_move and not args.move) or
            (args.post_restart_frames and not args.restart_after_move)):
        raise SystemExit("--post-restart-frames must be in 0..600 and requires --restart-after-move and --move")
    if args.board_abi_f32 and args.outcome == "ready":
        raise SystemExit("--board-abi-f32 requires a generated board")
    if args.outcome == "ready" and (scripted_move or args.release_frames or args.restart_after_move or args.post_restart_frames or args.roll != 0 or args.pitch != 0):
        raise SystemExit("READY captures cannot include a board pose or scripted motion")
    if args.outcome in ("won", "lost", "done"):
        validate_terminal_capture(args.rung, args.require_physical_outcome,
                                  bool(scripted_move or args.release_frames or
                                       args.restart_after_move or args.post_restart_frames))
    if args.outcome == "timeout" and (scripted_move or args.release_frames or args.restart_after_move or args.post_restart_frames):
        raise SystemExit("timeout captures cannot combine the deadline with scripted motion")
    if args.outcome == "next-trial" and (args.trials < 2 or scripted_move or args.release_frames or args.restart_after_move or args.post_restart_frames or args.rung != 1):
        raise SystemExit("next-trial captures require at least two trials, rung 1, and no scripted motion")
    uisupport.close_overlays()
    state.cfg.BLACK_BACKGROUND = args.theme == "dark"
    geometry.set_window_size(args.width, args.height)
    task = MarbleMaze()
    task.rng = random.Random(args.seed)
    run_rng = random.Random(args.seed)
    expected_board_seed = 0 if args.outcome == "ready" else run_rng.randrange(1 << 30)
    if args.outcome == "next-trial":
        # Each source board consumes a second stream value for its visual
        # grain seed after _next_trial() deals the tray.
        run_rng.random()
        expected_board_seed = run_rng.randrange(1 << 30)
        expected_grain_seed = run_rng.random() * 4.0
    else:
        expected_grain_seed = 0.0 if args.outcome == "ready" else run_rng.random() * 4.0
    task.start_rung = args.rung
    task.rung = args.rung
    task.total_trials = args.trials
    task.time_limit = (args.timeout_seconds
                       if args.outcome in ("timeout", "next-trial")
                       else trace_time_limit)
    task.adaptive = False
    task.show_shadows = True
    task.clock = lambda: 0.0
    if args.outcome != "ready":
        task.start_run()
        if args.board_abi_f32:
            # The browser receives board geometry as Float32 values. Re-run the
            # untouched source Simulation on those exact values for interaction
            # parity; retain the original grain seed so visuals/RNG identity do
            # not change when the meshes are rebuilt.
            task.tray = float32_abi_tray(task.tray)
            task.sim = marble_source.Simulation(task.tray)
            grain_seed = task.stage.grain_seed
            rng_state = task.rng.getstate()
            try:
                task._build_scene()
            finally:
                task.rng.setstate(rng_state)
                task.stage.grain_seed = grain_seed
        task.sim.roll = args.roll
        task.sim.pitch = args.pitch
    if args.outcome == "timeout":
        # Reach the source's real timeout through update(), keeping every
        # physics step at or below its certified 60 Hz maximum. This preserves
        # live marble poses and enters the normal lost-feedback UI without
        # fabricating a physical hole loss.
        while task.phase == "rolling" and task.sim.elapsed < task.seconds:
            step = min(1.0 / 60.0, task.seconds - task.sim.elapsed)
            task.update(step)
        if (task.phase != "lost" or task.sim is None or task.sim.settled or
                task.sim.elapsed + 1e-9 < task.seconds):
            task.close()
            raise SystemExit("timeout fixture did not reach unsettled lost feedback")
    if args.outcome == "next-trial":
        # Drive the original UI's actual feedback deadline and next-tray path:
        # tray one times out through update(), then the official update() calls
        # _next_trial() after its 2.6-second feedback interval. The captured
        # frame starts on the newly generated second board, then optionally
        # advances its requested neutral replay time.
        if task.phase == "rolling":
            while task.phase == "rolling" and task.sim.elapsed < task.seconds:
                step = min(1.0 / 60.0, task.seconds - task.sim.elapsed)
                task.update(step)
        if task.phase != "lost" or task.sim is None or task.sim.settled:
            task.close()
            raise SystemExit("first source tray did not enter unsettled timeout feedback")
        feedback_deadline = task.until
        task.clock = lambda: feedback_deadline + 1e-6
        task.update(0.0)
        if args.board_abi_f32:
            # Rollover replaces the first converted tray with a new source
            # binary64 tray. Convert it before advancing or claiming f32 metadata.
            rebuild_float32_capture_board(task, marble_source.Simulation)
        remaining = args.next_trial_elapsed_ms / 1000.0
        while remaining > 0:
            step = min(1.0 / 60.0, remaining)
            task.update(step)
            remaining -= step
        expected_second_tray = marble_source.deal(args.rung, seed=expected_board_seed)
        if args.board_abi_f32:
            expected_second_tray = float32_abi_tray(expected_second_tray)
        if (task.phase != "rolling" or task.trial != 2 or task.sim is None or
                not capture_elapsed_matches(task.sim.elapsed, args.next_trial_elapsed_ms) or
                task.tray != expected_second_tray):
            task.close()
            raise SystemExit(
                "source next-trial transition mismatch: "
                f"phase={task.phase!r}, trial={task.trial}, "
                f"elapsed={None if task.sim is None else task.sim.elapsed!r}, "
                f"second_board_matches_seed={task.tray == expected_second_tray}")
    if trace_actions:
        for action in trace_actions:
            if action["kind"] == "level":
                task.level_tray()
            else:
                task.held.clear()
                task.held.update(action["held"])
                task.update(action["dt"])
        task.held.clear()
    if args.move:
        task.held.update(args.move)
        for _frame in range(args.move_frames):
            task.update(1.0 / 60.0)
        task.held.clear()
        for _frame in range(args.release_frames):
            task.update(1.0 / 60.0)
        if args.restart_after_move:
            task.restart()
            for _frame in range(args.post_restart_frames):
                task.update(1.0 / 60.0)
    elif move_stages:
        for stage in move_stages:
            task.held.clear()
            task.held.update(stage["held"])
            for _frame in range(stage["frames"]):
                task.update(1.0 / 60.0)
        task.held.clear()
    if scripted_move and (task.phase not in ("rolling", "won", "lost") or task.sim is None):
        task.close()
        raise SystemExit("scripted held/released source replay reached an invalid phase")
    if args.outcome in ("won", "lost", "done"):
        # Mirror the upstream UI verdict tests: force the Simulation's discrete
        # terminal state, then let MarbleMaze.update() decide/paint the outcome.
        # The screenshot therefore includes the real source phase/message path,
        # not a hand-drawn terminal label.
        terminal_state = "home" if args.outcome in ("won", "done") else "lost"
        if args.require_physical_outcome:
            require_physical_terminal(task, args.outcome)
        else:
            for marble in task.sim.marbles:
                marble.state = terminal_state
            task.update(1.0 / 60.0)
        expected_phase = "won" if args.outcome == "done" else args.outcome
        if task.phase != expected_phase:
            task.close()
            raise SystemExit(
                f"source terminal fixture entered {task.phase!r}, expected {expected_phase!r}")
        if args.outcome == "done":
            # total_trials=1, so the ordinary source next-trial transition
            # records the completed run and retains the final rendered board.
            task._next_trial()
            if task.phase != "done":
                task.close()
                raise SystemExit("source completion fixture did not reach done")
    if (task.tray is not None and
            abs(task.stage.grain_seed - expected_grain_seed) > 1e-12):
        task.close()
        raise SystemExit(
            "source board/grain RNG stream diverged from the expected trial identity")
    tray = task.tray
    board_geometry = None if tray is None else {
        "rung": int(tray.rung),
        "cols": int(tray.cols),
        "rows": int(tray.rows),
        "width": float(tray.width),
        "depth": float(tray.depth),
        "cell": float(tray.cell),
        "thickness": float(tray.thickness),
        "height": float(tray.height),
        "walls": [{"x0": float(wall.x0), "y0": float(wall.y0),
                   "x1": float(wall.x1), "y1": float(wall.y1)}
                  for wall in tray.walls],
        "holes": [{"x": float(hole.x), "y": float(hole.y),
                   "radius": float(hole.radius), "home": bool(hole.home)}
                  for hole in tray.holes],
        "starts": [{"x": float(x), "y": float(y)} for x, y in tray.starts],
        "home": {"x": float(tray.home[0]), "y": float(tray.home[1]),
                 "radius": float(tray.home[2])},
    }
    # on_draw advances only while pyglet's event loop is running. Keep the
    # reference frame at exactly zero active time even if the host runs it.
    task.update = lambda _dt: None
    task._drawn_at = None

    window = state.window
    resize_replay = None
    if args.resize_to:
        initial_points = geometry.point_size()
        final_points = geometry.set_window_size(*args.resize_to)
        if final_points != args.resize_to:
            task.close()
            raise SystemExit(
                f"source resize mismatch: requested {args.resize_to}, got {final_points}"
            )
        window.dispatch_events()
        resize_replay = {
            "initialPoints": list(initial_points),
            "finalPoints": list(geometry.point_size()),
        }
    expected_dpr = os.environ.get("NW_MARBLE_PAIR_EXPECT_DPR")
    if expected_dpr is not None and abs(window.scale - float(expected_dpr)) > 1e-9:
        task.close()
        raise SystemExit(
            f"original capture DPR mismatch: requested {expected_dpr}, got {window.scale}"
        )
    window.switch_to()
    # `uisupport` creates the original window before this fixture selects its
    # requested theme. The real application sets GL's clear colour during
    # window construction, so changing BLACK_BACKGROUND alone leaves the
    # surrounding framebuffer in the old (usually white) colour. Mirror the
    # application's window initialization after switching to its context.
    clear_colour = 0.0 if args.theme == "dark" else 1.0
    gl.glClearColor(clear_colour, clear_colour, clear_colour, 1.0)
    window.dispatch_events()
    window.clear()
    task.on_draw()
    width, height, rgba = capture_rgba(window)
    if width <= 0 or height <= 0 or not rgba:
        task.close()
        raise SystemExit("original Marble Maze framebuffer capture is empty")
    args.png.parent.mkdir(parents=True, exist_ok=True)
    args.metadata.parent.mkdir(parents=True, exist_ok=True)
    ImageData(width, height, "RGBA", rgba, pitch=-width * 4).save(str(args.png))

    left, bottom, view_width, view_height = task._stage_rect()
    camera = None
    if task.tray is not None:
        view_proj, eye = task._camera(view_width / max(1, view_height))
        camera = {"eye": [float(value) for value in eye],
                  "viewProj": [float(value) for value in view_proj],
                  "aspect": view_width / max(1, view_height)}
    material_folder = Path(get_res_dir()) / "marblemaze"
    if task.phase in ("won", "lost"):
        physical_outcome = task.phase
    elif task.phase == "done" and task.results:
        # DONE retains the last source tray for its summary frame. Recover the
        # actual final-tray outcome from the result row, not from the requested
        # fixture mode (which may have transitioned through real gameplay).
        physical_outcome = "won" if task.results[-1][3] == 0 else "lost"
    else:
        physical_outcome = None
    metadata = {
        "captureComplete": True,
        "labelFonts": {name: capture_label_font(getattr(task, name))
                       for name in ("title", "status", "footnote")},
        "inputTrace": None if not args.input_trace else {
            "sha256": hashlib.sha256(args.input_trace.read_bytes()).hexdigest(),
            "events": len(trace_actions), "posesInjected": False},
        "terminalFixture": ("physical-replay" if args.require_physical_outcome else
                            "forced-discrete-state" if args.outcome in ("won", "lost", "done")
                            else "none"),
        "boardSeed": expected_board_seed,
        "boardGeometry": board_geometry,
        **({"boardGeometryPrecision": "wasm-f32-roundtrip"}
           if args.board_abi_f32 else {}),
        "grainSeed": task.stage.grain_seed,
        "rung": task.tray.rung if task.tray is not None else task.rung,
        "trial": 0 if task.tray is None else task.trial - 1,
        "elapsedMs": round(task.sim.elapsed * 1000) if task.sim is not None else 0,
        "secondsPerTray": round(task.seconds) if task.sim is not None else 0,
        "statusText": task.status.text if task.sim is not None else None,
        "roll": task.sim.roll if task.sim is not None else 0.0,
        "pitch": task.sim.pitch if task.sim is not None else 0.0,
        "camera": camera,
        "viewport": {"x": left, "y": height - bottom - view_height,
                     "width": view_width, "height": view_height},
        "sourceWindow": {
            "dpiScalingOverride": os.environ.get("PYGLET_DPI_SCALING"),
            "points": list(geometry.point_size()),
            "layoutPixels": list(geometry.pixel_size()),
            "framebuffer": [int(width), int(height)],
            "scale": float(window.scale),
        },
        "dpr": float(window.scale),
        "resizeReplay": resize_replay,
        "theme": args.theme,
        "inputReplay": (
            {"stages": move_stages} if move_stages else
            {"held": sorted(set(args.move)),
             "heldFrames": args.move_frames,
             "releaseFrames": args.release_frames,
             "restarted": args.restart_after_move,
             "postRestartFrames": args.post_restart_frames}
            if args.move else None),
        "assetHash": assets_digest(material_folder),
        "materialState": ("not-created:no-board" if task.tray is None else
                          "settled:3-of-3" if task.textured else
                          "settled:procedural-fallback"),
        "sceneState": {
            "version": 1,
            "phase": task.phase,
            "outcome": physical_outcome,
            **({"terminalReason": "timeout"} if args.outcome == "timeout" else {}),
            "elapsedMs": round(task.sim.elapsed * 1000) if task.sim is not None else 0,
            "roll": task.sim.roll if task.sim is not None else 0.0,
            "pitch": task.sim.pitch if task.sim is not None else 0.0,
            "marbles": [{name: getattr(marble, name) for name in (
                "x", "y", "z", "vx", "vy", "vz", "wx", "wy", "wz",
                "qw", "qx", "qy", "qz", "state")} for marble in
                (task.sim.marbles if task.sim is not None else [])],
        },
        "image": {"sha256": hashlib.sha256(args.png.read_bytes()).hexdigest(),
                  "dimensions": [width, height]},
    }
    args.metadata.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")
    task.close()
    print(json.dumps({"png": str(args.png), "metadata": str(args.metadata),
                      "boardSeed": expected_board_seed,
                      "grainSeed": metadata["grainSeed"],
                      "dimensions": [width, height],
                      "viewport": metadata["viewport"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
