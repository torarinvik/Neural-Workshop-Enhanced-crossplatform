"""Guard the synchronized-capture requirement of the Marble image comparator."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image

COMPARATOR = Path(__file__).with_name("marble_render_pair_test.py")
SYNC_FIELDS = (
    "boardSeed", "grainSeed", "rung", "trial", "elapsedMs", "secondsPerTray", "roll",
    "pitch", "camera", "viewport", "dpr", "theme", "assetHash",
    "materialState", "boardGeometry",
)


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="marble-pair-contract-") as temp:
        root = Path(temp)
        reference = root / "reference.png"
        candidate = root / "candidate.png"
        Image.new("RGB", (2, 2), "white").save(reference)
        Image.new("RGB", (2, 2), "white").save(candidate)
        image_binding = {"sha256": hashlib.sha256(reference.read_bytes()).hexdigest(),
                         "dimensions": [2, 2]}
        candidate_image_binding = {
            "sha256": hashlib.sha256(candidate.read_bytes()).hexdigest(),
            "dimensions": [2, 2],
            "readback": {"mode": "displayed-background-composite",
                         "background": "rgb(255, 255, 255)",
                         "width": 2, "height": 2},
        }
        reference_meta = root / "reference.json"
        candidate_meta = root / "candidate.json"
        shared = {"boardSeed": 17, "grainSeed": 2, "rung": 1,
                       "trial": 0, "elapsedMs": 0, "secondsPerTray": 15, "roll": 0.0,
                       "pitch": 0.0, "camera": {"aspect": 2.0,
                         "eye": [0.0, 1.0, 2.0],
                         "viewProj": [float(value) for value in range(16)]},
                       "viewport": {"x": 0, "y": 0, "width": 1, "height": 1},
                       "dpr": 1.0, "theme": "light", "captureComplete": True,
                       "assetHash": "a" * 64,
                       "materialState": "settled:3-of-3",
                       "resizeReplay": None,
                       "boardGeometry": {
                         "width": 1.1,
                         "walls": [{"x0": 0.1, "y0": 0.2,
                                    "x1": 0.3, "y1": 0.4}],
                         "holes": [{"x": 0.7, "y": 0.8,
                                    "radius": 0.04, "home": False}],
                       },
                       "image": image_binding}

        def save_pair(left: dict, right: dict) -> None:
            reference_meta.write_text(json.dumps(left))
            if right.get("image") == image_binding:
                right = {**right, "image": candidate_image_binding}
            candidate_meta.write_text(json.dumps(right))

        def run(*arguments: str) -> subprocess.CompletedProcess[str]:
            return subprocess.run(
                [sys.executable, str(COMPARATOR), str(reference), str(candidate),
                 *arguments], text=True, capture_output=True, check=False)

        no_manifest = run("--max-rmse", "1")
        assert no_manifest.returncode != 0
        assert "require --require-synchronized" in no_manifest.stderr

        save_pair(shared, {**shared, "elapsedMs": 5})
        mismatch = run("--reference-metadata", str(reference_meta),
                       "--candidate-metadata", str(candidate_meta),
                       "--require-synchronized")
        assert mismatch.returncode != 0
        assert "not synchronized" in mismatch.stderr

        save_pair(shared, {**shared, "secondsPerTray": 30})
        mismatched_duration = run(
            "--reference-metadata", str(reference_meta),
            "--candidate-metadata", str(candidate_meta),
            "--require-synchronized")
        assert mismatched_duration.returncode != 0
        assert "not synchronized" in mismatched_duration.stderr

        resize_reference = {**shared, "resizeReplay": {
            "initialPoints": [912, 684], "finalPoints": [800, 600]}}
        resize_candidate = {**resize_reference, "resizeReplay": {
            "initialPoints": [912, 684], "finalPoints": [800, 601]}}
        save_pair(resize_reference, resize_candidate)
        mismatched_resize = run(
            "--reference-metadata", str(reference_meta),
            "--candidate-metadata", str(candidate_meta),
            "--require-synchronized")
        assert mismatched_resize.returncode != 0
        assert "resizeReplay:" in mismatched_resize.stderr

        abi_geometry = {**shared, "boardGeometry": {
            "width": 1.100000023841858,
            "walls": [{"x0": 0.10000000149011612, "y0": 0.2,
                       "x1": 0.3, "y1": 0.4}],
            "holes": shared["boardGeometry"]["holes"],
        }}
        save_pair(shared, abi_geometry)
        geometry_abi_pass = run(
            "--reference-metadata", str(reference_meta),
            "--candidate-metadata", str(candidate_meta),
            "--require-synchronized")
        assert geometry_abi_pass.returncode == 0, geometry_abi_pass.stderr
        wrong_wall = json.loads(json.dumps(abi_geometry))
        wrong_wall["boardGeometry"]["walls"][0]["x0"] += 1e-8
        save_pair(shared, wrong_wall)
        geometry_mismatch = run(
            "--reference-metadata", str(reference_meta),
            "--candidate-metadata", str(candidate_meta),
            "--require-synchronized")
        assert geometry_mismatch.returncode != 0
        assert "boardGeometry.walls[0].x0" in geometry_mismatch.stderr

        outside_viewport = {**shared, "viewport": {
            "x": 2, "y": 0, "width": 1, "height": 1}}
        save_pair(outside_viewport, outside_viewport)
        invalid_viewport = run(
            "--reference-metadata", str(reference_meta),
            "--candidate-metadata", str(candidate_meta),
            "--require-synchronized")
        assert invalid_viewport.returncode != 0
        assert "viewport is outside its PNG" in invalid_viewport.stderr

        save_pair(shared, {**shared, "image": {
            "sha256": hashlib.sha256(candidate.read_bytes()).hexdigest(),
            "dimensions": [2, 2]}})

        save_pair(shared, shared)
        slightly_different_camera = {**shared, "camera": {
            **shared["camera"],
            "viewProj": [5e-8, *shared["camera"]["viewProj"][1:]]}}
        save_pair(shared, slightly_different_camera)
        synchronized = run(
            "--reference-metadata", str(reference_meta),
            "--candidate-metadata", str(candidate_meta),
            "--require-synchronized", "--max-rmse", "0")
        assert synchronized.returncode == 0, synchronized.stderr
        assert "PASS: Marble screenshot pair" in synchronized.stdout
        result = json.loads(run(
            "--reference-metadata", str(reference_meta),
            "--candidate-metadata", str(candidate_meta),
            "--require-synchronized", "--json").stdout)
        assert result["regions"]["stage"]["width"] == 1
        assert result["regions"]["stage"]["height"] == 1
        assert result["regions"]["chrome"]["pixelCount"] == 3
        assert sum(result["regions"][name]["pixelCount"] for name in
                   ("header", "footer", "stageSideMargins")) == 3

        Image.new("RGBA", (2, 2), (0, 0, 0, 0)).save(candidate)
        transparent = {**shared, "image": {
            "sha256": hashlib.sha256(candidate.read_bytes()).hexdigest(),
            "dimensions": [2, 2],
            "readback": {"mode": "raw", "background": None,
                         "width": 2, "height": 2},
        }}
        save_pair(shared, transparent)
        transparent_capture = run(
            "--reference-metadata", str(reference_meta),
            "--candidate-metadata", str(candidate_meta),
            "--require-synchronized", "--max-rmse", "0", "--json")
        assert transparent_capture.returncode == 0, transparent_capture.stderr
        transparent_result = json.loads(transparent_capture.stdout)
        assert transparent_result["metrics"]["meanAbsoluteError"] == 0
        assert transparent_result["candidateReadback"]["mode"] == "raw"
        wrong_background = {**shared, "image": {
            "sha256": hashlib.sha256(candidate.read_bytes()).hexdigest(),
            "dimensions": [2, 2],
            "readback": {**candidate_image_binding["readback"],
                         "background": "rgb(0, 0, 0)"},
        }}
        save_pair(shared, wrong_background)
        rejected_background = run(
            "--reference-metadata", str(reference_meta),
            "--candidate-metadata", str(candidate_meta),
            "--require-synchronized")
        assert rejected_background.returncode != 0
        assert "theme background" in rejected_background.stderr
        Image.new("RGB", (2, 2), "white").save(candidate)
        candidate_image_binding["sha256"] = hashlib.sha256(candidate.read_bytes()).hexdigest()
        save_pair(shared, shared)

        state_only = run("--reference-metadata", str(reference_meta),
                         "--candidate-metadata", str(candidate_meta),
                         "--require-synchronized")
        assert state_only.returncode == 0
        assert "SYNC VERIFIED" in state_only.stdout
        assert "PASS:" not in state_only.stdout

        missing_scene_state = run(
            "--reference-metadata", str(reference_meta),
            "--candidate-metadata", str(candidate_meta),
            "--require-synchronized", "--require-scene-state")
        assert missing_scene_state.returncode != 0
        assert "requires sceneState" in missing_scene_state.stderr

        rolling_state = {"phase": "rolling", "outcome": None, "elapsedMs": 0,
                         "roll": 0.0, "pitch": 0.0,
                         "marbles": [{"x": 0.1, "y": 0.2, "z": 0.01,
                                      "vx": 0.0, "vy": 0.0, "vz": 0.0,
                                      "wx": 0.0, "wy": 0.0, "wz": 0.0,
                                      "qw": 1.0, "qx": 0.0, "qy": 0.0,
                                      "qz": 0.0, "state": "rolling"}]}
        save_pair({**shared, "sceneState": rolling_state},
                  {**shared, "sceneState": rolling_state})
        scene_state_pass = run(
            "--reference-metadata", str(reference_meta),
            "--candidate-metadata", str(candidate_meta),
            "--require-synchronized", "--require-scene-state")
        assert scene_state_pass.returncode == 0, scene_state_pass.stderr
        mixed_rolling_state = {**rolling_state, "marbles": [
            {**rolling_state["marbles"][0], "state": "lost"},
            {**rolling_state["marbles"][0], "state": "rolling"},
        ]}
        save_pair({**shared, "sceneState": mixed_rolling_state},
                  {**shared, "sceneState": mixed_rolling_state})
        mixed_rolling_pass = run(
            "--reference-metadata", str(reference_meta),
            "--candidate-metadata", str(candidate_meta),
            "--require-synchronized", "--require-scene-state")
        assert mixed_rolling_pass.returncode == 0, mixed_rolling_pass.stderr
        all_terminal_rolling = {**rolling_state, "marbles": [
            {**rolling_state["marbles"][0], "state": "lost"},
            {**rolling_state["marbles"][0], "state": "home"},
        ]}
        save_pair({**shared, "sceneState": all_terminal_rolling},
                  {**shared, "sceneState": all_terminal_rolling})
        all_terminal_rolling_reject = run(
            "--reference-metadata", str(reference_meta),
            "--candidate-metadata", str(candidate_meta),
            "--require-synchronized", "--require-scene-state")
        assert all_terminal_rolling_reject.returncode != 0
        assert "inconsistent with its phase" in all_terminal_rolling_reject.stderr
        quantized_state = {**rolling_state,
                           "marbles": [{**rolling_state["marbles"][0],
                                        "x": rolling_state["marbles"][0]["x"] + 5e-9}]}
        save_pair({**shared, "sceneState": rolling_state},
                  {**shared, "sceneState": quantized_state})
        abi_quantization_pass = run(
            "--reference-metadata", str(reference_meta),
            "--candidate-metadata", str(candidate_meta),
            "--require-synchronized", "--require-scene-state")
        assert abi_quantization_pass.returncode == 0, abi_quantization_pass.stderr
        velocity_precision_state = {**rolling_state,
                                    "marbles": [{**rolling_state["marbles"][0],
                                                 "wy": 5e-8}]}
        save_pair({**shared, "sceneState": rolling_state},
                  {**shared, "sceneState": velocity_precision_state})
        velocity_precision_pass = run(
            "--reference-metadata", str(reference_meta),
            "--candidate-metadata", str(candidate_meta),
            "--require-synchronized", "--require-scene-state")
        assert velocity_precision_pass.returncode == 0, velocity_precision_pass.stderr
        binary32_source = {**rolling_state,
                           "marbles": [{**rolling_state["marbles"][0], "x": 0.3765}]}
        binary32_candidate = {**rolling_state,
                              "marbles": [{**rolling_state["marbles"][0],
                                           "x": 0.3765000104904175}]}
        save_pair({**shared, "sceneState": binary32_source},
                  {**shared, "sceneState": binary32_candidate})
        exact_binary32_pass = run(
            "--reference-metadata", str(reference_meta),
            "--candidate-metadata", str(candidate_meta),
            "--require-synchronized", "--require-scene-state")
        assert exact_binary32_pass.returncode == 0, exact_binary32_pass.stderr
        non_binary32_candidate = {**rolling_state,
                                  "marbles": [{**rolling_state["marbles"][0],
                                               "x": 0.3765000114904175}]}
        save_pair({**shared, "sceneState": binary32_source},
                  {**shared, "sceneState": non_binary32_candidate})
        non_binary32_reject = run(
            "--reference-metadata", str(reference_meta),
            "--candidate-metadata", str(candidate_meta),
            "--require-synchronized", "--require-scene-state")
        assert non_binary32_reject.returncode != 0
        assert "sceneState differs" in non_binary32_reject.stderr
        out_of_tolerance_state = {**rolling_state,
                                  "marbles": [{**rolling_state["marbles"][0],
                                               "x": rolling_state["marbles"][0]["x"] + 2e-8}]}
        save_pair({**shared, "sceneState": rolling_state},
                  {**shared, "sceneState": out_of_tolerance_state})
        abi_quantization_reject = run(
            "--reference-metadata", str(reference_meta),
            "--candidate-metadata", str(candidate_meta),
            "--require-synchronized", "--require-scene-state")
        assert abi_quantization_reject.returncode != 0
        assert "sceneState differs" in abi_quantization_reject.stderr
        divergent_velocity_state = {**rolling_state,
                                    "marbles": [{**rolling_state["marbles"][0],
                                                 "wy": 2e-7}]}
        save_pair({**shared, "sceneState": rolling_state},
                  {**shared, "sceneState": divergent_velocity_state})
        divergent_velocity_reject = run(
            "--reference-metadata", str(reference_meta),
            "--candidate-metadata", str(candidate_meta),
            "--require-synchronized", "--require-scene-state")
        assert divergent_velocity_reject.returncode != 0
        assert "sceneState differs" in divergent_velocity_reject.stderr
        ready_state = {"phase": "ready", "outcome": None, "elapsedMs": 0,
                       "roll": 0.0, "pitch": 0.0, "marbles": []}
        ready_meta = {**shared, "boardSeed": 0, "grainSeed": 0.0,
                      "camera": None, "materialState": "not-created:no-board",
                      "boardGeometry": None,
                      "sceneState": ready_state}
        save_pair(ready_meta, ready_meta)
        ready_pass = run(
            "--reference-metadata", str(reference_meta),
            "--candidate-metadata", str(candidate_meta),
            "--require-synchronized", "--require-scene-state")
        assert ready_pass.returncode == 0, ready_pass.stderr
        ready_without_scene = run(
            "--reference-metadata", str(reference_meta),
            "--candidate-metadata", str(candidate_meta),
            "--require-synchronized")
        assert ready_without_scene.returncode == 0, ready_without_scene.stderr
        invalid_ready_candidate = {**ready_meta, "boardSeed": 17}
        save_pair(ready_meta, invalid_ready_candidate)
        ready_seed_mismatch = run(
            "--reference-metadata", str(reference_meta),
            "--candidate-metadata", str(candidate_meta),
            "--require-synchronized")
        assert ready_seed_mismatch.returncode != 0
        assert "not synchronized" in ready_seed_mismatch.stderr
        for phase, outcome, marble_state in (
                ("won", "won", "home"), ("lost", "lost", "lost"),
                ("done", "won", "home")):
            terminal_state = {**rolling_state, "phase": phase,
                              "outcome": outcome,
                              "marbles": [{**rolling_state["marbles"][0],
                                           "state": marble_state}]}
            save_pair({**shared, "sceneState": terminal_state},
                      {**shared, "sceneState": terminal_state})
            terminal_pass = run(
                "--reference-metadata", str(reference_meta),
                "--candidate-metadata", str(candidate_meta),
                "--require-synchronized", "--require-scene-state")
            assert terminal_pass.returncode == 0, (
                f"{phase} scene-state pair rejected: {terminal_pass.stderr}")
        timeout_state = {**rolling_state, "phase": "lost", "outcome": "lost",
                         "terminalReason": "timeout"}
        save_pair({**shared, "sceneState": timeout_state},
                  {**shared, "sceneState": timeout_state})
        timeout_pass = run(
            "--reference-metadata", str(reference_meta),
            "--candidate-metadata", str(candidate_meta),
            "--require-synchronized", "--require-scene-state")
        assert timeout_pass.returncode == 0, timeout_pass.stderr
        physical_loss_with_timeout_pose = {**timeout_state}
        physical_loss_with_timeout_pose.pop("terminalReason")
        save_pair({**shared, "sceneState": physical_loss_with_timeout_pose},
                  {**shared, "sceneState": physical_loss_with_timeout_pose})
        rejected_physical_loss_pose = run(
            "--reference-metadata", str(reference_meta),
            "--candidate-metadata", str(candidate_meta),
            "--require-synchronized", "--require-scene-state")
        assert rejected_physical_loss_pose.returncode != 0
        assert "marble states inconsistent" in rejected_physical_loss_pose.stderr
        save_pair({**shared, "sceneState": rolling_state, "camera": None},
                  {**shared, "sceneState": rolling_state, "camera": None})
        missing_rolling_camera = run(
            "--reference-metadata", str(reference_meta),
            "--candidate-metadata", str(candidate_meta),
            "--require-synchronized")
        assert missing_rolling_camera.returncode != 0
        assert "invalid camera" in missing_rolling_camera.stderr
        save_pair({**shared, "sceneState": rolling_state},
                  {**shared, "sceneState": {**rolling_state, "roll": 0.01}})
        scene_state_mismatch = run(
            "--reference-metadata", str(reference_meta),
            "--candidate-metadata", str(candidate_meta),
            "--require-synchronized")
        assert scene_state_mismatch.returncode != 0
        assert "sceneState differs" in scene_state_mismatch.stderr

        invalid_limit = run("--max-rmse", "nan")
        assert invalid_limit.returncode != 0
        assert "finite non-negative" in invalid_limit.stderr

        save_pair({**shared, "image": {"sha256": "0" * 64,
                                        "dimensions": [2, 2]}}, shared)
        unbound = run(
            "--reference-metadata", str(reference_meta),
            "--candidate-metadata", str(candidate_meta),
            "--require-synchronized")
        assert unbound.returncode != 0
        assert "SHA-256 does not match PNG" in unbound.stderr

        diagnostic = run()
        assert diagnostic.returncode == 0, diagnostic.stderr
        assert "DIAGNOSTIC ONLY" in diagnostic.stdout
        assert "PASS:" not in diagnostic.stdout

    print("Marble render-pair synchronization contract: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
