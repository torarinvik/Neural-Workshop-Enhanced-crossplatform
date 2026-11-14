import assert from "node:assert/strict";
import fs from "node:fs";
import { fileURLToPath } from "node:url";

const shell = fileURLToPath(new URL("../shells/web/index.html", import.meta.url));
const source = fs.readFileSync(shell, "utf8");
const protocolPath = fileURLToPath(new URL("../src/wasm/runtime_protocol.elisa", import.meta.url));
const protocol = fs.readFileSync(protocolPath, "utf8");

assert.match(source, /nw_api_v1_task_mr_time/,
  "the shell must require and expose the Mr. Time task id");
assert.match(source, /nw_api_v1_mr_time_info/,
  "the shell must require the additive Mr. Time info accessor");
assert.match(source, /mrTime:\s*exports\.nw_api_v1_task_mr_time\(\)/,
  "the task table must allocate Mr. Time through common-v1");
assert.match(source, /function isMrTimeTask\(\)/,
  "Mr. Time must have an explicit catalog predicate");
assert.match(source, /function ensureMrTimeRun\(\)/,
  "Mr. Time must own a persistent browser-side run handle");
assert.match(source, /MR_TIME_OPTIONS_STORAGE = "neural-workshop\.mr-time\.options\.v1"/,
  "Mr. Time settings must have a versioned persistent key");
assert.match(source, /function readMrTimeOptions\(\)[\s\S]*MR_TIME_GAP_OPTIONS\.includes\(saved\.maxGapMs\)[\s\S]*MR_TIME_FLASH_OPTIONS\.includes\(saved\.flashMs\)/,
  "saved Mr. Time settings must be validated against source-supported choices");
assert.match(source, /function openMrTimeOptions\(returnTo\)[\s\S]*function applyMrTimeOptions\(\)[\s\S]*function cancelMrTimeOptions\(\)/,
  "Mr. Time must expose editable, applicable, cancellable browser options");
assert.match(source, /function mrTimeOptionRows\(\)[\s\S]*Which half to play[\s\S]*Adapt precision to performance/,
  "the browser options screen must expose all six source settings");
assert.match(source, /event\.key\.toLowerCase\(\) === "c" && isMrTimeTask\(\)\) openMrTimeOptions\("taskhub"\)/,
  "the real task menu must expose Mr. Time options");
assert.match(source, /if \(phase === MR_TIME_PHASE\.ready \|\| phase === MR_TIME_PHASE\.done\) \{\s*openMrTimeOptions\("task"\)/,
  "the task screen must expose options only at source-supported phases");
assert.match(source, /function scheduleMrTimeAdvance\(/,
  "Mr. Time deadlines must be driven by the browser monotonic clock");
assert.match(source, /MR_TIME_INFO\.appearedAtMs\)[\s\S]*MR_TIME_INFO\.flashMs/,
  "the flash deadline must be scheduled from source-owned timestamps");
assert.match(source, /MR_TIME_INFO\.askAtMs/,
  "the hidden recall gap must be scheduled from the source ask deadline");
assert.match(source, /MR_TIME_INFO\.feedbackUntilMs/,
  "feedback expiry must be scheduled from the source controller");
assert.match(source, /function mrTimeFrame\(/,
  "Mr. Time must render through the common display-list ABI");
assert.match(source, /function taskClick\(event\)[\s\S]*isMrTimeTask\(\)[\s\S]*API_EVENT\.pointerDown/,
  "the browser click path must dispatch Mr. Time shape clicks");
assert.match(source, /if \(isMrTimeTask\(\)\) \{[\s\S]*apiDispatchText\(handle, event\.key\)/,
  "the browser keyboard path must forward Mr. Time digit text");
assert.match(source, /const flags = event\?\.repeat \? 1 : 0;[\s\S]*API_EVENT\.keyDown/,
  "physical key dispatch must preserve the browser repeat bit");
assert.match(source, /else if \(event\.key === " " \|\| event\.key === "Enter"\) \{\s*apiDispatchKey\(handle, event\.key === " " \? API_KEY\.space : API_KEY\.enter, event\);/,
  "Mr. Time Space and Enter must use common physical-key dispatch");
assert.match(protocol, /elif kind == EVENT_KEY_DOWN:\s*return IGNORED if \(flags & 1\) != 0\s*phase: i64 = task_info\(index, 0\)/,
  "the common protocol must suppress OS-repeat keydown actions such as Enter");
assert.match(source, /if \(isMrTimeTask\(\)\) \{[\s\S]*apiDispatchText\(handle, event\.key\)[\s\S]*mrTimeAction\(MR_TIME_ACTION\.backspace\)/,
  "Mr. Time digit and Backspace paths must preserve source-accepted key repeats");
assert.match(source, /event\.key === "\." \|\| event\.key === ","/,
  "the browser keyboard path must forward decimal-point input");
assert.match(source, /mrTimeAction\(MR_TIME_ACTION\.backspace\)/,
  "Backspace/Delete must reach the controller-owned answer buffer");
assert.match(source, /mrTimeInfo, mrTimeAction, mrTimeFrame, mrTimeState/,
  "Mr. Time diagnostics must remain available to focused browser smoke tests");
assert.match(source, /if \(isMrTimeTask\(\)\) destroyMrTimeRun\(\)/,
  "leaving the task must dispose the controller and timer");

// The common state envelope intentionally omits mode/start-rung. The browser
// accessor must map the twelve envelope fields instead of indexing the
// additive info enum directly (which would shift trial/correct/deadline data).
assert.match(source, /\[MR_TIME_INFO\.rung\]: 1,[\s\S]*\[MR_TIME_INFO\.trial\]: 2,[\s\S]*\[MR_TIME_INFO\.adaptive\]: 11/,
  "the browser must translate Mr. Time's custom state field order");

console.log("mrtime_browser_contract_test: PASS (exports, lifecycle, scheduling, input, pointer, render, cleanup, state mapping)");
