#!/usr/bin/env bash
# Build the pinned MuJoCo browser runtime with the source-qualified Marble
# native-parity patch. Keep this output paired with the port core WASM.
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
MUJOCO_COMMIT="13827e9ee56f097f57acf69ae52b078f9839682d"
PARITY_PATCH="$ROOT/shells/web/vendor/mujoco/marble-wasm-parity.patch"
EXPECTED_PATCH_SHA256="e2c0eaf4566f4ca3a8510bfa1178cc29ee25c9cff2d9b9eb85d9be810ff12362"
DESTINATION="$ROOT/shells/web/vendor/mujoco"

for command_name in git emcc emcmake cmake shasum; do
    if ! command -v "$command_name" >/dev/null 2>&1; then
        echo "missing required build tool: $command_name (install Emscripten and CMake)" >&2
        exit 2
    fi
done

patch_hash="$(shasum -a 256 "$PARITY_PATCH")"
patch_hash="${patch_hash%% *}"
if [[ "$patch_hash" != "$EXPECTED_PATCH_SHA256" ]]; then
    echo "unexpected Marble WASM parity patch hash: $patch_hash" >&2
    echo "refusing to build an unqualified physics candidate" >&2
    exit 2
fi

emcc_version="$(emcc --version)"
if [[ "$emcc_version" != *"6.0.10"* ]]; then
    echo "this qualified MuJoCo build requires Emscripten 6.0.10" >&2
    echo "$emcc_version" >&2
    exit 2
fi

# Emscripten 6.x requires Python 3.10+, while macOS may put Apple's older
# /usr/bin/python3 ahead of Homebrew's interpreter. Prefer an already
# available versioned interpreter if the default is too old.
python_major_minor="$(python3 -c 'import sys; print("%d.%d" % sys.version_info[:2])' 2>/dev/null || echo 0.0)"
python_major="${python_major_minor%%.*}"
python_minor="${python_major_minor#*.}"
if (( python_major < 3 || (python_major == 3 && python_minor < 10) )); then
    for candidate in python3.14 python3.13 python3.12 python3.11 python3.10; do
        if command -v "$candidate" >/dev/null 2>&1 && \
            "$candidate" -c 'import sys; raise SystemExit(sys.version_info < (3, 10))'; then
            PATH="$(dirname "$(command -v "$candidate")"):$PATH"
            export PATH
            break
        fi
    done
    python_major_minor="$(python3 -c 'import sys; print("%d.%d" % sys.version_info[:2])' 2>/dev/null || echo 0.0)"
    python_major="${python_major_minor%%.*}"
    python_minor="${python_major_minor#*.}"
    if (( python_major < 3 || (python_major == 3 && python_minor < 10) )); then
        echo "Emscripten requires Python 3.10+; install it or put python3.10+ first on PATH." >&2
        exit 2
    fi
fi

WORK="$(mktemp -d "${TMPDIR:-/tmp}/nw-marble-mujoco-wasm.XXXXXX")"
trap 'rm -rf "$WORK"' EXIT INT TERM HUP

git clone --quiet --depth 1 --branch 3.12.0 \
    https://github.com/google-deepmind/mujoco.git "$WORK/mujoco"
actual_commit="$(git -C "$WORK/mujoco" rev-parse HEAD)"
if [[ "$actual_commit" != "$MUJOCO_COMMIT" ]]; then
    echo "MuJoCo 3.12.0 resolved to unexpected commit: $actual_commit" >&2
    exit 2
fi
git -C "$WORK/mujoco" apply --check "$PARITY_PATCH"
git -C "$WORK/mujoco" apply "$PARITY_PATCH"

emcmake cmake -S "$WORK/mujoco" -B "$WORK/build" \
    -DCMAKE_BUILD_TYPE=Release \
    -DMUJOCO_BUILD_TESTS_WASM=OFF \
    -DMUJOCO_WASM_THREADS=OFF
cmake --build "$WORK/build" --target mujoco_wasm \
    --parallel "${CMAKE_BUILD_PARALLEL_LEVEL:-8}"

cp "$WORK/mujoco/wasm/dist/mujoco.js" "$DESTINATION/mujoco.js"
cp "$WORK/mujoco/wasm/dist/mujoco.wasm" "$DESTINATION/mujoco.wasm"
echo "Built qualified MuJoCo 3.12.0 ($MUJOCO_COMMIT) with the pinned Marble parity patch."
shasum -a 256 "$DESTINATION/mujoco.js" "$DESTINATION/mujoco.wasm"
