// Common-v1 lifecycle smoke for source-backed Out of Sight.
// The controller owns the flock identities, blind geometry, crossings,
// question schedule, hidden targets, scoring, and adaptive ladder.  The host
// supplies only time, the two source answer actions, and a render request.
import assert from "node:assert/strict";
import fs from "node:fs";
import { fileURLToPath } from "node:url";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { decode, Kind } from "../shells/web/display-list.js";

const root = fileURLToPath(new URL("..", import.meta.url));
const wasm = process.env.NWCORE_WASM_PATH ?? `${root}/build/nwcore.wasm`;
const { exports, instance } = await instantiateElisa(fs.readFileSync(wasm), { warn: false });

const TASK = BigInt(exports.nw_api_v1_task_out_of_sight());
const STATUS = Object.freeze({ accepted: 1n, ignored: 2n, badOptions: -3n });
const EVENT = Object.freeze({ action: 1n, keyDown: 2n });
const KEY = Object.freeze({ space: 1n, enter: 2n });
const ACTION = Object.freeze({ start: 0n, mine: 1n, notMine: 2n });
const PHASE = Object.freeze({ ready: 0n, cueing: 1n, tracking: 2n,
  revealing: 3n, done: 4n });
const INFO = Object.freeze({
  phase: 0, dots: 1, startTargets: 2, speed: 3, blinds: 4,
  blindWidth: 5, crossMs: 6, probes: 7, totalRounds: 8, adaptive: 9,
  round: 10, held: 11, hits: 12, wrong: 13, late: 14,
  reactionCount: 15, meanMs: 16, accuracy: 17, mostHeld: 18,
  resultCount: 19, probesDone: 20, probe: 21, probeAtMs: 22,
  probeUntilMs: 23, verdict: 24, untilMs: 25, clockMs: 26,
  nextProbeMs: 27, nextCrossMs: 28, roundRight: 29,
});
const VALUE = Object.freeze({ x: 0n, y: 1n, vx: 2n, vy: 3n, target: 4n,
  busyUntilMs: 5n, riskyUntilMs: 6n, wasHidden: 7n });
const RESULT = Object.freeze({ held: 200n, asked: 201n, right: 202n });
const STATE_BYTES = 112;
const FRAME_BYTES = 1048576;
const STATE_BUFFER = Number(exports.nw_frame_alloc(BigInt(STATE_BYTES)));
const FRAME_BUFFER = Number(exports.nw_frame_alloc(BigInt(FRAME_BYTES)));
assert.ok(TASK > 0n && STATE_BUFFER > 0 && FRAME_BUFFER > 0);

function create(options = [8n, 2n, 16n, 1600n, 3n, 476n], seed = 17n) {
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
  return BigInt(exports.nw_api_v1_out_of_sight_info(handle, BigInt(field)));
}

