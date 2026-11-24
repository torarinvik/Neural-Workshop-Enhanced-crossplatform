// Marshal the public outcome object and host-owned evidence into Elisa.
const PUBLIC_KEYS = new Set(["scalar", "evidence_digests", "receipt_id", "frame_seq", "timestamp_ns"]);
const isDigest = (value) => typeof value === "string" && /^[0-9a-f]{64}$/.test(value);
const isId = (value) => Number.isSafeInteger(value) && value >= 0;
const isBytes = (value) => value instanceof Uint8Array || value instanceof Uint8ClampedArray;
const lookup = (table, key) => table instanceof Map ? table.get(key)
  : table && Object.hasOwn(table, key) ? table[key] : undefined;
const ascii = new TextEncoder();

export function createPublicOutcomeVerifier(exports, memory, { allowConcessions = false } = {}) {
  const verifyEvidence = allowConcessions
    ? exports.nw_public_outcome_verify_task_evidence : exports.nw_public_outcome_verify_evidence;
  return function verifyPublicOutcome(outcome, rgba, width, height, archive = null, ledger = null) {
    if (!outcome || typeof outcome !== "object" ||
        !isBytes(rgba) || !Number.isSafeInteger(width) || !Number.isSafeInteger(height) ||
        width <= 0 || height <= 0 || width > Math.floor(rgba.byteLength / 4 / height)) return false;
    const fields = Object.getOwnPropertyDescriptors(outcome);
    if (Reflect.ownKeys(fields).some((key) => !PUBLIC_KEYS.has(key) || !Object.hasOwn(fields[key], "value"))) return false;
    const scalar = fields.scalar?.value;
    const claimedEvidence = fields.evidence_digests?.value;
    if (!Number.isFinite(scalar) || !Array.isArray(claimedEvidence) || !claimedEvidence.length) return false;
    const evidence = Array.from(claimedEvidence);
    if (!evidence.every(isDigest)) return false;

    const id = fields.receipt_id?.value ?? null;
    if (id !== null && (!isId(id) || archive === null || ledger === null)) return false;
    if (archive === null && evidence.length > 1) return false;

    const record = id === null ? null : lookup(ledger, id);
    if (id !== null && (!record || !isDigest(record.stimulus_digest) ||
        (record.receipt_id != null && !isId(record.receipt_id)) ||
        (record.trial_seq != null && !isId(record.trial_seq)) ||
        (record.feedback_digest != null && !isDigest(record.feedback_digest)) ||
        (record.evidence_digests != null && (!Array.isArray(record.evidence_digests) ||
          record.evidence_digests.length !== evidence.length ||
          !Array.from(record.evidence_digests).every(isDigest))))) return false;

    if (record && ((record.receipt_id != null && record.trial_seq != null &&
        record.receipt_id !== record.trial_seq) ||
        record.stimulus_digest !== evidence[0] ||
        (record.feedback_digest != null && record.feedback_digest !== evidence.at(-1)) ||
        record.evidence_digests?.some((digest, index) => digest !== evidence[index]))) return false;

    // Each digest is verified once. Long trials can exceed WASM address space
    // if all their frames are copied into linear memory at the same time.
    // Use the existing verifier for batches ending in the final frame so
    // every call also checks the claimed scalar against the same pixels.
    const frame = new Uint8Array(rgba);
    const last = evidence.at(-1);
    const initialMemory = memory.buffer;
    const archived = archive === null ? null : [...new Set(evidence)].map(digest => {
      const bytes = lookup(archive, digest);
      if (!isBytes(bytes)) return null;
      return [digest, bytes.buffer === initialMemory ? new Uint8Array(bytes) : bytes];
    });
    if (archived?.includes(null)) return false;

    function verifyBatch(batch) {
      const allocations = [];
      function copy(bytes) {
        const pointer = exports.nw_frame_alloc(BigInt(Math.max(bytes.length, 1)));
        if (pointer <= 0n) throw new RangeError("Could not allocate public outcome evidence");
        allocations.push(pointer);
        new Uint8Array(memory.buffer, Number(pointer), bytes.length).set(bytes);
        return pointer;
      }
      try {
        const input = copy(frame);
        const digests = copy(ascii.encode(batch?.map(([digest]) => digest).join("") ?? last));
        let rows = 0n;
        if (batch !== undefined) {
          const table = new Uint8Array(batch.length * 16);
          const view = new DataView(table.buffer);
          batch.forEach(([, bytes], index) => {
            view.setBigInt64(index * 16, copy(bytes), true);
            view.setBigInt64(index * 16 + 8, BigInt(bytes.length), true);
          });
          rows = copy(table);
        }
        return verifyEvidence(input, BigInt(frame.length), BigInt(width), BigInt(height),
          digests, BigInt(batch?.length ?? 1), rows, -1n, 0n, scalar) === 1n;
      } finally {
        for (const pointer of allocations.reverse()) exports.nw_frame_free(pointer);
      }
    }

    if (archived === null) return verifyBatch();
    const finalFrame = archived.find(([digest]) => digest === last);
    let batch = [];
    let bytes = finalFrame[1].length;
    for (const item of archived) {
      if (item === finalFrame) continue;
      if (batch.length && bytes + item[1].length > 32 * 1024 * 1024) {
        if (!verifyBatch([...batch, finalFrame])) return false;
        batch = [];
        bytes = finalFrame[1].length;
      }
      batch.push(item);
      bytes += item[1].length;
    }
    return verifyBatch([...batch, finalFrame]);
  };
}

