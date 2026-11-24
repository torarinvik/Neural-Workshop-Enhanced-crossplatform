# Native desktop shell (SDL3)

    brew install sdl3 pkg-config      # or the platform equivalent
    scripts/build_sdl3.sh             # builds AND runs the headless selftest
    build/nw-sdl3                     # the window
    build/nw-sdl3 --selftest 180      # headless title/display-list smoke
    build/nw-sdl3 --selftest-tetris   # headless Freeform Tetris lifecycle smoke

Use `--headless` to run the desktop event loop with a hidden window. When
SDL has no explicit video driver, the desktop tries its dummy and offscreen
drivers in that order. Use `--dump` or `--screenshot FILE` to render and exit.

Use `--screen recognition --recognition-sound` to play Recognition with an
existing ESC-50 WAV library at `datasets/esc50` in the workshop data directory.
Recognition can start with two clips and may end early if it runs out of
eligible items. Press R to replay the current sound.
Use `--screen concentration --concentration-sound` to deal pairs from
the same library and hear a clip when you flip a card. Both tasks rescan the
library when you press Space to start, so you can add missing clips and retry
in the same window.

Both tasks use JPEG photographs from `datasets/tiny-imagenet` in the workshop
data directory by default. Use `--recognition-pictures` or
`--concentration-pictures` to override a saved sound preference. Both use TurboJPEG
through Elisa FFI. Install the platform TurboJPEG library or set
`NW_JPEG_LIBRARY` to its absolute path if it is outside the dynamic loader's
search path. Set the same variable when running `scripts/build_sdl3.sh` to
include the decoded-pixel and corrupt-image checks in the headless gate.

To include photo support in a macOS, Linux, or Windows package, set
`NW_JPEG_LIBRARY` to the target platform's TurboJPEG library and
`NW_JPEG_LICENSE` to a text file containing its BSD and IJG notices. The
packager tests the copy beside the application before publishing the staged
directory.

Press Space on the title screen to open the task hub. Use the arrow keys
or click a category tab to navigate, then press Enter or click a card to
launch its task. Escape returns from the task to the hub and from the hub
to the title when the hub was opened there. A direct `--screen taskhub`
launch starts at the hub.

Open Crazy Cog from Reasoning or use `--screen crazy-cog`. Press Space
or click to start, then drag cogs and chains out of the tray. Tab or F goes
one plane deeper, and Shift+Tab or G goes one plane nearer. Keys 1–5 select
a plane and R clears the board. Press C before or after a run to edit the
original profile’s `COG_*` settings. The desktop saves changes to the
profile’s `.crazy-cog-options` sidecar.

Open The Cipher Abyss from Reasoning or use `--screen cipher-abyss`.
Press Space or Enter to start. Use 1–8 for symbols, Enter to run or
answer, and T to begin the test. X saves the notebook to the workshop’s
data directory. The options read `CIPHER_RUNG`, `CIPHER_TRIALS`, and
`CIPHER_ADAPTIVE` from the selected profile and save edits to its
`.cipher-abyss-options` sidecar.

Open Notebook from Long-term memory or use `--screen notebook`.
Shift+1–8 copies the current fact onto a notebook line. Enter or N
advances a fact card, and 1–4 answers a question. The same controls are
available by click. Press C before or after a run to change the rung,
round count, and adaptive difficulty. The desktop reads the Python
profile's `NOTEBOOK_*` settings and saves changes in its
`.notebook-options` sidecar.

Open Where Was It? from Long-term memory or use `--screen where-was-it`.
Space, Enter, N, or the on-screen button advances through the study
rooms. Click the changed location in the test room. C opens options
before starting or after a run. The desktop reads `WHERE_WAS_IT_RUNG`,
`WHERE_WAS_IT_TRIALS`, and `WHERE_WAS_IT_ADAPTIVE` from the original
profile and saves edits to its `.where-was-it-options` sidecar.


