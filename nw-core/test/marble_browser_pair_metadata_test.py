#!/usr/bin/env python3
"""Ensure browser screenshot manifests attest live browser state."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile

from PIL import Image


TEST_DIR = Path(__file__).resolve().parent
HELPER = TEST_DIR / "marble_browser_pair_metadata.py"


def fixture() -> tuple[dict, dict]:
    marble = {
        "x": 0.1, "y": 0.2, "z": 0.0075,
        "vx": 0.0, "vy": 0.0, "vz": 0.0,
        "wx": 0.0, "wy": 0.0, "wz": 0.0,
        "qw": 1.0, "qx": 0.0, "qy": 0.0, "qz": 0.0,
        "state": "lost",
    }
    camera = {"eye": [0, 1, 2], "viewProj": [0.0] * 16, "aspect": 1.0}
    scene = {
        "version": 1, "phase": "lost", "outcome": "lost",
        "elapsedMs": 17, "roll": 0.0, "pitch": 0.0,
        "marbles": [marble],
    }
    source = {
        "captureComplete": True, "assetHash": "a" * 64,
        "boardSeed": 7, "grainSeed": 0.5, "rung": 1, "trial": 0,
        "elapsedMs": 17, "secondsPerTray": 45, "roll": 0.0, "pitch": 0.0,
        "statusText": "Down a hole — 0 of 1 home     tray 1/1   home 0/1   45s left   tilt 0°/0°",
        "boardGeometry": {
            "rung": 1, "cols": 2, "rows": 2, "width": 1.0, "depth": 1.0,
            "cell": 0.25, "thickness": 0.01, "height": 0.03,
            "walls": [{"x0": 0.1, "y0": 0.2, "x1": 0.3, "y1": 0.4}],
            "holes": [{"x": 0.7, "y": 0.8, "radius": 0.04, "home": False}],
            "starts": [{"x": 0.1, "y": 0.2}],
            "home": {"x": 0.7, "y": 0.8, "radius": 0.04},
        },
        "camera": camera, "viewport": {"x": 0, "y": 0, "width": 4, "height": 4},
        "dpr": 1.0, "theme": "light", "materialState": "settled:3-of-3",
        "sourceWindow": {
            "points": [4, 4], "layoutPixels": [4, 4],
            "framebuffer": [4, 4], "scale": 1.0,
        },
        "sceneState": scene, "image": {"dimensions": [4, 4], "sha256": "unused"},
    }
    browser = {
        "state": [2, 1, 1, 1, 1, 7, 17, 44983, 0, 0, 0, 0, 0],
        # A lost marble starts a short feedback timer. It must not be mistaken
        # for the configured 45-second tray budget.
        "secondsPerTray": 45,
        "board": {
            "rung": 1, "seed": 7, **source["boardGeometry"],
        },
        "grainSeed": 0.5, "roll": 0.0, "pitch": 0.0, "elapsed": 0.017,
        "statusText": source["statusText"],
        "marbles": [dict(marble)],
        "capture": {
            "camera": camera, "viewport": source["viewport"],
            "framebuffer": {"width": 4, "height": 4}, "dpr": 1.0,
            "dark": False, "materialState": "settled:3-of-3", "sampleCount": 4,
            "readback": {"mode": "displayed-background-composite",
                         "background": "rgb(255, 255, 255)",
                         "width": 4, "height": 4},
        },
    }
    return source, browser


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="marble-pair-metadata-") as folder:
        root = Path(folder)
        source, browser = fixture()
        source_path = root / "source.json"
        debug_path = root / "browser.json"
        png_path = root / "browser.png"
        output_path = root / "candidate.json"
        source_path.write_text(json.dumps(source))
        debug_path.write_text(json.dumps(browser))
        Image.new("RGB", (4, 4), "white").save(png_path)

        command = [sys.executable, str(HELPER), "--source-metadata", str(source_path),
                   "--png", str(png_path), "--browser-debug-json", "@browser",
                   "--output", str(output_path)]

        def run(debug: dict) -> subprocess.CompletedProcess[str]:
            debug_path.write_text(json.dumps(debug))
            actual = [str(debug_path) if item == "@browser" else item for item in command]
            return subprocess.run(actual, check=False, capture_output=True, text=True)

        valid = run(browser)
        assert valid.returncode == 0, valid.stderr
        candidate = json.loads(output_path.read_text())
        assert candidate["sceneState"] == source["sceneState"]
        assert candidate["camera"] == browser["capture"]["camera"]
        assert candidate["secondsPerTray"] == source["secondsPerTray"]
        assert candidate["statusText"] == source["statusText"]
        assert candidate["boardGeometry"] == source["boardGeometry"]
        assert candidate["sampleCount"] == 4
        assert candidate["image"]["readback"]["mode"] == "displayed-background-composite"
        Image.new("RGBA", (4, 4), (0, 0, 0, 0)).save(png_path)
        rejected_transparent_composite = run(browser)
        assert rejected_transparent_composite.returncode != 0
        assert "not fully opaque" in rejected_transparent_composite.stderr
        Image.new("RGB", (4, 4), "white").save(png_path)
        raw_readback = json.loads(json.dumps(browser))
        raw_readback["capture"]["readback"]["mode"] = "raw"
        rejected_raw_readback = run(raw_readback)
        assert rejected_raw_readback.returncode != 0
        assert "displayed-background composite" in rejected_raw_readback.stderr
        wrong_background = json.loads(json.dumps(browser))
        wrong_background["capture"]["readback"]["background"] = "rgb(0, 0, 0)"
        rejected_background = run(wrong_background)
        assert rejected_background.returncode != 0
        assert "displayed-background composite" in rejected_background.stderr
        wrong_controller_seed = json.loads(json.dumps(browser))
        wrong_controller_seed["state"][5] = 8
        rejected_seed = run(wrong_controller_seed)
        assert rejected_seed.returncode != 0
        assert "controller seed differs" in rejected_seed.stderr
        for invalid_value in (2.5, True, "2", 2**53):
            malformed = json.loads(json.dumps(browser))
            malformed["state"][0] = invalid_value
            rejected = run(malformed)
            assert rejected.returncode != 0
            assert "exact safe integers" in rejected.stderr
        wrong_samples = json.loads(json.dumps(browser))
        wrong_samples["capture"]["sampleCount"] = 2
        rejected_samples = run(wrong_samples)
        assert rejected_samples.returncode != 0
        assert "four samples" in rejected_samples.stderr

        # Native and WASM MuJoCo differ by a few 1e-8 in integrated angular
        # velocity; tolerate that measured precision delta but reject larger
        # physical-state divergence.
        quantization_delta = json.loads(json.dumps(browser))
        quantization_delta["marbles"][0]["wy"] = 5e-8
        assert run(quantization_delta).returncode == 0
        divergent_state = json.loads(json.dumps(browser))
        divergent_state["marbles"][0]["wy"] = 2e-7
        assert run(divergent_state).returncode != 0

        wrong_status = json.loads(json.dumps(browser))
        wrong_status["statusText"] = "Marbles back at the start     tray 1/1"
        rejected_status = run(wrong_status)
        assert rejected_status.returncode != 0
        assert "status text differs" in rejected_status.stderr

        # A multi-marble run can remain in the rolling phase after one ball
        # is lost while another is still moving. That is a valid physical
        # state, not a terminal-phase inconsistency.
        mixed_source = json.loads(json.dumps(source))
        mixed_browser = json.loads(json.dumps(browser))
        mixed_marble = dict(source["sceneState"]["marbles"][0],
                            x=0.11, state="rolling")
        mixed_source["sceneState"].update({"phase": "rolling", "outcome": None})
        mixed_source["sceneState"]["marbles"].append(dict(mixed_marble))
        mixed_source["boardGeometry"]["starts"].append({"x": 0.11, "y": 0.2})
        mixed_browser["state"][0] = 1
        mixed_browser["marbles"].append(dict(mixed_marble))
        mixed_browser["board"]["starts"].append({"x": 0.11, "y": 0.2})
        source_path.write_text(json.dumps(mixed_source))
        accepted_mixed_terminal = run(mixed_browser)
        assert accepted_mixed_terminal.returncode == 0, accepted_mixed_terminal.stderr

        no_moving_source = json.loads(json.dumps(mixed_source))
        no_moving_browser = json.loads(json.dumps(mixed_browser))
        no_moving_source["sceneState"]["marbles"][1]["state"] = "lost"
        no_moving_browser["marbles"][1]["state"] = "lost"
        source_path.write_text(json.dumps(no_moving_source))
        rejected_stale_rolling = run(no_moving_browser)
        assert rejected_stale_rolling.returncode != 0
        assert "rolling phase has no moving marble" in rejected_stale_rolling.stderr
        source_path.write_text(json.dumps(source))

        # Geometry is transported as Float32, so accept precisely that encoding
        # of the source double and reject any neighboring representable value.
        quantized_source = json.loads(json.dumps(source))
        quantized_source["boardGeometry"]["width"] = 1.1
        quantized_source["boardGeometry"]["walls"][0]["x0"] = 0.1
        quantized_browser = json.loads(json.dumps(browser))
        quantized_browser["board"]["width"] = 1.100000023841858
        quantized_browser["board"]["walls"][0]["x0"] = 0.10000000149011612
        source_path.write_text(json.dumps(quantized_source))
        accepted_geometry_abi = run(quantized_browser)
        assert accepted_geometry_abi.returncode == 0, accepted_geometry_abi.stderr
        wrong_geometry = json.loads(json.dumps(quantized_browser))
        wrong_geometry["board"]["walls"][0]["x0"] += 1e-8
        rejected_geometry = run(wrong_geometry)
        assert rejected_geometry.returncode != 0
        assert "board geometry differs" in rejected_geometry.stderr
        wrong_dimension = json.loads(json.dumps(quantized_browser))
        wrong_dimension["board"]["width"] += 0.001
        rejected_dimension = run(wrong_dimension)
        assert rejected_dimension.returncode != 0
        assert "board geometry differs" in rejected_dimension.stderr
        missing_wall = json.loads(json.dumps(quantized_browser))
        missing_wall["board"]["walls"].clear()
        rejected_topology = run(missing_wall)
        assert rejected_topology.returncode != 0
        assert "board geometry differs" in rejected_topology.stderr
        source_path.write_text(json.dumps(source))

        wrong_duration = json.loads(json.dumps(browser))
        wrong_duration["secondsPerTray"] = 44
        rejected_duration = run(wrong_duration)
        assert rejected_duration.returncode != 0
        assert "seconds-per-tray differs" in rejected_duration.stderr

        early_loss = json.loads(json.dumps(browser))
        early_loss["state"][7] = 2585
        accepted_early_terminal = run(early_loss)
        assert accepted_early_terminal.returncode == 0, accepted_early_terminal.stderr
        assert json.loads(output_path.read_text())["secondsPerTray"] == 45

        # While still running, the 60-Hz physics clock retains fractional
        # milliseconds and the controller stores their whole-millisecond
        # floor. Model a real in-progress phase here (terminal physical
        # captures synchronize to rounded settlement time instead).
        running_source = json.loads(json.dumps(source))
        running_source["statusText"] = "Marble rolling"
        running_source["sceneState"].update({"phase": "rolling", "outcome": None,
                                              "elapsedMs": 17})
        running_source["sceneState"]["marbles"][0]["state"] = "rolling"
        first_fractional_frame = json.loads(json.dumps(browser))
        first_fractional_frame["statusText"] = "Marble rolling"
        first_fractional_frame["state"][0] = 1
        first_fractional_frame["state"][6] = 16
        first_fractional_frame["state"][7] = 44984
        first_fractional_frame["state"][8] = -1
        first_fractional_frame["state"][10] = 0
        first_fractional_frame["elapsed"] = 1 / 60
        first_fractional_frame["marbles"][0]["state"] = "rolling"
        source_path.write_text(json.dumps(running_source))
        accepted_fractional_frame = run(first_fractional_frame)
        assert accepted_fractional_frame.returncode == 0, accepted_fractional_frame.stderr
        fractional_manifest = json.loads(output_path.read_text())
        assert fractional_manifest["elapsedMs"] == 17
        assert fractional_manifest["controllerElapsedMs"] == 16
        ahead_controller_clock = json.loads(json.dumps(first_fractional_frame))
        ahead_controller_clock["state"][6] = 17
        rejected_ahead_clock = run(ahead_controller_clock)
        assert rejected_ahead_clock.returncode != 0
        assert "active-play clock" in rejected_ahead_clock.stderr
        source_path.write_text(json.dumps(source))

        # A physically settled loss synchronizes the common controller to
        # the nearest millisecond before committing its result. The source
        # and physics clocks round 25/60 s to 417 ms, so the controller must
        # also report 417 rather than the active-play floor of 416.
        partial_tick_source = json.loads(json.dumps(source))
        partial_tick_source["elapsedMs"] = 417
        partial_tick_source["sceneState"]["elapsedMs"] = 417
        partial_tick_browser = json.loads(json.dumps(browser))
        partial_tick_browser["state"][6] = 417
        partial_tick_browser["state"][7] = 2585
        partial_tick_browser["elapsed"] = 25 / 60
        source_path.write_text(json.dumps(partial_tick_source))
        accepted_partial_tick = run(partial_tick_browser)
        assert accepted_partial_tick.returncode == 0, accepted_partial_tick.stderr
        partial_tick_manifest = json.loads(output_path.read_text())
        assert partial_tick_manifest["elapsedMs"] == 417
        assert partial_tick_manifest["controllerElapsedMs"] == 417
        stale_settlement_clock = json.loads(json.dumps(partial_tick_browser))
        stale_settlement_clock["state"][6] = 416
        rejected_stale_settlement_clock = run(stale_settlement_clock)
        assert rejected_stale_settlement_clock.returncode != 0
        assert "physical-settlement clock" in rejected_stale_settlement_clock.stderr
        source_path.write_text(json.dumps(source))

        mislabeled_points = json.loads(json.dumps(source))
        mislabeled_points["sourceWindow"]["points"] = [8, 4]
        source_path.write_text(json.dumps(mislabeled_points))
        rejected_window_units = run(browser)
        assert rejected_window_units.returncode != 0
        assert "points/layoutPixels disagree" in rejected_window_units.stderr

        source_path.write_text(json.dumps(source))
        bad_window_framebuffer = json.loads(json.dumps(source))
        bad_window_framebuffer["sourceWindow"]["framebuffer"] = [8, 4]
        source_path.write_text(json.dumps(bad_window_framebuffer))
        rejected_framebuffer = run(browser)
        assert rejected_framebuffer.returncode != 0
        assert "framebuffer differs from captured image" in rejected_framebuffer.stderr
        source_path.write_text(json.dumps(source))

        abi_quantized = json.loads(json.dumps(browser))
        abi_quantized["marbles"][0]["x"] += 5e-9
        accepted_quantization = run(abi_quantized)
        assert accepted_quantization.returncode == 0, accepted_quantization.stderr
        excessive_quantization = json.loads(json.dumps(browser))
        excessive_quantization["marbles"][0]["x"] += 2e-8
        rejected_quantization = run(excessive_quantization)
        assert rejected_quantization.returncode != 0
        assert "marble[0].x differs" in rejected_quantization.stderr

        binary32_source = json.loads(json.dumps(source))
        binary32_source["sceneState"]["marbles"][0]["x"] = 0.3765
        binary32_browser = json.loads(json.dumps(browser))
        binary32_browser["marbles"][0]["x"] = 0.3765000104904175
        source_path.write_text(json.dumps(binary32_source))
        exact_binary32 = run(binary32_browser)
        assert exact_binary32.returncode == 0, exact_binary32.stderr
        non_binary32 = json.loads(json.dumps(binary32_browser))
        non_binary32["marbles"][0]["x"] += 1e-9
        rejected_non_binary32 = run(non_binary32)
        assert rejected_non_binary32.returncode != 0
        assert "marble[0].x differs" in rejected_non_binary32.stderr
        source_path.write_text(json.dumps(source))

        timeout_source = json.loads(json.dumps(source))
        timeout_source["elapsedMs"] = 45000
        timeout_source["sceneState"].update({
            "phase": "lost", "outcome": "lost", "terminalReason": "timeout",
            "elapsedMs": 45000,
        })
        timeout_source["sceneState"]["marbles"][0]["state"] = "rolling"
        timeout_browser = json.loads(json.dumps(browser))
        timeout_browser["state"][6] = 45000
        timeout_browser["state"][7] = 0
        timeout_browser["elapsed"] = 45.0
        timeout_browser["terminalReason"] = "timeout"
        timeout_browser["marbles"][0]["state"] = "rolling"
        source_path.write_text(json.dumps(timeout_source))
        valid_timeout = run(timeout_browser)
        assert valid_timeout.returncode == 0, valid_timeout.stderr
        timeout_candidate = json.loads(output_path.read_text())
        assert timeout_candidate["sceneState"]["terminalReason"] == "timeout"
        false_physical_timeout = json.loads(json.dumps(timeout_browser))
        false_physical_timeout["terminalReason"] = None
        rejected_timeout_reason = run(false_physical_timeout)
        assert rejected_timeout_reason.returncode != 0
        assert "timeout reason" in rejected_timeout_reason.stderr

        ready_source = json.loads(json.dumps(source))
        ready_source.update({"boardSeed": 0, "grainSeed": 0.0, "elapsedMs": 0,
                             "secondsPerTray": 0,
                             "statusText": None,
                             "camera": None, "materialState": "not-created:no-board",
                             "boardGeometry": None})
        ready_source["sceneState"] = {
            "version": 1, "phase": "ready", "outcome": None, "elapsedMs": 0,
            "roll": 0.0, "pitch": 0.0, "marbles": [],
        }
        ready_browser = {
            "state": [0, 1, 0, 1, 1, 0, 0, 45000, -1, 0, 0, 0],
            "secondsPerTray": 0,
            "board": None, "grainSeed": 0, "roll": 0, "pitch": 0,
            "elapsed": 0, "marbles": [],
            "capture": {
                "camera": None, "viewport": ready_source["viewport"],
                "framebuffer": {"width": 4, "height": 4}, "dpr": 1.0,
                "dark": False, "materialState": "not-created:no-board",
                "sampleCount": None,
                "readback": {"mode": "displayed-background-composite",
                             "background": "rgb(255, 255, 255)",
                             "width": 4, "height": 4},
            },
        }
        source_path.write_text(json.dumps(ready_source))
        valid_ready = run(ready_browser)
        assert valid_ready.returncode == 0, valid_ready.stderr
        candidate_ready = json.loads(output_path.read_text())
        assert candidate_ready["sceneState"] == ready_source["sceneState"]
        assert candidate_ready["boardSeed"] == 0 and candidate_ready["camera"] is None
        invalid_ready = json.loads(json.dumps(ready_browser))
        invalid_ready["state"][2] = 1
        rejected_ready_trial = run(invalid_ready)
        assert rejected_ready_trial.returncode != 0
        assert "READY state" in rejected_ready_trial.stderr

        source_path.write_text(json.dumps(source))

        wrong_pose = json.loads(json.dumps(browser))
        wrong_pose["marbles"][0]["x"] += 0.01
        rejected_pose = run(wrong_pose)
        assert rejected_pose.returncode != 0
        assert "marble[0].x differs" in rejected_pose.stderr

        wrong_phase = json.loads(json.dumps(browser))
        wrong_phase["state"][0] = 1
        rejected_phase = run(wrong_phase)
        assert rejected_phase.returncode != 0
        assert "controller phase" in rejected_phase.stderr

    print("PASS: browser Marble screenshot manifest verifies live phase, pose, and renderer state")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
