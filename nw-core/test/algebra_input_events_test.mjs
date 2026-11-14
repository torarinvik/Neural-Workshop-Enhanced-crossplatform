import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import {fileURLToPath} from 'node:url';

const html = fs.readFileSync(fileURLToPath(new URL('../shells/web/index.html', import.meta.url)), 'utf8');
const source = html.slice(html.indexOf('let algebraComposing = false;'), html.indexOf('function algebraFrame('));
const listeners = {}, sent = [], timers = [];
let phase = 1, active = true, draws = 0;
const input = {value: '', disabled: true, focus() { this.focused = true; },
  addEventListener(name, callback) { listeners[name] = callback; }};
const context = vm.createContext({algebraTextInput: input, screen: 'task',
  isAlgebraTask: () => active, algebraInfo: () => phase, ensureAlgebraRun: () => 1n,
  apiDispatchText: (_handle, text) => sent.push(text), draw: () => draws++,
  setTimeout: callback => timers.push(callback)});
vm.runInContext(source, context);
context.focusAlgebraText();
assert.equal(input.disabled, false);
assert.ok(input.focused);
input.value = '12/7 + x';
listeners.input({isComposing: false});
assert.equal(sent.join(''), '12/7 + x');
listeners.compositionstart();
input.value = 'on';
listeners.input({isComposing: true});
assert.equal(sent.join(''), '12/7 + x', 'intermediate composition is not submitted');
listeners.compositionend();
listeners.input({isComposing: false});
for (const callback of timers.splice(0)) callback();
assert.equal(sent.join(''), '12/7 + xon', 'commit is sent once when final input follows compositionend');
listeners.compositionstart();
input.value = 'ce';
listeners.compositionend();
for (const callback of timers.splice(0)) callback();
assert.equal(sent.join(''), '12/7 + xonce', 'commit is sent when no final input follows');
phase = 2;
input.value = 'ignored';
listeners.input({isComposing: false});
assert.equal(sent.join(''), '12/7 + xonce');
assert.equal(input.value, '');
assert.equal(draws, 3);
console.log('algebra_input_events_test: PASS (paste, composition ordering, phase isolation)');
