// Complete Freeform Tetris run through the same common key-event ABI used by
// the browser shell.  This is deliberately a controller-level test: it finds
// a legal hard-drop column by ordinary left/right events and never writes the
// score, piece count, or terminal phase directly.
import assert from "node:assert/strict";
import fs from "node:fs";
import { fileURLToPath } from "node:url";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";

const wasmPath = process.env.NWCORE_WASM_PATH ??
  fileURLToPath(new URL("../build/nwcore.wasm", import.meta.url));
const { exports, instance } = await instantiateElisa(
  fs.readFileSync(wasmPath), { warn: false });

const task = BigInt(exports.nw_api_v1_tetris_task_id());
const accepted = 1n;
const EVENT_KEY_DOWN = 2n;
const KEY = Object.freeze({ space: 1n, right: 5n, down: 6n });
const STATE_BYTES = 112n;
const statePointer = exports.nw_frame_alloc(STATE_BYTES);
assert.ok(statePointer > 0n);

function state(handle) {
  const length = exports.nw_api_v1_read_state(
    handle, statePointer, STATE_BYTES);
  assert.equal(length, STATE_BYTES);
  const view = new DataView(
    instance.exports.memory.buffer, Number(statePointer), Number(length));
  return Array.from({ length: 12 }, (_, index) =>
    view.getBigInt64(16 + index * 8, true));
}

let timestamp = 1000n;
let sequence = 0n;
function key(handle, code) {
  sequence += 1n;
  timestamp += 1n;
  return exports.nw_api_v1_dispatch(
    handle, EVENT_KEY_DOWN, timestamp, sequence, code, 0n,
    0n, 0n, 0n, 0n, 0n);
}

const handle = exports.nw_api_v1_create(
  task, 1n, 1n, 25n, 5n, 0n, 0n, 0n, 0x54455452n);
assert.ok(handle > 0n);
try {
  assert.equal(key(handle, KEY.space), accepted, "Space starts Tetris");
  let previousPiece = state(handle)[2];
  let successfulDrops = 0;
  for (let piece = 0; piece < 25; piece += 1) {
    let placed = false;
    // The board is 72 columns wide.  Return to the left edge after each
    // successful drop because the controller resets the selection column.
    for (let column = 0; column < 72 && !placed; column += 1) {
      assert.equal(key(handle, KEY.down), accepted);
      const current = state(handle);
      if (current[2] !== previousPiece) {
        previousPiece = current[2];
        successfulDrops += 1;
        placed = true;
      } else if (column < 71) {
        assert.equal(key(handle, KEY.right), accepted);
      }
    }
    assert.equal(placed, true, `piece ${piece + 1} found no legal drop`);
  }
  const finalState = state(handle);
  assert.equal(finalState[2], 25n, "all target pieces were placed");
  assert.equal(finalState[0], 2n, "complete run reaches DONE");
  assert.equal(successfulDrops, 25);
} finally {
  assert.equal(exports.nw_api_v1_destroy(handle), 0n);
}

console.log("PASS: complete Freeform Tetris run through common key input");
