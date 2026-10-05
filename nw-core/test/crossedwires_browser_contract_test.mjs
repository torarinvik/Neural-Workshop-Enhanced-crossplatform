import assert from "node:assert/strict";
import fs from "node:fs";
import { fileURLToPath } from "node:url";

const shell = fileURLToPath(new URL("../shells/web/index.html", import.meta.url));
const source = fs.readFileSync(shell, "utf8");

assert.match(source, /nw_api_v1_task_crossed_wires/,
  "the shell must allocate Crossed Wires through common-v1");
assert.match(source, /nw_api_v1_task_crossed_wires.*nw_api_v1_task_monkey_ladder/s,
  "the startup export contract must require Crossed Wires");
assert.match(source, /crossedWires:\s*exports\.nw_api_v1_task_crossed_wires\(\)/,
  "the task table must expose the Crossed Wires stable ID");
assert.match(source, /function crossedWiresKeyIndex\(/,
  "the shell must preserve the source's four/eight-key physical mapping");
assert.match(source, /\[3n, 5n, 1n, 1n, 0n, 0n\]/,
  "the shell defaults must match WIRES_LEVEL=3 and source defaults");
assert.match(source, /function crossedWiresFrame\(/,
  "Crossed Wires must render through its source scene");
assert.match(source, /if \(isCrossedWiresTask\(\)\) \{[\s\S]*crossedWiresKeyIndex\(/,
  "Crossed Wires keyboard input must use source ports");
assert.match(source, /event\.key === "o" \|\| event\.key === "O"/,
  "the source O options shortcut must be consumed in the task route");
assert.match(source, /isCrossedWiresTask\(\)\) \{\s*bytes = crossedWiresFrame\(dark\(\)\)/,
  "the generic stateless frame must not render Crossed Wires");
assert.match(source, /if \(isCrossedWiresTask\(\)\) destroyCrossedWiresRun\(\)/,
  "leaving Crossed Wires must dispose its controller");

console.log("crossedwires_browser_contract_test: PASS (exports, source defaults, physical key mapping, render, cleanup)");
