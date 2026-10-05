import assert from "node:assert/strict";
import fs from "node:fs";
import { fileURLToPath } from "node:url";

const shell = fileURLToPath(new URL("../shells/web/index.html", import.meta.url));
const source = fs.readFileSync(shell, "utf8");

assert.match(source, /nw_api_v1_task_matrix_reasoning/,
  "the shell must require the Matrix Reasoning common-v1 task id");
assert.match(source, /matrixReasoning:\s*exports\.nw_api_v1_task_matrix_reasoning\(\)/,
  "the task table must expose Matrix Reasoning through common-v1");
assert.match(source, /function isMatrixReasoningTask\(\)/,
  "Matrix Reasoning must have an explicit category predicate");
assert.match(source, /return isTaskId\("matrix_reasoning"\)/,
  "Matrix Reasoning must be selected by stable task identity");
assert.match(source, /function ensureMatrixReasoningRun\(\)/,
  "Matrix Reasoning must own a persistent browser-side run handle");
assert.match(source, /MATRIX_LEVEL_OPTIONS = Object\.freeze\(\[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12\]\)/,
  "Matrix Reasoning must expose all twelve source levels");
assert.match(source, /MATRIX_OPTIONS_STORAGE = "neural-workshop\.matrix-reasoning\.options\.v1"/,
  "Matrix Reasoning options must use a versioned persistence key");
assert.match(source, /function readMatrixReasoningOptions\(\)/,
  "Matrix Reasoning options must be validated and restored from storage");
assert.match(source, /function openMatrixReasoningOptions\(returnTo\)/,
  "Matrix Reasoning must have a real options route");
assert.match(source, /BigInt\(\(matrixReasoningOptions\.feedback \? 1 : 0\) \|\s*\(matrixReasoningOptions\.explain \? 2 : 0\)\)/,
  "feedback and explanation must use the source-compatible packed flags slot");
assert.match(source, /function drawMatrixReasoningOptionsScreen\(\)/,
  "Matrix Reasoning options must render an explicit six-row screen");
assert.match(source, /if \(screen === "matrixReasoningOptions"\)[\s\S]*applyMatrixReasoningOptions\(\)[\s\S]*modifyMatrixReasoningOption\(1\)/,
  "Matrix Reasoning options must support keyboard apply and editing");
assert.match(source, /if \(screen === "matrixReasoningOptions"\) \{[\s\S]*matrixReasoningOptionRowFromEvent\(event\)/,
  "Matrix Reasoning options must support pointer row selection and editing");
assert.match(source, /const openingMatrixReasoningOptions = screen === "task" && isMatrixReasoningTask\(\)[\s\S]*next === "matrixReasoningOptions"/,
  "opening Matrix Reasoning options must preserve the live controller");
assert.match(source, /function matrixReasoningFrame\(black\)/,
  "Matrix Reasoning must render through the common display-list ABI");
assert.match(source, /MATRIX_REASONING_ACTION\.answer/,
  "number-key answers must reach the real controller");
assert.match(source, /apiDispatchPointer\(ensureMatrixReasoningRun\(\), API_EVENT\.pointerDown/,
  "candidate clicks must reach the common pointer ABI");
assert.match(source, /function scheduleMatrixReasoningAdvance\(/,
  "exposure and feedback deadlines must be scheduled by the browser shell");
assert.match(source, /if \(isMatrixReasoningTask\(\)\) destroyMatrixReasoningRun\(\)/,
  "leaving Matrix Reasoning must dispose its controller");
assert.match(source, /else if \(isMatrixReasoningTask\(\)\) \{[\s\S]*bytes = matrixReasoningFrame\(dark\(\)\)/,
  "the generic stateless task frame must not render Matrix Reasoning");
assert.match(source, /event\.key === "c" \|\| event\.key === "C"\) \{\s*const phase = matrixReasoningInfo\(MATRIX_REASONING_INFO\.phase\);\s*if \(phase === MATRIX_REASONING_PHASE\.ready \|\| phase === MATRIX_REASONING_PHASE\.done\) \{\s*openMatrixReasoningOptions\("task"\);/,
  "task-screen C must open Matrix Reasoning options only between runs");
assert.match(source, /matrixReasoningInfo,\s*matrixReasoningValue,\s*matrixReasoningAction,\s*matrixReasoningFrame/,
  "focused Matrix Reasoning browser diagnostics must remain available");

console.log("ravens_browser_contract_test: PASS (exports, task position, source defaults, keyboard, pointer, scheduling, render, lifecycle, cleanup)");
