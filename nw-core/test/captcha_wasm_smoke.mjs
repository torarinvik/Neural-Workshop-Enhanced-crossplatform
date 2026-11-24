import assert from "node:assert/strict";
import fs from "node:fs";
import { decode, Kind, render } from "../shells/web/display-list.js";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { TASK_IDS_BY_CATEGORY } from "../shells/web/task-registry.js";

const bytes = fs.readFileSync(process.env.NWCORE_WASM_PATH ?? new URL("../build/nwcore.wasm", import.meta.url));
const { exports: api } = await instantiateElisa(bytes, { warn: false });
const task = api.nw_api_v1_task_captcha();
const capacity = 1048576n;
const pointer = api.nw_frame_alloc(capacity);
const read = length => new Uint8Array(api.memory.buffer, Number(pointer), Number(length));
const frame = run => decode(read(api.nw_api_v1_render(run, pointer, capacity, 0n, 912n, 684n)));
const create = rung => api.nw_api_v1_create(task, 1n, rung, 1n, 1n, 0n, 0n, 0n, 17n);
assert.equal(task, 1314221109n);
assert.equal(api.nw_api_v1_supports(task, 1n), 1n);
assert.equal(create(12n), -3n);

try {
  const category = TASK_IDS_BY_CATEGORY[3];
  const card = category.indexOf("captcha");
  assert.equal(category[card - 1], "shadow_play");
  const hub = decode(read(api.nw_taskhub_write(pointer, capacity, 3n, BigInt(card), 0n, 912n, 684n)));
  assert.equal(hub.filter(command => command.text === "Captcha").length, 1);
  assert.equal(new TextDecoder().decode(read(api.nw_captcha_options_note(pointer, capacity, 30n))),
    "Rung 30: 8 characters.  6 decoys.  Clutter.");

  const run = create(30n);
  assert.ok(run > 0n);
  let sequence = 0n;
  const dispatch = (kind, action, time) => api.nw_api_v1_dispatch(run, BigInt(kind),
    BigInt(time), sequence++, BigInt(action), 0n, 0n, 0n, 500000n, 500000n, 0n);
  const info = field => api.nw_api_v1_captcha_info(run, BigInt(field));
  try {
    assert.ok(frame(run).some(command => command.text === "Press Space or click to start"));
    assert.equal(dispatch(5, 0, 0), 1n);
    assert.equal(info(0), 1n);
    const activeFrame = frame(run);
    assert.ok(activeFrame.some(command => command.text === "Type only the black characters, but not the small ones"));
    const faced = activeFrame.filter(command => command.kind === Kind.TEXT && command.f > 0);
    assert.equal(faced.length, 174);
    assert.ok(faced.some(command => Math.abs(command.e) > 90));
    assert.ok(new Set(faced.map(command => command.f)).size > 3);
    assert.ok(activeFrame.some(command => command.kind === Kind.MULTILINE));

    const rotated = faced.find(command => command.f === 16 && command.e !== 0);
    const rotations = [], painted = [];
    const ctx = {
      save() {}, restore() {}, setTransform() {}, clearRect() {}, translate() {}, scale() {},
      rotate(value) { rotations.push(value); },
      fillText(text) { painted.push([text, this.font]); },
    };
    render(ctx, [rotated], { width: 912, height: 684 });
    assert.deepEqual(rotations, [rotated.e * Math.PI / 180]);
    assert.match(painted[0][1], /"Verdana", Arial/);
    assert.equal(painted[0][0], rotated.text);

    const alphabet = "ACDEFGHJKMNPQRTUVWXY347";
    assert.equal(dispatch(1, 0, 100), 1n);
    assert.equal(dispatch(2, 25, 110), 1n);
    assert.equal(info(4), 0n);
    for (const letter of "NUJWHT7N") assert.equal(dispatch(1, alphabet.indexOf(letter), 120), 1n);
    assert.equal(dispatch(2, 2, 150), 1n);
    assert.equal(info(0), 2n);
    assert.equal(info(5), 1n);
    assert.ok(frame(run).some(command => command.text === "Right: NUJWHT7N" && command.color === 0x40ff40ff));
    assert.equal(api.nw_api_v1_advance(run, 2649n, 0n, sequence++), 2n);
    assert.equal(api.nw_api_v1_advance(run, 2650n, 0n, sequence++), 1n);
    assert.equal(info(0), 3n);
  } finally {
    assert.equal(api.nw_api_v1_destroy(run), 0n);
  }

  const timed = create(4n);
  try {
    assert.ok(timed > 0n);
    assert.equal(api.nw_captcha_think_configure(timed, 0.05, 0), 1n);
    assert.equal(api.nw_api_v1_dispatch(timed, 1n, 0n, 0n, 25n, 0n, 0n, 0n, 0n, 0n, 0n), 1n);
    assert.equal(api.nw_captcha_step(timed, 0.05), 1n);
    assert.equal(api.nw_api_v1_captcha_info(timed, 0n), 4n);
    assert.equal(api.nw_api_v1_captcha_info(timed, 1n), 4n);
    assert.equal(api.nw_api_v1_captcha_info(timed, 9n), 1n);
    const visible = frame(timed).filter(command => command.kind === Kind.TEXT).map(command => command.text);
    assert.ok(visible.includes("Out of time"));
    assert.ok(!visible.some(text => text.startsWith("It said ")));
    assert.equal(api.nw_captcha_step(timed, 0.05), 1n);
    assert.ok(frame(timed).some(command => command.text === "0 of 0 passed   highest rung passed 0"));
  } finally {
    assert.equal(api.nw_api_v1_destroy(timed), 0n);
  }
} finally {
  api.nw_frame_free(pointer);
}
console.log("PASS: Captcha WASM hub, dense scene, typefaces, typing, feedback, and cleanup");

