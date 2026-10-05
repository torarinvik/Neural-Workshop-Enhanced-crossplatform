#!/usr/bin/env python3
"""Bind a headed browser Marble capture to source state after verifying it.

The browser debug snapshot is captured from ``window.__nw.marbleDebug``. State
and render metadata are derived from that snapshot and checked against the
source manifest; source state is never copied into the browser claim.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import struct

from PIL import Image


MARBLE_FIELDS = (
    "x", "y", "z", "vx", "vy", "vz", "wx", "wy", "wz",
    "qw", "qx", "qy", "qz", "state",
)
PHASE_NUMBERS = {"ready": 0, "rolling": 1, "won": 2, "lost": 2, "done": 4}
NUMERIC_STATE_FIELDS = {
    "x", "y", "z", "vx", "vy", "vz", "wx", "wy", "wz",
    "qw", "qx", "qy", "qz",
}
STATE_TOLERANCE = 1e-12
# Native MuJoCo and the browser WASM build can differ by a few 1e-8 in an
# integrated angular velocity after only 30 fixed steps. Keep this far below
# one microunit while admitting that measured cross-build precision delta.
PHYSICS_STATE_TOLERANCE = 1e-7
# Generated board geometry crosses the stable WASM board ABI as binary32,
# while the upstream Python tray retains binary64 coordinates. The native
# trajectory suite certifies position parity to 1e-8 metres; use that bound
# for simulated physics, and separately allow an exact binary32 round-trip
# for the board-generated x/y start coordinates.
PHYSICS_POSITION_TOLERANCE = 1e-8


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def close_number(actual: object, expected: object, label: str,
                 tolerance: float = STATE_TOLERANCE) -> None:
    require(isinstance(actual, (int, float)) and not isinstance(actual, bool) and
            math.isfinite(actual), f"browser debug snapshot has invalid {label}")
    require(isinstance(expected, (int, float)) and not isinstance(expected, bool) and
            math.isfinite(expected), f"source manifest has invalid {label}")
    require(abs(float(actual) - float(expected)) <= tolerance,
            f"browser {label} differs from source: {actual!r} != {expected!r}")


def float32_roundtrip(value: float) -> float:
    """Return the exact binary32 value used at the generated-board ABI."""
    return struct.unpack("=f", struct.pack("=f", float(value)))[0]


def close_physics_number(actual: object, expected: object, label: str,
                         field: str) -> None:
    if (field in ("x", "y") and isinstance(actual, (int, float)) and
            not isinstance(actual, bool) and isinstance(expected, (int, float)) and
            not isinstance(expected, bool) and
            float(actual) == float32_roundtrip(float(expected))):
        return
    tolerance = (PHYSICS_STATE_TOLERANCE if field in {
        "vx", "vy", "vz", "wx", "wy", "wz", "qw", "qx", "qy", "qz"
    } else PHYSICS_POSITION_TOLERANCE)
    close_number(actual, expected, label, tolerance)


def geometry_mismatches(actual: object, expected: object,
                        path: str = "boardGeometry") -> list[str]:
    """Compare source geometry exactly, except exact Float32 board-ABI values."""
    if isinstance(actual, dict) and isinstance(expected, dict):
        if set(actual) != set(expected):
            return [path]
        return [mismatch for key in sorted(expected)
                for mismatch in geometry_mismatches(
                    actual[key], expected[key], f"{path}.{key}")]
    if isinstance(actual, list) and isinstance(expected, list):
        if len(actual) != len(expected):
            return [path]
        return [mismatch for index, (left, right) in enumerate(zip(actual, expected))
                for mismatch in geometry_mismatches(left, right, f"{path}[{index}]")]
    if (isinstance(actual, (int, float)) and not isinstance(actual, bool) and
            isinstance(expected, (int, float)) and not isinstance(expected, bool)):
        if not math.isfinite(actual) or not math.isfinite(expected):
            return [path]
        return ([] if float(actual) == float(expected) or
                float(actual) == float32_roundtrip(float(expected)) else [path])
    return ([] if type(actual) is type(expected) and actual == expected else [path])


def validate_source_window(source: dict) -> None:
    """Reject source manifests that conflate point, layout, or buffer units."""
    window = source.get("sourceWindow")
    require(isinstance(window, dict), "source manifest has no sourceWindow record")
    points, layout, framebuffer = (
        window.get("points"), window.get("layoutPixels"), window.get("framebuffer"))
    for label, size in (("points", points), ("layoutPixels", layout),
                        ("framebuffer", framebuffer)):
        require(isinstance(size, list) and len(size) == 2 and
                all(isinstance(value, int) and not isinstance(value, bool) and value > 0
                    for value in size),
                f"sourceWindow {label} must contain two positive integers")
    scale = window.get("scale")
    require(isinstance(scale, (int, float)) and not isinstance(scale, bool) and
            math.isfinite(scale) and scale > 0,
            "sourceWindow scale must be a positive finite number")
    for axis, (point_size, pixel_size) in enumerate(zip(points, layout)):
        require(abs(pixel_size - point_size * float(scale)) <= 0.51,
                f"sourceWindow points/layoutPixels disagree on axis {axis}")
    close_number(source.get("dpr"), scale, "source window scale")
    image = source.get("image")
    require(isinstance(image, dict) and image.get("dimensions") == framebuffer,
            "sourceWindow framebuffer differs from captured image dimensions")


def scene_state_matches(actual: dict, expected: dict) -> bool:
    """Accept only certified Float32 board-ABI quantization in marble fields."""
    if set(actual) != set(expected):
        return False
    if any(actual[field] != expected[field] for field in actual.keys() - {"marbles"}):
        return False
    actual_marbles, expected_marbles = actual.get("marbles"), expected.get("marbles")
    if (not isinstance(actual_marbles, list) or not isinstance(expected_marbles, list) or
            len(actual_marbles) != len(expected_marbles)):
        return False
    for actual_marble, expected_marble in zip(actual_marbles, expected_marbles):
        if (not isinstance(actual_marble, dict) or not isinstance(expected_marble, dict) or
                set(actual_marble) != set(expected_marble)):
            return False
        for field, value in actual_marble.items():
            expected_value = expected_marble[field]
            if (isinstance(value, (int, float)) and not isinstance(value, bool) and
                    isinstance(expected_value, (int, float)) and not isinstance(expected_value, bool)):
                if field in ("x", "y") and float(value) == float32_roundtrip(float(expected_value)):
                    continue
                if abs(float(value) - float(expected_value)) > PHYSICS_STATE_TOLERANCE:
                    return False
            elif value != expected_value:
                return False
    return True


def browser_manifest_state(source: dict, debug: dict, png: Path) -> dict:
    source_scene = source["sceneState"]
    controller = debug.get("state")
    board = debug.get("board")
    marbles = debug.get("marbles")
    capture = debug.get("capture")
    require(isinstance(controller, list) and len(controller) >= 12,
            "browser debug snapshot has no complete Marble controller state")
    require(all(isinstance(value, int) and not isinstance(value, bool) and
                abs(value) <= 2**53 - 1 for value in controller[:12]),
            "browser controller state must contain exact safe integers")
    require(isinstance(capture, dict),
            "browser debug snapshot has no capture state")

    phase = source_scene["phase"]
    source_status = source.get("statusText")
    browser_status = debug.get("statusText")
    if source_status is not None:
        require(isinstance(source_status, str) and isinstance(browser_status, str) and
                browser_status == source_status,
                "browser status text differs from source")
    require(phase in PHASE_NUMBERS, "source manifest has an unsupported Marble phase")
    require(int(controller[0]) == PHASE_NUMBERS[phase],
            f"browser controller phase does not match source {phase!r}")
    if phase in ("won", "lost"):
        expected_verdict = 1 if phase == "won" else 0
        require(int(controller[8]) == expected_verdict,
                "browser controller verdict differs from source outcome")
    ready = phase == "ready"
    source_seconds = source.get("secondsPerTray")
    require(isinstance(source_seconds, int) and not isinstance(source_seconds, bool) and
            source_seconds >= 0,
            "source manifest has invalid secondsPerTray")
    require(int(controller[1]) == source["rung"],
            "browser controller rung differs from source")
    if ready:
        browser_geometry = None
        require(board is None and source["boardSeed"] == 0 and source["trial"] == 0,
                "READY capture must not claim a generated board or trial")
        require(source.get("boardGeometry") is None,
                "source READY capture must not claim generated board geometry")
        require(isinstance(marbles, list) and not marbles and
                int(controller[2]) == 0,
                "browser READY state must not contain a board, trial, or marbles")
    else:
        require(isinstance(board, dict),
                "browser debug snapshot has no generated board")
        require(int(board.get("rung", -1)) == source["rung"],
                "browser board rung differs from source")
        require(int(board.get("seed", -1)) == source["boardSeed"],
                "browser board seed differs from source")
        require(controller[5] == source["boardSeed"],
                "browser controller seed differs from source board")
        require(isinstance(marbles, list) and marbles,
                "browser debug snapshot has no live Marble poses")
        # The common controller reports one-based current trial; source manifests
        # intentionally store the zero-based completed/current trial ordinal.
        require(int(controller[2]) - 1 == source["trial"],
                "browser trial index differs from source")
        source_geometry = source.get("boardGeometry")
        require(isinstance(source_geometry, dict),
                "source manifest has no generated board geometry")
        browser_geometry = {key: board.get(key) for key in (
            "rung", "cols", "rows", "width", "depth", "cell", "thickness",
            "height", "walls", "holes", "starts", "home")}
        require(all(value is not None for value in browser_geometry.values()),
                "browser board snapshot has incomplete generated geometry")
        geometry_errors = geometry_mismatches(browser_geometry, source_geometry)
        require(not geometry_errors,
                "browser board geometry differs from source: " +
                ", ".join(geometry_errors[:8]))
    # remainingMs is a feedback countdown after a marble is lost or reaches
    # home; it is not the configured tray budget in terminal captures. Read
    # the effective budget directly from the live browser board/options instead
    # of trying to reconstruct it from phase-dependent controller clocks.
    browser_seconds = debug.get("secondsPerTray")
    require(isinstance(browser_seconds, int) and not isinstance(browser_seconds, bool) and
            browser_seconds >= 0,
            "browser debug snapshot has invalid secondsPerTray")
    seconds_per_tray = int(browser_seconds)
    require((ready and seconds_per_tray == 0) or
            (not ready and seconds_per_tray > 0),
            "browser effective seconds-per-tray is inconsistent with phase")
    require(seconds_per_tray == source_seconds,
            "browser effective seconds-per-tray differs from source")
    close_number(debug.get("grainSeed"), source["grainSeed"], "grainSeed")
    close_number(debug.get("roll"), source_scene["roll"], "roll")
    close_number(debug.get("pitch"), source_scene["pitch"], "pitch")
    # The source manifest stores simulation time at millisecond precision.
    # Terminal transitions can occur on a fractional 60-Hz tick (for example,
    # 25/60 s), so compare at the manifest's recorded precision rather than
    # requiring the rounded millisecond value to equal the unrounded float.
    simulation_elapsed = debug.get("elapsed")
    require(isinstance(simulation_elapsed, (int, float)) and
            not isinstance(simulation_elapsed, bool) and
            math.isfinite(simulation_elapsed) and simulation_elapsed >= 0,
            "browser debug snapshot has invalid simulation elapsed time")
    simulation_elapsed_raw_ms = float(simulation_elapsed) * 1000
    browser_simulation_ms = int(round(simulation_elapsed_raw_ms))
    require(browser_simulation_ms == source_scene["elapsedMs"],
            "browser simulation elapsedMs differs from source")
    # While play is still active, the controller stores the whole-millisecond
    # floor and the physics clock retains its fractional remainder. Once all
    # marbles physically settle, marbleTick explicitly synchronizes the
    # controller to Math.round(elapsed * 1000) before reporting the result.
    # Timeout feedback is different: its final physics step remains unsettled,
    # so it keeps the active-play floor. Validate the representation used by
    # the actual lifecycle path rather than assuming every terminal verdict
    # came from physical settlement.
    source_marbles = source_scene.get("marbles")
    physically_settled = (
        phase in ("won", "lost", "done") and
        isinstance(source_marbles, list) and bool(source_marbles) and
        all(isinstance(marble, dict) and
            marble.get("state") in ("home", "lost")
            for marble in source_marbles)
    )
    expected_controller_ms = (
        math.floor(simulation_elapsed_raw_ms + 0.5)
        if physically_settled else
        math.floor(simulation_elapsed_raw_ms + 1e-9)
    )
    expected_clock_name = "physical-settlement" if physically_settled else "active-play"
    require(int(controller[6]) == expected_controller_ms,
            f"browser controller elapsed time differs from its {expected_clock_name} clock")

    require(len(marbles) == len(source_scene["marbles"]),
            "browser marble count differs from source")
    rendered_marbles = []
    for index, (actual, expected) in enumerate(zip(marbles, source_scene["marbles"])):
        require(isinstance(actual, dict), f"browser marble {index} is malformed")
        rendered = {field: actual.get(field) for field in MARBLE_FIELDS}
        require(rendered["state"] == expected.get("state"),
                f"browser marble {index} state differs from source")
        for field in NUMERIC_STATE_FIELDS:
            close_physics_number(rendered[field], expected.get(field),
                                 f"marble[{index}].{field}", field)
        rendered_marbles.append(rendered)

    live_outcome = None
    if phase in ("won", "lost", "done"):
        live_outcome = ("won" if all(marble["state"] == "home"
                                      for marble in rendered_marbles) else "lost")
        require(live_outcome == source_scene["outcome"],
                "browser marble states imply a different terminal outcome")
    elif phase == "rolling":
        require(any(marble["state"] in ("rolling", "falling")
                    for marble in rendered_marbles),
                "browser rolling phase has no moving marble")
    terminal_reason = source_scene.get("terminalReason")
    require(debug.get("terminalReason") == terminal_reason,
            "browser timeout reason differs from source")
    if terminal_reason == "timeout":
        require(phase == "lost" and all(marble["state"] in ("rolling", "falling")
                                         for marble in rendered_marbles),
                "timeout feedback must retain an unsettled, moving marble pose")
        require(source_scene["elapsedMs"] > 0,
                "timeout feedback must have a positive elapsed time")

    viewport = capture.get("viewport")
    framebuffer = capture.get("framebuffer")
    camera = capture.get("camera")
    camera_valid = (camera is None if ready else
                    isinstance(camera, dict) and isinstance(camera.get("viewProj"), list))
    require(isinstance(viewport, dict) and isinstance(framebuffer, dict) and
            camera_valid,
            "browser debug snapshot has incomplete renderer capture state")
    sample_count = capture.get("sampleCount")
    require((ready and sample_count is None) or
            (not ready and sample_count == 4),
            "browser Marble colour/depth target must report the source's four samples")
    browser_viewport = {key: int(viewport[key])
                        for key in ("x", "y", "width", "height")}
    require(browser_viewport == source["viewport"],
            "browser stage viewport differs from source")
    dimensions = [int(framebuffer["width"]), int(framebuffer["height"])]
    readback = capture.get("readback")
    expected_background = "rgb(0, 0, 0)" if capture.get("dark") is True else "rgb(255, 255, 255)"
    require(isinstance(capture.get("dark"), bool),
            "browser capture theme flag must be boolean")
    require(isinstance(readback, dict) and
            readback.get("mode") == "displayed-background-composite" and
            readback.get("background") == expected_background and
            readback.get("width") == dimensions[0] and
            readback.get("height") == dimensions[1],
            "browser PNG must attest a same-size displayed-background composite")
    with Image.open(png) as image:
        require(list(image.size) == dimensions,
                "browser screenshot dimensions differ from live framebuffer")
        if readback["mode"] == "displayed-background-composite":
            alpha = image.convert("RGBA").getchannel("A")
            require(alpha.getextrema() == (255, 255),
                    "browser displayed-background composite PNG is not fully opaque")
    close_number(capture.get("dpr"), source["dpr"], "devicePixelRatio")
    theme = "dark" if capture.get("dark") is True else "light"
    require(theme == source["theme"], "browser theme differs from source")
    require(capture.get("materialState") == source["materialState"],
            "browser material settlement differs from source")

    browser_scene = {
        "version": 1,
        "phase": phase,
        "outcome": live_outcome,
        "marbles": rendered_marbles,
        "roll": float(debug["roll"]),
        "pitch": float(debug["pitch"]),
        "elapsedMs": int(round(float(debug["elapsed"]) * 1000)),
    }
    if terminal_reason is not None:
        browser_scene["terminalReason"] = terminal_reason
    require(scene_state_matches(browser_scene, source_scene),
            "browser-rendered scene snapshot differs from source beyond the board-ABI physics tolerance")
    return {
        "camera": camera,
        "viewport": browser_viewport,
        "dpr": capture["dpr"],
        "theme": theme,
        "materialState": capture["materialState"],
        "sampleCount": sample_count,
        "secondsPerTray": seconds_per_tray,
        **({"statusText": browser_status} if source_status is not None else {}),
        "boardGeometry": None if ready else browser_geometry,
        "boardSeed": 0 if ready else int(board["seed"]),
        "grainSeed": float(debug["grainSeed"]),
        "elapsedMs": browser_simulation_ms,
        "controllerElapsedMs": int(controller[6]),
        "roll": float(debug["roll"]),
        "pitch": float(debug["pitch"]),
        "sceneState": browser_scene,
        "imageReadback": readback,
        "dimensions": dimensions,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-metadata", required=True, type=Path)
    parser.add_argument("--png", required=True, type=Path)
    parser.add_argument("--browser-debug-json", required=True, type=Path,
                        help="file containing window.__nw.marbleDebug JSON")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    source = json.loads(args.source_metadata.read_text())
    debug = json.loads(args.browser_debug_json.read_text())
    if not source.get("captureComplete") or not isinstance(source.get("sceneState"), dict):
        raise SystemExit("source manifest is incomplete or has no synchronized sceneState")
    validate_source_window(source)
    if not isinstance(debug, dict):
        raise SystemExit("browser debug snapshot must be a JSON object")
    browser_state = browser_manifest_state(source, debug, args.png)
    dimensions = browser_state.pop("dimensions")
    readback = browser_state.pop("imageReadback")
    if dimensions != source["image"].get("dimensions"):
        raise SystemExit(
            f"browser PNG dimensions {dimensions} differ from source fixture "
            f"{source['image'].get('dimensions')}")

    candidate = {key: value for key, value in source.items()
                 if key not in ("sourceWindow", "image", "camera", "viewport",
                                "dpr", "theme", "materialState", "boardSeed",
                                "grainSeed", "elapsedMs", "roll", "pitch",
                                "sceneState", "boardGeometry")}
    candidate.update(browser_state)
    candidate["image"] = {
        "sha256": hashlib.sha256(args.png.read_bytes()).hexdigest(),
        "dimensions": dimensions,
        "readback": readback,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(candidate, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"metadata": str(args.output), "image": candidate["image"]},
                     sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
