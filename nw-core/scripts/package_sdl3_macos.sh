#!/usr/bin/env bash
# Stage a relocatable macOS desktop distribution from the tested native build.
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
[[ "$(uname -s)" == Darwin ]] || { echo "This packager requires macOS" >&2; exit 2; }
output="${1:?pass a new output directory}"
mujoco_licenses="${2:?pass the MuJoCo license directory}"
mujoco_notices="$mujoco_licenses/LICENSES_THIRD_PARTY.md"
if [[ ! -f "$mujoco_notices" ]]; then
    mujoco_notices="$mujoco_licenses/THIRD_PARTY_NOTICES"
fi
sdl_license="${NW_SDL_LICENSE:-$(pkg-config --variable=prefix sdl3)/LICENSE.txt}"
binary="${NW_DESKTOP_BINARY:-$ROOT/build/nw-sdl3-mujoco}"
agent_library="${NW_AGENT_LIBRARY:-$ROOT/build/libnw-agent.dylib}"
if [[ -n "${NW_AGENT_LIBRARY:-}" && ! -f "$agent_library" ]]; then
    echo "Native agent library not found: $agent_library" >&2
    exit 2
fi
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
parent="$(cd -- "$(dirname -- "$output")" && pwd)"
stage="$(mktemp -d "$parent/.nw-desktop.XXXXXX")"
trap 'rm -rf -- "$stage"' EXIT
mkdir "$stage/lib" "$stage/licenses"
cp "$binary" "$stage/Neural Workshop"
if [[ -f "$agent_library" ]]; then
    cp "$agent_library" "$stage/lib/libnw-agent.dylib"
    chmod u+w "$stage/lib/libnw-agent.dylib"
    mkdir "$stage/include"
    cp "$ROOT/shells/sdl3/nw_triage_agent.h" "$stage/include/"
fi
cp -R "$ROOT/res" "$stage/res"
cp "$sdl_license" "$stage/licenses/SDL3.txt"
cp "$mujoco_licenses/LICENSE" "$stage/licenses/MuJoCo.txt"
cp "$mujoco_notices" "$stage/licenses/MuJoCo-third-party.md"

dependencies() {
    otool -L "$1" | sed -n 's/^[[:space:]][[:space:]]*\(.*\) (compatibility version.*/\1/p'
}
# Rewrite each dylib's dependencies relative to its own location. Staging a
# library before walking its children also handles dependency cycles.
bundle_dependencies() {
    local source="$1" artifact="$2" prefix="$3" dependency resolved name links identity recorded
    links="$(dependencies "$source")"
    identity="$(otool -D "$source" | sed -n '2p')"
    while IFS= read -r dependency; do
        [[ "$dependency" != "$identity" ]] || continue
        case "$dependency" in
            /System/Library/*|/usr/lib/*) continue ;;
            /*.dylib) resolved="$dependency" ;;
            @rpath/*.dylib|@loader_path/*.dylib)
                resolved="$(dirname -- "$source")/${dependency#*/}"
                [[ -f "$resolved" ]] || { echo "Could not resolve $dependency from $source" >&2; return 1; }
                ;;
            *) echo "Unexpected native dependency: $dependency" >&2; return 1 ;;
        esac
        name="$(basename -- "$dependency")"
        case "$name" in
            libSDL3.0.dylib|libmujoco*.dylib) ;;
            *)
                if [[ -z "${NW_DESKTOP_LIBRARY_LICENSES:-}" ||
                    ! -f "$NW_DESKTOP_LIBRARY_LICENSES/$name.txt" ]]; then
                    echo "Missing license for bundled library: $name" >&2
                    return 1
                fi
                cp "$NW_DESKTOP_LIBRARY_LICENSES/$name.txt" "$stage/licenses/$name.txt"
                ;;
        esac
        if [[ -f "$stage/lib/$name" ]]; then
            recorded="$(cat "$stage/.origin-$name")"
            if [[ ! "$recorded" -ef "$resolved" ]]; then
                echo "Conflicting dylibs with basename: $name" >&2
                return 1
            fi
        else
            printf '%s\n' "$resolved" > "$stage/.origin-$name"
            cp -L "$resolved" "$stage/lib/$name"
            chmod u+w "$stage/lib/$name"
            install_name_tool -id "@loader_path/$name" "$stage/lib/$name"
            bundle_dependencies "$resolved" "$stage/lib/$name" ""
        fi
        install_name_tool -change "$dependency" "@loader_path/$prefix$name" "$artifact"
    done <<< "$links"
}

