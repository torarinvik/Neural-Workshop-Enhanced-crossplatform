// Stateful 3D Maze smoke: solve the generated first-person maze through the
// exported topology while accounting for orientation and turn costs.
import assert from "node:assert/strict";
import fs from "node:fs";
import { fileURLToPath } from "node:url";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";

const root = fileURLToPath(new URL("..", import.meta.url));
const wasm = process.env.NWCORE_WASM_PATH ?? `${root}/build/nwcore.wasm`;
const { exports, instance } = await instantiateElisa(fs.readFileSync(wasm), { warn: false });
const TASK = BigInt(exports.nw_api_v1_task_you_are_here());
const EVENT = Object.freeze({ action: 1n, keyDown: 2n });
const STATUS = Object.freeze({ accepted: 1n, badOptions: -3n });
const KEY = Object.freeze({ space: 1n, enter: 2n });
const ACTION = Object.freeze({ start: 0, ahead: 1, back: 2, left: 3, right: 4, restart: 5 });
const INFO = Object.freeze({ phase: 0, trial: 2, totalTrials: 3, player: 4,
  facing: 5, steps: 6, held: 7, verdict: 8, width: 9, height: 10,
  minimum: 11, doorCount: 12, start: 13, wayOut: 14, solved: 15 });
const CELL = Object.freeze({ wall: 0, door: 1, key: 2 });
const STATE_BYTES = 112;
const FRAME_BYTES = 65536;
const statePtr = Number(exports.nw_frame_alloc(BigInt(STATE_BYTES)));
const framePtr = Number(exports.nw_frame_alloc(BigInt(FRAME_BYTES)));

function create(options = [1n, 1n, 0n, 1n, 0n, 0n], seed = 17n) {
  return exports.nw_api_v1_create(TASK, 1n, ...options, seed);
}
function info(handle, field) {
  return BigInt(exports.nw_api_v1_you_are_here_info(handle, BigInt(field)));
}
function cell(handle, field, at) {
  return BigInt(exports.nw_api_v1_you_are_here_cell(handle, BigInt(field), BigInt(at)));
}
function event(handle, kind, time, sequence, code, value = 0n) {
  return exports.nw_api_v1_dispatch(handle, kind, BigInt(time), BigInt(sequence),
    code, value, 0n, 0n, 0n, 0n, 0n);
}
function render(handle) {
  const length = exports.nw_api_v1_render(handle, BigInt(framePtr), BigInt(FRAME_BYTES),
    0n, 912n, 684n);
  assert.ok(length > 0n);
  return new Uint8Array(instance.exports.memory.buffer, framePtr, Number(length)).slice();
}

function solve(handle) {
  const width = Number(info(handle, INFO.width));
  const height = Number(info(handle, INFO.height));
  const start = Number(info(handle, INFO.start));
  const goal = Number(info(handle, INFO.wayOut));
  const doorCount = Number(info(handle, INFO.doorCount));
  const masks = 1 << doorCount;
  const stateCount = width * height * 4 * masks;
  const encode = (cellAt, facing, held) => ((cellAt * 4 + facing) * masks) + held;
  const queue = [encode(start, Number(info(handle, INFO.facing)), Number(info(handle, INFO.held)))];
  const previous = new Int32Array(stateCount).fill(-2);
  const previousAction = new Int8Array(stateCount);
  previous[queue[0]] = -1;
  const dirs = [[0, -1], [1, 0], [0, 1], [-1, 0]];
  let found = -1;
  for (let head = 0; head < queue.length && found < 0; head++) {
    const state = queue[head];
    const held = state % masks;
    const pose = Math.floor(state / masks);
    const facing = pose % 4;
    const at = Math.floor(pose / 4);
    if (at === goal) { found = state; break; }
    const actions = [ACTION.ahead, ACTION.back, ACTION.left, ACTION.right];
    for (const action of actions) {
      let nextFacing = facing;
      let next = at;
      if (action === ACTION.left) nextFacing = (facing + 3) % 4;
      else if (action === ACTION.right) nextFacing = (facing + 1) % 4;
      else {
        const direction = action === ACTION.ahead ? facing : (facing + 2) % 4;
        const x = at % width + dirs[direction][0];
        const y = Math.floor(at / width) + dirs[direction][1];
        if (x < 0 || x >= width || y < 0 || y >= height) continue;
        next = y * width + x;
        if (cell(handle, CELL.wall, next) !== 0n) continue;
        const door = Number(cell(handle, CELL.door, next));
        if (door > 0 && (held & (1 << (door - 1))) === 0) continue;
      }
      let nextHeld = held;
      const key = Number(cell(handle, CELL.key, next));
      if (key > 0) nextHeld |= 1 << (key - 1);
      const nextState = encode(next, nextFacing, nextHeld);
      if (previous[nextState] !== -2) continue;
      previous[nextState] = state;
      previousAction[nextState] = action;
      queue.push(nextState);
    }
  }
  assert.notEqual(found, -1, "generated 3D maze has a reachable exit");
  const route = [];
  for (let state = found; previous[state] !== -1; state = previous[state]) route.push(previousAction[state]);
  route.reverse();
  return route;
}

