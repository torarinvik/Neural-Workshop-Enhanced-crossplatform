// Common-v1 lifecycle smoke for the source-backed Matrix Reasoning task.
//
// The public state never carries the answer while a puzzle is live.  The
// focused accessor is used only by this conformance test to choose a known
// answer and prove that the controller grades, hides, times, renders, and
// disposes a real generated Ravens puzzle.
import assert from "node:assert/strict";
import fs from "node:fs";
import { fileURLToPath } from "node:url";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { decode, Kind } from "../shells/web/display-list.js";

const root = fileURLToPath(new URL("..", import.meta.url));
const wasm = process.env.NWCORE_WASM_PATH ?? `${root}/build/nwcore.wasm`;
const { exports, instance } = await instantiateElisa(fs.readFileSync(wasm), { warn: false });

const TASK = BigInt(exports.nw_api_v1_task_matrix_reasoning());
const STATUS = Object.freeze({ accepted: 1n, ignored: 2n, badOptions: -3n });
const EVENT = Object.freeze({ action: 1n, keyDown: 2n, pointerDown: 5n });
const KEY = Object.freeze({ space: 1n, enter: 2n, one: 12n });
const ACTION = Object.freeze({ start: 0n, answer: 1n });
const PHASE = Object.freeze({ ready: 0n, asking: 1n, hidden: 2n, feedback: 3n, done: 4n });
const INFO = Object.freeze({
  phase: 0, level: 1, trial: 2, totalTrials: 3, across: 4, choices: 5,
  answer: 6, picked: 7, correct: 8, verdict: 9, exposureMs: 10,
  adaptive: 11, feedback: 12, explain: 13, color: 14, trialLevel: 15,
  lines: 16, hasPuzzle: 17, answered: 18, meanMs: 19, askedAtMs: 20,
  feedbackUntilMs: 21,
});
const VALUE = Object.freeze({ gridCount: 0n, choiceCount: 1n, shape: 2n,
  fill: 3n, angle: 4n, part: 5n, cx: 6n, cy: 7n, radius: 8n,
  linePart: 9n, lineAttr: 10n, lineKind: 11n, lineParam: 12n });
const STATE_BYTES = 112;
const FRAME_BYTES = 1048576;
const STATE_BUFFER = Number(exports.nw_frame_alloc(BigInt(STATE_BYTES)));
const FRAME_BUFFER = Number(exports.nw_frame_alloc(BigInt(FRAME_BYTES)));
assert.ok(TASK > 0n && STATE_BUFFER > 0 && FRAME_BUFFER > 0);
assert.equal(TASK, 3934003723n, "Matrix Reasoning keeps its stable task ID");
assert.equal(Number(exports.nw_api_v1_supports(TASK)), 1);

function create(options = [1n, 5n, 0n, 1n, 1n, 1n], seed = 17n) {
  return exports.nw_api_v1_create(TASK, 1n, ...options, seed);
}

function dispatch(handle, kind, timestamp, sequence, code, value = 0n,
                 x = 0n, y = 0n) {
  return exports.nw_api_v1_dispatch(handle, kind, BigInt(timestamp),
    BigInt(sequence), code, value, 0n, 0n, x, y, 0n);
}

function action(handle, code, timestamp, sequence, value = 0n) {
  return dispatch(handle, EVENT.action, timestamp, sequence, code, value);
}

function keyDown(handle, key, timestamp, sequence) {
  return dispatch(handle, EVENT.keyDown, timestamp, sequence, key);
}

function pointer(handle, timestamp, sequence, x, y) {
  return dispatch(handle, EVENT.pointerDown, timestamp, sequence, 0n, 0n,
    BigInt(Math.round(x * 1000000 / 912)),
    BigInt(Math.round(y * 1000000 / 684)));
}

function advance(handle, timestamp, sequence) {
  return exports.nw_api_v1_advance(handle, BigInt(timestamp), 0n,
    BigInt(sequence));
}

function state(handle) {
  const length = exports.nw_api_v1_read_state(handle,
    BigInt(STATE_BUFFER), BigInt(STATE_BYTES));
  assert.equal(length, BigInt(STATE_BYTES));
  const view = new DataView(instance.exports.memory.buffer, STATE_BUFFER, STATE_BYTES);
  assert.equal(view.getUint32(0, true), 0x3152574e);
  assert.equal(view.getUint32(4, true), 1);
  assert.equal(view.getUint32(12, true), 12);
  return Array.from({ length: 12 }, (_, index) =>
    view.getBigInt64(16 + index * 8, true));
}

function info(handle, field) {
  return BigInt(exports.nw_api_v1_matrix_reasoning_info(handle, BigInt(field)));
}

function value(handle, field, at = 0) {
  return BigInt(exports.nw_api_v1_matrix_reasoning_value(handle, field, BigInt(at)));
}

function frame(handle) {
  const length = exports.nw_api_v1_render(handle, BigInt(FRAME_BUFFER),
    BigInt(FRAME_BYTES), 0n, 912n, 684n);
  assert.ok(length > 0n, `render failed: ${length}`);
  return new Uint8Array(instance.exports.memory.buffer, FRAME_BUFFER,
    Number(length)).slice();
}

function hasText(bytes, expected) {
  return decode(bytes).some(({ kind, text }) =>
    kind === Kind.TEXT && text.includes(expected));
}

for (const options of [
  [0n, 5n, 0n, 1n, 1n, 1n],
  [13n, 5n, 0n, 1n, 1n, 1n],
  [1n, 4n, 0n, 1n, 1n, 1n],
  [1n, 5n, 5000n, 1n, 1n, 1n],
  [1n, 5n, 0n, 2n, 1n, 1n],
  [1n, 5n, 0n, 1n, 4n, 1n],
  [1n, 5n, 0n, 1n, 1n, 2n],
]) {
  assert.equal(create(options), STATUS.badOptions,
    `bad options accepted: ${options}`);
}

