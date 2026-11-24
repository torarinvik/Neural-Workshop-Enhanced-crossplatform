import assert from "node:assert/strict";
import fs from "node:fs";
import { createHash } from "node:crypto";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";

const fixture = fileURLToPath(new URL("./public_outcome_fixture.py", import.meta.url));
const python = spawnSync("python3", [fixture], { encoding: "utf8", maxBuffer: 4 * 1024 * 1024 });
assert.equal(python.status, 0, python.stderr);
const cases = JSON.parse(python.stdout);
const path = process.env.NWCORE_WASM_PATH ?? new URL("../build/nwcore.wasm", import.meta.url);
const { exports, instance, verifyPublicOutcome, verifyTaskOutcome, createPublicFrameArchive } = await instantiateElisa(fs.readFileSync(path), { warn: false });
const output = exports.nw_frame_alloc(32n);
assert.ok(output > 0n);
const hashOut = exports.nw_frame_alloc(64n);
const expectedHash = exports.nw_frame_alloc(64n);
assert.ok(hashOut > 0n && expectedHash > 0n);
const digest = exports.nw_public_frame_digest;
const verify = exports.nw_public_outcome_verify_frame;

for (const count of [0, 1, 3, 55, 56, 63, 64, 65, 119, 120, 127, 128, 129, 4096]) {
  const bytes = Buffer.from(Array.from({ length: count }, (_, i) => (i * 97 + 13) & 255));
  const input = exports.nw_frame_alloc(BigInt(Math.max(1, count)));
  const memory = instance.exports.memory.buffer;
  new Uint8Array(memory, Number(input), count).set(bytes);
  assert.equal(digest(input, BigInt(count), hashOut), 1n);
  const hash = Buffer.from(memory, Number(hashOut), 64).toString("ascii");
  assert.equal(hash, createHash("sha256").update(bytes).digest("hex"), `SHA-256 for ${count} bytes`);
  assert.equal(digest(input, -1n, hashOut), -1n);
  assert.equal(digest(input, BigInt(count), BigInt(memory.byteLength) - 63n), -1n);
  exports.nw_frame_free(input);
}
const read = exports.nw_public_outcome_read;

for (const sample of cases) {
  const frame = Buffer.from(sample.rgba, "base64");
  const size = BigInt(frame.length);
  const pixels = exports.nw_frame_alloc(size);
  const width = BigInt(sample.width);
  const height = BigInt(sample.height);
  assert.ok(pixels > 0n);
  const memory = instance.exports.memory.buffer;
  new Uint8Array(memory, Number(pixels), frame.length).set(frame);
  const result = new DataView(memory, Number(output), 32);
  result.setBigInt64(0, -1n, true);
  assert.equal(read(pixels, size - 1n, width, height, output), -1n);
  assert.equal(read(pixels, size, 9223372036854775807n, height, output), -1n);
  assert.equal(read(pixels, size, width, 0n, output), -1n);
  assert.equal(read(pixels, size, width, height, output + 1n), -1n);
  assert.equal(read(1n + BigInt(memory.byteLength), size, width, height, output), -1n);
  assert.equal(result.getBigInt64(0, true), -1n, "invalid input leaves the result untouched");
  assert.equal(read(pixels, size, width, height, output), sample.scalar === null ? 0n : 1n);
  assert.deepEqual([0, 8, 16].map((offset) => Number(result.getBigInt64(offset, true))), sample.counts);
  assert.equal(result.getFloat64(24, true), sample.scalar ?? 0);
  assert.equal(digest(pixels, size, hashOut), 1n);
  assert.equal(Buffer.from(memory, Number(hashOut), 64).toString("ascii"), sample.digest);
  new Uint8Array(memory, Number(expectedHash), 64).set(Buffer.from(sample.digest, "ascii"));
  assert.equal(verify(pixels, size, width, height, expectedHash, sample.scalar ?? 0),
    sample.scalar === null ? 0n : 1n);
  if (sample.scalar !== null) {
    assert.equal(verify(pixels, size, width, height, expectedHash, sample.scalar + 1), 0n);
    assert.equal(verify(pixels, size, width, height, expectedHash, NaN), 0n);
    new Uint8Array(memory, Number(pixels), frame.length)[3] ^= 1; // Alpha changes evidence, not the score.
    assert.equal(verify(pixels, size, width, height, expectedHash, sample.scalar), 0n);
  }
  assert.equal(verify(pixels, size, width, height, BigInt(memory.byteLength) - 63n, 0), -1n);
  exports.nw_frame_free(pixels);
}
exports.nw_frame_free(output);
exports.nw_frame_free(hashOut);
exports.nw_frame_free(expectedHash);
console.log(`PASS: ${cases.length} public outcome RGBA cases match Python, including SHA-256 and altered-frame rejection`);