Open Same or Mirror? from Perception or use `--screen same-or-mirror`.
Press Space or click to start. On paired rounds, press S for Same or M
for Mirror. Click or use the number keys on the choice rows. C opens
options before a run or on the summary. The app reads the original
`SAME_OR_MIRROR_*` profile settings and saves edits to a
`.same-or-mirror-options` sidecar.

Open Which Is Nearer? from Perception or use `--screen which-is-nearer`.
Press Space or click to start. Click a solid or its numbered button, or
use 1–6. At higher rungs the eye sways, and ordered trials ask for each
solid nearest first. C opens the starting rung, scenes per run, and
adaptive options. The app reads the original `WHICH_IS_NEARER_*`
profile keys and saves changes in its `.which-is-nearer-options` sidecar.

Open Point of View from Perception or use `--screen point-of-view`.
Press Space or click to start, then click a picture or press its
number. C opens the starting rung, tables per run, and adaptive
options. The app reads the original `POINT_OF_VIEW_*` settings and
saves edits to a `.point-of-view-options` sidecar.

Open Inside or Out? from Perception or use `--screen inside-or-out`.
Press Space or click to start. Use I or Y for Inside or Yes, O or N
for Outside or No, or choose with 1–2 or the pointer. C opens starting
rung, puzzles per run, and adaptive difficulty. The app reads the
original `INSIDE_*` settings and saves edits to an
`.inside-or-out-options` sidecar.

Open Touching? from Perception or use `--screen touching`. Press Space
or click to start. For two shapes, use A, T, O or 1–3. When counting
touching pairs, use 0–5. Both modes accept pointer input. C opens
starting rung, puzzles per run, and adaptive settings. The app reads
`TOUCHING_*` from the original profile and writes edits to a
`.touching-options` sidecar.

Open Crossings from Attention or use `--screen crossings`. Press
Space or click to start, then use 0–6 or click the crossing count. C
opens starting rung, puzzles per run, and adaptive settings. The app
reads the original `CROSSINGS_*` profile keys and writes edits to a
`.crossings-options` sidecar.

Open Time It from Perception or use `--screen time-it`. Press Space or
click to start, then press Space as the ball reaches the hidden mark.
C opens starting rung, shots per run, and adaptive settings. The app
reads the original `TIMEIT_*` profile keys and writes edits to a
`.time-it-options` sidecar.

Open Shadow Play from Perception or use `--screen shadow-play`.
Press Space or Enter to start. Hold A/D, W/S, or Q/E to rotate around the
available axes. The arrows also turn and tip the rod. Drag to turn or tip,
and use Shift or the right mouse button while dragging to roll.
Press C on the ready or results screen to set the starting rung, trials,
and adaptive difficulty. SDL reads the original `SHADOW_*` profile
keys and saves edits to a `.shadow-play-options` sidecar.

Open Captcha from Perception or use `--screen captcha`. Press Space or
click to start, then type the characters required by the rule above the
picture. Backspace or Delete erases and Enter submits. Press C before or
after a run to set the starting rung, trials, and adaptive difficulty.
SDL reads the original `CAPTCHA_*` profile keys and saves edits to a
`.captcha-options` sidecar. SDL_ttf builds use the installed typefaces
where available. SDL-only builds rotate glyphs from the bitmap font.

Open Signals from Reasoning or use `--screen signals`. Press Space or
click to start. Choose an object with 1–8 or the pointer while listening,
and send glyphs with Q–I or the pointer while speaking. Press C before or
after a run to set the starting rung, games per run, and adaptive
difficulty. SDL reads the original `SIGNALS_*` profile keys and saves
edits to a `.signals-options` sidecar.

Open Fold It from Reasoning or use `--screen fold-it`. Press Space or
click to start, then click an answer or press its number. Press C before
or after a run to set the starting rung, nets per run, and adaptive
difficulty. SDL reads the original `FOLD_IT_*` profile keys and saves
edits to a `.fold-it-options` sidecar.

