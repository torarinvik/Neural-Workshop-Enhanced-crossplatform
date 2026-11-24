#!/usr/bin/env bash
# Stage and smoke-test a native Windows distribution from MinGW or MSYS2.
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
case "$(uname -s)" in
    MINGW*|MSYS*|UCRT*) ;;
    *) echo "Run this packager on Windows from MinGW or MSYS2" >&2; exit 2 ;;
esac
output="${1:?pass a new output directory}"
sdl_dll="${2:?pass the SDL3.dll used by the build}"
mujoco_dll="${3:?pass the mujoco.dll used by the build}"
mujoco_licenses="${4:?pass the MuJoCo license directory}"
mujoco_notices="$mujoco_licenses/LICENSES_THIRD_PARTY.md"
if [[ ! -f "$mujoco_notices" ]]; then
    mujoco_notices="$mujoco_licenses/THIRD_PARTY_NOTICES"
fi
sdl_license="${5:?pass the SDL license file}"
binary="${NW_DESKTOP_BINARY:-$ROOT/build/nw-sdl3-mujoco.exe}"
agent_library="${NW_AGENT_LIBRARY:-$ROOT/build/nw-agent.dll}"
if [[ -n "${NW_AGENT_LIBRARY:-}" && ! -f "$agent_library" ]]; then
    echo "Native agent library not found: $agent_library" >&2
    exit 2
fi
[[ -f "$binary" && -f "$sdl_dll" && -f "$mujoco_dll" &&
   -f "$sdl_license" && -f "$mujoco_licenses/LICENSE" &&
   -f "$mujoco_notices" ]] || {
    echo "Missing native Windows build, DLLs, or third-party licenses" >&2
    exit 2
}
jpeg_library="${NW_JPEG_LIBRARY:-}"
jpeg_license="${NW_JPEG_LICENSE:-}"
if [[ -n "$jpeg_library" || -n "$jpeg_license" ]]; then
    [[ -f "$jpeg_library" && -f "$jpeg_license" ]] || {
        echo "TurboJPEG packaging requires NW_JPEG_LIBRARY and NW_JPEG_LICENSE" >&2
        exit 2
    }
fi
source "$ROOT/scripts/package_sdl3_music.sh"
source "$ROOT/scripts/package_sdl3_video.sh"
[[ ! -e "$output" && ! -L "$output" ]] || { echo "Output already exists: $output" >&2; exit 2; }
parent="$(cd -- "$(dirname -- "$output")" && pwd -P)"
work="$(mktemp -d "$parent/.nw-desktop.XXXXXX")"
trap 'rm -rf -- "$work"' EXIT
stage="$work/Relocated Neural Workshop"
mkdir -p "$stage/licenses" "$work/profile"
cp "$binary" "$stage/Neural Workshop.exe"
cp "$sdl_dll" "$stage/SDL3.dll"
cp "$mujoco_dll" "$stage/mujoco.dll"
if [[ -f "$agent_library" ]]; then
    cp "$agent_library" "$stage/nw-agent.dll"
    chmod u+w "$stage/nw-agent.dll"
    mkdir "$stage/include"
    cp "$ROOT/shells/sdl3/nw_triage_agent.h" "$stage/include/"
fi
cp -R "$ROOT/res" "$stage/res"
cp "$sdl_license" "$stage/licenses/SDL3.txt"
cp "$mujoco_licenses/LICENSE" "$stage/licenses/MuJoCo.txt"
cp "$mujoco_notices" "$stage/licenses/MuJoCo-third-party.md"

