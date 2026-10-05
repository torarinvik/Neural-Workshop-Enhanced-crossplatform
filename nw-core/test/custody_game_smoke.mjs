// Common-v1 lifecycle smoke for the source-backed Chain of Custody controller.
// The layout, box identities, belt transitions, and score all come from the
// original Elisa kernel; this test deliberately contains no answer table.
import assert from "node:assert/strict";
import fs from "node:fs";
import { fileURLToPath } from "node:url";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { decode, Kind } from "../shells/web/display-list.js";

const root = fileURLToPath(new URL("..", import.meta.url));
const wasm = process.env.NWCORE_WASM_PATH ?? `${root}/build/nwcore.wasm`;
const { exports, instance } = await instantiateElisa(fs.readFileSync(wasm), { warn: false });

const TASK = BigInt(exports.nw_api_v1_task_custody());
const STATUS = Object.freeze({ accepted: 1n, ignored: 2n, badOptions: -3n });
const EVENT = Object.freeze({ action: 1n, keyDown: 2n });
const KEY = Object.freeze({ space: 1n, enter: 2n, left: 3n, up: 4n,
  right: 5n, down: 6n });
const ACTION = Object.freeze({ start: 0n, left: 1n, right: 2n, grab: 3n });
const PHASE = Object.freeze({ ready: 0n, marking: 1n, running: 2n,
  scored: 3n, done: 4n });
const INFO = Object.freeze({
  phase: 0, rung: 1, trial: 2, totalTrials: 3, width: 4, slots: 5,
  boxes: 6, bay: 7, claw: 8, held: 9, spent: 10, budget: 11,
  verdict: 12, deadlineMs: 13, beltMs: 14, markMs: 15,
  needCharge: 16, maxHeat: 17, moving: 18, right: 19,
  bestRung: 20, floorPercent: 21, beltDeadlineMs: 22,
});
const VALUE = Object.freeze({ look: 0n, charge: 1n, heat: 2n, slot: 3n,
  held: 4n, delivered: 5n, machine: 6n });
const STATE_BYTES = 112;
const FRAME_BYTES = 1048576;
const STATE_BUFFER = Number(exports.nw_frame_alloc(BigInt(STATE_BYTES)));
const FRAME_BUFFER = Number(exports.nw_frame_alloc(BigInt(FRAME_BYTES)));
assert.ok(TASK > 0n && STATE_BUFFER > 0 && FRAME_BUFFER > 0);

