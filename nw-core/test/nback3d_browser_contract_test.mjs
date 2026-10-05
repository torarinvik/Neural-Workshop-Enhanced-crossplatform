// Static browser-shell contract for the only port-scoped N-Back route.
// Runtime state/render/disposal behavior is covered by the WASM smoke; this
// test protects the surrounding menu, focus, keyboard, timer, and exit glue.
import assert from "node:assert/strict";
import fs from "node:fs";
import { fileURLToPath } from "node:url";

const root = fileURLToPath(new URL("..", import.meta.url));
const html = fs.readFileSync(`${root}/shells/web/index.html`, "utf8");
const registry = fs.readFileSync(`${root}/shells/web/task-registry.js`, "utf8");

assert.match(registry, /"nback_3d"/);
assert.match(html, /<canvas id="screen"[^>]*tabindex="0"/,
  "the shared screen must be keyboard-focusable");
assert.match(html, /<button id="screen-nback3d">3D N-Back<\/button>/);
assert.match(html, /if \(isTaskId\("nback_3d"\)\) \{\s*setScreen\("nback3d"\);\s*resetNBack3DRun\(\);/s);
assert.match(html, /if \(screen === "nback3d" && next !== "nback3d"\) \{\s*destroyNBack3DRun\(\);/s,
  "leaving the task must dispose its controller and timer");
assert.match(html, /function destroyNBack3DRun\(\) \{\s*cancelNBack3DTimer\(\);\s*if \(nback3dRunHandle !== 0n\) apiDestroyRun\(nback3dRunHandle\);/s);
assert.match(html, /if \(screen === "nback3d"\) \{\s*bytes = nback3dFrame\(dark\(\)\);/s,
  "the nback screen must render through the 3D controller");
assert.match(html, /if \(event\.key === "a" \|\| event\.key === "A"\) \{\s*nback3dAction\(NBACK3D_ACTION\.match\);/s);
assert.match(html, /else if \(event\.key === "p" \|\| event\.key === "P"\) \{\s*nback3dAction\(NBACK3D_ACTION\.pause\);/s);
assert.match(html, /else if \(event\.key === "r" \|\| event\.key === "R"\) \{\s*nback3dAction\(NBACK3D_ACTION\.restart\);/s);
assert.match(html, /if \(event\.key === "Escape"\) \{\s*setScreen\("taskhub"\);\s*draw\(\);/s);
assert.match(html, /scheduleNBack3DAdvance\(\);/);

console.log("nback3d_browser_contract_test: PASS (route, focus, keyboard, timer, render, exit, disposal)");
