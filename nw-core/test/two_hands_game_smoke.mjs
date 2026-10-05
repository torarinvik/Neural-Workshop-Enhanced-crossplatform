// Common-v1 lifecycle smoke for source-backed Two Hands.
// The test deliberately drives the shared kernel through both the explicit
// port action and the physical key/pointer paths used by the browser shell.
import assert from "node:assert/strict";
import fs from "node:fs";
import { fileURLToPath } from "node:url";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { decode, Kind } from "../shells/web/display-list.js";

const root = fileURLToPath(new URL("..", import.meta.url));
const wasm = process.env.NWCORE_WASM_PATH ?? `${root}/build/nwcore.wasm`;
const { exports, instance } = await instantiateElisa(fs.readFileSync(wasm), { warn: false });

const TASK = BigInt(exports.nw_api_v1_task_two_hands());
const STATUS = Object.freeze({ accepted: 1n, ignored: 2n, badOptions: -3n });
const EVENT = Object.freeze({ action: 1n, keyDown: 2n, pointerMove: 4n, pointerDown: 5n });
const KEY = Object.freeze({ space: 1n, enter: 2n, left: 3n, up: 4n, right: 5n, down: 6n });
const ACTION = Object.freeze({ start: 0n, port: 1n, left: 2n, right: 3n, jump: 4n, faster: 5n, slower: 6n });
const PORT = Object.freeze({ hold: 0n, left: 1n, right: 2n, jump: 3n, faster: 4n, slower: 5n });
const PHASE = Object.freeze({ ready: 0n, setting: 1n, running: 2n, scored: 3n, done: 4n });
const INFO = Object.freeze({
  phase: 0, rung: 1, trial: 2, totalTrials: 3, roadRows: 4, roadLength: 5,
  hazards: 6, carAt: 7, carLaneMilli: 8, carCrossing: 9, carAir: 10,
  carSpeed: 11, carTicks: 12, carPassed: 13, carClipped: 14, carHit: 15,
  roadClock: 16, roadPar: 17, shot: 18, targets: 19, points: 20,
  verdict: 21, untilMs: 22, beatAtMs: 23, clockMs: 24, resultCount: 25,
  clean: 26, taken: 27, bestRung: 28, startRung: 29, beatMs: 30, setMs: 31,
  adaptive: 32, crossXMilli: 33, crossYMilli: 34, loaded: 35,
});
const VALUE = Object.freeze({
  hazardAt: 0n, hazardLane: 1n, hazardKind: 2n, targetAt: 3n,
  targetAcrossMilli: 4n, targetUpMilli: 5n, targetDowned: 6n,
  resultRung: 100n, resultCleared: 101n, resultPoints: 102n, resultShot: 103n,
});
const STATE_BYTES = 112;
const FRAME_BYTES = 1048576;
const statePtr = Number(exports.nw_frame_alloc(BigInt(STATE_BYTES)));
const framePtr = Number(exports.nw_frame_alloc(BigInt(FRAME_BYTES)));
assert.ok(TASK > 0n && statePtr > 0 && framePtr > 0);

function create(options = [1n, 1n, 150n, 0n, 0n, 0n], seed = 17n) {
  return exports.nw_api_v1_create(TASK, 1n, ...options, seed);
}

function dispatch(handle, kind, timestamp, sequence, code, value = 0n,
  x = 0n, y = 0n) {
  return exports.nw_api_v1_dispatch(handle, kind, BigInt(timestamp),
    BigInt(sequence), code, value, 0n, 0n, x, y, 0n);
}

function keyDown(handle, key, timestamp, sequence, physical = 0n) {
  return dispatch(handle, EVENT.keyDown, timestamp, sequence, key, physical);
}

function action(handle, code, timestamp, sequence, value = 0n) {
  return dispatch(handle, EVENT.action, timestamp, sequence, code, value);
}

function advance(handle, timestamp, sequence) {
  return exports.nw_api_v1_advance(handle, BigInt(timestamp), 0n,
    BigInt(sequence));
}