Open Who Knows What? from Reasoning or use `--screen who-knows-what`.
Press Space or click to start, then click an answer or press its number.
Press C before or after a run to set the starting rung, stories per run,
and adaptive difficulty. SDL reads the original `WHO_KNOWS_WHAT_*`
profile keys and saves edits to a `.who-knows-what-options` sidecar.

Open Juggler from Attention or use `--screen juggler`. Press Space
or click to start. Hold Left or A and Right or D to move the tray. C
edits the starting rung, acts per run, and adaptive difficulty. SDL
reads the original `JUGGLER_*` profile keys and saves edits to a
`.juggler-options` sidecar.

Open Keep the Beat from Attention or use `--screen keep-the-beat`.
Press Space or click to start. Tap with Space, F, or J. Press C to
edit the starting rung, songs per run, and adaptive difficulty.
SDL reads the original `BEAT_*` profile keys and saves edits to a
`.keep-the-beat-options` sidecar.

Open Echo Cave from Attention or use `--screen echo-cave`. Press
Space or click to start. Steer with the mouse or arrows and WASD.
Press Space during flight to click. C opens the starting rung,
flights per run, and adaptive difficulty. SDL reads the original
`ECHO_*` keys and saves edits to an `.echo-cave-options` sidecar.

Open Catch from Attention or use `--screen catch`. Press Space or
click to start. Move with the mouse or the arrow and WASD keys. On
two-basket rungs, use the keys for red and the mouse for blue. Press
C to edit the starting rung, rounds per run, and adaptive difficulty.
SDL reads the original `CATCH_*` keys and saves edits to a
`.catch-options` sidecar.

Open Glider from Attention or use `--screen glider`. Press Space or
click to start. Hold Space, Up, or W to climb and release to sink.
Press C to edit the starting rung, flights per run, and adaptive
difficulty. SDL reads the original `GLIDER_*` keys and saves edits
to a `.glider-options` sidecar.

Open Lander from Attention or use `--screen lander`. Press Space or
click to start. Hold Up or W to fire and Left/A or Right/D to turn.
Press C to edit the starting rung, landings per run, and adaptive
difficulty. SDL reads the original `LANDER_*` profile keys and saves
edits to a `.lander-options` sidecar.

Open Balance from Attention or use `--screen balance`. Press Space
or click to start, then hold Left or A and Right or D to push the
cart. Stop under the lit flag with the pole upright. The app reads
the original `BALANCE_*` profile keys. Press C to edit options and
save them to a `.balance-options` sidecar.

Open Stop & Switch from Self-control or launch it with
`--screen stop-and-switch`. Press Space or click to start. Use F/Left and
J/Right to answer, and withhold your answer when the red ring appears.
Press C before or after a run to change the starting rung, blocks per run,
and adaptive difficulty. The native app reads the Python profile's
`STOP_AND_SWITCH_*` settings and saves changes in its `.stop-switch-options`
sidecar.

Open Hold It from Self-control or launch it with `--screen hold-it`.
Press Space or click to start, watch the lamps, then hold Space for the
requested duration. Release Space to submit. Press C before or after a run
to change the rung, holds per run, and adaptive difficulty. The desktop
reads the Python profile's `HOLDIT_*` settings and saves changes in its
`.hold-it-options` sidecar.

Open Video Jigsaw from Reasoning or launch it with `--screen video-jigsaw`.
It reads `.avi` clips from `datasets/ucf101` in the workshop data directory
and looks for ffmpeg beside the application before searching `PATH`.
Press Space to start, then click two tiles to
swap them, or use the arrow keys and Enter. Press C on the ready or results
screen or its Games card to edit the options. The task reads `VIDEO_JIGSAW_*` from the selected
Python INI, saves applied choices in `.video-jigsaw-options`, and uses the
existing UCF-101 `seen_jigsaw.txt` rotation.

To bundle the decoder on macOS, Linux, or Windows, set `NW_FFMPEG_BINARY`
to the target executable and `NW_FFMPEG_LICENSE` to the matching license
and notices file. Set `NW_DESKTOP_LIBRARY_LICENSES` for additional bundled
libraries. On Windows, pass any non-system decoder DLLs through
`NW_DESKTOP_DLL_DIR` as well. Each packager decodes a three-frame MPEG-4
AVI through the application using the staged executable before publishing
the output directory.

