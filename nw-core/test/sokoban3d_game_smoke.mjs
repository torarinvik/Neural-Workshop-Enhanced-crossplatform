// Common-v1 lifecycle smoke for the source-backed 3D Sokoban controller.
// This deliberately checks that the 3D pose/camera action changes are not
// silently routed through the flat Sokoban controller.
import assert from "node:assert/strict";
import fs from "node:fs";
import { fileURLToPath } from "node:url";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { decode } from "../shells/web/display-list.js";

const wasm = process.env.NWCORE_WASM_PATH ??
  fileURLToPath(new URL("../build/nwcore.wasm", import.meta.url));
const { exports, instance } = await instantiateElisa(fs.readFileSync(wasm), { warn: false });
const TASK = BigInt(exports.nw_api_v1_task_sokoban_3d());
const EVENT_ACTION = 1n;
const ACTION = Object.freeze({ start: 0n, ahead: 1n, back: 2n, left: 3n,
  right: 4n, undo: 5n, restart: 6n });
const FIELD = Object.freeze({ phase: 0, rung: 1, trial: 2, total: 3,
  player: 4, facing: 5, steps: 6, pushes: 7, verdict: 8, width: 9,
  height: 10, par: 11 });
const PHASE = Object.freeze({ ready: 0n, pushing: 1n, solved: 2n,
  lost: 3n, done: 4n });
const STATUS = Object.freeze({ accepted: 1n, ignored: 2n });
const CELL = Object.freeze({ wall: 0, goal: 1, box: 3 });
const STATE_BYTES = 112n;
const FRAME_BYTES = 1048576n;
const statePtr = Number(exports.nw_frame_alloc(STATE_BYTES));
const framePtr = Number(exports.nw_frame_alloc(FRAME_BYTES));

function create(seed = 17n) {
  return exports.nw_api_v1_create(TASK, 1n, 2n, 1n, 1n, 0n, 0n, 0n, seed);
}
function state(handle) {
  assert.equal(exports.nw_api_v1_read_state(handle, BigInt(statePtr), STATE_BYTES), STATE_BYTES);
  const view = new DataView(instance.exports.memory.buffer, statePtr, Number(STATE_BYTES));
  assert.equal(view.getUint32(0, true), 0x3152574e);
  return Array.from({ length: 12 }, (_, index) =>
    view.getBigInt64(16 + index * 8, true));
}
function action(handle, code, timestamp, sequence) {
  return exports.nw_api_v1_dispatch(handle, EVENT_ACTION, BigInt(timestamp),
    BigInt(sequence), code, 0n, 0n, 0n, 0n, 0n, 0n);
}
function info(handle, field) {
  return exports.nw_api_v1_sokoban3d_info(handle, BigInt(field));
}
function cell(handle, field, at) {
  return Number(exports.nw_api_v1_sokoban3d_value(handle,
    BigInt(field), BigInt(at)));
}
function frame(handle) {
  const length = exports.nw_api_v1_render(handle, BigInt(framePtr), FRAME_BYTES,
    0n, 912n, 684n);
  assert.ok(length > 16n, "3D Sokoban render contains display commands");
  return decode(new Uint8Array(instance.exports.memory.buffer, framePtr,
    Number(length)));
}

assert.equal(TASK, 1429046936n, "stable 3D Sokoban task ID");
assert.equal(exports.nw_api_v1_supports(TASK), 1n);
const run = create();
assert.ok(run > 0n);
assert.deepEqual(state(run).slice(0, 4), [PHASE.ready, 2n, 0n, 1n]);
assert.ok(frame(run).length > 0, "ready frame is real, not a canned status");

assert.equal(action(run, ACTION.start, 0, 0), STATUS.accepted);
let values = state(run);
assert.equal(values[FIELD.phase], PHASE.pushing);
assert.equal(values[FIELD.width], 6n);
assert.equal(values[FIELD.height], 6n);
assert.ok(frame(run).length > 0);

