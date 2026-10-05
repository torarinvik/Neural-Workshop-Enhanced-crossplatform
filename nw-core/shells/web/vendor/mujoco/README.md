# MuJoCo WebAssembly runtime

This directory vendors a single-threaded browser build of MuJoCo 3.12.0,
pinned to source commit `13827e9ee56f097f57acf69ae52b078f9839682d`. It lets the
local web shell run the same rigid-body engine as the native Marble Maze
implementation without a package manager or cross-origin isolation. The
browser build includes the narrow cross-platform floating-point parity patch
in `marble-wasm-parity.patch`; it is not byte-for-byte the published npm WASM.

Source: <https://github.com/google-deepmind/mujoco/tree/main/wasm>
Package: <https://www.npmjs.com/package/@mujoco/mujoco/v/3.12.0>
License: Apache-2.0 (MuJoCo / Google DeepMind)

To reproduce or refresh both runtime files, install CMake and Emscripten, then
run `scripts/build_marble_mujoco_wasm.sh` from the repository. The script
fetches and verifies the pinned upstream commit, applies the checked-in patch,
builds the Release browser target with Emscripten 6.0.10, and copies the paired
JS/WASM outputs together. It refuses a different patch checksum or compiler
version. Do not refresh from the npm package alone: that would remove the
native-matching fused reductions, active-set transfer, spatial operations, and
quaternion/trigonometric ordering qualified for Marble. Patch SHA-256:
`e2c0eaf4566f4ca3a8510bfa1178cc29ee25c9cff2d9b9eb85d9be810ff12362`.

The non-diagnostic patch was built from a clean MuJoCo checkout and qualified
against the original Python 3.13 / native MuJoCo 3.12.0 task on 2026-10-03.
All 80 deterministic held-input replays (16 rungs × seeds 0, 1, 17, 314159,
1073741823) matched every captured public physics value, discrete state,
contact set, and terminal result exactly. The full artifact gate also passed:
80 generated sessions, 3 adaptive multi-trial sessions, 320 hole/wall-clearance
boards, 80 byte-identical board/MJCF comparisons, and 162 controlled trajectory
scenarios / 17,263 per-frame states within their existing tolerances. These are
the recorded deterministic acceptance domains, not a claim about every
arbitrary initial condition or time-step partition.
