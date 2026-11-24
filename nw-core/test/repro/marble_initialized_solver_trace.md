# Initialized Marble solver diagnostics — 2026-10-01

This is a **diagnostic reproduction**, not a production physics change or a
claim that Marble Maze is identical to the original. Keep the strict original
application replay separate from every synchronized/function-level test.

Current recovery checkpoint is the final **Assigned no-slip cost and quadratic**
section below and plan3.13. Historical sections preserve older rejected
candidates; their next-action lists do not override the newest handoff.

## Durable source boundary

Use a fresh, isolated MuJoCo checkout at
`13827e9ee56f097f57acf69ae52b078f9839682d` (MuJoCo 3.12.0). The complete patch
is `marble_initialized_solver_trace.patch`, SHA-256
`3d97b6218c862c70170aa57b8ed4a1a90c2764e976cc76cd6aad9dfaf4f1cc60`.
It describes eleven source files, including the new recorder header. It
already includes the maintained browser arithmetic patch, previous initialized
Newton/cone/dense/RNE instrumentation, and the new live-H recorder. **Do not
apply the maintained parity patch a second time.** Do not apply this patch on a
different revision or an already modified shared engine checkout.

Check the exact HEAD and `git apply --check` before editing. Agent-driven
source edits use the normal file-editing mechanism. A clean pinned checkout
was patched, reverse-apply checked, configured, built, and replayed to validate
this complete recovery boundary. The original dirty diagnostic archive is
not required to reconstruct the source. Dependencies must still be obtained
at the revisions selected by the pinned CMake project.

The separately retained header, `marble_constraint_hessian_trace.h`, SHA-256
`d0acf3a0b34642cd4b89cca28f5d69943235f4deca3cb31006506631430247a5`, is
also included in that patch. It is documentation/recovery material; the
production browser engine does not include it.

## Build and prove recorder neutrality

The tested compiler is Emscripten 6.0.10. Configure with its `emcmake` wrapper,
`-DCMAKE_BUILD_TYPE=Release`, `-DMUJOCO_WASM_THREADS=OFF`,
`-DMUJOCO_BUILD_TESTS_WASM=OFF`, and `-DMUJOCO_BUILD_STUDIO=OFF`.
The pinned project selects `-O3`, thin LTO, platform SIMD, and the existing
debug/source-map binding settings. Do not alter optimization, operand
rounding, or the physics configuration to make instrumentation pass.

Wait for successful CMake configuration before running `cmake --build`;
starting it while configuration is still running produces a missing-cache
error, not a compiler or application regression. Preserve the generated JS
and adjacent WASM together. Retain a neutral pair before experimenting with
arithmetic changes; a trace's provenance must not point at overwritten files.

From the port root, select the diagnostic JS via `NW_MUJOCO_WASM_MODULE` and
run `node nw-core/test/marble_generated_play_session_test.mjs` with:

```text
NW_MARBLE_PLAY_CASE=16:0
NW_MARBLE_PLAY_TRACE_PATH=<new absolute JSON destination>
NW_MARBLE_PLAY_TRACE_CONTACTS=1
NW_MARBLE_PLAY_TRACE_ENGINE_EVENTS=17,18,216
NW_MARBLE_PLAY_TRACE_SPLIT_STEP=1
NW_MARBLE_PLAY_TRACE_PHASES=1
NW_MARBLE_PLAY_TRACE_NEWTON=1
```

Generate a maintained-runtime control using the same current core, board,
inputs, contact/phase flags, and event selection. Compare using
`marble_trace_neutrality.py <control> <diagnostic> --require-provenance`.
This checks all 7,601 events, public states, contacts, and initialized physics
snapshots exactly. Only explicit diagnostic payloads and four unused sparse
index buffers in **explicitly dense** snapshots are excluded. Actual Jacobian,
forces, accelerations, and contact fields are not masked.

Additionally compare complete `newtonTraces` at events 17, 18, and 216 with
the earlier neutral diagnostic capture. The clean reconstruction reproduced
those payloads exactly. It is a bounded capture matrix, not global proof that
all possible scenes remain unaffected by instrumentation.

Verified clean-reconstruction pair:

```text
mujoco.js   02353dac500e531a2ac0dff6dec1cdb303a0f7a21c90c336b44e316a30c4b36a
mujoco.wasm d32224a52bee929136e6390521bfd8ff6566552bee77ba08fba52feff66ff100
```

These differ from an earlier build in a different scratch directory, while
their recorded physics and diagnostic values are exact. Record actual build
hashes; do not require path-dependent debug builds to hash identically.

## Live initialized-H format and limits

The recorder has capacity 300,000 double values. Capture is explicitly
enabled/reset for one traced solver call and then disabled. Its call ordinal
counts **every** `mj_constraintUpdate_impl` entry, including calls that do
not produce a middle-zone Hessian. Overflow is reported and rejected by the
harness and decoder; never accept a silently truncated capture.

Schema 1 repeats records with width `17 + 4*dim + dim*dim`:

```text
schema, callOrdinal, row, nefc, dim, globalContactId, hasCost,
mu, N, T, Dm, NmT,
friction[5], jar[dim], D[dim], R[dim], force[dim], H[dim*dim]
```

Only middle-zone elliptic contacts with dimensions 3, 4, or 6 are recorded.
Copy `H` only **after** the routine has initialized and symmetrized every
active slot. Do not read incoming H, unused trailing 36-slot storage, or a
cache from a top/bottom-zone call. The recorder copies values and performs no
floating-point arithmetic. Global contact ID/row are provenance labels, not
indices to reuse blindly in a reduced native model.

`marble_cone_hessian_oracle.py` validates finite operands, dimensions, schema,
overflow, row bounds, call ordering, impedance/friction positivity, and the
whole selection before native pointer access. It reduces a captured contact
to a one-contact call of the original wheel's `mj_constraintUpdate_impl`.
That local call overwrites all active H slots. It does **not** replay the full
Jacobian-transpose projection, original accumulated cost, or whole solver.
The initialized synthetic incoming H is not asserted to equal omitted live H.

JSON numeric captures do not preserve negative-zero signs. Reports identify
that limitation and distinguish zero-sign-only differences from nonzero
differences. Never claim signed-zero capture fidelity from this fixture.

## Native oracle and durable fixture

The original active arm64 wheel library is `libmujoco.3.12.0.dylib`, SHA-256
`9e7724614fb0b3f346758ff4158ef65e7c398f2caa3e9daab41ed210b4ab689c`.
Use the original application's Python 3.13 venv, not an instrumented native
rebuild, as the authoritative exact-input function oracle. Opt-in native
tests verify architecture and the exact library hash. Include `/usr/sbin`
and `/sbin` in PATH when importing the original pyglet application.

`../fixtures/marble_initialized_hessian_oracle.json`, SHA-256
`8896fd32ec1f6414272b5fc00208dcae0e3a3162eabd3a64b6326ca543a48087`,
contains the 29 initialized H updates and twelve first dense-solve inputs/
stages from events 17, 18, and 216, together with provenance and direct-wheel
expectations. It is a reduced diagnostic fixture, not a full hard trace.

The maintained browser capture differs in live H on three calls/six values,
and force on five calls/thirteen values. The diagnostic constraint-update
arithmetic model matches direct-wheel force/H/state on all 29 inputs.
Its N/T/Dm/NmT labels are modeled intermediates; exported native `mju_norm`
does not turn them into an instrumented view of native internal variables.

The dense-solve operation-order model reproduces direct-wheel results for
all twelve captured first-island solves. All captured forward stages agree;
ten backward solves differ. Reverse stage 2 (solved row 3) is the first
difference in each of the eight event-17/18 cases. Event-216 steps 1 and 2
are already exact; do not claim that every dense solve is wrong.

The rank-update model in `marble_cone_update_oracle.py` separately reproduces
all six event-216 captured-input calls, 1,024 synthetic update/downdate calls,
and zero/clamp edge cases. It includes `x[k]==0` skipping, `mjMINVAL` rank
changes, untouched upper entries, and full modeled post-k vectors/factors.
Native whole-call agreement is checked directly; modeled post-k steps are
not instrumented native wheel stages. The two fused products in a vector
update are not interchangeable; follow the recorded instruction order.

## Test tiers and remaining acceptance gate

The five explicit stdlib-only modules are constraint-update, cone-update,
cone-Hessian, dense-solve, and inertia oracles. With Homebrew Python and no
native-library opt-in they pass 51 tests with nine documented native skips.
Do not use the broad `marble_*oracle_test.py` wildcard in a dependency-free
interpreter: the existing RNE oracle intentionally imports NumPy/MuJoCo.

The eight-module original-venv run additionally includes trace,
trace-neutrality, and RNE-cross tests. With
`NW_MUJOCO_REFERENCE_LIBRARY=<exact original wheel library>` it passes 102
tests, including the durable rejection-record check. Run the actual
browser/MuJoCo contract files too; the intentional
partial-disposal failure message is negative-path coverage.

Passing local primitives cannot authorize promotion. An isolated combined
candidate made all 29 captured force/H updates, twelve dense solves, and the
event-216 rank updates exact, yet failed the uninterrupted original replay
more severely. See the implementation-plan rejection checkpoint before
trying that combination again. Do not relax numeric/contact/result checks,
synchronize the acceptance trajectory, or label a diagnostic early-stop
success as a complete replay pass.

## Validity-aware follow-up (supersedes raw legacy scratch comparison)

After applying the complete patch above, apply
`marble_initialized_solver_validity.patch`, SHA-256
`d7633ad20431528acb41ea362a652b89aeb003f439b742f50d246f23d5509a98`.
This is a two-file diagnostic-only delta, not another arithmetic patch.
Its reverse-apply check passes on the isolated corrected source. Do not apply
the rejected three-primitive delta to a neutral recorder build.

The original constraint-iteration recorder incorrectly used `nv` to copy
`Jv`, whose allocated length is `nefc`. That drops valid rows when `nefc>nv`
and reads beyond the logical allocation when `nefc<nv`. Before the first
search, neither `Jv` nor `search` has been initialized. A previous raw
comparison could consequently treat stale scratch contents as a difference.

Schema 2 has width `10 + 8*nefc + nf + nv + 7*ncontact`:

```text
2, phase, ne, nf, nefc, ncontact, nv, HessianFlag, cost, validityBits,
D[nefc], R[nefc], frictionloss[nf], Jaref[nefc], type[nefc],
id[nefc], state[nefc], force[nefc], Jv[nefc], search[nv],
(dim, mu, friction[5])[ncontact]
```

Validity bits: cost=1, Jv=2, search=4. Zero bits require zero placeholders;
they never cause the actual solver arrays to be zeroed. The context's
diagnostic validity starts at zero in `PrimalPointers` and is marked only
after the actual producer runs. Jv requires search validity. Phase 1 requires
cost validity. Capture has an explicit overflow export; schema 2 without a
false overflow status is rejected. The ordinary Newton recorder similarly
copies Ma/gradient/preconditioned-gradient/search/Jaref only after production
of each field, preserving its historical width and label-aware state checks.

