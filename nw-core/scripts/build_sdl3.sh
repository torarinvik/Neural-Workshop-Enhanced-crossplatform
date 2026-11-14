#!/usr/bin/env bash
# Build the native SDL3 desktop shell.
#
# The SDL shell uses an explicit native export unit rather than the browser
# WASM export surface. The browser unit contains a wasm32 memory intrinsic and
# the full controller registry; native controllers are added to the SDL unit
# with their own lifecycle and frame-buffer ABI.
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT/scripts/env.sh"
mkdir -p "$ROOT/build"

PROJECTS_ROOT="$(cd -- "$ROOT/../.." && pwd)"
LATEST_ROOT="${ELISA_LATEST_STAGE1_ROOT:-$ELISA_STAGE1_ROOT}"
LATEST_BIN="${ELISA_LATEST_STAGE1_BIN:-$ELISA_STAGE1_BIN}"

SDL_CFLAGS="$(pkg-config --cflags sdl3 2>/dev/null || echo "-I/opt/homebrew/include")"
SDL_LIBS="$(pkg-config --libs sdl3 2>/dev/null || echo "-L/opt/homebrew/lib -lSDL3")"

if [[ -n "${ELISA_SDL_COMPILER:-}" ]]; then
    NATIVE_COMPILER="$ELISA_SDL_COMPILER"
    RUNTIME_ROOT="${ELISA_SDL_RUNTIME_ROOT:-$ELISA_STAGE1_ROOT}"
else
    if [[ ! -x "$LATEST_ROOT/scripts/elisac_stage1.sh" || ! -x "$LATEST_BIN" ]]; then
        echo "build_sdl3.sh: latest Elisa Stage1 checkout/product missing" >&2
        echo "  checkout: $LATEST_ROOT" >&2
        echo "  product:  $LATEST_BIN" >&2
        echo "Set ELISA_SDL_COMPILER for an explicit override, or set" >&2
        echo "ELISA_LATEST_STAGE1_ROOT and ELISA_LATEST_STAGE1_BIN." >&2
        exit 2
    fi
    stale_source="$(python3 "$ROOT/scripts/stage1_fresh.py" \
        "$LATEST_ROOT" "$LATEST_BIN" 2>/dev/null || true)"
    if [[ -n "$stale_source" ]]; then
        echo "build_sdl3.sh: latest Elisa Stage1 product is stale: $stale_source" >&2
        echo "Re-seed/rebuild the latest Elisa compiler product before building." >&2
        exit 2
    fi
    latest_head="$(git -C "$LATEST_ROOT" -c core.hooksPath=/dev/null rev-parse HEAD 2>/dev/null || true)"
    latest_origin_head="$(git -C "$LATEST_ROOT" -c core.hooksPath=/dev/null rev-parse --verify refs/remotes/origin/main 2>/dev/null || true)"
    if [[ -n "$latest_head" && -n "$latest_origin_head" ]]; then
        latest_behind="$(git -C "$LATEST_ROOT" -c core.hooksPath=/dev/null rev-list --count "$latest_head..$latest_origin_head" 2>/dev/null || echo 0)"
        if [[ "$latest_behind" != 0 ]]; then
            echo "build_sdl3.sh: selected Elisa Stage1 checkout is $latest_behind commit(s) behind origin/main" >&2
            exit 2
        fi
    fi
    NATIVE_COMPILER="$LATEST_BIN"
    RUNTIME_ROOT="${ELISA_SDL_RUNTIME_ROOT:-$LATEST_ROOT}"
fi

printf 'Elisa Stage1 compiler: %s\n' "$NATIVE_COMPILER"

SOURCE_TREE_PARENT="$(mktemp -d "$ROOT/build/sdl3-sources.XXXXXX")"
SOURCE_TREE="$SOURCE_TREE_PARENT/source"
NATIVE_LINK_OBJECT="$SOURCE_TREE_PARENT/nwcore_native_link.o"
trap 'rm -rf -- "$SOURCE_TREE_PARENT"' EXIT INT TERM HUP
RUNTIME_OBJ="${ELISA_SDL_RUNTIME_OBJ:-$RUNTIME_ROOT/build/runtime/elisacore_runtime.o}"
if [[ ! -f "$RUNTIME_OBJ" ]]; then
    echo "build_sdl3.sh: selected Stage1 runtime object is missing: $RUNTIME_OBJ" >&2
    echo "Set ELISA_SDL_RUNTIME_OBJ to the matching elisacore_runtime.o." >&2
    exit 2