function value(handle, field, at) {
  return BigInt(exports.nw_api_v1_out_of_sight_value(handle, field, BigInt(at)));
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

function textIn(bytes, expected) {
  return decode(bytes).some(({ kind, text }) =>
    kind === Kind.TEXT && text.includes(expected));
}

function snapshot(handle) {
  return [
    ...Array.from({ length: 30 }, (_, field) => info(handle, field)),
    ...Array.from({ length: 8 }, (_, field) => value(handle, BigInt(field), 0)),
    ...Array.from({ length: 8 }, (_, field) => value(handle, BigInt(field), 1)),
  ];
}

assert.equal(TASK, 1771687311n, "Out of Sight keeps its stable task ID");
assert.equal(Number(exports.nw_api_v1_supports(TASK)), 1);
assert.equal(create([2n, 2n, 16n, 1600n, 3n, 476n]), STATUS.badOptions);
const valid = create([8n, 1n, 16n, 1600n, 3n, 476n]);
assert.ok(valid > 0n);
assert.equal(exports.nw_api_v1_destroy(valid), 0n);
const badTarget = create([8n, 1n, 16n, 1600n, 3n, 476n]);
assert.ok(badTarget > 0n);
assert.equal(exports.nw_api_v1_destroy(badTarget), 0n);
assert.equal(create([8n, 2n, 7n, 1600n, 3n, 476n]), STATUS.badOptions);
assert.equal(create([8n, 2n, 16n, 700n, 3n, 476n]), STATUS.badOptions);
assert.equal(create([8n, 2n, 16n, 1600n, 7n, 476n]), STATUS.badOptions);
assert.equal(create([8n, 2n, 16n, 1600n, 3n, 672n]), STATUS.badOptions);

const run = create();
const replay = create();
assert.ok(run > 0n && replay > 0n);
assert.deepEqual(state(run), [0n, 0n, 5n, 8n, 2n, 0n, 6n, 0n, 0n, 0n,
  -1n, 0n]);
assert.equal(info(run, INFO.blindWidth), 9n);
assert.equal(info(run, INFO.probes), 6n);
assert.equal(info(run, INFO.totalRounds), 5n);
assert.equal(info(run, INFO.adaptive), 1n);
const ready = frame(run);
assert.deepEqual(frame(run), ready, "ready rendering is observational");
assert.ok(textIn(ready, "Out of Sight"));
assert.ok(textIn(ready, "Press Space to start"));

assert.equal(keyDown(run, KEY.space, 0, 0), STATUS.accepted);
assert.equal(action(replay, ACTION.start, 0, 0), STATUS.accepted);
assert.deepEqual(snapshot(run), snapshot(replay));
assert.equal(info(run, INFO.phase), PHASE.cueing);
assert.equal(info(run, INFO.round), 1n);
assert.equal(info(run, INFO.held), 2n);
assert.equal(info(run, INFO.dots), 8n);
assert.equal(value(run, VALUE.target, 0) === 0n || value(run, VALUE.target, 0) === 1n, true);
assert.ok(textIn(frame(run), "Remember your dots"));

// The two-second cue boundary changes to tracking without changing the RNG
// stream. Answer the first two generated probes using only the controller's
// exposed target identity; this exercises the source action boundary and the
// hidden-state copy without replacing the task's mechanics in the test.
assert.equal(advance(run, 2000, 1), STATUS.accepted);
assert.equal(advance(replay, 2000, 1), STATUS.accepted);
assert.equal(info(run, INFO.phase), PHASE.tracking);
assert.deepEqual(snapshot(run), snapshot(replay));
let now = 2000;
let sequence = 2;
let answered = 0;
while (answered < 2 && now < 30000) {
  now += 100;
  assert.equal(advance(run, now, sequence++), STATUS.accepted);
  assert.equal(advance(replay, now, sequence++), STATUS.accepted);
  const probe = Number(info(run, INFO.probe));
  if (probe < 0 || info(run, INFO.verdict) >= 0n) continue;
  const mine = value(run, VALUE.target, probe) !== 0n;
  assert.equal(action(run, mine ? ACTION.mine : ACTION.notMine, now, sequence++), STATUS.accepted);
  assert.equal(action(replay, mine ? ACTION.mine : ACTION.notMine, now, sequence++), STATUS.accepted);
  assert.equal(info(run, INFO.hits), BigInt(answered + 1));
  assert.deepEqual(snapshot(run), snapshot(replay));
  answered += 1;
}
assert.equal(answered, 2, "the source should raise two answerable probes");
assert.equal(info(run, INFO.reactionCount), 2n);
assert.ok(info(run, INFO.meanMs) >= 0n);
assert.ok(textIn(frame(run), "Out of Sight"));

// Use a compact non-adaptive configuration to verify a complete round and
// result row without waiting for the five-round default.  Packed 0 means
// width 4, two probes, one round, and adaptive off.
const short = create([3n, 1n, 75n, 0n, 0n, 0n], 23n);
assert.ok(short > 0n);
assert.equal(action(short, ACTION.start, 0, 0), STATUS.accepted);
let shortNow = 2000;
let shortSeq = 1;
assert.equal(advance(short, shortNow, shortSeq++), STATUS.accepted);
let shortAnswers = 0;
while (info(short, INFO.phase) === PHASE.tracking && shortNow < 30000) {
  shortNow += 100;
  assert.equal(advance(short, shortNow, shortSeq++), STATUS.accepted);
  const probe = Number(info(short, INFO.probe));
  if (probe >= 0 && info(short, INFO.verdict) < 0n) {
    const mine = value(short, VALUE.target, probe) !== 0n;
    assert.equal(action(short, mine ? ACTION.mine : ACTION.notMine,
      shortNow, shortSeq++), STATUS.accepted);
    shortAnswers += 1;
  }
}
assert.ok(shortAnswers >= 1);
while (info(short, INFO.phase) === PHASE.revealing && shortNow < 30000) {
  shortNow += 100;
  advance(short, shortNow, shortSeq++);
}
assert.equal(info(short, INFO.phase), PHASE.done);
assert.equal(info(short, INFO.resultCount), 1n);
assert.equal(value(short, RESULT.asked, 0), 2n);
assert.equal(value(short, RESULT.right, 0), 2n);
assert.ok(textIn(frame(short), "accuracy"));

for (const handle of [run, replay, short]) {
  assert.equal(exports.nw_api_v1_destroy(handle), 0n);
  assert.equal(exports.nw_api_v1_destroy(handle), 0n, "destroy is idempotent");
}

console.log("PASS: Out of Sight source-backed flock, blinds, crossings, probes, scoring, rendering, options, and cleanup");
