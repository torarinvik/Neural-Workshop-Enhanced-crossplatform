// Common-v1 lifecycle smoke for the source-backed Reflex controller.
// The source owns target placement, shrinking clocks, hit/miss accounting, and
// adaptive lifetime.  The host supplies only monotonic time and pointer input.
import assert from "node:assert/strict";
import fs from "node:fs";
import { fileURLToPath } from "node:url";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { decode, Kind } from "../shells/web/display-list.js";

const root = fileURLToPath(new URL("..", import.meta.url));
const wasm = process.env.NWCORE_WASM_PATH ?? `${root}/build/nwcore.wasm`;
const { exports, instance } = await instantiateElisa(fs.readFileSync(wasm), { warn: false });

const TASK = BigInt(exports.nw_api_v1_task_reflex());
const STATUS = Object.freeze({ accepted: 1n, ignored: 2n, badOptions: -3n });
const EVENT = Object.freeze({ action: 1n, keyDown: 2n, pointerDown: 5n });
const KEY = Object.freeze({ space: 1n, enter: 2n });
const ACTION = Object.freeze({ start: 0n });
const PHASE = Object.freeze({ ready: 0n, running: 1n, done: 2n });
const INFO = Object.freeze({
  phase: 0, totalTargets: 1, spawned: 2, maxActive: 3,
  baseLifetimeMs: 4, spawnGapMs: 5, startSize: 6, adaptive: 7,
  lifetimeMs: 8, hits: 9, misses: 10, presented: 11, accuracy: 12,
  meanMs: 13, activeCount: 14, verdict: 15, clockMs: 16,
  nextSpawnMs: 17, lastReactionMs: 18,
});
const VALUE = Object.freeze({ id: 0n, x: 1n, y: 2n, bornMs: 3n,
  lifetimeMs: 4n, remainingPpm: 5n, asset: 6n });
const STATE_BYTES = 112;
const FRAME_BYTES = 1048576;
const STATE_BUFFER = Number(exports.nw_frame_alloc(BigInt(STATE_BYTES)));
const FRAME_BUFFER = Number(exports.nw_frame_alloc(BigInt(FRAME_BYTES)));
assert.ok(TASK > 0n && STATE_BUFFER > 0 && FRAME_BUFFER > 0);

function create(options = [40n, 1600n, 700n, 3n, 130n, 1n], seed = 17n) {
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

function pointer(handle, timestamp, sequence, x, y) {
  return event(handle, EVENT.pointerDown, timestamp, sequence, 0n, 0n,
    BigInt(Math.round(x * 1000000 / 912)),
    BigInt(Math.round(y * 1000000 / 684)));
}

function advance(handle, timestamp, sequence) {
  return exports.nw_api_v1_advance(handle, BigInt(timestamp), 0n,
    BigInt(sequence));
}

function info(handle, field) {
  return BigInt(exports.nw_api_v1_reflex_info(handle, BigInt(field)));
}

function value(handle, field, at) {
  return BigInt(exports.nw_api_v1_reflex_value(handle, field, BigInt(at)));
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
    ...Array.from({ length: 19 }, (_, field) => info(handle, field)),
    ...Object.values(VALUE).map((field) => value(handle, field, 0)),
  ];
}

assert.equal(TASK, 2070613823n, "Reflex keeps its stable task ID");
assert.equal(Number(exports.nw_api_v1_supports(TASK)), 1);
assert.equal(create([9n, 1600n, 700n, 3n, 130n, 1n]), STATUS.badOptions);
assert.equal(create([40n, 300n, 700n, 3n, 130n, 1n]), STATUS.badOptions);
assert.equal(create([40n, 1600n, 100n, 3n, 130n, 1n]), STATUS.badOptions);
assert.equal(create([40n, 1600n, 700n, 7n, 130n, 1n]), STATUS.badOptions);
assert.equal(create([40n, 1600n, 700n, 3n, 120n, 1n]), STATUS.badOptions);
assert.equal(create([40n, 1600n, 700n, 3n, 130n, 2n]), STATUS.badOptions);

const run = create();
const replay = create();
assert.ok(run > 0n && replay > 0n);
assert.deepEqual(state(run), [0n, 40n, 0n, 3n, 0n, 0n, 0n, 0n,
  0n, 1600n, 1n, 0n]);
const readyFrame = frame(run);
assert.deepEqual(frame(run), readyFrame, "ready rendering is observational");
assert.ok(textIn(readyFrame, "Reflex"));
assert.ok(textIn(readyFrame, "Press Space to start"));
assert.equal(info(run, INFO.presented), 0n);
assert.equal(info(run, INFO.verdict), -1n);

