// Export one deterministic maximum-density Graph Mapping trial for reference
// screenshot capture. The seed and options match ensureGraphMappingRun in the
// browser shell; this file is verification tooling, not production gameplay.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";

const root = fileURLToPath(new URL("..", import.meta.url));
const output = path.resolve(process.argv[2] ??
  `${root}/output/verification/graphmapping-visual-review-20261109/seed17-max-dense.json`);
const wasmPath = process.env.NWCORE_WASM_PATH ?? `${root}/build/nwcore.wasm`;
const { exports } = await instantiateElisa(fs.readFileSync(wasmPath), { warn: false });
const task = BigInt(exports.nw_api_v1_task_graph_mapping());
const run = exports.nw_api_v1_create(task, 1n, 16n, 2n, 20n, 0n, 0n, 1n, 17n);
if (run <= 0n) throw new Error(`Graph Mapping create failed: ${run}`);
const status = exports.nw_api_v1_dispatch(run, 1n, 100n, 0n,
  0n, 0n, 0n, 0n, 0n, 0n, 0n);
if (status !== 1n) throw new Error(`Graph Mapping start failed: ${status}`);

function info(field) {
  return Number(exports.nw_api_v1_graph_mapping_info(run, BigInt(field)));
}

function value(field, at = 0) {
  return Number(exports.nw_api_v1_graph_mapping_value(run, BigInt(field), BigInt(at)));
}

function edges(field) {
  const result = [];
  for (let at = 0; at < 120; at++) {
    const code = value(field, at);
    if (code < 0) break;
    result.push([Math.floor(code / 16), code % 16]);
  }
  return result;
}

const nodes = info(2);
if (info(0) !== 1 || nodes !== 16 || info(3) !== 2 || info(12) !== 0) {
  throw new Error("fixture did not enter the expected 16-dot dense ASKING state");
}
const points = (xField, yField) => Array.from({ length: nodes }, (_, at) => ({
  x: value(xField, at) / 1_000_000,
  y: value(yField, at) / 1_000_000,
}));
const fixture = {
  provenance: { wasmSha256: null, taskId: task.toString(), seed: 17,
    options: { nodes: 16, density: "dense", trials: 20,
      exposureMs: 0, adaptive: false, subtle: true } },
  phase: "asking", trial: info(4), totalTrials: info(5), correct: info(6),
  message: "The same network?", nodes,
  graphs: [{ size: nodes, edges: edges(0) }, { size: nodes, edges: edges(1) }],
  spots: [points(2, 3), points(4, 5)],
};
fixture.provenance.wasmSha256 = await (async () => {
  const { createHash } = await import("node:crypto");
  return createHash("sha256").update(fs.readFileSync(wasmPath)).digest("hex");
})();
fs.mkdirSync(path.dirname(output), { recursive: true });
fs.writeFileSync(output, `${JSON.stringify(fixture, null, 2)}\n`);
exports.nw_api_v1_destroy(run);
console.log(`graphmapping_visual_fixture: PASS (${output})`);
