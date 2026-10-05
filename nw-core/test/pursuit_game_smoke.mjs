// Common-v1 lifecycle smoke for source-backed Pursuit.
// The controller owns the quarry RNG, continuous on-target score, scheduled
// habits, adaptive multiplier, keyboard steering, pointer position, feedback,
// and the source display-list scene; the test supplies only time and input.
import assert from "node:assert/strict";
import fs from "node:fs";
import { fileURLToPath } from "node:url";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { decode, Kind } from "../shells/web/display-list.js";

const root = fileURLToPath(new URL("..", import.meta.url));
const wasm = process.env.NWCORE_WASM_PATH ?? `${root}/build/nwcore.wasm`;
const { exports, instance } = await instantiateElisa(fs.readFileSync(wasm), { warn: false });

const TASK = BigInt(exports.nw_api_v1_task_pursuit());
const STATUS = Object.freeze({ accepted: 1n, ignored: 2n, badOptions: -3n });
const EVENT = Object.freeze({ action: 1n, keyDown: 2n, pointerMove: 4n });
const KEY = Object.freeze({ space: 1n, enter: 2n, right: 5n });
const ACTION = Object.freeze({ start: 0n, up: 1n, down: 2n, left: 3n, right: 4n });
const PHASE = Object.freeze({ ready: 0n, chasing: 1n, feedback: 2n, done: 3n });
const INFO = Object.freeze({
  phase: 0, speed: 1, surge: 2, turnMs: 3, turnDegrees: 4, size: 5,
  wobble: 6, morphMs: 7, seconds: 8, totalRounds: 9, adaptive: 10,
  round: 11, multiplier: 12, onTimePpm: 13, runTimeMs: 14,
  offSumPx: 15, offSamples: 16, untilMs: 17, verdict: 18,
  resultCount: 19, onPercent: 20, meanOffPx: 21, mouseX: 22,
  mouseY: 23, clockMs: 24,
});
const VALUE = Object.freeze({
  x: 0n, y: 1n, heading: 2n, surge: 3n, radius: 4n, form: 5n,
  color: 6n, nextTurnMs: 7n, nextSurgeMs: 8n, nextResizeMs: 9n,
  nextMorphMs: 10n,
});
const RESULT = Object.freeze({ sharePpm: 100n, driftPx: 101n, multiplierPpm: 102n });
const STATE_BYTES = 112;
const FRAME_BYTES = 1048576;
const STATE_BUFFER = Number(exports.nw_frame_alloc(BigInt(STATE_BYTES)));
const FRAME_BUFFER = Number(exports.nw_frame_alloc(BigInt(FRAME_BYTES)));
assert.ok(TASK > 0n && STATE_BUFFER > 0 && FRAME_BUFFER > 0);

function create(options = [18n, 60n, 900n, 120n, 22n, 4049n], seed = 17n) {
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

function action(handle, code, timestamp, sequence) {
  return event(handle, EVENT.action, timestamp, sequence, code);
}

function pointer(handle, timestamp, sequence, x, y) {
  return event(handle, EVENT.pointerMove, timestamp, sequence, 0n, 0n,
    BigInt(Math.round(x * 1000000 / 912)),
    BigInt(Math.round(y * 1000000 / 684)));
}

function advance(handle, timestamp, sequence) {
  return exports.nw_api_v1_advance(handle, BigInt(timestamp), 0n,
    BigInt(sequence));
}

function info(handle, field) {
  return BigInt(exports.nw_api_v1_pursuit_info(handle, BigInt(field)));
}

function value(handle, field, at = 0) {
  return BigInt(exports.nw_api_v1_pursuit_value(handle, field, BigInt(at)));
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
    ...Array.from({ length: 25 }, (_, field) => info(handle, field)),
    ...Array.from({ length: 11 }, (_, field) => value(handle, BigInt(field))),
    value(handle, RESULT.sharePpm, 0),
    value(handle, RESULT.driftPx, 0),
    value(handle, RESULT.multiplierPpm, 0),
  ];
}

assert.equal(TASK, 250940285n, "Pursuit keeps its stable task ID");
assert.equal(Number(exports.nw_api_v1_supports(TASK)), 1);
assert.equal(create([3n, 60n, 900n, 120n, 22n, 4049n]), STATUS.badOptions);
assert.equal(create([18n, 10n, 900n, 120n, 22n, 4049n]), STATUS.badOptions);
assert.equal(create([18n, 60n, 100n, 120n, 22n, 4049n]), STATUS.badOptions);
assert.equal(create([18n, 60n, 900n, 25n, 22n, 4049n]), STATUS.badOptions);
assert.equal(create([18n, 60n, 900n, 120n, 9n, 4049n]), STATUS.badOptions);
assert.equal(create([18n, 60n, 900n, 120n, 22n, 6272n]), STATUS.badOptions);

