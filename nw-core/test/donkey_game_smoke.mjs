// Common-v1 lifecycle smoke for source-backed Donkey.
// The controller owns the generated road, car/crossing state, collision and
// passing rules, timed beats, adaptive results, and the source display list.
// The host supplies only monotonic time and the single source swerve action.
import assert from "node:assert/strict";
import fs from "node:fs";
import { fileURLToPath } from "node:url";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { decode, Kind } from "../shells/web/display-list.js";

const root = fileURLToPath(new URL("..", import.meta.url));
const wasm = process.env.NWCORE_WASM_PATH ?? `${root}/build/nwcore.wasm`;
const { exports, instance } = await instantiateElisa(fs.readFileSync(wasm), { warn: false });

const TASK = BigInt(exports.nw_api_v1_task_donkey());
const STATUS = Object.freeze({ accepted: 1n, ignored: 2n, badOptions: -3n });
const EVENT = Object.freeze({ action: 1n, keyDown: 2n });
const KEY = Object.freeze({ space: 1n, enter: 2n, left: 3n, up: 4n, right: 5n });
const ACTION = Object.freeze({ start: 0n, switch: 1n });
const PHASE = Object.freeze({ ready: 0n, setting: 1n, running: 2n, scored: 3n, done: 4n });
const INFO = Object.freeze({
  phase: 0, rung: 1, trial: 2, totalTrials: 3, roadRows: 4,
  roadLength: 5, donkeys: 6, carAt: 7, carLane: 8, carCrossing: 9,
  carSpan: 10, carPassed: 11, hit: 12, verdict: 13, untilMs: 14,
  beatAtMs: 15, clockMs: 16, resultCount: 17, clean: 18, passedTotal: 19,
  bestRung: 20, startRung: 21, beatMs: 22, setMs: 23, adaptive: 24,
  roadStart: 25, swerve: 26,
});
const VALUE = Object.freeze({ blocked: 0n, beastAt: 1n, beastLane: 2n });
const RESULT = Object.freeze({ rung: 100n, cleared: 101n, passed: 102n });
const STATE_BYTES = 112;
const FRAME_BYTES = 1048576;
const STATE_BUFFER = Number(exports.nw_frame_alloc(BigInt(STATE_BYTES)));
const FRAME_BUFFER = Number(exports.nw_frame_alloc(BigInt(FRAME_BYTES)));
assert.ok(TASK > 0n && STATE_BUFFER > 0 && FRAME_BUFFER > 0);

function create(options = [3n, 5n, 180n, 800n, 1n, 0n], seed = 17n) {
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
  return BigInt(exports.nw_api_v1_donkey_info(handle, BigInt(field)));
}

function value(handle, field, at = 0) {
  return BigInt(exports.nw_api_v1_donkey_value(handle, field, BigInt(at)));
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
    ...Array.from({ length: 27 }, (_, field) => info(handle, field)),
    ...Array.from({ length: 3 }, (_, field) => value(handle, BigInt(field), 0)),
  ];
}

assert.equal(TASK, 4237590581n, "Donkey keeps its stable task ID");
assert.equal(Number(exports.nw_api_v1_supports(TASK)), 1);
assert.equal(create([0n, 5n, 180n, 800n, 1n, 0n]), STATUS.badOptions);
assert.equal(create([3n, 4n, 180n, 800n, 1n, 0n]), STATUS.badOptions);
assert.equal(create([3n, 5n, 100n, 800n, 1n, 0n]), STATUS.badOptions);
assert.equal(create([3n, 5n, 180n, 200n, 1n, 0n]), STATUS.badOptions);
assert.equal(create([3n, 5n, 180n, 800n, 2n, 0n]), STATUS.badOptions);
assert.equal(create([3n, 5n, 180n, 800n, 1n, 1n]), STATUS.badOptions);

const run = create();
const replay = create();
assert.ok(run > 0n && replay > 0n);
assert.deepEqual(state(run), [0n, 3n, 0n, 5n, 0n, 0n, 0n, 0n,
  0n, 0n, -1n, 0n]);
assert.equal(info(run, INFO.roadLength), 0n);
const ready = frame(run);
assert.deepEqual(frame(run), ready, "ready rendering is observational");
assert.ok(textIn(ready, "Donkey"));
assert.ok(textIn(ready, "Press Space to start"));

