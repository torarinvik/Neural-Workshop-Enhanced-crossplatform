// Common-v1 lifecycle smoke for the source-backed Graph Mapping task.
//
// The controller must keep the generated pair and ring positions alive across
// ABI calls, preserve the source's same/different truth, hide the pair after
// exposure, grade both keyboard and button answers, and render the real graph
// scene instead of the generic task placeholder.
import assert from "node:assert/strict";
import fs from "node:fs";
import { fileURLToPath } from "node:url";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { decode, Kind } from "../shells/web/display-list.js";

const root = fileURLToPath(new URL("..", import.meta.url));
const wasm = process.env.NWCORE_WASM_PATH ?? `${root}/build/nwcore.wasm`;
const { exports, instance } = await instantiateElisa(fs.readFileSync(wasm), { warn: false });

const TASK = BigInt(exports.nw_api_v1_task_graph_mapping());
const STATUS = Object.freeze({ accepted: 1n, ignored: 2n, badOptions: -3n });
const EVENT = Object.freeze({ action: 1n, keyDown: 2n, pointerDown: 5n });
const KEY = Object.freeze({ space: 1n, enter: 2n, left: 3n, right: 5n });
const ACTION = Object.freeze({ start: 0n, same: 1n, different: 2n });
const PHASE = Object.freeze({ ready: 0n, asking: 1n, hidden: 2n, feedback: 3n, done: 4n });
const INFO = Object.freeze({
  phase: 0, startNodes: 1, nodes: 2, density: 3, trial: 4,
  totalTrials: 5, correct: 6, sameTotal: 7, sameRight: 8,
  differentTotal: 9, differentRight: 10, subtle: 11, exposureMs: 12,
  adaptive: 13, feedback: 14, verdict: 15, feedbackUntilMs: 16,
  settledFor: 17, answered: 18, meanMs: 19, askedAtMs: 20, reallySame: 21,
});
const VALUE = Object.freeze({ leftEdge: 0n, rightEdge: 1n, leftX: 2n,
  leftY: 3n, rightX: 4n, rightY: 5n, reallySame: 6n });
const STATE_BYTES = 112;
const FRAME_BYTES = 1048576;
const STATE_BUFFER = Number(exports.nw_frame_alloc(BigInt(STATE_BYTES)));
const FRAME_BUFFER = Number(exports.nw_frame_alloc(BigInt(FRAME_BYTES)));
assert.ok(TASK > 0n && STATE_BUFFER > 0 && FRAME_BUFFER > 0);

function create(options = [6n, 1n, 20n, 0n, 1n, 1n], seed = 17n) {
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
  return BigInt(exports.nw_api_v1_graph_mapping_info(handle, BigInt(field)));
}

function value(handle, field, at = 0) {
  return BigInt(exports.nw_api_v1_graph_mapping_value(handle, field, BigInt(at)));
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
    ...Array.from({ length: 22 }, (_, field) => info(handle, field)),
    ...Array.from({ length: 16 }, (_, at) => value(handle, VALUE.leftX, at)),
    ...Array.from({ length: 16 }, (_, at) => value(handle, VALUE.leftY, at)),
    ...Array.from({ length: 16 }, (_, at) => value(handle, VALUE.rightX, at)),
    ...Array.from({ length: 16 }, (_, at) => value(handle, VALUE.rightY, at)),
    ...Array.from({ length: 120 }, (_, at) => value(handle, VALUE.leftEdge, at)),
    ...Array.from({ length: 120 }, (_, at) => value(handle, VALUE.rightEdge, at)),
  ];
}

assert.equal(TASK, 921237686n, "Graph Mapping keeps its stable task ID");
assert.equal(Number(exports.nw_api_v1_supports(TASK)), 1);
assert.equal(create([3n, 1n, 20n, 0n, 1n, 1n]), STATUS.badOptions);
assert.equal(create([6n, 3n, 20n, 0n, 1n, 1n]), STATUS.badOptions);
assert.equal(create([6n, 1n, 1n, 0n, 1n, 1n]), STATUS.badOptions);
assert.equal(create([6n, 1n, 20n, 1n, 1n, 1n]), STATUS.badOptions);
assert.equal(create([6n, 1n, 20n, 0n, 2n, 1n]), STATUS.badOptions);
assert.equal(create([6n, 1n, 20n, 0n, 1n, 2n]), STATUS.badOptions);

const run = create();
const replay = create();
assert.ok(run > 0n && replay > 0n);
assert.deepEqual(state(run), [0n, 6n, 0n, 20n, 0n, 0n, 0n, 0n,
  0n, -1n, 0n, 0n]);
assert.equal(info(run, INFO.startNodes), 6n);
assert.equal(info(run, INFO.density), 1n);
assert.equal(info(run, INFO.subtle), 1n);
assert.equal(info(run, INFO.adaptive), 1n);
assert.equal(info(run, INFO.feedback), 1n);
const readyFrame = frame(run);
assert.deepEqual(frame(run), readyFrame, "ready rendering is observational");
assert.ok(containsText(readyFrame, "Graph Mapping"));
assert.ok(containsText(readyFrame, "Press Space to start"));

