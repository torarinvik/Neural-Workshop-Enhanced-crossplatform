// Common-v1 lifecycle smoke for the source-backed Maze controller. The maze
// topology is read through the additive cell accessor and solved by a small
// test oracle; no fixture topology or pre-recorded verdict is used.
import assert from "node:assert/strict";
import fs from "node:fs";
import { fileURLToPath } from "node:url";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";

const root = fileURLToPath(new URL("..", import.meta.url));
const wasm = process.env.NWCORE_WASM_PATH ?? `${root}/build/nwcore.wasm`;
const { exports, instance } = await instantiateElisa(fs.readFileSync(wasm), { warn: false });

const TASK = BigInt(exports.nw_api_v1_task_maze());
const STATUS = Object.freeze({ accepted: 1n, ignored: 2n, badOptions: -3n });
const EVENT = Object.freeze({ action: 1n, keyDown: 2n });
const KEY = Object.freeze({ space: 1n, enter: 2n });
const ACTION = Object.freeze({ start: 0n, up: 1n, down: 2n, left: 3n, right: 4n });
const PHASE = Object.freeze({ ready: 0n, walking: 1n, solved: 2n, done: 3n });
const INFO = Object.freeze({
  phase: 0, rung: 1, trial: 2, totalTrials: 3, walker: 4, steps: 5,
  verdict: 6, width: 7, height: 8, start: 9, wayOut: 10, doorCount: 11,
  held: 12, minimum: 13, greedy: 14, adaptive: 15, showTrail: 16,
  solvedCount: 17, totalPar: 18, totalSteps: 19, bestRung: 20,
  takenSeconds: 21, message: 22,
});
const CELL = Object.freeze({ wall: 0n, walked: 1n, door: 2n, key: 3n });
const STATE_BYTES = 112;
const FRAME_BYTES = 65536;
const STATE_BUFFER = Number(exports.nw_frame_alloc(BigInt(STATE_BYTES)));
const FRAME_BUFFER = Number(exports.nw_frame_alloc(BigInt(FRAME_BYTES)));
assert.ok(STATE_BUFFER > 0 && FRAME_BUFFER > 0);

