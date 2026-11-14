import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import {fileURLToPath} from 'node:url';
import {instantiateElisa} from '../shells/web/elisa-wasm-runtime.js';
const root = fileURLToPath(new URL('..', import.meta.url));
const wasm = process.env.NWCORE_WASM_PATH ?? `${root}/build/nwcore.wasm`;
const {exports, instance} = await instantiateElisa(fs.readFileSync(wasm), {warn: false});
const html = fs.readFileSync(`${root}/shells/web/index.html`, 'utf8');
const source = html.slice(html.indexOf('function attachScrambleCorpus('), html.indexOf('function scrambleCorpusRequest('));
const context = vm.createContext({exports, instance, Number, BigInt, Uint8Array, Error,
  API_TASK: {scramble: BigInt(exports.nw_api_v1_task_scramble())},
  apiCreateRun: (task, options, seed) => exports.nw_api_v1_create(task, 1n, ...options, seed),
  apiDestroyRun: handle => exports.nw_api_v1_destroy(handle)});
vm.runInContext(`let scrambleRunHandle = 0n, scrambleCorpusVersion = 0, scrambleRunCorpusVersion = -1, scrambleCorpusBytes = null; ${source}`, context);
const encode = text => new TextEncoder().encode(text);
const valid = [encode('cat\t1\t\na\t2\t\n'), encode('a cat a cat a cat\n')];
context.installScrambleCorpus(valid);
assert.equal(vm.runInContext('scrambleCorpusVersion', context), 1);
assert.throws(() => context.installScrambleCorpus([encode('bad\n'), valid[1]]));
assert.equal(vm.runInContext('scrambleCorpusVersion', context), 1, 'rejected import does not replace saved bytes');
assert.equal(vm.runInContext('scrambleCorpusBytes[0].length', context), valid[0].length);
context.installScrambleCorpus([valid[0], new Uint8Array(0)]);
assert.equal(vm.runInContext('scrambleCorpusVersion', context), 2, 'index-only corpus is accepted');
context.installScrambleCorpus([new Uint8Array(0), valid[1]]);
assert.equal(vm.runInContext('scrambleCorpusVersion', context), 3, 'sentence-only corpus is accepted');
assert.throws(() => context.installScrambleCorpus([new Uint8Array(0), new Uint8Array(0)]));
console.log('scramble_browser_corpus_test: PASS (WASM validation and rejected replacement)');