bundle_dependencies "$binary" "$stage/Neural Workshop" "lib/"
if [[ -f "$stage/lib/libnw-agent.dylib" ]]; then
    install_name_tool -id "@loader_path/libnw-agent.dylib" "$stage/lib/libnw-agent.dylib"
    bundle_dependencies "$agent_library" "$stage/lib/libnw-agent.dylib" ""
fi
if [[ -n "$jpeg_library" ]]; then
    [[ ! -e "$stage/lib/libturbojpeg.0.dylib" ]] || { echo "TurboJPEG conflicts with a staged library" >&2; exit 1; }
    cp -L "$jpeg_library" "$stage/lib/libturbojpeg.0.dylib"
    cp "$jpeg_license" "$stage/licenses/TurboJPEG.txt"
    chmod u+w "$stage/lib/libturbojpeg.0.dylib"
    install_name_tool -id "@loader_path/libturbojpeg.0.dylib" "$stage/lib/libturbojpeg.0.dylib"
    bundle_dependencies "$jpeg_library" "$stage/lib/libturbojpeg.0.dylib" ""
fi

if [[ -n "$mixer_library" ]]; then
    [[ ! -e "$stage/lib/libSDL3_mixer.0.dylib" ]] || { echo "SDL_mixer conflicts with a staged library" >&2; exit 1; }
    cp -L "$mixer_library" "$stage/lib/libSDL3_mixer.0.dylib"
    stage_reward_music "$stage"
    chmod u+w "$stage/lib/libSDL3_mixer.0.dylib"
    install_name_tool -id "@loader_path/libSDL3_mixer.0.dylib" "$stage/lib/libSDL3_mixer.0.dylib"
    bundle_dependencies "$mixer_library" "$stage/lib/libSDL3_mixer.0.dylib" ""
fi

executables=("$stage/Neural Workshop")
if [[ -n "$ffmpeg_binary" ]]; then
    stage_ffmpeg "$stage" ffmpeg
    bundle_dependencies "$ffmpeg_binary" "$stage/ffmpeg" "lib/"
    executables+=("$stage/ffmpeg")
fi

rm -f "$stage/".origin-*
for library in "$stage/lib/"*.dylib; do
    codesign --force --sign - "$library"
done
for executable in "${executables[@]}"; do
    codesign --force --sign - "$executable"
done
for artifact in "${executables[@]}" "$stage/lib/"*.dylib; do
    codesign --verify "$artifact"
    nonportable="$(dependencies "$artifact" |
        awk '$0 !~ /^(@loader_path\/|\/System\/Library\/|\/usr\/lib\/)/')"
    [[ -z "$nonportable" ]] || { printf '%s\n' "$nonportable" >&2; exit 1; }
done
(
    cd /
    env -i PATH=/usr/bin:/bin HOME="$stage" SDL_VIDEODRIVER=dummy \
        "$stage/Neural Workshop" --selftest-marble-mujoco
    env -i PATH=/usr/bin:/bin "$stage/Neural Workshop" --selftest-marble-assets
    env -i PATH=/usr/bin:/bin HOME="$stage" SDL_VIDEODRIVER=dummy \
        "$stage/Neural Workshop" --selftest-taskhub-lifecycle
    env -i PATH=/usr/bin:/bin HOME="$stage" SDL_VIDEODRIVER=dummy \
        "$stage/Neural Workshop" --selftest-long-text
    if [[ -f "$stage/lib/libturbojpeg.0.dylib" ]]; then
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
    if [[ -f "$stage/lib/libSDL3_ttf.0.dylib" ]]; then
        env -i PATH=/usr/bin:/bin HOME="$stage" \
            "$stage/Neural Workshop" --headless --screen taskhub --screenshot "$stage/.font-smoke.png"
        env -i PATH=/usr/bin:/bin HOME="$stage" NW_SDL_FONT= \
            "$stage/Neural Workshop" --headless --screen taskhub --screenshot "$stage/.bitmap-smoke.png"
        [[ -s "$stage/.font-smoke.png" && -s "$stage/.bitmap-smoke.png" ]]
        if cmp -s "$stage/.font-smoke.png" "$stage/.bitmap-smoke.png"; then
            echo "Packaged TrueType capture matches the bitmap fallback" >&2
            exit 1
        fi
        rm "$stage/.font-smoke.png" "$stage/.bitmap-smoke.png"
    fi
)
mv "$stage" "$output"
