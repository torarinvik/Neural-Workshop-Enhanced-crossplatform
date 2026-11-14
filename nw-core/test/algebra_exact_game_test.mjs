import assert from 'node:assert/strict';
import fs from 'node:fs';
import { fileURLToPath } from 'node:url';
import { instantiateElisa } from '../shells/web/elisa-wasm-runtime.js';

const path = process.env.NWCORE_WASM_PATH ?? fileURLToPath(new URL('../build/nwcore.wasm', import.meta.url));
const { exports: e } = await instantiateElisa(fs.readFileSync(path), { warn: false });
const task = BigInt(e.nw_api_v1_task_algebra());
const create = level => e.nw_api_v1_create(task, 1n, BigInt(level), 1n, 0n, 0n, 0n, 0n, 17n);
let sequence = 0n;
const action = (run, code, value = 0) => e.nw_api_v1_dispatch(run, 1n, 1n, sequence++, BigInt(code), BigInt(value), 0n, 0n, 0n, 0n, 0n);
const info = (run, field) => e.nw_api_v1_algebra_info(run, BigInt(field));
const read = (run, field, length) => Array.from({length: Number(length)}, (_, i) => String.fromCharCode(Number(e.nw_api_v1_algebra_value(run, BigInt(field), BigInt(i))))).join('');
const write = (run, text) => { for (const c of text) assert.equal(action(run, 1, c.charCodeAt(0)), 1n); };
for (const level of [5, 7, 9, 11, 12]) {
  const run = create(level);
  assert.ok(run > 0n);
  assert.equal(action(run, 0), 1n);
  assert.equal(info(run, 0), 1n, `level ${level} generated`);
  const question = read(run, 0, info(run, 4));
  assert.ok(question.length);
  if (level === 5) {
    const match = /^(\d+)\/(\d+) \+ (\d+)\/(\d+)$/.exec(question);
    assert.ok(match, question);
    const [a, b, c, d] = match.slice(1).map(BigInt);
    const answer = `${a*d+c*b}/${b*d}`;
    write(run, answer);
    assert.equal(read(run, 1, info(run, 6)), answer);
    assert.equal(action(run, 3), 1n);
    assert.equal(info(run, 7), 1n, 'equivalent fraction is accepted');
  } else {
    write(run, '1234567890123456789012345678901234567890+x');
    assert.equal(info(run, 6), 42n);
    assert.equal(action(run, 2), 1n);
    assert.equal(info(run, 6), 41n);
    assert.equal(action(run, 3), 1n);
    assert.equal(info(run, 7), 0n);
  }
  assert.equal(e.nw_api_v1_destroy(run), 0n);
}
console.log('Algebra exact controller: fractions, symbolic rungs, long text, erase and grading pass');