const run = create();
const replay = create();
assert.ok(run > 0n && replay > 0n);
assert.deepEqual(state(run), [0n, 0n, 3n, 18n, 0n, 0n, 0n, 0n,
  -1n, 1000000n, 0n, 0n]);
assert.equal(info(run, INFO.speed), 18n);
assert.equal(info(run, INFO.wobble), 40n);
assert.equal(info(run, INFO.morphMs), 2000n);
assert.equal(info(run, INFO.seconds), 20n);
assert.equal(info(run, INFO.totalRounds), 3n);
assert.equal(info(run, INFO.adaptive), 1n);
const readyFrame = frame(run);
assert.deepEqual(frame(run), readyFrame, "ready rendering is observational");
assert.ok(textIn(readyFrame, "Pursuit"));
assert.ok(textIn(readyFrame, "Press Space to start"));

// Space and the explicit source action must produce the same deterministic
// quarry and schedule.
assert.equal(keyDown(run, KEY.space, 0, 0), STATUS.accepted);
assert.equal(action(replay, ACTION.start, 0, 0), STATUS.accepted);
assert.deepEqual(snapshot(run), snapshot(replay));
assert.equal(info(run, INFO.phase), PHASE.chasing);
assert.equal(info(run, INFO.round), 1n);
assert.equal(info(run, INFO.clockMs), 0n);
assert.ok(value(run, VALUE.radius) > 0n);
assert.ok(textIn(frame(run), "Stay on it"));

// Pointer coordinates are physical viewport coordinates expressed through the
// normalized ABI. Arrow nudging uses the same source step as the native UI.
const mouseBefore = info(run, INFO.mouseX);
assert.equal(action(run, ACTION.right, 1, 1), STATUS.accepted);
assert.ok(info(run, INFO.mouseX) > mouseBefore);
// Quarry coordinates are exposed as fixed-point reference pixels, matching the
// other scene controllers; convert them back to physical reference pixels before
// feeding the normalized pointer ABI.
const quarryX = Number(value(run, VALUE.x)) / 1000000 * 912;
const quarryY = Number(value(run, VALUE.y)) / 1000000 * 684;
assert.equal(pointer(run, 2, 2, quarryX, quarryY), STATUS.accepted);
assert.equal(pointer(replay, 2, 1, quarryX, quarryY), STATUS.accepted);
assert.equal(info(run, INFO.mouseX), info(replay, INFO.mouseX));
assert.equal(info(run, INFO.mouseY), info(replay, INFO.mouseY));
assert.equal(event(run, EVENT.pointerMove, 3, 3, 0n, 0n,
  1000001n, 500000n), -6n, "pointer coordinates are bounded");

// A short, non-adaptive run makes the continuous score and exact feedback
// boundary easy to observe without depending on a particular random heading.
const short = create([4n, 0n, 5000n, 30n, 60n, 0n], 23n);
assert.equal(action(short, ACTION.start, 0, 0), STATUS.accepted);
assert.equal(advance(short, 100, 1), STATUS.accepted);
const shortX = Number(value(short, VALUE.x)) / 1000000 * 912;
const shortY = Number(value(short, VALUE.y)) / 1000000 * 684;
assert.equal(pointer(short, 100, 2, shortX, shortY), STATUS.accepted);
assert.equal(advance(short, 200, 3), STATUS.accepted);
assert.ok(info(short, INFO.runTimeMs) > 0n);
assert.ok(info(short, INFO.onTimePpm) > 0n);
assert.equal(info(short, INFO.offSamples), 0n);
assert.equal(pointer(short, 200, 4, 0, 0), STATUS.accepted);
assert.equal(advance(short, 10000, 5), STATUS.accepted);
assert.equal(info(short, INFO.phase), PHASE.feedback);
assert.equal(info(short, INFO.resultCount), 1n);
assert.equal(value(short, RESULT.multiplierPpm, 0), 1000000n);
assert.ok(value(short, RESULT.sharePpm, 0) > 0n);
assert.ok(textIn(frame(short), "On it"));
const feedbackUntil = info(short, INFO.untilMs);
assert.ok(feedbackUntil > 10000n);
assert.equal(advance(short, Number(feedbackUntil), 6), STATUS.accepted);
assert.equal(info(short, INFO.phase), PHASE.done);
assert.equal(info(short, INFO.resultCount), 1n);
assert.ok(textIn(frame(short), "On target"));

for (const handle of [run, replay, short]) {
  assert.equal(exports.nw_api_v1_destroy(handle), 0n);
  assert.equal(exports.nw_api_v1_destroy(handle), 0n, "destroy is idempotent");
}

console.log("PASS: Pursuit source-backed quarry motion, continuous score, pointer/keyboard input, feedback, rendering, options, and cleanup");