// The source keeps a subtle run above its degree-preserving floor and tells
// the player why when the configured starting rung is too low. This is a
// READY-only message; the controller must not consume a graph or RNG draw to
// produce it.
const lowSubtle = create([4n, 1n, 5n, 0n, 1n, 1n], 19n);
assert.equal(info(lowSubtle, INFO.phase), PHASE.ready);
assert.equal(info(lowSubtle, INFO.trial), 0n);
assert.ok(containsText(frame(lowSubtle), "keeping the counts needs 6 dots"));

// The common key path and typed action path must agree, including the seeded
// graph pair, the independent ring placement, and the answer truth.
assert.equal(keyDown(run, KEY.space, 100, 0), STATUS.accepted);
assert.equal(action(replay, ACTION.start, 100, 0), STATUS.accepted);
assert.equal(info(run, INFO.phase), PHASE.asking);
assert.equal(info(run, INFO.trial), 1n);
assert.equal(info(run, INFO.nodes), 6n);
assert.ok(info(run, INFO.reallySame) === 0n || info(run, INFO.reallySame) === 1n);
assert.ok(info(run, INFO.reallySame) === value(run, VALUE.reallySame));
assert.ok(value(run, VALUE.leftEdge, 0) >= -1n);
assert.ok(value(run, VALUE.leftX, 0) >= 0n && value(run, VALUE.leftX, 0) <= 1000000n);
assert.deepEqual(snapshot(run), snapshot(replay), "same seed gives the same graph pair");
const askingFrame = frame(run);
assert.ok(containsText(askingFrame, "The same network?"));
assert.ok(containsText(askingFrame, "Same"));
assert.ok(containsText(askingFrame, "Different"));

const truth = info(run, INFO.reallySame);
const chosen = truth === 1n ? ACTION.same : ACTION.different;
assert.equal(action(run, chosen, 200, 1), STATUS.accepted);
assert.equal(info(run, INFO.phase), PHASE.feedback);
assert.equal(info(run, INFO.correct), 1n);
assert.equal(info(run, INFO.verdict), 1n);
const feedbackUntil = Number(info(run, INFO.feedbackUntilMs));
assert.equal(advance(run, feedbackUntil - 1, 2), STATUS.ignored);
assert.equal(info(run, INFO.phase), PHASE.feedback);
assert.equal(advance(run, feedbackUntil, 3), STATUS.accepted);
assert.equal(info(run, INFO.phase), PHASE.asking);
assert.equal(info(run, INFO.trial), 2n);

// Exposure removes both graph drawings but keeps the question/buttons alive.
const exposed = create([6n, 1n, 5n, 3000n, 1n, 1n], 23n);
assert.equal(action(exposed, ACTION.start, 100, 0), STATUS.accepted);
assert.equal(advance(exposed, 3099, 1), STATUS.ignored);
assert.equal(info(exposed, INFO.phase), PHASE.asking);
assert.equal(advance(exposed, 3100, 2), STATUS.accepted);
assert.equal(info(exposed, INFO.phase), PHASE.hidden);
assert.equal(containsText(frame(exposed), "The same network?"), true);
const exposedTruth = info(exposed, INFO.reallySame);
assert.equal(action(exposed, exposedTruth === 1n ? ACTION.same : ACTION.different,
  3200, 3), STATUS.accepted);
assert.equal(info(exposed, INFO.phase), PHASE.feedback);

// The source button rectangles are y-up. The common pointer ABI normalises
// the browser event back to that same reference window; clicking the centre
// of either button must be equivalent to a typed answer.
const pointerRun = create([6n, 1n, 5n, 0n, 0n, 1n], 31n);
assert.equal(keyDown(pointerRun, KEY.enter, 100, 0), STATUS.accepted);
const buttonLeft = (912 - 200.64 * 2 - 912 * 0.04) / 2;
const buttonY = 200;
const pointerTruth = info(pointerRun, INFO.reallySame);
const buttonX = pointerTruth === 1n ? buttonLeft + 100 : buttonLeft + 200.64 + 912 * 0.04 + 100;
assert.equal(pointer(pointerRun, 200, 1, buttonX, buttonY), STATUS.accepted);
assert.equal(info(pointerRun, INFO.phase), PHASE.feedback);
assert.equal(info(pointerRun, INFO.verdict), 1n);
assert.ok(containsText(frame(pointerRun), "Graph Mapping"));

for (const handle of [run, replay, exposed, pointerRun, lowSubtle]) {
  assert.equal(exports.nw_api_v1_destroy(handle), 0n);
  assert.equal(exports.nw_api_v1_destroy(handle), 0n, "destroy is idempotent");
}

console.log("PASS: Graph Mapping source-backed pair generation, seeded replay, exposure, answer grading, pointer hit testing, render, feedback, and cleanup");
