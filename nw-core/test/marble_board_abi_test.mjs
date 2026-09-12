import assert from "node:assert/strict";
import fs from "node:fs";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { decodeMarbleBoard } from "../shells/web/marble-maze.js";

const wasm = fs.readFileSync(new URL("../build/nwcore.wasm", import.meta.url));
const { exports, instance } = await instantiateElisa(wasm, { warn: false });
const capacity = 65536;
const pointer = Number(exports.nw_frame_alloc(BigInt(capacity)));
let maximumLength = 0;
let maximumWalls = 0;
const expectedMarbles = [1, 1, 1, 1, 2, 1, 2, 1,
  3, 1, 2, 1, 4, 1, 2, 3];
for (let rung = 1; rung <= 16; rung++) {
  const length = Number(exports.nw_marble_board_write(
    BigInt(pointer), BigInt(capacity), BigInt(rung), 17n + BigInt(rung)));
  assert.ok(length > 0, `rung ${rung} did not produce a board`);
  maximumLength = Math.max(maximumLength, length);
  const bytes = new Uint8Array(instance.exports.memory.buffer, pointer, length);
  const board = decodeMarbleBoard(bytes);

  assert.equal(board.built, true, `rung ${rung} is not built`);
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
  maximumWalls = Math.max(maximumWalls, board.walls.length);
}

assert.ok(maximumLength < capacity, `board ABI exceeds capacity: ${maximumLength}`);
console.log(`PASS: Marble Maze board ABI (16 rungs, up to ${maximumWalls} walls)`);
