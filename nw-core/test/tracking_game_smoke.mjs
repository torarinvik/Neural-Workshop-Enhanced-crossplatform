// Common-v1 lifecycle smoke for source-backed Moving Targets.
// The controller owns the hidden target identities, random deal, wall bounces,
// phase clock, picks, and adaptive round state; the test supplies only time
// and physical pointer coordinates.
import assert from "node:assert/strict";
import fs from "node:fs";
import { fileURLToPath } from "node:url";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { decode, Kind } from "../shells/web/display-list.js";

const root = fileURLToPath(new URL("..", import.meta.url));
const wasm = process.env.NWCORE_WASM_PATH ?? `${root}/build/nwcore.wasm`;
const { exports, instance } = await instantiateElisa(fs.readFileSync(wasm), { warn: false });

const TASK = BigInt(exports.nw_api_v1_task_tracking());
const STATUS = Object.freeze({ accepted: 1n, ignored: 2n, badOptions: -3n });
const EVENT = Object.freeze({ action: 1n, keyDown: 2n, pointerDown: 5n });
const KEY = Object.freeze({ space: 1n, enter: 2n });
const ACTION = Object.freeze({ start: 0n });
const PHASE = Object.freeze({ ready: 0n, cueing: 1n, tracking: 2n,
  picking: 3n, revealing: 4n, done: 5n });
const INFO = Object.freeze({
  phase: 0, balls: 1, startTargets: 2, seconds: 3, speed: 4,
  totalRounds: 5, adaptive: 6, tracked: 7, round: 8,
  deadlineMs: 9, asked: 10, picked: 11, caught: 12,
  roundsDone: 13, totalAsked: 14, totalCaught: 15, verdict: 16,
  lastTickMs: 17, maxTracked: 18,
});
const VALUE = Object.freeze({ id: 0n, x: 1n, y: 2n, vx: 3n, vy: 4n,
  target: 5n, picked: 6n });
const STATE_BYTES = 112;
const FRAME_BYTES = 1048576;
const STATE_BUFFER = Number(exports.nw_frame_alloc(BigInt(STATE_BYTES)));
const FRAME_BUFFER = Number(exports.nw_frame_alloc(BigInt(FRAME_BYTES)));
assert.ok(TASK > 0n && STATE_BUFFER > 0 && FRAME_BUFFER > 0);