function create(options = [1n, 1n, 0n, 1n, 0n, 0n], seed = 17n) {
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

function event(handle, kind, timestamp, sequence, code, value = 0n) {
  return exports.nw_api_v1_dispatch(handle, kind, BigInt(timestamp),
    BigInt(sequence), code, value, 0n, 0n, 0n, 0n, 0n);
}

function render(handle) {
  const length = exports.nw_api_v1_render(handle, BigInt(FRAME_BUFFER),
    BigInt(FRAME_BYTES), 0n, 912n, 684n);
  assert.ok(length > 0n);
  return new Uint8Array(instance.exports.memory.buffer, FRAME_BUFFER,
    Number(length)).slice();
}

function info(handle, field) {
  return BigInt(exports.nw_api_v1_maze_info(handle, BigInt(field)));
}

function cell(handle, field, at) {
  return BigInt(exports.nw_api_v1_maze_cell(handle, field, BigInt(at)));
}

function solvePath(handle) {
  const width = Number(info(handle, INFO.width));
  const height = Number(info(handle, INFO.height));
  const start = Number(info(handle, INFO.start));
  const goal = Number(info(handle, INFO.wayOut));
  const doorCount = Number(info(handle, INFO.doorCount));
  assert.ok(width > 0 && height > 0 && start >= 0 && goal >= 0);

  const cellCount = width * height;
  const maskCount = 1 << doorCount;
  const stateCount = cellCount * maskCount;
  const initialHeld = Number(info(handle, INFO.held));
  const previous = new Int32Array(stateCount);
  previous.fill(-2);
  const previousAction = new Int8Array(stateCount);
  const queue = [start * maskCount + initialHeld];
  previous[queue[0]] = -1;
  const directions = [
    { action: 1, dx: 0, dy: -1 },
    { action: 2, dx: 0, dy: 1 },
    { action: 3, dx: -1, dy: 0 },
    { action: 4, dx: 1, dy: 0 },
  ];
  let goalState = -1;
  for (let head = 0; head < queue.length && goalState < 0; head++) {
    const encoded = queue[head];
    const held = encoded % maskCount;
    const at = Math.floor(encoded / maskCount);
    if (at === goal) {
      goalState = encoded;
      break;
    }
    const x = at % width;
    const y = Math.floor(at / width);
    for (const direction of directions) {
      const nx = x + direction.dx;
      const ny = y + direction.dy;
      if (nx < 0 || nx >= width || ny < 0 || ny >= height) continue;
      const next = ny * width + nx;
      if (cell(handle, CELL.wall, next) !== 0n) continue;
      const door = Number(cell(handle, CELL.door, next));
      if (door > 0 && (held & (1 << (door - 1))) === 0) continue;
      let nextHeld = held;
      const key = Number(cell(handle, CELL.key, next));
      if (key > 0) nextHeld |= 1 << (key - 1);
      const nextState = next * maskCount + nextHeld;
      if (previous[nextState] !== -2) continue;
      previous[nextState] = encoded;
      previousAction[nextState] = direction.action;
      queue.push(nextState);
    }
  }
  assert.notEqual(goalState, -1, "generated cells contain a path to the exit");
  const path = [];
  for (let encoded = goalState; previous[encoded] !== -1; encoded = previous[encoded]) {
    path.push(previousAction[encoded]);
  }
  path.reverse();
  return path;
}

assert.equal(TASK, 3848665378n, "Maze keeps its stable task ID");
assert.equal(Number(exports.nw_api_v1_supports(TASK)), 1);
assert.equal(create([0n, 1n, 0n, 1n, 0n, 0n]), STATUS.badOptions,
  "rung is one-based and follows the source grade table");
assert.equal(create([1n, 4n, 0n, 1n, 0n, 0n]), STATUS.badOptions,
  "trial count follows the source option choices");
assert.equal(create([1n, 1n, 2n, 1n, 0n, 0n]), STATUS.badOptions,
  "adaptive is boolean");
assert.equal(create([1n, 1n, 0n, 2n, 0n, 0n]), STATUS.badOptions,
  "show-trail is boolean");

const run = create();
assert.ok(run > 0n);
assert.equal(exports.nw_api_v1_maze_info(run, 999n), -1n);
assert.deepEqual(state(run), [0n, 1n, 0n, 1n, 0n, 0n, -1n, 0n, 0n, 0n, 0n, 0n]);

assert.equal(event(run, EVENT.keyDown, 100, 0, KEY.space, 32n), STATUS.accepted,
  "Space starts the source run");
assert.equal(info(run, INFO.phase), PHASE.walking);
assert.equal(info(run, INFO.trial), 1n);
assert.equal(info(run, INFO.doorCount), 0n);
assert.equal(info(run, INFO.held), 0n);

const path = solvePath(run);
let timestamp = 101;
let sequence = 1;
for (const action of path) {
  assert.equal(event(run, EVENT.action, timestamp++, sequence++, BigInt(action)),
    STATUS.accepted);
}
assert.equal(info(run, INFO.phase), PHASE.solved,
  "the real generated route reaches the source exit");
assert.equal(info(run, INFO.walker), info(run, INFO.wayOut));
assert.equal(info(run, INFO.steps), BigInt(path.length));
assert.equal(info(run, INFO.steps), info(run, INFO.minimum),
  "the BFS route matches the controller's shortest-path certificate");
assert.equal(info(run, INFO.verdict), 1n);
assert.deepEqual(render(run), render(run),
  "Maze rendering is observational and deterministic");

assert.equal(event(run, EVENT.keyDown, timestamp++, sequence++, KEY.enter, 13n),
  STATUS.accepted, "Enter is the browser-friendly next-maze alias");
assert.equal(info(run, INFO.phase), PHASE.done);
assert.equal(info(run, INFO.solvedCount), 1n);
assert.equal(info(run, INFO.bestRung), 1n);
assert.equal(exports.nw_api_v1_destroy(run), 0n);
assert.equal(exports.nw_api_v1_destroy(run), 0n,
  "common v1 destruction remains idempotent for Maze");

// The first rung deliberately has no locks. Exercise the same exported route
// oracle on a door-bearing grade so keys and locked cells are not just stored
// metadata. The BFS tracks (cell, held-key-mask), exactly like Maze::search.
const lockedRun = create([3n, 1n, 0n, 1n, 0n, 0n], 17n);
assert.ok(lockedRun > 0n);
assert.equal(event(lockedRun, EVENT.keyDown, 100, 0, KEY.space, 32n), STATUS.accepted);
assert.equal(info(lockedRun, INFO.doorCount), 1n);
const lockedPath = solvePath(lockedRun);
let lockedTimestamp = 101;
let lockedSequence = 1;
for (const action of lockedPath) {
  assert.equal(event(lockedRun, EVENT.action, lockedTimestamp++, lockedSequence++, BigInt(action)),
    STATUS.accepted);
}
assert.equal(info(lockedRun, INFO.phase), PHASE.solved,
  "a key-aware route opens the door and reaches the exit");
assert.equal(info(lockedRun, INFO.steps), info(lockedRun, INFO.minimum));
assert.equal(info(lockedRun, INFO.held), 1n);
assert.equal(exports.nw_api_v1_destroy(lockedRun), 0n);

console.log("PASS: Maze source-backed lifecycle, generated solution, grading, render, and cleanup");
