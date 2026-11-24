import assert from "node:assert/strict";
import fs from "node:fs";
import { decode } from "../shells/web/display-list.js";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { attachTunerRecordings, loadTunerRecordings, tunerRecordingBank } from "../shells/web/tuner-recordings.js";

const bytes = fs.readFileSync(process.env.NWCORE_WASM_PATH ?? new URL("../build/nwcore.wasm", import.meta.url));
const { exports: api } = await instantiateElisa(bytes, { warn: false });
const index = fs.readFileSync(new URL("../res/misc/esc50/index.tsv", import.meta.url), "utf8");
const frames = 220500;
const wav = Buffer.alloc(44 + frames * 2);
wav.write("RIFF");
wav.writeUInt32LE(wav.length - 8, 4);
wav.write("WAVEfmt ", 8);
wav.writeUInt32LE(16, 16);
wav.writeUInt16LE(1, 20);
wav.writeUInt16LE(1, 22);
wav.writeUInt32LE(44100, 24);
wav.writeUInt32LE(88200, 28);
wav.writeUInt16LE(2, 32);
wav.writeUInt16LE(16, 34);
wav.write("data", 36);
wav.writeUInt32LE(frames * 2, 40);
for (let i = 0; i < frames; i++) wav.writeInt16LE(i % 4 < 2 ? 7500 : -7500, 44 + i * 2);
const body = wav.buffer.slice(wav.byteOffset, wav.byteOffset + wav.byteLength);
const reads = new Map();
const files = [];
for (const line of index.split("\n")) {
  if (!line || line.startsWith("#")) continue;
  const [row, , from, to, sounding, db] = line.split("\t").map(Number);
  if (to / 1000 - from / 1000 < 1 || sounding < 0.45 || db < -42) continue;
  const name = `${String(row).padStart(7, "0")}.wav`;
  files.push({
    name, webkitRelativePath: `datasets/esc50/${name}`, size: wav.length,
    async arrayBuffer() {
      reads.set(row, (reads.get(row) ?? 0) + 1);
      return body;
    },
  });
  if (files.length === 300) break;
}
const bank = tunerRecordingBank(index, files);
assert.equal(bank.size, 300);
assert.equal(tunerRecordingBank(index, files.slice(1)).size, 299);
assert.throws(() => tunerRecordingBank("malformed\trow", files), /Invalid ESC-50 index/);

const task = api.nw_api_v1_task_tuner();
const run = api.nw_api_v1_create(task, 1n, 1n, 3n, 1n, 0n, 0n, 0n, 17n);
const capacity = 1048576n;
const pointer = api.nw_frame_alloc(capacity);
const read = length => new Uint8Array(api.memory.buffer, Number(pointer), Number(length));
const info = field => api.nw_api_v1_tuner_info(run, BigInt(field));
const frame = () => decode(read(api.nw_api_v1_render(run, pointer, capacity, 1n, 912n, 684n)));
try {
  attachTunerRecordings(api, run, bank);
  assert.equal(api.nw_tuner_recording_add(run, 0n, 0n, 0n, 3000n), 2n);
  assert.equal(api.nw_api_v1_dispatch(run, 1n, 0n, 0n, 6n, 0n, 0n, 0n, 0n, 0n, 0n), 1n);
  assert.equal(info(6), 3n);
  // Python's seed 17 on the first 300 usable ESC-50 rows.
  assert.equal(api.nw_tuner_recording_row(run, -1n), 242n);
  assert.equal(api.nw_tuner_advance(run, 10, 0n), 2n);
  assert.equal(info(4), 0n);
  assert.ok(frame().some(command => command.text === "Loading recordings..."));
  assert.ok(frame().some(command => command.text?.endsWith("3 stations   recordings")));
  assert.equal(api.nw_tuner_audio(run, pointer, capacity), 0n);
  await loadTunerRecordings(api, run, bank, () => true, () => 10);
  assert.ok(reads.size >= 3 && [...reads.values()].every(count => count === 1), reads);
  assert.equal(api.nw_tuner_recording_row(run, -1n), -1n);
  assert.equal(info(4), 0n);
  for (let step = 1; step <= 8; step++) assert.equal(api.nw_tuner_advance(run, 10 + step / 20, 0n), 1n);
  assert.equal(info(4), 400n);
  const length = api.nw_tuner_audio(run, pointer, capacity);
  assert.equal(length, 35280n);
  const samples = read(length);
  const pcm = new DataView(samples.buffer, samples.byteOffset, samples.byteLength);
  let loud = 0;
  for (let i = 0; i < samples.byteLength; i += 4) {
    assert.equal(pcm.getInt16(i, true), pcm.getInt16(i + 2, true));
    loud = Math.max(loud, Math.abs(pcm.getInt16(i, true)));
  }
  assert.ok(loud === 3839 || loud === 3840, loud);

  for (let step = 9; step <= 82; step++) api.nw_tuner_advance(run, 10 + step / 20, 0n);
  assert.equal(info(11), 1n);
  // Python's target dial is 77.763 at this rung. Point to it on the cabinet.
  const x = BigInt(Math.round(633 / 912 * 1e6));
  const y = BigInt(Math.round(428 / 684 * 1e6));
  assert.equal(api.nw_api_v1_dispatch(run, 5n, 14100n, 1n, 0n, 0n, 0n, 0n, x, y, 0n), 1n);
  assert.equal(api.nw_api_v1_dispatch(run, 1n, 14100n, 2n, 4n, 0n, 0n, 0n, 0n, 0n, 0n), 1n);
  for (let step = 83; step <= 104; step++) api.nw_tuner_advance(run, 10 + step / 20, 0n);
  assert.equal(info(0), 2n);
  assert.equal(info(7), 1n);
  assert.equal(api.nw_tuner_advance(run, Number(info(10)) / 1000 + 0.01, 0n), 1n);
  assert.equal(info(2), 2n);
  assert.ok(api.nw_tuner_recording_row(run, -1n) >= 0n);
  reads.clear();
  await loadTunerRecordings(api, run, bank, () => false, () => 20);
  assert.equal(reads.size, 0);
  await loadTunerRecordings(api, run, bank, () => true, () => 20);
  assert.ok(reads.size > 0);
  assert.equal(api.nw_tuner_recording_row(run, -1n), -1n);
  assert.equal(info(4), 0n);
} finally {
  api.nw_frame_free(pointer);
  assert.equal(api.nw_api_v1_destroy(run), 0n);
}
console.log("PASS: browser ESC-50 index, recorded deal, deferred clock, lazy WAV reads, and stereo PCM");
