// Common-v1 lifecycle smoke for the source-backed Crossed Wires controller.
//
// The wiring is intentionally not exported. This test verifies the public
// marker/target/budget state, deterministic seeded deals, source key-event
// transport, budget exhaustion, verdict rendering, and cleanup without
// turning the hidden answer into a production API.
import assert from "node:assert/strict";
import fs from "node:fs";
import { fileURLToPath } from "node:url";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { decode, Kind } from "../shells/web/display-list.js";

const root = fileURLToPath(new URL("..", import.meta.url));
const wasm = process.env.NWCORE_WASM_PATH ?? `${root}/build/nwcore.wasm`;
const { exports, instance } = await instantiateElisa(fs.readFileSync(wasm), { warn: false });

const TASK = BigInt(exports.nw_api_v1_task_crossed_wires());
const STATUS = Object.freeze({ accepted: 1n, ignored: 2n });
const EVENT = Object.freeze({ action: 1n, keyDown: 2n });
const KEY = Object.freeze({ space: 1n, one: 12n });
const ACTION = Object.freeze({ start: 0n, press: 1n, restart: 2n, applyOptions: 3n });
const PHASE = Object.freeze({ ready: 0n, playing: 1n, scored: 2n, done: 3n });
const INFO = Object.freeze({
  phase: 0, rung: 1, trial: 2, totalTrials: 3, keys: 4, atX: 5,
  atY: 6, goalX: 7, goalY: 8, goalAt: 9, goals: 10, pressesLeft: 11,
});
const GAME_INFO = Object.freeze({
  reachedTotal: 22, targetTotal: 23, accuracy: 24, bestRung: 25,
  perfectRounds: 26,
});
const STATE_BYTES = 112;
const FRAME_BYTES = 1048576;
const STATE_BUFFER = Number(exports.nw_frame_alloc(BigInt(STATE_BYTES)));
const FRAME_BUFFER = Number(exports.nw_frame_alloc(BigInt(FRAME_BYTES)));
assert.ok(TASK > 0n && STATE_BUFFER > 0 && FRAME_BUFFER > 0);
assert.equal(TASK, 2239133075n, "Crossed Wires keeps its stable task ID");
assert.equal(Number(exports.nw_api_v1_supports(TASK)), 1);

function create(options = [3n, 5n, 1n, 1n, 0n, 0n], seed = 17n) {
  return exports.nw_api_v1_create(TASK, 1n, ...options, seed);
}

function dispatch(handle, kind, timestamp, sequence, code, value = 0n) {
  return exports.nw_api_v1_dispatch(handle, kind, BigInt(timestamp),
    BigInt(sequence), code, value, 0n, 0n, 0n, 0n, 0n);
}

function action(handle, code, timestamp, sequence, value = 0n) {
  return dispatch(handle, EVENT.action, timestamp, sequence, code, value);
}

function keyDown(handle, key, physical, timestamp, sequence) {
  return exports.nw_api_v1_dispatch(handle, EVENT.keyDown, BigInt(timestamp),
    BigInt(sequence), key, BigInt(physical), 0n, 0n, 0n, 0n, 0n);
}

function state(handle) {
  const length = exports.nw_api_v1_read_state(handle,
    BigInt(STATE_BUFFER), BigInt(STATE_BYTES));
  assert.equal(length, BigInt(STATE_BYTES));
  const view = new DataView(instance.exports.memory.buffer,
    STATE_BUFFER, STATE_BYTES);
  assert.equal(view.getUint32(0, true), 0x3152574e);
  assert.equal(view.getUint32(4, true), 1);
  assert.equal(view.getUint32(12, true), 12);
  return Array.from({ length: 12 }, (_, index) =>
    view.getBigInt64(16 + index * 8, true));
}

function gameInfo(handle, field) {
  return exports.nw_api_v1_crossed_wires_info(handle, BigInt(field));
}

function frame(handle) {
  const length = exports.nw_api_v1_render(handle, BigInt(FRAME_BUFFER),
    BigInt(FRAME_BYTES), 0n, 912n, 684n);
  assert.ok(length > 0n, `render failed: ${length}`);
  return new Uint8Array(instance.exports.memory.buffer, FRAME_BUFFER,
    Number(length)).slice();
}

