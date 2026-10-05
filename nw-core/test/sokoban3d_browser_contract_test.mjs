import assert from "node:assert/strict";
import fs from "node:fs";
import { fileURLToPath } from "node:url";

const root = fileURLToPath(new URL("..", import.meta.url));
const source = fs.readFileSync(`${root}/shells/web/index.html`, "utf8");
const registry = fs.readFileSync(`${root}/shells/web/task-registry.js`, "utf8");
assert.match(source, /nw_api_v1_task_sokoban_3d/);
assert.match(source, /sokoban3d:\s*exports\.nw_api_v1_task_sokoban_3d\(\)/);
assert.match(source, /function isSokoban3DTask\(\)/);
assert.match(source, /return isTaskId\("sokoban_3d"\)/);
assert.match(source, /isSokoban3DTask\(\) \? API_TASK\.sokoban3d : API_TASK\.sokoban/);
assert.match(registry, /"3D Sokoban"/);
console.log("sokoban3d_browser_contract_test: PASS (export, task identity, menu route, lifecycle selection)");
