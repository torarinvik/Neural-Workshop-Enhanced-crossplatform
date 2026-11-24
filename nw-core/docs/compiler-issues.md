# Compiler issues affecting the Neural Workshop port

This file tracks compiler defects found while porting, their minimal
reproductions, fixes, and the identity of the binaries actually exercised.
“Fixed” means the stated reproducer and its named verification passed; it does
not certify unrelated compiler behavior.

## Inferred generic protocol-bound enforcement in Stage1 (2026-10-05)

**Classification: Stage1 compiler semantic bug; fixed on the newest checked
upstream main and used for the current browser artifact.** Upstream
`2691a64c7522c94eee0d5b0b930d1995c7376a3c` incorrectly accepted a direct
generic call when it inferred a concrete argument type that did not implement
the callee's protocol bound. Stage0 correctly rejected the same program with
`type "int" does not satisfy required interface fact "Describe" for call to
"via_type_param"`. This was not an invalid port-Elisa call to rewrite: Stage1
was missing a semantic validation on its inferred-specialization path.

The fix is in the clean durable Stage1 clone
`/workspace/Elisa-compiler-upstream-inferred-bound-fix`,
branch `codex/fix-inferred-protocol-bounds`, at that exact upstream commit.
`src/semantic/check_generic_interface_bounds.elisa` checks inferred actual
argument types against callee bounds, and
`src/semantic/check_firm_arg_type_mismatch.elisa` carries the caller's
declaration scope through traversal so an unrelated same-named type parameter
cannot satisfy the bound. Positive/negative fixtures cover invalid inferred
literals, unbounded forwarded/explicit type parameters, concrete valid calls,
and correctly bounded forwarding. The focused
`test/parity/generic_inferred_protocol_bound_smoke.sh` passes on fresh Stage0
and patched Stage1: both reject invalid calls with the expected diagnostic,
Stage1 emits no object for them, and both accept the positive cases. Stage1
product SHA-256 is
`c1c1c7343d3cc544e1bcdb4f54a5e85a3c156e18c85874dc7c83e71aaa80ca7b`; source
fingerprint `a899d51329f24b78c12990a726c9dc5a506a56e192dedc15122ce2ddb3ed03f8`.

The broad assignment/type smoke reports zero false positives. Driver
acceptance has two bare-mode Stage1-only rejects, zero accept-gaps, within the
existing reject-gap ratchet of six; with the standard library it has zero
disagreements. This closes the targeted unsound acceptance, not every possible
Stage0/Stage1 semantic or diagnostic difference. Do not weaken the existing
acceptance ratchet.

The first latest-Stage1 browser build then exposed a distinct port integration
bug: `nw-core/src/wasm/wasm_exports.elisa` selected runtime files by a hard-coded
`Elisa-compiler-latest` sibling path, while the build selected a newer Stage1
tree. The old runtime lacked explicit `Unsafe.PointerCast` grants now required
by Stage1. The source now uses `@ELISA_STAGE1_ROOT@` markers. Corpus
modules carry them too, so both WASM build scripts materialize the whole
source tree with `prepare_runtime_sources.py`, as `check.sh` and
`build_sdl3.sh` do, and compile the export surface from that copy;
`prepare_wasm_exports.py` and its focused regression remain for the Python
module build. No shared compiler checkout was changed.

The final-name artifact `nw-core/build/nwcore.wasm` was built with matching
Stage0 `6a0628cc48a7e019ed023c835b379fb55522ff1e`, patched Stage1 above, and
runtime SHA-256
`b51e6114f0576681e432e1162a3dbdcdac46c140d3b7e7256c0069be0bd11897`. Its
SHA-256 is `4bd7b4217c2fd57b88ee19db62d9ccd6f1f4717414f5500692ef5fefcf9b79c5`;
the complete browser artifact suite passes, including all ported games and
only 3D N-back. Marble's 320-board 3.0 mm hole/wall and collar-clearance test,
80 board/MJCF cases, 80 generated sessions, 3 adaptive sessions, and 275
trajectory scenarios / 33,982 frame states pass without tolerance changes.
The exact 80-case original-Python per-frame/contact/result replay also passes
against the promoted bytes with no tolerance changes. Evidence is at
`nw-core/output/verification/marble-source-play-stage1-main2691-20261005/`;
source comparison log SHA-256
`17407bf9127c82cad00d3029866365de732be97b976f8dda9c1a95a6425d7dcc`.

## Current FFI boundary correction (2026-10-03)

Live upstream `main` refs were re-queried before rebuilding: Elisa-core Stage0
`ffbf5de5ca37e37a9dc7841627344c9d5371a400` and Elisa-compiler Stage1
`f4aefeb0ec0b3e13230a28f05053cb7a3a916dba`. Clean shallow clones of those
exact refs produced a private, fresh toolchain (Stage0 SHA-256
`97b687e5258f4182201db100821353913b7cf921f369d96d297f59b6d616f38a`, Stage1
`f838153e1f55b76ce354ba626841fb211ee421051f11321fb401f5760b93d8da`, runtime
`b28bf119bdfb7bec852692732c54b0f316f76eb2ea52c0d5879a8ec6d9e569f5`). Both
checkouts were clean at build time; Stage1 freshness and runtime provenance
checks pass. The only Stage1-vendored runtime delta is its bounded-byte
`unsafe_sview_bounded_bytes` helper, whose exact source hash is now reviewed by
`nw-core/scripts/check_stage1_runtime_provenance.sh`; the upstream
`wasm_component_runtime_smoke.sh` passes with both compiler generations.

The full port differential run exposed two Stage0 compile errors in `stats`
and `config`, both pointing to `stats.elisa`'s `strtod` end-pointer call. This
was not a compiler rejection of an invalid program: the C `char **endptr`
argument had been declared as Elisa `mutable u8&?&`, which made the borrow
checker treat the local output-pointer slot as a longer-lived writable
reference. The libc boundary now follows the current runtime convention and
declares that ABI argument as opaque `u8&?`, passing
`(&tail_pointer).cast[u8&?]` inside the existing trusted pointer-cast block.
`strtod` writes the end pointer into that local slot and returns; it does not
retain the slot or the input buffer. No compiler escape rule was weakened.

Verification on the exact fresh Stage0/Stage1 pair: `stats` passes 32/32
differential cases on both stages; `config` passes 342/342 on both. These
focused cases are part of a full current `nw-core/scripts/check.sh` pass:
127/127 suites and 82,961 cases on each compiler generation, with zero
failures. Results are under
`/private/tmp/nw-current-toolchain.KbEFPQ/full-check/check.qCVk7i/`. The fresh
Stage1 `wasm_component_runtime_smoke.sh` also passes. These results close this
FFI typing/parity issue and establish a current full differential baseline;
the compiler acceptance and diagnostic gates below remain independent and
must still be assessed on their own evidence.

**Current validation checkpoint (2026-09-26):** the selected local
`Elisa-compiler` checkout is at `a49aad83ef6389afcbdd07590b13bb6c5a07e6a7`
on `main`, not behind fetched `origin/main` (`7a17acd27cc37274ff47328ede19c9eaed14e2b1`).
Its source fingerprint is
`9de69658a554a61ac1679e3cd52398ea73800adf700fb0c51d7a636324dceef9`, and
the source-fresh Stage1 product SHA-256 is
`b8bd3a694848ea2d278439ca8f4f8cf7bb564145a4b40c417165ab6a756948de`.
`nw-core/scripts/stage1_fresh.py` passes, the native runtime object was
rebuilt from that product, and the content-addressed Stage1 runtime
provenance guard passes for the reviewed latest-compiler runtime deltas.
The focused sview region-tie regression passes at O0/O2 for both Stage0 and
Stage1, including rejection of the erased typed field-reference return with
no LLVM artifact emitted. The completed driver acceptance evidence reports
bare mode `2 disagreements (0 accept-gap, 2 reject-gap)` within ratchet 6 and
with-stdlib `0 disagreements`.

The qualified borrowed-view alias fixture already rejects correctly in
current Stage0. Its former Stage1-only test restriction was stale; the live
compiler regression now checks both generations at O0/O2, requires the
invalid-view diagnostic, and verifies no LLVM artifact is emitted. The
expanded safety suite passes. This case required a coverage correction,
with no change to either compiler's semantics.

The port WASM rebuilt from this exact Stage1 product through
`nw-core/scripts/build_latest_stage1_wasm.sh` passes the complete artifact
suite, including all registered games, the 3D-only N-Back vertical slice,
Marble browser/MuJoCo/renderer/board/session checks, and the 162-scenario /
17,263-state trajectory oracle. The promoted artifact SHA-256 is
`97fa27007ba5d7078353ba6363bcf5aaeb43a9833094b1dc2218c01a9ab2b15a`.
The independent hard 7,601-event Marble source/wasm replay remains a
separate physics-parity investigation documented in the root plan; compiler
validation does not resolve or waive that discrepancy. The following dated
entries are historical evidence.

**Historical Stage1 compiler (rechecked 2026-09-22):** the external compiler
checkout is `Elisa-compiler` `main@c27443bf9bd32f9ff7bf5081831181036ef09266`,
equal to `origin/main`. The source fingerprint is
`3a590c1bd38cffefccf504e0225a09433302ef21dfbe840f058e45376353b503`; the
source-fresh Stage1 product passes `nw-core/scripts/stage1_fresh.py` and has
SHA-256 `25917dc7da544546c6a3ecfd6e4424dc6f8bb63fede790fe1a5741fa39b479fa`.
The focused field-access scope, by-reference generic reproducer, positive
shadowing case, and exact mutable-aggregate-to-value parity smokes pass. The
fresh `driver_acceptance_smoke.sh` reports zero Stage0-reject/Stage1-accept
gaps in bare mode (six opposite-direction Stage1 rejects, within the existing
ratchet) and zero disagreements across all 537 diagnostic fixtures with the
standard library. Thus the investigated acceptance gap is fixed in compiler
source; no port-Elisa workaround is warranted. The port WASM was rebuilt from
this exact updated product with `nw-core/scripts/build_latest_stage1_wasm.sh`;
the full artifact gate and post-build provenance check passed. The artifact
SHA-256 is `c6cf8d7f3e6f18c4723c0fb86cb096e6bcfddcdc9ca70a7acfc5acb25d0ed26e`.
The compiler's separate broader full gate remains outstanding.

