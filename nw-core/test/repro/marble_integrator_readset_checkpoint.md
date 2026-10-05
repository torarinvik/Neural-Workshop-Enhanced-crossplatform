# Integration read-set checkpoint — 2026-10-02

## Framebuffer text/clear parity — 2026-10-03

`display-list.js` now resets the 2D context to identity before clearing the
full framebuffer. Marble drawing restores a reference transform but leaves it
active at frame exit; previously the next frame's `clearRect` erased only part
of the canvas and accumulated old title/status pixels. The regression asserts
identity at clear time. A fresh headed browser replay confirms the source and
candidate live status remain one line and do not accumulate.

Marble labels now render at their final framebuffer font size, with each
Courier New glyph's advance rounded to a pixel and the whole run aligned from
the left/center/right anchor. The source resolves Courier New at 96 DPI; the
font scale is4/3. A source-calibrated vertical correction keeps the small
footnote aligned. Follow-up same-state, source-paired captures establish a
theme-specific same-color stroke: 0.045em improves light labels, but worsens
dark labels. `marbleGlyphStrokeRatio` now returns0.045 for light and0 for dark.
With opaque/composited 800x600 DPR1 screenshots, the light A/B full-frame MAE
is0.842 without stroke versus0.663 with stroke (stage0.1102 in both). A
same-method dark A/B is3.096 with stroke versus1.545 without; its scene
geometry and pose match exactly. These comparisons are diagnostic only.

The actual shipping-code dark candidate was captured after real title →
category → Marble Maze menu navigation and start, with source state set from
the retained source fixture. Verified browser/source values: rung16, board seed
889418965, grain seed3.2267631084747164, roll0.14, pitch0, elapsed500ms,
800x600 framebuffer, DPR1, dark theme, `webgl2`, `settled:3-of-3` maps, and
exact dynamic status text. The derived metadata helper and strict
`--require-synchronized --require-scene-state` comparator pass with no
failures. Final dark pair:98.508% exact full-frame pixels, full-frame MAE
0.6900, stage MAE0.0431 over752x364. Candidate artifacts are
`output/playwright/mm-dark-dpr1/mm-shipping-dark-dpr1-theme-aware-final-800x600.png`,
`output/playwright/mm-dark-dpr1/mm-shipping-dark-dpr1-theme-aware-final-debug.json`,
and its `-metadata.json`; the source is
`output/playwright/mm-source-native-python-r16-east-30f-dark-dpr1-800x600.png`.
The same-state light screenshot pair is retained under
`output/playwright/mm-dark-dpr1/mm-shipping-light-dpr1-stroke-composited-800x600.png`
with debug and derived metadata. Both theme captures use matching source
scene fixtures and actual framebuffer screenshots, not transparent canvas
readback. These cross-renderer measurements remain diagnostic: no approved
threshold, reviewed pixel policy, or visual acceptance is claimed.

A fresh dark-theme DPR2 pair now exercises the same shipping renderer and
theme-specific text policy at 912x684 CSS pixels / 1824x1368 framebuffer.
It was reached through the actual title → category → Marble Maze → start
keyboard flow; only the deterministic scene snapshot was supplied by the
explicit test hook. Browser metadata verifies rung16, board seed
889418965, grain seed3.2267631084747164, 500ms, roll0.14, pitch0, dark
theme, WebGL2, exact status, camera and viewport, and all three settled
material maps. The source-paired comparator with
`--require-synchronized --require-scene-state` has no failures. Full-frame
MAE is1.2817 with98.9444% exact pixels; the 1714x842 stage is99.8467% exact
with MAE0.01987. Candidate PNG, same-task debug snapshot, and derived
metadata are under
`output/playwright/mm-dark-dpr2-check/`. Visual pixel results remain
diagnostic-only and do not establish an approved cross-rasterizer threshold.

The corresponding original-source light-theme DPR2 capture uses the same
912x684 CSS size, 1824x1368 framebuffer, rung16 board, 30 east-held frames,
500ms, roll0.14, and run/board/grain seeds. Its browser pair also passes the
strict synchronization and scene-state checks with no failures. Full-frame
MAE is1.5034 with98.6025% exact pixels; the 1714x842 stage is99.8464% exact
with MAE0.04830. Source reference files are
`output/playwright/mm-source-native-python-r16-east-30f-light-dpr2-912x684.{png,json}`;
browser PNG, same-task debug JSON, and derived metadata are under
`output/playwright/mm-light-dpr2-check/`. The 2x light-theme result remains
diagnostic-only; it does not set a pixel acceptance threshold.

Light-theme rung1 terminal display pairs were then captured at the same DPR2
size for lost, won, and done. Each capture was reached through the normal
browser title/category/task/start keys; only the phase fixture was injected.
The original source helper drives its normal result presentation from a
synthetic terminal state, so these prove rendering/state-envelope parity for
the three screens, not that gameplay physically earned the outcomes. All
three `--require-synchronized --require-scene-state` comparisons pass with no
failures. Their 3D stages are each99.9285% exact (MAE0.005554). Full-frame
metrics are: lost MAE1.5827/98.5774% exact, won MAE1.8938/98.2598% exact, and
done MAE1.4238/98.7278% exact. The remaining differences concentrate in
independently rasterized result/footer text. Source fixtures are
`output/playwright/mm-source-native-python-{lost,won,done}-r1-light-dpr2-912x684.{png,json}`;
browser captures and derived manifests are under
`output/playwright/mm-lost-light-dpr2-check/`. Measurements remain
diagnostic-only.

A separate 15-second timeout fixture reaches the source's lost-feedback phase
by advancing the original task through its real deadline/update loop. The
browser receives the resulting deterministic timeout scene snapshot after
normal menu navigation; this validates the phase/state envelope and rendering,
not the browser's real-time 15-second wait. Source and browser both report
15000ms, `terminalReason=timeout`, and exact status `Out of time — 0 of 1
home`. Strict sync/state comparison passes with no failures. Full-frame MAE is
1.5304 with98.6209% exact pixels; the stage is99.9286% exact with MAE0.005553.
Source pair files are
`output/playwright/mm-source-native-python-timeout-r1-light-dpr2-912x684.{png,json}`;
candidate PNG/debug/metadata are under
`output/playwright/mm-timeout-light-dpr2-check/`. This remains visual/state
evidence, not acceptance of timer scheduling or approved pixel limits.

The browser's real timeout was then exercised from a fresh load with no
`marble-test-state` and no frozen test clock. Starting Marble Maze through
the normal keyboard menu with a 15-second budget reached timeout at elapsed
15.000768s (controller elapsed15001ms), retained `terminalReason=timeout`, and
showed the exact source status. A 25ms page observer captured the composited
frame/debug snapshot during the 2.6-second feedback window before the ordinary
single-trial transition to DONE. The source was independently run to the same
15.000768s deadline. Strict synchronized/state comparison passes with no
failures; its full-frame and stage metrics are identical to the paired
deterministic timeout fixture above (MAE1.5304/98.6209% exact overall;
MAE0.005553/99.9286% exact stage). Candidate files are under
`output/playwright/mm-timeout-live-check/`; source pair is
`output/playwright/mm-source-native-python-timeout-live-15001ms-r1-light-dpr2-912x684.{png,json}`.
This is direct evidence that the browser countdown reaches timeout without
injected scene state. Restart and multi-tray rollover progression remain
unverified by this real-time run; pixel values remain diagnostic-only.

The earlier physical replay status is exactly
`inhuman — 140s     tray 1/1   home 0/3   139s left   tilt 8°/0°`, with roll
0.14 and elapsed 0.7000000000000005; candidate and source use identical text.
The DPR2 fixture separately uses500ms and produces that same exact status.
`node test/marble_chrome_test.mjs`, `node test/marble_text_metrics_test.mjs`,
`node test/marble_renderer_contract_test.mjs`, and
`python3 test/marble_capture_font_test.py` pass. The browser's local HTTP
server reset unchanged adapter requests during reload; owned headed sessions
fulfilled those exact local module bytes before capture. No physics source or
production binaries changed. Additional DPR/viewport combinations beyond the
checked 800x600 DPR1 and 912x684 DPR2 captures, other phases, and formal visual
acceptance remain open.

## Bounded combined-trig qualification — 2026-10-03

Browser font pass applied to static and live Marble Maze labels. Source
Courier rendering uses per-glyph integer framebuffer advances, so
display-list rendering now rounds each measured Canvas advance after the
reference-to-framebuffer scale, sets per-glyph fillText alignment to left,
and applies center/right anchoring once to the complete rounded string.
MARBLE_TEXT_SCALE changed from1.32 to4/3 (source Quartz uses96/72 point to
pixel conversion). New pure and render-path checks cover left/center/right
anchors, fractional scale, astral glyph iteration, and left-aligned glyph
draws; `node test/marble_text_metrics_test.mjs` PASS. Existing compiled
status ownership28-frame test and source font capture unit test PASS.

Fresh visible Chrome capture mm-shipping-glyph-rounded-fixed.png after
normal menu/start navigation uses renderer webgl2, canvas800x600, DPR1,
and confirms loaded display-list module rev marble-font-4. Comparison with
same-size source glyph capture yields dark-ink bounds: title source
(317,25)-(482,42), browser(316,24)-(482,42); status source
(87,57)-(712,72), browser(86,57)-(713,73); footer source
(33,574)-(767,585), browser(33,575)-(767,587). This strongly improves
horizontal alignment/spacing; vertical extents and ink coverage still
differ (browser title/status darker), so full font visual acceptance remains
open. The status appearance represents a single host string; display list
reports two retained commands (title and footer), confirming the static
status slot is filtered. No production WASM or physics changes.

Fresh source glyph capture mm-source-glyph-evidence.png/json completed:
title11glyphs advance15 sum165; footer92glyphs advance8 sum736;
status63glyphs advance10 sum630. Exact strings now stored, no missing-string
assumption. Browser Chrome Canvas measured title168.12933349609375px and
footer766.851318359375px at1.32; at4/3 title169.84556579589844 and
footer774.5809326171875. Hence scale-only correction cannot match source
spacing. Quartz glyph renderer rounds CTFont advances to integer pixels
(font/quartz.py line253); source title ascent22/descent-8 versus Canvas21/8,
footer source12/-5 versus Canvas12/4. Need glyph-placement/anchor treatment
and fresh visual proof, not blanket tolerance increase. First glyph capture
failed because current pyglet get_glyphs returns(glyphs,positions), not list;
helper and test corrected to unpack first component; rerun/unit test PASS.
No renderer change or visual acceptance in this measurement step.

Source font evidence now captured from label.document.get_font(0,label.dpi),
with requested/resolved family, point/pixel size, DPI, weight, ascent/descent,
content dimensions and anchors. Unit regression PASS and gate hooked.
Fresh original capture mm-source-font-evidence.png/json under nw-core/output/
playwright completed with real DPI override,800x600,rung16,seed17,east30,
release12,f32 board. All three labels resolve Courier New at DPI96:
title25.730994152046783px bold/ascent22/descent-8/content165x30;
status16.37426900584795px normal/ascent14/descent-5/content630x19;
footer14.035087719298243px normal/ascent12/descent-5/content736x17.
Thus source point-to-pixel conversion is 96/72=4/3, not browser's1.32.
Do not change the scale alone and declare parity: source integer glyph
advances and anchor metrics differ from Canvas and need fresh measured
browser comparisons. Capture modifies no original source or physics.

Status ownership regression extended to real maintained-core WASM frames:
seven dimensions (800x600, 912x684, 1280x720, 801x601, 320x240,
1920x1080, 321x241), four phases each, 28 frames PASS. This exposed a
second bug: exact normalized center x=456 misses odd-width frames because
Geometry truncates width/2 before normalization. marbleStaticChrome now
receives actual canvas dimensions and reproduces truncation followed by
f32 wire rounding for both slot coordinates, with 0.001 tolerance.
Tests prove precisely one compiled status slot removed and all other
commands retained, independent of phase text; gate.sh now runs this test.
Framebuffer capture contract also PASS. No engine/binary promotion or new
visual acceptance claimed. Original FONTLIST starts Courier New, matching
the browser's selected family; original font-resolution/rasterization and
the browser's 1.32 scale/2.5 offset still require measured validation.

Recovered browser loaded; corrected-slot filter verified with fresh normal
menu/start/east30/release12 capture mm-shipping-status-fixed2 under nw-core/
output/playwright. PNG SHA
fefd7d7c6125f8313b345d2d7e4ec09ef58bab9bc09779b05ef6416cfffc50e1.
Synchronized scene comparison has no failures; image visually inspected,
duplicate Press Space text gone. Remaining original-vs-browser font/UI
differences not accepted by this diagnostic comparator. Physics unchanged;
full visual phase/DPR coverage and reviewed policy still outstanding.

Corrected-filter fresh capture attempt75839 stalled on reload: console
confirms ERR_CONNECTION_RESET for local renderer/result-store modules.
Comparison was attempted too early and failed on absent PNG/JSON; no
capture/visual result claimed. Added explicit routes fulfilling unchanged
local renderer/result-store module bytes, preserving private engine routes;
reload/ready wait started. This is test transport recovery, not production fix.

Actual maintained-WASM Marble frame decoded directly with nw_frame_alloc/
nw_task_game_input_write at800x600: status center/top456,621.2999877929688,
not622; title647.52001953125/footer25.079999923706055.
Filter corrected to sub-one-reference-pixel status-slot distance, retaining
anchor/center/kind constraints. Regression covers observed binary32 coordinate
and rejecting a two-pixel-away command; PASS. First probe used nonexistent
nw_alloc and failed harmlessly, then corrected. Browser recapture pending.

Fresh UI-fixed browser reloaded and replayed ordinary menu/start/east30/
release12. Opaque capture mm-shipping-status-fixed.png SHA
e49a03af0a3d4a13b52a22f0cbf6d0d993068c89af1f01ac019ed46cc5503ec3
with direct debug/derived metadata under nw-core/output/playwright.
Synchronized scene comparison completes without failures; status overlap
visually inspected after fix. Remaining text rasterization/title/footer
differences still require review, not auto-acceptance. Receipt
status-fixed-visual-pair.json under extraction. Physics adapter bytes unchanged.
IMPORTANT: fresh image still shows status overlap; current filter did not
match actual emitted command coordinates. Fix is NOT verified; inspect
actual decoded slot rather than assuming reference456,622.

Duplicate live-status ownership fix applied at browser display-list boundary:
marble-chrome.js removes only center/top TEXT at reference456,622, the
SceneMarbleMaze status slot. index uses filter only for Marble task.
Title/help/verdict and non-Marble screens retained; host status still drawn.
Pure regression test PASS for target slot, text-independent selection,
preserved title/help/other-position/marker and input immutability.
Fresh reload/replay/capture of fix still required; no visual acceptance yet.

Opaque pair visually inspected alongside original: real status-line overlap
confirmed, not merely font antialiasing. Root cause identified: render(ctx,
decode(bytes)) already paints SceneMarbleMaze::put status at from_top62,
then drawMarbleMazeFrame paints host marbleStatusText in same slot.
Static status says Press Space while host shows running, both visible.
Correction must give one owner to dynamic status (and feedback) while
retaining title/help and matching original geometry. Do not count current
97.91% full-frame metric as accepted. UI fix not yet applied.

Fresh opaque displayed-background capture saved as nw-core/output/playwright/
mm-shipping-dpr1-release-opaque.{png,json}; JSON receipt explicitly contains
debug/readback mode/background/dimensions. Browser verified debug identical
to prior raw snapshot; metadata derivation uses that identical direct debug
JSON (opaque receipt intentionally wrapped). Scene synchronization comparator
completed, receipt dpr1-opaque-visual-pair.json under extraction root.
This explicit compositing fixes transparent UI readback, not production
rendering; original raw PNG retained for audit. Pixel verdict diagnostic-only.

Capture helper now offers explicit displayedBackground option: verifies
computed opaque black/white CSS background against captured theme,
composites to separate same-framebuffer-size alpha:false canvas with
three-argument drawImage (no scaling), snapshots in same synchronous call.
Raw mode remains default; returned readback receipt labels mode/background/
dimensions. Regression tests PASS for dimensions, draw operands, snapshot,
bad theme rejection and raw contract. New corrected browser capture and
pixel comparison still pending; no image edited or acceptance waived.

Bad-pixel capture inspected visually: stage/wood/marbles present, transparent
chrome appears black in raw PNG. Browser has exactly one canvas(screen),
800x600, CSS background rgb255/255/255. Renderer preserveDrawingBuffer=true.
Thus wrong-canvas hypothesis rejected; raw toDataURL omits CSS background,
which matters for clearRect-based transparent chrome. Investigate correct
opaque UI framebuffer painting or explicitly audited same-size CSS background
compositing; do not silently waive pixel mismatch or resample capture.
Scene-state acceptance remains separate from pixel acceptance.

Fresh stripped DPR1 release capture created via Playwright keyboard
east30/release12 fixed frames: elapsed0.7000000000000005,webgl2,
800x600 PNG db79a5cc45d17e4a428ed4a6e1915df82f7eb133542c013bd479cb6c6d7ebc15.
Files nw-core/output/playwright/mm-shipping-dpr1-release.{png,json},
derived -metadata.json. Compared existing original DPR1 release reference
in root output/playwright (initial nw-core reference path failed and corrected).
Scene synchronization checks pass, but pixel metrics are BAD:57.15% exact,
mean error107.37; chrome near255 error. Diagnostic-only, NOT visual acceptance.
Investigate framebuffer readback timing/transparency and inspect pixels
before interpreting as rendering regression; import awaited before helper
capture may cross animation tasks. Browser/server retained for correction.

Stripped candidate strict original replay14189 completed exit0:
cases80,failed[],runtimeFilesVerified=true,promoted=false. Fresh runtime
d552.../6428... now passes full strict original-source physics matrix.
Browser inspection confirms renderer=webgl2,no rendererError,settled3-of-3
materials,rung16 board889418965,grain3.2267631084747164,DPR1,800x600.
Wait30542 timed out solely because test expected wrong label
mujoco-webgl2 instead of actual webgl2; no runtime restart performed.
Browser capture/comparison and reviewed visual policy remain pending.

Fresh browser marble-shipping-oct3 navigated ordinary title/category/game
keys to Marble rung16, seed17, frozen clock,800x600,DPR1 verified.
Routes fulfill exact private JS/WASM; pre-start debug is no-board/renderer
pending as expected. Space launch issued and renderer-ready wait running;
capture not yet made. Strict replay14189 passing through rung13 at inspection.
Owned server28455/browser remain for continuation.

