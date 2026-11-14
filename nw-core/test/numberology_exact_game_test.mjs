import assert from 'node:assert/strict';
import fs from 'node:fs';
import {fileURLToPath} from 'node:url';
import {instantiateElisa} from '../shells/web/elisa-wasm-runtime.js';
import {decode,Kind} from '../shells/web/display-list.js';
const wasm=process.env.NWCORE_WASM_PATH ?? fileURLToPath(new URL('../build/nwcore.wasm',import.meta.url));
const cases=JSON.parse(fs.readFileSync(new URL('./numberology_exact_oracle.json',import.meta.url)));
const {exports:e,instance}=await instantiateElisa(fs.readFileSync(wasm),{warn:false});
const task=BigInt(e.nw_api_v1_task_numberology()), frame=Number(e.nw_frame_alloc(1048576n));
let sequence=0n;
const action=(r,c,v=0)=>e.nw_api_v1_dispatch(r,1n,10n,sequence++,BigInt(c),BigInt(v),0n,0n,0n,0n,0n);
const info=(r,f)=>e.nw_api_v1_numberology_info(r,BigInt(f));
const value=(r,f,i)=>e.nw_api_v1_numberology_value(r,BigInt(f),BigInt(i));
const text=(r,f,n)=>new TextDecoder().decode(Uint8Array.from({length:Number(n)},(_,i)=>Number(value(r,f,i))));
for (const example of cases) {
  const run=e.nw_api_v1_create(task,1n,BigInt(example.level),1n,0n,0n,0n,0n,BigInt(example.seed));
  assert.ok(run>0n);
  assert.equal(action(run,0),1n,`start level ${example.level}`);
  assert.equal(info(run,4),BigInt(example.terms.length));
  const numeric=BigInt(example.answer);
  assert.equal(info(run,17), numeric >= -(1n<<63n) && numeric <= (1n<<63n)-1n ? 1n : 0n,
    'legacy scalar fit flag identifies values requiring exact text');
  assert.equal(text(run,0,info(run,14)),example.terms.join('\n')+'\n',`terms level ${example.level}`);
  assert.equal(info(run,15),0n); assert.equal(value(run,2,0),-1n);
  const digits=example.answer === '0' ? '-000' : example.answer.startsWith('-') ? '-000'+example.answer.slice(1) : '000'+example.answer;
  for (const character of digits) assert.equal(action(run,1,character.charCodeAt(0)),1n);
  assert.equal(info(run,20), digits.startsWith('-') ? 1n : 0n);
  assert.equal(info(run,18), numeric >= -(1n<<63n) && numeric <= (1n<<63n)-1n ? 1n : 0n);
  assert.equal(action(run,3),1n);
  assert.equal(info(run,8),1n,`exact answer level ${example.level}`);
  assert.equal(text(run,2,info(run,15)),example.answer);
  const n=Number(e.nw_api_v1_render(run,BigInt(frame),1048576n,0n,912n,684n));
  assert.ok(n>0);
  const labels=decode(new Uint8Array(instance.exports.memory.buffer,frame,n).slice()).filter(c=>c.kind===Kind.TEXT).map(c=>c.text);
  assert.ok(labels.includes(example.rule), `rule level ${example.level}`);
  assert.equal(e.nw_api_v1_destroy(run),0n);
}
const high = cases.find(c => c.level === 1000);
let warmedBytes = 0;
for (let attempt=0; attempt<8; attempt++) {
  const run=e.nw_api_v1_create(task,1n,1000n,1n,0n,0n,0n,0n,19n);
  assert.ok(run>0n); assert.equal(action(run,0),1n);
  const wrong=high.answer.slice(0,-1)+(high.answer.endsWith('1') ? '2' : '1');
  for (const character of wrong) assert.equal(action(run,1,character.charCodeAt(0)),1n);
  assert.equal(action(run,3),1n); assert.equal(info(run,8),0n, 'large incorrect answer is rejected');
  assert.equal(text(run,2,info(run,15)),high.answer);
  assert.equal(e.nw_api_v1_destroy(run),0n);
  if (attempt === 0) warmedBytes = instance.exports.memory.buffer.byteLength;
  else assert.ok(instance.exports.memory.buffer.byteLength <= warmedBytes + 4194304,
    'repeated exact runs do not retain generation arenas');
}
const impossible=e.nw_api_v1_create(task,1n,9223372036854775807n,1n,0n,0n,0n,0n,19n);
assert.ok(impossible>0n); assert.equal(action(impossible,0),1n);
assert.equal(info(impossible,0),3n); assert.equal(info(impossible,19),1n, 'oversized generation fails explicitly');
assert.equal(e.nw_api_v1_destroy(impossible),0n);
const invalid=e.nw_api_v1_create(task,1n,1n,1n,0n,0n,0n,0n,19n);
assert.equal(action(invalid,0),1n); assert.equal(action(invalid,1,45),1n);
assert.equal(action(invalid,3),1n); assert.equal(info(invalid,8),0n, 'a lone minus is judged wrong');
assert.equal(e.nw_api_v1_destroy(invalid),0n);
console.log(`Numberology exact controller: ${cases.length} source cases, including 1,341-digit answers, match and grade`);
