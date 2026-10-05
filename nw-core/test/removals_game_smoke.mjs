// Common-v1 lifecycle smoke for the source-backed Removals controller.
// The round, answers, timing, and adaptive score all come from the Elisa
// controller; this test does not provide a browser-side answer table.
import assert from "node:assert/strict";
import fs from "node:fs";
import { fileURLToPath } from "node:url";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { decode, Kind } from "../shells/web/display-list.js";

const root = fileURLToPath(new URL("..", import.meta.url));
const wasm = process.env.NWCORE_WASM_PATH ?? `${root}/build/nwcore.wasm`;
const { exports, instance } = await instantiateElisa(fs.readFileSync(wasm), { warn: false });

const TASK = BigInt(exports.nw_api_v1_task_removals());
const STATUS = Object.freeze({ accepted: 1n, ignored: 2n, badOptions: -3n });
const EVENT = Object.freeze({ action: 1n, keyDown: 2n, pointerDown: 5n });
const KEY = Object.freeze({ space: 1n, one: 12n });
const ACTION = Object.freeze({ start: 0n, answer0: 1n });
const PHASE = Object.freeze({ ready: 0n, moving: 1n, asking: 2n,
  scored: 3n, done: 4n });
const INFO = Object.freeze({
  phase: 0, rung: 1, trial: 2, totalTrials: 3, vans: 4, boxes: 5,
  items: 6, moves: 7, cursor: 8, askingAt: 9, verdict: 10,
  deadlineMs: 11, asks: 13, right: 14, totalAsked: 15,
});
const VALUE = Object.freeze({ kind: 0n, thing: 1n, other: 2n,
  asked: 3n, answer: 4n, given: 5n });
const STATE_BYTES = 112;
const FRAME_BYTES = 1048576;
const STATE_BUFFER = Number(exports.nw_frame_alloc(BigInt(STATE_BYTES)));
const FRAME_BUFFER = Number(exports.nw_frame_alloc(BigInt(FRAME_BYTES)));
assert.ok(TASK > 0n && STATE_BUFFER > 0 && FRAME_BUFFER > 0);

function create(options = [1n, 1n, 500n, 0n, 0n, 0n], seed = 17n) {
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

function event(handle, kind, timestamp, sequence, code, value = 0n,
               x = 0n, y = 0n) {
  return exports.nw_api_v1_dispatch(handle, kind, BigInt(timestamp),
    BigInt(sequence), code, value, 0n, 0n, x, y, 0n);
}

function action(handle, code, timestamp, sequence) {
  return event(handle, EVENT.action, timestamp, sequence, code);
}

function info(handle, field) {
  return BigInt(exports.nw_api_v1_removals_info(handle, BigInt(field)));
}

function value(handle, field, at) {
  return BigInt(exports.nw_api_v1_removals_value(handle, field, BigInt(at)));
}

function advance(handle, timestamp, sequence) {
  return exports.nw_api_v1_advance(handle, BigInt(timestamp), 0n, BigInt(sequence));
}

function frame(handle) {
  const length = exports.nw_api_v1_render(handle, BigInt(FRAME_BUFFER),
    BigInt(FRAME_BYTES), 0n, 912n, 684n);
  assert.ok(length > 0n, `render failed: ${length}`);
  return new Uint8Array(instance.exports.memory.buffer, FRAME_BUFFER,
    Number(length)).slice();
}

assert.equal(TASK, 2704363772n, "Removals keeps its stable task ID");
assert.equal(Number(exports.nw_api_v1_supports(TASK)), 1);
assert.equal(create([0n, 1n, 500n, 0n, 0n, 0n]), STATUS.badOptions);
assert.equal(create([1n, 4n, 500n, 0n, 0n, 0n]), STATUS.badOptions);
assert.equal(create([1n, 1n, 700n, 0n, 0n, 0n]), STATUS.badOptions);
assert.equal(create([1n, 1n, 500n, 2n, 0n, 0n]), STATUS.badOptions);

const run = create();
const replay = create();
assert.ok(run > 0n && replay > 0n);
assert.deepEqual(state(run), [0n, 1n, 0n, 1n, 0n, 0n, 0n, 0n, 0n, 0n, -1n, 0n]);
const readyFrame = frame(run);
assert.deepEqual(frame(run), readyFrame, "ready rendering is observational");
assert.ok(decode(readyFrame).some(({ kind, text }) =>
  kind === Kind.TEXT && text === "Removals"));

assert.equal(event(run, EVENT.keyDown, 100, 0, KEY.space), STATUS.accepted);
assert.equal(action(replay, ACTION.start, 100, 0), STATUS.accepted);
assert.deepEqual(state(run), state(replay), "same seed gives the same round");
assert.equal(info(run, INFO.phase), PHASE.moving);
assert.equal(info(run, INFO.rung), 1n);
assert.equal(info(run, INFO.vans), 2n);
assert.equal(info(run, INFO.asks), 1n);
assert.equal(info(run, INFO.moves), 6n);
assert.equal(value(run, VALUE.kind, 0), 0n);
assert.ok(decode(frame(run)).some(({ kind, text }) =>
  kind === Kind.TEXT && text.includes("vans")));

// One timed callback advances exactly one source move.  A pre-deadline
// advance is accepted by the protocol but does not change the phase/cursor.
assert.equal(advance(run, 599, 1), STATUS.ignored);
assert.equal(info(run, INFO.cursor), 0n);
let sequence = 2;
let now = 600;
while (info(run, INFO.phase) === PHASE.moving) {
  assert.equal(advance(run, now, sequence), STATUS.accepted);
  sequence += 1;
  now += 500;
}
assert.equal(info(run, INFO.phase), PHASE.asking);
assert.equal(info(run, INFO.askingAt), 0n);
const answer = info(run, INFO.vans) > 0n ? value(run, VALUE.answer, 0) : -1n;
assert.ok(answer >= 0n && answer < info(run, INFO.vans));
assert.equal(action(run, ACTION.answer0 + answer, now, sequence), STATUS.accepted);
sequence += 1;
assert.equal(info(run, INFO.phase), PHASE.scored);
assert.equal(info(run, INFO.verdict), 1n);
assert.equal(info(run, INFO.right), 1n);
assert.equal(info(run, INFO.totalAsked), 1n);
assert.ok(decode(frame(run)).some(({ kind, text }) =>
  kind === Kind.TEXT && (text === "Right" || text.includes("All 1 right"))));

// Removals intentionally waits for Space after the verdict, matching the
// native UI.  Before the deadline it is ignored; at the boundary it completes
// the one-round run and exposes the source-shaped summary.
assert.equal(action(run, ACTION.start, now, sequence), STATUS.ignored);
sequence += 1;
assert.equal(action(run, ACTION.start, now + 800, sequence), STATUS.accepted);
assert.equal(info(run, INFO.phase), PHASE.done);
assert.ok(decode(frame(run)).some(({ kind, text }) =>
  kind === Kind.TEXT && text.includes("rounds")));

for (const handle of [run, replay]) {
  assert.equal(exports.nw_api_v1_destroy(handle), 0n);
  assert.equal(exports.nw_api_v1_destroy(handle), 0n, "destroy is idempotent");
}

console.log("PASS: Removals source-backed generation, timed walk, keyed answer, scoring, rendering, options, and cleanup");
