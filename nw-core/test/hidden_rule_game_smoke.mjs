import assert from "node:assert/strict";
import fs from "node:fs";
import { fileURLToPath } from "node:url";
import { decode, Kind } from "../shells/web/display-list.js";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";

const wasm = process.env.NWCORE_WASM_PATH ??
  fileURLToPath(new URL("../build/nwcore.wasm", import.meta.url));
const { exports: api, instance } = await instantiateElisa(fs.readFileSync(wasm), { warn: false });
const task = api.nw_api_v1_task_hidden_rule();
assert.equal(task, 189731380n);
const create = (rung, trials) => api.nw_api_v1_create(task, 1n, rung, trials, 1n, 0n, 0n, 0n, 17n);
assert.equal(create(5n, 1n), -3n);
assert.equal(create(1n, 2n), -3n);

const capacity = 65536n;
const buffer = api.nw_frame_alloc(capacity);
for (const [rung, par, answers] of [
  [1n, 1, [1, 0, 0, 0, 1, 1]],
  [19n, 21, [0, 0, 1, 0, 1, 0, 0, 1, 1, 1]],
]) {
  const run = create(rung, 1n);
  assert.ok(run > 0n);
  const info = field => api.nw_api_v1_hidden_rule_info(run, BigInt(field));
  const frame = () => {
    const length = api.nw_api_v1_render(run, buffer, capacity, 0n, 912n, 684n);
    assert.ok(length > 0n);
    return decode(new Uint8Array(instance.exports.memory.buffer, Number(buffer), Number(length)));
  };
  const text = () => frame().filter(command => command.kind === Kind.TEXT).map(command => command.text);
  let time = 100n;
  let sequence = 0n;
  const event = (kind, code, x = 0n, y = 0n) =>
    api.nw_api_v1_dispatch(run, kind, time++, sequence++, code, 0n, 0n, 0n, x, y, 0n);

  assert.equal(info(0), 0n);
  assert.equal(event(2n, 1n), 1n);
  assert.deepEqual([info(0), info(1), info(2)], [1n, rung, 1n]);
  assert.ok(text().includes(`Learn the rule for ${par} or less`));
  assert.ok(frame().some(command => command.kind === Kind.CIRCLE));
  // First row's second swatch, with the board in reference coordinates.
  const y = rung === 1n ? 519 : 544;
  assert.equal(event(5n, 0n, 224780n, BigInt(Math.round(y * 1e6 / 684))), 1n);
  assert.equal(event(1n, 6n), 1n);
  assert.equal(info(4), 1n);
  assert.equal(event(1n, 7n), 1n);
  assert.ok(text().includes(`question 1 of ${answers.length}`));
  for (const answer of answers) assert.equal(event(1n, answer ? 8n : 9n), 1n);
  assert.deepEqual([info(0), info(5), info(6), info(7)], [3n, BigInt(answers.length), 0n, 1n]);
  assert.ok(text().some(line => line.startsWith("The rule was:")));
  const deadline = info(9);
  assert.equal(api.nw_api_v1_advance(run, deadline - 1n, 0n, sequence++), 2n);
  assert.equal(api.nw_api_v1_advance(run, deadline, 0n, sequence++), 1n);
  assert.equal(info(0), 4n);
  assert.ok(text().includes(`1 of 1 under par   highest rung passed ${rung}`));
  assert.equal(api.nw_api_v1_destroy(run), 0n);
}
api.nw_frame_free(buffer);
console.log("Hidden Rule WASM replay: PASS");
