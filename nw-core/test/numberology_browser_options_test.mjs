import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
const html=fs.readFileSync(new URL('../shells/web/index.html',import.meta.url),'utf8');
const source=html.slice(html.indexOf('function openNumberologyOptions('),html.indexOf('function drawNumberologyOptionsScreen('));
const store=new Map(); let screen='task', destroyed=0;
const context=vm.createContext({
  NUMBEROLOGY_TRIAL_OPTIONS:[1,2,3,5,6,8,10,15], NUMBEROLOGY_MAX_LEVEL:9223372036854775807n,
  NUMBEROLOGY_OPTIONS_STORAGE:'test', localStorage:{setItem:(k,v)=>store.set(k,v)},
  setScreen:v=>{screen=v;}, draw:()=>{}, destroyNumberologyRun:()=>destroyed++, BigInt, String,
});
vm.runInContext(`let numberologyOptions={level:'1',trials:6,adaptive:true};
let numberologyOptionsDraft=null, numberologyOptionsSelection=0, numberologyLevelEditing=false;
let numberologyLevelText='', numberologyOptionsReturnScreen=null;\n${source}`,context);
context.openNumberologyOptions('task');
for(const digit of '10000') context.editNumberologyLevel(digit);
assert.equal(vm.runInContext('numberologyOptionsDraft.level',context),'10000');
context.editNumberologyLevel('Backspace');
assert.equal(vm.runInContext('numberologyOptionsDraft.level',context),'1000');
context.modifyNumberologyOption(1);
assert.equal(vm.runInContext('numberologyOptionsDraft.level',context),'1001');
vm.runInContext('numberologyOptionsSelection=1',context); context.modifyNumberologyOption(1);
vm.runInContext('numberologyOptionsSelection=2',context); context.modifyNumberologyOption(1);
context.applyNumberologyOptions();
assert.equal(screen,'task'); assert.equal(destroyed,1);
assert.deepEqual(JSON.parse(store.get('test')),{level:'1001',trials:8,adaptive:false});
context.openNumberologyOptions('task'); context.modifyNumberologyOption(-1);
context.cancelNumberologyOptions();
assert.equal(destroyed,1); assert.equal(JSON.parse(store.get('test')).level,'1001');
context.openNumberologyOptions('taskhub');
for(const digit of '9223372036854775808') context.editNumberologyLevel(digit);
assert.equal(vm.runInContext('numberologyOptionsDraft.level',context),'922337203685477580');
console.log('Numberology browser options: unbounded level entry, safe i64 bound, apply and cancel pass');
