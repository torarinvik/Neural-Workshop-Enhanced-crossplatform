import assert from 'node:assert/strict';
import fs from 'node:fs';
import { fileURLToPath } from 'node:url';
import { instantiateElisa } from '../shells/web/elisa-wasm-runtime.js';
import { decode, Kind } from '../shells/web/display-list.js';
const wasm = process.env.NWCORE_WASM_PATH ?? fileURLToPath(new URL('../build/nwcore.wasm', import.meta.url));
const {exports: e, instance} = await instantiateElisa(fs.readFileSync(wasm), {warn:false});
const task = BigInt(e.nw_api_v1_task_algebra());
let sequence = 0n;
const create = (level, hide, adaptive) => e.nw_api_v1_create(task, 1n, BigInt(level), 1n, BigInt(hide), BigInt(adaptive), 0n, 0n, 19n);
const action = (r, c, v=0) => e.nw_api_v1_dispatch(r,1n,1n,sequence++,BigInt(c),BigInt(v),0n,0n,0n,0n,0n);
const info = (r, field) => e.nw_api_v1_algebra_info(r, BigInt(field));
const answer = r => new TextDecoder().decode(Uint8Array.from({length:Number(info(r,10))}, (_,i)=>Number(e.nw_api_v1_algebra_value(r,2n,BigInt(i)))));
const frame = Number(e.nw_frame_alloc(1048576n));
for (const level of [1,3,12]) for (const right of [false,true]) {
  const oracle = create(level,0,0), run = create(level,1,1);
  assert.equal(action(oracle,0),1n); assert.equal(action(run,0),1n);
  assert.equal(action(oracle,1,120),1n); assert.equal(action(oracle,3),1n);
  const typed = right ? answer(oracle) : 'x';
  for (const ch of typed) assert.equal(action(run,1,ch.charCodeAt(0)),1n);
  assert.equal(action(run,3),1n);
  assert.equal(info(run,7), right ? 1n : 0n);
  assert.equal(info(run,1), BigInt(Math.min(12,Math.max(1,level+(right?1:-1)))));
  assert.equal(info(run,11),0n); assert.equal(info(run,12),0n); assert.equal(info(run,13),1n);
  assert.equal(e.nw_api_v1_algebra_value(run,3n,0n),-1n);
  const n=Number(e.nw_api_v1_render(run,BigInt(frame),1048576n,0n,912n,684n));
  const texts=decode(new Uint8Array(instance.exports.memory.buffer,frame,n).slice()).filter(c=>c.kind===Kind.TEXT).map(c=>c.text);
  assert.ok(!texts.some(t=>t.includes('which is') || t.includes('after mod ')));
  assert.equal(action(run,0),1n); assert.equal(action(run,0),1n);
  assert.equal(info(run,1),BigInt(level), 'restart restores configured level');
  if (level === 1 && !right) {
    const asked = new TextDecoder().decode(Uint8Array.from({length: Number(info(run,4))}, (_,i) => Number(e.nw_api_v1_algebra_value(run,0n,BigInt(i)))));
    assert.equal(asked, '2 + 4', 'finishing does not consume a question seed');
  }
  e.nw_api_v1_destroy(oracle); e.nw_api_v1_destroy(run);
}
assert.ok(create(1,2,0)<0n); assert.ok(create(1,0,2)<0n);
console.log('Algebra options: adaptive level bounds, reset, hidden working and validation pass');
