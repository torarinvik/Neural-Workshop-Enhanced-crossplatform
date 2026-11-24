// Common-v1 lifecycle smoke for the source-backed Traveling Salesman task.
// The controller owns the seeded scatter, Held-Karp optimum, route editing,
// adaptive ladder, timed feedback, and source-shaped render. The host supplies
// only monotonic event time and normalized pointer coordinates.
import assert from "node:assert/strict";
import fs from "node:fs";
import { fileURLToPath } from "node:url";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { decode, Kind } from "../shells/web/display-list.js";

const root = fileURLToPath(new URL("..", import.meta.url));
const wasm = process.env.NWCORE_WASM_PATH ?? `${root}/build/nwcore.wasm`;
const { exports, instance } = await instantiateElisa(fs.readFileSync(wasm), { warn: false });

const TASK = BigInt(exports.nw_api_v1_task_salesman());
const STATUS = Object.freeze({ accepted: 1n, ignored: 2n, badOptions: -3n });
const EVENT = Object.freeze({ action: 1n, keyDown: 2n, pointerDown: 5n });
const KEY = Object.freeze({ space: 1n, enter: 2n });
const ACTION = Object.freeze({ start: 0n, pick: 1n });
const PHASE = Object.freeze({ ready: 0n, touring: 1n, toured: 2n, done: 3n });
const INFO = Object.freeze({
  phase: 0, startCities: 1, cityCount: 2, trialCities: 3, round: 4,
  totalRounds: 5, routeCount: 6, bestCount: 7, verdict: 8, adaptive: 9,
  showBest: 10, feedbackUntilMs: 11, takenMs: 12, resultCount: 13,
  totalTimeMs: 14, bestCities: 15, closenessPercent: 16,
  startedAtMs: 17, cityStorageCount: 18, bestLengthPpm: 19,
  playerLengthPpm: 20,
});
const VALUE = Object.freeze({ x: 0n, y: 1n, route: 2n, best: 3n,
  bestLengthPpm: 4n, playerLengthPpm: 5n });
const STATE_BYTES = 112;
const FRAME_BYTES = 1048576;
const STATE_BUFFER = Number(exports.nw_frame_alloc(BigInt(STATE_BYTES)));
const FRAME_BUFFER = Number(exports.nw_frame_alloc(BigInt(FRAME_BYTES)));
assert.ok(TASK > 0n && STATE_BUFFER > 0 && FRAME_BUFFER > 0);

