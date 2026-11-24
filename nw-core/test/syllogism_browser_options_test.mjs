import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
const html=fs.readFileSync(new URL('../shells/web/index.html',import.meta.url),'utf8');
const options=html.slice(html.indexOf('function openSyllogismOptions('),html.indexOf('function openAlgebraOptions('));
const read=html.slice(html.indexOf('function readSyllogismOptions('),html.indexOf('function readAlgebraOptions('));
const controller=html.slice(html.indexOf('function isSyllogismTask()'),html.indexOf('function syllogismInfo('));
let screen='task', destroyed=0, created;
const storage=new Map();
const context=vm.createContext({SYLLOGISM_OPTIONS_STORAGE:'options',SYLLOGISM_LEVEL_OPTIONS:[1,2,3,4,5,6,7,8,9,10,11,12],
  SYLLOGISM_TRIAL_OPTIONS:[1,2,3,5,6,8,10,15], localStorage:{getItem:k=>storage.get(k)??null,setItem:(k,v)=>storage.set(k,v)},
  referencePointFromEvent:event=>event,setScreen:value=>{screen=value;},draw:()=>{},
  isTaskId:()=>true, API_TASK:{syllogism:1n}, apiCreateRun:(...args)=>{created=args;return 44n;}, apiDestroyRun:()=>destroyed++,upsertResultRecord:()=>({ok:true}),BigInt});
vm.runInContext(`let syllogismOptionsDraft=null,syllogismOptionsReturnScreen=null,syllogismOptionsSelection=0,syllogismRunHandle=0n,syllogismRunStats=null,syllogismFailedResults=[],syllogismSessionSerial=0,resultStoreMessage="";\n${read}\n${options}\n${controller}`,context);
assert.deepEqual(JSON.parse(JSON.stringify(vm.runInContext('syllogismOptions',context))),
  {level:3,trials:6,showWorking:true,adaptive:true,realWords:true});
context.openSyllogismOptions('task');
context.modifySyllogismOption(1);
for(let row=1;row<5;row++) {vm.runInContext(`syllogismOptionsSelection=${row}`,context);context.modifySyllogismOption(1);}
context.applySyllogismOptions();
assert.equal(screen,'task');
assert.deepEqual(JSON.parse(storage.get('options')),{level:4,trials:8,showWorking:false,adaptive:false,realWords:false});
context.ensureSyllogismRun();
assert.deepEqual(Array.from(created[1]),[4n,8n,1n,1n,1n,0n]);
context.openSyllogismOptions('task');
context.modifySyllogismOption(1); context.cancelSyllogismOptions();
assert.equal(destroyed,0,'cancel keeps an active run');
context.openSyllogismOptions('task'); context.applySyllogismOptions();
assert.equal(destroyed,1,'apply resets the active run');
assert.equal(context.syllogismOptionRowFromEvent({x:300,y:282}),4);
assert.equal(context.syllogismOptionRowFromEvent({x:265,y:113}),-2);
assert.equal(context.syllogismOptionRowFromEvent({x:647,y:113}),-3);
storage.set('options',JSON.stringify({level:99,trials:4,showWorking:'yes',adaptive:null,realWords:false}));
assert.deepEqual(JSON.parse(JSON.stringify(context.readSyllogismOptions())),
  {level:3,trials:6,showWorking:true,adaptive:true,realWords:false});
const click=html.slice(html.indexOf('function taskClick(event)'),html.indexOf('function marbleReferenceTransform()'));
const primary=html.slice(html.indexOf('function taskPrimary()'),html.indexOf('function taskClick(event)'));
let phase=1, actions=[];
Object.assign(context,{syllogismInfo:()=>phase,syllogismAction:action=>actions.push(action),draw:()=>{}});
vm.runInContext(`${primary}\n${click}`,context);
context.taskClick({}); assert.deepEqual(actions,[],'pointer does not answer an asking question');
phase=2; context.taskClick({}); assert.deepEqual(actions,[0],'pointer advances judged question');
phase=1; context.taskPrimary(); assert.deepEqual(actions,[0,1],'primary control submits asking question');
phase=3; context.taskPrimary(); assert.deepEqual(actions,[0,1,0],'primary control restarts a completed session');
console.log('Syllogism browser options: defaults, validation, persistence, apply, cancel and all controls pass');
