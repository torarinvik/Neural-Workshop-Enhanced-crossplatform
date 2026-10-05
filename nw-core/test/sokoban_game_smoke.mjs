// Real gameplay replay against the persistent Sokoban WASM controller.
// Unlike task_game_input_smoke.mjs this drives controller transitions and
// solves the generated board from its exported state; it does not fabricate
// a frame snapshot or verdict.
import assert from "node:assert/strict";
import fs from "node:fs";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { decode, Kind } from "../shells/web/display-list.js";

const wasm = process.argv[2]
  ? resolve(process.argv[2])
  : fileURLToPath(new URL("../build/nwcore.wasm", import.meta.url));
const { exports, instance } = await instantiateElisa(fs.readFileSync(wasm), { warn: false });
const RUN_BYTES = 600000;
const FRAME_BYTES = 65536;
const run = Number(exports.nw_frame_alloc(BigInt(RUN_BYTES)));
const frame = Number(exports.nw_frame_alloc(BigInt(FRAME_BYTES)));
assert.ok(run > 0 && frame > 0, "host allocations must succeed");

const INFO = Object.freeze({
  phase: 0, rung: 1, trial: 2, total: 3, player: 4, pushes: 5, moves: 6,
  verdict: 7, width: 8, height: 9, par: 10, minimum: 11, atLeast: 12,
  bound: 13, solved: 14, lost: 15, best: 16, efficiency: 17, hasLevel: 18,
});
const CELL = Object.freeze({ wall: 0, goal: 1, trap: 2, box: 3 });
const PHASE = Object.freeze({ ready: 0, pushing: 1, solved: 2, lost: 3, done: 4, unavailable: 5 });
const ACTION = Object.freeze({ space: 0, up: 1, down: 2, left: 3, right: 4, undo: 5, restart: 6 });
const STRIDE = (width) => [-width, width, -1, 1];

function info(field) {
  return Number(exports.nw_sokoban_run_info(BigInt(run), BigInt(field)));
}
function readCell(field, at) {
  return Number(exports.nw_sokoban_run_cell(BigInt(run), BigInt(field), BigInt(at)));
}
function act(action, now = 1000) {
  assert.equal(Number(exports.nw_sokoban_run_action(BigInt(run), BigInt(action), BigInt(now))), 1);
}
function frameBytes() {
  const length = Number(exports.nw_sokoban_run_frame_write(
    BigInt(frame), BigInt(FRAME_BYTES), BigInt(run), 0n, 912n, 684n));
  assert.ok(length > 0, "persistent game render returns a frame");
  return new Uint8Array(instance.exports.memory.buffer, frame, length).slice();
}
function state() {
  const width = info(INFO.width), height = info(INFO.height), cells = width * height;
  const walls = [], goals = [], boxes = [];
  for (let at = 0; at < cells; at++) {
    if (readCell(CELL.wall, at)) walls.push(at);
    if (readCell(CELL.goal, at)) goals.push(at);
    if (readCell(CELL.box, at)) boxes.push(at);
  }
  return { width, height, cells, walls: new Set(walls), goals: new Set(goals),
    boxes: new Set(boxes), player: info(INFO.player), pushes: info(INFO.pushes),
    moves: info(INFO.moves) };
}
function render() {
  const commands = decode(frameBytes());
  assert.ok(commands.length > 0, "gameplay frame decodes to display commands");
  assert.ok(commands.some((command) => command.kind === Kind.TEXT && command.text.includes("Sokoban")),
    "live controller frame includes the Sokoban scene");
  return commands;
}
function key(s, action) {
  return `${s.player}|${[...s.boxes].sort((a, b) => a - b).join(",")}|${action}`;
}
function findSolution(initial) {
  const deltas = STRIDE(initial.width);
  const queue = [{ player: initial.player, boxes: [...initial.boxes], parent: -1, action: -1 }];
  const seen = new Set([`${initial.player}|${[...initial.boxes].sort((a, b) => a - b).join(",")}`]);
  let head = 0;
  let goalIndex = -1;
  while (head < queue.length) {
    const currentIndex = head++;
    const current = queue[currentIndex];
    if (current.boxes.every((box) => initial.goals.has(box))) {
      goalIndex = currentIndex;
      break;
    }
    for (let direction = 0; direction < 4; direction++) {
      const ahead = current.player + deltas[direction];
      if (ahead < 0 || ahead >= initial.cells || initial.walls.has(ahead)) continue;
      const boxes = current.boxes.slice();
      const boxIndex = boxes.indexOf(ahead);
      if (boxIndex >= 0) {
        const beyond = ahead + deltas[direction];
        if (beyond < 0 || beyond >= initial.cells || initial.walls.has(beyond) || boxes.includes(beyond)) continue;
        boxes[boxIndex] = beyond;
      }
      const canonical = `${ahead}|${boxes.slice().sort((a, b) => a - b).join(",")}`;
      if (seen.has(canonical)) continue;
      seen.add(canonical);
      queue.push({ player: ahead, boxes, parent: currentIndex, action: direction });
    }
  }
  if (goalIndex < 0) throw new Error("generated Sokoban board has no player-reachable solution");
  const actions = [];
  for (let at = goalIndex; queue[at].parent >= 0; at = queue[at].parent) actions.push(queue[at].action);
  return actions.reverse();
}
function actionForDirection(direction) {
  return [ACTION.up, ACTION.down, ACTION.left, ACTION.right][direction];
}
function findBlockedPush(initial) {
  const deltas = STRIDE(initial.width);
  const queue = [{ player: initial.player, boxes: [...initial.boxes], parent: -1, action: -1 }];
  const seen = new Set([`${initial.player}|${[...initial.boxes].sort((a, b) => a - b).join(",")}`]);
  let head = 0;
  while (head < queue.length) {
    const currentIndex = head++;
    const current = queue[currentIndex];
    for (let direction = 0; direction < 4; direction++) {
      const ahead = current.player + deltas[direction];
      if (ahead < 0 || ahead >= current.cells || initial.walls.has(ahead)) continue;
      const boxIndex = current.boxes.indexOf(ahead);
      if (boxIndex >= 0) {
        const beyond = ahead + deltas[direction];
        const blocked = beyond < 0 || beyond >= initial.cells ||
          initial.walls.has(beyond) || current.boxes.includes(beyond);
        if (blocked) {
          const path = [];
          for (let at = currentIndex; queue[at].parent >= 0; at = queue[at].parent) {
            path.push(queue[at].action);
          }
          return { path: path.reverse(), action: direction };
        }
      }
      const boxes = current.boxes.slice();
      if (boxIndex >= 0) boxes[boxIndex] = ahead + deltas[direction];
      const canonical = `${ahead}|${boxes.slice().sort((a, b) => a - b).join(",")}`;
      if (seen.has(canonical)) continue;
      seen.add(canonical);
      queue.push({ player: ahead, boxes, parent: currentIndex, action: direction, cells: initial.cells });
    }
  }
  return null;
}
function equalBoard(actual, expected, label) {
  assert.equal(actual.player, expected.player, `${label}: player cell`);
  assert.deepEqual([...actual.boxes].sort((a, b) => a - b),
    [...expected.boxes].sort((a, b) => a - b), `${label}: crate cells`);
  assert.equal(actual.pushes, expected.pushes, `${label}: push counter`);
  assert.equal(actual.moves, expected.moves, `${label}: move counter`);
}

