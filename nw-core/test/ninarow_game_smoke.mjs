// Common-v1 lifecycle smoke for the source-backed N-in-a-row controller.
// The answer is read only because this test is checking the controller's
// exact generated puzzle and grading semantics; the browser UI reaches the
// same state through cursor movement, pointer selection, and Enter.
import assert from "node:assert/strict";
import fs from "node:fs";
import { fileURLToPath } from "node:url";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { decode, Kind } from "../shells/web/display-list.js";

const root = fileURLToPath(new URL("..", import.meta.url));
const wasm = process.env.NWCORE_WASM_PATH ?? `${root}/build/nwcore.wasm`;
const { exports, instance } = await instantiateElisa(fs.readFileSync(wasm), { warn: false });

const TASK = BigInt(exports.nw_api_v1_task_nina_row());
const STATUS = Object.freeze({ accepted: 1n, ignored: 2n, badOptions: -3n });
const EVENT = Object.freeze({ action: 1n, keyDown: 2n, pointerDown: 5n });
const KEY = Object.freeze({ space: 1n, enter: 2n, right: 5n });
const ACTION = Object.freeze({ start: 0n, select: 1n, up: 2n, down: 3n,
  left: 4n, right: 5n, submit: 6n });
const PHASE = Object.freeze({ ready: 0n, asking: 1n, judged: 2n, done: 3n });
const INFO = Object.freeze({ phase: 0, rung: 1, trial: 2, trials: 3, size: 4,
  choice: 5, answer: 6, pellets: 7, length: 8, verdict: 9,
  showAnswer: 10, adaptive: 11 });
const STATE_BYTES = 112;
const FRAME_BYTES = 1048576;
const STATE_BUFFER = Number(exports.nw_frame_alloc(BigInt(STATE_BYTES)));
const FRAME_BUFFER = Number(exports.nw_frame_alloc(BigInt(FRAME_BYTES)));
assert.ok(TASK > 0n && STATE_BUFFER > 0 && FRAME_BUFFER > 0);

function create(options = [1n, 5n, 0n, 0n, 0n, 3n], seed = 17n) {
  return exports.nw_api_v1_create(TASK, 1n, ...options, seed);
}

function state(handle) {
  const length = exports.nw_api_v1_read_state(handle,
    BigInt(STATE_BUFFER), BigInt(STATE_BYTES));
  assert.equal(length, BigInt(STATE_BYTES));
  const view = new DataView(instance.exports.memory.buffer, STATE_BUFFER, STATE_BYTES);
  assert.equal(view.getUint32(0, true), 0x3152574e);
  assert.equal(view.getUint32(12, true), 12);
  return Array.from({ length: 12 }, (_, index) =>
    view.getBigInt64(16 + index * 8, true));
}

function event(handle, kind, timestamp, sequence, code, value = 0n,
               x = 0n, y = 0n) {
  return exports.nw_api_v1_dispatch(handle, kind, BigInt(timestamp),
    BigInt(sequence), code, value, 0n, 0n, x, y, 0n);
}

function action(handle, code, timestamp, sequence, value = 0n) {
  return event(handle, EVENT.action, timestamp, sequence, code, value);
}

function frame(handle) {
  const length = exports.nw_api_v1_render(handle, BigInt(FRAME_BUFFER),
    BigInt(FRAME_BYTES), 0n, 912n, 684n);
  assert.ok(length > 0n, `render failed: ${length}`);
  return new Uint8Array(instance.exports.memory.buffer, FRAME_BUFFER,
    Number(length)).slice();
}

function verdicts(handle) {
  return decode(frame(handle)).filter(({ kind, color }) =>
    kind === Kind.TEXT && (color === 0x40ff40ff || color === 0xff4040ff))
    .map(({ text, color, b }) => ({ text, color, y: b }));
}

assert.equal(TASK, 3456348074n, "N-in-a-row keeps its stable task ID");
assert.equal(Number(exports.nw_api_v1_supports(TASK)), 1);
assert.equal(create([0n, 5n, 0n, 0n, 0n, 3n]), STATUS.badOptions);
assert.equal(create([1n, 4n, 0n, 0n, 0n, 3n]), STATUS.badOptions);
assert.equal(create([1n, 5n, 7n, 0n, 0n, 3n]), STATUS.badOptions);
assert.equal(create([1n, 5n, 0n, 9n, 0n, 3n]), STATUS.badOptions);
assert.equal(create([1n, 5n, 0n, 0n, 6n, 3n]), STATUS.badOptions);
assert.equal(create([1n, 5n, 0n, 0n, 0n, 4n]), STATUS.badOptions);

