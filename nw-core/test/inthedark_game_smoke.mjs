// Common-v1 lifecycle smoke for the source-backed In the Dark controller.
// The room walk is advanced by its source deadline; all answers are read only
// by the test so the generated lifecycle can be exercised without a fixture.
import assert from "node:assert/strict";
import fs from "node:fs";
import { fileURLToPath } from "node:url";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { decode, Kind } from "../shells/web/display-list.js";

const root = fileURLToPath(new URL("..", import.meta.url));
const wasm = process.env.NWCORE_WASM_PATH ?? `${root}/build/nwcore.wasm`;
const { exports, instance } = await instantiateElisa(fs.readFileSync(wasm), { warn: false });

const TASK = BigInt(exports.nw_api_v1_task_in_the_dark());
const STATUS = Object.freeze({ accepted: 1n, ignored: 2n, badOptions: -3n });
const EVENT = Object.freeze({ action: 1n, keyDown: 2n });
const KEY = Object.freeze({ space: 1n, one: 12n, two: 13n, three: 14n, four: 15n, five: 16n });
const ACTION = Object.freeze({ start: 0n });
const PHASE = Object.freeze({ ready: 0n, walking: 1n, asking: 2n, scored: 3n, done: 4n });
const INFO = Object.freeze({
  phase: 0, rung: 1, trial: 2, totalTrials: 3, lamps: 4, colours: 5,
  cursor: 6, askingAt: 7, verdict: 8, adaptive: 9, right: 10, rooms: 11,
});
const STATE_BYTES = 112;
const FRAME_BYTES = 1048576;
const STATE_BUFFER = Number(exports.nw_frame_alloc(BigInt(STATE_BYTES)));
const FRAME_BUFFER = Number(exports.nw_frame_alloc(BigInt(FRAME_BYTES)));
assert.ok(TASK > 0n && STATE_BUFFER > 0 && FRAME_BUFFER > 0);

function create(options = [2n, 5n, 1200n, 1n, 0n, 0n], seed = 17n) {
  return exports.nw_api_v1_create(TASK, 1n, ...options, seed);
}

