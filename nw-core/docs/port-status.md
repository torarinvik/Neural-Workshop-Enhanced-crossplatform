# Neural Workshop port status snapshot

## Current deployed artifact state — 2026-10-07

- Production browser `build/nwcore.wasm` was rebuilt and promoted from
  Elisa-compiler Stage1 commit `23a0e16a854cddec3016746a0cb9480db0c4db22`.
  The Stage1 source fingerprint is
  `0e17e6c92e8a03735d46be9eec69953336395d909c4121fbe83414d060589f57`, and
  the selected product SHA-256 is
  `f1d15c7713b8583c0ec3d5b617599f7208786b374eb291dab9c86892ca0d8b56`. The
  promoted WASM is 1,685,170 bytes, SHA-256
  `4e4b6e90f58257883672da6309793db175f5a1f501c6042a1ef2dccaa6eec897`; its
  Stage1 object SHA-256 is
  `bd71fdd5aa54123c8e87d90794e100967353d9d7c581069077f868d726fe0233`.
- The complete latest-Stage1 artifact suite passed. It covers the common
  runtime API contract (including Count v6, N-Back v4, Monkey Ladder v5,
  Sokoban v2, and Tetris v3 field serialization, malformed-state rejection,
  restored frame/state checks, and deterministic continuation), browser and
  controller contracts, Marble options and
  physics, 320 board-clearance cases, 80 board/MJCF comparisons, 80 generated
  sessions, 80 held-input sessions, and 275 trajectory scenarios / 33,982
  frame states. Pixel acceptance remains diagnostic-only (`accepted:false`).
  The prior artifact/object, served response, and promotion receipt are
  preserved under
  `output/verification/count-v6-snapshot-promotion-20261007/`.
- The live response at `http://127.0.0.1:8000/build/nwcore.wasm` was fetched
  after promotion and is byte-identical to the promoted WASM; its saved copy
  is included with the receipt.
- The Stage0 `make test-full` post-fix rerun passes. The integrated
  `scripts/gate.sh --full` completed on 2026-10-07 and failed: 232 of 569
  Stage1 parity checks failed and three top-level gate steps failed. The
  detailed logs are under
  `build/verification/full-gate-20261007/`, diagnose differences, and rerun
  before claiming the full gate passes.
- The reviewed catalog now records 43 web stateful controllers, 24 stateful
  Python controllers, and 24 stateful SDL controllers. Sokoban is included in
  both native counts because its direct and task-hub routes have source-backed
  controller lifecycle smokes. Each native host has 21 catalog entries still
  marked not integrated.

## Historical deployed artifact state — 2026-10-05

- Production browser `build/nwcore.wasm` is now rebuilt and promoted from the
  verified newer Elisa-compiler Stage1 snapshot `541788548651d43dd466d0b5210955eb966eb18e`,
  which is eight commits ahead of live `main` `72a752820ab581d46bb17b3fb7158ba3879a16e`.
  The WASM SHA-256 is
  `292800bf992e1cc61bce540ad53c0fa1f89f18de0ae35641166f5bd6d92e73c0`
  (1,783,900 bytes; deterministic module name `nwcore.wasm`); its Stage1 object
  SHA-256 is `a8e8d596ad07afa2005b266c66e5770e31d2f102ba781e71a62b7908bd8bab01`.
  The HTTP 200 response from `http://127.0.0.1:8000/build/nwcore.wasm` was
  independently hashed and is byte-identical to that promoted artifact.
- Exact build inputs: Stage1 product SHA-256
  `5459f03e7efbaa228936223931bfca61a96e6b4ad0558aeb8bf495b861cab81a`
  (source-tree SHA `e48688ca4edb0874d1f063844ec2e54e8faead200879aa4bbe5dd06fa7d65d5c`;
  Stage1 provenance passes), Stage0 from Elisa-core
  `f84b9c1034f708f69d048bd6cafb813e88c8210f` (SHA-256
  `5f2c14780bb91b25feeef3e4dce685ba9199d264ab75f335b064741a138ea84e`), and
  Stage1 runtime object SHA-256
  `b51e6114f0576681e432e1162a3dbdcdac46c140d3b7e7256c0069be0bd11897`.
  Runtime differences were accepted only by the content-addressed provenance
  allowlist. The final-name candidate was kept separate until the complete
  artifact gate passed, then atomically promoted.
- Full latest-Stage1 artifact gate passes: configured task/browser contracts
  (including only the 3D N-back task), Marble renderer/controller/physics and
  lifecycle checks, 320 pit/cup/collar-to-wall boards, 80 board/MJCF cases, 80
  generated plays, 3 adaptive sessions, and 275 trajectory scenarios / 33,982
  frame states. Tolerances were not changed. The hole/collar minima are each
  at least 3.000 mm; the independent source sweep remains 8,000 boards and
  3,830,639 hole/wall pairs with a measured minimum of 3.000038215 mm.
- A strict original-Python Marble play matrix was rerun against the exact
  `292800bf…` production core: 80/80 traces pass; all scheduled inputs,
  per-frame numeric values, contacts, discrete states, and terminal results
  match, with zero numeric deltas and unchanged tolerances. Runtime files were
  verified. Evidence is in
  `output/verification/marble-source-play-current-5417885-20261005/`; replay
  log SHA-256 is
  `3d590945a1a6070d57fa39e9348b46d75a610ed90c900f88a5e14d5f25681059`.
  This matrix is separate from the fixed canonical 7,601-event schedule.
- The fixed canonical rung-16/run-seed-0/board-seed-827307999 schedule has also
  been replayed separately on `292800bf…`: all 7,601 events pass, all public
  numeric deltas are zero, contacts/discrete state/result are exact, and the
  outcome is timeout at 120,017 ms (`home=0`, `lost=0`). Current trace SHA-256
  is `72aae2daf18fb2b4d0a93278247d08773a7f6fb768e962c4ccc95550aebe0642`;
  provenance SHA-256 is
  `c94cd5892ad93be81bacdf95dbf304b0afface4326e614c354df896eda384003`.
  The similarly named old replay receipt is still historical evidence for
  `6b1751a5…`, not for this result.
- The latest source/native Python extension is also built with this Stage1
  product: Python 3.13.12 module SHA-256
  `c4575aec550dff1fc21308a57ce7f284e90322c78b25d7a2972f4c54668ca5f8`
  (2,925,888 bytes). Its 80-case MJCF oracle applies the shared Float32 board
  ABI conversion, so all models match original source exactly; this corrects
  the test's transport-boundary expectation, not physics or tolerance. Native
  mesh parity covers 560 meshes over 80 boards, and strict synchronized
  800x600/DPR1 source/native scene state passes. The extension links the port's
  shim object (`d35099210e8afeaf75cd1e0e08acdb3674cbb2a7a2c8115fd55141c5f91e9c77`),
  not the standalone compiler runtime archive.
- The original 42 synchronized source/browser pairs were captured against the
  prior 2691 Stage1 artifact
  `4bd7b4217c2fd57b88ee19db62d9ccd6f1f4717414f5500692ef5fefcf9b79c5`; those
  images are historical, not exact-byte captures of the newly promoted
  `292800bf…` build. One exact-current synchronized pair has now been captured
  for rung 15/run seed 17/board seed `889418965`, whose closest pit-to-wall
  clearance is `3.000605385750532 mm`. Source and browser naturally reach a
  one-home/one-lost state at 2,933 ms; board geometry, camera and complete scene
  state pass strict synchronization with zero failures. The 800x600/DPR1 light
  stage is 99.2489% exact (MAE `0.226525`, RMSE `2.927396`), diagnostic only.
  The combined inventory is now 43 pairs with zero synchronization failures;
  pixel policy remains diagnostic-only (`accepted:false`). Exact pair hashes
  and paths are in `marble-physics-manifest.json` under
  `latestStage1HoleWallVisualPair`. The 43-pair zero-failure audit receipt is
  `output/verification/marble-visual-inventory-audit-20261005-stage1-current-hole-wall/receipt.json`
  (SHA-256 `6540c96f87baa14fcbebf268bd6364dfba33b0dbd75fad9036ce5d0e480292a5`).
- The separately versioned port-owned toolchain cache
  `nw-core/toolchain/` still needs an official Stage1/runtime stamp refresh.
  Its Stage0 binary is already the exact `f84b9c1` product above. The selected
  Stage1 product/runtime were used explicitly for this fully gated WASM build;
  do not label the old port-owned Stage1 binary or the existing PROVENANCE
  stamp as 5417885 outputs. Compiler-driver reject triage and shipping checks
  remain open.
- MuJoCo 3.12.0 JS/WASM: `e08297d7…` / `e5a36e90…`; reproducible through
  `scripts/build_marble_mujoco_wasm.sh`, pinned patch SHA
  `e2c0eaf4566f4ca3a8510bfa1178cc29ee25c9cff2d9b9eb85d9be810ff12362`.
- Historical 2691 Stage1 source-play evidence: its then-promoted exact bytes
  `4bd7b421…` passed 320
  3 mm hole/wall-clearance boards, 80 board/MJCF comparisons, 80 generated
  sessions, 3 adaptive sessions, and 275 trajectory scenarios / 33,982 frame
  states within existing tolerances. The strict 80-case generated
  original-source play replay passes against these exact promoted bytes,
  matching every per-frame value, contact identity, and terminal result with no
  tolerance changes. Evidence is at
  `output/verification/marble-source-play-stage1-main2691-20261005/`; the
  source comparison log SHA-256 is
  `17407bf9127c82cad00d3029866365de732be97b976f8dda9c1a95a6425d7dcc`.
  The legacy 7,601-event replay receipt described in a dated note was actually
  run on predecessor core `6b1751a5…`, despite its historical filename and
  manifest alias saying “current”; it is not evidence for `4bd7…` or the
  present `292800bf…` bytes. Preserve it as predecessor evidence only. The
  exact-current 80-case comparison and the separate canonical schedule replay
  are both now independently verified on `292800bf…`. October 4 receipts
  remain historical.
- A fresh source-vs-browser-adapter trajectory run now passes 275 scenarios /
  33,982 frame states, including exact 60 Hz/50 ms boundaries, 16 generated-
  board variable-partition cases, 16 arbitrary-initial-state cases, and 80
  generated-hole approaches (all 16 rungs across five board seeds; rung 1
  home cup, rungs 2-16 pits).
  The initial-state matrix perturbs pose, normalized orientation, and
  linear/angular velocity; the hole paths assert intended hole identity and
  terminal outcome. No tolerances were relaxed.
  Peak angular-velocity difference is `8.414e-10 rad/s` against the existing
  `1e-7` limit. This detailed trajectory receipt was rerun on the then-promoted
  predecessor Stage1 WASM `4bd7b421…` without rebuilding. The newer `292800bf…`
  artifact independently passed the same 275-scenario / 33,982-state suite in
  its complete promotion gate. Historical trajectory-test SHA-256:
  `d485e3fbd14a399018e80c97265de0b3a60062530249312b87812980cd70d574`.
  Detailed arbitrary-state receipt:
  `output/verification/marble-initial-state-parity-20261004/receipt.json`.
- The 2691 Stage1 packaging used a uniquely named scratch directory but links
  the candidate with the final artifact basename. This avoids leaking a random
  temporary name into the WASM `name` section; the exact resulting bytes were
  fully gated before promotion. The prior browser artifact is recoverable at
  `/private/tmp/nw-upstream-latest-20261005.wN6wg8/nwcore-before-stage1-promotion-6b1751a5.wasm`.
- Hole/wall geometry on the newly promoted `5417885` bytes: every pit and home-cup
  collar is at least 3.000 mm clear of all actual wall rectangles across 320
  ABI boards (up to 62 walls, 39 holes; 220 collars trimmed). The original
  Python source suite passes 47 tests and its UI/render suite passes 35 tests.
  An independent 8,000-board source sweep (rungs 1–16 × seeds 0–499) checked
  3,830,639 hole/wall pairs and measured a 3.000038215 mm minimum. Browser and
  native mesh geometry continues to match the original Builder for 560 meshes
  across 80 boards. The promoted WASM is
  `292800bf992e1cc61bce540ad53c0fa1f89f18de0ae35641166f5bd6d92e73c0`. The
  independent source sweep and mesh parity remain source-level checks of the
  same 3.0 mm rule.
- The six earlier synchronized 3.0 mm source/browser pairs were captured
  against predecessor compiler
  artifact `6b1751a591d2782629e2ad2c988bf89841635740650a630ba3c2dfd2839508a9`;
  their synchronization results remain useful, but those screenshots are not
  exact-byte evidence for the intermediate `4bd7b421…` artifact. The original
  42-pair inventory and its 2026-10-05 receipt remain historical for the newly
  promoted `292800bf…` bytes. The added 43rd pair is exact-current evidence for
  its closest-clearance partial-loss case; broader phase/viewport/theme
  coverage remains outstanding. No human-reviewed pixel policy exists
  (`accepted:false`).
- One live 2691-artifact capture verified the ordinary Games → Attention
  → Marble Maze → Enter → Space route and the served production bytes (HTTP 200,
  exact SHA match for the then-current `4bd7…` build). At 1600x900 in a running tray, the home opening is visibly
  separated from neighboring wall strips, though the gap is narrow at this
  scale. PNG: `output/playwright/marble-maze-live-current-stage1-main2691-20261005.png`
  (SHA-256
  `88cc549a7f836d931f8fcfa8e15a6795f0f3c0a063256ca6c7f5693adc686e91`). This
  screenshot is not an exact-byte capture of current `292800bf…`, nor a
  synchronized source pair or a pixel-acceptance result.
- The 26 older retained source/browser visual pairs were captured against the
  predecessor WASM (`0e7aef1d…cdded3d`) before the 3.0 mm clearance update.
  They remain useful historical renderer/lifecycle diagnostics but are not
  evidence for the repaired geometry. Six later synchronized pairs cover the
  minimum-clearance rung-15 board in a natural two-marble partial-loss state at
  DPR2/light, a rung-16 rolling/DPR1/dark state at 800x600, matching light/dark
  rolling states at 1280x720, a light-theme no-board READY state, and a natural
  rung-1 win at 67.1 seconds. Those pairs were captured against the 3.0 mm
  geometry on predecessor compiler artifact `6b1751a5…`; they are not exact-
  byte visual evidence for either later artifact. Of the original inventory,
  the newest synchronized evidence is exact for `4bd7…`; the separate 43rd
  pair now covers the closest-clearance partial-loss case on `2928…`. Continue
  refreshing source/browser phases and lifecycle pairs against the latter
  before claiming broad exact-current visual coverage.
- Only 3D N-back remains in the task catalog and WASM root; legacy 2D N-back
  scenes and exports are excluded. The 3D-only browser/controller checks pass.
- Historical Stage1 inferred-protocol-bound fix and its positive/negative
  tests remain recorded in the 2691 checkpoint; the associated 2 bare / 0
  with-stdlib driver disagreement result is not attributed to Stage1 `5417885`.
  On the exact current Stage0 `f84b9c1` / Stage1 `5417885` pair, the focused
  `test/parity/field_access_type_param_scope_smoke.sh` now passes: both stages
  reject primitive-reference field access and invalid generic field accesses,
  while accepting legitimate ref/value parameter shadowing in nested scopes.
  The original `literal_init_out_of_range.pos.elisa` driver regression was
  separately verified to exit 1 on both compilers. The complete current
  driver-acceptance matrix is still open; these targeted checks do not claim
  all Stage0/Stage1 diagnostic differences are resolved.
- The WASM export now resolves runtime include placeholders from the selected
  `ELISA_STAGE1_ROOT`; the previous hard-coded `Elisa-compiler-latest` path
  mixed the latest checker with an older runtime that lacked required
  `Unsafe.PointerCast` grants. Both Stage0 and Stage1 WASM builders exercise
  the resolver regression and compile against the same selected runtime.

The detailed source/browser loss, win, and DONE capture narratives immediately
below, including their numeric `0e7aef1d…cdded3d` fetch receipts, are
historical captures of the predecessor geometry. Within those dated capture
notes, “current” means current on the capture date, not the present promoted
WASM. Separate exact-current close-gap, rolling-tilt, READY, and natural-win
pairs are recorded after the historical notes; those older comparisons do
not supersede the exact-current evidence. Broader visual acceptance remains
open.

The historical physical-loss pair below exercised the predecessor WASM
through the real browser menu and fixed-frame test input path. At rung 2 / run
seed 17 / board seed `889418965`, 340 60 Hz frames and seven ordinary level-key inputs
lead to the same physical loss at 5667 ms in the original Python source and
browser. No board, pose, or outcome is injected. The browser received the
trace's westward holds as keyboard A, and its final marble values and state
match the source. Both captures use the same 800x600 logical canvas at DPR2
(1600x1200 framebuffer), light theme, and 45-second tray budget. The browser
returned HTTP 200 for the then-installed 1,760,837-byte production WASM, whose
fetched SHA-256 at capture time was
`0e7aef1d77dd68dcb17c08d4fc3541295425734bd42354da16a941592cdded3d`.
Strict source/board/scene/camera synchronization passed for this pair; the stage is
99.9462% exact with MAE 0.01457, while full-frame text/chrome differences
remain visible. These pixel values are diagnostic-only, not acceptance
thresholds. Captures and metadata are under
`output/playwright/mm-loss-current-20261005-`; the trace is retained at
`output/verification/marble-source-play-deterministic-20261004/traces/2-17.json`.

That terminal pair exposed a metadata-validator assumption, not a physics or
compiler defect: after physical settlement, the browser deliberately syncs
the controller clock using rounded milliseconds, whereas active play and an
unsettled timeout use the floored elapsed clock. The validator and its tests
now distinguish those lifecycle cases; the browser runtime and WASM were not
changed. The focused metadata test and eight-case visual-audit test pass.

A historical physical-win companion pair uses the same predecessor WASM and
retained source-play trace `1-17.json` (rung 1, run seed 17, board seed
`889418965`). Replaying 628 ordinary fixed 60 Hz frames and 12 level inputs
through the live browser key handlers reaches the same physical win at
10,467 ms as the Python source; no board, marble pose, or verdict is injected.
Both final marble states and renderer/camera scene state synchronize, with
maximum camera-matrix delta `5.6434717343734064e-8`. The stage (1504x737) is
99.975461% exact, MAE `0.0055092`, RMSE `0.4475333`; full-frame diagnostics are
98.319271% exact, MAE `1.6936754`, RMSE `17.2531895`. The win image pair is
under `output/playwright/mm-win-current-20261005-*`. These remain diagnostic
metrics, not approved pixel thresholds; multi-marble partial-loss and broader
viewport/theme/DPR coverage remain open.

The same physical-win trace also passed a source/browser DONE-state pair on
that predecessor WASM. Source and browser both report phase `done`, outcome
`won`, and elapsed 10,467 ms after the regular one-trial feedback/completion
transition. The
browser phase was reached through its normal feedback clock/update, not by
setting controller state. Camera delta is `5.6434717343734064e-8`; stage
metrics are unchanged from the win pair, and whole-frame metrics improve to
98.76% exact pixels, MAE `1.267949`, RMSE `15.119685`. These remain diagnostics
only. Multi-marble partial-loss and broader DPR/theme/viewport coverage are
still open.

The immediately preceding production core/object are preserved at
`/private/tmp/nwcore-before-deterministic-rebuild.XUToqx/`; the earlier
random-name dfaeb build is preserved at
`/private/tmp/nwcore-before-latest-default-build.IW4emThs/`, and the previous
b903 recovery copy remains at
`/private/tmp/nwcore-before-b903-promotion.XLePsaVd/`. Neither finite
replay proves arbitrary-state or arbitrary-timestep identity. A separate
fresh headless live-browser check of
the dfaeb artifact entered the real menu route and inspected rung 16, board
seed `211162261`: 23 holes, 53 walls, 1.5144 mm minimum measured clearance,
zero violations, MuJoCo/WebGL2, and no console errors or warnings. Screenshot:
`output/playwright/mm-r16-latest-dfaeb-wall-clearance.png` (SHA-256
`f89423d981e9259d3068e5077e4b66df37e022bb40ef4e13d922a09dd2e806df`). That
particular seed-211162261 image is a live geometry check, not itself a
synchronized pair. A second source/browser pair synchronizes original Python
and the immediately preceding dfaeb build at rung16/run seed17/board seed
889418965, DPR2, light theme, and zero elapsed/tilt. Its WASM differs from
the installed deterministic-name artifact only in the `name` custom section;
all other section payloads and the compiled object are byte-identical. It is
code-equivalent visual evidence, not a capture of the exact current file hash.
Source/browser scene and camera verification passes; the stage is 99.7629%
exact with MAE0.07318, but those remain diagnostic pixel measurements without
reviewed thresholds. The audit
previously reported 14 missing pairs because it was given only
`nw-core/output/playwright`; the historical files are in workspace-root
`output/playwright`. It now audits both roots, verifies all 18 listed pairs
with zero synchronization failures, and still returns `accepted: false`; pixel
policy remains open. The new pair's
source/browser PNGs, metadata, same-call debug snapshot, and comparator receipt
are under `output/playwright/marble-dfaeb-matched-20261004/`. Earlier
“private candidate”/“not promoted” checkpoints are historical. The wider port
plan remains active.

The home-cup's physical opening clears all walls by at least 1.5 mm, but its
larger decorative collar used to extend beneath nearby wall strips. Source,
native Python, and browser WebGL builders now cap the collar's outer radius to
the nearest wall rectangle minus that same clearance, without changing the
opening or physics. The promoted-WASM sweep passes 320 layouts (minimum
1.500 mm; 200 collars trimmed); source/native geometry parity passes 80 boards
and 560 meshes (50 collars trimmed in the freshly rebuilt native-module run).
The real-menu browser smoke starts the MuJoCo/WebGL2 task with no console
errors. The ring fix is a rendering
correction, not a change to generated board ABI or game behavior.

A new post-collar-fix source/browser pair at rung 16, run seed 17 / board seed
889418965, light theme, DPR2, and zero elapsed time is synchronized for board,
camera, and scene state. The stage comparator reports 99.7629% exact pixels,
MAE 0.07318, and RMSE 1.68295; those are diagnostic measurements, not
acceptance thresholds. The combined visual evidence audit now reports 18
pairs, zero sync/state failures, and `accepted: false`. Artifacts are under
`output/playwright/marble-collar-current-pair-20261004/`. The automated
320-layout rectangle-distance test is the direct overlap guard; the visual
pair is corroborating source/browser evidence.

The normal keyboard route was rechecked against the exact deterministic-name
production artifact on 2026-10-04: Games → Attention → Marble Maze → Space
(enter) → Space (start). The browser fetched `/build/nwcore.wasm` with HTTP
200 and content length 1,760,837 bytes, matching the local artifact whose
SHA-256 is `0e7aef1d77dd68dcb17c08d4fc3541295425734bd42354da16a941592cdded3d`.
The live status identified MuJoCo/WebGL2; the browser console had no errors or
warnings. The current-build ordinary-run screenshot is
`output/playwright/marble-current-artifact-20261004/marble-maze-live-run.png`
(SHA-256 `41ba96b5d7644f4e66ff2c5619d36e494c70c1134c14b9c5c9218eb6b47dab29`).
The exact 320-layout board-ABI regression was rerun against the same local
artifact and passed: up to 68 walls per layout, minimum hole and collar
clearance 1.500 mm, 200 collars trimmed. The screenshot is an ordinary live
smoke, not a synchronized source/browser pixel pair or a pixel-threshold
approval.

The current deterministic-name WASM now also has a fresh synchronized
source/browser render pair, rather than relying on the visually code-equivalent
preceding module. Both images were independently captured at rung 16, run seed
17 / board seed 889418965, light theme, zero tilt/time, settled materials, DPR
2, and a 1600x1200 framebuffer. The original reference was captured from the
current dirty source checkout (HEAD `dcd59a50351d742583e2501235ab1e5f24d63f41`);
its Marble UI file hash is `c07bdbae93dfee1d8acb362cb95ce833c9eca723e8afc633f7c7264ff14b097c`.
The browser loaded exact local production WASM SHA-256
`0e7aef1d77dd68dcb17c08d4fc3541295425734bd42354da16a941592cdded3d` and the
current MuJoCo/WebGL2 runtime. Source/browser board, camera, and scene state
synchronization passes with camera maximum absolute delta
`5.6434717343734064e-8`. The stage is 99.7629% exact, MAE 0.07318, RMSE
1.68295; these are still diagnostic metrics, not accepted pixel limits.
Artifacts, exact JS/WASM fingerprints, same-call browser debug snapshot, and
the consolidated audit receipt are under
`output/playwright/marble-current-pair-20261004/`. The two-root audit now
reports 19 listed pairs, zero synchronization failures, and `accepted: false`.
The first navigation attempt did encounter one transient local HTTP reset for
the MuJoCo JS module; an immediate reload loaded all assets successfully, and
the captured run had no console errors or warnings. Broader theme/tilt/DPR1
coverage, reviewed pixel policy, and shipping-build qualification remain open.

Fresh matched Marble capture (2026-10-03): original pyglet/OpenGL and installed
Stage1/WebGL2 were captured at rung 16, run seed 17 / board seed 889418965,
Float32-ABI board geometry, zero tilt and elapsed time, settled materials,
light theme, DPR 2, and 1600x1200 framebuffer. The state/camera/board sync
gate passes; camera max absolute delta is `5.6434717343734064e-8`. The stage
region is 99.7629% exact at a zero channel threshold, with mean absolute error
0.0732 and RMSE 1.6829. This remains diagnostic-only: those measurements do
not establish pixel acceptance, and the reviewed threshold plus the other 14
historical evidence pairs remain open. Source/browser PNGs and both state
manifests are `output/playwright/mm-{source,browser}-b903-r16-running.*`; the
browser's same-capture debug snapshot is `mm-browser-b903-r16-running-debug.json`.

## Current product scope — 3D N-back only

The current WASM root no longer builds or exports the legacy non-3D N-back
scenes, generic session/batch renderers, or old configurable N-back menu. The
3D N-back route remains the only N-back task. This was checked by the complete
artifact gate on the promoted `dfaeb45c` build, not only in a private
candidate. See the latest dated checkpoint in `IMPLEMENTATION_PLAN.md` for
compiler and test evidence.

Historical: stripped shipping candidate — 2026-10-03: diagnostic instrumentation removed
in an isolated checkout; durable input is
`test/repro/marble_shipping_candidate_unqualified.patch` (SHA256
`e2c0eaf4566f4ca3a8510bfa1178cc29ee25c9cff2d9b9eb85d9be810ff12362`).
The Release/no-thread Emscripten 6.0.10 build succeeded. Its fresh WASM
`6428e661ea292ad2004e8edb8d3337b5450e647fec6a1ffe9d132afcc5379b6f`
passes 162 crafted scenarios/17,263 states and three lifecycle cases/seven
timeout trays. All 80 generated-board cases and all 80 strict original-source
replays pass, with runtime hashes verified before and after replay.
Fresh browser loads this artifact with WebGL2 at DPR1; fresh synchronized
visual comparison and reviewed visual acceptance are not yet established.
Known-diagnostic guard passes, but does not prove minimality or acceptance.
No maintained runtime promotion. See the integration checkpoint for logs.

Checked-in isolated build qualification — 2026-10-03: the diagnostic wrapper
completed end to end. Its fresh WASM
`c3bdf5432da452d44c51a06ee68b7cd1ca8a509d8eb5b39b9f2ec9ff5eb89227`
passes all80 strict original source replays, with runtime-file hashes verified
before and after replay, plus162 crafted scenarios/17,263 states and3 lifecycle
cases/7 timeout trays. Receipts are in
`/private/tmp/nw-marble-wrapper-qualified-oct3`. These new bytes have not yet
received fresh browser visual qualification. The earlier candidate has13
diagnostic-only capture pairs, including physical win/loss/done and one DPR1
rolling pair; those visual receipts do not automatically qualify this build.
Minimal shipping recipe and reviewed pixel policy remain open; no promotion.

Clean reproduction — 2026-10-03: fresh private WASM
`c2df1704b7d2f676a42d9b3779ae054378526cbaa78fd1d855131994d6871f33`
independently passes all80 strict source replays, 162 crafted scenarios/
17,263 states, and three lifecycle cases/seven timeout trays. Fresh browser
capture renders rung16 with MuJoCo/WebGL2. Visual comparison is not accepted
yet; initial pair correctly rejected a 1x native versus 2x browser framebuffer
mismatch. Matching Retina captures subsequently pass synchronized scene/
camera qualification: stage99.844% exact pixels, full frame98.964%.
Pixel verdict remains diagnostic-only; broader visual/UI coverage and
reviewed acceptance are outstanding. Temporary browser/server were closed.
Maintained binaries remain unpromoted. See the integration
checkpoint for exact artifacts and further capture qualification.

Current combination — 2026-10-03: private layer29 uses the verified original
pi/4 unreduced trig branch; its WASM SHA-256 is
`beb0f59890d8bc819bf2f58b21b8e1bc4a7e83bdb78d19653c2d7a88595c2d76`.
The maintained JS MuJoCo adapter now uses Python-compatible compensated
two-coordinate norm arithmetic, fixing the post-integration speed-cap split.
The formerly failing rung16/seed1 full source replay passes with zero reported
differences. Fresh 162-scenario/17,263-frame original comparison also passes.
Complete strict source replay now PASSES all80 long-play cases, with full
per-frame/contact/result checks and adapter provenance. Core/MuJoCo production
binaries remain unchanged, but do not describe all production code as
unchanged: the adapter and norm helper were edited. Visual/UI acceptance and
remaining branch/helper qualification are still required before physics
promotion. The following layer28 handoff is historical.

Latest diagnostic handoff — 2026-10-03 (plan 3.17): private cumulative physics
layer 28, WASM SHA-256
`0f08066510b5851e0c7dea261572f71259dbb0d302f93fe9b1637b85dec0b6b5`,
passes strict uninterrupted original replay of the hard rung-16 timeout and
three win/loss trajectories. It also passes the 162-scenario/17,263-frame
native-versus-WASM trajectory suite and the 80-case generated outcome,
controller-history, and cleanup matrix. These are private candidate results,
not maintained-runtime results or a release certification. Production remains
unchanged. Complete strict original replay of all 80 long generated traces
completed with 79/80 passes and one numerical failure: rung 16/run seed 1,
first tolerance crossing event 3798/marble 1/qx. This rejects layer 28 for
promotion; keep tolerances unchanged and localize that retained trace.
Original visual/UI
gates and remaining branch/helper qualifications are still required before
promotion or other game work. Only 3D N-back is in eventual port scope.
See `test/repro/marble_integrator_readset_checkpoint.md` for the cumulative
patch chain, retained receipts, artifact identities, and current process
handoff. Earlier dated "current" sections below are historical and superseded.

Snapshot date: 2026-09-30 (Europe/Oslo). This is an evidence inventory, not a
release certification. Consult `IMPLEMENTATION_PLAN.md` for acceptance
criteria and the dated evidence ledger for test scope. Historical candidate
claims in this snapshot are superseded by the current optimized checkpoint and
the Current Out of Sight slice recorded later in this document.

**Current handoff (2026-10-02, plan3.16):** Marble remains first and strict
uninterrupted original parity remains failing. Isolated Stage0
79154665 passes its semantic and complete port artifact gate; a newer clean
local a98ef922 is separately qualified in the final compiler boundary below. Stage1 remote
is e287 and its integration freshness passes. Shipped Stage1 core120a247c...
and MuJoCo c91c0ae6.../56a96b23... are unchanged. All125 selected original
constraint-update calls match. Private Gauss and two-tangent QCQP corrections
pass actual compiled captured/synthetic tests, but neither qualifies the full
game. Latest QCQP2 candidate has114869 numeric exceedances/162 contacts and
is not promoted. The new cost observer is exactly neutral over7601 events
and prior diagnostics;22/134 quadratic returns differ from the actual original,
while all dots match. A private correction passes134 captured+1000 compiled
original cases but leaves physics unchanged and remains rejected with the
same114869 exceedances/162 contacts. Actual original private cost/restoration
is not captured. Fresh whole-solver checks agree on force/acceleration/state
outputs at20 matched-input checkpoints,with only two statistic ulps remaining.
The latest private shared-inertia correction clears42/120 captured original
product mismatches and all1120 compiled original tests, but its complete hard
game still fails:110690 over-limit values,105 contact sets,E195/value10 delta
4.996572333659799e-7. Current-input prior solver producers remain exact;
20 fresh exact-input solver boundaries clear all non-statistic outputs,with
three statistic ulps retained. No production promotion or compiler defect.
The coherent complete-RNE bias correction now matches20 captured+1000
synthetic actual original return vectors;1020 acceleration-mode outputs remain
identical to retained15. Current20 full bias outputs agree,versus10 differing
boundaries/21 values before. Live physics changes,but full hard replay retains
the same110690/105/E195 failure metrics. Next qualify actual current comVel/
velocity/Jacobian input production. See the final complete-RNE checkpoint for
recovery and
scope; older current-artifact labels below are historical.
The complete original comVel correction is now independently qualified:
20 current outputs match,versus8 derivative boundaries/21 values on16;
20 captured+1000 synthetic compiled calls pass across five layouts. All six
previous current/compiled producers remain exact. Complete17 replay FAILS:
111510 numeric breaches/103 contacts,E195/value10 delta4.950429832728531e-7.
Contacts decrease but numeric counts worsen;no promotion. Fresh matched solver
matrix has20 qualified boundaries,zero non-statistic differences and two
statistic ulps. Next qualify complete current integration inputs/actual output,
first guarding unique named checkAcc ownership and complete read-set copies.
See the final complete-comVel checkpoint;production/compiler hashes unchanged.

**Historical newest-Stage1 artifact checkpoint (2026-09-30):** the selected local
Elisa compiler is `Elisa-compiler-latest` at
`54360bf68398b4da8d63b82a3ad2979667798aa2`. Its source fingerprint is
`8218c14f9ee52b740a3dfa8ae91b8e501da3a73be2df730e916bb911373e3e90`; the fresh
Stage1 product SHA-256 is
`9f9085468802edae566cd4992a0e7e9b9c0bbf79755707d3894ab9bfd736954e`, and the
freshness guard passes. The selected checkout contains the reviewed latest
compiler fixes used by this port; its identity is guarded before and after
complete builds and parity sweeps.
The targeted Stage1 region-tie compiler regression passes at O0/O2 for both
Stage0 and Stage1, including the invalid typed field-reference return and its
no-LLVM-output assertion.

`nw-core/scripts/build_latest_stage1_wasm.sh` transactionally rebuilt and
promoted the production artifact only after compiler identity stayed stable
through the complete gate. `build/nwcore.wasm` SHA-256 is
`f37bfb3752b6ecc9e4ab087044a95b32576e1ebda12c553c5bf5ad1ab8685ea8`.
The current fast/medium gate finished `GATE GREEN`, and the stable Stage1
differential rerun passed every registered task,
controller, scene, trial-phase, text-metrics, screen/HUD, and batch suite after
the three source-side `sview(cstr, ...)` corrections in `stats_sweep.elisa`,
`config_sweep.elisa`, and `decimal_sweep.elisa`. The gate passed every
registered game/browser contract, the 3D-only N-Back
checks, all Marble browser/MuJoCo/renderer/board/session checks, and the
162-scenario/17,263-state trajectory oracle. The independent hard 7,601-event
Marble trace remains an open numerical-physics investigation; it is not being
misclassified as a compiler failure or waived by this artifact result.

**Stage1 generic-reference field-access parity (2026-09-21):** fixed in the
latest Elisa compiler source and rebuilt into the current port WASM. An
unbounded `T&` parameter is now recognized by Stage1's generic field checker;
the invalid member-access negative and lexical-shadow positive cases pass the
focused Stage0/Stage1 parity smoke. The fresh driver acceptance run has zero
Stage0-accept/Stage1-reject gaps in bare mode and zero disagreements across
537 standard-library fixtures. `build_latest_stage1_wasm.sh` rebuilt and
passed the full artifact gate from Stage1 product
`0783bbb2f581a9afe0450b3310acd16c3e426f1bb63e3be6a7941cd39d700724`; resulting
WASM SHA-256 is
`c6cf8d7f3e6f18c4723c0fb86cb096e6bcfddcdc9ca70a7acfc5acb25d0ed26e`.
Compiler checkout/product provenance stayed unchanged through the build.
The compiler's separate full upstream gate remains open.

The freshly rebuilt artifact was also exercised in a real headed browser:
Games → Attention → Marble Maze → Enter reached READY with official MuJoCo;
Space began a live tray using WebGL2; held ArrowRight reached the 8° tilt stop;
Escape returned to the selected-task menu. Console errors and warnings were
zero throughout. This is a live start/input/exit slice only, not an outcome or
visual-identity claim; detailed evidence and the exact artifact hash are in
the dated plan entry below.

**Fresh physical-win replay (2026-09-22):** the current Stage1-built WASM was
replayed through the real Games → Attention → Marble Maze route with the
source-compatible held A/S/D/W route. Official MuJoCo/WebGL2 reached the home
cup at 10.5333 seconds (`home=1`, `lost=0`, physical win), committed the
result through feedback to DONE, and Escape released the one model/data pair
(`1 created / 1 deleted`, zero live resources). Console errors and warnings
were zero. The running and summary screenshot hashes and exact route are
recorded in `lifecycleEvidence.headedBrowserSuccessFreshStage1` in the physics
manifest and in the dated plan entry.

**Native Marble renderer theme/viewport pairs (2026-09-21):** the synchronized
original-Python versus native-Python renderer harness now parameterizes theme,
logical width/height, DPR, rung, and held-frame count. Strict state
synchronization passes for the rung-16, three-marble, 30-frame east-held trace
across dark 912×684/DPR 2, light 800×600/DPR 2, light 912×684/DPR 1, and dark
800×600/DPR 1. The exact baseline and all measured stage metrics are in the
physics manifest; cross-renderer pixel figures remain diagnostic only.
Additional rung/state combinations, multi-step/responsive resizing, and
reviewed acceptance thresholds remain open. A live resize after the rung-16
input replay now has a strict source/native pair and matching recorded
initial/final window sizes in `IMPLEMENTATION_PLAN.md` and the physics
manifest.

**Native full-window READY captures (2026-09-21):** corrected the shell's
fixed charcoal clear so it follows the source light/dark setting, made its
diagnostic HUD opt-in, and aligned its display-list font fallback order with
the original fixed-width-first family list. Fresh original/native integrated
app captures at 800×600 logical / 1600×1200 framebuffer are 99.9508% exact in
light and 99.9532% exact in dark; remaining >10-channel differences are
limited to the title region, with blank stage and footer exact. These are
diagnostic-only READY-state captures; active gameplay/UI states, more viewport
scales, and approved pixel thresholds remain open. See the dated plan entry
and hash-bound images under `output/playwright/`.

A longer, independent rung-2 motion pair now adds 60 held-east frames at
800×600, dark theme, DPR 1. The source/native state comparator and per-frame
MuJoCo-versus-original-Simulation comparison pass; stage exactness is 99.8425%
(MAE 0.00575, RMSE 0.23604). Metrics are diagnostic only. This is one more
rolling pose, not collision/terminal proof or an approved pixel threshold.

**Marble Maze simultaneous-axis browser replay (2026-09-20):** the original
capture helper now records repeated held directions, and a real browser run
held ArrowRight+ArrowUp together for 30 fixed 60-Hz updates at rung 16. The
source and browser match at 500 ms, both tilt limits, board/grain seeds, camera,
materials, and all three marble states (one marble falling while two continue
rolling). The synchronized DPR-2 pair has a 99.8762% exact 1714×842 stage and
passes live metadata plus scene-state validation. Pixel scores remain
diagnostic-only; opposing-key overlap and broader theme/viewport coverage are
still open. See the dated evidence in `IMPLEMENTATION_PLAN.md`.

**Marble Maze opposing-key browser replay (2026-09-20):** ArrowRight+ArrowLeft
and ArrowUp+ArrowDown were each held concurrently for 30 fixed frames after
the real menu launch; both implementations kept the tray level and all three
marbles stationary through 500 ms. Both synchronized source/browser metadata
and scene states match, and each 1714×842 stage is 99.8458% exact. The
Python/native versus browser/WASM trajectory oracle explicitly asserts zero
roll and pitch for both held sets. The oracle now also covers staggered release
and rollover: E+W cancel, releasing W leaves E active, releasing E clears the
input remainder without moving the static tilt, and subsequently holding W
reverses it. Native/source and browser/WASM traces match at all 73 states in
that scenario; total oracle coverage is 138 scenarios / 14,959 frame states.
The real-browser keydown/keyup route is separately verified below; rendered
image scores remain diagnostic, not accepted thresholds.

**Marble Maze real-browser staggered key rollover (2026-09-21):** after the
normal Games → Attention → Marble Maze → Space route, a headed Chromium
session sent ArrowRight+ArrowLeft `keydown`, released ArrowLeft while keeping
ArrowRight down, then released ArrowRight and finally held ArrowLeft. The
observed controller masks and tilt were respectively `10/(0,0)`, `2/(+0.12,0)`,
`0/(+0.12,0)`, and `8/(-0.12,0)`, at exact 60-Hz frame checkpoints. The game
remained running and the tray reversed direction as expected. This complements
the 138-scenario / 14,959-state source/native-versus-browser/WASM trajectory
oracle. It is an input-path replay, not a rendered image pair; visual acceptance
limits remain open. The still-open visual threshold and paired-image gaps are
tracked in `IMPLEMENTATION_PLAN.md`.

**Marble Maze high-DPI compositor and capture-integrity corrections
(2026-09-20):** a fresh source-derived lost-state replay found and fixed a
browser 2D/WebGL coordinate handoff error. The canvas now resets to identity
while copying the stage in framebuffer-pixel coordinates, preventing the
inherited scaled/Y-flipped display-list transform from moving the stage. At
DPR 2, the synchronized 1714×842 stage comparison passed with 99.9285% exact
pixels (MAE `0.00555`, RMSE `0.4493`); these values are diagnostic only, not
approved parity thresholds. The browser screenshot metadata helper now
requires live `marbleDebug` state and rejects controller-phase, marble-pose,
viewport, DPR, theme, and material-state mismatches instead of copying those
claims from the source manifest. It takes the camera from the live renderer;
the synchronized pair comparator checks the camera trace. Its valid/mismatch
tests are registered in the artifact gate. The complete
`bash scripts/test_wasm_artifact.sh` gate
exited 0 after registering that test; it included 80 held-input sessions,
three multi-trial/adaptive sessions, all 80 board/MJCF cases, and 134
trajectory scenarios / 14,796 per-frame states. The focused renderer contract
and browser physics tests also pass. Visual state/theme/viewport coverage and
reviewed pixel limits remain open; see `IMPLEMENTATION_PLAN.md`.

**Marble Maze live WebGL status overlay (2026-09-20):** a freshly captured,
source-synchronized won frame showed that the browser painted the live
feedback line in its 2D fallback but omitted it in the active WebGL renderer.
The WebGL path now paints the dynamic status after its framebuffer composite,
leaving the Elisa-owned title, help, and verdict band as-is. A headed DPR-2
Games → Attention → Marble Maze → Space replay captured a real controller
feedback state with MuJoCo and WebGL2, no renderer error, and matched the
source marble pose/seed/time/camera/viewport/material manifest. The stage is
99.9285% exact (MAE `0.00555`, RMSE `0.4493`); metrics remain diagnostic.
The capture revealed and fixed helper assumptions too: common controller
state contains 12 slots, and its trial number is one-based. The browser-pair
unit test now covers both. After these overlay/helper changes,
`bash scripts/test_wasm_artifact.sh` exited 0 through the complete registered
suite, including all 134 Marble trajectory scenarios / 14,796 states. The
fresh won pair is stored in `output/playwright/`; status chrome is now present
in both images. Fresh synchronized READY, rolling, won, lost, and done captures
now exist at the baseline light-theme DPR-2 viewport; timeout/multi-trial,
theme/viewport captures, and reviewed pixel acceptance remain open.

**Marble Maze fresh DONE-state pair (2026-09-20):** the headed browser entered
Marble Maze through the normal Games → Attention route, launched the real board,
and advanced the source-derived one-trial win through feedback into DONE. The
live `marbleDebug` snapshot generated the browser manifest and was checked
against the source DONE manifest, including controller trial/verdict, marble
pose, board/grain seeds, camera, viewport, DPR, material state, and PNG hash.
The required synchronized comparator passed state validation; camera maximum
delta is `5.64e-8`, and the stage exact-pixel fraction is `99.9285%` (MAE
`0.00555`, RMSE `0.4493`). These remain diagnostic cross-rasterizer metrics,
not approved thresholds. Browser console reported zero errors and warnings.
See the paired image and sidecars named `mm-browser-done-912x684` under
`output/playwright/`. This closes only the baseline DONE render-state capture.

**Marble Maze fresh READY-state pair (2026-09-20):** the original capture
helper now records the genuine pre-run state without creating a tray or
simulation; no board seed/trial, marble pose, renderer camera, or materials are
claimed. The browser debug snapshot independently reports no board/marbles and
records its reserved source stage rectangle and framebuffer at DPR 2. The
source/browser metadata helper and synchronized scene comparator explicitly
validate READY's empty marble list, zero board/trial sentinels, absent camera,
and `not-created:no-board` material state. The normal Games → Attention →
Marble Maze menu route produced the candidate screenshot. State synchronization
passes; the reserved blank stage is 100% pixel-exact. Full-frame exactness is
98.7996% (MAE `0.8753`, RMSE `11.8123`), diagnostic-only and dominated by
cross-renderer text antialiasing. Capture: `mm-browser-ready-912x684.png`; raw
debug and both manifests are adjacent in `output/playwright/`. READY-specific
metadata/comparator contracts, the existing browser physics smoke, and Python
syntax checks pass. Timeout/multi-trial, theme/viewport variants, and reviewed
pixel acceptance remain open.

**Marble rolling-render evidence (2026-09-20):** a source UI replay now
captures a deterministic moving marble (eight east-held 60 Hz updates) and
serializes its complete position, velocity, angular velocity, quaternion,
tilt, phase, and elapsed time. The browser receives that exact state through
an opt-in renderer-test hook, advances only the common controller clock, and
keeps MuJoCo frozen for the screenshot. Both manifests attest the same state;
the required-scene-state comparator contract and real source/browser comparison
pass. The 1714×842 stage is 99.9660% pixel-exact (MAE 0.00480, RMSE 0.4148),
while full-frame and stage metrics remain diagnostic only. Baseline READY and
won/lost/done captures have since been added; timeout/multi-trial,
theme/viewport variants, and reviewed pixel acceptance limits remain open.
The full `bash scripts/test_wasm_artifact.sh` suite was rerun after the new
snapshot injection and comparator contract; it passed through all 134
trajectory scenarios / 14,796 per-frame states.

**Continuation note (2026-09-19):** the external compiler's source-fresh
Stage1 product at `380b0aec` rejects the historical Stage0/Stage1 acceptance
regression identically. The port-owned reseed hit its existing 4 GB RSS guard,
so its older provenance remains unchanged. This is deliberately recorded as a
toolchain freshness limitation, not hidden by relabeling an older binary.

**Native Marble controller bridge (2026-09-19):** Python and SDL now expose
Marble Maze's source-backed controller through their native export boundaries:
creation/options validation, held direction plus release, elapsed advancement,
state/results, display-list frames, task-hub launch, and disposal. The Python
`test_marble.py`, SDL `--selftest-marble`, and both builds pass. These hosts
use the deterministic 2D `SceneMarbleMaze` fallback and explicitly retain
physics ownership as a host boundary; browser MuJoCo remains the only
production 3D physics path. This closes the native controller wiring gap, not
native MuJoCo or exact original 3D pixel parity.

**Native In the Dark controller bridge (2026-09-19):** Python and SDL now
expose the source-backed timed controller, including option validation,
walking-clock advancement, answer dispatch, display-list frames, and cleanup.
`shells/python/test_inthedark.py`, the SDL `--selftest-in-the-dark`, and both
native builds pass. The route is available directly and from the native task
hub; it is still partial because original-controller differential replay,
full browser/native acceptance, and cross-platform release evidence remain
open.

**Native Fog of War controller bridge (2026-09-19):** Python and SDL now
expose the source-backed visibility controller, including radius/move/trial/
persistence validation, wall-bump versus movement semantics, revealed-map
state, display-list frames, and cleanup. The Python smoke, SDL
`--selftest-fog`, standard native builds, and catalog audit pass. Original
controller differential replay and complete cross-shell fidelity remain open.

**Native Removals controller bridge (2026-09-19):** Python and SDL now expose
the source-backed timed move/answer controller, including option validation,
clock advancement, five-choice answer dispatch, source answer/value inspection
for test replay, display-list frames, task-hub launch, direct routes, and
cleanup. The Python lifecycle smoke, SDL `--selftest-removals`, both 243-case
Stage0/Stage1 Removals parity suites, catalog audit, and full WASM artifact
suite pass. Original-controller differential replay and complete cross-shell
fidelity remain open; the SDL build was validated with an explicit existing
Stage1 product because the external compiler checkout currently fails its
source-freshness guard.

**Native Chain of Custody controller bridge (2026-09-19):** Python and SDL
now expose the source-backed belt, machine, claw, ownership, timing, delivery,
and adaptive-rung lifecycle, including display-list frames, direct routes,
task-hub launch, and cleanup. The native Python smoke, SDL
`--selftest-custody`, both 244-case Stage0/Stage1 Custody parity suites, and
catalog audit pass. Exact original-controller replay and full cross-shell
visual/input fidelity remain open; native source aggregate names were made
unique to satisfy the compiler's multi-module emission rule.

**Authoritative newest-compiler fast-gate checkpoint (2026-09-19):**
`DEVELOPER_DIR=/Library/Developer/CommandLineTools bash scripts/gate.sh`
exited 0 with `GATE GREEN`. It used external compiler
`main@bb1a8289e6f3063bedddccb519a6d719235d6fde`, equal to fetched
`origin/main`, dirty-worktree source fingerprint
`efd8be06c6222a6a9515c454fe548b5aa7722405c24c0e95e7d5d80463080eec`,
and source-fresh Stage1 product SHA-256
`c0b7b26f4d20446839f60ce929cd46bef3117a6db9f3c5f356bf05b2fc11b5a9`.
The complete-build provenance guard passed, and the post-run mtime check found
no Elisa source newer than the selected product. Existing external compiler
edits remained user-owned and untouched.

Both compiler-stage differential catalogs and all task/scene streams passed.
The latest-Stage1 artifact rebuild and registered browser/controller suite
also passed, including the 3D-only N-Back controller and the complete current
Marble matrix: Stage1's 64 model cases plus 32 scene frames / 101 commands,
all 16 MuJoCo boards, 1,344 option combinations, 80 generated sessions, 36
held-input sessions, seven adaptive trays, 80 board/MJCF comparisons, and 134
Python/native-versus-browser/WASM trajectories with 14,796 per-frame states.
The artifact is 1,095,131 bytes with SHA-256
`1fff9c78104ff6d962678837c1afba9b18596b1749b6e4a9b20cd6664b109bc2`;
the linked object hash is
`3dadabb11824fe50131a188fb9b2eecc3ff08332122f41cbecf907343be0770f`.
Stage0 fast tests, the Stage1 Glyphs RSS regression, targeted Stage1 parity
smokes, and runtime provenance all passed. The fast gate intentionally skipped
Stage0 `test-full`, self-host fixpoint, and the Stage1 semantic differential;
those slow-tier checks and the remaining fidelity/native-host backlog are not
claimed here.

**Current Graph Mapping checkpoint (2026-09-18):** the newest Stage1 artifact
now contains the source-backed fixed-storage Graph Mapping controller, the
`SceneGraphMapping` display list, common-v1 task ID `921237686` (canonical
FNV-1a for `graph_mapping`), and additive edge/point/info accessors. The
browser route is real: Games → Reasoning → Graph Mapping → Space renders two
generated graphs; Y/S/N/D, arrows, and source-layout buttons grade the actual
pair; exposure and 900 ms feedback deadlines are scheduled from the controller;
and task replacement destroys the run/timer. Focused controller and browser
contract smokes, catalog audit, and a headed localhost replay pass. The
source-derived Graph Mapping options UI now persists the six common-v1 fields;
feedback remains visibly fixed on because the source default is enabled and
the common ABI has no seventh slot. `C` opens options from the hub or only at
the source controller's ready/done boundary; active-trial `C` is consumed
without interrupting the run. The legacy darray-backed source sweep adapter is
kept test-only so the latest compiler's linear-handle ownership checks remain
active in production. Cross-rasterizer screenshots remain open.

**Graph Mapping controller differential (2026-09-19):**
`test/graphmapping_controller_diff.py` passes 864 source/controller cases over
all supported node sizes, densities, subtle/adaptive modes, exposure values,
and deterministic seeds. It compares the balanced deck, generated edges, ring
coordinates, pair truth, timing boundaries, score counters, duplicate answers,
and adaptation. It found and fixed a controller-only parity bug: the answer
deck was shuffled forward instead of using Python's descending Fisher–Yates
order. The remaining Graph Mapping backlog is cross-rasterizer/reference
screenshots, not the source/controller state contract or browser options
lifecycle.

**Current Crossed Wires checkpoint (2026-09-18):** the newest WASM build now
contains a fixed-storage common-v1 controller in
`src/tasks/crossedwires_game.elisa`, wired to the source kernel and
`SceneCrossedWires`. It preserves the source's private wiring, seed stream,
four/eight-key rung families, wrapped movement, target sequence, dead-port and
drift rules, operation budget, adaptive rung change, and verdict phases. The
browser route uses the source default level 3 / five rounds / adaptive / grid
settings, maps the original WASD, arrows, letter-ring, and keypad controls,
and disposes the handle when the task is replaced. `test/crossedwires_diff.py`
continues to pass the kernel's whole-bout and player-policy matrix; the new
`crossedwires_game_smoke.mjs` and
`crossedwires_browser_contract_test.mjs` pass against the production artifact.
Native Python and SDL hosts, the source options panel, and headed menu replay
remain open fidelity work and are not claimed by this checkpoint.

**Current Sudoku checkpoint (2026-09-18):** the newest WASM build now includes
`src/tasks/sudoku_game.elisa`, the source-backed `Sudoku` generator/rater, and
`SceneSudoku` through common-v1 task ID `4211466488`. The controller copies
source givens and the unique solution into fixed storage, keeps clues
immutable, implements cursor movement, 1–9/A–G entry, pencil masks, erase,
wrong-entry accounting, full-grid grading, adaptive rung changes, solved and
DONE verdicts, and idempotent cleanup. The generator was corrected to use a
bounded temporary region per rejection-sampling attempt; without that
boundary the source's default rung budget retained every abandoned candidate
grid and the browser artifact failed with a linear-memory access error before
the first puzzle appeared. The browser route uses the source defaults (rung 3,
three trials, visible clashes, adaptive scoring), renders the real scene, and
disposes the run on task/category changes and task exit. `test/sudoku_diff.py`
and `test/scene_sudoku_diff.py` remain the source kernel/scene parity oracles;
the production artifact now also passes
`test/sudoku_game_smoke.mjs` and
`test/sudoku_browser_contract_test.mjs`, covering seeded replay, immutable
givens, pencil/erase behavior, a real complete solve, verdict preservation,
rendering, browser input, and cleanup. Python/native and SDL3 adapters, the
source options panel, headed menu replay, and controller-level original UI
differential traces remain open and are not claimed here.

**Current Matrix Reasoning checkpoint (2026-09-18):** the newest WASM build
now includes the source-backed `MatrixReasoningGame` controller in
`src/tasks/ravens_game.elisa`, the existing Ravens generation kernel, and the
direct-geometry `SceneRavens` renderer through common-v1 task ID `3934003723`.
The controller copies generated grid and choice panels into durable fixed
storage, preserving source figure shape, fill, angle, part, placement, palette,
choice shuffling, correct-answer identity, feedback, explanation, adaptive
level, exposure, and terminal verdict state. The browser route uses the source
defaults (level 1, fifteen trials, no exposure, adaptive scoring, feedback,
explanation disabled, colour enabled), renders actual generated polygons rather
than the generic task placeholder, maps keyboard and normalized pointer
selection through the renderer's choice geometry, schedules exposure/feedback
deadlines, and destroys the run on task replacement. The focused
`ravens_game_smoke.mjs` and `ravens_browser_contract_test.mjs` pass against the
production artifact; the catalog audit also records the controller, kernel,
scene, exports, and host capability. The browser now persists the six
common-v1 option fields, including the packed feedback/explanation flags, and
preserves a live run while its six-row options panel is open. The focused
source parity is now green on both compilers: `ravens_diff.py` matches all 729
geometry/palette/layout/rule/whole-puzzle cases on Stage0 and Stage1, while
`scene_ravens_diff.py` matches 40 placement frames and 379 display commands on
both stages. Screenshot-level direct-geometry comparison remains open. Native Python and SDL3
adapters were added on 2026-09-19: `test_matrix_reasoning.py` and
`--selftest-matrix-reasoning` pass lifecycle, grading, timing, rendering, and
cleanup; the adapter changes preserve the 729-case Stage0/Stage1 differential.
The controller now follows the source's per-puzzle sampled-seed stream and
removes cards during the source `hidden` redraw phase; both behaviors have
regression coverage in the controller smoke.
The new `test/ravens_controller_diff.py` additionally compares the pymodule
run boundary with the original Python generator across 18 level/seed cases and
two adaptive trials, including every stored grid/choice figure attribute,
answer identity, feedback deadline, and next-trial level. It passes. A headed
Playwright replay selected Matrix Reasoning through the real task hub, started
with Space, answered the seeded first puzzle, and reached puzzle 2 with
`right 1`; captures are under `nw-core/output/playwright/`.

**Superseded completed artifact build and fast-gate boundary (2026-09-18 22:27
Europe/Oslo):** the served `build/nwcore.wasm` was rebuilt at 22:25 by
`scripts/build_latest_stage1_wasm.sh` with
`DEVELOPER_DIR=/Library/Developer/CommandLineTools`, and the configured fast
gate subsequently finished `GATE GREEN`. The external Elisa compiler
checkout was at commit
`dcf5ce4781c073b4669f7c85441bf82e5322a3c9`, one commit ahead of and zero
commits behind fetched `origin/main` at
`624baa97a608951c11a722efdb9ae20f8fae6a46`. Its working tree was
intentionally dirty with the newest compiler fixes; the complete source state
used by the build is identified by fingerprint
`7f115366d9f9655811ecec59fcd87886c6e5bffa05cb65250b3eb8c9f01d4832`.
The selected fresh Stage1 product, `Elisa-compiler/bin/elisac-stage1`, is
SHA-256
`96663b3774004282ee0617b5bd82d45c87cdf28e50f231a50337223731f0c730`; the
Stage1 runtime object is byte-identical to the canonical runtime at
`1dbb59736ed498f8e602003e9504953e6f2a8bef916340882d3d4ce6df3e9e48`.
The emitted WASM is 1,095,131 bytes with SHA-256
`1fff9c78104ff6d962678837c1afba9b18596b1749b6e4a9b20cd6664b109bc2`; the
linked object is SHA-256
`3dadabb11824fe50131a188fb9b2eecc3ff08332122f41cbecf907343be0770f`.
Freshness and post-build provenance guards passed. The complete artifact
suite and fast gate passed both-stage differential catalogs, all registered
game/controller/scene/browser contracts, the 3D-only N-Back controller,
compiler acceptance (bare: 6 documented reject-gaps and 0 accept-gaps;
with-stdlib: 0/0), the 360-fixture diagnostic smoke, the Stage0 fast tests,
the Stage1 Glyphs RSS smoke, the 80-board Marble timeout matrix, 36 generated
held-input Marble sessions, and the 134-scenario/14,796-frame official-MuJoCo
trajectory oracle. The 21 declined optional concurrency-runtime bodies were
expected backend warnings. The deliberately skipped slow `gate.sh --full`
tier and the remaining fidelity/native-host backlog remain open.

**Superseded latest-local refresh (2026-09-18):** the user's Xcode-license
and Homebrew repair was verified by a fresh `-O2` production build using
`DEVELOPER_DIR=/Library/Developer/CommandLineTools`. The selected Elisa
checkout is at `ee50240f9e0de8046708c7153f320c89b222bbb7`, with fetched
`origin/main` at `76230afa9e5fdf96f25f88f30405234912905ddb`; it is four commits
ahead and zero commits behind. The selected Stage1 product was reseeded from
current Elisa-core Stage0; its SHA-256 is
`f557e6dce94f90e776bdb57dc8952db0e4dc170232c0ce6feb749d90f505ebae`, and its
complete current-worktree source fingerprint is
`d8e56bf02aaf0ffb7f3190f8002097a2f7c59a2f23309096daf8476d5b6103af`. The
external compiler checkout remains user-owned and intentionally dirty; its
parser and machine-law changes were preserved. The served
`build/nwcore.wasm` is 974,768 bytes with SHA-256
`72cd4b672736123bb3a2562f885848f0ed01862ad83e1d1073d4fafd2539f582`; the
linked object is
`952008613f13e7569beed3757371b3ba0c765d8bee3b1e23a2e2d7c6685d5aaf`.
The guarded build's source-mtime and post-build provenance checks passed, and
the complete configured fast gate finished `GATE GREEN`, including both-stage
differential suites, all controller/scene/game/browser contracts, the 3D-only
N-Back smoke, and the 134-scenario/14,796-frame Marble trajectory oracle. The
SDL shell rebuilt from the same product with its 180-frame self-test at zero
bad frames.

**Marble controller result-history ownership (2026-09-18):** the common
Elisa controller now retains each completed source result row instead of
leaving the browser ledger as the only history owner. `ACTION_RECORD_RESULT`
accepts the host physics counts once after `REPORT` or timeout `SCORE`; the
controller stores rung, elapsed milliseconds, home/lost counts, physical
verdict, source-score win bit, and board seed through DONE. The additive
`nw_api_v1_marble_info`/`nw_api_v1_marble_value` accessors expose those rows
without changing the twelve-field state envelope. The runtime smoke verifies
the timed-out zero-lost score quirk, every stored field, and duplicate-commit
rejection. The browser commits and reads the controller row before updating
its durable compatibility ledger. The controller now also blocks both an
explicit `ACTION_NEXT` and automatic feedback expiry until the score and
result row are committed, so a stalled physics host cannot silently lose a
source result between trays. The runtime smoke covers that barrier as well.
The timeout path now also synchronizes the measured physics elapsed time into
the controller after the deterministic 15-second controller boundary and
before `SCORE`/`ACTION_RECORD_RESULT`; this preserves a final MuJoCo frame's
small elapsed-time overshoot in the authoritative row without moving the
timeout transition itself. The latest headed two-tray replay retained
`controllerElapsedMs=[15000,15016]` from physics elapsed values of about
`[15.0001,15.0164]` seconds.
This closes the controller-ownership slice
of MM-004; complete option-combination/replay, solved/lost generated-board
play, pixel, and native-host acceptance remains open. The generated-board
timeout/result-history submatrix is recorded below.

**Marble options-note layout correction (2026-09-18):** the source options
screen's live note is longest at rung 16, where the extra multi-marble
sentence must still fit above the native cancel/modify/apply footer. The
browser's previous approximation used 18-pixel line spacing and allowed the
wrapped note to overlap that footer. `shells/web/index.html` now wraps the
source note to the panel width and uses the compact native-style 12-pixel
line rhythm; a headed rung-16 options replay shows all note lines inside the
panel with the footer clear. Applying the row still returns to a board-less
READY controller, and Space then creates the three-marble MuJoCo tray. The
checkpoint is `nw-core/output/playwright/marble-options-layout-latest.png`,
SHA-256 `ad8ab52ad7f64e012c1f863f9fe2c8fc23bd989d3dfdd804c71ad21e6cf6bdea`.
The source-note differential remains green for all 16 rungs.

The same deterministic two-tray route was also run with the explicit browser
fallback solver. It retained both board seeds and both result rows, reached
`DONE; 2 trays of 2` with `score={trays:2, won:2, lost:0, home:0,
best_rung:1, seconds:30}`, and produced zero errors; the only warning was the
intentional forced MuJoCo-load diagnostic. The fallback rows retained measured
controller elapsed values of `15015` and `15017 ms`. Its visual checkpoint is
`nw-core/output/playwright/marble-fallback-multi-trial-latest.png`, SHA-256
`e9f45896a3169c6b214d9c17ff91743e641303b7bfacdde4c6e5880bf6f338a1`.

**Marble feedback scheduling correction (2026-09-18):** the browser now
advances the won/lost feedback phase by the complete wall-clock gap between
draws, matching the Python source's `clock() + 2.6` deadline while retaining
the active-physics 50 ms frame clamp. A headed MuJoCo loss followed by a
deliberate 3.2-second main-thread stall reached `DONE` on the next follow-up
frame instead of stretching feedback; console errors and warnings were zero.
The exact evidence is in
`docs/marble-physics-manifest.json` under
`lifecycleEvidence.headedBrowserFeedbackWallClock`. Focused Marble source,
MuJoCo, browser, renderer, cross-compiler, board, and trajectory tests pass;
the broader MM-004/MM-005/MM-006 fidelity backlog remains open.

**Marble status rounding correction (2026-09-18):** the visible roll and
pitch readout now uses a shared `marbleSourceRound()` implementation of
Python's nearest-ties-to-even `round(float)` rule. This matters for negative
half-degree boundaries, where JavaScript `Math.round()` would display `-1`
for `-1.5` while the native UI displays `-2`. The browser physics and
renderer gates plus the direct `marble_maze_browser_test.mjs` regression pass;
trajectory and board parity remain unchanged.

**Marble generated-board timeout session matrix (2026-09-18):**
`test/marble_generated_session_test.mjs` now drives the common controller and
official MuJoCo adapter through 80 generated trays (rungs 1–16 × run seeds
`0`, `1`, `17`, `314159`, and `1073741823`). Each case starts from the
board-less READY state, deals the controller-selected board, runs 300 source
50-ms frames with no tilt to the exact 15,000-ms timeout, synchronizes the
measured physics clock, commits the timeout score and host home/lost counts,
checks all seven retained result fields, waits through the native 2.6-second
feedback interval, and reaches DONE. The matrix exercises up to 60 walls, 39
holes, and four marbles per generated tray; every case disposes its MuJoCo
model/data pair. It is part of `scripts/test_wasm_artifact.sh` and passes on
the latest completed 1,095,131-byte Stage1 artifact recorded above. This closes generated-board
timeout/result-history coverage, while solved/lost input routes for arbitrary
generated boards, fallback-vs-MuJoCo identity, and exact cross-rasterizer
pixels remain intentionally open.

**Marble generated held-play slice (2026-09-18):**
`test/marble_generated_play_session_test.mjs` is also part of
`scripts/test_wasm_artifact.sh`. It drives the 36-case selected generated-board
matrix through the common keyboard ABI and official MuJoCo adapter using routes
derived from each board's transported wall geometry. The matrix includes home
captures and real swallowed-marble losses. The test checks physical/controller
level synchronization, all seven retained result fields, the result-commit
feedback barrier, DONE, and per-case MuJoCo cleanup. This is an end-to-end
solved/lost slice; exhaustive generated-board routes, all option combinations,
fallback-vs-MuJoCo contact identity, and exact cross-rasterizer pixels remain
open.

**Exhaustive-play driver audit (2026-09-19):** an attempted expansion of that
test to all 80 generated rung/seed pairs was intentionally rejected. The
existing driver holds each direction for a fixed 18 source frames and then
levels the tray; that is a useful deterministic regression trace, but it is
not a universal solver. On an otherwise valid rung-1 board it crossed a short
corridor, rebounded, and remained rolling after the route's final command.
This is evidence that the test driver needs an adaptive, bounded, physically
observable steering policy before the matrix can be widened—not evidence that
the MuJoCo adapter or controller incorrectly classified a result. The
production physics and the 36-case slice remain unchanged and the focused
browser, MuJoCo, renderer, generated-play, and multi-trial tests all pass.

**Authoritative toolchain/artifact refresh (2026-09-17):** the served artifact
was rebuilt from the clean detached worktree
`/tmp/elisa-compiler-clean-bfedb0d7` of the newest selected Elisa-compiler
Stage1 checkout. The compiler is
`bfedb0d707a00797ddd16341f21a8b6e0a9677af`, exactly matching fetched
`origin/main` at the build boundary. Its clean Stage1 product SHA-256 is
`892348e05a253d059f7e7f582aef1c13df04074f48129466d9fed5f6d6c6c0b9`, and the
source fingerprint is
`9de69658a554a61ac1679e3cd52398ea73800adf700fb0c51d7a636324dceef9`. The
current `-O2` artifact is `build/nwcore.wasm`, SHA-256
`4d6c172fa79b24038b14fd75a8d0d778f285fb7544a795dd1d429f07cb109148`
(`843967` bytes), with linked object SHA-256
`6b3e3149bc5e98f15b4a4b532691a6a89f93b0284279823eec2b0b140e8c9947`.
At the build boundary the canonical external checkout was clean at the same
commit, so no uncommitted compiler source was included or silently excluded.
The port-owned toolchain provenance records Stage0
`main@bef5f4a465c958b2b5672d216c53aa96532dc36c`, Stage1
`main@e82f160c88bc78b1cf35bcbf59408b5d714486ef`, and runtime SHA-256
`dbed0552a85df51da0c050e4f009bb7c565f792a0676df0f465e9e986e8845a4`.

The port-owned `toolchain/PROVENANCE` file intentionally remains the separate
Stage0-seeded pair listed above; the explicit latest-Stage1 artifact build does
not rewrite that pinned record. `bash scripts/build_latest_stage1_wasm.sh`
exited 0 with the newest compiler: its Stage0/Stage1 artifact checks, full
configured artifact/controller/scene sweep, 3D-only N-Back checks, API checks,
targeted compiler parity smokes, and the 134-scenario official MuJoCo Marble
trajectory oracle with 14,796 per-frame comparisons passed. The older
`e82f160c` configured fast-gate `GATE GREEN` is historical. The configured
fast gate was subsequently rerun with this exact `bfedb0d7` pair and finished
`GATE GREEN`, including the Stage0/Stage1 differential matrices, latest
artifact suite, Stage0 compiler tests, targeted Stage1 parity smokes, and
runtime provenance. The intentionally skipped slow `--full` tier remains
open.

**Production-host scope correction (2026-09-17):** the browser is the only
currently exposed task host. Its production surface contains the 3D N-Back
route only; the generic Mode/menu/session path and generic `C` delegation were
removed. Python and SDL are title-only shells for now, with no generic N-Back
preview/session ABI. The Python ABI exports only the title/task-entry and
timing functions needed by that shell, while SDL uses the minimal native title
export in `src/native/sdl_exports.elisa` rather than compiling the browser's
WASM export unit. `test/catalog_audit.py` enforces this boundary. The original
catalog and source-parity helpers remain test/reference data, not production
capabilities.

The refresh includes two Stage0 source-compatibility corrections found by the
artifact suite: Numberology's overflow guard no longer relies on a compiler
endpoint refinement that Stage0 loses, and Custody copies only the live
round-sized box arrays instead of reading through the adapter maximum. The
other newly ported controllers retain the earlier Stage0-safe helper/control-
flow/read-only-borrow fixes. These corrections preserve the source oracle and
do not broaden the N-Back scope beyond 3D.

The same refresh corrected two focused Marble fidelity boundaries. Direct
fallback `step(dt)` now matches native `Simulation.step(dt)` exactly at its
public boundary—one positive finite call advances elapsed time through four
equal physical substeps—while the UI-only 50 ms clamp and 60 Hz remainder loop
remain in `advance(dt, held)`. The WebGL2 renderer now forwards the native
`normal_scale` draw uniform rather than assuming `[1, 1, 1]`. Focused browser,
MuJoCo, renderer-contract, trajectory, and cross-compiler Marble checks pass.
The preceding `e82f160c` refresh completed its configured fast gate with
`GATE GREEN`; its exact compiler, artifact, and test identities are retained
in `docs/marble-physics-manifest.json` as historical evidence, not as a
current gate claim for the newer compiler artifact.

The follow-up fallback audit found one more source contract: when the native
speed cap engages, it scales `wx`/`wy` with `vx`/`vy`. The fallback now does the
same, preventing stale rolling spin from re-entering the next floor solve.
The high-speed/high-spin browser regression and official MuJoCo runtime test
pass; this correction affects only the explicitly labelled fallback path.

The browser READY boundary now also matches the native Marble lifecycle. The
native `_reset()` has no tray or `Simulation` until Space starts a run; the
browser launch path previously built the first board too early. `launchTask()`
now creates only the READY controller, READY rendering displays
`Press Space to start` without a board, and Space performs the lazy board
handshake for both the first tray and later PREPARING trays. A fresh served
Playwright smoke reached Games → Attention → Marble Maze with a blank board
area, then Space created the official MuJoCo tray and showed `the tray — 15s`.
The smoke had zero console errors/warnings; static regression coverage is in
`test/marble_renderer_contract_test.mjs`, with captures in
`output/playwright/marble-ready.png` and `output/playwright/marble-running.png`.
The retry control now uses the same distinction: a READY controller handle is
not an active physics run, so a failed MuJoCo load remains retryable before
Space; PREPARING, RUNNING, FEEDBACK, and DONE remain protected from a hot swap.
This closes the pre-start allocation/deal mismatch, while full multi-trial
result comparison and source/GPU pixel acceptance remain open.

The renderer failure path is now explicit as well. A WebGL2 construction or
frame failure selects the bounded 2D Marble view, but the live status now says
`renderer fallback` rather than silently presenting it as the native 3D tray;
normal runs say `renderer webgl2`, and a context-loss interval says
`renderer recovering`. The opt-in `window.__nw.marbleDebug` diagnostic retains
the renderer state and error. A headed query-gated exercise with
`marble-force-renderer-failure=1` reached a live MuJoCo tray, reported
`physics mujoco · renderer fallback`, and kept the physics state interactive.
This closes the observability part of MM-006; it does not close MM-005's
cross-rasterizer visual identity requirement.

The current controller audit also closes a lifecycle leak at the run boundary:
starting Marble from DONE clears `elapsed_ms` and `feedback_elapsed_ms` before
the asynchronous board-ready callback, so stale timing is not observable
during PREPARING. The source change is in
`src/tasks/marblemaze_game.elisa`, with an immediate post-start assertion in
`test/runtime_protocol_v1_smoke.mjs`; the latest-compiler artifact suite and
Marble parity suites pass with this reset. The older clean-compiler gate result
belongs to the superseded compiler checkpoint.

The follow-up undealt-READY/RNG audit now matches the native
`MarbleMaze._reset()`/`_next_trial()` boundary: a fresh controller remains at
`trial=0`, `board_seed=0`, and `grain_seed=0` with no tray or physics resource,
and the accepted Space action consumes the first board/grain draws. Later
prepared trials consume exactly one board identity at preparation time. The
runtime protocol regression, latest `bfedb0d7` Stage1 artifact suite, and the
headed smoke all pass; READY had zero live MuJoCo resources, then Space
created board seed `889418965` with one live model/data pair and no console
diagnostics.

The older 2026-09-16 checkpoint below is historical evidence only:
the served artifact was
rebuilt after the local `Elisa-compiler` Stage1 product advanced. The selected
compiler is `main@8110bb9ff33bb41fba24a7553f16c89685e98bd2`, exactly matching
fetched `origin/main`; its Stage1 product is
`Elisa-compiler/bin/elisac-stage1`, SHA-256
`b8917d13bf891c7f04f60daa3f2549dbb1dd0162ef508de5723d24f04cf90ff3`, and
the source fingerprint is
`d8fb78556b2af6538994f5502eaad0ff283d3f5e73add86befb691fa1fc8ab04`.
Six pre-existing compiler source edits were present; the freshness guard found
no source newer than the product. The resulting `-O2` artifact is
`build/nwcore.wasm`, SHA-256
`e840a1244dd70fe443b18f06207dae8bd431520fb4d83b63145e10a2106060aa`, with
linked object SHA-256
`ce15ef76d1361404ae9d73c0775cfd50701145dd478d3e17af23b39339b9af49`.
The complete artifact gate passes, including Mr. Time and the 134-scenario
Marble trajectory parity suite. The older compiler/product identities below
remain historical evidence and are not the current served artifact.

## N-Back port scope

The port scope is **3D N-Back only**. The original `nback` catalog identity is
retained as reference data for catalog comparison, but non-3D dual, position,
color, audio, combination, arithmetic, variable-N, Jaeggi/clinical, and
generic preview/session variants are not port features and must not be exposed
or delegated by a port shell. Shared N-Back helpers remain only where needed
by the 3D implementation or source-parity tests.

## Current 3D N-Back vertical slice

The live browser route is now backed by `NBack3DGame` through common WASM API
v1. The browser task is labeled `3D N-Back`, uses source mode 10 (Position)
with `grid_3d=true`, and does not expose the original application's other
N-Back variants. Space/Enter starts or resumes; A reports a match; P pauses; R
restarts; Escape returns to Games. The controller owns the seeded stimulus
stream, phase/deadline clock, response grading, pause state, score, and
pattern masking; JavaScript only translates keys and schedules `advance`.

The historical candidate artifact was `../build/nwcore.wasm`, 830,223 bytes, SHA-256
`69efccadb3e031853e0eedcc24ab992863650118f2a300836431b6763b350cb3`.
It was emitted at `-O2` with the newest Stage1 compiler revision
`main@9ce2616d5cd8c286d43a3a83967a74978b0fd355`, matching `origin/main`, from
an isolated checkout whose only working-tree changes synchronized the three
runtime-vendor files with canonical Elisa-core. The isolated
`bin/elisac-stage1` product has SHA-256
`fe8e2d7bac87f682186253e5b7a1787024d872e5fb71ea0dc4e3c0217dfe4e3e`.
The shared external compiler checkout still has separate uncommitted
diagnostic edits; those were preserved and excluded from the served artifact.
The compiler working-tree delta fingerprint is
`219ab68f209e45efb33a639c58bff497dbbf9d7b6f28f659ea0af917f2def831`; the
freshness guard found no newer `.elisa`/`.elisai` source than the product. The
linked object is SHA-256
`2bba67a16185ed54d37a5da51a085c8b1ccdf4f3aa7633f33e11e08cc0d1367b`.

The full artifact gate passed for this historical candidate, including the
dedicated `test/nback3d_game_smoke.mjs` exact source-stream/lifecycle check and
the headed localhost Games → 3D N-Back → Space → A smoke. This remains a partial
port: full original 3D display-command, tick-quantization, reaction-time,
statistics, startup-delay, and persistence differential coverage remains open.

**Fresh headed replay (2026-09-19):** a newly opened Chromium session selected
the 3D-only task from the live menu, used Space through the startup phase,
rendered the first cube stimulus, and submitted `A` during the response window.
The captured frames are `nw-core/output/playwright/nback3d-headed-ready.png`,
`nback3d-headed-running.png`, and `nback3d-headed-stimulus.png`. This confirms
ordinary menu/keyboard operation but does not close the explicitly listed
complete-session or original-controller differential gaps.

**Marble headed lifecycle replay (2026-09-19):** the live task hub selected
Attention → Marble Maze, opened and applied the source-shaped options screen,
started a real tray with Space, and moved the tray with held `W` input. The
running status reported `physics mujoco` and `renderer webgl2`; captures are
under `nw-core/output/playwright/marble-headed-ready.png`,
`marble-options.png`, and `marble-headed-running.png`.

## Repository identities and working-tree ownership

| Component | Root / revision | State |
| --- | --- | --- |
| Port workspace | repository root, `2bb707e43b56d6d0c113b9ed4869f74517eedf0c` | Dirty; preserve existing changes. The exact status snapshot is below. |
| Frozen Python reference | `original-neural-workshop-enhanced`, `dcd59a50351d742583e2501235ab1e5f24d63f41` | Clean at inspection; catalog fixture pins this commit. |
| Stage0 compiler source | sibling `Go projects/Elisa-core`, branch `main`, `1a3452b2d1358b4bf5f6ac2b3af49d5a384c2153` | Clean current checkout. The canonical fixture paths now resolve here; a refreshed port-owned Stage0 was built during follow-up, but its full runtime-object/provenance refresh was stopped at the host-level loader stall and is not used to make a new artifact claim. |
| Historical isolated Stage1 candidate source | sibling `Elisa-compiler`, branch `main`, `9ce2616d5cd8c286d43a3a83967a74978b0fd355` | Older candidate; not the current served artifact. |
| Legacy pinned Stage1 source | `worktrees/elisa-compiler-nw`, `df6cf8172cf75cf7fe861c9591d7d03f16a0d7c6` (detached) | Retained for the independent historical toolchain; its product is stale against that dirty worktree and is no longer used by the production browser build. |

The current root-tree inventory, captured before adding this report, is:

**Tracked modifications:** `.gitignore`; `nw-core/scripts/build-toolchain.sh`,
`build_wasm.sh`, `check.sh`, `check_result.py`, `gate.sh`;
`nw-core/shells/web/elisa-wasm-runtime.js`, `index.html`,
`marble-maze-mujoco.js`; `nw-core/src/scene_monkeyladder.elisa`,
`src/tasks/sokoban.elisa`, `src/wasm/wasm_exports.elisa`;
`nw-core/test/algebra_diff.py`, `chess_diff.py`, `expressions_diff.py`,
`marble_board_abi_test.mjs`, `marble_maze_mujoco_test.mjs`,
`task_game_input_smoke.mjs`, and `wasm_diff.mjs`.

**Untracked work:** root `IMPLEMENTATION_PLAN.md`; `nw-core/docs/compiler-issues.md`,
`docs/port-status.md`, and `docs/runtime-protocol.md`; `res/Logo/logo-dark.png`;
`scripts/build_stage1_wasm.sh`, `scripts/build_latest_stage1_wasm.sh`,
`scripts/stage1_glyphs_memory_smoke.sh`, and
`scripts/test_wasm_artifact.sh`; `src/tasks/counting_game.elisa`,
`src/tasks/marblemaze_game.elisa`, `src/tasks/monkeyladder_game.elisa`,
`src/tasks/sokoban_game.elisa`, and
`src/wasm/runtime_protocol.elisa`; `test/catalog_audit.py`,
`test/check_harness_test.sh`, `test/fixtures/`, `test/repro/`,
`test/counting_game_smoke.mjs`, `test/monkey_ladder_run_smoke.mjs`,
`test/monkey_ladder_state_frame_smoke.mjs`, `test/runtime_protocol_v1_smoke.mjs`,
`test/sokoban_game_diff.py`,
`test/sokoban_game_smoke.mjs`, `test/sokoban_game_sweep.elisa`, and
`test/source_fingerprint_test.py`.

This list records presence only; it does not attribute every item to this
implementation turn. Inspect `git status --short` before editing overlapping
paths. Do not discard, reset, stash, or rebuild these changes as a cleanup step.

## Compiler roots and tested binaries

The legacy pinned compiler/runtime binaries under `nw-core/toolchain/` retain
their historical identities below. They are not the provenance of the served
artifact: the production WASM was built through the explicit latest-Stage1
path from the isolated `9ce2616d` checkout recorded above.

| Artifact | SHA-256 | Provenance status |
| --- | --- | --- |
| `elisac-stage0` | `c5efa8ce20f781f21817eabc0481efe79a2c895031f49ce64bbb72911386c183` | Matches `toolchain/PROVENANCE`. |
| `elisac-stage1` | `e104009499aa46bd13859efb069eeea9240266f05f2bd09bd76017925fa5d4f3` | Matches `toolchain/PROVENANCE`; its recorded source fingerprint differs from the current worktree. |
| `elisacore_runtime.o` | `d392af4d754340af0b22ed7a00f9db8e66efbc0ab9dac034ac5c30d1f819b663` | Matches `toolchain/PROVENANCE`. |

The active production compiler candidate is the isolated `9ce2616d` Stage1
product `fe8e2d7bac87f682186253e5b7a1787024d872e5fb71ea0dc4e3c0217dfe4e3e`.
Its served artifact is `../build/nwcore.wasm` with SHA-256
`69efccadb3e031853e0eedcc24ab992863650118f2a300836431b6763b350cb3`, and
the linked object is `2bba67a16185ed54d37a5da51a085c8b1ccdf4f3aa7633f33e11e08cc0d1367b`.

`source_fingerprint.py` returns
`9de69658a554a61ac1679e3cd52398ea73800adf700fb0c51d7a636324dceef9` for the
current clean production compiler checkout and its active artifact. Stage0 provenance names commit
`e33dbd60f8c3fb0316114917265e4113d686495b`; the current checkout is
`5284109ca5805560a488c3b0a5d8cd4a1a45e317`. The local
`stage0-elisa-compiler` alias points to a stage0 executable with SHA-256
`4f0979111de75d5cbf4216bb8e79678edcaa8eb900e5a01570892fa8ac09b6b0`, not the
recorded `c5efa8...` product. The wrapper-default `structpy-tree` compiler is
another checkout and fails building the current stage1 worktree's runtime
because duplicate `memset` declarations have incompatible `int`/`i32` widths;
see COMP-008. The pinned Stage1 binary's recorded source fingerprint is
`52d3073d9a1123534b07c48e61afd1b447a49a3ec1e0efda54f96534dd3fbf7c`; an
earlier active-dirty external candidate used fingerprint
`fa6ecbf4ca34bb8259db062c13d606d69f9790ca9d275db57aa6e696088ca2bd` and is
superseded by the clean candidate recorded authoritatively in the live
checkpoint below. Commit identity and source fingerprint are separate fields.
The pinned stage1 binary was not
replaced.
The latest isolated `@test`-fix candidate,
`nw-core/build/elisac-stage1-test-entrypoint-pinned`, has SHA-256
`a2fe74bccae7021ae53a8dcd4f874dfcfed807a560b8b0c5f597cd6078d50f17` and was
rebuilt from source fingerprint `6efafa99aa280e28be16d98bac4d91241c4bd519913ad9330dcce4fa4fc6e4a8`
with the provenance-pinned stage0. The previous v2 candidate
(`d02a3d0ded5ff9cf91a9046b8b878713d89a29c2094b09ec9039634d4c05dda2`) was
built with a local convenience alias and is superseded for this regression.
Neither candidate is the provenance-pinned stage1 product.

The latest compiler-source candidate,
`nw-core/build/elisac-stage1-qualified-generic-v6`, has SHA-256
`b3b8402b3bf9f95a2c2b45e3d363e25f631f8b2ccd39fc7136deba8fcc6f18b3` and was
seed-built with selected stage0 SHA-256
`c5efa8ce20f781f21817eabc0481efe79a2c895031f49ce64bbb72911386c183`. The
current compiler-worktree fingerprint is
`dc16f4827d19bb533286771e9ef3e3e8664ee5d8585db6e67c6db0404c7807d1`; the
runtime object used for its focused native regression has SHA-256
`d392af4d754340af0b22ed7a00f9db8e66efbc0ab9dac034ac5c30d1f819b663`.
The qualified-generic wrong-target regression and `pyset` (1,000 cases) pass
on v6. Candidate v5, built from the same compiler backend source before the
test fixture/harness expansion, passed 511/511 native backend checks and the
affected `pyset`, `maze`, `fogworld`, `numberology`, `inthedark`,
`crossedwires`, and `cookiethief` stage1 sweeps. The pinned stage1 binary and
provenance remain untouched; the full artifact suite and compiler gate remain
open.

Historical compiler evidence before the current Count slice: an earlier
stage0 module and isolated stage1 v13 artifact passed the then-configured
artifact suite. That result is superseded for current source by the fresh
Count-capable candidate comparison below. The compiler runtime drift guard
passed after syncing 15 stale vendored runtime files to the canonical stage0
runtime (33 guarded files matched). Historical stage1 work also fixed
qualified-export handling, the test-runner ABI, and wasm32 integer-width
lowering. Those focused results do not certify the pinned stage1 product or
full compiler gate. The `memset`/`memcmp` conflict belongs only to the
unselected convenience compiler/runtime pairing in COMP-008, not the port's
pinned toolchain.

## Historical optimized Stage1 artifact checkpoint — 2026-09-16

The active browser artifact was rebuilt through the newest local Stage1
checkout and a freshly reseeded Stage1 product. The build wrapper verified that no
`.elisa` or `.elisai` source was newer than the selected product and that the
checkout was not behind fetched `origin/main` before compiling the port at
`-O2`. The port-pinned Stage0 remains the parity oracle for the artifact
matrix; the latest compiler's Stage0 was used only to reseed the selected
Stage1 product.

| Item | Current identity |
| --- | --- |
| Elisa compiler HEAD | `main@def45115b1ef741e951d00fe1f65565de583dce5` (matches fetched remote) |
| Fetched `origin/main` | `def45115b1ef741e951d00fe1f65565de583dce5` (local is zero ahead/behind) |
| Compiler source fingerprint | `9de69658a554a61ac1679e3cd52398ea73800adf700fb0c51d7a636324dceef9` |
| External Stage1 product | `Elisa-compiler/bin/elisac-stage1`, freshness-checked current product, SHA-256 `c7e91519ede2c4ad1f018d5caebacf3488416fba6b7b38975f075525088faa10` |
| Active WASM | `build/nwcore.wasm`, 830,219 bytes, SHA-256 `380abe137dc339d2baf8acafb928ece3683f3993251a8522b49ed049dad50465` |
| Linked Stage1 object | `build/nwcore_wasm.o`, SHA-256 `2bba67a16185ed54d37a5da51a085c8b1ccdf4f3aa7633f33e11e08cc0d1367b` |

The current compiler checkout contains active compiler implementation fixes;
the freshness guard and source fingerprint make the exact input explicit. The
complete
configured artifact suite now passes against the Buzz Wire artifact:
421 differential cases, 720 session frames, 6 batch, 3 menu, 4 task-hub, 45
stateless task-frame cases, all twenty controller smokes, and the Marble
browser/physics/renderer/board/trajectory checks. The MuJoCo cleanup test logs
its simulated partial-cleanup error while passing the recovery assertion. The
Marble trajectory oracle is file-backed and has a 120-second timeout so the
macOS synchronous-child stdin-EOF edge case cannot hang the artifact gate;
the repaired run completed 110 scenarios and 12,492 per-frame comparisons.
The generated-board submatrix now uses a 120-frame deterministic tilt trace
for each of the 80 certified boards; controlled cases keep the tighter
limits, while generated traces use explicitly declared small native/WASM
numerical-drift limits and still require exact discrete events.
Direct targeted O0/O2/O3 runs pass for the fixtures that timed out during the
long host-contended sweep. The latest-product 159-fixture optimization parity
corpus and complete compiler gate remain separate open evidence items. Stage1
still reports 21 declined concurrency-runtime bodies, so the compiler gate is
not complete.

## Current Removals and Chain of Custody slice — 2026-09-16

The browser now has sixteen source-backed common-v1 controllers: the earlier
twelve plus Removals, Chain of Custody, N-Cup Monte, and Reflex. Removals uses
`src/tasks/removals_game.elisa` with the original Removals kernel and scene;
Chain of Custody uses `src/tasks/custody_game.elisa`, the original Custody
kernel, and `SceneCustody`. Both are registered in the 45-task catalog audit,
exported through `wasm_exports.elisa`, and reachable from the real Working
memory task hub.

The current artifact is `build/nwcore.wasm`, 665,630 bytes,
SHA-256 `9da59a582200b5c312fd8e890c9428a62fc73614f438273a28c1ebc200c7bd00`;
the linked object is SHA-256
`250b76bf3f9729aa6ba04c849adef675cbe0f969926a2d8ffcb6d541e275b8b5`. It was
emitted with the latest external Stage1 product at
`main@5329edfdbefa27b5c1c51253da0073256ed51058`, product SHA-256
`c4fe7e9c2012558aa2a37293aba3f92dbd1f78dbd005d571ffba42e9295e5173`, source
fingerprint `9de69658a554a61ac1679e3cd52398ea73800adf700fb0c51d7a636324dceef9`,
and the sibling Stage0 seed SHA-256
`529a48195a1892fdcc07cf9bc40fc798c9f497938bbbc4df87ece58767e000d7`.

Focused controller tests, browser module syntax, catalog audit, and
`git diff --check` pass. The complete configured artifact suite also passes.
Native/Python/SDL adapters, options persistence, original media/effects,
snapshots, and the remaining twenty-nine catalog-controller packets remain
open.

## Current N-Cup Monte slice — 2026-09-16

N-Cup Monte remains the fifteenth source-backed common-v1 browser controller;
Reflex is the sixteenth controller added in the later checkpoint below.
The stable task ID is `ncup_monte = 704181153`. Its implementation is split
between the source kernel in `src/tasks/ncupmonte.elisa`, the controller in
`src/tasks/ncupmonte_game.elisa`, and the existing source-shaped renderer in
`src/scene_ncupmonte.elisa`. The controller copies every arena-backed deal and
swap fact into fixed storage before the temporary region is destroyed; no
hidden answer, permutation, deadline, or score is supplied by JavaScript.

The controller follows the original `neural_workshop/ui/ncupmonte.py` rules:
the initial deal uses the persistent MT19937 stream, the visible reveal ends
at the exact configured deadline, and the shuffle plans
`max(1, swap_count + cups)` distinct slot pairs from the same stream. Each
pair uses the original smoothstep interpolation and only changes the slot
permutation at the exact swap boundary. The controller distinguishes a cup's
identity from its visual slot, maps pointer coordinates back through that
permutation, preserves the adaptive cup count between rounds, and emits the
source-shaped ready/reveal/guess/result messages. Browser defaults are
`(3, 8, 1, 6, 340, 1150)`; source cup numbers remain enabled because the
shared v1 options ABI currently has six slots.

Runtime v1 now validates all six N-Cup option domains, allocates the correct
task-specific `Run` size, maps Space/Enter and pointer selection, advances the
reveal/shuffle clock, serializes the common twelve-field state envelope,
exposes `nw_api_v1_ncup_monte_info` and `nw_api_v1_ncup_monte_value`, renders
through `SceneNCupMonte`, and destroys handles idempotently. The web shell
creates the run only for the real Games → Attention → N-Cup Monte route,
drives deadlines with `requestAnimationFrame`, and releases the run on task
replacement, category changes, exit, and replay.

Verification completed on the latest optimized artifact:

```text
node test/ncupmonte_game_smoke.mjs
PASS: N-Cup Monte source-backed deal, timed smooth swaps, identity mapping, pointer input, adaptive scoring, rendering, options, and cleanup
python3 test/catalog_audit.py
PASS: 45 stable task IDs; original, Elisa, and browser menus, kernel/scene anchors, controller/export map, and host capabilities match
./scripts/build_latest_stage1_wasm.sh
PASS: complete configured artifact suite, including all sixteen controller smokes and Marble browser/physics/renderer/board/trajectory checks
```

The active `build/nwcore.wasm` is now 665,630 bytes with SHA-256
`9da59a582200b5c312fd8e890c9428a62fc73614f438273a28c1ebc200c7bd00`; the
linked object is SHA-256
`250b76bf3f9729aa6ba04c849adef675cbe0f969926a2d8ffcb6d541e275b8b5`. Both
were emitted at `-O2` by the latest external Elisa Stage1 product
`c4fe7e9c2012558aa2a37293aba3f92dbd1f78dbd005d571ffba42e9295e5173` from
compiler `main@5329edfdbefa27b5c1c51253da0073256ed51058`, with source
fingerprint `9de69658a554a61ac1679e3cd52398ea73800adf700fb0c51d7a636324dceef9`.
The build still reports the known 21 declined concurrency-runtime bodies.

This closes only the N-Cup controller/browser slice. The source-specific
options UI and persistence, original audio/effects, native/Python/SDL hosts,
broader original-controller differential replay, snapshot/effects protocols,
and the remaining twenty-nine catalog-controller packets remain open.

## Current Reflex slice — 2026-09-16

Reflex is now the sixteenth source-backed common-v1 browser controller. This
section is the post-Reflex handoff record and supersedes the fifteen-controller
count in older dated entries without deleting those entries. It records what
is implemented, what was actually tested, and what remains before the game can
be called identical to the original.

### Reference contract

The frozen reference is the local checkout at
`/Users/torarinvikbjarko/Documents/Coding Projects/Python Projects/neural-workshop-enhanced BACKUP`.
The source files audited for this slice are:

- `neural_workshop/ui/reflex.py`: target placement, target lifetime, image
  selection, click handling, adaptive timing, result presentation, and the
  visible task clock;
- `nwenv/reflex.py`: action vocabulary and environment-level start/step
  boundary;
- `nw-core/src/tasks/reflex.elisa`: the existing source kernel, including the
  MT19937 stream, `above_the_band` placement helper, shrinking predicate, and
  adaptive lifetime rule; and
- `nw-core/src/scene_reflex.elisa`: the source-shaped display-list projection.

The source option domains are preserved rather than replaced by arbitrary
integer ranges:

| Option | Supported values in this slice | Browser default |
| --- | --- | --- |
| target count | 10, 20, 30, 40, 60, 80, 120, 200, 300, 500 | 40 |
| base lifetime | 400, 600, 800, 1200, 1600, 2200, 3000, 4000 ms | 1600 ms |
| spawn gap | 150, 250, 400, 550, 700, 1000, 1500, 2000 ms | 700 ms |
| maximum active targets | 1, 2, 3, 4, 5, 6, 8, 10, 12 | 3 |
| starting image size | 60, 80, 100, 130, 170, 220, 280 px | 130 px |
| adaptive timing | boolean | true |

The stable task ID is `reflex = 2070613823`, the FNV-1a ID returned by the
runtime. A run begins READY, enters RUNNING on Space/Enter, and reaches DONE
only after all configured targets have been spawned and the last active target
has either been hit or expired. The controller owns the score, hidden target
identity, target geometry, target timestamps, lifetime, verdict, and RNG
state. The browser owns only callback scheduling, canvas-to-reference
coordinate conversion, and the asset lookup.

### Source semantics preserved

The controller uses fixed-size WASM-owned storage for twelve simultaneously
active targets and five hundred reaction samples. Each target has an immutable
identity, normalized X/Y coordinates, birth timestamp, target-specific
lifetime, and deterministic asset ID. Removing an expired or hit target shifts
the remaining records within WASM storage; no browser-side array index is used
as an identity.

Placement follows the reference coordinate system of 912 × 684 logical pixels.
The target side is scaled from the reference height and clamped to the source
minimum. X is sampled between the half-side margins. Y begins above the source
band and is capped below the top margin, so a resize changes presentation
geometry but not the random target coordinates or identity. The target starts
at its full side and shrinks continuously. The exact source `is_gone` boundary
is used for expiry, including the equality case at the lifetime deadline.

A pointer hit tests current target geometry and resolves overlapping targets by
the smallest current side, matching the source's visible-target preference.
An accepted hit records reaction time from the controller clock, increments
hits, stores the reaction sample, sets the source verdict, removes only the
selected identity, and applies the adaptive success update. An empty click is
ignored by the runtime pointer path; expiry increments misses and applies the
adaptive miss update. Accuracy and mean reaction time use the source rounding
behavior rather than JavaScript floating-point display calculations.

Adaptive timing is kept in the controller as a floating-point lifetime and is
reset to the configured base at each new run. Success and miss updates use the
source `Reflex::adapt` behavior and are bounded by the base-lifetime-derived
limits. A new spawn clears the previous transient verdict, so a result label
cannot survive into the next visible target unless the source permits it.

### Delivered files and ownership boundaries

`src/tasks/reflex_game.elisa` is the long-lived controller. Its `Run` record
contains validated options, persistent MT19937 state, target arrays, reaction
samples, deadlines, score, phase, and result fields. No target answer,
reaction score, or adaptive decision is reconstructed in JavaScript.

`src/wasm/runtime_protocol.elisa` adds the Reflex task ID, option validation,
run allocation size, creation, action, advance, pointer, read-state,
render, accessor, support, task-ID, and destruction branches. The common state
envelope maps phase, target totals, spawn count, active limit, hits, misses,
accuracy, mean reaction time, active count, current lifetime, adaptive flag,
and next-spawn deadline. The task-specific info fields are numbered and
documented in `docs/runtime-protocol.md`; the value fields expose identity,
position, birth time, lifetime, remaining fraction, and asset ID.

`src/wasm/wasm_exports.elisa` includes the Reflex kernel/controller/scene and
exports `nw_api_v1_task_reflex`, `nw_api_v1_reflex_info`, and
`nw_api_v1_reflex_value`. The required-export guard in the browser rejects a
stale artifact that lacks any of these symbols.

`shells/web/index.html` registers deterministic browser asset IDs 3000–3063,
creates the source-default run only on the real Games → Attention → Reflex
route, starts it from Space/Enter, advances it with `requestAnimationFrame`,
forwards physical canvas pointer coordinates to WASM, draws the source-shaped
display list, and destroys the handle on task replacement, category change,
screen change, replay, and exit. The generated asset tiles are an explicit
temporary compatibility layer: they keep asset identity deterministic while
the original filesystem-backed media pool is still being integrated.

`test/fixtures/task_catalog.json` records the controller, kernel, scene,
exports, and browser-only capability status. Native, Python, and SDL3 are
intentionally marked not integrated; catalog presence is not being mistaken
for cross-shell completion.

### Verification completed

The focused controller smoke currently covers:

1. stable ID, support discovery, and all option domains;
2. the exact common state envelope and READY values;
3. deterministic initialization for equal seeds and divergence for different
   seeds;
4. Space versus typed START equivalence;
5. the first target's source-derived identity, position, lifetime, and asset;
6. source target shrinkage before expiry and exact-deadline expiry;
7. pointer misses, pointer hits, overlapping-target preference, and identity
   removal;
8. adaptive lifetime promotion after a hit and reduction after a miss;
9. accuracy, mean reaction time, presented count, verdict, and DONE lifecycle;
10. source-shaped rendering with an asset command and live status text; and
11. idempotent destruction plus invalid-handle behavior.

The current optimized artifact command completed with:

```text
stage1 wasm: 665630 bytes
PASS: 421 cases identical
PASS: 720 session frame cases identical
PASS: 6 batch ABI cases validated
PASS: 3 menu ABI cases validated
PASS: 4 task hub ABI cases validated
PASS: 45 stateless task-frame ABI cases
PASS: all sixteen stateful controller smokes
PASS: Reflex source-backed target lifecycle, shrinking threshold, pointer scoring, rendering, options, and cleanup
PASS: common WASM runtime API v1
PASS: Marble browser, renderer, MuJoCo, board, and 110-scenario trajectory checks
```

The headed browser path was exercised at
`http://127.0.0.1:8000/shells/web/index.html` through Games → Attention →
Reflex → Enter → Space. The page progressed from READY to RUNNING, rendered
multiple live target sprites, accepted a real canvas pointer click, and
reported zero console errors and zero warnings. The inline module passed
`node --check --input-type=module`; `python3 test/catalog_audit.py` and
`git diff --check` also passed.

### Latest Elisa compiler provenance

The WASM rebuild used the latest local Elisa compiler checkout and the freshly
isolated Stage1 product, not the stale port-pinned Stage1 merely because it is
already present in the repository:

| Input | Identity |
| --- | --- |
| Elisa source checkout | `Elisa-compiler`, clean `main@5329edfdbefa27b5c1c51253da0073256ed51058` |
| fetched remote | `origin/main@45cb0ded70e7e8c8a41d21c63a09939706322ca4`; local is 11 ahead and 0 behind |
| compiler source fingerprint | `9de69658a554a61ac1679e3cd52398ea73800adf700fb0c51d7a636324dceef9` |
| selected Stage1 | `build/stage1-from-current-stage0-20260916` |
| Stage1 product SHA-256 | `c4fe7e9c2012558aa2a37293aba3f92dbd1f78dbd005d571ffba42e9295e5173` |
| reseed Stage0 SHA-256 | `529a48195a1892fdcc07cf9bc40fc798c9f497938bbbc4df87ece58767e000d7` |
| compile flags | `-emit obj -O2 -target-triple wasm32-unknown-wasi` |
| linked WASM | `9da59a582200b5c312fd8e890c9428a62fc73614f438273a28c1ebc200c7bd00`, 665,630 bytes |
| linked object | `250b76bf3f9729aa6ba04c849adef675cbe0f969926a2d8ffcb6d541e275b8b5` |

The wrapper checks the compiler checkout, fetched remote relationship, source
fingerprint, and source mtimes before compiling. The port-pinned Stage0 still
cannot parse the current Stage1 parser sources during direct reseeding, so it
was not promoted. The selected latest product is the reproducible production
input. The build still reports the known 21 declined concurrency-runtime
bodies; this is recorded compiler evidence, not hidden or reclassified as a
successful full compiler gate.

### Remaining Reflex work, in implementation order

The browser controller slice is green, but the original-fidelity task is not
closed. The next agent should address these items in order:

1. Integrate the original media pool and image bytes. Preserve the controller's
   asset identity mapping, verify dimensions/alpha/color space, and compare
   decoded image bounds against the reference before changing the renderer.
2. Add a source differential runner that feeds identical seeds, options, clock
   timestamps, pointer coordinates, and resize events to Python and WASM. It
   must compare every spawned target, normalized position, target lifetime,
   remaining fraction, active identity set, hit/miss result, reaction samples,
   adaptive lifetime, verdict, and final phase.
3. Cover seeds `0`, `1`, `17`, `314159`, and a high valid seed; every supported
   option class; total targets below/at/above the active limit; lifetime equal
   to spawn gap; and the maximum active target count. Include a run with all
   five hundred targets to expose sample-buffer and long-run drift.
4. Test pointer boundaries at the exact target edge, center, corner, overlap,
   outside region, and exact expiry timestamp. Separate logical reference
   coordinates from CSS pixels, device-pixel ratio, scroll offset, and browser
   zoom so resize cannot change hit identity.
5. Add resize-during-target-life, resize-during-overlap, focus loss,
   visibility pause, task replacement, and rapid exit/reopen tests. Prove that
   late animation callbacks cannot advance a destroyed handle or mutate a new
   run. Record handle/timer counts over at least 100 cycles.
6. Add the source options screen and persistence. Changing an option must
   destroy the previous run before creating the new one; old stored option
   records must migrate or fail explicitly, never silently fall back to a
   different target count.
7. Integrate original sound/effect events with stable IDs, exactly-once
   draining, cancellation on run generation, and focus-safe cleanup. Do not
   let effects become a second source of gameplay state.
8. Implement native, Python, and SDL3 adapters with native-width handles and
   the same semantic event/timestamp trace. The adapters must call the shared
   controller contract rather than duplicate scoring or target expiry.
9. Add O0/O1/O2/O3 optimization parity for Reflex using the latest compiler
   product, comparing common state, task-specific info/value traces, display
   bytes, and lifecycle outcomes. Review any warning-count or optimization
   change before accepting it.
10. Only then mark GAME-010 complete. The completion packet must include source
    revision, compiler provenance, original-media hashes, options migration,
    browser screenshots, differential traces, focus/resize/resource evidence,
    non-browser replay evidence, and the final artifact hash.

## Current Moving Targets slice — 2026-09-16

Moving Targets is now the seventeenth source-backed common-v1 browser
controller. This section records the current implementation and evidence; it
does not claim source-identical media, non-browser support, or closure of
GAME-011. The stable task ID is `moving_targets = 228173702`.

The reference contract was audited in the frozen Python checkout across
`neural_workshop/ui/tracking.py` and `nwenv/tracking.py`, then matched to the
portable `src/tasks/tracking.elisa` generator/motion helpers and
`src/scene_tracking.elisa` display projection. The controller preserves the
source option domains: balls 3/4/5/6/8/10/12/15/20/25/30; requested targets
1/2/3/4/5/6/8/10/12/15 clamped below the ball count; tracking seconds
3/5/8/10/15/20/30/45/60; speed 8/12/16/22/30/40/55/75 percent; rounds
3/5/8/10/15/20/30/50; and adaptive 0/1. The browser default is
`(8, 2, 8, 16, 5, 1)` with seed 17.

`src/tasks/tracking_game.elisa` owns a persistent MT19937 stream, fixed arrays
for thirty ball positions/velocities/target flags/picked flags, the phase
clock, score, round totals, and adaptive target count. Each round calls the
source `Tracking::deal_round` once and copies its temporary flock into the
long-lived record. Movement calls the source `Tracking::bounced` helper. The
phases are READY, CUEING, TRACKING, PICKING, REVEALING, and DONE. Cueing is a
fixed two seconds; tracking ends at the exact configured deadline; selecting
all requested target identities scores immediately; reveal lasts 1.8 seconds;
and the next round or DONE transition occurs only at that deadline. Pointer
selection is identity-based and happens in WASM, so JavaScript cannot
manufacture a catch by list index.

The common read-state envelope contains phase, round, total rounds, ball count,
asked, tracked, total caught, total asked, picked, caught, verdict, and
deadline. `nw_api_v1_tracking_info` fields `0..18` expose source options,
phase/counter values, and the controller clock. `nw_api_v1_tracking_value`
fields `0..6` expose stable ball identity, normalized position, velocity,
target flag, and picked flag. `runtime_protocol.elisa` and
`wasm_exports.elisa` cover validation, create/dispatch/advance/read/render/
destroy, keyboard mapping, pointer dispatch, support discovery, task ID, and
the two task-specific accessors. Snapshot/effects and native/Python/SDL3
adapters remain open.

The browser route is Games → Attention → Moving Targets. It creates a common
handle only for that route, starts with Space/Enter, advances only in phases
with an active deadline, forwards pointer coordinates during PICKING, and
destroys the run on task/category/screen/replay/exit replacement. A lifecycle
fix in `taskClick` reschedules the reveal clock after the final pointer pick;
without that callback the controller correctly entered REVEALING but the
browser would remain visually stuck. The browser keeps no second ball list,
hidden target set, score, random stream, or adaptive state.

Focused verification passed:

1. `node test/tracking_game_smoke.mjs` covers stable ID, option validation,
   deterministic deals, cue/tracking boundaries, bounce identity, pointer
   picks, adaptive success/miss, multi-round completion, rendering, and
   cleanup.
2. `python3 test/catalog_audit.py`, extracted browser-module
   `node --check --input-type=module`, and `git diff --check` pass.
3. `./scripts/build_latest_stage1_wasm.sh` completed the full configured gate:
   421 differential cases, 720 session frames, 6 batch, 3 menu, 4 task-hub,
   45 stateless task-frame cases, all seventeen controller smokes, the common
   runtime suite, and Marble browser/renderer/MuJoCo/board/trajectory checks.
4. A headed Playwright replay completed the real Games → Attention → Moving
   Targets → Enter → Space route. It observed CUEING, TRACKING, and PICKING,
   clicked both controller-reported target centers, observed REVEALING with
   `caught=2/2`, and then observed round 2 after the reveal deadline. The
   browser console contained zero errors and zero warnings. The visual
   checkpoints are `output/playwright/moving-targets-cue-live3.png` and
   `output/playwright/moving-targets-picking-live.png`.

The current optimized artifact is `build/nwcore.wasm`, 678,675 bytes,
SHA-256 `dfb9bd6ac82b158a153e7ba6053ad9a76b5b3b8a118c93b67d8d396b0ca50c94`;
the linked object is SHA-256
`2e26716976e5f1f1f35aa52292882de952ac3b6d9cc14546701716bbb9b5cf53`. It was
emitted with the latest local Elisa Stage1 product
`c4fe7e9c2012558aa2a37293aba3f92dbd1f78dbd005d571ffba42e9295e5173` from
clean compiler `main@5329edfdbefa27b5c1c51253da0073256ed51058`, source
fingerprint `9de69658a554a61ac1679e3cd52398ea73800adf700fb0c51d7a636324dceef9`,
reseeded with Stage0 SHA-256
`529a48195a1892fdcc07cf9bc40fc798c9f497938bbbc4df87ece58767e000d7` and
compiled with `-emit obj -O2 -target-triple wasm32-unknown-wasi`. The known 21
declined concurrency-runtime bodies remain explicit compiler-gate evidence.

The remaining Moving Targets work is: Python/WASM differential traces across
all option classes and deadline boundaries; exact aspect/resize/DPR/zoom and
pointer-edge parity; pause/focus/visibility policy; 100-cycle callback and
handle cleanup evidence; source options persistence; original media/effects;
native/Python/SDL3 adapters; O0/O1/O2/O3 parity with this latest product; and
the final source/media/compiler evidence packet. The current slice is
implemented and tested, but the fidelity task is still open.

## Current Lookout slice — 2026-09-16

Lookout is the eighteenth source-backed common-v1 browser controller. Its stable
task ID is `3096915418` (`lookout`). The audited source defaults are eight
shapes, colour watching, 16-percent speed, a 2,000 ms morph gap, ten cues, and
adaptive shape count. The six ABI slots are shape count
`3,4,5,6,8,10,12,15,20,25,30`; watching mode `0=color, 1=form, 2=both`;
speed `8,12,16,22,30,40,55,75`; morph gap `800,1200,2000,3000,5000,8000`
ms; cues `5,10,15,20,30,50`; and adaptive `0/1`.

`src/tasks/lookout_game.elisa` is a fixed-storage ABI adapter around the
portable `Lookout` kernel. It materializes the kernel's arena-backed run and
flock only inside a temporary region and copies every scalar, score, timestamp,
and flock array back before leaving. It preserves the source's non-rewinding
layout relaxation, 24-candidate shuffled minimum-coverage cue dealer, absent
cue clearing, 70-percent colour morph branch, six-second drought-forced match,
100 ms update clamp, immediate-return miss ordering, signal-detection scoring,
1.4-second feedback gate, and adaptive 3..30 shape count. It captures
`seen_at` before the source answer call clears seen markers, so delayed hit
reaction times remain correct.

The common state envelope is phase, cue number, total cues, live shape count,
watching mode, hits, misses, false alarms, reaction count, verdict, feedback
deadline, and controller clock. `nw_api_v1_lookout_info` fields `0..20` expose
source options, cue identity, score, mean and last reaction, deadlines, and
shape count. `nw_api_v1_lookout_value` fields `0..6` expose normalized position,
velocity, colour, form, and next-morph timestamp. `F` and `J` map to FORM and
COLOR; Space/Enter map to START only in READY/DONE. `SceneLookout` remains the
sole display projection and renders the source footer, live cue glyph, flock,
verdict, and feedback message.

The browser route is Games → Attention → Lookout. It creates one handle with
`(8,0,16,2000,10,1)` and seed 17, schedules animation only in WATCHING or
FEEDBACK, and destroys/cancels it on task replacement, screen exit, and replay.
The browser owns no cue, flock, score, reaction time, RNG, or adaptive state.

Focused verification passed:

1. `node test/lookout_game_smoke.mjs` covers support, all option domains,
   deterministic Space/action parity, absent cue, live match, delayed hit and
   reaction timing, adaptive promotion, false alarm, miss, render, and cleanup.
2. `./scripts/test_wasm_artifact.sh` passes 421 differential cases, 720 session
   frames, 6 batch, 3 menu, 4 task-hub, 45 stateless cases, all eighteen
   controller smokes, common runtime checks, and the Marble suite.
3. Headed Playwright completed Games → Attention → Lookout → Enter → Space,
   observed WATCHING with cue 1/10 and eight shapes, accepted `J`, and reached
   FEEDBACK with zero console errors and warnings.

The current optimized artifact is `build/nwcore.wasm`, 703,291 bytes,
SHA-256 `7228fd461868e41f0aed7f499f419be8925a49dc29299cabfd3ac018958867d0`;
the linked object is SHA-256
`de9fe5f9c711e9d5c403617c02cc71904be0f5599bf3796c8947939d3454f9fe`. Both
were emitted with the latest local Elisa Stage1 product
`c4fe7e9c2012558aa2a37293aba3f92dbd1f78dbd005d571ffba42e9295e5173` from clean
`main@5329edfdbefa27b5c1c51253da0073256ed51058`, source fingerprint
`9de69658a554a61ac1679e3cd52398ea73800adf700fb0c51d7a636324dceef9`, sibling
Stage0 SHA-256
`529a48195a1892fdcc07cf9bc40fc798c9f497938bbbc4df87ece58767e000d7`, and
`-O2 -target-triple wasm32-unknown-wasi`. The known 21 declined
concurrency-runtime bodies remain an explicit compiler-gate warning.

Remaining Lookout evidence is the full Python/WASM differential corpus,
three-mode browser parity, source options persistence, focus/visibility/resize
policy, effects, native/Python/SDL adapters, and O0/O1/O2/O3 parity with the
latest compiler product. GAME-013 remains open.

## Current Pursuit slice — 2026-09-16

Pursuit is the nineteenth source-backed common-v1 browser controller. Its
stable ID is `pursuit`; its unsigned FNV-1a task ID is `250940285`. The
reference contract was audited in
`original-neural-workshop-enhanced/neural_workshop/ui/pursuit.py`, its
`configdefaults.py` and `taskoptions.py` entries, the portable kernel
`nw-core/src/tasks/pursuit.elisa`, and `nw-core/src/scene_pursuit.elisa`.
The adapter is in `nw-core/src/tasks/pursuit_game.elisa`.

The six common option slots are source-derived and are validated before any
RNG draw:

| Slot | Domain | Meaning |
| ---: | --- | --- |
| `a` | `4,6,8,10,12,14,16,18,20,25,30,35,40,50,60,75,90` | quarry speed percentage |
| `b` | `0,20,40,60,80,100,150,200,300` | surge percentage |
| `c` | `200,300,400,600,900,1200,1600,2200,3000,5000` | turn interval in milliseconds |
| `d` | `30,45,60,90,120,150,180` | turn magnitude in degrees |
| `e` | `10,13,16,19,22,26,31,38,46,60` | base quarry radius |
| `f` | packed integer `0..6271` | wobble, morph interval, duration, rounds, and adaptive flag |

The packed `f` field is not a free-form bit bag. Its mixed-radix encoding is
`wobble + 7 * morph + 49 * seconds + 343 * (rounds - 1) + 2744 * adaptive`,
where wobble and morph indices are `0..6`, seconds index `0..7` maps to
`10,15,20,30,45,60,90,120`, rounds index `0..7` maps to `1,2,3,5,8,10,15,20`,
and adaptive is `0/1`. The source-compatible default is
`f=4049`: 40% wobble, a 2,000 ms morph interval, 20 seconds per round, 5
rounds, and adaptive difficulty. The browser route uses
`(18,60,900,120,22,4049)` with seed 17.

The controller preserves the source's meaningful ownership boundaries:

- `Pursuit::Run` and its arena-backed quarry are materialized in a temporary
  region for source operations and copied into fixed controller storage before
  the export returns; no arena pointer escapes into the durable ABI record.
- Quarry position and heading use the source's normalized/fractional model;
  `value` reports position in parts per million, while the scene converts that
  model to the source 912×684 reference viewport. Pointer input is converted
  from normalized browser coordinates to source pixels before the source hit
  test, including the source aspect correction.
- `advance` clamps elapsed time to the source 100 ms maximum, processes due
  turn/surge/resize/morph deadlines in source order, and keeps the continuous
  score, on-target time, off-target samples, mean off-target duration, and
  adaptive multiplier in the controller rather than in JavaScript.
- Result fields use the separate value namespace `100..102` for share ppm,
  drift pixels, and multiplier ppm. This avoids colliding with quarry value
  fields `0..10`, an ABI mistake that the focused smoke caught and fixed.
- `ScenePursuit` is the only display projection. It renders the source title,
  round/status line, target/quarry geometry, continuous score, footer, verdict,
  and feedback; rendering does not advance time, select input, or consume RNG.

The common actions are `START=0`, `UP=1`, `DOWN=2`, `LEFT=3`, and `RIGHT=4`.
Space/Enter start READY or DONE; source-compatible arrow nudges and normalized
pointer updates may update the cursor outside CHASING, but only CHASING samples
and scores it. The common state envelope records phase, round,
total rounds, speed, result count, on-target percentage, run time, off-target
sample count, verdict, multiplier, feedback deadline, and controller clock.
The task-specific info/value/result accessors expose the source options,
quarry state, sampled results, and final summary without making the shell a
second authority.

The browser route is Games → Attention → Pursuit. It requires the three
Pursuit exports before accepting the module, reads the stable task ID from
WASM, creates the default six-slot run, maps Space/Enter/arrows/pointer to the
common action path, schedules animation only during CHASING or FEEDBACK, and
destroys the handle/cancels callbacks when the route changes. A headed
Playwright replay reached READY, started with Enter then Space, rendered the
live quarry, and advanced one right-arrow action; the captured visual is
`output/playwright/pursuit-live.png` and the route reported no console errors
or warnings.

Focused evidence is `test/pursuit_game_smoke.mjs`. It covers stable ID and
support discovery, every direct option domain, every valid packed `f` value
class, malformed option rejection, deterministic Space/action behavior,
quarry motion, continuous scoring, pointer and keyboard controls, feedback,
DONE, result accessors, source-shaped rendering, and idempotent destruction.
The complete `scripts/test_wasm_artifact.sh` run on this slice passes 421
differential cases, 720 session frames, 6 batch, 3 menu, 4 task-hub, 45
stateless task-frame cases, all nineteen controller smokes, common runtime
checks, and the Marble browser/physics/renderer/board/trajectory suite. The
MuJoCo partial-cleanup message is an intentional recovery-test log, not a
failure.

The authoritative optimized artifact for this checkpoint is
`build/nwcore.wasm`, 720,382 bytes, SHA-256
`9610c7d9d3f1a548c87ac7ac88803ede0050d584b9f5629d013c87af3c011a41`; its
linked object is SHA-256
`40581dce9aff81ffa8d335573db1e3495561697c614605e3a58ec947dea455c5`. It was
emitted with `-emit obj -O2 -target-triple wasm32-unknown-wasi` by the latest
local Elisa checkout `main@825bb8398020c755007a2d989b7ffeb18e3e3d5f`, which is
18 commits ahead and zero behind `origin/main@45cb0ded70e7e8c8a41d21c63a09939706322ca4`.
The canonical Stage1 product is
`Elisa-compiler/bin/elisac-stage1`, SHA-256
`5560548da3b2a57c4ee55b56096909e96ebdfcc1448f8f3c7396b8c81ffc8999`; the
isolated seed product is
`Elisa-compiler/build/stage1-from-current-stage0-20260916-825bb839`, SHA-256
`764cb48eede340073fed59c9cc6fe39aae9da5a416a8c8cb796f3338d736ce38`.
The final wrapper observed compiler source fingerprint
`a9b984be8173d02d78586415f6a365ee5c348f1adb66d052fed9ab1572481047` and
the newer sibling Stage0 seed executable was SHA-256
`5dcaf4d2b91396965b3af888d7d36d0480c7b8e65d5f3f746994060e66115275`.

Pursuit remains a browser/common-v1 slice, not a completed original-fidelity
port. Remaining work is: differential replay against Python across every
packed configuration and seed; exact deadline, pointer-edge, aspect-ratio,
resize, focus, and background-tab policy; source options UI and persistence;
original visual/effect assets; native/Python/SDL adapters; snapshot/effect
transport; O0/O1/O2/O3 parity with the latest compiler; and the full compiler
gate, including the known 21 declined concurrency-runtime bodies.

## Reference runtime and declared dependencies

- Active `python3`: 3.9.6.
- Active Node.js: 26.8.2.
- Installed Python packages inspected: NumPy 2.0.2 and pyglet 2.1.16.
- `python-chess` and Python `mujoco` are not installed in this interpreter.
- Reference `requirements.txt` declares `pyglet>=2`, `python-chess>=1.999`,
  and `mujoco>=3.2`; `pyarrow>=14` is explicitly optional for a text-generation
  utility, not required to play.

The absence of those two Python dependencies is a reproducibility gap for
reference UI/engine runs, not evidence that their behavior is unnecessary. The
browser's vendored MuJoCo JS/WASM is a separate runtime and its artifact-level
tests do not certify the original Python MuJoCo version. Record actual package
versions before claiming native physics parity.

## Current tested scope

### Current Numberology slice and latest compiler evidence (2026-09-16)

The active browser artifact is `nw-core/build/nwcore.wasm`, 554,011 bytes,
SHA-256 `60e62ea897749f5eaeddcbcc2b1816def0bccb82dabb4eb70eb1f0a779468105`.
It was emitted at `-O2` by `scripts/build_latest_stage1_wasm.sh` from the
selected sibling Elisa compiler checkout `main@5329edfdbefa27b5c1c51253da0073256ed51058`.
That checkout is eleven commits ahead and zero commits behind fetched
`origin/main@45cb0ded70e7e8c8a41d21c63a09939706322ca4`; its current source
fingerprint is `9de69658a554a61ac1679e3cd52398ea73800adf700fb0c51d7a636324dceef9`,
and the isolated latest Stage1 product used to build the artifact has
SHA-256 `c4fe7e9c2012558aa2a37293aba3f92dbd1f78dbd005d571ffba42e9295e5173`.
The checkout is clean. The pinned Stage0 cannot currently reseed this source
tree because it rejects newer parser syntax; the failed atomic attempt did not
replace the product.

Numberology is the eighth stateful browser controller. The source-backed
`NumberologyGame` owns the generated sequence, signed typed-answer buffer,
grading, adaptive session result, explanation fields, and `SceneNumberology`
display list. `node test/numberology_game_smoke.mjs` passes against the active
artifact, covering stable ID, source option validation, deterministic generated
terms, text input, Enter grading, judged-to-next progression, adaptive session
state, explanation/read-only accessors, display-list rendering, and idempotent
destroy. A headed browser route also passes Games → Reasoning → Numberology →
Space → typed answer → Enter with zero console errors or warnings.

The complete configured artifact suite passes with this artifact, including
421 differential cases, 720 session frames, batch/menu/task-hub ABI checks, 45
stateless task frames, all current stateful-controller smokes, and the Marble
Maze board/trajectory/renderer/MuJoCo checks. This remains targeted port
evidence: the compiler backend still reports 21 declined concurrency-runtime
bodies, and the full compiler gate, Python/SDL adapters, source-derived
options/result/replay acceptance, and unimplemented catalog controllers remain
open.

### Current Count slice and fresh compiler evidence (2026-09-14)

The current source has six common-v1 lifecycle controllers: Monkey Ladder,
Sokoban, Count, Marble Maze, Tower of Hanoi, and Maze. The latest additions
include deterministic source-backed Maze generation, typed movement, exact
shortest-path grading, and the existing Maze scene, while Count retains its
deterministic shape generation, typed numeric input, exposure/feedback
deadlines, and adaptive scoring.
`python3 test/catalog_audit.py` passes with all 45 stable task IDs; the audited
source mapping now classifies 39 browser cards as stateless frames and six
tasks as stateful controllers (Monkey Ladder, Sokoban, Count, Marble Maze,
Tower of Hanoi, Maze).
The dedicated `counting_game_smoke.mjs` passes against the isolated stage0
candidate `build/nwcore-count-stage0.wasm`, covering options, generated shape
rendering, text input, grading, exposure, dense layouts, completion, replay,
and destroy.

The stage0 Marble mismatch is now resolved at the compiler source. For wasm32,
the unsuffixed limit `9223372036854775806` was treated as 32-bit `int` instead
of inheriting the mutable field's `i64` type. Stage0 emitted `-2` in the
comparison, so the overflow guard reset `boardGeneration` to 1. Comparison
analysis now contextually types an unsuffixed integer literal from the opposite
integral operand. The new wasm32 stage0/stage1 IR smoke verifies the exact
positive bound, and both isolated stage0 `-O1` and default `-O2` artifacts pass
the complete configured suite, including the expected second-tray generation
2. Details and hashes are in COMP-011. The pinned compiler binaries remain
unchanged; the full compiler gate and toolchain provenance refresh remain open.

The current stage1 compiler source rejected the Count controller because
semantic field-type inference keyed struct fields by bare name, resolving
`CountingGame.Run.answer: i64` to another module's same-named
`Run.answer: darray[i64]`. `resolve_types.elisa` now selects field rows by
declaring module, with conservative handling for ambiguous external bare type
names. The added
`worktrees/elisa-compiler-nw/test/parity/module_struct_field_type_collision_smoke.sh`
reproduces the old false type error on the earlier candidate and passes with the
fresh isolated compiler; stage0 and stage1 both return 42. The compiler source
fingerprint is `af2d1a692f01f88e54e538d28690997c7896f5fbc31bd176c8fa25db571aa762`,
and the compiler candidate SHA-256 is
`1e069595cd94567fced5553e108408375992bdde16ad6ea8c61fea217c8ba660`.
The pinned stage1 product and provenance remain untouched.

The Count-capable stage1 artifact has SHA-256
`0104146f666d46500928ff26ad3ff12370ab33dbc1c1a6161a32b4e8d9850764` and
passes `bash scripts/test_wasm_artifact.sh
build/nwcore-count-stage1-field-type-v2.wasm`: 421 differential cases, 720
session frames, 6 batch, 3 menu, 4 task-hub, 45 stateless task-frame cases,
Monkey Ladder, Sokoban, Count, common-v1, Marble browser/physics/MuJoCo, and
board ABI checks. The candidate is 941,322 bytes; the build still reports 21
declined concurrency bodies, which remain outside this artifact's imported API.

Headed Playwright against an isolated server root also verifies the current
Count menu/start/input path: Games → Perception → Count, Space starts, the first
round is answered with `8`, the WASM file returns HTTP 200, and status advances
to trial 2/15 with one correct answer. Browser console: zero errors and zero
warnings. Screenshot: `nw-core/output/playwright/count-stage1-trial2.png`.

The default `build/nwcore.wasm` has now been rebuilt from current source with
the isolated fixed stage0 compiler. It is 406,315 bytes (SHA-256
`223b0ea90cb57ccaeaeb9d05c0d1aa7f2d472afa5c235537971ea4d44a0b8847`) and
exports both `nw_api_v1_task_marble_maze` and `nw_api_v1_task_count`. Before
this rebuild, the stale 386,875-byte artifact lacked those exports and caused
a top-level exception before the first draw, leaving `loading…` visible. The
shell's API/export guard remains to diagnose stale or mismatched binaries.
Headed Playwright against `http://127.0.0.1:8000/shells/web/index.html`
confirmed the title screen renders, Games opens, and Space starts the selected
activity; the status advances to trial 1 rather than remaining blank/loading.

Count still lacks a source-derived options screen, full 15-trial
result/replay acceptance, Python/SDL adapters, and full comparison against the
frozen original. The page fetches the rebuilt default `build/nwcore.wasm`; the
separate Count-capable stage1 artifact remains isolated and did not replace it.

Historical pre-Count result: from `nw-core/`, an earlier rebuilt stage0 module passed
`bash scripts/test_wasm_artifact.sh build/nwcore.wasm`: 421 differential cases,
720 session frames, batch/menu/task-hub ABI checks, 45 stateless task frames,
both controller replays, common API v1 contract tests, and the configured
Marble Maze browser/physics/board ABI checks. An isolated v13 stage1 candidate
also built the updated source into a separate 877,952-byte artifact and passed
the same configured suite, now including the Marble lifecycle-controller
transitions. The provenance-pinned stage1 product remains unchanged and stale;
it did not build this artifact. These are targeted results, not the complete
gate or release matrix.

The isolated stage1 candidate also closes a newly reproduced qualified-generic
wrong-target bug at the focused regression level. The regression fails on the
pre-fix candidate (stage0 returns 168; stage1 returns 140) and passes on the
candidate recorded above. In addition to `pyset` (1,000 cases), the same
backend-source change passed the previously crashing/overrunning `maze` (428),
`fogworld` (498), `numberology` (261), `inthedark` (106), `crossedwires`
(1,546), and `cookiethief` (137) stage1 sweeps. A preceding candidate passed
the stage1 native backend smoke (511/511). This is strong targeted evidence,
not a full stage1 artifact build or full compiler-gate result.

The schema-v2 catalog fixture joins all 45 stable IDs to the kernel/scene
anchors in `IMPLEMENTATION_PLAN.md` and to audited controller/export/host
coverage. The current source catalog has 36 stateless browser task-frame cards
and nine stateful web lifecycle controllers (Monkey Ladder, Sokoban, Count,
Marble Maze, Tower of Hanoi, Maze, N-in-a-row, Numberology, and In the Dark)
using common WASM API v1. Marble's MuJoCo physics and custom
3D canvas renderer remain browser-host services; its common display-list render
operation is explicitly unsupported. This controller slice does not establish
complete Marble gameplay or original 3D parity. Python and SDL3 do not yet
integrate a catalog-game controller. The scoped 3D N-Back task's separate
session/batch paths do not yet convert its task-hub card into a stateful
catalog-game controller; non-3D N-Back paths are explicitly outside the port.
`catalog_audit.py` checks all of these mappings and fails when an anchor,
controller module, WASM export, or host support value is stale or missing.

Official differential runs share the per-user `TMPDIR` checker lock across
worktrees because five suites still use fixed `/tmp/nw_*` exchange files.
`check_harness_test.sh` verifies that two separate build roots can concurrently
request the fixed-oracle expressions suite without overwriting fixtures or
result files.

BASE-001 and CAT-001 are inventoried/audited; TEST-001 through TEST-003 have
dedicated regressions. The source/binary provenance mismatch described above
remains unresolved. API-001, most controller implementations, cross-shell
integration, Marble Maze source-engine certification, the full gate, desktop
packaging, and release evidence remain open. See `IMPLEMENTATION_PLAN.md` for
the per-task acceptance criteria; do not infer complete gameplay from a menu
card, stateless frame, or artifact smoke.

## Latest compiler-candidate update — 2026-09-14

Stage1 candidate `nw-core/build/elisac-stage1-wasm32-fixes-v12` was built
without changing the provenance-pinned executables or
`nw-core/toolchain/PROVENANCE`. Candidate SHA-256 is
`a7a9810f578533aacd7acac03470f972e5e42a575ec2a2c1a93a150bcd6f00c4`; its
source fingerprint is
`ee7f8bf59c5e560cd7b0eb78e75159c98f5a80c8d347152239368505f57db795`. It was
seeded using pinned stage0 SHA-256
`c5efa8ce20f781f21817eabc0481efe79a2c895031f49ce64bbb72911386c183` and the
selected runtime object remains
`d392af4d754340af0b22ed7a00f9db8e66efbc0ab9dac034ac5c30d1f819b663`.

The stage1 Glyphs compile-RSS regression is fixed for this candidate. Direct
construction into hidden `sret` storage avoids LLVM aggregate load/store
expansion; the import-only Glyphs O2 compile now completes in 0.29 seconds at
79,724,544 bytes peak RSS, and the new gate smoke passes at O1 and O2 under the
default 4 GiB guard. The stage1 WASM artifact suite passed 421 differential
cases, 720 session frames, all configured ABI checks, 45 stateless task-frame
checks, both live controller replays, common API v1, and Marble Maze browser,
physics, and 16-board checks. Fifteen available compiler parity smokes and the
O0/O2/O3 optimizer repro corpus also passed.

The v12 stage1 WASM build still reports 21 declined concurrency-runtime
bodies. The integrated fast gate was intentionally interrupted after all
stage0 differential suites and the first four stage1 suites (pyset,
scheduling, timing, board) passed; it is not a green full-gate result. Stage1
later differential suites, medium compiler tests, provenance reconciliation,
the remaining body-decline audit, and release certification remain open. Do
not promote v12 or infer that all compiler defects are fixed from these scoped
results.

## Current Marble Maze artifact/compiler checkpoint — 2026-09-14

The browser artifact `nw-core/build/nwcore.wasm` was rebuilt with the newest
usable Stage0 candidate at `-O2`, using
`nw-core/build/toolchain-latest-marble-20260914/elisac-stage0`. The source
checkout is Stage0 `5284109ca5805560a488c3b0a5d8cd4a1a45e317`, matching its
recorded `origin/main`; the binary SHA-256 is
`f976501a0e8d2f39a9bc1ac721ff13b6f95109ffbb90a7a557f6b0f91f8a1544`, from
source fingerprint
`00fbde8a5e92b6b11471a379eead635f9b98050d02bfc189d41b4912fc58c0f7`. The
WASM SHA-256 is
`cb15a3eee811466ff657e65b0751ae4eb6df47b0c2639b608378ba4ab6ec7645`. Its
full configured artifact suite passes, including the Marble browser/physics/
MuJoCo tests and 16-board ABI. A deterministic headed-browser test reports a
real failed tray (`0 trays of 1, 1 marbles lost, highest rung 6`) with the board
still rendered; capture is `nw-core/output/playwright/marble-maze-loss.png`.

Marble options now pass rung, trial count, adaptive progression, supported
seconds-per-tray override, and cast-shadows through the task options UI and
common WASM ABI (`e=time override ms`, `f=shadows bool`). The source-shaped final
result and timeout path both render. This does not establish original 3D visual
parity, reference-engine equivalence, solved full-run parity, or bounded MuJoCo
resources. The full compiler Stage1 path is not the binary used in this browser
artifact: its current dirty source has unresolved full-port diagnostics/backend
declines, and the separately tracked upstream commit beyond the Stage1 checkout
is documentation-only. Keep the Stage1 worktree and pinned provenance intact;
the later Stage1 checkpoint below supersedes the artifact/compiler status above.

## Current Stage1 compiler and Marble Maze artifact — 2026-09-14

The active `build/nwcore.wasm` is now built with the current optimized Stage1
compiler candidate at `-O2`, from Stage1 HEAD `df6cf8172cf75cf7fe861c9591d7d03f16a0d7c6`
and source fingerprint
`2fa156c5c83e0f46e79e5676397345c91b0e650b00a5ce08018b1a3ec62ff5ca`.
Stage1 candidate SHA-256:
`b78d2406c31794e11e9ea75e56ff106f682825aa6ffa071a9b0aeee58d645980`.
WASM SHA-256:
`b4247684c5d8dfe3a237f08ca2ba74bf6a75674da1ea92919af14c7bcb50a817`
(941,683 bytes). Stage1 was seeded at `-O2` by the isolated Stage0 candidate
SHA-256 `26c88ad430a02b5171d50032762c7024d908b61b76b9910213ff3565efc6703b`.
The pinned `toolchain/` binaries and `toolchain/PROVENANCE` remain unchanged.

The seed blocker was a Stage1 parser helper annotated as returning the qualified
`Parser.MachineFromTermAst`; Stage0 resolved that return as `<invalid>`, emitted
the call as `void`, then crashed storing it into the typed rebind target. The
helper now returns the locally scoped `MachineFromTermAst`. Stage0's backend
also reports `void` stores before LLVM aborts, with source-function/local
context. A broad semantic-type equality check was intentionally not retained:
opaque-pointer reference stores can validly use a value LLVM type different
from the semantic reference type.

The complete configured artifact suite passes against the active Stage1 WASM:
421 differential, 720 session-frame, all configured batch/menu/task-hub and
stateless task-frame ABI tests, Monkey Ladder, Sokoban, Count, common API v1,
Marble browser/physics/MuJoCo, and all 16 Marble boards. Headed browser QA
confirmed a rendered Marble tray with `physics mujoco`; holding Right updated
the reported tilt to `8°/0°`. Console: zero errors, zero warnings. The page was
returned to the title screen. Capture:
`output/playwright/marble-maze-stage1-browser.png` (SHA-256
`61ca676549e41ae7e7bbbcd22c09ceae2bea723614fa3e530a82241366f04b07`).

Stage1 WASM emission still reports 21 declined concurrency-runtime function
bodies. Those bodies were not exercised by this port suite, so this is not a
green full compiler gate. Marble Maze source parity also remains open: these
tests do not close MM-001–MM-006, especially original-engine trajectories,
multi-tray/adaptive result equivalence, exact 3D renderer/camera parity, or
long-run MuJoCo resource behavior.

## Current Marble and Stage1 verification checkpoint — 2026-09-15

### Compiler and served artifact

- The ordinary `http://127.0.0.1:8000/shells/web/index.html` page fetches
  `/build/nwcore.wasm`. The file and served response both hash to
  `bab8b0ceea0cbb895d6998ee0034b56658e9e5d9fc9421589cf3ac2673934540` (767,742
  bytes). The associated `nwcore_stage1_wasm.o` is 890,292 bytes, SHA-256
  `0b7cdd3a13ff3ffb9a3d0e930247573b8aa1d68b7cb0b23363883557b7c70763`.
- This current artifact was compiled at `-O2` with the latest available local
  Elisa Stage1 product in `/Users/torarinvikbjarko/Documents/Coding Projects/Elisa Projects/Elisa-compiler`:
  HEAD `c605b3faa516de7b2f4945a9ac4ccb21d78ae2e0`, working-tree fingerprint
  `f89a1eb3829a1e5c09f0007e8547e2753e8db8d246674a320869a0d607e876de`, product
  `bin/elisac-stage1` SHA-256
  `2ff6d2ce98a30e2d9414df55feccb7976eca6c62add7eab645f8cad98534d067`. Its
  source freshness check found no `.elisa`/`.elisai` file newer than that
  product. The port-pinned compiler binaries and
  `nw-core/toolchain/PROVENANCE` were not modified.
- `bash scripts/test_wasm_artifact.sh build/nwcore.wasm` passes: 421 differential
  cases, 720 session frames, 6 batch, 3 menu, 4 task-hub, 45 stateless task
  frames, Monkey Ladder, Sokoban, Count, common WASM API v1, Marble browser
  physics, MuJoCo, and board ABI suites. This is artifact evidence, not a full
  Elisa compiler-gate pass. The previously recorded 21 declined
  concurrency-runtime bodies and isolated toolchain provenance review remain
  open. Do not run an unoverridden pinned Stage0 build expecting to preserve
  this artifact.
- Rebuilt into an isolated `/tmp` directory with explicit
  `ELISA_STAGE1_ROOT=/Users/torarinvikbjarko/Documents/Coding Projects/Elisa Projects/Elisa-compiler`
  and matching `ELISA_STAGE1_BIN`, without overwriting `build/nwcore.wasm`.
  `build_stage1_wasm.sh` reproduced the exact active WASM and object hashes and
  reran the full suite successfully. This confirms actual current Stage1 use,
  rather than relying on the recorded file timestamp. The build still prints
  the 21-body decline warning; no full compiler-gate pass is claimed.

### Marble Maze source parity and browser result

- Original environment: Python 3.13.12, NumPy 2.5.2, MuJoCo 3.12.0, pyglet
  2.1.16. Browser vendor: official `@mujoco/mujoco` 3.12.0. SHA-256 values for
  the JS/WASM vendor files, effective model options, and renderer boundary are
  in `docs/marble-physics-manifest.json`.
- New `test/marble_source_reference_diff.mjs` compares every board field and
  ordering after the ABI's f32 conversion, plus generated MJCF, against the
  Python `deal()` / `_mjcf()` oracle for 80 cases (rungs 1–16 × seeds 0, 1, 17,
  314159, and 1073741823). All board fields and XML match. Maximums in this
  matrix: 58 wall strips, 39 holes, and 4 marbles. Effective solver option
  read-backs agree on the comparison board. This does not prove architecture-
  independent state trajectories.
- The 2026-09-15 headed browser run used the real Games menu, Marble Options,
  one trial, and a 15-second budget. It displayed `the tray — 15s` after the
  configured-budget fix, ran the real MuJoCo board to timeout, and reached the
  final result. The session console had zero messages. Capture:
  `nw-core/output/playwright/marble-maze-timeout-15s.png`, SHA-256
  `2715141e0accdfc4b4312c7da94121bb9ef65df145c56ce6d9d9f8fcebb27739`.
- Existing captures document a real rung-1 solve and rung-6 loss. The score
  summary on timeout with zero lost marbles still counts that tray as won,
  matching the original Python `score()` implementation; do not change only the
  port. Full adaptive/multi-tray comparison, replay, native-vs-WASM trajectory
  tolerances, high-rung visual QA, engine rejection, focus cancellation, and
100-cycle resource soak remain open. The 3D browser renderer is WebGL2; visual
parity with the native pyglet/OpenGL renderer has not been reviewed.

## Superseding Marble source-render and run-RNG checkpoint — 2026-09-15

This section supersedes the artifact hash and earlier renderer/RNG notes
above; retain those earlier entries as build history.

- The current active artifact and HTTP-served `/build/nwcore.wasm` both hash to
  `84813c64ee5439e194e72dcd1aa93bc039de15478f7b243f314e4badfb415004`
  (768,353 bytes). Its matching `build/nwcore_stage1_wasm.o` hash is
  `a00d91da0e78d90fea01fc2d50e72669950d47ddbcb5405f6d0ff6748374cda8`.
  It was built with the current external Stage1 product at `-O2` (compiler HEAD,
  fingerprint, and product hash above). A fresh isolated build reproduced both
  hashes and passed `scripts/test_wasm_artifact.sh`; all existing 21 concurrency
  body declines are still reported. The unoverridden port Stage1 wrapper
  refuses its stale default compiler product; do not bypass its freshness guard.
- The Marble run controller now mirrors the original UI's shared random-stream
  order: per-board 30-bit seed, then `random() * 4` wood-grain draw. New
  `nw_api_v1_marble_grain_seed(handle)` is additive and leaves the 112-byte
  state record stable. The conformance smoke verifies seed-17 pairs
  `(889418965, 3.2267631084747164)` and
  `(785170443, 1.158501511057862)`, then replay seed `57846291`. It also checks
  that Space starts/skips feedback while Enter is ignored in Marble Maze.
- The WebGL2 depth pass now honors source non-caster flags for pit tubes, home
  cup, and collar. The color pass uses alpha-to-coverage with blending off in
  an explicit four-sample RGBA8/depth24 framebuffer, resolves once to an
  RGBA8 texture, and composites with a shader like native `Stage._blit`; the
  browser's implementation-defined default framebuffer antialiasing is
  disabled. Source camera, tilt, geometry, and shader inputs were inspected
  side-by-side. This is not yet a visual-parity acceptance: WebGL2 and
  pyglet/OpenGL still have different rasterizers/sample masks, no synchronized
  reference screenshot diff has been accepted, and theme/DPR/high-rung views
  remain open.
- A headed browser rerun selected Games → Attention → Marble Maze, started the
  45-second live MuJoCo tray with Space, rendered the 3D board, and reported
  zero console messages. Capture:
  `output/playwright/marble-fidelity-check-20260915/.playwright-cli/page-2026-09-14T23-59-03-858Z.png`
  (SHA-256 `49f256bdb02b71dbf8317f9157bd4d1cdcc22ac96f923694374a69794d89e78c`).
- MM-001–MM-006 and GAME-020 remain open overall. Required remaining Marble
  evidence includes native-vs-WASM trajectory tolerances, the matched source vs
  browser screenshots, full adaptive/multi-trial scoring and replay, high-rung
  live renders, focus/load-failure recovery, and 100-cycle resource testing.

## Marble explicit-MSAA render and high-rung browser check — 2026-09-15

- `shells/web/marble-maze-renderer.js` now uses a browser-independent render
  target matching the native pipeline: 4× multisampled RGBA8/depth24
  renderbuffers, a single-sample RGBA8 resolve texture, and a dedicated
  composite shader into the default WebGL framebuffer. The context requests
  `antialias: false`, avoiding a second driver-controlled resolve. Disposal
  deletes the target, resolve, composite program, VAO, and buffer resources.
- A fresh headed browser run from Games → Attention → Marble Maze rendered the
  seed-17 rung-1 board with the explicit target and no console errors. Capture:
  `output/playwright/mm-browser-explicit-msaa-screen.png`, 912×685,
  SHA-256 `186de066515ea8108b145497e5aa9b0c34045a6eb199fad6b980e112dfc16e37`.
- The same run policy was exercised at rung 16 with one 15-second tray and
  shadows enabled. It rendered the `inhuman` board with three active marbles,
  39 holes, and no console errors; capture:
  `output/playwright/mm-browser-rung16-explicit-msaa.png`.
- A live default rung-1 run also exercised `C` → options → `Esc` while the
  tray was active: the run remained on tray 1/5 with its remaining budget,
  rather than being completed or replaced. `R` then reset the simulation and
  restored the full 45-second tray budget without changing the trial count.
  The final browser console remained empty.
- The artifact suite remains green after the renderer change: 421
  differential cases, 720 session frames, ABI/menu/task-hub/frame checks,
  Monkey Ladder, Sokoban, Count, common-v1, Marble browser physics, MuJoCo,
  board ABI, and the 31-scenario/1,527-frame native-vs-WASM trajectory oracle.

## Marble trajectory differential and current Stage1 confirmation — 2026-09-15

- Added `test/marble_trajectory_reference_diff.mjs` and included it in
  `scripts/test_wasm_artifact.sh`. The native Python/MuJoCo 3.12.0 reference and
  browser MuJoCo WASM 3.12.0 were run on identical serialized f32 tray data,
  initial states, tilt/level events, and per-frame time partitions. Coverage is
  31 scenarios / 1,527 captured frame states: generated rung 1–16 boards at
  seed 17 plus explicit rest, cap/spin, normal/glancing/corner/narrow-passage
  wall contact, resting-ball and three-ball chains, low/high-speed pit,
  home-cup, falling-wall, terminal parking, irregular partition, and source-UI
  clock cases. The comparison records all position/linear/angular/orientation values,
  state and hole identity, elapsed and nudge time, impact/cup/loss events, and
  home/lost totals.
- All discrete states/events/counts matched exactly. Maximum observed errors
  were `1.7e-14 m` in XY position, `3.1e-16 m` in Z, `3.5e-14 m/s` in XY
  velocity, `5.9e-15 m/s` in Z velocity, `5.2e-13` in quaternion components,
  `4.9e-12 rad/s` in angular velocity, and `1.6e-14` in the impact signal.
  Enforced tolerances are respectively `1e-8 m`, `1e-8 m/s`, `1e-8`,
  `1e-7 rad/s`, `1e-8`, and `1e-10` for scalar time/tilt/nudge values. These
  results are bounded to the tested trace matrix; they are not a proof for every
  collision arrangement or a claim that separate time partitions are invariant.
- The new reference test caught two browser-only differences. On swallow, the
  source intentionally leaves the last hole in `marble.over`; the MuJoCo
  adapter cleared it, so that clear was removed. Both browser adapters also
  dropped positive frame remainders below 1 ns; the native UI loops until its
  remainder is zero. The adapters now execute every positive remainder, and
  the `0.05`-second frame regression expects the source's three nominal bites
  plus the tiny fourth floating-point bite.
- Reconfirmed the newest external compiler before the fresh build:
  repository HEAD `c605b3faa516de7b2f4945a9ac4ccb21d78ae2e0`, source-tree
  fingerprint `f89a1eb3829a1e5c09f0007e8547e2753e8db8d246674a320869a0d607e876de`,
  Stage1 product SHA-256
  `2ff6d2ce98a30e2d9414df55feccb7976eca6c62add7eab645f8cad98534d067`. The
  source freshness check found no `.elisa`/`.elisai` inputs newer than that
  product. With `ELISA_STAGE1_ROOT` and `ELISA_STAGE1_BIN` explicitly set to
  that external tree/product, a fresh isolated `-O2` build emitted an object
  identical to the active Stage1 object's SHA-256
  `a00d91da0e78d90fea01fc2d50e72669950d47ddbcb5405f6d0ff6748374cda8` and
  passed the full updated artifact suite. The isolated linked WASM SHA-256 is
  `5c2fa9710e01fabb70473d253ee31c868b4f232f0f9df5fd8ee5b6a649632542`; the
  served active file remains `84813c64ee5439e194e72dcd1aa93bc039de15478f7b243f314e4badfb415004`.
  The first difference is in the custom `name` section, seven bytes longer in
  the isolated output; linked code and data bytes are identical. Both artifacts
  pass `test_wasm_artifact.sh`. The build still reports 21 declined concurrency
  bodies; this does not certify the complete Elisa compiler gate.
- MM-003 remains partial. Still required: impacts at corners and narrow
  passages, resting and simultaneous/multiple ball contacts, falling marbles
  interacting with explicit wall/ball pairs, already-home/lost solver parking,
  event-rich replays over every listed display partition, and a broader real
  solved/lost/timeout/restart browser replay. MM-005 paired reference/browser
  pixel review also remains open.

## Latest Elisa compiler optimization product — 2026-09-15

The current browser artifact has now been rebuilt from the latest available
Elisa compiler checkout, including its current uncommitted backend/semantic
optimization changes. The selected checkout is
`/Users/torarinvikbjarko/Documents/Coding Projects/Elisa Projects/Elisa-compiler`,
branch `codex/shared-typed-edir-lowering`, at HEAD
`c605b3faa516de7b2f4945a9ac4ccb21d78ae2e0`. After fetching `origin`, its
`origin/main` was `fd2cb3cff470319500db362e5fce2833cbe300de`, two commits behind
the selected checkout. The current Stage1 product is fresh against the
checkout's `.elisa`/`.elisai` source inputs.

- Source-tree fingerprint:
  `0ec13f4da73439e41c14aa1c7847534ef95955cba861af5d8eb39c6561b9eb26`.
- Stage1 product SHA-256:
  `13439241e5a5c4e9cbc9cee60ae24b454ca7f6f6b6d55aa5abbd67b9fa5b7b46`.
- Optimization level: `-O2`.
- Emitted object SHA-256:
  `a00d91da0e78d90fea01fc2d50e72669950d47ddbcb5405f6d0ff6748374cda8`.
- Promoted `nw-core/build/nwcore.wasm`: 768,353 bytes, SHA-256
  `84813c64ee5439e194e72dcd1aa93bc039de15478f7b243f314e4badfb415004`.
- HTTP-served WASM at `127.0.0.1:8000/build/nwcore.wasm`: same size and hash.

The isolated build used explicit `ELISA_STAGE1_ROOT` and `ELISA_STAGE1_BIN`
values for this checkout/product, then promoted the exact tested link to the
active browser path. The complete artifact suite passed, including the
31-scenario/1,527-state Marble trajectory oracle. The compiler still reports
21 declined concurrency-runtime bodies, so the complete compiler gate remains
uncertified; that warning is recorded rather than hidden.

The repeatable workflow now lives in
`nw-core/scripts/build_latest_stage1_wasm.sh`. `nw-core/scripts/gate.sh` keeps
Stage0 as the independent oracle but routes every Stage1 port differential,
targeted compiler smoke, optimizer-RSS check, and final production WASM build
through this latest checkout/product. The first pre-fix broad-gate attempt
exposed the old pinned Stage1 product as stale and was stopped after the clean
Stage0 phase; the corrected latest Stage1 Marble and optimizer checks pass.

## Latest compiler product refresh — 2026-09-15

The compiler freshness guard found that the earlier Stage1 product had become
older than current `.elisa` sources. It was rebuilt using the compiler's
supported guarded seed path, then the port was rebuilt through
`scripts/build_latest_stage1_wasm.sh`.

- Compiler checkout: `/Users/torarinvikbjarko/Documents/Coding Projects/Elisa Projects/Elisa-compiler`
- Branch/HEAD: `codex/shared-typed-edir-lowering` /
  `8d7db0561d0f72c1f548fa6a73d071c86b2fe57f`
- Fetched `origin/main`: `fd2cb3cff470319500db362e5fce2833cbe300de`
  (14 commits behind HEAD)
- Source fingerprint: `b9b6a2722fc7553d4156d3fe9b6377085b83944f24fad11f5c57821c8b3a3a38`
- Fresh Stage1 product SHA-256:
  `2cde942ba385ffdab42903faee94ff0c60e31428362882671acde888b446fe26`
- Optimization: `-O2`; no compiler source is newer than the product
- Active/served WASM: 768,353 bytes,
  `84813c64ee5439e194e72dcd1aa93bc039de15478f7b243f314e4badfb415004`

The complete configured artifact suite passes with this refreshed product,
including the Marble 31-scenario/1,527-frame trajectory oracle. The wrapper
and gate retain the stale-product refusal; the gate performs that check before
the Stage0 oracle build can touch the production filename, so this provenance
cannot silently regress.

## Latest-compiler compatibility fixes — 2026-09-15

The refreshed Stage1 gate exposed two non-Marble compatibility issues that the
old pinned product had not reported:

- In-the-Dark now binds its `Grade` value as `mutable` before passing it to
  `deal`, matching the latest semantic gate's mutable-struct ABI. Stage0 and
  Stage1 both pass 106/106 cases.
- The standalone Sokoban controller sweep now defines the
  `arena_profile_explicit_create` bridge introduced by the latest compiler's
  explicit-region profiler lowering. The frozen Stage0 runtime remains the
  independent oracle; production runtime files were not changed. Stage0 and
  Stage1 both pass 255/255 controller states.

The latest Stage1 production artifact and Marble/browser checks remain green
after these fixes.

## Latest Maze controller and production rebuild — 2026-09-15

The Maze vertical slice is now source-backed in the browser. The controller in
`src/tasks/maze_game.elisa` calls the exact `Maze::generate` kernel, copies the
winning corridor mask and layout values out of its temporary generation region,
and owns the run across ABI calls. It implements READY/WALKING/SOLVED/DONE,
keys and locked doors, one-cell arrow/WASD movement, restart, exact minimum
grading, source adaptive thresholds, result aggregation, and the `SceneMaze`
display list. `runtime_protocol.elisa` and `wasm_exports.elisa` expose stable
task ID `3848665378`, common lifecycle support, `nw_api_v1_maze_info`, and
`nw_api_v1_maze_cell`; the web shell creates/destroys the controller and does
not fall back to the generic task card for Planning → Maze.

`test/maze_game_smoke.mjs` solves a live rung-1 board and a door-bearing rung-3
board by searching the exported topology, checks exact shortest-path grading,
render stability, Enter-to-DONE progression, and destruction. The source
differential is also green at 428/428 cases for both Stage0 and the selected
latest Stage1. A headed browser smoke, after reloading the module, selected
Games → Planning → Maze, observed the Maze-specific `maze 0/5` ready status,
started with Space, and observed ArrowRight change the real status from
`steps 0` to `steps 1`.

The latest production build was emitted through
`scripts/build_latest_stage1_wasm.sh` with Elisa compiler HEAD
`8d7db0561d0f72c1f548fa6a73d071c86b2fe57f`, source fingerprint
`3faa64471197da94697d83712f0433aa8c443381b0654f80e0f5ecab5feaa17e`, and
Stage1 product SHA-256
`059e097f1d463bc7ce01e859c4d7b46ba491fe6b26d599433ea75088317cbb85`. The
emitted object is
`7ef77737f8475c20ede7e654304b75fd18eadbb84ccf241bf81574d3d23e878c`; the
852,475-byte active and HTTP-served WASM is
`fabcdd1bcedd57999934520dd64ca5d7284774e42856700132c773b45c4cc687`.
The complete configured artifact suite passes, including the new Maze smoke.
The compiler still reports 21 declined concurrency-runtime bodies, so the full
compiler gate and release certification remain open. Maze options UI and
persistence, all door-count/key-order replay cases, full multi-trial/result/
exit/resource acceptance, and Python/SDL adapters remain open as well.

## Latest Elisa Stage1 product and Marble renderer rebuild — 2026-09-15

The sibling compiler advanced after the preceding browser artifact was built,
so the Stage1 product was explicitly reseeded from the new compiler HEAD with
the guarded `scripts/elisac_stage1.sh --seed` workflow. The reseed completed
successfully; the stale-product escape hatch was not used.

- Compiler checkout: `/Users/torarinvikbjarko/Documents/Coding Projects/Elisa Projects/Elisa-compiler`
- Branch/HEAD: `main` /
  `565ccb2fd585d03f94457185376f526e1930b1cb`
- Fetched `origin/main`:
  `45cb0ded70e7e8c8a41d21c63a09939706322ca4`
- Source fingerprint:
  `9de69658a554a61ac1679e3cd52398ea73800adf700fb0c51d7a636324dceef9`
- Fresh Stage1 product SHA-256:
  `2324bf11c796433ac2868b4dc5d4c8ab26f4e471e30dfafb3d3067a1f159dd17`
- Optimization: `-O2`; the freshness guard found no newer compiler source
  input than the reseeded product.
- Emitted Stage1 object SHA-256:
  `6ac7931e8378237e71795238c9b40d54f14bea8d3639cec46033aa82501252e0`
- Active/served WASM: 852,475 bytes,
  `fae3de45596b36cc641ccd5bfbe3e3d2a78829a08597b45e0b66512ece3f37bc`; the
  HTTP response has the same hash, content type, and size.

The complete configured artifact suite passes against this new product:
421 differential cases, 720 session frames, common/batch/menu/task-hub and
stateless ABI suites, Monkey Ladder, Sokoban, Count, Tower of Hanoi, Maze,
Marble browser/MuJoCo/board/trajectory checks, and the renderer contract. The
31-scenario Marble trajectory oracle compares 1,527 states. The compiler still
reports 21 declined concurrency-runtime bodies, so the full compiler gate and
release certification remain open.

The same served artifact also passed the targeted headed Marble checks: options
set to rung 16, one tray, adaptive difficulty off, shadows on, and a 15-second
override produced a live DPR-2 board with three marbles and the dense wall
layout, accepted a held ArrowRight input, and reported zero page errors or
console warnings. A separate headed session completed 100 Escape → reopen →
Space-start cycles and returned to a live Marble run with zero errors/warnings.
The high-rung capture is
`nw-core/output/playwright/marble-rung16-latest.png`; the lifecycle result is
stability evidence, not a live allocation-count or WASM memory-growth proof.

The live focus-loss check is also clean. On a fresh tray, a held ArrowRight
reached `tilt 2°/0°`; after a window `blur`, the tilt stayed fixed for the next
300 ms while the clock continued, and the page had zero console errors and zero
warnings. The renderer contract test now guards both blur and hidden-document
input release. An injectable MuJoCo loader regression preserves a rejected
WASM-load error so the shell can select and label its fallback solver; partial
MuJoCo model/data allocation cleanup remains covered. Live native-object counts
are now instrumented: a headed 100-cycle soak ended with 101 model/data
creations, 100 deletions, and exactly one live model/data pair for the final
active tray, with zero console errors/warnings. Allocator high-water marks,
tab shutdown, context-loss recovery, and WASM-memory-growth bounds remain
unmeasured.

The renderer now applies the source's per-tray shadow span
`max(tray.width, tray.depth) * 0.78` (the source initially constructs
`render3d.Light` with a `0.30` default and replaces that field during
`on_draw`). The source-stage/browser-canvas review at the 912×684 logical layout is
recorded in `docs/marble-physics-manifest.json`: after diagnostic resampling,
global grayscale SSIM was `0.9697784562343885` with RGB channel correlations
`0.9570248638873162 / 0.9710029378539714 / 0.982701422705817`. This supports
geometry/material alignment but remains explicitly short of pixel identity
because pyglet/OpenGL and WebGL2 use different rasterizers and sample masks.

The board ABI boundary is defensive as well: `decodeMarbleBoard()` checks
fixed-length/truncated reads, rejects oversized count fields before looping,
and rejects non-finite geometry values. The 16-rung ABI sweep and the new
malformed-payload cases pass. The isolated Stage0 artifact and the latest
Stage1 production artifact now also match on decoded board fields and generated
MJCF for all 80 certified rung/seed cases; the scratch Stage0 WASM is
`nw-core/build/verification/marble-stage0/nwcore.wasm` (SHA-256
`73d411505fa2a1d1cd4fb77cb40be5baaf3f2849c4fa26aa0c6366d7ff9e24a2`).

The renderer now has an explicit WebGL loss/recovery lifecycle. It prevents the
browser's default context-loss behavior, stops issuing draw calls while the
context is unavailable, retains the retired renderer until restoration or task
exit, disposes its resources, and installs a fresh renderer with the active
board after restoration. The contract test covers the event hooks and the
shell's recovery/error path. A headed Chromium test forced
`WEBGL_lose_context`, observed `lost -> restored`, verified the restored context
was healthy, and produced zero console errors/warnings. Disposal now skips
pre-loss WebGL delete calls after restoration, avoiding stale-handle
`INVALID_OPERATION` warnings. The active Marble-task integration then observed
the shell remove the lost renderer, retain the recovery token, create a
different renderer after restoration, reapply the board, resume the live tray,
and clear the token, again with zero console errors/warnings.

## Latest Stage0/Stage1 Marble transport parity and Hanoi compatibility fix — 2026-09-15

- The isolated Stage0 `-O2` compile initially stopped on two current-source
  diagnostics in `src/tasks/hanoi_game.elisa`: `save_board` passed a read-only
  `Hanoi::Board&` to `Ints::at_ref`, whose API correctly requires a mutable
  borrowed darray. Both callers already own mutable boards, so the adapter
  signature is now `board: mutable Hanoi::Board&`. Stage0 then emitted its
  object with warnings only and exit 0; no production Stage1 file was used for
  this diagnosis.
- Scratch Stage0 hashes: compiler
  `toolchain/elisac-stage0` SHA-256
  `c5efa8ce20f781f21817eabc0481efe79a2c895031f49ce64bbb72911386c183`,
  object `97efcc72562a7546685d6a7be00d186169fe873cab0d267b8597683d280167c4`,
  linked WASM `73d411505fa2a1d1cd4fb77cb40be5baaf3f2849c4fa26aa0c6366d7ff9e24a2`.
- `test/marble_cross_compiler_parity_test.mjs` compares the live exported board
  bytes after decoding and the generated MJCF, not only a success code. It
  passed 80 cases (rungs 1–16 × seeds 0, 1, 17, 314159, and 1073741823)
  between that Stage0 WASM and the current latest-Stage1 artifact.
- The production browser build was rebuilt after the source fix through
  `scripts/build_latest_stage1_wasm.sh` with compiler HEAD
  `565ccb2fd585d03f94457185376f526e1930b1cb`, product SHA-256
  `2324bf11c796433ac2868b4dc5d4c8ab26f4e471e30dfafb3d3067a1f159dd17`,
  and `-O2`. The complete artifact gate remains green; the active and served
  WASM remain SHA-256
  `fae3de45596b36cc641ccd5bfbe3e3d2a78829a08597b45e0b66512ece3f37bc`.
- This closes the recorded Stage0/latest-Stage1 Marble board-transport
  parity check. It does not claim the full Elisa compiler gate: the build
  still reports 21 intentionally declined concurrency-runtime bodies, and the
  independent Python/native trajectory, renderer-pixel, allocator high-water,
  context-loss, and full release gaps remain tracked above.

## Latest Marble lifecycle memory repeat — 2026-09-15

A second headed 100-cycle run used the real `Escape -> Enter -> Space` route
against the served latest-Stage1 artifact. The WASM linear-memory buffer was
`10,223,616` bytes before the loop, after the loop, and at every one of the
100 samples (`min = max = 10,223,616`, growth `0` bytes). The MuJoCo
diagnostic counters moved from 8 to 108 model/data creations and from 7 to
107 deletions, so the test delta was exactly 100 create/delete pairs for each
resource type; one model/data pair remained live for the final active tray.
Playwright reported zero console messages: zero errors and zero warnings. This
closes the measured memory-growth question for this exercised lifecycle, while
allocator behavior under other workloads, browser-tab shutdown, and WebGL
context-loss recovery remain open.

## Latest Marble semantic ABI and collision checkpoint — 2026-09-15

The latest browser-side board decoder now validates semantic invariants after
the fixed and variable-length reads: boolean encodings, certified rung and
dimension ranges, positive geometry, cell/dimension consistency, wall ordering
and bounds, hole bounds, exactly one final home cup matching the fixed home
fields, usable start coordinates, and exact payload consumption. The malformed
ABI suite covers each rejection class, and all 16 generated rungs still decode.

The native-versus-browser MuJoCo trajectory oracle now covers 36 scenarios and
1,932 per-frame states. It includes two-marble wall-plus-pair contact,
four-marble central simultaneous contact, and a falling marble meeting both
explicit wall and ball pairs, alongside the existing wall, hole, home,
multi-ball, timing, tilt, and generated-rung cases. All discrete events and
continuous fields remain within the previously recorded tolerances. The
broader corner permutation and real-session matrix remains open.

The WebGL context-loss result is now closed for the measured lifecycle: live
headed Chromium observed `lost -> restored`, the shell replaced the renderer,
reapplied the board, resumed the active tray, cleared its recovery token, and
reported zero console errors/warnings. Stale pre-loss handles and asynchronous
texture completion are guarded. Remaining lifecycle scope is allocator
behavior under other workloads and browser-tab shutdown.

The shell also retains an opt-in per-trial result ledger. A live run configured
for rung 2, two trays, adaptive difficulty, and a 15-second override recorded
tray 1 at seed `889418965` as a timeout and lowered the next tray to rung 1;
tray 2 used seed `785170443` and timed out as well. Both records have the
source's zero-lost-marble `scoreWin` value, while retaining a separate timeout
verdict and exact `15000 ms` controller budget. The run reached DONE with
aggregate `2/2` scored wins, zero lost marbles, highest rung 2, and zero
console errors/warnings. The ledger is exposed only with
`?marble-test-hooks=1` and is protected by the renderer contract test.

The production provenance remains the latest Elisa Stage1 `-O2` product:
compiler `main@565ccb2fd585d03f94457185376f526e1930b1cb`, product SHA-256
`2324bf11c796433ac2868b4dc5d4c8ab26f4e471e30dfafb3d3067a1f159dd17`, emitted
object `6ac7931e8378237e71795238c9b40d54f14bea8d3639cec46033aa82501252e0`,
and served WASM
`fae3de45596b36cc641ccd5bfbe3e3d2a78829a08597b45e0b66512ece3f37bc`.
The artifact gate remains green; the compiler's 21 declined
concurrency-runtime bodies still prevent full compiler-gate certification.

## Latest Marble headed success replay — 2026-09-15

The positive play path is now measured from a fresh headed page, not only from
the Node-side MuJoCo wrapper. With Marble options set to rung 1, one tray,
adaptive difficulty off, shadows off, and a 45-second budget, the real route
`Games -> Attention -> Marble Maze -> Space` started board seed `889418965` on
the official MuJoCo WASM engine. The native differential test names tray
directions directly (`W/S/S/E/E/E/N/N/N/W/S/S`); the equivalent source UI
keys are `A/S/S/D/D/D/W/W/W/A/S/S` because the original maps W/up to north,
A/left to west, S/down to south, and D/right to east. Each held segment was
300 ms, followed by `L` and a 600 ms coast.

The fresh run reached the home cup in `10.599500000000148` physics seconds
(`10582 ms` controller time), with `home=1`, `lost=0`, `verdict=1`,
`timedOut=false`, `scoreWin=true`, and par time
`4.682685852050781` seconds. The page displayed the source-shaped success
message (“Home in 10s — a good line was about 4s”), remained on the MuJoCo
path, and Playwright recorded zero console errors and zero warnings. The
machine-readable copy is `lifecycleEvidence.headedBrowserSuccess` in
`nw-core/docs/marble-physics-manifest.json`.

This closes the basic live success transition for Marble. It does not claim
that every generated tray is human-solvable by this single replay, nor that
success-within-par is covered for every trial-count and adaptive combination;
the broader generated-board and real-session matrix remains tracked in the
implementation plan.

The MuJoCo cleanup counters were also hardened: a resource is counted as
deleted only after its native `delete()` returns successfully. An injected
model-delete exception now leaves one live model visible while the data object
that did delete is counted correctly. The failed model handle remains attached
to the game, and a second disposal succeeds without deleting the data object a
second time; the live deltas return to zero. The existing 100-cycle success
path still reports exactly 100 create/delete deltas and one expected live pair.
## Latest Elisa compiler rebuild — 2026-09-15

The cached Stage1 product was initially rejected by the freshness guard because
the sibling compiler had newer backend source. The guarded Stage0 seed was
allowed to finish, the compiler merge was resolved, and the selected latest
checkout is now clean at main@d6a693c0f724c05f7b71418658dd8bda95ba73b3,
seven commits ahead of origin/main (45cb0ded70e7e8c8a41d21c63a09939706322ca4).
Its source fingerprint is
9de69658a554a61ac1679e3cd52398ea73800adf700fb0c51d7a636324dceef9 and the
fresh Stage1 product is
82543b75bb15bafd4e7a12aab824446b565f661a89a9870b34513c5722f34fc7.

The port was rebuilt with that product at -O2. The emitted Stage1 object is
6ac7931e8378237e71795238c9b40d54f14bea8d3639cec46033aa82501252e0, and the
852,475-byte active and served WASM has hash
fae3de45596b36cc641ccd5bfbe3e3d2a78829a08597b45e0b66512ece3f37bc. The
complete artifact gate passed, including the 36-scenario/1,932-state Marble
trajectory oracle. The compiler still reports 21 declined concurrency-runtime
bodies, so this is the current optimized port product, not a full compiler-gate
certification.

## Stage0 oracle artifact isolation — 2026-09-15

The repository gate previously invoked the Stage0 WASM oracle builder with the
same `build/nwcore.wasm` path used by the production latest-Stage1 artifact.
That could leave a green gate followed by a browser page running Stage0. The
builder now accepts explicit object, artifact, and binding-prefix paths, and
`gate.sh` routes its oracle output under `nw-core/build/verification/stage0/`.
The production path remains reserved for `build_latest_stage1_wasm.sh`.

The isolated Stage0 build and artifact checks passed without modifying the
production file. The production file was then rebuilt from
`Elisa-compiler/main@d6a693c0f724c05f7b71418658dd8bda95ba73b3`; local and HTTP
served copies are both 852,475 bytes with SHA-256
`fae3de45596b36cc641ccd5bfbe3e3d2a78829a08597b45e0b66512ece3f37bc`.

## Current-runtime rebuild against latest Elisa — 2026-09-15

The selected Elisa compiler checkout remains clean at
`main@d6a693c0f724c05f7b71418658dd8bda95ba73b3`; its source fingerprint is
`9de69658a554a61ac1679e3cd52398ea73800adf700fb0c51d7a636324dceef9`, and its
fresh Stage1 product is
`82543b75bb15bafd4e7a12aab824446b565f661a89a9870b34513c5722f34fc7`.

The WASM export source had referenced a removed historical runtime worktree.
Its three runtime includes now resolve to the selected checkout's
`Elisa-compiler/elisacore_std` files. The recursive include closure contains
132 files with no missing targets. The latest Stage1 and isolated Stage0
artifact suites both pass, and Stage0/Stage1 Marble board/MJCF parity remains
80/80.

The rebuilt `-O2` production WASM is 873,133 bytes with SHA-256
`f53c7f8416444453d3a3dd030f82806c97fce03417b88e41cbc9552bdb6b37ef`; its
Stage1 object is
`e3828e728ac4045963cb650f003ff8dce2e3f426012935f058d8109133cdacd8`, and the
HTTP-served copy has the same hash. The known 21 declined concurrency-runtime
bodies still prevent claiming the complete compiler gate.

## Marble fallback rejection and cleanup owner — 2026-09-15

The web shell now keeps a failed MuJoCo game as a pending cleanup owner. If a
native model/data deletion throws, the next board setup retries that same
handle and refuses to allocate another engine until cleanup succeeds. This
matches the adapter's truthful delete accounting and prevents a recoverable
native leak from becoming unreachable in the shell. The renderer contract
test covers the owner, retry gate, and diagnostic error path.

A real Chromium run exercised the opt-in rejection path at
`?marble-test-hooks=1&marble-force-fallback=1&marble-seed=17`. The browser
logged exactly the expected fallback warning, selected `engine=fallback`,
decoded board seed `889418965`, entered a live 45-second tray after Space, and
reported zero console errors. This is controlled load-rejection evidence; it
does not claim that the normal MuJoCo load is unavailable. The complete record
is in `lifecycleEvidence.loadRejection.forcedBrowserExercise` in the Marble
physics manifest.

## Partial MuJoCo constructor cleanup — 2026-09-15

Marble Maze's adapter now retains a native model when model creation succeeds,
data construction throws, and the first model delete also throws. The game
owns that failed handle after the constructor exception; a later
`disposeEngine()` retries it and restores the live-model counter to baseline.
This closes the partial-construction leak path required by MM-006. The
regression and measured result are recorded in
`lifecycleEvidence.partialConstructorCleanup` in
`nw-core/docs/marble-physics-manifest.json`.

## Marble source-score commit and latest artifact — 2026-09-16

The controller now preserves the original Marble Maze distinction between a
physical timeout verdict and the source `score()` result. The source counts a
tray with zero lost marbles as a win even when the time limit expires before
the marble reaches the home cup. `ACTION_REPORT` therefore carries both the
physical all-home bit and the source-score bit, while a timeout enters feedback
with the physical loss first. The web host then sends the one-shot `SCORE`
action after reading the MuJoCo-owned lost count. Duplicate score commits are
ignored by the controller.

A fresh headed Chromium run against the rebuilt artifact used rung 1, one
trial, adaptive off, and a 15-second tray. MuJoCo timed out at controller time
`15000 ms` with `home=0`, `lost=0`, and physical `verdict=0`; the final
controller summary was `wins=1`, `losses=0`, while the browser ledger recorded
`timedOut=true` and `scoreWin=true`. The run produced zero console errors and
zero warnings. Runtime ABI smoke covers malformed/valid report bitmasks,
timeout scoring, and duplicate protection.

The production artifact was rebuilt through
`nw-core/scripts/build_latest_stage1_wasm.sh` with the clean latest Elisa
Stage1 checkout `main@d6a693c0f724c05f7b71418658dd8bda95ba73b3`, product
SHA-256 `82543b75bb15bafd4e7a12aab824446b565f661a89a9870b34513c5722f34fc7`,
and `-O2`. The active and HTTP-served 873,583-byte WASM hash is
`0d8c525d279da9a233308cf3d5814d83867e3e448b6166a695ca76ba17b31f41`; its
Stage1 object hash is
`a6b372d1246affd6f768d4f1d11f2a6b13749494d6f7eebcaeef29d41b5f61a4`.
The isolated current-runtime Stage0 artifact is 450,516 bytes with hash
`fc5f384a5470782ed946aaa8ea7c3dc28cd622eebf4ae2a7b97297fccc43bd54`.
Both complete artifact suites pass, and Stage0/latest-Stage1 Marble board/MJCF
parity remains 80/80. The known 21 declined concurrency-runtime bodies and
the intentional current-runtime drift remain open compiler-gate items.

## Marble settlement-clock synchronization — 2026-09-16

The browser physics loop advances MuJoCo before advancing the common WASM
controller. A marble that settles on that final frame therefore had a source
`Simulation.elapsed` value that could be one frame ahead of the controller's
millisecond clock. That was observable at the adaptive `1.6 × par` boundary.
The host now sends `SYNC_SETTLE_TIME=11` with the measured physics elapsed time
before `ACTION_REPORT`; the controller accepts only a monotonic value while
RUNNING and keeps the existing 112-byte state envelope. The runtime smoke test
covers the auxiliary-field validator, monotonic sync, and subsequent report.

The latest optimized artifact was rebuilt after this fix with the same clean
Elisa Stage1 `main@d6a693c0f724c05f7b71418658dd8bda95ba73b3` product
`82543b75bb15bafd4e7a12aab824446b565f661a89a9870b34513c5722f34fc7`.
The active and HTTP-served 873,782-byte WASM hash is
`0c3b19b0fcefd4e497d00e3046fe48c8eec17466ea1cfae5eaa9a62a7f7510bc`; the
Stage1 object hash is
`cd9f3e9ce40a07df602de01855452aac435df9e2453faef647045ba30f9a2750`.
The isolated Stage0 artifact is 450,608 bytes with hash
`676fa28521c3af685b9f9ab7a93a392c3590a05203d3eae841234787a10a3ef7`.
Both complete artifact suites pass, including 36-scenario/1,932-state
native-vs-browser trajectory parity and 80-case Stage0/Stage1 board/MJCF
parity. The known compiler-gate concurrency/runtime-drift caveats remain
explicitly open.

## Latest-compiler Marble acceptance replay — 2026-09-16

The production artifact was checked against the selected latest Elisa checkout
before the browser replay. The compiler checkout is clean at
`main@d6a693c0f724c05f7b71418658dd8bda95ba73b3`; its source fingerprint is
`9de69658a554a61ac1679e3cd52398ea73800adf700fb0c51d7a636324dceef9`, and the
fresh Stage1 product is
`82543b75bb15bafd4e7a12aab824446b565f661a89a9870b34513c5722f34fc7`.
No Elisa source file is newer than that product. The port was rebuilt at
`-O2` from the current runtime source, producing the active and HTTP-served
873,782-byte WASM with SHA-256
`0c3b19b0fcefd4e497d00e3046fe48c8eec17466ea1cfae5eaa9a62a7f7510bc`.

A fresh headed Chromium page used the actual menu route
`Space -> ArrowRight -> ArrowRight -> ten ArrowDown presses -> Space`, selected
`Games -> Attention -> Marble Maze`, and started the tray with a second Space.
The seed-17 board was `889418965`, the engine label was `mujoco`, and the
source-compatible route
`A,S,S,D,D,D,W,W,W,A,S,S` (300 ms held per segment, level after each segment,
600 ms coast) reached the home cup. The final browser ledger was:

```text
controller elapsed: 10748 ms
physics elapsed: 10.748100000000084 s
home/lost: 1/0
physical verdict: won
source score win: true
timed out: false
console errors/warnings: 0/0
```

Focused runtime protocol, MuJoCo, renderer-contract, and 80-case
Stage0/latest-Stage1 Marble board/MJCF parity checks pass after the replay;
`git diff --check`, JSON validation, shell syntax, and the served-hash check
also pass. The complete compiler gate remains explicitly caveated by the
known 21 declined concurrency-runtime bodies and intentional current-runtime
drift; this acceptance result is for the latest optimized Stage1 artifact,
not a claim that those unrelated gate caveats are resolved.

## Remote-aware latest-compiler guard — 2026-09-16

After fetching `origin/main`, the selected Elisa compiler remains clean at
`main@d6a693c0f724c05f7b71418658dd8bda95ba73b3`; the remote ref is
`45cb0ded70e7e8c8a41d21c63a09939706322ca4`, leaving local `main` seven commits
ahead and zero commits behind. The source fingerprint and Stage1 product hash
remain `9de69658a554a61ac1679e3cd52398ea73800adf700fb0c51d7a636324dceef9`
and `82543b75bb15bafd4e7a12aab824446b565f661a89a9870b34513c5722f34fc7`.

Both `nw-core/scripts/build_latest_stage1_wasm.sh` and `nw-core/scripts/gate.sh`
now reject a selected compiler checkout that is behind its fetched
`origin/main`, in addition to the existing source-newer-than-product check.
The guarded `-O2` rebuild passed the complete current artifact suite, with the
known 21 concurrency-runtime body declines still reported rather than hidden.

## Mixed Marble success/timeout replay — 2026-09-16

The browser acceptance harness now supports query-gated Marble options for
headed tests. `marble-test-rung`, `marble-test-trials`,
`marble-test-adaptive`, `marble-test-shadows`, and `marble-test-seconds` are
honored only when `marble-test-hooks=1`; ordinary URLs continue to use the
persisted settings and source defaults.

A fresh headed Chromium run used the real Games → Attention → Marble Maze
route, with seed `17`, two trays, adaptive difficulty, and a 15-second test
budget. The held route `A,S,S,D,D,D,W,W,W,A,S,S` used 350 ms per segment,
level after each segment, and 150 ms of coast. Tray 1 used board seed
`889418965`, reached home in `6.399900000000013` seconds, and promoted the
next tray from rung 1 to rung 2 under the source `1.6×par` rule. Tray 2 used
seed `785170443`, timed out at controller `15000 ms`, and retained
`scoreWin=true` with zero lost marbles while its physical verdict remained
loss. The run reached DONE with two result rows, best rung 2, zero console
errors/warnings, and capture
`output/playwright/marble-mixed-success-timeout.png` (SHA-256
`8cf1590834c1889b2340f02312e696ee1b205e6efcc0af7bc20d6fdd79e74d2b`).

The machine-readable record is
`lifecycleEvidence.headedBrowserMixedResults` in
`nw-core/docs/marble-physics-manifest.json`. This closes the real mixed
physical-success/timeout and success-within-par adaptive path; arbitrary
generated-board play, lost-marble browser coverage, and exact renderer pixel
identity remain open.

## Latest-artifact Marble loss replay — 2026-09-16

The current browser artifact was exercised through the real task-hub route
using the latest locally available Elisa Stage1 compiler output (`-O2`). A
fresh Chromium page entered `Games → Attention → Marble Maze`, started rung 6
with one trial, and held the North input (`W`) for 5 seconds. The official
MuJoCo-backed browser engine selected board seed `288545018`; the marble fell
at physics time `0.7019120000000006` seconds. The controller reported
`elapsedMs=702`, `home=0`, `lost=1`, `verdict=0`, `timedOut=false`, and
`scoreWin=false`. The run then reached the source-shaped `DONE` summary with
one loss, rung 6, zero wins, and one lost marble.

The page stayed rendered through loss feedback and final summary, and the
headed run recorded zero console errors and zero warnings. The screenshot is
`nw-core/output/playwright/marble-loss-latest.png` (SHA-256
`afeebe906e0858caa27efaf890efa24e9f476a71f2be65cc702ea8beee4675e7`). The
machine-readable record is `lifecycleEvidence.headedBrowserLoss` in
`nw-core/docs/marble-physics-manifest.json`. This closes current-artifact
real-loss evidence while arbitrary generated-board play, all-rung loss
coverage, persisted result export, and exact renderer pixel identity remain
open.

## Headed Marble resource and focus lifecycle soak — 2026-09-16

The test-gated `marbleDebug` view now exposes the MuJoCo model/data counters
without adding them to production UI state. A fresh headed Chromium route
entered `Games → Attention → Marble Maze`, started the official MuJoCo engine,
held `W` for 260 ms, dispatched the shell's normal blur lifecycle handler, and
verified that the held-mask bit changed from `1` to `0`; the tray remained
live, and the subsequent focus hook did not reintroduce the input.

The same page then performed 100 corrected `Escape → reopen → Space-start →
Escape` cycles. At most one model and one data object were live during any
cycle. Counters ended at `modelsCreated=101`, `modelsDeleted=101`,
`dataCreated=101`, `dataDeleted=101`, `liveModels=0`, and `liveData=0`. The
run reported zero console errors, zero console warnings, and zero page errors.
This is the first headed proof that the current artifact's successful engine
ownership returns to zero across repeated task replacement, while also
covering held-input release on blur. Allocator behavior under unrelated
workloads and browser-process shutdown remains open.

The machine-readable record is
`lifecycleEvidence.headedBrowserResourceSoak` in
`nw-core/docs/marble-physics-manifest.json`.

## Headed Marble all-rung render/input matrix — 2026-09-16

A fresh headed Chromium page repeated the real Games → Attention → Marble Maze
launch and Space-start route for every rung 1 through 16, using seed 17 and a
15-second test-only budget. Every rung selected the official MuJoCo engine,
entered RUNNING, rendered the expected decoded board dimensions/hole count and
marble count, accepted a 120 ms held ArrowRight input, and exited cleanly.
The matrix included the 4-marble rung 13 and the dense 12×10 rung 16 board;
all 16 rungs recorded zero console errors, zero console warnings, and zero
page errors.

The machine-readable dimensions and counts are in
`lifecycleEvidence.headedBrowserRungMatrix` in
`nw-core/docs/marble-physics-manifest.json`. This closes the headed
all-rung start/render/input smoke requirement; it does not replace complete
solved/lost trajectories for every generated board or synchronized source/GPU
pixel acceptance.

## Marble renderer map-start parity — 2026-09-16

The browser renderer's first-frame material path now keeps each marble colour,
roughness, and normal texture complete while its PNG is being decoded. The
native renderer uploads those maps synchronously before its first colour pass;
the browser cannot make that same event-loop guarantee, so the previous 1×1
placeholder could briefly be an incomplete WebGL texture. The placeholder now
uses the same linear filtering and wrap modes as the eventual upload, and the
image requests use asynchronous decode with high fetch priority. The renderer
contract regression checks this startup path and the existing fallback remains
explicit when a map is missing.

A fresh headed Chromium run reached the real Games → Attention → Marble Maze
route, created the WebGL2 renderer before Space-start, and observed all three
maps loaded (`marbleMapsLoaded=3`, `marbleMapsFailed=false`) before the first
RUNNING tray. The official MuJoCo engine remained active and the page recorded
no new console diagnostics. This reduces the first-frame material mismatch;
cross-GPU raster/pixel identity remains the separate MM-005 open item.

## Marble wall-order differential expansion — 2026-09-16

The native/browser MuJoCo trajectory oracle now replays each mirrored L-corner
in both serialized wall orders: vertical-first and horizontal-first. This
adds four order-permutation cases to the four directional corners, preserving
120 frames at 120 Hz for each case. The complete oracle now passes 45 scenarios
and 3,072 compared per-frame states with the same exact discrete events and
sub-microtolerance continuous-field differences. This specifically guards
against contact-iteration order dependence; arbitrary generated-board
solved/lost sessions and synchronized GPU pixels remain separate open work.

## Marble generated-board trajectory matrix — 2026-09-16

The native/browser MuJoCo trajectory oracle now runs a deterministic 120-frame
held-tilt trace against every board already covered by the board/MJCF transport
oracle: all 16 rungs and seeds `0`, `1`, `17`, `314159`, and `1073741823`.
This expands the complete source/native-vs-WASM differential to 110 scenarios
and 12,492 compared per-frame states. Hole ownership, rolling/falling/home/
lost state, impact events, and aggregate counts remain exact. The longer
generated traces use separate limits of `1e-8 m`, `1e-7 m/s`, `2e-8`
quaternion, and `2e-7 rad/s` for the small native/WASM numerical drift exposed
by long contact chains; the controlled cases retain the tighter limits. This
is still a dynamic trace smoke, not a claim that every generated board has a
solved and lost real-browser session; those lifecycle replays and synchronized
GPU pixel identity remain open.

## Marble options persistence replay — 2026-09-16

The headed browser route changed the real Marble options to rung 2, eight
trays, adaptive off, shadows off, and the source-selected budget (`seconds=0`),
applied them, reloaded the page, and reopened Marble Maze. The next READY
controller state retained rung 2, eight trials, board seed `889418965`, and a
45-second rung-derived budget. The persisted key is
`neural-workshop.marble-maze.options.v1`; generated-board result persistence
and complete multi-trial browser replays remain open.

## Marble generated-board headed matrix — 2026-09-16

A fresh headed browser run repeated the real menu launch and held-input start
for all 80 board/MJCF cases: rungs 1–16 with seeds `0`, `1`, `17`, `314159`,
and `1073741823`. Every case entered RUNNING on official MuJoCo, reported its
decoded dimensions, hole count, and marble count, accepted 120 ms of
ArrowRight input, and finished with zero console errors, warnings, or page
errors. The run seeds decoded to board seeds `827307999`, `288545018`,
`889418965`, `413098107`, and `695157754`, respectively. This is complete
generated-board start/render/input coverage; solved/lost physical sessions for
every generated board remain a separate requirement.

## Numberology stateful controller slice — 2026-09-16

The active optimized Stage1 artifact now includes
`nw-core/src/tasks/numberology_game.elisa`, built from clean Elisa compiler
`main@8617216995bc0801785928e2bc0cf8c73200df3d`, ten commits ahead and zero
commits behind fetched `origin/main@45cb0ded70e7e8c8a41d21c63a09939706322ca4`.
The source fingerprint is
`9de69658a554a61ac1679e3cd52398ea73800adf700fb0c51d7a636324dceef9`; the
selected Stage1 product is
`eda6d29a7c9217c22b3b8210c134e776f5b0d3232fd902b8e4bd0927d7be2441`.

The controller is source-backed rather than a canned answer table. It owns
the generated sequence, per-run MT19937 stream, signed typed-answer buffer,
source rule parameters and explanation, grading, adaptive session result, and
fixed state copied out of the temporary generation region. The common API
exports stable task ID `numberology = 1263422208`, text/action dispatch,
read-only term/info accessors, `SceneNumberology` rendering, and idempotent
destroy.

`test/numberology_game_smoke.mjs` passes against the active 910,439-byte
`build/nwcore.wasm`
(`3033bc59986c00dc905543574ab057f7160693f764394ffc7c1922ce1ea4a024`),
covering option rejection, deterministic generation, typed lifecycle, Enter
grading, judged-to-next progression, adaptive state, explanation fields,
rendering, and cleanup. A headed browser route passes Games → Reasoning →
Numberology → Space → typed answer → Enter with zero console errors/warnings.
The complete configured artifact suite also passes. This remains partial
GAME-033/API-001 evidence: options UI/persistence, full result/replay
acceptance, native/Python/SDL adapters, exhaustive seed differential replay,
and the all-shell protocol gate remain open; the compiler still reports 21
declined concurrency-runtime bodies.

## In the Dark stateful controller slice and latest compiler product — 2026-09-16

In the Dark now has a source-backed common-v1 controller in
`src/tasks/inthedark_game.elisa`, built into the active optimized Stage1
artifact from `Elisa-compiler/main@8617216995bc0801785928e2bc0cf8c73200df3d`.
The checkout is ten commits ahead and zero commits behind fetched
`origin/main@45cb0ded70e7e8c8a41d21c63a09939706322ca4`; it contains the two
current compiler-source edits and is therefore not called clean. The Stage1
product was freshly reseeded with the port-pinned Stage0 using the official
compiler script. The audited source fingerprint is
`077deecd2117547792e153a5794fd57b44e5b19e3d9508b6b3e67bad06d483c1`, and the
external product hash is
`03fb7200424b6849ea3243c33e774270b4e8909a080136d05092251254b52024`.

The controller owns the source-generated room walk, hidden lamp/colour state,
question/answer arrays, timed room transitions, all-question grading,
adaptive rung movement, and the 800 ms feedback deadline. It copies generated
data out of the temporary source arena before destroying it and renders
through `SceneInTheDark` without exposing hidden answers in the asking phase.
The common API exposes stable ID `in_the_dark = 1343235803`, typed colour
actions, state, room/question accessors, render, and idempotent destroy.
`test/inthedark_game_smoke.mjs` passes option rejection, deterministic
generation, timed walking, answer concealment, wrong/perfect grading,
feedback gating, adaptive movement, rendering, and cleanup.

The current `build/nwcore.wasm` is 554,011 bytes with SHA-256
`60e62ea897749f5eaeddcbcc2b1816def0bccb82dabb4eb70eb1f0a779468105`; its
linked `build/nwcore_wasm.o` is
`7e4957b7de5baf7a722c02ded43483713be17551cfce13d15391e5997a435dd7`. The
complete configured artifact suite passes, including the In the Dark and Fog
of War smokes
and all Marble browser/MuJoCo/board/trajectory checks. This is partial
GAME-003/API-001 evidence: the source-derived options UI, headed real-menu
replay, native/Python/SDL adapters, exhaustive seed differential, broader
result/exit/resource acceptance, and final all-shell protocol gate remain
open. The 21 declined concurrency-runtime bodies also remain open compiler
gate work.

## Fog of War stateful controller slice — 2026-09-16

Fog of War now has a source-backed common-v1 controller in
`src/tasks/fog_game.elisa`, built into the active optimized Stage1 artifact
from `Elisa-compiler/main@8617216995bc0801785928e2bc0cf8c73200df3d`. The
selected checkout is ten commits ahead and zero commits behind fetched
`origin/main@45cb0ded70e7e8c8a41d21c63a0993970634`; it contains the two
compiler-source edits represented by the audited fingerprint
`077deecd2117547792e153a5794fd57b44e5b19e3d9508b6b3e67bad06d483c1` and is
therefore not called clean. Its Stage1 product was freshly reseeded from the
port-pinned Stage0 through the official seed script before this artifact was
emitted.

The controller owns the source's 25×15 braided world, per-world deal-seed
stream, radius-based wall-shadow-free visibility, optional reveal persistence,
unique walked-cell coverage, directional bump count, move budget, world
feedback, and run completion. It copies the generated open mask out of the
temporary source arena before destroying that arena. The common API exposes
stable task ID `fog_of_war = 703034768`, common state, additive info/cell
accessors, `START/STAY/UP/DOWN/LEFT/RIGHT`, the existing `SceneFogOfWar`
display list, and idempotent destruction. The active browser route is real:
Games → Working memory → Fog of War → Space → arrow movement. A wall bump
increments the move/bump counters but leaves the display-list bytes unchanged.

`node test/fog_game_smoke.mjs` passes option rejection, same-seed world and
initial-sight replay, visibility and initial-coverage invariants, bump pixel
stability, legal movement, one-world budget completion, DONE/replay lifecycle,
persistent per-world reveal behavior, rendering, and cleanup. The full
`bash scripts/test_wasm_artifact.sh build/nwcore.wasm` gate also passes with
421 differential cases, 720 session frames, batch/menu/task-hub/task-frame
ABIs, all current stateful smokes, common-v1, and the full Marble suite. A
headed Chromium check reported zero console errors or warnings while launching
and moving the Fog task.

This remains partial GAME-004/API-001 evidence: the source-derived options UI
and persistence, native/Python/SDL adapters, exhaustive original-controller
differential replays, full focus/exit/resource acceptance, and final all-shell
protocol gate remain open. The compiler still reports 21 declined
concurrency-runtime bodies, so this is not a full compiler-gate result.

## Latest Elisa optimization checkout revalidation — 2026-09-16

The current production build was rerun with the clean external Elisa compiler
checkout at `main@5329edfdbefa27b5c1c51253da0073256ed51058`. It is eleven
commits ahead of fetched `origin/main@45cb0ded70e7e8c8a41d21c63a09939706322ca4`
and zero behind. The source fingerprint is
`9de69658a554a61ac1679e3cd52398ea73800adf700fb0c51d7a636324dceef9`; the
Stage1 product used for this build was freshly reseeded into the isolated path
`Elisa-compiler/build/stage1-from-current-stage0-20260916` with the newer
sibling Stage0 candidate (SHA-256
`529a48195a1892fdcc07cf9bc40fc798c9f497938bbbc4df87ece58767e000d7`). Its
product SHA-256 is
`c4fe7e9c2012558aa2a37293aba3f92dbd1f78dbd005d571ffba42e9295e5173`.
A direct reseed with the port-pinned Stage0 was attempted, but that older
Stage0 rejected current Stage1 parser sources; the atomic seed path did not
replace the canonical product.

The guarded `-O2` build accepted the checkout through the isolated latest
product and reran the full
configured artifact suite. The active WASM remains 554,011 bytes, SHA-256
`60e62ea897749f5eaeddcbcc2b1816def0bccb82dabb4eb70eb1f0a779468105`, with
linked Stage1 object SHA-256
`7e4957b7de5baf7a722c02ded43483713be17551cfce13d15391e5997a435dd7`.
This confirms the optimization-bearing latest local compiler product is the
one used by the port; the 21 declined concurrency-runtime bodies remain an
explicit compiler-gate limitation. The no-Stage0 product smoke passes, and
direct targeted O0/O2/O3 runs pass for the two fixtures that timed out during
the long sweep. The 159-fixture latest-product sweep remains pending a
quiescent-host rerun because separate concurrent-workload runs reported
load-sensitive timeouts; the older byte-identical gen2 product passes that
historical sweep.

## Transactional browser result ledger — 2026-09-16

The browser shell now persists completed Marble Maze runs through the versioned
`neural-workshop.results.v1` ledger in `shells/web/result-store.js`. Records are
validated before commit, repeated writes for one session ID upsert instead of
duplicating, and import/export are explicit JSON operations. Storage failures
and malformed imports are surfaced as failures while preserving the prior
ledger value. The shell provides `Export results` and `Import results` controls;
Marble's opt-in test hook exposes copied persisted records for browser tests.

`node test/result_store_test.mjs` and
`node test/marble_renderer_contract_test.mjs` pass. A headed Chromium run
through the real Games → Attention → Marble Maze path, using the active
optimized artifact with one 15-second rung-1 trial, timed out normally and
reached DONE with `persistence="saved"`. The resulting single record survived
a full page reload with no duplicate. This closes the browser-side durable
Marble result write and backup path, but not native atomic-file persistence,
profiles/statistics/progress graphs, all-game result adapters, or complete
MM-004/APP-005 parity.

## Concentration stateful controller and browser route — 2026-09-16

Concentration is now the eleventh source-backed common-v1 browser controller.
`src/tasks/concentration_game.elisa` keeps the source `Concentration::Board`
semantics while replacing arena-backed arrays with fixed controller storage
that survives ABI calls. It retains the source MT19937 stream, pair/card
identity, the two flipped slots, the physical-card identity sets used for
lapse scoring, turn count, matched state, verdict, cursor, peek deadline, and
mismatch-hide deadline. Each operation reconstructs a temporary source board,
calls the source kernel, copies the complete board back, and releases the
temporary representation; no arena-backed board is retained between calls.

The controller validates the source option sets: pair counts
`4,6,8,10,12,15,18,21,24,30,36,42,50`, picture/sound medium, peek durations
`0,500,1000,2000,3000,5000`, mismatch-hide durations
`300,500,700,900,1200,1600,2000`, and the show-turns/coach flags. It exposes
`START=0` and `SELECT=1`, with zero-based card-slot selection. Its phases are
READY, PEEK, PLAYING, and DONE. Picture mode waits through the source peek
deadline; sound mode starts in PLAYING. `advance` applies `peek_over` and
resolves delayed mismatches at their exact controller deadlines. The
source-derived DONE message reports turns and elapsed seconds, while the
verdict reports a clean run versus one or more identity-aware lapses.

The common runtime now includes stable task ID `concentration = 1179922742`,
allocates `ConcentrationGame::Run`, dispatches action and pointer-card input,
serializes twelve common state fields, renders through `SceneConcentration`,
and exposes additive `nw_api_v1_concentration_info` and
`nw_api_v1_concentration_card` accessors. The browser route is real:
Games → Long-term memory → Concentration → Space. It uses seed `17` and the
source-shaped default `(8, 0, 0, 900, 1, 0)`, schedules monotonic browser
advances for peek/mismatch deadlines, maps pointer-down card coordinates using
the same reference layout as the scene, and destroys/recreates the handle on
task replacement, exit, and replay. Picture mode currently uses a generated,
self-contained 64-card fallback image pool with stable asset IDs `1000..1063`;
sound mode uses the scene's non-image projection. Replacing that fallback with
the original media catalog remains a separate visual-fidelity task.

Focused verification passed:

1. `node test/concentration_game_smoke.mjs` covers stable ID/support, invalid
   options, deterministic same-seed dealing, READY/PEEK/PLAYING/DONE phases,
   source identity scoring, pointer selection, delayed mismatch resolution,
   picture peek and sound-mode behavior, display-list rendering, and
   idempotent destruction.
2. `python3 test/catalog_audit.py` passes with 45 stable IDs and the
   Concentration controller/kernel/scene/export mapping.
3. The browser module passes `node --check`; a headed Chromium route reached
   PLAYING with 16 rendered cards, accepted two real card pointer selections,
   advanced the mismatch timer, and reported zero console errors, warnings,
   or page errors.
4. The complete artifact gate includes the new Concentration smoke.

The current optimized artifact is `build/nwcore.wasm`, 570,813 bytes, SHA-256
`33956ada9046bd4d6abced73446739b68109bffb3f69396f509c8a9e91ec63c2`; its
linked `build/nwcore_wasm.o` SHA-256 is
`785ef2736a031e0e0bf72c64849992724ff0c5d9e82b1cebd58fe49852044884`. It was
emitted through `scripts/build_latest_stage1_wasm.sh` using clean local
Elisa-compiler `main@5329edfdbefa27b5c1c51253da0073256ed51058`, source
fingerprint `9de69658a554a61ac1679e3cd52398ea73800adf700fb0c51d7a636324dceef9`,
and isolated Stage1 product
`build/stage1-from-current-stage0-20260916` with SHA-256
`c4fe7e9c2012558aa2a37293aba3f92dbd1f78dbd005d571ffba42e9295e5173`. The
newer sibling Stage0 candidate used to reseed that product is SHA-256
`529a48195a1892fdcc07cf9bc40fc798c9f497938bbbc4df87ece58767e000d7`.

This closes only the Concentration controller/browser slice, not the full
GAME-006/API-001 requirement. Original media parity, source-derived options
UI and persistence, native/Python/SDL adapters, exhaustive source-versus-port
replay, full result/exit/resource acceptance, and snapshot/effects support
remain open. The latest compiler still reports 21 declined
concurrency-runtime bodies, and the long 159-fixture O0/O2/O3 parity sweep
still requires a quiescent-host rerun after separate load-sensitive
timeouts.

## Seen It Before? controller and headed browser route — 2026-09-16

Seen It Before? now has a source-traced common-v1 controller in
`src/tasks/recognition_game.elisa`, connected to the existing
`src/scene_recognition.elisa` scene and the browser task-hub entry. The
controller preserves the source's six option dimensions, seeded MT19937 deal
planning, minimum repeat lag, one-repeat-per-fresh-identity rule, picture
study timeout, sound replay phase, optional per-answer feedback, four-way
scoring, and DONE summary. A fixed 500-item identity store is used across ABI
calls; the source filesystem media pool is deliberately not smuggled into the
WASM kernel. The browser installs stable synthetic picture assets `2000..2499`
and keeps the controller, not JavaScript, authoritative for old/new answers.

The common API adds stable task ID `recognition = 3372563504`, create-option
validation, `START/SEEN/NEW/REPLAY` actions, left/right/R key mapping, primary
pointer button mapping, timed `advance`, twelve common state fields, additive
`nw_api_v1_recognition_info` fields, and
`nw_api_v1_recognition_item` fields. Feedback and completed runs are mapped to
the scene's terminal presentation phase, and the scene sprite was corrected to
use the display-list primitive's center coordinates; the original first
implementation visibly overlapped the buttons because it passed a bottom-left
corner to a center-based primitive.

Focused verification passed:

1. `node test/recognition_game_smoke.mjs` covers stable ID/support, invalid
   options, same-seed planned identity traces, keyboard and pointer answers,
   correct scoring, feedback deadlines, picture hiding, sound replay, frame
   decoding, and idempotent cleanup.
2. `python3 test/catalog_audit.py`, extracted browser-module `node --check`,
   and `git diff --check` pass.
3. A headed Chromium route passed Games → Long-term memory → Seen It Before? →
   Enter → Space, rendered both answer buttons and the synthetic picture,
   accepted ArrowRight, and advanced to the next item without page, console,
   or warning output. The visual checkpoint is
   `output/playwright/recognition-playing-fixed-2.png`.

The latest optimized artifact is 580,423 bytes with SHA-256
`33b6f7e4ceec83157bb5f18013bb3aa0df1c373adbac6725b5cfb4c4ae753dfa`; its
linked object is `b4fbcacade7720e3ee6253b98d8e227994194c505570715110465e6d44d3df79`.
It was emitted directly through the latest external Elisa Stage1 product at
`5329edfdbefa27b5c1c51253da0073256ed51058` and isolated product hash
`c4fe7e9c2012558aa2a37293aba3f92dbd1f78dbd005d571ffba42e9295e5173`.

This closes only the Recognition controller/browser slice. Original image and
sound dataset parity, real sound effects, source-derived options UI and
persistence, native/Python/SDL adapters, exhaustive source-versus-port replay,
full result/exit/resource acceptance, and snapshot/effects support remain open.
The complete post-change artifact gate still needs a quiescent-host rerun; the
known 21 declined concurrency-runtime bodies and compiler parity sweep remain
explicitly open.

## Current Out of Sight slice — 2026-09-16

Out of Sight is the twentieth source-backed common-v1 controller in the current
artifact. Its stable ID is `out_of_sight` and its unsigned FNV-1a task ID is
`1771687311`. The reference contract is
`original-neural-workshop-enhanced/neural_workshop/ui/outofsight.py`; the
portable source kernel is `src/tasks/outofsight.elisa`, the display projection
is `src/scene_outofsight.elisa`, and the fixed-storage ABI adapter is
`src/tasks/outofsight_game.elisa`.

The six validated option slots are `(dots, targets, speed_percent,
crossing_gap_ms, blind_count, packed_extra)`. Direct domains are dots
`3,4,5,6,8,10,12,15,20,25,30`, targets `1,2,3,4,5,6,8,10,12,15`, speed
`8,12,16,22,30,40,55,75`, crossing gaps `0,600,900,1200,1600,2200,3000,5000`,
and blind counts `0,1,2,3,4,5,6,8`. The packed field is mixed-radix:
`width_index + 6*probe_index + 42*round_index + 336*adaptive`, with widths
`4,6,9,12,16,20`, probes `2,4,6,8,10,15,20`, rounds `1,2,3,5,8,10,15,20`,
and an adaptive bit. The browser default is `(8,2,16,1600,3,476)`, which
decodes to nine-unit blind width, six probes, five rounds, and adaptive mode;
the browser route is Games → Attention → Out of Sight.

The controller has explicit READY, CUEING, TRACKING, REVEALING, and DONE
phases. Space/Enter dispatch START; `J` dispatches MINE and `F` dispatches
NOT_MINE. The controller, not JavaScript, owns the flock coordinates and
velocities, target identities, crossing and probe deadlines, blind slab
geometry, hidden markers, answer grading, reaction measurements, round
results, and adaptive target count. `info` exposes the common state plus
source options, reaction/accuracy totals, probe timing, and last-round result;
`value` exposes dot rows, blind slab rows, and completed-round result rows.

The source kernel uses arena-backed `Flock` and `Blinds` values, so the adapter
copies them into fixed controller arrays before returning from every ABI call.
The actual generated blind count is copied back separately from the configured
maximum; this prevents rendering and later source calls from reading unused
slab rows. No source arena pointer crosses the common-v1 boundary, and render
is read-only.

Focused evidence is `test/outofsight_game_smoke.mjs`. It verifies stable ID and
support discovery, direct and packed option rejection, deterministic seeded
replay, source-shaped dot/blind values, CUEING → TRACKING → REVEALING → DONE
transitions, J/F grading, late answers, result accessors, display-list text,
and idempotent destruction. The complete `scripts/test_wasm_artifact.sh` run
passes 421 differential cases, 720 session frames, 6 batch, 3 menu, 4 task-hub,
45 stateless task-frame cases, all twenty current stateful-controller smokes,
common runtime checks, and the Marble browser/renderer/MuJoCo/board/trajectory
suite. The expected MuJoCo partial-cleanup diagnostic remains a passing
recovery assertion.

A headed Playwright replay also reached Games → Attention → Out of Sight,
started with Space, advanced into TRACKING, accepted `J`, and reached
REVEALING with zero console errors, warnings, or page errors. The visual
checkpoint is `output/playwright/outofsight-live.png`.

The authoritative optimized artifact for this slice is `build/nwcore.wasm`,
751,845 bytes, SHA-256
`f6f5747a707048149d25226dd8cad3e41b242a95e7271eb930661cf4c15af2fd`; the
linked object SHA-256 is
`7667065bc57508b69c2eb1d839c27ebc207bc345fe2829e02eebe064c4461cc9`. It was
emitted with `-emit obj -O2 -target-triple wasm32-unknown-wasi` by the clean
latest local Elisa checkout `main@8e0d7888642b3963d0e5ddec694789a9781baa82`,
which is 19 commits ahead of fetched `origin/main@45cb0ded70e7e8c8a41d21c63a09939706322ca4`
and zero behind. The canonical Stage1 product is
`Elisa-compiler/bin/elisac-stage1`, SHA-256
`5560548da3b2a57c4ee55b56096909e96ebdfcc1448f8f3c7396b8c81ffc8999`; the
compiler source fingerprint is
`9de69658a554a61ac1679e3cd52398ea73800adf700fb0c51d7a636324dceef9`.

This closes only the Out of Sight common-v1/browser slice. Pixel-level parity
with the original Python/pyglet renderer, source-derived options UI and
persistence, native/Python/SDL adapters, exhaustive Python-versus-WASM replay,
snapshot/effect transport, and the full compiler gate remain open. Stage1
continues to report 21 declined concurrency-runtime bodies, so the latest
compiler has been used for the port artifact without claiming a completed
compiler certification.

## Current Marble Maze controller replay evidence — 2026-09-16

A fresh headed Playwright replay against the same localhost artifact exercised
the ordinary controller keys after a real Games → Attention → Marble Maze
launch. Holding ArrowLeft changed the authoritative tray roll to `-0.036`
radians; `L` returned roll and pitch to zero; and `R` rebuilt the native
simulation while resetting both physics elapsed time and the controller clock
(`controllerElapsedMs=400` at the next observed frame). `C` opened the real
five-row options screen, changing and applying the tray-count option rebuilt
the run with the new option, and Escape returned to the task hub with
`modelsCreated=modelsDeleted` and `dataCreated=dataDeleted`. Dispatching a
window blur cleared the held direction mask from `1` to `0`. The replay
reported zero page, console-error, or console-warning diagnostics.

This closes the ordinary keyboard/options/focus lifecycle evidence for MM-004
and MM-006. It does not close the broader generated-board solve matrix,
source-versus-WASM trajectory acceptance, synchronized pyglet/WebGL2 pixel
parity, or the remaining full-session/result requirements.

The MuJoCo loader also now has a bounded 15-second timeout through
`MARBLE_MUJOCO_LOAD_TIMEOUT_MS`. Its rejection and pending-load timeout are
covered by `node test/marble_maze_mujoco_test.mjs`; a normal headed localhost
load still selected the official MuJoCo engine. This prevents a browser-side
engine fetch/instantiate stall from presenting as an indefinite page load. The
fallback remains explicitly labeled and is not a claim of native physics
identity.

## Marble physics retry and live diagnostic — 2026-09-16

The failure path now exposes a `Retry Marble physics` button after a MuJoCo
load rejection, but only while no Marble simulation is active. This keeps the
shell usable after a timeout or rejected load while preventing a physics
implementation from being swapped underneath a running controller.

A headed Chromium replay at
`?marble-test-hooks=1&marble-force-fallback=1` initially showed
`title screen · physics fallback · retry available`, with the single expected
injection warning and zero console errors. Clicking the retry control loaded
the official MuJoCo implementation, hid the control, and left zero new
console errors or warnings. Both `window.__nw.marblePhysicsEngine` and the
test-gated `marbleDebug.engine` reported `mujoco` after the retry. The public
diagnostic is now a live getter, so it cannot retain the initialization-time
fallback value. Static coverage is in
`test/marble_renderer_contract_test.mjs`; the machine-readable record is
`lifecycleEvidence.retry` in `docs/marble-physics-manifest.json`.

The same forced-fallback page was then driven through the real menu and Space
start path. While the fallback tray was active, the retry control remained
hidden and the status continued to identify `physics fallback`; the page had
zero console errors. This verifies the active-run exclusion in the browser,
not only in the source contract.

The failure-injection route `?marble-test-hooks=1&marble-force-fallback=1&marble-force-retry-failure=1` now leaves the retry control visible and reports
`physics fallback · retry failed · retry available`, with zero console errors.
This closes the exercised load-retry success/failure-copy and diagnostic slice.
It does not claim fallback physics identity or offline retry success.

## Marble fullscreen shortcut — 2026-09-16

The native Marble Maze maps F11 to `display.toggle_fullscreen()`. The browser
task now recognizes F11 when the embedding browser delivers it, calls the
guarded Fullscreen API, and refits/redraws on `fullscreenchange`. Browsers that
reserve F11 for their own chrome remain a platform capability boundary; the
page handles a delivered-but-denied request without an unhandled rejection.
The source contract is covered by `test/marble_renderer_contract_test.mjs`.

## Marble zero-delta input release — 2026-09-16

The native `ui/marblemaze.py:update()` clears its fractional held-key
accumulator whenever no direction is held, even for an idle `dt == 0` call.
Both browser adapters now apply that release rule before returning from a
zero-delta `advance()`. Browser and MuJoCo adapter regressions cover the
case, preventing blur/release callbacks from carrying a stale partial nudge
into a later frame or replacement tray. Broader arbitrary-contact and
complete-play-session parity remains open.

## Core WASM startup timeout — 2026-09-16

The shared `nwcore.wasm` fetch now has a fixed 15-second production deadline.
When `AbortController` is available, a stalled request is aborted after the
bounded promise has first rejected with the actionable timeout error; this
preserves the real cause instead of exposing only a generic `AbortError`. The
timer is cleared on both success and failure. The existing `file://` branch
continues to provide `scripts/serve_web.sh` guidance, while served HTTP pages
show the fetch status or timeout detail.

The debug-only route
`?marble-test-hooks=1&core-wasm-timeout-ms=25` was exercised with a delayed
`nwcore.wasm` request. The page left `loading…` and displayed
`WASM core could not load: WASM core load timed out after 25ms`. Static coverage
is in `test/marble_renderer_contract_test.mjs`; the browser check used a
single temporary session, which has been closed. This resolves the shared-core
indefinite-loading path, but not the broader offline-server/browser matrix.

The same quiescent run of `scripts/build_latest_stage1_wasm.sh` passed the full
configured artifact suite again. The selected Elisa compiler is
`main@51325f58df42f1c7162b9a27841d756dac3c9b9d`, exactly matching fetched
`origin/main`; its reseeded Stage1 product is
`4f20f6ab1bdc2349ac2e9f0102e6aa893cb3710bfe83735f6ad4cce4ebc8427f`. The
active WASM and linked object remain
`a5b1a55981c92eced1994066aa474999a0f6446a4340a44524035d6f52cdaa24` and
`2f961bd2827465e0529525e830463fbc99fce93c4d9ea4af8a61bdb4481004ee`.
The suite again passed 421 differential cases, 720 session frames, all current
controller smokes, and the Marble 110-scenario/12,492-state trajectory gate.
Stage1's 21 declined concurrency-runtime bodies remain an explicit compiler
gate caveat.

## Differential fixture path correction and compiler-gate follow-up — 2026-09-16

The Elisa differential fixtures had a stale include root for the removed
`worktrees/elisa-core-nw` checkout. All 129 affected `.elisa` fixtures under
`src/` and `test/` now resolve runtime, RNG, math, and file-I/O includes from
the current canonical Elisa-core checkout at `../../Go projects/Elisa-core`.
The Stage0 compiler reached compile and link for the `pyset` fixture through
the corrected path; this removes the earlier missing-runtime-file failure.

The disposable native `pyset` process then remained in macOS `dyld_start` at
zero CPU while unrelated compiler/parity jobs were active on the host, so it
was stopped without claiming a differential pass. A quiescent-host rerun of
`test/check_harness_test.sh` and the complete `scripts/check.sh` matrix remains
required.

The port-owned toolchain refresh was not silently forced through runtime drift:
the guard identified differences in `arena.elisa`, `debug_referee.elisai`, and
`wasm_component_runtime.elisa` between Elisa-core and the clean external
Elisa-compiler checkout. A forced Stage0/Stage1 refresh reached the
self-hosted runtime-object build but hit the same host-level loader stall and
was stopped. The external compiler checkout is clean again, so no partial
compiler provenance is presented as verified. The active browser WASM remains
the independently verified latest Stage1 artifact documented in the current
optimized checkpoint.

## Marble direct-step boundary and current-artifact regression — 2026-09-16

The fallback and official MuJoCo Marble adapters now share the same
non-positive/non-finite direct-step behavior. A direct `step(0)`, `step(-1)`,
`step(Infinity)`, or `step(NaN)` is a no-op, so malformed replay data or a
paused callback cannot rewind elapsed time, advance the fallback physics in
reverse, or enter an unbounded loop. The production `advance()` path still
owns the source-compatible non-negative frame clamp and fixed-step remainder
loop; this guard covers callers that use the lower-level adapter directly.

The browser and MuJoCo Marble tests both cover the boundary and pass. The
current-artifact suite passed again: 421 differential cases, 720 session
frames, 6 batch, 3 menu, 4 task-hub, and 45 stateless task-frame cases; all
configured lifecycle-controller smokes; common runtime-protocol checks; and
the Marble board, renderer, MuJoCo, and 110-scenario/12,492-state trajectory
checks. The MuJoCo test's simulated partial-cleanup message is expected and
the recovery assertion passes. Native differential execution and the 21
declined compiler concurrency-runtime bodies remain open gates.

## Latest Stage1 product rebuild — 2026-09-16

The Stage1 product was regenerated after the previous artifact checkpoint, so
the production WASM was rebuilt through `scripts/build_latest_stage1_wasm.sh`
with the current product rather than leaving the browser tied to the older
binary hash. The wrapper verified
`Elisa-compiler@main=origin/main=51325f58df42f1c7162b9a27841d756dac3c9b9d`,
source fingerprint
`9de69658a554a61ac1679e3cd52398ea73800adf700fb0c51d7a636324dceef9`, and
Stage1 product SHA-256
`5ceea8b30168c8ed0eda4ef73daca748f7a22895ebf8cd444578ba0725acc762`.

The rebuilt WASM is 820,736 bytes with SHA-256
`a5b1a55981c92eced1994066aa474999a0f6446a4340a44524035d6f52cdaa24`; the
linked object is
`2f961bd2827465e0529525e830463fbc99fce93c4d9ea4af8a61bdb4481004ee`. The
complete artifact suite passed: 421 differential cases, 720 session frames,
6 batch, 3 menu, 4 task-hub, 45 stateless task-frame cases, all current
controller smokes, common runtime v1, and the Marble board/renderer/MuJoCo/
trajectory suite. The 21 declined concurrency-runtime bodies remain a
compiler-gate warning, not a passing certification.

## Latest compiler parity-smoke correction — 2026-09-16

The newest external Stage1 checkout remains the selected compiler
implementation source at
`main@51325f58df42f1c7162b9a27841d756dac3c9b9d`, matching fetched
`origin/main`. Its Stage1 product and the active browser artifact are unchanged
by this test-only correction. Four assertions in
`Elisa-compiler/test/parity/match_exhaustive_smoke.sh` still expected the old
singular diagnostic `missing variant "C"`; current Stage0 and Stage1 emit the
qualified plural `missing variants: E.C`. The assertions now match the current
contract, and the complete focused smoke passes with zero false positives.

The explicitly configured targeted run also passed the first fifteen registered
smokes through `wasm32_for_bounds_width`. It was then stopped at
`qualified_generic_scope_smoke` because its freshly linked native Stage0 child
remained in macOS loader state (`dyld_start`, zero CPU) while unrelated host
jobs were active. The owned child and temporary files were cleaned up. This is
not recorded as a compiler semantic failure or as a green full gate; a
quiescent-host rerun of that smoke and the remaining targeted set is required.
The external compiler checkout is therefore intentionally dirty only in the
parity-test file, while its implementation/runtime fingerprint, Stage1 product,
and served WASM hashes remain the recorded ones above.

## Latest compiler freshness verification — 2026-09-16

After the previous checkpoint, the external Elisa checkout advanced to
`main@def45115b1ef741e951d00fe1f65565de583dce5`, exactly matching fetched
`origin/main`; the checkout is clean. The freshness guard found no newer
compiler `.elisa`/`.elisai` source under `src` or `elisacore_std` than the
selected Stage1 product, whose SHA-256 is
`c7e91519ede2c4ad1f018d5caebacf3488416fba6b7b38975f075525088faa10`.

`bash scripts/build_latest_stage1_wasm.sh` rebuilt the active `-O2` artifact
with that product and reran the configured gate successfully: 421 differential
cases, 720 session frames, all ABI/controller smokes, the 3D-only N-Back
controller, and Marble board/renderer/MuJoCo/trajectory checks. The resulting
`build/nwcore.wasm` is 830,219 bytes with SHA-256
`380abe137dc339d2baf8acafb928ece3683f3993251a8522b49ed049dad50465`; its
linked object is
`2bba67a16185ed54d37a5da51a085c8b1ccdf4f3aa7633f33e11e08cc0d1367b`.
The HTTP server returns the same WASM hash. The compiler still reports the
known 21 declined concurrency-runtime bodies, so this is a fresh port-artifact
qualification, not a claim that the full compiler gate is complete.

## Marble renderer state restoration — 2026-09-16

The browser WebGL2 Marble renderer now matches the original
`render3d.Stage._restore()` contract after its resolved stage composite: it
re-enables alpha blending and restores the source-over equation
(`SRC_ALPHA`, `ONE_MINUS_SRC_ALPHA`) before the shell draws the status and
verdict UI. The previous browser path left blending disabled, which could
change the following 2D chrome even when the tray render was otherwise valid.
`test/marble_renderer_contract_test.mjs` guards the restoration, and the
focused Marble renderer/physics/MuJoCo/options/trajectory checks pass. This
fixes a GL-state lifecycle mismatch; exact source-versus-browser raster pixels
remain an open MM-005 requirement.

## Marble asynchronous material-settlement redraw — 2026-09-16

The original renderer has all three marble maps ready before its first 3D
colour pass. Because the browser fetches those maps asynchronously, the port
may initially render its procedural fallback, but it must redraw when the map
batch has either fully loaded or definitively failed. The previous browser
path had no such completion edge, so an otherwise successful load could remain
visually stuck on the first material until an unrelated frame-producing event.

The WebGL renderer now settles exactly three map requests, counting both
`onload` and `onerror`, and reports `onTexturesSettled` once. The shell redraws
only when the callback still belongs to the active Marble renderer/task and
also handles the already-settled-before-installation race. Disposal clears the
callback. A failed batch deliberately selects the existing procedural
fallback rather than mixing an incomplete texture set into the shader. The
contract test and focused Marble physics/MuJoCo/source-board/trajectory suite
are green.

## Marble renderer full-frame cleanup — 2026-09-16

The native `Stage._restore()` returns to a full-window viewport, unbinds the
active vertex array, and restores the theme clear colour after the stage pass.
The browser renderer previously left the viewport at the Marble stage
rectangle, which was normally hidden by the shell's 2D composite but remained
an observable WebGL lifecycle mismatch. It now restores the full physical
canvas viewport, clears the VAO binding, and restores the light/dark clear
colour alongside the existing depth/cull/sample-coverage and source-over
blend state. The renderer contract test covers this cleanup boundary.

The map upload path is also explicitly sized as WebGL2 `RGBA8`, with the
source's linear filtering and repeat/clamp wrapping. This keeps the browser's
colour, roughness, and normal sampling format aligned with the native texture
upload rather than depending on an unsized browser default.

## Latest Elisa compiler refresh after remote advance — 2026-09-16

The external Elisa compiler remote advanced beyond the previous recorded
checkpoint. After fetching `origin/main`, the selected revision is
`main@c79520ed8bf2b1144a6b10c7bf4b4ea6541bf437`, exactly matching the remote
at the build boundary. The Stage1 product is
Its current Stage1 product is
`bin/elisac-stage1`, SHA-256
`add6ee9cd6189dcbbe8138aaaf546222fe6d40130ed3d05e896da54d8701ad04`; the
freshness fingerprint remains
`9de69658a554a61ac1679e3cd52398ea73800adf700fb0c51d7a636324dceef9` with no
newer compiler source than the product.

`bash scripts/build_latest_stage1_wasm.sh` rebuilt the active `-O2` artifact
and passed the configured differential/controller/N-Back/Marble gate. The
served WASM and linked object remain
`380abe137dc339d2baf8acafb928ece3683f3993251a8522b49ed049dad50465` and
`2bba67a16185ed54d37a5da51a085c8b1ccdf4f3aa7633f33e11e08cc0d1367b`; the
compiler revision change does not alter the emitted port object. The known 21
declined concurrency-runtime bodies remain an open full-gate limitation. The
checkout now also contains the preserved concurrent edits to
`src/semantic/region_escape_stores.elisa` and
`test/fixtures/diagnostics/region_param_growth_escape.pos.elisa`; they were
made after the recorded product build and are not silently folded into the
artifact claim. The clean product fingerprint was
`9de69658a554a61ac1679e3cd52398ea73800adf700fb0c51d7a636324dceef9`; the
current dirty checkout fingerprint is
`f40bf115507281290dd5306e8b2cbbe5119977b713347739f0d6c75a6c8d98f0`. The
active compiler task subsequently also touched
`src/semantic/check_region_escape.elisa`; the final-audit worktree fingerprint
is
`9590d8a3a5224553637a6c9b44d940b2eabdf6325c5cf4d5894ca43562664012`.

## Latest Elisa compiler promotion and Marble exception cleanup — 2026-09-16

The latest clean external Elisa revision used for the active browser artifact
is `main@757eae239cf73cecb3c7ec7d0b02c30e09e51d35`, exactly matching
`origin/main`. Its Stage1 product SHA-256 is
`39f191c032fd0128e8c90ead3cb8d625cc595a1b633b84431100eab238ad2997`, and
the compiler source fingerprint remains
`9de69658a554a61ac1679e3cd52398ea73800adf700fb0c51d7a636324dceef9` with no
newer `.elisa`/`.elisai` source than the product. The active WASM and linked
object hashes remain
`380abe137dc339d2baf8acafb928ece3683f3993251a8522b49ed049dad50465` and
`2bba67a16185ed54d37a5da51a085c8b1ccdf4f3aa7633f33e11e08cc0d1367b`.
The configured artifact gate passed at this revision, including all current
ABI/controller smokes, 3D-only N-Back, and the Marble board/renderer/
MuJoCo/trajectory suite. The 21 declined concurrency-runtime bodies remain an
open broader compiler-gate limitation.

After that build boundary, the compiler task began an uncommitted follow-up in
`src/semantic/check_region_return_escape.elisa`; the current worktree
fingerprint is
`a42d0ac3c80eff0c0b9c8eda1144fce01961ad5943e7c010eb8b86b3560fa677`.
That edit is preserved and excluded from the active artifact. The browser
remains pinned to the clean `757eae23` compiler/product pair until the
follow-up is committed and rebuilt.

The Marble WebGL renderer now centralizes native post-render cleanup in
`_restoreState(width,height,dark)` and calls it from `finally`. A rendering
exception therefore cannot leak an off-screen framebuffer, stage viewport,
active VAO/program, disabled source-over blending, or a false depth-write mask
into the shell's following 2D UI batch. The renderer contract, focused Marble
suite, full artifact gate, and a headed Games → Attention → Marble Maze → Space
smoke all pass; the headed run reported zero console errors and warnings.
Exact cross-rasterizer pixel identity remains an open MM-005 item.

## Marble fallback mixed-contact correction — 2026-09-16

The bounded fallback path had one reproduced gameplay defect even though the
official MuJoCo path was green: on the canonical rung-1/board-seed
`889418965` held route, a diagonal rail rebound left the outgoing normal
velocity coupled to the old rolling spin. The next fallback floor-friction
pass consumed that rebound and parked the marble at the inner rail instead of
letting it enter the home cup.

`MarbleMazeGame.resolveWalls()` now recognizes only an outgoing wall impact
with both a meaningful normal and tangential component, then reprojects the
horizontal rolling axes to the post-impact travel vector. This approximates
the source/MuJoCo coupled floor-plus-rail contact without changing the
fallback's deliberate head-on wall skid behavior. The regression uses the
source-compatible route `W,S,S,E,E,E,N,N,N,W,S,S`, 18 held 60-Hz frames per
segment, and 36 coast frames after each level action; the fallback now reaches
`home=1`, `lost=0`, and `settled=true`.

The complete artifact gate passes, including the fallback regression, the
110-scenario official MuJoCo trajectory oracle, and all existing board/renderer
and lifecycle checks. A headed real-menu replay with MuJoCo forcibly
unavailable completed with the final summary `1 trays of 1, 0 marbles lost,
highest rung 1`, zero console errors, and only the intentional fallback
warning. This closes the reproduced canonical fallback route; arbitrary
offline fallback contact identity and broader fallback solved/lost matrices
remain open.

The same regression now performs one bounded wall projection after fallback
pair separation, because the pair solver can otherwise move a second marble
back into a rail after the first wall pass. An offline sweep covers all 80
certified boards (rungs 1–16 × seeds `0`, `1`, `17`, `314159`, and
`1073741823`) over the deterministic 120-frame E/W/N/S trace. Every checked
state remains finite and every active marble stays outside the decoded wall
boxes. This is a recorded finite-state/non-penetration guarantee for that
matrix, not a claim of arbitrary fallback trajectory identity with MuJoCo.

## Latest Elisa compiler promotion — 2026-09-16

While the previous artifact was being audited, Elisa-compiler advanced from
`757eae23` through `d785246a` to `9ce2616d`; the final artifact was therefore
rebuilt from the newest commit rather than retaining the earlier candidate.
The isolated checkout at
`/private/tmp/nw-elisa-9ce.AXUarG` was based on
`9ce2616d5cd8c286d43a3a83967a74978b0fd355`, exactly matching `origin/main` at
the build boundary. Its only working-tree changes were the three runtime
vendor files required to make the Stage1 runtime byte-identical to canonical
Elisa-core; the shared external compiler checkout's separate diagnostic edits
were not copied into the product.

The freshly seeded Stage1 product is
`fe8e2d7bac87f682186253e5b7a1787024d872e5fb71ea0dc4e3c0217dfe4e3e`; its
working-tree delta fingerprint is
`219ab68f209e45efb33a639c58bff497dbbf9d7b6f28f659ea0af917f2def831`, and its
freshness check found no newer compiler source. The `-O2` WASM candidate
passed the complete artifact gate before promotion: 421 differential cases,
720 session frames, 6 batch, 3 menu, 4 task-hub, 45 stateless task-frame,
all registered stateful controller smokes including 3D-only N-Back, all
current game smokes, browser Marble, renderer, MuJoCo, board ABI, fallback
finite/non-penetration, and 110-scenario Python/native-versus-browser
trajectory parity. The MuJoCo partial-cleanup message remains the intentional
simulated-error assertion.

The promoted files are `build/nwcore.wasm` (`69efccadb3e031853e0eedcc24ab992863650118f2a300836431b6763b350cb3`,
830,223 bytes) and `build/nwcore_wasm.o`
(`2bba67a16185ed54d37a5da51a085c8b1ccdf4f3aa7633f33e11e08cc0d1367b`). A
fresh headed Games → Attention → Marble Maze → Space replay against this
artifact reached `1 trays of 1, 0 marbles lost, highest rung 1` on official
MuJoCo with zero console errors and warnings. The port remains an
implementation backlog; this compiler promotion does not close the broader
Marble pixel/arbitrary-contact or full compiler-gate items.

## Overrun source-backed browser slice — 2026-09-17

The repaired macOS toolchain is now usable for the active port build. The
canonical external Elisa compiler checkout is
`main@bfedb0d707a00797ddd16341f21a8b6e0a9677af`, exactly matching
`origin/main`; its current Stage1 product is
`Elisa-compiler/bin/elisac-stage1`, SHA-256
`59f0d87769967c34ac5572755b60aa3373aae5aa31ad67a8aaaed38ebe9c4ae4`, with
source fingerprint
`62da6971256a5e14b5a24d6f1f1398794cae3d066511cca00cc88a8c782e31e0`.
The compiler worktree remains user-owned and unrelated compiler edits were
preserved.

The active `-O2` artifact is `build/nwcore.wasm`, 891,938 bytes, SHA-256
`2a7a40fb5f1612a80455b9991159e8db3ad1b2c7f28819053cd1b592bcd6d3bb`; the
linked object is
`11fde168cf1f2a6634e3257c810c5883153b11efdff1641473bfb274bebe271d`. The
complete configured artifact gate passed after the Overrun integration and
fallback-pool expansion, including the existing differential/API/session/
task-hub checks, 45-task catalog/stateless checks, 3D-only N-Back, every
registered controller smoke, and the full Marble parity suite. The 21 declined
concurrency-runtime bodies remain an explicit broader compiler limitation.

Overrun is now a real common-v1 browser controller, not the old generic
`Game started` card. `OverrunGame` calls the source arithmetic for start, write,
erase, timing, settlement, scoring, adaptive state, and result rows. Its fixed
offline fallback reproduces the original `SEED_TEXT` order and the source
24–44-character pool filter: 68 eligible sentences, 553 words, and 2,082
letters. The runtime exports stable task ID `1156693128`, info/value accessors,
keyboard/text/Backspace input, render, timed advance, and cleanup. The browser
route was freshly reloaded and reached Games → Attention → Overrun → Enter →
Space, READY, and TYPING with real source text; Playwright recorded zero
console errors and warnings. The visual checkpoint is
`output/playwright/overrun-browser-seed-expanded.png`, SHA-256
`caad726745fdb0488c19a448bbad0b7c57e9ee031235db0ac17db9c11a40ba86`.

This is a verified browser vertical slice, not final port closure. Remaining
Overrun work is direct Python UI/environment differential replay across rungs
and wave counts, source-exact options/persistence, focus/blur/cancel/restart
and repeated reopen checks, exact pixel/display-list checkpoints, text/IME
ownership, and native/Python/SDL adapters.

## Two Hands source-backed browser slice — 2026-09-17

Two Hands is now a real common-v1 controller and browser task route. The
controller in `src/tasks/twohands_game.elisa` keeps bounded persistent state,
rebuilds the source `TwoHands::Road` and solver views in scratch regions, and
uses the source generator, road builder, wheel press, ride advance, overrun,
and sighting functions. `src/wasm/runtime_protocol.elisa` and
`src/wasm/wasm_exports.elisa` expose stable task ID `1665677052`, validated
options, task info/value accessors, keyboard/action/pointer dispatch, timed
advance, read-state, display-list rendering, and idempotent cleanup. The
browser uses source-compatible defaults `(3, 5, 400, 1200, 1, 0)` with seed 17
and now routes Games → Attention → Two Hands to that controller instead of a
generic task card.

The focused `test/two_hands_game_smoke.mjs` passed source road generation and
replay, invalid options, keyboard/action parity, exact setting-to-running beat
timing, wheel input, pointer aim/fire, scoring, rendering, completion, and
idempotent disposal. The complete configured artifact gate passed 421
differential cases, 720 session frames, 6 batch ABI cases, 3 menu ABI cases, 4
task-hub ABI cases, 45 stateless task-frame cases, every current stateful
controller smoke including 3D-only N-Back, the Two Hands smoke, and the full
Marble physics/renderer/MuJoCo/board/fallback/trajectory suites. The expected
partial MuJoCo cleanup diagnostic remains an asserted recovery test.

The artifact was emitted with the newest local self-hosted Gen2 Stage1
compiler product `elisac-stage1-gen2` (SHA-256
`76902f1ed45dea4f934c623208dbdf6cad699dfd5dd0ea261d75da452cad173c`) from
compiler `main@bfedb0d707a00797ddd16341f21a8b6e0a9677af`, matching
`origin/main`; the compiler source fingerprint is
`74442013da271c1f412fd38aa9e154eb25b90089fa211d8296c17dc68491a770`. The
served `build/nwcore.wasm` is 934,840 bytes, SHA-256
`f8e5d28c913b2c9a3642d97363c4025cf8ac526df80d8597ce8307d361217233`, with
linked object SHA-256
`f536f5b7910d3e1cbf78c528113241a36b07f1c895b1c94deab9a75c9b22701a`.

A fresh headed Playwright replay reached READY, RUNNING, and SCORED through
the real menu, then accepted pointer movement/fire and started the next trial;
the browser console reported zero errors and warnings. The visual checkpoint
is `output/playwright/twohands-browser.png`, SHA-256
`7ab6a19aa1a50c85562926f0462b58f6a74406fd74d78eeea25c0c2cdda4e5e3`.
GAME-018 remains open for original UI/environment differential matrices,
simultaneous/opposing input, all supported options/rungs, focus-loss
cancellation, exact pixel/layout checks, repeated resource cycles,
Stage0/Stage1 parity, and native/Python/SDL adapters.

## Latest completed fast gate and compiler drift — 2026-09-18

The previously interrupted fast gate was re-polled to completion. It exited
0 with `GATE GREEN` at the latest-Stage1 build boundary
`Elisa-compiler@a4beace9a1f47b569a169072588a0023eba8afbd` equal to
`origin/main`. The boundary fingerprint was
`b4ff702ee808e104b7bd6cecfd1d6d3357112a7b2da62600bd5166c5ff7b0d92`, the
Stage1 product hash was
`a87d9a586c96442e2805a1f0c9b4f2d6fd437539e6aeefd3d6f30ef9d486ce0b`, and the
974,768-byte WASM/object hashes were
`72cd4b672736123bb3a2562f885848f0ed01862ad83e1d1073d4fafd2539f582` and
`952008613f13e7569beed3757371b3ba0c765d8bee3b1e23a2e2d7c6685d5aaf`.
The gate passed both compiler-stage differentials, all configured artifact
and controller checks, the 3D-only N-Back route, and the complete currently
registered Marble physics/board/trajectory/lifecycle checks. The slow
`gate.sh --full` tier and the broader implementation plan remain open.

The external compiler checkout changed after that boundary under a concurrent
compiler task. Its current observed dirty fingerprint is
`c94af266e349cd577d2d052494c28fe50006082fbd4359b53b5d145721bc74b6`, and its
fresh Stage1 product is
`21290051f91addb0f3a8f74710dac6bfa7991e15eb883c4bce70f2ac4d78edfc`.
Because those values differ from the gate boundary, the current product is
not certified by the recorded green run; rerun the fast gate after the
compiler worktree becomes quiescent.

**Current pinned-toolchain refresh (2026-09-18):** the repository toolchain
was rebuilt through `scripts/build-toolchain.sh` from the current selected
Elisa compiler worktree at `main@ac814e10a493f4e00693ce24a89fa2697b802275`.
Its source fingerprint is
`ed8ed996b4d7c01ce8a77310fc52166c38228628aad1178f68149f102fd55511`; the
compiler worktree remains intentionally dirty and user-owned, with its
semantic/parser changes preserved. The pinned Stage0, Stage1, and runtime
hashes are respectively
`4a3bcaab3e7e1202e40b23c5d8bcf3ac9049129572c5132b2cdff2c11128a8e8`,
`56da14b7d7500d3541c2718262b08f6d84f484aa243c10e4c4a4ecd3a4497754`, and
`1dbb59736ed498f8e602003e9504953e6f2a8bef916340882d3d4ce6df3e9e48`.
`build_wasm.sh` then emitted the current 945,341-byte artifact
`build/nwcore.wasm` with SHA-256
`79a097d46591b90b385c3c6955f432315c48b6a4c6129836fac3aee8f66dcaa3` and
linked object SHA-256
`2cd515a580be884a5a4f5d9bef3b0b45832b65575b66a9b20e0e33febaea4122`.
The configured artifact suite, including the Matrix controller and all
registered Marble checks, passed against that artifact. This refresh is not a
claim that the slow `gate.sh --full` tier or the remaining implementation
backlog is closed.

**Marble multi-trial/adaptive matrix (2026-09-18):**
`test/marble_multi_trial_session_test.mjs` is now registered in the artifact
suite. It passes three real official-MuJoCo sessions (fixed-rung two-tray,
adaptive rung-4 three-tray, and adaptive rung-16 two-tray with a 30-second
override), covering seven generated timeout trays. Each tray uses the source
50-ms frame clamp, commits the physical home/lost counts and source score bit,
crosses the 2.6-second feedback barrier, and either reaches the next
PREPARING/BOARD_READY handoff or DONE. The test verifies fixed versus adaptive
rung history, distinct board seeds, all seven retained result fields, exact
configured active time, and zero live MuJoCo models/data after every case.
This closes repeated feedback/next-board and adaptive-timeout coverage; it
does not close generated-board solved/lost route exhaustiveness, fallback
identity, cross-rasterizer pixels, or native/Python/SDL Marble adapters.

## Latest compiler capacity repair and validated artifact boundary — 2026-09-18

The newest compiler exposed a backend bug in constant-capacity handling. The
`region`/`with` binding backend was parsing capacity source spans with a
bare-decimal helper even though the normal constant folder supports named,
qualified, arithmetic, and parenthesized constants. Valid Sudoku functions
using capacities such as `ATTEMPT_REGION_BYTES` and `8 * 1024 * 1024` were
therefore declined as whole function bodies. The external compiler now parses
those capacity spans into the existing constant-expression AST and folds them
through the existing folder. The regression fixture and parity smoke are
`Elisa-compiler/test/repro/region_capacity_const_expression.elisa` and
`Elisa-compiler/test/parity/region_capacity_const_expression_smoke.sh`; the
port gate runs the smoke as `region_capacity_const_expression`.

The Crossed Wires and Sudoku scene drivers were also corrected to include the
required `scene_verdict` source and to use the reference Sudoku verdict
argument. Both stages now match the source exactly: Crossed Wires 36 frames /
1,019 commands and Sudoku 24 frames / 9,965 commands.

The latest quiescent Stage1 artifact boundary was:

- compiler `main@523b6e03988739183d4df50fcc794905ec8521ff`;
- origin reference `8d930a3b758e92af5f3d1497a944a0909dff895f`;
- source fingerprint `2d67cdb23bd68ac8a69a8504bc0d7f004505b9eb298bd428c2573dd35861598e`;
- Stage1 product SHA-256 `643119d1f61bff31a3f3f0ec2e8e21324ef3466b683d72c88c930447f189a600`;
- `build/nwcore.wasm` 1,095,131 bytes, SHA-256
  `1fff9c78104ff6d962678837c1afba9b18596b1749b6e4a9b20cd6664b109bc2`;
- linked object SHA-256
  `3dadabb11824fe50131a188fb9b2eecc3ff08332122f41cbecf907343be0770f`.

The guarded latest-Stage1 artifact build and all 25 targeted Stage1 parity
smokes passed, including the new capacity regression. The Stage1 Glyphs RSS
guard and runtime provenance check passed as well. Artifact verification
covered 421 differential cases, 720 session frames, all current ABI and
controller/browser contracts, 3D-only N-Back, and the complete registered
Marble suite: 80 generated timeout sessions, 4 held-input sessions, 3
multi-trial/adaptive sessions covering 7 trays, 80 board/MJCF cases, and 134
trajectory scenarios / 14,796 per-frame states.

The shared external compiler checkout then entered an active user-owned merge
state while a later full gate was running. Its freshness guard correctly
invalidated that gate when `codegen_expr_field_read.elisa` changed during the
Stage1 differential; those stale-product refusals are not parity failures.
The current external worktree must become quiescent before another seed and
fresh fast-gate certification. It was not reset or conflict-resolved here.

Marble remains the priority. The registered multi-trial/adaptive and physics
checks are green, while exact cross-rasterizer pixel identity, exhaustive
solved/lost generated routes, and native/Python/SDL adapter parity remain
open. The slow full compiler tier and the broader port backlog also remain
open.

## Reproducible Marble paired-pixel diagnostic — 2026-09-18

`test/marble_render_pair_test.py` now compares a same-board native reference
capture and WebGL2 capture without silently resampling or aligning them. The
recorded 768×576 pair passes explicit diagnostic limits of MAE ≤ `0.1`, RMSE ≤
`1.5`, and ≤ `0.5%` of pixels more than 10 levels apart. Its measured values
are exact-pixel fraction `0.9883196795428241`, MAE `0.05020555853843689`, RMSE
`1.0791504999862083`, maximum channel error `146`, and threshold-exceeding
fraction `0.0014218930844907408`. The comparator is a repeatable regression aid
for MM-005; it intentionally does not convert different OpenGL/WebGL sample
masks into a false exact-pixel claim.

As of 2026-09-19, this reviewed pair is part of
`scripts/test_wasm_artifact.sh`, directly after the renderer contract. The
script now changes into its resolved `nw-core` root before launching tests, so
its Python fixture imports behave identically whether the caller starts in
the repository root or in `nw-core`. A complete repository-root artifact run
exited 0 with the visual limits enforced and retained the green 134-scenario /
14,796-state Marble trajectory oracle. This is automated regression evidence,
not a claim of bit-identical OpenGL/WebGL rasterization.

The subsequent top-level fast-gate rerun was deliberately not certified:
Stage1 scene parity detected `src/semantic/check_readonly_ref.elisa` becoming
newer than the selected product, and runtime provenance also detected external
`profiler_hooks.elisa` / `runtime.elisa` drift. The gate correctly refused the
remaining Stage1 work. The corrected artifact script was separately rerun
under the sourced gate environment and exited 0, including the pixel check and
the complete 134-scenario / 14,796-state Marble trajectory oracle. Re-seed and
rerun the top-level gate after the external compiler becomes quiescent.

**Marble settlement/deadline boundary correction (2026-09-18):** the source
`MarbleMaze.update()` checks `sim.settled` before checking whether the active
clock reached the tray budget. The browser previously derived feedback text
and its ledger `timedOut` flag from elapsed time alone, so a marble that fell
into a hole on the deadline frame could be mislabeled as a timeout. The shared
`shells/web/marble-maze.js` module now provides `marbleFeedbackKind()`, and
`shells/web/index.html` uses it to preserve the source ordering; `timedOut` is
now true only for an unsettled tray. The focused browser and renderer contract
regressions pass, along with the MuJoCo, generated-session, held-play,
multi-trial, board/MJCF, trajectory, UI-options, and paired-pixel checks.

**Marble options/controller lifecycle matrix (2026-09-18):**
`test/marble_options_matrix_test.mjs` now covers all 1,344 combinations of
the 16 levels, six source trial-count choices, two adaptive settings, and
seven source time choices. It checks READY application, Space/start, fixed
time budgets, live RUNNING option resets, invalid-input rejection without
mutation, and persistent board/grain RNG identity across an options reset.
The matrix is registered in `scripts/test_wasm_artifact.sh`, so both Stage0
and Stage1 artifact runs execute it. It passes against the current served
artifact. It is controller-only;
MuJoCo contact parity, exact cross-rasterizer pixels, and native/Python/SDL
host integration remain separate open obligations.

The subsequent artifact-only `bash scripts/test_wasm_artifact.sh` also
completed green. The registered Marble portion passed the options matrix, 80
generated timeout sessions, four held-input sessions, three multi-trial/
adaptive sessions, 80 board/MJCF parity cases, and 134 native-versus-browser
trajectory scenarios covering 14,796 per-frame states. This is verification of
the served artifact and test registration; it is not a new compiler-provenance
claim while the external compiler worktree is under an active user-owned
parity run.

**Marble generated held-input matrix expansion (2026-09-18):**
`test/marble_generated_play_session_test.mjs` now passes 36 generated
held-input sessions across the complete route-driver slice of certified
single-marble rungs `1, 2, 3, 4, 6, 8, 10, 12, 14` and the five recorded run
seeds. The test derives each cell route from the transported wall geometry,
uses the controller's real board seed, drives held input through official
MuJoCo WASM, synchronizes measured elapsed time, commits the source result
row, and verifies feedback plus model/data cleanup. It includes physical home
captures and swallowed-marble losses. Nine single-marble combinations remain
unclaimed because this fixed-duration route driver does not reach a terminal
state on them, and coupled multi-marble routes remain a separate open
requirement. The focused test passes; this expands, but does not close, the
generated-board solved/lost and MM-003/MM-004 coverage obligations.

**Marble maximum-duration settlement boundary (2026-09-18):** the browser's
physical-settlement clock synchronization now preserves the source's final
frame allowance at the maximum duration option. The native
`MarbleMaze.update()` checks physical settlement after a complete capped frame,
so a 600-second tray can settle at up to 600050 ms. The controller already
accepts that `MAX_SETTLE_MS` bound, but the browser physical-settle branch had
been clamping its measured elapsed time to 600000 ms. It now uses the explicit
`MARBLE_MAX_SETTLE_MS = 600050` bound, matching the timeout path and preventing
the result-history elapsed field from losing the final 50 ms.

The renderer contract test guards the named bound and the physical-settle
dispatch. Focused Marble browser physics, renderer, and MuJoCo tests pass, as
does the complete registered artifact suite: 421 differential cases, all
current controller smokes, 1,344 option combinations, 80 generated timeout
sessions, 36 generated held-input sessions, seven multi-trial trays, 80
board/MJCF parity cases, and 134 trajectory scenarios with 14,796 per-frame
comparisons. This is a boundary correction only; the remaining exhaustive
play, fallback, pixel, and native/Python/SDL adapter work is still open.

## Full compiler gate attempt — 2026-09-19

The first `DEVELOPER_DIR=/Library/Developer/CommandLineTools bash
scripts/gate.sh --full` attempt reached the slow tier but did not produce a
valid newest-Stage1 certification. All Stage0 differential suites completed
green. During the Stage1 differential run, the user-owned external compiler
checkout changed `src/parser/parser_types_struct.elisa`; the freshness guard
therefore rejected the final nine Stage1 suites, and also rejected the latest
Stage1 artifact rebuild, Glyphs smoke, targeted Stage1 smokes, self-host
fixpoint, and Stage1 full parity as stale-product runs. The artifact and
Marble checks that ran before that boundary remained green, including 134
official trajectory scenarios / 14,796 states and 36 generated held-input
sessions.

The slow native Stage0 test suite also ran and failed only in the external
compiler's existing strict-FP/autovec expectations: one fold-warning test, one
fast-math fold test, one default-contraction test, and four backend LLVM-IR
tests expecting `contract` FP instructions. The port did not modify or revert
those compiler sources. At the terminal check the compiler was at
`dcf5ce4781c073b4669f7c85441bf82e5322a3c9` with `origin/main` at
`624baa97a608951c11a722efdb9ae20f8fae6a46`; its Stage1 product was stale and
its working tree was still user-owned and dirty. Another seed and full-gate
claim must wait until that worktree is quiescent.

## Fast-gate attempt after newest local Stage1 promotion — 2026-09-19

The newest local Stage1 promotion at
`80768ea780012e7043135e59b94e5e38fd3ac230` was source-fresh and completed the
provenance-checked WASM build. The product hash was
`2ea7adb461c5a447077dc5a9f314576ddc799418573c826b7fcbd126760853d1`, the
source fingerprint was
`9de69658a554a61ac1679e3cd52398ea73800adf700fb0c51d7a636324dceef9`, and the
served WASM/object hashes remained
`1fff9c78104ff6d962678837c1afba9b18596b1749b6e4a9b20cd6664b109bc2` and
`3dadabb11824fe50131a188fb9b2eecc3ff08332122f41cbecf907343be0770f`.
The artifact-level suite was green, including the 3D-only N-Back controller
and all current Marble physics, renderer, options, generated-session,
board/MJCF, and trajectory checks.

The subsequent fast gate was invalidated by a concurrent user-owned compiler
edit. Stage0 differential, the artifact suite, and the Stage0 fast native
compiler suite passed. Stage1 suites passed until the freshness guard observed
`src/driver/elisac_parse_error_report.elisa` changing; the remaining 16
Stage1 suites, latest artifact rebuild, Glyphs RSS smoke, and targeted Stage1
smokes were refused as stale. At terminal inspection the external checkout
was `4db52834046a88e405135f25ecffd363b6a4b2a9`, with 20 working-tree edits,
and an active `scripts/elisac_stage1.sh --seed`; 20 Elisa sources were newer
than `bin/elisac-stage1`. This is a compiler-worktree coordination state, not
a port regression. Wait for the seed and source edits to settle before the
next promotion; stale-product bypass is not allowed.

## Marble single-marble held-play coverage — 2026-09-20

`node test/marble_generated_play_session_test.mjs` passed against
`build/nwcore.wasm` (SHA-256
`26c6230f593d1a98161658c98b6106ef90384add624b514fa05a0c1551b5de5b`). The
matrix contains all five recorded run seeds on each of the nine certified
single-marble rungs: 45 physical sessions, 7 home captures and 38 swallowed-
marble losses. For the nine previously missing cases, the test-only input
driver now recenters on the measured cell, replans when physical motion
deviates from the nominal BFS edge, and steers toward the actual cup center.
Each case commits and checks the controller result row, reaches DONE, and
returns MuJoCo model/data counts to baseline. Historical 36-case descriptions
elsewhere in this file are superseded for this test only; coupled multi-marble
routes and broader adaptive, host, fallback, and pixel parity remain open.
The complete `bash scripts/test_wasm_artifact.sh` suite exited 0 on the same
artifact, including all registered controller/browser checks and the full
Marble board, trajectory, timeout, and multi-trial matrices.
An initial coupled-rung route-driver probe (rung 5, seed 0) exceeded its
120100 ms controller deadline before completing; it is deliberately excluded
from the passing matrix and confirms that multi-marble input steering remains
an open test-driver problem.

## Marble paired-render synchronization audit — 2026-09-20

The registered 768×576 diagnostic screenshot pair is not time-synchronized:
the reference shows `34s left`, while the browser capture shows `39s left`.
Although the measured pair is 98.831968% exact by pixel and passes its loose
diagnostic bounds, that metric cannot count as same-frame visual acceptance.
Regenerate a deterministic pair with matched board/RNG, pose, simulation
time, phase, assets, viewport/DPR, and theme, then compare the full stage and
review scene-region differences without masking the visible timer.

## Stage1 generic field-access scope correctness — 2026-09-20

Compiler investigation found a Stage1-only acceptance gap, not a defect in the
port's Elisa task code: a function-wide shadow-name collection let a local in
one branch hide an invalid field access on a generic parameter after the branch.
The external compiler checker now tracks binding lifetime across blocks,
branches, loops, match arms, lambdas, and comprehensions. The Stage0/Stage1
regression smoke rejects the invalid case on both compilers and accepts a valid
branch-local struct shadow on both; the neighboring field-type smoke also passes.
The updated external Stage1 product is source-fresh at
`66b8ed02cd5075ec4d3e7559187e32937699a985` plus the intentional working-tree
change, but had to be seeded at `-O0`: the guarded `-O2` and `-O3` builds each
exceeded the existing 4 GiB RSS limit and were not published. This does not
change the current port WASM artifact; it corrects Stage1 compiler acceptance
for subsequent builds. Details and hashes are in
[`compiler-issues.md`](compiler-issues.md).

## Marble generated play-session lifecycle — 2026-09-20

The coupled generated-board play driver previously continued issuing
steering/actions after the controller's configured board deadline had moved
the task into feedback, and could stop before physics finished a marble's
falling transition. The test now stops input at feedback, advances neutral
physics until settled or timeout, and follows the source timeout path:
synchronize host time, commit score, then record actual home/lost counts.
Timeout always carries a loss verdict; counts remain physics-owned. This was a
test-harness defect, not a Stage1 compiler or `marblemaze_game.elisa` defect.

The 80-case generated play matrix passes (7 physical wins, 73 physical losses),
as do focused MuJoCo, board-ABI, multi-trial, and generated-session tests. This
establishes lifecycle and cleanup coverage, not coupled-route play quality or
trajectory parity; source-vs-port action replay remains open.

## Marble paired-render gate synchronization — 2026-09-20

The registered native/browser screenshot pair reports different visible
remaining-time values (34s versus 39s), so it cannot be used as synchronized
visual acceptance. The artifact suite now runs that pair as diagnostic-only;
it no longer passes the historical pixel thresholds as a fidelity gate.
`marble_render_pair_test.py` permits threshold-based acceptance only when both
captures provide complete metadata with identical board/grain seeds, rung,
trial, elapsed time, pose, camera, viewport/DPR, theme, assets, and material
state. Each manifest must also bind to the exact PNG SHA-256 and dimensions;
valid state metadata without acceptance limits is still reported as
diagnostic-only, not PASS. A contract test checks missing metadata rejection,
mismatched-state rejection, PNG-binding rejection, synchronized acceptance,
and diagnostic-only output. MM-005 remains open pending actual synchronized
source/browser captures and visual review.

The complete `scripts/test_wasm_artifact.sh` run then passed through the final
134-scenario/14,796-state trajectory oracle. The 421-case differential, 720
session frames, registered browser/controller contracts, Marble options and
physics tests, 80 generated timeout sessions, 80 held-play sessions,
multi-trial/adaptive tests, and 80 board/MJCF parity cases were green. The
registered unsynchronized pair remained explicitly diagnostic-only. This is
verification of the gate and current artifact, not closure of MM-005.

## Marble synchronized frozen-frame comparison — 2026-09-20

Captured the original source and browser renderer at the same deterministic
state: board seed `889418965`, grain seed `3.2267631084747164`, rung 1,
trial 0, elapsed time 0, zero roll/pitch, light theme, settled three-material
set, identical camera/viewport, and 1824×1368 framebuffer at DPR 2. The
capture manifests bind each PNG to its SHA-256 and dimensions. Camera matrices
match within `5.65e-8` maximum absolute delta (the comparator's float32/float64
allowance is `2e-6`). The pair comparator reports MAE `1.19253`, exact-pixel
fraction `98.8535%`; board crop MAE is approximately `0.005`. These are
diagnostics only: there are not yet reviewed pixel bounds, so this does not
claim MM-005 acceptance.

The synchronized render audit exposed a real web-renderer layout defect:
`marbleStageRect()` had treated the source's fixed 8-framebuffer-pixel verdict
band clearance as 8 logical pixels and scaled it by DPR. At DPR 2 this
shortened the stage by 8 framebuffer pixels. The renderer now computes the
stage bottom in framebuffer coordinates and applies the fixed 8-pixel
clearance there. The browser's extra host-side title draw was removed because
the Elisa scene already owns that title and the keyboard-help footer. The
host retains the live status/verdict overlay: the common core scene supplies
a static board-less Marble placeholder rather than live physics state. The
3D renderer remains responsible for the tray frame. These were web-rendering
issues, not compiler behavior or Elisa task logic.

Verification: renderer contract tests, synchronized-pair contract tests, all
134 trajectory scenarios / 14,796 states, generated Marble lifecycle and
input matrices, and the full `bash scripts/test_wasm_artifact.sh` suite passed.
The historical unpaired 768×576 screenshot remains diagnostic-only. MM-005
still requires reviewer-approved pixel limits and review across additional
phases, themes, poses, viewport/DPR combinations, and result states.

The comparator additionally reports the header, footer, stage, stage-side
margins, and aggregate surrounding chrome, while retaining full-frame metrics.
After removing the duplicate title draw and recapturing the browser,
the stage (1714×842) remains 99.9286% exact, MAE `0.00555`, RMSE `0.4493`; the
remaining 1,052,044 chrome pixels have MAE `2.6342` (previously `2.8208`).
Thus the residual is concentrated
outside the 3D tray scene. Viewport coordinates are validated against the
hashed PNG before regional measurements; an out-of-frame viewport is rejected.
The new regional numbers are diagnostic only and do not waive review of text,
chrome, or additional render states. Full-frame exactness is now 99.1497%
(MAE `1.1139`); the refreshed capture is hash-bound in the manifest.

After adding the regional metrics and PNG-bounded viewport validation,
`bash scripts/test_wasm_artifact.sh` exited 0 through its final 134-scenario /
14,796-state Marble trajectory oracle. The regional synchronization contract,
Python syntax checks, and whitespace checks passed as well.

The complete artifact gate was rerun after removing the duplicate browser
title/status overlay; it again exited 0 through the same 134-scenario /
14,796-state trajectory oracle. The live headed browser route also reached the
seeded running Marble Maze board with WebGL2 and MuJoCo active and no duplicate
host-side chrome pass.

## Marble fixed-tilt source/browser capture — 2026-09-20

Added deterministic static-pose capture support to the browser test hook and
original-source screenshot helper. Both reject poses beyond the source's
`MAX_TILT`; production paths are unchanged. A real Games → Attention → Marble
Maze → Space browser route at board seed `889418965` was captured at roll
`+0.060` rad / pitch `-0.042` rad, elapsed 0, rung 1, trial 0, light theme,
settled materials, identical camera, 1824×1368 framebuffer, DPR 2. The
source/browser image and metadata hashes are in the manifest.

The comparator confirms synchronized camera state (maximum matrix delta
`5.65e-8`). The complete 1714×842 stage is 99.9725% exact, MAE `0.00495`,
RMSE `0.4283`; the full frame is 99.1728% exact, MAE `1.1164`. These are
diagnostic only: no reviewed pixel bounds are configured. This demonstrates
tilted geometry/camera registration at one static pose, not rolling dynamics,
arbitrary tilt paths, terminal states, theme parity, or global MM-005 closure.

## Marble Maze staggered-key rendered pair — 2026-09-21

Completed the previously missing source/browser image pair for the real
staggered rollover sequence. Both captures use the normal five-tray run, seed
17 (board seed `889418965`), rung 1, light theme, DPR 2, a 1824×1368
framebuffer, 1,250 ms, roll `-0.12`, pitch `0`, and synchronized
marble/camera/material state. The source helper replayed
`E+W:12, E:20, none:1, W:40, none:2`; the browser was launched through Games →
Attention → Marble Maze → Space and received the same ordinary overlapping
arrow-key events with exact 60-Hz fixed-frame steps. The first metadata bind
caught and corrected a fixture mismatch (source defaulted to one tray while
the browser correctly used five). The final metadata binder and required
synchronized scene-state comparator pass. The 1714×842 stage is 99.9789% exact
(MAE `0.00465`, RMSE `0.41358`); the full frame is 99.0716% exact (MAE
`1.12468`, RMSE `14.2659`). These are diagnostic metrics only, not approved
acceptance thresholds. Artifacts and the full evidence caveat are recorded in
`IMPLEMENTATION_PLAN.md`; MM-003/MM-005 coverage and reviewed
cross-rasterizer pixel limits remain open.

## Marble generated held-play coverage — 2026-09-21

Expanded verification to the complete 80-case generated board matrix (all 16
rungs × five certified run seeds) using feedback-based held-key steering and
the official MuJoCo WASM engine. The real controller input ABI drives the
physics; the route follower recenters/replans from measured marble state and
aims at the cup rather than injecting outcomes. A focused rerun on the current
artifact now classifies the three mutually exclusive terminal outcomes rather
than calling every non-win “lost”: 7 physical home captures, 41 physical
losses, and 32 source timeouts. An assertion requires those buckets to account
for every case. Every session retains its result-history/DONE checks and
MuJoCo cleanup. The complete artifact gate had passed on the latest-Stage1
artifact. Compiler provenance remained at Stage1 commit
`176c4aa2b11c7fddb1af5296f938dae1b8c67fcf`, equal to `origin/main`, through
the build. This replaces the earlier 45-case generated-play statement. At
that point it did not yet compare all 80 controller result rows against the
original Python UI; the source-replay result below supersedes that caveat. It
still does not prove every generated board solvable; those MM-003/MM-004/MM-006
checks remain open. MM-005 pixel acceptance remains separate and open.

The live browser active clock was corrected to advance the integer-ms Elisa
controller from the actual cumulative physics elapsed time, avoiding a
one-frame-early timeout caused by independent floating-point sums. The
source-replayed rung-16 timeout now agrees on terminal outcome and rounded
result elapsed time (120.016667 s physics elapsed); short rung-1 win and rung-2
loss traces also pass strict state parity. Long rung-16 native-vs-WASM
MuJoCo pose/spin parity remains open: tiny early numerical differences amplify
through contacts, so no tolerance widening is accepted as a fix. This is a
browser host/physics issue, not an Elisa compiler defect.

For result-row evidence, `bash scripts/test_marble_source_play_matrix.sh` now
replays the compact held-input trace from each of the 80 generated sessions
through the original Python 3.13.12 / MuJoCo 3.12.0 `Simulation`. All 80 rows match exactly across
terminal outcome, rounded elapsed milliseconds, home/lost counts, verdict, and
score result (7 wins, 41 physical losses, 32 timeouts). This closes generated
board terminal-result parity for the tested five run seeds per rung. It does
not erase the separate long-trace per-frame numeric divergence or prove every
possible action sequence/contact ordering.

The optional full-state trace now records contact geometry IDs/distances and
solver warmstarts for the high-rung native/WASM drift investigation. At the
first tolerance breach (rung 16, event 216), both engines have the same four
contact pairs. Copying the prior WASM wrapper state and `qacc_warmstart` into
the native replay makes the next step agree within 6.7e-15 per field, showing
that the event amplifies accumulated pre-contact floating-point divergence
rather than applying a different rule to an identical state. Their later
contact-pair sets differ at event 537 after the trajectories have diverged;
long-horizon contact-topology parity remains open.

## Marble synchronized renderer ownership audit — 2026-09-26

The source/browser review confirms the intended ownership boundary: the Elisa
scene emits the title, keyboard-help footer, and verdict band; the browser host
adds only live physics status/verdict text and composites the WebGL stage. No
duplicate host title or replacement chrome was found. The WebGL renderer mirrors
the source 4× MSAA resolve, shadow pass, camera, materials, hole clipping,
marble maps, shadow-caster rules, and tilt/quaternion transforms.

Synchronized high-rung captures measure the 3D stage at 99.8442% exact pixels
(MAE 0.04773, 0.1371% above channel threshold 10; camera maximum delta
5.643e-8). Terminal, dark-theme, tilted, rollover, and four directional pairs
remain between 99.8218% and 99.9789% stage exactness. The larger full-frame
residual is concentrated in independently rasterized text/chrome; title and
status bounding boxes differ only by a few pixels. These measurements are
diagnostic, not approved acceptance thresholds. Do not adjust font scale or
add a second title based on this audit. MM-005 still needs a reviewed
cross-rasterizer pixel policy and broader viewport/DPR/theme/phase coverage.

## Latest-runtime Stage0 verification — 2026-09-27

All 356 runtime include occurrences in the Stage0 sources now resolve to the
adjacent latest `Elisa-compiler/elisacore_std` checkout. After that migration,
the stable full Stage0 differential sweep completed with:

```text
All differential suites match the Python reference.
```

This covered the task/control suites, every registered game and scene sweep,
trial-phase, text metrics, screen/HUD, and assembled batch checks. The first
attempt is explicitly excluded because the harness script was edited while it
was running; the recorded result above came from the unchanged rerun in
`/tmp/nw-stage0-check-latest-runtime-rerun.log`.

Stage1 has not yet been rerun against the migrated sources. The selected
compiler was being rebuilt with active uncommitted semantic/diagnostic changes
at the end of this verification, so freshness and compiler-quiescence guards
correctly prevented a misleading Stage1 result. The latest Stage1 parity gate
and WebAssembly promotion remain pending until that compiler checkout is clean
and freshly seeded.

## Stable latest-compiler Stage1 and artifact verification — 2026-09-27

The compiler task finished and the adjacent `Elisa-compiler` checkout was
quiescent before the verification began. The stable full Stage1 command was:

```text
ELISACORE_STRICT_FP=1 \
ELISA_STAGE1_ROOT="$PWD/../Elisa-compiler" \
ELISA_STAGE1_BIN="$PWD/../Elisa-compiler/bin/elisac-stage1" \
bash nw-core/scripts/check.sh stage1
```

It completed with exit code 0 and the final line:

```text
All differential suites match the Python reference.
```

The run includes all ordinary task/control suites, all scene suites (including
Marble Maze, Graph Mapping, Matrix Reasoning, 3D Sokoban, and the task hub),
trialphase, textmetrics, screen, HUD text, and the assembled scene batch. The
three Stage1 compile declines found in the first post-runtime-migration run
were source mistakes in the test fixtures: `sview` accepts the declared `cstr`
values directly, not a raw `u8&?` cast. The corrected `stats_sweep.elisa`,
`config_sweep.elisa`, and `decimal_sweep.elisa` now pass Stage0/Stage1 parity;
the compiler backend was not weakened to accept the invalid argument type.

The same quiescent compiler snapshot then rebuilt and promoted
`build/nwcore.wasm` transactionally. The complete artifact gate passed its
runtime/API, browser-contract, game-smoke, source-backed game, Marble, and
generated-session checks. In particular, the 162-scenario/17,263-state Marble
trajectory oracle passed with maximum absolute errors within every documented
tolerance, and the generated held-input matrix passed 80 cases (7 wins, 41
physical losses, and 32 timeouts). The intentionally simulated partial-engine
cleanup failure in `marble_maze_mujoco_test.mjs` was followed by the test's
passing cleanup assertion and is not a gate failure.

Recorded provenance for this artifact:

| Item | Value |
| --- | --- |
| Elisa compiler commit | `1bc0cda143e3fc500caf55015cde5759e0d58100` |
| Elisa source fingerprint | `9de69658a554a61ac1679e3cd52398ea73800adf700fb0c51d7a636324dceef9` |
| Stage1 product SHA-256 | `9a7951ce4f5761898f7e2743f7c212dd84e4ac69e07bffc5e72a87b9e84acb23` |
| `build/nwcore.wasm` SHA-256 | `fd2ceece0f0475f39e479285659c6b6a45b85a3079382c5849cba1a784e7f328` |
| `build/nwcore_wasm.o` SHA-256 | `4d6a0e3cb0373b24d787fa8e7909343be380d5bab3d33bbe915fb30f545c28f5` |

The standalone runtime provenance check also passed and explicitly accepted the
committed latest-compiler runtime deltas. This closes the pending Stage1 and
artifact-verification checkpoint, but it does not close the independent strict
7,601-event Marble native/WASM numerical trace or the separately documented
cross-rasterizer pixel-policy work. Those remain open acceptance items rather
than being hidden by the broad artifact gate.

## Corrected latest-compiler/WASM checkpoint — 2026-09-27

The preceding checkpoint used a Stage1 product whose timestamp preceded the
selected compiler's committed HEAD. The original freshness guard checked only
source-file mtimes, so it missed committed-source advancement. The guard now
also compares the product timestamp with the selected checkout's committed HEAD
timestamp, with regression coverage in `nw-core/test/stage1_fresh_test.py`.

The first current-HEAD reseed with the port-pinned Stage0 exposed a Stage1
runtime-object segfault. The newer read-only Elisa-core Stage0 executable seeded
the current product and runtime successfully; the external Elisa-core source
checkout was not edited or reverted. Stage1's compiler-level WASI bug was then
fixed: Stage0 treats WASI as POSIX-ish, but Stage1 had set
`ELISA_TARGET_OS_POSIX=false` for WASM, causing the runtime's 21 concurrency
wrappers to be declined. The corrected `codegen_static_if.elisa` keeps the
target predicate aligned with Stage0. The remaining sview smoke issue was a
fixture ABI mistake (`sview(cstr?, ...)` declared as extern `cstr`); the fixture
now uses the public `ctx_string_view(cstr, ...)` wrapper and tests `strlen`
width separately.

Focused checks are green:

```text
stage1_fresh_test.py        PASS
wasm32_darray_abi_smoke.sh  PASS (292)
wasm32_sview_strlen_smoke.sh PASS (63)
wasm32_for_bounds_width_smoke.sh PASS (6)
```

The rebuilt `build/nwcore.wasm` passed the complete artifact suite, including
the 3D-only N-Back path, all game/browser contracts, all Marble checks, the
80-case held-input matrix, and the 162-scenario/17,263-state trajectory oracle.
The strict 7,601-event Marble trace and cross-rasterizer pixel-policy decision
remain open and are not waived by this artifact result.

## Full gate confirmation — 2026-09-27

The corrected latest-compiler run completed with `GATE GREEN` and exit code 0.
It passed runtime-include provenance, Stage0 differential and unit tests,
Stage1 freshness and parity smokes, the latest Stage1 WebAssembly rebuild,
artifact-level checks, all browser/game contracts and scene sweeps, the
3D-only N-Back path, and the complete Marble browser/MuJoCo/session/trajectory
coverage. The simulated partial-engine cleanup exception is intentionally
asserted by the negative cleanup test and is not a failure.

Active provenance:

| Item | Value |
| --- | --- |
| Elisa compiler HEAD | `1bc0cda143e3fc500caf55015cde5759e0d58100` |
| Source fingerprint | `8b70c5918c6f77a0b2a3979bef168c4ed8ee744e15c569cc556b2b4ae2ab4df4` |
| Stage0 bootstrap SHA-256 | `1b18a9b24f4d7475a6bdf5cf3bb86a090a470091b746f0f79b321beb39ac1fbf` |
| Stage1 product SHA-256 | `108f4bb4cf3041635abde708cf2650d4d42dcff4c067db009237b23483bc448c` |
| `build/nwcore.wasm` SHA-256 | `41e7aa48790d331e2710b46e73851bee2827c8c9d07ce1cbe03ba376fdf8346d` |
| `build/nwcore_wasm.o` SHA-256 | `0e52fa35c4161d0f88d3e37105358b5d9927b5350b669113e4dd1e8d8ab3560a` |

The strict 7,601-event Marble numerical replay and the cross-rasterizer pixel
policy remain open fidelity work. No tolerance was raised to obtain the green
gate.

## Strict Marble arithmetic boundary — 2026-09-27

The exact rung-16/seed-0 replay was rerun against the current promoted artifact
(`nwcore.wasm` SHA-256
`41e7aa48790d331e2710b46e73851bee2827c8c9d07ce1cbe03ba376fdf8346d`). Both
implementations replayed 7,601 events and timed out identically, but strict
numeric parity still first fails at event 196, marble 0, `value[10]` with
delta `1.0094403890548165e-7` versus the `1e-7` tolerance. The complete run
reports 111,546 exceedances; no tolerance was changed.

Synchronized native/WASM phase probing localizes the cause before the later
contact-topology divergence. At event 0 the native wheel produces subnormal
free-joint `qfrc_bias[4]`/`[10]` values of `1.5407439555097887e-33`, while WASM
produces zero. With identical fwd-constraint inputs, the first active solver
force differs by `1.713039432527097e-17`. Emscripten 6.0.10 lowers explicit
`fma()` to a software helper and leaves ordinary multiply-add expressions as
separate WebAssembly operations; relaxed SIMD does not provide a fused scalar
operation. This remains an arithmetic-lowering blocker, not a compiler-language
or task-controller defect. Production arithmetic and acceptance tolerances are
unchanged.

The Emscripten software FMA helper was independently compared with host arm64
`libm.fma` on 64 deterministic wide-range inputs and all results were
bit-identical. The unresolved issue is therefore operation selection/grouping
relative to the native wheel, not a faulty explicit-FMA primitive.

## Global contracted-operation experiment rejected — 2026-09-27

A disposable MuJoCo 3.12.0 rebuild used the production parity patch plus a
forced Emscripten wrapper that rewrote Clang's `llvm.fmuladd.f64` operations to
the explicit software-backed `llvm.fma.f64` intrinsic. The wrapper intercepted
all 65 C translation units; this was a real transformed candidate, not the
earlier no-op build where the Emscripten toolchain had overridden the wrapper.
It performed 2,380 intrinsic conversions in total.
The candidate was not promoted to the repository.

The unchanged rung-16/seed-0 replay rejected it. The first numeric breach moved
to event 216, with `value[10]` delta `4.0384860078290785e-7`, and later state
diverged substantially (maximum `value[10]` delta `10.489987076510078`). The
candidate reported 106,116 numeric exceedances but also changed contact and
trajectory behavior, so the lower aggregate count is not evidence of parity.
Production MuJoCo and `build/nwcore.wasm` remain unchanged. Future arithmetic
experiments must target a specific solver boundary and pass the strict replay
and full Marble gates before any promotion.

## Continuation checkpoint — 2026-09-28

The newest broad verification was run from an isolated Stage1 snapshot so
compiler edits could not invalidate the result. Its artifact-level checks
passed, including all browser/game contracts, the 3D-only N-Back route, all
Marble board/session checks, and the 162-scenario/17,263-state trajectory
oracle. The overall gate was intentionally not called green: the snapshot
was under /private/tmp, so the repository's relative runtime-include
provenance test resolved its expected Elisa-compiler path against the
workspace, and the pre-correction Stage0 config fixture used an untyped empty
string fallback.

The fixture issue is fixed in nw-core/test/config_sweep.elisa by using
"".cast[cstr]. The focused official differential harness now passes both
compilers:

    config [stage0]: PASS: 342 cases identical
    config [stage1]: PASS: 342 cases identical

The real-checkout runtime provenance test and the selected runtime byte
identity check also pass. A subsequent attempt to rebuild from the then-newest
live compiler began at e7d96c37 but the compiler advanced to 12de89d3 during
the artifact run; the promotion guard rejected the candidate and left the
prior artifact untouched. Therefore no artifact is currently attributed to
12de89d3; wait for a quiescent compiler, rebuild, and re-run provenance before
claiming newest-compiler status.

The strict 7,601-event Marble replay and the cross-rasterizer pixel-policy
decision remain open exactly as documented above. No tolerance was raised,
and no rejected arithmetic candidate was promoted.

## Fresh Marble replay evidence — 2026-09-28

The retained 7,601-event rung-16/run-seed-0 trace (`boardSeed=827307999`) was
replayed against the artifact currently present in `nw-core/build/` as a
diagnostic only. The first contact-topology mismatch is event 461, where the
WASM path contains an extra `(56,26)` ball contact. The first numeric breach is
event 216, `marble[0].value[10]`, with delta `4.609488333251477e-7` against the
unchanged `1e-7` limit. Continuing through contact mismatches records 170
contact mismatches and `111892` over-tolerance scalar values, with a later
maximum `value[10]` delta of `10.904862928315502`.

This run is not compiler-provenance evidence: the live Elisa compiler changed
during the attempted latest-Stage1 build, and the promotion guard rejected the
candidate. The diagnostic therefore changes no acceptance status. It confirms
the existing conclusion that the remaining divergence is in native-versus-WASM
MuJoCo floating-point lowering and subsequent solver feedback, not in the
Elisa Marble controller or held-input schedule. No production physics,
tolerance, compiler flag, or artifact was changed.

## Latest Stage1 artifact and strict Marble replay — 2026-09-28

The latest Stage1 seed and guarded WebAssembly build completed successfully.
The focused config suite passed 342/342 cases for both compiler stages, and
runtime include provenance passed. The artifact was built from Elisa compiler
commit `12de89d332e62045c22b2b7e541abbcc9ce6eab7`, source fingerprint
`72143d6d4c35a4426353aca19a84c9e160c1adcc947313fac38f94381b5bf306`, and
Stage1 product SHA-256
`0571f46bea20824f3ad4137ee7590e75d07fad80af344e986228c3477933082c`.
The post-build provenance guard passed unchanged. The promoted WASM SHA-256 is
`6e5ded20bf86805cab532f9a96b19b3bd12c9666c5a310a48748ae0da6fb933e`; the
object SHA-256 is
`3f6d04f8edce00926d469bcaa53081a91ac8bb096e25a7dc096839b636f1d140`.
The complete artifact gate passed all registered tasks, 3D-only N-Back, and
the current Marble lifecycle/controller/renderer/trajectory matrix.

The independent strict 7,601-event rung-16/run-seed-0 replay against this
artifact remains rejected at event 196 in `marble[0].value[10]`: delta
`1.0094403890548165e-7` against `1e-7`, with 111,546 over-tolerance scalar
values and maximum angular-component delta `9.997690068805735`. This confirms
the remaining issue is not an unverified or stale compiler artifact; it is the
separate native-wheel versus WASM MuJoCo numerical-lowering problem. No
tolerance or production physics candidate was changed.

## Superseding compiler/product provenance — 2026-09-28

The previous `12de89d3` record is historical. The latest guarded Stage1 build
completed from Elisa compiler commit
`07e43b730c244df4a510f87fd96a9321a0d010ec` at build time, local
`origin/main` `b841e64b6438d06d69abcc75cecd266b8714b125`, source fingerprint
`d15ae155da5333c17b35ded2e6a7b4dfa941241b777d060863342df67d4d6b9f`, and
fresh Stage1 product SHA-256
`f70596355eb860a607b2a6aa2c2b85b94de94fe1b56709eb918dec3010769b21`.
The post-build guard confirmed unchanged compiler HEAD, origin ref, source
fingerprint, and product hash before promotion. The promoted WASM is
`nw-core/build/nwcore.wasm` SHA-256
`bf57ff606a672a28cff50d6ea14783d659e07d5c8f3ee74af40315d83ac6b7c9`; its
matching object SHA-256 is
`3f6d04f8edce00926d469bcaa53081a91ac8bb096e25a7dc096839b636f1d140`.

The full artifact suite passed: compiler/product differential checks, 421
identical ordinary cases, 720 session-frame cases, batch/menu/task-hub/task
ABIs, all registered game routes, browser contracts, 3D-only N-Back, all
Marble controller/renderer/lifecycle checks, all 16 boards, generated and
held-input sessions, multi-trial/adaptive sessions, board/MJCF parity, and the
162-scenario / 17,263-state broad trajectory oracle. The exact packed
module-qualified Stage0-reject/Stage1-accept mismatch is gone. The latest
semantic acceptance comparison still reports one visible Stage1-only safety
tightening disagreement:

    TestAnalyzeInfersDisjointnessForNonOverlappingViewsAndFreshAllocations
    Stage0 0 / Stage1 0 / product 0 / expected 2

This is not silently waived and needs a deliberate compiler/test decision.

The unchanged strict Marble replay remains open against this exact artifact.
The rung-16/run-seed-0 trace (board seed `827307999`, 7,601 events) first
exceeds the declared numeric tolerance at event 196,
`marble[0].value[10]`, by `1.0094403890548165e-7` versus the unchanged `1e-7`
limit; the full run records 111,546 over-tolerance scalar values and a maximum
angular-component delta of `9.997690068805735`. This is a verified
native-wheel-versus-WASM MuJoCo arithmetic boundary, not an unverified compiler
artifact. No tolerance or production physics candidate was changed. A future
candidate must pass the complete strict replay, contact topology, terminal
result, and broad Marble gates together. The cross-rasterizer pixel policy is
also still unresolved.

## Latest Stage1 soundness regression recheck — 2026-09-28

The source-fresh captured Stage1 product passes
`Elisa-compiler/test/parity/diagnostics_smoke.sh` with 494/494 fixtures. The
reference-alias regression fixture
`Elisa-compiler/test/repro/disjoint_fresh_invalidated_by_reference_alias.elisa`
was compiled directly at `-O0` with the current Stage0 and Stage1 products:
both compile, but Stage0 emits the unsound
`elisa.disjoint.update_pair` alias metadata while Stage1 emits none. The
Stage1 backend IR absence assertion therefore passes, closing the reported
Stage0-reject/Stage1-accept soundness direction without changing the Elisa
port source.

The broader `driver_acceptance_smoke.sh` recheck has zero
Stage0-reject/Stage1-accept gaps, but reports 25 Stage1-only reject gaps
against the existing ratchet. These are the current direction of the safety
and backend tightening (aggregate-reference lifetime, raw dictionary optional
reference use, static-string binding, and related unsupported backend shapes).
No acceptance baseline was changed and no Stage1-only rejection was silently
relabeled as parity. The strict Marble native/WASM replay and reviewed
cross-rasterizer pixel policy remain the open port blockers.

## RNE-local Marble candidate rejection — 2026-09-28

The event-0 matched-input trace localizes the first public-state split to the
acceleration-side `mju_mulInertVec` operation inside recursive Newton--Euler
bias. A disposable Emscripten candidate therefore added the wheel's decoded
fused contraction order only to a private `mju_rneMulInertVec` helper used by
the two `mj_rne` calls. It did not change the public helper or any CRB,
derivative, or post-constraint caller.

The candidate was rejected by the unchanged full rung-16/run-seed-0/board-
seed-827307999 replay: first strict numeric breach at event 216 in
`marble[0].value[10]` (`4.0206669149611685e-7` versus `1e-7`), 108,453
over-tolerance scalar values, maximum later `value[10]` delta
`9.029549244303196`, and 233 contact-set mismatches (events 461–2935).
Its temporary source and artifact stayed under `/private/tmp` and were not
promoted. The retained production artifact and all acceptance tolerances are
unchanged; the active blocker remains complete native/WASM Marble physics
parity, not the browser controller.

## Physics-kernel-only fast-math candidate rejection — 2026-09-28

A disposable compiler-policy candidate applied `-ffast-math` only to the C
physics-kernel translation units, leaving the C++ model/XML validation path on
normal flags so MuJoCo's NaN safety check remained active. The candidate loaded
Marble successfully but failed the unchanged full replay earlier than the
retained artifact: first breach at event 175 in `marble[0].value[10]`
(`2.465728896616781e-7` versus `1e-7`), 112,543 over-tolerance scalar values,
maximum later `value[10]` delta `8.609797127020093`, and 113 contact-set
mismatches (events 440–2783). It remained in `/private/tmp` and was not
promoted. The production compiler settings, MuJoCo sources, artifact, and
tolerances are unchanged.

## Cholesky-only accumulation candidate rejection — 2026-09-28

The synchronized Newton trace shows identical Hessian inputs and a first
solver-side mismatch in dense Cholesky output. A disposable candidate changed
only the two `mju_dot` calls inside `mju_cholFactor` to the native arm64
wheel's ordinary multiply-then-add accumulation, while retaining the shared
Emscripten fused dot helper everywhere else. The candidate built and loaded
Marble, but the unchanged full rung-16/run-seed-0 replay rejected it earlier
than the retained artifact: event 195 `marble[0].value[10]` first exceeded
the `1e-7` limit by `1.5407814157875066e-7`; the run recorded `117883`
over-tolerance scalar values and a later maximum `value[10]` delta of
`11.307561086289608`. It was not promoted, and the disposable diagnostic
tree was restored to its clean baseline.

## Diagnostic trace-schema compatibility correction — 2026-09-28

`nw-core/test/marble_source_play_trace.py` now accepts older retained WASM
traces that predate newly added engine diagnostic arrays. Missing fields are
skipped during synchronization and comparison, while present-field size
mismatches remain hard errors. This preserves the value of historical traces
without weakening runtime parity checks; it is a harness-only compatibility
change and does not modify production physics or the promoted WASM artifact.

## Stage1 view-element address lowering fixed — 2026-09-28

The Stage1 backend previously declined the affine_move_projection accepted
fixture at peek(&xs[0]) when xs: view[Handle]. Its value-read lowering
already understood view[T][i], but its place resolver had no corresponding
address path, so the function body was omitted instead of emitting the
reference argument. This was a compiler backend defect, not an Elisa source
port defect.

Elisa-compiler/src/backend/codegen_convert.elisa now provides a shared
view-element address helper that loads {data, len}, performs the existing
view count check, and GEPs by the element type. codegen_place.elisa uses it
for local views and nested view fields. The backend IR suite includes a
view_element_address regression assertion, and the official native backend
smoke is green at 542/542. The latest semantic diagnostics smoke is also green
at 528/528 against Stage1 product
bea037dbddc0dc2302051a7fd8fe5ee000cc9ea889fbf5a6fb85b87036de0952
from compiler commit 33ad2fbaedc58b3d3a96fb2d0d271e073949c270.

## Dense-solve diagnostic oracle correction — 2026-09-28

`nw-core/test/marble_dense_solve_oracle.py` now skips valid empty Newton
records before the first dense solve instead of treating them as malformed
Cholesky input. It still rejects malformed present operands and rejects an
event containing no comparable dense solve. The active-wheel check reached all
three event-0 dense solves after the empty warm-up record; two matched exactly
and one differed by one ULP. This changed only diagnostic coverage; no shipped
WASM, MuJoCo source, physics tolerance, or acceptance rule changed.

## Cross-platform task smoke audit — 2026-09-28

All 41 generated `*_game_smoke.mjs` cases pass, including the scoped 3D
N-back case. All 22 browser contract tests pass. Catalog/registry, generic
submit, runtime protocol, and 45-case stateless task-frame ABI checks pass.

The four dedicated native-shell smokes and the four extension-backed Python
lifecycle tests for Chain of Custody, Fog of War, In the Dark, and Removals
also pass when `nw-core/build/pymod` is included in `PYTHONPATH`. The initial
aggregate command omitted that extension directory and reported only
`ModuleNotFoundError: nwcore`; the corrected command passed all cases.

These are gameplay/shell smoke results, not proof of strict Marble
long-horizon native/WASM trajectory identity. The strict physics gate and
compiler freshness gate remain open.

## Native Python smoke launch-path hardening — 2026-09-28

Four standalone extension-backed lifecycle tests (`test_custody.py`,
`test_fog_of_war.py`, `test_inthedark.py`, and `test_removals.py`) relied on the
caller to put `nw-core/build/pymod` on `PYTHONPATH`. They now derive the
repository root from `__file__` and insert the built extension directory before
importing `nwcore`, matching the other self-contained native Python smokes.

Direct invocation of all four files, with no `PYTHONPATH` override, passes.
This removes a harness-only false negative from the aggregate audit and does
not change any controller, ABI, compiler, WASM, or Marble physics behavior.

The full `shells/python/test_*.py` matrix also passes through the pinned
reference environment from `nw-core/scripts/env.sh`, with
`NEURAL_WORKSHOP_SOURCE_ROOT` supplied for source-backed Marble geometry. That
includes the controller, 560-mesh/80-board geometry, 80-case MJCF, native
MuJoCo, native 3D render, renderer, and 3D-only N-Back checks. System Python
3.9 is not an acceptance environment because it selects an older cpython-39
extension artifact without the current `marble_board` export; the pinned
Python 3.13/3.14 artifacts contain it.

## Compiler parity checkpoint — 2026-09-29

The port now has a freshly seeded Stage1 product from the newest compiler worktree
used by the project (`Elisa-compiler-latest`, base
`54360bf68398b4da8d63b82a3ad2979667798aa2`, product SHA-256
`ca5d65c417d6f2f0a125ef6e286cd700bbea784c5aba18d04dd4acc2c7f58f4f`). The
compiler-side moved-local-container bug is fixed: Stage1 now rejects `return move`
of a local by-value `darray`/`dstr` whose backing storage belongs to the inferred
auto-region, matching Stage0. The plain-return control and caller-owned parameter
forwarding remain accepted.

The fresh product passed the targeted Stage0/Stage1 probes, full driver acceptance
with zero with-std disagreements, 694/694 diagnostics smoke fixtures, and 545/545
native backend checks. This does not close strict Marble long-horizon physics
parity or the cross-rasterizer pixel policy. The diagnostic line-parity gate still
has one explicit, un-baselined `value_block_nested_loop` duplicate-location
mismatch, and the gen2 self-host gate was skipped because no gen2 product was
present. The port scope remains 3D N-back only; legacy N-back is not part of the
port.

## Diagnostic parity follow-up — 2026-09-29

The Stage1 value-block semantic walker now preserves the Stage0 diagnostic pair for
mutating methods in nested captured statement loops. The replacement Stage1 product
SHA-256 is `017f7ccac250c6780c7cbd6ada877be81d899b163a37bc7217b1d5ec1240b6b4`.
Freshness passed; diagnostic line parity is 600/600 with zero defects, and the
semantic diagnostics smoke remains 694/694. This is a compiler diagnostic-location
fix only. The strict Marble physics and cross-rasterizer visual gates remain open,
and 3D N-back remains the only N-back scope in the port.

## Rejected Marble `mji_dot6` FMA candidate — 2026-09-30

Native arm64 disassembly localized the first event-0 public-state divergence to
the inline six-component RNE projection (`mji_dot6`) used by `mj_rne`: native
code contracts the multiply/add sequence into fused instructions, while the
WebAssembly build emitted separate `f64.mul`/`f64.add` operations. A disposable
MuJoCo candidate wrapped only `mji_dot6` in an Emscripten-side `fma` path.

The candidate was replayed through strict rung 16 / seed 0 and was rejected. It
still breached first at event 196 with `value[10]` delta
`1.0094403890548165e-7`, produced 111,546 scalar exceedances, reached maximum
delta `9.997690068805735`, and timed out exactly like production. Event 0 still
showed native `qfrc_bias=1.5407439555097887e-33` versus WASM `0`. The temporary
hunk was removed and no candidate binary was promoted; production vendor hashes
remain unchanged (`mujoco.js=d9ef82762e323c7a549d4eafaf35395f07aef7265e840e6dc0f9c40460847357`,
`mujoco.wasm=2ce3a5933d7174b442c052e691d74e9f3a34075c95ce8f9b44efddbad1146f38`).

This demonstrates that calling the C `fma` symbol is not sufficient evidence of
native-equivalent fused rounding in the WebAssembly toolchain. The next candidate
must inspect and verify the generated `fma` implementation before changing physics,
tolerances, or the source oracle.

## Synchronized event-195 phase capture — 2026-09-30

The exact rung-16 / run-seed-0 Marble trace was regenerated with event-195
MuJoCo engine snapshots and split step phases, then replayed with
`--diagnostic-phase-step --diagnostic-sync-before-step1`. Synchronizing native
state to each WebAssembly step-1 input prevents accumulated trajectory drift
from being mistaken for a local kernel difference. The trace is
`/tmp/marble-event195-trace.json`, with the focused comparison in
`/tmp/marble-event195-synced-step1.log`.

At event 195/substep 0, `checkPos`, `checkVel`, and `kinematics` match exactly.
`comPos` has only two contact-Jacobian residuals, at most
`1.3552527156068805e-20`. The first meaningful freshly recomputed velocity
split is `mj_comVel`'s free-joint `mji_crossMotion` component 5:
`cdof_dot[29]` is native `0.04647584013033667` versus WebAssembly
`0.046475840130336676`, and `cdof_dot[101]` is native
`0.01564291498464024` versus WebAssembly `0.015642914984640238`.
The next RNE bias difference is only `5.260359331079598e-22`; larger constraint
and acceleration differences are downstream amplification.

This confirms the engine arithmetic boundary but not a production fix. The
component-5 `mji_crossMotion` FMA and its zero-angular-prefix variant already
matched these local scalars yet failed the full replay by increasing contact
mismatches from 104 to 140. They remain rejected. At event 196 the contact
identities still agree while a near-zero elliptic-cone margin rounds to native
`-2.7755575615628914e-17`/state 4 versus WebAssembly `0.0`/state 0. Production
MuJoCo assets, tolerances, source oracle, and game code remain unchanged; the
next candidate must come from an independent upstream solver arithmetic site.
## Newest Stage1 promotion after Monkey Ladder and Go source repairs — 2026-09-30

The port was rebuilt through the newest available Elisa Stage1 compiler before
promotion. The selected compiler is
`/Users/torarinvikbjarko/Documents/Coding Projects/Elisa Projects/Elisa-compiler-latest`
at commit `54360bf68398b4da8d63b82a3ad2979667798aa2`; the fresh Stage1 product
SHA-256 is
`017f7ccac250c6780c7cbd6ada877be81d899b163a37bc7217b1d5ec1240b6b4`, with source
fingerprint `8218c14f9ee52b740a3dfa8ae91b8e501da3a73be2df730e916bb911373e3e90`.
The compiler freshness/provenance gate passed for the complete build.

The latest compiler exposed two real port-source issues. Monkey Ladder's sampled
values were being copied from a temporary darray into a persistent fixed-array
record; the corrected `copy_deal` helper in
`nw-core/src/tasks/monkeyladder_game.elisa` performs a scalar fixed-array store
through a read-only darray parameter. This keeps the deal values live after the
temporary arena is released. The Go generator was passing overlapping mutable
references (`&work` and `&work.board`) to `legal_position` and `capture_moves`.
The corrected board-bound helper family in `nw-core/src/tasks/go.elisa` removes
that overlap without weakening Stage1's alias checker or changing the algorithm.

The resulting promoted browser artifact is
`nw-core/build/nwcore.wasm`, SHA-256
`b163d7365623a31cc07d4b13d77fe98089aac252be76de481a22c2c9d26d370e`.
The official artifact run passed 421 direct cases, 720 session-frame cases, all
current ABI suites, the persistent Monkey Ladder lifecycle/browser contract, the
3D-only N-Back lifecycle/browser contract, all current task and browser contracts,
Go lifecycle/browser coverage, all 16 Marble boards, 80 board/MJCF cases, 80
held-input sessions, adaptive/multi-trial sessions, and 162 native/browser Marble
trajectory scenarios covering 17,263 states. The screenshot-pair percentage was
reported only as diagnostic information because the pair has no synchronization
metadata; it is not a pixel-fidelity acceptance result.

Legacy N-Back remains outside the port. The strict original-source Marble replay
remains an independent open fidelity boundary despite the artifact matrix passing;
the production physics assets and tolerances were not changed in this checkpoint.

## Exact newest-compiler parity gates — 2026-09-30

The exact promoted Stage1 product remained fresh and unchanged: compiler commit
`54360bf68398b4da8d63b82a3ad2979667798aa2`, source fingerprint
`8218c14f9ee52b740a3dfa8ae91b8e501da3a73be2df730e916bb911373e3e90`, Stage1 SHA
`017f7ccac250c6780c7cbd6ada877be81d899b163a37bc7217b1d5ec1240b6b4`, and promoted
WASM SHA `b163d7365623a31cc07d4b13d77fe98089aac252be76de481a22c2c9d26d370e`.

The remaining exact-product compiler gates passed: diagnostic line parity is
600/600 with zero defects, and native backend smoke is 545/545 compile-and-run
checks. The two global-mutable fixtures skipped by the backend script are expected
Stage0 rejections, not parity failures. Combined with the previously recorded
694/694 diagnostics smoke and zero-disagreement with-stdlib driver acceptance,
the current compiler parity checkpoint is green. Strict original-source Marble
numeric/contact replay remains open; legacy N-Back remains excluded.

## Emscripten explicit-FMA lowering probe — 2026-09-30

A disposable Emscripten 6.0.10 probe verified the explicit `fma()` calls used by
the maintained Marble parity patch. For a normal cancellation witness
(`0.85614055058838223 * 0.85757312403591035 - 0.73420312658190334`), ordinary
WASM evaluation rounded to zero while explicit FMA returned the host fused result
`0xbc8af0732f42f3b8`. For a subnormal witness, ordinary evaluation returned
`0x04cfc574a6190cc4` while explicit FMA returned the host fused result
`0x04cfc574a6190cc3`. Both `-O3` and `-ffp-contract=off` builds agreed.

The generic Emscripten FMA implementation is therefore not the remaining Marble
bug. The synchronized event-195 trace still identifies the first fresh boundary
as the two free-joint `mji_crossMotion` component-5 values; the existing targeted
candidate remains rejected by the full hard replay. No maintained physics source,
vendor asset, compiler flag, tolerance, or browser artifact changed.

## Strict Marble replay re-confirmed — 2026-09-30

The unchanged `NW_MARBLE_PLAY_CASE=16:0` replay was rerun against the promoted
WASM and the original Python source after the newest compiler gates. All 7,601
input/frame events completed with the same timeout outcome. The first strict
breach remains event 196 `marble[0].value[10]`, delta
`1.0094403890548165e-7` versus `1e-7`; the complete run reports 111,546 scalar
exceedances and the known downstream contact/topology divergence. The artifact
SHA remains
`b163d7365623a31cc07d4b13d77fe98089aac252be76de481a22c2c9d26d370e`.

This confirms the retained baseline rather than introducing a regression. No
physics source, tolerance, source oracle, vendor asset, or visual policy changed.

## Fast/medium gate green after Stage0 affine-alias repair — 2026-09-30

The newest selected Stage1 compiler remained at
`54360bf68398b4da8d63b82a3ad2979667798aa2`, with source fingerprint
`8218c14f9ee52b740a3dfa8ae91b8e501da3a73be2df730e916bb911373e3e90` and fresh
Stage1 product SHA-256
`9f9085468802edae566cd4992a0e7e9b9c0bbf79755707d3894ab9bfd736954e`.
The promoted artifact is `build/nwcore.wasm`, SHA-256
`f37bfb3752b6ecc9e4ab087044a95b32576e1ebda12c553c5bf5ad1ab8685ea8`.

The configured fast/medium `scripts/gate.sh` run completed with `GATE GREEN`.
Both Stage0 and Stage1 differential catalogs and scene streams matched the
Python reference. The WASM artifact and browser contract tiers passed all
registered game contracts, the 3D-only N-Back lifecycle/browser/live cases,
common runtime/API checks, and the full Marble browser/MuJoCo/renderer/board/
session matrix, including 16 boards, 80 generated board/MJCF cases, 80
held-input sessions, adaptive/multi-trial sessions, and 162 trajectory
scenarios covering 17,263 per-frame states. The screenshot pair remained
diagnostic-only because it has no synchronization metadata.

The Stage0 compiler correction used during this gate is local ownership
analysis, not a port workaround. Packed enum match binders now alias the actual
scrutinee field through refined variant views, and consumption propagation is
limited to genuine match binders. Focused packed-enum ownership regressions and
the complete `test/semantic` package pass. The full upstream `go test ./...`
attempt passed the modified compiler packages but timed out in the unrelated
aggregate `elisacore/src` runtime harness after ten minutes under host
contention; this is retained as an unverified slow-harness result.

The gate skipped its documented slow tier: Stage0 `test-full`, Stage1 self-host
fixpoint, and Stage1 semantic differential. The independent strict
original-source Marble replay remains open at event 196, with the unchanged
`1.0094403890548165e-7` breach against `1e-7` and downstream contact/topology
divergence. No tolerance or visual exception was introduced, and legacy N-Back
remains excluded from the port; only 3D N-Back is included.

## Strict replay bound to the current promoted artifact — 2026-09-30

The unchanged `NW_MARBLE_PLAY_CASE=16:0` source replay was run against the
current `build/nwcore.wasm`, SHA-256
`f37bfb3752b6ecc9e4ab087044a95b32576e1ebda12c553c5bf5ad1ab8685ea8`. It exited
1 for the expected strict-parity failure. Both implementations processed all
7,601 input/frame events and ended in the same timeout (`home=0`, `lost=0`,
`elapsed=120.016667s`). The first breach remains event 196, marble 0,
`value[10]`, delta `1.0094403890548165e-7` against tolerance `1e-7`, and the
run reports 111,546 numeric exceedances with the known later contact/topology
divergence. This is current-artifact confirmation, not a regression; no
production source, physics asset, tolerance, visual rule, or N-Back scope
changed.

## Rejected public quaternion multiplication candidate — 2026-09-30

The matched-input free-body probe distinguished the public `mju_mulQuat` call
used by `mju_quatIntegrate` from the earlier inline `mji_mulQuat` experiment. A
disposable MuJoCo 3.12.0 build added only an Emscripten explicit-FMA form for
that public helper. It made event-195 substeps 0–3 bit-identical in matched
free-joint `qacc`, `qvelNext`, and `qposNext`, but failed the actual live replay:
the first breach moved to event 195 with delta `4.954140766511017e-7`, and the
run reported 112,823 scalar exceedances with maximum `value[10]` drift
`10.794540096724532`. Temporary artifact hashes were JS
`e89f23d0b6c0c19894e4eed063d6f0bde67406562add8523316831f2cd97d2c8` and WASM
`d83b5368cb4bfe00c0db42201eef3d5d88e15cdc47ad16310e03100a2e6dbeb6`.

The candidate was rejected and was not copied into the maintained parity patch
or shipped assets. Evidence remains in
`/private/tmp/marble-public-quat-full-replay.log` and
`/private/tmp/marble-event195-public-quat-candidate.compare.log`. Production
artifacts, tolerances, source oracle, and the 3D-only N-Back scope are unchanged.

## Rejected integration-only quaternion candidate — 2026-09-30

A second disposable build changed only `mju_quatIntegrate`, using the existing
inline Emscripten `mji_mulQuat` FMA helper for the free-joint position update;
all unrelated public `mju_mulQuat` callers remained unchanged. Its JS/WASM
hashes were `b6b5475230871d839478614915adda08335255bd12080f609baf70eac010ad65`
and `9e0068a76c60ee805f271e74b7a3b72fec50933cbe582f87b5258a77f7b2559e`.
The exact hard replay still failed identically: event-195 first breach with
delta `4.954140766511017e-7`, 112,823 scalar exceedances, and maximum
`value[10]` drift `10.794540096724532`. Evidence is in
`/private/tmp/marble-quat-integrate-full-replay.log`. This rejects the
integration arithmetic change itself; production assets and the maintained
parity patch remain unchanged.

A paired trace against the retained production module found the candidate's
first public state split at event 1, marble 0, `values[4]`, at subnormal scale:
`-1.3119087288461426e-40` versus `1.2282076319812372e-40`; event 0 was identical.
The `values[10]` delta grew from `4.842792833414933e-12` at event 100 to
`4.612853210517187e-8` at event 190 and `4.0834558268088017e-7` at event 195.
The paired traces are `/private/tmp/marble-baseline-candidate-compare.json` and
`/private/tmp/marble-quat-integrate-candidate-compare.json`. The local
matched-input quaternion correction is therefore downstream of an earlier
trajectory split and is not a valid production fix.

The retained-baseline event-0/1 matched-input capture shows the causal order:
all event-0 substeps and event-1 substep 0 are exact through the free-joint
solve and advance probes. The first split is event 1 substep 1 in free-bias
`w = R * qvel_rot`, component 2, with maximum difference
`5.525725645712019e-36`; downstream free-bias values differ up to
`4.1359030488911964e-25` and solved rotational qacc up to
`7.276949283756419e-38`, while qposNext is still exact. Evidence is
`/private/tmp/marble-events0-1-freeprobe.compare.log`. This keeps the earlier
free-bias arithmetic boundary ahead of quaternion integration as the next
causal target; no production change was made.

## Current compiler product checkpoint after fresh Stage0 reseed — 2026-09-30

The compiler verification was repeated after restoring the temporary
exiting-recovery experiment. The authoritative Stage0 was rebuilt from the
current Elisa-core compiler checkout at commit
`e42bbdfe8a1b8123c3c4bfd096d64eb4c97c8b11`; that checkout retains its local
ownership-analysis edits. The rebuilt Stage0 binary is
`/private/tmp/elisac-stage0-current-20260930`, SHA-256
`9cbfc27f93c227b664e47f19d991f5198d6a162b1fd67880d4602e4c94f70e3d`.

Stage1 was freshly reseeded from that Stage0 using the newest selected
compiler checkout at commit `54360bf68398b4da8d63b82a3ad2979667798aa2`, source
fingerprint `8218c14f9ee52b740a3dfa8ae91b8e501da3a73be2df730e916bb911373e3e90`,
and product SHA-256
`c314877326e1efbf2bcd699ad6e8af0634f48cb919aa669dafbf5d334e2dad31`.
`stage1_fresh.py` and the freshness check passed. No port WASM artifact was
regenerated by this compiler-only reseed.

Newest-oracle targeted comparison:

```text
affine_try_recovery.neg       current Stage0=accept  Stage1=accept
linear_error_exit_leak.neg   current Stage0=accept  Stage1=accept
affine_container_return.neg  current Stage0=reject  Stage1=reject
```

The temporary candidate that propagated affine consumption through exiting
recovery was rejected and reverted because it would create false Stage1
rejections against the current newest Stage0. The post-reseed gates are green:
bare driver acceptance has zero accept gaps and the same two documented reject
gaps within its existing baseline; standard-library driver acceptance has zero
disagreements; diagnostic line parity is `600/600`; diagnostics smoke is
`694/694`; and native backend smoke is `545/545`. This confirms compiler parity,
not strict Marble source parity; the latter remains open at the known
event-196/contact-topology boundary.

## Latest compiler default-path correction — 2026-09-30

The release-facing `nw-core/scripts/gate.sh` and
`nw-core/scripts/build_sdl3.sh` selectors now default to
`Elisa-compiler-latest`, consistent with the newest-compiler policy and the
latest Stage1 WASM builder. Explicit `ELISA_LATEST_STAGE1_ROOT` and
`ELISA_LATEST_STAGE1_BIN` overrides remain supported. This changes only the
default checkout selection; freshness, source-fingerprint, product, and
origin checks are unchanged. Both scripts pass `bash -n`, and the selected
latest Stage1 product passes `stage1_fresh.py`.

## Production WASM rebuilt from newest Stage1 — 2026-09-30

`nw-core/scripts/build_latest_stage1_wasm.sh` rebuilt and promoted the
production browser artifact using Elisa-compiler-latest commit
`54360bf68398b4da8d63b82a3ad2979667798aa2`, source fingerprint
`8218c14f9ee52b740a3dfa8ae91b8e501da3a73be2df730e916bb911373e3e90`, and
Stage1 product SHA-256
`c314877326e1efbf2bcd699ad6e8af0634f48cb919aa669dafbf5d334e2dad31`.
The promoted `nw-core/build/nwcore.wasm` SHA-256 is
`b2b40a4dc961dac57ad5f83d75f6e80040b8f9fe6738b5a684d8a5c1d4cff0e8`.

Artifact-level validation passed before promotion: all controller contracts,
3D N-back, 80 generated Marble sessions, 80 held-input Marble sessions, 3
adaptive Marble sessions, 16-board ABI/MJCF parity, and 162 trajectory
scenarios covering 17,263 per-frame states. The strict long-horizon native-vs-
WASM Marble replay remains a separate open parity gate.

## Full release gate green on newest compiler — 2026-09-30

The normal release gate completed with `GATE GREEN` after using the default
newest-compiler selectors. It rebuilt and promoted the latest-Stage1 artifact,
then passed the complete release-facing Stage0/Stage1 differential suites,
WebAssembly ABI/runtime checks, all game/browser contracts, the 3D-only N-Back
coverage, compiler freshness/provenance checks, Stage0 fast tests, and targeted
Stage1 parity smokes.

Marble coverage in this gate passed browser physics/contracts, all 16 boards,
board ABI, 80 generated sessions, 80 held-input sessions, three adaptive
sessions, Python/WASM board+MJCF parity over 80 cases, and 162 native/browser
trajectory scenarios covering 17,263 per-frame states within the documented
tolerances. The gate's diagnostic partial-disposal error is intentional
negative-path coverage and did not fail the test.

The gate skipped only its documented slow tier: Stage0 `test-full`, the
self-host fixpoint, and the Stage1 semantic differential. The strict
original-source Marble replay remains a separate open blocker: the retained
production artifact still first breaches at event 196,
`marble[0].value[10]`, by `1.0094403890548165e-7` against the `1e-7`
threshold, with later contact-topology divergence. Broad artifact parity must
not be used to claim that this long-horizon source replay is solved.

## Stage0 full-suite verification and timeout correction — 2026-09-30

The newest Stage0 source passed the complete serial compiler suite with:

```text
unset ELISACORE_STRICT_FP
DEVELOPER_DIR=/Library/Developer/CommandLineTools \
  go test -p 1 -timeout 30m ./...
```

`elisacore/src` passed in `901.728s`, and all remaining compiler and fixture
packages passed as well. The earlier ten-minute failure was Go's default test
timeout, not a compiler assertion or a failing test. The Stage0 repository's
`Makefile` now sets `-timeout 30m` for `test-full`, so this slow native-runtime
gate cannot be falsely reported as failed on the current toolchain.

## Direct-wheel solver diagnostics and e287 candidate — 2026-10-01

Marble-first work remains open. The retained production core is
`21c358dd11907c384fcd12b611caea85b0a33f152b4df40033294ab84f24bd5f`,
with the current manifest's maintained MuJoCo pair. The original-wheel hard
replay first exceeds the numeric bound at event 216/value[11], has 112,554
over-bound values and 143 contact-set mismatches, and times out at 120.016667 s.
Historical event-196 records above identify older artifacts, not this core.

Added durable direct active-wheel constraint-update fixtures and diagnostic
force/state/cost/Hessian arithmetic checks. The focused suite passes 83 tests;
1,024 synthetic contact states and 24 recorded operand sets reproduce scalar
wheel outputs. Explicitly initialized Hessian tests additionally pass 2,096
enabled/disabled comparisons. Incoming live H was not recorded: these are
bounded constructed-input results, not proof of identical live trajectories.
Dense trace-neutrality checking now excludes only four unused sparse indexing
buffers, and only when both snapshots explicitly use dense Jacobians. Actual
Jacobian, force, acceleration, contact, and public-state checks remain exact.

Integrated newest fetched Stage1 revision
`e2871b2cbfc601b9e13dc50d31184a22303e655d` in a private checkout, preserving
the shared dirty compiler tree. Fixed four invalid `is _` checks in its new
aggregate-copy optimization with `!= null`; the optimization and semantic
checking remain enabled. The complete reconciled source overlay and recovery
instructions are saved under `nw-core/test/repro/latest_stage1_e287_overlay.*`.

Fresh Stage1 product hash:
`c6d28027b7ad6012bf711144912c2f5cf05ae857e302cde8a05cc99ca687cf50`.
Private core hash:
`120a247c8c375ddc02917cffc933743af18655649e07539b07d0fc71ae94f064`.
Bootstrap, aggregate-copy smoke, product smoke, the complete port artifact
gate, and 7,601-event retained-core exact trace neutrality pass. Original-wheel
strict replay fails identically, as expected from neutrality to the imperfect
retained port. Full driver acceptance is still running at this checkpoint;
BARE has zero accept gaps and the existing two reject gaps. WITH-STD and
production promotion are not yet claimed. See the latest implementation-plan
checkpoint for exact paths, hashes, scope, and next causal physics work.

## e287 compiler acceptance and production promotion — 2026-10-01

Full driver acceptance subsequently passed: WITH-STD has zero disagreements;
BARE retains only its two existing reject gaps and zero accept gaps. Upstream
was rechecked immediately before promotion and still identifies e287. The
verified core and object were promoted to the normal production file paths;
old files remain recoverable in `build/stage1-promotion.WYJAuVAz/`.
The current physics manifest records the new hashes and compiler provenance.

Fresh post-promotion replay from the actual production path passed artifact
and active-wheel provenance checking, exactly matched the previous core's
7,601 recorded events, and still failed original-wheel strict physics parity
with the unchanged event-216/112,554-sample/143-contact discrepancy. No engine
arithmetic or tolerance was promoted. The local port-8000 HTTP listener was
absent during the read-only probe; this checkpoint validates the production
files, not a live browser reload. Marble identity and the overall plan remain
open.

## Initialized solver reproduction and rejected coherent candidate — 2026-10-01

Added a bounded live-H recorder, durable initialized-H/dense fixtures, and
complete diagnostic engine recovery patch/instructions under `test/repro/`.
A clean pinned MuJoCo source rebuild exactly matches all 7,601 maintained
physics snapshots and all selected Newton payloads. The recorder reads only
fully initialized active Hessian storage and reports overflow explicitly.

Direct original-wheel models now reproduce all 29 live reduced H/force
updates, twelve first-island dense solves, and six recorded rank updates;
the rank-update model also matches 1,024 synthetic update/downdate calls.
These are bounded primitive diagnostics, not whole-trajectory identity.

A combined isolated three-primitive candidate makes those captured operations
exact but is rejected by the full unsynchronized original replay: first
numeric breach event 216/value[10], 116,249 over-bound values, 282 contact
mismatches from events 461–4246. Maintained production remains unchanged with
its known 112,554 values/143-contact failure. The rejected delta and bounded
evidence are durable; do not repeat or promote that combination blindly.

Eight exact-input solver probes qualify the existing native diagnostic
library against the active original wheel. Remaining initialized solver
differences are in `PrimalPrepare` tangent UV/polynomial accumulation and
line-search derivatives. A pre-first-solve raw `search` trace validity hole
must be corrected before using those scratch values as evidence. Separate
upstream RNE/Jacobian phase differences remain outside the synchronized
solver probes. See the latest implementation-plan checkpoint for precise
labels, values, scope, reproduction steps, and ordered next work.

Focused verification passes 102 original-venv tests, 51 stdlib tests with nine
native skips, both browser/MuJoCo contracts including all 16 boards, and shell
syntax checking. This is not a full release-gate or strict Marble pass.
Upstream Stage1 was rechecked and still identifies e287; the verified newest
compiler core is unchanged. Marble-first and 3D-only N-back scope remain.

## Initialized recorder validity and preparation-order model — 2026-10-01

Corrected two diagnostic defects in a fresh isolated MuJoCo source tree:
pre-first-search scratch reads, and copying `Jv` with `nv` instead of `nefc`.
The durable follow-up patch and schema-2 decoder record explicit field
validity and overflow. Invalid fields are represented by zeros without
changing solver operands. Legacy/mixed schemas are explicitly incomparable;
fully initialized later search vectors and every Jv constraint row remain
checked. All 7,601 maintained physics/contact/phase snapshots are exactly
neutral. Twelve traced solver calls produce 166 validly decoded iteration
records, including 94 initialized Jv records and 72 invalid placeholders.

The bounded preparation model now includes Gauss callbacks, scalar and cone
polynomials, U/V rescaling, fused UU/UV/VV accumulation, Dm, and scaling.
Inspection of the actual original wheel also identifies a fused `mu*mu+1`
denominator factor. It matches 195 retained initialized polynomial probes
across eight native diagnostic boundaries and ten tangent stages across
event-18 substeps 0/3. The native probe library is boundary-qualified, not
globally identical to the original wheel. Full captured q0/Gauss/Dm output
validation and downstream line-search cost/derivative order are still open.

Verification: 129 focused original-venv tests, 76 stdlib tests with nine
native skips, both browser/MuJoCo contracts including all 16 boards, and
complete recorder neutrality pass. A fresh ordinary strict production
replay still rejects contact event 482. Remote compiler HEAD remains e287.
Production core/object/engine hashes are unchanged; no arithmetic candidate
or threshold change was promoted. See the latest plan and reproduction
notes for exact source layering, schema, hashes, and next steps.

## Complete preparation capture and native qualification — 2026-10-02

The full initialized preparation proof obligation is now closed on the bounded
captured matrix: 74 calls, 1,167 active coefficients, including q0, Gauss and
Dm. The original wheel remains authoritative. Before trusting the new native
recorder, corrected its generic dot order to the wheel's 32-element rounded
chunks/fused-quad/tail order; the initial newer native build failed every
selected solver output check. The portable dot model and corrected native
build each match direct original public dot on 9,200 deterministic cases.

The corrected native recorder exactly matches original whole-solver outputs
at all twenty selected boundaries: twelve neutral and eight from the rejected
three-primitive trace. This is not global native identity. All 7,601 neutral
WASM physics/contact/phase snapshots remain exact to the maintained control.
The preparation recorder is opt-in, bounded, validity-aware and exports hard
overflow/invalid status. The consumer requires explicit whole-output
qualification and all three input/reference/diagnostic hashes before modeling.
Complete recovery deltas, a bounded fixture and its generator are durable in
`test/repro/` and `test/fixtures/`.

All twelve neutral schema-2 iteration pairs are comparable and still show
real initialized differences in their 166 records. They are not excused as
legacy stale scratch. The next numerical work is complete PrimalEval
cost/derivative order and zone branches; pre-constraint RNE/Jacobian differences
also remain open. No isolated arithmetic candidate was promoted.

Focused verification: 156 original-venv tests, 103 dependency-light tests with
twelve expected native skips, and both browser/MuJoCo contract files including
all sixteen boards pass. A fresh ordinary unsynchronized maintained replay
still rejects the contact set at event 482. Production core/object/engine and
acceptance thresholds are unchanged. Stage1 upstream still identifies e287.
Stage0 has newer clean local semantic-lifetime commits at 473e; its private
fresh build and full semantic package pass. Production Stage1's historical
seed provenance remains a2f, not falsely relabeled as the newer Stage0.
The new private Stage0 also builds the whole port and passes the complete
artifact gate, including 162 scenarios/17,263 trajectory states. All 80
Stage0/production-Stage1 Marble board+MJCF cases and canonical runtime
provenance pass. The private Stage0 artifact is not promoted over Stage1.
Its 7,601-event hard trace is exactly neutral to the maintained imperfect port;
this isolates compiler neutrality from the original-physics acceptance failure.
Marble identity and the overall plan remain active and incomplete.

### Direct original PrimalEval qualification — 2026-10-02

The next solver boundary now has a complete bounded model and recorder.
Every evaluation is associated with its actual preparation ordinal and copies
only initialized cost/derivative outputs, raw second derivative, R and compact
friction loss after equality rows. The new decoder rejects unknown schemas,
missing false validity flags, unsafe dimensions, truncated/nonfinite captures,
invalid preparation associations and inconsistent convexity clamps.

The actual original SDK-26 wheel's private PrimalEval is called through a
test-only Darwin-arm64 bridge with exact file hash, loaded-image/public-dot
anchor, entry-byte, structure-size/offset and complete-input guards. An SDK-27
diagnostic rebuild is not substituted for that oracle. Padding in its owned
partial context is not captured solver scratch or parity evidence.

Twenty final native whole-output boundaries pass. The model matches the actual
original routine on 191 native and 129 browser captured selections plus 5,145
synthetic selections. Browser evaluations differ from original on 50 calls/
75 nonzero output fields at identical prepared operands. One rebuilt-native
second derivative also differs by one bit despite a final solver-output pass;
the new regression prevents treating that final pass as intermediate identity.

The final neutral recorder pair replays all 7,601 events exactly like the
maintained control, including contacts and initialized phase snapshots. Its
WASM hash is 65f74552c93b1a85999497720fc3da77bda4f669bd03a8fff4de49967b4f9a6a;
the native diagnostic hash is 446aea43c3a11f1a2d6b03439af645fc35401bf48c75c41545cf03c62ec05840.
The four-file evaluation delta, full fixture, generator and regression gates
are durable in test/repro and test/fixtures. See plan version 3.8's final
checkpoint for exact reconstruction, identity guards and next work order.

183 focused original-venv tests and 130 dependency-light tests (16 explicit
native skips) pass. Stage1 remote still identifies e287; the clean local
Stage0 remains 473e. No compiler/source arithmetic or production asset changed.
Next implement a coherent isolated preparation/evaluation candidate and
necessary producer order, then require ordinary unsynchronized strict replay
and all independent trajectory/result/UI gates. Strict original fidelity is
still failing; Marble remains the only game-port priority and only 3D N-back
belongs in the eventual port.

### Coherent solver and dense no-slip candidates rejected — 2026-10-02

Plan version 3.9's final checkpoint supersedes the preceding proposed
candidate work. Both complete preparation/evaluation v1 and dense no-slip
residual-order v2 have been privately built and tested. Neither is promoted.
Both pass 1,002 compiled exact-FMA cases and 5,465 complete evaluator cases.
Each matches 47 captured preparation calls/753 active values and 129 direct-
original evaluation outputs, but v1 still differs at all twelve qualified
whole-solver boundaries and v2 at eleven.

The first v1 no-slip residual mismatch is explained by the historical
browser-specific dot kernel rounding trailing products instead of reproducing
the original arm64 wheel's fused tails. v2 passes 9,200 actual-original public-
dot checks and 9,205 compound residual checks and removes that first residual
split. Compound residual goldens are not private-original residual calls.

Ordinary unsynchronized hard replay still fails for both. v1 reports first
numeric breach event195, 117,451 over-bound values and 302 contact mismatches.
v2 reports event195, 115,017 values and 204 contacts. Their first contact
failure remains event461; both time out. These are still failing independent
numeric/contact gates, not acceptance because local calculations improved.
Shipped core/object and MuJoCo JS/WASM remain unchanged.

v2's next initialized force split is event17/substep0/island0/iteration0/
contact0. Normal, friction, matrix, RHS, old force and residual agree exactly;
the QCQP/projectEllipsoid wrapper differs only at tangent4. A new strictly
hash/loaded-image/ABI/entry-guarded test bridge calls the actual original local
generic five-tangent QCQP. It returns active=true on these operands, so the
next recorder must distinguish raw QCQP output from projected force and later
costChange restoration. Do not compare raw original output to projected
browser force. Total Gauss-cost production and pre-constraint RNE/Jacobian
order remain open.

Both candidate patches are complete alternatives on the five-layer neutral
source; do not apply them sequentially or add the prior three-primitive delta
again. Full rejected-run metrics, retained artifact identities, original
raw QCQP output, bounded operand witnesses, fixture generators and tests
are saved in test/repro and test/fixtures. Follow plan 3.9 for exact recovery
and the next producer-level instrumentation sequence.

Stage1 remote still identifies e287. Latest clean local Stage0 is now
e91cb2e58a170330638b15661002bb54860720ec; a fresh private compiler passes its
semantic package and the complete port artifact gate, including 162 scenarios/
17,263 states. Its private core hash is unchanged from the 473e core. No new
Stage1 reseed or compiler bug is claimed. Marble remains the sole game-port
priority; non-3D N-back remains excluded entirely.

### Raw generic QCQP boundary is now neutral and directly attributed — 2026-10-02

Plan 3.10's final checkpoint supersedes the prior proposed outer-boundary
recorder work. The new initialized recorder preserves all 7,601 physics/input/
contact snapshots exactly against retained rejected v2. It copies raw solve,
post-projection and retained forces separately, and records costChange's
actual restoration branch rather than inferring it from returned zero.
The bounded decoder rejects truncation, missing/invalid flags, nonfinite
fields, wrong dimensions, inconsistent branches and overflow.

Of 134 contact records, 114 use the generic five-tangent kernel; 96 are active
and 18 inactive. Direct guarded original calls differ in raw nonzero force
on 29 of 114 inputs, with zero active-flag differences. Eighteen two-tangent
calls and two normal guards are not miscounted as generic reference checks.
No captured restoration branch runs.

At the previously qualified event17/substep0 first contact, raw tangent4 is
-4.338100803531913e-39 original versus -4.3381008035319136e-39 browser:
bits b7f79e6e17344b5a versus b7f79e6e17344b5b. The split exists before
projection; projected/retained vectors and all complete input operands are
preserved. This is an engine arithmetic mismatch, not evidence of an Elisa
compiler bug or a reason to change the original source.

A decomposed diagnostic driver using actual original public factor/solve/dot
primitives reproduces original raw outputs/flags on all 114 captured inputs
and 1,000 bounded deterministic synthetic cases. Disassembly confirms its
fused radius subtraction and doubled-dot Newton update. Its reconstructed
intermediates are not direct original private-intermediate captures.

Recovery layer: test/repro/marble_initialized_qcqp_boundary.patch, applied
only after the complete rejected v2 source. Durable fixture:
test/fixtures/marble_qcqp_boundary.json. The receipt CLI revalidates retained
runtime hashes and exact control neutrality before any original private call.
Next capture initialized generic QCQP factor/solve/dot/Newton iteration
boundaries with explicit validity/termination flags; then check the first
differing producer on identical operands before another arithmetic candidate.
Projection, 2/3-tangent kernels, actual restoration-path coverage, total Gauss
cost and pre-constraint RNE/Jacobian order remain open.

Validation: 226 focused original-runtime/oracle tests pass; the dependency-light
selection passes 186 with 21 explicit native skips. Existing browser options
notes (all 16 levels), renderer and MuJoCo runtime/contact/hole/all-board
contracts pass. Shipped core/object and MuJoCo pair remain unchanged.
Strict uninterrupted Marble parity remains failing; no production promotion
or broader game-port completion is claimed. Stage1 remote is rechecked e287;
clean local Stage0 remains e91cb2e.
Origin Stage0 HEAD3cbea2b is a verified ancestor of local e91cb2e, so the
qualified clean local compiler includes the published head plus newer
committed work; no downgrade or shared checkout mutation was performed.

### Generic QCQP radius corrected privately; full Marble still rejected — 2026-10-02

Plan3.11's final checkpoint supersedes the prior raw-boundary next step.
Marble remains first and non-3D N-back remains excluded entirely.
The neutral generic-kernel recorder preserves all7601 rejected-v2 physics
snapshots exactly. It captures114 groups/1286 initialized steps;99 first
differences are the value = norm - radius*radius operation. Actual exact-wheel
disassembly fuses this subtraction. Factor/solve/dot inputs preceding the
known event17/substep0/inner iteration13 split agree.

A narrowly targeted PRIVATE software-FMA operation now matches actual
original raw outputs/active flags on114 frozen captured+1000 synthetic
cases. Thirteen invalid packets are rejected. On the new complete trace,
all114 captured raw outputs/flags and1286 initialized steps agree with
direct-original/final-qualified reference controls. The formerly split
first projected wrapper agrees on the NEW candidate's exact matched inputs.
These are local proofs; reconstructed driver internals are not original
private-intermediate captures.

Independent ordinary original replay still fails:111077 numeric exceedances,
136 contact mismatches at events443..1966,first numeric breach event195
marble0/value10 delta8.227014482997674e-7 against unchanged1e-7.
Both runs timeout at120.016667s,home0/lost0. Do not promote this kernel fix.
Seven of twelve exactly qualified whole-solver boundaries still differ;
S2 is exact on4/12 and no-slip contact records on5/12.
47 preparation calls/753 values and129 actual-original evaluations still
match. Another38 direct original constraintUpdate impl calls match initialized
force/state/cost outputs;11 have only JSON-lost zero-sign differences.

Durable additive recorder: test/repro/marble_initialized_qcqp_kernel.patch.
Durable candidate delta: test/repro/marble_qcqp_fused_radius_rejected.patch,
applied only after the full v2 alternative plus both QCQP observers.
Receipts: test/fixtures/marble_qcqp_kernel_boundary.json and
test/fixtures/marble_qcqp_fused_radius_rejected.json.
The latter generator retains exact full-rejection and qualification evidence.
Its NumPy cost probes are reconstructions, not native intermediate captures.
Explicit arithmetic-comparison mode verifies runtime identities but records
changed physics and claimed=false; neutral mode still rejects changed physics.

Next record actual surrounding Gauss/total-cost and no-slip costChange
producers with branch-valid operands, proving neutrality to this NEW
candidate trace before any further arithmetic edits. Keep original public/
private routine provenance strict; SDK27 rebuild intermediate bits alone are
not an original oracle. Projection,QCQP2/3,restoration and pre-constraint
RNE/Jacobian work remain independently open.

249 focused tests pass;209 dependency-light tests pass with22 native skips.
Maintained options1344 combinations,renderer and all16 MuJoCo-board contracts
pass. Core120a247c...,object44ec4766...,MuJoCo c91c0ae6.../56a96b23... remain
unchanged. Newest Stage1 remotee287/local clean Stage0e91 were rechecked;
published Stage0origin3cbea2b remains a verified ancestor. No compiler defect
or production/game acceptance is established by these diagnostic results.

### All-call Gauss and separate QCQP2 checkpoint — 2026-10-02

Plan3.12's final checkpoint supersedes the prior Gauss-capture next step.
Marble remains first. Only3D N-back is in scope; no other N-back is delegated.
Production core120a247c...,object44ec4766...,MuJoCo JSc91c0ae6.../
WASM56a96b23... remain unchanged. No compiler defect is established.

The new all-call original oracle covers125 initialized primal updates,
including106 later calls, rather than the old first-only38. All actual
original force/state/cost outputs and reference-model nonzero outputs match;
10 calls have only unverified JSON-lost zero signs. SDK27 rebuilt-native
constraint-cost splits therefore must not be called actual original impl bugs.

The neutral Gauss observer records actual assigned Ma, operands, costs and
partial sums. It is exactly neutral over7601 events to the rejected radius
candidate. The guarded actual original zero-constraint private primal routine
isolates Gauss; all used632-byte context offsets and its image/entry are checked.
Complete eight-dof blocks are rounded, scalar tails fused. Browser Gauss/total
cost differs in43/125 calls;48 reconstructed partial sums differ.
The private arithmetic/probe delta matches125 frozen captured+1000 synthetic
actual original compiled results and rejects16 malformed packets. All125
new captured Gauss/constraint/total outputs match. Every recorded physics field
is nevertheless exactly unchanged, and ordinary original replay still has
111077 numeric exceedances/136 contacts443..1966. Do not promote it.

Separate actual original QCQP2 calls expose11/18 raw-vector differences with
matching active flags. Its disassembly-ordered model and narrow private
arithmetic/probe delta match18 captured+1000 synthetic original final vectors/
flags;13 malformed packets are rejected. On the new trace all18 raw calls
match, plus Gauss125 and genericQCQP114/1286 initialized steps stay locally
exact. No three-tangent call is captured and QCQP3 arithmetic is unchanged.

Complete unsynchronized original replay REJECTS the latest QCQP2 candidate:
114869 numeric exceedances,162 contact mismatches443..2536;first numeric
breach195/marble0/value10 delta8.252424372745537e-7 against unchanged1e-7.
Both runs timeout120.016667s/home0/lost0. More contact/numeric mismatches than
the prior candidate are not excused by local original-kernel proofs.
Private root:/private/tmp/nw-marble-gauss-boundary.qbjhDfzx; upstream source
now has twelve ordered recovery layers, documented exactly in plan3.12.
Retained latest pair:retained-qcqp2-candidate-dist,JS7c65c25e.../
WASM60b0852b...;trace SHAf797cd91... . Keep earlier retained pairs immutable.

Durable observers/arithmetic deltas:
test/repro/marble_initialized_gauss_trace.patch;
test/repro/marble_gauss_native_order_rejected.patch;
test/repro/marble_qcqp2_native_order_candidate.patch (complete game rejected).
Receipts:fixtures/marble_all_primal_updates.json,marble_gauss_boundary.json,
marble_gauss_native_order_rejected.json,marble_qcqp2_boundary.json,
marble_qcqp2_native_order_rejected.json. Two rejection generators revalidate
actual original counts, retained bytes, compiled proofs and independent failure.
Reconstructed original partial/iteration states are not private-state captures.

Next capture actual no-slip costChange delta/matrix/residual/quadratic/dot/
pre-restoration/final change and forces with branch-valid assigned fields.
Prove the observer neutral to the LATEST QCQP2 trace before another arithmetic
edit. Public original quadratic/dot results may qualify their own boundaries;
a compound reconstruction is not actual private costChange. Never invoke an
instruction-range address as a routine. Projection/restoration,pre-constraint
RNE/Jacobian and real QCQP3 cases remain separate scope. All hard/successful
tray/contact/result/matrix/rendered UI gates remain mandatory before promotion.

The first clean local Stage0 boundary was79154665 (published3cbea2b remains an ancestor).
Its private compiler SHA6b170b57... passes semantic5.009s and the complete
port artifact gate. Private core SHA2662eac9... is identical to e91 output.
Private root:/private/tmp/nw-elisa-stage0-791.i6OEZBwV;gate retry log
SHAf89c70db... . Stage1 remotee287/freshness remain qualified; deployed seed
is historicallya2f, not relabeled as791. The first image-only gate attempt
chose a Homebrew Python without Pillow; choosing the existing CLT Python
passed, without installation/system changes.286 focused original-runtime
tests and246 dependency-light tests with28 explicit native skips pass;
maintained options1344 configurations,renderer and all16 MuJoCo boards pass.
No production physics, game-completion or goal-completion claim is made.

Final compiler recheck supersedes the initial791 label: newest clean local
Stage0 is nowa98ef9228144619570f0aa47c5a92c4050f7d4ae, and it too was privately
rebuilt/qualified at /private/tmp/nw-elisa-stage0-a98.GuBT4voP.
Compiler SHA334159dc...;semantic fixtures2.528s and selected semantic/backend/
parser/lexer/interpreter/easm/frontendir/unparse plus fixture packages pass.
This is not the full upstream slow runtime/SMT suite. Full port artifact gate
passes162 scenarios/17263 states,80 play cases,3 adaptive sessions/7 timeouts,
80 board/MJCF pairs and all existing game/3D-only N-back contracts.
Core SHA2662eac9... is identical to e91/791;gate log SHA960bd7dd... .
Published3cbea2b remains an ancestor and final shared HEAD is clean a98.
Stage1 remote e287,private fingerprintd2b607b8.../productc6d28027... and its
freshness remain unchanged. The older dirty shared Stage1 tree is preserved,
not substituted for this newer qualified published integration.286 focused
tests rerun PASS6.064s;rejection/boundary receipts and goldens regenerate
byte-for-byte. Shipped core/object/MuJoCo hashes remain unchanged.

## Assigned no-slip cost and quadratic-order checkpoint — 2026-10-02

Current plan3.13 supersedes the prior cost-recorder next action. Owned root
/private/tmp/nw-marble-costchange.7SuZEZYO reconstructs all twelve recovery
layers byte-exactly before adding13 marble_initialized_costchange_trace.patch
(SHA25098c9a...) and14 marble_quadratic_native_order_candidate.patch
(SHA4a263a9e...). Both new patch boundaries forward/reverse-check; current
private upstream includes14, and retained observer/candidate pairs are separate.
The candidate filename is not an acceptance decision: whole game is REJECTED.

Observer schema1 records actual quadratic/dot returns,delta,matrix,residual,
pre/final cost and actual pre/post-restoration forces. Bounded owner/dim/
branch metadata is explicit; no second arithmetic evaluation or unassigned
scratch. All7601 input/physics/contact events and old assigned diagnostic
payloads match the latest QCQP2 control. Only five named additive traceKeys
inventory fields are allowed; old payloads are not blanket exempted.

Original public returns on134 calls (20 two-tangent/114 five-tangent/zero
three-tangent) show22 quadratic mismatches,zero dot mismatches. Composed
before/final cost differs3 times; restoration differs0,with no captured restore
branch. Private original costChange/restoration is not captured. The original
defined-symbol inventory establishes no standalone costChange/projectEllipsoid
callable; do not infer a callable from an inlined instruction range.

Private guarded quadratic correction matches134 captured+1000 synthetic
compiled original IEEE results;18 malformed packets reject. Three-tangent
quadratic has333 synthetic cases only,not actual Marble capture or QCQP3
coverage. All134 new public returns/composed costs match; Gauss125,generic
QCQP114/1286 steps and QCQP2-18 remain exact on current inputs. Nevertheless
all7601 physical events are unchanged. Full ordinary replay retains114869
numeric exceedances,162 contacts443..2536,E195/value10 delta8.252424372745537e-7,
timeout120.016667s/home0/lost0. No production promotion.

Boundary fixture marble_costchange_boundary.json SHA2ae9cc61...;
rejection fixture marble_quadratic_native_order_rejected.json SHA48126278...;
generator generate_marble_costchange_rejection_fixture.py. Full identities,
protocol,commands and next work are in the final plan/reproduction sections.
Next requalify latest exact-input whole-solver outputs,then localize projection
and earliest pre-constraint RNE/Jacobian splits with actual original producers.
Locally exact but inert cost fixes do not explain ongoing trajectory divergence.

Final310 original-runtime tests pass7.841s without skips;270 dependency-light
tests pass1.140s with31 explicit native skips. Options1344,renderer and all16
maintained MuJoCo boards pass. Stage1e287/freshness and clean Stage0a98 remain
qualified; published Stage0 ancestor3cbea2b is unchanged. Shipped core/object/
MuJoCo hashes were rechecked unchanged. No compiler defect,strict Marble
acceptance,non-3D N-back delegation or goal-completion claim.

Final matched-input whole-solver localization supersedes the older7/12 split
counts: on the latest trace,20 exact-input copies qualify the SDK27 native
library's final outputs against the exact original wheel. All21 original
output arrays are then compared with current browser outputs:18 have no
numeric split;E17/substep1 andE18/substep2 have only one solver_stats ulp each.
All recorded non-statistic force/acceleration/state/island outputs agree.
Browser JSON zero signs and private rebuilt intermediates remain unqualified.
This is explicitly synchronized diagnostic localization,NOT uninterrupted
game acceptance. Whole-output fixture marble_costchange_whole_solver.json
SHAc4ccba45...;generator generate_marble_costchange_whole_solver_fixture.py.
Next prioritize earliest upstream RNE/Jacobian/phase input drift; the matched
solver outputs do not establish which upstream routine is responsible.
The new regression brings the focused selections to311 original-runtime and
271 dependency-light tests (31 explicit native skips). Strict hard rejection
and production non-promotion remain unchanged.

## Actual-original shared inertia checkpoint — 2026-10-02

Current plan3.14 supersedes3.13's initial upstream-inertia audit. Owned root:
/private/tmp/nw-marble-costchange.7SuZEZYO. Its private upstream now contains
all15 ordered recovery layers. Additive15 patch
nw-core/test/repro/marble_inertia_native_order_candidate.patch,
SHAc88a317e5c3d41d31fecd40cdb13ce1739137d639e50333dac393875e42caf7c,
forward-checks on14 and reverse-checks on15. Preserve all earlier retained
runtime pairs; do not duplicate maintained parity or older residual hunks.

Guarded OriginalInertia checks exact wheel9e772461...,same loaded image and
public symbol offset0x12ba10. All finite bounded initialized RNE-mirror
packets,owner/parent/options/sleep metadata and entire remaining raw tail are
validated before ANY native callback. Original public returns differ42/120
times before the correction (66 nonzero values); scalar model differs0.
First E0/substep0/body1 acceleration component1 is original
-7.50413793389272e-18/browser -7.504137933892721e-18.

Private __EMSCRIPTEN__ shared mju_mulInertVec order uses the existing guarded
FMA wrapper; native/global flags stay unchanged. Shared mass-matrix/
initialization/derivative callers mean resulting physics changes cannot be
attributed solely to RNE. Actual compiled probe matches120 captured+1000
synthetic original return bits and rejects12 malformed packets. Browser
JSON zero signs/private original RNE intermediates remain unqualified.

Retained15 JS c477b87e1ced0dee08ee9d451c4b56facb478024b7e7155918f2041f274a25b8;
WASM7150d99f969711aecabe6a295d9a64f6f720942de62d885977296b9fce88cb1b;
traceb0b65c58fd0a1c86f512686b3e53ebd7622bc56f17165c9b82d982ab273ce41e.
All120 current inertia products match. Current-input cost134,Gauss125,
genericQCQP114/1286 andQCQP2-18 plus frozen compiled producers remain exact.
The7601-event input schedule is unchanged but recorded physics changes from
E0/substep1 qacc4:0 to -4.9679927381240586e-27. Neutrality is NOT claimed.

Independent ordinary strict replay stops at contactE463; full contact-count
diagnostic reports110690 numeric breaches/105 contacts463..1966. First
numeric E195/value10 delta4.996572333659799e-7 vs1e-7. Both timeout120.016667,
home0/lost0. Smaller counts than14 do not qualify the game;15 remains
REJECTED for promotion. Receipt marble_inertia_native_order_rejected.json
SHAd71ad9c90cc97429b9ccc93793c8c2f175aa5baf010a1e4d3137246a4b4d56d9;
generator generate_marble_inertia_rejection_fixture.py. Original golden and
receipt regenerate byte-exactly.

Fresh exact-input whole-solver qualification covers20 current boundaries
against the actual original wheel,not the older14 inputs. All21 final arrays
are compared:17 have no numeric split;three have only one solver_stats ulp
each,E17/1,E18/2,E216/2. All recorded force/acceleration/state/island outputs
agree. These are explicitly synchronized copies,NOT uninterrupted-game
acceptance or qualification of SDK27 private intermediate values.
Fixture marble_inertia_whole_solver.json
SHA96784aebfe9a0474a419df70fb16ba0df5feda0c2daaba7801867436412cf8cf;
whole-solver generator --candidate-prefix inertia-candidate. Its default
cost-candidate output still regenerates the old fixture byte-exactly.

Next: complete current-input RNE/cross/projection/Jacobian/integration producer
localization using actual original callable/context qualification. Public
inertia is cleared locally; full RNE is not. Do not repeat rejected standalone
FMA experiments or reopen cleared solver outputs without contrary actual
original evidence. A coherent candidate still needs every strict hard/success/
trajectory/contact/result/board/UI gate to pass before promotion or other games.

326 original-runtime methods PASS3.169s,no skips;286 dependency-light methods
PASS0.509s,32 explicit native skips. Maintained options1344,renderer contract
and MuJoCo contacts/holes/all16 boards pass. Stage1 remotee287/freshness and
clean Stage0a98/product identities rechecked unchanged; no fresh full compiler
gate is claimed. Shipped core120a247c...,object44ec4766...,MuJoCo
c91c0ae6.../56a96b23... unchanged. Non-3D N-back remains wholly excluded;
no new compiler defect,strict Marble completion or goal-completion claim.

## Complete actual-original RNE bias checkpoint — 2026-10-02

Historical plan3.15 superseded3.14's complete-RNE next action and is now superseded by3.16 below. Owned root remains
/private/tmp/nw-marble-costchange.7SuZEZYO. All prior15 layers/pairs remain
retained. Add16 marble_rne_bias_family_candidate.patch
SHAb6084b8a42ae41f6aea63c95c3eb539840efdb95e9d77b232f30cd3aacf688e6,
additive on15;forward/reverse checks pass. Preserve trailing blank unified
context lines during patch serialization;the retained hash is the corrected
patch. Current private upstream includes16.

Guarded public original mj_rne offset0x60ef8,exact wheel9e772461... and owned
model/data prove the actual complete bias return on identical operands. All
finite packet/parent/DOF ownership/options/sleep metadata,before/after named
owners,unchanged inputs and actual assigned-return tails validate before calls.
No guessed inline ABI or rebuilt-SDK private intermediate attribution.
Pre-correction20 boundaries:10 differ/21 values;complete scalar force model
matches all actual original return bits. First E0/substep3/component5 is
original -6.681911775230489e-52/browser0.

Private16 corrects the coherent __EMSCRIPTEN__ bias-only DOF accumulation,
cross-force and six-axis projection family using the guarded FMA wrapper,
plus matching assigned mirror. Native/generic/global flag behavior is unchanged.
All1020 compiled complete bias returns match actual original (20 captured,
1000 synthetic;single free body,three siblings,nested hinge/parent accumulation,
zero velocity/derivative,scale imbalance,gravity-disabled/signed-zero cases).
Acceleration-mode returns match retained15 in1020 identical contexts with
nonzero qacc;this is unchanged behavior,NOT original acceleration qualification.

Retained16 JS c477b87e... (same as15);WASM
9761684924dfac7e772bb55fb164de8b39d4da7f0ec8e18f5a24f965efaf4af6.
Tracee4bbb8e7bf8958a54de8b6d76ad4a9e7b070a074c1787f9770394e64ddc64b76.
Current20 full bias returns/model finals agree. Inertia120,cost134,Gauss125,
genericQCQP114/1286 andQCQP2-18 plus all frozen compiled producers stay exact.
The7601-event input schedule/configuration/result is unchanged. Physics is
NOT neutral:first E0/substep3 probe_rneBias qfrc_bias5 changes0 to
-6.681911775230489e-52;live fwdVelocity/later states also change. Equal failure
metrics do not mean equal physics bytes or probe-only effects.

Strict original replay stops at contactE463. Full separate count diagnostic
retains110690 over-limit values/105 contact sets463..1966,E195/value10 delta
4.996572333659799e-7 vs1e-7,timeout120.016667/home0/lost0. Candidate16 is
REJECTED for complete-game promotion. Rejection fixture
marble_rne_bias_family_rejected.json
SHAc4a5d3583963b27a6ca2d716e1988d0aaebbc715eecd72b88da9e38b0de55849;
generator generate_marble_rne_family_rejection_fixture.py rechecks original
returns/golden identities and both independent failure logs,not just summaries.

Fresh20 exact-input whole-solver copies requalify SDK27 final outputs against
actual original. All21 fields compare:17 are numerically exact;E17/1,E18/2,
E216/2 retain only one statistic ulp each,no non-stat force/acceleration/state
splits. Explicit synchronized localization is not ordinary trajectory acceptance.
Fixture marble_rne_family_whole_solver.json
SHA3a55ff382665c6f5d15dbabcd5c9aaf6efc2165ab665753ef7ece69b16ad4b19.

The historical next action was to qualify current complete mj_comVel/velocity/Jacobian input production
against actual original owned copied contexts using NAMED before/after phases.
Current bias RNE is locally cleared,not universally equivalent physics. Keep
all local regressions exact and require every strict hard/success/contact/
result/trajectory/board/adaptive/rendered/UI gate before shipping or other games.

336 focused original methods PASS2.684s,no skips;296 dependency-light methods
PASS0.391s,32 native skips. Maintained options1344,renderer and all16 boards
PASS. Stage1 remotee287/freshness and clean Stage0a98 remain unchanged. No
compiler defect,full new compiler gate,production arithmetic/tolerance change,
non-3D N-back inclusion or goal-completion claim.

## Complete actual-original comVel checkpoint — 2026-10-02

Current plan3.16 supersedes3.15's complete-velocity next action. The3.15 RNE
receipts/golden and older cost/inertia whole receipts were reproduced byte-exactly
first. Production remains unchanged;Marble remains FIRST and strict ordinary
game parity remains OPEN. No other game or non-3D N-back work occurred.

New guarded `marble_comvel_original.py` calls ACTUAL original public mj_comVel
at offset0x60110 in wheel9e772461...,on native-owned copied model/data. Every
selected packet validates before any native call. The entire tree/body/joint/
DOF topology,qvel/cdof input and both complete cvel/cdof_dot outputs are
finite/bounded/owned;unique NAMED probe_input/probe_comVel phases are required.
Missing/duplicate owners,changed operands,invalid topology/flags and sleep
reject. A complete scalar reconstruction is independently final-bit-qualified,
not an original private recorder or an assumed inline ABI.

Before17,eight of20 complete current calls differ at21 derivative cells;all
body velocities agree. First E1/substep1 cdof_dot57 original
2.0752927017112467e-40 versus browser2.0752927017112463e-40. Layer17
marble_comvel_family_candidate.patch
SHAa155ad5c3de235f5ba481aadc76e8cd2579ac9ffdf35ac3b674328b558f266cc
is additive on all16 ordered recovery layers at pin13827e9... . Forward/reverse
checks pass. Only Emscripten comVel cross-motion/grouped triple accumulation
changes;single-axis rounded product/add and native original calls remain.
No shared generic primitive,RNE branch,binding or global build flag changes.

All20 new current original calls agree. Full original golden20 captured+1000
synthetic across five free/ball/slide/hinge/nested/fixed layouts is independently
qualified with the complete reconstruction and ACTUAL compiled public call.
Retained16 fails683 calls/2700 values(8 captured,675 synthetic);17 passes1020.
Golden SHA bf30ef4d1ab07e970ce7c075269edca4142b6493fb309ecc8abce4fd62d92fdb.
All six previous current producer comparisons and frozen compiled proofs remain
exact:inertia120,cost134,Gauss125,generic114/1286steps,QCQP2-18,RNE20.
The1020 compiled RNE acceleration-path controls against15 still pass;this
is unchanged-path evidence,not original acceleration-path acceptance.

Root /private/tmp/nw-marble-costchange.7SuZEZYO now has17 source layers;
preserve every older pair. New retained-comvel-family-candidate-dist JS
SHAc477b87e1ced0dee08ee9d451c4b56facb478024b7e7155918f2041f274a25b8;
adjacentWASMce9127d43ff80fba767a17225394073f15898481a3bc5112b714c3b2fc82b9a2.
New hard traceSHA8edf9e30dc86ce598810cabeb1c9c7b05a94da7c434483740e49262f146a6008.
Input schedule/configuration/results7601 entries are identical to16,but live
physics changes:first E1 engineStep1Inputs2 cdof_dot57 changes the values
above. This is not probe-only or recorder-neutral.

Independent ordinary strict replay still FAILS at first contactE463. Its
separate full-count replay has111510 numeric breaches,103 contact mismatches
E463..1966,first numericE195/value10 delta4.950429832728531e-7 versus1e-7;
timeout120.016667/home0/lost0. Compared with16,contacts105→103 but numeric
breaches110690→111510. Full17 is REJECTED,not promoted. No relaxed tolerance.

Durable complete receipt marble_comvel_family_rejected.json SHA
0bb428c956fea0c5fac8cd157b41885f8e3adc4a2846d37be7fea64874adcd88;
generator generate_marble_comvel_family_rejection_fixture.py validates runtime/
schedule,reruns40 captured+1020 golden actual originals and models,checks
compiled control/candidate,all six regressions and both ordinary failures.
All complete inputs and actual return bits are retained;browser nonzero outputs
reconstruct from those plus differences,not a zero-sign qualification claim.

Fresh17 exact-input native solver final outputs qualify against actual original
at20 boundaries. All21 browser fields compare:18 numerically exact boundaries,
two statistic ulpsE17/1 andE18/2,no non-statistic force/acceleration/state/island
differences. Synchronized localization is NOT ordinary acceptance or original
private SDK27 intermediate identity. Whole receipt SHA
75154974dec5a65344a9010b7d4e38253c40d8e0e2483dfaa2c3752b18337518;
generator --candidate-prefix comvel-family-candidate. New receipts/golden and
all older whole-prefix receipts are required byte-exact reproductions.

NEXT qualify complete CURRENT integration/position advancement on actual
original owned input and actual enclosing outputs. Before relying on legacy
--diagnostic-sync-before-implicit,replace positional phase[4] with one named
checkAcc owner and enforce a strict complete read-set guard for new captures;
the generic old-trace sync intentionally skips absent fields. Validate full
needed static/dynamic/options/flags/shape/finiteness before native mutation,
assert copies before calling,and qualify actual whole outputs before private
free-body/LU/advance models. This is a localization priority,not a proven
integrator defect. Never promote an SDK-only private intermediate or reuse
old Sept25 cell attribution. Every candidate still needs strict full parity.

350 focused original-runtime methods PASS3.169s,no skips;310 dependency-light
methods PASS0.514s,32 explicit native skips;14 new comVel methods are in gate.sh.
Maintained options1344,renderer,contacts/holes/all16 boards PASS. Latest
qualified Stage1e287/Stage0a98 and shipped core/object/MuJoCo hashes unchanged.
No new full upstream/compiler/game gate,production promotion or goal completion.

#### Generated Marble pit/wall intersection fixed — 2026-10-03

The hole placer constrained the far-side marble passage but allowed an offset
whose circular pit crossed into the nearest wall strip. The original Python
reference and Elisa port now both enforce a 1.5 mm pit-to-wall gap, using
`min(halfCorridor - holeRadius - 0.0015m, halfCorridor + 0.55*holeRadius)` as
the upper offset bound. Layouts with no feasible passage-and-clearance interval
are rejected; rung slack 2–16 was increased in both source tables to preserve
feasible placement. Browser corridor-width notes were synchronized with the
new source widths.

`marble_board_abi_test.mjs` checks 320 boards (20 seeds ×16 rungs), every pit
and cup against every wall rectangle; minimum observed clearance is 1.500 mm.
The full Stage1 private-WASM artifact suite passes with that expanded test,
including 80 Python/WASM board+MJCF parity cases, 80 held-input runs, three
adaptive multi-trial sessions, and 162 trajectory scenarios / 17,263 states.
The deterministic gameplay oracle has the two expected changed outcomes:
rung2/seed1 loss→win and rung3/seed17 win→loss. A headed isolated browser
check visually confirms level2 clearance and reports no console diagnostics.

Verification used newest `origin/main` commits Stage0
`0283083be57d60691edd8872229f53d102f9afae` and Stage1
`50df0c9a019769c9b41f96be983c0abfd26256f7`; complete port root compiles on
both. The private Stage1 candidate is not promoted, and the production WASM
remains untouched. This closes the specific pit/wall-overlap defect only;
strict whole-game parity to the original MuJoCo remains unresolved. See
`IMPLEMENTATION_PLAN.md` and `nw-core/docs/marble-physics-manifest.json` for
the detailed invariant, seeds, binary hashes and verification limits.

#### Exact current-build dark/tilted Marble parity — 2026-10-04

Added a second synchronized render pair for the exact promoted deterministic-
name WASM: rung 16, run seed 17 / board seed `889418965`, dark theme, 8° east
tilt, 500 ms, DPR 2. Both source and browser received the same real held input
for 30 frames; neither scene nor pose was injected. Their 30-hole/60-wall
board geometry and marble states synchronize: two marbles have physically
fallen into pits, the third remains rolling. Browser runtime is MuJoCo/WebGL2;
console errors and warnings are zero.

Strict `marble_render_pair_test.py --require-synchronized --require-scene-state`
passes with zero failures and camera delta `5.6434717343734064e-8`. The 3D
stage is 99.7614% exact (MAE `0.032714`, RMSE `0.83108`); whole-frame metrics
are diagnostic only, not an approved visual threshold. The inventory audit
now finds 20 listed pairs, zero synchronization failures, and remains
`accepted: false`. Captures and durable receipt are under
`nw-core/output/playwright/marble-current-pair-20261004/dark-tilt/`.
Remaining visual work includes broader DPR1 phases, current-build lifecycle
and viewport coverage, pixel-policy review, and shipping qualification.

#### Exact current-build Marble restart and fractional-clock evidence — 2026-10-04

Added a real restart pair to the same exact-WASM dark session. Source and
browser held east for 30 frames, invoked their ordinary restart paths, then
advanced one neutral 60 Hz frame. Both reset to zero tilt and the same three
starting marble states on board seed `889418965`; strict scene synchronization
passes with no failures.

This exposed a one-millisecond representation mismatch in the capture
metadata, not in the runtime: physics time is 16.666… ms (rounded to 17),
while the browser's whole-ms controller is correctly at 16 and carries the
fraction. The metadata builder now validates the controller against the
floored simulation clock and publishes both values separately. One-frame and
25-frame carry regressions pass; ahead-of-floor controller time is rejected.

The combined audit now covers 21 diagnostic pairs with zero synchronization
failures, but remains `accepted: false`. The restart stage is 99.6823% exact
(MAE `0.14583`, RMSE `4.85261`); these are not approved pixel thresholds.
Artifacts and the durable audit are under
`nw-core/output/playwright/marble-current-pair-20261004/dark-tilt/`. Remaining
work includes other current-build lifecycle paths, DPR1/viewports, pixel
policy, and shipping qualification.

#### Exact current-build Marble DPR1 light/tilt pair — 2026-10-04

Added an 800x600/DPR1 light-theme source/browser pair on the exact promoted
WASM. Original Pyglet used `PYGLET_DPI_SCALING=real` under the strict DPR1
guard; headed Chrome used an 800x600, scale-factor-1 device context. Both
entered Marble Maze through the title and task menus, then independently
received a 30-frame east hold using the source input/update path and ordinary
browser keydown. At500ms they match on rung16, board seed `889418965`, grain
seed `3.2267631084747164`, 30 holes, 60 walls, 8-degree roll, zero pitch, and
two physically lost marbles plus one rolling marble. No pose/board injection.
Browser runtime is MuJoCo/WebGL2 with settled materials; the fetched
1,760,837-byte core WASM hash is the exact current
`0e7aef1d77dd68dcb17c08d4fc3541295425734bd42354da16a941592cdded3d` artifact.

Strict scene/camera comparison passes with no failures and maximum camera
delta `5.6434717343734064e-8`. Stage metrics are 99.5375% exact, MAE
`0.147261`, RMSE `2.41974`; whole-frame values are 98.0423% exact, MAE
`0.669419`, RMSE `6.52195`. These remain diagnostic, not accepted thresholds.
The combined audit now has22 pairs, zero synchronization failures, and
`accepted:false`. The captures and receipt are in
`nw-core/output/playwright/marble-current-pair-20261004/dpr1-light-tilt/`.
Broader DPR1 coverage, lifecycle/viewports, reviewed pixel policy, and shipping
qualification remain open.

#### Exact promoted Stage1 close-clearance visual pair — 2026-10-05

Captured an additional synchronized source/browser pair on the exact promoted
Stage1 artifact, closing the specific visual-evidence gap for holes closest to
wall strips. The fixture is rung 15, run seed 17, board seed `889418965`; hole
2 is closest to wall 22 with 3.000605385750532 mm physical circle-to-rectangle
clearance. The original-source trace has 188 ordinary events: 178 fixed 60 Hz
frames and 10 level actions. Both source and browser naturally reach physical
loss at 2,933 ms with one of two marbles home and one lost. The trace contains
no injected board, pose, phase, or outcome.

The original Python source capture and browser replay use a light-theme
800x600 logical surface at DPR2 (1600x1200 framebuffer). Browser navigation
uses the normal Games → Attention → Marble Maze → Enter → Space route; the
recorded directional/level actions are replayed as keyboard events with only
the test clock and deterministic frame stepping controlled. The browser runs
MuJoCo/WebGL2 with settled materials. It fetched HTTP 200 for the promoted
1,783,900-byte `nw-core/build/nwcore.wasm`; response SHA-256 is exactly
`4bd7b4217c2fd57b88ee19db62d9ccd6f1f4717414f5500692ef5fefcf9b79c5`.

The metadata and `marble_render_pair_test.py --require-synchronized
--require-scene-state` checks pass with zero failures. Board geometry and
captured scene states match; maximum camera-matrix absolute delta is
`5.6434717343734064e-8`. Visual inspection shows the near-minimum-clearance
opening visibly separated from its neighboring wall. The 1504x737 stage is
99.6395% exact (MAE `0.1113024727`, RMSE `2.0639207744`); full-frame exactness
is 98.4049% (MAE `1.5603260994`, RMSE `16.5943541336`). These are diagnostic
measurements only; no pixel acceptance limits have been approved.

Artifacts are under
`output/playwright/current-stage1-clearance-20261005/`:

- Source image: `source-close-gap-partial-loss-dpr2.png` (SHA-256
  `11e1d8c0886367a12e9a130d224df72ed8d19f032ba9257fc80417b1afafc1d7`);
  metadata JSON SHA-256
  `3d7b02be2e10783648acee7140b24890ec6a1eb181beae4ab216d1444c016ed4`.
- Browser image: `browser-close-gap-partial-loss-stage1-current.png` (SHA-256
  `5c884978163614820c775e88978f4f14e8614b9063b7c0db051ffaa732027244`);
  metadata JSON SHA-256
  `97cb0662286ea7ddee88f9c524de442974b73fae4055c5f752e85f006fb4c879`;
  debug JSON SHA-256
  `0637677f69304ad4acf8ab507c99712e24f8a74bcaad6a92b211278f8f541ae4`.
- Source trace:
  `output/verification/marble-source-play-clearance-20261005/traces/15-17.json`
  (SHA-256 `5d8206710f7a13dc0ffe5f2ca41f4f515aa62145badc5eaead3f05a791432f8d`).

The refreshed two-root inventory lists 33 pairs, has zero synchronization
failures, and remains `accepted:false`. Receipt:
`output/verification/marble-visual-inventory-audit-20261005-stage1-current-close-gap/receipt.json`
(SHA-256 `b5ffebe9533943c4703d7968b594f67b5a2db2e06915a55c8948aedfc6886b45`).
This is exact-current-build evidence for the closest-clearance visual case,
not overall Marble visual acceptance or shipping qualification. Recapture
remaining phases and lifecycle transitions on the promoted bytes, then seek a
human-reviewed regional pixel policy.

#### Exact promoted Stage1 rung-16 rolling/tilt pair — 2026-10-05

Captured another synchronized pair on the exact Stage1 browser core. Original
Python Marble and browser both use rung16, run seed17, board seed `889418965`,
and the same 800x600 logical surface at DPR2 (1600x1200 framebuffer). Both
receive 30 ordinary eastward held-key frames at 60 Hz, then release; they end
at 500 ms with roll0.14 radians, pitch0, and the same three rolling marbles.
The theme is dark, the run has five trays, and the level-derived budget is
140 seconds. The browser reached the task through Games → Attention → Marble
Maze, set Level16 in the in-game options, applied with Enter, and started with
Space. Only test-clock/frame stepping is controlled; no board, pose, or phase
is injected.

The browser's served WASM fetch returned HTTP200/1,783,900 bytes, with SHA-256
`4bd7b4217c2fd57b88ee19db62d9ccd6f1f4717414f5500692ef5fefcf9b79c5`, exactly
the promoted core. MuJoCo/WebGL2 and settled materials are confirmed. Browser
metadata validation and strict
`marble_render_pair_test.py --require-synchronized --require-scene-state`
both pass with zero failures, exact board/scene state, and maximum camera
delta `5.6434716899644854e-8`. The 1504x737 stage is 99.7237% exact (MAE
`0.0376400`, RMSE `0.878894`); the full 1600x1200 frame is 98.8155% exact
(MAE `1.201673`, RMSE `14.82503`). These remain diagnostic pixel statistics,
not approved thresholds.

Source image and metadata are
`output/playwright/current-stage1-rolling-20261005/source-r16-seed17-east30-dpr2-dark.{png,json}`;
SHA-256 values are `b6045fbd4846bc0234c09bc95828c318a1e7d842fabfc73a4b0e3b97fae3be36`
and `b560c9141ee78c6c556383cd49cb3a411cb4c404ca983f44dd263ca8051e5c95`.
Browser image, metadata, and debug snapshot share the same prefix; SHA-256
values are `b2379dbcb22dee12d97a2cf1c763381884e23ffe8a4adeb17c7036a8a34bc2f9`,
`e9c6cc85efc2960ade9ca18d14bb116f8466284424079cd5b73b7d50bd4a391f`, and
`afb91d330fc89e6d412e04cad51d3a610804462977bf90b83fa0b782ab2d7f9a`.

At this rolling-pair checkpoint, the two-root visual inventory listed 34 pairs
with zero synchronization failures and remained `accepted:false`. Receipt:
`output/verification/marble-visual-inventory-audit-20261005-stage1-current-rolling/receipt.json`
(SHA-256 `74c493f8cc0d4666a624af01bb388dbe902841a35ae8244ff5e2ba18ed46ff24`).
This adds exact-current evidence for one rolling high-rung dark/DPR2 case; it
does not close the other phase/viewport/theme, lifecycle, pixel-policy, or
shipping gates.

#### Exact-current-Stage1 rung-16 READY source/browser pair — 2026-10-05

Captured before board creation at rung16, run-seed17, zero elapsed time, five
trays, adaptive leveling disabled, and the source's By-level (zero override)
time setting. Both use an 800x600 logical view at DPR2 (1600x1200 framebuffer)
in dark theme. The browser reached the READY prompt through the real Games →
Attention → Marble Maze route, applied these options through the ordinary `C`
options screen, and stopped before pressing Space; no board, pose, phase, or
time was injected. Its served 1,783,900-byte WASM returned HTTP200 and matched
promoted artifact `4bd7b4217c2fd57b88ee19db62d9ccd6f1f4717414f5500692ef5fefcf9b79c5`.

`marble_browser_pair_metadata.py` and strict
`marble_render_pair_test.py --require-synchronized --require-scene-state` pass
with zero failures: both scenes are READY with no board or marbles, camera
delta0, and the full 1504x737 task stage is pixel-identical. The full frame is
99.1524% exact (MAE `1.094473`, RMSE `14.546481`), diagnostic only because no
pixel acceptance thresholds have been reviewed. The browser renderer remains
pending because no board has been created, as expected. Source/browser files
are under `nw-core/output/playwright/current-stage1-ready-20261005/`; all PNG,
metadata, debug, and artifact hashes are in
`nw-core/docs/marble-physics-manifest.json`. At this READY-capture checkpoint,
the refreshed 35-pair inventory
has zero synchronization/state failures and remains `accepted:false`; receipt
`nw-core/output/verification/marble-visual-inventory-audit-20261005-stage1-current-ready/receipt.json`
(SHA-256 `98b6638e88313922685ff08b63c5149b2fcda8099f5116a74043c1fb4681cf2b`).

#### Exact-current-Stage1 natural physical win source/browser pair — 2026-10-05

Captured a naturally earned rung-1 win against the exact promoted Stage1
artifact `4bd7b4217c2fd57b88ee19db62d9ccd6f1f4717414f5500692ef5fefcf9b79c5`
(1,783,900 bytes). The fixture uses run seed 1, generated board seed
`288545018`, a 120-second limit, light theme, and a 1280x720 CSS viewport at
DPR1. The retained trace has 4,179 events (4,026 fixed 60 Hz frames and 153
level actions). Source and browser both naturally reach `won` at 67,100 ms
with one marble home and none lost. The source follows the original task
update path; the browser follows title → Games → Attention → Marble Maze →
Space and replays ordinary keyboard input. Neither side receives an injected
board, pose, phase, or result.

The browser served the exact promoted WASM bytes with HTTP 200. Its renderer is
WebGL2/MuJoCo, all three material maps settled, and console errors/warnings are
zero. Strict `marble_render_pair_test.py --require-synchronized
--require-scene-state` passes with exact Float32 board geometry and all trace
states synchronized; maximum camera delta is `5.643471734e-8`. At the
1203x439 task stage, exact pixels are 99.9716% (MAE `0.007519798`, RMSE
`0.536298`); the complete 1280x720 frame is 98.3460% exact (MAE `1.338255`,
RMSE `14.340943`). These measurements are diagnostic only; no pixel threshold
has been approved.

Images, metadata, and browser debug data are under
`output/playwright/current-stage1-win-20261005/`; their hashes, along with the
trace hash, are indexed in `docs/marble-physics-manifest.json`. The refreshed
two-root inventory lists 36 pairs, has zero synchronization/state failures,
and remains `accepted:false`. Receipt:
`output/verification/marble-visual-inventory-audit-20261005-stage1-current-win/receipt.json`
(SHA-256 `23a207c014651ab8ebf482acf721554771916ff824df7c7dc141d7d4a0cb1b21`).
This closes the exact-current natural-win capture gap only; timeout,
cleanup/restart, broader viewport/theme coverage, reviewed pixel policy, and
shipping qualification remain open.

#### Exact-current-Stage1 natural timeout source/browser pair — 2026-10-05

The rung-1/run-seed-17 board (board seed `889418965`) is captured at its
natural 15,000 ms timeout against promoted Stage1 WASM
`4bd7b4217c2fd57b88ee19db62d9ccd6f1f4717414f5500692ef5fefcf9b79c5`
(1,783,900 bytes). It uses one tray, adaptive leveling off, shadows on, a
light 1280x720 CSS view, and DPR2. The original source and browser each advance
900 neutral fixed 60 Hz frames from an ordinary run start. The browser reaches
Marble Maze through title → Games → Attention → Marble Maze → Enter → Space;
no board, pose, elapsed-time snapshot, result, or terminal phase is injected.
The marble stays rolling at the start location as the time limit expires and
both sides display `Out of time — 0 of 1 home`.

The browser served the exact promoted WASM over HTTP 200; MuJoCo and WebGL2
were active, all three material maps settled, and the final browser console
had zero errors/warnings. Strict synchronized metadata and scene-state
comparison pass with zero failures, including exact board geometry and marble
state; maximum camera delta is `5.6434717343734064e-8`. The 2406x886 stage is
99.9845% exact (MAE `0.003515321`, RMSE `0.358317`); the full 2560x1440 image is
99.0850% exact (MAE `1.059005`, RMSE `14.143707`). Pixel metrics remain
diagnostic only; no acceptance limit has been approved.

The source/browser PNGs, metadata, and browser debug JSON are under
`output/playwright/` with prefix
`current-stage1-timeout-r1-seed17-15s-20261005-`; file and artifact hashes are
in `docs/marble-physics-manifest.json`. The refreshed two-root inventory has
37 pairs, zero synchronization/state failures, and remains `accepted:false`.
Receipt:
`output/verification/marble-visual-inventory-audit-20261005-stage1-current-timeout/receipt.json`
(SHA-256 `64c22ce9d1702640d14069258f8814c59ca75e1e40acb624f61e64824af16954`).
This closes the exact-current timeout screenshot pair.

#### Exact-current-Stage1 R-key restart source/browser pair — 2026-10-05

This rung16/run-seed17, board-seed-`889418965` capture uses one tray, the
level-derived 140-second budget, light theme, and a 1280x720 CSS view at DPR2.
On exact promoted Stage1 WASM
`4bd7b4217c2fd57b88ee19db62d9ccd6f1f4717414f5500692ef5fefcf9b79c5`, source
and browser both start normally, tilt east for 30 fixed 60 Hz frames, release
for 12, restart using the original source method and the browser's ordinary
`R` key, then run 12 neutral frames. The board seed is preserved; 0.14-radian
pre-restart tilt resets to zero, the timer resets, and the three marbles
return to the exact source start positions before the final 200 ms state.
Nothing in the board, pose, or controller is injected.

The served 1,783,900-byte WASM matches the promoted hash with HTTP 200. MuJoCo
and WebGL2 are live, all material maps settled, and browser console errors and
warnings are zero. Resource counters show two model/data instances created,
one disposed, and one live after restart. Strict source/browser state and
render synchronization passes with zero failures; geometry and all marble
poses match, with maximum camera delta `5.6434716899644854e-8`. The 2406x886
stage is 99.8288% exact (MAE `0.0535361`, RMSE `1.443811`); the whole
2560x1440 frame is 98.8710% exact (MAE `1.220513`, RMSE `14.966181`). These
remain diagnostic pixel statistics, not accepted thresholds.

PNG, metadata, and browser debug hashes are in
`docs/marble-physics-manifest.json` under prefix
`current-stage1-restart-r16-seed17-20261005-`. The two-root inventory lists
38 pairs, zero synchronization/state failures, and remains `accepted:false`;
receipt:
`output/verification/marble-visual-inventory-audit-20261005-stage1-current-restart/receipt.json`
(SHA-256 `1c3a442b084450a410def7d260a0d6c57c4b0a4c59cedc50de0196adab276740`).
This closes the same-page leave/re-entry lifecycle case as well; renderer/physics
recovery, additional theme/viewport pairs, reviewed pixel policy, and shipping
qualification remain open.

#### Exact-current-Stage1 same-page Marble Maze re-entry source/browser pair — 2026-10-05

Captured rung16/run-seed17/board-seed `889418965` on the exact promoted
1,783,900-byte Stage1 WASM, SHA-256
`4bd7b4217c2fd57b88ee19db62d9ccd6f1f4717414f5500692ef5fefcf9b79c5`. In one
browser page, the run starts through the ordinary menus, exits to Games with
Escape, re-enters the selected Marble Maze with Enter and Space, and advances
12 neutral fixed 60 Hz frames. Source and browser reach the same rolling state
at 200 ms with three marbles and identical board geometry, camera, and scene
state. No board, pose, controller state, or phase is injected. The run uses one
trial, adaptive leveling disabled, the level-derived 140-second budget, light
theme, 1280x720 CSS viewport, and DPR2 (2560x1440 framebuffer).

Lifecycle counters prove disposal and recreation: the first MuJoCo model/data
pair is gone after exit (`created 1 / deleted 1 / live 0`); immediately after
re-entry and before its first frame the live count remains zero; after 12
frames a fresh pair exists (`created 2 / deleted 1 / live 1`). WebGL2/MuJoCo
are active, materials are settled 3-of-3, the served WASM is HTTP200 and hash
identical to the promoted bytes, and final browser console errors/warnings are
zero.

`marble_browser_pair_metadata.py` and strict
`marble_render_pair_test.py --require-synchronized --require-scene-state`
pass with zero failures; maximum camera delta is `5.6434716899644854e-8`. The
2406x886 stage is 99.8288% exact (MAE `0.0535361`, RMSE `1.443811`); full-frame
exactness is 98.9564% (MAE `1.130569`, RMSE `14.446705`). Pixel results remain
diagnostic only. PNG, metadata, and debug JSON hashes are indexed under
`latestStage1ReentryVisualPair` in `docs/marble-physics-manifest.json`. The
two-root audit now lists 39 pairs, zero synchronization/state failures, and
`accepted:false`; receipt
`output/verification/marble-visual-inventory-audit-20261005-stage1-current-reentry/receipt.json`
(SHA-256 `3ca8cf835e2016d1475e9df7f8af9b900ba22a98be607ad20fe48e3535a35770`).

#### Exact-current-Stage1 live WebGL context-loss recovery — 2026-10-05

On the exact promoted Stage1 WASM
`4bd7b4217c2fd57b88ee19db62d9ccd6f1f4717414f5500692ef5fefcf9b79c5`, started
a normal rung16/run-seed17/board-seed-`889418965` run and advanced it 12
neutral 60 Hz frames. The headed browser then exercised the real
`WEBGL_lose_context` extension on the task's WebGL2 canvas, waited for the
shell to report `recovering`, and restored the context. This is an actual GL
context-loss event, not a mocked renderer callback.

During loss, the old renderer remains the recovery owner while renderer state
is `recovering`; the controller remains rolling at 200 ms with all three
marbles unchanged, and the MuJoCo model/data counts remain one live instance.
On restoration, the application creates a replacement WebGL2 renderer, fully
disposes the old renderer and clears its callbacks, restores the 3D stage, and
settles all 3 material maps. Exactly one task canvas remains. The exact WASM
was served with HTTP200 and matching SHA; browser console errors and warnings
are both zero. The retained receipt is
`output/playwright/current-stage1-context-recovery-r16-seed17-20261005.json`
(SHA-256 `58d564c6fccfbe559ea546f645ac468813d74c1117d10156ca29ca00776d5cce`);
its Playwright harness path and hash are also recorded in the physics manifest.

This closes the real renderer context-loss/restoration scenario for the
current browser artifact only. It is not a source/browser pixel pair and does
not cover every renderer-construction fault or MuJoCo initialization/retry
failure. Existing `node test/marble_renderer_contract_test.mjs` also passes.

#### Exact-current-Stage1 physics fallback and retry recovery — 2026-10-05

Exercised a complete fallback/retry lifecycle on the exact promoted Stage1
WASM `4bd7b4217c2fd57b88ee19db62d9ccd6f1f4717414f5500692ef5fefcf9b79c5`
(1,783,900 bytes). Test-only query hooks deliberately force initial MuJoCo
load failure, then one failed retry. The UI continues to identify the fallback
engine, marks the retry as failed, and leaves the retry control visible and
enabled while the controller is board-less READY. The test removes only the
retry-failure flag from the current URL and retries again; this loads the real
MuJoCo module successfully in READY and hides the retry control before play.

After ordinary Space start and 12 fixed 60 Hz frames, the game is running on
MuJoCo/WebGL2 at rung16, run-seed17, board-seed `889418965`, elapsed200ms, with
three marbles, settled 3-of-3 material maps, and exactly one live MuJoCo
model/data pair. The served core is HTTP200 and byte-identical to the promoted
WASM. There are zero browser errors; the two recorded console warnings are
the expected, deliberately injected initial-load and first-retry failures.
The full browser receipt is
`output/playwright/current-stage1-physics-retry-recovery-r16-seed17-20261005.json`
(SHA-256 `fa1c70c4bb412ed2ac8be55e9438c9d71b786eb2ea0e5c29d6a23082f5f4eed1`),
and its headed driver hash/path are in the physics manifest.

This proves the opt-in injected fallback/retry flow and subsequent real
recovery, not every network failure mode or a source/browser visual pair.

#### Exact-current-Stage1 rung-16 rolling DPR1/light source/browser pair — 2026-10-05

Captured the same rung16/run-seed17/board-seed `889418965` east-tilted rolling
fixture at 1280x720 logical pixels and DPR1, light theme. The source and real
browser each receive 30 east-held 60 Hz frames: both are at 500 ms, roll
`0.14` radians (8 degrees), pitch zero, and three rolling marbles. The browser
uses the real title → Games → Attention → Marble Maze → Enter → Space route,
followed by 30 actual ArrowRight-held fixed frames. No board, pose, result,
phase, or marble state is injected. It uses WebGL2/MuJoCo and reaches
`settled:3-of-3` material state; its served HTTP200 WASM is byte-identical to
the promoted 1,783,900-byte Stage1 artifact
`4bd7b4217c2fd57b88ee19db62d9ccd6f1f4717414f5500692ef5fefcf9b79c5`.
Browser console errors/warnings are zero.

`marble_browser_pair_metadata.py` and strict
`marble_render_pair_test.py --require-synchronized --require-scene-state`
pass with zero failures; Float32 board geometry, full scene state, camera, and
frame dimensions match, with maximum camera delta
`5.6434716899644854e-8`. The 1203x439 stage is 99.6559% exact (MAE
`0.1092119`, RMSE `2.080275`); full-frame exactness is 98.5171% (MAE
`1.043279`, RMSE `12.355948`). These measurements are diagnostic only. Visual
inspection confirms holes remain clearly separated from adjacent wall strips
in this DPR1/light frame too.

Images and JSON metadata/debug evidence are under
`output/playwright/current-stage1-rolling-dpr1-light-20261005/`; individual
hashes and provenance are recorded in the physics manifest. The refreshed
two-root inventory lists 40 pairs, zero synchronization failures, and remains
`accepted:false`; receipt
`output/verification/marble-visual-inventory-audit-20261005-stage1-current-rolling-dpr1-light/receipt.json`
(SHA-256 `78d8798df590cda3f50de65946642da2f01db908bdfb2dbdcf36c6d1a5092d3d`).

#### Exact-current-Stage1 rung-16 rolling DPR1/dark source/browser pair — 2026-10-05

Captured the dark-theme counterpart to the DPR1/light pair at 1280x720 CSS and
framebuffer. Both replay the same rung16/run-seed17/board-seed `889418965`
state after 30 east-held 60 Hz frames: rolling at 500 ms, roll `0.14`, pitch0,
three marbles. The browser uses the ordinary game route and the theme checkbox;
it serves promoted WASM `4bd7b4217c2fd57b88ee19db62d9ccd6f1f4717414f5500692ef5fefcf9b79c5`
byte-for-byte (HTTP200, 1,783,900 bytes), with WebGL2/MuJoCo, 3-of-3 materials
settled, and zero console errors/warnings. No board or pose is injected.

Strict metadata and scene-state comparison pass without failures; geometry,
marble/controller state, time, and camera synchronize (camera max delta
`5.6434716899644854e-8`). The 1203x439 stage is 99.6559% exact (MAE
`0.0468589`, RMSE `0.978129`); whole-frame exactness is 98.7939% (MAE
`0.951299`, RMSE `12.145638`). All pixels remain diagnostic-only. The dark
frame also visibly preserves separation between hole rims and nearby wall
strips.

Artifacts and hashes are in
`output/playwright/current-stage1-rolling-dpr1-dark-20261005/` and the
`latestStage1RollingDpr1DarkVisualPair` manifest entry. The refreshed two-root
inventory lists 41 pairs with zero synchronization failures and
`accepted:false`; receipt
`output/verification/marble-visual-inventory-audit-20261005-stage1-current-rolling-dpr1-dark/receipt.json`
(SHA-256 `1258c5f5c932f42c6ec7ae162fc198bf18306a45734b230d4e027f97a36436fc`).

#### Exact-current-Stage1 rung-16 rolling 800x600/DPR1 light source/browser pair — 2026-10-05

Captured the same physical rung16/run-seed17/board-seed `889418965` rolling
fixture at the alternate 800x600 viewport, DPR1, light theme. Original source
and real browser each receive 30 east-held fixed 60 Hz frames, reaching 500 ms,
roll `0.14`, pitch0, and three marbles. The browser follows the ordinary
title → Games → Attention → Marble Maze → Enter → Space route and actual
ArrowRight input; no board, pose, result, or phase is injected. The browser
serves the promoted Stage1 WASM byte-for-byte (HTTP200, 1,783,900 bytes,
SHA-256 `4bd7b4217c2fd57b88ee19db62d9ccd6f1f4717414f5500692ef5fefcf9b79c5`),
uses WebGL2/MuJoCo, and settles all three material maps. Console errors and
warnings are zero. Visual inspection confirms the hole/cup openings remain
separated from neighboring wall strips at this viewport too.

Strict metadata and synchronized scene-state comparison pass with no failures;
camera maximum delta is `5.6434716899644854e-8`. The 752x364 stage is 99.4502%
exact (MAE `0.1739866`, RMSE `2.617171`); the complete 800x600 frame is 97.9925%
exact (MAE `0.6846604`, RMSE `6.565277`). Pixel metrics remain diagnostic, not
accepted limits. The two-root inventory now lists 42 pairs with zero
synchronization failures and `accepted:false`; audit, metadata, and render-pair
contract tests pass. Receipt
`output/verification/marble-visual-inventory-audit-20261005-stage1-current-rolling-800x600-light/receipt.json`
(SHA-256 `61246c39823393684d3283eb5926e9f119fa41ef3876f19e740fb41207268da1`).
Capture evidence and hashes are in `output/playwright/current-stage1-rolling-800x600-light-20261005/`
and `latestStage1Rolling800x600LightVisualPair` in the physics manifest.

**Remaining Marble-first work:** current Stage1 now has this second viewport
shape and 10 synchronized visual pairs; broaden matched phase/theme/DPR and
viewport coverage, then obtain human review of a regional pixel policy.
Rebuild/verify the standalone native CPython extension from the latest Stage1
compiler. Shipping qualification and remaining compiler-driver rejects remain
open. Keep the 3.0 mm clearance and strict source/trajectory gates.

#### Exact current-build DPR1 dark-theme counterpart — 2026-10-04

Captured the same rung16/seed17/board889418965 physical tilt at DPR1 in dark
mode, pairing against the already recorded light capture. Source independently
replayed east for30 frames; Chromium used the normal theme checkbox in the same
running session, preserving elapsed500ms, roll0.14, pitch0, and the physical
two-lost/one-rolling outcomes. Both captures are true 800x600 DPR1, use the
exact current WASM hash `0e7aef1d77dd68dcb17c08d4fc3541295425734bd42354da16a941592cdded3d`,
and report MuJoCo/WebGL2 with settled materials. No pose or board injection.

Strict source/browser synchronization passes with zero failures and camera
delta `5.6434717343734064e-8`. Dark stage metrics are99.5379% exact (MAE
`0.0625694`, RMSE `1.13324`); full-frame metrics are diagnostic only. The
combined audit now lists23 diagnostic pairs, zero synchronization failures,
and remains `accepted:false`. Artifacts are under
`nw-core/output/playwright/marble-current-pair-20261004/dpr1-dark-tilt/`.
These paired light/dark cases improve DPR1 theme coverage but do not close the
remaining viewport/phase matrix, lifecycle paths, pixel policy, or shipping
qualification. Latest two-root audit receipt:
`nw-core/output/playwright/marble-current-pair-20261004/dpr1-dark-tilt/audit.json`
(SHA-256 `288b34072594461671abb48076b316dfa5d34b12edf3170664861cee8f3afbfa`).

#### Exact-current-WASM 3 mm close-gap partial-loss pair — 2026-10-05

Added a synchronized source/browser visual pair against the exact promoted
3.0 mm-clearance WASM. The fixture is rung 15, run seed 17, board seed
`889418965`; its nearest physical pit-to-wall clearance is
`3.000605385750532` mm (hole 2 to wall 22). The original-source trace
`output/verification/marble-source-play-clearance-20261005/traces/15-17.json`
has 188 ordered events (178 fixed 60 Hz frames and 10 level actions) and
reaches a genuine physical-loss result at 2,933 ms with one of two marbles
home and one lost. No pose, board, outcome, or phase was injected. Browser
navigation used the ordinary Games/Attention/Marble Maze route and Space start;
directional and level events were replayed as normal keys under the explicit
frozen-clock test hook.

Both captures are light-theme, 800x600 logical/DPR2 (1600x1200 framebuffer),
with the same board, camera, elapsed time, and complete marble state. The
browser fetched the exact promoted 1,761,708-byte WASM (SHA-256
`6b1751a591d2782629e2ad2c988bf89841635740650a630ba3c2dfd2839508a9`), uses
MuJoCo/WebGL2 with settled materials, and reports zero console errors or
warnings. Strict source/browser synchronization and scene-state checks pass;
camera maximum absolute difference is `5.6434717343734064e-8`. The 1504x737
3D stage is 99.6395% exact, with MAE `0.1113025` and RMSE `2.0639208`; the
full-frame MAE is `1.5603261`. These are diagnostic-only measurements, not
reviewed acceptance thresholds. Visual inspection confirms the closest hole
and wall are distinctly separated.

The retained files are
`output/playwright/mm-clearance-partial-loss-current-20261005-source.png`,
`-source.json`, `-browser.png`, `-browser-debug.json`, `-browser.json`, and
`-browser-capture.json`. Their SHA-256 identities, source trace hash, minimum
gap, exact-WASM identity, synchronization receipt, and regional pixel metrics
are in `docs/marble-physics-manifest.json`. The two-root visual inventory now
has 27 pairs, zero failures, and `accepted:false`; latest receipt:
`output/verification/marble-visual-inventory-audit-20261005-clearance-partial-loss/receipt.json`.
Next visual work is matched light/dark capture at DPR1 plus a second viewport
shape, followed by review of regional errors and a human-approved pixel policy.
This pair does not establish overall Marble parity or close shipping-build
qualification.

#### Exact canonical long-horizon replay on the 3 mm-clearance artifact — 2026-10-05

The retained rung-16 / run-seed-0 / board-seed-827307999 input schedule was
replayed on the current 1,761,708-byte core (`6b1751a591d2782629e2ad2c988bf89841635740650a630ba3c2dfd2839508a9`). All 7,601 non-state event schedules match the Oct 4 canonical trace, and strict replay against the original Python Marble source passes with zero numeric deltas, exact contacts/discrete states, and exact terminal result. Browser runtime files and the native MuJoCo 3.12.0 wheel pass provenance verification.

Current timeout: 120,017 ms, `home=0`, `lost=0`, `verdict=0`, `scoreWin=1`; predecessor timeout: `home=0`, `lost=1`, `scoreWin=0`. This records the intended clearance geometry's changed physical trajectory. It does not imply all-rung difficulty parity. The stale active `currentArtifact.artifact` hash in `marble-physics-manifest.json` was corrected to the promoted Oct 5 WASM/object hashes; prior dated receipts remain unchanged. Replay trace, provenance, and log are under `output/verification/marble-hard-trace-replay-current-20261005/`, with exact hashes indexed in the physics manifest and implementation plan.

Next: evaluate generated outcome/difficulty distributions under 3 mm clearance and keep the exact source/browser replay gate strict; then continue the remaining visual matrix and shipping qualification.

#### Exact-current-WASM DPR1 dark tilt pair for 3 mm clearance — 2026-10-05

Added a synchronized dark-theme 800x600/DPR1 capture pair on rung16, run-seed17, board-seed `889418965`, after the same 30-frame east hold in source and browser. The source ran with `PYGLET_DPI_SCALING=real`, so the actual native framebuffer is 800x600; the earlier unsuited DPR2 attempt was discarded. Browser path was the real title/Games/Attention/Marble Maze/Space route, with ordinary `d` keydown/up and 30 fixed 60 Hz steps. At 500 ms both have roll `0.14`, pitch0, and the same three rolling marbles; no pose injection. The browser uses MuJoCo/WebGL2, dark theme, settled materials, and its served core request is HTTP200/1,761,708 bytes; response bytes are identical to current WASM SHA-256 `6b1751a591d2782629e2ad2c988bf89841635740650a630ba3c2dfd2839508a9`.

`marble_browser_pair_metadata.py` passes, as does `marble_render_pair_test.py --require-synchronized --require-scene-state` with zero failures. Camera maximum delta is `5.6434716899644854e-8`. DPR1 stage exact fraction is 99.4502% (MAE0.0760183, RMSE1.26271); full-frame MAE0.707326/RMSE7.89388. Values remain diagnostic. The combined two-root audit now lists28 pairs, zero synchronization failures, and `accepted:false`; receipt `output/verification/marble-visual-inventory-audit-20261005-clearance-dpr1-dark/receipt.json` (SHA-256 `0c744587a010e250a7a2a54ada1ffb14702efaf00746752d0d08ab6bde21c0b0`). Full image/metadata hashes are recorded in `marble-physics-manifest.json` under `exactCurrentDpr1DarkTiltPairOct5`.

Next: add another current-artifact viewport shape and additional DPR1 phases while preserving strict source/scene checks. Pixel acceptance, shipping qualification, and remaining lifecycle coverage stay open.

#### Exact-current-WASM wide DPR1 dark rolling pair for 3 mm clearance — 2026-10-05

Added a second viewport shape at 1280x720 logical pixels / DPR1 / 1280x720
framebuffer, preserving the prior rung16/run-seed17/board-seed
`889418965` rolling fixture. Both the original Python source and browser
received 30 east-held 60 Hz frames (500 ms total), producing roll `0.14`,
pitch0, and three rolling marbles with no board, pose, result, or phase
injection. The source was captured with `PYGLET_DPI_SCALING=real`; the browser
followed the real title/Games/Attention/Marble Maze/Space route, ran on
MuJoCo/WebGL2 in dark theme, and reached `settled:3-of-3` material state.

The browser fetched `/build/nwcore.wasm` with HTTP200 and content length
1,761,708; its saved response was byte-identical to the promoted local core
(SHA-256 `6b1751a591d2782629e2ad2c988bf89841635740650a630ba3c2dfd2839508a9`).
Source/browser board geometry matches after the Float32 ABI, all marble
poses/velocities/orientations/states and camera match, and strict synchronized
scene-state comparison passes with zero failures. Maximum camera-matrix delta
is `5.6434716899644854e-8`. The 1203x439 3D stage is 99.6559% exact (MAE
`0.0468589`, RMSE `0.978129`); full-frame exactness is 98.7939% (MAE
`0.951299`, RMSE `12.1456`). The captured pair visually shows distinct gaps
between pit/cup openings and adjacent wall strips. All pixel results are
diagnostic-only; no visual acceptance thresholds are inferred.

Source/browser PNGs and same-call debug/metadata files are under
`output/playwright/mm-clearance-wide-dpr1-dark-current-20261005-*`; hashes and
the served-core receipt are indexed under
`holeWallVisualClearanceCurrentOct5.exactCurrentWideDpr1DarkPairOct5` in
`docs/marble-physics-manifest.json`. The two-root inventory now has 29 listed
pairs, zero synchronization failures, and `accepted:false`; receipt
`output/verification/marble-visual-inventory-audit-20261005-clearance-wide-dpr1-dark/receipt.json`
(SHA-256 `a143e2a50c6e4f7059bc97be53eab863470cfa80aa43e3161ee3f42524505cae`).
#### Exact-current-WASM wide DPR1 light rolling companion — 2026-10-05

Added a matched light-theme source/browser pair at the same 1280x720/DPR1
viewport and exact rung16/run-seed17/board-seed `889418965` rolling pose as the
dark companion: 30 east-held 60 Hz frames, elapsed500ms, roll0.14, pitch0, and
three rolling marbles. No board, pose, result, or phase was injected. Source
capture used the original Python implementation with
`PYGLET_DPI_SCALING=real`; browser navigation used the normal menu and start
keys, selected the light theme, and reached settled MuJoCo/WebGL2 materials.
The browser reported zero console errors and warnings; its HTTP200 1,761,708-
byte WASM response matches the exact promoted local artifact byte-for-byte.

Strict board/camera/scene-state synchronization passes with zero failures;
maximum camera-matrix delta is `5.6434716899644854e-8`. The 1203x439 stage is
99.6559% exact (MAE `0.109212`, RMSE `2.08028`); the whole 1280x720 image is
98.5171% exact (MAE `1.04328`, RMSE `12.35595`). Visual inspection confirms
the distinct hole-to-wall gaps remain in light mode as well as dark. All image
metrics remain diagnostic-only, not approved pixel limits.

Artifacts and hashes are under
`output/playwright/mm-clearance-wide-dpr1-light-current-20261005-*` and in
`holeWallVisualClearanceCurrentOct5.exactCurrentWideDpr1LightPairOct5` in the
physics manifest. The visual audit and regression assertion include this pair;
the refreshed two-root audit now covers30 pairs with zero synchronization
failures and `accepted:false`. Receipt:
`output/verification/marble-visual-inventory-audit-20261005-clearance-wide-dpr1-both-themes/receipt.json`
(SHA-256 `f13c9ab8f266bac4f41611f87e66bf8d050fd278ff0e1a87d82158f25b933e15`).
Both themes now have matched DPR1 coverage at the wide viewport. Additional
current-build phase/lifecycle coverage, human pixel-policy review, and shipping
qualification remain open.

#### Exact-current-WASM wide DPR1 light READY phase — 2026-10-05

Added the current 3 mm-clearance artifact's genuine pre-start `READY` phase at
1280x720/DPR1/light. The original source capture uses `--outcome ready`, which
leaves the board uncreated. In the browser, ordinary title → Games → Attention
→ Marble Maze → Space input enters “Press Space to start”; capture stops before
the second Space, so physics is not started and no board or marbles are
injected. Both sides report phase `ready`, elapsed0, zero marbles, no board,
and no material/renderer allocation. The browser core request is HTTP200 and
byte-identical to the promoted 1,761,708-byte WASM; the browser has zero console
errors/warnings and zero live MuJoCo models/data.

Strict synchronized scene/camera comparison passes (camera delta0). The full
1203x439 stage is pixel-exact; the complete 1280x720 frame is 98.9672% exact
(MAE `0.903964`, RMSE `12.080737`). Metrics are diagnostic-only; the exact
stage does not establish a reviewed whole-app pixel threshold. Artifacts and
hashes are under
`output/playwright/mm-clearance-ready-wide-dpr1-light-current-20261005-*`,
indexed as `exactCurrentWideReadyDpr1LightOct5` in the physics manifest. The
visual inventory now covers 31 pairs with zero synchronization failures and
`accepted:false`; receipt
`output/verification/marble-visual-inventory-audit-20261005-clearance-ready-wide-dpr1/receipt.json`
(SHA-256 `0f65799542bdfe1f00a26a9dc2da48790fd6ea0f8e27ea7b22e8ce01e042c983`).
Further current-build run/feedback/terminal lifecycle phases, pixel-policy
review, compiler driver triage, and shipping-build qualification remain open.

#### Predecessor-WASM natural physical win and trace-timed source capture — 2026-10-05

Added a synchronized, naturally reached win capture on the exact promoted
3.0 mm-clearance artifact. The fixture is rung1/run-seed1/board-seed
`288545018`, configured with a 120-second game limit. The recorded 4,179-event
trace was replayed through the original Python task update path and through
ordinary browser keyboard input and fixed-frame updates. Both implementations
reach `won` at 67,100 ms with one marble home and none lost; no pose, result, or
terminal phase is injected. The browser follows the real title → Games →
Attention → Marble Maze → Space route at 1280x720/DPR1/light, uses WebGL2 and
MuJoCo, and settles all three material maps. Its served WASM response is
HTTP200, 1,761,708 bytes, byte-for-byte equal to local
`nw-core/build/nwcore.wasm` SHA-256
`6b1751a591d2782629e2ad2c988bf89841635740650a630ba3c2dfd2839508a9`.

This run exposed and fixed a source-capture harness bug, not a compiler or game
physics discrepancy: `marble_source_capture.py` previously set the original
task's `time_limit` to zero, selecting the board's 45-second default even when
the input trace recorded a 120-second limit. The source therefore appeared to
lose/time out around 45 seconds while the trace's real outcome was a win at
67.1 seconds. The harness now validates the trace's `timeLimitMs` (zero/default
or integer 15,000–120,000 ms) and passes it to the original task. Its separate
`--timeout-seconds` remains only the capture-process watchdog. Regression
coverage is in `test/marble_physical_capture_test.py`; 6 tests pass. The full
source replay and browser replay both consume all 4,179 recorded events and
match every captured event state exactly.

Source/browser metadata and strict
`marble_render_pair_test.py --require-synchronized --require-scene-state`
comparison pass with zero failures; maximum camera-matrix delta is
`5.643471734e-8`, and geometry matches after the Float32 board ABI. At the
1203x439 stage, exact pixels are 99.9716% (MAE `0.007519798`, RMSE `0.536298`);
full-frame exactness is 98.3460% (MAE `1.338255`, RMSE `14.34094`). These are
diagnostics only, not an approved visual threshold. Pair artifacts and hashes
are indexed as
`holeWallVisualClearanceCurrentOct5.exactCurrentWideDpr1LightPhysicalWinTraceOct5`
in `docs/marble-physics-manifest.json`. The two-root inventory now has 32
diagnostic pairs, zero synchronization failures, and `accepted:false`; receipt
`output/verification/marble-visual-inventory-audit-20261005-physical-win-two-roots/receipt.json`
(SHA-256
`9c2bff894111cb9fd7943244dadcdfaed47270f4326f59a995b84e006b2a3e58`).
Current-phase/lifecycle coverage, reviewed pixel policy, compiler-driver
triage, and shipping-build qualification remain open.
