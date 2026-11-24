import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import {instantiateElisa} from '../shells/web/elisa-wasm-runtime.js';
import {upsertResultRecord,loadResultLedger} from '../shells/web/result-store.js';

const html=fs.readFileSync(new URL('../shells/web/index.html',import.meta.url),'utf8');
const code=html.slice(html.indexOf('function isSyllogismTask()'),html.indexOf('function syllogismFrame('));
const wasm=process.env.NWCORE_WASM_PATH ?? new URL('../build/nwcore.wasm',import.meta.url);
const {exports:e}=await instantiateElisa(fs.readFileSync(wasm),{warn:false});
const task=BigInt(e.nw_api_v1_task_syllogism());
const cases=JSON.parse(fs.readFileSync(new URL('./syllogism_session_oracle.json',import.meta.url)));
const answer=cases.find(row=>row.level===1).rows[0].answer;
let seq=0n,now=1000n,fail=false;
const map=new Map();
const storage={getItem:key=>map.get(key)??null,setItem:(key,value)=>{if(fail)throw Error('unavailable');map.set(key,value);}};
const c=vm.createContext({exports:e,BigInt,Number,API_TASK:{syllogism:task},isTaskId:()=>true,
  apiCreateRun:(t,opts,seed)=>e.nw_api_v1_create(t,1n,...opts,seed),
  apiDestroyRun:r=>e.nw_api_v1_destroy(r),upsertResultRecord:r=>upsertResultRecord(r,storage),
  apiDispatchAction:(r,action,value)=>e.nw_api_v1_dispatch(r,1n,now,seq++,BigInt(action),BigInt(value),0n,0n,0n,0n,0n)});
vm.runInContext(`let syllogismRunHandle=0n,syllogismRunStats=null,syllogismFailedResults=[],syllogismSessionSerial=0,resultStoreMessage='';
let syllogismOptions={level:1,trials:1,showWorking:true,adaptive:false,realWords:true};\n${code}`,c);
assert.equal(c.syllogismAction(0),1n);
now=2750n;fail=true;
assert.equal(c.syllogismAction(6,answer),1n);
assert.equal(vm.runInContext('syllogismRunStats.persistence',c),'unavailable');
assert.equal(loadResultLedger(storage).ledger.records.length,0);
now=3000n;fail=false;
assert.equal(c.syllogismAction(0),1n);
let records=loadResultLedger(storage).ledger.records;
assert.equal(records.length,1);
assert.equal(records[0].completed,true);
assert.equal(records[0].right,1);
assert.equal(records[0].bestLevel,1);
assert.equal(records[0].seconds,1);
assert.deepEqual(records[0].results.map(row=>[row.trial,row.level,row.correct,row.elapsedMs]),[[1,1,true,1750]]);
assert.equal(c.syllogismAction(6,answer),2n);
assert.equal(loadResultLedger(storage).ledger.records.length,1);
now=4000n;assert.equal(c.syllogismAction(0),1n);
now=4200n;assert.equal(c.syllogismAction(6,(answer+1)%3),1n);
records=loadResultLedger(storage).ledger.records;
assert.equal(records.length,2);
assert.equal(records[1].completed,false);
assert.equal(records[1].results[0].correct,false);
c.destroySyllogismRun();
assert.equal(loadResultLedger(storage).ledger.records.length,2);
console.log('Syllogism browser results: real WASM controller retry, score and partial session pass');