function state(handle) {
  const length = exports.nw_api_v1_read_state(handle,
    BigInt(STATE_BUFFER), BigInt(STATE_BYTES));
  assert.equal(length, BigInt(STATE_BYTES));
  const view = new DataView(instance.exports.memory.buffer, STATE_BUFFER, STATE_BYTES);
  assert.equal(view.getUint32(0, true), 0x3152574e);
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

function advance(handle, timestamp, sequence) {
  return exports.nw_api_v1_advance(handle, BigInt(timestamp), 0n,
    BigInt(sequence));
}

function info(handle, field) {
  return BigInt(exports.nw_api_v1_in_the_dark_info(handle, BigInt(field)));
}

function asked(handle, field, at) {
  return BigInt(exports.nw_api_v1_in_the_dark_asked(
    handle, BigInt(field), BigInt(at)));
}

function frame(handle) {
  const length = exports.nw_api_v1_render(handle, BigInt(FRAME_BUFFER),
    BigInt(FRAME_BYTES), 0n, 912n, 684n);
  assert.ok(length > 0n, `render failed: ${length}`);
  return new Uint8Array(instance.exports.memory.buffer, FRAME_BUFFER,
    Number(length)).slice();
}

function answerKey(value) {
  return KEY.one + BigInt(value);
}

function walkToQuestions(handle, timestamp, sequence) {
  let now = timestamp;
  let seq = sequence;
  while (info(handle, INFO.phase) === PHASE.walking) {
    const deadline = Number(info(handle, 18));
    assert.ok(deadline >= now);
    assert.equal(advance(handle, deadline, seq++), STATUS.accepted);
    now = deadline;
  }
  assert.equal(info(handle, INFO.phase), PHASE.asking);
  return { timestamp: now, sequence: seq };
}

assert.equal(TASK, 1343235803n, "In the Dark keeps its stable task ID");
assert.equal(Number(exports.nw_api_v1_supports(TASK)), 1);
assert.equal(create([0n, 5n, 1200n, 1n, 0n, 0n]), STATUS.badOptions);
assert.equal(create([2n, 4n, 1200n, 1n, 0n, 0n]), STATUS.badOptions);
assert.equal(create([2n, 5n, 700n, 1n, 0n, 0n]), STATUS.badOptions);
assert.equal(create([2n, 5n, 1200n, 2n, 0n, 0n]), STATUS.badOptions);

const run = create();
assert.ok(run > 0n);
assert.deepEqual(state(run), [0n, 2n, 0n, 5n, 0n, 0n, 0n, 0n, -1n, 1n, 0n, 0n]);
const readyFrame = frame(run);
assert.deepEqual(frame(run), readyFrame, "ready rendering is observational");
assert.ok(decode(readyFrame).some(({ kind, text }) =>
  kind === Kind.TEXT && text === "In the Dark"));

assert.equal(event(run, EVENT.keyDown, 100, 0, KEY.space, 32n), STATUS.accepted);
assert.equal(info(run, INFO.phase), PHASE.walking);
assert.equal(info(run, INFO.trial), 1n);
assert.ok(info(run, INFO.rooms) >= 6n);
assert.ok(info(run, INFO.lamps) >= 2n && info(run, INFO.colours) >= 2n);
const walkingFrame = frame(run);
assert.deepEqual(frame(run), walkingFrame, "room rendering is observational");
let cursor = walkToQuestions(run, 100, 1);
assert.equal(info(run, INFO.phase), PHASE.asking);
assert.ok(info(run, INFO.askingAt) === 0n);

const askCount = Number(info(run, 22));
assert.ok(askCount >= 2 && askCount <= 6);
for (let at = 0; at < askCount; at++) {
  const answer = asked(run, 1, at);
  assert.ok(answer >= 0n && answer < info(run, INFO.colours));
  assert.equal(event(run, EVENT.keyDown, cursor.timestamp + 1 + at,
    cursor.sequence + at, answerKey(answer), 0n), STATUS.accepted);
}
cursor = { timestamp: cursor.timestamp + askCount, sequence: cursor.sequence + askCount };
assert.equal(info(run, INFO.phase), PHASE.scored);
assert.equal(info(run, INFO.verdict), 1n);
assert.equal(info(run, INFO.right), BigInt(askCount));
assert.ok(decode(frame(run)).some(({ kind, text }) =>
  kind === Kind.TEXT && text.includes("right")));

// The source waits 0.8 seconds before accepting Space for the next round.
assert.equal(event(run, EVENT.keyDown, cursor.timestamp + 1,
  cursor.sequence, KEY.space, 32n), STATUS.ignored);
const feedbackDeadline = Number(info(run, 18));
assert.equal(advance(run, feedbackDeadline, cursor.sequence + 1), STATUS.accepted);
assert.equal(event(run, EVENT.keyDown, feedbackDeadline + 1,
  cursor.sequence + 2, KEY.space, 32n), STATUS.accepted);
assert.equal(info(run, INFO.phase), PHASE.walking);
assert.equal(info(run, INFO.trial), 2n);
assert.equal(exports.nw_api_v1_destroy(run), 0n);
assert.equal(exports.nw_api_v1_destroy(run), 0n, "destroy is idempotent");

// A wrong round still records every asked question, enters scored feedback,
// and drops an adaptive rung when fewer than half are right.
const wrong = create([2n, 1n, 500n, 1n, 0n, 0n], 41n);
assert.equal(action(wrong, ACTION.start, 1, 0), STATUS.accepted);
let wrongCursor = walkToQuestions(wrong, 1, 1);
const wrongCount = Number(info(wrong, 22));
for (let at = 0; at < wrongCount; at++) {
  const answer = asked(wrong, 1, at);
  const wrongColour = answer === 0n ? 1n : 0n;
  assert.equal(event(wrong, EVENT.keyDown, wrongCursor.timestamp + 1 + at,
    wrongCursor.sequence + at, answerKey(wrongColour), 0n), STATUS.accepted);
}
assert.equal(info(wrong, INFO.phase), PHASE.scored);
assert.equal(info(wrong, INFO.verdict), 0n);
assert.equal(info(wrong, INFO.rung), 1n, "adaptive failure drops one rung");
assert.equal(exports.nw_api_v1_destroy(wrong), 0n);

// Exercise low, middle, and top source grades so the controller never falls
// back to a canned room list at a different rung.
for (const level of [1, 6, 12]) {
  const family = create([BigInt(level), 1n, 500n, 0n, 0n, 0n], BigInt(level + 80));
  assert.ok(family > 0n);
  assert.equal(action(family, ACTION.start, 10, 0), STATUS.accepted);
  assert.equal(info(family, INFO.phase), PHASE.walking);
  assert.ok(info(family, INFO.rooms) > 0n);
  assert.ok(frame(family).length > 0);
  assert.equal(exports.nw_api_v1_destroy(family), 0n);
}

console.log("PASS: In the Dark source-backed timed rooms, all-question grading, adaptive feedback, rendering, and cleanup");
