import assert from "node:assert/strict";
import fs from "node:fs";
import { decode, Kind } from "../shells/web/display-list.js";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { TASK_IDS_BY_CATEGORY } from "../shells/web/task-registry.js";

const bytes = fs.readFileSync(process.env.NWCORE_WASM_PATH ?? new URL("../build/nwcore.wasm", import.meta.url));
const runtime = await instantiateElisa(bytes, { warn: false });
const { exports: api } = runtime;
const task = api.nw_api_v1_task_shadow_play();
const capacity = 1048576n;
const pointer = api.nw_frame_alloc(capacity);
const read = length => new Uint8Array(api.memory.buffer, Number(pointer), Number(length));
const text = length => new TextDecoder().decode(read(length));
const render = run => decode(read(api.nw_api_v1_render(run, pointer, capacity, 0n, 912n, 684n)));
const create = rung => api.nw_api_v1_create(task, 1n, rung, 1n, 1n, 0n, 0n, 0n, 17n);
assert.equal(task, 2286122724n);
assert.equal(api.nw_api_v1_supports(task, 1n), 1n);
assert.equal(create(12n), -3n);

try {
  const category = TASK_IDS_BY_CATEGORY[3];
  const card = category.indexOf("shadow_play");
  assert.equal(category[card - 1], "tuner");
  const hub = decode(read(api.nw_taskhub_write(pointer, capacity, 3n, BigInt(card), 0n, 912n, 684n)));
  assert.equal(hub.filter(command => command.text === "Shadow Play").length, 1);
  assert.match(text(api.nw_shadow_play_options_note(pointer, capacity, 30n)), /Floor shadow too.*outline turns.*lamp swings/);

  const run = create(1n);
  assert.ok(run > 0n);
  const info = field => api.nw_api_v1_shadow_play_info(run, BigInt(field));
  const advance = (time, held = 0n) => api.nw_shadow_play_advance(run, time, held);
  try {
    assert.ok(render(run).some(command => command.text === "Press Space or Enter to start"));
    assert.equal(api.nw_api_v1_dispatch(run, 2n, 0n, 0n, 2n, 0n, 0n, 0n, 0n, 0n, 0n), 1n);
    assert.equal(advance(0.05, 64n), -6n);
    assert.ok(render(run).some(command => command.kind === Kind.POLYGON));
    // Python seed 17 starts 1.556 radians right of its target at rung one.
    assert.equal(advance(0.05, 1n), 1n);
    assert.equal(api.nw_shadow_play_drag(run, -125.3, 0, 0n), 1n);
    for (let frame = 2; frame <= 15 && info(0) === 1n; frame++) {
      assert.equal(advance(frame * 0.05), 1n);
      if (frame === 8) {
        const length = api.nw_shadow_play_audio(run, pointer, capacity);
        assert.ok(length > 0n && read(length).some(value => value !== 0));
        // One read is capped at 8192 frames. Drain the remainder before checking for duplicates.
        assert.ok(api.nw_shadow_play_audio(run, pointer, capacity) > 0n);
        assert.equal(api.nw_shadow_play_audio(run, pointer, capacity), 0n);
      }
    }
    assert.equal(info(0), 2n);
    assert.ok(render(run).some(command => command.text === "The shadow fits" && command.color === 0x40ff40ff));
    assert.equal(advance(3.5), 1n);
    assert.equal(info(0), 3n);
  } finally {
    assert.equal(api.nw_api_v1_destroy(run), 0n);
    assert.equal(api.nw_shadow_play_audio(run, pointer, capacity), -1n);
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
const agent = runtime.createShadowPlayEnvironment(context, { seed: 17, rung: 1, trials: 1, frameHz: 20 });
try {
  assert.equal(agent.n_actions, 6);
  assert.equal(agent.step()[0].outcome, undefined);
  let audible = false;
  let receipt;
  for (let frame = 0; frame < 30; frame++) {
    receipt = agent.act(0);
    assert.ok(receipt.ok);
    const observation = agent.advance();
    if (observation.audio_pcm) audible ||= observation.audio_pcm.some(value => value !== 0);
    assert.equal(observation.outcome, undefined);
  }
  assert.ok(audible);
  let judged;
  for (let frame = 0; frame < 20 && !judged?.outcome; frame++) judged = agent.advance();
  assert.equal(judged.outcome.scalar, 1);
  assert.ok(judged.outcome.receipt_id > receipt.receipt_id);
  assert.ok(agent.verify(judged.outcome, judged));
  assert.equal(agent.step()[2], true);
} finally {
  agent.close();
}
console.log("PASS: Shadow Play hub, held and drag rotation, stereo audio, and verified clocked agent verdict");