const run = create();
assert.ok(run > 0n);
assert.deepEqual(state(run), [0n, 1n, 0n, 5n, 0n, 0n, -1n, 0n, 0n, -1n, 1n, 1n]);
const stableReadyFrame = frame(run);
assert.deepEqual(frame(run), stableReadyFrame, "ready rendering is observational");
assert.ok(decode(stableReadyFrame).some(({ kind, text }) =>
  kind === Kind.TEXT && text === "N-in-a-row"));

assert.equal(event(run, EVENT.keyDown, 1000, 0, KEY.space, 32n), STATUS.accepted);
let values = state(run);
assert.equal(values[INFO.phase], PHASE.asking);
assert.equal(values[INFO.trial], 1n);
assert.ok(values[INFO.size] >= 5n && values[INFO.length] >= 3n);
assert.ok(values[INFO.answer] >= 0n && values[INFO.answer] < values[INFO.size] * values[INFO.size]);
assert.equal(values[INFO.pellets] >= values[INFO.length], true);
const askingFrame = frame(run);
assert.deepEqual(frame(run), askingFrame, "asking rendering does not consume the RNG");
assert.ok(decode(askingFrame).some(({ kind, text }) =>
  kind === Kind.TEXT && text.includes("Find the move that completes")));

// Pointer selection uses the same reference board geometry as the scene. A
// subsequent Enter, rather than the click itself, is the grading event.
assert.equal(event(run, EVENT.pointerDown, 1001, 1, 0n, 1n,
  500000n, 500000n), STATUS.accepted);
assert.equal(action(run, ACTION.select, 1002, 2, values[INFO.answer]), STATUS.accepted);
assert.equal(event(run, EVENT.keyDown, 1003, 3, KEY.enter, 13n), STATUS.accepted);
values = state(run);
assert.equal(values[INFO.phase], PHASE.judged);
assert.equal(values[INFO.verdict], 1n);
assert.equal(values[INFO.showAnswer], 1n);
assert.deepEqual(verdicts(run), [{ text: "Right", color: 0x40ff40ff, y: 60 }]);
assert.ok(decode(frame(run)).some(({ kind, text }) => kind === Kind.TEXT && text === "Right"));

assert.equal(event(run, EVENT.keyDown, 1004, 4, KEY.space, 32n), STATUS.accepted,
  "Space advances from judged feedback to the next position");
assert.equal(state(run)[INFO.phase], PHASE.asking);
assert.equal(state(run)[INFO.trial], 2n);
assert.deepEqual(verdicts(run), []);

// Exercise cursor movement without needing the private answer field: the
// controller accepts a move and preserves the selected empty cell.
const beforeMove = state(run)[INFO.choice];
assert.equal(event(run, EVENT.keyDown, 1005, 5, KEY.right, 39n), STATUS.accepted);
assert.ok(state(run)[INFO.choice] >= beforeMove);
assert.equal(exports.nw_api_v1_destroy(run), 0n);
assert.equal(exports.nw_api_v1_destroy(run), 0n);

// A high custom line length must use the source's board enlargement rule and
// remain renderable through the enlarged frame buffer.
const custom = create([1n, 1n, 5n, 7n, 8n, 0n], 9n);
assert.ok(custom > 0n);
assert.equal(action(custom, ACTION.start, 1, 0), STATUS.accepted);
values = state(custom);
assert.equal(values[INFO.phase], PHASE.asking);
assert.ok(values[INFO.size] >= values[INFO.length]);
assert.ok(values[INFO.size] >= 5n);
assert.ok(frame(custom).length > 0);
assert.equal(exports.nw_api_v1_destroy(custom), 0n);

const missed = create([1n, 1n, 0n, 0n, 0n, 3n], 42n);
assert.equal(action(missed, ACTION.start, 1, 0), STATUS.accepted);
values = state(missed);
assert.notEqual(values[INFO.choice], values[INFO.answer], "the fixture starts on a wrong cell");
assert.equal(event(missed, EVENT.keyDown, 2, 1, KEY.enter, 13n), STATUS.accepted);
const missedVerdict = { text: "No", color: 0xff4040ff, y: 60 };
assert.deepEqual(verdicts(missed), [missedVerdict]);
assert.equal(action(missed, ACTION.start, 3, 2), STATUS.accepted);
assert.deepEqual(verdicts(missed), [missedVerdict], "the summary retains the last verdict");
assert.ok(decode(frame(missed)).some(({ text }) => text === "0 of 1 right, highest level 0"));
assert.equal(action(missed, ACTION.start, 4, 3), STATUS.accepted);
assert.deepEqual(verdicts(missed), []);
assert.equal(exports.nw_api_v1_destroy(missed), 0n);

console.log("PASS: N-in-a-row source-backed lifecycle, exact generator state, input, grading, render, options, and cleanup");