`marble_iteration_trace.py` keeps schema 1 readable but never calls it
initialized-field parity evidence. Mixed or legacy schemas are explicitly
incomparable, not silently successful. Valid later search/Jv values remain
checked, including all rows after row `nv-1`. Native library metadata is
export-driven; absence of the new exports means schema 1, not an inferred
upgrade. The retained native diagnostic library is still schema 1. Build and
qualify an updated native recorder before making schema-2 cross-build claims.

Verified Emscripten 6.0.10 diagnostic pair:

```text
mujoco.js   bb18c8ffbd3d81a430cf5e1c9cd43ced0c2aac78cfe3582bfd0ff0909b6b5e2d
mujoco.wasm 02a9bedf33d580aafcd738cb3d2aa0a866ed5637be80f8ba399099c50e67a0a8
```

The full 7,601-event physics/contact/phase neutrality check passes against
the maintained control. Twelve selected Newton traces decode 166 iteration
records: 72 have explicitly invalid Jv/search represented by zeros, and 94
have initialized Jv/search. Actual recorded `(nefc,nv)` shapes are `(6,6)`
and `(9,6)`; regression tests separately cover `(3,6)` and zero constraints.
Do not require raw schema-1 scratch payloads to equal the corrected zeros.
This does not exempt any initialized physics snapshot or acceptance field.

## Complete preparation model, bounded validation

`marble_primal_prepare_oracle.py` models initialized Gauss coefficients,
scalar rows, elliptic bottom-polynomial accumulation, U/V rescaling,
UU/UV/VV accumulation, Dm, and final half-scaling. Inputs are bounded and
validated before a caller's dot callback can run. Only the initialized
3 scalar or 9 elliptic quad slots are returned; unused trailing storage is
not read. Frictionless contacts earlier in the global contact list are
allowed, but cannot be consumed as an elliptic group.

The active original arm64 wheel's inlined `_mj_solPrimal` range
`0x1017a4..0x1019fc` establishes the constraint order:

- DJ is a separately rounded D*Jaref product; each tangent accumulation is
  `fma(Jaref,DJ,q0)`, `fma(Jv,DJ,q1)`, `fma(Jv*D,Jv,q2)`.
- Rescaled U/V products are rounded before UU/UV/VV accumulation, which is
  sequential `fma(U,U,UU)`, `fma(U,V,UV)`, `fma(V,V,VV)`.
- Dm uses a separately rounded `mu*mu` multiplied by `fma(mu,mu,1)`.
  Replacing both factors with the same rounded square is not equivalent.

`../fixtures/marble_primal_prepare_windows.json`, SHA-256
`0b7f10d11535587e6d48eab9971a833296d9434abb9bf15ce386d9aa8f9cd942`,
retains first-preparation initialized inputs for all eight event-18/216
substeps from the rejected candidate. Its source logs identify the native
diagnostic library previously qualified against the active original wheel
at those eight whole-solver output boundaries. The model matches all 195
retained q1/q2/product/operand probes and ten retained tangent-sum stages
from event 18, substeps 0 and 3. These are SDK-27 diagnostic intermediates,
not direct instrumentation of the original SDK-26 wheel.

Full captured q0, Gauss, and Dm output equivalence is **not yet established**.
Synthetic tests check Gauss callback ordering and active-slot behavior;
those are not full native capture validation. Complete and qualify these
outputs, then continue into PrimalEval cost/derivative order before another
coherent candidate. JSON captures do not preserve zero signs. The corrected
payload names distinguish preparation partial sums from objective cost.

The follow-up explicit stdlib selection adds iteration-trace and preparation
tests to the earlier five modules: 76 tests pass with nine native skips.
The original-venv selection adds the same two modules to the earlier eight:
129 tests pass with the exact original library opt-in. Both Node browser/
MuJoCo contracts pass, including all 16 boards. Upstream still identifies
Stage1 e287. Production artifacts are unchanged; a fresh ordinary strict
maintained replay still rejects the contact set at event 482. No engine
candidate, acceptance tolerance, or other game's implementation is promoted.

## Complete preparation capture and native qualification — 2026-10-02

This section supersedes the earlier statement that complete q0/Gauss/Dm
capture validation is open. It does **not** supersede the strict replay failure
or turn the native rebuild into the authoritative original wheel.

### Exact reconstruction layers

Use a clean isolated checkout at the same engine pin. Apply these in order:

1. `marble_initialized_solver_trace.patch` (complete neutral base above).
2. `marble_initialized_solver_validity.patch` (validity/Jv-size repair above).
3. `marble_initialized_preparation_trace.patch`, SHA-256
   `746bc05442128c8efaaeccb08b086ad9ee845643ed52f02ff9806c425b5f46b6`.
4. For the native diagnostic build only,
   `marble_native_wheel_dot_compatibility.patch`, SHA-256
   `663fcb716bdcf1dbac25afaf25ae3b1ba445671b4a9c58f3a7d67b113b40b7b7`.

The preparation delta contains three files, including its new recorder
header. Forward checks pass on the base+validity checkout; reverse checks
pass on the new prepared source. The native compatibility delta is a separate
single-file layer. Do not apply the rejected three-primitive arithmetic delta
to a neutral recorder tree. Build/retain the neutral WASM pair before changing
experimental arithmetic or overwriting generated output paths.

The preparation recorder is opt-in for one traced solver call, bounded at
300,000 doubles, and exports schema, size, call count, overflow and invalid
status. Copy only after `PrimalSearch` produces Mv/Jv and `PrimalPrepare`
produces all output coefficients. Required initialized bits are
cost|Jv|search|Ma|Jaref = 79. Mv validity is established by this exact callsite,
not by inventing an earlier context validity bit. Invalid and overflow status
are hard diagnostic failures; they never initialize or alter solver arrays.

Schema 1 repeats:

```text
header: [1,ordinal,island,nv,nefc,ne,nf,sparse,blocks,79]
inputs: search[nv],Ma[nv],Mv[nv],qfrc_smooth[nv],
        Jaref[nefc],Jv[nefc],D[nefc],type[nefc],id[nefc]
outputs: quadGauss[3]
each block: [row,dim,globalContactId,type,width],
            [mu,friction[5]] only for elliptic blocks,
            quad[3] for scalar or quad[9] for elliptic blocks
total width: 13+4*nv+5*nefc+sum(5+(dim==1 ? 3 : 15))
```

Ordinals are contiguous from zero within one traced solver call. Scalar rows
consume one constraint row; elliptic blocks consume 3, 4 or 6. No unused
trailing quad storage is copied. The bounded decoder checks numeric arrays,
whole block coverage, repeated group type/id, active widths and friction
parameters before invoking any model/native callback. It localizes only
consumed global contact IDs rather than allocating by a potentially giant ID.
Native copy length is bounded before copying into a ctypes buffer.

### Why the first new native build was not qualified

The native build uses Apple Clang 21, Release O3 and LTO. CMake initially
selected Homebrew lld for Apple bitcode, producing `Unsupported stack probing
method`. Configure this private build with
`DEVELOPER_DIR=/Library/Developer/CommandLineTools`, explicit CLT clang/clang++,
and `-DSUPPORTS_LLD=OFF -DSUPPORTS_GOLD=OFF`. Keep optimization and LTO enabled.
This resolves the linker pairing; it is not a system-setting change or an
Elisa compiler repair. SDK/minimum-macOS warnings in private dependencies are
not deployment qualification.

That successful build still failed all eight initial exact-input solver-output
checks. Its public dot matched the wheel at lengths 1..12, including 6, but
differed on 98/500 length-16 and 94/500 length-18 tests. Inspection shows the
SDK-26 original wheel's generic dot uses separate products in complete
32-element chunks, then fused four-lane quads and the specified tail order.
The newer native compiler selected 16-element chunks. Disabling fusion
globally or assuming a single six-element formula would be the wrong repair.

The native-only compatibility layer spells out the original chunk, quad,
lane-reduction and tail order under Apple arm64 conditional compilation. The
rest of the engine and all WASM arithmetic are unchanged. Both the portable
`marble_native_dot_oracle.py` model and the new native rebuild match direct
original public dot bit-for-bit on 9,200 deterministic finite cases: every
length 0..80 plus 95/96/97, 127/128/129, 255/256/257 and 511/512, 100 cases
per length. Inputs include mixed signs and large scale differences. This is
bounded qualification, not a claim for untested sizes, architectures or
arbitrary toolchains.

Qualified native library SHA-256:
`4e488a77fd270346209afd450ee9b56528988bfa23e7d9c35b20b4fb9ce42eff`.
The original unmodified wheel remains SHA-256 `9e772461...` above; the new
library was built with a different SDK and is not substituted for that wheel.

### Neutrality, qualification and complete output fixture

Retained neutral diagnostic pair:

```text
mujoco.js   2e3eeb80d5718ffd8a13a11b55a39efe4c99077b680472db5db5209db2476fc8
mujoco.wasm 6a1d6f769d06e51926d4a38aaadefed7019e0d6aa4de9af2a371f2cd2844eb35
```

All 7,601 event/public-state/contact/initialized-phase snapshots exactly match
the maintained control, checked with required provenance. Retained trace
SHA-256: `7cf57a3cebd738ebdc8a5e4438839091b1f7126a7739c24354319e2d9b1308d0`.
The corresponding paths are under
`/private/tmp/nw-marble-prepared-trace.PSCe4n0X/`; temporary paths are evidence
locations, not permanent dependencies or production files.

`marble_source_play_trace.py --diagnostic-preparation-jsonl <new-output>` requires
exact active-wheel solver-library validation. Use the original application's
venv, the matching `--native-rne-trace-lib`, `--diagnostic-phase-step`,
`--diagnostic-newton-trace`, `--diagnostic-sync-before-fwdconstraint`,
`--diagnostic-validate-solver-trace-lib`, and the event selector/early-stop
flags. These are synchronized diagnostic probes, never acceptance runs.
Each JSONL boundary preserves explicit true/false qualification, actual
solver-output differences, loaded/RECORD-verified original-wheel identity,
diagnostic library hash and input trace path/hash/runtime provenance. A failed
native rebuild is recorded as false, not accepted because the command exits
successfully after its requested diagnostic stop.

The consumer `qualified_preparations` rejects failed/missing qualification,
incorrect event/substep, unverified active wheel, any output difference, and
any reference/diagnostic/input-trace hash mismatch before decoding a model.

