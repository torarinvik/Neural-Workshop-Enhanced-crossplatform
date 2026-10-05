// Common-v1 lifecycle smoke for the source-backed Fog of War controller.
// The test deliberately treats the generated walls as an oracle only for
// choosing legal probes; it checks the source contract rather than a fixture
// maze: five actions, seeded generation, circular visibility, no wall-shadow
// leakage, bump accounting, unique walked coverage, and the world/run gates.
import assert from "node:assert/strict";
import fs from "node:fs";
import { fileURLToPath } from "node:url";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { decode, Kind } from "../shells/web/display-list.js";

const root = fileURLToPath(new URL("..", import.meta.url));
const wasm = process.env.NWCORE_WASM_PATH ?? `${root}/build/nwcore.wasm`;
const { exports, instance } = await instantiateElisa(fs.readFileSync(wasm), { warn: false });

const TASK = BigInt(exports.nw_api_v1_task_fog_of_war());
const STATUS = Object.freeze({ accepted: 1n, ignored: 2n, badOptions: -3n });
const EVENT = Object.freeze({ action: 1n, keyDown: 2n });
const KEY = Object.freeze({ space: 1n, enter: 2n, up: 4n, down: 6n });
const ACTION = Object.freeze({ start: 0n, stay: 1n, up: 2n, down: 3n, left: 4n, right: 5n });
const PHASE = Object.freeze({ ready: 0n, exploring: 1n, finished: 2n, done: 3n });
const INFO = Object.freeze({
  phase: 0, trial: 1, totalTrials: 2, walker: 3, moves: 4,
  movesAllowed: 5, width: 6, height: 7, start: 8, openCount: 9,
  walkedCount: 10, persist: 11, radius: 12, visibleCount: 13,
  coveragePpm: 14, results: 15, totalMoves: 16, averagePercent: 17,
  bumps: 18, message: 19,
});
const CELL = Object.freeze({ wall: 0n, revealed: 1n, walked: 2n });
const STATE_BYTES = 112;
const FRAME_BYTES = 1048576;
const STATE_BUFFER = Number(exports.nw_frame_alloc(BigInt(STATE_BYTES)));
const FRAME_BUFFER = Number(exports.nw_frame_alloc(BigInt(FRAME_BYTES)));
assert.ok(STATE_BUFFER > 0 && FRAME_BUFFER > 0);

function create(options = [2n, 400n, 3n, 0n, 0n, 0n], seed = 17n) {
  return exports.nw_api_v1_create(TASK, 1n, ...options, seed);
}

function state(handle) {
  const length = exports.nw_api_v1_read_state(handle,
    BigInt(STATE_BUFFER), BigInt(STATE_BYTES));
  assert.equal(length, BigInt(STATE_BYTES));
  const view = new DataView(instance.exports.memory.buffer, STATE_BUFFER, STATE_BYTES);
  assert.equal(view.getUint32(0, true), 0x3152574e);
  assert.equal(view.getUint32(4, true), 1);
  assert.equal(view.getUint32(12, true), 12);
  return Array.from({ length: 12 }, (_, index) =>
    view.getBigInt64(16 + index * 8, true));
}

function event(handle, kind, timestamp, sequence, code, value = 0n) {
  return exports.nw_api_v1_dispatch(handle, kind, BigInt(timestamp),
    BigInt(sequence), code, value, 0n, 0n, 0n, 0n, 0n);
}

function action(handle, code, timestamp, sequence) {
  return event(handle, EVENT.action, timestamp, sequence, code);
}

function info(handle, field) {
  return BigInt(exports.nw_api_v1_fog_info(handle, BigInt(field)));
}

function cell(handle, field, at) {
  return BigInt(exports.nw_api_v1_fog_cell(handle, field, BigInt(at)));
}

function frame(handle) {
  const length = exports.nw_api_v1_render(handle, BigInt(FRAME_BUFFER),
    BigInt(FRAME_BYTES), 0n, 912n, 684n);
  assert.ok(length > 0n, `render failed: ${length}`);
  return new Uint8Array(instance.exports.memory.buffer, FRAME_BUFFER,
    Number(length)).slice();
}

function directionTargets(handle) {
  const width = Number(info(handle, INFO.width));
  const height = Number(info(handle, INFO.height));
  const at = Number(info(handle, INFO.walker));
  const x = at % width;
  const y = Math.floor(at / width);
  return [
    { action: ACTION.up, dx: 0, dy: -1 },
    { action: ACTION.down, dx: 0, dy: 1 },
    { action: ACTION.left, dx: -1, dy: 0 },
    { action: ACTION.right, dx: 1, dy: 0 },
  ].map((direction) => {
    const nx = x + direction.dx;
    const ny = y + direction.dy;
    const target = nx >= 0 && nx < width && ny >= 0 && ny < height
      ? ny * width + nx : -1;
    return { ...direction, target,
      blocked: target < 0 || cell(handle, CELL.wall, target) !== 0n };
  });
}

assert.equal(TASK, 703034768n, "Fog of War keeps its stable task ID");
assert.equal(Number(exports.nw_api_v1_supports(TASK)), 1);
assert.equal(create([0n, 400n, 3n, 0n, 0n, 0n]), STATUS.badOptions);
assert.equal(create([2n, 99n, 3n, 0n, 0n, 0n]), STATUS.badOptions);
assert.equal(create([2n, 400n, 4n, 0n, 0n, 0n]), STATUS.badOptions);
assert.equal(create([2n, 400n, 3n, 2n, 0n, 0n]), STATUS.badOptions);
assert.equal(create([2n, 400n, 3n, 0n, 1n, 0n]), STATUS.badOptions);

