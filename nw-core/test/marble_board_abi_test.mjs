import assert from "node:assert/strict";
import fs from "node:fs";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { decodeMarbleBoard } from "../shells/web/marble-maze.js";
import { marbleCupCollarOuterRadius } from "../shells/web/marble-maze-renderer.js";

const wasm = fs.readFileSync(process.env.NWCORE_WASM_PATH ??
  new URL("../build/nwcore.wasm", import.meta.url));
const { exports, instance } = await instantiateElisa(wasm, { warn: false });
const capacity = 65536;
const pointer = Number(exports.nw_frame_alloc(BigInt(capacity)));
let maximumLength = 0;
let maximumWalls = 0;
let boardsChecked = 0;
let minimumHoleWallClearance = Number.POSITIVE_INFINITY;
let minimumCollarWallClearance = Number.POSITIVE_INFINITY;
let adjustedHomeCollars = 0;
const expectedMarbles = [1, 1, 1, 1, 2, 1, 2, 1,
  3, 1, 2, 1, 4, 1, 2, 3];
const holeWallClearance = 0.0075 * 0.80;
const geometrySeeds = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9,
  10, 11, 12, 13, 14, 15, 16, 17, 314159, 1073741823];

// The shell receives a pointer/length pair from WASM, so malformed bytes must
// fail at the ABI boundary rather than reaching a count-controlled loop or
// leaking a DataView RangeError.
assert.throws(() => decodeMarbleBoard(new Uint8Array(68)),
  /marble board: bad header|marble board: truncated/);
{
  const hostile = new Uint8Array(68);
  const view = new DataView(hostile.buffer);
  view.setUint32(0, 826496845, true);
  view.setUint32(4, 1, true);
  view.setUint32(64, 0xffffffff, true);
  assert.throws(() => decodeMarbleBoard(hostile), /wall count too large/);
}
{
  const nonFinite = new Uint8Array(68);
  const view = new DataView(nonFinite.buffer);
  view.setUint32(0, 826496845, true);
  view.setUint32(4, 1, true);
  view.setFloat32(24, Number.NaN, true);
  assert.throws(() => decodeMarbleBoard(nonFinite), /non-finite width/);
}

const canonicalLength = Number(exports.nw_marble_board_write(
  BigInt(pointer), BigInt(capacity), 1n, 17n));
assert.ok(canonicalLength > 0, "canonical malformed-payload fixture was not generated");
const canonicalBytes = new Uint8Array(
  instance.exports.memory.buffer, pointer, canonicalLength).slice();

function variableOffsets(bytes) {
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  const wallCount = view.getUint32(64, true);
  const holeCountOffset = 68 + wallCount * 16;
  const holeCount = view.getUint32(holeCountOffset, true);
  const startsCountOffset = holeCountOffset + 4 + holeCount * 16;
  return {
    firstWall: 68,
    finalHole: holeCountOffset + 4 + (holeCount - 1) * 16,
    startsCount: startsCountOffset,
    firstStart: startsCountOffset + 4,
  };
}

function malformedBoard(label, edit, pattern) {
  const bytes = canonicalBytes.slice();
  const view = new DataView(bytes.buffer);
  edit(view, variableOffsets(bytes));
  assert.throws(() => decodeMarbleBoard(bytes), pattern, label);
}

malformedBoard("invalid boolean encoding", (view) => view.setUint32(8, 2, true),
  /invalid built flag/);
malformedBoard("out-of-range rung", (view) => view.setUint32(12, 0, true),
  /rung out of range/);
malformedBoard("reversed wall", (view, offsets) => {
  view.setFloat32(offsets.firstWall + 8, 0, true);
}, /wall geometry out of bounds/);
malformedBoard("invalid home flag", (view, offsets) => {
  view.setUint32(offsets.finalHole + 12, 2, true);
}, /invalid home flag/);
malformedBoard("home cup not last", (view, offsets) => {
  view.setUint32(offsets.finalHole + 12, 0, true);
}, /home cup ordering or geometry is invalid/);
malformedBoard("start outside tray", (view, offsets) => {
  const width = view.getFloat32(24, true);
  view.setFloat32(offsets.firstStart, width + 1, true);
}, /start is out of bounds/);
assert.throws(() => decodeMarbleBoard(
  new Uint8Array([...canonicalBytes, 0])), /trailing data/);

