import assert from "node:assert/strict";
import fs from "node:fs";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { decode, Kind } from "../shells/web/display-list.js";

const wasm = process.env.NWCORE_WASM_PATH ?? fileURLToPath(new URL("../build/nwcore.wasm", import.meta.url));
const { exports, instance } = await instantiateElisa(fs.readFileSync(wasm), { warn: false });
const task = BigInt(exports.nw_api_v1_task_scrabble());
const run = exports.nw_api_v1_create(task, 1n, 1n, 1n, 1n, 1n, 0n, 0n, 17n);
const info = field => Number(exports.nw_api_v1_scrabble_info(run, BigInt(field)));
const value = (field, at) => Number(exports.nw_api_v1_scrabble_value(run, BigInt(field), BigInt(at)));
let sequence = 0n;
let clockOffset = 0n;
const action = (code, val = 0) => exports.nw_api_v1_dispatch(run, 1n, 1000n + clockOffset + sequence, sequence++, BigInt(code), BigInt(val), 0n, 0n, 0n, 0n, 0n);
const key = (code, flags = 0n) => exports.nw_api_v1_dispatch(run, 2n, 1000n + clockOffset + sequence, sequence++, BigInt(code), 999n, 0n, flags, 0n, 0n, 0n);
assert.equal(info(0), 0);
const offline = exports.nw_api_v1_create(task, 1n, 1n, 1n, 1n, 1n, 0n, 0n, 17n);
assert.equal(exports.nw_api_v1_dispatch(offline, 1n, 1000n, 0n, 0n, 0n, 0n, 0n, 0n, 0n, 0n), 1n);
const offlineInfo = field => Number(exports.nw_api_v1_scrabble_info(offline, BigInt(field)));
const offlineValue = (field, at) => Number(exports.nw_api_v1_scrabble_value(offline, BigInt(field), BigInt(at)));
const seedOracle = JSON.parse(execFileSync("python3", [fileURLToPath(new URL("./scrabble_controller_oracle.py", import.meta.url))],
  {encoding: "utf8", env: {...process.env, NW_SCRABBLE_SEED: "1", NW_SCRABBLE_LEVEL: "1"}}));
assert.equal(offlineInfo(0), 1, "the source seed list supports offline play");
assert.deepEqual(Array.from({length: 49}, (_, at) => offlineValue(0, at)), seedOracle.board);
assert.deepEqual(Array.from({length: seedOracle.rack.length}, (_, at) => offlineValue(2, at)), seedOracle.rack);
assert.equal(offlineInfo(9), seedOracle.score);
assert.deepEqual(Array.from({length: offlineInfo(10)}, (_, at) => [offlineValue(5, at), offlineValue(6, at)]), seedOracle.best);
assert.equal(exports.nw_api_v1_destroy(offline), 0n);
const defaultOffline = exports.nw_api_v1_create(task, 1n, 3n, 5n, 1n, 1n, 0n, 0n, 17n);
assert.equal(exports.nw_api_v1_dispatch(defaultOffline, 1n, 1000n, 0n, 0n, 0n, 0n, 0n, 0n, 0n, 0n), 1n);
const defaultOracle = JSON.parse(execFileSync("python3", [fileURLToPath(new URL("./scrabble_controller_oracle.py", import.meta.url))],
  {encoding: "utf8", env: {...process.env, NW_SCRABBLE_SEED: "1", NW_SCRABBLE_LEVEL: "3"}}));
assert.equal(Number(exports.nw_api_v1_scrabble_info(defaultOffline, 0n)), 1);
assert.deepEqual(Array.from({length: 81}, (_, at) => Number(exports.nw_api_v1_scrabble_value(defaultOffline, 0n, BigInt(at)))), defaultOracle.board);
assert.equal(Number(exports.nw_api_v1_scrabble_info(defaultOffline, 9n)), defaultOracle.score);
assert.equal(exports.nw_api_v1_destroy(defaultOffline), 0n);
// Replay a source-generated deal whose legal answer uses two copies of O.
// Exercise a disconnected invalid word, board edges, duplicate tile inventory,
// undo, and the final score through the common keyboard protocol.
const repeatedOracle = JSON.parse(execFileSync("python3", [fileURLToPath(new URL("./scrabble_controller_oracle.py", import.meta.url))],
  {encoding: "utf8", env: {...process.env, NW_SCRABBLE_SEED: "1", NW_SCRABBLE_LEVEL: "3"}}));