The wrapped-signature follow-up fixed the shared declaration-range scanner and
interface body indentation. Nested-module AST/interface parity and all 10
C-bind cases now pass. The remaining focused parser/emitter mismatch is the
multiline `dispatch` fixture, whose trailing `-> void` is still omitted by
both `-emit ast` and `-emit iface`; its neighboring wrapped `execute` also
loses the error effect in those projections. `pymodule_so_smoke.sh`, seeded
stress (`seed=7,count=15`), and the complete port artifact gate pass on the
current product. This remaining case is tracked as compiler parser metadata
work, not a port-side Elisa workaround.

**Stage1 backend/parser corrections (2026-09-22):** the full gate exposed two
new compiler defects and both now have focused evidence. A value-match arm
ending in a statement-form `if` previously emitted the branch control flow but
did not store either yielded value into the match result slot. The resulting
uninitialized aggregate was optimized to `ret undef` at `-O2`; the recursive
result-slot lowering in `src/backend/codegen_condition.elisa` now handles the
final `if` and nested final `if`s. `test/repro/match_arm_final_if.elisa` now
executes with the same result at `-O0`, `-O2`, and `-O3`, and
`opt_pipeline_smoke.sh` passes all 171 fixtures.

The malformed-input corpus also found an extern declaration with `-> &?`.
Stage1 retained the malformed header as a void-looking extern and later trapped
inside LLVM `DataLayout::getABITypeAlign`; Stage1 now rejects an arrow with no
identifier return head in `src/parser/parser_export_surface.elisa`. The named
`malformed_extern_pointer_return` regression is in
`test/breadth/malformed_input_fuzz.py`; the regression-only malformed sweep
passes 11/11 with zero abnormal exits or invalid IR. The assign-type smoke was
also corrected to accept the current oracle's equivalent scalar diagnostic
spelling (`int` versus the older `i64`) without weakening the mismatch check.

The complete `gate.sh --full` run at this compiler boundary reached all tiers
but remains red: 12/435 Stage1 parity checks failed. The two compiler defects
above are fixed and targeted checks pass; remaining failures are separately
tracked as diagnostic-baseline/line drift, emit-format parity, flow census,
Python-module linkage, seeded-stress, and other compiler-gate work. The port
artifact has not been promoted from this newly seeded product yet.

The first attempted matrix run used the previous Stage1 product after compiler
source had advanced; the Stage1 wrapper correctly refused it as stale (exit 2),
which was initially miscounted as Stage0-accept/Stage1-reject disagreement.
That run is invalid and superseded by the fresh-product run above. An earlier
Stage1 product was used for `nw-core/scripts/build_latest_stage1_wasm.sh`; the
then-current artifact gate and post-build provenance check passed. Its WASM
SHA-256 was `26c6230f593d1a98161658c98b6106ef90384add624b514fa05a0c1551b5de5b`.
That artifact was superseded by the current artifact above after the
generic-reference correction was verified.

**Primitive-reference field-access regression (rechecked 2026-09-20):** the
current source-fresh Stage1 product includes the semantic fix for
`buf: mutable u8&` followed by `buf.count`; a freshly built Stage0 and Stage1
both reject the case with `field access requires struct type, got u8`. The permanent diagnostic fixture is
`Elisa-compiler/test/fixtures/diagnostics/field_access_through_primitive_ref.neg.elisa`.
The fresh full driver-acceptance sweep reports zero Stage0-reject/Stage1-accept
gaps in both bare and standard-library configurations. The production browser WASM
was rebuilt from that exact Stage1 product by
`nw-core/scripts/build_latest_stage1_wasm.sh`; the complete artifact suite and
post-build compiler-provenance check passed. Artifact SHA-256:
`26c6230f593d1a98161658c98b6106ef90384add624b514fa05a0c1551b5de5b`.
No port-side Elisa workaround is required for this issue.

**Generic field-access shadow-scope regression (fixed 2026-09-20):** Stage1's
`check_field_access_type_param` previously collected every local declaration in
a generic function into one function-wide `shadowed` set. A same-named local in
an inner branch therefore hid a later invalid access on the generic parameter:
Stage0 rejected `value.unknown`, but Stage1 accepted the file when a valid
non-generic sibling kept the backend from declining the whole unit. The checker
now pushes declarations and binders when they enter scope and truncates them at
branch, loop, match-arm, lambda, comprehension, and block exits. A permanent
reproducer and a valid branch-local shadow are covered by
`Elisa-compiler/test/parity/field_access_type_param_scope_smoke.sh`.

The same focused parity smoke now also guards the by-value primitive case:
`primitive_field_access_scope_leak.neg.elisa` requires both compilers to reject
an invalid field access after a branch-local struct shadow closes, while
`primitive_field_access_scope_shadow.pos.elisa` requires both compilers to
accept the valid field access inside that branch. Both cases pass on current
Stage0 and the source-fresh Stage1 product identified below, so no additional
compiler semantic change was needed for this follow-up.

The external Stage1 source includes the committed fix in
`Elisa-compiler/src/semantic/check_field_access_type_param.elisa`. The current
source-fresh `-O3` product has SHA-256
`655aae4f5606b56abeab8d63d163abaad3420057371c16b319e581e68fe20a5a`. The
current external Stage0 and this Stage1 product agree on both
regressions: both reject the outer invalid access and both accept the valid
branch-local struct access. `field_type_smoke.sh` and the focused parity smoke
pass. No port Elisa workaround was made.

**Superseded local Stage1 rebuild (2026-09-19, not yet a full artifact promotion):**
the port-owned toolchain was reseeded from local Elisa compiler `main` at
`15c54315f71c3bb30a1105605deff4661f26cc9f`, with fetched `origin/main` at
`57e78b7015777b1165ed7876b8b5bee03f97de18` (the local checkout is ahead, not
behind). The resulting port-owned Stage1 has SHA-256
`7c2ab9f538d0b14597bce146233eabcad062cfce6f5ec87ee6aaf47c32bf1b76`; its
port-owned Stage0 and runtime have SHA-256
`819fcf887f973763f2ac56324b618fbd71c98d1b54f487e62178419c135e412a` and
`a541ce95c0cb3e9e6568460c9ffe956ba142185328ccb5cee195c600a7705244`. The
mutable-aggregate-to-value parity smoke rejects the repro identically on both
stages, Graph Mapping passes 489/489, and Mr. Time passes 1,785/1,785. The
newest-Stage1 artifact build passed all checks through the full controller and
browser sequence, then stopped at the existing Marble Python source-contract
check because pyglet cannot create a Cocoa display in the headless process;
therefore this build is recorded as source-fresh and focused-green, not as a
fully promoted artifact. The compiler checkout was not edited by this task.

**Targeted driver-acceptance recheck (2026-09-19):** the historical
`dict_index_key_mismatch.neg.elisa` case is no longer an acceptance gap in the
current external Stage1 product. After reseeding that product from compiler
`main@380b0aec0211575e8f416a1ede8ed7ac33b0e005`, the case was compiled both
bare and with the standard-library prelude: Stage0 and Stage1 both exited 1.
The diagnostics differ (`indexing is not implemented for dict[i64, i64]`
versus `cannot assign int to mutable i64&?`), but both drivers reject the
program, which is the required compiler-level behavior. The product passed the
source-freshness check. Rebuilding the port-owned copy from that checkout was
attempted but stopped by its existing 4,194,304 KB Stage1 seed RSS guard; that
guard was not relaxed, and the older port-owned product was not relabeled as
new. The source-level dict-index diagnostic implementation is in
`Elisa-compiler/src/semantic/resolve_types_initializers.elisa`; no Elisa port
workaround is required for this case.

**Authoritative current port-build record (2026-09-19):** the selected Elisa
Stage1 checkout is
`main@bb1a8289e6f3063bedddccb519a6d719235d6fde`, exactly equal to fetched
`origin/main`. Its tested dirty-worktree source fingerprint is
`efd8be06c6222a6a9515c454fe548b5aa7722405c24c0e95e7d5d80463080eec`, and
the source-fresh `Elisa-compiler/bin/elisac-stage1` product has SHA-256
`c0b7b26f4d20446839f60ce929cd46bef3117a6db9f3c5f356bf05b2fc11b5a9`.
`DEVELOPER_DIR=/Library/Developer/CommandLineTools bash scripts/gate.sh`
exited 0 with `GATE GREEN`; its complete-build provenance guard passed, and a
post-run check found no Elisa source newer than the selected product. The
external compiler's existing semantic/wrapper edits remained user-owned and
were not edited or reverted by this task.

The fast gate passed the complete Stage0/Stage1 port differential catalogs,
latest-Stage1 WASM/artifact build, all registered controller/browser/scene
checks, 3D-only N-Back, the full current Marble matrix, the Stage0 fast native
tests, Stage1 Glyphs RSS regression, targeted Stage1 parity smokes, and runtime
provenance. The resulting 1,095,131-byte `nw-core/build/nwcore.wasm` has
SHA-256
`1fff9c78104ff6d962678837c1afba9b18596b1749b6e4a9b20cd6664b109bc2`,
and `nwcore_wasm.o` has SHA-256
`3dadabb11824fe50131a188fb9b2eecc3ff08332122f41cbecf907343be0770f`.
The 21 optional concurrency-runtime bodies remain documented backend warnings.
The slow `--full` tier was intentionally skipped, so Stage0 `test-full`, the
self-host fixpoint, and the Stage1 semantic differential remain open.

**Superseded authoritative port-build record (2026-09-18):** the selected Elisa
Stage1 checkout is `main@ee50240f9e0de8046708c7153f320c89b222bbb7`, four commits
ahead of and zero commits behind `origin/main` at
`76230afa9e5fdf96f25f88f30405234912905ddb`. Its complete current-worktree
source fingerprint is
`d8e56bf02aaf0ffb7f3190f8002097a2f7c59a2f23309096daf8476d5b6103af`, and the
freshly reseeded product `Elisa-compiler/bin/elisac-stage1` has SHA-256
`f557e6dce94f90e776bdb57dc8952db0e4dc170232c0ce6feb749d90f505ebae`. The
product was seeded from the current Elisa-core Stage0 binary, SHA-256
`11f0416c4fc1247b1978f0c5e0def7186c2498d3bf46c7b92f5c8a8d19b0b6a7`. The
served `-O2` artifact `nw-core/build/nwcore.wasm` is SHA-256
`72cd4b672736123bb3a2562f885848f0ed01862ad83e1d1073d4fafd2539f582`
(`974768` bytes), and `nwcore_wasm.o` is
`952008613f13e7569beed3757371b3ba0c765d8bee3b1e23a2e2d7c6685d5aaf`.
The port-owned Stage0/Stage1/runtime provenance is recorded in
`nw-core/toolchain/PROVENANCE` and the runtime vendor selected by the
provenance check is byte-identical to canonical Stage0.