// The host publishes significant frames by calling capture after painting the
// canvas. Archive bytes are private and only leave this closure as copies.
export function createPublicFrameArchive(context, exports, memory, verifyPublicOutcome) {
  const frames = new Map();
  let sequence = 0;

  function capture() {
    const { width, height } = context.canvas;
    const { data } = context.getImageData(0, 0, width, height);
    const timestamp_ns = Math.round(performance.now() * 1000000);
    const rgba = new Uint8Array(data);
    const input = exports.nw_frame_alloc(BigInt(Math.max(rgba.length, 1)));
    if (input <= 0n) throw new RangeError("Could not allocate the captured frame");
    let output = 0n;
    let digest;
    try {
      output = exports.nw_frame_alloc(64n);
      if (output <= 0n) throw new RangeError("Could not allocate the frame digest");
      const bytes = new Uint8Array(memory.buffer);
      bytes.set(rgba, Number(input));
      if (exports.nw_public_frame_digest(input, BigInt(rgba.length), output) !== 1n)
        throw new Error("Could not hash the captured frame");
      digest = new TextDecoder().decode(bytes.subarray(Number(output), Number(output) + 64));
    } finally {
      if (output > 0n) exports.nw_frame_free(output);
      exports.nw_frame_free(input);
    }

    if (!frames.has(digest)) frames.set(digest, rgba);
    return {
      frame_seq: ++sequence,
      timestamp_ns, width, height, digest, rgba: rgba.slice(),
    };
  }

  function readScalar({ rgba, width, height }) {
    const input = exports.nw_frame_alloc(BigInt(Math.max(rgba.length, 1)));
    if (input <= 0n) throw new RangeError("Could not allocate public outcome pixels");
    let output = 0n;
    try {
      output = exports.nw_frame_alloc(32n);
      if (output <= 0n) throw new RangeError("Could not allocate the public outcome scalar");
      new Uint8Array(memory.buffer, Number(input), rgba.length).set(rgba);
      const status = exports.nw_public_outcome_read(input, BigInt(rgba.length), BigInt(width), BigInt(height), output);
      if (status === 0n) return null;
      if (status !== 1n) throw new Error("Could not read the public outcome scalar");
      return new DataView(memory.buffer, Number(output), 32).getFloat64(24, true);
    } finally {
      if (output > 0n) exports.nw_frame_free(output);
      exports.nw_frame_free(input);
    }
  }

  const archive = {
    capture,
    createReceiptSession(options) { return createPublicOutcomeSession(archive, readScalar, options); },
    get(digest) { return frames.get(digest)?.slice(); },
    clear() { frames.clear(); },
    verify(outcome, frame, ledger = null) {
      return verifyPublicOutcome(outcome, frame.rgba, frame.width, frame.height, frames, ledger);
    },
  };
  return archive;
}

