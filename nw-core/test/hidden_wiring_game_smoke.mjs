import assert from "node:assert/strict";
import fs from "node:fs";
import { fileURLToPath } from "node:url";
import { decode, Kind } from "../shells/web/display-list.js";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";

const wasm = process.env.NWCORE_WASM_PATH ??
  fileURLToPath(new URL("../build/nwcore.wasm", import.meta.url));
const { exports: api, instance } = await instantiateElisa(fs.readFileSync(wasm), { warn: false });
const task = api.nw_api_v1_task_hidden_wiring();
assert.equal(task, 462267443n);
const create = (rung, rounds) => api.nw_api_v1_create(task, 1n, rung, rounds, 1n, 0n, 0n, 0n, 17n);
assert.equal(create(2n, 1n), -3n);
assert.equal(create(1n, 2n), -3n);
const capacity = 65536n;
const buffer = api.nw_frame_alloc(capacity);
for (const [rung, par, answers] of [[1n, 4, [0, 2]], [20n, 18, [29, 12, 92, 93, 28]]]) {
  const run = create(rung, 1n);
  assert.ok(run > 0n);
  let time = 100n;
  let sequence = 0n;
  const event = (kind, code, x = 0n, y = 0n) =>
    api.nw_api_v1_dispatch(run, kind, time++, sequence++, code, 0n, 0n, 0n, x, y, 0n);
  const info = field => api.nw_api_v1_hidden_wiring_info(run, BigInt(field));
  const text = () => {
    const length = api.nw_api_v1_render(run, buffer, capacity, 0n, 912n, 684n);
    assert.ok(length > 0n);
    return decode(new Uint8Array(instance.exports.memory.buffer, Number(buffer), Number(length)))
      .filter(command => command.kind === Kind.TEXT).map(command => command.text);
  };
  assert.equal(event(5n, 0n, 500000n, 500000n), 1n);
  assert.deepEqual([info(0), info(1), info(2)], [1n, rung, 1n]);
  assert.ok(text().includes(`Learn the wiring for ${par} or less`));
  assert.equal(event(1n, 8n), 1n);
  assert.equal(info(4), 1n);
  assert.equal(event(1n, 9n), 1n);
  let setting = 0;
  for (const want of answers) {
    for (let bit = 0; bit < 8; bit++) {
      if (((setting ^ want) >> bit) & 1) assert.equal(event(2n, BigInt(12 + bit)), 1n);
    }
    setting = want;
    assert.equal(event(2n, 2n), 1n);
  }
  assert.deepEqual([info(0), info(6), info(7)], [3n, 0n, 1n]);
  assert.ok(text().some(line => line.startsWith("A = ")));
  const deadline = info(9);
  assert.equal(api.nw_api_v1_advance(run, deadline - 1n, 0n, sequence++), 2n);
  assert.equal(api.nw_api_v1_advance(run, deadline, 0n, sequence++), 1n);
  assert.ok(text().includes(`1 of 1 under par   highest rung passed ${rung}`));
  assert.equal(api.nw_api_v1_destroy(run), 0n);
}
api.nw_frame_free(buffer);
console.log("Hidden Wiring WASM replay: PASS");
