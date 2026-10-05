import assert from "node:assert/strict";
import fs from "node:fs";
import { fileURLToPath } from "node:url";

const source = fs.readFileSync(fileURLToPath(new URL("../shells/web/index.html", import.meta.url)), "utf8");
assert.match(source, /nw_api_v1_task_chess/);
assert.match(source, /return isTaskId\("chess"\)/);
assert.match(source, /function ensureChessRun\(\)/);
assert.match(source, /function chessFrame\(black\)/);
assert.match(source, /apiDispatchKey\(handle, API_KEY\.enter, event\)/);
assert.match(source, /if \(isChessTask\(\)\) destroyChessRun\(\)/);
console.log("chess_browser_contract_test: PASS (export, route, lifecycle, keyboard, render, cleanup)");
