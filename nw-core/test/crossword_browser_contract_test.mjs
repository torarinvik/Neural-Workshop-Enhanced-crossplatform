import assert from "node:assert/strict";
import fs from "node:fs";
import { fileURLToPath } from "node:url";

const source = fs.readFileSync(fileURLToPath(new URL("../shells/web/index.html", import.meta.url)), "utf8");
assert.match(source, /nw_api_v1_task_crossword/);
assert.match(source, /return isTaskId\("crossword"\)/);
assert.match(source, /function ensureCrosswordRun\(\)/);
assert.match(source, /function crosswordFrame\(black\)/);
assert.match(source, /apiDispatchText\(handle, event\.key\)/);
assert.match(source, /if \(isCrosswordTask\(\)\) destroyCrosswordRun\(\)/);
console.log("crossword_browser_contract_test: PASS (export, route, lifecycle, text input, render, cleanup)");