function textLines(bytes) {
  return decode(bytes).filter(({ kind }) => kind === Kind.TEXT)
    .map(({ text }) => text);
}

function hasText(bytes, expected) {
  return textLines(bytes).some((line) => line.includes(expected));
}

for (const options of [
  [0n, 5n, 1n, 1n, 0n, 0n],
  [13n, 5n, 1n, 1n, 0n, 0n],
  [3n, 4n, 1n, 1n, 0n, 0n],
  [3n, 5n, 2n, 1n, 0n, 0n],
  [3n, 5n, 1n, 2n, 0n, 0n],
  [3n, 5n, 1n, 1n, 1n, 0n],
]) {
  assert.ok(create(options) < 0n, `bad options accepted: ${options}`);
}

const run = create();
const replay = create();
assert.ok(run > 0n && replay > 0n);
assert.deepEqual(state(run), [0n, 3n, 0n, 5n, 0n, 0n, 0n, 0n, 0n,
  0n, 0n, 0n]);
for (const field of Object.values(GAME_INFO)) assert.equal(gameInfo(run, field), 0n);
assert.equal(gameInfo(run, 27), -1n,
  "the task-specific info endpoint must not expose private run fields");
const readyFrame = frame(run);
assert.deepEqual(frame(run), readyFrame, "ready rendering is observational");
assert.ok(hasText(readyFrame, "Crossed Wires"));
assert.ok(hasText(readyFrame, "Press Space to start"));

// Physical Space and typed START must create identical seeded rounds.
assert.equal(keyDown(run, KEY.space, 32, 100, 0), STATUS.accepted);
assert.equal(action(replay, ACTION.start, 100, 0), STATUS.accepted);
assert.deepEqual(state(run), state(replay), "key and action starts diverged");
let values = state(run);
assert.deepEqual(values.slice(0, 5), [PHASE.playing, 3n, 1n, 5n, 4n]);
assert.ok(values[INFO.goals] >= 3n && values[INFO.pressesLeft] > 0n);
const playingFrame = frame(run);
assert.ok(hasText(playingFrame, "through a mirror"));
assert.ok(hasText(playingFrame, "4 keys, 4 targets"));
assert.ok(hasText(playingFrame, "round 1/5"));
assert.ok(hasText(playingFrame, "presses left"));
assert.ok(!textLines(playingFrame).some((line) => line.includes("wiring")),
  "hidden wiring leaked into the display list");

// The physical number-key path is accepted by common-v1 and is converted to
// the zero-based semantic port by the Crossed Wires adapter.
const beforeKey = state(run);
assert.equal(keyDown(run, KEY.one, 49, 101, 1), STATUS.accepted);
values = state(run);
assert.equal(values[INFO.pressesLeft], beforeKey[INFO.pressesLeft] - 1n);
assert.equal(action(replay, ACTION.press, 101, 1, 0n), STATUS.accepted);
assert.deepEqual(state(run), state(replay), "physical port conversion diverged");

// A valid action code with an inactive four-key port is ignored, and does not
// mutate the marker or consume the budget.
const beforeInvalid = state(run);
assert.equal(action(run, ACTION.press, 102, 2, 7n), STATUS.ignored);
assert.deepEqual(state(run), beforeInvalid);

// Exhaust this round through public semantic presses. The controller must
// settle exactly once when the source budget is spent.
let timestamp = 103;
let sequence = 3;
while (state(run)[INFO.phase] === PHASE.playing) {
  const current = state(run);
  assert.ok(current[INFO.pressesLeft] > 0n);
  const result = action(run, ACTION.press, timestamp++, sequence++, 0n);
  assert.equal(result, STATUS.accepted);
}
values = state(run);
assert.equal(values[INFO.phase], PHASE.scored);
assert.ok(values[INFO.goalAt] <= values[INFO.goals]);
const scoredFrame = frame(run);
assert.ok(hasText(scoredFrame, "out of presses") || hasText(scoredFrame, "All "));

