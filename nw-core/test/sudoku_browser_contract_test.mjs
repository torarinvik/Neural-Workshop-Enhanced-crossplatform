import assert from "node:assert/strict";
import fs from "node:fs";
import { fileURLToPath } from "node:url";

const shell = fileURLToPath(new URL("../shells/web/index.html", import.meta.url));
const source = fs.readFileSync(shell, "utf8");

assert.match(source, /nw_api_v1_task_sudoku/,
  "the shell must require the Sudoku common-v1 task id");
assert.match(source, /sudoku:\s*exports\.nw_api_v1_task_sudoku\(\)/,
  "the task table must expose Sudoku through common-v1");
assert.match(source, /function isSudokuTask\(\)/,
  "Sudoku must have an explicit category predicate");
assert.match(source, /return isTaskId\("sudoku"\)/,
  "Sudoku must be selected by stable task identity");
assert.match(source, /function ensureSudokuRun\(\)/,
  "Sudoku must own a persistent browser-side run handle");
assert.match(source, /\[3n, 3n, 1n, 1n, 0n, 0n\]/,
  "the shell defaults must match the source's rung, trials, clashes, and adaptive options");
assert.match(source, /function sudokuDigit\(key\)/,
  "Sudoku must preserve the source's 1-9/A-G digit alphabet");
assert.match(source, /function sudokuFrame\(black\)/,
  "Sudoku must render through the common display-list ABI");
assert.match(source, /if \(isSudokuTask\(\)\) \{[\s\S]*SUDOKU_ACTION\.start/,
  "Space and Enter must reach the Sudoku start/advance path");
assert.match(source, /SUDOKU_ACTION\.pencil/,
  "N must reach the source pencil-mode action");
assert.match(source, /SUDOKU_ACTION\.erase/,
  "0, Backspace, and Delete must reach the source erase action");
assert.match(source, /SUDOKU_ACTION\.write, digit/,
  "typed Sudoku digits must reach the controller as semantic values");
assert.match(source, /if \(isSudokuTask\(\)\) destroySudokuRun\(\)/,
  "leaving Sudoku must dispose its controller");
assert.match(source, /else if \(isSudokuTask\(\)\) \{[\s\S]*bytes = sudokuFrame\(dark\(\)\)/,
  "the generic stateless task frame must not render Sudoku");
assert.match(source, /sudokuInfo, sudokuValue, sudokuAction, sudokuFrame, sudokuState/,
  "focused Sudoku browser diagnostics must remain available");

console.log("sudoku_browser_contract_test: PASS (exports, task position, source defaults, keyboard, render, lifecycle, cleanup)");
