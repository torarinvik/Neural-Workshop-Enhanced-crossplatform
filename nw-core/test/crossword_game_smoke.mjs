import assert from "node:assert/strict";
import fs from "node:fs";
import { fileURLToPath } from "node:url";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { decode, Kind } from "../shells/web/display-list.js";

const wasm = process.env.NWCORE_WASM_PATH ?? fileURLToPath(new URL("../build/nwcore.wasm", import.meta.url));
const { exports, instance } = await instantiateElisa(fs.readFileSync(wasm), { warn: false });
const task = BigInt(exports.nw_api_v1_task_crossword());
const run = exports.nw_api_v1_create(task, 1n, 1n, 1n, 1n, 1n, 0n, 0n, 17n);
const info = field => Number(exports.nw_api_v1_crossword_info(run, BigInt(field)));
const cell = (field, at) => Number(exports.nw_api_v1_crossword_value(run, BigInt(field), BigInt(at)));
let sequence = 0n;
const action = (code, value = 0n) => exports.nw_api_v1_dispatch(run, 1n,
  1000n, sequence++, code, value, 0n, 0n, 0n, 0n, 0n);
function upload(text) {
  const bytes = new TextEncoder().encode(text);
  const pointer = Number(exports.nw_frame_alloc(BigInt(bytes.length)));
  assert.ok(pointer > 0);
  try {
    new Uint8Array(instance.exports.memory.buffer, pointer, bytes.length).set(bytes);
    return exports.nw_api_v1_crossword_set_lexicon(run, BigInt(pointer), BigInt(bytes.length));
  } finally {
    exports.nw_frame_free(BigInt(pointer));
  }
}
assert.equal(info(0), 0);
assert.equal(info(12), 0);
assert.equal(action(0n), 2n, "without a clue index, starting must leave the run ready");
assert.equal(info(2), 0);
assert.equal(upload("bad\tnot-a-rank\ta clue\n"), -3n);
assert.equal(info(12), 0, "invalid data must not be adopted");
assert.equal(upload("aaa\t1\tThree-letter fixture clue\naaaa\t2\tFour-letter fixture clue\n"), 0n);
assert.equal(info(12), 1);
assert.equal(action(0n), 1n);
assert.equal(info(0), 1);
assert.equal(action(10n, 1n), 2n, "options cannot reset a grid in progress");
const size = info(4);
assert.equal(size, 4);
const firstBlank = Array.from({ length: size * size }, (_, at) => at)
  .find(at => cell(0, at) !== 0 && cell(2, at) === 0);
assert.equal(info(6), firstBlank, "the cursor starts at the first unfilled cell");
assert.equal(info(13), 1);
assert.equal(info(14), 1);
const clicked = firstBlank === 0 ? 1 : 0;
const col = clicked % size, row = Math.floor(clicked / size);
const px = Math.round((259.5 + (col + 0.5) * 393 / size) * 1000000 / 912);
const py = Math.round((179 + (size - row - 0.5) * 393 / size) * 1000000 / 684);
const pointer = button => exports.nw_api_v1_dispatch(run, 5n, 1000n, sequence++,
  BigInt(button), 0n, 0n, 0n, BigInt(px), BigInt(py), 0n);
assert.equal(pointer(0), 1n);
assert.equal(info(6), clicked, "pointer selects the visible cell");
const facing = info(7);
assert.equal(pointer(0), 1n);
assert.equal(info(7), 1 - facing, "clicking the current cell turns");
assert.equal(pointer(2), 1n);
assert.equal(info(7), facing, "right click turns");
const frame = Number(exports.nw_frame_alloc(1048576n));
assert.ok(frame > 0);
try {
  const length = Number(exports.nw_api_v1_render(run, BigInt(frame), 1048576n, 0n, 912n, 684n));
  assert.ok(length > 0);
  const bytes = new Uint8Array(instance.exports.memory.buffer, frame, length).slice();
  const text = decode(bytes).filter(command => command.kind === Kind.TEXT).map(command => command.text);
  assert.ok(text.some(line => line.includes("Four-letter fixture clue")), "the real slot clue is rendered");
} finally {
  exports.nw_frame_free(BigInt(frame));
}
function moveTo(target) {
  let remaining = size * size * 2;
  while (info(6) !== target && remaining-- > 0) {
    const current = info(6);
    const code = Math.floor(current / size) > Math.floor(target / size) ? 4n
      : Math.floor(current / size) < Math.floor(target / size) ? 5n
      : current % size > target % size ? 2n : 3n;
    assert.equal(action(code), 1n);
    assert.notEqual(info(6), current, "movement must reach the target in the open fixture");
  }
  assert.equal(info(6), target);
}
const ends = [];
for (let row = 0; row < size; row++) ends.push({ at: row * size + size - 1, down: 0 });
for (let column = 0; column < size; column++) ends.push({ at: (size - 1) * size + column, down: 1 });
const end = ends.find(({ at }) => !cell(2, at));
assert.ok(end, "fixture must have an editable entry endpoint");
moveTo(end.at);
if (info(7) !== end.down) assert.equal(action(6n), 1n);
assert.equal(action(7n, 0n), 1n);
assert.equal(info(6), end.at, "writing at the end of an entry does not wrap");
assert.equal(action(7n, 1n), 1n);
assert.equal(info(10), 1, "a changed incorrect letter records a slip");
assert.equal(exports.nw_api_v1_dispatch(run, 2n, 1000n, sequence++, 2n,
  0n, 0n, 0n, 0n, 0n, 0n), 2n, "Enter does not submit an incomplete grid");
for (let at = 0; at < size * size; at++) {
  if (at === end.at || cell(2, at)) continue;
  moveTo(at);
  assert.equal(action(7n, BigInt(cell(0, at) - 97)), 1n);
}
assert.equal(info(0), 1, "an incorrect full grid remains open");
assert.equal(info(11), 1);
moveTo(end.at);
assert.equal(action(7n, BigInt(cell(0, end.at) - 97)), 1n);
assert.equal(info(0), 2, "a correct full grid settles automatically");
assert.equal(info(8), 0, "a solved grid with a slip is not clean");
assert.equal(info(15), 1);
assert.equal(info(16), 1);
assert.equal(info(17), 0);
assert.equal(info(1), 1, "one slip keeps the adaptive level");
assert.equal(action(0n), 1n);
assert.equal(info(0), 3);
assert.equal(action(0n), 1n);
assert.equal(info(0), 1, "Space starts a fresh run after done");
for (let at = 0; at < size * size; at++) {
  if (cell(2, at)) continue;
  moveTo(at);
  assert.equal(action(7n, BigInt(cell(0, at) - 97)), 1n);
}
assert.equal(info(0), 2);
assert.equal(info(8), 1);
assert.equal(info(1), 2, "a clean solve climbs a level");
assert.equal(info(17), 1);
assert.equal(action(10n, 1n), 1n, "options reset a settled run");
assert.equal(info(0), 0);
assert.equal(info(1), 1);
assert.equal(info(12), 1, "options preserve the imported index");
assert.equal(info(13), 0);
assert.equal(info(14), 0);
assert.equal(action(10n, 512n), -6n, "invalid packed options are rejected");
assert.equal(exports.nw_api_v1_destroy(run), 0n);
assert.equal(exports.nw_api_v1_destroy(run), 0n);
console.log("crossword_game_smoke: PASS (absent/invalid index, supplied clues, cursor, slips, automatic settlement, cleanup)");
