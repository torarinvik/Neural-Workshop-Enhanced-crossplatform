import assert from "node:assert/strict";
import fs from "node:fs";
import { fileURLToPath } from "node:url";

const root = fileURLToPath(new URL("..", import.meta.url));
const source = fs.readFileSync(`${root}/shells/web/index.html`, "utf8");
const registry = fs.readFileSync(`${root}/shells/web/task-registry.js`, "utf8");

assert.match(source, /nw_api_v1_task_monkey_ladder/,
  "the shell must expose Monkey Ladder through common-v1");
assert.match(source, /monkeyLadder:\s*exports\.nw_api_v1_task_monkey_ladder\(\)/,
  "the task table must allocate Monkey Ladder through common-v1");
assert.match(registry, /"Monkey Ladder"/,
  "the reviewed browser registry must retain the Monkey Ladder menu entry");
assert.match(source, /function isMonkeyTask\(\)[\s\S]*return isTaskId\("monkey_ladder"\)/,
  "Monkey Ladder must be selected by its stable task identity");
assert.match(source, /function ensureMonkeyRun\(\)[\s\S]*BigInt\(monkeyOptions\.grid\)[\s\S]*BigInt\(monkeyOptions\.level\)[\s\S]*BigInt\(monkeyOptions\.showMs\)/,
  "the controller must receive the selected source options instead of fixed constants");
assert.match(source, /MONKEY_OPTIONS_STORAGE = "neural-workshop\.monkey-ladder\.options\.v1"/,
  "Monkey Ladder options must have a versioned persistence key");
assert.match(source, /function readMonkeyOptions\(\)[\s\S]*grid: 5, level: 3, adaptive: true, showMs: 700[\s\S]*perTileMs: 280, revealAnswer: true/,
  "Monkey Ladder browser defaults must match the source task options");
assert.match(source, /function openMonkeyOptions\(returnTo\)/,
  "the source C shortcut must open a real Monkey Ladder options screen");
assert.match(source, /function applyMonkeyOptions\(\)[\s\S]*localStorage\.setItem\(MONKEY_OPTIONS_STORAGE[\s\S]*apiDestroyRun\(monkeyRunHandle\)/,
  "applying options must persist values and replace a live controller");
assert.match(source, /function drawMonkeyOptionsScreen\(\)[\s\S]*Monkey Ladder options/,
  "Monkey Ladder options must render as an explicit screen");
assert.match(source, /if \(screen === "monkeyOptions"\)[\s\S]*cancelMonkeyOptions\(\)[\s\S]*applyMonkeyOptions\(\)[\s\S]*modifyMonkeyOption\(/,
  "Monkey Ladder options must support cancel, apply, and keyboard editing");
assert.match(source, /canvas\.addEventListener\("click",[\s\S]*if \(screen === "monkeyOptions"\)[\s\S]*monkeyOptionRowFromEvent\(/,
  "Monkey Ladder options must support selecting and toggling rows with the canvas");
assert.match(source, /function startMonkeyRound\([\s\S]*scheduleMonkeyAdvance\(handle\)/,
  "the live Monkey Ladder screen must schedule source-owned reveal deadlines");
assert.match(source, /function monkeyRunFrame\(black\)[\s\S]*nw_api_v1_render\(/,
  "Monkey Ladder must render through the common display-list ABI");
assert.match(source, /if \(screen === "monkey"\) apiDispatchPointer\(ensureMonkeyRun\(\), API_EVENT\.pointerMove/,
  "pointer movement must remain connected to the live controller");
assert.match(source, /if \(screen === "monkey" && next !== "monkey" && !openingMonkeyOptions\)/,
  "opening options must preserve the live Monkey Ladder run");
assert.match(source, /if \(screen === "monkey" && next !== "monkey" && !openingMonkeyOptions\)[\s\S]*apiDestroyRun\(monkeyRunHandle\)/,
  "leaving Monkey Ladder must dispose its controller");

console.log("monkey_ladder_browser_contract_test: PASS (menu route, options persistence, timing, pointer, render, disposal)");
