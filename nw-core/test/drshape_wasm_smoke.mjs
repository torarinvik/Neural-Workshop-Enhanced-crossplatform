import assert from "node:assert/strict";
import fs from "node:fs";
import { decode, Kind } from "../shells/web/display-list.js";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { TASK_IDS_BY_CATEGORY } from "../shells/web/task-registry.js";

const bytes = fs.readFileSync(process.env.NWCORE_WASM_PATH ?? new URL("../build/nwcore.wasm", import.meta.url));
const runtime = await instantiateElisa(bytes, { warn: false });
const { exports: api } = runtime;
const task = api.nw_api_v1_task_dr_shape();
const capacity = 1048576n;
const pointer = api.nw_frame_alloc(capacity);
const read = length => new Uint8Array(api.memory.buffer, Number(pointer), Number(length));
assert.equal(task, 2055552569n);
assert.equal(api.nw_api_v1_supports(task, 1n), 1n);
assert.equal(api.nw_api_v1_create(task, 1n, 12n, 1n, 1n, 0n, 0n, 0n, 17n), -3n);

try {
  const category = TASK_IDS_BY_CATEGORY[3];
  const card = category.indexOf("dr_shape");
  assert.deepEqual(category.slice(card - 1, card + 2), ["point_of_view", "dr_shape", "inside_or_out"]);
  const hub = decode(read(api.nw_taskhub_write(pointer, capacity, 3n, BigInt(card), 0n, 912n, 684n)));
  assert.equal(hub.filter(command => command.text === "Dr Shape").length, 1);
  const note = new TextDecoder().decode(read(api.nw_drshape_options_note(pointer, capacity, 30n)));
  assert.match(note, /^Rung 30: 6 candidates\. .*Some cards are sounds\..*Scenes\..*Sensory overload\.$/);

  const run = api.nw_api_v1_create(task, 1n, 1n, 1n, 1n, 0n, 0n, 0n, 17n);
  assert.ok(run > 0n);
  const info = field => api.nw_api_v1_drshape_info(run, BigInt(field));
  const frame = () => decode(read(api.nw_api_v1_render(run, pointer, capacity, 1n, 912n, 684n)));
  let sequence = 0n;
  const key = (code, time) => api.nw_api_v1_dispatch(run, 2n, time, sequence++, code, 0n, 0n, 0n, 0n, 0n, 0n);
  const advance = time => api.nw_api_v1_advance(run, time, 0n, sequence++);
  try {
    assert.ok(frame().some(command => command.text === "Press Space to start"));
    assert.equal(key(1n, 0n), 1n);
    assert.equal(key(12n, 0n), 2n);
    assert.equal(info(12), -1n);
    for (let time = 50n; time <= 7000n; time += 50n) {
      assert.equal(advance(time), 1n);
      if (time === 650n) {
        const length = api.nw_drshape_audio(run, pointer, capacity);
        assert.ok(length > 0n && read(length).some(value => value !== 0));
        assert.equal(api.nw_drshape_audio(run, pointer, capacity), 0n);
        assert.ok(frame().some(command => command.kind === Kind.POLYGON && command.len === 10));
      }
    }
    assert.ok(frame().some(command => command.text === "Which is the same shape?  1-3"));
    assert.equal(key(12n, 7000n), 1n);
    assert.equal(info(12), -1n);
    assert.equal(advance(7050n), 1n);
    assert.equal(info(12), 0n);
    assert.ok(frame().some(command => command.text === "Card 1 -- that is the one" && command.color === 0x40ff40ff));
    assert.equal(advance(9550n), 1n);
    assert.equal(info(0), 3n);
  } finally {
    assert.equal(api.nw_api_v1_destroy(run), 0n);
    assert.equal(api.nw_drshape_audio(run, pointer, capacity), -1n);
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
const agent = runtime.createDrShapeEnvironment(context, { seed: 17, rung: 1, trials: 1, frameHz: 20 });
try {
  assert.equal(agent.n_actions, 6);
  assert.equal(agent.step(0)[0].outcome, undefined);
  let audible = false;
  for (let frame = 1; frame < 142; frame++) {
    const observation = agent.step()[0];
    if (observation.audio_pcm) audible ||= observation.audio_pcm.some(value => value !== 0);
    assert.equal(observation.outcome, undefined);
  }
  assert.ok(audible);
  const receipt = agent.act(0);
  assert.ok(receipt.ok);
  const judged = agent.advance();
  assert.equal(judged.outcome.scalar, 1);
  assert.equal(judged.outcome.receipt_id, receipt.receipt_id);
  assert.ok(agent.verify(judged.outcome, judged));
  assert.equal(agent.step()[2], true);
} finally {
  agent.close();
}
console.log("PASS: Dr Shape browser hub, timed shape reveal, settings, stereo audio, and clocked agent verdict");
