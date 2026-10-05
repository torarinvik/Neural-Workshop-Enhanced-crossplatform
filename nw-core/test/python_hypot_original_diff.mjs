import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { pythonHypot2 } from "../shells/web/python-hypot.js";

const python = process.env.NW_REFERENCE_PYTHON ??
  "/Users/torarinvikbjarko/Documents/Coding Projects/Python Projects/neural-workshop-enhanced/.venv/bin/python3";
const pairs = [[-5.27654306449275, -4.394853154911779], [0, -0],
  [Number.MIN_VALUE, Number.MIN_VALUE], [Number.MAX_VALUE, Number.MAX_VALUE]];
for (let exponent = -1074; exponent <= -1020; exponent++) {
  pairs.push([2 ** exponent, 2 ** (exponent + 1)], [2 ** exponent, 1],
    [2 ** exponent, 0], [2 ** exponent, Number.MIN_VALUE]);
}
let seed = 565;
function random() { seed = (Math.imul(seed, 1664525) + 1013904223) >>> 0; return seed / 2 ** 32; }
for (let i = 0; i < 20000; i++) {
  const exponent = Math.floor(random() * 2046) - 1022;
  pairs.push([(random() * 2 - 1) * 2 ** exponent, (random() * 2 - 1) * 2 ** exponent]);
}
const result = spawnSync(python, ["-c", `
import json,math,struct,sys
rows=json.load(sys.stdin)
print(json.dumps([struct.pack(">d",math.hypot(x,y)).hex() for x,y in rows]))
`], { input: JSON.stringify(pairs), encoding: "utf8", maxBuffer: 16 * 1024 * 1024 });
assert.equal(result.status, 0, result.stderr);
const expected = JSON.parse(result.stdout);
for (let i = 0; i < pairs.length; i++) {
  const buffer = Buffer.alloc(8);
  buffer.writeDoubleBE(pythonHypot2(...pairs[i]));
  assert.equal(buffer.toString("hex"), expected[i], `norm case ${i}: ${pairs[i]}`);
}
assert.equal(pythonHypot2(Infinity, NaN), Infinity);
assert.ok(Number.isNaN(pythonHypot2(NaN, 1)));
console.log(`PASS: Python-compatible hypot2 (${pairs.length} complete-bit comparisons)`);
