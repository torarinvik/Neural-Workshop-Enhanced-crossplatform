#!/usr/bin/env bash
# Capture and strictly compare the same original/native Python Marble state.
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE_ROOT="${NEURAL_WORKSHOP_SOURCE_ROOT:-$ROOT/../../../Python Projects/neural-workshop-enhanced}"
if [[ -x "$SOURCE_ROOT/.venv/bin/python3" ]]; then
    REFERENCE_PYTHON="$SOURCE_ROOT/.venv/bin/python3"
else
    REFERENCE_PYTHON="$ROOT/build/marble-oracle-venv/bin/python"
fi
COMPARATOR_PYTHON="${NW_MARBLE_COMPARATOR_PYTHON:-python3}"
OUTPUT="$ROOT/output/playwright"
RUNG="${NW_MARBLE_PAIR_RUNG:-1}"
FRAMES="${NW_MARBLE_PAIR_FRAMES:-12}"
THEME="${NW_MARBLE_PAIR_THEME:-light}"
WIDTH="${NW_MARBLE_PAIR_WIDTH:-912}"
HEIGHT="${NW_MARBLE_PAIR_HEIGHT:-684}"
DPR="${NW_MARBLE_PAIR_DPR:-2}"
RESIZE_TO="${NW_MARBLE_PAIR_RESIZE_TO:-}"
OUTCOME="${NW_MARBLE_PAIR_OUTCOME:-rolling}"
if [[ "$THEME" != light && "$THEME" != dark ]]; then
    echo "NW_MARBLE_PAIR_THEME must be light or dark" >&2
    exit 2
fi
if [[ ! "$WIDTH" =~ ^[0-9]+$ || ! "$HEIGHT" =~ ^[0-9]+$ ||
      "$WIDTH" -lt 320 || "$HEIGHT" -lt 240 ]]; then
    echo "NW_MARBLE_PAIR_WIDTH/HEIGHT must be integers >= 320x240" >&2
    exit 2
fi
if [[ "$DPR" != 1 && "$DPR" != 2 ]]; then
    echo "NW_MARBLE_PAIR_DPR must be 1 or 2" >&2
    exit 2
fi
case "$OUTCOME" in
    rolling|won|lost|done) ;;
    *) echo "NW_MARBLE_PAIR_OUTCOME must be rolling, won, lost, or done" >&2; exit 2 ;;
esac
if [[ "$OUTCOME" != rolling && "$RUNG" != 1 ]]; then
    echo "terminal native/source captures currently require rung 1" >&2
    exit 2
fi
if [[ -n "$RESIZE_TO" && ! "$RESIZE_TO" =~ ^[0-9]+x[0-9]+$ ]]; then
    echo "NW_MARBLE_PAIR_RESIZE_TO must look like 800x600" >&2
    exit 2
fi
if [[ -n "$RESIZE_TO" ]]; then
    RESIZE_WIDTH="${RESIZE_TO%x*}"
    RESIZE_HEIGHT="${RESIZE_TO#*x}"
    if [[ "$RESIZE_WIDTH" -lt 640 || "$RESIZE_HEIGHT" -lt 480 ]]; then
        echo "NW_MARBLE_PAIR_RESIZE_TO must be at least 640x480" >&2
        exit 2
    fi
fi
PYGLET_DPI_SCALING=real
if [[ "$DPR" == 2 ]]; then
    PYGLET_DPI_SCALING=platform
fi
if [[ "$RUNG" == 1 && "$FRAMES" == 12 && "$THEME" == light && "$WIDTH" == 912 && "$HEIGHT" == 684 && "$DPR" == 2 ]]; then
    NAME="native-python-roll12-912x684"
elif [[ "$THEME" == light && "$WIDTH" == 912 && "$HEIGHT" == 684 && "$DPR" == 2 ]]; then
    NAME="native-python-r${RUNG}-east-${FRAMES}f-912x684"
else
    NAME="native-python-r${RUNG}-east-${FRAMES}f-${THEME}-dpr${DPR}-${WIDTH}x${HEIGHT}"
fi
if [[ "$OUTCOME" != rolling ]]; then
    NAME="native-python-${OUTCOME}-r${RUNG}-${THEME}-dpr${DPR}-${WIDTH}x${HEIGHT}"
fi
if [[ -n "$RESIZE_TO" ]]; then
    NAME="${NAME}-resize-${RESIZE_TO}"
fi

if [[ ! -x "$REFERENCE_PYTHON" ]]; then
    echo "missing Marble reference Python: $REFERENCE_PYTHON" >&2
    exit 2
fi
if [[ ! -f "$SOURCE_ROOT/neural_workshop/marblemaze.py" ]]; then
    echo "missing original Neural Workshop source: $SOURCE_ROOT" >&2
    echo "Set NEURAL_WORKSHOP_SOURCE_ROOT to the reference checkout." >&2
    exit 2
fi

mkdir -p "$OUTPUT"
SOURCE_REPLAY_ARGS=(
    --seed 17 --rung "$RUNG" --width "$WIDTH" --height "$HEIGHT" --theme "$THEME"
    --outcome "$OUTCOME"
)
if [[ "$OUTCOME" == rolling ]]; then
    SOURCE_REPLAY_ARGS+=(--move E --move-frames "$FRAMES" --board-abi-f32)
fi
if [[ -n "$RESIZE_TO" ]]; then
    SOURCE_REPLAY_ARGS+=(--resize-to "$RESIZE_TO")
fi
NEURAL_WORKSHOP_SOURCE_ROOT="$SOURCE_ROOT" \
NW_MARBLE_PAIR_EXPECT_DPR="$DPR" \
PYGLET_DPI_SCALING="$PYGLET_DPI_SCALING" "$REFERENCE_PYTHON" \
    "$ROOT/test/marble_source_capture.py" \
    --source-root "$SOURCE_ROOT" \
    --png "$OUTPUT/mm-source-$NAME.png" \
    --metadata "$OUTPUT/mm-source-$NAME.json" \
    "${SOURCE_REPLAY_ARGS[@]}"

NEURAL_WORKSHOP_SOURCE_ROOT="$SOURCE_ROOT" \
NW_MARBLE_PAIR_EXPECT_DPR="$DPR" \
PYGLET_DPI_SCALING="$PYGLET_DPI_SCALING" \
NW_MARBLE_NATIVE_RUNG="$RUNG" \
NW_MARBLE_NATIVE_FRAMES="$FRAMES" \
NW_MARBLE_NATIVE_THEME="$THEME" \
NW_MARBLE_NATIVE_WIDTH="$WIDTH" \
NW_MARBLE_NATIVE_HEIGHT="$HEIGHT" \
NW_MARBLE_NATIVE_RESIZE_TO="$RESIZE_TO" \
NW_MARBLE_NATIVE_OUTCOME="$OUTCOME" \
NW_MARBLE_RENDER_CAPTURE="$OUTPUT/mm-$NAME.png" \
NW_MARBLE_RENDER_METADATA="$OUTPUT/mm-$NAME.json" \
    bash "$ROOT/scripts/test_marble_native_render.sh"

"$COMPARATOR_PYTHON" "$ROOT/test/marble_render_pair_test.py" \
    "$OUTPUT/mm-source-$NAME.png" "$OUTPUT/mm-$NAME.png" \
    --reference-metadata "$OUTPUT/mm-source-$NAME.json" \
    --candidate-metadata "$OUTPUT/mm-$NAME.json" \
    --require-synchronized --require-scene-state --pixel-threshold 10 --json