Qualified capture matrix: neutral event 17/18/216, all four substeps, and the
previously rejected three-primitive trace at event 18/216, all four substeps.
All twenty native rebuild outputs exactly match the original wheel's full
existing solver-output field selection on copied inputs. The matrix contains
74 completed preparation calls and 1,167 initialized output coefficients.
The complete preparation model matches all of them, including previously
unvalidated q0, Gauss linear/quadratic coefficients and Dm. The Gauss constant
is passed through from its producer; this does not independently prove the
upstream accumulated cost producer. Actual wheel dot callbacks and the
separately verified portable dot model give the same comparison results.
JSON zero-sign fidelity is explicitly not claimed.

Durable fixture: `../fixtures/marble_primal_prepare_full_oracle.json`, SHA-256
`60721ce1badd3cd76df9118a14d122f33bbe7f8be21d3b64e69832a836c10b5b`.
It contains bounded active captures, whole-output qualification/provenance,
model comparison summaries, source capture hashes and validity-aware native/
WASM comparison summaries. Large unrelated iteration/contact arrays remain
in the hash-identified raw captures. The adjacent generator
`generate_marble_primal_prepare_fixture.py` accepts explicit capture-root,
neutral/candidate traces, reference/diagnostic library paths, and the actual
qualification date via `--captured-on`. It rechecks
all qualification and complete model results before emitting JSON; it never
changes a source, library or production artifact.

The twelve neutral schema-2 pairs are now genuinely comparable and contain
166 iteration records. **All twelve retain real initialized differences**
(Jaref, cost, or force depending on boundary). There is no stale-scratch
explanation or legacy-schema pass for these differences. Whole-output
qualification of the native rebuild does not make the browser identical.

Verification: twelve explicit original-venv modules pass 156 tests with the
original and matching diagnostic library opt-ins. Nine explicitly selected
dependency-light modules pass 103 tests with twelve documented native skips.
Both browser/MuJoCo contract files pass, including all sixteen live boards;
the partial cleanup exception is intentional negative-path coverage. Syntax
checks and narrow tracked-file whitespace checks pass. No headed reload or
complete release acceptance is claimed.

A fresh ordinary maintained original-wheel replay verifies production
provenance, then still rejects contact event 482. Log SHA-256
`07a8bb521ff4533ba44e759cc1de3cf4cfae00378db6eeb73bee8a3f8613921c`.
This is fail-fast, not a new full counted run. Production hashes and strict
thresholds are unchanged. Next complete the original wheel's PrimalEval
cost/derivative order and zone branches before another coherent candidate;
keep the pre-constraint RNE/Jacobian differences in scope.

## Complete evaluation recorder and direct original oracle — 2026-10-02

The preceding pending Eval action is now completed on a bounded matrix.
The next action is a coherent isolated arithmetic candidate, not another
claim that a rebuilt-native intermediate is the original wheel's result.
Strict original full-game parity remains failing and production is unchanged.

### Source layer and build identities

Apply marble_initialized_evaluation_trace.patch after the complete neutral,
validity and preparation layers above. Its SHA-256 is
87e2c278d1523d34c5631923329ab0138882d869ccafa7a02b2c77bd9f4a9965.
Native Apple-arm64 diagnostic builds also use the separate qualified generic-
dot layer above. The Eval delta adds one header and modifies engine_solver.c,
the preparation recorder and generated bindings. It forward/reverse checks
against the retained prepared/evaluation trees. It changes no solver operand.

Private reconstruction root is /private/tmp/nw-marble-eval-trace.AoVTVr62.
Retained final pair is retained-eval-final-dist; final trace is
retained-eval-final-hard-trace.json. Earlier directory names are historical,
not the current reconstruction boundary. One incremental native build needed
the per-process CLT developer-directory selection again. One incremental
WASM build failed because Xcode Python 3.9 was selected; its old outputs were
not accepted as the final pair. The successful rebuild explicitly put
/opt/homebrew/bin on PATH and selected EMSDK_PYTHON=/opt/homebrew/bin/python3.
Keep these process settings for every incremental build, not only configure.

Final diagnostic identities:

~~~text
native lib 446aea43c3a11f1a2d6b03439af645fc35401bf48c75c41545cf03c62ec05840
JS         76f74a67e0c276073a707f3c7660d8298b1af98a36dd676fc0fdacc58088b676
WASM       65f74552c93b1a85999497720fc3da77bda4f669bd03a8fff4de49967b4f9a6a
trace      a09b951e727317e121b5efdd9392e1ef4438f06af5cdfdff4d79b9ef5f9a83d8
fixture    8929d5b67770d137dbc8a913a0c8605e801afaa18235471f7fff96ce49797482
~~~

### Schema and association

The opt-in completed-evaluation recorder is bounded at 300,000 doubles.
Schema 1 repeats:

~~~text
[1,evalOrdinal,preparationOrdinal,island,nv,nefc,ne,nf,
 alpha,cost,firstDerivative,secondDerivative,rawSecondDerivative]
R[nefc],frictionloss[ne:ne+nf]
~~~

Total width is 13+nefc+nf. The friction loss array is compact nf entries
after equality rows, not the older constraint recorder's incomplete prefix.
Prepared Gauss, Jaref/Jv/D/type/id/contact and only active quad coefficients
come from the associated actual preparation. The preparation ID starts at -1
and is set only after successful preparation copy. Required validity mask is
79; completed evaluation is copied only after all outputs are assigned.

marble_eval_trace.py checks explicit false overflow/invalid metadata, schema,
contiguous ordinals, actual preparation association, dimensions, finite arrays,
whole row groups and clamp consistency before modeling or native calls. The
copy function bounds capacity before copying to ctypes. Missing exports in
older diagnostic libraries stay optional; missing evaluation data never
becomes a fake successful capture.

### Direct original routine, not a substituted rebuild

marble_primal_eval_oracle.py includes an exact-wheel-only test bridge.
It refuses anything other than Darwin arm64 and wheel SHA 9e772461... above.
It verifies consumed field offsets and structure sizes, uses dladdr on public
mju_dot to identify the same loaded image/base, and checks entry bytes before
constructing the private function pointer. Original offsets are public dot
0x10c504 and PrimalEval 0x105808. Context/point/contact sizes are 632/32/584;
the plan's final checkpoint records all consumed field offsets.

Only owned, fully validated bounded arrays are passed. The original routine
must increment LSiter once, preserve alpha and return finite values. Partial-
context padding is zero-initialized and is not captured scratch evidence.
Never use these offsets with another wheel, substitute a SDK-27 rebuild for
this oracle, or ship this private bridge as a cross-platform application API.

The complete model matches direct original output bits on 320 captured
selections and 5,145 synthetic selections. The latter comprise 5,000
deterministic mixed cases and 145 branch/boundary cases. Both nine-zone
transition matrices, scalar equality/friction/inequality and 3/4/6-dimensional
cones/degenerate tangents are covered. Untested magnitudes/subnormals and
another architecture/toolchain are not certified by this bounded result.

There are 20 explicitly whole-output-qualified native boundaries with 191
evaluations. The final neutral trace supplies 129 browser evaluations at
events 17/18/216; 50 calls differ from direct original on 75 nonzero output
fields at identical prepared operands. One native rebuild intermediate also
differs: event17/substep2/eval9 second derivative differs by one bit even though
its final solver output passes. The actual original routine is authoritative
for those intermediates; the fixture/test retains this distinction.

All 7,601 event/public/contact/initialized-phase snapshots are exactly neutral
to the maintained control with required provenance. The rejected arithmetic
candidate's older trace does not have completed Eval data and is not
relabeled; only eight corresponding qualified native boundaries are retained.

### Capture and regenerate

Run from the port repository root. In these examples use the final verified
private root above or a new freshly reconstructed equivalent. Keep each
capture filename fresh because JSONL capture appends. For each neutral event
17,18,216, run the original source-play script with:

~~~text
--source-root <original-application-root>
--trace <final-neutral-hard-trace>
--native-rne-trace-lib <verified-new-native-lib>
--diagnostic-split-step --diagnostic-phase-step --diagnostic-newton-trace
--diagnostic-sync-before-fwdconstraint --diagnostic-validate-solver-trace-lib
--diagnostic-validate-solver-trace-event <event>
--diagnostic-stop-after-event <event>
--diagnostic-preparation-jsonl <capture-root>/neutral-final-prepare<event>.jsonl
~~~

Use original-application .venv/bin/python3 and a PATH including /usr/sbin so
pyglet's platform probe works. Repeat events18/216 using the retained rejected
candidate trace and native-wheel-order-prefix-prepare<event>.jsonl names.
Every file must contain exactly four ordered substeps with exactInputCopy and
solverOutputsExactlyEqual explicitly true and empty outputDifferences.
Those flags certify whole outputs only, not every intermediate.

The generator emits JSON on stdout and never changes libraries or sources:

~~~sh
"<original-root>/.venv/bin/python3" \
  nw-core/test/repro/generate_marble_primal_eval_fixture.py \
  --capture-root <capture-root> \
  --neutral-trace <final-neutral-hard-trace> \
  --candidate-trace <retained-rejected-three-primitive-trace> \
  --maintained-control-trace <retained-maintained-control-trace> \
  --reference-library <exact-original-wheel-lib> \
  --diagnostic-library <verified-new-native-lib> \
  --captured-on <actual-YYYY-MM-DD> --compact
~~~

It rechecks all qualification/library/input identities, active wheel provenance,
neutral artifact hashes and exact physics neutrality, then directly checks
the complete model against the original routine before emitting the fixture.
Do not recover a failed qualification by editing its booleans or hash fields.
The saved fixture includes active operands, outputs and original output bits;
large unrelated diagnostic state/iteration arrays are omitted deliberately.

Verification passes: 183 focused original-venv tests; 130 explicitly selected
standard-library tests with 16 expected native skips; renderer/UI contracts;
MuJoCo runtime/contacts/holes/all16 boards. The new native diagnostic dot also
passes all 9,200 cases. Older preparation-native tests are identity-locked to
their earlier qualified library; use that retained file for those tests rather
than broadening their guard to accept a different hash.

Next follow plan3.8's complete candidate sequence. Preserve the chosen fused
operand and separately rounded products in every preparation/Eval branch,
verify actual WASM exact-FMA calls, and retain unresolved RNE/Jacobian producer
differences. A candidate needs ordinary unsynchronized hard replay plus all
independent trajectory/contact/result/render gates before promotion. No
local-only arithmetic result, synchronization or tolerance relaxation is an
acceptable completion of Marble fidelity.

## Coherent candidate v1/v2 recovery and current next producer — 2026-10-02

Both later candidates are rejected. Their durable complete arithmetic deltas
are marble_solver_preparation_eval_rejected.patch and
marble_solver_residual_order_rejected.patch. Apply exactly one after all five
neutral layers described above (including completed evaluation capture).
They are alternatives on that base, not sequential layers. Each includes
the prior three-primitive changes; do not apply that separate delta again.
Plan version 3.9 lists exact patch/fixture/runtime hashes and build settings.

