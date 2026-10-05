import assert from "node:assert/strict";
import { captureMarbleFramebuffer } from "./marble_framebuffer_capture.mjs";

const debug = { testClockFrozen: true, elapsed: 0.7,
  capture: { framebuffer: { width: 1600, height: 1200 } } };
let calls = 0;
const canvas = { width: 1600, height: 1200, toDataURL(type) {
  assert.equal(type, "image/png"); calls++;
  return "data:image/png;base64,AA==";
} };
const result = captureMarbleFramebuffer(canvas, debug);
assert.equal(calls, 1);
assert.deepEqual(result.debug.capture.readback, {
  mode: "raw", background: null, width: 1600, height: 1200,
});
assert.equal(result.readback.mode, "raw");
assert.notEqual(result.debug, debug);
debug.elapsed = 1;
assert.equal(result.debug.elapsed, 0.7, "capture must not retain mutable live state");
for (const invalid of [null, { ...debug, testClockFrozen: false },
  { ...debug, capture: null },
  { ...debug, capture: { framebuffer: { width: 1600, height: 1202 } } }]) {
  assert.throws(() => captureMarbleFramebuffer(canvas, invalid));
}
assert.equal(calls, 1, "invalid metadata must fail before readback");
for (const output of ["data:,", "data:image/jpeg;base64,AA==", "data:image/png;base64,"]) {
  assert.throws(() => captureMarbleFramebuffer({ ...canvas, toDataURL: () => output }, debug));
}
const operations = [];
const composite = {
  getContext(kind, options) {
    assert.equal(kind, "2d");
    assert.deepEqual(options, { alpha: false });
    return {
      set fillStyle(value) { operations.push(["background", value]); },
      fillRect(...args) { operations.push(["fill", ...args]); },
      drawImage(...args) { operations.push(["draw", ...args]); },
    };
  },
  toDataURL: canvas.toDataURL,
};
const displayed = { ...canvas, ownerDocument: {
  defaultView: { getComputedStyle: () => ({ backgroundColor: "rgb(255, 255, 255)" }) },
  createElement: name => { assert.equal(name, "canvas"); return composite; },
} };
const opaque = captureMarbleFramebuffer(displayed, debug, { displayedBackground: true });
assert.deepEqual(operations, [["background", "rgb(255, 255, 255)"],
  ["fill", 0, 0, 1600, 1200], ["draw", displayed, 0, 0]]);
assert.equal(composite.width, 1600);
assert.equal(composite.height, 1200);
assert.equal(opaque.readback.mode, "displayed-background-composite");
assert.deepEqual(opaque.debug.capture.readback, opaque.readback);
assert.throws(() => captureMarbleFramebuffer(displayed,
  { ...debug, capture: { ...debug.capture, dark: true } }, { displayedBackground: true }));
console.log("PASS: raw/opaque same-resolution Marble capture and frozen snapshot contract");
