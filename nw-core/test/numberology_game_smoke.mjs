// Common-v1 lifecycle smoke for the source-backed Numberology controller.
// The answer is inspected only to make the test able to exercise both wrong
// and correct submissions; the browser never reads it for presentation.
import assert from "node:assert/strict";
import fs from "node:fs";
import { fileURLToPath } from "node:url";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { decode, Kind } from "../shells/web/display-list.js";

const root = fileURLToPath(new URL("..", import.meta.url));
const wasm = process.env.NWCORE_WASM_PATH ?? `${root}/build/nwcore.wasm`;
const { exports, instance } = await instantiateElisa(fs.readFileSync(wasm), { warn: false });

const TASK = BigInt(exports.nw_api_v1_task_numberology());
const STATUS = Object.freeze({ accepted: 1n, ignored: 2n, badOptions: -3n });
const EVENT = Object.freeze({ action: 1n, keyDown: 2n, text: 8n });
const KEY = Object.freeze({ space: 1n, enter: 2n, undo: 8n });
const ACTION = Object.freeze({ start: 0n, write: 1n, backspace: 2n, submit: 3n });
const PHASE = Object.freeze({ ready: 0n, working: 1n, judged: 2n, done: 3n });
const INFO = Object.freeze({ phase: 0, level: 1, trial: 2, trials: 3, shown: 4,
  answer: 5, typedValue: 6, typedLength: 7, verdict: 8, adaptive: 9,
  right: 10, complexity: 11 });
const STATE_BYTES = 112;
const FRAME_BYTES = 1048576;
const STATE_BUFFER = Number(exports.nw_frame_alloc(BigInt(STATE_BYTES)));
const FRAME_BUFFER = Number(exports.nw_frame_alloc(BigInt(FRAME_BYTES)));
assert.ok(TASK > 0n && STATE_BUFFER > 0 && FRAME_BUFFER > 0);

function create(options = [1n, 6n, 1n, 0n, 0n, 0n], seed = 17n) {
  return exports.nw_api_v1_create(TASK, 1n, ...options, seed);
}

