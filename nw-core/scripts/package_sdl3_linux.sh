#!/usr/bin/env bash
# Package the native Linux build with its SDL and MuJoCo libraries.
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
[[ "$(uname -s)" == Linux ]] || { echo "This packager requires Linux" >&2; exit 2; }
output="${1:?pass a new output directory}"
mujoco_licenses="${2:?pass the MuJoCo license directory}"
mujoco_notices="$mujoco_licenses/LICENSES_THIRD_PARTY.md"
if [[ ! -f "$mujoco_notices" ]]; then
    mujoco_notices="$mujoco_licenses/THIRD_PARTY_NOTICES"
fi
sdl_license="${3:?pass the SDL license file}"
binary="${NW_DESKTOP_BINARY:-$ROOT/build/nw-sdl3-mujoco}"
agent_library="${NW_AGENT_LIBRARY:-$ROOT/build/libnw-agent.so}"
if [[ -n "${NW_AGENT_LIBRARY:-}" && ! -f "$agent_library" ]]; then
    echo "Native agent library not found: $agent_library" >&2
    exit 2
fi
command -v patchelf >/dev/null || { echo "patchelf is required" >&2; exit 2; }
[[ -x "$binary" && -f "$sdl_license" && -f "$mujoco_licenses/LICENSE" &&
   -f "$mujoco_notices" ]] || {
    echo "Missing MuJoCo-enabled SDL build or third-party license files" >&2
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
mkdir "$stage"
mkdir "$stage/lib" "$stage/licenses"
cp "$binary" "$stage/Neural Workshop"
if [[ -f "$agent_library" ]]; then
    cp "$agent_library" "$stage/lib/libnw-agent.so"
    chmod u+w "$stage/lib/libnw-agent.so"
    mkdir "$stage/include"
    cp "$ROOT/shells/sdl3/nw_triage_agent.h" "$stage/include/"
fi
cp -R "$ROOT/res" "$stage/res"
cp "$sdl_license" "$stage/licenses/SDL3.txt"
cp "$mujoco_licenses/LICENSE" "$stage/licenses/MuJoCo.txt"
cp "$mujoco_notices" "$stage/licenses/MuJoCo-third-party.md"

# Select direct dependencies by their ELF names and retain the system GL stack.
resolved="$(env -u LD_PRELOAD ldd "$binary")"
sdl=0
mujoco=0
ttf=0
bundle_dependencies() {
    local source="$1" destination="$2" dependency name license path links recorded
    if ! links="$(patchelf --print-needed "$source")"; then
        printf 'Could not read ELF dependencies for %s\n' "$source" >&2
        return 1
    fi
    while IFS= read -r dependency; do
        [[ -n "$dependency" ]] || continue
        name="$(basename -- "$dependency")"
        license="${NW_DESKTOP_LIBRARY_LICENSES:-}/$name.txt"
        case "$name" in
            libSDL3.so*|libSDL3-*.so*) sdl=1 ;;
            libmujoco.so*|libmujoco-*.so*) mujoco=1 ;;
            libSDL3_ttf.so*|libSDL3_ttf-*.so*)
                ttf=1
                if [[ -z "${NW_DESKTOP_LIBRARY_LICENSES:-}" || ! -f "$license" ]]; then
                    echo "Missing license for bundled library: $name" >&2
                    return 1
                fi
                cp "$license" "$stage/licenses/$name.txt"
                ;;
            *)
                [[ -n "${NW_DESKTOP_LIBRARY_LICENSES:-}" && -f "$license" ]] || continue
                cp "$license" "$stage/licenses/$name.txt"
                ;;
        esac
        if [[ "$dependency" == /* ]]; then
            path="$dependency"
            patchelf --replace-needed "$dependency" "$name" "$destination"
        else
            path="$(awk -v name="$dependency" '$1 == name && $2 == "=>" {
                sub(/^[^=]*=>[[:space:]]*/, "")
                sub(/[[:space:]]*\(0x[[:xdigit:]]+\)$/, "")
                print
                exit
            }' <<< "$resolved")"
        fi
        [[ -f "$path" ]] || { echo "Could not resolve $dependency" >&2; return 1; }
        if [[ -f "$stage/lib/$name" ]]; then
            recorded="$(cat "$work/.origin-$name")"
            [[ "$path" -ef "$recorded" ]] || { echo "Conflicting ELF dependencies: $name" >&2; return 1; }
            continue
        fi
        printf '%s\n' "$path" > "$work/.origin-$name"
        cp -L "$path" "$stage/lib/$name"
        chmod u+w "$stage/lib/$name"
        patchelf --set-rpath '$ORIGIN' "$stage/lib/$name"
        bundle_dependencies "$path" "$stage/lib/$name"
    done <<< "$links"
}
bundle_dependencies "$binary" "$stage/Neural Workshop"
[[ "$sdl" == 1 && "$mujoco" == 1 ]] || { echo "Expected SDL and MuJoCo dependencies" >&2; exit 1; }
patchelf --set-rpath '$ORIGIN/lib' "$stage/Neural Workshop"

