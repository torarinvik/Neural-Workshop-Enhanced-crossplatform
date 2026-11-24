# Sourced by the desktop packagers. Match the runtime's executable-relative
# name and keep the license and notices supplied for this ffmpeg build.
ffmpeg_binary="${NW_FFMPEG_BINARY:-}"
ffmpeg_license="${NW_FFMPEG_LICENSE:-}"
if [[ -n "$ffmpeg_binary" || -n "$ffmpeg_license" ]]; then
    [[ -f "$ffmpeg_binary" && -x "$ffmpeg_binary" && -s "$ffmpeg_license" ]] || {
        echo "ffmpeg packaging requires NW_FFMPEG_BINARY and NW_FFMPEG_LICENSE" >&2
        exit 2
    }
fi

stage_ffmpeg() {
    local directory="$1" name="$2"
    cp -L "$ffmpeg_binary" "$directory/$name"
    chmod u+wx "$directory/$name"
    cp "$ffmpeg_license" "$directory/licenses/FFmpeg.txt"
}
