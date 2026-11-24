import assert from "node:assert/strict";
import fs from "node:fs";
import { decode, Kind } from "../shells/web/display-list.js";
import { TASK_IDS_BY_CATEGORY } from "../shells/web/task-registry.js";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";

const bytes = fs.readFileSync(process.env.NWCORE_WASM_PATH ?? new URL("../build/nwcore.wasm", import.meta.url));
const { exports: api, createShapeFromMotionEnvironment } = await instantiateElisa(bytes, { warn: false });
const task = api.nw_api_v1_task_shape_from_motion();
const capacity = 65536n;
const pointer = api.nw_frame_alloc(capacity);
const bytesAt = size => new Uint8Array(api.memory.buffer, Number(pointer), Number(size));
const dotPositions = frame => frame.filter(command => command.kind === Kind.RECT && command.color === 0xeceef2ff)
  .map(({ a, b, c }) => [a, b, c]);
assert.equal(task, 464666890n);
assert.equal(api.nw_api_v1_supports(task, 1n), 1n);
assert.equal(api.nw_api_v1_create(task, 1n, 13n, 1n, 0n, 0n, 0n, 0n, 17n), -3n);

try {
  const category = TASK_IDS_BY_CATEGORY[3];
  const card = category.indexOf("shape_from_motion");
  assert.deepEqual(category.slice(card - 1, card + 2), ["which_is_nearer", "shape_from_motion", "point_of_view"]);
  const hub = decode(bytesAt(api.nw_taskhub_write(pointer, capacity, 3n, BigInt(card), 0n, 912n, 684n)));
  assert.equal(hub.filter(command => command.text === "Shape from Motion").length, 1);

  const noteSize = api.nw_sfm_options_note(pointer, capacity, 25n);
  assert.equal(new TextDecoder().decode(bytesAt(noteSize)),
    "Rung 25: 50 dots, 6 choices.  Each dot lives 0.25 s.  60% noise.  A third ask which way it turns.  Wrong choices look alike.");

  const run = api.nw_api_v1_create(task, 1n, 12n, 1n, 1n, 0n, 0n, 0n, 17n);
  assert.ok(run > 0n);
  const info = field => Number(api.nw_sfm_info(run, BigInt(field)));
  const frame = () => decode(bytesAt(api.nw_api_v1_render(run, pointer, capacity, 1n, 912n, 684n)));
  let sequence = 0n;
  const key = (code, time) => api.nw_api_v1_dispatch(run, 2n, time, sequence++, code, 0n, 0n, 0n, 0n, 0n, 0n);
  const advance = time => api.nw_api_v1_advance(run, time, 0n, sequence++);
  try {
    assert.ok(frame().some(command => command.text === "Press Space or click to start"));
    assert.equal(key(1n, 0n), 1n);
    assert.equal(info(8), -1);
    const first = frame();
    const dots = dotPositions(first);
    assert.equal(dots.length, 300);
    assert.equal(advance(400n), 1n);
    const moving = frame();
    assert.notDeepEqual(dotPositions(moving), dots);

    const target = moving.find(command => command.text === "4  Ring");
    assert.ok(target);
    const coord = (point, extent) => BigInt(Math.round(point * 1e6 / extent));
    assert.equal(api.nw_api_v1_dispatch(run, 5n, 400n, sequence++, 0n, 0n, 0n, 0n,
      coord(target.a, 912), coord(target.b, 684), 0n), 1n);
    assert.equal(info(5), 1);
    assert.equal(info(8), 3);
    const judged = frame();
    assert.deepEqual(dotPositions(judged), dotPositions(moving));
    assert.ok(judged.some(command => command.text === "Right: a ring"));
    assert.equal(advance(2899n), 2n);
    assert.deepEqual(frame(), judged);
    assert.equal(advance(2900n), 1n);
    assert.equal(info(0), 3);
    assert.ok(frame().some(command => command.text === "1 of 1 passed   highest rung passed 12"));
  } finally {
    assert.equal(api.nw_api_v1_destroy(run), 0n);
  }
} finally {
  api.nw_frame_free(pointer);
}

const canvas = { width: 912, height: 684 };
const pixels = new Uint8ClampedArray(canvas.width * canvas.height * 4);
const context = {
  canvas,
  save() {}, restore() {}, setTransform() {}, translate() {}, scale() {}, rotate() {},
  strokeRect() {}, beginPath() {}, arc() {}, fill() {}, stroke() {}, moveTo() {}, lineTo() {}, closePath() {},
  clearRect() { pixels.fill(0); },
  fillRect(x, y) {
    if (this.fillStyle === "rgba(236,238,242,1.000)") {
      const index = (Math.round(x) + Math.round(y) * canvas.width) * 4;
      if (index >= 0 && index <= pixels.length - 4) pixels.set([236, 238, 242, 255], index);
    }
  },
  fillText() {
    if (this.fillStyle === "rgba(64,255,64,1.000)") {
      pixels.set([64, 255, 64, 255], pixels.length - 4);
      pixels.set([64, 255, 64, 255], pixels.length - 4 - canvas.width * 4);
    }
  },
  getImageData() { return { data: pixels }; },
};

const env = createShapeFromMotionEnvironment(context, { seed: 17, rung: 1, trials: 1, frameHz: 20 });
try {
  assert.equal(env.n_actions, 6);
  assert.equal(env.step(5)[0].outcome, undefined);
  const receipt = env.act(0);
  assert.ok(receipt.ok);
  assert.equal(env.act(1).ok, false);
  const judged = env.advance();
  assert.equal(judged.outcome.scalar, 1);
  assert.equal(judged.outcome.receipt_id, receipt.receipt_id);
  assert.ok(env.verify(judged.outcome, judged));
  assert.equal(env.step()[2], true);
} finally {
  env.close();
}
console.log("PASS: Shape from Motion hub, settings preview, animation, pointer verdict, and stepped receipt verification");