Strict replay14189 verified live, completed cases passing through rung5
at inspection; no final acceptance yet. Preparing fresh browser visuals:
Playwright skill fully read, npx verified. Owned server8017 handle28455
started for nw-core; owned browser session marble-shipping-oct3 opening
about:blank with Desktop Chrome DPR1. No candidate routing/capture yet.
Close only this owned session/server after captures. Earlier13 captures
are different private artifact bytes and cannot qualify this new build.

Stripped candidate all80 generated held-play matrix97057 completed exit0:
80 trace files,7 wins/41 physical losses/32 timeouts; history/cleanup PASS.
Started full original-source matrix replay using original venv interpreter
and --verify-runtime-files, logging all80-strict-source.log under extraction.
Outcome/controller success is not numerical parity: wait for all80 strict
comparators and before/after runtime hash verification. Visual remains open.

All80 generation97057 verified live, trace count advanced66->71; fresh
MuJoCo JS/WASM hashes still exactly d552.../6428....
Removed marbleSyncSolverContacts is referenced only in test diagnostic
solver-input synchronization, with explicit missing-function guard; no
production adapter use. Ordinary uninterrupted all80 generator is running
without that synchronization. Await generator completion before strict replay.

All80 stripped-candidate generation handle97057 verified live; trace count
advanced47->51 during this turn. Do not launch matrix replay until generator
exit0 and complete80 are observed. Seven strict replay/provenance regression
tests pass. Matrix replay implementation re-inspected: complete rung/seed
set, contact/event snapshots, identical provenance, explicit comparator
PASS, and actual runtime-file hashes before/after replay are required.
Next invocation must include --verify-runtime-files; acceptance still pending.

Fresh stripped candidate physics checks completed: crafted trajectory
handle65463 exit0, 162 scenarios/17263 per-frame states PASS; lifecycle
handle53798 exit0, three multi-trial/adaptive cases/seven real timeout trays
PASS. Logs under extraction root. All80 generated held-input/contact trace
generation started against same d552.../6428... module, output all80-source-
traces and all80-source-driver.log. Strict original-source replay and fresh
visual acceptance remain required; no production promotion.

Stripped shipping build3785 completed exit0; mujoco_wasm target100%.
Fresh JS SHA256 d552068dfc512e993ce4642c367421135dd26b62a54d5b394646407165030bc2;
WASM 6428e661ea292ad2004e8edb8d3337b5450e647fec6a1ffe9d132afcc5379b6f.
Crafted trajectory test started handle65463; multi-trial lifecycle53798.
Both use this exact private module. No parity result/promotion yet.
Diagnostic guard now detects marbleRecord names without trace/probe suffix;
six regression tests pass and stripped candidate still has zero findings.

Saved stripped patch revalidated against live compilation tree: git diff
SHA256 exactly matches e2c0eaf4...; reverse apply --check passes, and five
shipping diagnostic guard regression tests pass. Build3785 remains live;
bindings clang PID85928 observed running with accumulated CPU time1:17.33,
so unchanged target output is not evidence of a stopped build.
No duplicate build/restart; artifact acceptance still pending.

Stripped candidate patch saved durably as
marble_shipping_candidate_unqualified.patch, SHA256
e2c0eaf4566f4ca3a8510bfa1178cc29ee25c9cff2d9b9eb85d9be810ff12362.
Known-diagnostic-additions guard passes with empty findings; explicitly
not shipping acceptance. Build handle 3785 verified live, with clang++
actually compiling upstream generated bindings (PID85928 observed).
No restart or duplicate build launched. Artifact/parity still pending.

Stripped shipping build handle 3785 verified live: engine/static library
finished (96% target output), generated bindings/unpack compilation started.
Only observed warning is upstream miniz large-file I/O notice, not a solver
compile failure. Build still active, so artifact success is not claimed.
Trajectory and multi-trial entry points inspected: alternate module loader
uses NW_MUJOCO_WASM_MODULE, without requiring removed diagnostic bindings.
Existing trajectory tolerances remain unchanged; strict source replay is
still separately required before promotion.

Isolated stripped shipping configuration completed successfully (handle
42392 exit0; CMake configure/generate done). Started mujoco_wasm Release,
single-thread-runtime target with four build workers; build.log retained
under /private/tmp/nw-marble-shipping-extract.kS8VslBy.
Compilation result and numerical/visual acceptance remain pending;
production files unchanged.

Stripped patch review started: 13 modified engine files, 707 additions/
86 deletions before final stale diagnostic cleanup; generated bindings
match upstream. Solver review found an unused diagnostic second-derivative
increment calculation and stale probe comments/includes, now removed.
Isolated Release/no-thread WASM configuration started with verified
Emscripten 6.0.10, DEVELOPER_DIR=CommandLineTools and Homebrew Python.
Live configuration handle 42392 last observed populating qhull;
configure/build success not yet claimed. Logs under extraction root.

Remaining constraint update/state recorder definitions removed from isolated
extraction after complete inspection of the standalone end-of-file block.
Their buffers/APIs and now-unused fully inspected constraint-Hessian trace
header/include deleted. Actual mj_constraintUpdate and impl remain intact.
Diff --check PASS; targeted whole src/generated-binding diagnostic symbol
search yields no matches. This is a targeted negative check, not complete
minimality or arithmetic proof. Next: inspect full patch, compile isolated
shipping candidate and rerun independent physics/visual acceptance.

Forward warmstart state/update recording removed from isolated extraction:
four state calls, two update-record/finish brackets, declarations and local
trace offsets deleted. engine_forward.c has no trace symbols; diff check PASS.
Nonempty warmstart function comparison matches qualified diagnostic source
after removing only those diagnostic statements and whitespace, including
both actual mj_constraintUpdate calls and cost-based warmstart selection.
Constraint recorder definitions/header remain to remove before build.

Final solver trace validity enum/context field/seven assignments removed
from isolated extraction, along with the two constraint-state recording
calls and their declaration. engine_solver.c now has no trace/MARBLE_VALID
symbols; diff --check PASS. This does not prove all instrumentation absent:
engine_forward.c still calls constraint-state/update recorders, and
engine_core_constraint.c still defines them and includes the Hessian
trace header. Those must be removed together before build qualification.
Actual oldstate/dualStateChange and Hessian logic remain intact.

Newton recorder removed from isolated shipping extraction: 46 recording
calls, million-element buffer, reset/size/records/copy/run APIs, recorder
body and now-unused probe labels deleted. The diagnostic run API's forced
serial dispatch is removed with that API, not inserted into production.
No remaining Newton recorder/API/probe-label symbols; diff --check PASS.
Trace-valid bits and constraint-state recorder plumbing still remain and
need coordinated removal. Full arithmetic comparison/build/parity remains
pending; no production promotion.

Generic QCQP kernel recorder removed from isolated shipping extraction:
fully inspected marble_qcqp_kernel_trace.h deleted, include removed,
prefactor/prior-lambda diagnostic copies and four recorder calls removed.
Whole src group-symbol search clean; diff --check PASS. Nonempty mju_QCQP
comparison with qualified source matches after removing only those
diagnostic statements and whitespace. Rank check, twenty-iteration bound,
convergence/update thresholds, fused residual, derivative and scaling
are retained. Arithmetic-bearing marble_rank/norm/product locals retained.
Newton and constraint-state traces remain; rebuilt shipping parity pending.

Contact QCQP witness tracing removed from isolated shipping extraction:
fully inspected marble_qcqp_trace.h deleted, including include/reset/enables,
witness copies/locals/recording and kernel recording brackets/declarations.
solveQCQP no longer accepts a witness; both callers updated. costChange's
diagnostic-only restored output removed and all three callers updated.
Actual QCQP2/QCQP3/QCQP selection, friction projection, force assignment,
restoration and per-contact improvement accumulation remain.
Solver search has no witness/recorder/restored symbols; diff --check PASS.
QCQP kernel instrumentation in engine_util_solve.c and Newton traces still
remain. No rebuilt numerical parity or shipping promotion claimed.

Cost-change snapshot tracing removed from isolated shipping extraction:
complete inspected marble_costchange_trace.h and its include/owner brackets/
enable/reset callers deleted; diagnostic force copies, partial return captures
and final recorder removed. costChange keeps the original tracing-disabled
quadratic/dot expression, scalar branch, force-restoration threshold/action
and restored output (still needed by remaining QCQP diagnostics).
Whole src search finds no cost-change recorder symbols; the separate
marbleCostRowDot arithmetic helper in engine_util_blas.c is retained.
Diff --check PASS. Unlike a whitespace
comparison this removal selects the existing non-recording branch; rebuilt
numerical parity must still prove it. Shipping artifact remains unqualified.

Prepared/evaluated line-search snapshots removed from isolated shipping
extraction: both diagnostic headers, includes, begin/end brackets, context
association ordinal/init, unclamped-derivative diagnostic copy, and two
recording calls deleted. Headers were inspected completely: recorders copied
operands/results and updated only diagnostic buffers/association state.
Actual PrimalPrepare, PrimalEval, assigned derivatives, convexity clamp and
LSiter increment remain. Whole src symbol search clean; diff --check PASS.
Newton/QCQP/cost tracing remains; rebuild/parity qualification still pending.

Gauss operand/partial-sum tracing removed from isolated shipping extraction:
marble_gauss_trace.h deleted with its include/reset/begin/end callers;
PrimalUpdateConstraint diagnostic partial array, prior-cost copy, enabled flag,
per-dof snapshot and final recorder removed. Whole src symbol search clean;
diff --check PASS. Nonempty Gauss arithmetic slice matches the qualified
source after stripping only diagnostic statements and whitespace.
The rounded eight-dof prefix/fused tail policy is retained exactly.
Remaining Newton/QCQP/prepare/eval/cost traces still need removal; this
is not a rebuilt/parity-qualified shipping artifact or production promotion.

Detailed cone recorder removed from isolated shipping extraction: buffer,
append helper, size/copy APIs, reset, recording brackets and HessianCone
snapshot calls/local diagnostic headers deleted. Whole src symbol search
is clean and diff --check passes. Nonempty HessianCone function comparison
against qualified diagnostic source matches after stripping only recorder
statements/brackets and whitespace; dense/sparse cone arithmetic retained.
Newton/QCQP and other header-based traces still remain; no rebuilt shipping
qualification or production promotion claimed.

Hessian input/output and final cone-factor snapshots removed from isolated
shipping extraction: million-element buffer, recorder trio, size/copy APIs,
flags/resets and three FactorizeHessian call sites deleted. Whole src search
finds no remaining group symbols; diff --check PASS.
FactorizeHessian matches the qualified diagnostic source after removing
only these recorder calls and whitespace, including dense/sparse
factorization and actual HessianCone invocation. Detailed cone/Newton/QCQP
tracing remains. The stripped artifact is still unbuilt/unqualified.

Solver Cholesky operand snapshot group removed from isolated shipping extraction:
million-element buffer, recorder, size/copy APIs, reset and two call sites
deleted, including their now-unused local factor aliases. Whole src search
finds no remaining group symbols. PrimalUpdateMgrad matches the qualified
diagnostic source after stripping these diagnostic statements, the previously
removed dense-solve trace begin/end bracket, and whitespace; actual
dense/sparse solve operands and arithmetic retained.
Source diff check passes. Rebuild and independent parity remain pending.

Constraint iteration snapshot group removed from the isolated shipping extraction:
million-element buffer, schema/size/overflow/copy APIs, snapshot recorder and
two primal-update calls/resets deleted. No remaining group symbols;
diff --check PASS. The actual constraint update and trace-valid cost bit
(still consumed by remaining Newton diagnostics) are retained.
Hessian/cone/Newton/QCQP instrumentation remains. This is source cleanup,
not a rebuilt or parity-qualified shipping artifact; production unchanged.

Constraint input/output snapshot group removed in shipping extraction:
million-element buffer,4 getter/copy/recorder functions, flags/resets and
primal update bracket deleted. No remaining group symbols; diff --check PASS.
Actual mj_constraintUpdate_impl and its cost/force/state outputs retained.
Iteration snapshots, Hessian/cone/Newton/QCQP instrumentation still remain;
stripped build and full independent parity not yet qualified.

Sparse-input snapshot group removed from shipping extraction: million-element
buffer, getter/copy/recorder, reset and matrix-product snapshots deleted.
Actual mju_mulSymVecSparse/flex updates retained. Diff --check PASS.
Constraint-input and other Newton traces remain; stripped build unqualified.

Primal Jv/Jaref/update trace groups removed from shipping extraction:
three buffers/resets,10 getter/copy/recorder functions, capture calls and
update bracket deleted. Actual Jv/Jaref computations and alpha updates
preserved. No remaining recorder symbols, diff --check PASS. Newton/QCQP/
constraint/sparse trace instrumentation still remains; no rebuild verdict.

No-slip basic recorder/buffer/getters/reset/declaration/call removed from
shipping extraction, along with unused raw_improvement diagnostic copy.
Audit confirmed oldstate remains consumed by dualStateChange, so preserved
it; production improvement scaling/saveStats unchanged. Diff --check PASS.
QCQP witnesses and primal/Newton trace plumbing still pending; no promotion.

No-slip step/contact recorder groups removed from shipping extraction:
both declarations/calls, recorder bodies, getters/copy APIs,200000-element
buffers and resets deleted. Production contact_change/improvement updates
preserved. Diff --check PASS. Remaining oldstate/raw_improvement capture
scratch may now be diagnostic-only and needs caller/use audit next; basic
no-slip/QCQP/Newton traces still remain. No rebuilt parity acceptance.

No-slip input recorder removed as a complete group in shipping extraction:
262144-element buffer, matrix/force snapshot recorder, size/copy getters,
solNoSlip capture call and diagnostic reset deleted. No remaining symbols
in src; diff --check PASS. Production no-slip updates untouched. Step/contact
recorders and QCQP/Newton instrumentation remain; no rebuilt parity proof.

Cholesky rank-update trace path removed: util_solve declaration/call and
solver recorder function deleted. mju_cholUpdate full function equals
qualified source byte-for-byte after removing just recorder call; FMA and
rank behavior preserved. Diff --check PASS. Cone trace storage/other recorder
callers remain and must be stripped later. No shipping build/parity verdict.

Dense Cholesky trace fully removed in shipping extraction: million-element
buffer, reset/begin/end/size/copy functions, solver declarations/calls, and
per-substitution recording deleted. mju_cholSolve arithmetic tokens compare
equal to qualified source after removing only recorder syntax; backward FMA
ordering preserved. No dense-trace references in solver/util_solve, diff
--check PASS. Other instrumentation remains; no build/parity qualification.

Removed engine inertia/Gauss/evaluation packet-probe bodies in shipping
extraction after their bindings were removed. These bounded diagnostic
bridges called production kernels; ordinary kernels left untouched.
No remaining probe-symbol references in src; diff --check PASS. Solver
trace instrumentation still remains, so no shipping parity/build claim.
Bindings file was additionally cleaned back to exact pinned upstream content
(git diff --exit-code passed), removing leftover diagnostic comments/includes.

Removed remaining seven diagnostic browser wrappers: free-joint solve/
advance/derivative, solver-contact injection, and constraint begin/end/copy.
Their exports and last4 diagnostic C declarations also removed. No production
adapter uses solver-contact injection (test-only diagnostic replay hook).
Shipping bindings now contain no Marble diagnostic exports. Engine traces
remain; build/parity still unqualified. Diff --check PASS; qualified source
and production vendor unchanged.

Removed inertia/Gauss/evaluation packet browser interfaces and their C
declarations from shipping extraction. Diff --check PASS. Engine probe
bodies remain for next cleanup; bindings also still contain free-joint,
constraint-trace and solver-contact diagnostic wrappers. No packet removal
changes ordinary engine arithmetic. Full extraction/build/parity incomplete.

Removed76 now-unused diagnostic C declarations from shipping bindings:
each symbol's whole-file occurrence count was exactly1 before deletion.
Also removed marbleWheelFmaProbe export/declaration only; production engine
FMA function preserved. Remaining Gauss/eval/inertia probe bindings still
have real callers and were retained for coordinated next removal. Diff
--check PASS. Engine trace bodies still present; shipping build unqualified.

Removed complete242-line marble_newton_trace_wrapper and marbleNewtonTrace
Embind export from isolated shipping checkout. This diagnostic-only browser
interface copied Newton/no-slip/jaref/QCQP/constraint trace arrays into JS;
ordinary engine solver execution untouched. No remaining wrapper/export
reference; diff --check PASS. C declarations and engine trace buffers/calls
remain to be removed in coordinated cleanup. No shipping build qualification.

QCQP2/QCQP5 packet diagnostics removed in isolated shipping extraction:
both engine wrappers, C declarations and Embind exports deleted. Full solve
file diff against qualified source contains only the two diagnostic function
removals, preserving actual mju_QCQP2/mju_QCQP3/mju_QCQP arithmetic. Diff
--check PASS. QCQP witnesses/trace headers, Newton/constraint buffers and
other probes remain; not a qualified shipping artifact and no promotion.

Removed cost-primitives diagnostic packet probe, C binding declaration and
marbleCostPrimitivesProbe export from shipping extraction. Full BLAS file
diff against qualified checkout contains only removal of that diagnostic
block; public dot/quadratic producers unchanged. No remaining symbol
references; diff --check PASS. Other probes and trace instrumentation remain;
no shipping build/parity proof yet, qualified candidate preserved.

Removed bounded residual diagnostic packet probe across engine definition,
generated C declaration and marbleWheelResidualProbe binding in isolated
shipping extraction. Ordinary residual() full source slice SHA matches
qualified source3cd00c59efe5c90c3cf15db0d93ad58adff03554dc06eaa030d4a726c2a85713;
dot/FMA helpers untouched. Diff --check PASS. QCQP/cost-change/Newton trace
plumbing still remains; extraction unbuilt/unqualified and no promotion.

Constraint-update production hook cleanup in isolated shipping extraction:
removed Hessian trace-call counter, active Hessian recorder and classified
state/force recorder from mj_constraintUpdate_impl. Full function token
comparison against qualified source after deleting only those diagnostics
matches; diff --check PASS. Trace buffers/functions/header remain because
solver/binding diagnostics still reference them; remove coordinated callers
before deleting definitions. This source cleanup is not rebuilt parity proof.

