// Common-v1 lifecycle smoke for source-backed Lookout.
// The controller owns the flock, cue dealer, morph clock, signal-detection
// scoring, adaptive count, and feedback transition; the host supplies only
// monotonic time and the two source answer actions.
import assert from "node:assert/strict";
import fs from "node:fs";
import { fileURLToPath } from "node:url";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { decode, Kind } from "../shells/web/display-list.js";

const root = fileURLToPath(new URL("..", import.meta.url));
const wasm = process.env.NWCORE_WASM_PATH ?? `${root}/build/nwcore.wasm`;
const { exports, instance } = await instantiateElisa(fs.readFileSync(wasm), { warn: false });

const TASK = BigInt(exports.nw_api_v1_task_lookout());
const STATUS = Object.freeze({ accepted: 1n, ignored: 2n, badOptions: -3n });
const EVENT = Object.freeze({ action: 1n, keyDown: 2n });
const KEY = Object.freeze({ space: 1n, enter: 2n });
const ACTION = Object.freeze({ start: 0n, color: 1n, form: 2n });
const PHASE = Object.freeze({ ready: 0n, watching: 1n, feedback: 2n, done: 3n });
const INFO = Object.freeze({
  phase: 0, watching: 1, startCount: 2, count: 3, speed: 4,
  morphMs: 5, totalCues: 6, adaptive: 7, cueNumber: 8, cueColor: 9,
  cueForm: 10, hits: 11, misses: 12, falseAlarms: 13,
  reactionCount: 14, meanMs: 15, verdict: 16, clockMs: 17,
  untilMs: 18, lastReactionMs: 19, shapeCount: 20,
});
const VALUE = Object.freeze({ x: 0n, y: 1n, vx: 2n, vy: 3n, color: 4n,
  form: 5n, nextMorphMs: 6n });
const STATE_BYTES = 112;
const FRAME_BYTES = 1048576;
const STATE_BUFFER = Number(exports.nw_frame_alloc(BigInt(STATE_BYTES)));
const FRAME_BUFFER = Number(exports.nw_frame_alloc(BigInt(FRAME_BYTES)));
assert.ok(TASK > 0n && STATE_BUFFER > 0 && FRAME_BUFFER > 0);

function create(options = [8n, 0n, 16n, 2000n, 10n, 1n], seed = 17n) {
  return exports.nw_api_v1_create(TASK, 1n, ...options, seed);
}

function event(handle, kind, timestamp, sequence, code) {
  return exports.nw_api_v1_dispatch(handle, kind, BigInt(timestamp),
    BigInt(sequence), code, 0n, 0n, 0n, 0n, 0n, 0n);
}

function keyDown(handle, key, timestamp, sequence) {
  return event(handle, EVENT.keyDown, timestamp, sequence, key);
}

function action(handle, code, timestamp, sequence) {
  return event(handle, EVENT.action, timestamp, sequence, code);
}

function advance(handle, timestamp, sequence) {
  return exports.nw_api_v1_advance(handle, BigInt(timestamp), 0n,
    BigInt(sequence));
}

function info(handle, field) {
  return BigInt(exports.nw_api_v1_lookout_info(handle, BigInt(field)));
}

