import assert from "node:assert/strict";
import fs from "node:fs";
import { fileURLToPath } from "node:url";

const shell = fileURLToPath(new URL("../shells/web/index.html", import.meta.url));
const source = fs.readFileSync(shell, "utf8");

assert.match(source, /nw_api_v1_task_graph_mapping/,
  "the shell must require and expose the Graph Mapping task id");
assert.match(source, /nw_api_v1_graph_mapping_info/,
  "the shell must require the additive Graph Mapping info accessor");
assert.match(source, /nw_api_v1_graph_mapping_value/,
  "the shell must require the additive Graph Mapping value accessor");
assert.match(source, /graphMapping:\s*exports\.nw_api_v1_task_graph_mapping\(\)/,
  "the task table must allocate Graph Mapping through common-v1");
assert.match(source, /function isGraphMappingTask\(\)/,
  "Graph Mapping must have an explicit catalog predicate");
assert.match(source, /function ensureGraphMappingRun\(\)/,
  "Graph Mapping must own a persistent browser-side run handle");
assert.match(source, /GRAPH_MAPPING_NODE_OPTIONS = Object\.freeze\(\[4, 5, 6, 7, 8, 9, 10, 12, 14, 16\]\)/,
  "Graph Mapping must expose the source node-size options");
assert.match(source, /GRAPH_MAPPING_DENSITY_OPTIONS = Object\.freeze\(\[0, 1, 2\]\)/,
  "Graph Mapping must expose sparse, medium, and dense source options");
assert.match(source, /GRAPH_MAPPING_OPTIONS_STORAGE = "neural-workshop\.graph-mapping\.options\.v1"/,
  "Graph Mapping options must use a versioned persistence key");
assert.match(source, /function readGraphMappingOptions\(\)/,
  "Graph Mapping options must be validated and restored from storage");
assert.match(source, /function openGraphMappingOptions\(returnTo\)/,
  "Graph Mapping must have a real options route");
assert.match(source, /function drawGraphMappingOptionsScreen\(\)/,
  "Graph Mapping options must render an explicit six-row screen");
assert.match(source, /Feedback is always on[\s\S]*graphMappingOptionsSelection/,
  "the omitted seventh feedback setting must remain explicit rather than silently invented");
assert.match(source, /if \(event\.key\.toLowerCase\(\) === "c" && isGraphMappingTask\(\)\) openGraphMappingOptions\("taskhub"\)/,
  "task-hub C must open Graph Mapping options");
assert.match(source, /if \(event\.key\.toLowerCase\(\) === "c"\) \{\s*const phase = graphMappingInfo\(GRAPH_MAPPING_INFO\.phase\);\s*if \(phase === GRAPH_MAPPING_PHASE\.ready \|\| phase === GRAPH_MAPPING_PHASE\.done\) \{\s*openGraphMappingOptions\("task"\);/,
  "task-screen C must open Graph Mapping options only between runs");
assert.match(source, /if \(screen === "graphMappingOptions"\)[\s\S]*applyGraphMappingOptions\(\)[\s\S]*modifyGraphMappingOption\(1\)/,
  "Graph Mapping options must support keyboard apply and editing");
assert.match(source, /if \(screen === "graphMappingOptions"\) \{[\s\S]*graphMappingOptionRowFromEvent\(event\)/,
  "Graph Mapping options must support pointer row selection and editing");
assert.match(source, /const openingGraphMappingOptions = screen === "task" && isGraphMappingTask\(\)[\s\S]*next === "graphMappingOptions"/,
  "opening Graph Mapping options must preserve the live controller until apply/cancel decides its lifecycle");
assert.match(source, /function scheduleGraphMappingAdvance\(/,
  "Graph Mapping exposure and feedback deadlines must use the browser clock");
assert.match(source, /function graphMappingFrame\(/,
  "Graph Mapping must render through the common display-list ABI");
assert.match(source, /screen === "task" && isGraphMappingTask\(\)[\s\S]*apiDispatchPointer\(ensureGraphMappingRun\(\), API_EVENT\.pointerDown/,
  "browser pointer-down must reach source-owned Graph Mapping button hit testing");
assert.match(source, /if \(isGraphMappingTask\(\)\) \{[\s\S]*event\.key === " " \|\| event\.key === "Enter"[\s\S]*GRAPH_MAPPING_ACTION\.start/,
  "Space and Enter must reach the Graph Mapping start path");
assert.match(source, /event\.key === "y"[\s\S]*GRAPH_MAPPING_ACTION\.same/,
  "Y must select Same through the controller");
assert.match(source, /event\.key === "n"[\s\S]*GRAPH_MAPPING_ACTION\.different/,
  "N must select Different through the controller");
assert.match(source, /if \(isGraphMappingTask\(\)\) destroyGraphMappingRun\(\)/,
  "leaving Graph Mapping must dispose the controller and timer");
assert.match(source, /graphMappingInfo, graphMappingValue, graphMappingAction, graphMappingFrame/,
  "Graph Mapping diagnostics must remain available to focused browser smoke tests");
assert.match(source, /else if \(isGraphMappingTask\(\)\) \{[\s\S]*bytes = graphMappingFrame\(dark\(\)\)/,
  "the generic stateless task frame must not be the Graph Mapping render path");

console.log("graphmapping_browser_contract_test: PASS (exports, lifecycle, timers, keyboard, pointer, render, cleanup)");