for (let rung = 1; rung <= 16; rung++) {
  for (const seed of geometrySeeds) {
    const length = Number(exports.nw_marble_board_write(
      BigInt(pointer), BigInt(capacity), BigInt(rung), BigInt(seed)));
    assert.ok(length > 0, `rung ${rung}, seed ${seed} did not produce a board`);
    maximumLength = Math.max(maximumLength, length);
    const bytes = new Uint8Array(instance.exports.memory.buffer, pointer, length);
    const board = decodeMarbleBoard(bytes);

    assert.equal(board.built, true, `rung ${rung}, seed ${seed} is not built`);
    assert.equal(board.rung, rung);
    assert.ok(board.cols >= 4 && board.rows >= 4);
    assert.ok(board.starts.length > 0);
    assert.equal(board.starts.length, expectedMarbles[rung - 1]);
    assert.equal(board.holes.at(-1).home, true);
    assert.ok(board.walls.length > 0);
    assert.ok(board.home.radius > 0);
    assert.ok(board.seconds > 0);
    assert.ok(board.width > 0 && board.depth > 0 && board.cell > 0);
    for (const wall of board.walls) {
      assert.ok(wall.x0 <= wall.x1 && wall.y0 <= wall.y1);
    }
    for (const hole of board.holes) {
      for (const wall of board.walls) {
        const dx = Math.max(wall.x0 - hole.x, 0, hole.x - wall.x1);
        const dy = Math.max(wall.y0 - hole.y, 0, hole.y - wall.y1);
        const clearance = Math.hypot(dx, dy) - hole.radius;
        minimumHoleWallClearance = Math.min(minimumHoleWallClearance, clearance);
        assert.ok(clearance >= holeWallClearance - 1e-6,
          `rung ${rung}, seed ${seed} hole overlaps wall ` +
          `(clearance ${clearance})`);
      }
      if (hole.home) {
        const outer = marbleCupCollarOuterRadius(board, hole);
        if (outer !== null) {
          assert.ok(outer > hole.radius,
            `rung ${rung}, seed ${seed} emitted a zero-width cup collar`);
          if (outer < hole.radius * 1.34 - 1e-9) adjustedHomeCollars += 1;
          for (const wall of board.walls) {
            const dx = Math.max(wall.x0 - hole.x, 0, hole.x - wall.x1);
            const dy = Math.max(wall.y0 - hole.y, 0, hole.y - wall.y1);
            const clearance = Math.hypot(dx, dy) - outer;
            minimumCollarWallClearance = Math.min(
              minimumCollarWallClearance, clearance);
            assert.ok(clearance >= holeWallClearance - 1e-6,
              `rung ${rung}, seed ${seed} cup collar overlaps wall ` +
              `(clearance ${clearance})`);
          }
        }
        if (rung === 14 && seed === 0) {
          assert.ok(outer === null || outer < hole.radius * 1.34 - 1e-9,
            "rung 14 seed 0 must retain the home-collar overlap regression");
        }
      }
    }
    maximumWalls = Math.max(maximumWalls, board.walls.length);
    boardsChecked += 1;
  }
}

assert.ok(maximumLength < capacity, `board ABI exceeds capacity: ${maximumLength}`);
assert.equal(boardsChecked, 16 * geometrySeeds.length);
assert.ok(adjustedHomeCollars > 0,
  "clearance sweep did not exercise the wall-trimmed cup collar");
console.log(`PASS: Marble Maze board ABI, hole/wall and cup-collar clearance ` +
  `(${boardsChecked} boards, up to ${maximumWalls} walls, ` +
  `hole minimum ${(minimumHoleWallClearance * 1000).toFixed(3)}mm, ` +
  `collar minimum ${(minimumCollarWallClearance * 1000).toFixed(3)}mm, ` +
  `${adjustedHomeCollars} collars trimmed)`);
