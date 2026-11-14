import assert from 'node:assert/strict';
import fs from 'node:fs';
import {instantiateElisa} from '../shells/web/elisa-wasm-runtime.js';
import {decode,Kind} from '../shells/web/display-list.js';

const wasm=process.env.NWCORE_WASM_PATH ?? new URL('../build/nwcore.wasm',import.meta.url);
const {exports:e,instance}=await instantiateElisa(fs.readFileSync(wasm),{warn:false});
const task=e.nw_api_v1_task_syllogism(), frame=e.nw_frame_alloc(1048576n);
let sequence=0n, wrongCases=0;
const action=(run,code)=>e.nw_api_v1_dispatch(run,1n,10n,sequence++,BigInt(code),0n,0n,0n,0n,0n,0n);
function selected(run) {
  const n=Number(e.nw_api_v1_render(run,frame,1048576n,0n,912n,684n));
  assert.ok(n>0);
  const blue=decode(new Uint8Array(instance.exports.memory.buffer,Number(frame),n).slice())
    .filter(cmd=>cmd.kind===Kind.TEXT && cmd.color===0x0072b2ff).map(cmd=>cmd.text);
  assert.equal(blue.length,1,'exactly one option is selected');
  return blue[0];
}
for (let choice=0; choice<2; choice++) {
  const run=e.nw_api_v1_create(task,1n,1n,1n,0n,0n,0n,0n,17n);
  assert.ok(run>0n); assert.equal(action(run,0),1n);
  assert.equal(e.nw_api_v1_syllogism_value(run,0n,0n),-1n,'answer hidden while asking');
  assert.ok(e.nw_api_v1_syllogism_info(run,5n)>=2n);
  if (choice) assert.equal(action(run,3),1n);
  const before=selected(run);
  assert.equal(action(run,1),1n);
  const answer=Number(e.nw_api_v1_syllogism_value(run,0n,0n));
  assert.ok(answer>=0);
  if (answer!==choice) wrongCases++;
  assert.equal(selected(run),before,'judged screen retains the submitted selection');
  assert.equal(e.nw_api_v1_destroy(run),0n);
}
assert.ok(wrongCases>=1,'at least one replay submits an incorrect choice');
console.log('Syllogism feedback: answer hidden and submitted choice remains selected');
