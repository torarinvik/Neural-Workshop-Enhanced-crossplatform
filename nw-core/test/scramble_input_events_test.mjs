import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import {fileURLToPath} from 'node:url';

const html = fs.readFileSync(fileURLToPath(new URL('../shells/web/index.html', import.meta.url)), 'utf8');
const source = html.slice(html.indexOf('let scrambleComposing = false;'), html.indexOf('function isScrabbleTask()'));
const listeners = {}, sent = [], timers = [];
let phase = 1, active = true, draws = 0;
const input = {value: '', disabled: true, focus() { this.focused = true; },
  addEventListener(name, callback) { listeners[name] = callback; }};
const context = vm.createContext({scrambleTextInput: input, screen: 'task',
  isScrambleTask: () => active, scrambleInfo: () => phase, ensureScrambleRun: () => 1n,
  apiDispatchText: (_handle, text) => sent.push(text), draw: () => draws++,
  setTimeout: callback => timers.push(callback)});
vm.runInContext(source, context);
context.focusScrambleText();
assert.equal(input.disabled, false);
assert.ok(input.focused);
input.value = 'ordinary paste';
listeners.input({isComposing: false});
assert.equal(sent.join(''), 'ordinary paste');
listeners.compositionstart();
input.value = 'on';
listeners.input({isComposing: true});
assert.equal(sent.join(''), 'ordinary paste', 'intermediate composition is not submitted');
listeners.compositionend();
listeners.input({isComposing: false});
for (const callback of timers.splice(0)) callback();
assert.equal(sent.join(''), 'ordinary pasteon', 'commit is sent once when final input follows compositionend');
listeners.compositionstart();
input.value = 'ce';
listeners.compositionend();
for (const callback of timers.splice(0)) callback();
assert.equal(sent.join(''), 'ordinary pasteonce', 'commit is sent when no final input follows');
phase = 2;
input.value = 'ignored';
listeners.input({isComposing: false});
assert.equal(sent.join(''), 'ordinary pasteonce');
assert.equal(input.value, '');
assert.equal(draws, 3);
console.log('scramble_input_events_test: PASS (paste, composition ordering, phase isolation)');
