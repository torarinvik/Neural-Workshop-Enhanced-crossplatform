import assert from "node:assert/strict";
import fs from "node:fs";
import { fileURLToPath } from "node:url";

const root = fileURLToPath(new URL("..", import.meta.url));
const source = fs.readFileSync(`${root}/shells/web/index.html`, "utf8");
const registry = fs.readFileSync(`${root}/shells/web/task-registry.js`, "utf8");

// The browser contract is deliberately source-facing: the WASM smoke owns
// controller state and display-list decoding, while this test protects the
// glue that can otherwise make a working controller appear inert in a real
// browser.
assert.match(source, /<canvas id="screen"[^>]*tabindex="0"/,
  "the shared task canvas must be keyboard-focusable");
assert.match(source, /nw_api_v1_task_sokoban\b/,
  "the shell must expose the 2D Sokoban task export");
assert.match(source, /sokoban:\s*exports\.nw_api_v1_task_sokoban\(\)/,
  "the task table must allocate Sokoban through common-v1");
assert.match(registry, /"Sokoban"/,
  "the reviewed browser registry must retain the Sokoban menu entry");
assert.match(source, /function isSokobanTask\(\)[\s\S]*return isTaskId\("sokoban"\)/,
  "Sokoban must be selected by its stable task identity");
assert.match(source, /function ensureSokobanRun\(\)[\s\S]*apiCreateRun\(isSokoban3DTask\(\) \? API_TASK\.sokoban3d : API_TASK\.sokoban/,
  "the 2D route must create the real persistent Sokoban controller");
assert.match(source, /function sokobanFrame\(black\)[\s\S]*nw_api_v1_render\(/,
  "Sokoban must render through the common display-list ABI");
assert.match(source, /SOKOBAN_OPTIONS_STORAGE = "neural-workshop\.sokoban\.options\.v1"/,
  "Sokoban options must have a versioned persistence key");
assert.match(source, /function readSokobanOptions\(\)[\s\S]*rung: 2, trials: 5, adaptive: true, showTraps: false/,
  "Sokoban browser defaults must match the source task options");
assert.match(source, /function openSokobanOptions\(returnTo\)/,
  "the source C shortcut must open a real Sokoban options screen");
assert.match(source, /event\.key\.toLowerCase\(\) === "c" && isSokobanTask\(\) && !isSokoban3DTask\(\)/,
  "the 2D options screen must not be applied to 3D Sokoban");
assert.match(source, /function applySokobanOptions\(\)[\s\S]*localStorage\.setItem\(SOKOBAN_OPTIONS_STORAGE/,
  "applying options must persist the selected values");
assert.match(source, /if \(returnTo === "task" && sokobanRunHandle !== 0n\)[\s\S]*apiDestroyRun\(sokobanRunHandle\)[\s\S]*ensureSokobanRun\(\)/,
  "applying live options must recreate the controller with the new configuration");
assert.match(source, /function drawSokobanOptionsScreen\(\)[\s\S]*Sokoban options/,
  "Sokoban options must render as an explicit screen rather than a no-op shortcut");
assert.match(source, /if \(screen === "sokobanOptions"\)[\s\S]*cancelSokobanOptions\(\)[\s\S]*applySokobanOptions\(\)[\s\S]*modifySokobanOption\(/,
  "Sokoban options must support cancel, apply, and keyboard editing");
assert.match(source, /canvas\.addEventListener\("click",[\s\S]*if \(screen === "sokobanOptions"\)[\s\S]*sokobanOptionRowFromEvent\(/,
  "Sokoban options must support selecting and toggling rows with the canvas");
assert.match(source, /const openingSokobanOptions = screen === "task" && isSokobanTask\(\)[\s\S]*next === "sokobanOptions"/,
  "opening options must preserve the live run until apply or cancel");
assert.match(source, /if \(isSokobanTask\(\)\) \{[\s\S]*bytes = sokobanFrame\(dark\(\)\)/,
  "the task screen must use the live Sokoban frame rather than a generic placeholder");
assert.match(source, /if \(screen === "task"\) \{[\s\S]*if \(isSokobanTask\(\)\) \{[\s\S]*apiKeyFromEvent\(event, true\)[\s\S]*apiDispatchKey\(ensureSokobanRun\(\), key, event\)/,
  "focused keyboard input must reach the controller-owned action path");
assert.match(source, /else if \(screen === "task" && isSokobanTask\(\)\) \{[\s\S]*apiDispatchKeyUp\(ensureSokobanRun\(\), event\)/,
  "keyup events must be forwarded so held directional input cannot leak");
assert.match(source, /else if \(screen === "task" && isSokobanTask\(\)\) \{[\s\S]*API_EVENT\.focus, 0[\s\S]*\}/,
  "blur must dispatch the source lifecycle event");
assert.match(source, /else if \(screen === "task" && isSokobanTask\(\)\) \{[\s\S]*API_EVENT\.focus, 1[\s\S]*\}/,
  "focus must dispatch the source lifecycle event");
assert.match(source, /else if \(screen === "task" && isSokobanTask\(\)\) \{[\s\S]*API_EVENT\.visibility, document\.hidden \? 0 : 1[\s\S]*\}/,
  "visibility changes must reach the controller lifecycle boundary");
assert.match(source, /if \(isSokobanTask\(\)\) \{\s*apiDestroyRun\(sokobanRunHandle\);\s*sokobanRunHandle = 0n;/,
  "leaving Sokoban must dispose the persistent run handle");

console.log("sokoban_browser_contract_test: PASS (menu route, focus, keyboard, keyup, lifecycle, render, disposal)");