Open Maze from Planning or launch with `--screen maze`. Press Space to start
or advance, use the arrow keys or WASD to walk, and press R to restart the
current board. Press C on the Planning card or inside Maze to edit the
starting level, trial count, trail visibility, and adaptive difficulty. Maze
reads the selected Python profile’s INI and loads applied SDL choices from
the profile’s `.maze-options` file.

Open 3D Sokoban from Planning or launch with `--screen sokoban3d`. Press
Space to start or advance, use the arrow keys or WASD to walk or turn, and
press U to undo or R to restart. Press C on the Planning card or inside the
task to edit the level, warehouses per run, adaptive difficulty, goal rings,
and trap markers. The task reads `SOKO3D_*` settings from the Python profile
and saves applied choices in the profile’s `.sokoban3d-options` file.

Open Cookie Thief from Self-Control or launch with `--screen cookie-thief`.
Press Space to start or advance, X or Up to grab, Z or Down to leave, and G
or Right to reach for a golden cookie. The selected profile supplies the
starting level, round count, beat and setup durations, and adaptive difficulty.
Press C on the Self-Control card or on the task’s ready or results screen
to edit those settings. Applied choices are saved in the profile’s
`.cookie-thief-options` file.

Press U on the title screen or task hub to choose an existing profile.
The picker lists profiles with a named configuration or stats file.
Use Up and Down to move, Enter to select, or Esc to cancel. Choose
**New user** to enter a name and create the profile. The choice is saved
in the Python-compatible `defaults.ini` file.

Use `--user NAME` to select a Python profile for the current launch.
`--user default` selects the default profile even when Python remembered a
different user. Named profiles use `NAME-config.ini` and their corresponding
profile-scoped results files.

Crossword, Scrabble, Algebra, Scramble, Numberology, and Syllogism load
their original Python INI options. Saved SDL choices override the INI,
and command-line options take precedence over both.

Concentration and Recognition read their original profile INI settings.
Applying an SDL options menu saves that task’s choices beside the selected
profile as `<profile>.concentration-options` or `<profile>.recognition-options`.
SDL loads those choices on restart. The original INI remains available to the
Python application.

With `--screen nback3d`, use F1/F2 to change the level, F3/F4 to change
the base trial count, and F5/F6 to slow down or speed up the next session.
The profile’s `KEY_POSITION1` sets the match key and updates its on-screen
label. SDL translates printable ASCII and common Pyglet navigation, function,
and numeric keypad symbols. Reserved and unsupported symbols fall back to A.
Use `--trial-ms`, `--tick-ms`, and `--stim-ms` to override the trial interval,
scheduler tick, and stimulus duration. Their corresponding environment
variables are `NW_TRIAL_MS`, `NW_TICK_MS`, and `NW_STIM_MS`. Command-line
values take precedence over environment values, which take precedence over
the profile. Set the trial interval to zero to derive it from the tick count.
In headless mode, 3D N-Back disables reward music and applause. With no
explicit trial interval, it uses a 1 ms tick and a 10 ms interval by default.
A configured tick shorter than 100 ms sets the interval to ten ticks, with a
10 ms minimum.
Use `--screen nback3d --adaptive` to advance or fall back between
3D N-Back sessions. Adaptive mode reads the original profile’s score
thresholds, fallback session count, and trial-count formula. It saves the
next level and fallback count beside the profile as `<profile>.nback3d-progress`.
With `RESET_LEVEL = True`, the task restores progress from the current
training day, which starts at the profile’s `ROLLOVER_HOUR`.
When a native record is unavailable, it reads the original position-mode history
from the selected profile’s stats file. Completed sessions append compatible
summary rows to that file. Use `--statsfile` to select another. Add
`--clinical-log` to also append Python-compatible clinical summary records
to the selected user’s binary log. Press G on the ready or results screen
to view history, N to cycle through recorded game modes, M to change score
style, and G or Esc to return.

