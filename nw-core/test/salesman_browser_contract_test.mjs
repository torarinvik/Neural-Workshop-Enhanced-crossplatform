import assert from "node:assert/strict";
import fs from "node:fs";
import { fileURLToPath } from "node:url";

const shell = fileURLToPath(new URL("../shells/web/index.html", import.meta.url));
const source = fs.readFileSync(shell, "utf8");

assert.match(source, /nw_api_v1_task_salesman/,
  "the shell must require and expose the Traveling Salesman task id");
assert.match(source, /nw_api_v1_salesman_info/,
  "the shell must require the additive Salesman info accessor");
assert.match(source, /nw_api_v1_salesman_value/,
  "the shell must require the additive Salesman value accessor");
assert.match(source, /salesman:\s*exports\.nw_api_v1_task_salesman\(\)/,
  "the task table must allocate Salesman through common-v1");
assert.match(source, /function isSalesmanTask\(\)/,
  "Salesman must have an explicit catalog predicate");
assert.match(source, /function ensureSalesmanRun\(\)/,
  "Salesman must own a persistent browser-side run handle");
assert.match(source, /function scheduleSalesmanAdvance\(/,
  "Salesman feedback deadlines must be driven by the browser monotonic clock");
assert.match(source, /function salesmanFrame\(/,
  "Salesman must render through the common display-list ABI");
assert.match(source, /screen === "task" && isSalesmanTask\(\)[\s\S]*apiDispatchPointer\(ensureSalesmanRun\(\), API_EVENT\.pointerDown/,
  "browser pointer-down must reach source-owned city hit testing");
assert.match(source, /if \(isSalesmanTask\(\)\) \{[\s\S]*event\.key === " " \|\| event\.key === "Enter"/,
  "Space and Enter must reach the Salesman start path");
assert.match(source, /if \(isSalesmanTask\(\)\) destroySalesmanRun\(\)/,
  "leaving Salesman must dispose the controller and timer");
assert.match(source, /salesmanInfo, salesmanValue, salesmanAction, salesmanFrame/,
  "Salesman diagnostics must remain available to focused browser smoke tests");
assert.match(source, /else if \(isSalesmanTask\(\)\) \{[\s\S]*bytes = salesmanFrame\(dark\(\)\)/,
  "the generic stateless task frame must not be the Salesman render path");

console.log("salesman_browser_contract_test: PASS (exports, lifecycle, scheduling, input, pointer, render, cleanup)");