function state(handle) {
  const length = exports.nw_api_v1_read_state(handle,
    BigInt(STATE_BUFFER), BigInt(STATE_BYTES));
  assert.equal(length, BigInt(STATE_BYTES));
  const view = new DataView(instance.exports.memory.buffer, STATE_BUFFER, STATE_BYTES);
  assert.equal(view.getUint32(0, true), 0x3152574e);
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

function frame(handle) {
  const length = exports.nw_api_v1_render(handle, BigInt(FRAME_BUFFER),
    BigInt(FRAME_BYTES), 0n, 912n, 684n);
  assert.ok(length > 0n, `render failed: ${length}`);
  return new Uint8Array(instance.exports.memory.buffer, FRAME_BUFFER,
    Number(length)).slice();
}

function writeAnswer(handle, answer, sequence, timestamp) {
  const text = String(answer);
  for (const character of text) {
    assert.equal(event(handle, EVENT.text, timestamp++, sequence++, 0n,
      BigInt(character.codePointAt(0))), STATUS.accepted);
  }
  return { sequence, timestamp };
}

assert.equal(TASK, 1263422208n, "Numberology keeps its stable task ID");
assert.equal(Number(exports.nw_api_v1_supports(TASK)), 1);
assert.equal(create([0n, 6n, 1n, 0n, 0n, 0n]), STATUS.badOptions);
assert.equal(create([1n, 4n, 1n, 0n, 0n, 0n]), STATUS.badOptions);
assert.equal(create([1n, 6n, 2n, 0n, 0n, 0n]), STATUS.badOptions);

const run = create();
assert.ok(run > 0n);
assert.deepEqual(state(run), [0n, 1n, 0n, 6n, 0n, -1n, 0n, 0n, -1n, 1n, 0n, 0n]);
const readyFrame = frame(run);
assert.deepEqual(frame(run), readyFrame, "ready rendering is observational");
assert.ok(decode(readyFrame).some(({ kind, text }) =>
  kind === Kind.TEXT && text === "Numberology"));

assert.equal(event(run, EVENT.keyDown, 1000, 0, KEY.space, 32n), STATUS.accepted);
let values = state(run);
assert.equal(values[INFO.phase], PHASE.working);
assert.equal(values[INFO.trial], 1n);
assert.ok(values[INFO.shown] >= 4n);
assert.ok(values[INFO.complexity] > 0n);
for (let index = 0; index < Number(values[INFO.shown]); index++) {
  assert.notEqual(exports.nw_api_v1_numberology_term(run, BigInt(index)), -1n);
}
const workingFrame = frame(run);
assert.deepEqual(frame(run), workingFrame, "working rendering does not mutate state");
assert.ok(decode(workingFrame).some(({ kind, text }) =>
  kind === Kind.TEXT && text.includes("?")));

// Invalid/empty submission is ignored, while a complete wrong answer enters
// the source's judged state and reveals the generated rule/result.
assert.equal(action(run, ACTION.submit, 1001, 1), STATUS.ignored);
const wrong = values[INFO.answer] === 0n ? 1n : 0n;
let cursor = writeAnswer(run, wrong, 2, 1002);
assert.equal(event(run, EVENT.keyDown, cursor.timestamp, cursor.sequence,
  KEY.enter, 13n), STATUS.accepted);
values = state(run);
assert.equal(values[INFO.phase], PHASE.judged);
assert.equal(values[INFO.verdict], 0n);
assert.ok(decode(frame(run)).some(({ kind, text }) =>
  kind === Kind.TEXT && text.includes("No")));

// Space advances to the next generated question. Backspace owns the typed
// buffer in the controller, not in the browser.
cursor = { timestamp: cursor.timestamp + 1, sequence: cursor.sequence + 1 };
assert.equal(event(run, EVENT.keyDown, cursor.timestamp, cursor.sequence,
  KEY.space, 32n), STATUS.accepted);
values = state(run);
assert.equal(values[INFO.phase], PHASE.working);
assert.equal(values[INFO.trial], 2n);
assert.equal(event(run, EVENT.text, cursor.timestamp + 1, cursor.sequence + 1,
  0n, 49n), STATUS.accepted);
assert.equal(action(run, ACTION.backspace, cursor.timestamp + 2, cursor.sequence + 2), STATUS.accepted);
assert.equal(state(run)[INFO.typedLength], 0n);
assert.equal(exports.nw_api_v1_destroy(run), 0n);
assert.equal(exports.nw_api_v1_destroy(run), 0n);

// A one-question perfect session advances the persisted starting level when
// the source option is enabled, and the next session begins at that level.
const perfect = create([1n, 1n, 1n, 0n, 0n, 0n], 23n);
assert.equal(action(perfect, ACTION.start, 1, 0), STATUS.accepted);
values = state(perfect);
cursor = writeAnswer(perfect, values[INFO.answer], 1, 2);
assert.equal(event(perfect, EVENT.keyDown, cursor.timestamp, cursor.sequence,
  KEY.enter, 13n), STATUS.accepted);
assert.equal(state(perfect)[INFO.verdict], 1n);
assert.equal(event(perfect, EVENT.keyDown, cursor.timestamp + 1, cursor.sequence + 1,
  KEY.space, 32n), STATUS.accepted);
assert.equal(state(perfect)[INFO.phase], PHASE.done);
assert.equal(state(perfect)[INFO.level], 1n);
assert.equal(state(perfect)[INFO.right], 1n);
assert.equal(exports.nw_api_v1_numberology_info(perfect, 13n), 2n);
assert.equal(action(perfect, ACTION.start, cursor.timestamp + 2, cursor.sequence + 2), STATUS.accepted);
assert.equal(state(perfect)[INFO.level], 2n);
assert.equal(exports.nw_api_v1_destroy(perfect), 0n);

// All six source rule families must remain generative and renderable.
for (let level = 1; level <= 7; level++) {
  const family = create([BigInt(level), 1n, 0n, 0n, 0n, 0n], BigInt(level + 30));
  assert.ok(family > 0n);
  assert.equal(action(family, ACTION.start, 10, 0), STATUS.accepted);
  const generated = state(family);
  assert.equal(generated[INFO.phase], PHASE.working);
  assert.ok(generated[INFO.shown] >= 4n);
  assert.ok(generated[INFO.complexity] > 0n);
  assert.ok(frame(family).length > 0);
  assert.equal(exports.nw_api_v1_destroy(family), 0n);
}

console.log("PASS: Numberology source-backed generator, typed lifecycle, grading, explanation, adaptive session, render, and cleanup");
