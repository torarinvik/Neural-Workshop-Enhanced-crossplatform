// Common-v1 lifecycle, source timing, typed recall, produce timing, pointer
// hit-testing, feedback, and display-list checks for the Mr. Time port.
import assert from "node:assert/strict";
import fs from "node:fs";
import { fileURLToPath } from "node:url";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { decode, Kind } from "../shells/web/display-list.js";

const wasm = process.env.NWCORE_WASM_PATH ??
  fileURLToPath(new URL("../build/nwcore.wasm", import.meta.url));
const { exports, instance } = await instantiateElisa(fs.readFileSync(wasm), { warn: false });

const TASK = BigInt(exports.nw_api_v1_task_mr_time());
const EVENT = Object.freeze({ action: 1n, text: 8n, pointerDown: 5n });
const ACTION = Object.freeze({ start: 0n, digit: 1n, point: 2n,
  backspace: 3n, submit: 4n, act: 5n });
const FIELD = Object.freeze({ phase: 0, rung: 1, trial: 2, total: 3,
  correct: 4, trialMode: 5, answerCount: 6, targetMs: 7,
  intervalMs: 8, verdict: 9, resultCount: 10, adaptive: 11 });
const INFO = Object.freeze({ mode: 1, startRung: 2, deadline: 14,
  feedbackUntil: 15, maxGap: 16, flash: 17, appearedAt: 18, askAt: 19 });
const PHASE = Object.freeze({ ready: 0n, showing: 1n, waiting: 2n,
  asking: 3n, counting: 4n, feedback: 5n, done: 6n });
const MODE = Object.freeze({ recall: 0n, produce: 1n, both: 2n });
const STATUS = Object.freeze({ accepted: 1n, ignored: 2n, badOptions: -3n });
const FRAME_CAPACITY = 65536n;
const statePtr = Number(exports.nw_frame_alloc(112n));
const framePtr = Number(exports.nw_frame_alloc(FRAME_CAPACITY));
assert.ok(TASK > 0n && statePtr > 0 && framePtr > 0);

function create(options, seed = 17n) {
  return exports.nw_api_v1_create(TASK, 1n, ...options, seed);
}

function state(handle) {
  assert.equal(exports.nw_api_v1_read_state(handle, BigInt(statePtr), 112n), 112n);
  const view = new DataView(instance.exports.memory.buffer, statePtr, 112);
  assert.equal(view.getUint32(0, true), 0x3152574e);
  assert.equal(view.getUint32(12, true), 12);
  return Array.from({ length: 12 }, (_, index) =>
    view.getBigInt64(16 + index * 8, true));
}

function info(handle, field) {
  return exports.nw_api_v1_mr_time_info(handle, BigInt(field));
}

function dispatch(handle, kind, timestamp, sequence, code, value = 0n,
                 x = 0n, y = 0n) {
  return exports.nw_api_v1_dispatch(handle, kind, BigInt(timestamp),
    BigInt(sequence), code, value, 0n, 0n, x, y, 0n);
}

function action(handle, code, timestamp, sequence, value = 0n) {
  return dispatch(handle, EVENT.action, timestamp, sequence, code, value);
}

function text(handle, character, timestamp, sequence) {
  return dispatch(handle, EVENT.text, timestamp, sequence, 0n,
    BigInt(character.codePointAt(0)));
}

function advance(handle, timestamp, sequence) {
  return exports.nw_api_v1_advance(handle, BigInt(timestamp),
    BigInt(Math.max(0, timestamp - 1)), BigInt(sequence));
}

function frame(handle) {
  const length = exports.nw_api_v1_render(handle, BigInt(framePtr),
    FRAME_CAPACITY, 0n, 912n, 684n);
  assert.ok(length > 0n, `Mr. Time render succeeds (${length})`);
  return decode(new Uint8Array(instance.exports.memory.buffer, framePtr,
    Number(length)).slice());
}

function texts(handle) {
  return frame(handle).filter(({ kind }) => kind === Kind.TEXT)
    .map(({ text: value }) => value);
}

