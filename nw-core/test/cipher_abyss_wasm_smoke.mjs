import assert from "node:assert/strict";
import fs from "node:fs";
import { decode } from "../shells/web/display-list.js";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { TASK_IDS_BY_CATEGORY } from "../shells/web/task-registry.js";

const artifact = fs.readFileSync(process.env.NWCORE_WASM_PATH ?? new URL("../build/nwcore.wasm", import.meta.url));
const { exports: api, createCipherAbyssEnvironment } = await instantiateElisa(artifact, { warn: false });
const task = api.nw_api_v1_task_cipher_abyss();
assert.equal(task, 1865539977n);
assert.equal(api.nw_api_v1_supports(task, 1n), 1n);
const position = TASK_IDS_BY_CATEGORY[4].indexOf("cipher_abyss");
assert.equal(position, 27);

const handle = api.nw_api_v1_create(task, 1n, 1n, 1n, 1n, 0n, 1n, 0n, 17n);
assert.ok(handle > 0n);
const capacity = 1048576n;
const pointer = api.nw_frame_alloc(capacity);
const info = field => Number(api.nw_api_v1_cipher_abyss_info(handle, BigInt(field)));
const decoder = new TextDecoder();
let sequence = 0n;
let now = 0n;

function view(length) {
  assert.ok(length > 0n && length <= capacity, String(length));
  return new Uint8Array(api.memory.buffer, Number(pointer), Number(length));
}
function frame() {
  return decode(view(api.nw_api_v1_render(handle, pointer, capacity, 1n, 912n, 684n)));
}
function record(kind) {
  return decoder.decode(view(api.nw_cipher_abyss_record(handle, BigInt(kind), pointer, capacity)));
}
function dispatch(kind, code = 0, x = 0, y = 0) {
  return api.nw_api_v1_dispatch(handle, BigInt(kind), now, sequence++, BigInt(code), 0n, 0n, 0n,
    BigInt(Math.round(x * 1e6 / 912)), BigInt(Math.round(y * 1e6 / 684)), 0n);
}
function tick(dt) {
  now += BigInt(dt);
  assert.ok(api.nw_api_v1_advance(handle, now, BigInt(dt), sequence++) > 0n);
}

