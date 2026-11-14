import assert from 'node:assert/strict';
import fs from 'node:fs';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { instantiateElisa } from '../shells/web/elisa-wasm-runtime.js';
import { decode, Kind } from '../shells/web/display-list.js';

const wasm = process.env.NWCORE_WASM_PATH ?? fileURLToPath(new URL('../build/nwcore.wasm', import.meta.url));
const { exports, instance } = await instantiateElisa(fs.readFileSync(wasm), {warn: false});
const cases = JSON.parse(execFileSync('python3', [fileURLToPath(new URL('./scramble_seed_oracle.py', import.meta.url))], {encoding: 'utf8'}));
const task = BigInt(exports.nw_api_v1_task_scramble());
for (const item of cases) {
  const run = exports.nw_api_v1_create(task, 1n, BigInt(item.rung), 1n, 0n, 0n, 0n, 0n, 17n);
  let seq = 0n;
  const dispatch = (kind, code, value = 0n) => exports.nw_api_v1_dispatch(run, kind, 1000n + seq, seq++, code, value, 0n, 0n, 0n, 0n, 0n);
  const info = field => Number(exports.nw_api_v1_scramble_info(run, BigInt(field)));
  assert.equal(dispatch(1n, 0n), 1n);
  const shown = Array.from({length: info(4)}, (_, i) => {
    const c = Number(exports.nw_api_v1_scramble_value(run, 0n, BigInt(i)));
    return c === 26 ? ' ' : String.fromCharCode(97 + c);
  }).join('');
  assert.equal(shown, item.shown, `source-generated level ${item.rung}`);
  assert.equal(info(8), item.words);
  const answer = item.answer.toUpperCase().replaceAll(' ', "  '  ");
  for (const c of answer) assert.equal(dispatch(8n, 0n, BigInt(c.codePointAt(0))), 1n);
  assert.equal(dispatch(1n, 3n), 1n);
  assert.equal(info(6), 1, `case and punctuation normalize for level ${item.rung}`);
  assert.equal(exports.nw_api_v1_destroy(run), 0n);
}
const wrong = exports.nw_api_v1_create(task, 1n, 1n, 1n, 0n, 0n, 0n, 0n, 17n);
assert.equal(exports.nw_api_v1_dispatch(wrong, 1n, 1000n, 0n, 0n, 0n, 0n, 0n, 0n, 0n, 0n), 1n);
assert.equal(exports.nw_api_v1_dispatch(wrong, 8n, 1001n, 1n, 0n, 120n, 0n, 0n, 0n, 0n, 0n), 1n);
assert.equal(exports.nw_api_v1_dispatch(wrong, 1n, 1002n, 2n, 3n, 0n, 0n, 0n, 0n, 0n, 0n), 1n);
assert.equal(exports.nw_api_v1_scramble_info(wrong, 6n), 0n);
const ptr = Number(exports.nw_frame_alloc(1048576n));
const length = Number(exports.nw_api_v1_render(wrong, BigInt(ptr), 1048576n, 0n, 912n, 684n));
const labels = decode(new Uint8Array(instance.exports.memory.buffer, ptr, length).slice()).filter(c => c.kind === Kind.TEXT).map(c => c.text);
assert.ok(labels.some(text => text.includes(cases[0].answer)), 'wrong feedback reveals the original sentence');
exports.nw_frame_free(BigInt(ptr));
assert.equal(exports.nw_api_v1_destroy(wrong), 0n);
console.log('scramble_seed_game_test: PASS (12 source deals, normalized answers, wrong feedback)');