function value(handle, field, at) {
  return BigInt(exports.nw_api_v1_lookout_value(handle, field, BigInt(at)));
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

function frame(handle) {
  const length = exports.nw_api_v1_render(handle, BigInt(FRAME_BUFFER),
    BigInt(FRAME_BYTES), 0n, 912n, 684n);
  assert.ok(length > 0n, `render failed: ${length}`);
  return new Uint8Array(instance.exports.memory.buffer, FRAME_BUFFER,
    Number(length)).slice();
}

function textIn(frameBytes, expected) {
  return decode(frameBytes).some(({ kind, text }) =>
    kind === Kind.TEXT && text.includes(expected));
}

function snapshot(handle) {
  return [
    ...Array.from({ length: 21 }, (_, field) => info(handle, field)),
    ...Array.from({ length: 8 }, (_, at) => value(handle, VALUE.x, at)),
    ...Array.from({ length: 8 }, (_, at) => value(handle, VALUE.y, at)),
    ...Array.from({ length: 8 }, (_, at) => value(handle, VALUE.color, at)),
    ...Array.from({ length: 8 }, (_, at) => value(handle, VALUE.form, at)),
  ];
}

assert.equal(TASK, 3096915418n, "Lookout keeps its stable task ID");
assert.equal(Number(exports.nw_api_v1_supports(TASK)), 1);
assert.equal(create([2n, 0n, 16n, 2000n, 10n, 1n]), STATUS.badOptions);
assert.equal(create([8n, 3n, 16n, 2000n, 10n, 1n]), STATUS.badOptions);
assert.equal(create([8n, 0n, 7n, 2000n, 10n, 1n]), STATUS.badOptions);
assert.equal(create([8n, 0n, 16n, 700n, 10n, 1n]), STATUS.badOptions);
assert.equal(create([8n, 0n, 16n, 2000n, 4n, 1n]), STATUS.badOptions);
assert.equal(create([8n, 0n, 16n, 2000n, 10n, 2n]), STATUS.badOptions);

const run = create();
const replay = create();
assert.ok(run > 0n && replay > 0n);
assert.deepEqual(state(run), [0n, 0n, 10n, 0n, 0n, 0n, 0n, 0n,
  0n, -1n, 0n, 0n]);
const readyFrame = frame(run);
assert.deepEqual(frame(run), readyFrame, "ready rendering is observational");
assert.ok(textIn(readyFrame, "Lookout"));
assert.ok(textIn(readyFrame, "Press Space to start"));

// Space and the explicit source action must produce the same seeded flock and
// cue. This also proves that the common state envelope maps the controller's
// source fields consistently for the browser shell.
assert.equal(keyDown(run, KEY.space, 0, 0), STATUS.accepted);
assert.equal(action(replay, ACTION.start, 0, 0), STATUS.accepted);
assert.deepEqual(snapshot(run), snapshot(replay));
assert.equal(info(run, INFO.phase), PHASE.watching);
assert.equal(info(run, INFO.cueNumber), 1n);
assert.equal(info(run, INFO.count), 8n);
assert.equal(info(run, INFO.cueColor), 3n);
assert.equal(info(run, INFO.cueForm), 3n);
assert.equal(info(run, INFO.clockMs), 0n);
assert.ok(textIn(frame(run), "cue 1/10"));

// The absent-cue dealer clears the live colour channel before a cue starts.
for (let at = 0; at < 8; at += 1) {
  assert.notEqual(value(run, VALUE.color, at), info(run, INFO.cueColor));
}

// A match appears during normal motion. Waiting 150 ms before answering makes
// the reaction-time copy boundary observable: the source clears its seen
// marker while entering feedback, so the adapter must capture the time first.
assert.equal(advance(run, 900, 1), STATUS.accepted);
assert.equal(advance(replay, 900, 1), STATUS.accepted);
assert.deepEqual(snapshot(run), snapshot(replay));
assert.equal(action(run, ACTION.color, 1050, 2), STATUS.accepted);
assert.equal(action(replay, ACTION.color, 1050, 2), STATUS.accepted);
assert.equal(info(run, INFO.phase), PHASE.feedback);
assert.equal(info(run, INFO.hits), 1n);
assert.equal(info(run, INFO.misses), 0n);
assert.equal(info(run, INFO.falseAlarms), 0n);
assert.equal(info(run, INFO.reactionCount), 1n);
assert.equal(info(run, INFO.lastReactionMs), 150n);
assert.equal(info(run, INFO.meanMs), 150n);
assert.equal(info(run, INFO.count), 9n, "adaptive hit raises the flock count");
assert.deepEqual(snapshot(run), snapshot(replay));
assert.ok(textIn(frame(run), "Hit"));
assert.ok(textIn(frame(run), "150 ms"));

assert.equal(advance(run, 2449, 3), STATUS.accepted);
assert.equal(advance(run, 2450, 4), STATUS.accepted);
assert.equal(info(run, INFO.phase), PHASE.watching);
assert.equal(info(run, INFO.cueNumber), 2n);
assert.equal(info(run, INFO.count), 9n);

// A press before the signal is seen is a false alarm, not a generic success.
const falseAlarm = create([8n, 0n, 16n, 2000n, 10n, 0n], 17n);
assert.equal(action(falseAlarm, ACTION.start, 0, 0), STATUS.accepted);
assert.equal(action(falseAlarm, ACTION.color, 1, 1), STATUS.accepted);
assert.equal(info(falseAlarm, INFO.phase), PHASE.feedback);
assert.equal(info(falseAlarm, INFO.hits), 0n);
assert.equal(info(falseAlarm, INFO.falseAlarms), 1n);
assert.equal(info(falseAlarm, INFO.verdict), 0n);
assert.ok(textIn(frame(falseAlarm), "No"));

// Leaving a live match unanswered eventually records a miss. The source's
// drought-forcing rule makes this bounded even for a rare initial cue.
const missRun = create([3n, 0n, 16n, 800n, 5n, 0n], 23n);
assert.equal(action(missRun, ACTION.start, 0, 0), STATUS.accepted);
let missSequence = 1;
let missNow = 50;
while (info(missRun, INFO.phase) === PHASE.watching && missNow <= 20000) {
  advance(missRun, missNow, missSequence++);
  missNow += 50;
}
assert.equal(info(missRun, INFO.phase), PHASE.feedback);
assert.equal(info(missRun, INFO.misses), 1n);
assert.equal(info(missRun, INFO.verdict), 0n);
assert.ok(textIn(frame(missRun), "slipped"));

for (const handle of [run, replay, falseAlarm, missRun]) {
  assert.equal(exports.nw_api_v1_destroy(handle), 0n);
  assert.equal(exports.nw_api_v1_destroy(handle), 0n, "destroy is idempotent");
}

console.log("PASS: Lookout source-backed flock, cue absence, morph clock, signal scoring, reaction timing, rendering, options, and cleanup");
