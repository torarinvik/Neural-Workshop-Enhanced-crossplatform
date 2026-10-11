#!/usr/bin/env bash
# Build the production browser artifact with the newest local Elisa Stage1
# checkout, then run the complete artifact-level gate. The ordinary
# build_wasm.sh remains the Stage0 oracle build; this entry point is explicit so
# a later gate cannot accidentally replace the production WASM with Stage0.
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
PROJECTS_ROOT="$(cd -- "$ROOT/../.." && pwd)"
LATEST_ROOT="${ELISA_LATEST_STAGE1_ROOT:-${ELISA_STAGE1_ROOT:-$PROJECTS_ROOT/Elisa-compiler-port-current-23a0}}"
LATEST_BIN="${ELISA_LATEST_STAGE1_BIN:-${ELISA_STAGE1_BIN:-$LATEST_ROOT/bin/elisac-stage1}}"

if [[ ! -x "$LATEST_ROOT/scripts/elisac_stage1.sh" || ! -x "$LATEST_BIN" ]]; then
    echo "build_latest_stage1_wasm.sh: latest Elisa Stage1 checkout/product missing" >&2
    echo "  checkout: $LATEST_ROOT" >&2
    echo "  product:  $LATEST_BIN" >&2
    echo "Set ELISA_LATEST_STAGE1_ROOT and ELISA_LATEST_STAGE1_BIN explicitly." >&2
    exit 2
fi

stale_source="$(python3 "$ROOT/scripts/stage1_fresh.py" \
    "$LATEST_ROOT" "$LATEST_BIN" 2>/dev/null || true)"
if [[ -n "$stale_source" ]]; then
    echo "build_latest_stage1_wasm.sh: Stage1 product is stale: $stale_source" >&2
    echo "Re-seed/rebuild the latest Elisa compiler product before building." >&2
    exit 2
fi

head="$(git -C "$LATEST_ROOT" -c core.hooksPath=/dev/null rev-parse HEAD 2>/dev/null || echo unknown)"
branch="$(git -C "$LATEST_ROOT" -c core.hooksPath=/dev/null rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)"
origin_head="$(git -C "$LATEST_ROOT" -c core.hooksPath=/dev/null rev-parse --verify refs/remotes/origin/main 2>/dev/null || true)"
if [[ -n "$origin_head" ]]; then
    behind_origin="$(git -C "$LATEST_ROOT" -c core.hooksPath=/dev/null rev-list --count "$head..$origin_head" 2>/dev/null || echo 0)"
    if [[ "$behind_origin" != 0 ]]; then
        echo "build_latest_stage1_wasm.sh: compiler checkout is $behind_origin commit(s) behind origin/main" >&2
        echo "  local:  $head" >&2
        echo "  origin: $origin_head" >&2
        echo "Fetch and review the newer Elisa compiler before building the port." >&2
        exit 2
    fi
fi
fingerprint="$(python3 "$ROOT/scripts/source_fingerprint.py" "$LATEST_ROOT")"
sha256_file() {
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum "$1" | awk '{print $1}'
    else
        shasum -a 256 "$1" | awk '{print $1}'
    fi
}
product_hash="$(sha256_file "$LATEST_BIN")"

ARTIFACT="${NW_STAGE1_WASM_ARTIFACT:-$ROOT/build/nwcore.wasm}"
ARTIFACT_DIR="$(dirname -- "$ARTIFACT")"
ARTIFACT_NAME="$(basename -- "$ARTIFACT")"
mkdir -p "$ARTIFACT_DIR"
# Keep the build transactional, but link under the final basename: wasm-ld
# records the output name in the module's `name` section. A random candidate
# filename would make otherwise identical builds differ and would leak the
# temporary name into the shipped module.
CANDIDATE_DIR="$(mktemp -d "$ARTIFACT_DIR/.nwcore-stage1-candidate.XXXXXXXX")"
CANDIDATE="$CANDIDATE_DIR/$ARTIFACT_NAME"
cleanup_candidate() {
    if [[ -n "${CANDIDATE:-}" && -e "$CANDIDATE" ]]; then
        rm -f -- "$CANDIDATE"
    fi
    if [[ -n "${CANDIDATE_DIR:-}" && -d "$CANDIDATE_DIR" ]]; then
        rmdir -- "$CANDIDATE_DIR" 2>/dev/null || true
    fi
}
trap cleanup_candidate EXIT INT TERM HUP

echo "latest Elisa Stage1: $LATEST_ROOT @ $head ($branch)"
if [[ -n "$origin_head" ]]; then
    echo "origin/main: $origin_head (local is not behind)"
fi
echo "source fingerprint: $fingerprint"
echo "product SHA-256: $product_hash"

# env.sh still validates the port's pinned Stage0/runtime files because they
# are needed by the shared test harness. They are not used to emit this object;
# the explicit Stage1 root/product below are the compiler that builds it.
# The port-side content-aware snapshot above is authoritative; the upstream
# wrapper still uses mtime-only checking and would reject timestamp-only churn.
ELISA_ALLOW_STALE_STAGE1=1 \
ELISA_STAGE1_ROOT="$LATEST_ROOT" \
ELISA_STAGE1_BIN="$LATEST_BIN" \
NW_STAGE1_WASM_OBJECT="${NW_STAGE1_WASM_OBJECT:-$ROOT/build/nwcore_wasm.o}" \
NW_STAGE1_WASM_ARTIFACT="$CANDIDATE" \
bash "$ROOT/scripts/build_stage1_wasm.sh"

# The latest compiler checkout is shared with other work.  A concurrent
# reseed, checkout, or source edit during the build would make the emitted
# artifact impossible to attribute to the provenance printed above.  The
# build itself is intentionally allowed to finish so it cannot leave a
# half-written object; reject the result and require a quiescent rerun.
post_head="$(git -C "$LATEST_ROOT" -c core.hooksPath=/dev/null rev-parse HEAD 2>/dev/null || echo unknown)"
post_origin_head="$(git -C "$LATEST_ROOT" -c core.hooksPath=/dev/null rev-parse --verify refs/remotes/origin/main 2>/dev/null || true)"
post_fingerprint="$(python3 "$ROOT/scripts/source_fingerprint.py" "$LATEST_ROOT")"
post_product_hash="$(sha256_file "$LATEST_BIN")"
if [[ "$post_head" != "$head" ||
      "$post_origin_head" != "$origin_head" ||
      "$post_fingerprint" != "$fingerprint" ||
      "$post_product_hash" != "$product_hash" ]]; then
    echo "build_latest_stage1_wasm.sh: compiler provenance changed during the build" >&2
    echo "  before: HEAD=$head origin/main=${origin_head:-<absent>} fingerprint=$fingerprint product=$product_hash" >&2
    echo "  after:  HEAD=$post_head origin/main=${post_origin_head:-<absent>} fingerprint=$post_fingerprint product=$post_product_hash" >&2
    echo "The artifact was not promoted; quiesce the Elisa compiler checkout and rerun." >&2
    exit 2
fi

mv -f -- "$CANDIDATE" "$ARTIFACT"
rmdir -- "$CANDIDATE_DIR"
CANDIDATE=""
CANDIDATE_DIR=""
echo "promoted verified latest-Stage1 artifact: $ARTIFACT"

echo "compiler provenance unchanged for the complete build"