const evidencePython = spawnSync("python3", [fixture, "--evidence"], { encoding: "utf8" });
assert.equal(evidencePython.status, 0, evidencePython.stderr);
const { feedback, scenarios } = JSON.parse(evidencePython.stdout);
for (const { name, outcome, archive, ledger, expected, expected_task_zero } of scenarios) {
  const hostArchive = archive && new Map(Object.entries(archive)
    .map(([digest, rgba]) => [digest, Buffer.from(rgba, "base64")]));
  const hostLedger = ledger && new Map(Object.entries(ledger)
    .map(([id, record]) => [Number(id), record]));
  const hostFrame = Buffer.from(feedback.rgba, "base64");
  assert.equal(verifyPublicOutcome(outcome, hostFrame, feedback.width, feedback.height,
    hostArchive, hostLedger), expected, `web adapter: ${name}`);
  assert.equal(verifyPublicOutcome({ ...outcome, n_pos: 1 }, hostFrame, feedback.width,
    feedback.height, hostArchive, hostLedger), false, "private fields fail closed");
  assert.equal(verifyTaskOutcome(outcome, hostFrame, feedback.width, feedback.height,
    hostArchive, hostLedger), expected, `nonzero task evidence: ${name}`);
  assert.equal(verifyTaskOutcome({ ...outcome, scalar: 0 }, hostFrame, feedback.width,
    feedback.height, hostArchive, hostLedger), expected_task_zero, `zero task evidence: ${name}`);
  const archiveObject = hostArchive && Object.fromEntries(hostArchive);
  assert.equal(verifyPublicOutcome(outcome, hostFrame, feedback.width, feedback.height,
    archiveObject, ledger), expected, `plain objects: ${name}`);
  assert.equal(verifyPublicOutcome({ ...outcome, get scalar() { throw new Error("getter invoked"); } },
    hostFrame, feedback.width, feedback.height, hostArchive, hostLedger), false);
  assert.equal(verifyPublicOutcome({ ...outcome, evidence_digests: Array(1) }, hostFrame,
    feedback.width, feedback.height, hostArchive, hostLedger), false, "sparse digest list");
  const allocated = [];
  const allocate = (count) => {
    const address = exports.nw_frame_alloc(BigInt(Math.max(count, 1)));
    assert.ok(address > 0n);
    allocated.push(address);
    return address;
  };
  const copy = (data) => {
    const address = allocate(data.length);
    new Uint8Array(instance.exports.memory.buffer, Number(address), data.length).set(data);
    return address;
  };
  const words = (values) => {
    const address = allocate(values.length * 8);
    const view = new DataView(instance.exports.memory.buffer, Number(address), values.length * 8);
    values.forEach((value, index) => view.setBigInt64(index * 8, BigInt(value), true));
    return address;
  };
  const digests = outcome.evidence_digests;
  const frame = Buffer.from(feedback.rgba, "base64");
  const rgba = copy(frame);
  const evidence = copy(Buffer.from(digests.join(""), "ascii"));
  const rows = archive ? words(digests.flatMap((digest) => {
    if (!(digest in archive)) return [0n, 0n];
    const data = Buffer.from(archive[digest], "base64");
    return [copy(data), data.length];
  })) : 0n;
  const selected = ledger?.[outcome.receipt_id];
  const receipt = selected ? words([
    outcome.receipt_id, selected.receipt_id ?? -1, selected.trial_seq ?? -1,
    selected.stimulus_digest ? copy(Buffer.from(selected.stimulus_digest, "ascii")) : 0n,
    selected.feedback_digest ? copy(Buffer.from(selected.feedback_digest, "ascii")) : 0n,
    selected.evidence_digests ? copy(Buffer.from(selected.evidence_digests.join(""), "ascii")) : 0n,
    selected.evidence_digests?.length ?? 0,
  ]) : 0n;
  const verifyEvidence = (archiveRows = rows, receiptRow = receipt) => exports.nw_public_outcome_verify_evidence(
    rgba, BigInt(frame.length), BigInt(feedback.width), BigInt(feedback.height), evidence,
    BigInt(digests.length), archiveRows, BigInt(outcome.receipt_id ?? -1), receiptRow, outcome.scalar);
  assert.equal(verifyEvidence(), expected ? 1n : 0n, name);
  const verifyTask = (width, count = BigInt(digests.length)) => exports.nw_public_outcome_verify_task_evidence(
    rgba, BigInt(frame.length), width, BigInt(feedback.height), evidence,
    count, rows, BigInt(outcome.receipt_id ?? -1), receipt, 0);
  assert.equal(verifyTask(BigInt(feedback.width)), expected_task_zero ? 1n : 0n, name);
  assert.equal(verifyTask(BigInt(feedback.width), 0n), -1n);
  if (expected_task_zero) assert.equal(verifyTask(0n), -1n, "invalid dimensions cannot concede");
  if (rows) assert.equal(verifyEvidence(rows + 1n), -1n, "misaligned frame table");
  if (receipt) {
    assert.equal(verifyEvidence(rows, receipt + 1n), -1n, "misaligned receipt table");
    const row = new DataView(instance.exports.memory.buffer, Number(receipt), 56);
    row.setBigInt64(24, BigInt(instance.exports.memory.buffer.byteLength), true);
    assert.equal(verifyEvidence(), -1n, "out-of-bounds stimulus digest");
  }
  for (const address of allocated.reverse()) exports.nw_frame_free(address);
}
console.log(`PASS: ${scenarios.length} archive and receipt binding cases match Python`);


