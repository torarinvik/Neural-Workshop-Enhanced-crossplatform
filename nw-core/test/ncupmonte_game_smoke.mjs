// Common-v1 lifecycle smoke for the source-backed N-Cup Monte controller.
// The source owns the random deal, the swap permutation, the smoothstep
// clock, and the adaptive cup ladder; this test only supplies time and input.
import assert from "node:assert/strict";
import fs from "node:fs";
import { fileURLToPath } from "node:url";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { decode, Kind } from "../shells/web/display-list.js";

const root = fileURLToPath(new URL("..", import.meta.url));
const wasm = process.env.NWCORE_WASM_PATH ?? `${root}/build/nwcore.wasm`;
const { exports, instance } = await instantiateElisa(fs.readFileSync(wasm), { warn: false });

const TASK = BigInt(exports.nw_api_v1_task_ncup_monte());
const STATUS = Object.freeze({ accepted: 1n, ignored: 2n, badOptions: -3n });
const EVENT = Object.freeze({ action: 1n, keyDown: 2n, pointerDown: 5n });
const KEY = Object.freeze({ space: 1n, enter: 2n });
const ACTION = Object.freeze({ start: 0n, choose: 1n });
const PHASE = Object.freeze({ ready: 0n, reveal: 1n, shuffle: 2n,
  guess: 3n, result: 4n });
const INFO = Object.freeze({
  phase: 0, cups: 1, maxCups: 2, adaptive: 3, swapCount: 4,
  swapMs: 5, revealMs: 6, showNumbers: 7, ball: 8, guess: 9,
  swapN: 10, swapAt: 11, deadlineMs: 12, swapStartedMs: 13,
  swapElapsedMs: 14, swapA: 15, swapB: 16, round: 17, hits: 18,
  misses: 19, lastCorrect: 20,
});
const VALUE = Object.freeze({ order: 0n, x: 1n, targetX: 2n, swap: 3n });
const STATE_BYTES = 112;
const FRAME_BYTES = 1048576;
const STATE_BUFFER = Number(exports.nw_frame_alloc(BigInt(STATE_BYTES)));
const FRAME_BUFFER = Number(exports.nw_frame_alloc(BigInt(FRAME_BYTES)));
assert.ok(TASK > 0n && STATE_BUFFER > 0 && FRAME_BUFFER > 0);

function create(options = [3n, 8n, 1n, 6n, 340n, 1150n], seed = 17n) {
  return exports.nw_api_v1_create(TASK, 1n, ...options, seed);
}

function event(handle, kind, timestamp, sequence, code, value = 0n,
               x = 0n, y = 0n) {
  return exports.nw_api_v1_dispatch(handle, kind, BigInt(timestamp),
    BigInt(sequence), code, value, 0n, 0n, x, y, 0n);
}

function keyDown(handle, key, timestamp, sequence) {
  return event(handle, EVENT.keyDown, timestamp, sequence, key);
}

function action(handle, code, timestamp, sequence, value = 0n) {
  return event(handle, EVENT.action, timestamp, sequence, code, value);
}

function advance(handle, timestamp, sequence) {
  return exports.nw_api_v1_advance(handle, BigInt(timestamp), 0n,
    BigInt(sequence));
}

function info(handle, field) {
  return BigInt(exports.nw_api_v1_ncup_monte_info(handle, BigInt(field)));
}

function value(handle, field, at) {
  return BigInt(exports.nw_api_v1_ncup_monte_value(handle, field,
    BigInt(at)));
}

function state(handle) {
  const length = exports.nw_api_v1_read_state(handle,
    BigInt(STATE_BUFFER), BigInt(STATE_BYTES));
  assert.equal(length, BigInt(STATE_BYTES));
  const view = new DataView(instance.exports.memory.buffer, STATE_BUFFER,
    STATE_BYTES);
  assert.equal(view.getUint32(0, true), 0x3152574e);
  assert.equal(view.getUint32(4, true), 1);
  assert.equal(view.getUint32(12, true), 12);
  return Array.from({ length: 12 }, (_, index) =>
    view.getBigInt64(16 + index * 8, true));
}

function frameAt(handle, width = 912, height = 684) {
  const length = exports.nw_api_v1_render(handle, BigInt(FRAME_BUFFER),
    BigInt(FRAME_BYTES), 0n, BigInt(width), BigInt(height));
  assert.ok(length > 0n, `render failed: ${length}`);
  return new Uint8Array(instance.exports.memory.buffer, FRAME_BUFFER,
    Number(length)).slice();
}

function frame(handle) {
  return frameAt(handle);
}

function textIn(frameBytes, expected) {
  return decode(frameBytes).some(({ kind, text }) =>
    kind === Kind.TEXT && text.includes(expected));
}