try {
  const menu = decode(view(api.nw_taskhub_write(pointer, capacity, 4n, BigInt(position), 0n, 912n, 684n)));
  assert.ok(menu.some(command => command.text === "The Cipher Abyss"));
  const note = decoder.decode(view(api.nw_cipher_abyss_options_note(pointer, capacity, 1n)));
  assert.equal(note, "Rung 1 (patterns): 2 symbols, rows of 3, 8 experiments.");
  assert.ok(frame().some(command => command.text === "Press Space or click to start"));
  assert.equal(api.nw_cipher_abyss_record(handle, 0n, pointer, capacity), 0n);
  assert.equal(api.nw_cipher_abyss_options_apply(handle, 1n, 1n, 1n), 1n);
  assert.equal(dispatch(2, 2), 1n);
  assert.equal(info(0), 1);
  assert.ok(frame().some(command => command.text === "1. click symbols to build an input"));

  const scale = 389 / 640;
  const symbolX = (912 - 1000 * scale) / 2 + 122 * scale;
  const symbolY = 179 + 62 * scale;
  assert.equal(dispatch(5, 0, symbolX, symbolY), 1n);
  assert.equal(dispatch(6, 0, symbolX, symbolY), 1n);
  assert.equal(dispatch(2, 12), 1n);
  assert.equal(dispatch(2, 13), 1n);
  assert.equal(dispatch(2, 2), 1n);
  assert.equal(info(11), 1);
  const state = view(api.nw_api_v1_read_state(handle, pointer, capacity));
  const fields = new DataView(state.buffer, state.byteOffset, state.byteLength);
  assert.equal(fields.getUint32(0, true), 0x3152574e);
  assert.equal(fields.getBigInt64(16 + 11 * 8, true), 1n);
  assert.equal(record(0), "# The Cipher Abyss, rung 1 (patterns)\n# symbols 0-1; input -> output\n 1  1 0 1 -> 1 1 0\n");
  assert.ok(view(api.nw_cipher_abyss_audio_window(handle, 0, 0.1, pointer, capacity)).some(byte => byte !== 0));

  assert.equal(dispatch(2, 89), 1n);
  assert.ok(frame().some(command => command.text === "TEST 1 of 2: what does it give for"));
  // Seed 17 gives if(same,shift(1),rot(1)) in the Python version.
  for (const code of [12, 12, 13, 2]) assert.equal(dispatch(2, code), 1n);
  assert.ok(frame().some(command => command.text === "TEST 2 of 2: what does it give for"));
  for (const code of [12, 12, 12, 2]) assert.equal(dispatch(2, code), 1n);
  tick(50);
  assert.equal(info(0), 2);
  assert.equal(info(8), 1);
  assert.equal(info(1), 2);
  const metrics = JSON.parse(record(1));
  assert.equal(metrics.rung, 1);
  assert.equal(metrics.experiments, 1);
  assert.equal(metrics.reference_experiments, 3);
  assert.deepEqual(metrics.bits, [2.874]);
  assert.equal(metrics.accuracy, 1);
  assert.equal(metrics.won, true);
  assert.match(record(0), /test 0 1 0 -> 0 0 1  right\ntest 1 1 1 -> 0 0 0  right\n# the machine: if\(same,shift\(1\),rot\(1\)\)\n$/);
  const feedback = frame();
  assert.ok(feedback.some(command => command.text === "CRACKED"));
  assert.ok(feedback.some(command => command.text === "Cracked it." && command.color === 0x40ff40ff));
  tick(8999);
  assert.equal(info(0), 2);
  tick(1);
  assert.equal(info(0), 3);
  assert.ok(frame().some(command => command.text === "1 of 1 cracked"));
  assert.equal(dispatch(2, 1), 1n);
  assert.ok(!frame().some(command => command.text === "1. click symbols to build an input"));
} finally {
  assert.equal(api.nw_api_v1_destroy(handle), 0n);
  api.nw_frame_free(pointer);
}

// A version-one Python save can contribute a lower-rung operator to feedback.
const recall = api.nw_api_v1_create(task, 1n, 4n, 1n, 0n, 0n, 0n, 0n, 17n);
assert.ok(recall > 0n);
const recallPointer = api.nw_frame_alloc(capacity);
try {
  const load = text => {
    const bytes = new TextEncoder().encode(text);
    new Uint8Array(api.memory.buffer, Number(recallPointer), bytes.length).set(bytes);
    return api.nw_cipher_abyss_load_library(recall, recallPointer, BigInt(bytes.length));
  };
  const library = '{"version":1,"operators":{"rev":2,"prefix":7}}';
  assert.equal(load(library), 1n);
  assert.ok(load('{"operators":') < 0n);
  const act = port => assert.equal(api.nw_cipher_abyss_agent_event(recall, 0, BigInt(port)), 1n);
  act(37);
  assert.equal(load(library), 2n);
  act(24);
  for (const port of [14, 14, 14, 14, 23, -1]) act(port);
  const length = api.nw_api_v1_render(recall, recallPointer, capacity, 1n, 912n, 684n);
  const recalled = decode(new Uint8Array(api.memory.buffer, Number(recallPointer), Number(length)));
  assert.ok(recalled.some(command => command.text === "You met rev at rung 2"));
  const persisted = api.nw_cipher_abyss_record(recall, 2n, recallPointer, capacity);
  assert.deepEqual(JSON.parse(decoder.decode(
    new Uint8Array(api.memory.buffer, Number(recallPointer), Number(persisted)))), JSON.parse(library));
} finally {
  assert.equal(api.nw_api_v1_destroy(recall), 0n);
  api.nw_frame_free(recallPointer);
}

// Python seed 1 at rung 19 deals a second machine with a different rule.
const twins = api.nw_api_v1_create(task, 1n, 19n, 1n, 0n, 1n, 0n, 0n, 1n);
assert.ok(twins > 0n);
const twinPointer = api.nw_frame_alloc(capacity);
try {
  const act = port => assert.equal(api.nw_cipher_abyss_agent_event(twins, 0, BigInt(port)), 1n);
  const enter = row => {
    for (const symbol of row) act(14 + symbol);
    act(23);
  };
  act(37);
  assert.equal(api.nw_api_v1_cipher_abyss_info(twins, 10n), 1n);
  act(24);
  for (const answer of [[1, 1, 1, 2, 3, 3], [3, 2, 0, 0, 0, 2], [1, 2, 0, 0, 0, 0]]) enter(answer);
  const length = api.nw_api_v1_render(twins, twinPointer, capacity, 1n, 912n, 684n);
  const twinFrame = decode(new Uint8Array(api.memory.buffer, Number(twinPointer), Number(length)));
  assert.ok(twinFrame.some(command => command.text === "A SECOND MACHINE:"));
  enter([0, 0, 0, 1, 2, 2]);
  act(-1);
  assert.equal(api.nw_api_v1_cipher_abyss_info(twins, 8n), 3n);
} finally {
  assert.equal(api.nw_api_v1_destroy(twins), 0n);
  api.nw_frame_free(twinPointer);
}

const canvas = { width: 228, height: 171 };
const context = {
  canvas,
  save() {}, restore() {}, setTransform() {}, translate() {}, scale() {}, rotate() {},
  strokeRect() {}, beginPath() {}, arc() {}, fill() {}, stroke() {}, moveTo() {}, lineTo() {}, closePath() {},
  clearRect() {}, fillRect() {}, fillText() {},
  getImageData: () => ({ data: new Uint8ClampedArray(canvas.width * canvas.height * 4) }),
};
const environment = createCipherAbyssEnvironment(context, { seed: 17, rung: 1, trials: 1, frameHz: 20 });
try {
  assert.equal(environment.n_actions, 37);
  assert.ok(environment.act(14).ok);
  assert.equal(environment.advance().done, false);
} finally {
  environment.close();
}
console.log("Cipher Abyss WASM menu, settings, tutorial, input, PCM, round records, operator recall, twin machines, feedback, and stepped environment passed");