assert.ok(repeatedOracle.repeated);
const repeatRun = exports.nw_api_v1_create(task, 1n, 3n, 1n, 1n, 0n, 0n, 0n, 17n);
let repeatSequence = 0n;
const repeatKey = code => exports.nw_api_v1_dispatch(repeatRun, 2n, 1000n + repeatSequence, repeatSequence++, BigInt(code), 0n, 0n, 0n, 0n, 0n, 0n);
const repeatInfo = field => Number(exports.nw_api_v1_scrabble_info(repeatRun, BigInt(field)));
const repeatValue = (field, at) => Number(exports.nw_api_v1_scrabble_value(repeatRun, BigInt(field), BigInt(at)));
assert.equal(repeatKey(1), 1n);
assert.deepEqual(Array.from({length: 81}, (_, at) => repeatValue(0, at)), repeatedOracle.board);
assert.deepEqual(Array.from({length: 7}, (_, at) => repeatValue(2, at)), repeatedOracle.rack);
const moveTo = cell => {
  while (Math.floor(repeatInfo(6) / 9) > Math.floor(cell / 9)) assert.equal(repeatKey(4), 1n);
  while (Math.floor(repeatInfo(6) / 9) < Math.floor(cell / 9)) assert.equal(repeatKey(6), 1n);
  while (repeatInfo(6) % 9 > cell % 9) assert.equal(repeatKey(3), 1n);
  while (repeatInfo(6) % 9 < cell % 9) assert.equal(repeatKey(5), 1n);
};
moveTo(80);
assert.equal(repeatKey(6), 1n);
assert.equal(repeatKey(5), 1n);
assert.equal(repeatInfo(6), 80, "movement cannot cross the bottom or right edge");
moveTo(0);
assert.equal(repeatKey(4), 1n);
assert.equal(repeatKey(3), 1n);
assert.equal(repeatInfo(6), 0, "movement cannot cross the top or left edge");
assert.equal(repeatKey(12), 1n);
assert.equal(repeatKey(2), 1n);
assert.equal(repeatInfo(0), 1, "disconnected invalid word does not settle");
assert.equal(repeatValue(4, 0), 1, "an invalid submission leaves the tile in place");
assert.equal(repeatKey(8), 1n);
assert.equal(repeatValue(4, 0), 0, "undo returns the tile to its rack slot");
assert.ok(repeatedOracle.invalid, "the source found an invalid connected word");
moveTo(repeatedOracle.invalid.cell);
assert.equal(repeatKey(12 + repeatedOracle.invalid.slot), 1n);
assert.equal(repeatKey(2), 1n);
assert.equal(repeatInfo(0), 1, `source-invalid words ${repeatedOracle.invalid.words} are rejected`);
assert.equal(repeatKey(8), 1n);
let firstRepeatSlot = -1;
for (const [cell, letter] of repeatedOracle.repeated.laid) {
  moveTo(cell);
  const slot = repeatedOracle.rack.findIndex((item, index) => item === letter && !repeatValue(4, index));
  assert.notEqual(slot, -1);
  assert.equal(repeatKey(12 + slot), 1n);
  if (firstRepeatSlot < 0) {
    firstRepeatSlot = slot;
    assert.equal(repeatKey(12 + slot), 2n, "a spent duplicate cannot be used twice");
  } else assert.notEqual(slot, firstRepeatSlot, "the second copy uses its own rack slot");
}
assert.equal(repeatKey(2), 1n);
assert.equal(repeatInfo(0), 2);
assert.equal(repeatInfo(5), repeatedOracle.repeated.score);
const repeatFrame = Number(exports.nw_frame_alloc(1048576n));
const repeatLength = Number(exports.nw_api_v1_render(repeatRun, BigInt(repeatFrame), 1048576n, 0n, 912n, 684n));
const repeatLabels = decode(new Uint8Array(instance.exports.memory.buffer, repeatFrame, repeatLength).slice()).filter(c => c.kind === Kind.TEXT).map(c => c.text);
assert.ok(repeatLabels.includes(repeatedOracle.repeated.message), "repeated-letter score and feedback match the source");
exports.nw_frame_free(BigInt(repeatFrame));
assert.equal(exports.nw_api_v1_destroy(repeatRun), 0n);
// Source pool falls back only when no index rows are in the rank band; an
// in-band row that is too short still suppresses the fallback.
for (const [indexText, expectedPhase] of [["zzz\t5000\t\n", 1], ["a\t1\t\nzzz\t5000\t\n", 3]]) {
  const fallback = exports.nw_api_v1_create(task, 1n, 1n, 1n, 1n, 1n, 0n, 0n, 17n);
  const data = new TextEncoder().encode(indexText);
  const input = Number(exports.nw_frame_alloc(BigInt(data.length)));
  new Uint8Array(instance.exports.memory.buffer, input, data.length).set(data);
  assert.equal(exports.nw_api_v1_scrabble_set_lexicon(fallback, BigInt(input), BigInt(data.length)), 0n);
  exports.nw_frame_free(BigInt(input));
  assert.equal(exports.nw_api_v1_dispatch(fallback, 1n, 1000n, 0n, 0n, 0n, 0n, 0n, 0n, 0n, 0n), 1n);
  assert.equal(Number(exports.nw_api_v1_scrabble_info(fallback, 0n)), expectedPhase);
  if (expectedPhase === 1) {
    assert.deepEqual(Array.from({length: 49}, (_, at) => Number(exports.nw_api_v1_scrabble_value(fallback, 0n, BigInt(at)))), seedOracle.board);
  }
  assert.equal(exports.nw_api_v1_destroy(fallback), 0n);
}
const alphabet = "aeinorst";
const rows = process.env.NW_SCRABBLE_LEXICON ? fs.readFileSync(process.env.NW_SCRABBLE_LEXICON, "utf8") : Array.from({length: 120}, (_, w) => {
  const word = Array.from({length: 2 + w % 4}, (_, k) => alphabet[(Math.floor(w / 8) + k * 3 + w % 8) % 8]).join("");
  return `${word}\t${w + 1}\tfixture clue\n`;
}).join("");
const bytes = new TextEncoder().encode(rows);
const pointer = Number(exports.nw_frame_alloc(BigInt(bytes.length)));
new Uint8Array(instance.exports.memory.buffer, pointer, bytes.length).set(bytes);
assert.equal(exports.nw_api_v1_scrabble_set_lexicon(run, BigInt(pointer), BigInt(bytes.length)), 0n);
exports.nw_frame_free(BigInt(pointer));
assert.equal(info(11), 1);
const invalid = new TextEncoder().encode("invalid\n");
const invalidPointer = Number(exports.nw_frame_alloc(BigInt(invalid.length)));
new Uint8Array(instance.exports.memory.buffer, invalidPointer, invalid.length).set(invalid);
assert.equal(exports.nw_api_v1_scrabble_set_lexicon(run, BigInt(invalidPointer), BigInt(invalid.length)), -3n);
exports.nw_frame_free(BigInt(invalidPointer));
assert.equal(info(11), 1, "invalid replacement retains the existing index");
assert.equal(action(0), 1n);
assert.equal(info(0), 1);
clockOffset += 10000n; // Simulate time spent generating the deal in the host.
assert.equal(action(10), 1n, "the host starts the clock after generation");
assert.equal(action(10), 2n, "the start clock can be synchronized only once");
assert.equal(info(4), 7);
assert.ok(info(9) > 0 && info(10) > 0, "real source deal has a scored best play");
const initialCursor = info(6);
assert.equal(key(4), 1n); // Up
assert.equal(info(6), initialCursor - 7);
assert.equal(key(6), 1n); // Down
assert.equal(info(6), initialCursor);
assert.equal(key(23), 1n); // Tab changes direction.
assert.equal(key(23), 1n);
assert.equal(key(12), 1n); // The slot comes from the key code, not its value.
assert.equal(value(4, 0), 1);
assert.equal(key(8), 1n); // Backspace restores it.
assert.equal(value(4, 0), 0);
assert.equal(key(18, 1n), 2n, "repeated key-down is ignored");
assert.equal(value(4, 6), 0);
assert.equal(action(1), 1n);
assert.equal(info(0), 1, "empty submission stays open");
// Coordinates use the same source layout at the 912x684 reference size.
const step = (600 - 179) * 0.13;
const boardBottom = 179 + step * 1.6;
const boardSide = 600 - boardBottom;
const boardLeft = (912 - boardSide) / 2;
const rackN = Array.from({length: 7}, (_, i) => value(2, i)).filter(Boolean).length;
const rackLeft = (912 - step * (rackN + 0.5 + 2.6)) / 2;
const point = (kind, x, y, button = 0) => exports.nw_api_v1_dispatch(run, BigInt(kind), 1000n + clockOffset + sequence, sequence++, BigInt(button), 0n, 0n, 0n, BigInt(Math.round(x * 1000000 / 912)), BigInt(Math.round(y * 1000000 / 684)), 0n);
const target = Array.from({length: 49}, (_, at) => at).find(at => value(0, at) === 0 && at !== info(6));
const targetX = boardLeft + (target % 7 + 0.5) * boardSide / 7;
const targetY = boardBottom + (7 - Math.floor(target / 7) - 0.5) * boardSide / 7;
assert.equal(point(4, targetX, targetY), 1n, "hover is accepted");
assert.equal(point(5, targetX, targetY), 1n);
assert.equal(info(6), target, "board click selects the square");
assert.equal(point(5, rackLeft + step * 0.45, boardBottom - step * 0.8), 1n);
assert.equal(value(4, 0), 1, "rack click spends the tile");
assert.notEqual(value(3, target), 0, "rack click lays the tile");
assert.equal(point(5, rackLeft + step * (rackN + 0.5 + 1.3), boardBottom - step * 0.8), 1n);
assert.equal(info(0), 1, "illegal play-button submission stays open");
const target2 = Array.from({length: 49}, (_, at) => at).find(at => value(0, at) === 0 && at !== target && at !== info(6));
const x2 = boardLeft + (target2 % 7 + 0.5) * boardSide / 7;
const y2 = boardBottom + (7 - Math.floor(target2 / 7) - 0.5) * boardSide / 7;
assert.equal(point(5, x2, y2), 1n);
assert.equal(point(5, rackLeft + step * 1.45, boardBottom - step * 0.8), 1n);
assert.equal(value(4, 1), 1);
assert.equal(point(5, targetX, targetY), 1n);
assert.equal(value(4, 0), 0, "clicking an earlier tile restores its rack slot");
assert.equal(value(3, target), 0);
assert.notEqual(value(3, target2), 0, "lifting one tile preserves another");
assert.equal(point(5, x2, y2), 1n);
assert.equal(value(4, 1), 0);
assert.equal(point(5, rackLeft + step * (rackN + 0.5 + 1.3), boardBottom - step * 0.8), 1n);
assert.equal(info(0), 1, "empty play-button submission stays open");
assert.equal(point(5, targetX, targetY, 2), 1n, "right click turns");
const frame = Number(exports.nw_frame_alloc(1048576n));
const length = Number(exports.nw_api_v1_render(run, BigInt(frame), 1048576n, 0n, 912n, 684n));
const labels = decode(new Uint8Array(instance.exports.memory.buffer, frame, length).slice()).filter(c => c.kind === Kind.TEXT).map(c => c.text);
const rackLetters = Array.from({length: 7}, (_, i) => value(2, i)).filter(Boolean).map(x => String.fromCharCode(x).toUpperCase());
assert.ok(rackLetters.every(letter => labels.includes(letter)), "dealt rack letters render");
const size = info(4);
const best = Array.from({length: info(10)}, (_, i) => [value(5, i), value(6, i)]);
const oracle = JSON.parse(execFileSync("python3", [fileURLToPath(new URL("./scrabble_controller_oracle.py", import.meta.url))],
  {encoding: "utf8", env: process.env}));
