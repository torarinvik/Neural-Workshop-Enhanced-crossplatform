import assert from 'node:assert/strict';
import fs from 'node:fs';
import {instantiateElisa} from '../shells/web/elisa-wasm-runtime.js';
import {decode, Kind} from '../shells/web/display-list.js';

const cases = JSON.parse(fs.readFileSync(new URL('./numberology_session_oracle.json', import.meta.url)));
const path = process.env.NWCORE_WASM_PATH ?? new URL('../build/nwcore.wasm', import.meta.url);
const {exports: e, instance} = await instantiateElisa(fs.readFileSync(path), {warn: false});
const task = BigInt(e.nw_api_v1_task_numberology());
const frame = e.nw_frame_alloc(1048576n);
let sequence = 0n;
const act = (run, code, value = 0) => e.nw_api_v1_dispatch(run, 1n, 17n, sequence++, BigInt(code), BigInt(value), 0n, 0n, 0n, 0n, 0n);
const info = (run, field) => e.nw_api_v1_numberology_info(run, BigInt(field));
const value = (run, field, length) => new TextDecoder().decode(Uint8Array.from(
  {length: Number(length)}, (_, i) => Number(e.nw_api_v1_numberology_value(run, BigInt(field), BigInt(i)))));
const labels = run => {
  const n = Number(e.nw_api_v1_render(run, frame, 1048576n, 0n, 912n, 684n));
  assert.ok(n > 0);
  return decode(new Uint8Array(instance.exports.memory.buffer, Number(frame), n).slice())
    .filter(item => item.kind === Kind.TEXT).map(item => item.text);
};
for (const scenario of cases) {
  const run = e.nw_api_v1_create(task, 1n, BigInt(scenario.level), BigInt(scenario.trials),
    BigInt(scenario.adaptive), 0n, 0n, 0n, BigInt(scenario.seed));
  assert.ok(run > 0n);
  assert.equal(act(run, 0), 1n);
  for (const [index, row] of scenario.rows.entries()) {
    assert.equal(info(run, 0), 1n);
    assert.equal(info(run, 2), BigInt(index + 1));
    assert.equal(act(run, 3), 2n, 'empty submission stays working');
    assert.equal(value(run, 0, info(run, 14)), row.terms.join('\n') + '\n');
    for (const character of row.input) assert.equal(act(run, 1, character.charCodeAt(0)), 1n);
    assert.equal(act(run, 3), 1n);
    assert.equal(info(run, 0), 2n);
    assert.equal(info(run, 10), BigInt(row.right));
    const painted = labels(run);
    assert.ok(painted.includes(row.message), `judgment: ${row.message}`);
    assert.ok(painted.includes(row.rule), `rule: ${row.rule}`);
    assert.equal(act(run, 0), 1n);
  }
  assert.equal(info(run, 0), 3n);
  assert.equal(info(run, 13), BigInt(scenario.next_level));
  assert.ok(labels(run).includes(scenario.message), `summary: ${scenario.message}`);
  assert.equal(e.nw_api_v1_destroy(run), 0n);
}
console.log('Numberology complete-session replay: source questions, feedback, score and progression match');
