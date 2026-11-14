import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import {instantiateElisa} from '../shells/web/elisa-wasm-runtime.js';
import {upsertResultRecord, loadResultLedger} from '../shells/web/result-store.js';

const html = fs.readFileSync(new URL('../shells/web/index.html', import.meta.url), 'utf8');
const functions = html.slice(html.indexOf('function newNumberologySession()'), html.indexOf('function numberologyFrame('));
const wasm = process.env.NWCORE_WASM_PATH ?? new URL('../build/nwcore.wasm', import.meta.url);
const {exports: e} = await instantiateElisa(fs.readFileSync(wasm), {warn: false});
const task = BigInt(e.nw_api_v1_task_numberology());
const source = JSON.parse(fs.readFileSync(new URL('./numberology_session_oracle.json', import.meta.url)));
const answer = source.find(row => row.seed === 17 && row.level === 1).rows[0].answer;
const map = new Map(); let fail = false, seq = 0n;
const storage = {getItem: key => map.get(key) ?? null,
  setItem: (key, value) => {if (fail) throw new Error('storage unavailable'); map.set(key, value);}};
const c = vm.createContext({exports:e, BigInt, Number, String, NUMBEROLOGY_PHASE:{done:3},
  NUMBEROLOGY_OPTIONS_STORAGE:'options', localStorage:storage, isTaskId:()=>true,
  API_TASK:{numberology:task}, apiCreateRun:(t,opts,seed)=>e.nw_api_v1_create(t,1n,...opts,seed),
  apiDestroyRun:r=>e.nw_api_v1_destroy(r), upsertResultRecord:r=>upsertResultRecord(r,storage),
  apiDispatchAction:(r,action,value)=>e.nw_api_v1_dispatch(r,1n,100n,seq++,BigInt(action),BigInt(value),0n,0n,0n,0n,0n)});
vm.runInContext(`let numberologyRunHandle=0n, numberologyRunStats=null, numberologyFailedResults=[], numberologySessionSerial=0, resultStoreMessage='';
let numberologyOptions={level:'1',trials:1,adaptive:true};\n${functions}`, c);
assert.equal(c.numberologyAction(0),1n);
for (const ch of answer) assert.equal(c.numberologyAction(1,ch.charCodeAt(0)),1n);
fail = true;
assert.equal(c.numberologyAction(3),1n);
assert.equal(vm.runInContext('numberologyRunStats.persistence',c),'unavailable');
assert.equal(loadResultLedger(storage).ledger.records.length,0);
fail = false;
assert.equal(c.numberologyAction(0),1n);
let records = loadResultLedger(storage).ledger.records;
assert.equal(records.length,1);
assert.equal(records[0].task,'numberology');
assert.equal(records[0].completed,true);
assert.equal(records[0].right,1);
assert.deepEqual(records[0].results.map(row=>[row.trial,row.level,row.correct]),[[1,'1',true]]);
assert.equal(c.numberologyAction(3),2n);
assert.equal(loadResultLedger(storage).ledger.records.length,1,'ignored actions do not duplicate a result');
assert.equal(c.numberologyAction(0),1n, 'restart opens a separate session');
assert.equal(c.numberologyAction(1,45),1n);
assert.equal(c.numberologyAction(3),1n);
records = loadResultLedger(storage).ledger.records;
assert.equal(records.length,2);
assert.equal(records[1].completed,false, 'a judged trial is saved before session completion');
assert.equal(records[1].results[0].correct,false);
assert.equal(records[1].results[0].level,'2');
c.destroyNumberologyRun();
assert.equal(loadResultLedger(storage).ledger.records.length,2,'results survive disposal');
vm.runInContext("numberologyOptions={level:'1',trials:1,adaptive:false}",c);
assert.equal(c.numberologyAction(0),1n);
for (const ch of answer) c.numberologyAction(1,ch.charCodeAt(0));
fail = true;
assert.equal(c.numberologyAction(3),1n);
assert.equal(c.numberologyAction(0),1n);
assert.equal(c.numberologyAction(0),1n);
assert.equal(vm.runInContext('numberologyFailedResults.length',c),1,'failed prior session survives restart');
fail = false;
assert.equal(c.numberologyAction(1,45),1n);
assert.equal(vm.runInContext('numberologyFailedResults.length',c),0);
assert.equal(loadResultLedger(storage).ledger.records.length,3,'prior session is retried after restart');
c.destroyNumberologyRun();

console.log('Numberology browser results: failed write retry, single record, completion and disposal pass');