const shell = fs.readFileSync(new URL("../shells/web/index.html", import.meta.url), "utf8");
assert.ok(shell.includes("createPublicFrameArchive: () => core.createPublicFrameArchive(ctx)"));
const stimulus = cases.find((sample) => sample.scalar === null && sample.width > 1);
let canvasSample = stimulus;
let canvasBytes = Uint8ClampedArray.from(Buffer.from(canvasSample.rgba, "base64"));
const captured = createPublicFrameArchive({
  get canvas() { return canvasSample; },
  getImageData(x, y, width, height) {
    assert.deepEqual([x, y, width, height], [0, 0, canvasSample.width, canvasSample.height]);
    return { data: canvasBytes };
  },
});
const first = captured.capture();
assert.equal(first.frame_seq, 1);
assert.equal(first.digest, stimulus.digest);
assert.equal(captured.capture().digest, first.digest);
canvasBytes.fill(255);
first.rgba.fill(255);
assert.deepEqual(captured.get(first.digest), Uint8Array.from(Buffer.from(stimulus.rgba, "base64")));
canvasSample = feedback;
canvasBytes = Uint8ClampedArray.from(Buffer.from(canvasSample.rgba, "base64"));
const last = captured.capture();
assert.equal(last.frame_seq, 3);
assert.ok(last.timestamp_ns >= first.timestamp_ns);
assert.equal(last.digest, feedback.digest);
const evidence = [first.digest, last.digest];
const claim = { scalar: feedback.scalar, evidence_digests: evidence, receipt_id: 4 };
const ledger = new Map([[4, { receipt_id: 4, trial_seq: 4, stimulus_digest: first.digest,
  feedback_digest: last.digest, evidence_digests: evidence }]]);
assert.equal(captured.verify(claim, last), false, "a claimed receipt requires a ledger");
assert.equal(captured.verify(claim, last, ledger), true);
captured.get(last.digest).fill(0);
assert.equal(captured.verify(claim, last, ledger), true, "archive lookups return copies");
last.rgba[3] ^= 1;
assert.equal(captured.verify(claim, last, ledger), false, "altered capture is rejected");
last.rgba[3] ^= 1;
captured.clear();
assert.equal(captured.verify(claim, last, ledger), false, "cleared evidence cannot verify");
console.log("PASS: canvas capture, SHA-256 archive, and receipt verification");