The configured fast gate exited 0 with `GATE GREEN`, covering both compiler
stages' differential matrices, scene/controller sweeps, 3D-only N-Back,
artifact/API checks, targeted compiler parity smokes, and runtime provenance.
The deliberately skipped slow `gate.sh --full` tier remains open and includes
stage0 test-full, self-host fixpoint, and Stage1 semantic differential work.
The external compiler checkout is intentionally user-owned and dirty; its
parser and machine-law edits were preserved, and no Codex edit was made to
those compiler sources. The latest source-mtime check found no Elisa source
newer than the reseeded product.
The source-level issues fixed during this refresh include a Stage0-safe
Numberology i64 overflow guard and a Custody live-array bound that previously
read beyond small round allocations. Earlier fixes for reserved helper names,
inline control-flow suites, read-only indexing, and overlapping references are
also included in the current port source. These fixes are verified against
the existing source differential oracle; they do not constitute blanket
compiler certification.

The current Marble-focused source pass also keeps compiler evidence separate
from UI timing assumptions: the fallback adapter's direct `step(dt)` uses the
native four-equal-substep contract, while the browser `advance` layer owns the
source 50 ms clamp and positive 60 Hz remainder partition. The WebGL2 renderer
forwards the native `normal_scale` uniform. Renderer-contract, browser-physics,
MuJoCo, trajectory, and Stage0/Stage1 board/MJCF parity tests cover these
boundaries; exact source/GPU pixel identity remains a separate open acceptance
item.

The paragraph below is historical evidence for an older isolated candidate;
the later refresh note is authoritative for the current port artifact. That
older candidate was rebuilt from the then-newest fetched Elisa-compiler checkout
`main@9ce2616d5cd8c286d43a3a83967a74978b0fd355`, exactly matching
`origin/main` at the build boundary. The isolated Stage1 product used for the
artifact has SHA-256
`fe8e2d7bac87f682186253e5b7a1787024d872e5fb71ea0dc4e3c0217dfe4e3e`; its
working-tree delta fingerprint is
`219ab68f209e45efb33a639c58bff497dbbf9d7b6f28f659ea0af917f2def831`. The
isolated checkout synchronized its three vendored runtime files to canonical
Elisa-core, and the shared checkout's separate uncommitted diagnostic edits
were preserved and excluded. The resulting optimized `-O2` WASM artifact is
SHA-256
`69efccadb3e031853e0eedcc24ab992863650118f2a300836431b6763b350cb3`.
The wrapper records the exact working-tree delta, rejects a checkout behind
fetched `origin/main`, and refuses to build if any compiler source becomes
newer than the selected product. The complete artifact gate and a fresh
headed Marble success smoke passed against this artifact. The known 21
declined concurrency-runtime bodies remain a broader compiler-gate limitation.
See `docs/port-status.md` and `implementation-plan.md` for the full
current provenance and remaining compiler-gate caveats.

**Historical refresh superseded by the authoritative record above (2026-09-16):** the
current served build uses compiler HEAD
`8110bb9ff33bb41fba24a7553f16c89685e98bd2`, matching fetched `origin/main`,
with Stage1 product SHA-256
`b8917d13bf891c7f04f60daa3f2549dbb1dd0162ef508de5723d24f04cf90ff3`, source
fingerprint
`d8fb78556b2af6538994f5502eaad0ff283d3f5e73add86befb691fa1fc8ab04`, and
six pre-existing compiler source edits. The current `-O2` WASM is
`e840a1244dd70fe443b18f06207dae8bd431520fb4d83b63145e10a2106060aa`; the
full artifact gate passes. The older isolated-candidate identity remains
historical evidence only.

## Toolchain identity for the 2026-09-13 verification

Use [`../toolchain/PROVENANCE`](../toolchain/PROVENANCE) as the machine-readable
record. At the time of this verification:

| Stage | Source root | HEAD | Source state | Binary SHA-256 |
| --- | --- | --- | --- | --- |
| stage0 recorded in provenance | `worktrees/elisa-core-nw` | recorded `e33dbd60f8c3fb0316114917265e4113d686495b`; current checkout `5284109ca5805560a488c3b0a5d8cd4a1a45e317` | recorded product SHA differs from current binaries | recorded `c5efa8ce20f781f21817eabc0481efe79a2c895031f49ce64bbb72911386c183` |
| stage0 used for this smoke | local `stage0-elisa-compiler` symlink → `Go projects/Elisa-core` | `5284109ca5805560a488c3b0a5d8cd4a1a45e317` | executable hash measured at test time | `4f0979111de75d5cbf4216bb8e79678edcaa8eb900e5a01570892fa8ac09b6b0` |
| stage0 used to rebuild latest COMP-007 candidate | `nw-core/toolchain/elisac-stage0` | provenance-pinned product | selected by `nw-core/scripts/env.sh` | `c5efa8ce20f781f21817eabc0481efe79a2c895031f49ce64bbb72911386c183` |
| wrapper-default stage0 (not used) | `Go projects/structpy-tree` | `2c65e57e23b37f5c4fddb5f92f806d7d9721c5e5` | rejects runtime build due a `memset` declaration conflict; see COMP-008 | `f7de7b6c94aca616053c4ae26f23830ea5f6ff7dfac7c2752c78729a49416a9a` |
| stage1 pinned | `worktrees/elisa-compiler-nw` | `df6cf8172cf75cf7fe861c9591d7d03f16a0d7c6` | dirty; `source_fingerprint.py` digest `6efafa99aa280e28be16d98bac4d91241c4bd519913ad9330dcce4fa4fc6e4a8` | `e104009499aa46bd13859efb069eeea9240266f05f2bd09bd76017925fa5d4f3` |
| stage1 isolated candidate | same source root | same commit plus current dirty source | rebuilt from the digest above; test-only path `nw-core/build/elisac-stage1-test-entrypoint-v2` | `d02a3d0ded5ff9cf91a9046b8b878713d89a29c2094b09ec9039634d4c05dda2` |
| stage1 isolated candidate (latest COMP-007 verification) | same source root | same commit plus current dirty source | source fingerprint `6efafa99aa280e28be16d98bac4d91241c4bd519913ad9330dcce4fa4fc6e4a8`; test-only path `nw-core/build/elisac-stage1-test-entrypoint-pinned` | `a2fe74bccae7021ae53a8dcd4f874dfcfed807a560b8b0c5f597cd6078d50f17` |

The pinned binary's recorded source fingerprints are stage0
`9de69658a554a61ac1679e3cd52398ea73800adf700fb0c51d7a636324dceef9` and stage1
`52d3073d9a1123534b07c48e61afd1b447a49a3ec1e0efda54f96534dd3fbf7c`. The
current stage1 source fingerprint is
`6efafa99aa280e28be16d98bac4d91241c4bd519913ad9330dcce4fa4fc6e4a8`, as
computed by `nw-core/scripts/source_fingerprint.py`. The
isolated candidate is explicitly separate from the pinned product. Do not
identify either by commit alone: the worktree has relevant uncommitted
compiler/runtime changes. Refresh pinned provenance only as part of an
approved, fully verified toolchain replacement.

## COMP-001 — wasm32 checked dynamic-array index width

**Status:** fixed in stage1; parity smoke is in the gate.

**Symptom:** the darray header stores its element count as `i64`, but `usize` is
`i32` on wasm32. Checked indexing emitted an LLVM integer comparison with an
`i32` index and an `i64` count, yielding invalid IR/WASM for
`get values[index] else fallback` on wasm32.

**Fix:** in
`worktrees/elisa-compiler-nw/src/backend/codegen_expr_blocks.elisa`, zero-extend
the wasm32 index to `i64` for the unsigned bounds comparison only. Retain the
original target-width index for the element GEP. This also preserves rejection
of a wrapped-negative unsigned index.

**Regression artifacts:**

- `worktrees/elisa-compiler-nw/test/repro/wasm32_checked_index.elisa`
- `worktrees/elisa-compiler-nw/test/parity/wasm32_checked_index_smoke.sh`
- `nw-core/scripts/gate.sh` includes the `wasm32_checked_index` parity smoke.

**Verification:** the smoke compiled with both pinned compiler binaries,
linked, and validated the resulting wasm modules. The 2026-09-12 stage0 and
stage1 browser artifact suites also passed their 421 differential cases and
720 session-frame cases. The root gate had no failure in this smoke.

## COMP-002 — stage1 `sview`/`strlen` ABI on wasm32

**Status:** fixed in stage1; exercised by artifact-level session tests.

**Symptom:** `emit_sview_from_parts` declared libc `strlen` as returning `i64`
on every target. On wasm32, `size_t` is `i32`; the conflicting declaration
could lower to an invalid bitcast/trap stub (`.Lstrlen_bitcast_invalid`) when
the runtime's existing `strlen` declaration was reused. The defect affected
string-view clamping and therefore session ABI paths.

**Fix:** in
`worktrees/elisa-compiler-nw/src/backend/codegen_call.elisa`, use the target
pointer width for the `strlen` result and zero-extend its unsigned result to
`i64` before the existing clamp arithmetic.

**Verification:** both pinned WASM artifact builds completed and their session,
menu, task-hub, and other listed ABI checks passed. The 2026-09-12 run checked
421 differential cases, 720 session frames, 6 batch ABI cases, 3 menu ABI
cases, and 4 task-hub ABI cases on each artifact. This evidence is scoped to
those artifacts and cases; it is not a claim that every string-view path has
been exhaustively fuzzed.

## COMP-003 — stage1 compile RSS for the `Glyphs` module

**Status:** fixed for the reproduced Glyphs optimizer-RSS failure in isolated
stage1 candidate v12. The provenance-pinned stage1 binary is unchanged; this is
not general stage1 certification or promotion approval.

