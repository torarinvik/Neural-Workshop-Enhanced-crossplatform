import assert from "node:assert/strict";
import { pythonHypot2 } from "../shells/web/python-hypot.js";

const bits = value => { const bytes = Buffer.alloc(8); bytes.writeDoubleBE(value); return bytes.toString("hex"); };
assert.equal(bits(pythonHypot2(-5.27654306449275, -4.394853154911779)), "401b77e104adbcae");
assert.equal(pythonHypot2(3, 4), 5);
assert.equal(bits(pythonHypot2(-0, -0)), "0000000000000000");
assert.equal(pythonHypot2(Number.MIN_VALUE, Number.MIN_VALUE), Number.MIN_VALUE);
assert.equal(pythonHypot2(Number.MAX_VALUE, Number.MAX_VALUE), Infinity);
assert.equal(pythonHypot2(Infinity, NaN), Infinity);
assert.equal(pythonHypot2(NaN, -Infinity), Infinity);
assert.ok(Number.isNaN(pythonHypot2(NaN, 1)));
assert.equal(pythonHypot2(2 ** -1024, 0), 2 ** -1024);
assert.equal(pythonHypot2(2 ** -1023, 0), 2 ** -1023);
console.log("PASS: Python-compatible norm regression and special-value contracts");
