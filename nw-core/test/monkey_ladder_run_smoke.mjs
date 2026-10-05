// Exercise the persistent Monkey Ladder controller ABI rather than supplying
// guessed phases and answers to the stateless frame writer.
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import { fileURLToPath } from "node:url";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { decode, Kind } from "../shells/web/display-list.js";

const wasm = process.env.NWCORE_WASM_PATH ??
  fileURLToPath(new URL("../build/nwcore.wasm", import.meta.url));
const { exports, instance, stubbed } = await instantiateElisa(fs.readFileSync(wasm), { warn: false });
assert.ok(!stubbed.includes("arena_profile_explicit_create"),
  "explicit-region profiler hook is implemented as a no-op when profiling is unsupported");
const FRAME_CAPACITY = 65536;
const RUN_CAPACITY = 8192;
const framePtr = Number(exports.nw_frame_alloc(BigInt(FRAME_CAPACITY)));
const runPtr = Number(exports.nw_frame_alloc(BigInt(RUN_CAPACITY)));
assert.ok(framePtr > 0 && runPtr > 0, "frame and persistent run allocations succeed");

const INFO = { phase: 0, grid: 1, level: 2, roundLevel: 3, length: 4,
  nextIndex: 5, wrong: 6, cursor: 7, cursorEnabled: 8, deadline: 11 };
const PHASE = { ready: 0, show: 1, input: 2, result: 3 };
const ACTION = { start: 0, tick: 1, select: 2, up: 3, down: 4,
  left: 5, right: 6, commit: 7 };
const CELL = { sequence: 0, clicked: 1 };

function initialize({ grid = 5, level = 3, adaptive = 1, showMs = 700,
  perTileMs = 280, reveal = 1, seed = 1 } = {}) {
  assert.equal(Number(exports.nw_monkey_ladder_run_init(BigInt(runPtr),
    BigInt(grid), BigInt(level), BigInt(adaptive), BigInt(showMs),
    BigInt(perTileMs), BigInt(reveal), BigInt(seed))), 1);
}
function info(field) {
  return Number(exports.nw_monkey_ladder_run_info(BigInt(runPtr), BigInt(field)));
}
function cell(kind, at) {
  return Number(exports.nw_monkey_ladder_run_cell(BigInt(runPtr),
    BigInt(kind), BigInt(at)));
}
function action(kind, value = 0, nowMs = 0) {
  return Number(exports.nw_monkey_ladder_run_action(BigInt(runPtr),
    BigInt(kind), BigInt(value), BigInt(nowMs)));
}
function frame() {
  const length = Number(exports.nw_monkey_ladder_run_frame_write(
    BigInt(framePtr), BigInt(FRAME_CAPACITY), BigInt(runPtr), 0n,
    912n, 684n));
  assert.ok(length > 0, "persistent controller frame is encoded");
  return decode(new Uint8Array(instance.exports.memory.buffer,
    framePtr, length).slice());
}
function labels(commands) {
  return commands.filter((command) => command.kind === Kind.TEXT &&
    /^[0-9]+$/.test(command.text)).map((command) => command.text);
}

// A seeded first round agrees cell-for-cell with the task's Python-compatible
// sample primitive. The host may tick early but cannot force recall early.
initialize({ seed: 1 });
assert.equal(info(INFO.phase), PHASE.ready);
action(ACTION.select, 0, 99);
assert.equal(info(INFO.phase), PHASE.ready, "selection in ready phase is ignored");
action(ACTION.start, 0, 100);
assert.equal(info(INFO.phase), PHASE.show);
assert.equal(info(INFO.length), 3);
assert.equal(info(INFO.deadline), 1640, "deadline uses base plus per-tile duration");
const firstDeal = [0, 1, 2].map((index) => cell(CELL.sequence, index));
assert.deepEqual(firstDeal, [0, 1, 2].map((index) => Number(
  exports.nw_monkey_ladder_expected(1n, 3n, BigInt(index)))),
"controller deal matches the existing deterministic reference ABI");
action(ACTION.select, firstDeal[0], 1000);
assert.equal(info(INFO.phase), PHASE.show,
  "selection during the reveal phase cannot answer the hidden trial");
assert.equal(info(INFO.nextIndex), 0);
assert.equal(action(ACTION.tick, 0, 1639), PHASE.show);
assert.equal(action(ACTION.tick, 0, 1640), PHASE.input);
const firstInputFrame = frame();
assert.deepEqual(labels(firstInputFrame), [], "answer is concealed during input");
assert.deepEqual(frame(), firstInputFrame,
  "re-rendering unchanged state is deterministic and observational");
assert.equal(info(INFO.nextIndex), 0, "rendering does not advance answer validation");

action(ACTION.select, -1, 1640);
assert.equal(info(INFO.phase), PHASE.input,
  "pointer selection outside the board is ignored instead of counted as a miss");