// Changing settings resets the run but retains the original random stream.
// Match that stream against a reference run that consumes one deal and then
// restarts under the requested settings.
const changed = create([3n, 5n, 1n, 1n, 0n, 0n], 31n);
const reference = create([4n, 5n, 0n, 0n, 0n, 0n], 31n);
assert.equal(action(changed, ACTION.start, 10, 0), STATUS.accepted);
const optionPayload = 4n | (3n << 4n) | (0n << 8n) | (0n << 9n);
assert.equal(action(changed, ACTION.applyOptions, 11, 1, optionPayload), STATUS.accepted);
assert.deepEqual(state(changed).slice(0, 4), [PHASE.ready, 4n, 0n, 5n]);
assert.equal(gameInfo(changed, 20), 0n, "adaptive setting must apply");
assert.equal(gameInfo(changed, 21), 0n, "grid setting must apply");
assert.equal(action(changed, ACTION.start, 12, 2), STATUS.accepted);
assert.equal(action(reference, ACTION.start, 10, 0), STATUS.accepted);
assert.equal(action(reference, ACTION.restart, 11, 1), STATUS.accepted);
assert.deepEqual(state(changed), state(reference),
  "options reset must keep the seeded deal stream intact");
const invalidOptionState = state(changed);
assert.ok(action(changed, ACTION.applyOptions, 13, 3, 4n | (8n << 4n)) < 0n,
  "an unknown round choice must fail ABI payload validation");
assert.deepEqual(state(changed), invalidOptionState,
  "invalid options must not mutate the controller");

// The one-round form reaches DONE only after the source's 800 ms scored pause.
const short = create([3n, 1n, 0n, 1n, 0n, 0n], 17n);
assert.equal(action(short, ACTION.start, 100, 0), STATUS.accepted);
let shortTime = 101;
let shortSequence = 1;
while (state(short)[INFO.phase] === PHASE.playing) {
  assert.equal(action(short, ACTION.press, shortTime++, shortSequence++, 0n),
    STATUS.accepted);
}
assert.equal(state(short)[INFO.phase], PHASE.scored);
const settledAt = shortTime - 1;
assert.equal(action(short, ACTION.start, settledAt + 799, shortSequence++), STATUS.ignored);
assert.equal(state(short)[INFO.phase], PHASE.scored);
assert.equal(action(short, ACTION.start, settledAt + 800, shortSequence++), STATUS.accepted);
assert.equal(state(short)[INFO.phase], PHASE.done);
assert.ok(hasText(frame(short), "1 rounds"));
assert.ok(hasText(frame(short), "% of targets reached, highest rung"));
const reached = Number(gameInfo(short, GAME_INFO.reachedTotal));
const targets = Number(gameInfo(short, GAME_INFO.targetTotal));
assert.ok(targets > 0 && reached >= 0 && reached <= targets);
assert.equal(Number(gameInfo(short, GAME_INFO.accuracy)),
  (() => {
    const numerator = reached * 100;
    const quotient = Math.floor(numerator / targets);
    const remainder = numerator % targets;
    return remainder * 2 > targets ||
      (remainder * 2 === targets && quotient % 2 === 1)
      ? quotient + 1 : quotient;
  })());
assert.equal(gameInfo(short, GAME_INFO.bestRung), 3n);
assert.equal(gameInfo(short, GAME_INFO.perfectRounds),
  reached === targets ? 1n : 0n);

// Trial advancement on a multi-round task is gated by exactly the same pause.
const scoredAt = timestamp - 1;
assert.equal(action(run, ACTION.start, scoredAt + 799, sequence++), STATUS.ignored);
assert.equal(state(run)[INFO.phase], PHASE.scored);
assert.equal(action(run, ACTION.start, scoredAt + 800, sequence++), STATUS.accepted);
assert.equal(state(run)[INFO.trial], 2n);

for (const handle of [run, replay, short, changed, reference]) {
  assert.equal(exports.nw_api_v1_destroy(handle), 0n);
  assert.equal(exports.nw_api_v1_destroy(handle), 0n, "destroy is idempotent");
}

console.log("PASS: Crossed Wires source-backed deal, hidden wiring, physical ports, budget settlement, verdict render, completion, and cleanup");