// The task host decides when a response window opens and which rendered
// frames are significant. A receipt is finalized by one accepted action.
function createPublicOutcomeSession(archive, readScalar, { ports, drive, neutralOutcomes = false, multiple = false }) {
  if (!Number.isSafeInteger(ports) || ports < 1 || typeof drive !== "function")
    throw new TypeError("An outcome session requires action ports and a driver");

  const ledger = new Map();
  let nextId = 0;
  let receipt = null;
  let evidence = [];
  let finalized = false;
  let driving = false;
  let owed = false;
  let frameSequence = 0;

  const stamp = () => Math.round(performance.now() * 1000000);
  const copyReceipt = (row) => ({ ...row, ports: [...row.ports],
    ...(row.evidence_digests ? { evidence_digests: [...row.evidence_digests] } : {}) });

  function requireIdleDriver() {
    if (driving) throw new Error("The action driver must return before changing the response window");
  }

  function openFromFrame(frame, keepEvidence = false) {
    frameSequence = frame.frame_seq;
    const id = ++nextId;
    receipt = {
      ok: true, receipt_id: id, trial_seq: id, frame_seq: frameSequence,
      timestamp_ns: frame.timestamp_ns, ports: [], logp: null,
      stimulus_digest: frame.digest, window_open_ns: frame.timestamp_ns,
    };
    if (!keepEvidence) evidence = [frame.digest];
    finalized = false;
    owed = false;
    ledger.set(id, receipt);
    return frame;
  }

  function open() {
    requireIdleDriver();
    return openFromFrame(archive.capture());
  }

  function act(port, logp = null) {
    const selected = multiple && Array.isArray(port) ? [...new Set(port)] : [port];
    if (!receipt || finalized || selected.length === 0 ||
        selected.some(value => !Number.isSafeInteger(value) || value < 0 || value >= ports))
      return { ok: false, receipt_id: null, frame_seq: frameSequence, timestamp_ns: stamp(), ports: [], logp: null };
    // Reserve the action slot before invoking the host driver.
    finalized = true;
    driving = true;
    try {
      drive(multiple ? selected : port);
    } catch (error) {
      finalized = false;
      throw error;
    } finally {
      driving = false;
    }
    receipt = { ...receipt, timestamp_ns: stamp(), ports: selected, logp };
    ledger.set(receipt.receipt_id, receipt);
    owed = true;
    return copyReceipt(receipt);
  }

  function publish({ openNext = false, keepEvidence = false, settleIdle = false, readOutcome = true } = {}) {
    requireIdleDriver();
    const frame = archive.capture();
    const published = settleFrame(frame, settleIdle, readOutcome);
    if (openNext) openFromFrame(frame, keepEvidence);
    return published;
  }

  function settleFrame(frame, settleIdle, readOutcome) {
    frameSequence = frame.frame_seq;
    if (!receipt) return frame;
    evidence.push(frame.digest);
    if (!readOutcome || (!owed && !settleIdle)) return frame;
    const scalar = readScalar(frame);
    if (scalar === null && !neutralOutcomes) return frame;

    owed = false;
    const evidence_digests = [...evidence];
    receipt.stimulus_digest = evidence_digests[0];
    receipt.evidence_digests = evidence_digests;
    receipt.feedback_digest = frame.digest;
    receipt.feedback_frame_seq = frame.frame_seq;
    return { ...frame, outcome: {
      scalar: scalar ?? 0, evidence_digests: [...evidence_digests],
      receipt_id: receipt.receipt_id, frame_seq: frame.frame_seq, timestamp_ns: frame.timestamp_ns,
    } };
  }

  function closeWindow() {
    requireIdleDriver();
    receipt = null;
    evidence = [];
    owed = false;
  }

  return {
    open, act, publish, closeWindow,
    getReceipt(id) { const row = ledger.get(id); return row && copyReceipt(row); },
    verify(outcome, frame) {
      const id = outcome && Object.getOwnPropertyDescriptor(outcome, "receipt_id")?.value;
      if (!ledger.get(id)?.feedback_digest) return false;
      return archive.verify(outcome, frame, ledger);
    },
    clear() {
      closeWindow();
      archive.clear();
      ledger.clear();
    },
  };
}