The stage1 wrapper's default driver limit remains 4,194,304 KB. The root cause
was large aggregate values returned through `sret`: stage1 materialized a
large struct as a typed LLVM `load`, then copied it with a typed `store` into
the hidden return destination. LLVM's O1/O2 SROA path expanded
`Glyphs.cover_blank`'s 16 KiB value into 16,388 instructions; `EarlyCSE` then
processed that expansion and the optimizer exceeded the guard. The failure
was in code generation/optimization, not parsing or semantic analysis.

Stage1 now initializes exact matching struct-literal returns directly into the
caller's `sret` destination, recursively doing the same for nested struct
literals. It retains the existing value-producing path for unsupported forms
and functions with `ensure` contracts, and it does not retry after partially
emitting a constructor. Large safe zero values use target-sized `memset`
initialization rather than an LLVM aggregate constant copy. The fix does not
raise the default memory guard, lower optimization, or remove oracle cases.

The paired reproducer remains at:

- `nw-core/test/repro/stage1_glyphs_compile_memory.elisa` — includes
  `src/glyphs.elisa` and calls none of its routines. Before the fix, the
  default guard stopped it at approximately 4.33 GiB.
- `nw-core/test/repro/stage1_glyphs_compile_memory_control.elisa` — identical
  runtime/helper imports without the Glyphs module; compiles successfully at
  `-O2` under the default guard.

The dedicated regression `nw-core/scripts/stage1_glyphs_memory_smoke.sh` now
compiles the import-only repro at both `-O1` and `-O2` through the ordinary
4 GiB wrapper guard; it is registered in `nw-core/scripts/gate.sh`.

**Verification and exact candidate scope (2026-09-14):**

- Candidate: `nw-core/build/elisac-stage1-wasm32-fixes-v12`, SHA-256
  `a7a9810f578533aacd7acac03470f972e5e42a575ec2a2c1a93a150bcd6f00c4`;
  built from current stage1 source fingerprint
  `ee7f8bf59c5e560cd7b0eb78e75159c98f5a80c8d347152239368505f57db795` using
  pinned stage0 SHA-256
  `c5efa8ce20f781f21817eabc0481efe79a2c895031f49ce64bbb72911386c183`.
- The pinned runtime object SHA-256 remains
  `d392af4d754340af0b22ed7a00f9db8e66efbc0ab9dac034ac5c30d1f819b663`.
  The pinned stage1 SHA-256 remains
  `e104009499aa46bd13859efb069eeea9240266f05f2bd09bd76017925fa5d4f3`.
- Candidate O0 IR for `Glyphs.cover_blank` and `Glyphs.templates_blank` writes
  into the `sret` destination and contains no aggregate load/store pair.
- The import-only Glyphs `-O2 -emit llvm` compile completed through the normal
  wrapper in 0.29 seconds with 79,724,544 bytes maximum RSS (about 76 MiB),
  versus the earlier guarded failure above 4 GiB. The dedicated `-O1`/`-O2`
  smoke passed under the default guard.
- The candidate's stage1 WASM artifact suite passed: 421 differential cases,
  720 session frames, batch/menu/task-hub ABI checks, 45 stateless task-frame
  ABI checks, Monkey Ladder and Sokoban replays, and Marble Maze browser,
  physics, and 16-board checks. The artifact build still reports 21 declined
  concurrency-runtime bodies; that separate limitation remains open.
- Fifteen available targeted stage1 parity smokes and the optimizer corpus
  (`-O0`/`-O2`/`-O3`, LLVM IR round-trip) passed. The repository fast gate was
  not completed: its stage0 differential half passed and the initial stage1
  pyset, scheduling, timing, and board suites passed, then the run was
  intentionally stopped to avoid repeating 53 slow frame-oracle suites. Do
  not describe that interrupted run as a green gate.

This closes COMP-003 for the reproduced optimizer-RSS failure on candidate v12
only. Remaining declined bodies, full compiler-suite/gate completion,
toolchain provenance identity, and release certification are not closed by
this result. The later isolated COMP-006 candidate v13
(`elisac-stage1-readonly-v1`, SHA-256
`bd111a8d02b94203e14adfc122d5678fdcb586308f36dc75712dd83ec134809d`) also
passed `stage1_glyphs_memory_smoke.sh` at `-O1` and `-O2` under the unchanged
default 4 GiB wrapper guard. That run recorded pass/fail under the guard, not
per-optimization RSS measurements.

## COMP-004 — fast compiler tests inherited the port's strict-FP setting

**Status:** gate invocation fixed; full gate not yet rerun after the change.

`nw-core/scripts/env.sh` exports `ELISACORE_STRICT_FP=1` so the port's
stage0/stage1 differential builds avoid contraction differences. The stage0
compiler's fast Go suite contains backend tests that assert default LLVM IR
includes the `contract` marker. Invoking `make test` in the already-sourced
port environment contaminated those default-mode assertions and caused four
backend test failures; this was not a compiler output regression.

`nw-core/scripts/gate.sh` now runs the compiler suite as
`env -u ELISACORE_STRICT_FP make -C "$ELISA_CORE/compiler" test`. The suite
tests strict mode explicitly where required. Verification of that exact
invocation passed all configured fast packages on 2026-09-12. Rerun the full
gate to verify the integrated invocation.

## COMP-005 — stage1 drops module-qualified export targets

**Status:** source fix applied and reproduced with an isolated stage1
candidate; end-to-end stage1 WASM verification remains blocked by separate
backend/runtime and artifact-validation failures. The pinned product and its
provenance remain unchanged.

**Symptom:** the existing qualified-export syntax
`export fn public(...) = Module::implementation` is parsed, but the stage1
backend searches the function table as if the entire qualified spelling were
a top-level function name. The backend strips the export wrapper. A minimal
WASM-targeted unit then fails with `declined 1: increment_export` and no object
is written. The same fixture compiled with stage0 defines both
`ExportFixture.increment` and `increment_export`.

**Source fix:** the parser now captures complete repeated `Scope::Ident`
targets, including whitespace around `::`; semantic export-name checking,
decorator matching, and backend wrapper resolution use the complete module
path. Generic specialization uses the final member name, and wrapper lookup
prefers the exact arity. Existing top-level targets remain supported.

**Regression fixture:** `nw-core/test/repro/stage1_qualified_export.elisa`.
The compiler repository already has a larger qualified-export parity fixture
in `worktrees/elisa-compiler-nw/test/parity/resolve_smoke.elisa`; run that with
the rebuilt stage1 product as well.

**Evidence and limitation:** the runtime drift guard now passes: the vendored
and selected canonical runtime trees are in sync across all 33 guarded files.
An isolated candidate was built at `nw-core/build/elisac-stage1-probe`; it
compiles `stage1_qualified_export.elisa`, and `llvm-nm` shows
`ExportFixture.increment`, `increment_export`, and the whitespace-separated
`increment_export_spaced`. Pinned stage0 compiles the same three symbols.
The full port now passes stage1 semantic checking, but its backend still
declines 57 bodies (21 concurrency-runtime, 34 scene render/render-with-board,
and 2 generic `arena_dict_find_index` instantiations). With the semantic gate
explicitly disabled for diagnosis, linking the produced WASM fails Node
validation because `.Lpy_sample_range` compares an `i64` against an `i32`.
These failures are not evidence against the qualified-export fix; neither do
they permit promotion of the candidate. The pinned product hash remains
`e104009499aa46bd13859efb069eeea9240266f05f2bd09bd76017925fa5d4f3`, and its
provenance was not refreshed.

## COMP-006 — readonly-reference check confuses same-named module functions

**Status:** context-aware source fix applied and the focused regression passes
on stage0 and an isolated stage1 candidate. Nested/aliased qualified lookup and
full compiler-gate verification remain open.

The readonly-reference checker originally kept mutable-parameter contracts in
a bare-function-name side table. When distinct modules declared the same
helper name, a call could inherit another module's mutable-reference contract
and receive a false diagnostic; conservatively skipping ambiguous names then
avoided false positives but also skipped the specialized readonly check.

`worktrees/elisa-compiler-nw/src/semantic/check_readonly_ref.elisa` now records
each function signature with its owning module and resolves a call target
before looking up the parameter contract. Resolution prefers the current
module, then top-level declarations, then a unique visible imported owner for
an unqualified name; a direct `Module::function` call uses that exact module.
By-value declarations are also recorded so a same-named local by-value
function does not inherit a mutable-reference contract from another module.
The ordinary readonly-reference and immutable-struct-field address checks
both use the resolver. Existing mutable/readonly overload pairs remain exempt
from the readonly mismatch diagnostic.

The regression
`worktrees/elisa-compiler-nw/test/parity/readonly_lookup_smoke.elisa` covers
top-level contracts, a same-name by-value local shadow, module-local and
explicitly qualified calls, a qualified immutable-field address, overload
exemptions, a unique imported unqualified call, and an unimported hidden owner
that must not leak a diagnostic. The imported-owner case populates
`table.imported_modules` directly; it tests lookup given visibility metadata,
not the parser/import pipeline that populates that metadata. Qualified lookup
currently handles one `Module::function` segment only; module aliases and
nested paths remain outside this fix.

**Verification (2026-09-14):** the test passed with the port-pinned stage0
`nw-core/toolchain/elisac-stage0` (SHA-256
`c5efa8ce20f781f21817eabc0481efe79a2c895031f49ce64bbb72911386c183`) and an
isolated stage1 candidate built from source fingerprint
`9e2026cfc333d82568adaf3995b902e8016d11f636e6185d02c00a3fa14d289a`:
`nw-core/build/elisac-stage1-readonly-v1`, SHA-256
`bd111a8d02b94203e14adfc122d5678fdcb586308f36dc75712dd83ec134809d` (object
SHA-256 `55d7e2631067ceac36deacfa22fc60de0cafd1f8ade61b3c9713657b64ecd03d`).
The selected runtime object SHA-256 was
`d392af4d754340af0b22ed7a00f9db8e66efbc0ab9dac034ac5c30d1f819b663`.
`test/parity/emit_test_run_parity_smoke.sh` passed with **12 identical, 0
divergent** cases. Its readonly case requires exactly one selected test, one
pass, zero skips/failures, and exit status 0 from both compilers, so equal
failure output cannot satisfy the regression. The pinned stage1 product and
`nw-core/toolchain/PROVENANCE` were not changed. This is focused candidate
evidence only; the full compiler gate remains undone.