// Space and the typed action are the same source start transition, including
// the first deterministic target deal.
assert.equal(keyDown(run, KEY.space, 100, 0), STATUS.accepted);
assert.equal(action(replay, ACTION.start, 100, 0), STATUS.accepted);
assert.equal(advance(run, 100, 1), STATUS.accepted);
assert.equal(advance(replay, 100, 1), STATUS.accepted);
assert.deepEqual(snapshot(run), snapshot(replay), "same seed gives the same target");
assert.equal(info(run, INFO.phase), PHASE.running);
assert.equal(info(run, INFO.spawned), 1n);
assert.equal(info(run, INFO.activeCount), 1n);
assert.equal(value(run, VALUE.id, 0), 0n);
assert.equal(value(run, VALUE.bornMs, 0), 100n);
assert.equal(value(run, VALUE.lifetimeMs, 0), 1600n);
assert.equal(value(run, VALUE.remainingPpm, 0), 1000000n);
assert.equal(value(run, VALUE.asset, 0), 3000n);
const runningFrame = frame(run);
assert.ok(decode(runningFrame).some(({ kind, ref }) =>
  kind === Kind.SPRITE && ref === 3000));
assert.ok(textIn(runningFrame, "Click them before they go"));

// An empty click has no score consequence.  Clicking the target's current
// centre is accepted even though the target is not a browser-side object.
assert.equal(pointer(run, 200, 2, 0, 0), STATUS.ignored);
const targetX = Number(value(run, VALUE.x, 0));
const targetY = Number(value(run, VALUE.y, 0));
assert.equal(pointer(run, 300, 3, targetX / 1000000 * 912,
  targetY / 1000000 * 684), STATUS.accepted);
assert.equal(pointer(replay, 300, 3, targetX / 1000000 * 912,
  targetY / 1000000 * 684), STATUS.accepted);
assert.deepEqual(snapshot(run), snapshot(replay),
  "pointer hit matches the deterministic replay before feedback");
assert.equal(info(run, INFO.hits), 1n);
assert.equal(info(run, INFO.misses), 0n);
assert.equal(info(run, INFO.presented), 1n);
assert.equal(info(run, INFO.accuracy), 100n);
assert.equal(info(run, INFO.meanMs), 200n);
assert.equal(info(run, INFO.lastReactionMs), 200n);
assert.equal(info(run, INFO.lifetimeMs), 1552n,
  "a hit tightens adaptive lifetime by the source factor");
assert.equal(info(run, INFO.verdict), 1n);
assert.ok(textIn(frame(run), "200 ms"));

// An independent run covers the source's exact gone threshold and miss
// adaptation.  A target at 6% life remains clickable; after it falls below
// that threshold, the next advance records one miss.
const missRun = create([10n, 400n, 2000n, 1n, 130n, 1n], 23n);
assert.equal(action(missRun, ACTION.start, 0, 0), STATUS.accepted);
assert.equal(advance(missRun, 0, 1), STATUS.accepted);
assert.equal(value(missRun, VALUE.remainingPpm, 0), 1000000n);
assert.equal(advance(missRun, 375, 2), STATUS.ignored);
assert.equal(info(missRun, INFO.misses), 0n);
assert.equal(advance(missRun, 377, 3), STATUS.accepted);
assert.equal(info(missRun, INFO.misses), 1n);
assert.equal(info(missRun, INFO.lifetimeMs), 432n,
  "a miss eases adaptive lifetime by the source factor");
assert.equal(info(missRun, INFO.verdict), 0n);
assert.ok(textIn(frame(missRun), "Gone"));

// The source finishes only after the last target has both been presented and
// removed.  This also proves that a late callback cannot keep a done run in a
// live phase or spawn beyond the configured target count.
const doneRun = create([10n, 400n, 150n, 1n, 130n, 0n], 29n);
assert.equal(action(doneRun, ACTION.start, 0, 0), STATUS.accepted);
let sequence = 1;
assert.equal(advance(doneRun, 0, sequence++), STATUS.accepted);
for (let now = 1000; now <= 10000; now += 1000) {
  advance(doneRun, now, sequence++);
  if (info(doneRun, INFO.phase) === PHASE.done) break;
}
assert.equal(info(doneRun, INFO.phase), PHASE.done);
assert.equal(info(doneRun, INFO.spawned), 10n);
assert.equal(info(doneRun, INFO.activeCount), 0n);
assert.equal(advance(doneRun, 11000, sequence++), STATUS.ignored);
assert.ok(textIn(frame(doneRun), "of 10"));

for (const handle of [run, replay, missRun, doneRun]) {
  assert.equal(exports.nw_api_v1_destroy(handle), 0n);
  assert.equal(exports.nw_api_v1_destroy(handle), 0n, "destroy is idempotent");
}

console.log("PASS: Reflex source-backed target lifecycle, shrinking threshold, pointer scoring, adaptive timing, rendering, options, and cleanup");
