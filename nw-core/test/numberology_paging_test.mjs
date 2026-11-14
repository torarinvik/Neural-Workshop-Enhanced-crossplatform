import assert from 'node:assert/strict';
import fs from 'node:fs';
import {instantiateElisa} from '../shells/web/elisa-wasm-runtime.js';
import {decode, Kind} from '../shells/web/display-list.js';

const wasm = process.env.NWCORE_WASM_PATH ?? new URL('../build/nwcore.wasm', import.meta.url);
const {exports:e, instance} = await instantiateElisa(fs.readFileSync(wasm), {warn:false});
const task = BigInt(e.nw_api_v1_task_numberology());
const frame = e.nw_frame_alloc(1048576n);
let sequence = 0n;
const action = (run, code, value=0) => e.nw_api_v1_dispatch(run,1n,10n,sequence++,BigInt(code),BigInt(value),0n,0n,0n,0n,0n);
const info = (run, field) => e.nw_api_v1_numberology_info(run, BigInt(field));
const fixture = JSON.parse(fs.readFileSync(new URL('./numberology_exact_oracle.json', import.meta.url))).find(item=>item.level===1000);
const run = e.nw_api_v1_create(task,1n,1000n,1n,0n,0n,0n,0n,19n);
assert.ok(run>0n); assert.equal(action(run,0),1n);
const raw = fixture.terms.join('\n')+'\n';
const pages = Math.ceil(raw.length / 48);
assert.ok(pages > 1); assert.equal(info(run,22),BigInt(pages));
assert.equal(action(run,4),2n, 'previous page stops at start');
let reconstructed = '';
for (let page=0; page<pages; page++) {
  assert.equal(info(run,21),BigInt(page+1));
  const n = Number(e.nw_api_v1_render(run,frame,1048576n,0n,912n,684n));
  assert.ok(n > 0);
  const commands = decode(new Uint8Array(instance.exports.memory.buffer,Number(frame),n).slice());
  const labels = commands.filter(item=>item.kind===Kind.TEXT);
  assert.ok(labels.some(item=>item.text===`Sequence page ${page+1}/${pages}`));
  const line = labels.find(item=>item.b===494 && item.d===1);
  assert.ok(line, 'sequence is visible');
  assert.ok(line.text.split('\n').every(part=>part.length<=40));
  reconstructed += line.text.replaceAll('\n','');
  if (page+1<pages) assert.equal(action(run,5),1n);
}
assert.equal(reconstructed, fixture.terms.join(',   ')+',   ?');
assert.equal(action(run,5),2n, 'next page stops at end');
assert.equal(action(run,4),1n);
assert.equal(info(run,21),BigInt(pages-1));
const typed = '1234567890'.repeat(8);
assert.equal(action(run,1,45),1n);
for (const digit of typed) assert.equal(action(run,1,digit.charCodeAt(0)),1n);
const length = Number(e.nw_api_v1_render(run,frame,1048576n,0n,912n,684n));
const entry = decode(new Uint8Array(instance.exports.memory.buffer,Number(frame),length).slice())
  .find(item=>item.kind===Kind.TEXT && item.b===215);
assert.equal(entry.text, '-...' + typed.slice(-36) + '_');
assert.equal(info(run,16),BigInt(typed.length), 'all digits remain in the exact input');
assert.equal(action(run,3),1n);
assert.equal(info(run,8),0n);
const answerPages = Math.ceil(fixture.answer.length / 48);
assert.equal(info(run,23),BigInt(pages));
assert.equal(info(run,24),BigInt(answerPages));
assert.equal(info(run,22),BigInt(pages+answerPages));
assert.equal(action(run,5),1n); // last sequence page
let shownAnswer = '';
for (let page=0; page<answerPages; page++) {
  assert.equal(action(run,5),1n);
  const n = Number(e.nw_api_v1_render(run,frame,1048576n,0n,912n,684n));
  const labels = decode(new Uint8Array(instance.exports.memory.buffer,Number(frame),n).slice())
    .filter(item=>item.kind===Kind.TEXT);
  assert.ok(labels.some(item=>item.text===`Answer page ${page+1}/${answerPages}`));
  assert.ok(labels.some(item=>item.text==='No — see answer pages'));
  assert.ok(labels.some(item=>item.text==='< Previous (Page Up)'));
  assert.ok(labels.some(item=>item.text==='Next (Page Down) >'));
  shownAnswer += labels.find(item=>item.b===494 && item.d===1).text.replaceAll('\n','');
}
assert.equal(shownAnswer,fixture.answer);
assert.equal(action(run,5),2n);

assert.equal(e.nw_api_v1_destroy(run),0n);
console.log('Numberology paging: full source sequence is readable across bounded pages');
