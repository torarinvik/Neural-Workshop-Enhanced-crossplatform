import assert from 'node:assert/strict';
import fs from 'node:fs';
import { fileURLToPath } from 'node:url';
import { instantiateElisa } from '../shells/web/elisa-wasm-runtime.js';
import { decode, Kind } from '../shells/web/display-list.js';
const path = process.env.NWCORE_WASM_PATH ?? fileURLToPath(new URL('../build/nwcore.wasm', import.meta.url));
const { exports: e, instance } = await instantiateElisa(fs.readFileSync(path), { warn: false });
const task = BigInt(e.nw_api_v1_task_algebra());
const framePtr = Number(e.nw_frame_alloc(1048576n));
function texts(run) {
  const length = Number(e.nw_api_v1_render(run, BigInt(framePtr), 1048576n, 0n, 912n, 684n));
  assert.ok(length > 0);
  return decode(new Uint8Array(instance.exports.memory.buffer, framePtr, length).slice())
    .filter(command => command.kind === Kind.TEXT).map(command => command.text);
}
let sequence = 0n;
const create = level => e.nw_api_v1_create(task, 1n, BigInt(level), 1n, 0n, 0n, 0n, 0n, 19n);
const action = (run, code, value = 0) => e.nw_api_v1_dispatch(run, 1n, 1n, sequence++, BigInt(code), BigInt(value), 0n, 0n, 0n, 0n, 0n);
const info = (run, field) => e.nw_api_v1_algebra_info(run, BigInt(field));
const value = (run, field, at) => e.nw_api_v1_algebra_value(run, BigInt(field), BigInt(at));
const write = (run, text) => { for (const char of text) assert.equal(action(run, 1, char.charCodeAt(0)), 1n); };
for (let level = 1; level <= 12; level++) {
  const first = create(level), second = create(level);
  assert.ok(first > 0n && second > 0n);
  assert.equal(action(first, 0), 1n);
  assert.equal(action(second, 0), 1n);
  assert.equal(info(first, 10), 0n, 'answer length remains hidden');
  assert.equal(value(first, 2, 0), -1n, 'answer remains hidden');
  assert.ok(info(first, 9) > 0n, 'candidate count reflects the actual problem');
  assert.ok(texts(first).some(text => text.startsWith('the answer is one of about ')));
  write(first, 'x');
  assert.equal(action(first, 3), 1n);
  assert.equal(info(first, 7), 0n);
  const answer = Array.from({length: Number(info(first, 10))}, (_, at) => String.fromCharCode(Number(value(first, 2, at)))).join('');
  assert.ok(answer.length, `level ${level} reveals its exact answer`);
  assert.ok(texts(first).includes(`No - it was ${answer}`), `level ${level} renders answer feedback`);
  write(second, answer.toUpperCase());
  assert.equal(action(second, 3), 1n);
  assert.equal(info(second, 7), 1n, `level ${level}: ${answer}`);
  assert.equal(action(first, 0), 1n);
  assert.equal(info(first, 0), 3n);
  assert.equal(action(first, 0), 1n);
  assert.equal(info(first, 0), 1n, 'a completed session starts again');
  assert.equal(info(first, 2), 1n);
  assert.equal(e.nw_api_v1_destroy(first), 0n);
  assert.equal(e.nw_api_v1_destroy(second), 0n);
}
for (const input of ['('.repeat(40) + '1' + ')'.repeat(40), '-'.repeat(80) + '1', '2^'.repeat(40) + '1', '1^9223372036854775807']) {
  const run = create(1);
  assert.equal(action(run, 0), 1n);
  write(run, input);
  assert.equal(action(run, 3), 1n, 'deep input must be rejected without a trap');
  assert.equal(info(run, 7), 0n);
  assert.equal(e.nw_api_v1_destroy(run), 0n);
}
console.log('Algebra feedback: all 12 exact answers round-trip; deeply nested input is safely rejected');
