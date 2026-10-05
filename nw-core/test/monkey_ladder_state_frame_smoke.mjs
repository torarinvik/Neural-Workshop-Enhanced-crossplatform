// The adaptive level shown after a round must not replace the sequence that
// was actually played. Check the v2 frame ABI on the real stage0/stage1 WASM
// artifacts, including concealment during recall.
import assert from "node:assert/strict";
import fs from "node:fs";
import { fileURLToPath } from "node:url";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { decode, Kind } from "../shells/web/display-list.js";

const wasm = process.env.NWCORE_WASM_PATH ??
  fileURLToPath(new URL("../build/nwcore.wasm", import.meta.url));
const { exports, instance } = await instantiateElisa(fs.readFileSync(wasm), { warn: false });
const CAPACITY = 65536;
const ptr = Number(exports.nw_frame_alloc(BigInt(CAPACITY)));
assert.ok(ptr > 0, "frame allocation succeeds");

function render({ phase, sequenceLevel, displayLevel, adaptive, clickedUpto,
  wrong, seed = 1, revealAnswer = 1 }) {
  const length = Number(exports.nw_monkey_ladder_write_state(
    BigInt(ptr), BigInt(CAPACITY), BigInt(phase), BigInt(sequenceLevel),
    BigInt(displayLevel), BigInt(adaptive), BigInt(clickedUpto), BigInt(wrong),
    0n, 0n, BigInt(revealAnswer), BigInt(seed), 912n, 684n));
  assert.ok(length > 0, "Monkey Ladder state frame is encoded");
  return decode(new Uint8Array(instance.exports.memory.buffer, ptr, length).slice());
}

const numberLabels = (commands) => commands
  .filter((command) => command.kind === Kind.TEXT && /^[0-9]+$/.test(command.text))
  .map((command) => command.text);
const expected = [0, 1, 2].map((index) => Number(
  exports.nw_monkey_ladder_expected(1n, 3n, BigInt(index))));
assert.equal(new Set(expected).size, 3, "dealt sequence contains distinct cells");

const result = render({ phase: 3, sequenceLevel: 3, displayLevel: 4,
  adaptive: 1, clickedUpto: 3, wrong: -1 });
const resultText = result.filter((command) => command.kind === Kind.TEXT)
  .map((command) => command.text);
assert.ok(resultText.some((text) => text.includes("Length 4") &&
  text.includes("Correct") && text.includes("next length 4")),
"result status reports the adaptive next length");
assert.deepEqual(numberLabels(result).sort(), ["1", "2", "3"],
  "result reveals only the three cells dealt for this round, not the next level's new deal");

const miss = render({ phase: 3, sequenceLevel: 3, displayLevel: 2,
  adaptive: 1, clickedUpto: 1, wrong: 24 });
const missText = miss.filter((command) => command.kind === Kind.TEXT)
  .map((command) => command.text);
assert.ok(missText.some((text) => text.includes("Length 2") &&
  text.includes("Miss") && text.includes("back to length 2")),
"miss status reports the adaptive lower level");
assert.deepEqual(numberLabels(miss).sort(), ["1", "2", "3"],
  "miss feedback still reveals the original round's sequence");

const concealed = render({ phase: 2, sequenceLevel: 3, displayLevel: 3,
  adaptive: 1, clickedUpto: 0, wrong: -1, revealAnswer: 1 });
assert.deepEqual(numberLabels(concealed), [],
  "the answer remains concealed during the input phase");

console.log("PASS: Monkey Ladder keeps dealt answer through adaptive result and conceals it during recall");
