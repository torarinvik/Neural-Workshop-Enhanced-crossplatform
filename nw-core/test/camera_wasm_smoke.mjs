import assert from "node:assert/strict";
import fs from "node:fs";

import { CameraRenderer, decodeCameraMesh } from "../shells/web/camera-renderer.js";
import { decode, Kind } from "../shells/web/display-list.js";
import { TASK_IDS_BY_CATEGORY } from "../shells/web/task-registry.js";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";

const { exports: api } = await instantiateElisa(
  fs.readFileSync(process.env.NWCORE_WASM_PATH ?? new URL("../build/nwcore.wasm", import.meta.url)),
  { warn: false },
);
const task = api.nw_api_v1_task_camera();
assert.equal(task, 2663290958n);
assert.equal(api.nw_api_v1_supports(task, 1n), 1n);
const create = (rung, trials) => api.nw_api_v1_create(task, 1n, rung, trials, 1n, 0n, 0n, 0n, 17n);
assert.equal(create(7n, 3n), -3n);
assert.equal(create(8n, 2n), -3n);
const run = create(8n, 1n);
assert.ok(run > 0n);
const capacity = 131072n;
const buffer = api.nw_frame_alloc(capacity);
assert.ok(buffer > 0n);
const bytes = length => {
  assert.ok(length >= 0n, `unexpected WASM status ${length}`);
  return new Uint8Array(api.memory.buffer, Number(buffer), Number(length));
};
// Reuse the same caller-owned buffer for the frame and each lazily loaded
// mesh, as the browser renderer does. Decoded frame fields must outlive
// those writes, even when the runtime grows WASM memory.
const receiver = {
  render(frame, readMesh) {
    for (const kind of new Set(frame.draws.map(draw => draw.mesh))) {
      assert.ok(decodeCameraMesh(readMesh(kind, frame.field), kind).indices.length);
    }
    return frame;
  },
};
const frame = () => CameraRenderer.prototype.renderRun.call(receiver, api, run, buffer, capacity, 881, 641);
const perception = TASK_IDS_BY_CATEGORY[3];
assert.deepEqual(perception.slice(1, 6), ["mr_time", "camera", "what_next", "will_it_fall", "same_or_mirror"]);
const hub = decode(bytes(api.nw_taskhub_write(buffer, capacity, 3n, 2n, 0n, 912n, 684n)));
assert.equal(hub.filter(command => command.kind === Kind.TEXT && command.text === "Camera").length, 1);
const note = (rung, adaptive) => new TextDecoder().decode(bytes(api.nw_camera_options_note(buffer, capacity, rung, adaptive)));
assert.equal(note(1n, 1n), "Rung 1: within 3 m and 30 degrees, 4 objects.  A meter shows how close you are.  A match climbs a rung, a miss drops one; the ladder has no top.");
assert.equal(note(100n, 0n), "Rung 100: within 2.3e-11 mm and 4.8e-11 degrees, 260 objects.");
const chrome = (handle = run) => decode(bytes(api.nw_camera_chrome(handle, buffer, capacity, 1n, 881n, 641n)));
const hasText = (commands, text) => commands.some(command => command.kind === Kind.TEXT && command.text === text);
const info = field => api.nw_camera_info(run, BigInt(field));
let sequence = 0n;
let now = 0n;
const event = (kind, action = 0n, value = 0n, aux = 0n) =>
  api.nw_api_v1_dispatch(run, kind, now, sequence++, action, value, 0n, 0n, 0n, 0n, aux);
const action = (code, value = 0n, aux = 0n) => event(1n, code, value, aux);
const advance = time => {
  const elapsed = time - now;
  now = time;
  return api.nw_api_v1_advance(run, now, elapsed, sequence++);
};

