import assert from "node:assert/strict";
import fs from "node:fs";
import { fileURLToPath } from "node:url";

const source = fs.readFileSync(fileURLToPath(new URL("../shells/web/index.html", import.meta.url)), "utf8");
assert.match(source, /nw_api_v1_task_crossword/);
assert.match(source, /return isTaskId\("crossword"\)/);
assert.match(source, /function ensureCrosswordRun\(\)/);
assert.match(source, /function crosswordFrame\(black\)/);
assert.match(source, /apiDispatchText\(handle, event\.key\)/);
assert.match(source, /nw_api_v1_crossword_set_lexicon/);
assert.match(source, /crossword-index-import/);
assert.match(source, /crosswordIndexRequest\("readwrite", store => store\.put\(buffer, "lexicon"\)\)/);
assert.match(source, /const defaults = \{ level: 2, trials: 3, showMistakes: true, adaptive: true \}/);
assert.match(source, /openCrosswordOptions\("taskhub"\)/);
assert.match(source, /openCrosswordOptions\("task"\)/);
assert.match(source, /apiDispatchPointer\(ensureCrosswordRun\(\), API_EVENT\.pointerDown, event\)/);
const crosswordKeys = source.slice(source.indexOf('    if (isCrosswordTask()) {', source.indexOf('window.addEventListener("keydown"')),
  source.indexOf('    if (isSyllogismTask()) {', source.indexOf('window.addEventListener("keydown"')));
assert.match(crosswordKeys, /event\.key === "Tab"\)\s*\{\s*crosswordAction\(6\)/,
  "Tab must turn the active crossword direction");
assert.match(source, /if \(isCrosswordTask\(\)\) destroyCrosswordRun\(\)/);
console.log("crossword_browser_contract_test: PASS (export, route, lifecycle, text input, render, cleanup)");
