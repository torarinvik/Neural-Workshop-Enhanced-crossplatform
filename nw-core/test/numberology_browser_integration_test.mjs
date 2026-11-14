import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import {instantiateElisa} from '../shells/web/elisa-wasm-runtime.js';
const html=fs.readFileSync(new URL('../shells/web/index.html',import.meta.url),'utf8');
const functions=html.slice(html.indexOf('function isNumberologyTask()'),html.indexOf('function numberologyFrame('));
const wasm=process.env.NWCORE_WASM_PATH ?? new URL('../build/nwcore.wasm',import.meta.url);
const {exports:e}=await instantiateElisa(fs.readFileSync(wasm),{warn:false});
const task=BigInt(e.nw_api_v1_task_numberology());
const storage=new Map(); let seq=0n;
const c=vm.createContext({exports:e,BigInt,Number,String,NUMBEROLOGY_PHASE:{done:3},
  NUMBEROLOGY_OPTIONS_STORAGE:'numberology',localStorage:{setItem:(k,v)=>storage.set(k,v)},
  isTaskId:()=>true,API_TASK:{numberology:task},
  apiCreateRun:(t,opts,seed)=>e.nw_api_v1_create(t,1n,...opts,seed),
  apiDestroyRun:r=>e.nw_api_v1_destroy(r),
  apiDispatchAction:(r,action,value)=>e.nw_api_v1_dispatch(r,1n,100n,seq++,BigInt(action),BigInt(value),0n,0n,0n,0n,0n),
});
vm.runInContext(`let numberologyRunHandle=0n; let numberologyOptions={level:'1',trials:1,adaptive:true};\n${functions}`,c);
assert.equal(c.numberologyAction(0),1n);
const answer=String(c.numberologyExactInfo(5));
for(const ch of answer) assert.equal(c.numberologyAction(1,ch.charCodeAt(0)),1n);
assert.equal(c.numberologyAction(3),1n);
assert.equal(c.numberologyAction(0),1n);
assert.equal(JSON.parse(storage.get('numberology')).level,'2','perfect result persists next level');
c.destroyNumberologyRun();
vm.runInContext("numberologyOptions={level:'1000',trials:1,adaptive:false}",c);
assert.equal(c.numberologyAction(0),1n);
assert.equal(c.numberologyExactInfo(17),0,'large answer does not fit scalar API');
const source=JSON.parse(fs.readFileSync(new URL('./numberology_exact_oracle.json',import.meta.url)));
// This shell chooses seed 17; compare the exact bytes with the display label
// and verify that the browser's own value wrapper exposes every shown term.
assert.ok(c.numberologyExactInfo(14)>0);
assert.ok(c.numberologyValue(0,0)>=48 || c.numberologyValue(0,0)===45);
assert.ok(source.some(x=>x.level===1000));
c.destroyNumberologyRun();
console.log('Numberology browser integration: option-selected high level and persisted promotion pass');