fi
python3 "$ROOT/scripts/prepare_runtime_sources.py" \
    "$ROOT" "$SOURCE_TREE" "$RUNTIME_ROOT"

"$NATIVE_COMPILER" -emit obj -O2 -o "$ROOT/build/nwcore_native.o" \
    "$SOURCE_TREE/src/native/sdl_exports.elisa"

# Keep the original object for inspection and future consumers. The private
# link object redirects the eight common arena/cache cells to the selected
# runtime object's single process-wide definitions.
python3 "$ROOT/scripts/prepare_native_object.py" \
    "$ROOT/build/nwcore_native.o" "$NATIVE_LINK_OBJECT"

RUNTIME_LINK_FLAGS=()
case "$(uname -s)" in
    Darwin) RUNTIME_LINK_FLAGS=(-Wl,-dead_strip) ;;
    Linux|MINGW*|MSYS*|CYGWIN*) RUNTIME_LINK_FLAGS=(-Wl,--allow-multiple-definition) ;;
esac

cc -O2 -std=c11 $SDL_CFLAGS \
    -o "$ROOT/build/nw-sdl3" \
    "$ROOT/shells/sdl3/main.c" \
    "$NATIVE_LINK_OBJECT" \
    "$RUNTIME_OBJ" \
    "${RUNTIME_LINK_FLAGS[@]}" \
    $SDL_LIBS

# Prove it RUNS, not just that it linked. --selftest drives the same decode and
# frame-walk the window path uses, with no SDL_Init, so it works headless -- and
# it checks the pooled STRINGS, not just the command count: the wasm build
# corrupted exactly those while geometry stayed correct, so a check that counted
# commands would have passed straight through that bug.
"$ROOT/build/nw-sdl3" --selftest 180
"$ROOT/build/nw-sdl3" --selftest-long-text
"$ROOT/build/nw-sdl3" --selftest-3d-maze
"$ROOT/build/nw-sdl3" --selftest-taskhub
"$ROOT/build/nw-sdl3" --selftest-sokoban
"$ROOT/build/nw-sdl3" --selftest-monkey-ladder
"$ROOT/build/nw-sdl3" --selftest-nback3d
"$ROOT/build/nw-sdl3" --selftest-tetris
"$ROOT/build/nw-sdl3" --selftest-mr-time
"$ROOT/build/nw-sdl3" --selftest-graph-mapping
"$ROOT/build/nw-sdl3" --selftest-matrix-reasoning
"$ROOT/build/nw-sdl3" --selftest-marble
"$ROOT/build/nw-sdl3" --selftest-in-the-dark
"$ROOT/build/nw-sdl3" --selftest-fog
"$ROOT/build/nw-sdl3" --selftest-removals
"$ROOT/build/nw-sdl3" --selftest-custody
"$ROOT/build/nw-sdl3" --selftest-concentration
"$ROOT/build/nw-sdl3" --selftest-recognition
"$ROOT/build/nw-sdl3" --selftest-trivia
"$ROOT/build/nw-sdl3" --selftest-reflex
"$ROOT/build/nw-sdl3" --selftest-algebra
"$ROOT/build/nw-sdl3" --selftest-syllogism
"$ROOT/build/nw-sdl3" --selftest-algebra-options
"$ROOT/build/nw-sdl3" --selftest-numberology
python3 "$ROOT/test/numberology_sdl_results_test.py" --binary "$ROOT/build/nw-sdl3"
python3 "$ROOT/test/syllogism_sdl_options_test.py"
"$ROOT/build/nw-sdl3" --selftest-jigsaw
"$ROOT/build/nw-sdl3" --selftest-sudoku
"$ROOT/build/nw-sdl3" --selftest-task-options
"$ROOT/build/nw-sdl3" --selftest-go
"$ROOT/build/nw-sdl3" --selftest-crossed-wires
"$ROOT/build/nw-sdl3" --selftest-scrabble
"$ROOT/build/nw-sdl3" --selftest-scramble
"$ROOT/build/nw-sdl3" --selftest-crossword
"${PYTHON_BIN:-python3}" "$ROOT/test/crossword_native_settings_test.py"
"${PYTHON_BIN:-python3}" "$ROOT/test/scrabble_native_settings_test.py"
"${PYTHON_BIN:-python3}" "$ROOT/test/scramble_native_settings_test.py"
"$ROOT/build/nw-sdl3" --selftest-ncup-monte
"$ROOT/build/nw-sdl3" --selftest-moving-targets
"$ROOT/build/nw-sdl3" --selftest-lookout
"$ROOT/build/nw-sdl3" --selftest-pursuit
"$ROOT/build/nw-sdl3" --selftest-out-of-sight
"$ROOT/build/nw-sdl3" --selftest-buzz-wire
"$ROOT/build/nw-sdl3" --selftest-donkey
"$ROOT/build/nw-sdl3" --selftest-count