// A 912×684 flight can produce more evidence than fits in a single verification batch.
const flightPixels = new Uint8ClampedArray(912 * 684 * 4);
const flightContext = {
  canvas: { width: 912, height: 684 },
  getImageData: () => ({ data: flightPixels }),
};
const flightArchive = createPublicFrameArchive(flightContext, exports, exports.memory, verifyPublicOutcome);
const flightEvidence = [];
for (let frame = 0; frame < 14; frame++) {
  flightPixels[0] = frame;
  flightEvidence.push(flightArchive.capture().digest);
}
flightPixels.fill(0);
for (let row = 1; row <= 2; row++) {
  const start = flightPixels.length - row * 912 * 4;
  for (let column = 0; column < 5; column++) {
    flightPixels.set([64, 255, 64, 255], start + column * 4);
  }
}
const flightVerdict = flightArchive.capture();
flightEvidence.push(flightVerdict.digest);
const flightClaim = { scalar: 1, evidence_digests: flightEvidence, receipt_id: 7 };
const flightLedger = new Map([[7, {
  receipt_id: 7, trial_seq: 7, stimulus_digest: flightEvidence[0],
  feedback_digest: flightVerdict.digest, evidence_digests: flightEvidence,
}]]);
assert.equal(flightArchive.verify(flightClaim, flightVerdict, flightLedger), true);
assert.equal(flightArchive.verify({ ...flightClaim, scalar: -1 }, flightVerdict, flightLedger), false);
flightArchive.clear();

const loadCanvas = (sample) => {
  canvasSample = sample;
  canvasBytes = Uint8ClampedArray.from(Buffer.from(sample.rgba, "base64"));
};
const driven = [];
const session = captured.createReceiptSession({ ports: 4, drive: (port) => driven.push(port) });
assert.equal(session.act(1).ok, false);
loadCanvas(stimulus);
const opened = session.open();
assert.equal(session.act(4).ok, false);
const actionReceipt = session.act(1, -0.5);
assert.equal(actionReceipt.ok, true);
assert.equal(actionReceipt.stimulus_digest, opened.digest);
assert.equal(actionReceipt.frame_seq, opened.frame_seq);
assert.equal(actionReceipt.logp, -0.5);
assert.equal(session.act(2).ok, false);
assert.deepEqual(driven, [1]);
const quiet = session.publish();
assert.equal(quiet.outcome, undefined, "sparse action still awaits feedback");
loadCanvas(feedback);
const settled = session.publish();
assert.deepEqual(settled.outcome.evidence_digests, [opened.digest, quiet.digest, settled.digest]);
assert.equal(settled.outcome.scalar, feedback.scalar);
assert.equal(session.verify(settled.outcome, settled), true);
assert.equal(session.publish().outcome, undefined, "a lingering verdict pays once");
const row = session.getReceipt(actionReceipt.receipt_id);
assert.equal(row.feedback_frame_seq, settled.frame_seq);
row.evidence_digests.reverse();
actionReceipt.ports.push(3);
assert.deepEqual(session.getReceipt(actionReceipt.receipt_id).ports, [1]);
assert.equal(session.verify(settled.outcome, settled), true);
const other = session.open();
assert.notEqual(other.digest, opened.digest);
const otherReceipt = session.act(0);
assert.equal(session.verify({ ...settled.outcome, receipt_id: otherReceipt.receipt_id }, settled), false);
session.clear();
assert.equal(session.verify(settled.outcome, settled), false);
assert.equal(session.act(0).ok, false);

const neutral = captured.createReceiptSession({ ports: 1, drive() {}, neutralOutcomes: true });
loadCanvas(stimulus);
neutral.open();
neutral.act(0);
const conceded = neutral.publish();
assert.equal(conceded.outcome.scalar, 0);
assert.equal(neutral.verify(conceded.outcome, conceded), false, "no visual verdict backs a neutral concession");
assert.equal(neutral.publish().outcome, undefined);
neutral.clear();

let attemptedReentry = false;
const guarded = captured.createReceiptSession({ ports: 1, drive() {
  if (!attemptedReentry) {
    attemptedReentry = true;
    guarded.closeWindow();
  }
} });
const guardedStimulus = guarded.open();
assert.throws(() => guarded.act(0), /driver must return/);
assert.equal(guarded.act(0).stimulus_digest, guardedStimulus.digest);
guarded.clear();
console.log("PASS: receipt issuance, delayed settlement, one outcome per action, and verified evidence");