assert.equal(Number(exports.nw_sokoban_run_init(BigInt(run), 2n, 1n, 0n, 0n, 17n)), 1);
assert.equal(info(INFO.phase), PHASE.ready, "new run begins ready");
const readyFrameBytes = frameBytes();
render();
// Directional keys must not implicitly start a task; this mirrors the source
// UI, where step() ignores keys outside its pushing phase.
act(ACTION.up);
assert.equal(info(INFO.phase), PHASE.ready, "movement does not start a run");
act(ACTION.space);
assert.equal(info(INFO.phase), PHASE.pushing, "Space starts a generated puzzle");
assert.equal(info(INFO.hasLevel), 1, "started run owns a real generated level");
assert.equal(info(INFO.trial), 1, "first puzzle is trial one");
const activeFrameBytes = frameBytes();
assert.notDeepEqual(activeFrameBytes, readyFrameBytes,
  "a live controller frame cannot be replaced by the stale ready frame");
const initial = state();
assert.ok(initial.width > 0 && initial.height > 0 && initial.boxes.size > 0 && initial.goals.size > 0);
assert.ok(!initial.walls.has(initial.player), "player starts on floor");
render();

// A wall bump is an exact no-op: no movement, push, or hidden step changes.
const wallDirection = STRIDE(initial.width).findIndex((delta) => initial.walls.has(initial.player + delta));
assert.notEqual(wallDirection, -1, "generated player has a neighboring wall for bump replay");
act(actionForDirection(wallDirection));
equalBoard(state(), initial, "wall bump");

// Exercise every direction that is a boundary or wall from the generated
// start position. The controller must not turn an out-of-board index into a
// wrapped row, a hidden move, or a counter update.
for (let direction = 0; direction < 4; direction++) {
  const ahead = initial.player + STRIDE(initial.width)[direction];
  if (ahead < 0 || ahead >= initial.cells || initial.walls.has(ahead)) {
    act(actionForDirection(direction));
    equalBoard(state(), initial, `boundary/wall direction ${direction}`);
  }
}