Free-bias trace plumbing removed in isolated shipping extraction:27 trace
copy calls, TRACE_VALUES macro/cursor and trace parameter deleted; both
production call sites updated to omit NULL. Compared complete helper source
against qualified diagnostic version after removing only trace syntax and
whitespace: arithmetic tokens unchanged. Other solver/constraint diagnostics
remain; no build or parity qualification yet. Qualified source preserved.

Removed unused mjd_freeJoint_qDeriv_probe from shipping extraction after
whole-checkout search showed only its definition (no binding/caller).
Ordinary mjd_smooth_vel unchanged. Shipping guard now also rejects derivative
TRACE_VALUES macros; five tests PASS, isolated diff whitespace check PASS.
Remaining freeBias_vel_blocks trace parameter/macro/calls must be stripped
without changing matrix arithmetic; solver/constraint traces also pending.
No build/acceptance claim or production promotion.

RNE diagnostic engine mirror fully removed from isolated shipping extraction:
projection trace size/body and Python compatibility trace aliases deleted.
No mj_rne_*trace references remain in engine source or generated bindings;
git diff --check PASS. Ordinary mj_rne-to-mj_rnePostConstraint source slice
hash compared against qualified diagnostic checkout (unchanged). Other solver/
constraint/derivative diagnostics remain, so extraction is still not a build
or parity-qualified shipping artifact. Qualified source/patch untouched.

Shipping extraction continues in kS8VslBy/upstream: removed RNE projection
diagnostic browser declaration/wrapper/Embind export. Engine diagnostic
mirror and compatibility aliases still remain and must be removed next;
ordinary mj_rne arithmetic untouched. Shipping guard fixed to recognize
camelCase Marble Trace/Probe exports and mjd derivative trace/probe symbols,
which initial regex missed. Four tests PASS; isolated git diff --check PASS.
Extraction still incomplete and unbuilt; never treat guard as parity proof.

Minimal shipping extraction STARTED in independent clone
/private/tmp/nw-marble-shipping-extract.kS8VslBy/upstream, pinned13827e9…;
complete qualified diagnostic patch applied cleanly. Removed first dedicated
free-bias intermediate probe across engine wrapper, C declaration, C++ wrapper
and Embind export. Retained production freeBias_vel_blocks arithmetic and its
ordinary callers unchanged. This is partial extraction, not build/parity proof:
many trace hooks/headers and other probe exports still remain; guard must reject
until fully removed. Qualified clean source/patch and vendor files untouched.

Shipping extraction guard added: test/marble_shipping_patch_guard.py scans
added lines/headers for known Marble/mj/mju trace/probe symbols; rejects full
diagnostic candidate while allowing removal-only cleanup and qualified FMA
arithmetic names. Three regression tests PASS and included in portable gate.
This negative guard is NOT proof of minimality/parity/visual acceptance. Seven
diagnostic headers plus solver hooks must be removed together; preserve full
qualified diagnostic patch. Shipping extraction/build not yet completed.

Strict wrapper original replay COMPLETE PASS: session80235 exit0, final
receipt cases80/failed[]/runtimeFilesVerified:true/promoted:false. Exact new
728e7c365… JS/c3bdf543… WASM independently qualified against original native
per-frame/contact/result traces, with actual runtime hashes checked both
before and after. Prior pending notes superseded. Output root retains
all80-strict-source.log; crafted162/17,263state and lifecycle3/7 receipts also
pass. Fresh browser visuals for these new bytes remain required; earlier13
capture pairs used fe1fb613…/c2df1704… and cannot be inherited. Minimal shipping
patch qualification and human-reviewed pixel policy remain open. No promotion.

Strict wrapper replay session80235 remains live; completed rows through
rung9/seed314159 exit0, no failed verdict observed so far (not overallPASS).
Isolated builder now retains exact candidate.patch, upstream-commit.txt,
emscripten-version.txt, cmake-version.txt and artifact-sha256.txt before
successful scratch cleanup. Three builder contract tests PASS. This receipt
addition applies to FUTURE builds; already-completed wrapper output contains
its earlier logs/cache and binary hashes, not these new provenance files.
Physics patch/compiler flags unchanged by receipt retention. No promotion.

Wrapper artifact80-case generation COMPLETE PASS: session75975 exit0,
7wins/41physical losses/32timeouts, complete80 trace files. Started strict
original replay session80235 with --verify-runtime-files; receipt wrapper output root
all80-strict-source.log. Hash guard now checks before AND after replay to
reject mid-run runtime changes. Seven verifier tests PASS. Original replay
verdict pending; do not infer it from generated-controller success.

Fresh wrapper artifact generation session75975 remains live,65/80 trace files
observed (not a completed-matrix verdict). Added optional
marble_source_matrix_replay.py --verify-runtime-files: before replay, hash
all3 adapter files, core WASM, trace harness, MuJoCo JS/WASM against recorded
absolute-path provenance. Changed or missing bytes reject qualification;
historical replay without this flag remains available but output explicitly
records runtimeFilesVerified:false. Seven verifier tests PASS, including live
bytes match, changed WASM rejection and missing WASM rejection. Use this flag
when qualifying new wrapper artifacts after generation exits0. Comparator
edit does not alter running generator or its recorded harness hash.

Checked-in diagnostic wrapper end-to-end build SUCCESS (session53330 exit0).
Output/private/tmp/nw-marble-wrapper-qualified-oct3 retains build/configure
logs and CMakeCache; successful wrapper cleaned its owned scratch checkout.
JS SHA256728e7c36584c5f4e3767824461531d5a8d994ff1aabfe0f15f2fb16c0680e558;
WASM SHA256c3bdf5432da452d44c51a06ee68b7cd1ca8a509d8eb5b39b9f2ec9ff5eb89227.
Multi-trial lifecycle PASS (session37397 exit0,3cases/7timeout trays);
crafted trajectory suite exit0 (session74813). Receipts multi-trial.log and
crafted-trajectories.log in output root. Fresh80-case input/contact trace
generation now running session75975, receipt all80-source-driver.log and
all80-source-traces directory. Initial generator invocation exited1 because
directory was absent; created directory and reran only that failed generator,
not build. Strict original replay remains pending. New artifact identities
differ from previous private build; no inherited parity or visual verdict.
Complete diagnostic recipe is reproducibly executable, not byte-reproducible
or minimal shipping qualification. No production promotion.

Build session53330 remains live during bindings compilation. Compiler82173
observed98%CPU, CPUtime1:46 at elapsed2:06: active work, not a hang despite
unchanged98% log. Source ABI fixture standalone check PASS (this is an
executable assertion script, not a unittest-discovery module). No new binary
or qualification verdict yet; continue polling same handle, do not restart.

Wrapper build session53330 revalidated live: configure completed successfully
(57.9s), static MuJoCo library built, generated bindings compilation at98%.
clang++ process82173 observed executing; no build verdict or artifact yet.
Do not restart on unchanged buffered output. Six source-matrix verifier tests
PASS. After successful build: run trajectory and multi-trial suites with
NW_MUJOCO_WASM_MODULE=/private/tmp/nw-marble-wrapper-qualified-oct3/mujoco.js;
generate fresh80-case held-play/contact traces with that exact module and
strictly replay them using original Python. Previous candidate receipts do
not qualify these new bytes. Destination still isolated; no promotion.

Checked-in diagnostic wrapper end-to-end qualification STARTED, not yet
passed: exec session53330, output destination/private/tmp/
nw-marble-wrapper-qualified-oct3, scratch directory
/var/folders/k7/71kp36qd5_q9_tfp77s2vqzc0000gn/T/nw-marble-diagnostic-rebuild.bieXZl9K.
Invoked with DEVELOPER_DIR=/Library/Developer/CommandLineTools and
EMSDK_PYTHON=/opt/homebrew/bin/python3. Unqualified default emcc invocation
still selects Xcode Python3.9 and fails Emscripten's>=3.10 assertion, hence
explicit override. Verified live handle; clone resolves pinned13827e9…;
configuration in progress. Two builder contract tests PASS. Resume by polling
session53330 before considering any restart; logs in scratch. This validates
the complete diagnostic recipe only, not the minimal shipping recipe; artifact
must pass full source/lifecycle/visual qualification after build. No production
files changed by the isolated builder.

DPR1 source/browser rolling pair PASS: headed Desktop Chrome device context,
devicePixelRatio asserted1, actual800x600 raw framebuffer. Same rung16/seed17
east30/released12 replay passes strict metadata and synchronized scene/camera.
Receipt output/playwright/mm-dpr1-release-render-diagnostic.json, browser PNG
SHA2563c56936d83bb2dc875106e874334f7cf8ca9ce65cb57af16907848a9709504f4.
Inventory13pairs; one DPR1 case only, broader phases/hardware remain unproven.
Pixel-policy/minimal-shipping qualification still open; candidate only.
Owned browser marble-dpr1-oct3 closed and server stopped.

DPR1 source reference capture succeeds with Pyglet's documented real-pixel
window mode selected by process-local PYGLET_DPI_SCALING=real and strict
NW_MARBLE_PAIR_EXPECT_DPR=1 guard. Actual framebuffer800x600/scale1, rung16/
runseed17, east30 frames then neutral12, Float32 board. No image downsampling
or source checkout edits. Source capture now records dpiScalingOverride in
sourceWindow provenance. Artifacts output/playwright/mm-source-dpr1-release.
Browser DPR1 pair remains pending; this configured original reference does
not claim native standard-density monitor validation or paired acceptance.

Physical LOSS pair PASS: browser actual input replay rung2/runseed1 matches
source settled lost, including board, poses, elapsed time and feedback.
Synthetic KeyboardEvents use normal key handlers; no trace state injection.
Capture raw PNG/debug in same task; receipt output/playwright/
mm-physical-loss-current-render-diagnostic.json. Browser PNG SHA256
1d257d33bdb376e1c4e6060f7848e89c9888b989599629192c9b02c075cc1d33.
Explicit inventory now12pairs, diagnostic-only. Previous source-only pending
note below superseded. DPR1/pixel-policy/minimal-shipping qualification remain.
Owned capture server stopped; browser marble-loss-oct3 closed. Production
binaries not promoted; same isolated fe1fb613…/c2df1704… candidate routed.

Physical LOSS source reference now succeeds at rung2/runseed1: replay of
all80-source-traces/2-1.json through actual source UI inputs reaches settled
lost without timeout or pose injection. Capture output/playwright/
mm-source-physical-loss-current.{png,json}, boardSeed288545018, grainSeed
2.276815499288849, raw1600x1200 (800x600/DPR2). Removed the capture helper's
artificial rung1 restriction ONLY for physical replay; forced discrete-state
fixtures still require rung1/no scripted motion. Five physical-capture tests
PASS, including all16 physical rungs and forced-fixture rejection. Browser
matching loss replay remains pending; do not add source-only pair to inventory.

Physical WIN and DONE source/browser pairs now PASS strict metadata and
synchronized scene/camera comparison. The browser replays the same628 fixed
frames and12 level actions through normal window key handlers (synthetic
KeyboardEvents, not OS/isTrusted input), never trace poses. Source independently
replays UI inputs; DONE uses original _next_trial(), browser uses Space after
physical win. Both800x600 logical/DPR2, rung1/runseed17/Float32 board.
Receipts: output/playwright/mm-physical-win-current-render-diagnostic.json and
mm-physical-done-current-render-diagnostic.json. Raw PNG/debug captured together.
Browser PNG SHA256: win8f3b25930f3f8a6559eca9d691b1819fb3de23bf99ec80abf110aef6306d7070;
done2f5b84f50bf3c817db9c10865fdd70a3f1c66a856eba4bd10a014ea5c6ca0f3e.
Inventory now explicitly lists11 pairs; previous source-only pending notes
below are historical. These are diagnostic-only, not reviewed pixel acceptance.
Physical loss (not timeout), DPR1, reviewed pixel policy, and minimal shipping
build qualification remain open. Private candidate only; no binary promotion.
Owned browser marble-win-oct3 closed and capture server stopped.

Fresh original PHYSICAL WIN capture succeeds: runseed17/rung1, Float32
board,800x600 logical/DPR2. New --input-trace reads only bounded frame dt/held
and level actions (1..8000 events, dt<=50ms), explicitly discards recorded
poses. Replays private clean all80-source-traces/1-17.json (628frames/12level
actions) through source UI held/update/level_tray, then requires settled won.
Output/playwright/mm-source-physical-win-current.{png,json} exits0; metadata
terminalFixture physical-replay, inputTrace SHA/event count/posesInjected:false.
Four portable capture tests PASS (including pose discard/invalid input
rejection); renderer contract PASS. Browser matching input replay still
pending; do not add source-only win to paired coverage. No terminal-state
assignment, camera injection, production binary write, or acceptance claim.

Added source physical terminal capture mode: --require-physical-outcome
with won/lost/done allows bounded held/staged replay, requires source phase
and settled Simulation to have reached requested outcome, and skips all
forced marble-state assignment. Ordinary renderer fixtures keep existing
behavior but new metadata labels terminalFixture physical-replay versus
forced-discrete-state versus none. Inventory exposes unrecorded for older
metadata instead of inferring physical qualification. Two portable rejection/
settlement tests PASS and included in gate; renderer contract PASS. Actual
original neutral unreached-win request exits1 with "physical capture requires
settled won, got 'rolling'" and produces no falsely qualified capture.
Successful physical win/loss captures and browser pairs remain pending;
this adds faithful capture capability, not acceptance of terminal coverage.

Fresh timeout pair PASS strict metadata and synchronized scene/camera:
rung1/runseed17/nonadaptive/one trial/15s,800x600 logical/DPR2. Browser reaches
unsettled timeout through900 neutral fixed frames, feedback frozen only for
capture, raw helper snapshots PNG/debug together. Original independently
uses real update() timeout loop and Float32 fixture; both phase lost with
terminalReason timeout/live marble still rolling. No terminal-pose injection.
Receipt output/playwright/mm-timeout-current-render-diagnostic.json with
source/browser PNG, debug and metadata; diagnostic-only, not pixel acceptance.
Two startup waits timed out following renderer/result-store local socket
resets. Route fulfillment of those two UNCHANGED local JS files bypassed
transport failure; same private physics fe1fb613…/c2df1704… routed as before.
No maintained source/binary changes. Owned session/server closed/stopped.
Added timeout to inventory: nine pairs; physical won/lost and done, DPR1,
reviewed pixel policy and shipping qualification remain open.

Prepared fresh original timeout reference through real update() loop:
outcome timeout/rung1/runseed17/15s/Float32 fixture/800x600 logical/DPR2.
Capture exits0; output/playwright/mm-source-timeout-current.{png,json}.
Browser paired capture remains pending; do NOT add source-only reference to
accepted paired inventory. No terminal-state injection or production change.
Evidence audit now rejects valid JSON of wrong top-level shape (null/list/
boolean/number/string) rather than crashing with AttributeError; verifies
scene-state metadata object and reports TypeError as pair failure. Four
regression groups PASS; eight-pair current audit rerun exits0. All verdicts
remain diagnostic-only, accepted:false. Next compare fresh timeout reference
to independent browser900-frame timeout with frozen feedback/raw helper.

Fresh READY pair passes strict metadata and synchronized scene/camera
qualification: rung1/runseed17,800x600 logical/1600x1200 framebuffer, light.
Browser uses ordinary menu navigation into Marble without starting; source
--outcome ready. Raw helper snapshots PNG/debug together; no generated board,
no marbles, zero clock. Receipt output/playwright/mm-ready-current-render-diagnostic.json,
with mm-source-ready-current and mm-browser-ready-current artifacts. Private
clean physics routed as before but no physics tray instantiated in this phase.
Added pair to audit; now eight listed cases cover ready+rolling atDPR2.
Terminal phases, DPR1, pixel policy and shipping qualification remain open.
Owned ready session closed/server8013 stopped; no maintained binary write.

Current visual evidence inventory implemented: test/marble_visual_evidence_audit.py
reexecutes strict synchronized scene/camera comparator on seven explicit
current pairs, binding PNG hashes through their metadata rather than trusting
old receipts. Fresh audit exits0, seven pairs/failures[], accepted:false;
output/playwright/mm-current-visual-evidence-audit.json. Current listed coverage
is ONLY rolling phase and DPR2 (themes light/dark; alternate viewport included).
Ready/won/lost/done and DPR1 remain fresh-qualification gaps, not covered by
motion/rollover screenshots. Three portable fail-closed audit tests PASS and
added to gate: failed/missing pair, malformed JSON, and substituted accepted
verdict reject. Inventory never grants pixel-policy approval or shipping
acceptance. Next prioritize these phase/DPR gaps and shipping build rather
than repeating already-covered rolling screenshots.

Raw helper browser integration PASS: live import of test/marble_framebuffer_capture.mjs
after independent rung16/800x600 logical east30/release12 replay returns PNG
and debug together. Downloads both from that same saved capture, not fresh
debug. PNG1600x1200 SHA4564bacdd0fc524d470188663ea992d3deb874c9bba563cd8607450d8dc3c9b8
matches previous raw capture byte-for-byte. Strict metadata and synchronized
scene/camera comparator exit0; durable output/playwright/mm-helper-800x600-release-*
receipt remains diagnostic-only. First page load result-store.js socket failure
caused terminal wait timeout; same-session reload succeeded. Do not conflate
that failed startup with parity evidence. Private physics fe1fb613…/c2df1704…
served by route fulfillment, maintained binaries unchanged. Owned helper
browser closed/server8013 stopped. Earlier helper-unverified note superseded.

Added reusable test-only raw framebuffer helper and capture instructions:
test/marble_framebuffer_capture.mjs and repro/marble_framebuffer_capture.md.
Requires frozen test clock/exact live framebuffer dimensions; captures PNG
and cloned debug state in one synchronous task, no CSS readback/resampling.
Portable Node contract PASS; included in gate. Browser integration of the
new helper NOT yet run; previous raw800x600 capture remains separate evidence.
No production shell/runtime change. Next use helper for remaining DPR/phase
captures, and record physics provenance separately; policy review pending.