const readyPlayer = values[FIELD.player];
const readyFacing = values[FIELD.facing];
assert.equal(action(run, ACTION.ahead, 1, 1), STATUS.accepted);
values = state(run);
assert.equal(values[FIELD.steps], 1n, "a 3D walk costs one step");
assert.notEqual(values[FIELD.player], readyPlayer, "3D movement updates the live pose");
assert.equal(action(run, ACTION.undo, 2, 2), STATUS.accepted);
values = state(run);
assert.equal(values[FIELD.player], readyPlayer);
assert.equal(values[FIELD.facing], readyFacing);
assert.equal(values[FIELD.steps], 0n);

assert.equal(action(run, ACTION.left, 3, 3), STATUS.accepted);
values = state(run);
assert.equal(values[FIELD.facing], (readyFacing + 3n) % 4n,
  "turning changes camera pose without changing board position");
assert.equal(values[FIELD.player], readyPlayer);
assert.equal(values[FIELD.steps], 1n);
assert.equal(exports.nw_api_v1_destroy(run), 0n);

// Solve the generated rung-2 warehouse from its exported board, then replay
// the route through the controller. This checks that the 3D action transform,
// push semantics, and source verdict are connected to the live state rather
// than merely incrementing a move counter.
const solvedRun = create(23n);
assert.equal(action(solvedRun, ACTION.start, 0, 0), STATUS.accepted);
const width = Number(info(solvedRun, FIELD.width));
const height = Number(info(solvedRun, FIELD.height));
const cells = width * height;
const walls = Array.from({ length: cells }, (_, at) => cell(solvedRun, CELL.wall, at) === 1);
const goals = Array.from({ length: cells }, (_, at) => cell(solvedRun, CELL.goal, at) === 1);
const initialBoxes = Array.from({ length: cells }, (_, at) => cell(solvedRun, CELL.box, at) === 1);
const initialPlayer = Number(state(solvedRun)[FIELD.player]);
const initialFacing = Number(state(solvedRun)[FIELD.facing]);
const deltas = [-width, 1, width, -1];
const routeQueue = [{ player: initialPlayer, facing: initialFacing,
  boxes: initialBoxes, route: [] }];
const seen = new Set();
let route = null;
while (routeQueue.length > 0 && route === null) {
  const current = routeQueue.shift();
  const key = `${current.player}/${current.facing}/${current.boxes.map((v) => v ? 1 : 0).join("")}`;
  if (seen.has(key)) continue;
  seen.add(key);
  if (current.boxes.every((hasBox, at) => !hasBox || goals[at])) {
    route = current.route;
    break;
  }
  for (const code of [ACTION.ahead, ACTION.back, ACTION.left, ACTION.right]) {
    let player = current.player;
    let facing = current.facing;
    let boxes = current.boxes.slice();
    if (code === ACTION.left) facing = (facing + 3) % 4;
    else if (code === ACTION.right) facing = (facing + 1) % 4;
    else {
      const direction = code === ACTION.ahead ? facing : (facing + 2) % 4;
      const next = player + deltas[direction];
      if (next < 0 || next >= cells || walls[next] ||
          Math.floor(next / width) !== Math.floor(player / width) &&
          (direction === 1 || direction === 3)) continue;
      if (boxes[next]) {
        const beyond = next + deltas[direction];
        if (beyond < 0 || beyond >= cells || walls[beyond] || boxes[beyond] ||
            Math.floor(beyond / width) !== Math.floor(next / width) &&
            (direction === 1 || direction === 3)) continue;
        boxes[next] = false;
        boxes[beyond] = true;
      }
      player = next;
    }
    routeQueue.push({ player, facing, boxes, route: [...current.route, code] });
  }
}
assert.ok(route && route.length > 0 && route.length < 1000,
  "generated 3D warehouse has a bounded solution route");
assert.equal(action(solvedRun, ACTION.restart, 1, 1), STATUS.accepted);
let sequence = 2;
for (const code of route) {
  assert.equal(action(solvedRun, code, sequence, sequence), STATUS.accepted,
    "solution actions are accepted by the live 3D controller");
  sequence += 1;
}
values = state(solvedRun);
assert.equal(values[FIELD.phase], PHASE.solved);
assert.equal(values[FIELD.verdict], 1n,
  "a generated source solution produces the source success verdict");
assert.equal(exports.nw_api_v1_destroy(solvedRun), 0n);
console.log("PASS: 3D Sokoban common lifecycle, source movement, camera turn, undo, render, and cleanup");
