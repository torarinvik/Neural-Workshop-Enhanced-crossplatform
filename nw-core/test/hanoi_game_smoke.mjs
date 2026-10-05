import assert from "node:assert/strict";
import fs from "node:fs";
import { fileURLToPath } from "node:url";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";

const root = fileURLToPath(new URL("..", import.meta.url));
const wasm = process.env.NWCORE_WASM_PATH ?? `${root}/build/nwcore.wasm`;
const { exports, instance } = await instantiateElisa(fs.readFileSync(wasm), { warn: false });

const TASK = BigInt(exports.nw_api_v1_task_hanoi());
const STATUS = Object.freeze({ accepted: 1n, ignored: 2n, badEvent: -6n });
const EVENT = Object.freeze({ action: 1n, keyDown: 2n });
const KEY = Object.freeze({ space: 1n, enter: 2n });
const ACTION = Object.freeze({ pick0: 1n, pick1: 2n, pick2: 3n });
const STATE_BYTES = 112;
const FRAME_BYTES = 65536;
const STATE_BUFFER = Number(exports.nw_frame_alloc(BigInt(STATE_BYTES)));
const FRAME_BUFFER = Number(exports.nw_frame_alloc(BigInt(FRAME_BYTES)));
assert.ok(STATE_BUFFER > 0 && FRAME_BUFFER > 0);

function create(options = [3n, 1n, 0n, 0n, 0n, 0n], seed = 7n) {
  return exports.nw_api_v1_create(TASK, 1n, ...options, seed);
}

function state(handle) {
  const length = exports.nw_api_v1_read_state(handle,
    BigInt(STATE_BUFFER), BigInt(STATE_BYTES));
  assert.equal(length, BigInt(STATE_BYTES));
  const view = new DataView(instance.exports.memory.buffer, STATE_BUFFER, STATE_BYTES);
  assert.equal(view.getUint32(0, true), 0x3152574e);
  return Array.from({ length: 12 }, (_, index) =>
    view.getBigInt64(16 + index * 8, true));
}

function event(handle, kind, timestamp, sequence, code, value = 0n) {
  return exports.nw_api_v1_dispatch(handle, kind, BigInt(timestamp),
    BigInt(sequence), code, value, 0n, 0n, 0n, 0n, 0n);
}

function action(handle, code, timestamp, sequence) {
  return event(handle, EVENT.action, timestamp, sequence, code);
}

function render(handle) {
  const length = exports.nw_api_v1_render(handle, BigInt(FRAME_BUFFER),
    BigInt(FRAME_BYTES), 0n, 912n, 684n);
  assert.ok(length > 0n);
  return new Uint8Array(instance.exports.memory.buffer, FRAME_BUFFER,
    Number(length)).slice();
}

assert.equal(TASK, 1419634454n, "Tower of Hanoi keeps its stable task ID");
assert.equal(Number(exports.nw_api_v1_supports(TASK)), 1);
assert.equal(create([4n, 4n, 2n, 0n, 0n, 0n]), -3n,
  "round count follows the source option choices");

const run = create();
assert.ok(run > 0n);
assert.deepEqual(state(run), [0n, 0n, 0n, 1n, 0n, 0n, -1n, -1n, 0n, 0n, 0n, 0n]);
assert.equal(event(run, EVENT.keyDown, 100, 0, KEY.space, 32n), STATUS.accepted);
assert.deepEqual(state(run), [1n, 3n, 1n, 1n, 0n, 7n, -1n, -1n, 0n, 0n, 0n, 0n]);

// The source solution for three disks, expressed as peg selections.
const solution = [
  [0, 2], [0, 1], [2, 1], [0, 2], [1, 0], [1, 2], [0, 2],
];
let sequence = 1;
let timestamp = 101;
for (const [source, target] of solution) {
  assert.equal(action(run, ACTION[`pick${source}`], timestamp, sequence++), STATUS.accepted);
  timestamp += 1;
  assert.equal(action(run, ACTION[`pick${target}`], timestamp, sequence++), STATUS.accepted);
  timestamp += 1;
}
const solved = state(run);
assert.equal(solved[0], 2n, "the exact kernel solve enters feedback");
assert.equal(solved[4], 7n);
assert.equal(solved[5], 7n);
assert.equal(solved[7], 1n);
assert.deepEqual(render(run), render(run), "Hanoi rendering is observational and stable");
assert.equal(exports.nw_api_v1_advance(run, 2000n, 0n, BigInt(sequence++)), STATUS.accepted);
assert.equal(state(run)[0], 3n, "feedback advances to the run summary");
assert.equal(exports.nw_api_v1_destroy(run), 0n);

const illegal = create();
assert.equal(event(illegal, EVENT.keyDown, 1, 0, KEY.enter, 13n), STATUS.accepted,
  "Enter is a browser-friendly alias for the source Space start");
assert.equal(action(illegal, ACTION.pick0, 2, 1), STATUS.accepted);
assert.equal(action(illegal, ACTION.pick1, 3, 2), STATUS.accepted);
assert.equal(action(illegal, ACTION.pick0, 4, 3), STATUS.accepted);
assert.equal(state(illegal)[4], 1n, "a legal move increments the move count");
assert.equal(action(illegal, ACTION.pick1, 5, 4), STATUS.accepted,
  "an illegal set-down is consumed as a cancelled selection");
assert.equal(state(illegal)[6], -1n);
assert.equal(state(illegal)[4], 1n, "an illegal set-down is not scored as a move");
assert.equal(exports.nw_api_v1_destroy(illegal), 0n);

console.log("PASS: Tower of Hanoi source-backed lifecycle, exact solution, illegal move, feedback, render, and cleanup");