// Walk to an empty neighboring tile, then undo it. The board returns exactly
// to its source state and the two public counters rewind with it.
const walkDirection = STRIDE(initial.width).findIndex((delta) => {
  const ahead = initial.player + delta;
  return ahead >= 0 && ahead < initial.cells && !initial.walls.has(ahead) && !initial.boxes.has(ahead);
});
assert.notEqual(walkDirection, -1, "generated player has a walkable neighbor");
act(actionForDirection(walkDirection));
const walked = state();
assert.equal(walked.moves, initial.moves + 1, "legal walk increments move count");
assert.notEqual(walked.player, initial.player, "legal walk changes player position");
act(ACTION.undo);
equalBoard(state(), initial, "undo of walk");

// A push into a wall or another crate is also an exact no-op. Find a reachable
// blocked push in the generated board instead of assuming a particular level
// layout, replay the route through the real controller, and compare every
// observable board counter before and after the rejected action.
const blockedPush = findBlockedPush({ ...initial, cells: initial.cells });
assert.ok(blockedPush, "generated board has a reachable blocked push for replay");
for (const direction of blockedPush.path) act(actionForDirection(direction));
const beforeBlockedPush = state();
act(actionForDirection(blockedPush.action));
equalBoard(state(), beforeBlockedPush, "blocked crate push");
act(ACTION.restart);
equalBoard(state(), initial, "restart after blocked push");

// Grow beyond the controller's initial 64-entry allocation, then unwind the
// whole stack. This specifically covers realloc movement and exact LIFO undo,
// without imposing a source-incompatible maximum number of legal moves.
const reverseDirection = [1, 0, 3, 2][walkDirection];
for (let move = 0; move < 70; move++) {
  act(actionForDirection(move % 2 === 0 ? walkDirection : reverseDirection));
}
assert.equal(info(INFO.moves), 70, "long walk is not capped at the first history allocation");
for (let move = 0; move < 70; move++) act(ACTION.undo);
equalBoard(state(), initial, "70-move dynamically grown undo history");

// Find and replay a full solution from the exported board, so success cannot
// be manufactured by incrementing a phase, generic input value, or answer key.
const solution = findSolution(initial);
assert.ok(solution.length > 0 && solution.length < 5000, "board has a bounded legal solution");
let sawPush = false;
let pushCount = 0;
let pushSnapshot = null;
for (const direction of solution) {
  const before = state();
  const ahead = before.player + STRIDE(before.width)[direction];
  const wasPush = before.boxes.has(ahead);
  if (wasPush) pushCount++;
  act(actionForDirection(direction), 1000 + info(INFO.moves) * 1000);
  const after = state();
  if (wasPush && !sawPush) {
    sawPush = true;
    pushSnapshot = { before, after, direction };
    assert.equal(after.pushes, before.pushes + 1, "legal crate push increments push counter");
    assert.ok(!after.boxes.has(ahead), "crate leaves its prior cell on a push");
  }
}
assert.ok(sawPush, "solution includes at least one real crate push");
assert.equal(info(INFO.phase), PHASE.solved, "all generated crates on goals settles the puzzle");
assert.equal(info(INFO.verdict), 1, "source par verdict is emitted only on solve");
assert.equal(info(INFO.solved), 1, "solved-puzzle result is recorded");
render();

// Solved -> Space finishes the one-trial run and exposes a real summary.
act(ACTION.space, 9000);
assert.equal(info(INFO.phase), PHASE.done, "Space after final solved puzzle ends run");
assert.equal(info(INFO.best), 2, "summary records highest solved rung");
assert.ok(info(INFO.efficiency) >= 0, "summary computes push efficiency");
render();

// Reinitializing a persistent handle clears its prior run and can start again.
assert.equal(Number(exports.nw_sokoban_run_dispose(BigInt(run))), 1,
  "explicitly release the old run's dynamically grown undo buffer");
assert.equal(Number(exports.nw_sokoban_run_init(BigInt(run), 2n, 1n, 0n, 0n, 17n)), 1);
assert.equal(info(INFO.phase), PHASE.ready, "reinitialization returns to ready");
act(ACTION.space);
const restartStart = state();
const restartPath = findSolution(restartStart);
act(actionForDirection(restartPath[0]));
assert.notEqual(info(INFO.moves), 0, "restart replay first makes a legal move");
act(ACTION.restart);
equalBoard(state(), restartStart, "restart restores the original board");
assert.equal(Number(exports.nw_sokoban_run_dispose(BigInt(run))), 1,
  "run disposal releases persistent dynamic history");

console.log(`PASS: live Sokoban WASM replay (${solution.length} solution moves, ${pushCount} crate pushes, 70-move undo growth)`);