## Current boundary

The SDL desktop runs the shared title and task hub and drives the native task
controllers. `scripts/build_sdl3.sh` lists the built-in headless checks.

Marble Maze uses native MuJoCo physics and an OpenGL renderer in builds with
`NW_MUJOCO_LIBRARY`. The standard build uses the 2D display-list fallback.
`nw_marble_board_write` encodes the generated board for the native host.

The title call uses the source renderer's presentation flags that suppress
the original-only accelerator block. Consequently every visible SDL control
describes an action this port actually implements.

## What it is

This is the SDL3 consumer for the same encoded display list used by the other
host shells. Elisa generates and renders frames and manages SDL's window, clock,
and event loop through FFI. Elisa's executable entry point binds SDL and the
optional font and MuJoCo functions. It expands the command line, handles Marble
startup checks, and runs the desktop session. The build checks the SDL event
layout and pixel constants against the C headers. The headless replay harness
uses a C entry point to inject events and inspect frames. On Windows ARM64, Elisa binds the MuJoCo renderer’s OpenGL procedures.
The Windows x86 builds use a C procedure bridge.

The title, task hub, and current native task adapters have scalar C ABIs in
src/native/sdl_exports.elisa. `nw_frame_alloc` returns a real native pointer
(malloc cast to i64), so the shell casts it back before decoding. Freeform
Tetris uses the same controller kernel and display scene as the browser and
Python adapters.

## Elisa migration

Syllogism option validation, command-line parsing and settings persistence now
live in `src/native/syllogism_options*.elisa`. They call SDL3 through its native
FFI for environment, clock and file operations; writes use an exclusive temporary
file and atomic rename. `test/syllogism_sdl_options_test.py` compiles this unit
with the selected compiler and tests the C ABI directly through Python `ctypes`, without a C
implementation or a window. Frame rendering, display-list decoding and
Numberology results handling also live in Elisa. The Elisa desktop loop
polls SDL, dispatches events, and presents frames through FFI. The remaining
C presentation bindings cover the Windows OpenGL calling convention. Elisa
resolves the procedures through SDL when a context opens. TrueType
rasterization calls SDL_ttf directly from Elisa. MuJoCo model field offsets
are generated from the selected headers at build time and used by Elisa
after it verifies the linked library version.
A source-fresh Stage1 product is required for the compiler verification gate.

## Coverage

The decoder handles RECT, BORDERED_RECT, BOX, CIRCLE, ARC, LINE, TRIANGLE,
POLYGON/POLY_POINT, TEXT, VERDICT, and MARKER. Circles, triangles, and
polygons use SDL_RenderGeometry; arcs are polylines because SDL3 has no arc
primitive.

The renderer draws title sprites from PNG resources. It counts SOUND commands
as display-list events. The Elisa SDL audio binding can play overlapping WAV
cues and stop individual streams. Adaptive 3D N-Back uses the bundled applause
WAV and honors `USE_SESSION_FEEDBACK`, `USE_APPLAUSE`, and `SFX_VOLUME`.
3D N-Back reward music uses SDL_mixer through Elisa FFI. Put OGG or WAV tracks
in `res/music/advance`, `res/music/great`, and `res/music/good` beside the
binary, or point `NW_REWARD_MUSIC_DIR` at the original workshop’s music
directory. Set `NW_MIXER_LIBRARY` if SDL_mixer is outside the loader search
path. The player honors `USE_MUSIC`, `USE_MUSIC_MANUAL`, `MUSIC_VOLUME`, and
`USE_SESSION_FEEDBACK`. For packaged music, supply `NW_MIXER_LIBRARY` and `NW_MIXER_LICENSE`.
Supply `NW_REWARD_MUSIC_DIR` and `NW_REWARD_MUSIC_LICENSES` to include tracks
and their attribution notices. The package smoke test loads the staged
SDL_mixer and plays a track from each populated tier with dummy audio.
General task cue dispatch and audio set selection remain open.
The title selftest checks pooled text and the frame-end marker.

