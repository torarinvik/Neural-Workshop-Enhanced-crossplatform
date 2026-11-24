import assert from "node:assert/strict";
import fs from "node:fs";
import { decode, Kind } from "../shells/web/display-list.js";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { TASK_IDS_BY_CATEGORY } from "../shells/web/task-registry.js";

const bytes = fs.readFileSync(process.env.NWCORE_WASM_PATH ?? new URL("../build/nwcore.wasm", import.meta.url));
const { exports: api, createWhoKnowsWhatEnvironment } = await instantiateElisa(bytes, { warn: false });
assert.equal(typeof createWhoKnowsWhatEnvironment, "function");
const task = api.nw_api_v1_task_who_knows_what();
assert.equal(task, 163698951n);
assert.equal(api.nw_api_v1_supports(task, 1n), 1n);
assert.equal(api.nw_api_v1_create(task, 1n, 11n, 1n, 1n, 0n, 0n, 0n, 222n), -3n);
const capacity = 65536n;
const pointer = api.nw_frame_alloc(capacity);
const buffer = length => new Uint8Array(api.memory.buffer, Number(pointer), Number(length));
const category = TASK_IDS_BY_CATEGORY[4];
const selected = category.indexOf("who_knows_what");
assert.equal(category[selected - 1], "fold_it");
try {
  const hub = decode(buffer(api.nw_taskhub_write(pointer, capacity, 4n, BigInt(selected), 0n, 912n, 684n)));
  assert.ok(hub.some(command => command.text === "Who Knows What?"));
  assert.equal(new TextDecoder().decode(buffer(api.nw_who_knows_what_options_note(pointer, capacity, 25n))),
    "Rung 25: 4 people, 4 containers, 3 things, 10 to 13 events.  With second-order questions, phone calls, lies, peeks.");
  const run = api.nw_api_v1_create(task, 1n, 25n, 2n, 1n, 1n, 0n, 0n, 222n);
  assert.ok(run > 0n);
  const info = field => api.nw_api_v1_who_knows_what_info(run, BigInt(field));
  const frame = () => decode(buffer(api.nw_api_v1_render(run, pointer, capacity, 1n, 912n, 684n)));
  let sequence = 0n;
  const send = (kind, key, time, x = 0, y = 0) => api.nw_api_v1_dispatch(run, BigInt(kind), BigInt(time),
    sequence++, BigInt(key), 0n, 0n, 0n, BigInt(Math.round(x * 1e6 / 912)), BigInt(Math.round(y * 1e6 / 684)), 0n);
  try {
    assert.ok(frame().some(command => command.text === "Press Space or click to start"));
    assert.equal(send(2, 1, 0), 1n);
    assert.equal(info(4), 4n);
    assert.equal(info(5), 16n);
    assert.equal(info(6), -1n);
    const playing = frame();
    assert.ok(playing.some(command => command.text === "Where does Esme think Dev will look for the apple?"));
    assert.equal(playing.filter(command => command.text === "out").length, 16);
    assert.ok(playing.some(command => command.text?.includes("peeks into")));
    const choices = playing.filter(command => command.kind === Kind.BOX && command.e === 2);
    assert.equal(choices.length, 4);
    assert.equal(send(5, 0, 10, 100, 400), 2n);
    // Python seed 222, rung 25, the drawer.
    const third = choices[2];
    assert.equal(send(5, 0, 20, third.a + third.c / 2, third.b + third.d / 2), 1n);
    assert.equal(info(1), 26n);
    assert.equal(info(6), 2n);
    assert.ok(frame().some(command => command.text === "Right: the drawer" && command.color === 0x40ff40ff));
    assert.equal(api.nw_api_v1_advance(run, 2519n, 0n, sequence++), 2n);
    assert.equal(api.nw_api_v1_advance(run, 2520n, 0n, sequence++), 1n);
    assert.equal(info(2), 2n);
    // The second puzzle's correct answer is the basket, so pressing 2 must fail.
    assert.equal(send(2, 13, 2600), 1n);
    assert.equal(info(1), 25n);
    assert.ok(frame().some(command => command.text === "No: the basket" && command.color === 0xff4040ff));
    assert.equal(api.nw_api_v1_advance(run, 5100n, 0n, sequence++), 1n);
    assert.ok(frame().some(command => command.text === "1 of 2 passed   highest rung passed 25"));
  } finally {
    assert.equal(api.nw_api_v1_destroy(run), 0n);
  }

  const stepped = api.nw_api_v1_create(task, 1n, 1n, 2n, 1n, 1n, 0n, 0n, 222n);
  try {
    assert.equal(api.nw_who_knows_what_think_configure(stepped, 0.1, 0.05), 1n);
    assert.equal(api.nw_api_v1_dispatch(stepped, 1n, 0n, 0n, 4n, 0n, 0n, 0n, 0n, 0n, 0n), 1n);
    assert.equal(api.nw_who_knows_what_step(stepped, 0.1), 1n);
    assert.equal(api.nw_api_v1_who_knows_what_info(stepped, 0n), 4n);
    const flag = decode(buffer(api.nw_api_v1_render(stepped, pointer, capacity, 0n, 912n, 684n)));
    assert.ok(flag.some(command => command.text === "Out of time" && command.color === 0xff4040ff));
    assert.equal(api.nw_who_knows_what_step(stepped, 0.01), 1n);
    assert.equal(api.nw_who_knows_what_think_left(stepped), 0.05);
    assert.equal(api.nw_api_v1_who_knows_what_info(stepped, 12n), 1n);
  } finally {
    assert.equal(api.nw_api_v1_destroy(stepped), 0n);
  }
} finally {
  api.nw_frame_free(pointer);
}
console.log("PASS: Who Knows What? WASM hub, original options, 16-panel story, mixed input, adaptive results, and stepped clock");