action(ACTION.select, firstDeal[0], 1641);
assert.equal(info(INFO.nextIndex), 1);
assert.equal(cell(CELL.clicked, 0), firstDeal[0]);
action(ACTION.select, firstDeal[0], 1642);
assert.equal(info(INFO.phase), PHASE.input,
  "repeating an accepted cell is ignored instead of counted as a miss");
assert.equal(info(INFO.nextIndex), 1);
action(ACTION.select, firstDeal[1], 1643);
action(ACTION.select, firstDeal[2], 1644);
assert.equal(info(INFO.phase), PHASE.result);
assert.equal(info(INFO.roundLevel), 3, "result retains the dealt round length");
assert.equal(info(INFO.level), 4, "adaptive success advances only the next round");
assert.deepEqual(labels(frame()).sort(), ["1", "2", "3"],
  "result displays the completed round's sequence, not a newly dealt one");

// The next dealt round is longer. An incorrect cell ends it, reports the
// selected cell, reduces only the next level, and honors reveal-answer=false.
action(ACTION.start, 0, 2000);
assert.equal(info(INFO.phase), PHASE.show);
assert.equal(info(INFO.roundLevel), 4);
const secondDeal = Array.from({ length: 4 }, (_, index) => cell(CELL.sequence, index));
const pythonDeals = JSON.parse(execFileSync("python3", ["-c",
  "import json, random; r=random.Random(1); a=r.sample(range(25), 3); b=r.sample(range(25), 4); print(json.dumps([a,b]))"],
{ encoding: "utf8" }));
assert.deepEqual(secondDeal, pythonDeals[1],
  "successive controller rounds consume the same continuous Python RNG stream");
action(ACTION.tick, 0, info(INFO.deadline));
assert.equal(info(INFO.phase), PHASE.input);
const wrongCell = (secondDeal[0] + 1) % 25;
action(ACTION.select, wrongCell, info(INFO.deadline));
assert.equal(info(INFO.phase), PHASE.result);
assert.equal(info(INFO.wrong), wrongCell);
assert.equal(info(INFO.level), 3);
assert.equal(labels(frame()).length, 4,
  "enabled answer reveal shows the completed four-cell sequence after a miss");

// Cursor motion is bounded by the configured grid and shares the same commit
// validation path as pointer selection. Non-adaptive runs keep their length.
initialize({ grid: 3, level: 2, adaptive: 0, showMs: 0,
  perTileMs: 0, reveal: 0, seed: 7 });
action(ACTION.start, 0, 50);
action(ACTION.tick, 0, 50);
assert.equal(info(INFO.phase), PHASE.input);
action(ACTION.left, 0, 51);
assert.equal(info(INFO.cursor), 0, "left edge clamps");
assert.equal(info(INFO.cursorEnabled), 1);
action(ACTION.up, 0, 51);
assert.equal(info(INFO.cursor), 0, "top edge clamps");
action(ACTION.down, 0, 51);
action(ACTION.right, 0, 51);
assert.equal(info(INFO.cursor), 4);
const thirdDeal = [cell(CELL.sequence, 0), cell(CELL.sequence, 1)];
action(ACTION.select, (thirdDeal[0] + 1) % 9, 52);
assert.equal(info(INFO.phase), PHASE.result);
assert.deepEqual(labels(frame()), [], "disabled answer reveal stays concealed after a miss");
initialize({ grid: 3, level: 2, adaptive: 0, showMs: 0,
  perTileMs: 0, reveal: 0, seed: 7 });
action(ACTION.start, 0, 60);
action(ACTION.tick, 0, 60);
// Move to the first dealt tile and commit it through keyboard semantics.
let target = thirdDeal[0];
let row = Math.floor(target / 3);
let col = target % 3;
for (let index = 0; index < row; index++) action(ACTION.down, 0, 61);
for (let index = 0; index < col; index++) action(ACTION.right, 0, 61);
action(ACTION.commit, 0, 62);
assert.equal(info(INFO.nextIndex), 1);
action(ACTION.select, thirdDeal[1], 63);
assert.equal(info(INFO.phase), PHASE.result);
assert.equal(info(INFO.level), 2, "non-adaptive success leaves the level unchanged");

// The original option set reaches a ten-by-ten board and a 50-cell sequence.
// Exercise the largest supported state and renderer path, not just its clamp.
initialize({ grid: 10, level: 50, adaptive: 0, showMs: 0,
  perTileMs: 0, reveal: 1, seed: 99 });
assert.equal(info(INFO.grid), 10);
assert.equal(info(INFO.length), 0);
action(ACTION.start, 0, 70);
assert.equal(info(INFO.length), 50);
const largestDeal = Array.from({ length: 50 }, (_, index) => cell(CELL.sequence, index));
assert.equal(new Set(largestDeal).size, 50, "largest dealt sequence contains no duplicate cells");
assert.ok(largestDeal.every((selected) => selected >= 0 && selected < 100),
  "largest deal stays within the ten-by-ten board");
assert.equal(labels(frame()).length, 50, "largest board frame renders every answer label");

console.log("PASS: Monkey Ladder persistent timing, seeded deals, recall, adaptive results, cursor, and concealment");