Fresh alternate viewport PASS synchronized scene/camera: rung16/runseed17,
light theme,800x600 logical/1600x1200 framebuffer,30 east-held frames then12
released frames, independent original Float32 fixture/browser fixed stepping.
Initial page import result-store.js request reset; first run timed out, reload
succeeded. Element screenshot measured1600x1202 due CSS fractional positioning;
strict metadata verifier correctly rejected that image. Captured raw canvas
PNG via toDataURL, no cropping/rescaling, dimensions1600x1200; qualified
metadata and synchronized comparator then exit0 diagnostic-only. Retain raw
rejected screenshot separately. Valid pair uses mm-source-r16-800x600-release.png
and mm-browser-r16-800x600-release-framebuffer.png under output/playwright;
receipt mm-r16-800x600-release-render-diagnostic.json. Private candidate route
fe1fb613…/c2df1704…, no maintained binaries changed. Owned viewport session
closed/server8013 stopped. Async user question asks whether to review bounded
cross-rasterizer differences or demand exact pixels; no approval inferred.

Visual metadata verifier strengthened: controller first12 ABI values must
be exact safe integers (no bool/string/fractional/out-of-safe-range coercion),
and generated-board controller seed must equal source/board seed. Previously
the board seed alone was checked; stale controller seed could qualify.
Regression suite PASS including explicit malformed-state/seed rejection.
Requalified six existing live-debug/image pairs with stricter helper: flat
rung16, dark-east30, release, restart, manual tray2 and automatic tray2.
All pass and qualified metadata regenerated; images unchanged. This closes
that evidence-consistency gap, not physics/visual acceptance or promotion.

Common-controller feedback boundary regression now replaces one2600ms jump
with2599ms + zero-time update +1ms in every real timeout tray of the
multi-trial/adaptive matrix. At2599ms require phase feedback, remaining1ms,
unchanged board seed/result-row count; zero update preserves complete state;
final1ms transitions to PREPARING or DONE as appropriate. Fresh private clean
pair run exits0, three cases/seven timeout trays, receipt
/private/tmp/nw-marble-clean-repro.25heUla5/feedback-boundary-multi-trial.log.
Original source update uses now>=until and FEEDBACK_SECONDS2.6. This regression
qualifies integer controller deadline behavior, not submillisecond browser
wall-clock bookkeeping; retain that distinction from previous host capture.
No compiler/game change or binary promotion was required for this case.

Automatic host rollover PASS: browser runseed17/rung1/nonadaptive/two trials/
15s advances900 neutral fixed frames, verifies first-tray timeout, waits
2700ms wall time, then ticks WITHOUT Space. Host deals tray2 at elapsed0;
twelve subsequent neutral frames produce200ms. Corrected original automatic
transition reference matches synchronized board/grain/scene/camera; comparator
exits0 diagnostic-only. Browser PNG SHA9d25d2b1d2e0452208a2b4c07cd00bb06ded34bf62b2dc4b5aade1a60c814271
also equals prior manual-next frame, independently confirming resulting view.
Durable receipt output/playwright/mm-nexttrial200-auto-render-diagnostic.json
with associated browser/debug/qualified metadata. This qualifies a delayed
automatic feedback tick, NOT the exact2600ms boundary or all lifecycle paths.
Private clean pair remains isolated; no maintained artifact write. Owned
marble-auto-oct3 session closed/server8013 stopped.

Fresh second-tray pair PASS synchronized scene/camera: rung1/runseed17,
two trials/nonadaptive/15s, Retina1824x1368. Browser independently advances
900 neutral frames to real unsettled timeout, ordinary Space next, then
12 neutral frames to200ms. Reference uses actual original automatic feedback
deadline/update transition and corrected Float32 fixture. Board785170443/
grain1.158501511057862 match. No source pose injected. Durable capture/debug/
metadata quartet and diagnostic comparison under output/playwright/
mm-nexttrial200-f32-*. Fullframe exactfraction0.9906874390838206,
MAE1.1322598457336426; failures[]. Verdict remains diagnostic-only.
This qualifies the resulting scene, not equivalence of Space vs automatic
feedback timing; deadline timing gates remain separate. Private pair
fe1fb613…/c2df1704… served by route fulfillment; maintained binaries untouched.
Also hardened both fixture rebuild paths with finally restoration of RNG
and grain; injected scene-error regression proves identity restored while
the exception propagates. ABI fixture and renderer contract PASS.
Owned session marble-rollover-oct3 closed/server8013 stopped.

Second-tray Float32 fixture fixes: --board-abi-f32 previously converted only
tray1, then mislabeled unrounded tray2 geometry as Float32. Rollover now
rebuilds its converted board before advancing; expected seeded tray is also
converted for identity qualification. Live replay exposed another fixture
error: _build_scene consumes rng.random(), so fixture rebuilding shifted
the next board stream even when grain_seed was restored. Both initial and
rollover fixture rebuilds now preserve RNG getstate/setstate as well as grain.
Extended ABI regression verifies simulation/scene share rounded geometry,
original tray unchanged, grain and RNG unchanged. ABI fixture and renderer
contract PASS. Actual original next-trial/two-trial/200ms Float32 capture
now exits0 with expected board785170443/grain1.158501511057862;
output/playwright/mm-nexttrial200-f32-source.{png,json}. Independent metadata
check confirms board dimensions, wall coordinates, and hole geometry are
exact Math.fround values; elapsedMs200. This repairs the harness, not the
game/compiler. Older Float32 rollover reference receipts need regeneration;
do not reuse their incorrectly labeled source geometry/RNG qualification.
Browser second-tray paired capture remains pending; production unchanged.

Capture-helper correction: next-trial nonzero elapsed option was unusable:
it advanced requested frames then unconditionally required sim.elapsed==0.
Actual original UI reproduction with next-trial/two trials/200ms failed at
phase rolling/trial2/elapsed0.20000000000000004 with correct second board.
Corrected qualification checks requested milliseconds with absolute1e-12
step-roundoff allowance (no relative tolerance). Zero-time behavior preserved;
incorrect/nonfinite clocks still rejected. Two regression methods PASS and
included in portable gate. Actual original 200ms second-tray capture now
exits0; output/playwright/mm-nexttrial200-source.{png,json} retained, board
seed785170443/grain1.158501511057862. This is a capture-harness fix, not a
game/compiler change, and does not yet qualify the browser second-tray pair.
No production binary write; remaining visual and shipping gates stay open.

Fresh restart qualification: rung16/runseed17/light, one trial, Retina
1824x1368 framebuffer. Both implementations replay thirty east-held frames,
twelve released frames, real restart(), then twelve neutral frames. Browser
uses ordinary r key and fixed-frame test clock, no pose injection. Paired
metadata and synchronized scene/camera checks pass with no failures;
stage exactfraction0.9980231265781034, MAE0.1161879152059555; fullframe
exactfraction0.9875823169949728, MAE1.5796144008636475. Source restart message
verified directly against ui/marblemaze.py; browser capture visually inspected.
Durable output/playwright/mm-clean-oct3-r16-restart-render-diagnostic.json
and associated PNG/debug/metadata artifacts retained. Verdict diagnostic-only,
not reviewed rasterizer acceptance. Candidate fe1fb613…/c2df1704… remained
private via route fulfillment. Session marble-restart-oct3 closed and owned
server8013 stopped. Terminal and viewport/DPR coverage remain next steps.

Fresh release qualification: rung16/runseed17/light, one trial, 912x684
logical/1824x1368 framebuffer. Original --move E --move-frames30
--release-frames12 --board-abi-f32 compared to ordinary browser east keydown,
thirty fixed frames, keyup, twelve neutral fixed frames. No pose injection.
Paired metadata and synchronized scene/camera comparator pass; stage exact
fraction0.9984679750663116, MAE0.0483027845621109; fullframe exactfraction
0.9896478563917103, MAE1.2028039693832397. Existing tolerances unchanged.
Durable receipt output/playwright/mm-clean-oct3-r16-release-render-diagnostic.json;
associated source/browser PNGs, metadata, and raw debug JSON share that
prefix. Physics remains private clean pair fe1fb613…/c2df1704… through browser
route fulfillment. Verdict diagnostic-only; no pixel acceptance or promotion.
Session marble-release-oct3 closed; owned local server8013 stopped.
Next: independently replay restart and terminal phases plus viewport/DPR
coverage. These motion receipts do not establish all phase or timing behavior.

Fresh dark motion qualification: rung16/runseed17, one trial, 912x684 logical
layout/1824x1368 framebuffer, thirty east-held 60Hz frames. Original capture
uses --board-abi-f32; browser uses ordinary ArrowRight keydown/up and exactly
thirty marbleTestStepFixedFrame calls, NOT source-pose injection. Paired
metadata and synchronized scene/camera comparator pass with no failures.
Stage exactfraction0.9984665892454759, MAE0.019871516153216362;
fullframe exactfraction0.9898410248025034, MAE1.2005558013916016.
No reviewed pixel limits were added; verdict remains diagnostic-only.
Captures/debug/qualified metadata and durable comparison receipt are
output/playwright/mm-clean-oct3-*r16-dark-east30* (repository-root output,
not nw-core/output). Physics was the same private clean pair via route
fulfillment, JS fe1fb613…/WASM c2df1704…; maintained pair unchanged.
Renderer contract test also PASS. Temporary session marble-motion-oct3
and owned server8013 were closed/stopped. Next coverage includes release,
restart, terminal views, other viewport/DPR, and reviewed visual policy;
this is not completion of MM-005 or authorization to promote.

Fresh paired visual receipt: matching Retina 1824x1368 captures now pass
synchronized board/phase/marble/camera qualification. Stage exact-pixel
fraction0.9984423373808541, stageMAE0.04773044213652611; full-frame fraction
0.9896446502770083 and MAE1.2048602104187012. Camera maxdelta
5.6434717343734064e-8 within existing2e-6 scene bound. Result remains
diagnostic-only, NOT reviewer-approved pixel acceptance. Receipt:
`/private/tmp/nw-marble-clean-repro.25heUla5/fresh-rung16-dpr2-render-diagnostic.json`.
Fresh image/metadata quartet is under output/playwright/mm-clean-oct3-*;
use source-rung16-dpr2, not the earlier1x source capture. The1x/2x pair
correctly failed viewport qualification before a matching source capture.
Private Playwright session marble-clean-oct3 closed and owned server8013
stopped after capture; do not resume those as live processes. Next broaden
motion/theme/phase/DPR coverage and qualify shipping source recipe before
promotion; no other game work or production binary write occurred.

Fresh clean artifact qualification completed: all80-source-driver.log exited0;
strict original matrix replay all80-strict-source.log exited0 with cases80,
failed[], promoted:false. These verdicts apply to fresh JS fe1fb613… and
WASM c2df1704… (full identities below), not only the retained build.
Fresh multi-trial.log also exited0: three cases/seven real timeout trays,
history, next-board handoff, and cleanup qualified. Earlier statements below
that generation/replay remain pending are superseded by this receipt.
Browser visual qualification now uses isolated Playwright session
marble-clean-oct3 and local server8013; route fulfillment serves the fresh
private pair without modifying maintained vendor binaries. Initial browser
reload had two connection-reset module requests; reloading succeeded with
MuJoCo/WebGL2, rung16, elapsed0. Fresh native capture is retained at
output/playwright/mm-clean-oct3-source-rung16.{png,json}; fresh browser
paired capture and synchronized comparison remain pending. No visual
acceptance or shipping promotion is claimed.

Added isolated rebuild entry point
`scripts/build_marble_diagnostic_candidate.sh /absolute/new-output-directory`.
It checks corrected full-patch SHA, pinned upstream commit, qualified
Emscripten6.0.10, Release/single-thread configuration, and refuses existing
or relative destinations before any build/network work. It retains failed
build roots and exports logs/CMakeCache with the pair; no shipping manifest
or maintained binary write. Two portable builder contract methods pass
(invalid/missing/existing/extra arguments and shell syntax); gate includes
them. Full wrapper build was NOT rerun independently: only equivalent manual
clean build plus negative wrapper checks are qualified so far.

Example subsequent qualification (not an executed promotion):

```
env DEVELOPER_DIR=/Library/Developer/CommandLineTools EMSDK_PYTHON=/opt/homebrew/bin/python3 \
  bash nw-core/scripts/build_marble_diagnostic_candidate.sh /absolute/new-output-directory
env NW_MUJOCO_WASM_MODULE=/absolute/new-output-directory/mujoco.js \
  node nw-core/test/marble_trajectory_reference_diff.mjs
env NW_MUJOCO_WASM_MODULE=/absolute/new-output-directory/mujoco.js \
  bash nw-core/scripts/test_marble_source_play_matrix.sh
env NW_MUJOCO_WASM_MODULE=/absolute/new-output-directory/mujoco.js \
  node nw-core/test/marble_multi_trial_session_test.mjs
```

The new output parent must already exist; outputs are diagnostic only and
binary hashes can vary with embedded source paths. Full clean-artifact trace
generation is still live in `/private/tmp/nw-marble-clean-repro.25heUla5`;
resume it rather than launching a duplicate. Fresh strict source verdict
and original visual acceptance remain pending.

Fresh clean-build crafted suite PASS: 162 scenarios/17,263 per-frame states,
same maximum errors as qualified retained layer29+norm, receipt
`/private/tmp/nw-marble-clean-repro.25heUla5/crafted-trajectories.log`.
Binary section inspection confirms imports/types/function/export/table/
element sections agree, but globals/code/data/name/debug_info differ. This
is NOT merely custom debug metadata. Read-only WASM text inspection shows
embedded absolute source filenames differ between build roots; stack pointer
moves from90545264 to90545520 and data relocations change. This explains a
plausible relocation source, but does not certify all code differences as
benign or establish byte reproducibility. Disassemblies retained as fresh.wat
and retained.wat under the clean root. Fresh complete80 generation is now
running into that root's `all80-source-traces`, receipt
`all80-source-driver.log`; strict original replay remains pending. Do not
promote or borrow earlier binary acceptance. Production artifacts unchanged.

Clean build completed successfully. Fresh JS SHA-256
`fe1fb613b51cef42421ab59546cfacb1a3a343891687b86394fdc0e22bbb55d5`,
WASM SHA-256 `c2df1704b7d2f676a42d9b3779ae054378526cbaa78fd1d855131994d6871f33`.
These DIFFER from the qualified retained layer29 pair despite identical
patched source; do not assume debug metadata or reuse old acceptance for
the fresh artifact. Next compare section/toolchain/dependency identities
and run fresh compiled/local and original trajectories. Fresh crafted suite
is now running, root `/private/tmp/nw-marble-clean-repro.25heUla5`, receipt
`crafted-trajectories.log`. No production replacement occurred.

Retained synchronized flat visual comparator rerun in an isolated temporary
Pillow12.3.0/NumPy2.5.3 environment reports `diagnostic-only`, not acceptance.
Scene/camera synchronization passes; stage exact fraction0.9984423373808541,
stage MAE0.04773044213652611; whole-frame exact fraction0.9897055664563456,
MAE1.1934727430343628. Receipt `retained-flat-render-qualified-diagnostic.json`.
These are historical screenshot measurements, not current-runtime captures
or reviewer-approved pixel limits. Original app and system Python unchanged.
Only the fresh crafted suite remains live from this turn.

Clean-reproduction audit correction: previous complete-diff SHA
2ed74ba5... omitted seven untracked diagnostic headers and was NOT sufficient
for a fresh build. The same named complete patch now includes those headers;
its superseding SHA-256 is
`4e5ce41448539819438891ed187dc5e8fa7182ba77d7d5e8f9bb9dcff5574974`.
Do not use the old hash as the complete recovery artifact. New isolated root
`/private/tmp/nw-marble-clean-repro.25heUla5` contains a clean detached checkout
of the pinned upstream commit. Full corrected patch passes forward --check
against its pristine Git index and reverse --check against the reconstructed
working source. All20 engine source/header files and generated bindings.cc
are byte-identical to the qualified private candidate's inputs.

Clean Emscripten6.0.10 Release/single-thread CMake configuration completed with
separate fetched dependencies; build is now running, log
`/private/tmp/nw-marble-clean-repro.25heUla5/build.log`. Configure receipt
`configure.log`. No reused compiler objects or production artifact writes.
Build and subsequent fresh-artifact replay remain pending; source equality
does not prove binary identity or full clean-build acceptance. Retained old
pair and all matrix evidence remain intact.

COMPLETE current-combination matrix verdict PASS: all80 configured long-play
cases strictly match the original at unchanged field tolerances and contact/
result checks. Final aggregate `cases:80,failed:[]`; runner exits0. Receipt
`hypot-all80-strict-source.log`, trace directory `hypot-all80-source-traces`.
All processes from this sequence are terminal. This proves the specified
matrix, not universal arithmetic/visual parity or full plan completion.
`scripts/test_marble_source_play_matrix.sh` now runs this strict comparator
with contact-enabled state snapshots instead of --results-only, and retains
failure evidence. Shell syntax check passes; the wrapper itself was not
rerun independently (its generator/runner paths were exercised separately).

Saved COMPLETE private upstream diff as
`marble_layer29_complete_diagnostic_candidate.patch`, SHA-256
`2ed74ba531d9a7792ec1718c418e70172cc9dc66b649972831d3c866b005bb51`.
Reverse applicability against the current private tree passes. This includes
diagnostic instrumentation/bindings and all cumulative arithmetic layers;
it is not a clean shipping patch. Apply only to upstream base
13827e9ee56f097f57acf69ae52b078f9839682d, not earlier cumulative patches.
Build qualification uses Emscripten6.0.10, CMake Release, single-thread WASM,
and the retained build configuration. Fresh clean-tree reproduction and
diagnostic-neutral stripping, original visual/UI acceptance, remaining
branch/helper coverage, and production artifact/manifest integration are
still required. Do not copy this diagnostic artifact over production merely
because the matrix passes. Maintained adapter is corrected; maintained
core/MuJoCo binary artifacts remain unchanged.

Current-combination generation completes PASS for80 cases (7 wins,41 physical
losses,32 timeouts); receipt `hypot-all80-source-driver.log`. Strict original
matrix replay is now live through `marble_source_matrix_replay.py`, log
`hypot-all80-strict-source.log`; verdict pending. Runner now requires complete
unique absolute adapter identities with valid SHA-256 strings, in addition
to uniform provenance and full matrix/state/contact checks; six acceptance
tests pass. Older traces lacking adapter identities cannot certify the new
combination through this runner.