## Still to check

1. Build against the real latest Stage1 core object on each supported desktop
   platform.
2. Compare title frames against the browser at the same banner and theme.
3. Keep test/display_decode.py and src/native/display_decode.elisa consistent as the
   display-list protocol evolves.

The headless selftests prove ABI decoding, the Tetris lifecycle, and
resource-free rendering paths; they are not evidence that full visual parity
or every task's desktop adapter is done.

### Relocatable macOS build

After building with `NW_MUJOCO_LIBRARY`, run
`bash scripts/package_sdl3_macos.sh OUTPUT_DIR MUJOCO_LICENSE_DIR` from the
core directory. The output directory must be new. The MuJoCo license
directory supplies `LICENSE` and `LICENSES_THIRD_PARTY.md`. Set
`NW_SDL_LICENSE` if the SDL license is outside its pkg-config prefix.

Run the `Neural Workshop` executable inside the output directory. Keep
`lib` and `res` beside it when moving the distribution. The command
produces an ad hoc signed directory for the architecture of the input
executable. Developer ID signing and notarization are separate release steps.

### Linux distribution staging

On Linux, after building with `NW_MUJOCO_LIBRARY`, run
`bash scripts/package_sdl3_linux.sh OUTPUT_DIR MUJOCO_LICENSE_DIR SDL_LICENSE_FILE`
from the core directory. The script requires `patchelf` and a new output
directory. It bundles SDL and MuJoCo and checks that the executable resolves
the staged copies before running Marble's dummy-video self-test. The target
system supplies the OpenGL stack and other system libraries.

### Windows distribution staging

From a MinGW or MSYS2 shell on Windows, stage an existing MuJoCo-enabled
`build/nw-sdl3-mujoco.exe` with
`bash scripts/package_sdl3_windows.sh OUTPUT_DIR SDL_DLL MUJOCO_DLL MUJOCO_LICENSE_DIR SDL_LICENSE_FILE`.
Pass the DLLs used by the executable. When building with a MuJoCo import
library, set `NW_MUJOCO_DLL_DIR` if the runtime DLL lives in a different directory. The staging check runs the Marble
physics and resource self-tests with Windows system directories on PATH and
a temporary profile. Keep the DLLs, `res`, and `licenses` beside the packaged
`Neural Workshop.exe`. Marble uses SDL to resolve the OpenGL 3.3 functions from the active
Windows graphics context. The Windows build and package still require
validation on Windows. MuJoCo builds that import the Microsoft Visual C++
runtime require the matching x64 redistributable on the target machine.

### TrueType text

Set `NW_SDL_TTF=1` when building to link SDL_ttf from pkg-config. The
executable tries Courier New and platform monospace fallbacks automatically.
Set `NW_SDL_FONT` to override the selected font. An empty override selects
the bitmap renderer. TrueType glyph coverage depends on the selected font.

For macOS packaging, set `NW_DESKTOP_LIBRARY_LICENSES` to a directory
containing one license and notices file per additional bundled library,
using the dylib basename plus `.txt` (for example,
`libSDL3_ttf.0.dylib.txt`). The macOS packager follows transitive
dependencies and runs a headless task-hub screenshot for SDL_ttf builds.
On Windows, set `NW_DESKTOP_DLL_DIR` to a directory containing
`SDL3_ttf.dll` and any additional DLLs it requires. Supply the matching notices
in `NW_DESKTOP_LIBRARY_LICENSES` using the DLL basename plus `.txt`. The
Windows packager checks the staged libraries with a headless PNG capture.

On Linux, supply the SDL_ttf license and notices in
`NW_DESKTOP_LIBRARY_LICENSES`, using its ELF dependency basename plus
`.txt`. The packager bundles SDL_ttf and checks that it loads from the
staged directory. To bundle private transitive libraries such as a custom
FreeType build, provide their notices using the same naming convention.
The target system supplies the remaining shared libraries and fonts.
The TrueType package still needs an end-to-end Linux run.
