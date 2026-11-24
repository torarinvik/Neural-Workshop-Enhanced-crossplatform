import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import {upsertResultRecord, loadResultLedger} from '../shells/web/result-store.js';

const html=fs.readFileSync(new URL('../shells/web/index.html',import.meta.url),'utf8');
const code=html.slice(html.indexOf('function isSyllogismTask()'),html.indexOf('function syllogismFrame('));
let phase=0, count=0, fail=false;
const values=new Map();
const storage={getItem:key=>values.get(key)??null,setItem:(key,value)=>{if(fail)throw Error('unavailable');values.set(key,value);}};
const e={nw_api_v1_syllogism_info:(_h,field)=>BigInt(({0:phase,8:1,9:3,14:2,15:count})[Number(field)]??0),
  nw_api_v1_syllogism_value:(_h,field)=>BigInt(({2:3,3:1,4:2500})[Number(field)]??-1)};
const c=vm.createContext({exports:e,BigInt,Number,API_TASK:{syllogism:1n},isTaskId:()=>true,
  apiCreateRun:()=>1n,apiDestroyRun:()=>0n,upsertResultRecord:record=>upsertResultRecord(record,storage),
  apiDispatchAction:(_h,action)=>{if(action===0 && (phase===0||phase===3)){phase=1;count=0;return 1n;}
    if(action===6 && phase===1){phase=2;count++;return 1n;}
    if(action===0 && phase===2){phase=3;return 1n;}return 2n;}});
vm.runInContext(`let syllogismRunHandle=0n,syllogismRunStats=null,syllogismFailedResults=[],syllogismSessionSerial=0,resultStoreMessage='';
let syllogismOptions={level:3,trials:1,showWorking:true,adaptive:true,realWords:true};\n${code}`,c);
assert.equal(c.syllogismAction(0),1n);
fail=true;
assert.equal(c.syllogismAction(6,0),1n);
assert.equal(vm.runInContext('syllogismRunStats.persistence',c),'unavailable');
assert.equal(loadResultLedger(storage).ledger.records.length,0);
fail=false;
assert.equal(c.syllogismAction(0),1n);
let records=loadResultLedger(storage).ledger.records;
assert.equal(records.length,1);
assert.equal(records[0].task,'syllogism');
assert.equal(records[0].completed,true);
assert.equal(records[0].right,1);
assert.deepEqual(records[0].results.map(row=>[row.trial,row.level,row.correct,row.elapsedMs]),[[1,3,true,2500]]);
assert.equal(c.syllogismAction(6,0),2n);
assert.equal(loadResultLedger(storage).ledger.records.length,1);
assert.equal(c.syllogismAction(0),1n);
fail=true; c.syllogismAction(6,0); c.syllogismAction(0); c.syllogismAction(0);
assert.equal(vm.runInContext('syllogismFailedResults.length',c),1);
fail=false; c.syllogismAction(6,0);
records=loadResultLedger(storage).ledger.records;
assert.equal(records.length,3);
c.destroySyllogismRun();
assert.equal(loadResultLedger(storage).ledger.records.length,3);
console.log('Syllogism browser results: retries, unique sessions, completion and disposal pass');