try {
  assert.equal(info(0), 0n);
  assert.equal(frame(), null);
  assert.ok(hasText(chrome(), "Press Space to start"));
  assert.equal(action(31n), 1n);
  assert.equal(info(0), 1n);
  const initial = frame();
  assert.equal(initial.passes.length, 2);
  const searching = chrome();
  assert.ok(hasText(searching, "Stand where the photo was taken"));
  assert.ok(hasText(searching, "rung 8  photo 1/1  within 30.1 cm, 4.4°"));
  const photo = initial.passes[1];
  const border = searching.find(command => command.kind === Kind.BOX);
  assert.deepEqual([border.a, border.b, border.c, border.d, border.e],
    [photo.x - 3, photo.y - 3, photo.width + 6, photo.height + 6, 3]);
  assert.equal(api.nw_camera_frame(run, buffer, 8n, 881n, 641n), -8n);
  assert.equal(api.nw_camera_mesh(buffer, capacity, 8n, initial.field), -3n);
  for (let kind = 0; kind < 8; kind++) {
    const mesh = decodeCameraMesh(bytes(api.nw_camera_mesh(buffer, capacity, BigInt(kind), initial.field)), kind);
    assert.ok(mesh.vertices.length && mesh.indices.length);
  }
  assert.equal(action(53n, 2n), -6n);
  assert.equal(action(53n, 1n), 1n);
  const peek = frame();
  assert.equal(peek.passes.length, 1);
  assert.ok(!chrome().some(command => command.kind === Kind.BOX));
  assert.deepEqual(peek.passes[0].eye, initial.passes[1].eye);
  assert.equal(action(54n), 1n);
  assert.equal(action(32n), 1n);
  assert.equal(advance(100n), 1n);
  assert.notDeepEqual(frame().passes[0].eye, initial.passes[0].eye);
  assert.equal(action(42n), 1n);
  assert.equal(action(55n, 24000n, -12000n), 1n);
  assert.equal(action(32n), 1n);
  assert.equal(action(53n, 1n), 1n);
  assert.equal(event(9n), 1n);
  assert.equal(info(8), 0n);
  const blurred = frame().passes[0].eye;
  assert.equal(advance(200n), 2n);
  assert.deepEqual(frame().passes[0].eye, blurred);
  assert.equal(action(30n), 1n);
  assert.equal(info(0), 2n);
  assert.equal(info(5), 1n);
  assert.ok(chrome().some(command => command.color === 0xff4040ff && /^Missed: .+ off$/.test(command.text)));
  assert.equal(advance(2001n), 1n);
  assert.equal(info(0), 3n);
  assert.equal(frame(), null);
  assert.ok(hasText(chrome(), "0 of 1 matched   highest rung matched 0"));
  const easy = create(1n, 1n);
  try {
    assert.equal(api.nw_api_v1_dispatch(easy, 1n, 0n, 0n, 31n, 0n, 0n, 0n, 0n, 0n, 0n), 1n);
    const meter = chrome(easy).filter(command => [0x282830c8, 0x5a8ce6ff].includes(command.color));
    assert.equal(meter.length, 2);
    // Camera.closeness for the original Python scene at rung 1, seed 17.
    assert.ok(Math.abs(meter[1].c / meter[0].c - 0.8264462809917354) < 1e-6);
  } finally {
    assert.equal(api.nw_api_v1_destroy(easy), 0n);
  }
  const precise = create(100n, 1n);
  try {
    assert.equal(api.nw_api_v1_dispatch(precise, 1n, 0n, 0n, 31n, 0n, 0n, 0n, 0n, 0n, 0n), 1n);
    // Python's Camera uses two significant digits for sub-millimetre
    // tolerances outside the fixed-decimal range.
    assert.ok(hasText(chrome(precise), "rung 100  photo 1/1  within 2.3e-11 mm, 4.8e-11°"));
  } finally {
    assert.equal(api.nw_api_v1_destroy(precise), 0n);
  }
} finally {
  assert.equal(api.nw_api_v1_destroy(run), 0n);
  api.nw_frame_free(buffer);
}
assert.equal(api.nw_camera_info(run, 0n), -1n);
console.log("PASS: Camera WASM options, controls, render packets, display commands, judgement, and cleanup");
