import assert from "node:assert/strict";
import fs from "node:fs";
import { fileURLToPath } from "node:url";

const source = fs.readFileSync(fileURLToPath(new URL("../shells/web/index.html", import.meta.url)), "utf8");
assert.match(source, /nw_api_v1_task_scrabble/);
assert.match(source, /return isTaskId\("scrabble"\)/);
assert.match(source, /function ensureScrabbleRun\(\)/);
assert.match(source, /function scrabbleFrame\(black\)/);
assert.match(source, /scrabbleAction\(0\)/);
assert.match(source, /scrabbleAction\(1\)/);
assert.match(source, /if \(isScrabbleTask\(\)\) destroyScrabbleRun\(\)/);
console.log("scrabble_browser_contract_test: PASS (export, route, lifecycle, keyboard, render, cleanup)");