Current private root is /private/tmp/nw-marble-coherent-solver.RvdtgXGz.
Retained v1 pair is retained-coherent-v1-dist; retained v2 pair is
retained-residual-v2-dist. upstream currently contains v2. Native whole-
output qualification uses the neutral 446aea43... diagnostic library from
the completed-evaluation root, not a new candidate-native library.

Generate actual-original evaluator goldens with:

~~~bash
"<original source>/.venv/bin/python3" \
  nw-core/test/repro/generate_marble_solver_probe_inputs.py \
  --reference-library "<original source>/.venv/lib/python3.13/site-packages/mujoco/libmujoco.3.12.0.dylib" \
  > "<owned temporary root>/original-eval-golden.jsonl"
node nw-core/test/marble_solver_compiled_probe_test.mjs \
  "<retained private pair>/mujoco.js" "<owned temporary root>/original-eval-golden.jsonl"
~~~

The probe invokes the actual compiled PrimalEval with bounded packed inputs.
Both candidates pass 1,002 FMA and 5,465 complete evaluator selections; this
does not qualify uninterrupted trajectories or the total Gauss-cost producer.

Generate original-public-dot/compound residual goldens with:

~~~bash
"<original source>/.venv/bin/python3" \
  nw-core/test/repro/generate_marble_noslip_probe_inputs.py \
  --reference-library "<original source>/.venv/lib/python3.13/site-packages/mujoco/libmujoco.3.12.0.dylib" \
  --rejected-fixture nw-core/test/fixtures/marble_solver_preparation_eval_rejected.json \
  > "<owned temporary root>/original-noslip-golden.jsonl"
node nw-core/test/marble_noslip_compiled_probe_test.mjs \
  "<retained private v2 pair>/mujoco.js" "<owned temporary root>/original-noslip-golden.jsonl"
~~~

This passes 9,200 actual original public-dot and 9,205 compound residual
selections. A residual golden is actual original dot plus the specified bias
addition/FMA order, not an original private residual invocation. The historical
browser-specific dot did not fuse the original arm64 wheel's trailing quads/
tails. v2 fixes that first no-slip residual split locally, but remains rejected.

To regenerate the two rejection fixtures, use the corresponding
generate_marble_coherent_rejection_fixture.py or
generate_marble_residual_rejection_fixture.py with:

~~~text
--capture-root /private/tmp/nw-marble-coherent-solver.RvdtgXGz
--reference-library <exact original wheel dylib>
--diagnostic-library /private/tmp/nw-marble-eval-trace.AoVTVr62/build-native/lib/libmujoco.3.12.0.dylib
--captured-on 2026-10-02
~~~

They emit JSON on stdout and require matching retained runtime, trace, core,
golden/probe logs and exact whole-output qualifications. Preserve fixtures
and generators in the repo; private capture paths may disappear. The fixtures
retain concise original/candidate whole-output differences and complete first
residual/force-solve operands so subsequent agents need not infer inputs from
rounded console output. Both fixtures were freshly regenerated and checked
against their saved contents.

For additional native contact records, set NW_MARBLE_DUMP_NOSLIP_TRACE=1 and
run marble_source_play_trace.py with the selected event qualification,
exact-input synchronization and neutral diagnostic library. Use a new log/
JSONL path: qualification JSONL appends. Only the selected event's four
exact-copy rows are qualified; earlier diagnostic log entries from the same
process are not interchangeable matched-input evidence.

Ordinary unsynchronized replay still fails at contact event461. The separate
full contact-continuation diagnostic reports v1 117,451 over-bound values/
302 contact mismatches and v2 115,017 values/204 contacts, first numeric breach
event195 in both. Preserve these rejections alongside local passes.

The next v2 initialized split is the first no-slip QCQP/projection wrapper
force at event17/substep0/island0/iteration0/contact0/tangent4. All input
matrix/RHS/residual/normal/friction/old-force values agree. The original
generic five-tangent QCQP bridge in marble_qcqp_original.py is guarded by the
exact original wheel, validated loaded-image/ABI anchor, offset 0x120704 and
entry bytes ef3bb66ded33016deb2b026de923036d. Its raw force and active=true
result are saved separately. Projection runs; raw original QCQP cannot be
compared directly to the projected browser force.

Next add neutral bounded recordings of raw QCQP output, active flag,
post-projection output and costChange/restoration output separately. Prove
neutrality against retained v2, then compare initialized producer operands
and outputs to direct original calls before changing arithmetic. Keep total
Gauss-cost and pre-constraint RNE/Jacobian work open and require all original
uninterrupted trajectory/contact/result/UI gates before promotion.

## Neutral raw-QCQP outer boundary — 2026-10-02

Apply marble_initialized_qcqp_boundary.patch ONLY after the complete v2
alternative delta on all five neutral layers. SHA-256:
c4193e3dc3600f032d03fb83fc96d06e8a206bd903159102b2ae6b8290b77b0f.
Forward check on unchanged v2 and reverse check on instrumented source passed.
The generated binding additions and new private recorder header must survive
codegen/build preparation. This adds diagnostics, not arithmetic.

Owned root: /private/tmp/nw-marble-qcqp-boundary.kQ2FIfTD.
Retain JS/WASM together in retained-qcqp-dist. Build with the unchanged
Emscripten 6.0.10/Release/single-threaded settings above. Selected hard-run
diagnostics are 0,1,17,18,216, exactly matching the retained v2 control.
Use a NEW trace path and the ordinary generated-play capture flags; no input
synchronization is injected into this run.

~~~bash
"<original source>/.venv/bin/python3" nw-core/test/marble_trace_neutrality.py \
  /private/tmp/nw-marble-coherent-solver.RvdtgXGz/coherent-residual-v2-hard-trace.json \
  /private/tmp/nw-marble-qcqp-boundary.kQ2FIfTD/qcqp-boundary-hard-trace.json \
  --require-provenance
"<original source>/.venv/bin/python3" nw-core/test/marble_qcqp_trace.py \
  /private/tmp/nw-marble-qcqp-boundary.kQ2FIfTD/qcqp-boundary-hard-trace.json \
  --control /private/tmp/nw-marble-coherent-solver.RvdtgXGz/coherent-residual-v2-hard-trace.json \
  --reference-library "<exact original wheel dylib>"
~~~

All 7,601 event/physics snapshots pass exact neutrality against REJECTED v2.
The receipt is saved as fixtures/marble_qcqp_boundary.json, SHA-256
9368f88a7f4bab8e39e0d0ac53714ed1a5a6ad445b3ab2e181d1e719b0c5ed19.
It contains the complete first retained contact plus bounded raw-difference
witnesses, direct original output, counts, identities and reconstructed
original-public-primitive driver steps. The CLI rechecks retained runtime
bytes against their provenance before any private original call. If scratch
paths disappear, reconstruct/replay and record fresh identities; never edit
an old trace's provenance to make a replacement runtime appear identical.

Schema/calls/overflow/invalid metadata are explicit. Header 14 carries schema,
ordinal,island,iteration,row,contact,dim,route,validity,active,projection,
restoration,costChange,normal. Append mu,Ac,bc,oldForce,residual,valid raw/
projected arrays,retainedForce. Full packet widths/branch meanings are in
plan 3.10. Normal-guard packets omit raw/projected arrays rather than copying
uninitialized v. Actual restoration is recorded inside the existing
costChange > 1e-10 branch, not inferred from returned zero.

114 generic calls are directly checked:96 active,18 inactive; 29 have nonzero
raw-force differences and all active flags agree. 18 two-tangent calls and
two normal guards are decoded but not passed to the generic five-tangent ABI.
No actual restoration path is captured. At event17/substep0's first contact,
raw tangent4 bits differ b7f79e6e17344b5a(original) versus
b7f79e6e17344b5b(browser), before projection. The original-primitive driver's
final raw outputs/flags match all 114 captured inputs and 1,000 bounded
synthetic cases. Its intermediate steps remain reconstructed, not direct
original private-state captures.

To inspect the exact original generic kernel without disassembling the
entire Mach-O image, use LLVM's Mach-O-specific selector:

~~~bash
llvm-objdump --macho --disassemble --dis-symname _mju_QCQP \
  --no-show-raw-insn "<exact original wheel dylib>"
~~~

Mach-O address-range options in this environment did NOT limit disassembly
as expected; avoid dumping the entire library. Actual instructions confirm
separately rounded scaling, fused radius subtraction at 0x121074/0x1210a8,
doubled-dot division at 0x1213a0..0x1213a4 and final separate multiplication.

Next add initialized generic-kernel iteration capture with an outer-call
association and branch validity masks, prove neutrality to this retained
observer, and compare the first factor/solve/dot/Newton update difference on
identical operands. Do not globally change arithmetic or assume projection
is already correct. Preserve original strict replay/contact/result/UI gates;
neither observer neutrality nor reference-driver qualification promotes v2.

## Initialized generic kernel and locally corrected radius — 2026-10-02

Plan3.11's final checkpoint is the current handoff. Add
marble_initialized_qcqp_kernel.patch ONLY after the complete residual-v2
alternative and raw-QCQP observer on all five neutral layers.
Patch SHA835ff311c9108abb63ec69847b4d432112f2f91ece5c2d6d017719ff8e9aa2ab.
Owned root:/private/tmp/nw-marble-qcqp-iteration.ZNbeXFzt.
It preserves neutral-source-boundary copies before the arithmetic experiment.
retained-kernel-dist JS4248f115.../WASM46f30623... and kernel-hard-trace.json
SHA4cedfb98... are neutral to the previous outer-observer trace across all7601
events. Header15,branch masks3/7/15/31,actual parent association and variable
widths95/100/105 prevent uninitialized solve/tmp/delta reads. Overflow,
schema,calls and invalid status are explicit. See plan3.11 for every field.

~~~bash
"<original source>/.venv/bin/python3" nw-core/test/marble_qcqp_kernel_trace.py \
  /private/tmp/nw-marble-qcqp-iteration.ZNbeXFzt/kernel-hard-trace.json \
  --control /private/tmp/nw-marble-qcqp-boundary.kQ2FIfTD/qcqp-boundary-hard-trace.json \
  --reference-library "<exact original wheel dylib>"
~~~

The receipt fixtures/marble_qcqp_kernel_boundary.json retains114 groups/
1286 steps;99 first differences are radius subtraction. At known17/0/parent0,
inner iteration13,bits3f70886dd4eadc34 browser versus3f70886dd4eadc35 original
disassembly-backed fma(-r,r,norm). Factor/solve/dot/scaling inputs preceding
this split agree. The independently final-qualified driver's internals are
reconstructed, not original private-state captures.

