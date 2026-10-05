// Common-v1 lifecycle smoke for the source-backed Trivia controller.
// The question corpus, distractor selection, answer index, and adaptive rung
// all remain authoritative in Elisa; this test only drives the public ABI.
import assert from "node:assert/strict";
import fs from "node:fs";
import { fileURLToPath } from "node:url";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { decode, Kind } from "../shells/web/display-list.js";

const root = fileURLToPath(new URL("..", import.meta.url));
const wasm = process.env.NWCORE_WASM_PATH ?? `${root}/build/nwcore.wasm`;
const { exports, instance } = await instantiateElisa(fs.readFileSync(wasm), { warn: false });

const TASK = BigInt(exports.nw_api_v1_task_trivia());
const STATUS = Object.freeze({ accepted: 1n, ignored: 2n, badOptions: -3n });
const EVENT = Object.freeze({ action: 1n, keyDown: 2n });
const KEY = Object.freeze({ space: 1n, enter: 2n, down: 6n, one: 12n });
const ACTION = Object.freeze({ start: 0n, up: 1n, down: 2n, submit: 3n,
  choose0: 4n, advance: 12n });
const PHASE = Object.freeze({ ready: 0n, asking: 1n, judged: 2n, done: 3n });
const INFO = Object.freeze({
  phase: 0, startRung: 1, rung: 2, trial: 3, totalTrials: 4,
  optionCount: 5, choice: 6, answered: 7, answer: 8, lastRight: 9,
  right: 10, asked: 11, pool: 12, adaptive: 13, showAnswer: 14,
  dealQuestion: 15, dealSeed: 16,
});
const VALUE = Object.freeze({ optionQuestion: 0n, optionAnswer: 1n, optionId: 2n });
const STATE_BYTES = 112;
const FRAME_BYTES = 1048576;
const STATE_BUFFER = Number(exports.nw_frame_alloc(BigInt(STATE_BYTES)));
const FRAME_BUFFER = Number(exports.nw_frame_alloc(BigInt(FRAME_BYTES)));
assert.ok(STATE_BUFFER > 0 && FRAME_BUFFER > 0);