if [[ -f "$stage/lib/libnw-agent.so" ]]; then
    resolved="$resolved"$'\n'"$(env -u LD_PRELOAD ldd "$agent_library")"
    patchelf --set-rpath '$ORIGIN' "$stage/lib/libnw-agent.so"
    bundle_dependencies "$agent_library" "$stage/lib/libnw-agent.so"
fi
if [[ -n "$jpeg_library" ]]; then
    [[ ! -e "$stage/lib/libturbojpeg.so.0" ]] || { echo "TurboJPEG conflicts with a staged library" >&2; exit 1; }
    cp -L "$jpeg_library" "$stage/lib/libturbojpeg.so.0"
    cp "$jpeg_license" "$stage/licenses/TurboJPEG.txt"
    chmod u+w "$stage/lib/libturbojpeg.so.0"
    patchelf --set-rpath '$ORIGIN' "$stage/lib/libturbojpeg.so.0"
    jpeg_checked="$(env -i PATH=/usr/bin:/bin ldd "$stage/lib/libturbojpeg.so.0")"
    [[ "$jpeg_checked" != *'not found'* ]] || { printf '%s\n' "$jpeg_checked" >&2; exit 1; }
fi

if [[ -n "$mixer_library" ]]; then
    [[ ! -e "$stage/lib/libSDL3_mixer.so.0" ]] || { echo "SDL_mixer conflicts with a staged library" >&2; exit 1; }
    cp -L "$mixer_library" "$stage/lib/libSDL3_mixer.so.0"
    stage_reward_music "$stage"
    chmod u+w "$stage/lib/libSDL3_mixer.so.0"
    resolved="$resolved"$'\n'"$(env -u LD_PRELOAD ldd "$mixer_library")"
    patchelf --set-rpath '$ORIGIN' "$stage/lib/libSDL3_mixer.so.0"
    bundle_dependencies "$mixer_library" "$stage/lib/libSDL3_mixer.so.0"
fi

ffmpeg_dynamic=0
if [[ -n "$ffmpeg_binary" ]]; then
    stage_ffmpeg "$stage" ffmpeg
    if needed="$(patchelf --print-needed "$ffmpeg_binary" 2>/dev/null)" && [[ -n "$needed" ]]; then
        ffmpeg_dynamic=1
        resolved="$(env -u LD_PRELOAD ldd "$ffmpeg_binary")"
        bundle_dependencies "$ffmpeg_binary" "$stage/ffmpeg"
        patchelf --set-rpath '$ORIGIN/lib' "$stage/ffmpeg"
    fi
fi

