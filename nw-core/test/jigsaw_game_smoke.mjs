import assert from "node:assert/strict";
import fs from "node:fs";
import { fileURLToPath } from "node:url";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";

const wasm = process.env.NWCORE_WASM_PATH ??
  fileURLToPath(new URL("../build/nwcore.wasm", import.meta.url));
const { exports, instance } = await instantiateElisa(fs.readFileSync(wasm), { warn: false });
const task = BigInt(exports.nw_api_v1_task_jigsaw());
const run = exports.nw_api_v1_create(task, 1n, 2n, 1n, 0n, 1n, 0n, 0n, 17n);
assert.ok(run > 0n);
const framePtr = Number(exports.nw_frame_alloc(1048576n));
const info = (field) => Number(exports.nw_api_v1_jigsaw_info(run, BigInt(field)));
const value = (field, at) => Number(exports.nw_api_v1_jigsaw_value(run, BigInt(field), BigInt(at)));
const action = (code, argument, time, sequence) => exports.nw_api_v1_dispatch(
  run, 1n, BigInt(time), BigInt(sequence), BigInt(code), BigInt(argument),
  0n, 0n, 0n, 0n, 0n);
const frame = () => {
  const length = exports.nw_api_v1_render(run, BigInt(framePtr), 1048576n, 0n, 912n, 684n);
  assert.ok(length > 0n);
  return Number(length);
};

assert.equal(info(0), 0); // ready
assert.ok(frame() > 0);
assert.equal(action(0, 0, 100, 0), 1n);
assert.equal(info(0), 1); // solving
const count = info(2) ** 2;
const order = Array.from({ length: count }, (_, at) => value(0, at));
let sequence = 1;
let time = 101;
for (let position = 0; position < count; position++) {
  if (order[position] === position) continue;
  const other = order.indexOf(position, position + 1);
  assert.ok(other >= 0);
  assert.equal(action(1, position, time++, sequence++), 1n);
  assert.equal(action(1, other, time++, sequence++), 1n);
  [order[position], order[other]] = [order[other], order[position]];
}
assert.equal(info(0), 2); // solved
assert.equal(info(8), 1); // verdict
assert.equal(info(9), 1); // one result
assert.ok(frame() > 0);
assert.equal(exports.nw_api_v1_advance(run, 2000n, 1899n, BigInt(sequence)), 1n);
assert.equal(info(0), 3); // one-puzzle session complete
assert.equal(exports.nw_api_v1_destroy(run), 0n);
assert.equal(exports.nw_api_v1_destroy(run), 0n);
console.log("jigsaw_game_smoke: PASS (source permutation, exact swaps, feedback completion, render, and cleanup)");
