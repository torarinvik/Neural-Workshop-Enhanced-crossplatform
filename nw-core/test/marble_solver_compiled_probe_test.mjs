// Isolated diagnostic module only. Calls the same compiled PrimalEval used
// by its real solver, not a reimplementation of the model in JavaScript.
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import fs from "node:fs";
import { dirname, resolve } from "node:path";
import { pathToFileURL } from "node:url";

const [moduleFile, inputFile] = process.argv.slice(2).map((path) => resolve(path));
assert.ok(moduleFile && inputFile, "provide private module and generated golden JSONL paths");
const sha = (path) => createHash("sha256").update(fs.readFileSync(path)).digest("hex");
const module = await (await import(pathToFileURL(moduleFile).href)).default();
assert.equal(typeof module.marbleWheelEvalProbe, "function");
assert.equal(typeof module.marbleWheelFmaProbe, "function");
const bits = (value) => {
  const bytes = new ArrayBuffer(8);
  new DataView(bytes).setFloat64(0, value, false);
  return Buffer.from(bytes).toString("hex");
};
const counts = { fma: 0, eval: 0, rejected: 0 };
let differences = 0;
const first = [];
for (const line of fs.readFileSync(inputFile, "utf8").trim().split("\n")) {
  const row = JSON.parse(line);
  assert.equal(row.referenceSha256, "9e7724614fb0b3f346758ff4158ef65e7c398f2caa3e9daab41ed210b4ab689c");
  assert.ok(Array.isArray(row.values) && row.values.length <= 800000);
  assert.ok(row.values.every((v) => typeof v === "number" && Number.isFinite(v)));
  let actual;
  if (row.kind === "fma") {
    assert.equal(row.values.length, 3);
    actual = [module.marbleWheelFmaProbe(...row.values)];
  } else {
    assert.equal(row.kind, "eval");
    const output = module.marbleWheelEvalProbe(row.values);
    assert.equal(output.accepted, true, row.label);
    actual = Array.from(output.result, Number);
  }
  const actualBits = actual.map(bits);
  if (JSON.stringify(actualBits) !== JSON.stringify(row.expectedBits)) {
    differences++;
    if (first.length < 8) first.push({ label: row.label, expectedBits: row.expectedBits, actualBits, actual });
  }
  counts[row.kind]++;
}
for (const values of [[], [1], [1, 0.5, 1, 0, 0, 0, 0, 0, 0],
                      [2, 0.5, 0, 0, 0, 0, 0, 0, 1],
                      [1, 0.5, 0, 0, 0.5, 0, 0, 0, 1],
                      [true, 0.5, 0, 0, 0, 0, 0, 0, 1],
                      [1, Infinity, 0, 0, 0, 0, 0, 0, 1]]) {
  assert.equal(module.marbleWheelEvalProbe(values).accepted, false);
  counts.rejected++;
}
console.log(JSON.stringify({ schema: "neural-workshop.marble-compiled-eval-probe.v1",
  runtime: { jsPath: moduleFile, jsSha256: sha(moduleFile),
             wasmSha256: sha(resolve(dirname(moduleFile), "mujoco.wasm")) },
  inputSha256: sha(inputFile), counts, differences, first }));
assert.equal(counts.fma, 1002);
assert.equal(counts.eval, 5465);
assert.equal(differences, 0, "compiled evaluator differs from actual original on matched prepared inputs");
