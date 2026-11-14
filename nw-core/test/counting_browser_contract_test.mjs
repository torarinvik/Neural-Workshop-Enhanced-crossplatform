import assert from "node:assert/strict";
import fs from "node:fs";
import { fileURLToPath } from "node:url";

const shell = fileURLToPath(new URL("../shells/web/index.html", import.meta.url));
const source = fs.readFileSync(shell, "utf8");

assert.match(source, /COUNT_OPTIONS_STORAGE = "neural-workshop\.count\.options\.v1"/,
  "Count settings must have a versioned persistent key");
assert.match(source, /COUNT_KIND_OPTIONS = Object\.freeze\(\[0, 1, 2, 3, 4\]\)/,
  "shape choices must match the source options");
assert.match(source, /COUNT_START_OPTIONS = Object\.freeze\(\[2, 4, 6, 8, 10, 12, 16, 20, 25, 30, 40, 50, 60\]\)/,
  "starting counts must match the source options");
assert.match(source, /COUNT_TRIAL_OPTIONS = Object\.freeze\(\[5, 10, 15, 20, 30, 50, 80, 100\]\)/,
  "trial counts must match the source options");
assert.match(source, /COUNT_EXPOSURE_OPTIONS = Object\.freeze\(\[0, 200, 350, 500, 750, 1000, 2000, 4000\]\)/,
  "exposure times must match the source options");
assert.match(source, /function readCountOptions\(\)[\s\S]*COUNT_KIND_OPTIONS\.includes\(saved\.kind\)[\s\S]*COUNT_EXPOSURE_OPTIONS\.includes\(saved\.exposureMs\)/,
  "persisted Count choices must be validated against supported values");
assert.match(source, /function openCountOptions\(returnTo\)[\s\S]*function applyCountOptions\(\)[\s\S]*function cancelCountOptions\(\)/,
  "Count options must support edit, apply, and cancel");
assert.match(source, /function countOptionRows\(\)[\s\S]*Shapes to count[\s\S]*Show the true count after each trial/,
  "the options screen must expose all six Count settings");
assert.match(source, /event\.key\.toLowerCase\(\) === "c" && isCountTask\(\)\) openCountOptions\("taskhub"\)/,
  "the real task menu must expose Count options");
assert.match(source, /if \(phase === COUNT_PHASE\.ready \|\| phase === COUNT_PHASE\.done\) \{\s*openCountOptions\("task"\)/,
  "the task screen must expose options only while READY or DONE");
assert.match(source, /\[BigInt\(countOptions\.kind\), BigInt\(countOptions\.startCount\),[\s\S]*countOptions\.showAnswer \? 1n : 0n\]/,
  "accepted settings must initialize a fresh source controller");
assert.match(source, /phase === COUNT_PHASE\.showing && countOptions\.exposureMs > 0/,
  "timed exposure must schedule from the selected setting");
assert.match(source, /function countFrame\(black\)[\s\S]*BigInt\(REFERENCE_WIDTH\),\s*BigInt\(REFERENCE_HEIGHT\)/,
  "Count display lists must use reference dimensions before browser scaling");
assert.match(source, /if \(isCountTask\(\)\) destroyCountRun\(\)/,
  "leaving Count must dispose its controller and timer");
assert.match(source, /countInfo, countAction, countFrame, countState/,
  "focused browser replay hooks must expose Count diagnostics");

console.log("counting_browser_contract_test: PASS (options, persistence, routing, source timing, lifecycle)");
