import assert from "node:assert/strict";
import fs from "node:fs";
import { fileURLToPath } from "node:url";

const source = fs.readFileSync(fileURLToPath(new URL("../shells/web/index.html", import.meta.url)), "utf8");
assert.match(source, /nw_api_v1_task_verbal/);
assert.match(source, /return isTaskId\("verbal_reasoning"\)/);
assert.match(source, /function ensureVerbalRun\(\)/);
assert.match(source, /function verbalFrame\(black\)/);
assert.match(source, /apiDispatchKey\(handle, API_KEY\.enter, event\)/);
assert.match(source, /if \(isVerbalTask\(\)\) destroyVerbalRun\(\)/);
console.log("verbal_browser_contract_test: PASS (export, route, lifecycle, keyboard, render, cleanup)");
