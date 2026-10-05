import assert from "node:assert/strict";
import fs from "node:fs";
import { fileURLToPath } from "node:url";

const source = fs.readFileSync(fileURLToPath(new URL("../shells/web/index.html", import.meta.url)), "utf8");
assert.match(source, /nw_api_v1_task_syllogism/);
assert.match(source, /return isTaskId\("syllogism"\)/);
assert.match(source, /function ensureSyllogismRun\(\)/);
assert.match(source, /function syllogismFrame\(black\)/);
assert.match(source, /apiDispatchKey\(handle, API_KEY\.space, event\)/);
assert.match(source, /if \(isSyllogismTask\(\)\) destroySyllogismRun\(\)/);
console.log("syllogism_browser_contract_test: PASS (export, route, lifecycle, keyboard, render, cleanup)");
