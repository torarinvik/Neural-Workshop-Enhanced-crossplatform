// Common-v1 lifecycle smoke for source-backed Buzz Wire.
// The controller owns the seeded three-dimensional wire, hand/tremor state,
// contact accounting, adaptive rung, and source display-list chrome. The host
// supplies only monotonic time and press/release actions for the eleven source
// ports.
import assert from "node:assert/strict";
import fs from "node:fs";
import { fileURLToPath } from "node:url";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { decode, Kind } from "../shells/web/display-list.js";

const root = fileURLToPath(new URL("..", import.meta.url));
const wasm = process.env.NWCORE_WASM_PATH ?? `${root}/build/nwcore.wasm`;
const { exports, instance } = await instantiateElisa(fs.readFileSync(wasm), { warn: false });

const TASK = BigInt(exports.nw_api_v1_task_buzz_wire());
const STATUS = Object.freeze({ accepted: 1n, ignored: 2n, badOptions: -3n });
const EVENT = Object.freeze({ action: 1n, keyDown: 2n, keyUp: 3n });
const KEY = Object.freeze({ space: 1n, enter: 2n });
const ACTION = Object.freeze({ start: 0n, press: 1n, release: 2n, tap: 3n, clear: 4n });
const PHASE = Object.freeze({ ready: 0n, flying: 1n, settled: 2n, done: 3n });
const INFO = Object.freeze({
  phase: 0, currentRung: 1, trialRung: 2, trial: 3, totalTrials: 4,
  adaptive: 5, touchesAllowed: 6, buzzes: 7, alongPpm: 8,
  secondsLeftMs: 9, usedPpm: 10, bead: 11, beads: 12,
  wireLengthUm: 13, wirePoints: 14, clockMs: 15, deadlineMs: 16,
  verdict: 17, resultCount: 18, wins: 19, touchTotal: 20,
  bestRung: 21, heldMask: 22, scraping: 23, home: 24,
  showMeter: 25, showBeads: 26, showSight: 27, lossReason: 28,
});
const VALUE = Object.freeze({
  cx: 0n, cy: 1n, cz: 2n, vx: 3n, vy: 4n, vz: 5n, yaw: 6n,
  pitch: 7n, arc: 8n, touches: 9n, home: 10n, bead: 11n,
  scraping: 12n, wireX: 20n, wireY: 21n, wireZ: 22n,
  wireTx: 23n, wireTy: 24n, wireTz: 25n, wireArc: 26n,
});
const RESULT = Object.freeze({ rung: 100n, home: 101n, buzzes: 102n, timeMs: 103n });
const STATE_BYTES = 112;
const FRAME_BYTES = 1048576;
const STATE_BUFFER = Number(exports.nw_frame_alloc(BigInt(STATE_BYTES)));
const FRAME_BUFFER = Number(exports.nw_frame_alloc(BigInt(FRAME_BYTES)));
assert.ok(TASK > 0n && STATE_BUFFER > 0 && FRAME_BUFFER > 0);

function create(options = [1n, 1n, 1n, 1n, 1n, 1n], seed = 17n) {
  return exports.nw_api_v1_create(TASK, 1n, ...options, seed);
}

function event(handle, kind, timestamp, sequence, code, value = 0n) {
  return exports.nw_api_v1_dispatch(handle, kind, BigInt(timestamp),
    BigInt(sequence), code, value, 0n, 0n, 0n, 0n, 0n);
}

function keyDown(handle, key, timestamp, sequence) {
  return event(handle, EVENT.keyDown, timestamp, sequence, key);
}

function action(handle, code, timestamp, sequence, value = 0n) {
  return event(handle, EVENT.action, timestamp, sequence, code, value);
}

function advance(handle, timestamp, elapsed, sequence) {
  return exports.nw_api_v1_advance(handle, BigInt(timestamp), BigInt(elapsed),
    BigInt(sequence));
}

function info(handle, field) {
  return BigInt(exports.nw_api_v1_buzz_wire_info(handle, BigInt(field)));
}

function value(handle, field, at = 0) {
  return BigInt(exports.nw_api_v1_buzz_wire_value(handle, field, BigInt(at)));
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
  const length = exports.nw_api_v1_render(handle,
    BigInt(FRAME_BUFFER), BigInt(FRAME_BYTES), 0n, 912n, 684n);
  assert.ok(length > 0n, `render failed: ${length}`);
  return new Uint8Array(instance.exports.memory.buffer, FRAME_BUFFER,
    Number(length)).slice();
}

function textIn(bytes, expected) {
  return decode(bytes).some(({ kind, text }) =>
    kind === Kind.TEXT && text.includes(expected));
}

function snapshot(handle) {
  return [
    ...Array.from({ length: 29 }, (_, field) => info(handle, field)),
    ...Array.from({ length: 13 }, (_, field) => value(handle, BigInt(field))),
    ...Array.from({ length: 8 }, (_, field) => value(handle, VALUE.wireX, field)),
    ...Array.from({ length: 8 }, (_, field) => value(handle, VALUE.wireArc, field)),
  ];
}

