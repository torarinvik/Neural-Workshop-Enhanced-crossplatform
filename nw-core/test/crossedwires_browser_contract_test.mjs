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
assert.match(source, /const defaults = \{ level: 3, trials: 5, adaptive: true, showGrid: true \}/,
  "the options defaults must match the source level, rounds, adaptive, and grid settings");
assert.match(source, /function crossedWiresFrame\(/,
  "Crossed Wires must render through its source scene");
assert.match(source, /if \(isCrossedWiresTask\(\)\) \{[\s\S]*crossedWiresKeyIndex\(/,
  "Crossed Wires keyboard input must use source ports");
assert.match(source, /CROSSED_WIRES_ACTION = Object\.freeze\([^\n]*applyOptions: 3/,
  "the options panel must apply settings through the controller");
assert.match(source, /neural-workshop\.crossed-wires\.options\.v1/,
  "settings must persist under a task-specific storage key");
assert.match(source, /function openCrossedWiresOptions\(/,
  "O and the four-key C shortcut must open the options panel");
assert.match(source, /crossedWiresAction\(CROSSED_WIRES_ACTION\.applyOptions,/,
  "applying options from a live task must reset the existing controller");
assert.match(source, /if \(event\.key === "Escape"\) cancelCrossedWiresOptions\(\)/,
  "Escape must discard an options draft");
assert.match(source, /CROSSED_WIRES_OPTIONS_STORAGE,\s*JSON\.stringify\(crossedWiresOptions\)/,
  "accepted options must be saved");
assert.match(source, /isCrossedWiresTask\(\)\) \{\s*bytes = crossedWiresFrame\(dark\(\)\)/,
  "the generic stateless frame must not render Crossed Wires");
assert.match(source, /if \(isCrossedWiresTask\(\)\) destroyCrossedWiresRun\(\)/,
  "leaving Crossed Wires must dispose its controller");

console.log("crossedwires_browser_contract_test: PASS (exports, source defaults, physical key mapping, render, cleanup)");