`marble_multi_trial_session_test.mjs` now supports explicit private runtime
selection using NW_MUJOCO_WASM_MODULE. It passes with layer29 plus the corrected
adapter:3 multi-trial/adaptive cases,7 real timeout trays,result history,
next-board handoff,and cleanup. Receipt `hypot-multi-trial.log`. This tests
host/controller lifecycle, not original per-frame parity of each trial or
paired visual acceptance. Matrix source replay remains the only live process
from this turn. No production physics promotion.

Fresh layer29-plus-compensated-norm crafted suite PASS:
162 scenarios/17,263 per-frame states at unchanged field tolerances, receipt
`hypot-crafted-trajectories.log`. Added portable `python_hypot_test.mjs` to
gate.sh: known failing norm bits, signed zero, subnormal scale boundaries,
overflow, infinity/NaN precedence pass; gate shell syntax passes. These are
not substitutes for full long-play or paired visual acceptance. Full trace
generation remains live; resume exact handle/state rather than restarting.

Wrapper hypot correction implemented in `shells/web/python-hypot.js`, using
power-of-two scaling, split-product compensation, compensated accumulation,
and square-root correction. The MuJoCo adapter's two-coordinate norm now
uses it; renderer and analytic fallback remain untouched. Original Python
qualification `python_hypot_original_diff.mjs` PASS: 20,224 complete-bit
comparisons, including the failing speed-cap operands, deterministic varied
normal exponents, subnormal boundaries, maximum magnitudes, signed zeros;
NaN/infinity precedence asserted separately. This is sampled qualification,
not universal proof. Maintained MuJoCo/core binary files remain unchanged,
but the maintained JS adapter HAS changed (do not call all production code
unchanged). MuJoCo backend contacts/holes/all16-board test passes.

With private layer29 plus this adapter correction, seed1 strict uninterrupted
7,601-event source replay PASSES with zero reported deltas in all compared
fields, including struck; receipts `hypot-seed1-trace.json`,
`hypot-seed1-original.log`. Earlier 79/80 layer28 result cannot certify this
new combination. Added adapter-file SHA identities (MuJoCo adapter, game
module, norm helper) to generated trace provenance. Fresh complete generation
is running into `hypot-all80-source-traces`, log `hypot-all80-source-driver.log`.
Next strictly replay all80, rerun crafted/lifecycle suites, and finish original
visual acceptance before production physics promotion. No accepted full-matrix
verdict for this combination exists yet.

Layer-29 fresh unsynchronized localization (`pi4-next-trace.json`,
`pi4-next-unsynced.log`) confirms event69/substep3/implicit qpos/qvel now agree;
only a solver statistic differs. At event70/checkPos qvel differs, but qpos
does not yet differ. The remaining producer is the Python-vs-JS wrapper speed
cap AFTER implicit, not a remaining integration output at that boundary.
Recorded raw velocity [-5.281384333465093,-4.398885466589486] times
keep=1-0.22/240 yields [-5.27654306449275,-4.394853154911779]. Actual Python
math.hypot is `0x1.b77e104adbcaep+2`; actual Node Math.hypot is one ULP lower.
The reciprocal scale reproduces both differing velocity components exactly.
Added `marble_speed_cap_hypot_test.py` and portable gate coverage for this
local original boundary; it is not a complete replacement implementation.

Consulted primary CPython v3.13.12 Modules/mathmodule.c, vector_norm lines
2365–2412 and dl_mul/dl_fast_sum: power-of-two scaling, compensated squared
products/sums, square-root differential correction, rescaling. Source:
https://raw.githubusercontent.com/python/cpython/v3.13.12/Modules/mathmodule.c
Next implement and qualify that two-coordinate operation for the JS adapter,
including subnormal/overflow/NaN/infinity handling and varied exact original
bits. Do not substitute plain sqrt(x*x+y*y) or fix this one input specially.
Then rerun seed1 and the entire original trajectory matrix. No production
physics artifact was replaced; layer29 remains rejected for full replay.

Layer 29: pinned combined sincos entry loads its unreduced threshold from
entry-736, bits `0x1.921fb54442d18p-1` (rounded pi/4), then branches on <=.
The prior 0.5 limit was conservative, not the actual dispatch threshold.
Added SHA guard for the 16-byte threshold region
`c5ebbec1d24f658b078269886bb3938f337dcdf307fc062fb83d87d5c7fb64d3`.
Expanded model qualification to that observed branch: 12,158 full platform
pairs match exactly, including both signed boundaries/inward neighbors,
signed subnormals, deterministic uniform samples, and seed-1 failing angle.
Five portable model tests pass. Larger inputs remain rejected by the model;
range reduction is not implemented. Read-only entry inspection also identifies
the moderate-range reduction constants, but they are not qualified here.

Private integration now uses the polynomial through that observed pi/4
threshold. Cumulative spatial patch
`marble_pi4_trig_spatial_cumulative_candidate.patch`; retained pair
`retained-pi4-trig-candidate-dist`, WASM SHA-256
`beb0f59890d8bc819bf2f58b21b8e1bc4a7e83bdb78d19653c2d7a88595c2d76`.
Fresh compiled helper receipt `pi4-quaternion-compiled.json` removes the sole
captured integration mismatch (all 72 captured integrations match), but 56
synthetic integrations still differ. Ordinary 7,601-event seed-1 strict replay
STILL FAILS, with 3,803 over-tolerance values; receipts `pi4-seed1-trace.json`
and `pi4-seed1-original.log`. Do not infer full parity from the isolated fix.
Next localize the new earliest unsynchronized split using fresh layer-29
inputs, then qualify the remaining producer (including range reduction if
exercised). Production unchanged; no layer-29 promotion. All current
processes completed.

Failing seed-1 localization completed: coarse/middle/exact traces and matching
unsynchronized receipts (`seed1-{coarse,middle,exact}-trace.json` and
`seed1-{coarse,middle,exact}-unsynced.log`) identify event 69/substep 3/implicit
as the first selected position split; before it qpos/qvel agree. The first
step-1-visible split is event 70/checkPos, but the preceding step-2 implicit
output already differs. Solver statistics have a separate tiny difference;
do not confuse that statistic with the isolated position output. The coarse
recorder was explicitly verified neutral against the complete retained
16-1 trace: all 7,601 input schedules and non-engine public state snapshots
are identical.

Fresh actual-original quaternion qualification (`seed1-quaternion-original.json`
and `seed1-quaternion-compiled.json`) contains 1,072 rows and exactly one
captured integration mismatch. It is event69/step3/joint2, half-angle
0.6849294978512117, OUTSIDE the qualified abs(x)<=0.5 branch. Thus the bounded
candidate correctly falls back to the unqualified generic trig path, and
that known range gap is now exercised by real gameplay, not merely synthetic
stress. No tolerance or domain limit was widened. Next inspect and qualify
the original combined sincos dispatch/range reduction for this interval,
including exact complete original integration outputs and varied boundary
operands, before a new private build. All current diagnostic processes are
terminal. Production remains unchanged and layer 28 remains rejected.

COMPLETE layer-28 strict source matrix verdict: FAIL, 79/80 cases pass.
The sole failing case is rung 16/run seed 1, board seed 288545018; retained
trace `impedance-all80-source-traces/16-1.json`, aggregate receipt
`impedance-all80-strict-source.log`. Full matrix runner completed with exit 1
and final `failed: [[16,1]]`; no source replay remains running. First numeric
tolerance exceedance is event 3798/marble 1/value 7 (qx), delta
1.0122044036275923e-8 against 1e-8. Maximum qx delta is
1.317347698981397e-8; contact-set failure is not reported. Do not widen the
tolerance or promote a 79/80 result. Next generate current-input unsynchronized
phase captures for rung 16/run seed 1 and locate the earliest divergence,
which may be much earlier than the tolerance crossing. The original single
hard seed passes, but is no longer sufficient acceptance evidence.
Separately rechecked the options/controller matrix (1,344 combinations,
invalid rejection, persistent RNG reset) and renderer contracts; both PASS
on unchanged production core/renderer, not a paired visual acceptance claim.

Full source-matrix generation finished: `impedance-all80-source-driver.log`
reports PASS for 80 cases (7 wins, 41 physical losses, 32 timeouts). All 80
state-bearing contact-enabled traces are retained in
`impedance-all80-source-traces`. Strict source replay is now running using
the original venv interpreter through `marble_source_matrix_replay.py`, log
`impedance-all80-strict-source.log`. The runner additionally requires an
explicit completed-replay PASS audit, not merely exit zero; four fail-closed
acceptance tests pass and are included in gate.sh. The matrix source verdict
is still pending; do not infer acceptance from completed trace generation.

Complete long-source matrix preparation: fixed directory trace mode in
`marble_generated_play_session_test.mjs` to include per-event state snapshots
for both frame and level events. Previously only single-file trace mode
included these required source-comparison operands. A rung-1/seed-17 directory
smoke matches all 640 events of its previously retained single-file trace
exactly and passes strict source replay. Receipts `directory-mode-smoke.log`,
`directory-mode-source.log`, and `impedance-full-source-matrix/1-17.json`.
Added `marble_source_matrix_replay.py`, which requires all 16 rungs times five
configured seeds, contact diagnostics, complete event snapshots, unique
filename/case identities, and uniform runtime provenance before strictly
replaying every case. It rejects the partial smoke directory as intended;
no incomplete matrix can produce a success report. Full generation is now
running into fresh `impedance-all80-source-traces`, log
`impedance-all80-source-driver.log`. Once generation completes, run using the
actual original venv Python, with that directory and `--source-root` pointing
to the original project. This new matrix is not yet accepted or promoted.

Layer-28 existing crafted/native trajectory suite also PASSES:
`marble_trajectory_reference_diff.mjs` compares 162 scenarios and 17,263
per-frame states against the original Python/native runtime. Receipt
`impedance-trajectory-reference.log`. Maximum errors are below the suite's
unchanged field-specific tolerances (largest angular-velocity difference
6.743050562363351e-12; largest quaternion difference 2.2460644455435386e-12).
This is tolerance-based trajectory coverage, not bitwise proof, visual
acceptance, universal helper qualification, or complete long generated
held-play source replay. Native runtime and private WASM identity must remain
pinned in subsequent qualification. No production replacement has occurred.

Layer-28 generated gameplay matrix completed successfully: 80 cases across
all configured rungs/seeds, 7 wins, 41 physical losses, and 32 timeouts;
controller result history and cleanup assertions pass. Receipt
`impedance-generated-matrix.log`. This matrix alone does not compare each
trajectory with the original. A fourth strict original trajectory now passes:
rung 3/run seed 17, board seed 889418965, 527 events, physical win/home 1.
All reported marble-state deltas are zero; struck maximum difference is
2.7755575615628914e-17. Receipts `impedance-win-3-17.json` and
`impedance-win-3-original.log`. Remaining required work includes source parity
across the complete generated matrix and the broader crafted trajectory,
input-lifecycle, visual, and branch/helper qualification suites.

Layer-28 broader strict source checks now also PASS: rung 1/run seed 17,
board seed 889418965, 640 events, physical win/home 1; and rung 3/run seed 0,
board seed 827307999, 118 events, physical loss/lost 1. Both have zero reported
numeric deltas for every compared field and no contact-set mismatch. Fresh
receipts under the owned private root are `impedance-win-1-17.json`,
`impedance-win-original.log`, `impedance-loss-3-0.json`, and
`impedance-loss-original.log`; their generated drivers also pass controller
result-history and resource-cleanup assertions. Together with the rung-16
timeout these establish three ordinary trajectories across win/loss/timeout,
not the complete rung/seed or lifecycle acceptance matrix. The broader
generated matrix is a separate check, not source parity evidence. Continue
expanding strict source replay before any production promotion.

Layer 28 breakthrough: private getimpedance final scaling now uses explicit
wheel FMA under Emscripten, preserving native behavior. Retained WASM
`retained-impedance-candidate-dist/mujoco.wasm` has SHA-256
`0f08066510b5851e0c7dea261572f71259dbb0d302f93fe9b1637b85dec0b6b5`.
The cumulative constraint patch is
`marble_impedance_constraint_cumulative_candidate.patch` (reverse check
passes against the private tree; apply to pinned upstream base, not earlier
cumulative constraint patches). Verified actual original owned model geoms
0 and 57 both have solimp [0.9,0.95,0.001,0.5,2].

Fresh ordinary full replay `impedance-hard-trace.json` PASSES 7,601 events on
rung 16, run seed 0, board seed 827307999. All reported marble values, tilt,
elapsed, and nudgeDue have zero numeric delta. `struck` maximum delta is
2.7755575615628914e-17. No contact-set mismatch is reported. Both ordinary
continued-contact diagnostic replay and strict replay without that option
completed successfully (`impedance-original-replay.log` and
`impedance-strict-replay.log`). This proves tolerance-based acceptance for
this one trajectory, not full bitwise identity or the whole acceptance
matrix. Unsynchronized selected live phases events 1125–1130 show no
differences (`impedance-unsynced.log`); copied diagnostic probe differences
remain separate. Production core and maintained MuJoCo hashes unchanged.

Next: broader original-versus-private full trajectory matrix, including
physical wins/losses, all configured rung/seed cases, varied time steps,
input lifecycle, and unsupported-angle behavior. Do not promote on this
single timeout trajectory; the 60 synthetic quaternion differences and
unqualified upper-impedance/range-reduction branches remain outstanding.

Event-1127 impedance localization: original `_mj_makeImpedance` at 0x42ef8
inlines getimpedance. Instruction 0x43590 is `fmadd d0,d10,d2,d13`, following
`d2 = maximum-minimum`: the final scale is fused. For recorded contact 1,
position -0.00035537936711282306, margin 0, default solimp
[0.9,0.95,0.001,0.5,2], x=0.35537936711282303 and
y=0.2525889891390213. Separately rounded scaling yields browser impedance
0.9126294494569511; fused scaling yields the recorded original value
0.912629449456951. Added a local expression regression to the portable gate.
This does not yet qualify the complete original makeImpedance routine or
all solimp branches: verify actual contact parameters, varied complete
outputs, and fresh full replay before promoting any candidate. Upper-branch
`1-b*power(...)` also contains a fused original instruction and needs its
own operand/order qualification; do not assume the single scale fix covers
that branch or the independent diagA difference.

Next-divergence localization on layer 27: fresh unsynchronized phase sweeps
(`small-trig-next-trace.json`, `small-trig-middle-trace.json`, then
`small-trig-exact-trace.json`, each with matching `*-unsynced.log`) narrow the
first selected live phase difference to event 1127/substep 3/fwdPosition.
The preceding selected comPos phase agrees. The differing arrays are
efc_AR, efc_D, efc_KBIP, efc_R, and efc_diagA; no qpos, qvel, contact frame,
or Jacobian difference is reported at that boundary. First KBIP difference
is index 26: original 0.912629449456951 versus WASM 0.9126294494569511.
First diagA difference is index 9: original 725492.6180827137 versus WASM
725492.6180827138. This points next toward constraint construction/reference
parameter arithmetic, but does not yet identify the responsible expression.
Capture the exact original and browser read sets for the affected contact,
then separate diagonal approximation, impedance, regularization, and
projection stages before making another arithmetic patch. The copied
post-constraint-zeroacc diagnostic probe has an earlier tiny cfrc difference;
it is not the first live-state failure and must not be silently conflated
with this boundary. All these processes completed; no background replay is
left running. Plan version 3.17 now links the latest candidate evidence rather
than presenting the older 3.16 recovery result as current.

Private layer 27 implemented the bounded paired polynomial only inside
`mju_quatIntegrate`; native and public generic axis-angle paths are unchanged.
The separately retained artifact lives at
`/private/tmp/nw-marble-costchange.7SuZEZYO/retained-small-trig-candidate-dist`.
Its WASM SHA-256 is
`3ccd85e28ddd6ec3ff6b95b3b0eaeee06faa83a3d356c21670dbae230644fc99`.
The cumulative spatial patch is
`marble_small_trig_spatial_cumulative_candidate.patch`; reverse applicability
against the current private tree passes. Apply this cumulative patch to the
pinned upstream base, not on top of the earlier cumulative spatial patches.

Compiled helper replay on `event565-trig-original.json` checks 1,048 cases:
all captured integrations match exactly, but 60 total synthetic integrations
still differ. The full 7,601-event ordinary replay still FAILS: first numeric
tolerance exceedance event 1333/marble 1/value 6, delta
1.0210641443464397e-8 against 1e-8; 45,698 numeric exceedances and 167 contact
set mismatches (events 1542–4835). Receipts are `small-trig-hard-trace.json`,
`small-trig-original-replay.log`, `small-trig-compiled.json`, and the bounded
unsynchronized diagnostic `small-trig-unsynced.log` under that private root.
This candidate is rejected for production promotion. All four production
artifact hashes remain unchanged. The next localization must use fresh
unsynchronized phase captures between the corrected event-565 boundary and
the new first tolerance failure; do not treat the later failure as proof of
identity before it. The portable model contract tests now run in `gate.sh`;
the pinned macOS qualification is deliberately a separate platform-specific
command, not a portable gate requirement.

`marble_small_sincos_qualification.py` now verifies the macOS arm64 combined
ABI entry, both coefficient tables, and the inspected small sine/cosine kernel
regions against pinned SHA-256 identities before comparing outputs. On the
current macOS 27.0 arm64 runtime, all 12,157 input pairs match both returned
binary64 outputs exactly. Coverage includes deterministic seed-565 uniform
samples, signed zero, both domain boundaries and their inward neighbors,
signed powers of two down to the smallest subnormal, and the event-565 input
0.019710379478423627. Both model functions reject nonfinite inputs and the
first representable values outside [-0.5, 0.5]. Four portable model contract
tests pass, including the original failing sine bits `3f942e9f87ba42fc`.

Reproduce with Homebrew Python supporting `math.fma`:

```
/opt/homebrew/bin/python3 nw-core/test/marble_small_sincos_model_test.py
/opt/homebrew/bin/python3 nw-core/test/marble_small_sincos_qualification.py
```

This is sampled local qualification, not a universal arithmetic proof or game
acceptance. The domain is deliberately bounded, not a claim about the actual
platform dispatch threshold. No WASM arithmetic was changed in this step.
Next: implement the paired polynomial only in a private integration candidate,
retain a separately identified artifact, then rerun complete original-input
integration checks and ordinary unsynchronized full gameplay replay. Larger
angles/range reduction remain unqualified. Layer 26 still fails full parity;
production must not be replaced on the strength of this local result.

