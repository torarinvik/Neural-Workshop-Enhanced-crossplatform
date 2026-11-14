import assert from 'node:assert/strict';
import { Kind, render } from '../shells/web/display-list.js';
for (const round of [false, true]) {
  const calls = [];
  const ctx = { save() {}, restore() {}, setTransform() {}, clearRect() {}, translate() {}, scale() {},
    measureText: () => ({width: 8}), fillText(text, x, y) { calls.push({text, x, y}); } };
  render(ctx, [{kind: Kind.TEXT, a: 456, b: 300, c: 12, d: 0, color: 0xffffffff,
    text: 'A\nB', anchor: ['center', 'middle']}],
    {width: 912, height: 684, roundGlyphAdvances: round});
  assert.deepEqual(calls.map(c => c.text), ['A', 'B']);
  assert.equal(calls[1].y - calls[0].y, 15);
}
console.log('Browser multiline text: both rendering paths draw centered separate lines');
