import assert from "node:assert/strict";
import fs from "node:fs";
import { fileURLToPath } from "node:url";

const shell = fileURLToPath(new URL("../shells/web/index.html", import.meta.url));
const source = fs.readFileSync(shell, "utf8");
const start = source.indexOf("function reflexInfo(field)");
const end = source.indexOf("function reflexValue(field, at)", start);
assert.ok(start >= 0 && end > start, "Reflex accessor is present");
const accessor = source.slice(start, end);
assert.match(accessor, /if \(field >= 0 && field < 4\) return Number\(state\[field\]\)/);
assert.doesNotMatch(accessor, /const commonField/);
assert.match(source, /return isTaskId\("reflex"\)/);
assert.match(source, /apiDispatchPointer\(ensureReflexRun\(\), API_EVENT\.pointerDown/);
assert.match(source, /reflexAction\(REFLEX_ACTION\.start\)/);
assert.match(source, /bytes = reflexFrame\(dark\(\)\)/);
console.log("reflex_browser_contract_test: PASS (menu position, state-field mapping, pointer input, start, render)");