This is diagnostic progress following implementation-plan 3.16, not physics
acceptance or a promoted runtime. All seventeen private recovery layers remain
rejected for whole-game parity. Production arithmetic is unchanged.

The opt-in `NW_MARBLE_PLAY_TRACE_INTEGRATOR=1` recorder captures model topology,
sparse mass/derivative layouts, damping, options, time, integration input arrays,
and post-implicit output arrays. Floating operands also carry big-endian IEEE
binary64 hex strings so negative zero survives JSON transport. It records only
the named `checkAcc` and `implicit` phases. Recording does not copy native state
or qualify native outputs by itself.

Retained replay:
`/private/tmp/nw-marble-costchange.7SuZEZYO/comvel-family-integrator-readset-v2-trace.json`
and adjacent `.log`. It used the unchanged layer-17 private pair and board 16:0,
with diagnostic events 0, 1, 17, 18, 216; contacts, split-step, phase, and Newton
recording enabled. The full generated session passed (timeout, not a win).
`marble_trace_neutrality.py --require-provenance` compared it against
`comvel-family-candidate-hard-trace.json`: all existing event and physical
snapshots exactly equal. The thirteen neutrality unit tests also passed.

Correction: the first unversioned replay had its hook in step 1 and produced
no integration packets. Its neutrality result alone was insufficient. The v2
hook is in step 2; an independent content check confirmed forty packets
(twenty checkAcc/implicit pairs), with nq21/nv18/nD108/nC18 and integrator3.
V2 independently passed full replay neutrality. Do not use the first replay as
integration evidence. Five new dependency-light guard tests pass for unique
named ownership, malformed/duplicate/missing owners, signed zero, invalid bits,
nonfinite operands and numeric/bit disagreement. All six legacy positional
checkAcc accesses in the source diagnostic now use the named-owner helper;
the old partial-state synchronization remains explicitly unqualified.

Next work, before any arithmetic edit:

Actual-original enclosing-call result: `marble_integrator_original.py` validates
every selected packet before calls, verifies original public `mj_implicit`
image/address, compares all model dimensions/integer layouts against an owned
original model, copies floating inputs with exact-bit assertions, and rejects
nonfinite outputs or mutated read-only operands. Twenty calls completed using
original wheel 9e772461... on v2 inputs. Fifteen boundaries have 54 bitwise
differences, restricted to qpos/qvel. Time, qacc_warmstart, qDeriv, qH and
qHDiagInv agree. Earliest difference is event1/substep1. This localizes the
next investigation to the integration/advance path, not a production fix.
Report `/private/tmp/nw-marble-costchange.7SuZEZYO/integrator-original-v2-comparison.json`
SHA4cabbd67c9b7d0b62d27524ee52a282d64c85f31e99b7757219add5fac5a3263;
input trace SHA808dc675d7cf7ba1d59eb45803344a4b42be45ccd955eec93e4078311d11fd8e.
Compact durable differences are in
`nw-core/test/fixtures/marble_integrator_original_differences.json`.
Eight guard tests pass. No SDK-private LU original identity is claimed.

Further localization: guarded actual-original public `mj_integratePos`
(offset0x10970c in the same original image) was called on copied pre-call
qpos and the exact captured browser post-call qvel. All twenty calls completed;
thirteen boundaries have 26 bitwise differences. Every difference is a
quaternion component (index modulo7 >=3); all nine translation coordinates
agree at every boundary. This excludes differing velocity as the explanation
for these particular quaternion discrepancies, but does not yet distinguish
norm/trigonometry/quaternion multiply ordering. The enclosing implicit result
remains15/54. Velocity differences require separate free-body solve/advance
localization. Next compare complete original quaternion-integration operands
and returns before proposing a narrow private arithmetic patch.
Full v3 report: `/private/tmp/nw-marble-costchange.7SuZEZYO/integrator-original-position-v3-comparison.json`
SHAe3c417a01b99d0d68d1aeab6554ebd82bb2fb35a5bd7abcf2d9bd7bcac9a3372.
Eight guard tests still pass; production binaries are untouched.

Quaternion sub-check: `marble_quaternion_original.py` calls actual original
public normalize3, normalize4, axisAngle2Quat and mulQuat on independent owned
buffers, and qualifies their composition against complete original public
quatIntegrate. A scalar multiplication ordering derived from original ARM64
mju_mulQuat disassembly agrees bitwise with the original multiply and complete
composition for all60 captured quaternion operands and1000 seeded finite
synthetic cases. The60 captured complete original quaternion returns reproduce
the26 browser component differences. This is NOT evidence that multiplication
alone causes them: normalization/trig inputs came from original public helper
calls, not captured browser helper outputs. Next obtain compiled browser helper
outputs on these same operands; qualify each complete helper before choosing
the narrowest private arithmetic correction. No production patch yet.
Retained report: `/private/tmp/nw-marble-costchange.7SuZEZYO/quaternion-original-composition.json`.

Compiled-helper localization now runs all1060 cases through the existing public
layer17 bindings using native-WASM-owned output storage. Captured60 cases:
normalize3/normalize4/axisAngle all0 differing calls; multiplication22 differing
calls; complete quaternion integration22 differing calls. Thus multiplication
is the evidenced arithmetic correction for this captured gameplay set. Across
all1060, differing calls are integrate915/normalize3=104/normalize4=118/
axisAngle64/multiply881: broader helpers remain separate unresolved synthetic
coverage, not a reason to assert a universal multiplication-only fix.
Durable report `nw-core/test/fixtures/marble_quaternion_helper_localization.json`
records the exact17 JS/WASM hashes and first discrepancies. Original helper
golden is `quaternion-original-helper-v2-golden.json`; compiled output is
`quaternion-compiled-helper-v2-comparison.json` under the retained root.
Next create a private Emscripten-only integration-local quaternion multiply
candidate using the qualified original FMA ordering. Preserve native/global
callers, qualify complete compiled helper and enclosing integration returns,
then rerun ordinary numeric/contact replay. Do not promote on helper parity.

Private layer18 candidate is now built and retained in
`retained-quaternion-integration-candidate-dist` under the owned root. Its
durable patch `marble_quaternion_integration_candidate.patch` reverse-checks
against the private source. It changes only Emscripten quatIntegrate's multiply
to the already-qualified wheel FMA ordering; generic mulQuat/native code stays
unchanged. Compiled complete quaternion integration now agrees on all60
captured cases (previously22 differing calls). Across1060 cases it has272
remaining differences (previously915), attributable scope not yet qualified.
Other helper mismatch counts remain unchanged. The build is terminal success;
no whole-game replay or enclosing integrator candidate qualification yet.
Next run the ordinary layer18 replay with integration recording, actual-original
enclosing comparison and independent full numeric/contact gates. Candidate
report `quaternion-integration-candidate-helper-comparison.json` is retained.
Production artifacts remain untouched; layer18 is NOT promoted or accepted.

Layer18 ordinary and enclosing qualification are now terminal. Current trace
`quaternion-integration-candidate-hard-trace.json` completed7601 events, timeout
120.016667s/home0/lost0. Actual original enclosing integration on20 current
boundaries has11 differing boundaries/28 values, ALL qvel; every qpos/time/
qacc_warmstart/qDeriv/qH/qHDiagInv value agrees. Separate original position
calls on current browser velocities have0 differences. Report SHA
10f5a31376009a29d5ea323e1af147d1df6ab673189dc5c0e11083ed1fd388c4.
Pair WASM SHA5a44fe506d8585743e30f4e6212da8c14095a8d9b04d1d0a920f5802be81dba7;
JS remainsc477b87e... . Ordinary strict replay FAIL at contact event520.
Full numeric/contact replay FAIL:95411 numeric exceedances,122 contact-set
mismatches events520–1966; first numeric event329/marble0/value8 delta
1.0087108537337741e-8 versus tolerance1e-8. This improves first numeric onset
versus17(event195), but does not establish whole-game correctness. Layer18
whole-game verdict REJECTED, retain it only for next localization. Full and
strict logs have prefixes `quaternion-integration-candidate-original-`.
Next localize the28 velocity differences on current18 identical operands:
qualify actual original free-body solve versus velocity axpy/advance before
changing either. Existing derivative/factor outputs agreeing does not prove
local unsymmetric solve qacc agrees; local qacc is not stored in data.qacc.
Eight guard tests are now included in gate.sh. Production remains unchanged.

Velocity localization: actual-original public mjd_freeMhat/factorLU6/solveLU6
symbol offsets0x66f80/0x11ecec/0x11ef2c are image/address guarded. After the
original enclosing call assigns qDeriv, restoring pre-call qvel and independently
calling these public routines plus exact FMA advancement reproduces enclosing
qvel bits at ALL20 boundaries. Report
`quaternion-integration-original-local-solve.json` retains all54 local qacc bits
per boundary; this is qualified public-call composition, not private-intermediate
capture. Compiled layer18 free-solve recorder replay also completed and retained
`quaternion-integration-free-solve-trace.json`/`.log`. All20 checkAcc read-set
packets match the prior18 trace exactly. Its252-value free-solve packets contain
28 local qacc differences, on the exact same11 boundaries and indices3/9/15
(first rotational acceleration per marble) as enclosing qvel differences.
This identifies local solve as the next path, not velocity axpy alone. NEXT
retain original matrix/LU/pivot/rhs results and compare complete compiled probe
stages on current18 operands before proposing a private local-solve correction.
No recorder-wide physics-neutrality claim beyond the verified complete read-set
packets yet; add independent full neutrality coverage for probe-only fields.
Eight guard tests pass; both new jobs terminal; production unchanged.

Complete-stage comparison now identifies the first producer:240 matrix values,
240 LU values,0 pivots and28 solutions differ over20 boundaries/60 free solves.
Matrix discrepancies occur at rotational off-diagonal indices22/23/27/29/33/34;
do not infer a factorization bug from LU inheriting a different input matrix.
Original matrix/LU/pivot/rhs/solution bits are retained in
`quaternion-integration-original-local-stages.json`; complete comparison is
`local-solve-stage-comparison.json`. The dependency-light reproducible comparator
is `marble_local_solve_compare.py`; compact durable counts/first values and input
identities are in `fixtures/marble_local_solve_stage_differences.json`.
NEXT qualify the enclosing original mjd_freeMhat matrix construction and its
freeBias_vel_blocks rotation products/gyroscopic derivative on identical current
operands. Inspect original machine ordering before arithmetic changes. The
private SDK probe is not original private-intermediate evidence. Eight guards
pass; no candidate promotion or production change.

Actual public-bias follow-up: original `mjd_freeBias_vel` at0x669f8 now has
the same image/address guard and complete36-value outputs retained for all60
owned free-body calls. Enclosing original velocity composition still qualifies.
Report `quaternion-integration-original-bias-stages.json` includes biasBits
alongside full matrix/LU/pivot/rhs/solution bits. The current compiled300-value
intermediate packet (three100-value bodies) has360 differing final rotational
bias values against the complete actual original public return, before matrix
assembly. This is evidence that freeBias_vel_blocks arithmetic already differs,
not just assembly or LU. Browser intermediate values remain diagnostic-only;
the actual original public final B output is the qualification authority.
Original machine inspection shows fused triple products/cross expressions in
freeBias_vel_blocks. NEXT reconstruct the complete final bias using exact
machine operation order; check it against ALL60 original B outputs, then varied
finite synthetic inputs before modifying a private candidate. Do not assume a
generic blanket FMA conversion reproduces original cancellation order.
Eight guard tests pass; original-bias job terminal; production unchanged.

Complete bias reconstruction is now qualified for current captured operands:
`marble_free_bias_model.py` uses local fused dot/cross/3x3 products, the explicit
world inertia, K/C construction and rotated final B. ALL60 complete36-value
returns agree bitwise with actual original public mjd_freeBias_vel;0 differing
calls/values. This is reconstructed arithmetic independently checked against
original final returns, not original private intermediate capture. Report
`free-bias-fused-model-comparison.json` retained. Three dependency-light model
tests pass, including a cancellation where fused and rounded products differ.
Input/reference identities are guarded. NEXT qualify varied finite synthetic
operands against the actual original public call, then implement a PRIVATE
freeBias-local Emscripten ordering candidate preserving generic/global/native
helpers. Run complete matrix/solve/enclosing integration and ordinary replay
checks before promotion. Production untouched; no new arithmetic candidate yet.

Broader original bias qualification: `marble_free_bias_synthetic.py` performs
1000 seeded finite cases/3000 public original calls on three owned free bodies.
It varies velocity, independent finite positions/CoM offsets, positive masses
and anisotropic inertia over multiple powers of two, retaining current captured
rotation matrices. Complete fused reconstruction agrees on all3000 returns:
0 differing calls/values. These are finite operand stress cases, not claims of
physical trajectory validity. Original routine image/address and native-owned
library are guarded; every operand copy is bit-checked. First report retained
as `free-bias-synthetic-comparison.json`; copy-assertion rerun is
`free-bias-synthetic-v2-comparison.json`. NEXT implement the private bias-local
ordering correction; qualify complete compiled bias, local matrices/solves and
enclosing current-input integration, then independent ordinary numeric/contact
replay. Three model tests now included in gate.sh. No promotion yet.

Private layer19 bias-local candidate is now built, retained and tested. The
Emscripten-only freeBias_vel_blocks branch uses local dot/cross/matrix helpers
and the qualified wheel FMA implementation; native/generic math stays unchanged.
The cumulative derivative-file patch is
`marble_bias_local_cumulative_derivative.patch`: it includes pre-existing trace
instrumentation and applies to the ORIGINAL pinned derivative file, NOT as an
incremental layer19 patch on already instrumented sources. Reverse-check against
current private source PASS. Retained pair `retained-bias-local-candidate-dist`
WASM SHA424fbb2155b00e56db4f12d4a62ede7898da165566f5b112b10d9e793c00cdbd.
Current7601-event trace `bias-local-candidate-hard-trace.json` completed timeout
120.016667/home0/lost0. Actual original enclosing integration matches ALL20
boundaries:0 different values/calls, including position-only checks. Complete
original matrix/LU/pivot/solution comparison also ALL0. Reports:
`bias-local-candidate-original-integration.json`,
`bias-local-candidate-stage-comparison.json`. Full ordinary replay still FAILS:
103250 numeric exceedances/110 contact mismatches events520–1966; first numeric
event315/marble0/value10 delta3.478482195617971e-7 versus1e-7.
Layer19 whole-game verdict REJECTED; no promotion. No claim that all synthetic
compiled bias cases or earlier solver regression matrices have been rerun yet.
NEXT qualify current19 whole forward/constraint outputs on identical inputs,
then localize the earliest remaining producer. Do not keep patching integration
from stale18 discrepancies: current19 complete integrator returns agree. Retain
all failed ordinary logs; production artifacts unchanged. All build/replay/
original comparison jobs terminal; three model unit tests PASS.

Fresh19 whole-constraint qualification: all20 instrumented native final returns
qualify against actual original wheel copies. Browser final non-statistic fields
ALL agree;19/20 complete nonzero outputs agree, one solver_stats value differs.
Durable `fixtures/marble_bias_local_whole_solver.json` retains all21 fields,
runtime/input/library identities and the statistic difference. The whole receipt
generator now supports bias-local/quaternion prefixes without altering previous
prefix semantics. Fresh19 actual-original complete comVel also ALL20 agree.
Exploratory current-input step1 phase localization completed throughE216 and
is retained in `bias-local-candidate-current-phase-localization.log`. First
ordinary forward producer field after the separate post-constraint RNE probe
is efc_aref atE1/substep0/probe_referenceConstraint. It propagates through
fwdVelocity/sensorVel. This uses historical step1 synchronization and is NOT
strict full read-set qualification or an arithmetic-patch authorization.
NEXT inspect reference-constraint computation and qualify its complete actual
original public outputs on a strict copied model/data read-set. Preserve the
post-constraint RNE probe differences separately; do not silently drop them.
Do not recycle stale Sept25 Jacobian or derivative candidates. Whole-game19
remains REJECTED, production unchanged; all new qualification jobs terminal.

Reference arithmetic inspection: original mj_referenceConstraint0x49bc8 has
SIMD/scalar aref loops that round (-K*I)*(pos-margin), then fuse subtraction
of B*vel. E1/substep0 current operands reproduce the observed original value
2.1239362617724917 versus compiled2.123936261772492. Dependency-light
`marble_reference_arithmetic.py` records that exact core ordering and two unit
tests pass. This ONE observed row is NOT complete public-call qualification:
Jacobian velocity/surface velocity/adhesion/equality branches must be guarded
and complete finite copied inputs verified before calling actual original
referenceConstraint. NEXT build that strict current-input public-call oracle,
qualify all selected outputs and synthetic coefficients, then consider a
private aref-core correction. No runtime arithmetic change made this turn.

Actual-original reference public-call oracle now completes all20 selected
boundaries using original-owned data, dense Jacobian/coefficient/position/
margin/velocity copies, guarded original routine0x49bc8, no equality/friction
rows, surface velocity, adhesion, plugins or sleep branch. Owned original
forward allocates matching rows before bounded shape/copy checks. Original
efc_vel agrees throughout;4 nonzero efc_aref values differ from browser.
The initial reconstruction exposed93 signed-zero disagreements; preserve this
failed evidence in v2. Correct FMSUB semantics is -fma(B,vel,-spring), not
fma(-B,vel,spring). V3 complete original output reconstruction now has0 bit
differences on all20 calls, including signed zero. Three arithmetic unit tests
pass. Reports `reference-original-current-v2-comparison.json` and v3 retained.
Captured browser JSON zero signs remain unqualified. NEXT strengthen owned
model/contact/input immutability checks and synthetic coefficient qualification
before a private aref candidate; no production runtime arithmetic change yet.