# Confirm the loader uses the staged copies and all system dependencies resolve.
checked="$(env -i PATH=/usr/bin:/bin ldd "$stage/Neural Workshop")"
if [[ -f "$stage/lib/libnw-agent.so" ]]; then
    checked="$checked"$'\n'"$(env -i PATH=/usr/bin:/bin ldd "$stage/lib/libnw-agent.so")"
fi
if [[ -n "$mixer_library" ]]; then
    checked="$checked"$'\n'"$(env -i PATH=/usr/bin:/bin ldd "$stage/lib/libSDL3_mixer.so.0")"
fi
if [[ "$ffmpeg_dynamic" == 1 ]]; then
    checked="$checked"$'\n'"$(env -i PATH=/usr/bin:/bin ldd "$stage/ffmpeg")"
fi
if [[ "$checked" == *'not found'* ]]; then
    printf 'Could not resolve staged libraries:\n%s\n' "$checked" >&2
    exit 1
fi
for library in "$stage/lib/"*; do
    name="$(basename -- "$library")"
    [[ -z "$jpeg_library" || "$name" != "libturbojpeg.so.0" ]] || continue
    [[ -z "$mixer_library" || "$name" != "libSDL3_mixer.so.0" ]] || continue
    if ! awk -v name="$name" -v expected="$library" '
        $1 == name && $2 == "=>" {
            sub(/^[^=]*=>[[:space:]]*/, "")
            sub(/[[:space:]]*\(0x[[:xdigit:]]+\)$/, "")
            if ($0 == expected) found = 1
        }
        END { exit !found }
    ' <<< "$checked"; then
        echo "Loader did not select bundled library: $name" >&2
        exit 1
    fi
done

(
    cd /
    env -i PATH=/usr/bin:/bin HOME="$work" SDL_VIDEODRIVER=dummy \
        "$stage/Neural Workshop" --selftest-marble-mujoco
    env -i PATH=/usr/bin:/bin "$stage/Neural Workshop" --selftest-marble-assets
    env -i PATH=/usr/bin:/bin HOME="$work" SDL_VIDEODRIVER=dummy \
        "$stage/Neural Workshop" --selftest-taskhub-lifecycle
    env -i PATH=/usr/bin:/bin HOME="$work" SDL_VIDEODRIVER=dummy \
        "$stage/Neural Workshop" --selftest-long-text
    if [[ -f "$stage/lib/libturbojpeg.so.0" ]]; then
        env -i PATH=/usr/bin:/bin "$stage/Neural Workshop" --selftest-jpeg-package
    fi
    if [[ -n "$ffmpeg_binary" ]]; then
        env -i PATH=/usr/bin:/bin "$stage/Neural Workshop" --selftest-video-jigsaw-package \
            "$ROOT/test/fixtures/video_jigsaw_package.avi"
    fi
    if [[ -n "$mixer_library" ]]; then
        music_check=(--selftest-music-package)
        if [[ -n "$reward_music" ]]; then
            music_check+=(--with-tracks)
        fi
        env -i PATH=/usr/bin:/bin SDL_AUDIODRIVER=dummy "$stage/Neural Workshop" "${music_check[@]}"
    fi
    if [[ "$ttf" == 1 ]]; then
        env -i PATH=/usr/bin:/bin HOME="$work" SDL_VIDEODRIVER=dummy \
            "$stage/Neural Workshop" --screen taskhub --screenshot "$work/font-smoke.png"
        env -i PATH=/usr/bin:/bin HOME="$work" SDL_VIDEODRIVER=dummy NW_SDL_FONT= \
            "$stage/Neural Workshop" --screen taskhub --screenshot "$work/bitmap-smoke.png"
        [[ -s "$work/font-smoke.png" && -s "$work/bitmap-smoke.png" ]]
        if cmp -s "$work/font-smoke.png" "$work/bitmap-smoke.png"; then
            echo "Packaged TrueType capture matches the bitmap fallback" >&2
            exit 1
        fi
    fi
)
mv "$stage" "$output"
