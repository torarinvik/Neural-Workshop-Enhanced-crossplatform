import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { buildMarbleMazeMjcf } from "../shells/web/marble-maze-mujoco.js";
import { decodeMarbleBoard } from "../shells/web/marble-maze.js";

const testDirectory = path.dirname(fileURLToPath(import.meta.url));
const repositoryRoot = path.resolve(testDirectory, "../..");
const referenceRoot = process.env.NW_REFERENCE_ROOT ??
  path.resolve(repositoryRoot, "../../Python Projects/neural-workshop-enhanced");
const python = process.env.NW_REFERENCE_PYTHON ??
  path.join(referenceRoot, ".venv/bin/python3");
if (!fs.existsSync(python)) {
  throw new Error(`Python reference interpreter not found: ${python}; set NW_REFERENCE_PYTHON`);
}

const seeds = [0, 1, 17, 314159, 1073741823];
const cases = [];
for (let rung = 1; rung <= 16; rung++) {
  for (const seed of seeds) cases.push([rung, seed]);
}

const pythonProgram = `
import json, sys
sys.path.insert(0, ${JSON.stringify(testDirectory)})
from marble_source_capture import float32_abi_tray
from neural_workshop import marblemaze as mm

def board_dict(t):
    return {
        "built": True,
        "rung": t.rung,
        "cols": t.cols,
        "rows": t.rows,
        "width": t.width,
        "depth": t.depth,
        "cell": t.cell,
        "thickness": t.thickness,
        "height": t.height,
        "home": {"x": t.home[0], "y": t.home[1], "radius": t.home[2]},
        "seconds": t.seconds,
        "route": t.route,
        "walls": [w._asdict() for w in t.walls],
        "holes": [h._asdict() for h in t.holes],
        "starts": [{"x": p[0], "y": p[1]} for p in t.starts],
    }

results = []
for rung, seed in json.load(sys.stdin):
    # The browser creates MJCF from the board after it has crossed the
    # Float32 WASM ABI. Compare against the source using that same transported
    # geometry instead of letting six-decimal MJCF formatting amplify a
    # sub-micrometre difference between Float64 and Float32 board coordinates.
    tray = float32_abi_tray(mm.deal(rung, seed=seed))
    results.append({"board": board_dict(tray), "mjcf": mm._mjcf(tray, len(tray.starts))})
print(json.dumps(results, allow_nan=False, separators=(",", ":")))
`;
const reference = spawnSync(python, ["-c", pythonProgram], {
  cwd: referenceRoot,
  input: JSON.stringify(cases),
  encoding: "utf8",
  maxBuffer: 16 * 1024 * 1024,
});
if (reference.status !== 0) {
  throw new Error(`Python Marble Maze reference failed:\n${reference.stderr}`);
}
const expected = JSON.parse(reference.stdout);

function f32Reference(value) {
  if (typeof value === "number") return Math.fround(value);
  if (Array.isArray(value)) return value.map(f32Reference);
  if (value && typeof value === "object") {
    return Object.fromEntries(Object.entries(value).map(([key, child]) =>
      [key, f32Reference(child)]));
  }
  return value;
}

const wasmPath = process.env.NWCORE_WASM_PATH ??
  path.resolve(testDirectory, "../build/nwcore.wasm");
const wasm = fs.readFileSync(wasmPath);
const { exports, instance } = await instantiateElisa(wasm, { warn: false });
const capacity = 65536;
const pointer = Number(exports.nw_frame_alloc(BigInt(capacity)));
let maximumWalls = 0;
let maximumHoles = 0;
let maximumMarbles = 0;

for (let index = 0; index < cases.length; index++) {
  const [rung, seed] = cases[index];
  const length = Number(exports.nw_marble_board_write(
    BigInt(pointer), BigInt(capacity), BigInt(rung), BigInt(seed)));
  assert.ok(length > 0, `WASM board generation failed for rung ${rung}, seed ${seed}`);
  const bytes = new Uint8Array(instance.exports.memory.buffer, pointer, length);
  const board = decodeMarbleBoard(bytes);
  assert.deepEqual(board, f32Reference(expected[index].board),
    `board fields/order differ for rung ${rung}, seed ${seed}`);
  assert.equal(buildMarbleMazeMjcf(board, board.starts.length), expected[index].mjcf,
    `MJCF differs for rung ${rung}, seed ${seed}`);
  maximumWalls = Math.max(maximumWalls, board.walls.length);
  maximumHoles = Math.max(maximumHoles, board.holes.length);
  maximumMarbles = Math.max(maximumMarbles, board.starts.length);
}

console.log(`PASS: Python/WASM Marble board+MJCF parity (${cases.length} cases; ` +
  `16 rungs × ${seeds.length} seeds; max ${maximumWalls} walls, ` +
  `${maximumHoles} holes, ${maximumMarbles} marbles)`);
