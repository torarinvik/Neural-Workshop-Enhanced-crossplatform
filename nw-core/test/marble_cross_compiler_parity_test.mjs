import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { buildMarbleMazeMjcf } from "../shells/web/marble-maze-mujoco.js";
import { decodeMarbleBoard } from "../shells/web/marble-maze.js";

const testDirectory = path.dirname(fileURLToPath(import.meta.url));
const stage0Path = process.env.NWCORE_STAGE0_WASM_PATH ??
  path.resolve(testDirectory, "../build/verification/marble-stage0/nwcore.wasm");
const stage1Path = process.env.NWCORE_STAGE1_WASM_PATH ??
  path.resolve(testDirectory, "../build/nwcore.wasm");
const missing = [stage0Path, stage1Path].filter((filename) => !fs.existsSync(filename));
if (missing.length) {
  throw new Error("Marble cross-compiler parity artifacts are missing: " +
    missing.join(", ") + ". Build the isolated Stage0 artifact and latest Stage1 artifact, " +
    "or set NWCORE_STAGE0_WASM_PATH/NWCORE_STAGE1_WASM_PATH.");
}

const cases = [];
for (let rung = 1; rung <= 16; rung++) {
  for (const seed of [0, 1, 17, 314159, 1073741823]) cases.push([rung, seed]);
}

async function readBoards(filename) {
  const { exports, instance } = await instantiateElisa(fs.readFileSync(filename), { warn: false });
  const capacity = 65536;
  const pointer = Number(exports.nw_frame_alloc(BigInt(capacity)));
  return cases.map(([rung, seed]) => {
    const length = Number(exports.nw_marble_board_write(
      BigInt(pointer), BigInt(capacity), BigInt(rung), BigInt(seed)));
    assert.ok(length > 0, `${filename}: empty board for rung ${rung}, seed ${seed}`);
    const bytes = new Uint8Array(instance.exports.memory.buffer, pointer, length).slice();
    const board = decodeMarbleBoard(bytes);
    return { board, mjcf: buildMarbleMazeMjcf(board, board.starts.length) };
  });
}

const [stage0, stage1] = await Promise.all([
  readBoards(stage0Path),
  readBoards(stage1Path),
]);
assert.deepEqual(stage1, stage0,
  "latest Stage1 Marble board transport differs from the Stage0 oracle");
console.log(`PASS: Stage0/Stage1 Marble board+MJCF parity (${cases.length} cases; ` +
  "16 rungs × 5 seeds)");
