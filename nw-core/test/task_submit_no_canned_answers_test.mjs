import assert from "node:assert/strict";
import fs from "node:fs";
import { fileURLToPath } from "node:url";

const sourcePath = fileURLToPath(new URL("../shells/web/index.html", import.meta.url));
const source = fs.readFileSync(sourcePath, "utf8");
const taskSubmit = source.match(/function taskSubmit\(\) \{([\s\S]*?)\n\}\n\nfunction taskPrimary\(\)/);
assert.ok(taskSubmit, "the shell must retain its task submit dispatcher");
assert.doesNotMatch(taskSubmit[1], /const\s+correct\s*=\s*\{/,
  "generic fallback grading must not keep a task-answer dictionary");
assert.match(taskSubmit[1], /taskState\.verdict\s*=\s*-1/,
  "generic legacy submissions must preserve unknown verdict rather than fabricate grading");
assert.doesNotMatch(source, /const CHOICE_TASKS\s*=/,
  "answer-choice fallback metadata must not remain once fixed grading is removed");

console.log("task_submit_no_canned_answers_test: PASS (generic fallback leaves verdict unknown)");
