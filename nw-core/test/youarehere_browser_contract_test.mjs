import assert from "node:assert/strict";
import fs from "node:fs";
import { fileURLToPath } from "node:url";

const root = fileURLToPath(new URL("..", import.meta.url));
const source = fs.readFileSync(`${root}/shells/web/index.html`, "utf8");
const registry = fs.readFileSync(`${root}/shells/web/task-registry.js`, "utf8");
assert.match(source, /nw_api_v1_task_you_are_here/);
assert.match(source, /youAreHere:\s*exports\.nw_api_v1_task_you_are_here\(\)/);
assert.match(source, /function isYouAreHereTask\(\)/);
assert.match(source, /return isTaskId\("you_are_here"\)/);
assert.match(source, /youAreHereFrame\(dark\(\)\)/);
assert.match(registry, /"3D Maze"/);
console.log("youarehere_browser_contract_test: PASS (export, task identity, menu route, lifecycle, and render selection)");