The additive marble_qcqp_fused_radius_rejected.patch changes only the generic
browser radius operation plus diagnostic actual-kernel probe/binding.
SHA30e36adf452b2546d27d4395ac4bd487be1db02f2f8caa2809d181da40216efa.
Apply only on the complete neutral kernel observer, not directly on production.
The unchanged private Emscripten6.0.10 build yields retained-fused-candidate-dist
JSb27ca7ab.../WASM268fc5e3... . Use the existing build recipe above and retain
these paths; generated binding edits must not be lost to codegen.

~~~bash
"<original source>/.venv/bin/python3" nw-core/test/repro/generate_marble_qcqp_probe_inputs.py \
  --trace /private/tmp/nw-marble-qcqp-iteration.ZNbeXFzt/kernel-hard-trace.json \
  --control /private/tmp/nw-marble-qcqp-boundary.kQ2FIfTD/qcqp-boundary-hard-trace.json \
  --reference-library "<exact original wheel dylib>" > "<new golden JSONL>"
node nw-core/test/marble_qcqp_compiled_probe_test.mjs \
  /private/tmp/nw-marble-qcqp-iteration.ZNbeXFzt/retained-fused-candidate-dist/mujoco.js \
  "<new golden JSONL>"
~~~

The actual compiled generic kernel matches all114 captured+1000 synthetic
original raw vectors/active flags including IEEE zero signs;13 malformed
packets are rejected. The fixed38-value packet is schema,n5,radius,A25,b5,mu5.
This does not test projection/restoration or QCQP2/3.

Capture the candidate with the SAME ordinary7601-event generated-play schedule,
contacts,split/phase/Newton and selected events0,1,17,18,216. Keep fresh trace
and qualification paths. The candidate is arithmetic, not a neutral observer.
Its first changed physics is event1's pre-step efc_force. Explicit comparison:

~~~bash
"<original source>/.venv/bin/python3" nw-core/test/marble_qcqp_kernel_trace.py \
  /private/tmp/nw-marble-qcqp-iteration.ZNbeXFzt/fused-candidate-hard-trace.json \
  --control /private/tmp/nw-marble-qcqp-iteration.ZNbeXFzt/kernel-hard-trace.json \
  --reference-library "<exact original wheel dylib>" --arithmetic-candidate
~~~

This checks retained runtime bytes but records claimed=false and changed
physics, never pretending candidate and control are neutral. All114 new
captured raw returns/flags and1286 initialized stages match their respective
original controls. Do not mix these changed inputs with the old v2 receipts.

Ordinary original replay WITHOUT input sync still rejects:
first contact difference443;full diagnostic111077 over-bound values,
136 contacts443..1966;first numeric breach195/value10 delta8.227014482997674e-7.
Terminal timeout matches but cannot override numeric/contact rejection.
Selected native exact-input qualifications17,18,216/four substeps all pass;
whole original outputs differ on7/12,iteration costs on8/12,no-slip contacts
on7/12. First formerly split projected wrapper is exact on NEW matched inputs.
Preparation47 calls/753 values and129 actual original evaluations match.

Actual original constraint-update CLI on events0,1,17,18,216 checks38 calls:
all force/state/cost nonzero values match;its model also qualifies. Eleven
calls have JSON-lost zero-sign differences. CLI status1 here reflects those
unverified signs, not a nonzero output failure. This does not test surrounding
Gauss addition/J-transpose multiplication.

Receipt generation expects retained compiled/golden/kernel/full replay logs
and all12 exact-output-qualified native captures. Use fresh output paths;
qualification JSONL appends and must contain exactly four selected rows.

~~~bash
"<original source>/.venv/bin/python3" nw-core/test/repro/generate_marble_qcqp_rejection_fixture.py \
  --capture-root /private/tmp/nw-marble-qcqp-iteration.ZNbeXFzt \
  --reference-library "<exact original wheel dylib>" \
  --diagnostic-library /private/tmp/nw-marble-eval-trace.AoVTVr62/build-native/lib/libmujoco.3.12.0.dylib
~~~

Saved fixtures/marble_qcqp_fused_radius_rejected.json has SHAee00934f... .
Its NumPy cost probes are RECONSTRUCTIONS, not captured native producers.
Next add initialized Gauss/total-cost and no-slip costChange producer
recording, prove exact neutrality to this corrected PRIVATE candidate before
more arithmetic, then validate first actual original producer operands.
Do not promote a locally correct generic operation until every strict original
trajectory/contact/result and rendered UI gate passes together.

## All-call Gauss and small-QCQP recovery — 2026-10-02

Marble remains first. These are private diagnostic layers, NOT shipped fixes.
Source root:/private/tmp/nw-marble-gauss-boundary.qbjhDfzx/upstream.
Pin13827e9ee56f097f57acf69ae52b078f9839682d. Apply the prior nine QCQP
recovery layers (through fused radius) in their documented order, then:

10. marble_initialized_gauss_trace.patch,
    SHA0120a1f6a3ecf9082ad2a8525d74676ad9ac3eaa8b1ff16d973a1e2b82b3755e.
11. marble_gauss_native_order_rejected.patch,
    SHA1262c12ce389d3cc7837f4197561219efcf354a1cf87c887ec2c0e75986a5e16.
12. marble_qcqp2_native_order_candidate.patch,
    SHA94ac847cae2291eb9001882a973f11865410b24b3c7219dd8af1025182ac0cea.

No duplicate production patch or earlier v1/three-primitive alternative.
Keep generated binding edits through codegen/builds. Forward checks use exact
preserved neutral-source-boundary and qcqp2-source-boundary files; reverse
checks passed on each resulting source at its checkpoint. The source now
includes all twelve layers. Keep all retained dist pairs immutable.

### Original scope and assigned capture

The all-call S2 oracle checks125 actual original constraintUpdate impl calls,
including106 later calls. Force/state/cost and reference-model nonzero outputs
match;10 JSON-lost zero-sign-only calls are unverified signs. It excludes
Gauss,J-transpose multiplication,input contact-H and whole physics acceptance.
SDK27 rebuilt-native intermediate cost differences are not actual-original
constraintUpdate evidence.

Gauss schema1 header9:ordinal,island,nv,nefc,valid3,assigned costBefore/
costAfter/Gauss plus schema. Five nv arrays are Ma,qfrc_smooth,qacc,
qacc_smooth and actual assigned partial sums. Width9+5nv,nv<=512,capacity
300000; actual ownership to every S2 update and explicit overflow/invalid
metadata are mandatory. No copied scratch or recomputed observer arithmetic.
Original Gauss uses the exact-wheel guarded private primal routine with a
fully owned zero-constraint632-byte context. That isolates actual final Gauss
but does not capture original private partial sums/full primal contexts.
The original eight-dof rounded prefix/scalar-FMADD tail model is final-qualified.

### Neutral observer and Gauss candidate

retained-gauss-dist:JSad6863f1.../WASMb84292b5...;
gauss-hard-trace.json SHA273367cb... is exactly neutral over7601 events to
the prior radius candidate SHAf76fe3c8... . It is not accepted original physics.
Actual original Gauss differs43/125 calls,partial model48 calls.
Layer11's actual compiled zero-constraint primal probe passes125 captured+
1000 synthetic Gauss/final-cost IEEE results,16 malformed rejects.
retained-gauss-candidate-dist:JSc7c2710e.../WASM7fe45567...;
gauss-candidate-hard-trace.json SHA874e5c44... . All125 captured Gauss/
constraint/total/partial outputs now match. All7601 recorded physics/input/
contact fields remain exactly unchanged. Explicit arithmetic mode still says
claimed=false; no trajectory improvement is inferred.
Ordinary original replay still111077 numeric exceedances/136 contacts,
first numeric195/value10 delta8.227014482997674e-7. No promotion.

~~~bash
"<original source>/.venv/bin/python3" nw-core/test/marble_iteration_constraint_oracle.py \
  /private/tmp/nw-marble-gauss-boundary.qbjhDfzx/gauss-hard-trace.json \
  --reference-library "<exact original wheel dylib>" \
  --event 0 --event 1 --event 17 --event 18 --event 216
"<original source>/.venv/bin/python3" nw-core/test/marble_gauss_trace.py \
  /private/tmp/nw-marble-gauss-boundary.qbjhDfzx/gauss-hard-trace.json \
  --control /private/tmp/nw-marble-qcqp-iteration.ZNbeXFzt/fused-candidate-hard-trace.json \
  --reference-library "<exact original wheel dylib>"
"<original source>/.venv/bin/python3" nw-core/test/repro/generate_marble_gauss_probe_inputs.py \
  --trace /private/tmp/nw-marble-gauss-boundary.qbjhDfzx/gauss-hard-trace.json \
  --control /private/tmp/nw-marble-qcqp-iteration.ZNbeXFzt/fused-candidate-hard-trace.json \
  --reference-library "<exact original wheel dylib>" > "<fresh golden JSONL>"
node nw-core/test/marble_gauss_compiled_probe_test.mjs \
  /private/tmp/nw-marble-gauss-boundary.qbjhDfzx/retained-gauss-candidate-dist/mujoco.js \
  "<fresh golden JSONL>"
"<original source>/.venv/bin/python3" nw-core/test/repro/generate_marble_gauss_rejection_fixture.py \
  --capture-root /private/tmp/nw-marble-gauss-boundary.qbjhDfzx \
  --reference-library "<exact original wheel dylib>"
~~~

### Separate two-tangent kernel and latest rejected full trace

Original public QCQP2/QCQP3 symbols are exact-image/address checked in
marble_qcqp_small_original.py. All dimensions/finite operands/scales/radius
are checked before native calls; outputs/flags/immutable inputs afterward.
This trace has18 QCQP2 calls,ZERO QCQP3.11 raw vectors differ before layer12;
active flags match. The instruction-ordered QCQP2 model is final-bit-qualified
on18+1000 cases. Reconstructed iterations are not original private captures.
Layer12 changes only __EMSCRIPTEN__ QCQP2 arithmetic plus an actual compiled
probe/binding. Packet11 is schema1,n2,radius,A4,b2,mu2. It validates the whole
packet before calling mju_QCQP2.18 captured+1000 synthetic cases pass,13
malformed packets are rejected. QCQP3 arithmetic is untouched.

Latest retained pair:retained-qcqp2-candidate-dist,
JS7c65c25e9869ff9f75f14ca50a3f14c256650e9bef35bf25677e9ecc6932c892,
WASM60b0852b843fb749a773c023380904104aaf1dab604cd5d8f68db93a90412a2f.
Trace qcqp2-candidate-hard-trace.json
SHAf797cd91293f30590ffe689ae6c1d221f831c823587d8036e87eb86e35dbc083.
NEW-input QCQP2 raw/flags18,Gauss125,generic QCQP114/1286 initialized steps
remain locally exact. Ordinary full original replay STILL FAILS:
114869 numeric exceedances;162 contacts443..2536;
first numeric195/value10 delta8.252424372745537e-7;
timeout120.016667s/home0/lost0.
First changed physics versus Gauss control is
events[17].engineStep1Inputs[2].arrays.efc_force[7].

