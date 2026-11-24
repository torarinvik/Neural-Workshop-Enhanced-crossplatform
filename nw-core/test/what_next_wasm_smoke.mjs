import assert from "node:assert/strict";
import fs from "node:fs";
import { decode, Kind } from "../shells/web/display-list.js";
import { TASK_IDS_BY_CATEGORY } from "../shells/web/task-registry.js";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { encodeWhatNextGroup, loadWhatNextGroup } from "../shells/web/video-jigsaw-media.js";

const wasm = fs.readFileSync(process.env.NWCORE_WASM_PATH ?? new URL("../build/nwcore.wasm", import.meta.url));
const { exports: api } = await instantiateElisa(wasm, { warn: false });
const task = api.nw_api_v1_task_what_next();
assert.equal(api.nw_api_v1_supports(task, 1n), 1n);

const sampleCount = Math.ceil(160 * 120 * 3 / 97);
const clip = (length, seed, still = false) => ({
  frames: new Array(length),
  samples: Uint8Array.from({ length: length * sampleCount }, (_, at) =>
    still ? 64 : (seed * 37 + Math.floor(at / sampleCount) * 6 + (at % sampleCount) * 97 * 3) % 256),
});
const decoded = [clip(120, 0), clip(100, 3), clip(100, 4)];
const group = encodeWhatNextGroup(decoded);
const stillGroup = encodeWhatNextGroup([clip(120, 0, true)]);
assert.throws(() => encodeWhatNextGroup([]), /clip count/);
assert.throws(() => encodeWhatNextGroup([{ frames: [null], samples: new Uint8Array(1) }]), /clip frames/);

const run = api.nw_api_v1_create(task, 1n, 1n, 1n, 1n, 0n, 0n, 0n, 17n);
assert.ok(run > 0n);
assert.equal(api.nw_api_v1_create(task, 1n, 2n, 1n, 1n, 0n, 0n, 0n, 17n), -3n);
const pointer = api.nw_frame_alloc(BigInt(group.length));
assert.ok(pointer > 0n);
const card = TASK_IDS_BY_CATEGORY[3].indexOf("what_next");
assert.equal(card, 3);
const hubLength = api.nw_taskhub_write(pointer, BigInt(group.length), 3n, BigInt(card), 0n, 912n, 684n);
assert.ok(hubLength > 0n);
const hub = decode(new Uint8Array(api.memory.buffer, Number(pointer), Number(hubLength)));
assert.equal(hub.filter(command => command.text === "What Happens Next").length, 1);
const preview = (rung, clips) => {
  const length = api.nw_what_next_options_note(pointer, BigInt(group.length), rung, clips);
  assert.ok(length > 0n);
  return new TextDecoder().decode(new Uint8Array(api.memory.buffer, Number(pointer), Number(length)));
};
assert.equal(preview(1n, 0n), "Rung 1: 2 options; the decoys are another clip.  Import video clips to build the library.");
assert.equal(preview(24n, 2n), "Rung 24: 6 options; the decoys are played backwards, later on, the opening again, from the opening, skipped ahead.  Only the last 70% of the opening is shown.  2 clips saved.");
const frame = () => {
  const length = api.nw_api_v1_render(run, pointer, BigInt(group.length), 0n, 912n, 684n);
  assert.ok(length > 0n);
  return decode(new Uint8Array(api.memory.buffer, Number(pointer), Number(length)));
};
const info = field => api.nw_what_next_info(run, BigInt(field));
let sequence = 0n;
const event = (kind, code, now, x = 0n, y = 0n) =>
  api.nw_api_v1_dispatch(run, kind, now, sequence++, code, 0n, 0n, 0n, x, y, 0n);
const click = (tile, now) => event(5n, 0n, now,
  BigInt(Math.round(tile.a / 912 * 1e6)), BigInt(Math.round(tile.b / 684 * 1e6)));
const load = (data, now, length = data.length) => {
  new Uint8Array(api.memory.buffer, Number(pointer), data.length).set(data);
  return api.nw_what_next_load(run, pointer, BigInt(length), now, sequence++);
};
const advance = now => api.nw_api_v1_advance(run, now, 0n, sequence++);