function controllerSnapshot(handle) {
  return [
    ...Array.from({ length: 21 }, (_, field) => info(handle, field)),
    ...Array.from({ length: 9 }, (_, at) => value(handle, VALUE.order, at)),
    ...Array.from({ length: 9 }, (_, at) => value(handle, VALUE.x, at)),
  ];
}

assert.equal(TASK, 704181153n, "N-Cup Monte keeps its stable task ID");
assert.equal(Number(exports.nw_api_v1_supports(TASK)), 1);
assert.equal(create([2n, 8n, 1n, 6n, 340n, 1150n]), STATUS.badOptions);
assert.equal(create([3n, 2n, 1n, 6n, 340n, 1150n]), STATUS.badOptions);
assert.equal(create([3n, 8n, 2n, 6n, 340n, 1150n]), STATUS.badOptions);
assert.equal(create([3n, 8n, 1n, 3n, 340n, 1150n]), STATUS.badOptions);
assert.equal(create([3n, 8n, 1n, 6n, 350n, 1150n]), STATUS.badOptions);
assert.equal(create([3n, 8n, 1n, 6n, 340n, 1100n]), STATUS.badOptions);

const run = create();
const replay = create();
assert.ok(run > 0n && replay > 0n);
assert.deepEqual(state(run), [0n, 3n, 8n, 1n, 6n, 340n, 1150n,
  1n, 0n, -1n, 0n, 0n]);
const readyFrame = frame(run);
assert.deepEqual(frame(run), readyFrame, "ready rendering is observational");
assert.ok(textIn(readyFrame, "N-Cup Monte"));
assert.ok(textIn(readyFrame, "Press Space to hide the ball"));

// Space and the typed start action are equivalent and preserve deterministic
// source generation for the same seed.
assert.equal(keyDown(run, KEY.space, 100, 0), STATUS.accepted);
assert.equal(action(replay, ACTION.start, 100, 0), STATUS.accepted);
assert.deepEqual(controllerSnapshot(run), controllerSnapshot(replay),
  "same seed gives the same dealt round");
assert.equal(info(run, INFO.phase), PHASE.reveal);
assert.equal(info(run, INFO.round), 1n);
assert.ok(info(run, INFO.ball) >= 0n && info(run, INFO.ball) < 3n);
assert.equal(info(run, INFO.deadlineMs), 1250n);
assert.ok(textIn(frame(run), "Watch the ball"));

// A reveal callback before its exact deadline is ignored.  At the boundary
// the source plans swap_count + cups swaps and exposes the first animation.
assert.equal(advance(run, 1249, 1), STATUS.ignored);
assert.equal(advance(replay, 1249, 1), STATUS.ignored);
assert.equal(info(run, INFO.phase), PHASE.reveal);
assert.equal(advance(run, 1250, 2), STATUS.accepted);
assert.equal(advance(replay, 1250, 2), STATUS.accepted);
assert.deepEqual(controllerSnapshot(run), controllerSnapshot(replay));
assert.equal(info(run, INFO.phase), PHASE.shuffle);
assert.equal(info(run, INFO.swapN), 9n, "source plans swaps plus cup count");
assert.equal(info(run, INFO.swapAt), 0n);
assert.ok(info(run, INFO.swapA) >= 0n && info(run, INFO.swapA) < 3n);
assert.ok(info(run, INFO.swapB) >= 0n && info(run, INFO.swapB) < 3n);
assert.ok(textIn(frame(run), "Watch the ball"));

const firstA = Number(info(run, INFO.swapA));
const firstB = Number(info(run, INFO.swapB));
const firstStartA = value(run, VALUE.x, firstA);
const firstTargetA = value(run, VALUE.targetX, firstA);
assert.notEqual(firstStartA, firstTargetA, "a real swap moves both cups");
assert.equal(advance(run, 1420, 3), STATUS.ignored);
assert.equal(advance(replay, 1420, 3), STATUS.ignored);
assert.equal(info(run, INFO.swapElapsedMs), 170n);
assert.deepEqual(controllerSnapshot(run), controllerSnapshot(replay));
const midFrame = frame(run);
assert.notDeepEqual(midFrame, readyFrame, "shuffle frame is not the ready frame");

// Finish every swap on exact boundaries, checking that each accepted callback
// settles one pair and that the next pair starts at the same timestamp.
let runSequence = 4;
let replaySequence = 4;
let boundaryCount = 0;
let lastBoundary = 0;
while (info(run, INFO.phase) === PHASE.shuffle) {
  const boundary = Number(info(run, INFO.deadlineMs));
  lastBoundary = boundary;
  assert.equal(advance(run, boundary, runSequence), STATUS.accepted);
  assert.equal(advance(replay, boundary, replaySequence), STATUS.accepted);
  runSequence += 1;
  replaySequence += 1;
  boundaryCount += 1;
  assert.deepEqual(controllerSnapshot(run), controllerSnapshot(replay));
  assert.ok(boundaryCount <= 9, "swap loop must terminate");
}
assert.equal(boundaryCount, 9);
assert.equal(info(run, INFO.phase), PHASE.guess);
assert.equal(info(run, INFO.swapAt), info(run, INFO.swapN));
assert.equal(info(run, INFO.swapA), -1n);
assert.equal(info(run, INFO.swapB), -1n);
assert.ok(textIn(frame(run), "Which cup hides the ball?"));