~~~bash
"<original source>/.venv/bin/python3" nw-core/test/repro/generate_marble_qcqp2_probe_inputs.py \
  --trace /private/tmp/nw-marble-gauss-boundary.qbjhDfzx/gauss-candidate-hard-trace.json \
  --reference-library "<exact original wheel dylib>" > "<fresh golden JSONL>"
node nw-core/test/marble_qcqp2_compiled_probe_test.mjs \
  /private/tmp/nw-marble-gauss-boundary.qbjhDfzx/retained-qcqp2-candidate-dist/mujoco.js \
  "<fresh golden JSONL>"
NW_MUJOCO_WASM_MODULE="<latest retained pair>/mujoco.js" \
NW_MARBLE_PLAY_CASE=16:0 NW_MARBLE_PLAY_TRACE_PATH="<fresh trace path>" \
NW_MARBLE_PLAY_TRACE_CONTACTS=1 NW_MARBLE_PLAY_TRACE_ENGINE_EVENTS=0,1,17,18,216 \
NW_MARBLE_PLAY_TRACE_SPLIT_STEP=1 NW_MARBLE_PLAY_TRACE_PHASES=1 \
NW_MARBLE_PLAY_TRACE_NEWTON=1 node nw-core/test/marble_generated_play_session_test.mjs
"<original source>/.venv/bin/python3" nw-core/test/marble_source_play_trace.py \
  --source-root "<original source>" --trace "<fresh trace path>"
# Independently obtain full counts; this diagnostic mode is not acceptance.
"<original source>/.venv/bin/python3" nw-core/test/marble_source_play_trace.py \
  --source-root "<original source>" --trace "<fresh trace path>" \
  --diagnostic-continue-contact-mismatches
"<original source>/.venv/bin/python3" nw-core/test/marble_qcqp2_trace.py \
  "<latest retained trace>" --control "<retained Gauss candidate trace>" \
  --reference-library "<exact original wheel dylib>"
"<original source>/.venv/bin/python3" nw-core/test/repro/generate_marble_qcqp2_rejection_fixture.py \
  --capture-root /private/tmp/nw-marble-gauss-boundary.qbjhDfzx \
  --reference-library "<exact original wheel dylib>"
~~~

Generators require the exact retained capture/report/log names and identities,
all actual compiled proofs and original goldens. Latest QCQP2 receipt additionally
retains current-input Gauss and generic reports. Reproduce those with their
trace CLIs, latest trace/control and --arithmetic-candidate. Do not overwrite
the old proof logs with a later runtime identity. Runtime paths are part of
capture provenance; relocated files require explicit retained-byte checks.

Next build a bounded branch-valid actual no-slip costChange observer and prove
neutrality against THIS latest QCQP2 trace before further arithmetic. Capture
actual quadratic/dot/pre-restoration/final/restored-force values, not second
evaluations or NumPy reconstructions. Original public primitive comparisons
qualify those primitives only; no standalone costChange symbol is established.
Never invoke a private instruction range as a function. Projection/restoration
and pre-constraint RNE/Jacobian remain open. All strict original gameplay,
successful tray/contact/result/matrix/UI gates are required together to ship.

## Assigned no-slip cost and quadratic — 2026-10-02

Current source recovery is FOURTEEN ordered layers: all twelve from the
preceding checkpoint, followed by neutral
`marble_initialized_costchange_trace.patch` (SHA25098c9a1a410fd7863faf71c6291404d56fd8b911b6dbc20f5cd6d6e284616b)
and arithmetic/probe-only `marble_quadratic_native_order_candidate.patch`
(SHA4a263a9ef7e278a88cc3919a42e3709d92837754fb6ae85f8ffca0eeeade9035).
The complete arithmetic candidate is REJECTED. No production files changed.
Do not duplicate maintained parity, the complete v2 alternative or layer13.
Both new deltas were forward/reverse checked on their exact boundaries.

Owned root:`/private/tmp/nw-marble-costchange.7SuZEZYO`; its upstream currently
includes14. Build with the previously pinned Emscripten6.0.10/O3/thin-LTO/
single-thread Release options and `EMSDK_PYTHON=/opt/homebrew/bin/python3`.
Retain JS/WASM together before another build. Never overwrite either retained
directory or let a trace's runtime provenance point at overwritten bytes.

Neutral pair:`retained-cost-observer-dist`, JS7c65c25e.../WASM00c528b8...;
`cost-observer-hard-trace.json` SHA4200ce65... . Arithmetic pair:
`retained-cost-candidate-dist`, JScceca307.../WASMe0e4965d...;
`cost-candidate-hard-trace.json` SHAc2f09fb8... . Full hashes are recorded in
plan3.13 and the manifest. Neutral observer's control remains prior
`/private/tmp/nw-marble-gauss-boundary.qbjhDfzx/qcqp2-candidate-hard-trace.json`
SHAf797cd91... . That control is rejected arithmetic, not production.

Capture both new hard traces with the prior command, changing the module and
destination to the correct retained pair and selecting engine events
`0,1,17,18,216`. Keep case16:0/contact/split/phase/Newton flags and the
production core unchanged. The neutral capture has7601 EXACT physical/input/
contact events and every old assigned diagnostic payload unchanged. Inventory
traceKeys permits only the five named cost fields; no assigned value is waived.

Cost schema1 header13 is ordinal/island/iteration/row/contact/dimension/valid7/
restored/actual quadratic/actual dot/pre-change/final-change after schema.
Append matrix,old force,before force,residual,actual delta,final force with
width13+n*n+5*n,n2/3/5,capacity300000. Explicit schema/calls/overflow/invalid
metadata and actual QCQP owner pairing are mandatory. Every scalar is the
actual once-evaluated producer return. Normal-guard output is a real branch;
outside elliptic no-slip calls are not captured. Do not impose a recomposed
FMA value when decoding the actual assigned pre-change scalar.

Using the original application's Python3.13.12 and exact wheel9e772461...:

~~~sh
<original-python> nw-core/test/marble_costchange_trace.py \
  /private/tmp/nw-marble-costchange.7SuZEZYO/cost-observer-hard-trace.json \
  --control /private/tmp/nw-marble-gauss-boundary.qbjhDfzx/qcqp2-candidate-hard-trace.json \
  --reference-library "<exact original wheel dylib>"

<original-python> nw-core/test/marble_costchange_oracle.py \
  /private/tmp/nw-marble-costchange.7SuZEZYO/cost-observer-hard-trace.json \
  --reference-library "<exact original wheel dylib>"

node nw-core/test/marble_cost_primitives_compiled_probe_test.mjs \
  /private/tmp/nw-marble-costchange.7SuZEZYO/retained-cost-candidate-dist/mujoco.js \
  /private/tmp/nw-marble-costchange.7SuZEZYO/original-cost-primitives-golden.jsonl
~~~

The first command emits the neutral receipt, the second emits original golden
JSONL. Preserve stdout using unique log destinations in an actual rerun;
do not overwrite existing captures. Golden SHA668b8dad... . Exact original
public routines are loaded-image guarded and validate complete finite operands
before pointers; the model uses row-dot order plus increasing-row outer FMA.
Models of row/final-cost/restoration intermediates are not original captures.
Original defined-symbol inventory did not establish a standalone costChange or
projectEllipsoid callable; never invoke an inlined instruction range.

Neutral134 calls (20 n2,114 n5,zero n3) show22 quadratic/zero dot mismatches,
three composed pre/final mismatches,zero composed restoration splits and no
captured restoration. Candidate matches all134 actual public returns and
composed results. Probe matches134 captured+1000 synthetic IEEE cases and
rejects18 malformed inputs. Three-tangent quadratic has333 synthetic cases
ONLY; there is no captured three-tangent Marble/QCQP3 claim.

For candidate cost/Gauss/generic reports use their trace CLIs with the candidate
trace, observer trace as `--control`, exact `--reference-library` and
`--arithmetic-candidate`. Small-QCQP uses its explicitly arithmetic trace CLI
without that flag. Current regressions stay Gauss125,generic114/1286 steps,
QCQP2-18 exact. Re-run frozen compiled producer probes on the new pair, not
by reusing old reports with mismatched runtime provenance.

All7601 recorded physics fields are EXACTLY unchanged by the arithmetic delta.
The arithmetic receipt nevertheless says claimed=false/arithmeticCandidate=true;
do not relabel it a neutral observer. Ordinary original replay still rejects:
strict contactE443; full diagnostic114869 numeric exceedances/162 contacts
443..2536; first numericE195/value10 delta8.252424372745537e-7; timeout
120.016667/home0/lost0. No forced synchronization was used in either replay.

~~~sh
<original-python> nw-core/test/marble_source_play_trace.py \
  --source-root "<original checkout>" \
  --trace /private/tmp/nw-marble-costchange.7SuZEZYO/cost-candidate-hard-trace.json

<original-python> nw-core/test/marble_source_play_trace.py \
  --source-root "<original checkout>" \
  --trace /private/tmp/nw-marble-costchange.7SuZEZYO/cost-candidate-hard-trace.json \
  --diagnostic-continue-contact-mismatches

<original-python> nw-core/test/repro/generate_marble_costchange_rejection_fixture.py \
  --capture-root /private/tmp/nw-marble-costchange.7SuZEZYO \
  --reference-library "<exact original wheel dylib>"
~~~

Full-count mode is diagnostic, not an alternate acceptance gate. Ensure
`/usr/sbin:/sbin` are on PATH for the original pyglet environment. Generator
requires exact retained report/proof/golden/log names and validates identities,
neutrality,prior diagnostics,actual original returns,current regressions and
independent rejection. Saved fixture SHA48126278... is reproduced byte-exactly.

Latest full exact-input original solver requalification is now complete as
recorded below. Prioritize earliest pre-constraint RNE/Jacobian/phase input
drift first; reopen projection only with contrary actual output evidence.
Cleared Gauss/quadratic ulp mismatches were inert on this schedule.
No compiler defect was established. All original hard/success/contact/result/
trajectory/matrix/UI gates are still mandatory together before promotion.

### Final latest exact-input whole-solver localization

Replay the current trace through the existing qualified native diagnostic
library446aea43... and active original wheel9e772461... with:

~~~text
--native-rne-trace-lib <qualified native dylib>
--diagnostic-newton-trace
--diagnostic-sync-before-fwdconstraint
--diagnostic-validate-solver-trace-lib
--diagnostic-phase-step
--diagnostic-split-step
--diagnostic-stop-after-event 216
--diagnostic-solver-output-json <new original outputs JSONL>
--diagnostic-preparation-jsonl <new qualified captures JSONL>
--provenance-json <new native provenance JSON>
~~~

