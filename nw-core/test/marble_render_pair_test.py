"""Measure a synchronized native/browser Marble Maze screenshot pair.

This is intentionally a diagnostic comparator, not a claim that pyglet/OpenGL
and WebGL2 must produce identical sample masks. Both images must already be
captured from the same board, camera, tilt, theme, viewport, and material
settlement state. Optional limits make a reviewed pair reproducible without
turning a cross-rasterizer comparison into a false exact-pixel assertion.

No files are written by this command.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import struct
import sys
from pathlib import Path

import numpy as np
from PIL import Image

SYNC_FIELDS = (
    "boardSeed", "grainSeed", "rung", "trial", "elapsedMs", "secondsPerTray", "roll",
    "pitch", "camera", "viewport", "dpr", "theme", "assetHash",
    "materialState", "boardGeometry",
)
CAMERA_ABS_TOLERANCE = 2e-6
MARBLE_STATE_ABS_TOLERANCE = 1e-8
MARBLE_VELOCITY_ABS_TOLERANCE = 1e-7


def float32_roundtrip(value: float) -> float:
    """Return the exact binary32 value used at the generated-board ABI."""
    return struct.unpack("=f", struct.pack("=f", float(value)))[0]


def board_geometry_mismatches(left: object, right: object,
                              path: str = "boardGeometry") -> list[str]:
    """Require identical board topology and exact values after the Float32 ABI."""
    if isinstance(left, dict) and isinstance(right, dict):
        if set(left) != set(right):
            return [path]
        return [field for key in sorted(left)
                for field in board_geometry_mismatches(
                    left[key], right[key], f"{path}.{key}")]
    if isinstance(left, list) and isinstance(right, list):
        if len(left) != len(right):
            return [path]
        return [field for index, (a, b) in enumerate(zip(left, right))
                for field in board_geometry_mismatches(a, b, f"{path}[{index}]")]
    if (isinstance(left, (int, float)) and not isinstance(left, bool) and
            isinstance(right, (int, float)) and not isinstance(right, bool)):
        if not math.isfinite(left) or not math.isfinite(right):
            return [path]
        return ([] if float(left) == float(right) or
                float(right) == float32_roundtrip(float(left)) else [path])
    return ([] if type(left) is type(right) and left == right else [path])


def read_rgb(path: Path,
             background: tuple[int, int, int] | None = None) -> np.ndarray:
    try:
        with Image.open(path) as image:
            if background is None:
                # Original-source framebuffer RGB values are the rendered
                # channels to compare; do not composite their driver alpha.
                visible = image.convert("RGB")
            else:
                # Browser canvas readback preserves transparent pixels. The
                # page displays that canvas over its theme CSS background.
                backdrop = Image.new("RGBA", image.size, (*background, 255))
                visible = Image.alpha_composite(
                    backdrop, image.convert("RGBA")).convert("RGB")
            return np.asarray(visible, dtype=np.float32)
    except Exception as error:  # pragma: no cover - CLI-facing error
        raise SystemExit(f"could not read {path}: {error}") from error


def measure(reference: np.ndarray, candidate: np.ndarray,
            pixel_threshold: float) -> dict[str, object]:
    if reference.shape != candidate.shape:
        raise SystemExit(
            "screenshot dimensions/channels differ: "
            f"reference={reference.shape}, candidate={candidate.shape}")
    difference = np.abs(reference - candidate)
    exact = np.all(difference == 0.0, axis=2)
    over = np.max(difference, axis=2) > pixel_threshold
    return {
        "width": int(reference.shape[1]),
        "height": int(reference.shape[0]),
        "channels": int(reference.shape[2]),
        "exactPixelFraction": float(np.mean(exact)),
        "meanAbsoluteError": float(np.mean(difference)),
        "rmse": math.sqrt(float(np.mean(np.square(difference)))),
        "maximumAbsoluteError": float(np.max(difference)),
        "pixelsOverThresholdFraction": float(np.mean(over)),
        "pixelThreshold": float(pixel_threshold),
    }


def measure_pixel_set(reference: np.ndarray, candidate: np.ndarray,
                      pixel_threshold: float) -> dict[str, object]:
    """Summarize an arbitrary selected pixel set without hiding its size."""
    if reference.shape != candidate.shape:
        raise SystemExit("render-region selection has mismatched shape")
    if reference.size == 0:
        return {"pixelCount": 0, "exactPixelFraction": None,
                "meanAbsoluteError": None, "rmse": None,
                "maximumAbsoluteError": None,
                "pixelsOverThresholdFraction": None}
    delta = np.abs(reference.astype(np.float32) - candidate.astype(np.float32))
    per_pixel = np.max(delta, axis=1)
    return {
        "pixelCount": int(reference.shape[0]),
        "exactPixelFraction": float(np.mean(np.all(delta == 0.0, axis=1))),
        "meanAbsoluteError": float(np.mean(delta)),
        "rmse": math.sqrt(float(np.mean(np.square(delta)))),
        "maximumAbsoluteError": float(np.max(delta)),
        "pixelsOverThresholdFraction": float(np.mean(per_pixel > pixel_threshold)),
    }


def region_metrics(reference: np.ndarray, candidate: np.ndarray,
                   viewport: dict[str, object],
                   pixel_threshold: float) -> dict[str, object]:
    """Report the complete source stage separately from all surrounding UI."""
    height, width = reference.shape[:2]
    x, y = int(viewport["x"]), int(viewport["y"])
    stage_width, stage_height = int(viewport["width"]), int(viewport["height"])
    stage_left = reference[y:y + stage_height, x:x + stage_width]
    stage_right = candidate[y:y + stage_height, x:x + stage_width]
    outside = np.ones((height, width), dtype=bool)
    outside[y:y + stage_height, x:x + stage_width] = False
    header = np.zeros((height, width), dtype=bool)
    header[:y] = True
    footer = np.zeros((height, width), dtype=bool)
    footer[y + stage_height:] = True
    side_margins = np.zeros((height, width), dtype=bool)
    side_margins[y:y + stage_height, :x] = True
    side_margins[y:y + stage_height, x + stage_width:] = True
    return {
        "stage": measure(stage_left, stage_right, pixel_threshold),
        "chrome": measure_pixel_set(reference[outside], candidate[outside],
                                     pixel_threshold),
        "header": measure_pixel_set(reference[header], candidate[header],
                                     pixel_threshold),
        "footer": measure_pixel_set(reference[footer], candidate[footer],
                                     pixel_threshold),
        "stageSideMargins": measure_pixel_set(reference[side_margins],
                                               candidate[side_margins],
                                               pixel_threshold),
    }


def camera_difference(left: object, right: object, path: str = "camera") -> tuple[float, list[str]]:
    """Compare camera traces with a tight allowance for float32/float64 math."""
    if isinstance(left, dict) and isinstance(right, dict):
        if set(left) != set(right):
            return math.inf, [path]
        deltas = [camera_difference(left[key], right[key], f"{path}.{key}")
                  for key in sorted(left)]
    elif isinstance(left, list) and isinstance(right, list):
        if len(left) != len(right):
            return math.inf, [path]
        deltas = [camera_difference(a, b, f"{path}[{index}]")
                  for index, (a, b) in enumerate(zip(left, right))]
    elif (isinstance(left, (int, float)) and not isinstance(left, bool) and
          isinstance(right, (int, float)) and not isinstance(right, bool)):
        delta = abs(float(left) - float(right))
        return delta, [path] if delta > CAMERA_ABS_TOLERANCE else []
    else:
        return 0.0, [] if left == right else [path]
    return max((item[0] for item in deltas), default=0.0), [
        mismatch for _delta, fields in deltas for mismatch in fields]


def scene_state_mismatches(left: object, right: object) -> list[str]:
    """Compare source and browser physics states within the board ABI bound.

    Generated geometry is serialized through Float32 in the WASM board ABI,
    whereas the source simulation retains Python doubles. All non-marble
    fields remain exact; position uses the trajectory suite's certified 1e-8
    bound, while integrated velocity/rotation permits the measured 1e-7
    native-versus-WASM MuJoCo precision delta. For x/y, the exact Float32
    encoding of the source value is also accepted because those generated
    start coordinates cross the binary32 board ABI before reaching the browser.
    """
    if not isinstance(left, dict) or not isinstance(right, dict) or set(left) != set(right):
        return ["sceneState"]
    mismatches = []
    for field in left.keys() - {"marbles"}:
        if left[field] != right[field]:
            mismatches.append(f"sceneState.{field}")
    left_marbles, right_marbles = left.get("marbles"), right.get("marbles")
    if not isinstance(left_marbles, list) or not isinstance(right_marbles, list) or len(left_marbles) != len(right_marbles):
        return mismatches + ["sceneState.marbles"]
    for index, (left_marble, right_marble) in enumerate(zip(left_marbles, right_marbles)):
        label = f"sceneState.marbles[{index}]"
        if (not isinstance(left_marble, dict) or not isinstance(right_marble, dict) or
                set(left_marble) != set(right_marble)):
            mismatches.append(label)
            continue
        for field, left_value in left_marble.items():
            right_value = right_marble[field]
            if (isinstance(left_value, (int, float)) and not isinstance(left_value, bool) and
                    isinstance(right_value, (int, float)) and not isinstance(right_value, bool)):
                if field in ("x", "y") and float(right_value) == float32_roundtrip(float(left_value)):
                    continue
                tolerance = (MARBLE_VELOCITY_ABS_TOLERANCE if field in {
                    "vx", "vy", "vz", "wx", "wy", "wz", "qw", "qx", "qy", "qz"
                } else MARBLE_STATE_ABS_TOLERANCE)
                if abs(float(left_value) - float(right_value)) > tolerance:
                    mismatches.append(f"{label}.{field}")
            elif left_value != right_value:
                mismatches.append(f"{label}.{field}")
    return mismatches


def load_synchronized_metadata(reference_path: Path, candidate_path: Path,
                               reference_image: Path,
                               candidate_image: Path,
                               reference_rgb: np.ndarray,
                               candidate_rgb: np.ndarray) -> dict[str, object]:
    """Validate shared render state and bind each manifest to its PNG bytes."""
    try:
        reference = json.loads(reference_path.read_text())
        candidate = json.loads(candidate_path.read_text())
    except Exception as error:  # pragma: no cover - CLI-facing error
        raise SystemExit(f"could not read capture metadata: {error}") from error
    if not isinstance(reference, dict) or not isinstance(candidate, dict):
        raise SystemExit("capture metadata must be JSON objects")
    candidate_readback: dict[str, object] = {}
    for label, metadata in (("reference", reference), ("candidate", candidate)):
        missing = [field for field in SYNC_FIELDS if field not in metadata]
        if missing:
            raise SystemExit(
                f"{label} capture metadata is missing synchronization fields: "
                + ", ".join(missing))
        if metadata.get("captureComplete") is not True:
            raise SystemExit(
                f"{label} capture did not attest a complete settled render")
        image = metadata.get("image")
        if not isinstance(image, dict):
            raise SystemExit(f"{label} capture metadata has no image binding")
        actual_path = reference_image if label == "reference" else candidate_image
        actual_rgb = reference_rgb if label == "reference" else candidate_rgb
        try:
            actual_hash = hashlib.sha256(actual_path.read_bytes()).hexdigest()
        except OSError as error:
            raise SystemExit(f"could not hash {label} image: {error}") from error
        expected_dimensions = [int(actual_rgb.shape[1]), int(actual_rgb.shape[0])]
        if image.get("sha256") != actual_hash:
            raise SystemExit(f"{label} metadata image SHA-256 does not match PNG")
        if image.get("dimensions") != expected_dimensions:
            raise SystemExit(f"{label} metadata dimensions do not match PNG")
        if label == "candidate" and "readback" in image:
            readback = image["readback"]
            expected_background = ("rgb(0, 0, 0)" if metadata["theme"] in
                                   ("dark", True) else "rgb(255, 255, 255)")
            mode = readback.get("mode") if isinstance(readback, dict) else None
            valid_background = (
                readback.get("background") == expected_background
                if mode == "displayed-background-composite" else
                readback.get("background") is None if mode == "raw" else False)
            if (not isinstance(readback, dict) or
                    mode not in ("raw", "displayed-background-composite") or
                    not valid_background or
                    readback.get("width") != expected_dimensions[0] or
                    readback.get("height") != expected_dimensions[1]):
                raise SystemExit(
                    "candidate image readback has an invalid mode, theme background, or size")
            if mode == "displayed-background-composite":
                try:
                    with Image.open(actual_path) as captured_image:
                        alpha = captured_image.convert("RGBA").getchannel("A")
                        if alpha.getextrema() != (255, 255):
                            raise SystemExit(
                                "composited candidate PNG contains transparent pixels")
                except OSError as error:
                    raise SystemExit(f"could not inspect candidate PNG alpha: {error}") from error
            candidate_readback = {
                **readback,
                "displayBackground": expected_background,
                "displayCompositeApplied": True,
            }
        elif label == "candidate":
            # Older PNGs did not preserve readback provenance. Alpha is still
            # composited against the manifest theme below, matching display.
            candidate_readback = {
                "mode": "legacy-unrecorded",
                "displayBackground": ("rgb(0, 0, 0)" if metadata["theme"] in
                                       ("dark", True) else "rgb(255, 255, 255)"),
                "displayCompositeApplied": True,
            }
        if not isinstance(metadata["assetHash"], str) or not metadata["assetHash"]:
            raise SystemExit(f"{label} capture metadata has no material asset hash")
        if not isinstance(metadata["materialState"], str) or not metadata["materialState"]:
            raise SystemExit(f"{label} capture metadata has no material settlement state")
        for field in ("boardSeed", "rung", "trial", "elapsedMs"):
            value = metadata[field]
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise SystemExit(f"{label} capture metadata has invalid {field}")
        for field in ("grainSeed", "roll", "pitch", "dpr"):
            value = metadata[field]
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise SystemExit(f"{label} capture metadata has invalid {field}")
        if not 0 <= metadata["grainSeed"] < 4:
            raise SystemExit(f"{label} capture metadata has invalid grainSeed")
        if metadata["dpr"] <= 0:
            raise SystemExit(f"{label} capture metadata has invalid dpr")
        ready_state = (isinstance(metadata.get("sceneState"), dict) and
                       metadata["sceneState"].get("phase") == "ready")
        camera_valid = (metadata["camera"] is None if ready_state else
                        isinstance(metadata["camera"], dict) and bool(metadata["camera"]))
        if not camera_valid:
            raise SystemExit(f"{label} capture metadata has invalid camera")
        viewport = metadata["viewport"]
        if not isinstance(viewport, dict) or any(
                isinstance(viewport.get(field), bool) or
                not isinstance(viewport.get(field), int)
                for field in ("x", "y", "width", "height")):
            raise SystemExit(f"{label} capture metadata has invalid viewport")
        if (viewport["x"] < 0 or viewport["y"] < 0 or
                viewport["width"] <= 0 or viewport["height"] <= 0 or
                viewport["x"] + viewport["width"] > actual_rgb.shape[1] or
                viewport["y"] + viewport["height"] > actual_rgb.shape[0]):
            raise SystemExit(f"{label} capture viewport is outside its PNG")
        if not isinstance(metadata["theme"], (str, bool)):
            raise SystemExit(f"{label} capture metadata has invalid theme")
        if (not isinstance(metadata["assetHash"], str) or
                len(metadata["assetHash"]) != 64 or
                any(char not in "0123456789abcdef" for char in metadata["assetHash"].lower())):
            raise SystemExit(f"{label} capture metadata has invalid assetHash")
    camera_delta, camera_mismatches = camera_difference(
        reference["camera"], candidate["camera"])
    mismatched = [field for field in SYNC_FIELDS
                  if field not in ("camera", "boardGeometry") and
                  reference[field] != candidate[field]]
    if reference.get("resizeReplay") != candidate.get("resizeReplay"):
        mismatched.append("resizeReplay")
    mismatched.extend(board_geometry_mismatches(
        reference["boardGeometry"], candidate["boardGeometry"]))
    if camera_mismatches:
        mismatched.append("camera")
    if mismatched:
        details = ", ".join(
            f"{field}: {reference[field]!r} != {candidate[field]!r}"
            for field in mismatched)
        raise SystemExit(f"captures are not synchronized ({details})")
    left_scene, right_scene = reference.get("sceneState"), candidate.get("sceneState")
    if (left_scene is None) != (right_scene is None):
        raise SystemExit("captures are not synchronized (sceneState is present on only one side)")
    if left_scene is not None:
        scene_mismatches = scene_state_mismatches(left_scene, right_scene)
        if scene_mismatches:
            raise SystemExit("captures are not synchronized (sceneState differs: " +
                             ", ".join(scene_mismatches) + ")")
        phase = left_scene.get("phase") if isinstance(left_scene, dict) else None
        outcome = left_scene.get("outcome") if isinstance(left_scene, dict) else None
        timeout = (isinstance(left_scene, dict) and
                   left_scene.get("terminalReason") == "timeout")
        if (not isinstance(left_scene, dict) or
                phase not in ("ready", "rolling", "won", "lost", "done") or
                ("terminalReason" in left_scene and not timeout) or
                (timeout and phase != "lost") or
                (phase == "ready" and (outcome is not None or
                 reference["boardSeed"] != 0 or reference["elapsedMs"] != 0 or
                 left_scene.get("marbles") != [])) or
                (phase == "rolling" and outcome is not None) or
                (phase in ("won", "lost") and outcome != phase) or
                (phase == "done" and outcome not in ("won", "lost")) or
                left_scene.get("elapsedMs") != reference["elapsedMs"] or
                left_scene.get("roll") != reference["roll"] or
                left_scene.get("pitch") != reference["pitch"] or
                not isinstance(left_scene.get("marbles"), list) or
                (phase != "ready" and not left_scene["marbles"])):
            raise SystemExit("capture sceneState phase/outcome is malformed or unsynchronized")
        marble_states = [marble.get("state") if isinstance(marble, dict) else None
                         for marble in left_scene["marbles"]]
        known_states = {"rolling", "falling", "home", "lost"}
        moving_states = {"rolling", "falling"}
        terminal_states = {"home", "lost"}
        states_consistent = all(state in known_states for state in marble_states)
        if phase == "rolling":
            # Individual marbles can be lost or reach home while the trial continues;
            # only require that at least one marble is still moving.
            states_consistent = (states_consistent and
                                 any(state in moving_states for state in marble_states))
        elif phase == "won":
            states_consistent = states_consistent and all(
                state == "home" for state in marble_states)
        elif phase == "lost" and timeout:
            # Timeout freezes the active board, which can already contain settled
            # or lost marbles alongside the marble(s) that were still moving.
            states_consistent = (states_consistent and
                                 any(state in moving_states for state in marble_states))
        elif phase == "lost":
            states_consistent = (states_consistent and
                                 all(state in terminal_states for state in marble_states) and
                                 any(state == "lost" for state in marble_states))
        elif phase == "done" and outcome == "won":
            states_consistent = states_consistent and all(
                state == "home" for state in marble_states)
        elif phase == "done":
            states_consistent = (states_consistent and
                                 all(state in terminal_states for state in marble_states) and
                                 any(state == "lost" for state in marble_states))
        if not states_consistent:
            raise SystemExit("capture sceneState contains marble states inconsistent with its phase")
    shared_state = {field: reference[field] for field in SYNC_FIELDS}
    if left_scene is not None:
        shared_state["sceneState"] = left_scene
    return {"synchronized": True, "sharedState": shared_state,
        "candidateReadback": candidate_readback,
        "cameraMaxAbsDelta": camera_delta,
        "cameraAbsTolerance": CAMERA_ABS_TOLERANCE}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reference", type=Path,
                        help="native/pyglet reference screenshot")
    parser.add_argument("candidate", type=Path,
                        help="browser/WebGL2 screenshot")
    parser.add_argument("--reference-metadata", type=Path,
                        help="JSON state manifest recorded with the reference")
    parser.add_argument("--candidate-metadata", type=Path,
                        help="JSON state manifest recorded with the candidate")
    parser.add_argument("--require-synchronized", action="store_true",
                        help="require and compare both capture-state manifests")
    parser.add_argument("--require-scene-state", action="store_true",
                        help="require identical scene phase and marble pose in both manifests")
    parser.add_argument("--pixel-threshold", type=float, default=0.0,
                        help="per-channel threshold for the over-limit fraction")
    parser.add_argument("--max-mean-absolute-error", type=float)
    parser.add_argument("--max-rmse", type=float)
    parser.add_argument("--max-pixels-over", type=float,
                        help="maximum fraction of pixels above the threshold")
    parser.add_argument("--json", action="store_true",
                        help="emit one JSON object instead of human-readable output")
    args = parser.parse_args(argv)

    numeric_options = {
        "--pixel-threshold": args.pixel_threshold,
        "--max-mean-absolute-error": args.max_mean_absolute_error,
        "--max-rmse": args.max_rmse,
        "--max-pixels-over": args.max_pixels_over,
    }
    for name, value in numeric_options.items():
        if value is not None and (not math.isfinite(value) or value < 0):
            raise SystemExit(f"{name} must be a finite non-negative number")
    if args.max_pixels_over is not None and args.max_pixels_over > 1:
        raise SystemExit("--max-pixels-over must be between 0 and 1")

    has_reference_metadata = args.reference_metadata is not None
    has_candidate_metadata = args.candidate_metadata is not None
    if has_reference_metadata != has_candidate_metadata:
        raise SystemExit("supply both capture metadata files or neither")
    if args.require_synchronized and not has_reference_metadata:
        raise SystemExit("synchronized acceptance requires both metadata files")
    if args.require_scene_state and not args.require_synchronized:
        raise SystemExit("--require-scene-state also requires --require-synchronized")
    has_limits = any(value is not None for value in (
        args.max_mean_absolute_error, args.max_rmse, args.max_pixels_over))
    if has_limits and not args.require_synchronized:
        raise SystemExit(
            "pixel acceptance limits require --require-synchronized metadata")

    reference_rgb = read_rgb(args.reference)
    candidate_rgb = read_rgb(args.candidate)
    sync = ({"synchronized": False} if not has_reference_metadata else
            load_synchronized_metadata(args.reference_metadata,
                                       args.candidate_metadata,
                                       args.reference, args.candidate,
                                       reference_rgb, candidate_rgb))
    if sync["synchronized"]:
        dark_theme = sync["sharedState"]["theme"] in ("dark", True)
        candidate_rgb = read_rgb(args.candidate,
                                 (0, 0, 0) if dark_theme else (255, 255, 255))
    if args.require_scene_state and not sync["sharedState"].get("sceneState"):
        raise SystemExit("scene acceptance requires sceneState in both metadata files")

    metrics = measure(reference_rgb, candidate_rgb, args.pixel_threshold)
    regions = (region_metrics(reference_rgb, candidate_rgb,
                              sync["sharedState"]["viewport"],
                              args.pixel_threshold)
               if sync["synchronized"] else None)
    failures: list[str] = []
    if (args.max_mean_absolute_error is not None and
            metrics["meanAbsoluteError"] > args.max_mean_absolute_error):
        failures.append(
            f"meanAbsoluteError {metrics['meanAbsoluteError']:.9g} > "
            f"{args.max_mean_absolute_error:.9g}")
    if args.max_rmse is not None and metrics["rmse"] > args.max_rmse:
        failures.append(f"rmse {metrics['rmse']:.9g} > {args.max_rmse:.9g}")
    if (args.max_pixels_over is not None and
            metrics["pixelsOverThresholdFraction"] > args.max_pixels_over):
        failures.append(
            f"pixelsOverThresholdFraction "
            f"{metrics['pixelsOverThresholdFraction']:.9g} > "
            f"{args.max_pixels_over:.9g}")

    acceptance_limits = any(value is not None for value in (
        args.max_mean_absolute_error, args.max_rmse, args.max_pixels_over))
    result = ("fail" if failures else
              "pass" if sync["synchronized"] and acceptance_limits else
              "diagnostic-only")
    if args.json:
        print(json.dumps({**sync, "metrics": metrics, "regions": regions,
                          "failures": failures,
                          "result": result}, sort_keys=True))
    else:
        print(
            f"Marble pair {metrics['width']}x{metrics['height']}: "
            f"exact={metrics['exactPixelFraction']:.6%}, "
            f"MAE={metrics['meanAbsoluteError']:.9g}, "
            f"RMSE={metrics['rmse']:.9g}, "
            f"max={metrics['maximumAbsoluteError']:.9g}, "
            f">{metrics['pixelThreshold']:g}="
            f"{metrics['pixelsOverThresholdFraction']:.6%}")
        if regions is not None:
            stage = regions["stage"]
            chrome = regions["chrome"]
            print("  stage: "
                  f"{stage['width']}x{stage['height']} "
                  f"MAE={stage['meanAbsoluteError']:.9g}, "
                  f">{args.pixel_threshold:g}="
                  f"{stage['pixelsOverThresholdFraction']:.6%}")
            print("  surrounding chrome: "
                  f"{chrome['pixelCount']} pixels "
                  f"MAE={chrome['meanAbsoluteError']:.9g}, "
                  f">{args.pixel_threshold:g}="
                  f"{chrome['pixelsOverThresholdFraction']:.6%}")
            for name in ("header", "footer", "stageSideMargins"):
                region = regions[name]
                mae = ("n/a" if region["meanAbsoluteError"] is None else
                       f"{region['meanAbsoluteError']:.9g}")
                print(f"  {name}: {region['pixelCount']} pixels MAE={mae}")
        if failures:
            for failure in failures:
                print(f"FAIL: {failure}")
        elif sync["synchronized"] and acceptance_limits:
            print("PASS: Marble screenshot pair stays within requested diagnostic limits")
        elif sync["synchronized"]:
            print("SYNC VERIFIED; pixel metrics are diagnostic only because "
                  "no acceptance limits were configured")
        else:
            print("DIAGNOSTIC ONLY: screenshot pair has no synchronization metadata; "
                  "pixel metrics are not fidelity acceptance")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
