import assert from "node:assert/strict";
import fs from "node:fs";
import { decode, Kind } from "../shells/web/display-list.js";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { TASK_IDS_BY_CATEGORY } from "../shells/web/task-registry.js";

const bytes = fs.readFileSync(process.env.NWCORE_WASM_PATH ?? new URL("../build/nwcore.wasm", import.meta.url));
const runtime = await instantiateElisa(bytes, { warn: false });
const { exports: api } = runtime;
const task = api.nw_api_v1_task_tuner();
const capacity = 1048576n;
const pointer = api.nw_frame_alloc(capacity);
const read = length => new Uint8Array(api.memory.buffer, Number(pointer), Number(length));
assert.equal(task, 4284132915n);
assert.equal(api.nw_api_v1_supports(task, 1n), 1n);
assert.equal(api.nw_api_v1_create(task, 1n, 12n, 1n, 1n, 0n, 0n, 0n, 17n), -3n);

try {
  const category = TASK_IDS_BY_CATEGORY[3];
  const card = category.indexOf("tuner");
  assert.equal(category[card - 1], "time_it");
  const hub = decode(read(api.nw_taskhub_write(pointer, capacity, 3n, BigInt(card), 0n, 912n, 684n)));
  assert.equal(hub.filter(command => command.text === "Tuner").length, 1);
  const note = new TextDecoder().decode(read(api.nw_tuner_options_note(pointer, capacity, 30n)));
  assert.equal(note, "Rung 30: 9 stations.  The tune comes in another key.  Stations drift.");

  const run = api.nw_api_v1_create(task, 1n, 1n, 1n, 1n, 0n, 0n, 0n, 17n);
  assert.ok(run > 0n);
  const info = field => api.nw_api_v1_tuner_info(run, BigInt(field));
  const frame = () => decode(read(api.nw_api_v1_render(run, pointer, capacity, 1n, 912n, 684n)));
  let sequence = 0n;
  const action = (code, time) => api.nw_api_v1_dispatch(run, 1n, time, sequence++, code, 0n, 0n, 0n, 0n, 0n, 0n);
  const down = (x, y, time) => api.nw_api_v1_dispatch(run, 5n, time, sequence++, 0n, 0n, 0n, 0n,
    BigInt(Math.round(x / 912 * 1e6)), BigInt(Math.round(y / 684 * 1e6)), 0n);
  try {
    assert.ok(frame().some(command => command.text === "Press Space or Enter to start"));
    assert.equal(action(6n, 0n), 1n);
    assert.equal(action(4n, 0n), 2n);
    assert.equal(info(11), 0n);
    assert.equal(api.nw_tuner_advance(run, 0.1, 2n), 1n);
    assert.equal(info(5), 45509n);
    assert.equal(api.nw_tuner_advance(run, 0.2, 4n), 1n);
    assert.equal(info(5), 45109n);
    for (let time = 3; time <= 25; time++) {
      assert.equal(api.nw_tuner_advance(run, time / 10, 0n), 1n);
      const length = api.nw_tuner_audio(run, pointer, capacity);
      assert.ok(length > 0n);
      if (time === 6) assert.ok(read(length).some(value => value !== 0));
    }
    assert.equal(api.nw_tuner_audio(run, pointer, capacity), 0n);
    assert.equal(info(11), 1n);
    assert.ok(frame().some(command => command.kind === Kind.LINE && command.color === 0xc8281eff));
    const width = 389 * 1.9;
    const left = (912 - width) / 2;
    const dialY = 179 + 389 * 0.62 + 8;
    const dialX = left + width * (0.07 + 0.86 * 0.1681381804);
    assert.equal(down(dialX + 10, dialY, 2500n), 1n);
    assert.equal(api.nw_tuner_drag(run, dialX, dialY, -10, 0, 0n), 1n);
    assert.equal(info(5), 16814n);
    assert.equal(action(5n, 2500n), 1n);
    assert.equal(action(4n, 2500n), 1n);
    for (let time = 26; time <= 36; time++) api.nw_tuner_advance(run, time / 10, 0n);
    assert.equal(info(0), 2n);
    assert.ok(frame().some(command => command.text === "Locked on to the sound" && command.color === 0x40ff40ff));
    assert.equal(api.nw_tuner_advance(run, 6.5, 0n), 1n);
    assert.equal(info(0), 3n);
  } finally {
    assert.equal(api.nw_api_v1_destroy(run), 0n);
    assert.equal(api.nw_tuner_audio(run, pointer, capacity), -1n);
  }
} finally {
  api.nw_frame_free(pointer);
}

const canvas = { width: 320, height: 240 };
const pixels = new Uint8ClampedArray(canvas.width * canvas.height * 4);
const context = {
  canvas, save() {}, restore() {}, setTransform() {}, translate() {}, scale() {}, rotate() {},
  strokeRect() {}, fillRect() {}, beginPath() {}, arc() {}, fill() {}, stroke() {},
  moveTo() {}, lineTo() {}, closePath() {},
  clearRect() { pixels.fill(0); },
  fillText() {
    if (this.fillStyle === "rgba(64,255,64,1.000)") {
      pixels.set([64, 255, 64, 255], pixels.length - 4);
      pixels.set([64, 255, 64, 255], pixels.length - 4 - canvas.width * 4);
    }
  },
  getImageData() { return { data: pixels }; },
};
const agent = runtime.createTunerEnvironment(context, { seed: 17, rung: 1, trials: 1, frameHz: 20 });
try {
  assert.equal(agent.n_actions, 6);
  let audible = false;
  for (let frame = 0; frame < 24; frame++) {
    const observation = agent.step(0)[0];
    if (observation.audio_pcm) audible ||= observation.audio_pcm.some(value => value !== 0);
    assert.equal(observation.outcome, undefined);
  }
  for (let frame = 24; frame < 52; frame++) agent.step();
  assert.ok(audible);
  const receipt = agent.act(4);
  assert.ok(receipt.ok);
  let judged;
  for (let frame = 0; frame < 22; frame++) {
    const observation = agent.advance();
    if (observation.outcome) {
      judged = observation;
      break;
    }
  }
  assert.equal(judged?.outcome.scalar, 1);
  assert.ok(judged.outcome.receipt_id > receipt.receipt_id);
  assert.ok(agent.verify(judged.outcome, judged));
  assert.equal(agent.step()[2], true);
} finally {
  agent.close();
}
console.log("PASS: Tuner WebAssembly hub, settings, tuning, stereo audio, and receipt-linked verdict");