This is SYNCHRONIZED diagnostic localization only. The retained filenames in
the owned cost root are cost-candidate-qualified-outputs.jsonl,
cost-candidate-qualified-captures.jsonl,cost-candidate-native-provenance.json
and cost-candidate-whole-qualified.log. Their qualification documents retain
the active loaded-wheel hash,exact model/data/contact/option input-copy checks
and diagnostic-library final-output qualification on current tracec2f09fb8... .
All20 boundaries (events0,1,17,18,216 and four substeps each) qualify native
final outputs against the original wheel. Rebuilt private intermediates are
NOT original private captures.

Compare all21 final original arrays with current browser fwdConstraint arrays.
No field is exempted. Eighteen boundaries have no numeric output difference;
E17/substep1 andE18/substep2 retain only one solver_stats ulp each. All
recorded non-statistic force/acceleration/state/island outputs agree. Browser
JSON zero signs remain unqualified. This narrows upstream investigation but
does not prove a particular upstream routine wrong or qualify unsampled events.

~~~sh
<original-python> nw-core/test/repro/generate_marble_costchange_whole_solver_fixture.py \
  --capture-root /private/tmp/nw-marble-costchange.7SuZEZYO
~~~

The generator validates complete20 selection/provenance/qualification and
every finite bounded21-field output before comparing. Fixture
marble_costchange_whole_solver.json SHAc4ccba45... retains both statistic
splits,not a waiver. Latest311 original-runtime tests and271 dependency-light
tests (31 explicit native skips) pass. Strict ordinary hard replay remains
rejected and production hashes remain unchanged.

## Actual-original shared inertia on the current combined candidate — Oct2

Current plan3.14 supersedes3.13. Preserve the fourteen layers and their pairs
above; add marble_inertia_native_order_candidate.patch as layer15 ONLY.
SHA c88a317e5c3d41d31fecd40cdb13ce1739137d639e50333dac393875e42caf7c.
Forward-check on14/reverse-check on15 pass. The disposable upstream at
/private/tmp/nw-marble-costchange.7SuZEZYO/upstream now includes15. Build
flags remain Emscripten6.0.10/Release/O3/thin-LTO/single-thread,not global FMA.
Do not overwrite retained-cost-candidate-dist or earlier pairs when rebuilding.

This is a platform-guarded actual public mju_mulInertVec correction plus
bounded real probe/binding,not a complete RNE replacement. The helper is
SHARED with mass-matrix/initialization/derivative callers; full physics changes
cannot be attributed solely to RNE. Original public symbol0x12ba10/image/hash
guard,complete finite packet/owner/body/options/sleep validation and all-packet
prevalidation are in test/marble_inertia_original.py. The unguarded older
inertia CLI is historical; use this guarded oracle for current evidence.

Before:120 actual captured products,42 differing calls/66 nonzero values.
After:all120 current products match. Compiled probe matches120 captured+1000
synthetic original return bits;12 malformed packets reject. Golden
original-inertia-golden.jsonl SHA6af673f24a8a5b485ad3377ecbba22a7a4971191ccc4a5a387ec342e065b4809.
The complete golden is generated from14's captured operands; new current-input
comparisons separately use15's operands. Do not confuse those two checks.

Retained15 pair:retained-inertia-candidate-dist/mujoco.js
SHAc477b87e1ced0dee08ee9d451c4b56facb478024b7e7155918f2041f274a25b8;
adjacentWASM7150d99f969711aecabe6a295d9a64f6f720942de62d885977296b9fce88cb1b.
Trace inertia-candidate-hard-trace.json
SHAb0b65c58fd0a1c86f512686b3e53ebd7622bc56f17165c9b82d982ab273ce41e.
Input schedule/configuration identities match14 for7601 events. Physics is
NOT neutral:first E0/substep1 qacc4 changes0 to -4.9679927381240586e-27.
Current cost134/Gauss125/generic114+1286steps/QCQP2-18 and all four frozen
compiled producer proofs remain exact.

Commands from repository root (redirect outputs to fresh owned paths; do not
overwrite existing retained evidence):

~~~bash
NW_INERTIA_ROOT=/private/tmp/nw-marble-costchange.7SuZEZYO
NW_INERTIA_PY='/workspace/neural-workshop-enhanced/.venv/bin/python3'
NW_INERTIA_LIB='/workspace/neural-workshop-enhanced/.venv/lib/python3.13/site-packages/mujoco/libmujoco.3.12.0.dylib'

"$NW_INERTIA_PY" nw-core/test/marble_inertia_original.py \
  "$NW_INERTIA_ROOT/cost-candidate-hard-trace.json" \
  --control "$NW_INERTIA_ROOT/cost-candidate-hard-trace.json" \
  --reference-library "$NW_INERTIA_LIB" --golden

node nw-core/test/marble_inertia_compiled_probe_test.mjs \
  "$NW_INERTIA_ROOT/retained-inertia-candidate-dist/mujoco.js" \
  "$NW_INERTIA_ROOT/original-inertia-golden.jsonl"

"$NW_INERTIA_PY" nw-core/test/marble_inertia_original.py \
  "$NW_INERTIA_ROOT/inertia-candidate-hard-trace.json" \
  --control "$NW_INERTIA_ROOT/cost-candidate-hard-trace.json" \
  --reference-library "$NW_INERTIA_LIB"

"$NW_INERTIA_PY" nw-core/test/repro/generate_marble_inertia_rejection_fixture.py \
  --capture-root "$NW_INERTIA_ROOT" --reference-library "$NW_INERTIA_LIB"

"$NW_INERTIA_PY" nw-core/test/repro/generate_marble_costchange_whole_solver_fixture.py \
  --capture-root "$NW_INERTIA_ROOT" --candidate-prefix inertia-candidate
~~~

Hard trace generation uses the same prior play-harness command but15's retained
JS/adjacentWASM and a new inertia-candidate-hard-trace.json output. Flags:
NW_MARBLE_PLAY_CASE=16:0,NW_MARBLE_PLAY_TRACE_CONTACTS=1,
NW_MARBLE_PLAY_TRACE_ENGINE_EVENTS=0,1,17,18,216,
NW_MARBLE_PLAY_TRACE_SPLIT_STEP=1,NW_MARBLE_PLAY_TRACE_PHASES=1,
NW_MARBLE_PLAY_TRACE_NEWTON=1. Run the ordinary original source comparator
with no synchronization/no result-only mode. It stops at contactE463. A
SEPARATE --diagnostic-continue-contact-mismatches full-count run retains all
7601 events,110690 numeric breaches,105 contact mismatches463..1966 and first
numericE195/value10 delta4.996572333659799e-7 vs1e-7. Timeout120.016667/home0/
lost0 is not acceptance. The complete game candidate is REJECTED,not promoted.

Fixture marble_inertia_native_order_rejected.json
SHA9a8356878e825d0eda8a234cea2f777a8d6ac5852bfa7acc3a136f5db675e739.
Generator requires both original comparison receipts,the full original golden,
actual compiled proof,four new current-input producer reports,four frozen
compiled regression logs and both independent replay failures. It rechecks
actual returns and artifact identity rather than trusting reported success.

Fresh exact-input solver qualification uses the existing original-driver command
with15's trace/new inertia-candidate-qualified-{outputs,captures}.jsonl,
inertia-candidate-whole-qualified.log and stopE216. All20 diagnostic-library
final outputs qualify against the actual original wheel. All21 browser fields
are compared;three statistic ulps atE17/1,E18/2,E216/2 remain,no other numeric
force/acceleration/state/island differences. Explicit synchronized localization
is not ordinary acceptance or private SDK27 intermediate identity. Whole fixture
marble_inertia_whole_solver.json
SHA92fd7f33936ac6ecbdd8c5e94d53ab467673221a0422decbb36ac2178c3d87ee.
Both new receipts/golden and the old default whole-solver receipt regenerate
byte-exactly.326 original methods/286 dependency-light methods(32 native skips)
pass. Options1344,renderer and all16 maintained boards pass. Shipped hashes
unchanged. Next audit a complete qualified upstream RNE/cross/Jacobian/
integration family,not another presumed isolated FMA fix or compiler mutation.

## Complete actual-original RNE bias on the current candidate — Oct2

Plan3.15 supersedes3.14's complete-RNE next action. Preserve layers1–15 and
all retained pairs above; add marble_rne_bias_family_candidate.patch as layer16
ONLY, on pinned MuJoCo commit13827e9ee56f097f57acf69ae52b078f9839682d.
Patch SHA b6084b8a42ae41f6aea63c95c3eb539840efdb95e9d77b232f30cd3aacf688e6.
Forward-check on15/reverse-check on16 pass. Blank context lines containing a
single space in this unified patch are intentional; do not trim them away.
No new compiler source edits or global contraction flags are part of16.

The Emscripten-guarded helper family changes only mj_rne's flg_acc=0 path and
its diagnostic mirror. Complete public original mj_rne is the authority, not
an assumed standalone cross-force ABI or a rebuilt private intermediate.
Original symbol offset0x60ef8/image SHA9e7724614fb0b3f346758ff4158ef65e7c398f2caa3e9daab41ed210b4ab689c
and owned native model/data/input checks are in test/marble_rne_original.py.
Sleep-enabled models reject before native calls. Complete tree/DOF ownership,
finite bounded input arrays and unique named before/after phases are required;
the actual return must equal the assigned trace tail. Native imports are
deferred so malformed-input and fixture guards also run without NumPy/MuJoCo.

Before16:10 of20 current complete RNE returns differ,21 nonzero output values.
After16:all20 actual-original returns agree; separately reconstructed bias
outputs agree bitwise on these inputs. Golden original-rne-golden.jsonl
SHAfb83534383fa8546a88996af188b88fe25eec9fd381f1866c813f49d4a5b8699
contains20 captured+1000 synthetic actual-original returns, across single
free-body,three-free-body and nested free/hinge layouts. This golden uses15's
captured operands; the new20 current-input comparison uses16's operands.
Compiled16 matches all1020 actual-original bias return bits. An independent
15-versus16 compiled flg_acc=1 control matches all1020 outputs; this proves
that path unchanged, not original-wheel acceleration-path qualification.

Retained16 pair:retained-rne-family-candidate-dist/mujoco.js
SHAc477b87e1ced0dee08ee9d451c4b56facb478024b7e7155918f2041f274a25b8;
adjacentWASM9761684924dfac7e772bb55fb164de8b39d4da7f0ec8e18f5a24f965efaf4af6.
Trace rne-family-candidate-hard-trace.json
SHAe4bbb8e7bf8958a54de8b6d76ad4a9e7b070a074c1787f9770394e64ddc64b76.
JS is unchanged because16 adds no binding. Never substitute15's adjacentWASM
just because the JS hash is equal. Build flags remain6.0.10/Release/O3/thin-LTO/
single-thread. The disposable source includes16; keep all older pairs immutable.

Commands from repository root, with outputs redirected to fresh owned paths:

