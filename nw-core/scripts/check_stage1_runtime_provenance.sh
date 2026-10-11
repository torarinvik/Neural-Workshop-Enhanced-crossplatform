#!/usr/bin/env bash
# Check the runtime carried by the selected Stage1 compiler against the
# selected Stage0 checkout without throwing away newer Stage1 runtime work.
#
# Elisa-core is the Stage0 source of truth, but Elisa-compiler is a separate
# repository and may land a small, committed runtime improvement before it is
# mirrored back there. The old check_runtime_drift.sh treated every such
# difference as a reason to copy the older runtime over the newer compiler.
# That is unsafe for the port: it can remove the very optimisations/capability
# changes the latest Stage1 product was built to use.
#
# Policy:
#   * unknown runtime-file differences still fail;
#   * reviewed latest-compiler deltas below are allowed;
#   * a dirty Stage1 runtime file is accepted only when it is byte-identical to
#     the selected Stage0 canonical file. This covers a synchronized in-progress
#     runtime change without allowing a Stage1-only edit to hide behind the
#     allowlist.
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
DEFAULT_CORE="$ROOT/../../../Go projects/Elisa-core"
if [[ ! -d "$DEFAULT_CORE/compiler" && -d "$ROOT/../stage0-elisa-compiler/compiler" ]]; then
    DEFAULT_CORE="$ROOT/../stage0-elisa-compiler"
fi
DEFAULT_STAGE1_ROOT="$ROOT/../../Elisa-compiler-port-current-23a0"
if [[ ! -d "$DEFAULT_STAGE1_ROOT" && -d "$ROOT/../stage1-elisa-compiler" ]]; then
    DEFAULT_STAGE1_ROOT="$ROOT/../stage1-elisa-compiler"
fi
CORE="${ELISA_CORE:-$DEFAULT_CORE}"
STAGE1_ROOT="${ELISA_STAGE1_ROOT:-$DEFAULT_STAGE1_ROOT}"
CANONICAL="$CORE/compiler/runtime/elisacore_std"
VENDORED="$STAGE1_ROOT/elisacore_std"

if [[ ! -d "$CANONICAL" || ! -d "$VENDORED" ]]; then
    echo "stage1 runtime provenance: runtime directory missing" >&2
    echo "  canonical: $CANONICAL" >&2
    echo "  selected:  $VENDORED" >&2
    exit 2
fi

# These are committed in the current latest Elisa-compiler main checkout and
# are intentional Stage1/runtime improvements. Keep this list content-addressed:
# a filename-only exception would allow an unrelated future edit to bypass the
# provenance gate. A new runtime file or hash must be reviewed here explicitly.
allowed_runtime_hash() {
    local name="$1" hash="$2"
    # Latest upstream Stage1's reserve-sized arena cache, added to avoid a
    # mmap/munmap pair for every compiler-call region. It keeps at most 32
    # parked reservations and only retains regions whose used prefix is at
    # most 32768 words; the prefix is zeroed before parking.
    if [[ "$name" == arena.elisa &&
          "$hash" == b02e1201234b06110a3259931b85861aac398052c4d958d1158a61efcb3147d0 ]]; then
        return 0
    fi
    # Current upstream Stage1's bounded reserve-sized Linux mmap cache. It
    # zeroes each parked region's used prefix and caps reuse at 32 entries of
    # at most 32768 used words; its static target branch does not affect WASM.
    if [[ "$name" == arena.elisa &&
          "$hash" == 43bed14a5a02f1f0750c3af0a6face7752fc136290e5740adbc673c2424e7f6e ]]; then
        return 0
    fi
    case "$name:$hash" in
        debug_referee.elisa:996e120aa02b0c3f9ea8d39f63c47aede7c4bfa7e2c44aafae8547d9f5f9e655|elisacore_runtime_concurrency.elisa:f572acf9e116b03bf23ac7a94e8c10fd58db0c94ba993f22e9122a7d30717068|stores_packed_aos.elisa:85c3b56c3e1125bc376629999dbcc0b8ff42dc1639b2ebf60f31b8de9dfae33e|stores_rows.elisa:60161bf3f22b8f0361a609b983da7c60c4db9e5c829ce29d1ca09976dc8c8cb0) return 0 ;;
        arena.elisa:0d9abc7f841d5aeb7076872fb6ccbaf09517a00b25914514e40defc37e80009d|arena.elisa:f6b0aa58dda0cc61ff90004d1e4cb2c6214cfa834a329f490363fa4ff59b0469|arena.elisa:44dac34f06e939e1bb00be0a6b258320087a9da3007278f282f8bf708614bf7b|debug_referee.elisai:60a4e3d933ea9563152dbb2599327da863c65dacbb95f6de0b748ce05f6e2bd3|profiler_hooks.elisa:8d50dc3df11bcb1a7e7f41f6f3b31ea64459761ac7a3e72707ae0f9444a4227d|runtime.elisa:a0becfaa8cca1e827f3dded69ae6c5cb9f38eec6615cb60c57e0d6cd2b7f2da4|wasm_component_runtime.elisa:9a25b3f9fd117686c015a9ffa3644589a68aab2045d72ecfb164485283e7267c|wasm_component_runtime.elisa:77e6c58242dcd774e9fb41d550b5a1a9fba15a615d143fff7ce95ed2991b1912|collections.elisa:7e804bd2c397099b88bc8dfc594b7ea1824d84366ed7b340c716a4dbdea2b1ee|collections.elisai:65fe7970474e1fc545fa7e1b018ecd0fe75d17fd5d091c39bf795f89d95b09b4|collections.elisai:1ad2dae57c316189f9e0bd3bd06d850fef6b1d3522b51e13bb5e031875ad2de9|elisacore_fileio.elisa:46be3306b5c08863b85c324bec85eaf342a076d04708926077197940ee6da504|elisacore_json.elisa:0cc4276ed37830c6c39c2a87469cb0b7cc362a4a2f09458dfc9db98949ce6a58|elisacore_runtime_concurrency.elisa:7f7b56edd3ad3aabf7ee4002e2d3e57269d924160f3c43a7eca9cb32fe67f870|elisacore_runtime_prelude.elisa:4b7bbeb487ad32c192451a959ac1a9d5940a001462ed8dab388258b1e8e833ea|elisacore_runtime_strings.elisa:0d88b70fb672677acd7f44fe857932624ea65cc00130466b887db02ff735f539|heap.elisa:57777b4a7fae7da2bfc2c1a1152437c58a27950e2accb27b9f76fbbd32cb3fdb|names.elisa:2e55c06840a331243bed3bfc5a7bb4dbebac4da396857445c1a778d81c027988|elisacore_runtime_atomics_codegen_smoke.elisa:7fc5f2cd78de24a8ab632a5ed3b56f81d7daac28b329ffc5d9213eec79a99581) return 0 ;;
    esac
    return 1
}