The same isolated v13 candidate subsequently built a separate stage1 WASM
artifact at `nw-core/build/elisac-stage1-readonly-v1.wasm`, SHA-256
`af937fe43a024dc08bc962747321b40a0330f2363e7035849d3e5d5df982dfcd` (object
SHA-256 `66ccd2b20b72015df4448f2709300f903866703f4544ce63526c74559a2d6c8c`).
`scripts/test_wasm_artifact.sh` passed 421 differential cases, 720 session
frames, 6 batch ABI cases, 3 menu ABI cases, 4 task-hub ABI cases, 45 stateless
task-frame ABI checks, Monkey Ladder and Sokoban live replays, common-v1
contract tests, and Marble browser/physics/all-16-board checks. The emitted
module was 866,719 bytes. Its 17 imports contain none of the 21 declined
concurrency-runtime function names below. This does not fix those bodies, run
the remaining compiler gates, or promote the candidate.

## Runtime concurrency body-decline scope audit (not a code fix)

The stage1 v12 port WASM artifact reported 21 declined bodies from
`elisacore_std/elisacore_runtime_concurrency.elisa`: `mutex`,
`mutex_dispose`, `mutex_lock`, `mutex_unlock`, `condvar`, `condvar_dispose`,
`cond_wait`, `notify_one`, `notify_all`, `yield_thread`, `sleep_usec`,
`ctx_concurrency_join_handle`, `spawn_raw`, `detach_raw`, `ctx_pool_lock`,
`ctx_pool_unlock`, `ctx_pool_wait`, `ctx_pool_signal`, `ctx_pool_broadcast`,
`ctx_pool_state_new`, and `pool_shutdown`. The audit found no matching port
application call/import in `nw-core/src`, `nw-core/shells`, or `nw-core/test`,
and no corresponding import in either the v12 or v13 emitted WASM module.
This classifies the functions as unexercised by the current Neural Workshop
app/API, not as implemented or generally safe. Keep the warning and exact
names visible; if a supported feature begins calling any of them, add a
use-site reproducer and implement/verify the required body before counting
that feature complete.

## COMP-007 — stage1 native test-runner omitted the test entrypoint's store context

**Status:** source fix applied; the focused regression and native test-runner
parity smoke pass on an isolated candidate built with the port-pinned stage0
and tested with the port-pinned runtime object. The pinned stage1 product
remains unchanged.

**Root cause:** stage1's backend inferred a hidden packed-AST-store parameter
for an `@test` function that directly parsed source and then traversed the AST.
The generated C dispatch shim correctly declared and called each test as
`void test_name(void)`, matching stage0's rule that tests are entry points with
their own region/store. As a result, the test body read a nonexistent hidden
argument as its store. The previous crash surfaced in `ctx_aos_store_alloc`;
LLVM IR and the generated caller established the ABI mismatch.

**Fix:** `codegen_declare_signature.elisa` now recognizes `@test` as an entry
point both when deciding whether the declaration intrinsically needs the
compiler AST store and when propagating a store requirement from its body.
Existing body analysis still gives a test its local arena and initializes the
appropriate packed store when the test parses or constructs AST data.

**Regression:**
`test/parity/readonly_lookup_smoke.elisa` parses source into `Ast::File` and
passes it through semantic analysis. The case is now included in
`test/parity/emit_test_run_parity_smoke.sh` as
`compiler AST store on @test entrypoint`.

**Verification:** the isolated candidate at
`nw-core/build/elisac-stage1-test-entrypoint-v2` has SHA-256
`d02a3d0ded5ff9cf91a9046b8b878713d89a29c2094b09ec9039634d4c05dda2` and was
built from stage1 source fingerprint
`6efafa99aa280e28be16d98bac4d91241c4bd519913ad9330dcce4fa4fc6e4a8`. With
the native runtime object built in the same compiler worktree, the complete
`emit_test_run_parity_smoke.sh` passed: 12 identical cases, 0 divergent,
including readonly AST traversal, pass/skip/filter behavior, and panic capture.
The v2 candidate above was originally built using a local compiler alias. To
remove that pairing ambiguity, the same source fingerprint was rebuilt as
`nw-core/build/elisac-stage1-test-entrypoint-pinned` with the exact stage0
selected by `nw-core/scripts/env.sh`; the candidate SHA-256 is
`a2fe74bccae7021ae53a8dcd4f874dfcfed807a560b8b0c5f597cd6078d50f17`. The
complete `emit_test_run_parity_smoke.sh` then passed again: 12 identical cases,
0 divergent, with stage0 SHA-256
`c5efa8ce20f781f21817eabc0481efe79a2c895031f49ce64bbb72911386c183` and
runtime object SHA-256
`d392af4d754340af0b22ed7a00f9db8e66efbc0ab9dac034ac5c30d1f819b663`. This
closes the selected-pair focused regression only. The isolated candidate and
pinned stage1 product remain distinct; do not refresh provenance or replace
the pinned binary based only on this smoke.

## COMP-008 — non-pinned stage0 convenience path has an incompatible runtime tree

**Status:** excluded from the port's pinned-toolchain gate; remains relevant
only to standalone use of the compiler wrapper without `nw-core/scripts/env.sh`.

The wrapper-default `Go projects/structpy-tree/compiler/bin/elisac` has SHA-256
`f7de7b6c94aca616053c4ae26f23830ea5f6ff7dfac7c2752c78729a49416a9a`. When it
was manually paired with the stage1 worktree's native-runtime source, runtime
object generation rejected conflicting `memset` declarations (`i64` versus
`i32`); after an exploratory local edit, it exposed a similar `memcmp`
conflict. This compiler/runtime tree is not the port's selected pair.

The supported port environment is explicit: `nw-core/scripts/env.sh` selects
`nw-core/toolchain/elisac-stage0` (the provenance-recorded SHA-256
`c5efa8ce20f781f21817eabc0481efe79a2c895031f49ce64bbb72911386c183`) and
`nw-core/toolchain/elisacore_runtime.o` (SHA-256
`d392af4d754340af0b22ed7a00f9db8e66efbc0ab9dac034ac5c30d1f819b663`). The
focused test-runner parity passed with that selected pair. Do not replace
runtime sources or alter `toolchain/PROVENANCE` to make the unrelated
convenience pair appear compatible. If standalone wrapper compatibility is a
requirement, add a separate explicit toolchain-selection and ABI test first.

## COMP-009 — qualified generic calls resolve through a bare-name fallback

**Status:** source fix applied; an isolated candidate passes the focused
wrong-target regression, all 511 native backend checks on the immediately
preceding build, and seven affected stage1 differential sweeps. The pinned
stage1 product and provenance remain unchanged.

**Root cause:** `generic_index_of` is intentionally a bare-name resolver. It
prefers the current module, then a top-level template, then the first matching
name. The explicit and inferred `Expr.Scope` call paths used that resolver for
`Module::function`, so a top-level generic could steal a qualified call to a
module's monomorphic or generic function. A minimal pre-fix program returned
140 under stage1 while stage0 returned 168. The same defect manifested in
`PySet.new`: a generic `put[T]` from an unrelated owner received a set's
darray pointer as an IndexMap receiver and crashed during arena reallocation.

**Fix:** `codegen_generic_inference.elisa` now has an exact `(owner, name)`
lookup. `codegen_name_mangling.elisa` resolves the complete scoped owner path,
including root module aliases and nested paths, and only tries a path relative
to the current module when an exact direct function does not take precedence.
Explicit one-/multi-type-argument calls and inferred calls use that exact
template slot. `emit_generic_call_at_slot` temporarily pins the generic
owner while reusing the established instantiation machinery, then restores
the previous owner. Bare identifier resolution is unchanged.

**Regression:**
`worktrees/elisa-compiler-nw/test/repro/qualified_generic_scope_shadow.elisa`
checks (1) a module's monomorphic `put` shadowed by top-level `put[T]`,
(2) inferred module generic lookup, (3) explicit `f[T]`, and (4) explicit
`f[A, B]`. Its parity runner is
`worktrees/elisa-compiler-nw/test/parity/qualified_generic_scope_smoke.sh`,
registered by name in `nw-core/scripts/gate.sh`.

**Verification:** isolated candidate
`nw-core/build/elisac-stage1-qualified-generic-v6` has SHA-256
`b3b8402b3bf9f95a2c2b45e3d363e25f631f8b2ccd39fc7136deba8fcc6f18b3` and was
seed-built with pinned stage0 SHA-256
`c5efa8ce20f781f21817eabc0481efe79a2c895031f49ce64bbb72911386c183`. The
current compiler-tree fingerprint is
`dc16f4827d19bb533286771e9ef3e3e8664ee5d8585db6e67c6db0404c7807d1`; the
runtime object used by the focused smoke has SHA-256
`d392af4d754340af0b22ed7a00f9db8e66efbc0ab9dac034ac5c30d1f819b663`.
Candidate v6 returns 168 like stage0 and passes the `pyset` differential
(1,000 cases). Candidate v5, built from the same backend source before only
the fixture/harness files were expanded, passed `backend_native_smoke.sh`
(511/511) and stage1 sweeps for `pyset` (1,000), `maze` (428), `fogworld`
(498), `numberology` (261), `inthedark` (106), `crossedwires` (1,546), and
`cookiethief` (137). The pre-fix candidate failed the focused regression
(stage0=168, stage1=140). These checks do not close the complete stage1
artifact suite, compiler gate, remaining compiler issues, or all-games plan;
do not promote the candidate or refresh pinned provenance based on them.

## COMP-010 — stage1 field-type inference conflates same-named module structs

**Status:** fixed in the current isolated stage1 candidate and now registered
with broadened stage0/stage1 parity coverage; the pinned stage1 product and
provenance are unchanged. Qualified type names are still flattened to bare
names in parts of semantic analysis, so ambiguous external bare-name
references remain deliberately unresolved rather than guessed.

**Symptom and root cause:** `struct_field_owner`, `struct_field_name`, and
`struct_field_type` were searched using only the bare `(owner, field)` pair.
When both `Dynamic.Run.answer: darray[i64]` and
`Scalar.Run.answer: i64` were registered, analyzing `Scalar::read` could select
the first row and reject a valid integer comparison as
`cannot compare darray[i64] and int`. The existing parallel
`struct_field_module` metadata was already recorded but was not consulted by
`field_type_of` or `field_type_id_of`.

