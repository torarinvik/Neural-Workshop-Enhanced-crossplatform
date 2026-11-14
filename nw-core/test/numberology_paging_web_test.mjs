import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
const html=fs.readFileSync(new URL('../shells/web/index.html',import.meta.url),'utf8');
const code=html.slice(html.indexOf('function numberologyPageAt('),html.indexOf('function newNumberologySession('));
const context=vm.createContext({NUMBEROLOGY_ACTION:{previousPage:4,nextPage:5}});
vm.runInContext(code,context);
assert.equal(context.numberologyPageAt(265,365),4);
assert.equal(context.numberologyPageAt(647,365),5);
assert.equal(context.numberologyPageAt(456,365),0);
assert.equal(context.numberologyPageAt(265,400),0);
assert.match(html,/const page = numberologyPageAt\(point\.x, point\.y\)/);
const clickStart=html.indexOf('  if (isNumberologyTask()) {',html.indexOf('function taskClick(event)'));
const clickEnd=html.indexOf('  if (isHanoiTask()) {',clickStart);
assert.ok(clickStart>=0 && clickEnd>clickStart);
const block=html.slice(clickStart,clickEnd);
let phase=1, pages=2, calls=[], draws=0;
Object.assign(context,{isNumberologyTask:()=>true,numberologyInfo:()=>phase,
  NUMBEROLOGY_INFO:{phase:0},NUMBEROLOGY_PHASE:{working:1,judged:2},
  referencePointFromEvent:event=>event,numberologyExactInfo:()=>pages,
  numberologyAction:action=>calls.push(action),draw:()=>draws++});
context.NUMBEROLOGY_ACTION.start=0;
vm.runInContext(`function click(event) { ${block} }`,context);
context.click({x:647,y:365});
phase=2; context.click({x:265,y:365});
assert.deepEqual(calls,[5,4]);
assert.equal(draws,2);
pages=1; context.click({x:265,y:365});
assert.deepEqual(calls,[5,4,0], 'single-page judged click advances normally');
console.log('Numberology browser paging targets pass');
