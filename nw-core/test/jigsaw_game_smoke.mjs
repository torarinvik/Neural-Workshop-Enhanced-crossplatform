import assert from "node:assert/strict";
import fs from "node:fs";
import { fileURLToPath } from "node:url";
import { decode, Kind } from "../shells/web/display-list.js";
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

const frameText = () => {
  const length = frame();
  return decode(new Uint8Array(instance.exports.memory.buffer, framePtr, length))
    .filter(({ kind }) => kind === Kind.TEXT).map(({ text }) => text);
};

assert.equal(info(0), 0); // ready
assert.ok(frame() > 0);
assert.equal(action(0, 0, 100, 0), 1n);
assert.equal(info(0), 1); // solving
const count = info(2) ** 2;
const order = Array.from({ length: count }, (_, at) => value(0, at));
let sequence = 1;
let time = 1101;
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
assert.equal(value(4, 0), 4);
assert.ok(frameText().includes(`Solved in ${info(6)} swaps — the minimum was ${info(5)} — in 1s`));
assert.equal(exports.nw_api_v1_advance(run, 4000n, 3899n, BigInt(sequence)), 1n);
assert.equal(info(0), 3); // one-puzzle session complete
const summary = frameText();
assert.ok(summary.includes("1 puzzles, 100% swap efficiency, 1s each, largest puzzle 4 pieces"));
assert.ok(!summary.some((text) => text.startsWith("Solved in ")));
assert.equal(exports.nw_api_v1_destroy(run), 0n);
assert.equal(exports.nw_api_v1_destroy(run), 0n);
console.log("jigsaw_game_smoke: PASS (source permutation, exact swaps, feedback completion, render, and cleanup)");

// Video Jigsaw uses the same controller with the source 4:3 aspect ratio.
const video = exports.nw_api_v1_create(task, 2n, 3n, 2n, 1n, 1n, 0n, 6n, 17n);
assert.ok(video > 0n);
const videoInfo = (field) => exports.nw_api_v1_jigsaw_info(video, BigInt(field));
let videoSequence = 0n;
const videoEvent = (kind, time, code, value = 0n, x = 0n, y = 0n) =>
  exports.nw_api_v1_dispatch(video, kind, time, videoSequence++, code, value, 0n, 0n, x, y, 0n);
assert.equal(videoEvent(1n, 100n, 0n), 1n);
assert.deepEqual([videoInfo(2), videoInfo(15)], [3n, 2n]);
assert.equal(videoEvent(1n, 200n, 5n, 240n), 1n);
const videoFramePtr = exports.nw_frame_alloc(65536n);
const videoLength = exports.nw_api_v1_render(video, videoFramePtr, 65536n, 0n, 912n, 684n);
assert.ok(videoLength > 0n);
const videoFrame = decode(new Uint8Array(instance.exports.memory.buffer, Number(videoFramePtr), Number(videoLength)));
assert.ok(videoFrame.some(({ text }) => text === "Video Jigsaw"));
const clips = videoFrame.filter(({ kind }) => kind === Kind.SPRITE_FIT);
assert.equal(clips.length, 7);
assert.ok(Math.abs(clips.at(-1).c / clips.at(-1).d - 4 / 3) < 1e-5);
const x = BigInt(Math.round(clips[0].a / 912 * 1e6));
const y = BigInt(Math.round(clips[0].b / 684 * 1e6));
assert.equal(videoEvent(5n, 201n, 0n, 0n, x, y), 1n);
assert.equal(videoInfo(7), 0n);
assert.equal(videoEvent(1n, 202n, 1n, 0n), 1n); // Clear the pick.
const videoOrder = Array.from({ length: 6 }, (_, i) => exports.nw_api_v1_jigsaw_value(video, 0n, BigInt(i)));
for (let i = 0; i < videoOrder.length; i++) {
  if (videoOrder[i] === BigInt(i)) continue;
  const other = videoOrder.indexOf(BigInt(i), i + 1);
  assert.ok(other >= 0);
  assert.equal(videoEvent(1n, 300n, 1n, BigInt(i)), 1n);
  assert.equal(videoEvent(1n, 300n, 1n, BigInt(other)), 1n);
  [videoOrder[i], videoOrder[other]] = [videoOrder[other], videoOrder[i]];
}
assert.equal(videoInfo(0), 2n);
assert.equal(exports.nw_api_v1_advance(video, 2000n, 1700n, videoSequence++), 1n);
assert.deepEqual([videoInfo(2), videoInfo(15)], [3n, 3n]);
assert.equal(videoEvent(1n, 2001n, 6n), 1n);
assert.deepEqual([videoInfo(0), videoInfo(3), videoInfo(9)], [0n, 1n, 1n]);
assert.equal(videoEvent(1n, 2002n, 0n), 1n);
assert.deepEqual([videoInfo(0), videoInfo(2), videoInfo(15)], [1n, 3n, 2n]);
assert.equal(videoEvent(1n, 2003n, 5n, 240n), 1n);
assert.equal(videoEvent(1n, 2004n, 6n), 2n);

exports.nw_frame_free(videoFramePtr);
assert.equal(exports.nw_api_v1_destroy(video), 0n);
console.log("PASS: Video Jigsaw 4:3 layout, pointer hit, and adaptive progression");