try {
  assert.equal(info(0), 0n);
  assert.equal(info(11), 2n);
  assert.equal(api.nw_what_next_pick_clip(run, 3n), -6n);
  assert.ok(frame().some(command => command.text === "Press Space to start"));
  assert.equal(event(2n, 1n, 0n), 1n);
  assert.equal(info(0), 1n);
  assert.equal(api.nw_what_next_pick_clip(run, 0n), -6n);
  assert.equal(api.nw_what_next_pick_clip(run, 3n), 2n);
  assert.equal(api.nw_what_next_pick_clip(run, 2n), 1n);
  assert.equal(load(group, 1n, group.length - 1), -6n);
  assert.equal(load(stillGroup, 1n), 2n);
  assert.equal(info(0), 1n);
  assert.equal(info(2), 0n);
  assert.equal(loadWhatNextGroup(api, run, decoded, 2n, sequence++), 1n);
  assert.equal(info(0), 2n);
  assert.equal(info(4), 2n);
  assert.equal(info(9), -1n);
  assert.equal(info(10), -1n);
  assert.equal(api.nw_what_next_clip(run, 0n), 0n);
  assert.equal(api.nw_what_next_frame(run, 0n, 1002n), 15n);
  const clips = [1n, 2n].map(stream => api.nw_what_next_clip(run, stream));
  assert.deepEqual([...clips].sort(), [0n, 1n]);
  const trueOption = BigInt(clips.indexOf(0n));
  assert.equal(api.nw_what_next_frame(run, trueOption + 1n, 1002n), 48n);
  assert.equal(api.nw_what_next_frame(run, trueOption + 1n, 3502n), 52n);
  const scene = frame();
  const tiles = scene.filter(command => command.kind === Kind.SPRITE_FIT);
  assert.deepEqual(tiles.map(tile => tile.ref), [100016, 100017, 100018]);
  assert.ok(scene.some(command => command.text === "how it starts"));
  assert.ok(!scene.some(command => command.text === "another clip"));
  assert.equal(click(tiles[0], 900n), 2n);
  assert.equal(event(2n, 17n, 950n), 2n);
  assert.equal(click(tiles[Number(trueOption) + 1], 1000n), 1n);
  assert.equal(info(0), 3n);
  assert.equal(info(5), 1n);
  assert.equal(info(6), 1n);
  assert.equal(info(8), trueOption);
  assert.equal(info(9), trueOption);
  assert.equal(info(10), 6n);
  const judged = frame();
  assert.ok(judged.some(command => command.text === "another clip"));
  assert.ok(judged.some(command => command.text === "what happened"));
  assert.ok(judged.some(command => command.text === "Right: that is what happened"));
  assert.equal(advance(3999n), 2n);
  assert.equal(advance(4000n), 1n);
  assert.equal(info(0), 4n);
  assert.ok(frame().some(command => command.text === "1 of 1 passed   highest rung passed 1"));
  assert.ok(!frame().some(command => command.kind === Kind.SPRITE_FIT));
  assert.equal(api.nw_what_next_frame(run, 0n, 4000n), -1n);
  assert.equal(event(2n, 1n, 4100n), 1n);
  assert.equal(loadWhatNextGroup(api, run, decoded, 4200n, sequence++), 1n);
  const wrongOption = api.nw_what_next_clip(run, 1n) === 0n ? 1n : 0n;
  assert.equal(event(2n, 12n + wrongOption, 4300n), 1n);
  assert.equal(info(6), 0n);
  const missed = frame();
  assert.ok(missed.some(command => command.text?.startsWith("No — that was another clip")));
  const borderColors = missed.filter(command => command.kind === Kind.BOX).map(command => command.color);
  assert.equal(borderColors[0], 0x000000ff);
  assert.equal(borderColors[Number(wrongOption) + 1], 0xd6403aff);
  assert.equal(borderColors[2 - Number(wrongOption)], 0x3caa5aff);
} finally {
  assert.equal(api.nw_api_v1_destroy(run), 0n);
  api.nw_frame_free(pointer);
}
console.log("PASS: What Happens Next WASM media packet, playback, scene, keyboard and pointer input, and scoring");
