import assert from 'node:assert/strict';
import {createElisaRuntime} from '../shells/web/elisa-wasm-runtime.js';
const runtime = createElisaRuntime();
const memory = new WebAssembly.Memory({initial: 1});
runtime.attach({exports: {memory, __heap_base: 1024}});
const view = new DataView(memory.buffer);
const mask = (1n << 64n) - 1n;
const limbs = x => [BigInt.asIntN(64, x & mask), BigInt.asIntN(64, x >> 64n)];
const result = () => view.getBigUint64(32,true) | (view.getBigUint64(40,true) << 64n);
for (const [a,b] of [[(1n<<127n)+12345678901234567890n,(1n<<64n)+91n],
                      [(1n<<128n)-1n, 1000000000000000000n],
                      [0xfedcba9876543210abcdef1234567890n,0x123456789abcdef1n]]) {
  runtime.imports.env.__multi3(32,...limbs(a),...limbs(b));
  assert.equal(result(),BigInt.asUintN(128,a*b));
  runtime.imports.env.__udivti3(32,...limbs(a),...limbs(b));
  assert.equal(result(),a/b);
}
assert.throws(()=>runtime.imports.env.__udivti3(32,1n,0n,0n,0n),RangeError);
console.log('WASM 128-bit multiply and divide preserve full limb precision');