function create(options = [8n, 2n, 8n, 16n, 5n, 1n], seed = 17n) {
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

function advance(handle, timestamp, sequence) {
  return exports.nw_api_v1_advance(handle, BigInt(timestamp), 0n,
    BigInt(sequence));
}

function pointer(handle, timestamp, sequence, x, y) {
  return event(handle, EVENT.pointerDown, timestamp, sequence, 0n, 0n,
    BigInt(Math.round(x * 1000000 / 912)),
    BigInt(Math.round(y * 1000000 / 684)));
}

function info(handle, field) {
  return BigInt(exports.nw_api_v1_tracking_info(handle, BigInt(field)));
}

function value(handle, field, at) {
  return BigInt(exports.nw_api_v1_tracking_value(handle, field, BigInt(at)));
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

function controllerSnapshot(handle) {
  return [
    ...Array.from({ length: 19 }, (_, field) => info(handle, field)),
    ...Array.from({ length: 8 }, (_, at) => value(handle, VALUE.x, at)),
    ...Array.from({ length: 8 }, (_, at) => value(handle, VALUE.y, at)),
    ...Array.from({ length: 8 }, (_, at) => value(handle, VALUE.target, at)),
  ];
}

assert.equal(TASK, 228173702n, "Moving Targets keeps its stable task ID");
assert.equal(Number(exports.nw_api_v1_supports(TASK)), 1);
assert.equal(create([2n, 2n, 8n, 16n, 5n, 1n]), STATUS.badOptions);
assert.equal(create([8n, 7n, 8n, 16n, 5n, 1n]), STATUS.badOptions);
assert.equal(create([8n, 2n, 4n, 16n, 5n, 1n]), STATUS.badOptions);
assert.equal(create([8n, 2n, 8n, 10n, 5n, 1n]), STATUS.badOptions);
assert.equal(create([8n, 2n, 8n, 16n, 4n, 1n]), STATUS.badOptions);
assert.equal(create([8n, 2n, 8n, 16n, 5n, 2n]), STATUS.badOptions);

const run = create();
const replay = create();
assert.ok(run > 0n && replay > 0n);
assert.deepEqual(state(run), [0n, 0n, 5n, 8n, 0n, 2n, 0n, 0n,
  0n, 0n, -1n, 0n]);
const readyFrame = frame(run);
assert.deepEqual(frame(run), readyFrame, "ready rendering is observational");
assert.ok(textIn(readyFrame, "Moving Targets"));
assert.ok(textIn(readyFrame, "Press Space to start"));

// Space and the source action start the same deterministic deal.
assert.equal(keyDown(run, KEY.space, 100, 0), STATUS.accepted);
assert.equal(action(replay, ACTION.start, 100, 0), STATUS.accepted);
assert.deepEqual(controllerSnapshot(run), controllerSnapshot(replay));
assert.equal(info(run, INFO.phase), PHASE.cueing);
assert.equal(info(run, INFO.round), 1n);
assert.equal(info(run, INFO.asked), 2n);
assert.equal(info(run, INFO.deadlineMs), 2100n);
assert.ok(textIn(frame(run), "Follow the 2 coloured balls"));

// The cue boundary does not move the flock.  The first tracking tick does,
// and a tracking deadline moves once more before opening the pick phase.
const cueSnapshot = controllerSnapshot(run);
assert.equal(advance(run, 2099, 1), STATUS.ignored);
assert.equal(advance(replay, 2099, 1), STATUS.ignored);
assert.equal(advance(run, 2100, 2), STATUS.accepted);
assert.equal(advance(replay, 2100, 2), STATUS.accepted);
assert.deepEqual(controllerSnapshot(run), controllerSnapshot(replay));
assert.equal(info(run, INFO.phase), PHASE.tracking);
assert.deepEqual(controllerSnapshot(run).slice(-24), cueSnapshot.slice(-24),
  "cue-to-tracking transition itself does not move balls");
const beforeMove = controllerSnapshot(run);
assert.equal(advance(run, 2200, 3), STATUS.accepted);
assert.equal(advance(replay, 2200, 3), STATUS.accepted);
assert.deepEqual(controllerSnapshot(run), controllerSnapshot(replay));
assert.notDeepEqual(controllerSnapshot(run).slice(-24), beforeMove.slice(-24),
  "tracking advances normalized positions deterministically");
assert.ok(textIn(frame(run), "Keep watching"));

assert.equal(advance(run, 10100, 4), STATUS.accepted);
assert.equal(advance(replay, 10100, 4), STATUS.accepted);
assert.equal(info(run, INFO.phase), PHASE.picking);
assert.ok(textIn(frame(run), "Click the balls you followed"));

// Select both hidden targets by their current physical centers.  The pointer
// path receives coordinates only; it must find the stable target identity.
let sequence = 5;
let picked = 0;
for (let at = 0; at < 8; at += 1) {
  if (value(run, VALUE.target, at) !== 1n) continue;
  const x = Number(value(run, VALUE.x, at)) / 1000000 * 912;
  const y = Number(value(run, VALUE.y, at)) / 1000000 * 684;
  assert.equal(pointer(run, 10100, sequence++, x, y), STATUS.accepted);
  assert.equal(pointer(replay, 10100, sequence++, x, y), STATUS.accepted);
  picked += 1;
}
assert.equal(picked, 2);
assert.equal(info(run, INFO.phase), PHASE.revealing);
assert.equal(info(run, INFO.caught), 2n);
assert.equal(info(run, INFO.totalCaught), 2n);
assert.equal(info(run, INFO.tracked), 3n, "adaptive success raises the target count");
assert.equal(info(run, INFO.verdict), 1n);
assert.deepEqual(controllerSnapshot(run), controllerSnapshot(replay));
assert.ok(textIn(frame(run), "All 2"));

// A second run proves a wrong pick scores a miss and lowers the next target
// count.  With three balls and two targets, choosing one target and the one
// distractor reaches the requested pick count with one caught target.
const missRun = create([3n, 2n, 3n, 8n, 3n, 1n], 23n);
assert.equal(action(missRun, ACTION.start, 0, 0), STATUS.accepted);
assert.equal(advance(missRun, 2000, 1), STATUS.accepted);
assert.equal(advance(missRun, 5000, 2), STATUS.accepted);
let targetAt = -1;
let distractorAt = -1;
for (let at = 0; at < 3; at += 1) {
  if (value(missRun, VALUE.target, at) === 1n) targetAt = at;
  else distractorAt = at;
}
assert.ok(targetAt >= 0 && distractorAt >= 0);
let missSequence = 3;
for (const at of [targetAt, distractorAt]) {
  const x = Number(value(missRun, VALUE.x, at)) / 1000000 * 912;
  const y = Number(value(missRun, VALUE.y, at)) / 1000000 * 684;
  assert.equal(pointer(missRun, 5000, missSequence++, x, y), STATUS.accepted);
}
assert.equal(info(missRun, INFO.verdict), 0n);
assert.equal(info(missRun, INFO.caught), 1n);
assert.equal(info(missRun, INFO.tracked), 1n);

// Finish a short non-adaptive run at exact phase deadlines, including the
// revealing boundary and the final DONE transition.
const doneRun = create([3n, 1n, 3n, 8n, 3n, 0n], 29n);
assert.equal(action(doneRun, ACTION.start, 0, 0), STATUS.accepted);
let doneSequence = 1;
while (info(doneRun, INFO.phase) !== PHASE.done) {
  const phase = info(doneRun, INFO.phase);
  if (phase === PHASE.cueing || phase === PHASE.tracking || phase === PHASE.revealing) {
    advance(doneRun, Number(info(doneRun, INFO.deadlineMs)), doneSequence++);
  } else if (phase === PHASE.picking) {
    let target = -1;
    for (let at = 0; at < 3; at += 1) {
      if (value(doneRun, VALUE.target, at) === 1n) target = at;
    }
    assert.ok(target >= 0);
    const x = Number(value(doneRun, VALUE.x, target)) / 1000000 * 912;
    const y = Number(value(doneRun, VALUE.y, target)) / 1000000 * 684;
    assert.equal(pointer(doneRun, Number(info(doneRun, INFO.lastTickMs)), doneSequence++, x, y), STATUS.accepted);
  } else {
    assert.fail(`unexpected phase ${phase}`);
  }
  assert.ok(doneSequence < 40, "short run must terminate");
}
assert.equal(info(doneRun, INFO.phase), PHASE.done);
assert.equal(info(doneRun, INFO.roundsDone), 3n);
assert.equal(info(doneRun, INFO.totalAsked), 3n);
assert.equal(info(doneRun, INFO.totalCaught), 3n);
assert.ok(textIn(frame(doneRun), "of 3 balls held over 3 rounds"));
assert.equal(advance(doneRun, 30000, doneSequence++), STATUS.ignored);

for (const handle of [run, replay, missRun, doneRun]) {
  assert.equal(exports.nw_api_v1_destroy(handle), 0n);
  assert.equal(exports.nw_api_v1_destroy(handle), 0n, "destroy is idempotent");
}

console.log("PASS: Moving Targets source-backed scatter, phase clock, bouncing identity, pointer picks, adaptive scoring, rendering, options, and cleanup");
