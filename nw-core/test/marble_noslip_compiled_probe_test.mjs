// Isolated candidate only; no browser or production files are modified.
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import fs from "node:fs";
import { dirname, resolve } from "node:path";
import { pathToFileURL } from "node:url";

assert.equal(process.argv.length, 4, "provide private module and golden JSONL");
const [moduleFile, inputFile] = process.argv.slice(2).map((p) => resolve(p));
const sha = (p) => createHash("sha256").update(fs.readFileSync(p)).digest("hex");
const module = await (await import(pathToFileURL(moduleFile).href)).default();
assert.equal(typeof module.marbleWheelResidualProbe, "function");
const bits = (v) => {
  const b = new ArrayBuffer(8);
  new DataView(b).setFloat64(0, v, false);
  return Buffer.from(b).toString("hex");
};
const counts = { dot: 0, residual: 0, rejected: 0 };
let differences = 0;
const first = [];
for (const line of fs.readFileSync(inputFile, "utf8").trim().split("\n")) {
  const row = JSON.parse(line);
  assert.equal(row.referenceSha256, "9e7724614fb0b3f346758ff4158ef65e7c398f2caa3e9daab41ed210b4ab689c");
  assert.ok(["dot", "residual"].includes(row.kind));
  assert.ok(Array.isArray(row.values) && row.values.length <= 1029);
  assert.ok(row.values.every((v) => typeof v === "number" && Number.isFinite(v)));
  const actual = module.marbleWheelResidualProbe(row.values);
  assert.equal(actual.accepted, true, row.label);
  if (bits(actual.result) !== row.expectedBits) {
    differences++;
    if (first.length < 8) first.push({ label: row.label, expectedBits: row.expectedBits,
                                     actualBits: bits(actual.result) });
  }
  counts[row.kind]++;
}
for (const p of [[], [1], [2, 0, 0, 0, 0], [1, Infinity, 0, 0, 0],
                 [true, 0, 0, 0, 0], [1, 0, 0, 0, 0.5], [1, 0, 0, 0, 513],
                 [1, 0, 0, 0, 1]]) {
  assert.equal(module.marbleWheelResidualProbe(p).accepted, false);
  counts.rejected++;
}
console.log(JSON.stringify({ schema: "neural-workshop.marble-compiled-noslip-probe.v1",
  runtime: { jsPath: moduleFile, jsSha256: sha(moduleFile),
             wasmSha256: sha(resolve(dirname(moduleFile), "mujoco.wasm")) },
  inputSha256: sha(inputFile), counts, differences, first }));
assert.equal(counts.dot, 9200);
assert.equal(counts.residual, 9205);
assert.equal(differences, 0, "compiled residual differs from qualified operation order");
