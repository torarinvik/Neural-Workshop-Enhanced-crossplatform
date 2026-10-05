import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { decodeMarbleBoard, marbleOptionNoteLines } from "../shells/web/marble-maze.js";

const testDirectory = path.dirname(fileURLToPath(import.meta.url));
const repositoryRoot = path.resolve(testDirectory, "../..");
const referenceRoot = process.env.NW_REFERENCE_ROOT ??
  path.resolve(repositoryRoot, "../../Python Projects/neural-workshop-enhanced");
const python = process.env.NW_REFERENCE_PYTHON ??
  path.join(referenceRoot, ".venv/bin/python3");
if (!fs.existsSync(python)) {
  throw new Error(`Python reference interpreter not found: ${python}; set NW_REFERENCE_PYTHON`);
}

const pythonProgram = String.raw`
import json
import ast
from pathlib import Path
from typing import Any, Dict
from neural_workshop.marblemaze import GRADES as _MARBLE_GRADES

source = Path('neural_workshop/ui/taskoptions.py').read_text()
tree = ast.parse(source)
function = next(node for node in tree.body
                if isinstance(node, ast.FunctionDef)
                and node.name == 'marble_maze_note')
namespace = {'_MARBLE_GRADES': _MARBLE_GRADES, '_': lambda value: value,
             'Any': Any, 'Dict': Dict}
exec(compile(ast.Module(body=[function], type_ignores=[]),
             'taskoptions.py:marble_maze_note', 'exec'), namespace)
marble_maze_note = namespace['marble_maze_note']

print(json.dumps([
    marble_maze_note({"MARBLE_MAZE_LEVEL": rung})
    for rung in range(1, 17)
], ensure_ascii=False, separators=(",", ":")))
`;
const reference = spawnSync(python, ["-c", pythonProgram], {
  cwd: referenceRoot,
  encoding: "utf8",
  maxBuffer: 128 * 1024,
});
if (reference.status !== 0) {
  throw new Error(`Python Marble Maze options reference failed:\n${reference.stderr}`);
}
const expected = JSON.parse(reference.stdout);

const wasmPath = process.env.NWCORE_WASM_PATH ??
  path.resolve(testDirectory, "../build/nwcore.wasm");
const wasm = fs.readFileSync(wasmPath);
const { exports, instance } = await instantiateElisa(wasm, { warn: false });
const capacity = 65536;
const pointer = Number(exports.nw_frame_alloc(BigInt(capacity)));
for (let rung = 1; rung <= 16; rung++) {
  const length = Number(exports.nw_marble_board_write(
    BigInt(pointer), BigInt(capacity), BigInt(rung), 1n));
  assert.ok(length > 0, `WASM failed to build Marble Maze level ${rung}`);
  const expectedBoard = decodeMarbleBoard(new Uint8Array(
    instance.exports.memory.buffer, pointer, length));
  assert.equal(marbleOptionNoteLines(rung, expectedBoard).join(" "), expected[rung - 1],
    `browser Marble Maze options note differs at level ${rung}`);
}

console.log("PASS: Marble Maze browser options notes match the original source (16 levels)");
