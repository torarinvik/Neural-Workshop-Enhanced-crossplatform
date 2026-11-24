import assert from "node:assert/strict";
import fs from "node:fs";
import { fileURLToPath } from "node:url";
import { decode, Kind } from "../shells/web/display-list.js";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";

const wasm = process.env.NWCORE_WASM_PATH ??
  fileURLToPath(new URL("../build/nwcore.wasm", import.meta.url));
const { exports: api, instance } = await instantiateElisa(fs.readFileSync(wasm), { warn: false });
const task = api.nw_api_v1_task_video_sequence();
assert.equal(task, 3061430628n);
const create = (pieces, clips) => api.nw_api_v1_create(task, 1n, pieces, clips, 1n, 1n, 0n, 0n, 17n);
assert.equal(create(2n, 1n), -3n);
assert.equal(create(4n, 2n), -3n);
const run = create(4n, 1n);
assert.ok(run > 0n);
const capacity = 65536n;
const buffer = api.nw_frame_alloc(capacity);
assert.ok(buffer > 0n);
const info = field => api.nw_api_v1_video_sequence_info(run, BigInt(field));
let sequence = 0n;
const event = (kind, time, code, value = 0n, x = 0n, y = 0n) =>
  api.nw_api_v1_dispatch(run, kind, time, sequence++, code, value, 0n, 0n, x, y, 0n);
const frame = () => {
  const length = api.nw_api_v1_render(run, buffer, capacity, 0n, 912n, 684n);
  assert.ok(length > 0n);
  return decode(new Uint8Array(instance.exports.memory.buffer, Number(buffer), Number(length)));
};
const pointer = (kind, time, { a, b }) => event(kind, time, 0n, 0n,
  BigInt(Math.round(a / 912 * 1e6)), BigInt(Math.round(b / 684 * 1e6)));

assert.equal(info(0), 0n);
assert.equal(event(2n, 100n, 1n), 1n);
assert.equal(info(0), 4n);
assert.equal(event(1n, 400n, 3n), 1n);
assert.equal(info(0), 0n);
assert.equal(event(2n, 500n, 1n), 1n);
assert.equal(event(1n, 900n, 2n, 3n), 2n);
assert.equal(event(1n, 1000n, 2n, 23n), 1n);
assert.deepEqual([info(0), info(1), info(2), info(4), info(7), info(8)], [1n, 4n, 1n, 1n, 5n, 1000n]);
assert.equal(api.nw_api_v1_video_sequence_source_frame(run, 3n, 1400n), 16n);
const tiles = frame().filter(command => command.kind === Kind.SPRITE_FIT);
assert.deepEqual(tiles.map(tile => tile.ref), [100000, 100002, 100001, 100003]);
assert.equal(pointer(4n, 2000n, tiles[1]), 1n);
assert.equal(info(9), 1n);
assert.equal(pointer(5n, 2100n, tiles[1]), 1n);
assert.equal(info(6), 1n);
assert.equal(pointer(5n, 2200n, tiles[2]), 1n);
assert.deepEqual([info(0), info(5)], [2n, 1n]);
assert.equal(api.nw_api_v1_advance(run, 3799n, 1599n, sequence++), 2n);
assert.equal(api.nw_api_v1_advance(run, 3800n, 1n, sequence++), 1n);
assert.equal(info(0), 3n);
assert.ok(frame().some(command => command.text?.includes("100% swap efficiency")));
assert.equal(api.nw_api_v1_destroy(run), 0n);
api.nw_frame_free(buffer);
console.log("Video Sequence WASM replay: PASS");
