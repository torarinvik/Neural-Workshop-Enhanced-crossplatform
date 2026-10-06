// The web shell must reject a core that lacks any common v1 lifecycle export.
// This catches version-compatible but incomplete/stale WASM artifacts before
// task routing reaches a call site that would otherwise fail at runtime.
import assert from "node:assert/strict";
import fs from "node:fs";
import { fileURLToPath } from "node:url";

const root = fileURLToPath(new URL("..", import.meta.url));
const html = fs.readFileSync(`${root}/shells/web/index.html`, "utf8");
const requiredMatch = html.match(/const REQUIRED_CORE_EXPORTS = \[([\s\S]*?)\n\];/);
assert.ok(requiredMatch, "web shell must declare REQUIRED_CORE_EXPORTS");
const requiredExports = new Set(
  [...requiredMatch[1].matchAll(/"(nw_[a-zA-Z0-9_]+)"/g)].map((match) => match[1]),
);

for (const name of [
  "nw_api_v1_create",
  "nw_api_v1_dispatch",
  "nw_api_v1_advance",
  "nw_api_v1_read_state",
  "nw_api_v1_render",
  "nw_api_v1_drain_effects",
  "nw_api_v1_snapshot",
  "nw_api_v1_restore",
  "nw_api_v1_destroy",
]) {
  assert.ok(requiredExports.has(name), `web shell must require ${name}`);
}

assert.match(html, /REQUIRED_CORE_EXPORTS\.filter\(\s*\(name\) => typeof exports\[name\] !== "function"\)/,
  "every required export must be checked against the instantiated core");
assert.match(html, /coreVersion !== 1/,
  "the shell must reject a core with an incompatible API version");

console.log("runtime_protocol_shell_contract_test: PASS (complete v1 lifecycle exports and ABI version are required)");