**Fix:** `worktrees/elisa-compiler-nw/src/semantic/resolve_types.elisa` now
resolves the current module's matching field first, then a top-level owner,
then a module-owned row only if the pair is unambiguous. Missing/ambiguous
external bare names return the existing unknown sentinel instead of borrowing
an unrelated field's type. This does not implement fully qualified semantic
type identities; that remains a broader compiler task.

**Regression:**
`worktrees/elisa-compiler-nw/test/repro/stage1_struct_field_module_collision.elisa`
uses same-named `Run.answer` fields with incompatible types and performs a
typed comparison, mutation, and return from the owning module.
`worktrees/elisa-compiler-nw/test/parity/module_struct_field_type_collision_smoke.sh`
compiles and executes it under both stages. The smoke's fixture path is the
stage1-specific reproducer above; the older similarly named fixture remains
reference material and is not probed by a nonexistent path.

The registered coverage now also includes:

- `module_struct_field_mutable_smoke.sh` for same-named fields whose
  mutability differs;
- `module_struct_return_type_smoke.sh` for a bare return type inside the
  owning module;
- `module_struct_namespacing_smoke.sh` for qualified, module-bare, and
  top-level struct precedence;
- `module_type_alias_namespacing_smoke.sh` for two module-local aliases that
  target different same-named structs;
- `module_struct_field_scope_matrix_smoke.sh` and its fixture for a two-level
  `Outer::Inner::Scalar` owner, a module alias (`using ... as S`), and a
  selective imported member (`using ...::read`); and
- `module_struct_field_ambiguous_external_smoke.sh` and its fixture for an
  explicit top-level `A::Run` reference when an incompatible `B::Run` row is
  registered first. That case must compile and run without selecting B's
  `darray[i64]` field type, preserving the conservative unknown sentinel.

The six additional names are part of `nw-core/scripts/gate.sh`'s latest-stage1
targeted parity list alongside the original collision smoke.

**Verification (2026-09-18):** the pre-fix isolated stage1 candidate fails at
the comparison (`darray[i64]` versus `int`) and subsequent integer addition.
The current candidate, `nw-core/build/elisac-stage1-field-type-v2`, has
SHA-256 `1e069595cd94567fced5553e108408375992bdde16ad6ea8c61fea217c8ba660`
and returns 42 alongside pinned stage0. It was seeded with pinned stage0
`c5efa8ce20f781f21817eabc0481efe79a2c895031f49ce64bbb72911386c183` after
the module-aware resolver source change. The current worktree fingerprint
`af2d1a692f01f88e54e538d28690997c7896f5fbc31bd176c8fa25db571aa762` was
computed after adding the regression files, so it is not asserted as the
seed-time fingerprint. The current-source Count-capable stage1 WASM artifact
`nw-core/build/nwcore-count-stage1-field-type-v2.wasm` (SHA-256
`0104146f666d46500928ff26ad3ff12370ab33dbc1c1a6161a32b4e8d9850764`)
passes the full configured artifact suite. The seven focused COMP-010 smokes
listed above pass under the pinned stage0 binary and the newest local Stage1
product at compiler commit
`ee50240f9e0de8046708c7153f320c89b222bbb7`, product SHA-256
`f557e6dce94f90e776bdb57dc8952db0e4dc170232c0ce6feb749d90f505ebae`, and
fetched `origin/main` `76230afa9e5fdf96f25f88f30405234912905ddb`. The complete
current compiler worktree fingerprint is
`d8e56bf02aaf0ffb7f3190f8002097a2f7c59a2f23309096daf8476d5b6103af`; the
product was reseeded from current Elisa-core Stage0 before the focused smokes
and full fast gate were rerun. No compiler semantic source was changed by the
port-side coverage expansion. This does not close the complete slow compiler
gate, provenance audit, or unrelated stage0 mismatch below.

## COMP-015 — reference sweeps used the compiler's built-in `Task` name

**Status:** resolved in the port's reference/parity adapters; no compiler
change was required.

The first current-source fast-gate run reported Stage1 linear-reference errors
for `Task&` in `src/tasks/recognition.elisa` and
`src/tasks/graphmapping_legacy.elisa`. The diagnostics were correct: these are
reference-only sweep kernels, and `Task` is already the compiler/runtime's
linear concurrency type name. The Graph Mapping adapter also redeclared the
production `GraphMapping` module instead of extending it. Its deck code then
used a forward Fisher–Yates pass, which consumed the expected number of random
draws but did not match CPython's descending `random.shuffle` order.

The adapter now declares `extend GraphMapping:`, uses `LegacyTask`, and performs
the descending shuffle. The Recognition reference kernel uses `RecognitionTask`.
The production `GraphMappingGame::Run`, `RecognitionGame::Run`, exports, and
WASM ABI were not changed by this correction.

**Verification (2026-09-18):** with the current external Stage1 product
(`ee50240f9e0de8046708c7153f320c89b222bbb7`, product SHA-256
`f557e6dce94f90e776bdb57dc8952db0e4dc170232c0ce6feb749d90f505ebae`):

- Recognition: 1,516 identical cases under both Stage0 and Stage1.
- Graph Mapping: 489 identical cases under both Stage0 and Stage1.

The focused green results clear this adapter defect, and the subsequent full
fast gate also passed. The slow compiler tiers and broader port plan remain
separate requirements.

## COMP-011 — stage0 contextual integer comparison truncates a Marble limit

**Status:** root cause fixed in stage0 compiler source; focused compiler
regression and full configured O1/O2 stage0 WASM artifact suites pass. Pinned
compiler binary/provenance refresh and the full compiler gate remain open.

**Symptom:** `test/runtime_protocol_v1_smoke.mjs` creates Marble Maze with seed
17, starts it, reports a win, and advances through feedback. Stage0 advanced
phase, trial, seed, and rung but left `boardGeneration=1`; stage1 correctly
returned 2. Dispatching the next-tray action directly reproduced the same
failure, ruling out timer and feedback scheduling.

**Root cause:** the source compared mutable `run.board_generation: i64` with
the unsuffixed literal `9223372036854775806`. For the `wasm32` target the
literal's default `int` width is 32 bits. Stage0's comparison analyzer unwrapped
the mutable field for code generation but analyzed the literal without that
field's expected type. The backend therefore narrowed the literal's low 32
bits (`0xfffffffe`) and sign-extended it; emitted LLVM IR showed
`icmp slt i64 %board_generation, -2`. Since generation is 1, the comparison
was false and the overflow fallback stored 1. This is a silent incorrect
comparison, not a Marble state-layout, timer, or ABI-marshalling defect.

**Fix:** `worktrees/elisa-core-nw/compiler/src/semantic/analyzer_expr_operators_analyzebinaryexpr_to_analyzeenumispayloadpattern.go`
now contextually analyzes an unsuffixed integer literal (including parentheses
and unary minus) against the opposite integral operand for equality and ordered
numeric comparisons. Explicit suffixes remain authoritative. The existing
contextual literal range check continues to reject a value that cannot fit a
narrow target.

**Regression and verification (2026-09-14):**

- Added semantic test
  `TestAnalyzeContextualWideIntegerComparisonLiteral` and stage0/stage1 parity
  fixture `worktrees/elisa-compiler-nw/test/repro/contextual_wide_i64_comparison.elisa`.
  Its wasm32 LLVM smoke failed before the fix because stage0 emitted `-2`; with
  the fix both stages emit the full positive bound
  `9223372036854775806`. The smoke is registered in `nw-core/scripts/gate.sh`.
- Isolated stage0 candidate `nw-core/build/elisac-stage0-contextual-i64`,
  SHA-256 `f976501a0e8d2f39a9bc1ac721ff13b6f95109ffbb90a7a557f6b0f91f8a1544`,
  was built from stage0 source fingerprint
  `00fbde8a5e92b6b11471a379eead635f9b98050d02bfc189d41b4912fc58c0f7`.
- `bash scripts/build_wasm.sh` with that isolated compiler rebuilt the default
  `nw-core/build/nwcore.wasm`, SHA-256
  `223b0ea90cb57ccaeaeb9d05c0d1aa7f2d472afa5c235537971ea4d44a0b8847`,
  406,315 bytes. The complete configured artifact suite passed: 421
  differential cases, 720 session frames, 6 batch, 3 menu, 4 task-hub, 45
  stateless task-frame cases, Monkey Ladder, Sokoban, Count, common-v1, Marble
  browser/physics/MuJoCo, and board ABI checks. In particular the Marble
  lifecycle now observes `boardGeneration=2` after the second-tray transition.
- A separate stage0 `-O1` artifact, SHA-256
  `c246c4226ce1d0124ac2d6fae07a2c65f118a21eff762c59b884239175ff050e`,
  passed the full same configured artifact suite, including the exact Marble
  lifecycle assertion.
- The previously stale default artifact, SHA-256
  `a8a0ad85b1a1171e454133a06ac39fb3f9d10d5737c3236abd79b2355a55dfa2`, lacked
  `nw_api_v1_task_marble_maze` and `nw_api_v1_task_count`; that binary is no
  longer served from the default path. The export/version guard remains in the
  web shell for future stale builds.
- The pinned `nw-core/toolchain/elisac-stage0`, stage1 product, runtime object,
  and `toolchain/PROVENANCE` were not changed. Regenerate/review an isolated
  full toolchain and provenance before promoting compiler binaries. Do not
  weaken the generation assertion.

## Gate snapshot — 2026-09-12

`bash nw-core/scripts/gate.sh` completed with exit 1 before the two harness
corrections documented below were integrated into that run. The checker
reported four failed suite invocations:

1. Stage0 chess, expressions, and algebra were started before their Python
   reference fixtures were written. The three differential harnesses now
   generate/write the reference fixture before launching the Elisa binary.
   Fresh stage0 runs passed: chess 866, expressions 342, algebra 318.
2. Stage1 glyphs crossed the memory guard; COMP-003 remains open.

The same gate run passed both stage0 and stage1 WASM artifact tests and the
targeted stage1 parity smokes (including `wasm32_checked_index`). Its separate
stage0 fast compiler test step failed only because of the inherited strict-FP
setting (COMP-004); the corrected environment-isolated command passed
afterwards. The slow compiler tier (`gate.sh --full`) was not run. No full gate
has yet been rerun after these corrections; do not report a green gate.