is_allowed() {
    local line="$1" path name hash
    case "$line" in
        Files\ *\ and\ *\ differ)
            path="${line##* and }"
            path="${path% differ}"
            name="${path##*/}"
            [[ -f "$path" ]] || return 1
            hash="$(shasum -a 256 "$path" | awk '{print $1}')"
            allowed_runtime_hash "$name" "$hash"
            ;;
        "Only in $VENDORED:"\ *)
            name="${line##*: }"
            path="$VENDORED/$name"
            [[ -f "$path" ]] || return 1
            hash="$(shasum -a 256 "$path" | awk '{print $1}')"
            allowed_runtime_hash "$name" "$hash"
            ;;
        *)
            return 1
            ;;
    esac
}

dirty_synced_runtime=""
if [[ -d "$STAGE1_ROOT/.git" || -f "$STAGE1_ROOT/.git" ]]; then
    dirty_runtime="$(git -C "$STAGE1_ROOT" -c core.hooksPath=/dev/null status --porcelain -- elisacore_std)"
    if [[ -n "$dirty_runtime" ]]; then
        while IFS= read -r entry; do
            [[ -z "$entry" ]] && continue
            relative="${entry:3}"
            case "$relative" in
                elisacore_std/*) ;;
                *)
                    echo "stage1 runtime provenance: selected compiler runtime has an unsupported dirty entry" >&2
                    echo "  $entry" >&2
                    exit 1
                    ;;
            esac
            canonical_file="$CANONICAL/${relative#elisacore_std/}"
            vendored_file="$VENDORED/${relative#elisacore_std/}"
            if [[ ! -f "$canonical_file" || ! -f "$vendored_file" ]] || ! cmp -s "$canonical_file" "$vendored_file"; then
                echo "stage1 runtime provenance: selected compiler runtime is dirty and differs from Stage0 canonical" >&2
                echo "  $entry" >&2
                exit 1
            fi
            dirty_synced_runtime+="${relative#elisacore_std/}"$'\n'
        done <<< "$dirty_runtime"
    fi
fi

report="$(mktemp "${TMPDIR:-/tmp}/stage1-runtime-provenance.XXXXXX")"
trap 'rm -f "$report"' EXIT

if diff -rq "$CANONICAL" "$VENDORED" >"$report" 2>&1; then
    echo "stage1 runtime provenance: selected vendor is byte-identical to Stage0 canonical"
    exit 0
fi

unexpected=0
while IFS= read -r line; do
    if is_allowed "$line"; then
        continue
    fi
    echo "stage1 runtime provenance: unexpected drift:" >&2
    echo "  $line" >&2
    unexpected=1
done < "$report"

if (( unexpected )); then
    echo "stage1 runtime provenance: review the new difference before building" >&2
    exit 1
fi

if [[ -n "$dirty_synced_runtime" ]]; then
    echo "stage1 runtime provenance: accepted byte-identical synchronized runtime worktree"
    printf '%s' "$dirty_synced_runtime"
fi
echo "stage1 runtime provenance: accepted committed latest-compiler deltas"
cat "$report"