printf 'built %s\n' "$ROOT/build/nw-sdl3"
printf 'run it with: %s\n' "$ROOT/build/nw-sdl3"
printf '  --screen 3d-maze: Space/Enter=start, arrows=walk/turn, R=restart\n'
printf '  --screen taskhub: arrows=navigate, Space/Enter=launch implemented native controllers\n'
printf '  --screen sokoban: Space/Enter=start, arrows=move, U=undo, R=restart\n'
printf '  --screen monkey-ladder: Space/Enter=start/commit, arrows=move cursor\n'
printf '  --screen nback3d: Space/Enter=start, A=match, P=pause, R=restart\n'
printf '  --screen tetris: Space/Enter=start/drop, arrows=move/rotate, 1-6=select, R=restart\n'
printf '  --screen mr-time: Space/Enter=start/submit, digits/decimal/backspace=answer\n'
printf '  --screen graph-mapping: Space/Enter=start, Y/S/N/D or arrows=answer\n'
printf '  --screen matrix-reasoning: Space/Enter=start, 1-8=answer\n'
printf '  --screen marble: Space=start/next, arrows=hold tilt, L=level, R=restart\n'
printf '  --screen in-the-dark: Space/Enter=start, 1-5=answer\n'
printf '  --screen fog-of-war: Space/Enter=start, arrows=walk\n'
printf '  --screen removals: Space/Enter=start, 1-5=answer\n'
printf '  --screen chain-of-custody: Space/Enter=start, arrows=claw, Z=grab/drop\n'
printf '  --screen concentration: Space=start, arrows=cursor, Enter=select\n'
printf '  --screen recognition: Space=start, left=seen, right=new\n'
printf '  --screen trivia: Space=start/submit/advance, arrows=choice, 1-8=answer\n'
printf '  --screen reflex: Space/Enter=start, click=target, Esc=menu\n'
printf '  --screen algebra: Space=start/next, type answer, Enter=submit, O=options\n'
printf '    Algebra options: --algebra-level N --algebra-trials N --algebra-no-working --algebra-no-adaptive\n'
printf '  --screen numberology: Space=start, type answer, Enter=submit, O=options\n'
printf '    --numberology-level N --numberology-trials N --numberology-no-adaptive\n'
printf '  --screen jigsaw: Space=start, 0-9=select tile, Enter=advance\n'
printf '    Jigsaw options: --jigsaw-side N --jigsaw-puzzles N --jigsaw-no-adaptive --jigsaw-no-preview --jigsaw-mark-placed\n'
printf '  --screen sudoku: Space=start, arrows=cursor, 1-9/A-G=write, 0/Backspace/Delete=erase, N=pencil\n'
printf '    Sudoku options: --sudoku-level N --sudoku-puzzles N --sudoku-no-clashes --sudoku-no-adaptive\n'
printf '  --screen go: Space=start/answer/next, arrows=cursor, mouse=intersection\n'
printf '  --screen scrabble: Space=start/next, 1-7=lay, arrows=move, Tab=turn, Enter=play, mouse=select/lay\n'
printf '    Scrabble options: --scrabble-level N --scrabble-trials N --scrabble-no-premiums --scrabble-no-adaptive --scrabble-lexicon PATH\n'
printf '  --screen crossword: Space=start/next, letters=write, arrows=move, Tab=turn, mouse=select/turn\n'
printf '    Crossword options: --crossword-level N --crossword-trials N --crossword-no-mistakes --crossword-no-adaptive --crossword-lexicon PATH\n'
printf '  --screen ncup-monte: Space=start/next, mouse=choose cup\n'
printf '  --screen moving-targets: Space=start, mouse=select tracked balls\n'
printf '  --screen lookout: Space=start, F=form, J=colour\n'
printf '  --screen pursuit: Space=start, arrows/mesh=follow the shape\n'
printf '  --screen out-of-sight: Space=start, J=mine, F=not mine\n'
printf '  --screen buzz-wire: Space=start, arrows/W/S=move, I/K/J/L=turn, Shift=brace\n'
printf '  --screen donkey: Space=start, arrows/Space=swerve\n'
printf '  title mode: space=play/pause, right arrow=step, q/esc=quit\n'