assert.deepEqual(Array.from({length: size * size}, (_, at) => value(0, at)), oracle.board, "source board");
assert.deepEqual(Array.from({length: oracle.rack.length}, (_, at) => value(2, at)), oracle.rack, "source rack");
assert.equal(info(9), oracle.score, "source best score");
assert.deepEqual(best, oracle.best, "source best placement");
for (const [cell, letter] of best) {
  while (Math.floor(info(6) / size) > Math.floor(cell / size)) assert.equal(key(4), 1n);
  while (Math.floor(info(6) / size) < Math.floor(cell / size)) assert.equal(key(6), 1n);
  while (info(6) % size > cell % size) assert.equal(key(3), 1n);
  while (info(6) % size < cell % size) assert.equal(key(5), 1n);
  const slot = Array.from({length: 7}, (_, i) => i).find(i => value(2, i) === letter && !value(4, i));
  assert.notEqual(slot, undefined);
  assert.equal(key(12 + slot), 1n);
}
clockOffset += 2500n;
assert.equal(key(2), 1n);
assert.equal(info(0), 2, "best source play settles");
assert.equal(info(7), 1);
assert.equal(info(5), info(9));
assert.equal(info(12), oracle.score);
assert.equal(info(13), oracle.score);
assert.equal(info(14), 1);
assert.equal(info(15), 1);
assert.equal(info(16), 2);
const scoredLength = Number(exports.nw_api_v1_render(run, BigInt(frame), 1048576n, 0n, 912n, 684n));
const scoredLabels = decode(new Uint8Array(instance.exports.memory.buffer, frame, scoredLength).slice()).filter(c => c.kind === Kind.TEXT).map(c => c.text);
assert.ok(scoredLabels.includes(oracle.message), `source scored feedback: ${JSON.stringify(scoredLabels)}`);
assert.equal(action(0), 1n);
assert.equal(info(0), 3);
const doneLength = Number(exports.nw_api_v1_render(run, BigInt(frame), 1048576n, 0n, 912n, 684n));
const doneLabels = decode(new Uint8Array(instance.exports.memory.buffer, frame, doneLength).slice()).filter(c => c.kind === Kind.TEXT).map(c => c.text);
assert.ok(doneLabels.includes(`1 played, ${oracle.score} points of a possible ${oracle.score}`));
assert.equal(action(0), 1n);
assert.equal(info(1), 1, "a new run resets the starting level");
assert.equal(action(9, 2), 1n, "applying options resets a live run");
assert.deepEqual([info(0), info(1), info(3), info(17), info(18), info(11)], [0, 2, 1, 0, 0, 1]);
assert.equal(action(9, 2 | (7 << 4)), -6n, "invalid trial choice is rejected");
exports.nw_frame_free(BigInt(frame));
assert.equal(exports.nw_api_v1_destroy(run), 0n);
// Premium visibility affects painting only, not the generated board.
const variants = [];
for (const show of [1n, 0n]) {
  const h = exports.nw_api_v1_create(task, 1n, 1n, 1n, show, 0n, 0n, 0n, 17n);
  assert.ok(h > 0n);
  assert.equal(exports.nw_api_v1_dispatch(h, 1n, 1000n, 0n, 0n, 0n, 0n, 0n, 0n, 0n, 0n), 1n);
  const buf = Number(exports.nw_frame_alloc(1048576n));
  const size = Number(exports.nw_api_v1_render(h, BigInt(buf), 1048576n, 0n, 912n, 684n));
  const commands = decode(new Uint8Array(instance.exports.memory.buffer, buf, size).slice());
  variants.push({board: Array.from({length: 49}, (_, at) => exports.nw_api_v1_scrabble_value(h, 0n, BigInt(at))),
                 rects: commands.filter(c => c.kind === Kind.RECT).length});
  exports.nw_frame_free(BigInt(buf));
  assert.equal(exports.nw_api_v1_destroy(h), 0n);
}
assert.deepEqual(variants[0].board, variants[1].board);
assert.ok(variants[0].rects > variants[1].rects, "premium setting controls board painting");
if (process.env.NW_SCRABBLE_LEXICON) {
  const lowerOracle = JSON.parse(execFileSync("python3", [fileURLToPath(new URL("./scrabble_controller_oracle.py", import.meta.url))],
    {encoding: "utf8", env: {...process.env, NW_SCRABBLE_LEVEL: "2"}}));
  assert.ok(lowerOracle.lower, "real source fixture includes a legal low-scoring play");
  for (const adaptive of [1n, 0n]) {
  const other = exports.nw_api_v1_create(task, 1n, 2n, 1n, 1n, adaptive, 0n, 0n, 17n);
  const input = Number(exports.nw_frame_alloc(BigInt(bytes.length)));
  new Uint8Array(instance.exports.memory.buffer, input, bytes.length).set(bytes);
  assert.equal(exports.nw_api_v1_scrabble_set_lexicon(other, BigInt(input), BigInt(bytes.length)), 0n);
  exports.nw_frame_free(BigInt(input));
  let seq = 0n;
  const otherAction = (code, v = 0) => exports.nw_api_v1_dispatch(other, 1n, 5000n + seq, seq++, BigInt(code), BigInt(v), 0n, 0n, 0n, 0n, 0n);
  const otherInfo = field => Number(exports.nw_api_v1_scrabble_info(other, BigInt(field)));
  const otherValue = (field, at) => Number(exports.nw_api_v1_scrabble_value(other, BigInt(field), BigInt(at)));
  assert.equal(otherAction(0), 1n);
  const side = otherInfo(4);
  for (const [cell, letter] of lowerOracle.lower.laid) {
    while (Math.floor(otherInfo(6) / side) > Math.floor(cell / side)) otherAction(5);
    while (Math.floor(otherInfo(6) / side) < Math.floor(cell / side)) otherAction(6);
    while (otherInfo(6) % side > cell % side) otherAction(2);
    while (otherInfo(6) % side < cell % side) otherAction(3);
    const slot = Array.from({length: 7}, (_, n) => n).find(n => otherValue(2, n) === letter && !otherValue(4, n));
    assert.notEqual(slot, undefined);
    assert.equal(otherAction(7, slot), 1n);
  }
  assert.equal(otherAction(1), 1n);
  assert.equal(otherInfo(0), 2, "legal lower score settles");
  assert.equal(otherInfo(5), lowerOracle.lower.score);
  assert.equal(otherInfo(7), 0, "low share receives source negative verdict");
  assert.equal(otherInfo(1), adaptive ? 1 : 2, "adaptive setting controls the level drop");
  const frame2 = Number(exports.nw_frame_alloc(1048576n));
  const length2 = Number(exports.nw_api_v1_render(other, BigInt(frame2), 1048576n, 0n, 912n, 684n));
  const labels2 = decode(new Uint8Array(instance.exports.memory.buffer, frame2, length2).slice()).filter(c => c.kind === Kind.TEXT).map(c => c.text);
  assert.ok(labels2.includes(lowerOracle.lower.message), "lower-score feedback matches source");
  exports.nw_frame_free(BigInt(frame2));
  assert.equal(exports.nw_api_v1_destroy(other), 0n);
  }
}
console.log("scrabble_game_smoke: PASS (source fallback and index, seeded deal, best placement, verdict, cleanup)");