function create(options = [3n, 2n, 1n, 1n, 0n, 0n], seed = 17n) {
  return exports.nw_api_v1_create(TASK, 1n, ...options, seed);
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

function event(handle, kind, timestamp, sequence, code, value = 0n) {
  return exports.nw_api_v1_dispatch(handle, kind, BigInt(timestamp),
    BigInt(sequence), code, value, 0n, 0n, 0n, 0n, 0n);
}

function action(handle, code, timestamp, sequence, value = 0n) {
  return event(handle, EVENT.action, timestamp, sequence, code, value);
}

function keyDown(handle, key, timestamp, sequence) {
  return event(handle, EVENT.keyDown, timestamp, sequence, key);
}

function info(handle, field) {
  return BigInt(exports.nw_api_v1_trivia_info(handle, BigInt(field)));
}

function value(handle, field, at) {
  return BigInt(exports.nw_api_v1_trivia_value(handle, field, BigInt(at)));
}

function frame(handle) {
  const length = exports.nw_api_v1_render(handle, BigInt(FRAME_BUFFER),
    BigInt(FRAME_BYTES), 0n, 912n, 684n);
  assert.ok(length > 0n, `render failed: ${length}`);
  return new Uint8Array(instance.exports.memory.buffer, FRAME_BUFFER,
    Number(length)).slice();
}

assert.equal(TASK, 200484614n, "Trivia keeps its stable task ID");
assert.equal(Number(exports.nw_api_v1_supports(TASK)), 1);
assert.equal(create([0n, 2n, 1n, 1n, 0n, 0n]), STATUS.badOptions);
assert.equal(create([3n, 4n, 1n, 1n, 0n, 0n]), STATUS.badOptions);
assert.equal(create([3n, 2n, 2n, 1n, 0n, 0n]), STATUS.badOptions);
assert.equal(create([3n, 2n, 1n, 2n, 0n, 0n]), STATUS.badOptions);

const run = create();
const replay = create(undefined, 17n);
assert.ok(run > 0n && replay > 0n);
assert.deepEqual(state(run), [0n, 3n, 0n, 2n, 0n, 0n, -1n, -1n, -1n, 0n, 1n, 1n]);
assert.equal(info(run, INFO.pool), 120n);
const readyFrame = frame(run);
assert.deepEqual(frame(run), readyFrame, "ready rendering is observational");
assert.ok(decode(readyFrame).some(({ kind, text }) =>
  kind === Kind.TEXT && text === "Trivia"));

assert.equal(keyDown(run, KEY.space, 100, 0), STATUS.accepted);
assert.equal(action(replay, ACTION.start, 100, 0), STATUS.accepted);
assert.deepEqual(state(run), state(replay), "same seed gives the same first deal");
assert.equal(info(run, INFO.phase), PHASE.asking);
assert.equal(info(run, INFO.optionCount), 4n);
assert.ok(info(run, INFO.asked) >= 0n);
assert.equal(info(run, INFO.dealQuestion), info(run, INFO.asked));
assert.ok(info(run, INFO.dealSeed) >= 0n);
const ids = [];
for (let at = 0; at < Number(info(run, INFO.optionCount)); at += 1) {
  ids.push(value(run, VALUE.optionId, at));
  assert.equal(value(run, VALUE.optionQuestion, at), info(run, INFO.asked));
  assert.ok(value(run, VALUE.optionId, at) >= 0n);
}
assert.equal(new Set(ids.map(String)).size, ids.length, "options are distinct");
assert.equal(ids.filter((_, at) => value(run, VALUE.optionAnswer, at) === 1n).length, 1);
const expectedAnswer = ids.findIndex((_, at) =>
  value(run, VALUE.optionAnswer, at) === 1n);
assert.equal(info(run, INFO.answer), BigInt(expectedAnswer));

const askingFrame = frame(run);
assert.deepEqual(frame(replay), askingFrame, "same deal renders identically");
const askingText = decode(askingFrame).filter(({ kind }) => kind === Kind.TEXT);
assert.ok(askingText.length >= 5, "question and options are rendered");

const answer = info(run, INFO.answer);
assert.ok(answer >= 0n && answer < info(run, INFO.optionCount));
assert.equal(action(run, ACTION.choose0 + answer, 101, 1), STATUS.accepted);
assert.equal(info(run, INFO.phase), PHASE.judged);
assert.equal(info(run, INFO.lastRight), 1n);
assert.equal(info(run, INFO.right), 1n);
assert.equal(info(run, INFO.rung), 4n, "adaptive correct answer promotes the rung");
assert.ok(decode(frame(run)).some(({ kind, text }) =>
  kind === Kind.TEXT && text === "Right"));

assert.equal(keyDown(run, KEY.space, 102, 2), STATUS.accepted);
assert.equal(info(run, INFO.phase), PHASE.asking);
assert.equal(info(run, INFO.trial), 2n);
assert.equal(info(run, INFO.optionCount), 4n);

// Arrow selection and a deliberately wrong answer exercise the same source
// input path used by the browser for the second question.
assert.equal(keyDown(run, KEY.down, 103, 3), STATUS.accepted);
assert.equal(info(run, INFO.choice), 1n);
const secondAnswer = info(run, INFO.answer);
const wrong = secondAnswer === 0n ? 1n : 0n;
assert.equal(action(run, ACTION.choose0 + wrong, 104, 4), STATUS.accepted);
assert.equal(info(run, INFO.phase), PHASE.judged);
assert.equal(info(run, INFO.lastRight), 0n);
assert.equal(info(run, INFO.right), 1n);
assert.ok(decode(frame(run)).some(({ kind, text }) =>
  kind === Kind.TEXT && text === "No"));

const replayAnswer = info(replay, INFO.answer);
assert.equal(action(replay, ACTION.choose0 + replayAnswer, 101, 1), STATUS.accepted);
assert.equal(action(replay, ACTION.advance, 102, 2), STATUS.accepted);
assert.equal(info(replay, INFO.phase), PHASE.asking);
assert.equal(info(replay, INFO.trial), 2n);
assert.equal(info(replay, INFO.asked), info(run, INFO.asked),
  "replay remains aligned before its second answer");

for (const handle of [run, replay]) {
  assert.equal(exports.nw_api_v1_destroy(handle), 0n);
  assert.equal(exports.nw_api_v1_destroy(handle), 0n, "destroy is idempotent");
}

console.log("PASS: Trivia source-backed corpus, distractors, keyboard actions, adaptive scoring, rendering, replay, and cleanup");