assert.equal(TASK, 1837057308n);
assert.equal(Number(exports.nw_api_v1_supports(TASK)), 1);
assert.equal(create([0n, 1n, 0n, 1n, 0n, 0n]), STATUS.badOptions);
const run = create();
assert.ok(run > 0n);
assert.equal(info(run, INFO.phase), 0n);
assert.equal(event(run, EVENT.keyDown, 100, 0, KEY.space, 32n), STATUS.accepted);
assert.equal(info(run, INFO.phase), 1n);
const readyFrame = render(run);
const initialFacing = info(run, INFO.facing);
const initialPlayer = info(run, INFO.player);
assert.equal(event(run, EVENT.action, 101, 1, BigInt(ACTION.left)), STATUS.accepted);
assert.notEqual(info(run, INFO.facing), initialFacing, "left turns in place");
assert.equal(info(run, INFO.player), initialPlayer, "turning does not move the player");
assert.equal(info(run, INFO.steps), 1n, "turning has the source step cost");
assert.equal(event(run, EVENT.action, 102, 2, BigInt(ACTION.restart)), STATUS.accepted);
assert.equal(info(run, INFO.player), initialPlayer, "restart returns to the dealt start");
assert.equal(info(run, INFO.facing), initialFacing, "restart restores the source heading");
assert.equal(info(run, INFO.steps), 0n);
let sequence = 3;
let wallTested = false;
const width = Number(info(run, INFO.width));
const height = Number(info(run, INFO.height));
const start = Number(info(run, INFO.player));
const directions = [[0, -1], [1, 0], [0, 1], [-1, 0]];
for (let absolute = 0; absolute < 4 && !wallTested; absolute++) {
  const x = start % width + directions[absolute][0];
  const y = Math.floor(start / width) + directions[absolute][1];
  if (x < 0 || x >= width || y < 0 || y >= height || cell(run, CELL.wall, y * width + x) !== 0n) {
    const turns = (absolute - Number(initialFacing) + 4) % 4;
    for (let turn = 0; turn < turns; turn++) {
      assert.equal(event(run, EVENT.action, 102 + sequence, sequence++, BigInt(ACTION.right)), STATUS.accepted);
    }
    const beforeSteps = info(run, INFO.steps);
    const beforePlayer = info(run, INFO.player);
    assert.equal(event(run, EVENT.action, 102 + sequence, sequence++, BigInt(ACTION.ahead)), STATUS.accepted);
    assert.equal(info(run, INFO.player), beforePlayer, "a wall rejects forward motion");
    assert.equal(info(run, INFO.steps), beforeSteps, "a blocked move has no step cost");
    wallTested = true;
  }
}
assert.equal(wallTested, true, "the generated start has a testable wall boundary");
assert.equal(event(run, EVENT.action, 102 + sequence, sequence++, BigInt(ACTION.restart)), STATUS.accepted);
const route = solve(run);
let time = 103 + sequence;
for (let routeIndex = 0; routeIndex < route.length; routeIndex++) {
  assert.equal(event(run, EVENT.action, time++, sequence++, BigInt(route[routeIndex])), STATUS.accepted);
}
assert.equal(info(run, INFO.phase), 2n);
assert.equal(info(run, INFO.player), info(run, INFO.wayOut));
assert.equal(info(run, INFO.steps), info(run, INFO.minimum));
assert.equal(info(run, INFO.verdict), 1n);
assert.notDeepEqual(readyFrame, render(run));
const wideLength = exports.nw_api_v1_render(run, BigInt(framePtr), BigInt(FRAME_BYTES),
  0n, 1280n, 720n);
assert.ok(wideLength > 0n, "3D render remains valid after an aspect change");
assert.equal(exports.nw_api_v1_destroy(run), 0n);
console.log("PASS: 3D Maze generated topology, turn-aware solution, first-person render, grading, and cleanup");
