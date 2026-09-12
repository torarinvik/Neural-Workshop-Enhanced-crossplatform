import assert from "node:assert/strict";
import fs from "node:fs";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { decodeMarbleBoard, MARBLE } from "../shells/web/marble-maze.js";
import { loadMarbleMazeMuJoCo } from "../shells/web/marble-maze-mujoco.js";

const Game = await loadMarbleMazeMuJoCo();

function board(overrides = {}) {
  return {
    built: true, rung: 1, cols: 1, rows: 1, width: 1, depth: 1,
    cell: 1, thickness: 0.01, height: 0.01, seconds: 45, route: 1,
    home: { x: 0.8, y: 0.5, radius: 0.08 },
    walls: [], holes: [], starts: [{ x: 0.1, y: 0.5 }], ...overrides,
  };
}

// The browser adapter must use the same tilt signs and fixed four-substep
// schedule as the native Simulation.
{
  const game = new Game(board());
  for (let index = 0; index < 30; index++) game.tilt("E");
  for (let index = 0; index < 60; index++) game.step(1 / 60);
  const marble = game.marbles[0];
  assert.ok(marble.x > 0.1);
  assert.ok(marble.vx > 0.1);
  assert.ok(Math.abs(Math.hypot(marble.qw, marble.qx, marble.qy, marble.qz) - 1) < 1e-10);
  assert.ok(marble.qy < -0.05 || marble.qy > 0.05);
}

// Held controls are time-based, not one nudge per event: two half-ticks make
// one native tilt step and releasing clears the fractional remainder.
{
  const game = new Game(board());
  game.advance(1 / 120, new Set(["E"]));
  assert.equal(game.roll, 0);
  game.advance(1 / 120, new Set(["E"]));
  assert.equal(game.roll, MARBLE.TILT_STEP);
  game.advance(1 / 240, new Set(["E"]));
  game.advance(1 / 240, new Set());
  assert.equal(game.nudgeDue, 0);
}

// A levelled tray restores the native rest clamp, and restart preserves the
// elapsed run clock while recreating the physical state.
{
  const capped = new Game(board());
  capped.marbles[0].vx = 3;
  capped.rollWithTravel(capped.marbles[0]);
  capped.step(1 / 60);
  assert.ok(capped.speed <= MARBLE.SPEED_CAP + 1e-9);

  const game = new Game(board());
  game.marbles[0].vx = 0.005;
  game.rollWithTravel(game.marbles[0]);
  game.level();
  for (let index = 0; index < 30; index++) game.step(1 / 60);
  assert.ok(game.speed < 1e-10);
  const elapsed = game.elapsed;
  game.restart();
  assert.equal(game.elapsed, elapsed);
  assert.equal(game.marbles[0].x, game.board.starts[0].x);
  assert.equal(game.roll, 0);
  assert.equal(game.pitch, 0);
}

// Explicit wall pairs remain solid and preserve a measurable rolling skid on
// a square impact, as they do when MuJoCo runs the native MJCF.
{
  const wall = { x0: 0.30, y0: 0.02, x1: 0.31, y1: 0.40 };
  const game = new Game(board({ walls: [wall], starts: [{ x: 0.20, y: 0.20 }] }));
  const marble = game.marbles[0];
  marble.vx = 0.5;
  game.rollWithTravel(marble);
  let bounced = false;
  for (let index = 0; index < 120; index++) {
    game.step(1 / 60);
    if (marble.vx < 0) { bounced = true; break; }
  }
  assert.equal(bounced, true);
  assert.ok(game.slipping(marble) > 0.2);
}

// A slow pit crossing is swallowed, a fast crossing clears the far lip, and
// a home cup settles the run as a win.
{
  const pit = { x: 0.5, y: 0.5, radius: 1.6 * MARBLE.RADIUS, home: false };
  const slow = new Game(board({ starts: [{ x: 0.45, y: 0.5 }], holes: [pit] }));
  slow.marbles[0].vx = 0.4;
  for (let index = 0; index < 240 && !slow.settled; index++) slow.step(1 / 60);
  assert.equal(slow.marbles[0].state, "lost");

  const fast = new Game(board({ starts: [{ x: 0.45, y: 0.5 }], holes: [pit] }));
  fast.marbles[0].vx = 0.95;
  for (let index = 0; index < 240 && !fast.settled; index++) fast.step(1 / 60);
  assert.equal(fast.marbles[0].state, "rolling");

  const home = new Game(board({
    holes: [{ x: 0.5, y: 0.5, radius: 0.08, home: true }],
  }));
  home.marbles[0].vx = 0.4;
  for (let index = 0; index < 240 && !home.settled; index++) home.step(1 / 60);
  assert.equal(home.marbles[0].state, "home");
  assert.equal(home.won, true);
}

// Compile every certified board through the same MuJoCo model path. This
// catches malformed wall geometry, pair counts, or ABI data that a one-rung
// physics smoke test would miss.
const wasm = fs.readFileSync(new URL("../build/nwcore.wasm", import.meta.url));
const { exports, instance } = await instantiateElisa(wasm, { warn: false });
const capacity = 65536;
const pointer = Number(exports.nw_frame_alloc(BigInt(capacity)));
for (let rung = 1; rung <= 16; rung++) {
  const length = Number(exports.nw_marble_board_write(
    BigInt(pointer), BigInt(capacity), BigInt(rung), BigInt(17 + rung)));
  const boardBytes = new Uint8Array(instance.exports.memory.buffer, pointer, length);
  const tray = decodeMarbleBoard(boardBytes);
  const game = new Game(tray);
  game.step(1 / 60);
  assert.equal(game.marbles.length, tray.starts.length);
  assert.ok(game.marbles.every((marble) => Number.isFinite(marble.x)));
  game.disposeEngine();
}

console.log("PASS: MuJoCo-backed Marble Maze runtime, contacts, holes, and all 16 boards");