function markCenter(handle) {
  const commands = frame(handle);
  const arc = commands.find(({ kind }) => kind === Kind.ARC);
  if (arc) return [arc.a, arc.b];
  const start = commands.findIndex(({ kind }) => kind === Kind.MULTILINE);
  assert.ok(start >= 0, "a visible produce trial has an outline");
  // begin_multiline stores the first point in the header and repeats it as
  // the first POLY_POINT, so skip that duplicate before finding the centre.
  const points = [commands[start], ...commands.slice(start + 2)
    .filter(({ kind }) => kind === Kind.POLY_POINT)];
  return [
    points.reduce((total, point) => total + point.a, 0) / points.length,
    points.reduce((total, point) => total + point.b, 0) / points.length,
  ];
}

assert.equal(Number(exports.nw_api_v1_abi_version()), 1);
assert.equal(Number(exports.nw_api_v1_supports(TASK)), 1);
assert.equal(create([0n, 0n, 5n, 3000n, 400n, 1n]), STATUS.badOptions,
  "rung zero is rejected");
assert.equal(create([0n, 1n, 4n, 3000n, 400n, 1n]), STATUS.badOptions,
  "trial counts retain the source option set");
assert.equal(create([0n, 1n, 5n, 300n, 400n, 1n]), STATUS.badOptions,
  "maximum gaps retain the source option set");
assert.equal(create([0n, 1n, 5n, 3000n, 50n, 1n]), STATUS.badOptions,
  "flash durations retain the source option set");
assert.equal(create([0n, 1n, 5n, 3000n, 400n, 2n]), STATUS.badOptions,
  "adaptive is boolean");

// Recall: the visible flash ends, the hidden gap ends, the interval freezes at
// ASKING, and a decimal answer goes through the real source parser and scorer.
const recall = create([0n, 1n, 5n, 3000n, 400n, 1n], 17n);
assert.ok(recall > 0n);
assert.deepEqual(state(recall), [PHASE.ready, 1n, 0n, 5n, 0n, MODE.recall,
  0n, 0n, 0n, -1n, 0n, 1n]);
assert.equal(info(recall, INFO.mode), MODE.recall);
assert.equal(info(recall, INFO.startRung), 1n);
assert.equal(info(recall, INFO.maxGap), 3000n);
assert.equal(info(recall, INFO.flash), 400n);
assert.ok(texts(recall).includes("Mr. Time"));
assert.ok(texts(recall).includes("Press Space to start"));
assert.equal(action(recall, ACTION.submit, 999, 0), STATUS.ignored,
  "empty submission before START is ignored");

let sequence = 1;
assert.equal(action(recall, ACTION.start, 1000, sequence++), STATUS.accepted);
let values = state(recall);
assert.equal(values[FIELD.phase], PHASE.showing);
assert.equal(values[FIELD.trial], 1n);
assert.equal(values[FIELD.trialMode], MODE.recall);
assert.equal(info(recall, INFO.appearedAt), 1000n);
assert.ok(info(recall, INFO.askAt) > 1400n);
assert.ok(frame(recall).some(({ kind }) => kind === Kind.ARC || kind === Kind.MULTILINE),
  "the recall shape is rendered during its flash");

assert.equal(advance(recall, 1399, sequence++), STATUS.ignored);
assert.equal(advance(recall, 1401, sequence++), STATUS.accepted);
values = state(recall);
assert.ok(values[FIELD.phase] === PHASE.waiting || values[FIELD.phase] === PHASE.asking);
if (values[FIELD.phase] === PHASE.waiting) {
  assert.equal(advance(recall, Number(info(recall, INFO.askAt)) + 1, sequence++),
    STATUS.accepted);
}
values = state(recall);
assert.equal(values[FIELD.phase], PHASE.asking);
const intervalMs = Number(values[FIELD.intervalMs]);
assert.ok(intervalMs >= 400);
const answerText = (intervalMs / 1000).toFixed(3);
for (const character of answerText) {
  assert.equal(text(recall, character, Number(info(recall, INFO.askAt)) + 2, sequence++),
    STATUS.accepted, `text input ${character}`);
}
const beforeBackspace = state(recall)[FIELD.answerCount];
assert.equal(action(recall, ACTION.backspace, Number(info(recall, INFO.askAt)) + 3,
  sequence++), STATUS.accepted);
assert.equal(state(recall)[FIELD.answerCount], beforeBackspace - 1n);
const lastCharacter = answerText.at(-1);
assert.equal(text(recall, lastCharacter, Number(info(recall, INFO.askAt)) + 4, sequence++),
  STATUS.accepted);