function info(handle, field) {
  return BigInt(exports.nw_api_v1_two_hands_info(handle, BigInt(field)));
}

function value(handle, field, at = 0) {
  return BigInt(exports.nw_api_v1_two_hands_value(handle, field, BigInt(at)));
}

function state(handle) {
  const length = exports.nw_api_v1_read_state(handle, BigInt(statePtr), BigInt(STATE_BYTES));
  assert.equal(length, BigInt(STATE_BYTES));
  const view = new DataView(instance.exports.memory.buffer, statePtr, STATE_BYTES);
  assert.equal(view.getUint32(0, true), 0x3152574e);
  assert.equal(view.getUint32(4, true), 1);
  assert.equal(view.getUint32(12, true), 12);
  return Array.from({ length: 12 }, (_, index) =>
    view.getBigInt64(16 + index * 8, true));
}

function frame(handle) {
  const length = exports.nw_api_v1_render(handle, BigInt(framePtr),
    BigInt(FRAME_BYTES), 0n, 912n, 684n);
  assert.ok(length > 0n, `render failed: ${length}`);
  return new Uint8Array(instance.exports.memory.buffer, framePtr,
    Number(length)).slice();
}

function textIn(bytes, expected) {
  return decode(bytes).some(({ kind, text }) =>
    kind === Kind.TEXT && text.includes(expected));
}

function snapshot(handle) {
  return [
    ...Array.from({ length: 36 }, (_, field) => info(handle, field)),
    ...Array.from({ length: 3 }, (_, field) => value(handle, BigInt(field), 0)),
  ];
}

assert.equal(TASK, 1665677052n, "Two Hands keeps its stable task ID");
assert.equal(Number(exports.nw_api_v1_supports(TASK)), 1);
assert.equal(create([0n, 1n, 150n, 0n, 0n, 0n]), STATUS.badOptions);
assert.equal(create([1n, 4n, 150n, 0n, 0n, 0n]), STATUS.badOptions);
assert.equal(create([1n, 1n, 100n, 0n, 0n, 0n]), STATUS.badOptions);
assert.equal(create([1n, 1n, 150n, 200n, 0n, 0n]), STATUS.badOptions);
assert.equal(create([1n, 1n, 150n, 0n, 2n, 0n]), STATUS.badOptions);
assert.equal(create([1n, 1n, 150n, 0n, 0n, 1n]), STATUS.badOptions);

const run = create();
const replay = create();
assert.ok(run > 0n && replay > 0n);
assert.equal(info(run, INFO.phase), PHASE.ready);
assert.equal(info(run, INFO.rung), 1n);
assert.equal(info(run, INFO.resultCount), 0n);
assert.ok(textIn(frame(run), "Two Hands"));
assert.ok(textIn(frame(run), "Press Space to start"));
assert.deepEqual(state(run), [0n, 1n, 0n, 1n, 0n, 0n, 0n, 0n, 0n, 0n, 0n, -1n]);

// Space through the physical key mapper and the explicit start action must
// deal the same source road and preserve the same generated hazard list.
assert.equal(keyDown(run, KEY.space, 0, 0, 32n), STATUS.accepted);
assert.equal(action(replay, ACTION.start, 0, 0), STATUS.accepted);
assert.equal(info(run, INFO.phase), PHASE.setting);
assert.equal(info(run, INFO.trial), 1n);
assert.ok(info(run, INFO.roadLength) > 0n);
assert.equal(info(run, INFO.roadRows), 28n);
assert.equal(info(run, INFO.hazards), info(replay, INFO.hazards));
assert.equal(info(run, INFO.targets), info(replay, INFO.targets));
for (let at = 0n; at < info(run, INFO.hazards); at += 1n) {
  assert.equal(value(run, VALUE.hazardAt, Number(at)),
    value(replay, VALUE.hazardAt, Number(at)));
  assert.equal(value(run, VALUE.hazardLane, Number(at)),
    value(replay, VALUE.hazardLane, Number(at)));
  assert.equal(value(run, VALUE.hazardKind, Number(at)),
    value(replay, VALUE.hazardKind, Number(at)));
}