# Optional app-local DLLs supplied with their matching license notices.
if [[ -n "${NW_DESKTOP_DLL_DIR:-}" ]]; then
    shopt -s nullglob
    extra_dlls=("$NW_DESKTOP_DLL_DIR/"*.[dD][lL][lL])
    if (( ${#extra_dlls[@]} == 0 )); then
        echo "No DLLs found in $NW_DESKTOP_DLL_DIR" >&2
        exit 2
    fi
    for dll in "${extra_dlls[@]}"; do
        name="$(basename -- "$dll")"
        if [[ -e "$stage/$name" ]]; then
            echo "Extra DLL conflicts with a staged library: $name" >&2
            exit 2
        fi
        license="${NW_DESKTOP_LIBRARY_LICENSES:?pass the extra DLL license directory}/$name.txt"
        if [[ ! -f "$license" ]]; then
            echo "Missing license for bundled library: $name" >&2
            exit 2
        fi
        cp "$dll" "$stage/$name"
        cp "$license" "$stage/licenses/$name.txt"
    done
fi

if [[ -n "$jpeg_library" ]]; then
    [[ ! -e "$stage/turbojpeg.dll" ]] || { echo "TurboJPEG conflicts with a staged library" >&2; exit 1; }
    cp -L "$jpeg_library" "$stage/turbojpeg.dll"
    cp "$jpeg_license" "$stage/licenses/TurboJPEG.txt"
fi

if [[ -n "$mixer_library" ]]; then
    [[ ! -e "$stage/SDL3_mixer.dll" ]] || { echo "SDL_mixer conflicts with a staged library" >&2; exit 1; }
    cp -L "$mixer_library" "$stage/SDL3_mixer.dll"
    stage_reward_music "$stage"
fi

# Preserve Windows system configuration and remove developer DLL search paths.
if [[ -n "$ffmpeg_binary" ]]; then
    stage_ffmpeg "$stage" ffmpeg.exe
    video_fixture="$(cygpath -w "$ROOT/test/fixtures/video_jigsaw_package.avi")"
fi
windows_root="$(cygpath -u "${SYSTEMROOT:?Windows system directory is required}")"
profile="$(cygpath -w "$work/profile")"
font_capture="$(cygpath -w "$work/font-smoke.png")"
bitmap_capture="$(cygpath -w "$work/bitmap-smoke.png")"
(
    cd "$work/profile"
    export PATH="$windows_root/System32:$windows_root" SDL_VIDEODRIVER=dummy
    export APPDATA="$profile" USERPROFILE="$profile"
    "$stage/Neural Workshop.exe" --selftest-marble-mujoco
    "$stage/Neural Workshop.exe" --selftest-marble-assets
    "$stage/Neural Workshop.exe" --selftest-taskhub-lifecycle
    "$stage/Neural Workshop.exe" --selftest-long-text
    if [[ -f "$stage/turbojpeg.dll" ]]; then
        env -u NW_JPEG_LIBRARY "$stage/Neural Workshop.exe" --selftest-jpeg-package
    fi
    if [[ -n "$ffmpeg_binary" ]]; then
        "$stage/Neural Workshop.exe" --selftest-video-jigsaw-package "$video_fixture"
    fi
    if [[ -n "$mixer_library" ]]; then
        music_check=(--selftest-music-package)
        if [[ -n "$reward_music" ]]; then
            music_check+=(--with-tracks)
        fi
        env -u NW_MIXER_LIBRARY -u NW_REWARD_MUSIC_DIR SDL_AUDIODRIVER=dummy "$stage/Neural Workshop.exe" "${music_check[@]}"
    fi
    if [[ -f "$stage/SDL3_ttf.dll" ]]; then
        unset NW_SDL_FONT
        "$stage/Neural Workshop.exe" --screen taskhub --screenshot "$font_capture"
        NW_SDL_FONT= "$stage/Neural Workshop.exe" --screen taskhub --screenshot "$bitmap_capture"
    fi
)
if [[ -f "$stage/SDL3_ttf.dll" ]]; then
    [[ -s "$work/font-smoke.png" && -s "$work/bitmap-smoke.png" ]]
    if cmp -s "$work/font-smoke.png" "$work/bitmap-smoke.png"; then
        echo "Packaged TrueType capture matches the bitmap fallback" >&2
        exit 1
    fi
fi
mv "$stage" "$output"