const run = create();
const replay = create();
assert.ok(run > 0n && replay > 0n);
assert.deepEqual(state(run), [0n, 1n, 0n, 5n, 0n, 0n, -1n, 0n,
  -1n, 0n, 0n, 0n]);
assert.equal(info(run, INFO.level), 1n);
assert.equal(info(run, INFO.feedback), 1n);
assert.equal(info(run, INFO.explain), 0n);
assert.equal(info(run, INFO.color), 1n);
const readyFrame = frame(run);
assert.deepEqual(frame(run), readyFrame, "ready rendering is observational");
assert.ok(hasText(readyFrame, "Matrix Reasoning"));
assert.ok(hasText(readyFrame, "Press Space to start"));

assert.equal(keyDown(run, KEY.space, 100, 0), STATUS.accepted);
assert.equal(action(replay, ACTION.start, 100, 0), STATUS.accepted);
assert.deepEqual(state(run), state(replay), "same seed gives the same generated puzzle");
assert.equal(info(run, INFO.phase), PHASE.asking);
assert.equal(info(run, INFO.trial), 1n);
assert.equal(info(run, INFO.across), 2n);
assert.equal(info(run, INFO.choices), 4n);
assert.equal(info(run, INFO.hasPuzzle), 1n);
assert.ok(info(run, INFO.answer) >= 0n && info(run, INFO.answer) < info(run, INFO.choices));
assert.ok(info(run, INFO.lines) >= 0n);
assert.ok(value(run, VALUE.gridCount, 0) > 0n);
assert.ok(value(run, VALUE.choiceCount, 0) > 0n);
assert.ok(value(run, VALUE.shape, 0) >= 0n);
assert.ok(value(run, VALUE.radius, 0) > 0n);
const askingFrame = frame(run);
assert.ok(hasText(askingFrame, "Which one finishes the pattern?"));
assert.ok(hasText(askingFrame, "1-8 or click"));

const answer = info(run, INFO.answer);
assert.equal(action(run, ACTION.answer, 200, 1, answer), STATUS.accepted);
assert.equal(info(run, INFO.phase), PHASE.feedback);
assert.equal(info(run, INFO.picked), answer);
assert.equal(info(run, INFO.correct), 1n);
assert.equal(info(run, INFO.verdict), 1n);
const feedbackUntil = Number(info(run, INFO.feedbackUntilMs));
assert.equal(advance(run, feedbackUntil - 1, 2), STATUS.ignored);
assert.equal(info(run, INFO.phase), PHASE.feedback);
assert.equal(advance(run, feedbackUntil, 3), STATUS.accepted);
assert.equal(info(run, INFO.phase), PHASE.asking);
assert.equal(info(run, INFO.trial), 2n);

// The common pointer path must use the same two-column placement as the live
// scene.  This point is in the upper-left candidate at the reference size.
const pointerRun = create([1n, 5n, 0n, 0n, 0n, 1n], 31n);
assert.equal(action(pointerRun, ACTION.start, 100, 0), STATUS.accepted);
assert.equal(pointer(pointerRun, 200, 1, 700, 300), STATUS.accepted);
assert.equal(info(pointerRun, INFO.phase), PHASE_DONE_OR_FEEDBACK(pointerRun));
function PHASE_DONE_OR_FEEDBACK(handle) {
  const phase = info(handle, INFO.phase);
  assert.ok(phase === PHASE.feedback || phase === PHASE.done || phase === PHASE.asking);
  return phase;
}

// Exposure hides the generated cards through the source deadline, after
// which a remembered keyboard/pointer answer is still accepted.
const exposed = create([1n, 5n, 10000n, 1n, 1n, 1n], 23n);
assert.equal(action(exposed, ACTION.start, 100, 0), STATUS.accepted);
assert.equal(advance(exposed, 10099, 1), STATUS.ignored);
assert.equal(info(exposed, INFO.phase), PHASE.asking);
assert.equal(advance(exposed, 10100, 2), STATUS.accepted);
assert.equal(info(exposed, INFO.phase), PHASE.hidden);
const hiddenCommands = decode(frame(exposed));
assert.ok(hasText(frame(exposed), "Which one finishes the pattern?"));
assert.equal(hiddenCommands.filter(({ kind }) =>
  kind === Kind.RECT || kind === Kind.POLYGON || kind === Kind.MULTILINE).length, 0,
"hidden phase removes the source cards from the redraw");
assert.equal(action(exposed, ACTION.answer, 10200, 3, info(exposed, INFO.answer)), STATUS.accepted);
assert.equal(info(exposed, INFO.phase), PHASE.feedback);

// A no-feedback run advances immediately, matching the source option.
const noFeedback = create([1n, 5n, 0n, 0n, 0n, 1n], 41n);
assert.equal(action(noFeedback, ACTION.start, 100, 0), STATUS.accepted);
assert.equal(action(noFeedback, ACTION.answer, 200, 1, info(noFeedback, INFO.answer)), STATUS.accepted);
assert.equal(info(noFeedback, INFO.phase), PHASE_DONE_OR_FEEDBACK(noFeedback));
assert.equal(info(noFeedback, INFO.answered), 1n);

for (const handle of [run, replay, pointerRun, exposed, noFeedback]) {
  assert.equal(exports.nw_api_v1_destroy(handle), 0n);
  assert.equal(exports.nw_api_v1_destroy(handle), 0n, "destroy is idempotent");
}

console.log("PASS: Matrix Reasoning source-backed generation, deterministic panels, exposure, pointer/keyboard grading, feedback, render, and cleanup");
