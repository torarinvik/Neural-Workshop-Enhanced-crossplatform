import { decode, render } from "./display-list.js";

const EVENT_ACTION = 1n;
const PHASE_RUNNING = 2n;
const PHASE_SCORED = 3n;
const PHASE_DONE = 4n;
const FRAME_CAPACITY = 65536n;
const VERDICT_HOLD_MS = 1000n;
const TASK_PORTS = 4;
const FRAME_HEADER_BYTES = 36;

function decodePort(ports) {
  if (Number.isSafeInteger(ports)) return ports;
  const selected = Array.isArray(ports) ? ports.filter(Number.isSafeInteger)
    : ports && typeof ports === "object"
      ? Object.keys(ports).filter((key) => /^\d+$/.test(key) && ports[key]).map(Number)
      : [];
  return selected.length === 1 ? selected[0] : null;
}

// Use a caller-owned canvas so a stepped run can coexist with interactive play.
export function createCookieThiefEnvironment(exports, context, createArchive, {
  seed = 0, rung = 4, trials = 5, frameHz = 60, beatMs = Math.floor(1000 / frameHz),
  setMs = Math.floor(1000 / frameHz), runtimePorts = TASK_PORTS, adaptive = true,
  coach = true, neutralOutcomes = false, black = false, thinkSeconds = 0,
  frameExport = null,
} = {}) {
  if (Number(thinkSeconds) > 0)
    throw new RangeError("Cookie Thief is already clocked and cannot use a think clock");
  if (!Number.isFinite(frameHz) || frameHz < 10)
    throw new RangeError("Cookie Thief requires at least 10 frames per second");
  const actionCount = runtimePorts === 0 ? TASK_PORTS : runtimePorts;
  if (!Number.isSafeInteger(actionCount) || actionCount < TASK_PORTS)
    throw new RangeError("Cookie Thief requires at least four runtime ports");

  if (frameExport !== null &&
      (typeof SharedArrayBuffer === "undefined" || !(frameExport instanceof SharedArrayBuffer)))
    throw new TypeError("Cookie Thief frame export requires a SharedArrayBuffer");
  const sharedBytes = frameExport === null ? null : new Uint8Array(frameExport);
  const task = exports.nw_api_v1_task_cookie_thief();
  const framePtr = exports.nw_frame_alloc(FRAME_CAPACITY);
  if (framePtr <= 0n) throw new Error("Could not allocate the Cookie Thief display list");

  let handle = 0n;
  let session;
  let tick;
  let clockOffset;
  let sequence;
  let currentFrame;
  let acted;
  let closed = false;
  let events;
  let counters;
  let startedAt;
  const now = () => clockOffset + BigInt(Math.floor(tick * 1000 / frameHz));
  const phase = () => exports.nw_api_v1_cookie_thief_info(handle, 0n);
  const dispatch = (action) => exports.nw_api_v1_dispatch(handle, EVENT_ACTION,
    now(), sequence++, BigInt(action), 0n, 0n, 0n, 0n, 0n, 0n);

  function paint() {
    const { width, height } = context.canvas;
    const length = exports.nw_api_v1_render(handle, framePtr, FRAME_CAPACITY,
      BigInt(black), BigInt(width), BigInt(height));
    if (length <= 0n) throw new Error(`Cookie Thief environment render failed (${length})`);
    const commands = decode(new Uint8Array(exports.memory.buffer, Number(framePtr), Number(length)));
    render(context, commands, { width, height });
  }

  function checkExportCapacity() {
    if (!sharedBytes) return;
    const { width, height } = context.canvas;
    if (sharedBytes.length < FRAME_HEADER_BYTES + width * height * 4)
      throw new RangeError("Cookie Thief frame export buffer is too small for the canvas");
  }

  function publish(options) {
    const frame = session.publish(options);
    if (sharedBytes) {
      // The display list has already been drawn and its scratch space can
      // hold the packed header until the next render.
      const size = exports.nw_frame_export_header(framePtr, BigInt(FRAME_HEADER_BYTES),
        BigInt(frame.frame_seq), BigInt(frame.timestamp_ns), frame.width, frame.height, false);
      if (size !== BigInt(FRAME_HEADER_BYTES)) throw new Error("Could not encode the frame export header");
      sharedBytes.set(frame.rgba, FRAME_HEADER_BYTES);
      sharedBytes.set(new Uint8Array(exports.memory.buffer, Number(framePtr), FRAME_HEADER_BYTES));
    }
    return { ...frame, done: phase() === PHASE_DONE };
  }

  function requireOpen() {
    if (closed) throw new Error("Cookie Thief environment is closed");
  }

  function close() {
    if (closed) return;
    closed = true;
    session?.clear();
    if (handle > 0n) exports.nw_api_v1_destroy(handle);
    exports.nw_frame_free(framePtr);
  }

  function observe() {
    requireOpen();
    const { digest, ...observation } = currentFrame;
    return structuredClone(observation);
  }

  function reset(nextSeed = 0) {
    requireOpen();
    checkExportCapacity();
    const nextHandle = exports.nw_api_v1_create(task, 1n, BigInt(rung), BigInt(trials),
      BigInt(beatMs), BigInt(setMs), BigInt(adaptive), BigInt(coach && neutralOutcomes), BigInt(nextSeed));
    if (nextHandle <= 0n) throw new RangeError(`Cookie Thief environment creation failed (${nextHandle})`);
    if (handle > 0n) exports.nw_api_v1_destroy(handle);
    handle = nextHandle;
    try {
      session?.clear();
      session = createArchive().createReceiptSession({
        ports: neutralOutcomes ? actionCount : TASK_PORTS,
        drive: (port) => { if (port < TASK_PORTS) dispatch(port + 1); },
        neutralOutcomes,
      });
      tick = 0;
      clockOffset = 0n;
      sequence = 0n;
      acted = false;
      events = [];
      counters = { logical_trials: 0, significant_frames: 1, unique_public_outcome_bits: 0,
        dropped_frames: 0, duplicate_frames: 0, action_to_outcome_latency_ms: [] };
      startedAt = performance.now();
      if (dispatch(0) !== 1n) throw new Error("Could not start the Cookie Thief run");
      paint();
      currentFrame = publish();
      return observe();
    } catch (error) {
      close();
      throw error;
    }
  }

  function act(ports, logp = null) {
    requireOpen();
    const receipt = session.act(decodePort(ports), logp);
    acted ||= receipt.ok;
    return receipt;
  }

  function advance() {
    requireOpen();
    const previous = phase();
    if (previous === PHASE_DONE) return observe();
    checkExportCapacity();
    tick++;
    if (previous === PHASE_SCORED) {
      // Keep the verdict visible for one published frame in stepped mode.
      clockOffset += VERDICT_HOLD_MS;
      dispatch(0);
    } else {
      exports.nw_api_v1_advance(handle, now(), 0n, sequence++);
    }
    paint();
    const next = phase();
    const newTrial = next === PHASE_RUNNING && previous !== PHASE_RUNNING;
    currentFrame = publish({
      openNext: next === PHASE_RUNNING && (newTrial || acted),
      keepEvidence: !newTrial,
      settleIdle: !neutralOutcomes && next === PHASE_SCORED,
    });
    acted = false;
    if (next !== PHASE_RUNNING) session.closeWindow();
    counters.significant_frames++;
    if (newTrial) counters.logical_trials++;
    const { outcome, frame_seq, timestamp_ns, done } = currentFrame;
    if (outcome) {
      const receipt = session.getReceipt(outcome.receipt_id);
      counters.unique_public_outcome_bits++;
      counters.action_to_outcome_latency_ms.push((timestamp_ns - receipt.timestamp_ns) / 1e6);
      events.push({ type: "outcome", ...outcome });
    }
    if (done) events.push({ type: "run_end", frame_seq, timestamp_ns });
    return observe();
  }

  try {
    reset(seed);
  } catch (error) {
    close();
    throw error;
  }

  return {
    observe, act, advance, reset, close,
    n_actions: actionCount,
    think_left: 0,
    forfeits: 0,
    step(ports = null) {
      act(ports);
      const observation = advance();
      const delivered = events;
      events = [];
      return [observation, structuredClone(delivered), observation.done];
    },
    accounting: {
      snapshot() {
        const wall_time_s = (performance.now() - startedAt) / 1000;
        return { ...structuredClone(counters), wall_time_s,
          trials_per_s: wall_time_s > 0 ? counters.logical_trials / wall_time_s : 0 };
      },
    },
    getReceipt(id) { return session.getReceipt(id); },
    verify(outcome, frame) { return session.verify(outcome, frame); },
  };
}