function create(options = [3n, 1n, 400n, 400n, 0n, 0n], seed = 17n) {
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

function action(handle, code, timestamp, sequence) {
  return event(handle, EVENT.action, timestamp, sequence, code);
}

function info(handle, field) {
  return BigInt(exports.nw_api_v1_custody_info(handle, BigInt(field)));
}

function value(handle, field, at) {
  return BigInt(exports.nw_api_v1_custody_value(handle, field, BigInt(at)));
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

assert.equal(TASK, 1119512566n, "Chain of Custody keeps its stable task ID");
assert.equal(Number(exports.nw_api_v1_supports(TASK)), 1);
assert.equal(create([0n, 1n, 400n, 400n, 0n, 0n]), STATUS.badOptions);
assert.equal(create([11n, 1n, 400n, 400n, 0n, 0n]), STATUS.badOptions);
assert.equal(create([3n, 4n, 400n, 400n, 0n, 0n]), STATUS.badOptions);
assert.equal(create([3n, 1n, 100n, 400n, 0n, 0n]), STATUS.badOptions);
assert.equal(create([3n, 1n, 400n, 200n, 0n, 0n]), STATUS.badOptions);
assert.equal(create([3n, 1n, 400n, 400n, 2n, 0n]), STATUS.badOptions);
assert.equal(create([3n, 1n, 400n, 400n, 0n, 1n]), STATUS.badOptions);

const run = create();
const replay = create();
assert.ok(run > 0n && replay > 0n);
assert.deepEqual(state(run), [0n, 3n, 0n, 1n, 0n, 0n, 0n, 0n, 0n, -1n, 0n, 0n]);
const readyFrame = frame(run);
assert.deepEqual(frame(run), readyFrame, "ready rendering is observational");
assert.ok(decode(readyFrame).some(({ kind, text }) =>
  kind === Kind.TEXT && text === "Chain of Custody"));

assert.equal(event(run, EVENT.keyDown, 100, 0, KEY.space), STATUS.accepted);
assert.equal(action(replay, ACTION.start, 100, 0), STATUS.accepted);
assert.deepEqual(state(run), state(replay), "same seed gives the same generated layout");
assert.equal(info(run, INFO.phase), PHASE.marking);
assert.equal(info(run, INFO.rung), 3n);
assert.equal(info(run, INFO.width), 6n);
assert.equal(info(run, INFO.boxes), 5n);
assert.equal(info(run, INFO.slots), 12n);
assert.equal(info(run, INFO.needCharge), 0n);
assert.equal(info(run, INFO.maxHeat), 100n);
assert.equal(info(run, INFO.budget), 70n);
assert.equal(info(run, INFO.markMs), 400n);
assert.equal(info(run, INFO.beltMs), 400n);
assert.ok(value(run, VALUE.machine, 0) >= -1n);
assert.ok(value(run, VALUE.look, 0) >= 0n && value(run, VALUE.look, 0) < 2n);
assert.ok(decode(frame(run)).some(({ kind, text }) =>
  kind === Kind.TEXT && text.includes("deliver the ringed box")));

// The marking deadline is inclusive. An early tick is ignored without
// mutating the source phase; the boundary enters the live belt phase.
assert.equal(advance(run, 499, 1), STATUS.ignored);
assert.equal(info(run, INFO.phase), PHASE.marking);
assert.equal(advance(run, 500, 2), STATUS.accepted);
assert.equal(info(run, INFO.phase), PHASE.running);

// Keyboard aliases use the same task-neutral key map as the browser shell.
assert.equal(event(run, EVENT.keyDown, 501, 3, KEY.right), STATUS.accepted);
assert.equal(info(run, INFO.claw), 1n);
assert.equal(event(run, EVENT.keyDown, 502, 4, KEY.up), STATUS.accepted);
assert.ok(info(run, INFO.held) >= -1n && info(run, INFO.held) < info(run, INFO.boxes));
assert.ok(decode(frame(run)).some(({ kind, text }) =>
  kind === Kind.TEXT && (text.includes("Which one") || text.includes("Picked it up") || text.includes("Nothing there"))));

// Finish the live phase through source belt deadlines. At rung three the
// original budget is 70 steps; no browser-side timer or score shortcut is
// allowed in this loop.
let sequence = 5;
let now = 503;
while (info(run, INFO.phase) === PHASE.running) {
  const deadline = info(run, INFO.beltDeadlineMs);
  assert.ok(deadline >= 0n);
  now = Math.max(now, Number(deadline));
  assert.equal(advance(run, now, sequence), STATUS.accepted);
  sequence += 1;
  now += 1;
}
assert.equal(info(run, INFO.phase), PHASE.scored);
assert.equal(info(run, INFO.verdict), 0n);
assert.equal(info(run, INFO.spent), 70n);
assert.ok(decode(frame(run)).some(({ kind, text }) =>
  kind === Kind.TEXT && text.includes("Out of actions")));

// Scored state is a real deadline-gated phase, and Space starts the next
// source trial only at that deadline.
const verdictDeadline = Number(info(run, INFO.deadlineMs));
assert.equal(action(run, ACTION.start, Math.max(now, verdictDeadline - 1), sequence), STATUS.ignored);
sequence += 1;
assert.equal(action(run, ACTION.start, Math.max(now, verdictDeadline), sequence), STATUS.accepted);
assert.equal(info(run, INFO.phase), PHASE.done);
assert.ok(decode(frame(run)).some(({ kind, text }) =>
  kind === Kind.TEXT && text.includes("delivered")));

for (const handle of [run, replay]) {
  assert.equal(exports.nw_api_v1_destroy(handle), 0n);
  assert.equal(exports.nw_api_v1_destroy(handle), 0n, "destroy is idempotent");
}

console.log("PASS: Chain of Custody source-backed generation, marking, belt timing, input, rendering, scoring, options, and cleanup");