Reference layer20 progress: read-only operand immutability and1000 seeded
synthetic actual-original calls (varied coefficients/Jacobian/qvel/positions/
margins, signed-zero velocity cases) now pass complete arithmetic qualification.
Private Emscripten aref loop uses original negated-FMA semantics; native path
and other reference branches unchanged. Durable incremental patch
`marble_reference_acceleration_candidate.patch` reverse-check PASS. Build and
7601-event generated trace terminal success. Retained pair
`retained-reference-candidate-dist`, trace `reference-candidate-hard-trace.json`.
Fresh actual-original reference comparison ALL20 complete efc_vel/efc_aref
outputs agree numerically; arithmetic model bitwise agreement also ALL20 plus
1000 synthetic calls. Browser JSON zero signs remain unqualified. Four unit
tests pass and are included in gate.sh. Original independent full replay still
FAILS95146 numeric exceedances; no promotion. Retain report
`reference-candidate-original-comparison.json` and full replay
`reference-candidate-original-full.log`. NEXT qualify current20 complete
integrator/solver regressions and re-localize remaining earliest forward phase,
including the outstanding post-constraint RNE probe differences. Model/contact
metadata guards should continue to be strengthened; do not describe the
finite copied numerical read-set as full universal MuJoCo support. All jobs
terminal; production unchanged.

Current20 integration regression ALL20 outputs still agree. Fresh current20
phase log `reference-candidate-current-phase-localization.log` identifies point
Jacobian differences at comPos before constraint assembly (E1/substep1 etc),
plus the separately retained E0/substep3 post-constraint RNE force probe.
New `marble_jacobian_original.py` uses actual original public mj_jac at0x4bc88,
owned model topology/weld identity, complete copied cdof/subtree_com, explicit
point/body and both complete54-value outputs. Input copies/immutability and
original loaded-image/address guarded. Current trace lacks ALL browser point
Jacobians at E0/substep1 despite3 stale contacts: explicitly recorded as
uncaptured, not a parity pass; any partial captured output remains a rejection.
Report `reference-candidate-original-jacobian-v2.json` retained. NEXT inspect
reported actual-original differences and reconstruct exact cross/final-add
ordering; add full capture coverage before claiming all20 boundaries qualified.
No production arithmetic changed in this localization turn.

Original Jacobian arithmetic now qualifies: fused cross components followed by
separately rounded translational additions reproduce BOTH complete54-value
outputs on all124 captured calls and1240 seeded finite point/cdof/subtree_com
stress calls. Bounds/acyclic ordered DOF parents prevent invalid reconstruction
access/loops; three unit tests pass and gate.sh includes them. Report
`reference-candidate-original-jacobian-synthetic.json` retains original output
bits, current trace identity, coverage gap and20 browser jacp differences.
The uncapturedE0/substep1 boundary remains explicitly unqualified. NEXT create
an mj_jac-local Emscripten fused-cross candidate preserving generic cross/native
code; verify original complete outputs on new current inputs and independent
ordinary replay. Before universal coverage claims, resolve missing capture and
broaden topology/signed-zero tests. Production remains unchanged.

Packet-validation progress: `validated_packet` now checks all captured input
and output sizes/bit agreement, bounded explicit dimensions, standalone free
body ownership, sparse row coverage/block bounds/diagonal offsets and the exact
mass-to-derivative map, sleep/fluid/feature exclusions and finite timestep/time.
All forty retained v2 packets pass. Seven dependency-light tests pass, including
truncated arrays and unsupported/malformed layout rejection. Native-owned
topology comparison, guarded operand copy and original call remain pending;
this is not evidence of original integration parity.

1. Add strict dependency-light packet validation: finite values, bounded exact
   dimensions, integer topology/layout, valid bit/value agreement, unique named
   phase, and complete integration read-set. Reject unsupported task branches
   (sleep, fluid, flex, actuators, sensors, history, plugins) explicitly.
2. Verify captured model layout against the native-owned original model before
   any mutation; copy the complete validated operands with their exact bits.
3. Call the actual original public `mj_implicit` (library SHA recorded in plan
   3.16, symbol offset 0x88328), checking loaded-image and ownership guards.
   Compare time, qpos, qvel, qacc_warmstart, qDeriv, qH and qHDiagInv completely.
4. The named-phase lookup repair is implemented; continue to test it with
   original-library diagnostic replay. Do not relabel the old partial
   synchronization helper as strict validation.
5. Only after enclosing-output qualification localizes a difference, consider
   a private integration arithmetic candidate. No promotion without ordinary
   unsynchronized complete Marble replay acceptance.
# Jacobian candidate replay checkpoint — 2026-10-03

Bounded combined-trig model progress: read-only inspection of current platform routine identifies small-angle sine/cosine polynomial coefficients and fused Horner order. `marble_small_sincos_model.py` deliberately rejects abs(half-angle)>.5 rather than pretending range reduction is implemented. Its sine matches all162 in-domain fresh golden rows; complete sine/cosine bits match10,000 deterministic varied platform combined calls in[-.5,.5]. This remains a platform-specific reconstructed arithmetic candidate, not a qualified universal libm replacement; platform code/constant identity and wider/boundary stress need durable guards/receipts before private integration. Large-angle range reduction and all broader synthetic cases remain outstanding. No production changes.

Original axisAngle disassembly reveals compiler contraction of the separate source sin/cos calls into macOS `__sincos_stret` (two-double struct return ABI), followed by separately rounded axis products. Added `marble_platform_sincos.py`: all1,048 fresh golden rows exactly match the platform combined routine, while independent Python/platform sin/cos differs on six rows. This narrows the compatibility target to combined sincos behavior, not merely standalone libm sine/cosine. Receipt `event565-platform-sincos.json`; no portable replacement yet. Read-only bounded inspection of the running combined routine can guide arithmetic qualification; require broad original complete-output tests and native image/OS identity before using any reconstructed polynomial. Production unchanged.

Event565 trig isolation: unit-axis actual-original axisAngle calls qualify complete captured component multiplication; compiled unit-axis probe isolates sine (`3f942e9f87ba42fb` WASM vs `3f942e9f87ba42fc` original), cosine agrees. Added sine/cosine scalar fields and checks to the existing quaternion oracle/probe; old fixtures without them remain supported. A bounded Decimal Taylor cross-check (`marble_trig_reference.py`, finite half-angles abs<=16,120 and240 digit evaluations required to yield identical binary64 rounding) runs on all1,048 actual golden rows in this fresh trace, and finds71 original-library differences from the high-precision rounded results. In particular event565 sine high-precision rounding matches WASM, not the original's one-bit-higher result. Receipt `event565-trig-highprecision-v2.json`. Therefore simply replacing trig with a more accurate/correctly rounded function would NOT meet original parity; need qualify original libm arithmetic/ABI semantics, not a one-input ULP patch or tolerance waiver. No production trig change has been made.

Layer26 next unsynchronized drift localized after expanded352–709, middle544–576 and consecutive564–568 captures. Authoritative `translation-next-exact-unsynced.log` first selected live difference event565/substep3/checkPos: quaternion qpos13 original `-0.07204960811589031`, browser `-0.0720496081158903`. Fresh complete quaternion oracle/compiled receipts `event565-quaternion-original.json` / `event565-quaternion-compiled.json` isolate the preceding event565/substep2/joint1 integration: one captured integration difference and one axisAngle-on-original-operands difference, with the latter in rotation quaternion vector components (scalar component agrees). This now exposes the remaining axis-angle/trig family noted by synthetic checks; do not add another normalization patch without further qualification. Original helper outputs are compositional return evidence, not original private intermediate captures. Next isolate sine/cosine versus component multiplication at the exact half-angle, then qualify a narrow arithmetic/runtime correction against original outputs. Production unchanged.

Layer26 free-joint translation candidate: pinned original integratePos disassembly and all20 captured position calls qualify `fma(dt,velocity,position)` on all free translation components. Added50 finite translation-only varied calls per packet (1,000 total on the five-event window), guarding unchanged velocity; quaternion outputs of those stress calls are not claimed qualified. Private support.c changes only free-joint translation, native and slide/hinge paths unchanged. Durable `marble_translation_cumulative_candidate.patch` includes existing support-file edits/instrumentation, applies to original pinned file, and reverse-checks. Build succeeds; retained pair `retained-translation-candidate-dist`, WASM SHA256 `03659975d82018991ae5f48b2d00e756e3a96ee0ee9863822091b2b71e975afa`.

Fresh7,601-event driver receipt `translation-candidate-hard-trace.json`; complete original integration regression `translation-candidate-original-integrator.json` has zero differing boundaries/values on all fresh selected packets, including event351. Ordinary replay `translation-candidate-original-replay.log` still FAILS: first numeric exceedance event709/marble1/value10 delta `4.2741984418448453e-7` against `1e-7`;52,716 numeric exceedances;383 contact mismatches events857–6983. Later first divergence and fewer numeric exceedances do not waive increased contact mismatch count. Layer26 REJECTED for promotion. Next unsynchronized localization after352, retain unresolved quaternion synthetic and post-constraint probes, and reconcile durable runtime receipts before any production promotion. Production unchanged.

Next layer25 drift refined with consecutive348–352 trace `quaternion4-next-exact-trace.json` and unsynchronized replay `quaternion4-next-exact-unsynced.log`: first selected live phase difference is event351/substep2/checkPos, translation qpos0 original `0.29857571414268885`, browser `0.2985757141426888` (delta5.551115123125783e-17). Fresh exact-input original integration oracle `event351-original-integrator.json` reports one differing boundary/value, unlike the earlier selected regressions. Inspect its isolated position-on-browser-velocity receipt before attributing to control/adapter logic. This newly exposed translation boundary was not covered by earlier helper samples. Production unchanged.

Layer25 current exact-input integration regression (`quaternion4-current-original-integrator.json`) reports zero differing boundaries/values on the fresh selected hard trace. Expanded unsynchronized receipt `quaternion4-later-drift-unsynced.log` selects160–520: non-probe/non-statistic phase arrays remain exact through selected320, while352 inherits qpos/qvel and position-related drift. Next bracket320–352, not the later tolerance crossing520. These jobs completed normally; production unchanged and full acceptance still fails.

Layer25 private quaternion4 normalization correction applies only to kinematics and quatIntegrate; native and generic public normalization remain unchanged. Cumulative `marble_quaternion4_spatial_cumulative_candidate.patch` and `marble_quaternion4_smooth_cumulative_candidate.patch` include all earlier edits/instrumentation in those files, are for original pinned files rather than incremental application, and reverse-check against private tree. Build succeeds. Retained pair `retained-quaternion4-candidate-dist`: JS SHA256 `68f8cc9eb8711883658e3af912b6cb9d64b9e660d18041d43b9451ae0160634e`, WASM `0f5c01863e97d07edf5df8b24d63667ae835c914d1cda64f87d768c2d5e77119`. Helper receipt `quaternion4-candidate-helper.json`: all60 captured complete integration outputs agree; synthetic full integration differences reduced178→63 but remain unresolved. Public generic normalize4 differences are expected because only local callers changed.

Fresh `quaternion4-candidate-hard-trace.json` completes7,601 events. Unsynchronized selected phase replay through160 (`quaternion4-candidate-early-unsynced.log`) has no non-probe/non-statistic array differences, including the formerly differing event157 kinematics. Ordinary full replay `quaternion4-candidate-original-replay.log` still FAILS: first numeric exceedance event520/marble0/value10 delta `1.390830777214802e-7` versus `1e-7`;92,818 numeric exceedances;155 contact mismatches events689–2498. Layer25 REJECTED for promotion. Next fresh complete original integration/kinematics qualification and unsynchronized localization after160, while retaining the 63 synthetic and post-constraint discrepancies. Production unchanged.

Next live drift localized via consecutive156–160 unsynchronized trace `frame-next-exact-trace.json` / `frame-next-exact-unsynced.log`: event157/substep0/kinematics, body2 xquat and matching geom/inertial orientations differ; preceding selected live phases are exact. Original free-body kinematics normalizes the copied qpos quaternion, then normalizes xquat again. Fresh original/compiled helper receipts `event157-quaternion-original.json` / `event157-quaternion-compiled.json` confirm one captured normalize4 mismatch at event157/step0/joint1 and one complete captured integration mismatch. Complete original normalize4 length and component model matches all60 captured and1,000 synthetic calls, including its `abs(norm-1)>mjMINVAL` rescaling threshold. Ordering: sqrt(fma(w,w,fma(z,z,fma(x,x,y*y)))); reciprocal products separately rounded. Four standalone model tests pass and are included in gate.sh. Next correct the responsible kinematics/integration local normalization paths, preserving native and unrelated generic callers, then qualify fresh compiled behavior and full replay. Production unchanged.

Layer24 expanded unsynchronized replay `frame-candidate-later-drift-unsynced.log` completes through382. Selected non-probe/non-statistic phase arrays remain exact at52/56/60/64/80/96/128; event160 already inherits drift. Fresh middle-window trace/replay `frame-candidate-middle-window-trace.json` / `frame-candidate-middle-window-unsynced.log` narrows128–160 in four-event increments; inspect its earliest live phase receipt for the next consecutive capture. All these jobs reached terminal status; none need restarting. Ordinary full-game acceptance still fails; production unchanged.

Layer23/layer24 direct trace comparison resolves the identical tolerance receipt: actual non-engine public state differs on 7,552 events, first event49 (marble2 angular values and qaccWarmstart differ at tiny scales). Example value10 `-1.3311832071768124` vs `-1.3311832071768122`; qaccWarmstart12 `0.13737550231333903` vs `0.1373755023133384`. Thus the local correction DOES affect live runtime and is not merely spectator diagnostic output. Equal first-exceedance/count summaries do not imply trace neutrality. Initial naive comparison also counted engine snapshots present only on one trace's selected-event set; corrected comparison excludes only the optional engine snapshot, not public marbles/contacts/warmstart. Harness inspection confirms selected phase calls operate on live data, while RNE probe calls use a copied MjData restored in finally. Next extend layer24 capture beyond52 to locate independent remaining drift.

Layer24 collision-frame-local candidate built successfully and durable `marble_collision_frame_candidate.patch` reverse-checks. Retained pair `retained-frame-candidate-dist`, WASM SHA256 `e40c8008a46ef5a11b68bacdd37f193bec665e8545d1cd23e31853f2a6549630`. Generic makeFrame/normalize/cross and native branch unchanged. Two frame and two sphere/box model unit tests pass. Fresh selected unsynchronized phase receipt `frame-candidate-early-unsynced.log` has no non-probe/non-statistic phase array differences through event52, removing the former event49 frame/constraint discrepancy at these selected boundaries. This is selected-boundary evidence, not proof of every intervening phase or complete whole-game acceptance.

Fresh full 7,601-event trace `frame-candidate-hard-trace.json`; ordinary replay `frame-candidate-original-replay.log` still FAILS with the same first tolerance exceedance event382/marble1/value10 delta `2.0925396260196294e-7` against `1e-7`, 96,874 numeric exceedances, 195 contact mismatches events535–2441. Layer24 remains REJECTED for promotion. Next compare full runtime-state trace neutrality against layer23 and extend unsynchronized capture beyond52; investigate why removing local phase drift did not change the full-play tolerance receipt rather than assuming broad trajectory improvement. Compiled synthetic frame binding qualification still outstanding. Production unchanged.

Complete original frame-construction model qualified: `marble_frame_original.py` guards the pinned image and private makeFrame offset0x12bc0c, validates finite complete inputs before native calls, and compares all nine result bits. Two event49 raw normals reproduce the captured original renormalized normal; complete model agreement holds for those two calls plus 1,000 varied finite normal/tangent calls, including undefined and supplied tangent paths. Receipt `event49-original-frame-model.json`; two model unit tests pass and are included in gate.sh. Original ordering: fused three-product dot; normalize normal and orthogonalized tangent using fused norm-square; tangent projection products and subtractions remain separately rounded; final cross uses fused first product plus negated rounded second product. This is original complete-return qualification, not capture of original private intermediate buffers. Next apply only to collision frame construction in a private candidate, leaving generic engine normalization/cross unchanged, then verify fresh original calls and full unsynchronized replay. Production unchanged.

Layer23 next drift narrowed with unsynchronized selected capture48–52 (`quaternion-norm-next-exact-trace.json`, replay `quaternion-norm-next-exact-unsynced.log`): first non-probe dynamic phase difference event49/substep1/fwdPosition, ten efc_J and 40 efc_AR values. Pre-sync contact2 is sphere/box; depth/position agree, but frame normal/tangent differ. All captured geometry size/pose/orientation inputs match packed binary64. Exact-boundary original raw sphere/box probe (`event49-original-sphere-box.json`) passes complete reconstruction on two captured calls and 200 varied outside calls. Collision driver subsequently invokes `mju_makeFrame`, which normalizes the raw contact frame again; this is the next upstream candidate, not proof that the already-qualified raw collision ordering is wrong. Added exact-label selection to the original raw probe to avoid mixing this boundary with later inherited input drift. Next qualify makeFrame normal/tangent outputs against actual original calls before another local correction.

Layer23 fresh exact-input integration regression on ten selected events (including40–44) passes every complete output field: zero differing boundaries and values in `quaternion-norm-current-original-integrator.json`. However expanded unsynchronized phase replay `quaternion-norm-drift-bracket-unsynced.log` already inherits non-probe dynamic drift by event64 while event44 remains exact outside post-constraint probes/statistics. Event382 is only the declared-tolerance crossing, not the first bitwise divergence. Next narrow44–64; do not restrict the search to event382 or claim fully exact trajectories before it.

Layer23 integration-local normalize3 candidate built successfully; cumulative spatial patch `marble_quaternion_norm_cumulative_candidate.patch` includes layer18 multiplication and reverse-checks against current private source. Retained pair `retained-quaternion-norm-candidate-dist`, WASM SHA256 `5ca35a6f49b9d634fff286ea023da83a5da7aea77eb0e05cd66f76998a7e32cf`. Compiled helper receipt `quaternion-norm-candidate-helper.json`: zero complete integration differences on all 60 captured failing-window cases; 177 complete synthetic integration cases remain different (normalize4/trig and other synthetic boundaries unresolved). Generic normalize3/multiply unchanged, so their public helper differences are expected, not proof of the integration-local correction failing. Sphere/box model unit tests now included in gate.sh.

Fresh full driver/replay receipts `quaternion-norm-candidate-hard-trace.json` and `quaternion-norm-candidate-original-replay.log`: 7,601 events completed, ordinary replay still FAILS. First numeric exceedance moved from event216 to event382/marble1/value10, delta `2.0925396260196294e-7` against `1e-7`; 96,874 numeric exceedances; 195 contact-set mismatches events535–2441. This is progress on the identified early cause, NOT overall acceptance: layer23 remains REJECTED for promotion. Next fresh exact-input original integration regression and unsynchronized drift localization before event382; preserve outstanding post-constraint and broader synthetic discrepancies. Production unchanged.