// Pointer input is translated from the final visual slot to the hidden cup
// identity.  The replay uses the equivalent typed action to cross-check the
// same controller result.
const ball = Number(info(run, INFO.ball));
let ballSlot = -1;
for (let slot = 0; slot < 3; slot += 1) {
  if (value(run, VALUE.order, slot) === BigInt(ball)) ballSlot = slot;
}
assert.ok(ballSlot >= 0);
const x = Number(value(run, VALUE.x, ballSlot));
const y = 684 * 0.38 + Math.min(96, 912 / (3 + 2)) * 1.15 / 2;
const guessTime = lastBoundary + 1;
const pointerStatus = event(run, EVENT.pointerDown, guessTime, runSequence, 0n,
  0n, BigInt(Math.round(x * 1000000 / 912)),
  BigInt(Math.round(y * 1000000 / 684)));
assert.equal(pointerStatus, STATUS.accepted);
assert.equal(action(replay, ACTION.choose, guessTime, replaySequence,
  BigInt(ball)), STATUS.accepted);
assert.deepEqual(controllerSnapshot(run), controllerSnapshot(replay));
assert.equal(info(run, INFO.phase), PHASE.result);
assert.equal(info(run, INFO.lastCorrect), 1n);
assert.equal(info(run, INFO.hits), 1n);
assert.equal(info(run, INFO.cups), 4n, "adaptive success raises the cup ladder");
assert.ok(textIn(frame(run), "Caught it"));

// Pointer coordinates are logical protocol coordinates even when the browser
// renders into a DPR-scaled physical canvas. Rendering first at 1551x1163
// must not make a visible cup unclickable.
{
  const dprRun = create();
  assert.equal(keyDown(dprRun, KEY.space, 100, 0), STATUS.accepted);
  let dprSequence = 1;
  while (info(dprRun, INFO.phase) !== PHASE.guess) {
    const deadline = Number(info(dprRun, INFO.deadlineMs));
    assert.ok(deadline > 0, "DPR replay must expose a finite swap deadline");
    assert.equal(advance(dprRun, deadline, dprSequence), STATUS.accepted);
    dprSequence += 1;
  }
  frameAt(dprRun, 1551, 1163);
  const dprBall = Number(info(dprRun, INFO.ball));
  let dprSlot = -1;
  for (let slot = 0; slot < 3; slot += 1) {
    if (value(dprRun, VALUE.order, slot) === BigInt(dprBall)) dprSlot = slot;
  }
  assert.ok(dprSlot >= 0);
  const dprX = Number(value(dprRun, VALUE.x, dprSlot));
  const dprCupWidth = Math.min(96, 1551 / 5);
  const dprY = 1163 * 0.38 + dprCupWidth * 1.15 / 2;
  const dprStatus = event(dprRun, EVENT.pointerDown, 9999, dprSequence, 0n,
    0n, BigInt(Math.round(dprX * 1000000 / 1551)),
    BigInt(Math.round(dprY * 1000000 / 1163)));
  assert.equal(dprStatus, STATUS.accepted,
    "DPR-scaled visible cup must accept its logical pointer coordinate");
  assert.equal(info(dprRun, INFO.phase), PHASE.result);
  assert.equal(exports.nw_api_v1_destroy(dprRun), 0n);
}

// The next round keeps the adapted cup count, resets the permutation, and
// consumes the next source deal from the same persistent MT19937 stream.
assert.equal(keyDown(run, KEY.enter, guessTime + 1, runSequence + 1), STATUS.accepted);
assert.equal(action(replay, ACTION.start, guessTime + 1, replaySequence + 1), STATUS.accepted);
assert.deepEqual(controllerSnapshot(run), controllerSnapshot(replay));
assert.equal(info(run, INFO.phase), PHASE.reveal);
assert.equal(info(run, INFO.round), 2n);
assert.equal(info(run, INFO.cups), 4n);
assert.equal(info(run, INFO.guess), -1n);
assert.equal(info(run, INFO.swapN), 0n);

for (const handle of [run, replay]) {
  assert.equal(exports.nw_api_v1_destroy(handle), 0n);
  assert.equal(exports.nw_api_v1_destroy(handle), 0n, "destroy is idempotent");
}

console.log("PASS: N-Cup Monte source-backed deal, timed smooth swaps, identity mapping, pointer input, adaptive scoring, rendering, options, and cleanup");
