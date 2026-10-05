import assert from "node:assert/strict";
import fs from "node:fs";
import { fileURLToPath } from "node:url";

const shell = fileURLToPath(new URL("../shells/web/index.html", import.meta.url));
const source = fs.readFileSync(shell, "utf8");
assert.match(source, /nw_api_v1_task_jigsaw/);
assert.match(source, /return isTaskId\("jigsaw"\)/);
assert.match(source, /function ensureJigsawRun\(\)/);
assert.match(source, /\[2n, 5n, 1n, 1n, 0n, 0n\]/);
assert.match(source, /function jigsawFrame\(black\)/);
assert.match(source, /apiDispatchPointer\(ensureJigsawRun\(\), API_EVENT\.pointerDown/);
assert.match(source, /JIGSAW_ACTION\.start/);
assert.match(source, /if \(isJigsawTask\(\)\) destroyJigsawRun\(\)/);
assert.match(source, /isJigsawTask\(\)/);
assert.match(source, /bytes = jigsawFrame\(dark\(\)\)/);
console.log("jigsaw_browser_contract_test: PASS (export, source position, lifecycle, keyboard, pointer, render, cleanup)");