const largestVideo = exports.nw_api_v1_create(task, 2n, 3n, 1n, 1n, 1n, 0n, 2500n, 17n);
assert.ok(largestVideo > 0n);
let largestSequence = 0n;
const largestAction = (code, value, now) =>
  exports.nw_api_v1_dispatch(largestVideo, 1n, now, largestSequence++, code, value, 0n, 0n, 0n, 0n, 0n);
assert.equal(largestAction(0n, 0n, 100n), 1n);
assert.equal(largestAction(5n, 240n, 200n), 1n);
const largestInfo = (field) => exports.nw_api_v1_jigsaw_info(largestVideo, BigInt(field));
assert.deepEqual([largestInfo(2), largestInfo(15)], [58n, 44n]);
assert.equal(largestAction(1n, 2551n, 300n), 1n);
assert.equal(largestInfo(7), 2551n);
const largestCapacity = 262144n;
const largestFramePtr = exports.nw_frame_alloc(largestCapacity);
const largestLength = exports.nw_api_v1_render(largestVideo, largestFramePtr, largestCapacity, 0n, 912n, 684n);
assert.ok(largestLength > 0n);
const largestCommands = decode(new Uint8Array(instance.exports.memory.buffer, Number(largestFramePtr), Number(largestLength)));
const fittedRefs = largestCommands.filter(({ kind }) => kind === Kind.SPRITE_FIT).map(({ ref }) => ref);
assert.equal(fittedRefs.pop(), 5500, "the preview keeps its existing sprite ID");
assert.deepEqual(fittedRefs.sort((a, b) => a - b),
  Array.from({ length: 2552 }, (_, index) => 3000 + index + (index >= 2500 ? 1 : 0)));
exports.nw_frame_free(largestFramePtr);
assert.equal(exports.nw_api_v1_destroy(largestVideo), 0n);
console.log("PASS: Video Jigsaw 2,500-piece preset fits a 58×44 grid with unique tile and preview IDs");

for (const [pieces, columns, rows] of [[4000n, 73n, 55n], [1000000n, 320n, 240n]]) {
  const custom = exports.nw_api_v1_create(task, 2n, 3n, 1n, 0n, 0n, 0n, pieces, 17n);
  assert.ok(custom > 0n);
  assert.equal(exports.nw_api_v1_dispatch(custom, 1n, 100n, 0n, 0n, 0n, 0n, 0n, 0n, 0n, 0n), 1n);
  assert.equal(exports.nw_api_v1_dispatch(custom, 1n, 200n, 1n, 5n, 240n, 0n, 0n, 0n, 0n, 0n), 1n);
  assert.deepEqual([2n, 15n].map(field => exports.nw_api_v1_jigsaw_info(custom, field)), [columns, rows]);
  const lastTile = columns * rows - 1n;
  assert.equal(exports.nw_api_v1_dispatch(custom, 1n, 300n, 2n, 1n, lastTile, 0n, 0n, 0n, 0n, 0n), 1n);
  assert.equal(exports.nw_api_v1_jigsaw_info(custom, 7n), lastTile);
  const capacity = 8n * 1024n * 1024n;
  const ptr = exports.nw_frame_alloc(capacity);
  const length = exports.nw_api_v1_render(custom, ptr, capacity, 0n, 912n, 684n);
  assert.ok(length >= 40n * columns * rows);
  const commands = decode(new Uint8Array(instance.exports.memory.buffer, Number(ptr), Number(length)));
  assert.equal(commands.filter(({ kind }) => kind === Kind.SPRITE_FIT).length, Number(columns * rows));
  assert.ok(commands.some(({ kind, ref }) => kind === Kind.SPRITE_FIT && ref === 3001 + Number(lastTile)));
  exports.nw_frame_free(ptr);
  assert.equal(exports.nw_api_v1_destroy(custom), 0n);
}
console.log("PASS: custom Video Jigsaw grids render up to the 320×240 source pixel limit");

for (const [photoSize, expectedColumns, expectedRows] of [[64n, 63n, 64n], [16n, 16n, 16n]]) {
  const photo = exports.nw_api_v1_create(task, 1n, 3n, 1n, 0n, 1n, 0n, 4000n, 17n);
  assert.ok(photo > 0n);
  assert.equal(exports.nw_api_v1_dispatch(photo, 1n, 100n, 0n, 0n, 0n, 0n, 0n, 0n, 0n, 0n), 1n);
  assert.equal(exports.nw_api_v1_dispatch(photo, 1n, 200n, 1n, 5n, photoSize, 0n, 0n, 0n, 0n, 0n), 1n);
  assert.deepEqual([2n, 15n].map(field => exports.nw_api_v1_jigsaw_info(photo, field)),
    [expectedColumns, expectedRows]);
  const capacity = 262144n;
  const ptr = exports.nw_frame_alloc(capacity);
  const length = exports.nw_api_v1_render(photo, ptr, capacity, 0n, 912n, 684n);
  assert.ok(length > 0n);
  const refs = decode(new Uint8Array(instance.exports.memory.buffer, Number(ptr), Number(length)))
    .filter(({ kind }) => kind === Kind.SPRITE_FIT).map(({ ref }) => ref);
  assert.equal(refs.pop(), 5500);
  const tileCount = Number(expectedColumns * expectedRows);
  assert.deepEqual(refs.sort((a, b) => a - b),
    Array.from({ length: tileCount }, (_, i) => 3000 + i + Number(i >= 2500)));
  exports.nw_frame_free(ptr);
  assert.equal(exports.nw_api_v1_destroy(photo), 0n);
}
console.log("PASS: a 4,000-piece photo grid fits large and small square crops");