~~~bash
NW_RNE_ROOT=/private/tmp/nw-marble-costchange.7SuZEZYO
NW_RNE_PY='/workspace/neural-workshop-enhanced/.venv/bin/python3'
NW_RNE_LIB='/workspace/neural-workshop-enhanced/.venv/lib/python3.13/site-packages/mujoco/libmujoco.3.12.0.dylib'
NW_RNE_SOURCE='/workspace/neural-workshop-enhanced'

"$NW_RNE_PY" nw-core/test/marble_rne_original.py \
  "$NW_RNE_ROOT/inertia-candidate-hard-trace.json" \
  --control "$NW_RNE_ROOT/inertia-candidate-hard-trace.json" \
  --reference-library "$NW_RNE_LIB" --source-root "$NW_RNE_SOURCE" --golden

NW_RNE_CONTROL_MODULE="$NW_RNE_ROOT/retained-inertia-candidate-dist/mujoco.js" \
node nw-core/test/marble_rne_compiled_probe_test.mjs \
  "$NW_RNE_ROOT/retained-rne-family-candidate-dist/mujoco.js" \
  "$NW_RNE_ROOT/original-rne-golden.jsonl"

"$NW_RNE_PY" nw-core/test/marble_rne_original.py \
  "$NW_RNE_ROOT/rne-family-candidate-hard-trace.json" \
  --control "$NW_RNE_ROOT/inertia-candidate-hard-trace.json" \
  --reference-library "$NW_RNE_LIB" --source-root "$NW_RNE_SOURCE"

"$NW_RNE_PY" nw-core/test/repro/generate_marble_rne_family_rejection_fixture.py \
  --capture-root "$NW_RNE_ROOT" --reference-library "$NW_RNE_LIB"

"$NW_RNE_PY" nw-core/test/repro/generate_marble_costchange_whole_solver_fixture.py \
  --capture-root "$NW_RNE_ROOT" --candidate-prefix rne-family-candidate
~~~

Generate the ordinary hard trace with16's retained pair and the same play flags
listed for15. Every7601 schedule/configuration/outcome entry is preserved, but
physics is NOT neutral:first E0/substep1 probe_rneBias qfrc_bias[5] changes0
to -6.681911775230489e-52. Live forward velocity and later physical state change
too; do not describe this as probe-only. The independent strict original replay
still stops at contactE463. The separate full-count run still has110690 numeric
breaches,105 contact mismatches463..1966,first numericE195/value10
delta4.996572333659799e-7 versus1e-7,timeout120.016667/home0/lost0.
These rejection metrics equal15, not every physical state byte. Full candidate
16 is REJECTED and no maintained physics/compiler artifact is replaced.

New current-input prior-producer checks all agree:inertia120,cost134,
Gauss125,generic114/1286iterations,QCQP2-18; all five frozen compiled proofs
also pass. Fresh16 exact-input original whole-solver qualification uses the
existing native driver protocol,16's trace/new rne-family-candidate-qualified-
{outputs,captures}.jsonl and stopE216. All20 final native outputs qualify
against the actual original wheel; all21 browser fields are compared. Three
solver_stats ulps remain atE17/1,E18/2,E216/2,with no other nonzero output
differences. This synchronized diagnostic is not an uninterrupted-game pass
and not original private intermediate identity.

Durable rejection fixture marble_rne_bias_family_rejected.json
SHAa2e105dc62aa3b0cb92bbeaec87b67bbb8cd2a0065cffa9680d5b4c4a7a7795f;
whole fixture marble_rne_family_whole_solver.json
SHAcb57459755764999334603d428b9f8f530679b5fbb826b44c8504d1637599dae.
The rejection generator reruns40 captured original returns and all1020 golden
original calls,checks compiled proofs and both independent ordinary failures.
Both new fixtures/golden and older default-cost/inertia whole receipts must
regenerate byte-exactly. Current focused verification:336 original-runtime
methods,296 dependency-light methods(32 explicit native skips); options1344,
renderer and all16 maintained boards pass. Shipped hashes remain unchanged.

Historical next action:qualify complete current mj_comVel/velocity/Jacobian inputs using the
actual original owned model/data,unique named probe_input/probe_comVel phases
and original symbol0x60110. Copy and verify its entire read set,including
tree/joint/DOF topology and qvel/cdof; compare complete outputs on16's current
operands before proposing a guarded complete producer-family candidate.
Previous isolated cross-motion patches remain rejected and are not authority
for a new live patch. Do not start other games or infer a compiler defect from
this floating-point diagnostic.

## Complete actual-original comVel on the current candidate — Oct2

Current plan3.16 supersedes3.15. Preserve all16 layers and pairs above;add
marble_comvel_family_candidate.patch as layer17 ONLY. Patch SHA
a155ad5c3de235f5ba481aadc76e8cd2579ac9ffdf35ac3b674328b558f266cc.
Forward check on a copy of16's exact retained-comvel-base-core-smooth.c and
reverse check on17 pass. Source root now includes17. Original pin/build flags
are unchanged;no compiler mutation,new binding or global contraction flag.
Native macros resolve to original helper calls;only guarded complete comVel
cross-motion/grouped triples change,and single-axis rounded product/add stays.

New original oracle uses actual public mj_comVel/image9e772461.../offset0x60110
on original-owned data. Complete topology/finite shapes/options and unique
NAMED probe_input/probe_comVel ownership validate BEFORE any original call;
sleep/missing fields/mutated inputs/invalid ranges reject. All cvel/cdof_dot
outputs compare. Original private intermediates and JSON zero signs are NOT
qualified. Full scalar reconstruction independently matches original bits.

Before:eight/20 boundaries,21 derivative values differ;all cvel agrees.
After:all20 current complete outputs agree. Original golden SHA
bf30ef4d1ab07e970ce7c075269edca4142b6493fb309ecc8abce4fd62d92fdb
contains20 captured+1000 synthetic calls across five free/ball/slide/hinge/
nested/fixed layouts. It uses16's captured inputs,new current checks use17's.
Compiled original control16 fails683 calls/2700 values,17 passes all1020.
No mirror or surrogate is used by the compiled public-call test.

New retained-comvel-family-candidate-dist pair JS
SHAc477b87e1ced0dee08ee9d451c4b56facb478024b7e7155918f2041f274a25b8;
adjacentWASMce9127d43ff80fba767a17225394073f15898481a3bc5112b714c3b2fc82b9a2.
Hard traceSHA8edf9e30dc86ce598810cabeb1c9c7b05a94da7c434483740e49262f146a6008.
Never substitute16's WASM because its JS hash is equal. All six current and
compiled prior producer proofs pass,including complete RNE and1020 retained15
acceleration-mode controls. Current complete integration is NOT yet qualified.

Commands from repository root;write outputs only to fresh owned evidence paths:

~~~bash
NW_COMVEL_ROOT=/private/tmp/nw-marble-costchange.7SuZEZYO
NW_COMVEL_PY='/workspace/neural-workshop-enhanced/.venv/bin/python3'
NW_COMVEL_LIB='/workspace/neural-workshop-enhanced/.venv/lib/python3.13/site-packages/mujoco/libmujoco.3.12.0.dylib'
NW_COMVEL_SOURCE='/workspace/neural-workshop-enhanced'

"$NW_COMVEL_PY" nw-core/test/marble_comvel_original.py \
  "$NW_COMVEL_ROOT/rne-family-candidate-hard-trace.json" \
  --control "$NW_COMVEL_ROOT/rne-family-candidate-hard-trace.json" \
  --reference-library "$NW_COMVEL_LIB" --source-root "$NW_COMVEL_SOURCE" --golden

node nw-core/test/marble_comvel_compiled_probe_test.mjs \
  "$NW_COMVEL_ROOT/retained-comvel-family-candidate-dist/mujoco.js" \
  "$NW_COMVEL_ROOT/original-comvel-golden.jsonl"

"$NW_COMVEL_PY" nw-core/test/marble_comvel_original.py \
  "$NW_COMVEL_ROOT/comvel-family-candidate-hard-trace.json" \
  --control "$NW_COMVEL_ROOT/rne-family-candidate-hard-trace.json" \
  --reference-library "$NW_COMVEL_LIB" --source-root "$NW_COMVEL_SOURCE"

"$NW_COMVEL_PY" nw-core/test/repro/generate_marble_comvel_family_rejection_fixture.py \
  --capture-root "$NW_COMVEL_ROOT" --reference-library "$NW_COMVEL_LIB"

"$NW_COMVEL_PY" nw-core/test/repro/generate_marble_costchange_whole_solver_fixture.py \
  --capture-root "$NW_COMVEL_ROOT" --candidate-prefix comvel-family-candidate
~~~

Generate hard capture with the same17 pair/play flags and
NW_MARBLE_PLAY_TRACE_PATH=<new path>(not TRACE_JSON). All7601 schedule/
configuration/results remain the same,but physics is NOT neutral:first
E1 engineStep1Inputs2 cdof_dot57 changes2.0752927017112463e-40 to
2.0752927017112467e-40. Independent strict original replay stops atcontactE463;
separate full-count run has111510 numeric breaches/103 contacts463..1966,
firstE195/value10 delta4.950429832728531e-7 versus1e-7,timeout120.016667/
home0/lost0. Contacts improve but numeric counts worsen versus16. Full17
REJECTED,not promoted. Both independent replay failures must be retained.

Rejection receipt SHA
519527343ea7511d9fb99399c23bda2334f1dbdd98f8f88d7b4b1a4af4023e71;
generator reruns all40 captured+1020 golden original calls and verifies complete
inputs/bits/models/compiled proofs/regressions/runtime/schedule/failure logs.
Fresh20 whole-solver qualification uses17's inputs,new comvel-family-candidate-
qualified-{outputs,captures}.jsonl and stopE216 with the existing original/native
driver protocol. All21 final fields compare:two statistic ulpsE17/1,E18/2,
zero other nonzero outputs. SDK27 final returns qualify against actual original;
private intermediates do not. Whole receipt SHA
e2cbcde367b77aeebfd551ff39822bb208e70c93f38ab1832257bf7e66b4c64a.
Synchronized output equality cannot waive ordinary rejection.

350 focused original methods/310 dependency-light methods(32 native skips)
pass;maintained options1344,renderer and all16 boards pass. New receipts/golden
and previous whole-prefix receipts regenerate byte-exactly. Shipped hashes stay.

NEXT qualify complete CURRENT original integration/position advancement.
First repair legacy positional checkAcc phase[4] selection into unique named
ownership and add strict complete read-set/finite/static/options/flags copy
validation for new evidence. Generic old-trace synchronization intentionally
skips absent fields,which is not complete equal-input proof. Assert exact
copies before calling the actual original enclosing routine;only then localize
free-body solve/LU/advance arithmetic. Require neutral recorder proof and full
independent hard parity for any candidate. No premature compiler or other-game
work;only3D N-back ever belongs in the port.
