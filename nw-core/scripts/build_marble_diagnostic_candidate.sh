#!/usr/bin/env bash
# Rebuild the complete qualified diagnostic candidate without shipping it.
# Absolute source paths can change binary hashes: fresh parity is still required.
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
PATCH="$ROOT/test/repro/marble_layer29_complete_diagnostic_candidate.patch"
COMMIT=13827e9ee56f097f57acf69ae52b078f9839682d
EXPECTED_PATCH=4e5ce41448539819438891ed187dc5e8fa7182ba77d7d5e8f9bb9dcff5574974
if [[ $# != 1 || "$1" != /* || -e "$1" ]]; then
    echo "Usage: bash $0 /absolute/new-output-directory (must not exist)" >&2
    exit 2
fi
DESTINATION="$1"
for command_name in git emcc emcmake cmake shasum; do
    command -v "$command_name" >/dev/null || {
        echo "Missing build tool: $command_name" >&2; exit 2;
    }
done
version="$(emcc --version)"
if [[ "$version" != *"6.0.10"* ]]; then
    echo "This diagnostic recipe requires qualified Emscripten 6.0.10." >&2
    exit 2
fi
actual_patch="$(shasum -a 256 "$PATCH")"
if [[ "${actual_patch%% *}" != "$EXPECTED_PATCH" ]]; then
    echo "Diagnostic patch identity changed; requalify before building." >&2
    exit 2
fi
WORK="$(mktemp -d "${TMPDIR:-/tmp}/nw-marble-diagnostic-rebuild.XXXXXXXX")"
complete=0
cleanup() {
    if [[ "$complete" == 1 ]]; then
        rm -rf "$WORK"
    else
        echo "Incomplete build retained at: $WORK" >&2
    fi
}
trap cleanup EXIT
git clone --quiet --depth 1 --branch 3.12.0 \
    https://github.com/google-deepmind/mujoco.git "$WORK/upstream"
if [[ "$(git -C "$WORK/upstream" rev-parse HEAD)" != "$COMMIT" ]]; then
    echo "Unexpected upstream commit; refusing build." >&2
    exit 2
fi
git -C "$WORK/upstream" apply --check "$PATCH"
git -C "$WORK/upstream" apply "$PATCH"
emcmake cmake -S "$WORK/upstream" -B "$WORK/build-wasm" \
    -DCMAKE_BUILD_TYPE=Release -DMUJOCO_BUILD_TESTS_WASM=OFF \
    -DMUJOCO_WASM_THREADS=OFF > "$WORK/configure.log" 2>&1
cmake --build "$WORK/build-wasm" --target mujoco_wasm \
    --parallel "${CMAKE_BUILD_PARALLEL_LEVEL:-4}" > "$WORK/build.log" 2>&1
# Plain mkdir intentionally fails if the destination appeared during the build.
mkdir "$DESTINATION"
cp "$WORK/upstream/wasm/dist/mujoco.js" "$WORK/upstream/wasm/dist/mujoco.wasm" \
    "$WORK/configure.log" "$WORK/build.log" "$WORK/build-wasm/CMakeCache.txt" \
    "$DESTINATION/"
# Keep the exact inputs/tool versions after the successful scratch cleanup.
# These receipts describe a build, not acceptance of its physics or visuals.
cp "$PATCH" "$DESTINATION/candidate.patch"
git -C "$WORK/upstream" show -s --format=fuller HEAD > "$DESTINATION/upstream-commit.txt"
emcc --version > "$DESTINATION/emscripten-version.txt"
cmake --version > "$DESTINATION/cmake-version.txt"
shasum -a 256 "$DESTINATION/candidate.patch" "$DESTINATION/mujoco.js" \
    "$DESTINATION/mujoco.wasm" > "$DESTINATION/artifact-sha256.txt"
shasum -a 256 "$DESTINATION/mujoco.js" "$DESTINATION/mujoco.wasm"
echo "Diagnostic build only. No production file or physics manifest was changed."
echo "Run original trajectory, full source matrix, lifecycle, and visual gates before promotion."
complete=1
