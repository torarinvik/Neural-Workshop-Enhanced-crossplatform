#!/usr/bin/env bash
# Verify the native Camera renderer in a hidden SDL3 OpenGL window.
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT/scripts/env.sh"
compiler="${ELISA_SDL_COMPILER:-$ELISA_STAGE1_BIN}"
runtime_root="${ELISA_SDL_RUNTIME_ROOT:-$ELISA_STAGE1_ROOT}"
runtime="${ELISA_SDL_RUNTIME_OBJ:-$runtime_root/build/runtime/elisacore_runtime.o}"
work="$(mktemp -d)"
trap 'rm -rf -- "$work"' EXIT

camera_objcopy=llvm-objcopy
if [[ "$(uname -s)" == Linux ]] && ! command -v "$camera_objcopy" >/dev/null 2>&1; then
    camera_objcopy=objcopy
fi
case "$(uname -s)" in
    Darwin) gl=(-framework OpenGL) ;;
    Linux) gl=(-lGL -lm); export ELISA_HOST_LINUX=1 ;;
    *) echo "test_camera_gl.sh: this replay supports macOS and Linux" >&2; exit 2 ;;
esac
if [[ "$(uname -m)" == x86_64 ]]; then
    export ELISA_HOST_X86_64=1
fi

python3 "$ROOT/scripts/prepare_runtime_sources.py" "$ROOT" "$work/source" "$runtime_root"
"$compiler" -emit obj -O2 -o "$work/camera.o" "$work/source/test/camera_gl_smoke.elisa"
"$compiler" -emit obj -O2 -o "$work/camera_sdl.o" "$work/source/src/native/sdl_camera_exports.elisa"
# The export object owns Camera's Elisa state. Localize its other symbols
# so only the Camera ABI crosses into the SDL host's runtime.
nm -g "$work/camera_sdl.o" | awk '$NF ~ /^_?nw_sdl_camera_/ { print $NF }' > "$work/camera.exports"
"$camera_objcopy" --keep-global-symbols="$work/camera.exports" "$work/camera_sdl.o" "$work/camera_link.o"
read -r -a sdl_flags <<< "$(pkg-config --cflags --libs sdl3)"
cc -o "$work/replay" "$work/camera.o" "$work/camera_link.o" "$runtime" "${gl[@]}" "${sdl_flags[@]}"
mkdir -p "$work/res"
cp -R "$ROOT/res/camera" "$work/res/"
"$work/replay"
echo "PASS: native Camera OpenGL live view, photo peek, resize, and SDL composition"
