# Shared input validation and resource staging for the desktop packagers.
mixer_library="${NW_MIXER_LIBRARY:-}"
mixer_license="${NW_MIXER_LICENSE:-}"
reward_music="${NW_REWARD_MUSIC_DIR:-}"
reward_licenses="${NW_REWARD_MUSIC_LICENSES:-}"
if [[ -n "$mixer_library" || -n "$mixer_license" || -n "$reward_music" || -n "$reward_licenses" ]]; then
    [[ -f "$mixer_library" && -f "$mixer_license" ]] || {
        echo "Reward music packaging requires NW_MIXER_LIBRARY and NW_MIXER_LICENSE" >&2
        exit 2
    }
fi
if [[ -n "$reward_music" || -n "$reward_licenses" ]]; then
    [[ -d "$reward_music" && -d "$reward_licenses" ]] || {
        echo "Bundled reward tracks require NW_REWARD_MUSIC_DIR and NW_REWARD_MUSIC_LICENSES" >&2
        exit 2
    }
fi

stage_reward_music() {
    local destination="$1" album track
    local -a tracks
    cp "$mixer_license" "$destination/licenses/SDL3_mixer.txt"
    [[ -n "$reward_music" ]] || return 0
    mkdir -p "$destination/licenses/music"
    cp -R "$reward_licenses/." "$destination/licenses/music/"
    for album in advance great good; do
        [[ -d "$reward_music/$album" ]] || continue
        mkdir -p "$destination/res/music/$album"
        tracks=()
        while IFS= read -r -d '' track; do
            tracks+=("$track")
        done < <(find "$reward_music/$album" -maxdepth 1 -type f \( -name '*.ogg' -o -name '*.wav' \) -print0)
        if (( ${#tracks[@]} )); then
            cp "${tracks[@]}" "$destination/res/music/$album/"
        fi
    done
}
