import assert from "node:assert/strict";
import {createHash} from "node:crypto";
import fs from "node:fs";
import {dirname, resolve} from "node:path";
import {pathToFileURL} from "node:url";

assert.equal(process.argv.length, 4, "provide private module and original complete-comVel golden JSONL");
const [modulePath, inputPath] = process.argv.slice(2).map(p => resolve(p));
const rows = fs.readFileSync(inputPath, "utf8").trim().split("\n").map(line => JSON.parse(line));
const inputs = ["qvel", "cdof"], outputs = ["cvel", "cdof_dot"];
const topology = ["body_parentid", "body_dofadr", "body_dofnum", "dof_jntid", "jnt_type", "jnt_dofadr"];
const bits = value => {
  const buffer = new ArrayBuffer(8);
  new DataView(buffer).setFloat64(0, value, false);
  return Buffer.from(buffer).toString("hex");
};
const sha = path => createHash("sha256").update(fs.readFileSync(path)).digest("hex");
// Validate the complete golden before allocating or calling any native model.
for (const row of rows) {
  assert.equal(row.referenceSha256, "9e7724614fb0b3f346758ff4158ef65e7c398f2caa3e9daab41ed210b4ab689c");
  assert.ok(["captured", "synthetic"].includes(row.kind));
  assert.ok(typeof row.xml === "string" && row.xml.length < 10000);
  const {model: m, arrays: a} = row.input;
  const nb = m.body_parentid.length, nv = a.qvel.length;
  assert.ok(nb >= 1 && nb <= 1000 && nv >= 1 && nv <= 512);
  for (const flag of ["enableflags", "disableflags"])
    assert.ok(Number.isInteger(m.options[flag]) && m.options[flag] >= 0 && m.options[flag] <= 2147483647);
  assert.equal(m.options.enableflags & 16, 0, "sleep-enabled context is unqualified");
  assert.equal(m.disableflags, m.options.disableflags);
  for (const field of topology) {
    assert.ok(Array.isArray(m[field]) && m[field].length <= 1000);
    assert.ok(m[field].every(Number.isInteger));
  }
  for (const [field, width] of [["qvel", nv], ["cdof", 6 * nv], ["cvel", 6 * nb], ["cdof_dot", 6 * nv]]) {
    assert.equal(a[field].length, width);
    assert.ok(a[field].every(v => typeof v === "number" && Number.isFinite(v)));
    if (outputs.includes(field)) {
      assert.equal(row.expected[field].length, width);
      assert.equal(row.expectedBits[field].length, width);
      assert.ok(row.expected[field].every(v => typeof v === "number" && Number.isFinite(v)));
      assert.deepEqual(row.expected[field].map(bits), row.expectedBits[field]);
    }
  }
}
const module = await (await import(pathToFileURL(modulePath).href)).default();
const contexts = new Map(), counts = {captured: 0, synthetic: 0}, layouts = {};
const differingCalls = {captured: 0, synthetic: 0};
let differences = 0, differentValues = 0;
const first = [];
try {
  for (const row of rows) {
    const {model: m, arrays: a} = row.input;
    let context = contexts.get(row.xml);
    if (!context) {
      const model = module.MjModel.from_xml_string(row.xml);
      context = {model, data: new module.MjData(model)};
      contexts.set(row.xml, context);
    }
    const {model, data} = context;
    for (const field of topology)
      assert.deepEqual(Array.from(model[field]), m[field], "owned comVel topology differs: " + field);
    model.opt.enableflags = m.options.enableflags;
    model.opt.disableflags = m.options.disableflags;
    for (const field of [...inputs, ...outputs]) {
      assert.equal(data[field].length, a[field].length);
      data[field].set(a[field]);
      assert.deepEqual(Array.from(data[field]), a[field], "owned comVel input copy differs");
    }
    // Actual existing public call on native-owned model/data, no mirror or new
    // binding. Compare every output bit; JSON captures do not qualify zero signs.
    module.mj_comVel(model, data);
    const diff = {};
    for (const field of outputs) {
      const actual = Array.from(data[field], bits);
      const indices = actual.flatMap((value, i) => value === row.expectedBits[field][i] ? [] : [i]);
      if (indices.length) {
        diff[field] = {indices, expectedBits: indices.map(i => row.expectedBits[field][i]),
          actualBits: indices.map(i => actual[i])};
        differentValues += indices.length;
      }
    }
    if (Object.keys(diff).length) {
      differences++;
      differingCalls[row.kind]++;
      if (first.length < 8) first.push({label: row.label, kind: row.kind, differences: diff});
    }
    for (const field of inputs)
      assert.deepEqual(Array.from(data[field]), a[field], "comVel mutated input arrays");
    counts[row.kind]++;
    layouts[row.layout] = (layouts[row.layout] ?? 0) + 1;
  }
} finally {
  for (const {model, data} of contexts.values()) {
    data.delete();
    model.delete();
  }
}
console.log(JSON.stringify({schema: "neural-workshop.marble-compiled-comvel.v1",
  runtime: {jsPath: modulePath, jsSha256: sha(modulePath), wasmSha256: sha(resolve(dirname(modulePath), "mujoco.wasm"))},
  inputSha256: sha(inputPath), counts, layouts, differences, differentValues, differingCalls, first,
  completePublicCall: true, sleepEnabled: false, originalPrivateIntermediatesCaptured: false,
  ordinaryTrajectoryAcceptance: false, promoted: false}));
assert.deepEqual(counts, {captured: 20, synthetic: 1000});
assert.equal(differences, 0, "actual compiled complete comVel outputs differ from original");