// With no setting delay the first clock edge enters running, without moving
// the car. The source beat is then exactly the selected beat interval.
assert.equal(advance(run, 0, 1), STATUS.accepted);
assert.equal(advance(replay, 0, 1), STATUS.accepted);
assert.equal(info(run, INFO.phase), PHASE.running);
assert.equal(info(run, INFO.carAt), 0n);
assert.equal(info(run, INFO.beatAtMs), 150n);
assert.equal(keyDown(run, KEY.up, 1, 2, 38n), STATUS.accepted);
assert.equal(action(replay, ACTION.port, 1, 2, PORT.faster), STATUS.accepted);
assert.deepEqual(snapshot(run), snapshot(replay));
assert.equal(info(run, INFO.carSpeed), 2n);
assert.equal(keyDown(run, KEY.space, 2, 3, 32n), STATUS.accepted);
assert.equal(action(replay, ACTION.port, 2, 3, PORT.jump), STATUS.accepted);
assert.equal(info(run, INFO.carAir), 3n);
assert.equal(keyDown(run, KEY.right, 3, 4, 39n), STATUS.ignored);
assert.equal(action(replay, ACTION.port, 3, 4, PORT.right), STATUS.ignored);

// Aim is updated independently of wheel input; primary pointer-down enters the
// source sighted/fire path even when the selected reticle contains no target.
assert.equal(dispatch(run, EVENT.pointerMove, 4, 5, 0n, 0n, 500000n, 500000n), STATUS.accepted);
assert.equal(dispatch(replay, EVENT.pointerMove, 4, 5, 0n, 0n, 500000n, 500000n), STATUS.accepted);
assert.equal(info(run, INFO.crossXMilli), 500000n);
assert.equal(info(run, INFO.crossYMilli), 500000n);
const pointerResult = dispatch(run, EVENT.pointerDown, 5, 6, 0n, 1n, 500000n, 500000n);
const replayPointerResult = dispatch(replay, EVENT.pointerDown, 5, 6, 0n, 1n, 500000n, 500000n);
assert.ok(pointerResult === STATUS.accepted || pointerResult === STATUS.ignored);
assert.equal(pointerResult, replayPointerResult);

let now = 150;
let sequence = 7;
while (info(run, INFO.phase) === PHASE.running && sequence < 5000) {
  now += 150;
  assert.equal(advance(run, now, sequence), STATUS.accepted);
  assert.equal(advance(replay, now, sequence), STATUS.accepted);
  sequence += 1;
}
assert.equal(info(run, INFO.phase), PHASE.scored);
assert.equal(info(run, INFO.resultCount), 1n);
assert.ok(info(run, INFO.verdict) === 0n || info(run, INFO.verdict) === 1n);
assert.deepEqual(snapshot(run), snapshot(replay));
assert.ok(textIn(frame(run), "Two Hands"));
assert.equal(action(run, ACTION.start, info(run, INFO.untilMs) - 1n, sequence), STATUS.ignored);
assert.equal(action(run, ACTION.start, info(run, INFO.untilMs), sequence + 1), STATUS.accepted);
assert.equal(info(run, INFO.phase), PHASE.done);
assert.equal(info(run, INFO.resultCount), 1n);
assert.ok(value(run, VALUE.resultRung, 0) >= 1n);
assert.ok(value(run, VALUE.resultCleared, 0) === 0n || value(run, VALUE.resultCleared, 0) === 1n);
assert.ok(textIn(frame(run), "roads driven"));

for (const handle of [run, replay]) {
  assert.equal(exports.nw_api_v1_destroy(handle), 0n);
  assert.equal(exports.nw_api_v1_destroy(handle), 0n, "destroy is idempotent");
}

console.log("PASS: Two Hands source road generation, wheel/keyboard input, pointer aim/fire, timed beats, scoring, rendering, options, and cleanup");