Quaternion drift localized on 60 fresh captured joints plus 1,000 synthetic cases. The compiled helper probe formerly checked normalized axis components but omitted the returned normalize3 length. Added that scalar check. Event42/substep3/joint0 has identical normalized-axis bits yet different length: WASM `40096c413ccc03ef`, original `40096c413ccc03ee`; this changes the subsequent angle and integration result. Event44/substep0/joint1 differs in length and axis. The exact original normalize3 model `sqrt(fma(z,z,fma(x,x,y*y)))`, followed by reciprocal and separately rounded component products, reproduces complete original length AND axis bits on all 1,060 cases (`drift-quaternion-normalize-model.json`). Fresh compiled receipt `drift-quaternion-compiled-length.json`: two captured integration differences, two captured length differences, one captured axis difference; no captured normalize4 or axisAngle-on-original-operands differences. Generic multiply remains deliberately unchanged and its differences are not a regression of the integration-local multiply candidate. Next apply normalize3 ordering only inside quatIntegrate, then qualify compiled full helpers and gameplay again. Production unchanged.

Unsynchronized drift localization refined: selected events32/36/40 had no non-probe, non-statistic array differences; event44 already inherited drift. A fresh consecutive capture40–44 (`sphere-box-drift-exact-trace.json`) identifies the first selected live-state difference at event42/substep3/implicit: qpos index4 source `0.008868357255295101`, browser `0.008868357255295103`. Exact-input actual-original integration receipt `sphere-box-drift-exact-original-integrator.json` independently reproduces this difference and isolates it to position integration with identical browser post-integration velocity: original bits `3f822992c30bbfba`, browser `3f822992c30bbfbb`. Another local qpos-only difference occurs event44/substep0/index13 (`bf8b59bf16672bd9` vs `bf8b59bf16672bd8`). Other complete integrator output fields agree on these packets. Earlier five-event integration success did not cover this quaternion boundary. Next localize normalize/axis-angle/multiplication helper stages on these new operands; do not infer another implicit velocity-solver defect. Production unchanged.

Expanded early trace completed. First unsynchronized diagnostic replay exposed a recorder-only NameError: the new pre-sync collision logger used a substep variable initialized only by synchronization mode. Fixed it to the actual completed phase-list length. Re-run `sphere-box-expanded-unsynced-v2.log` finished through event216 with no before-step1 or before-fwdConstraint synchronization. This is the authoritative expanded unsynchronized receipt; the failed first log is not physics evidence. Separate post-constraint force-probe differences still begin at event0/substep3. Further extraction of the earliest non-probe dynamic divergence is required before another physics edit.

Fresh layer22 regression receipts: `sphere-box-candidate-original-integrator.json` has zero differing integration boundaries/values; `sphere-box-candidate-original-jacobian.json` has 130 captured calls, 1,300 varied reconstruction calls, zero jacp/jacr differences and no missing selected boundaries. Trace SHA256 `f99fdd3b127e0f443a512c1e43fcb140a778e532ca6b071f5373e50f3ffe23d9`. Fresh `sphere-box-current-phase-localization.log` confirms all 20 pre-sync complete contact-geometry arrays agree, including the formerly differing event216/substep1 sphere/box. Selected forward phases no longer differ there. Separate post-constraint force probes and solver statistics remain; event216 entry also contains solver-state differences inherited from earlier unrecorded steps. This does NOT qualify unsynchronized trajectory parity. Expanding early selected events to 0,1,2,3,4,8,16,17,18,32,64,96,128,160,192,208,216 to locate that preceding drift; do not attribute inherited solver arrays to collision without new evidence.

Layer22 private outside sphere/box candidate built successfully and its durable `marble_sphere_box_outside_candidate.patch` reverse-checks against the private source. Native compilation path is unchanged; inside-center fallback remains original (boundary classification and generic callers still need regression qualification). Retained pair: `retained-sphere-box-candidate-dist`, WASM SHA256 `0427ace3f34d27410110ba3a943f9c9bd670adf330909fed16a6a184396b4533`. Fresh driver completed 7,601 events, receipt `sphere-box-candidate-hard-trace.json`. Ordinary original replay FAILS: unchanged first numeric exceedance event216/marble0/value10 delta `1.666538045341781e-7` versus `1e-7`; 102,404 numeric exceedances; 113 contact-set mismatches events482–1966. Therefore layer22 is REJECTED for promotion, despite fewer contact mismatches than layer21. Next rerun pre-sync collision and complete original local/regression qualification on fresh layer22 inputs to establish whether the selected collision mismatch is removed and locate the remaining independent cause. Production unchanged.

Sphere/box arithmetic reconstruction now reproduces every bit of the complete raw result (depth, position, normal, tangent) for all ten captured calls and 1,000 varied finite outside-branch calls against the pinned original private routine. Receipt `sphere-box-original-model-synthetic.json`; two model unit tests pass. Disassembly qualifies the dot ordering as `fma(z,z,fma(x,x,y*y))` for norm-square and analogous product ordering for local/world transforms; deepest and midpoint additions use fused multiply-add, while final world-position translation remains separately rounded. Only outside-center contacts are qualified; inside branch remains explicitly rejected by the model. Varied calls retain captured orientations/sizes and use far-outside centers with a large query margin, not gameplay trajectories. Next implement a sphere/box-local private candidate, preserve native/inside behavior, and run fresh compiled/original and ordinary full-replay checks. Local reconstruction success is not production acceptance.

Collision-input qualification: enriched `jacobian-presync-collision-operands.log` confirms all 177 size, 177 position and 531 orientation scalar operands match packed binary64 at the differing event216/substep1 boundary (JSON does not independently preserve browser signed zero). Added `marble_sphere_box_original.py`, guarded to the pinned actual-original library, to invoke its private raw sphere/box kernel. Initial source-signature invocation was invalid: the original optimized private ABI omits unused mat1, as confirmed by disassembled x1..x5 operand loads; that failed receipt is NOT parity evidence. Corrected optimized-ABI invocation reproduces original depth and position on every selected captured sphere/box call and retains full raw output bits in `sphere-box-original-raw.json`. This establishes a concrete actual-original collision oracle for further arithmetic localization; no compiled correction or promotion yet. The script remains an exact-image private diagnostic, not a portable public API.

Pre-sync collision receipt `jacobian-presync-collision.log` completed all 20 selected boundaries on the actual original runtime. Nineteen complete contact-geometry arrays match; the sole differing boundary is event216/substep1/contact0 (geoms56/48; types2/6, sphere/box). Original depth `-2.077988697010702e-5`, WASM `-2.0779886970107887e-5`; original normal-y `-0.633967748739735`, WASM `-0.6339677487397352`; corresponding tangent-x differs likewise. Other recorded geometry fields match. This is direct pre-solver-sync evidence that collision output differs upstream of constraint assembly. The harness now additionally emits source/WASM geom_xpos, geom_xmat and geom_size operands; this second enriched capture still needs running and checking, including bit-level qualification before attributing the difference to `mjraw_SphereBox` arithmetic. Syntax verification passed. No production changes.

Contact-assembly inspection: `mj_instantiateContact` obtains pair differences through `mj_contactJacobian`, then rotates with `mju_mulMatMat`; these stages must be qualified independently. At event216/substep1, the first differing row translation coefficient is source `0.633967748739735` versus WASM `0.6339677487397352`. The recorded WASM contact0 normal is `[0.7733594853351656, -0.6339677487397352, 0]` (geoms56/48, dim3), so the row coefficient is consistent with the contact normal. The same phase also differs in `efc_pos` by `8.673617379884035e-19`; this makes collision/contact geometry an upstream candidate, not proof of a matrix-product bug. Current synchronization/comparison logging does not provide an independently retained pre-overwrite native contact-frame receipt at this boundary. Next capture native collision geometry before solver synchronization and qualify pair-difference/rotation operands before choosing an arithmetic patch. No speculative contact rotation patch has been applied.

Fresh phase localization on the complete owned-buffer layer21 trace finished through event216, with actual-wheel validation of the diagnostic solver library enabled. Receipt: `jacobian-current-phase-localization.log`. The selected ordinary forward fields no longer first differ at event1 or event17: the first remaining forward array difference is event216/substep1/fwdPosition (`efc_J`: seven values, `efc_AR`: 26 values). A separate zero-acceleration post-constraint force probe still first differs at event0/substep3 (`cfrc_ext`: two values; `cfrc_int`: three values); event17/substep2 also retains one solver statistic difference. These are exploratory phase-localization observations with before-step1 and before-fwdConstraint synchronization, NOT ordinary trajectory acceptance or complete independent read-set qualification. Next target is the contact Jacobian assembly after exact point Jacobians; do not change generic dot/cross rules without original-library qualification. Three Jacobian unit tests and 13 trace-neutrality unit tests passed. The owned-buffer cleanup now also frees its first allocation if the second constructor throws.

Recorder follow-up: point Jacobians now use binding-owned `DoubleBuffer` output storage rather than borrowing `efc_J`. This removes the constraint-allocation-dependent early return and restores coverage at event0/substep1. Fresh `jacobian-owned-buffer-trace.json` SHA256 `27bce73e599f95039350c5e9db179d76b05c331e17597cf6c84ddb5f460274ea`: 130 captured actual-original calls, 1,300 varied reconstruction calls, zero jacp/jacr differences, no uncaptured selected boundaries. Full 7,601-event recursive comparison against the pre-edit layer21 trace passed for every existing physics and diagnostic field; only the deliberately changed harness SHA identity was excluded, and 288 newly present 54-value point-Jacobian arrays were shape/name-checked. Existing output arrays were NOT excluded. The recorder fix does not change the rejected layer21 gameplay result or justify production promotion. Reports remain under the owned private root.

The interrupted layer21 build completed successfully (`mujoco_wasm` 100%); its old process handle no longer exists and no matching build process remains. The Jacobian-only patch reverse-checks against the private upstream tree. The fresh pair is retained at `/private/tmp/nw-marble-costchange.7SuZEZYO/retained-jacobian-candidate-dist`, not installed in production.

Fresh `jacobian-candidate-hard-trace.json` SHA256: `29792ce6520a2945267f9ede453129db78a470a8b1de58d65b378406011c33fa`. The generated driver completed all 7,601 events. Actual-original Jacobian comparison: 124 captured calls, zero translation or rotation Jacobian differences; reconstruction qualification also passed 1,240 varied original-library calls. These varied calls qualify the reconstruction, not a compiled synthetic probe. Event0/substep1 still has no recorded browser Jacobian outputs and remains explicitly unqualified.

The ordinary original replay FAILS: first numeric exceedance event216/marble0/value10, delta `1.666538045341781e-7` against `1e-7`; 104,372 numeric exceedances and 151 contact-set mismatches (events482–1966). Full replay log: `jacobian-candidate-original-replay.log` in the owned private root. Layer21 is therefore REJECTED for promotion despite local Jacobian agreement. Production is unchanged. Next: inspect current integration/reference regression receipts, repair the missing recorder boundary with neutrality proof, and localize the remaining forward/post-constraint differences using this fresh trace rather than older candidate inputs.

Browser lifecycle follow-up (2026-10-03): corrected the plan's stale summary
that restart/rollover remained unverified. Re-ran the synchronized comparator
on the durable rung-16/run-seed-17 light DPR2 real-key restart pair; it exits
zero with no scene/camera failures (stage exact fraction0.9980231266, stage
MAE0.1161879152). Re-ran both second-tray visual pairs: ordinary Space-next
and delayed automatic host rollover each match the original source at tray-2
elapsed200ms with no scene/camera failures (stage exact fraction0.9998094496,
stage MAE0.0043858918; board seed785170443, grain seed1.158501511057862).
The automatic case waits2700ms and, by itself, does not qualify the exact
2600ms boundary; a later deterministic browser-host replay below qualifies
the timestamp transition, and a still later entry records the native-RAF
deadline crossing. The fresh
multi-trial test passes three controller cases and
seven actual timeout trays, including result history, next-board handoff,
adaptive progression, and cleanup. `marble_maze_browser_test.mjs`,
`marble_renderer_contract_test.mjs`, and `marble_board_abi_test.mjs` pass.
The retained images/comparisons are still diagnostic-only; this neither
establishes reviewed pixel thresholds nor promotes a physics artifact.

Exact browser-host feedback-boundary replay (2026-10-03): fresh Chromium
session `marble-boundary-oct3` served the current shell at localhost:8017 and
used the actual Games -> Attention -> Marble Maze -> Enter -> Space path.
Debug-only options configured rung1, two trays, nonadaptive, 15s, and frozen
active RAF; the game engine reported MuJoCo and the renderer WebGL2. Nine
hundred real 1/60s Marble physics steps produced elapsed15.000000000000325s,
FEEDBACK/trial1, timeout, 2600ms remaining, and one recorded result. With
`performance.now` overridden only in this disposable page, one actual
`marbleTestStepFixedFrame` host tick at exactly t0+2599ms remained FEEDBACK
with1ms remaining, unchanged board seed819894323, and one result row. A second
tick at the same timestamp left the captured controller-state array,
board/grain identity, and result-row JSON exactly equal to their pre-tick
values. The t0+2600ms host tick transitioned to RUNNING/trial2 at elapsed0
with a newly dealt board
(seed956103216, versus819894323) and still exactly one result row. A subsequent
1/60s fixed frame advanced tray2 to0.016666666666666666s with one live MuJoCo
model/data. Restoring native `performance.now` and pressing Escape disposed
all resources (created/deleted models3/3 and data3/3; live counts0/0). This is
exact transition coverage of the browser host using controlled timestamps,
not an unmodified RAF boundary measurement. At this point in the chronology,
the separately retained natural RAF path had only been observed after a2700ms
delay; the subsequent entry below checks its near-boundary callbacks. The temporary browser was closed;
the pre-existing retained browser session was left untouched. No production
code or physics artifact changed.

Natural-RAF feedback-boundary replay (2026-10-03): fresh session
`mm-natural-raf-oct3` entered the game through the real menu and used the same
rung1/two-tray/nonadaptive/15s MuJoCo/WebGL2 test configuration. After899
fixed 60Hz physics steps, the final fixed step naturally entered timeout
feedback. For that single helper call, `cancelAnimationFrame` was temporarily
wrapped so its post-tick cleanup would not cancel the native RAF callback that
`marbleTick` had just scheduled; native cancellation and `performance.now`
were restored immediately before returning to the browser event loop. The
feedback loop then ran on native RAF timestamps. A per-frame observer recorded
the last feedback callback at t0+2594.8ms (phase FEEDBACK, 6ms remaining) and
the next callback at t0+2611.5ms (phase RUNNING, trial2, elapsed0). Thus the
host did not advance before2600ms and advanced on its first observed RAF after
the deadline, with11.5ms frame-scheduling overshoot. Tray2 used board seed
990686516 and the first tray remained the only recorded result. This is actual
native RAF feedback scheduling after fixed-step timeout setup, not15s of
uninterrupted wall-time physics or evidence from another browser engine.
Escape cleanup reported models/data created1/deleted1 and zero live; console
was clean after a retry of the initial page load. The temporary browser was
closed and no browser sessions remained. No production code or physics
artifact changed.

Displayed-background READY capture and legacy raw-PNG correction
(2026-10-03): The browser READY image had been captured with raw canvas
`toDataURL()` readback. Its transparent canvas pixels become black if RGB
comparison simply drops alpha, even though the displayed canvas is CSS white.
The original-source framebuffer also retains alpha coverage on glyph edges,
so only the browser candidate should be composited; original RGB remains the
reference signal. Replayed the normal browser route title -> Games ->
Attention -> Marble Maze -> Space in Chromium at800x600 logical/DPR2 and
captured using `captureMarbleFramebuffer(..., {displayedBackground:true})`.
The same-task debug snapshot records `mode=displayed-background-composite`,
`rgb(255,255,255)`, and1600x1200. Source and candidate both have no board,
marbles, model, or data; scene metadata and 1504x737 viewport match exactly.
New pair is `output/playwright/mm-source-ready-current.png` versus
`output/playwright/mm-browser-ready-current-composited.png`, with candidate
debug/metadata alongside. Strict synchronized comparison has zero failures:
stage exactness100%, stage MAE0, full-frame exactness98.96375%, MAE1.178742.
These text/chrome differences are diagnostic, not accepted pixel limits.

Capture contract hardening: `marble_framebuffer_capture.mjs` now binds its
readback mode/background/dimensions into the returned debug snapshot;
`marble_browser_pair_metadata.py` accepts new comparison metadata only for
same-size, theme-matched, fully opaque displayed composites; and
`marble_render_pair_test.py` composites recorded/legacy raw browser alpha over
the synchronized theme while preserving source framebuffer RGB. Contract
tests cover the transparent READY failure mode, wrong theme background, and
raw-canvas-to-displayed-pixel recovery. The visual evidence audit now rechecks
14 pairs (light/dark, DPR1/2, ready/rolling/win/loss/done/timeout/restart/
rollover/alternate viewport), reports the effective readback treatment, and
exits0 with failures[]; `accepted` remains false. Focused capture, metadata,
comparator, and audit regression tests all pass. Existing raw captures are
retained and measured through the display composite rather than excluded.

The first current HTTP page load again logged `ERR_CONNECTION_RESET` for a few
late local modules; a same-session reload then loaded all resources and
initialized the app with zero console errors. To isolate server concurrency,
the test was repeated on a standard-library `ThreadingHTTPServer` at port8032.
Its first fresh Chrome navigation reset requests for
`marble-maze-mujoco.js`, `marble-maze-renderer.js`, and `result-store.js`;
none of those requests appeared in that server's access log. Direct `curl`
requests to the exact renderer and result-store URLs returned HTTP200. Reload
in that browser then fetched all three modules successfully (HTTP200), loaded
the WASM dependencies, and set `window.__nw`. A second fresh Chrome process
on the same threaded server loaded every module and WASM dependency on its
first navigation, with zero console errors. The earlier serial-server cold
run also had two late module resets. Thus a threaded server did not prevent
the intermittent first-navigation symptom, while clean first-load and reload
success show it is not a persistent failure; the reset occurs before the
threaded Python handler logs those requests. This evidence does not identify
whether the remaining cause is in browser startup, local transport, or another
layer, so no retry/bootstrap workaround or serving-code change is justified
yet. All three Playwright sessions created for this check and both temporary
servers (ports8031/8032) were closed/stopped. No app, physics, compiler, or
production WASM artifact changed.