## COMP-012 — invalid qualified return type broke the current Stage1 seed

**Status:** fixed in the current Stage1 source tree and verified by a fresh
Stage1 `-O2` seed plus the configured Stage1-built WASM artifact suite. Pinned
toolchain binaries and provenance remain unchanged; the complete compiler gate
and the 21 declined concurrency-runtime bodies remain open.

**Symptom and root cause:** Stage0 reached
`parse_machine_from_arm_terminator` in
`worktrees/elisa-compiler-nw/src/parser/parser_stmt_machine_from.elisa` and
resolved the callee `parse_machine_from_terminator` signature as returning
`<invalid>`. The source had qualified the return as
`Parser.MachineFromTermAst` from inside `extend Parser`, while the sibling
helpers used the local type. Code generation consequently built a void call and
attempted to store it as the typed `MachineFromTermAst` rebind result, reaching
an LLVM store assertion.

**Fix:** the helper's result annotation is now the locally scoped
`MachineFromTermAst`. Stage0 `storeValue` additionally rejects an LLVM `void`
operand with a contextual compiler diagnostic before invoking `LLVMBuildStore`;
the VarDecl and reference-store paths report the function/local/source line.
The check intentionally does not require exact equality between a semantic
reference type and an LLVM value type because opaque-pointer writes through
mutable references can validly store the referenced value.

**Verification (2026-09-14):** a new Stage1 seed completed at `-O2` using
isolated Stage0 candidate `nw-core/build/elisac-stage0-store-diagnostic`
(SHA-256 `26c88ad430a02b5171d50032762c7024d908b61b76b9910213ff3565efc6703b`).
The current Stage1 product candidate
`nw-core/build/elisac-stage1-current-source-20260914` has SHA-256
`b78d2406c31794e11e9ea75e56ff106f682825aa6ffa071a9b0aeee58d645980`, from
source fingerprint
`2fa156c5c83e0f46e79e5676397345c91b0e650b00a5ce08018b1a3ec62ff5ca`. Its
Stage1-built `nw-core/build/nwcore.wasm` (SHA-256
`b4247684c5d8dfe3a237f08ca2ba74bf6a75674da1ea92919af14c7bcb50a817`) passes
the complete configured artifact suite and the headed Marble start/tilt browser
check. The WASM build still warns that 21 concurrency-runtime bodies were
declined; those untested functions and a full compiler-gate run are not covered
by this qualification.

## COMP-013 — pinned Stage0 cannot currently reseed the latest Stage1 source

**Status:** open bootstrap-compatibility issue; contained by a verified
isolated reseed with a newer sibling Stage0. The port does not replace the
pinned Stage0 or provenance records, and the latest Stage1 product remains
usable. The full compiler gate and the 21 declined concurrency-runtime bodies
remain open.

**Latest checkpoint (2026-09-16):** the current Elisa-compiler Stage0 completed
the official self-hosted reseed after the pending latest-source fixes were
repaired, publishing the active `bin/elisac-stage1` product recorded at the top
of this file. This closes the immediate “latest product cannot be refreshed”
blocker for the selected compiler checkout. It does not make the older
port-pinned Stage0 bootstrap-compatible; that narrower issue remains open and
is why `nw-core/scripts/build_latest_stage1_wasm.sh` keeps the latest compiler
root/product explicit and refuses stale products.

**Symptom:** On 2026-09-16, the official
`Elisa-compiler/scripts/elisac_stage1.sh --seed` command was run at the latest
clean Stage1 checkout `main@5329edfdbefa27b5c1c51253da0073256ed51058` with
`nw-core/toolchain/elisac-stage0` (SHA-256
`c5efa8ce20f781f21817eabc0481efe79a2c895031f49ce64bbb72911386c183`). Stage0
returned status 1 while parsing current Stage1 sources, beginning with parser
diagnostics in `src/parser/parser_protocol_parameters.elisa` and continuing
through compiler modules. The seed script's atomic publication left the
existing `bin/elisac-stage1` product unchanged at SHA-256
`03fb7200424b6849ea3243c33e774270b4e8909a080136d05092251254b52024`.

**Current workaround and evidence:** A newer sibling Stage0 candidate at
`Go projects/Elisa-core/compiler/bin/elisac-stage0` (SHA-256
`529a48195a1892fdcc07cf9bc40fc798c9f497938bbbc4df87ece58767e000d7`) completed
the official seed into the isolated product
`Elisa-compiler/build/stage1-from-current-stage0-20260916` (SHA-256
`c4fe7e9c2012558aa2a37293aba3f92dbd1f78dbd005d571ffba42e9295e5173`). The
no-Stage0 product smoke passes. Direct O0/O2/O3 compilation and execution of
the two fixtures that timed out during a long host-contended sweep pass; the
full 159-fixture latest-product sweep is therefore not recorded as green until
it is rerun on a quiescent host. The older self-hosted-gen2 product passes that
historical sweep. The port was rebuilt at `-O2` explicitly through the isolated
latest product; the complete WASM/Marble/Fog suite passes and the active
artifact hash is recorded in `nw-core/docs/port-status.md`.

**Required follow-up:** Minimize the first Stage0 parser rejection, identify
the first latest-branch commit that introduced syntax outside the pinned
Stage0 language, and either update/review the pinned Stage0 or backport a
source-compatible spelling. Keep the isolated product path and provenance
explicit until that bootstrap path succeeds; do not weaken the freshness guard
or silently fall back to the legacy pinned Stage1 product. Rerun the latest
product's full optimization parity corpus on a quiescent host before promoting
its product hash to the compiler's canonical `bin/elisac-stage1` path.

## COMP-014 — stale exhaustive-match parity assertion

**Status:** test assertion corrected; compiler implementation passes the focused
smoke. The complete latest-product compiler gate remains open.

The current Stage0/Stage1 diagnostic is:

```text
non-exhaustive match over "E"; missing variants: E.C
```

`test/parity/match_exhaustive_smoke.sh` had four older `grep` checks that still
looked for the removed singular spelling `missing variant "C"`, even though
the test header and the compiler's current diagnostic contract already used
the qualified plural spelling. The correction changes only those expected
strings; it does not weaken the test or change compiler output. The statement,
expression, and both `when` checks now pass, while the exhaustive, wildcard,
`or`, non-enum, and boolean negative cases remain covered.

Verification with the explicit current toolchain passed:

```text
Elisa-core/compiler/bin/elisac
Elisa-compiler/bin/elisac-stage1
Elisa-compiler@main = origin/main = 51325f58df42f1c7162b9a27841d756dac3c9b9d
match-exhaustive smoke OK; 0 false positives across frontend+stdlib
```

The registered Stage1 targeted set then passed through the wasm32 mixed-width
checks (`try_fallible`, `catch_exhaustive`, `match_expr`, `match_pattern`,
`match_exhaustive`, `enum_constructor`, `enum_tail_payload`,
`atomic_payload`, `scalar_match_arm`, `legacy_error_syntax`,
`wasm32_checked_index`, `wasm32_darray_abi`, `wasm32_sview_strlen`,
`wasm32_debug_referee`, and `wasm32_for_bounds_width`). The batch was stopped
at `qualified_generic_scope_smoke` after its freshly linked native Stage0
executable remained in macOS loader state with zero CPU; this reproduces the
documented host-level `dyld_start` stall rather than a compiler diagnostic.
The child and temporary run were removed, and no unrelated Rust/compiler jobs
were touched. A quiescent-host rerun is still required before this becomes a
full targeted-gate claim.

## Fast gate snapshot with concurrent latest-compiler drift — 2026-09-18

The interrupted `DEVELOPER_DIR=/Library/Developer/CommandLineTools bash
scripts/gate.sh` session was re-polled to completion and exited 0 with
`GATE GREEN`. At the latest-Stage1 artifact build boundary it observed
`Elisa-compiler@a4beace9a1f47b569a169072588a0023eba8afbd`, equal to
`origin/main`, source fingerprint
`b4ff702ee808e104b7bd6cecfd1d6d3357112a7b2da62600bd5166c5ff7b0d92`, and
Stage1 product SHA-256
`a87d9a586c96442e2805a1f0c9b4f2d6fd437539e6aeefd3d6f30ef9d486ce0b`.
The emitted 974,768-byte WASM and linked object hashes were
`72cd4b672736123bb3a2562f885848f0ed01862ad83e1d1073d4fafd2539f582` and
`952008613f13e7569beed3757371b3ba0c765d8bee3b1e23a2e2d7c6685d5aaf`.
All fast differential, controller, ABI, browser, targeted-parity, and
Marble checks passed; the slow full compiler tier was skipped as designed.

After that build boundary, the user-owned external compiler worktree was
modified by a concurrent compiler task. The current dirty fingerprint is
`c94af266e349cd577d2d052494c28fe50006082fbd4359b53b5d145721bc74b6` and the
current Stage1 product is
`21290051f91addb0f3a8f74710dac6bfa7991e15eb883c4bce70f2ac4d78edfc`.
The product is fresh by source mtime, but the later state is not included in
the green gate claim. The external task must finish before another
freshness-checked promotion or certification.

## COMP-015 — full-gate run invalidated by concurrent compiler edits

**Status:** open external-worktree coordination issue; no port source failure
was established.

On 2026-09-19, `nw-core/scripts/gate.sh --full` was run with
`DEVELOPER_DIR=/Library/Developer/CommandLineTools` against compiler commit
`dcf5ce4781c073b4669f7c85441bf82e5322a3c9`. Stage0's complete differential
tier passed. During the Stage1 differential tier, the user-owned compiler
worktree modified `src/parser/parser_types_struct.elisa`, making
`bin/elisac-stage1` stale. The freshness guard correctly refused the final
nine Stage1 suites, the latest-product artifact build, the Glyphs RSS smoke,
all targeted Stage1 smokes, the self-host fixpoint, and the Stage1 full parity
tier. Those refusals are not compiler or port parity results.

The same run's slow native Stage0 `test-full` reached the compiler tests and
reported the current repository's strict-FP/autovec expectation mismatch:
`TestAutovecVerifierWarnsOnNonVectorizedComprehension`, the fast-math branch
of `TestEligibleFoldPinsStrictTree`, the default branch of
`TestStrictFPDropsContraction`, and four backend tests expecting `contract`
FP instructions. The run exited with `GATE FAILED: 7 step(s)`. The external
worktree was not edited, reset, merged, or conflict-resolved here.