assert.equal(TASK, 747330860n, "Buzz Wire keeps its stable task ID");
assert.equal(Number(exports.nw_api_v1_supports(TASK)), 1);
assert.equal(create([0n, 1n, 1n, 1n, 1n, 1n]), STATUS.badOptions);
assert.equal(create([13n, 1n, 1n, 1n, 1n, 1n]), STATUS.badOptions);
assert.equal(create([1n, 4n, 1n, 1n, 1n, 1n]), STATUS.badOptions);
assert.equal(create([1n, 1n, 2n, 1n, 1n, 1n]), STATUS.badOptions);
assert.equal(create([1n, 1n, 1n, 2n, 1n, 1n]), STATUS.badOptions);
assert.equal(create([1n, 1n, 1n, 1n, 2n, 1n]), STATUS.badOptions);
assert.equal(create([1n, 1n, 1n, 1n, 1n, 2n]), STATUS.badOptions);

const run = create();
const replay = create();
assert.ok(run > 0n && replay > 0n);
assert.deepEqual(state(run), [0n, 1n, 0n, 1n, 0n, 0n, 0n, 0n,
  -1n, 0n, 0n, 0n]);
assert.equal(info(run, INFO.beads), 0n);
const ready = frame(run);
assert.deepEqual(frame(run), ready, "ready rendering is observational");
assert.ok(textIn(ready, "Buzz Wire"));
assert.ok(textIn(ready, "Press Space to start"));

// Keyboard start and the explicit source action must deal the same wire and
// hand. The large wire payload is compared through the stable value accessors,
// rather than by exposing the source darrays to the browser.
assert.equal(keyDown(run, KEY.space, 0, 0), STATUS.accepted);
assert.equal(action(replay, ACTION.start, 0, 0), STATUS.accepted);
assert.deepEqual(snapshot(run), snapshot(replay));
assert.equal(info(run, INFO.phase), PHASE.flying);
assert.equal(info(run, INFO.trial), 1n);
assert.equal(info(run, INFO.trialRung), 1n);
assert.equal(info(run, INFO.touchesAllowed), 6n);
assert.equal(info(run, INFO.beads), 40n);
assert.ok(info(run, INFO.wirePoints) > 32n);
assert.ok(info(run, INFO.wireLengthUm) > 0n);
assert.ok(textIn(frame(run), "Level 1"));

// A directional press is a held source port, not a one-frame browser hint.
// At this deterministic starter wire the first port produces a fresh contact
// during the first second, exercising the hand/wire copy boundary and the
// source's fresh-contact accounting without assuming a particular frame rate.
assert.equal(action(run, ACTION.press, 1, 1, 0n), STATUS.accepted);
assert.equal(action(replay, ACTION.press, 1, 1, 0n), STATUS.accepted);
assert.equal(info(run, INFO.heldMask), 1n);
let contactNow = 101;
let contactSequence = 2;
while (info(run, INFO.buzzes) === 0n && contactNow <= 2101) {
  assert.equal(advance(run, contactNow, 100, contactSequence), STATUS.accepted);
  assert.equal(advance(replay, contactNow, 100, contactSequence), STATUS.accepted);
  contactNow += 100;
  contactSequence += 1;
}
assert.deepEqual(snapshot(run), snapshot(replay));
assert.ok(info(run, INFO.buzzes) >= 1n);
assert.equal(action(run, ACTION.release, contactNow - 100, contactSequence, 0n), STATUS.accepted);
assert.equal(action(replay, ACTION.release, contactNow - 100, contactSequence, 0n), STATUS.accepted);
assert.equal(info(run, INFO.heldMask), 0n);
assert.deepEqual(snapshot(run), snapshot(replay));

// A compact timeout run verifies the settled result row, source verdict text,
// and the settled -> done boundary used by Space/Enter in the browser shell.
const timeout = create([1n, 1n, 0n, 1n, 1n, 1n], 23n);
assert.equal(action(timeout, ACTION.start, 0, 0), STATUS.accepted);
assert.equal(advance(timeout, 20000, 20000, 1), STATUS.accepted);
assert.equal(info(timeout, INFO.phase), PHASE.settled);
assert.equal(info(timeout, INFO.verdict), 0n);
assert.equal(info(timeout, INFO.lossReason), 2n);
assert.equal(info(timeout, INFO.resultCount), 1n);
assert.equal(value(timeout, RESULT.home, 0), 0n);
assert.equal(value(timeout, RESULT.buzzes, 0), 0n);
assert.equal(value(timeout, RESULT.rung, 0), 1n);
assert.ok(textIn(frame(timeout), "Out of time"));
assert.equal(action(timeout, ACTION.start, 20000, 2), STATUS.accepted);
assert.equal(info(timeout, INFO.phase), PHASE.done);
assert.equal(info(timeout, INFO.resultCount), 1n);

for (const handle of [run, replay, timeout]) {
  assert.equal(exports.nw_api_v1_destroy(handle), 0n);
  assert.equal(exports.nw_api_v1_destroy(handle), 0n, "destroy is idempotent");
}

console.log("PASS: Buzz Wire source-backed wire deal, held ports, contact accounting, timeout feedback, rendering, options, and cleanup");