// Keyboard Space and the explicit source action must deal the same road and
// schedule. This also checks the route used by the browser's key mapper.
assert.equal(keyDown(run, KEY.space, 0, 0), STATUS.accepted);
assert.equal(action(replay, ACTION.start, 0, 0), STATUS.accepted);
assert.deepEqual(snapshot(run), snapshot(replay));
assert.equal(info(run, INFO.phase), PHASE.setting);
assert.equal(info(run, INFO.trial), 1n);
assert.ok(info(run, INFO.roadLength) > 0n);
assert.ok(info(run, INFO.donkeys) >= 0n);
assert.ok(textIn(frame(run), "Road 1 of 5"));

// The setting clock is source-owned: no beat can move the car early, then the
// first advance at the setting boundary transitions into the running phase.
assert.equal(advance(run, 799, 1), STATUS.ignored);
assert.equal(advance(replay, 799, 1), STATUS.ignored);
assert.equal(info(run, INFO.phase), PHASE.setting);
assert.equal(advance(run, 800, 2), STATUS.accepted);
assert.equal(advance(replay, 800, 2), STATUS.accepted);
assert.equal(info(run, INFO.phase), PHASE.running);
assert.equal(info(run, INFO.carAt), 0n);

// A key-down swerve and the explicit action are equivalent. The crossing is
// held through subsequent beats, so the second action is intentionally ignored
// while the first crossing is active.
assert.equal(keyDown(run, KEY.right, 801, 3), STATUS.accepted);
assert.equal(action(replay, ACTION.switch, 801, 3), STATUS.accepted);
assert.deepEqual(snapshot(run), snapshot(replay));
assert.equal(info(run, INFO.carCrossing), info(run, INFO.carSpan));
assert.equal(keyDown(run, KEY.left, 802, 4), STATUS.ignored);
assert.equal(action(replay, ACTION.switch, 802, 4), STATUS.ignored);
assert.deepEqual(snapshot(run), snapshot(replay));

// Run the same deterministic road to its source collision/finish boundary.
// The controller advances exactly one source beat per eligible timestamp; the
// bound is generous enough for the largest generated road but finite if a
// regression stops advancing.
let now = 800;
let sequence = 5;
while (info(run, INFO.phase) === PHASE.running && sequence < 5000) {
  now += 180;
  assert.equal(advance(run, now, sequence), STATUS.accepted);
  assert.equal(advance(replay, now, sequence), STATUS.accepted);
  sequence += 1;
}
assert.equal(info(run, INFO.phase), PHASE.scored);
assert.equal(info(run, INFO.resultCount), 1n);
assert.ok(info(run, INFO.verdict) === 0n || info(run, INFO.verdict) === 1n);
assert.deepEqual(snapshot(run), snapshot(replay));
assert.ok(textIn(frame(run), "Donkey"));
assert.ok(textIn(frame(run), info(run, INFO.verdict) === 1n ? "Home" : "Hit one"));
assert.equal(action(run, ACTION.start, info(run, INFO.untilMs) - 1n, sequence), STATUS.ignored);

// A compact one-road run verifies result completion and the scored -> done
// boundary without making success depend on a hand-picked road layout.
const short = create([1n, 1n, 80n, 0n, 0n, 0n], 23n);
assert.ok(short > 0n);
assert.equal(action(short, ACTION.start, 0, 0), STATUS.accepted);
assert.equal(advance(short, 0, 1), STATUS.accepted);
let shortNow = 0;
let shortSequence = 2;
while (info(short, INFO.phase) === PHASE.running && shortSequence < 5000) {
  shortNow += 80;
  assert.equal(advance(short, shortNow, shortSequence), STATUS.accepted);
  shortSequence += 1;
}
assert.equal(info(short, INFO.phase), PHASE.scored);
assert.equal(info(short, INFO.resultCount), 1n);
const scoredUntil = info(short, INFO.untilMs);
assert.equal(action(short, ACTION.start, scoredUntil - 1n, shortSequence), STATUS.ignored);
assert.equal(action(short, ACTION.start, scoredUntil, shortSequence + 1), STATUS.accepted);
assert.equal(info(short, INFO.phase), PHASE.done);
assert.equal(info(short, INFO.resultCount), 1n);
assert.ok(value(short, RESULT.rung, 0) >= 1n);
assert.ok(value(short, RESULT.cleared, 0) === 0n || value(short, RESULT.cleared, 0) === 1n);
assert.ok(value(short, RESULT.passed, 0) >= 0n);
assert.ok(textIn(frame(short), "of 1 roads cleared"));

for (const handle of [run, replay, short]) {
  assert.equal(exports.nw_api_v1_destroy(handle), 0n);
  assert.equal(exports.nw_api_v1_destroy(handle), 0n, "destroy is idempotent");
}

console.log("PASS: Donkey source-backed road generation, timed beats, swerves, collision, scoring, rendering, options, and cleanup");