The next action is procedural: wait for the external task to finish, verify
that no `.elisa` source is newer than Stage1, seed exactly once, and rerun the
full gate. Do not set `ELISA_ALLOW_STALE_STAGE1=1` and do not promote the
rejected product. If the strict-FP/autovec failures persist on the quiescent
compiler checkout, record them as compiler-repository failures and separate
them from the port's artifact/Marble acceptance evidence.

## COMP-016 — fast gate invalidated by active newest-compiler seed

**Status:** open external-worktree coordination issue; no port regression
was established.

The newest local Stage1 product at
`main@80768ea780012e7043135e59b94e5e38fd3ac230` was source-fresh and produced
a green artifact-level result. During the later fast gate, the user-owned
compiler advanced to `4db52834046a88e405135f25ecffd363b6a4b2a9` and changed
`src/driver/elisac_parse_error_report.elisa` plus 19 other Elisa sources. The
gate's freshness guard rejected the remaining 16 Stage1 differential suites,
the latest Stage1 artifact rebuild, Glyphs RSS regression, and all targeted
Stage1 smokes. Stage0 differential, Stage0 fast native tests, artifact-level
Marble/N-Back checks, and runtime provenance passed.

At the terminal check the compiler had an active
`scripts/elisac_stage1.sh --seed` process, and the selected
`bin/elisac-stage1` product was older than all 20 changed source files. No
compiler source was edited or reverted by this task. Do not set
`ELISA_ALLOW_STALE_STAGE1=1`; wait for the user-owned seed/worktree to become
quiescent, then seed once and rerun the freshness-checked promotion and gate.

## COMP-017 — quiescent newest-compiler fast gate completed

**Status:** fast-tier coordination blocker closed at the exact boundary below;
slow-tier compiler qualification remains open.

After four earlier fast/full attempts were correctly invalidated by concurrent
external compiler edits, the compiler tree and seeded product remained stable
for one complete fast run. The successful boundary was:

- compiler and fetched origin:
  `bb1a8289e6f3063bedddccb519a6d719235d6fde`;
- source fingerprint:
  `efd8be06c6222a6a9515c454fe548b5aa7722405c24c0e95e7d5d80463080eec`;
- `bin/elisac-stage1` SHA-256:
  `c0b7b26f4d20446839f60ce929cd46bef3117a6db9f3c5f356bf05b2fc11b5a9`;
- generated WASM SHA-256:
  `1fff9c78104ff6d962678837c1afba9b18596b1749b6e4a9b20cd6664b109bc2`;
- generated linked-object SHA-256:
  `3dadabb11824fe50131a188fb9b2eecc3ff08332122f41cbecf907343be0770f`.

`DEVELOPER_DIR=/Library/Developer/CommandLineTools bash scripts/gate.sh`
exited 0 with `GATE GREEN`. Both compiler-stage differential catalogs, the
latest-Stage1 artifact build, all registered port tests, the Stage0 fast Go
suite, Glyphs optimizer RSS regression, targeted Stage1 parity smokes, and
runtime provenance passed. The build reported the same compiler identity at
the end, and the post-run freshness check found no Elisa source newer than the
product. The compiler worktree remains intentionally dirty with user-owned
semantic and wrapper changes; this record identifies that state by fingerprint
and does not imply that those changes are committed.

This closes only COMP-016's immediate quiescence/certification blocker. The
gate explicitly skipped Stage0 `test-full`, self-host fixpoint, and Stage1
semantic differential. The known strict-FP/autovec expectations seen in an
earlier `--full` attempt and the 21 optional concurrency-runtime backend
declines therefore remain separate, open compiler work.

## COMP-018 — post-registration gate invalidated by renewed external drift

**Status:** open coordination issue; no port or Marble parity failure was
established.

The fast gate was rerun after registering the Marble paired-pixel diagnostic
and making the artifact script independent of its caller's working directory.
Stage0 completed green and Stage1 parity was green through the scene stream
until the freshness guard observed
`Elisa-compiler/src/semantic/check_readonly_ref.elisa` newer than
`bin/elisac-stage1`. The same run later reported runtime provenance drift in
the user-owned `elisacore_std/profiler_hooks.elisa` and `runtime.elisa` copies.
The gate therefore refused the remaining Stage1 suites and did not produce a
new compiler certification.

The artifact script itself was corrected to select a Pillow-capable image
Python even when `scripts/env.sh` places a reference venv first on `PATH`.
Running `source scripts/env.sh && bash scripts/test_wasm_artifact.sh` then
exited 0, including the 3D-only N-Back check, the paired-pixel limits, all
Marble board/MJCF/session checks, and the 134-scenario/14,796-state trajectory
oracle. The next top-level certification must wait for one fresh Stage1 seed
after the external compiler's source and vendored runtime state settle.

At the final post-run inspection the user-owned checkout had already advanced
again to `7f84f61f4b019c1be9a4b6c083322e62ce91f848`; its product was
`f1e833758635e1bb1021088e62b7425664ef46a9c3772ef290a08fc02f50496f`, and
`src/parser/parser_stmt_expression_tail.elisa` was newer than that product.
This confirms that the compiler worktree is still active; no reseed or stale
product bypass was performed.

## Out of Sight native adapter boundary — 2026-09-20

The Out of Sight controller directly accessed darray fields inside the
source-owned run, blinds, and flock records. That is valid in the browser
controller but is not a safe native interop boundary. The port now keeps those
accesses in source-owned `adapter_load`/`adapter_save` helpers and transfers
only scalar values and fixed arrays through the controller.

The latest Stage1 product compiled the corrected Python/WASM export, the full
artifact suite passed the Out of Sight smoke, and the SDL3 export compiled and
passed its complete native selftest set. No compiler source change was needed.

## Buzz Wire ABI naming correction — 2026-09-20

The native Python build initially rejected Buzz Wire because its source-side
records used generic names that collided in the global interop namespace. The
port renamed those records (`BuzzWireGrade`, `BuzzWireStep`, `BuzzWireWire`,
`BuzzWireHand`, `BuzzWireRun`, and related helpers), moved wire darray access
behind source-owned adapters, and updated runtime/export/test references.
The latest seeded Stage1 compiler at `1c9c767fe7c386d538253a5b7aba20bfb55b299c`
then passed the full WASM artifact suite, Python module build, and SDL build.
This was a port naming/boundary defect, not a compiler defect.

## Donkey native ABI naming correction — 2026-09-20

The Donkey Python export initially failed with the Stage1 diagnostic that the
named struct `Stage` appeared more than once. The complete export unit already
contains several generic scene records, so Donkey's `Stage`, `Road`, `Beast`,
and `Paint` names were not valid native interop names. The source and
controller records were made unique (`DonkeyStage`, `DonkeyStageRoad`,
`DonkeyBeast`, `DonkeyPaint`, `DonkeyRoad`, `DonkeyCar`, `DonkeyPresses`, and
`DonkeyRun`). The latest Stage1 product then built the pymodule and passed the
Donkey native lifecycle/frame smoke. No compiler change was warranted.

## Two Hands native ABI naming correction — 2026-09-20

Including Two Hands in the complete native export units exposed the same
port-boundary problem: generic `Run`, `Road`, `Ride`, `Solver`, `Play`,
`Hazard`, `Target`, `Paint`, and `Stage` names collided with records from
other included tasks. The source/controller/scene records were renamed to
collision-free `TwoHands*` names and all runtime, export, and test references
were updated. The latest Stage1 compiler then built the Python and SDL export
products, and the Python lifecycle check plus SDL Two Hands selftest passed.
No compiler source change was warranted; the failure was caused by the port's
global ABI namespace and was fixed in Elisa source.

## Overrun native ABI naming correction — 2026-09-20

Adding Overrun to the complete native export units exposed generic
`Wave`, `Pool`, `Run`, `Deadline`, `Score`, and `Paint` records that collided
with other included games. They were renamed to collision-free `Overrun*`
records in the Elisa task/controller/scene source. The latest seeded Stage1
product then built both Python and SDL exports, and their lifecycle/frame
smokes passed. This was another port namespace issue, not a compiler defect;
the compiler freshness guard and latest Stage1 build were retained.

## Current compiler parity checkpoint — 2026-09-29

The latest port verification used the dirty compiler worktree
`Elisa-compiler-latest` at base commit `54360bf68398b4da8d63b82a3ad2979667798aa2`,
seeded with the newest Stage0 oracle at `-O3`. Stage1 product SHA-256:
`ca5d65c417d6f2f0a125ef6e286cd700bbea784c5aba18d04dd4acc2c7f58f4f`. The freshness
guard passed. The compiler source changes include fixed-array spread lowering,
generic UFCS fallthrough, darray-backed reference-field ABI/index lowering, and
local moved `darray`/`dstr` auto-region return rejection.

The moved-container regression is closed: the port fixture and three reduced probes
are rejected by both Stage0 and Stage1, while a plain by-value container return
remains accepted by both. Full driver acceptance passed with 0 with-std
disagreements and 0 accept-gaps in bare mode; the two remaining bare reject-gaps
are the established loop-element and parameter-structural declines. Diagnostics
smoke passed 694/694 fixtures, and native backend smoke passed 545/545 checks.

One separate diagnostic-location defect remains explicitly open: in
`value_block_nested_loop.pos.elisa`, Stage0 emits the mutation-through-call message
at both the loop header and call lines, while Stage1 emits only the call-line copy.
The diagnostic line-parity gate therefore reports 1 defect; its baseline was not
changed. The gen2 self-host gate was skipped because no gen2 product was available.

## Diagnostic line-parity follow-up — 2026-09-29

`resolve_value_blocks.elisa` was corrected so Stage1 preserves Stage0's header and
call diagnostic pair for a mutating method inside a captured statement loop. The
replacement fresh Stage1 product is
`017f7ccac250c6780c7cbd6ada877be81d899b163a37bc7217b1d5ec1240b6b4`.
`diagnostic_line_parity.sh` is now green at 600/600 with zero defects and no
baseline change; diagnostics smoke remains 694/694. This patch changes diagnostic
reporting only, so the earlier full driver-acceptance result remains the applicable
accept/reject measurement; rerun that full gate if a single-product certification
is required.