function create(options = [7n, 5n, 1n, 1n, 0n, 0n], seed = 17n) {
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

function info(handle, field) {
  return BigInt(exports.nw_api_v1_salesman_info(handle, BigInt(field)));
}

function value(handle, field, at = 0) {
  return BigInt(exports.nw_api_v1_salesman_value(handle, field, BigInt(at)));
}

function frame(handle) {
  const length = exports.nw_api_v1_render(handle, BigInt(FRAME_BUFFER),
    BigInt(FRAME_BYTES), 0n, 912n, 684n);
  assert.ok(length > 0n, `render failed: ${length}`);
  return new Uint8Array(instance.exports.memory.buffer, FRAME_BUFFER,
    Number(length)).slice();
}

function containsText(bytes, expected) {
  return decode(bytes).some(({ kind, text }) =>
    kind === Kind.TEXT && text.includes(expected));
}

function snapshot(handle) {
  return [
    ...Array.from({ length: 21 }, (_, field) => info(handle, field)),
    ...Array.from({ length: 7 }, (_, at) => value(handle, VALUE.x, at)),
    ...Array.from({ length: 7 }, (_, at) => value(handle, VALUE.y, at)),
    ...Array.from({ length: 7 }, (_, at) => value(handle, VALUE.best, at)),
  ];
}

assert.equal(TASK, 2749539657n, "Traveling Salesman keeps its stable task ID");
assert.equal(Number(exports.nw_api_v1_supports(TASK)), 1);
assert.equal(create([4n, 5n, 1n, 1n, 0n, 0n]), STATUS.badOptions);
assert.equal(create([7n, 4n, 1n, 1n, 0n, 0n]), STATUS.badOptions);
assert.equal(create([7n, 5n, 2n, 1n, 0n, 0n]), STATUS.badOptions);
assert.equal(create([7n, 5n, 1n, 2n, 0n, 0n]), STATUS.badOptions);
assert.equal(create([7n, 5n, 1n, 1n, 1n, 0n]), STATUS.badOptions);

const run = create();
const replay = create();
assert.ok(run > 0n && replay > 0n);
assert.deepEqual(state(run), [0n, 7n, 7n, 7n, 0n, 5n, 0n, 0n,
  -1n, 1n, 1n, 0n]);
const readyFrame = frame(run);
assert.deepEqual(frame(run), readyFrame, "ready rendering is observational");
assert.ok(containsText(readyFrame, "Traveling Salesman"));
assert.ok(containsText(readyFrame, "Press Space to start"));

// The key path and typed action path must produce the same source state.
assert.equal(keyDown(run, KEY.space, 100, 0), STATUS.accepted);
assert.equal(action(replay, ACTION.start, 100, 0), STATUS.accepted);
assert.equal(info(run, INFO.phase), PHASE.touring);
assert.equal(info(run, INFO.round), 1n);
assert.equal(info(run, INFO.cityCount), 7n);
assert.equal(info(run, INFO.trialCities), 7n);
assert.equal(info(run, INFO.bestCount), 7n);
assert.ok(info(run, INFO.bestLengthPpm) > 0n);
assert.deepEqual(snapshot(run), snapshot(replay), "same seed gives the same city tour");
const touringFrame = frame(run);
assert.ok(containsText(touringFrame, "Traveling Salesman"));
assert.ok(containsText(touringFrame, "Visit every city"));

// The final city settles exactly once. Picking the most recently picked city
// again performs the source undo operation and does not add a duplicate.
assert.equal(action(run, ACTION.pick, 200, 1, 0n), STATUS.accepted);
assert.equal(info(run, INFO.routeCount), 1n);
assert.equal(action(run, ACTION.pick, 300, 2, 0n), STATUS.accepted);
assert.equal(info(run, INFO.routeCount), 0n);
assert.equal(action(run, ACTION.pick, 400, 3, 0n), STATUS.accepted);
for (let city = 1; city < 7; city += 1) {
  assert.equal(action(run, ACTION.pick, 400 + city * 100, 3 + city,
    BigInt(city)), STATUS.accepted);
}
// Replay the same effective route without the undo on a separate handle.
let sequence = 1;
let timestamp = 400;
for (let city = 0; city < 7; city += 1) {
  assert.equal(action(replay, ACTION.pick, timestamp, sequence++, BigInt(city)),
    STATUS.accepted);
  timestamp += 100;
}
assert.deepEqual(snapshot(run), snapshot(replay), "undo then route equals direct route");
assert.equal(info(run, INFO.phase), PHASE.toured);
assert.equal(info(run, INFO.routeCount), 7n);
assert.equal(info(run, INFO.resultCount), 1n);
assert.ok(info(run, INFO.takenMs) > 0n);
assert.ok(info(run, INFO.playerLengthPpm) >= info(run, INFO.bestLengthPpm));
assert.equal(info(run, INFO.verdict) === 0n || info(run, INFO.verdict) === 1n, true);
assert.ok(containsText(frame(run), "shortest route"));

const feedbackUntil = Number(info(run, INFO.feedbackUntilMs));
assert.equal(advance(run, feedbackUntil - 1, 10), STATUS.ignored);
assert.equal(info(run, INFO.phase), PHASE.toured);
assert.equal(advance(run, feedbackUntil, 11), STATUS.accepted);
assert.equal(info(run, INFO.phase), PHASE.touring);
assert.equal(info(run, INFO.round), 2n);

// Pointer coordinates use the same scene transform as SceneSalesman. This
// validates that a browser click, not only a typed synthetic city index, can
// drive the route.
const pointerRun = create([5n, 3n, 0n, 1n, 0n, 0n], 31n);
assert.equal(keyDown(pointerRun, KEY.enter, 100, 0), STATUS.accepted);
for (let city = 0; city < 5; city += 1) {
  const x = 912 * 0.06 + Number(value(pointerRun, VALUE.x, city)) / 1000000 * (912 * 0.88);
  const y = 56 + Number(value(pointerRun, VALUE.y, city)) / 1000000 * (584 - 56);
  assert.equal(pointer(pointerRun, 200 + city, city + 1, x, y), STATUS.accepted);
}
assert.equal(info(pointerRun, INFO.routeCount), 5n);
assert.equal(info(pointerRun, INFO.phase), PHASE.toured);
assert.ok(containsText(frame(pointerRun), "Traveling Salesman"));

function verdicts(handle) {
  return decode(frame(handle)).filter(({ kind, color }) =>
    kind === Kind.TEXT && (color === 0x40ff40ff || color === 0xff4040ff))
    .map(({ text, color, b }) => ({ text, color, y: b }));
}

assert.equal(verdicts(pointerRun)[0].color, 0xff4040ff);
let finalSequence = 6;
let finalTime;
for (let round = 2; round <= 3; round += 1) {
  finalTime = Number(info(pointerRun, INFO.feedbackUntilMs));
  assert.equal(advance(pointerRun, finalTime, finalSequence++), STATUS.accepted);
  assert.deepEqual(verdicts(pointerRun), [], "the next route clears the verdict");
  const optimum = Array.from({ length: 5 }, (_, city) => value(pointerRun, VALUE.best, city));
  for (const city of optimum) {
    assert.equal(action(pointerRun, ACTION.pick, ++finalTime, finalSequence++, city), STATUS.accepted);
  }
}
const finalVerdict = { text: "The shortest route there is — in 0s", color: 0x40ff40ff, y: 60 };
assert.deepEqual(verdicts(pointerRun), [finalVerdict]);
finalTime = Number(info(pointerRun, INFO.feedbackUntilMs));
assert.equal(advance(pointerRun, finalTime, finalSequence++), STATUS.accepted);
assert.equal(info(pointerRun, INFO.phase), PHASE.done);
assert.ok(containsText(frame(pointerRun), "3 routes, "));
assert.deepEqual(verdicts(pointerRun), [finalVerdict], "the summary retains the final route verdict");
assert.equal(keyDown(pointerRun, KEY.enter, finalTime + 1, finalSequence++), STATUS.accepted);
assert.deepEqual(verdicts(pointerRun), [], "a new run clears the verdict");

for (const handle of [run, replay, pointerRun]) {
  assert.equal(exports.nw_api_v1_destroy(handle), 0n);
  assert.equal(exports.nw_api_v1_destroy(handle), 0n, "destroy is idempotent");
}

console.log("PASS: Traveling Salesman source-backed scatter, exact optimum, route undo/pointer input, feedback, render, replay, and cleanup");
