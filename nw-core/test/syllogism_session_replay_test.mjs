import assert from 'node:assert/strict';
import fs from 'node:fs';
import {instantiateElisa} from '../shells/web/elisa-wasm-runtime.js';
import {decode,Kind} from '../shells/web/display-list.js';

const wasm=process.env.NWCORE_WASM_PATH ?? new URL('../build/nwcore.wasm',import.meta.url);
const cases=JSON.parse(fs.readFileSync(new URL('./syllogism_session_oracle.json',import.meta.url)));
const {exports:e,instance}=await instantiateElisa(fs.readFileSync(wasm),{warn:false});
const task=e.nw_api_v1_task_syllogism(), frame=e.nw_frame_alloc(1048576n);
let sequence=0n;
const action=(run,code,value=0)=>e.nw_api_v1_dispatch(run,1n,10n,sequence++,BigInt(code),BigInt(value),0n,0n,0n,0n,0n);
const info=(run,field)=>e.nw_api_v1_syllogism_info(run,BigInt(field));
const labels=run=>{
  const n=Number(e.nw_api_v1_render(run,frame,1048576n,0n,912n,684n)); assert.ok(n>0);
  return decode(new Uint8Array(instance.exports.memory.buffer,Number(frame),n).slice())
    .filter(item=>item.kind===Kind.TEXT).map(item=>item.text);
};
const short={north:'N',south:'S',east:'E',west:'W',above:'up',below:'down'};
function displayed(option,count,index) {
  if(count<=9) return `${index+1}. ${option}`;
  if(count<=12) return option;
  return option.split(/\s+/).filter(word=>word!=='and').map(word=>short[word]??word).join(' ');
}
for(const example of cases) {
  const run=e.nw_api_v1_create(task,1n,BigInt(example.level),2n,0n,1n,0n,0n,BigInt(example.seed));
  assert.ok(run>0n); assert.equal(action(run,0),1n);
  for(const [trial,row] of example.rows.entries()) {
    assert.equal(info(run,0),1n); assert.equal(info(run,2),BigInt(trial+1));
    assert.equal(info(run,5),BigInt(row.options.length));
    assert.equal(e.nw_api_v1_syllogism_value(run,0n,0n),-1n);
    const asking=labels(run);
    assert.ok(asking.includes(row.lines.join('\n')),`level ${example.level} premises`);
    assert.ok(asking.includes(row.asked),`level ${example.level} question`);
    assert.ok(asking.some(text=>text.startsWith(`${row.grade}     question `)));
    row.options.forEach((option,index)=>assert.ok(asking.includes(displayed(option,row.options.length,index))));
    const chosen=trial===0 ? (row.answer+1)%row.options.length : row.answer;
    for(let i=0;i<chosen;i++) assert.equal(action(run,3),1n);
    assert.equal(action(run,1),1n);
    assert.equal(info(run,7),trial===0 ? 0n : 1n);
    assert.equal(e.nw_api_v1_syllogism_value(run,0n,0n),BigInt(row.answer));
    const judged=labels(run);
    assert.ok(judged.includes(row.working.join('\n')),`level ${example.level} working`);
    assert.ok(judged.includes(trial===0 ? `No — it was "${row.options[row.answer]}"` : 'Right'));
    assert.equal(action(run,0),1n);
  }
  assert.equal(info(run,0),3n);
  assert.ok(labels(run).includes(`1 of 2 right, highest level ${example.level}`));
  assert.equal(action(run,0),1n,'finished run can restart');
  assert.equal(info(run,0),1n);
  assert.equal(e.nw_api_v1_destroy(run),0n);
}
const madeUp=JSON.parse(fs.readFileSync(new URL('./syllogism_madeup_oracle.json',import.meta.url)));
for (const row of madeUp) {
  const run=e.nw_api_v1_create(task,1n,BigInt(row.level),1n,1n,1n,1n,0n,17n);
  assert.ok(run>0n); assert.equal(action(run,0),1n);
  assert.equal(info(run,10),0n); assert.equal(info(run,11),0n); assert.equal(info(run,12),0n);
  assert.ok(labels(run).includes(row.lines.join('\n')));
  assert.ok(labels(run).includes(row.asked));
  const wrong=(row.answer+1)%row.options.length;
  for(let i=0;i<wrong;i++) assert.equal(action(run,3),1n);
  assert.equal(action(run,1),1n); assert.equal(info(run,7),0n);
  assert.ok(labels(run).includes(row.lines.join('\n')), 'disabled working preserves premises');
  assert.equal(e.nw_api_v1_destroy(run),0n);
}
const keys=e.nw_api_v1_create(task,1n,1n,1n,0n,1n,0n,0n,17n);
assert.ok(keys>0n); assert.equal(action(keys,0),1n);
const keyCount=Number(info(keys,5));
assert.equal(action(keys,2),1n); assert.equal(info(keys,6),BigInt(keyCount-1),'left wraps');
assert.equal(action(keys,3),1n); assert.equal(info(keys,6),0n,'right wraps');
assert.equal(action(keys,6,keyCount),2n,'out-of-range option does nothing');
const keyAnswer=cases.find(item=>item.level===1).rows[0].answer;
assert.equal(action(keys,6,keyAnswer),1n); assert.equal(info(keys,7),1n,'direct selection submits');
assert.equal(e.nw_api_v1_destroy(keys),0n);
const space=e.nw_api_v1_create(task,1n,1n,1n,0n,1n,0n,0n,17n);
assert.ok(space>0n); assert.equal(action(space,0),1n);
assert.equal(e.nw_api_v1_dispatch(space,2n,10n,sequence++,1n,0n,0n,0n,0n,0n,0n),1n);
assert.equal(info(space,0),2n,'space submits while asking');
assert.equal(e.nw_api_v1_destroy(space),0n);
const adaptive=e.nw_api_v1_create(task,1n,1n,2n,0n,0n,0n,0n,17n);
assert.ok(adaptive>0n); assert.equal(action(adaptive,0),1n);
const first=cases.find(item=>item.level===1).rows[0];
for(let i=0;i<first.answer;i++) assert.equal(action(adaptive,3),1n);
assert.equal(action(adaptive,1),1n);
assert.equal(info(adaptive,7),1n); assert.equal(info(adaptive,1),2n);
assert.equal(info(adaptive,9),1n); assert.equal(info(adaptive,11),1n);
assert.equal(action(adaptive,0),1n);
const second=cases.find(item=>item.level===2).rows[1];
assert.ok(labels(adaptive).includes(second.asked),'adaptive question uses the next session seed');
const wrong=(second.answer+1)%second.options.length;
for(let i=0;i<wrong;i++) assert.equal(action(adaptive,3),1n);
assert.equal(action(adaptive,1),1n);
assert.equal(info(adaptive,7),0n); assert.equal(info(adaptive,1),1n);
assert.equal(action(adaptive,0),1n);
assert.ok(labels(adaptive).includes('1 of 2 right, highest level 1'));
assert.equal(e.nw_api_v1_destroy(adaptive),0n);
// Result history uses event timestamps, and a restarted run starts a new tally.
const timed=e.nw_api_v1_create(task,1n,1n,1n,0n,1n,0n,0n,17n);
const timedAction=(code,value,when)=>e.nw_api_v1_dispatch(timed,1n,BigInt(when),sequence++,BigInt(code),BigInt(value),0n,0n,0n,0n,0n);
assert.ok(timed>0n); assert.equal(timedAction(0,0,1000),1n);
assert.equal(timedAction(6,0,2750),1n);
assert.equal(info(timed,14),1n); assert.equal(info(timed,15),1n);
assert.equal(e.nw_api_v1_syllogism_value(timed,2n,0n),1n);
assert.equal(e.nw_api_v1_syllogism_value(timed,4n,0n),1750n);
assert.equal(e.nw_api_v1_syllogism_value(timed,2n,1n),-1n);
assert.equal(timedAction(0,0,3000),1n); assert.equal(info(timed,0),3n);
assert.equal(timedAction(0,0,4000),1n);
assert.equal(info(timed,14),0n); assert.equal(info(timed,15),0n);
assert.equal(e.nw_api_v1_syllogism_value(timed,2n,0n),-1n);
assert.equal(e.nw_api_v1_destroy(timed),0n);
console.log(`Syllogism source sessions: ${cases.length} levels, question seeds, working and scores match`);