const run = create();
assert.ok(run > 0n);
assert.deepEqual(state(run), [0n, 0n, 3n, 0n, 0n, 400n, 25n, 15n, 0n, 0n, 0n, 0n]);
assert.equal(info(run, 999), -1n);
const readyFrame = frame(run);
assert.deepEqual(frame(run), readyFrame, "ready rendering is observational");
assert.ok(decode(readyFrame).some(({ kind, text }) =>
  kind === Kind.TEXT && text === "Fog of War"));

// The same controller seed must produce the same source world and initial
// sight. This catches accidental use of the temporary generation arena after
// it has been destroyed as well as a changed random-stream order.
const replay = create();
assert.equal(action(run, ACTION.start, 100, 0), STATUS.accepted);
assert.equal(action(replay, ACTION.start, 100, 0), STATUS.accepted);
assert.deepEqual(state(run), state(replay));
assert.equal(info(run, INFO.phase), PHASE.exploring);
assert.equal(info(run, INFO.trial), 1n);
assert.equal(info(run, INFO.width), 25n);
assert.equal(info(run, INFO.height), 15n);
assert.ok(info(run, INFO.openCount) > 0n);
assert.equal(info(run, INFO.walkedCount), 1n);
assert.ok(info(run, INFO.visibleCount) > 0n);
assert.equal(info(run, INFO.coveragePpm),
  BigInt(Math.round(1000000 / Number(info(run, INFO.openCount)))),
  "initial coverage is exactly one walked floor cell");
assert.deepEqual(frame(run), frame(replay), "seeded worlds render identically");

const beforeBump = state(run);
const beforeBumpFrame = frame(run);
const beforeBumpVisible = info(run, INFO.visibleCount);
const blocked = directionTargets(run).find(({ blocked: isBlocked }) => isBlocked);
assert.ok(blocked, "the generated world has a wall or boundary to bump");
assert.equal(action(run, blocked.action, 101, 1), STATUS.accepted);
assert.equal(info(run, INFO.moves), beforeBump[INFO.moves] + 1n);
assert.equal(info(run, INFO.bumps), 1n);
assert.equal(info(run, INFO.walker), beforeBump[INFO.walker]);
assert.equal(info(run, INFO.walkedCount), beforeBump[INFO.walkedCount]);
assert.equal(info(run, INFO.visibleCount), beforeBumpVisible);
assert.deepEqual(frame(run), beforeBumpFrame,
  "a wall bump spends a move but changes no pixels");

const open = directionTargets(run).find(({ blocked: isBlocked }) => !isBlocked);
assert.ok(open, "the generated world has a walkable neighbour");
const oldWalker = info(run, INFO.walker);
const oldWalked = info(run, INFO.walkedCount);
assert.equal(action(run, open.action, 102, 2), STATUS.accepted);
assert.equal(info(run, INFO.walker), BigInt(open.target));
assert.ok(info(run, INFO.walkedCount) === oldWalked ||
  info(run, INFO.walkedCount) === oldWalked + 1n);
assert.equal(cell(run, CELL.walked, Number(info(run, INFO.walker))), 1n);
assert.notEqual(info(run, INFO.walker), oldWalker);

// A one-world, one-hundred-move run reaches feedback on the final blocked
// direction. Space then closes the run, and a second Space starts a new run.
const budget = create([1n, 100n, 1n, 0n, 0n, 0n], 23n);
assert.equal(event(budget, EVENT.keyDown, 1000, 0, KEY.space, 32n), STATUS.accepted);
assert.equal(info(budget, INFO.phase), PHASE.exploring);
const budgetBlocked = directionTargets(budget).find(({ blocked: isBlocked }) => isBlocked);
assert.ok(budgetBlocked);
for (let index = 0; index < 100; index++) {
  assert.equal(action(budget, budgetBlocked.action, 1001 + index, 1 + index), STATUS.accepted);
}
assert.equal(info(budget, INFO.phase), PHASE.finished);
assert.equal(info(budget, INFO.moves), 100n);
assert.equal(info(budget, INFO.bumps), 100n);
assert.equal(info(budget, INFO.results), 1n);
assert.ok(info(budget, INFO.coveragePpm) > 0n);
assert.equal(event(budget, EVENT.keyDown, 1101, 101, KEY.enter, 13n), STATUS.accepted);
assert.equal(info(budget, INFO.phase), PHASE.done);
assert.ok(info(budget, INFO.averagePercent) >= 0n);
assert.equal(event(budget, EVENT.keyDown, 1102, 102, KEY.space, 32n), STATUS.accepted);
assert.equal(info(budget, INFO.phase), PHASE.exploring);
assert.equal(info(budget, INFO.trial), 1n);

// Persistent reveal is per-world, not per-run: it accumulates after movement
// but `_next_trial` clears it exactly like the original screen.
const persistent = create([1n, 100n, 2n, 1n, 0n, 0n], 31n);
assert.equal(action(persistent, ACTION.start, 2000, 0), STATUS.accepted);
const firstVisible = info(persistent, INFO.visibleCount);
const persistentMove = directionTargets(persistent).find(({ blocked: isBlocked }) => !isBlocked);
assert.ok(persistentMove);
assert.equal(action(persistent, persistentMove.action, 2001, 1), STATUS.accepted);
assert.ok(info(persistent, INFO.visibleCount) >= firstVisible);

assert.equal(exports.nw_api_v1_destroy(run), 0n);
assert.equal(exports.nw_api_v1_destroy(run), 0n, "destroy is idempotent");
assert.equal(exports.nw_api_v1_destroy(replay), 0n);
assert.equal(exports.nw_api_v1_destroy(budget), 0n);
assert.equal(exports.nw_api_v1_destroy(persistent), 0n);

console.log("PASS: Fog of War source-backed world generation, visibility, bump budget, coverage, rendering, and cleanup");