const canvas = { width: 320, height: 240 };
const pixels = new Uint8ClampedArray(canvas.width * canvas.height * 4);
const context = {
  canvas,
  save() {}, restore() {}, setTransform() {}, translate() {}, scale() {}, rotate() {},
  fillRect() {}, strokeRect() {}, beginPath() {}, arc() {}, fill() {}, stroke() {},
  moveTo() {}, lineTo() {}, closePath() {},
  clearRect() { pixels.fill(0); },
  fillText() {
    const color = this.fillStyle === "rgba(64,255,64,1.000)" ? [64, 255, 64, 255]
      : this.fillStyle === "rgba(255,64,64,1.000)" ? [255, 64, 64, 255] : null;
    if (color) {
      pixels.set(color, pixels.length - 4);
      pixels.set(color, pixels.length - 4 - canvas.width * 4);
    }
  },
  getImageData() { return { data: pixels }; },
};
const runtime = await instantiateElisa(bytes, { warn: false });
const alphabet = "ACDEFGHJKMNPQRTUVWXY347";
const agent = runtime.createCaptchaEnvironment(context, { seed: 17, trials: 1, frameHz: 20, thinkSeconds: 0.25 });
try {
  assert.equal(agent.n_actions, 25);
  assert.equal(agent.step(0)[0].outcome, undefined);
  assert.equal(agent.step(23)[0].outcome, undefined);
  // Reset clears both the entry and the think bank.
  agent.reset(17);
  for (const char of "MNUJ") assert.equal(agent.step(alphabet.indexOf(char))[0].outcome, undefined);
  assert.ok(agent.think_left < 0.051);
  const receipt = agent.act(24);
  assert.ok(receipt.ok);
  assert.equal(agent.act(0).ok, false);
  const judged = agent.advance();
  assert.equal(judged.outcome.scalar, 1);
  assert.equal(judged.outcome.receipt_id, receipt.receipt_id);
  assert.ok(agent.verify(judged.outcome, judged));
  assert.equal(agent.forfeits, 0);
  assert.equal(agent.step()[2], true);
} finally {
  agent.close();
}

const clock = runtime.createCaptchaEnvironment(context, {
  seed: 17, trials: 2, frameHz: 20, thinkSeconds: 0.1, refillSeconds: 0.05,
});
try {
  assert.equal(clock.step(0)[0].outcome, undefined);
  const flag = clock.step()[0];
  assert.equal(flag.outcome.scalar, -1);
  assert.ok(clock.verify(flag.outcome, flag));
  assert.equal(clock.forfeits, 1);
  assert.equal(clock.step()[2], false);
  assert.equal(clock.think_left, 0.05);
  assert.equal(clock.step()[0].outcome.scalar, -1);
  assert.equal(clock.step()[2], true);
  assert.equal(clock.forfeits, 2);
} finally {
  clock.close();
}
console.log("PASS: Captcha stepped WASM typing receipts, deadline, refill, forfeits, and verified outcomes");
