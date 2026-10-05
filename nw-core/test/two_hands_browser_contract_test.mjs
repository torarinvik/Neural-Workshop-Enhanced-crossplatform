import assert from "node:assert/strict";
import fs from "node:fs";
import { fileURLToPath } from "node:url";

const shell = fileURLToPath(new URL("../shells/web/index.html", import.meta.url));
const source = fs.readFileSync(shell, "utf8");

assert.match(source, /nw_api_v1_task_two_hands/,
  "the shell must require and expose the Two Hands task id");
assert.match(source, /nw_api_v1_two_hands_info/,
  "the shell must require the additive Two Hands info accessor");
assert.match(source, /nw_api_v1_two_hands_value/,
  "the shell must require the additive Two Hands value accessor");
assert.match(source, /twoHands:\s*exports\.nw_api_v1_task_two_hands\(\)/,
  "the task table must allocate Two Hands through common-v1");
assert.match(source, /function isTwoHandsTask\(\)/,
  "Two Hands must have an explicit catalog predicate");
assert.match(source, /function ensureTwoHandsRun\(\)/,
  "Two Hands must own a persistent browser-side run handle");
assert.match(source, /function scheduleTwoHandsAdvance\(/,
  "Two Hands setting and beat deadlines must use the browser monotonic clock");
assert.match(source, /function twoHandsFrame\(/,
  "Two Hands must render through the common display-list ABI");
assert.match(source, /if \(screen === "task" && isTwoHandsTask\(\)\) \{[\s\S]*apiDispatchPointer\(ensureTwoHandsRun\(\), API_EVENT\.pointerDown/,
  "the browser pointer-down path must reach Two Hands aim/fire");
assert.match(source, /if \(isTwoHandsTask\(\)\) \{[\s\S]*apiKeyFromEvent\(event, true\)/,
  "the browser keyboard path must forward Two Hands aliases");
assert.match(source, /if \(isTwoHandsTask\(\)\) destroyTwoHandsRun\(\)/,
  "leaving Two Hands must dispose the controller");
assert.match(source, /twoHandsInfo, twoHandsValue, twoHandsAction, twoHandsFrame/,
  "Two Hands diagnostics must remain available to focused browser smoke tests");
assert.match(source, /twoHandsAction\(TWO_HANDS_ACTION\.start\);[\s\S]*scheduleTwoHandsAdvance\(\)/,
  "Space/Enter must start and schedule a source-backed Two Hands run");
assert.match(source, /isPursuitTask\(\) \|\| isTwoHandsTask\(\) \|\| isOverrunTask\(\)/,
  "pointer-generated canvas clicks must not fall through to generic task state");

console.log("two_hands_browser_contract_test: PASS (exports, lifecycle, scheduling, keyboard, pointer, render, cleanup)");