assert.equal(action(recall, ACTION.submit, Number(info(recall, INFO.askAt)) + 5,
  sequence++), STATUS.accepted);
values = state(recall);
assert.equal(values[FIELD.phase], PHASE.feedback);
assert.equal(values[FIELD.resultCount], 1n);
assert.equal(values[FIELD.correct], 1n,
  "a millisecond-rounded answer remains inside the rung-one band");
assert.equal(values[FIELD.verdict], 1n);
assert.ok(info(recall, INFO.feedbackUntil) > 0n);
assert.equal(advance(recall, Number(info(recall, INFO.feedbackUntil)) + 1, sequence++),
  STATUS.accepted);
assert.equal(state(recall)[FIELD.phase], PHASE.showing,
  "feedback expiry deals the next recall trial");
assert.ok(texts(recall).some((value) => value.includes("right 1")));
assert.equal(exports.nw_api_v1_destroy(recall), 0n);
assert.equal(exports.nw_api_v1_destroy(recall), 0n,
  "destroy remains idempotent");

// Produce: the same controller accepts the semantic ACT action at the exact
// target, and the browser-facing pointer route hits the shape's centre.
const produce = create([1n, 1n, 5n, 3000n, 400n, 0n], 4n);
assert.ok(produce > recall);
sequence = 0;
assert.equal(action(produce, ACTION.start, 5000, sequence++), STATUS.accepted);
values = state(produce);
assert.equal(values[FIELD.phase], PHASE.counting);
assert.equal(values[FIELD.trialMode], MODE.produce);
assert.ok(values[FIELD.targetMs] >= 300n);
assert.equal(values[FIELD.intervalMs], values[FIELD.targetMs]);
assert.ok(info(produce, INFO.deadline) > BigInt(values[FIELD.targetMs]));
assert.equal(action(produce, ACTION.act, 5000 + Number(values[FIELD.targetMs]), sequence++),
  STATUS.accepted);
values = state(produce);
assert.equal(values[FIELD.phase], PHASE.feedback);
assert.equal(values[FIELD.correct], 1n);
assert.equal(values[FIELD.verdict], 1n);
assert.ok(texts(produce).some((value) => value.includes("Exactly")));
assert.equal(exports.nw_api_v1_destroy(produce), 0n);

// Pointer coordinates are normalized by the common protocol. A centre hit
// must reach the same ACT transition as Space; an outside click is ignored.
const pointer = create([1n, 1n, 5n, 3000n, 400n, 0n], 9n);
sequence = 0;
assert.equal(action(pointer, ACTION.start, 7000, sequence++), STATUS.accepted);
const pointerTargetMs = Number(state(pointer)[FIELD.targetMs]);
const [centreX, centreY] = markCenter(pointer);
assert.equal(dispatch(pointer, EVENT.pointerDown, 7000 + pointerTargetMs, sequence++, 0n,
  0n, BigInt(Math.round(centreX * 1000000 / 912)),
  BigInt(Math.round(centreY * 1000000 / 684))), STATUS.accepted);
assert.equal(state(pointer)[FIELD.phase], PHASE.feedback);
assert.equal(state(pointer)[FIELD.correct], 1n);
assert.equal(exports.nw_api_v1_destroy(pointer), 0n);

// An unanswered produce trial settles as a miss at its bounded deadline, so
// a background tab or a forgotten run cannot remain in COUNTING forever.
const timeout = create([1n, 1n, 5n, 3000n, 400n, 0n], 13n);
sequence = 0;
assert.equal(action(timeout, ACTION.start, 9000, sequence++), STATUS.accepted);
const timeoutDeadline = Number(info(timeout, INFO.deadline));
assert.equal(advance(timeout, timeoutDeadline + 1, sequence++), STATUS.accepted);
values = state(timeout);
assert.equal(values[FIELD.phase], PHASE.feedback);
assert.equal(values[FIELD.resultCount], 1n);
assert.equal(values[FIELD.correct], 0n);
assert.equal(values[FIELD.verdict], 0n);
assert.ok(texts(timeout).some((value) => value.includes("Never answered")));
assert.equal(exports.nw_api_v1_destroy(timeout), 0n);

console.log("mrtime_game_smoke: PASS (common lifecycle, recall timing/input, produce timing, pointer hit, timeout, render, disposal)");
