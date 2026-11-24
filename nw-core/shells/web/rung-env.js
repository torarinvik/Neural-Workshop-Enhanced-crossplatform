import { decode, render } from "./display-list.js";

const EVENT_ACTION = 1n;
const PHASE_RUNNING = 1n;
const PHASE_SCORED = 2n;
const PHASE_DONE = 3n;
const PHASE_FLAGGED = 4n;
const FRAME_CAPACITY = 131072n;
const FRAME_HEADER_BYTES = 36;

function decodePort(ports, count, multiple = false) {
  const selected = Number.isSafeInteger(ports) ? [ports]
    : Array.isArray(ports) ? ports.filter(port => Number.isSafeInteger(port) && port >= 0 && port < count)
    : ports && typeof ports === "object"
      ? Object.keys(ports).filter((key) => /^\d+$/.test(key) && ports[key]).map(Number).filter(port => port < count)
      : [];
  return multiple ? selected : (selected.length === 1 ? selected[0] : null);
}

function integerDial(value, fallback, name, taskName) {
  const input = value ?? fallback;
  let integer;
  if (typeof input === "number" && Number.isFinite(input)) {
    integer = BigInt(Math.trunc(input));
  } else if (typeof input === "bigint" || typeof input === "boolean") {
    integer = BigInt(input);
  } else if (typeof input === "string" && /^[+-]?[0-9](?:_?[0-9])*$/.test(input.trim())) {
    integer = BigInt(input.trim().replaceAll("_", ""));
  } else {
    throw new TypeError(`${taskName} ${name} must be an integer or decimal integer string`);
  }
  if (BigInt.asIntN(64, integer) !== integer)
    throw new RangeError(`${taskName} ${name} is outside the signed 64-bit range`);
  return integer;
}

// Use a caller-owned canvas so a stepped run can coexist with interactive play.
function createRungEnvironment(exports, context, createArchive, task, {
  seed = 0, rung = 1, trials = task.trials, frameHz = 60, runtimePorts = task.ports,
  adaptive = true, neutralOutcomes = false, black = false, thinkSeconds = 0,
  refillSeconds = thinkSeconds, frameExport = null, coach = true,
} = {}) {
  const taskName = task.name;
  if (task.clocked && thinkSeconds > 0)
    throw new RangeError(`${taskName} is already clocked and cannot use a think clock`);
  if (task.clocked && frameHz < 10)
    throw new RangeError(`${taskName} requires at least 10 frames per second`);
  if (!Number.isFinite(frameHz) || frameHz <= 0)
    throw new RangeError(`${taskName} requires a positive frame rate`);
  if (!Number.isFinite(thinkSeconds) || !Number.isFinite(refillSeconds) ||
      (thinkSeconds > 0 && refillSeconds < 0))
    throw new RangeError(`${taskName} requires a finite think clock and a nonnegative enabled refill`);
  const startingRung = integerDial(rung, 1, "rung", taskName);
  const rounds = integerDial(trials, task.trials, "trials", taskName);
  const climbs = Boolean(adaptive ?? true);
  const bankCapacity = Math.max(0, thinkSeconds);
  const refill = bankCapacity ? refillSeconds : 0;
  const actionCount = runtimePorts === 0 ? task.ports : runtimePorts;
  if (!Number.isSafeInteger(actionCount) || actionCount < task.ports)
    throw new RangeError(`${taskName} requires at least ${task.ports} runtime ports`);

  if (frameExport !== null &&
      (typeof SharedArrayBuffer === "undefined" || !(frameExport instanceof SharedArrayBuffer)))
    throw new TypeError(`${taskName} frame export requires a SharedArrayBuffer`);
  const sharedBytes = frameExport === null ? null : new Uint8Array(frameExport);
  const frameCapacity = task.frameCapacity ?? FRAME_CAPACITY;
  const framePtr = exports.nw_frame_alloc(frameCapacity);
  if (framePtr <= 0n) throw new Error(`Could not allocate the ${taskName} display list`);

  let handle = 0n;
  let session;
  let driver;
  let currentFrame;
  let acted;
  let closed = false;
  let events;
  let counters;
  let startedAt;
  const phase = () => driver.phase();

  function paint(bank = driver.thinkLeft()) {
    const { width, height } = context.canvas;
    const length = exports.nw_api_v1_render(handle, framePtr, frameCapacity,
      BigInt(black), BigInt(width), BigInt(height));
    if (length <= 0n) throw new Error(`${taskName} environment render failed (${length})`);
    const commands = decode(new Uint8Array(exports.memory.buffer, Number(framePtr), Number(length)));
    render(context, commands, { width, height });
    if (bankCapacity && bank > 0) {
      context.save();
      context.fillStyle = "rgb(96,120,168)";
      context.fillRect(0, 0, width * (bank / bankCapacity), 6);
      context.restore();
    }
  }

  function checkExportCapacity() {
    if (!sharedBytes) return;
    const { width, height } = context.canvas;
    if (sharedBytes.length < FRAME_HEADER_BYTES + width * height * 4)
      throw new RangeError(`${taskName} frame export buffer is too small for the canvas`);
  }

  function publish(options) {
    const frame = session.publish(options);
    const audio = driver.audio?.(framePtr, frameCapacity);
    if (sharedBytes) {
      // The display list has already been drawn and its scratch space can
      // hold the packed header until the next render.
      const size = exports.nw_frame_export_header(framePtr, BigInt(FRAME_HEADER_BYTES),
        BigInt(frame.frame_seq), BigInt(frame.timestamp_ns), frame.width, frame.height, false);
      if (size !== BigInt(FRAME_HEADER_BYTES)) throw new Error("Could not encode the frame export header");
      sharedBytes.set(frame.rgba, FRAME_HEADER_BYTES);
      sharedBytes.set(new Uint8Array(exports.memory.buffer, Number(framePtr), FRAME_HEADER_BYTES));
    }
    return { ...frame, ...audio, done: phase() === PHASE_DONE };
  }

  function requireOpen() {
    if (closed) throw new Error(`${taskName} environment is closed`);
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
    const nextHandle = exports.nw_api_v1_create(task.id(), 1n, startingRung, rounds,
      BigInt(climbs), 1n, BigInt(Boolean(task.coaching && neutralOutcomes && coach)), 0n, integerDial(nextSeed, 0, "seed", taskName));
    if (nextHandle <= 0n) throw new RangeError(`${taskName} environment creation failed (${nextHandle})`);
    if (handle > 0n) exports.nw_api_v1_destroy(handle);
    handle = nextHandle;
    try {
      session?.clear();
      task.prepare?.(handle);
      driver = task.driver(handle, frameHz, bankCapacity, refill);
      session = createArchive().createReceiptSession({
        ports: neutralOutcomes ? actionCount : task.ports,
        drive: (port) => {
          if (task.multiple) {
            const supported = port.filter(value => value < task.ports);
            if (supported.length) driver.act(supported);
          } else if (port < task.ports) driver.act(port);
        },
        multiple: task.multiple,
        neutralOutcomes,
      });
      acted = false;
      events = [];
      counters = { logical_trials: 0, significant_frames: 1, unique_public_outcome_bits: 0,
        dropped_frames: 0, duplicate_frames: 0, action_to_outcome_latency_ms: [] };
      startedAt = performance.now();
      if (driver.start() !== 1n) throw new Error(`Could not start the ${taskName} run`);
      paint();
      currentFrame = publish({ openNext: phase() === PHASE_RUNNING });
      if (currentFrame.done) {
        const { frame_seq, timestamp_ns } = currentFrame;
        events.push({ type: "run_end", frame_seq, timestamp_ns });
      }
      return observe();
    } catch (error) {
      close();
      throw error;
    }
  }

  function act(ports, logp = null) {
    requireOpen();
    const receipt = session.act(decodePort(ports, neutralOutcomes ? actionCount : task.ports, task.multiple), logp);
    acted ||= receipt.ok;
    return receipt;
  }

  function advance() {
    requireOpen();
    const previous = phase();
    if (previous === PHASE_DONE) return observe();
    checkExportCapacity();
    const previousBank = driver.thinkLeft();
    if (driver.step() !== 1n) throw new Error(`Could not step ${taskName}`);
    const next = phase();
    const newTrial = next === PHASE_RUNNING && previous !== PHASE_RUNNING;
    // Python publishes the new deal before displaying its bank refill.
    paint(newTrial ? previousBank : undefined);
    currentFrame = publish({
      openNext: next === PHASE_RUNNING && (newTrial || acted),
      keepEvidence: !newTrial,
      settleIdle: !neutralOutcomes && (next === PHASE_SCORED || next === PHASE_FLAGGED),
      readOutcome: neutralOutcomes || !task.outcomeOnVerdict || next === PHASE_SCORED,
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
    get think_left() { return driver.thinkLeft(); },
    get forfeits() { return driver.forfeits(); },
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


function turnDriver(exports, handle, frameHz, capacity, refill, task) {
  let tick = 0;
  let sequence = 0n;
  const dispatch = (action, value = 0) => exports.nw_api_v1_dispatch(handle, EVENT_ACTION,
    BigInt(Math.floor(tick * 1000 / frameHz)), sequence++, BigInt(action), BigInt(value), 0n, 0n, 0n, 0n, 0n);
  return {
    start() {
      if (task.configure(handle, capacity, refill) !== 1n)
        throw new Error(`Could not configure the ${task.name} think clock`);
      return dispatch(task.answerValue ? 0 : task.ports);
    },
    act: port => task.answerValue ? dispatch(1, port) : dispatch(port),
    step() {
      tick++;
      return task.step(handle, 1 / frameHz);
    },
    phase: () => task.info(handle, 0n),
    thinkLeft: () => task.thinkLeft(handle),
    forfeits: () => Number(task.info(handle, task.forfeitField)),
  };
}

export function createTriageEnvironment(exports, context, createArchive, options) {
  const task = {
    name: "Triage", trials: 5, ports: 17, clocked: false, forfeitField: 14n,
    id: exports.nw_api_v1_task_triage,
    configure: exports.nw_triage_think_configure,
    step: exports.nw_triage_step,
    info: exports.nw_api_v1_triage_info,
    thinkLeft: exports.nw_triage_think_left,
    driver: (handle, frameHz, capacity, refill) => turnDriver(exports, handle, frameHz, capacity, refill, task),
  };
  return createRungEnvironment(exports, context, createArchive, task, options);
}

export function createNotebookEnvironment(exports, context, createArchive, options) {
  const task = {
    name: "Notebook", trials: 3, ports: 13, clocked: false, forfeitField: 18n,
    id: exports.nw_api_v1_task_notebook,
    configure: exports.nw_notebook_think_configure,
    step: exports.nw_notebook_step,
    info: exports.nw_api_v1_notebook_info,
    thinkLeft: exports.nw_notebook_think_left,
    driver: (handle, frameHz, capacity, refill) => turnDriver(exports, handle, frameHz, capacity, refill, task),
  };
  return createRungEnvironment(exports, context, createArchive, task, options);
}

export function createWhereWasItEnvironment(exports, context, createArchive, options) {
  const task = {
    name: "Where Was It?", trials: 8, ports: 31, clocked: false, forfeitField: 13n,
    id: exports.nw_api_v1_task_where_was_it,
    configure: exports.nw_where_was_it_think_configure,
    step: exports.nw_where_was_it_step,
    info: exports.nw_api_v1_where_was_it_info,
    thinkLeft: exports.nw_where_was_it_think_left,
    driver: (handle, frameHz, capacity, refill) => turnDriver(exports, handle, frameHz, capacity, refill, task),
  };
  return createRungEnvironment(exports, context, createArchive, task, options);
}

export function createSameOrMirrorEnvironment(exports, context, createArchive, options) {
  const task = {
    name: "Same or Mirror?", trials: 12, ports: 5, clocked: false, forfeitField: 12n,
    id: exports.nw_api_v1_task_same_or_mirror,
    configure: exports.nw_same_or_mirror_think_configure,
    step: exports.nw_same_or_mirror_step,
    info: exports.nw_api_v1_same_or_mirror_info,
    thinkLeft: exports.nw_same_or_mirror_think_left,
    driver: (handle, frameHz, capacity, refill) => turnDriver(exports, handle, frameHz, capacity, refill, task),
  };
  return createRungEnvironment(exports, context, createArchive, task, options);
}

export function createPointOfViewEnvironment(exports, context, createArchive, options) {
  const task = {
    name: "Point of View", trials: 10, ports: 5, clocked: false, forfeitField: 12n,
    id: exports.nw_api_v1_task_point_of_view,
    configure: exports.nw_point_of_view_think_configure,
    step: exports.nw_point_of_view_step,
    info: exports.nw_api_v1_point_of_view_info,
    thinkLeft: exports.nw_point_of_view_think_left,
    driver: (handle, frameHz, capacity, refill) => turnDriver(exports, handle, frameHz, capacity, refill, task),
  };
  return createRungEnvironment(exports, context, createArchive, task, options);
}

export function createWillItFallEnvironment(exports, context, createArchive, options) {
  const task = {
    name: "Will It Fall?", trials: 10, ports: 8, clocked: false, forfeitField: 12n, answerValue: true,
    id: exports.nw_api_v1_task_will_it_fall,
    configure: exports.nw_falls_think_configure,
    step: exports.nw_falls_step,
    info: exports.nw_falls_info,
    thinkLeft: exports.nw_falls_think_left,
    driver: (handle, frameHz, capacity, refill) => turnDriver(exports, handle, frameHz, capacity, refill, task),
  };
  return createRungEnvironment(exports, context, createArchive, task, options);
}

export function createCaptchaEnvironment(exports, context, createArchive, options) {
  const task = {
    name: "Captcha", trials: 5, ports: 25, clocked: false, forfeitField: 9n,
    id: exports.nw_api_v1_task_captcha,
    configure: exports.nw_captcha_think_configure,
    step: exports.nw_captcha_step,
    info: exports.nw_api_v1_captcha_info,
    thinkLeft: exports.nw_captcha_think_left,
    driver: (handle, frameHz, capacity, refill) => turnDriver(exports, handle, frameHz, capacity, refill, task),
  };
  return createRungEnvironment(exports, context, createArchive, task, options);
}

export function createSignalsEnvironment(exports, context, createArchive, options) {
  const task = {
    name: "Signals", trials: 3, ports: 16, clocked: false, forfeitField: 12n,
    id: exports.nw_api_v1_task_signals,
    configure: exports.nw_signals_think_configure,
    step: exports.nw_signals_step,
    info: exports.nw_api_v1_signals_info,
    thinkLeft: exports.nw_signals_think_left,
    driver: (handle, frameHz, capacity, refill) => turnDriver(exports, handle, frameHz, capacity, refill, task),
  };
  return createRungEnvironment(exports, context, createArchive, task, options);
}

export function createFoldItEnvironment(exports, context, createArchive, options) {
  const task = {
    name: "Fold It", trials: 10, ports: 6, clocked: false, forfeitField: 12n,
    id: exports.nw_api_v1_task_fold_it,
    configure: exports.nw_fold_it_think_configure,
    step: exports.nw_fold_it_step,
    info: exports.nw_api_v1_fold_it_info,
    thinkLeft: exports.nw_fold_it_think_left,
    driver: (handle, frameHz, capacity, refill) => turnDriver(exports, handle, frameHz, capacity, refill, task),
  };
  return createRungEnvironment(exports, context, createArchive, task, options);
}

export function createWhoKnowsWhatEnvironment(exports, context, createArchive, options) {
  const task = {
    name: "Who Knows What?", trials: 10, ports: 4, clocked: false, forfeitField: 12n,
    id: exports.nw_api_v1_task_who_knows_what,
    configure: exports.nw_who_knows_what_think_configure,
    step: exports.nw_who_knows_what_step,
    info: exports.nw_api_v1_who_knows_what_info,
    thinkLeft: exports.nw_who_knows_what_think_left,
    driver: (handle, frameHz, capacity, refill) => turnDriver(exports, handle, frameHz, capacity, refill, task),
  };
  return createRungEnvironment(exports, context, createArchive, task, options);
}

export function createSonarEnvironment(exports, context, createArchive, options) {
  const task = {
    name: "Sonar", trials: 8, ports: 6, frameCapacity: 1048576n, clocked: false, forfeitField: 14n,
    id: exports.nw_api_v1_task_sonar,
    configure: exports.nw_sonar_think_configure,
    step: exports.nw_sonar_step,
    info: exports.nw_api_v1_sonar_info,
    thinkLeft: exports.nw_sonar_think_left,
    driver: (handle, frameHz, capacity, refill) => turnDriver(exports, handle, frameHz, capacity, refill, task),
  };
  return createRungEnvironment(exports, context, createArchive, task, options);
}

export function createGambleEnvironment(exports, context, createArchive, options) {
  const task = {
    name: "Gamble", trials: 5, ports: 9, frameCapacity: 1048576n, clocked: false, forfeitField: 10n,
    id: exports.nw_api_v1_task_gamble,
    configure: exports.nw_gamble_think_configure,
    step: exports.nw_gamble_step,
    info: exports.nw_api_v1_gamble_info,
    thinkLeft: exports.nw_gamble_think_left,
    driver: (handle, frameHz, capacity, refill) => turnDriver(exports, handle, frameHz, capacity, refill, task),
  };
  return createRungEnvironment(exports, context, createArchive, task, options);
}

export function createBluffEnvironment(exports, context, createArchive, options) {
  const task = {
    name: "Bluff", trials: 5, ports: 2, frameCapacity: 1048576n, clocked: false, forfeitField: 10n,
    id: exports.nw_api_v1_task_bluff,
    configure: exports.nw_bluff_think_configure,
    step: exports.nw_bluff_step,
    info: exports.nw_api_v1_bluff_info,
    thinkLeft: exports.nw_bluff_think_left,
    driver: (handle, frameHz, capacity, refill) => turnDriver(exports, handle, frameHz, capacity, refill, task),
  };
  return createRungEnvironment(exports, context, createArchive, task, options);
}

export function createExploreOrExploitEnvironment(exports, context, createArchive, options) {
  const task = {
    name: "Explore or Exploit", trials: 3, ports: 8, frameCapacity: 1048576n, clocked: false, forfeitField: 10n,
    id: exports.nw_api_v1_task_explore_exploit,
    configure: exports.nw_explore_exploit_think_configure,
    step: exports.nw_explore_exploit_step,
    info: exports.nw_api_v1_explore_exploit_info,
    thinkLeft: exports.nw_explore_exploit_think_left,
    driver: (handle, frameHz, capacity, refill) => turnDriver(exports, handle, frameHz, capacity, refill, task),
  };
  return createRungEnvironment(exports, context, createArchive, task, options);
}

export function createInsideOrOutEnvironment(exports, context, createArchive, options) {
  const task = {
    name: "Inside or Out?", trials: 5, ports: 2, clocked: false, forfeitField: 12n,
    id: exports.nw_api_v1_task_inside_or_out,
    configure: exports.nw_inside_or_out_think_configure,
    step: exports.nw_inside_or_out_step,
    info: exports.nw_api_v1_inside_or_out_info,
    thinkLeft: exports.nw_inside_or_out_think_left,
    driver: (handle, frameHz, capacity, refill) => turnDriver(exports, handle, frameHz, capacity, refill, task),
  };
  return createRungEnvironment(exports, context, createArchive, task, options);
}
export function createTouchingEnvironment(exports, context, createArchive, options) {
  const task = {
    name: "Touching?", trials: 5, ports: 6, clocked: false, forfeitField: 12n,
    id: exports.nw_api_v1_task_touching,
    configure: exports.nw_touching_think_configure,
    step: exports.nw_touching_step,
    info: exports.nw_api_v1_touching_info,
    thinkLeft: exports.nw_touching_think_left,
    driver: (handle, frameHz, capacity, refill) => turnDriver(exports, handle, frameHz, capacity, refill, task),
  };
  return createRungEnvironment(exports, context, createArchive, task, options);
}
export function createCrossingsEnvironment(exports, context, createArchive, options) {
  const task = {
    name: "Crossings", trials: 5, ports: 7, clocked: false, forfeitField: 12n,
    id: exports.nw_api_v1_task_crossings,
    configure: exports.nw_crossings_think_configure,
    step: exports.nw_crossings_step,
    info: exports.nw_api_v1_crossings_info,
    thinkLeft: exports.nw_crossings_think_left,
    driver: (handle, frameHz, capacity, refill) => turnDriver(exports, handle, frameHz, capacity, refill, task),
  };
  return createRungEnvironment(exports, context, createArchive, task, options);
}

function clockedDriver(handle, frameHz, dispatch, info, start = 2) {
  let seconds = 0;
  const event = port => dispatch(handle, seconds, BigInt(port));
  return {
    start: () => event(start),
    act: event,
    step() {
      seconds += 1 / frameHz;
      return event(-1);
    },
    phase: () => info(handle, 0n),
    thinkLeft: () => 0,
    forfeits: () => 0,
  };
}

export function createWhichIsNearerEnvironment(exports, context, createArchive, options) {
  return createRungEnvironment(exports, context, createArchive, {
    name: "Which Is Nearer?", trials: 12, ports: 6, clocked: true,
    id: exports.nw_api_v1_task_which_is_nearer,
    driver: (handle, frameHz) => clockedDriver(handle, frameHz,
      exports.nw_which_is_nearer_agent_event, exports.nw_api_v1_which_is_nearer_info, 6),
  }, options);
}

export function createShapeFromMotionEnvironment(exports, context, createArchive, options) {
  return createRungEnvironment(exports, context, createArchive, {
    name: "Shape from Motion", trials: 12, ports: 6, clocked: true,
    id: exports.nw_api_v1_task_shape_from_motion,
    driver: (handle, frameHz) => clockedDriver(handle, frameHz,
      exports.nw_sfm_agent_event, exports.nw_sfm_info, 6),
  }, options);
}

export function createDamKeeperEnvironment(exports, context, createArchive, options) {
  return createRungEnvironment(exports, context, createArchive, {
    name: "Dam Keeper", trials: 5, ports: 6, clocked: true,
    id: exports.nw_api_v1_task_dam_keeper,
    driver: (handle, frameHz) => clockedDriver(handle, frameHz,
      exports.nw_dam_keeper_agent_event, exports.nw_api_v1_dam_keeper_info, 6),
  }, options);
}

export function createDispatchEnvironment(exports, context, createArchive, options) {
  return createRungEnvironment(exports, context, createArchive, {
    name: "Dispatch", trials: 3, ports: 18, clocked: true, coaching: true,
    id: exports.nw_api_v1_task_dispatch,
    driver: (handle, frameHz) => clockedDriver(handle, frameHz,
      exports.nw_dispatch_agent_event, exports.nw_api_v1_dispatch_info, 18),
  }, options);
}

export function createFirebreakEnvironment(exports, context, createArchive, options) {
  return createRungEnvironment(exports, context, createArchive, {
    name: "Firebreak", trials: 5, ports: 9, frameCapacity: 1048576n, clocked: true,
    id: exports.nw_api_v1_task_firebreak,
    driver: (handle, frameHz) => clockedDriver(handle, frameHz,
      exports.nw_firebreak_agent_event, exports.nw_api_v1_firebreak_info, 9),
  }, options);
}

export function createCrossroadsEnvironment(exports, context, createArchive, options) {
  return createRungEnvironment(exports, context, createArchive, {
    name: "Crossroads", trials: 5, ports: 4, frameCapacity: 1048576n, clocked: true,
    id: exports.nw_api_v1_task_crossroads,
    driver: (handle, frameHz) => clockedDriver(handle, frameHz,
      exports.nw_crossroads_agent_event, exports.nw_api_v1_crossroads_info, 4),
  }, options);
}

export function createRailYardEnvironment(exports, context, createArchive, options) {
  return createRungEnvironment(exports, context, createArchive, {
    name: "Rail Yard", trials: 5, ports: 17, frameCapacity: 1048576n, clocked: true,
    id: exports.nw_api_v1_task_railyard,
    driver: (handle, frameHz) => clockedDriver(handle, frameHz,
      exports.nw_railyard_agent_event, exports.nw_api_v1_railyard_info, 17),
  }, options);
}

export function createAirTrafficEnvironment(exports, context, createArchive, options) {
  return createRungEnvironment(exports, context, createArchive, {
    name: "Air Traffic", trials: 5, ports: 12, frameCapacity: 1048576n, clocked: true,
    id: exports.nw_api_v1_task_airtraffic,
    driver: (handle, frameHz) => clockedDriver(handle, frameHz,
      exports.nw_airtraffic_agent_event, exports.nw_api_v1_airtraffic_info, 12),
  }, options);
}

export function createEscortEnvironment(exports, context, createArchive, options) {
  return createRungEnvironment(exports, context, createArchive, {
    name: "Escort", trials: 5, ports: 6, frameCapacity: 1048576n, clocked: true,
    id: exports.nw_api_v1_task_escort,
    driver: (handle, frameHz) => clockedDriver(handle, frameHz,
      exports.nw_escort_agent_event, exports.nw_api_v1_escort_info, 6),
  }, options);
}

export function createSokobanLiveEnvironment(exports, context, createArchive, options) {
  return createRungEnvironment(exports, context, createArchive, {
    name: "Sokoban Live", trials: 5, ports: 4, frameCapacity: 1048576n, clocked: true,
    id: exports.nw_api_v1_task_sokobanlive,
    driver: (handle, frameHz) => clockedDriver(handle, frameHz,
      exports.nw_sokobanlive_agent_event, exports.nw_api_v1_sokobanlive_info, 4),
  }, options);
}

export function createKitchenEnvironment(exports, context, createArchive, options) {
  return createRungEnvironment(exports, context, createArchive, {
    name: "Kitchen", trials: 5, ports: 13, frameCapacity: 1048576n, clocked: true,
    id: exports.nw_api_v1_task_kitchen,
    driver: (handle, frameHz) => clockedDriver(handle, frameHz,
      exports.nw_kitchen_agent_event, exports.nw_api_v1_kitchen_info, 13),
  }, options);
}

export function createCraneEnvironment(exports, context, createArchive, options) {
  return createRungEnvironment(exports, context, createArchive, {
    name: "Crane", trials: 5, ports: 5, frameCapacity: 1048576n, clocked: true,
    id: exports.nw_api_v1_task_crane,
    driver: (handle, frameHz) => clockedDriver(handle, frameHz,
      exports.nw_crane_agent_event, exports.nw_api_v1_crane_info, 5),
  }, options);
}

export function createFerryEnvironment(exports, context, createArchive, options) {
  return createRungEnvironment(exports, context, createArchive, {
    name: "Ferry", trials: 5, ports: 6, frameCapacity: 1048576n, clocked: true,
    id: exports.nw_api_v1_task_ferry,
    driver: (handle, frameHz) => clockedDriver(handle, frameHz,
      exports.nw_ferry_agent_event, exports.nw_api_v1_ferry_info, 6),
  }, options);
}

export function createDockingEnvironment(exports, context, createArchive, options) {
  return createRungEnvironment(exports, context, createArchive, {
    name: "Docking", trials: 5, ports: 12, frameCapacity: 1048576n, clocked: true,
    id: exports.nw_api_v1_task_docking,
    driver: (handle, frameHz) => clockedDriver(handle, frameHz,
      exports.nw_docking_agent_event, exports.nw_api_v1_docking_info, 12),
  }, options);
}

export function createUnicycleEnvironment(exports, context, createArchive, options) {
  return createRungEnvironment(exports, context, createArchive, {
    name: "Unicycle", trials: 5, ports: 8, frameCapacity: 1048576n, clocked: true,
    id: exports.nw_api_v1_task_unicycle,
    driver: (handle, frameHz) => clockedDriver(handle, frameHz,
      exports.nw_unicycle_agent_event, exports.nw_api_v1_unicycle_info, 8),
  }, options);
}

export function createRoverEnvironment(exports, context, createArchive, options) {
  return createRungEnvironment(exports, context, createArchive, {
    name: "Rover", trials: 5, ports: 4, frameCapacity: 1048576n, clocked: true,
    id: exports.nw_api_v1_task_rover,
    driver: (handle, frameHz) => clockedDriver(handle, frameHz,
      exports.nw_rover_agent_event, exports.nw_api_v1_rover_info, 4),
  }, options);
}

export function createMorningRoundEnvironment(exports, context, createArchive, options) {
  return createRungEnvironment(exports, context, createArchive, {
    name: "Morning Round", trials: 5, ports: 6, frameCapacity: 1048576n, clocked: true,
    id: exports.nw_api_v1_task_morning_round,
    driver: (handle, frameHz) => clockedDriver(handle, frameHz,
      exports.nw_morning_round_agent_event, exports.nw_api_v1_morning_round_info, 6),
  }, options);
}

export function createHeavierEnvironment(exports, context, createArchive, options) {
  return createRungEnvironment(exports, context, createArchive, {
    name: "Heavier", trials: 5, ports: 8, frameCapacity: 1048576n, clocked: true,
    id: exports.nw_api_v1_task_heavier,
    driver: (handle, frameHz) => clockedDriver(handle, frameHz,
      exports.nw_heavier_agent_event, exports.nw_api_v1_heavier_info, 8),
  }, options);
}

export function createCrazyCogEnvironment(exports, context, createArchive, options) {
  return createRungEnvironment(exports, context, createArchive, {
    name: "Crazy Cog", trials: 5, ports: 17, frameCapacity: 1048576n, clocked: true,
    id: exports.nw_api_v1_task_crazy_cog,
    driver: (handle, frameHz) => clockedDriver(handle, frameHz,
      exports.nw_crazy_cog_agent_event, exports.nw_api_v1_crazy_cog_info, 17),
  }, options);
}

export function createPotterEnvironment(exports, context, createArchive, options) {
  return createRungEnvironment(exports, context, createArchive, {
    name: "Potter's Wheel", trials: 5, ports: 17, frameCapacity: 1048576n, clocked: true,
    id: exports.nw_api_v1_task_potters_wheel,
    driver: (handle, frameHz) => clockedDriver(handle, frameHz,
      exports.nw_potters_wheel_agent_event, exports.nw_api_v1_potters_wheel_info, 17),
  }, options);
}

export function createConductorEnvironment(exports, context, createArchive, options) {
  return createRungEnvironment(exports, context, createArchive, {
    name: "Conductor", trials: 5, ports: 16, frameCapacity: 1048576n, clocked: true,
    id: exports.nw_api_v1_task_conductor,
    driver: (handle, frameHz) => clockedDriver(handle, frameHz,
      exports.nw_conductor_agent_event, exports.nw_api_v1_conductor_info, 16),
  }, options);
}

export function createTightropeEnvironment(exports, context, createArchive, options) {
  return createRungEnvironment(exports, context, createArchive, {
    name: "Tightrope", trials: 5, ports: 15, frameCapacity: 1048576n, clocked: true,
    id: exports.nw_api_v1_task_tightrope,
    driver: (handle, frameHz) => clockedDriver(handle, frameHz,
      exports.nw_tightrope_agent_event, exports.nw_api_v1_tightrope_info, 15),
  }, options);
}

export function createSignPainterEnvironment(exports, context, createArchive, options) {
  return createRungEnvironment(exports, context, createArchive, {
    name: "Sign Painter", trials: 5, ports: 19, frameCapacity: 1048576n, clocked: true,
    id: exports.nw_api_v1_task_sign_painter,
    driver: (handle, frameHz) => clockedDriver(handle, frameHz,
      exports.nw_sign_painter_agent_event, exports.nw_api_v1_sign_painter_info, 19),
  }, options);
}

export function createBartenderEnvironment(exports, context, createArchive, options) {
  return createRungEnvironment(exports, context, createArchive, {
    name: "Bartender", trials: 5, ports: 15, frameCapacity: 1048576n, clocked: true,
    id: exports.nw_api_v1_task_bartender,
    driver: (handle, frameHz) => clockedDriver(handle, frameHz,
      exports.nw_bartender_agent_event, exports.nw_api_v1_bartender_info, 15),
  }, options);
}

export function createLockPickEnvironment(exports, context, createArchive, options) {
  return createRungEnvironment(exports, context, createArchive, {
    name: "Lock Pick", trials: 5, ports: 15, frameCapacity: 1048576n, clocked: true,
    id: exports.nw_api_v1_task_lock_pick,
    driver: (handle, frameHz) => clockedDriver(handle, frameHz,
      exports.nw_lock_pick_agent_event, exports.nw_api_v1_lock_pick_info, 15),
  }, options);
}

export function createAirHockeyEnvironment(exports, context, createArchive, options) {
  return createRungEnvironment(exports, context, createArchive, {
    name: "Air Hockey", trials: 5, ports: 16, frameCapacity: 1048576n, clocked: true,
    id: exports.nw_api_v1_task_air_hockey,
    driver: (handle, frameHz) => clockedDriver(handle, frameHz,
      exports.nw_air_hockey_agent_event, exports.nw_api_v1_air_hockey_info, 16),
  }, options);
}

export function createSemaphoreEnvironment(exports, context, createArchive, options) {
  return createRungEnvironment(exports, context, createArchive, {
    name: "Semaphore", trials: 5, ports: 40, frameCapacity: 1048576n, clocked: true,
    id: exports.nw_api_v1_task_semaphore,
    driver: (handle, frameHz) => clockedDriver(handle, frameHz,
      exports.nw_semaphore_agent_event, exports.nw_api_v1_semaphore_info, 40),
  }, options);
}

export function createShadowPuppetsEnvironment(exports, context, createArchive, options) {
  return createRungEnvironment(exports, context, createArchive, {
    name: "Shadow Puppets", trials: 5, ports: 16, frameCapacity: 1048576n, clocked: true,
    id: exports.nw_api_v1_task_shadow_puppets,
    driver: (handle, frameHz) => clockedDriver(handle, frameHz,
      exports.nw_shadow_puppets_agent_event, exports.nw_api_v1_shadow_puppets_info, 16),
  }, options);
}

export function createNightWatchEnvironment(exports, context, createArchive, options) {
  return createRungEnvironment(exports, context, createArchive, {
    name: "Night Watch", trials: 5, ports: 16, frameCapacity: 1048576n, clocked: true,
    id: exports.nw_api_v1_task_night_watch,
    driver: (handle, frameHz) => clockedDriver(handle, frameHz,
      exports.nw_night_watch_agent_event, exports.nw_api_v1_night_watch_info, 16),
  }, options);
}

export function createKerbsideEnvironment(exports, context, createArchive, options) {
  return createRungEnvironment(exports, context, createArchive, {
    name: "Kerbside", trials: 5, ports: 2, frameCapacity: 1048576n, clocked: true,
    id: exports.nw_api_v1_task_kerbside,
    driver: (handle, frameHz) => clockedDriver(handle, frameHz,
      exports.nw_kerbside_agent_event, exports.nw_api_v1_kerbside_info, 2),
  }, options);
}

export function createSteadicamEnvironment(exports, context, createArchive, options) {
  return createRungEnvironment(exports, context, createArchive, {
    name: "Steadicam", trials: 5, ports: 6, frameCapacity: 1048576n, clocked: true,
    id: exports.nw_api_v1_task_steadicam,
    driver: (handle, frameHz) => clockedDriver(handle, frameHz,
      exports.nw_steadicam_agent_event, exports.nw_api_v1_steadicam_info, 6),
  }, options);
}

export function createFreeKickEnvironment(exports, context, createArchive, options) {
  return createRungEnvironment(exports, context, createArchive, {
    name: "Free Kick", trials: 5, ports: 9, frameCapacity: 1048576n, clocked: true,
    id: exports.nw_api_v1_task_free_kick,
    driver: (handle, frameHz) => clockedDriver(handle, frameHz,
      exports.nw_free_kick_agent_event, exports.nw_api_v1_free_kick_info, 9),
  }, options);
}

export function createByEarEnvironment(exports, context, createArchive, options) {
  return createRungEnvironment(exports, context, createArchive, {
    name: "By Ear", trials: 5, ports: 13, frameCapacity: 1048576n, clocked: true,
    id: exports.nw_api_v1_task_by_ear,
    driver: (handle, frameHz) => clockedDriver(handle, frameHz,
      exports.nw_by_ear_agent_event, exports.nw_api_v1_by_ear_info, 13),
  }, options);
}

export function createPianoTunerEnvironment(exports, context, createArchive, options) {
  return createRungEnvironment(exports, context, createArchive, {
    name: "Piano Tuner", trials: 5, ports: 5, frameCapacity: 1048576n, clocked: true,
    id: exports.nw_api_v1_task_piano_tuner,
    driver: (handle, frameHz) => clockedDriver(handle, frameHz,
      exports.nw_piano_tuner_agent_event, exports.nw_api_v1_piano_tuner_info, 5),
  }, options);
}

export function createCricketHuntEnvironment(exports, context, createArchive, options) {
  return createRungEnvironment(exports, context, createArchive, {
    name: "Cricket Hunt", trials: 5, ports: 7, frameCapacity: 1048576n, clocked: true,
    id: exports.nw_api_v1_task_cricket_hunt,
    driver: (handle, frameHz) => clockedDriver(handle, frameHz,
      exports.nw_cricket_hunt_agent_event, exports.nw_api_v1_cricket_hunt_info, 7),
  }, options);
}

export function createClawMachineEnvironment(exports, context, createArchive, options) {
  return createRungEnvironment(exports, context, createArchive, {
    name: "Claw Machine", trials: 5, ports: 5, frameCapacity: 1048576n, clocked: true,
    id: exports.nw_api_v1_task_claw_machine,
    driver: (handle, frameHz) => clockedDriver(handle, frameHz,
      exports.nw_claw_machine_agent_event, exports.nw_api_v1_claw_machine_info, 5),
  }, options);
}

export function createGloveEnvironment(exports, context, createArchive, options) {
  return createRungEnvironment(exports, context, createArchive, {
    name: "Glove", trials: 5, ports: 4, frameCapacity: 1048576n, clocked: true,
    id: exports.nw_api_v1_task_glove,
    driver: (handle, frameHz) => clockedDriver(handle, frameHz,
      exports.nw_glove_agent_event, exports.nw_api_v1_glove_info, 4),
  }, options);
}

export function createCipherAbyssEnvironment(exports, context, createArchive, options) {
  return createRungEnvironment(exports, context, createArchive, {
    name: "The Cipher Abyss", trials: 5, ports: 37, frameCapacity: 1048576n, clocked: true,
    id: exports.nw_api_v1_task_cipher_abyss,
    driver: (handle, frameHz) => clockedDriver(handle, frameHz,
      exports.nw_cipher_abyss_agent_event, exports.nw_api_v1_cipher_abyss_info, 37),
  }, options);
}

export function createFullStopEnvironment(exports, context, createArchive, options) {
  return createRungEnvironment(exports, context, createArchive, {
    name: "Full Stop", trials: 5, ports: 16, frameCapacity: 1048576n, clocked: true,
    id: exports.nw_api_v1_task_full_stop,
    driver: (handle, frameHz) => clockedDriver(handle, frameHz,
      exports.nw_full_stop_agent_event, exports.nw_api_v1_full_stop_info, 16),
  }, options);
}

export function attachPassageCaches(exports, load, handle, caches) {
  const pointers = [];
  try {
    const spans = [];
    for (const cache of caches) {
      const size = BigInt(cache.byteLength);
      const pointer = size ? exports.nw_frame_alloc(size) : 0n;
      if (size && !pointer) throw new Error("Could not allocate passage cache.");
      pointers.push(pointer);
      if (size) new Uint8Array(exports.memory.buffer, Number(pointer), cache.byteLength).set(cache);
      spans.push(pointer, size);
    }
    if (load(handle, ...spans) !== 1n) throw new Error("Passage caches rejected.");
  } finally {
    for (const pointer of pointers) if (pointer) exports.nw_frame_free(pointer);
  }
}

export function createMissingWordEnvironment(exports, context, createArchive, options) {
  return createPassageEnvironment(exports, context, createArchive, options, "missing_word", "The Missing Word");
}

export function createProofreaderEnvironment(exports, context, createArchive, options) {
  return createPassageEnvironment(exports, context, createArchive, options, "proofreader", "The Proofreader");
}

function createPassageEnvironment(exports, context, createArchive, options, task, name) {
  const supplied = options?.passageCaches;
  const cacheFiles = ["passages", "sentences", "lexicon"].map(key => {
    const bytes = supplied?.[key];
    if (bytes === undefined) return new Uint8Array();
    if (bytes instanceof ArrayBuffer) return new Uint8Array(bytes);
    if (bytes instanceof Uint8Array) return bytes;
    throw new TypeError(`Invalid ${key} cache`);
  });
  return createRungEnvironment(exports, context, createArchive, {
    name, trials: 5, ports: 16, frameCapacity: 1048576n, clocked: true,
    id: exports[`nw_api_v1_task_${task}`],
    prepare: supplied ? handle => attachPassageCaches(exports, exports[`nw_${task}_load`], handle, cacheFiles) : undefined,
    driver: (handle, frameHz) => clockedDriver(handle, frameHz,
      exports[`nw_${task}_agent_event`], exports[`nw_api_v1_${task}_info`], 16),
  }, options);
}

export function createFiguresOfSpeechEnvironment(exports, context, createArchive, options) {
  const source = options?.questionCache;
  if (source !== undefined && !(source instanceof ArrayBuffer) && !(source instanceof Uint8Array))
    throw new TypeError("Invalid questions.jsonl cache");
  const cache = source instanceof ArrayBuffer ? new Uint8Array(source) : source;
  return createRungEnvironment(exports, context, createArchive, {
    name: "Figures of Speech", trials: 5, ports: 8, frameCapacity: 1048576n, clocked: true,
    id: exports.nw_api_v1_task_figures_of_speech,
    prepare: cache ? handle => attachPassageCaches(exports, exports.nw_figures_of_speech_load, handle, [cache]) : undefined,
    driver: (handle, frameHz) => clockedDriver(handle, frameHz,
      exports.nw_figures_of_speech_agent_event, exports.nw_api_v1_figures_of_speech_info, 8),
  }, options);
}

export function createBetweenTheLinesEnvironment(exports, context, createArchive, options) {
  const source = options?.questionCache;
  if (source !== undefined && !(source instanceof ArrayBuffer) && !(source instanceof Uint8Array))
    throw new TypeError("Invalid questions.jsonl cache");
  const cache = source instanceof ArrayBuffer ? new Uint8Array(source) : source;
  return createRungEnvironment(exports, context, createArchive, {
    name: "Between the Lines", trials: 5, ports: 8, frameCapacity: 1048576n, clocked: true,
    id: exports.nw_api_v1_task_between_the_lines,
    prepare: cache ? handle => attachPassageCaches(exports, exports.nw_between_the_lines_load, handle, [cache]) : undefined,
    driver: (handle, frameHz) => clockedDriver(handle, frameHz,
      exports.nw_between_the_lines_agent_event, exports.nw_api_v1_between_the_lines_info, 8),
  }, options);
}

export function createSocialSenseEnvironment(exports, context, createArchive, options) {
  const source = options?.questionCache;
  if (source !== undefined && !(source instanceof ArrayBuffer) && !(source instanceof Uint8Array))
    throw new TypeError("Invalid questions.jsonl cache");
  const cache = source instanceof ArrayBuffer ? new Uint8Array(source) : source;
  return createRungEnvironment(exports, context, createArchive, {
    name: "Social Sense", trials: 5, ports: 8, frameCapacity: 1048576n, clocked: true,
    id: exports.nw_api_v1_task_social_sense,
    prepare: cache ? handle => attachPassageCaches(exports, exports.nw_social_sense_load, handle, [cache]) : undefined,
    driver: (handle, frameHz) => clockedDriver(handle, frameHz,
      exports.nw_social_sense_agent_event, exports.nw_api_v1_social_sense_info, 8),
  }, options);
}

export function createBadArgumentEnvironment(exports, context, createArchive, options) {
  const source = options?.questionCache;
  if (source !== undefined && !(source instanceof ArrayBuffer) && !(source instanceof Uint8Array))
    throw new TypeError("Invalid questions.jsonl cache");
  const cache = source instanceof ArrayBuffer ? new Uint8Array(source) : source;
  return createRungEnvironment(exports, context, createArchive, {
    name: "Bad Argument", trials: 5, ports: 8, frameCapacity: 1048576n, clocked: true,
    id: exports.nw_api_v1_task_bad_argument,
    prepare: cache ? handle => attachPassageCaches(exports, exports.nw_bad_argument_load, handle, [cache]) : undefined,
    driver: (handle, frameHz) => clockedDriver(handle, frameHz,
      exports.nw_bad_argument_agent_event, exports.nw_api_v1_bad_argument_info, 8),
  }, options);
}

export function createWhichFeelingEnvironment(exports, context, createArchive, options) {
  const source = options?.commentCache;
  if (source !== undefined && !(source instanceof ArrayBuffer) && !(source instanceof Uint8Array))
    throw new TypeError("Invalid goemotions.tsv cache");
  const cache = source instanceof ArrayBuffer ? new Uint8Array(source) : source;
  return createRungEnvironment(exports, context, createArchive, {
    name: "Which Feeling", trials: 5, ports: 8, frameCapacity: 1048576n, clocked: true,
    id: exports.nw_api_v1_task_which_feeling,
    prepare: cache ? handle => attachPassageCaches(exports, exports.nw_which_feeling_load, handle, [cache]) : undefined,
    driver: (handle, frameHz) => clockedDriver(handle, frameHz,
      exports.nw_which_feeling_agent_event, exports.nw_api_v1_which_feeling_info, 8),
  }, options);
}

export function createHowStronglyEnvironment(exports, context, createArchive, options) {
  const source = options?.dialogueCache;
  if (source !== undefined && !(source instanceof ArrayBuffer) && !(source instanceof Uint8Array))
    throw new TypeError("Invalid eqbench.jsonl cache");
  const cache = source instanceof ArrayBuffer ? new Uint8Array(source) : source;
  return createRungEnvironment(exports, context, createArchive, {
    name: "How Strongly", trials: 5, ports: 8, frameCapacity: 1048576n, clocked: true,
    id: exports.nw_api_v1_task_how_strongly,
    prepare: cache ? handle => attachPassageCaches(exports, exports.nw_how_strongly_load, handle, [cache]) : undefined,
    driver: (handle, frameHz) => clockedDriver(handle, frameHz,
      exports.nw_how_strongly_agent_event, exports.nw_api_v1_how_strongly_info, 8),
  }, options);
}

export function createReadingPeopleEnvironment(exports, context, createArchive, options) {
  const source = options?.storyCache;
  if (source !== undefined && !(source instanceof ArrayBuffer) && !(source instanceof Uint8Array))
    throw new TypeError("Invalid emobench.jsonl cache");
  const cache = source instanceof ArrayBuffer ? new Uint8Array(source) : source;
  return createRungEnvironment(exports, context, createArchive, {
    name: "Reading People", trials: 5, ports: 8, frameCapacity: 1048576n, clocked: true,
    id: exports.nw_api_v1_task_reading_people,
    prepare: cache ? handle => attachPassageCaches(exports, exports.nw_reading_people_load, handle, [cache]) : undefined,
    driver: (handle, frameHz) => clockedDriver(handle, frameHz,
      exports.nw_reading_people_agent_event, exports.nw_api_v1_reading_people_info, 8),
  }, options);
}

export function createSecondThoughtsEnvironment(exports, context, createArchive, options) {
  return createRungEnvironment(exports, context, createArchive, {
    name: "Second Thoughts", trials: 5, ports: 8, frameCapacity: 1048576n, clocked: true,
    id: exports.nw_api_v1_task_second_thoughts,
    driver: (handle, frameHz) => clockedDriver(handle, frameHz,
      exports.nw_second_thoughts_agent_event, exports.nw_api_v1_second_thoughts_info, 8),
  }, options);
}

export function createWhyTheyFeelEnvironment(exports, context, createArchive, options) {
  return createRungEnvironment(exports, context, createArchive, {
    name: "Why They Feel", trials: 5, ports: 8, frameCapacity: 1048576n, clocked: true,
    id: exports.nw_api_v1_task_why_they_feel,
    driver: (handle, frameHz) => clockedDriver(handle, frameHz,
      exports.nw_why_they_feel_agent_event, exports.nw_api_v1_why_they_feel_info, 8),
  }, options);
}

export function createToneOfVoiceEnvironment(exports, context, createArchive, options) {
  return createRungEnvironment(exports, context, createArchive, {
    name: "Tone of Voice", trials: 5, ports: 8, frameCapacity: 1048576n, clocked: true,
    id: exports.nw_api_v1_task_tone_of_voice,
    driver: (handle, frameHz) => clockedDriver(handle, frameHz,
      exports.nw_tone_of_voice_agent_event, exports.nw_api_v1_tone_of_voice_info, 8),
  }, options);
}

// Browser: 12 pointer moves, a click and two scrolls; port 15 starts a run.
export function createBrowserEnvironment(exports, context, createArchive, options) {
  return createRungEnvironment(exports, context, createArchive, {
    name: "Browser", trials: 5, ports: 15, frameCapacity: 1048576n, clocked: true,
    id: exports.nw_api_v1_task_browser,
    driver: (handle, frameHz) => clockedDriver(handle, frameHz,
      exports.nw_browser_agent_event, exports.nw_api_v1_browser_info, 15),
  }, options);
}

// Spreadsheet: Browser's ports -- 12 pointer moves, a click and two
// scrolls; port 15 starts a run.
export function createSpreadsheetEnvironment(exports, context, createArchive, options) {
  return createRungEnvironment(exports, context, createArchive, {
    name: "Spreadsheet", trials: 5, ports: 15, frameCapacity: 1048576n, clocked: true,
    id: exports.nw_api_v1_task_spreadsheet,
    driver: (handle, frameHz) => clockedDriver(handle, frameHz,
      exports.nw_spreadsheet_agent_event, exports.nw_api_v1_spreadsheet_info, 15),
  }, options);
}

// Errands: Browser's ports -- 12 pointer moves, a click and two scrolls;
// port 15 starts a run.
export function createErrandsEnvironment(exports, context, createArchive, options) {
  return createRungEnvironment(exports, context, createArchive, {
    name: "Errands", trials: 3, ports: 15, frameCapacity: 1048576n, clocked: true,
    id: exports.nw_api_v1_task_errands,
    driver: (handle, frameHz) => clockedDriver(handle, frameHz,
      exports.nw_errands_agent_event, exports.nw_api_v1_errands_info, 15),
  }, options);
}

// Manual: 21 ports name places on the panel -- six switches, two to each
// of four knobs (down, up), six buttons -- and Finish; port 21 starts a run.
export function createManualEnvironment(exports, context, createArchive, options) {
  return createRungEnvironment(exports, context, createArchive, {
    name: "Manual", trials: 5, ports: 21, frameCapacity: 1048576n, clocked: true,
    id: exports.nw_api_v1_task_manual,
    driver: (handle, frameHz) => clockedDriver(handle, frameHz,
      exports.nw_manual_agent_event, exports.nw_api_v1_manual_info, 21),
  }, options);
}

// Forms: 46 ports, one per key -- a to z, 0 to 9, space, @ . - /, then
// Backspace, Tab, Enter, Up and Down; port 46 starts a run.
export function createFormsEnvironment(exports, context, createArchive, options) {
  return createRungEnvironment(exports, context, createArchive, {
    name: "Forms", trials: 5, ports: 46, frameCapacity: 1048576n, clocked: true,
    id: exports.nw_api_v1_task_forms,
    driver: (handle, frameHz) => clockedDriver(handle, frameHz,
      exports.nw_forms_agent_event, exports.nw_api_v1_forms_info, 46),
  }, options);
}

// Desktop: 17 ports -- the pointer up, down, left or right by a long,
// medium or short step, then click, press, let go, Done and right-click.
export function createDesktopEnvironment(exports, context, createArchive, options) {
  return createRungEnvironment(exports, context, createArchive, {
    name: "Desktop", trials: 5, ports: 17, frameCapacity: 1048576n, clocked: true,
    id: exports.nw_api_v1_task_desktop,
    driver: (handle, frameHz) => clockedDriver(handle, frameHz,
      exports.nw_desktop_agent_event, exports.nw_api_v1_desktop_info, 17),
  }, options);
}

export function createEmotionEnvironment(exports, context, createArchive, options) {
  return createRungEnvironment(exports, context, createArchive, {
    name: "Emotion", trials: 5, ports: 8, frameCapacity: 1048576n, clocked: true,
    id: exports.nw_api_v1_task_emotion,
    driver: (handle, frameHz) => clockedDriver(handle, frameHz,
      exports.nw_emotion_agent_event, exports.nw_api_v1_emotion_info, 8),
  }, options);
}

export function createDelayEnvironment(exports, context, createArchive, options) {
  return createRungEnvironment(exports, context, createArchive, {
    name: "Delay", trials: 3, ports: 2, clocked: true,
    id: () => exports.nw_api_v1_task_delay(),
    driver: (handle, frameHz) => clockedDriver(handle, frameHz,
      exports.nw_delay_agent_event, exports.nw_api_v1_delay_info),
  }, options);
}

export function createStopAndSwitchEnvironment(exports, context, createArchive, options) {
  return createRungEnvironment(exports, context, createArchive, {
    name: "Stop & Switch", trials: 6, ports: 2, clocked: true,
    id: () => exports.nw_api_v1_task_stop_switch(),
    driver: (handle, frameHz) => clockedDriver(handle, frameHz,
      exports.nw_stop_switch_agent_event, exports.nw_api_v1_stop_switch_info),
  }, options);
}

export function createHoldItEnvironment(exports, context, createArchive, options) {
  return createRungEnvironment(exports, context, createArchive, {
    name: "Hold It", trials: 5, ports: 1, clocked: true,
    id: () => exports.nw_api_v1_task_hold_it(),
    driver(handle, frameHz) {
      let seconds = 0;
      let held = false;
      return {
        start: () => exports.nw_hold_it_agent_event(handle, 0, 2n),
        act() { held = true; },
        step() {
          seconds += 1 / frameHz;
          const result = exports.nw_hold_it_agent_event(handle, seconds, held ? 0n : -1n);
          held = false;
          return result;
        },
        audio(pointer, capacity) {
          const length = exports.nw_hold_it_audio(handle, pointer, capacity);
          if (length < 0n) throw new Error(`Hold It audio export failed (${length})`);
          if (length === 0n) return undefined;
          return {
            audio_pcm: new Uint8Array(exports.memory.buffer, Number(pointer), Number(length)).slice(),
            audio_rate: 22050, audio_channels: 2, audio_sample_width: 2,
          };
        },
        phase: () => exports.nw_api_v1_hold_it_info(handle, 0n),
        thinkLeft: () => 0,
        forfeits: () => 0,
      };
    },
  }, options);
}

export function createTimeItEnvironment(exports, context, createArchive, options) {
  return createRungEnvironment(exports, context, createArchive, {
    name: "Time It", trials: 5, ports: 1, clocked: true,
    id: exports.nw_api_v1_task_time_it,
    driver(handle, frameHz) {
      const clock = clockedDriver(handle, frameHz,
        exports.nw_time_it_agent_event, exports.nw_api_v1_time_it_info, 1);
      return {
        ...clock,
        audio(pointer, capacity) {
          const length = exports.nw_time_it_audio(handle, pointer, capacity);
          if (length < 0n) throw new Error(`Time It audio export failed (${length})`);
          if (length === 0n) return undefined;
          return {
            audio_pcm: new Uint8Array(exports.memory.buffer, Number(pointer), Number(length)).slice(),
            audio_rate: 22050, audio_channels: 2, audio_sample_width: 2,
          };
        },
      };
    },
  }, options);
}
export function createBeatEnvironment(exports, context, createArchive, options) {
  return createRungEnvironment(exports, context, createArchive, {
    name: "Keep the Beat", trials: 5, ports: 1, clocked: true,
    id: exports.nw_api_v1_task_beat,
    driver(handle, frameHz) {
      const clock = clockedDriver(handle, frameHz,
        exports.nw_beat_agent_event, exports.nw_api_v1_beat_info, 1);
      return {
        ...clock,
        audio(pointer, capacity) {
          const length = exports.nw_beat_audio(handle, pointer, capacity);
          if (length < 0n) throw new Error(`Keep the Beat audio export failed (${length})`);
          if (length === 0n) return undefined;
          return {
            audio_pcm: new Uint8Array(exports.memory.buffer, Number(pointer), Number(length)).slice(),
            audio_rate: 22050, audio_channels: 2, audio_sample_width: 2,
          };
        },
      };
    },
  }, options);
}

export function createCatchEnvironment(exports, context, createArchive, options) {
  return createRungEnvironment(exports, context, createArchive, {
    name: "Catch", trials: 5, ports: 8, clocked: true, multiple: true,
    id: exports.nw_api_v1_task_catch,
    driver(handle, frameHz) {
      const clock = clockedDriver(handle, frameHz,
        exports.nw_catch_agent_event, exports.nw_api_v1_catch_info, 8);
      return {
        ...clock,
        act(ports) {
          const mask = ports.reduce((bits, port) => bits | (1 << port), 0);
          if (exports.nw_catch_agent_mask(handle, BigInt(mask)) !== 1n)
            throw new Error("Catch could not queue simultaneous controls");
        },
        audio(pointer, capacity) {
          const length = exports.nw_catch_audio(handle, pointer, capacity);
          if (length < 0n) throw new Error(`Catch audio export failed (${length})`);
          if (length === 0n) return undefined;
          return {
            audio_pcm: new Uint8Array(exports.memory.buffer, Number(pointer), Number(length)).slice(),
            audio_rate: 22050, audio_channels: 2, audio_sample_width: 2,
          };
        },
      };
    },
  }, options);
}
export function createEchoCaveEnvironment(exports, context, createArchive, options) {
  return createRungEnvironment(exports, context, createArchive, {
    name: "Echo Cave", trials: 5, ports: 9, clocked: true, multiple: true,
    id: exports.nw_api_v1_task_echo_cave,
    driver(handle, frameHz) {
      const clock = clockedDriver(handle, frameHz,
        exports.nw_echo_cave_agent_event, exports.nw_api_v1_echo_cave_info, 9);
      return {
        ...clock,
        act(ports) {
          const mask = ports.reduce((bits, port) => bits | (1 << port), 0);
          if (exports.nw_echo_cave_agent_mask(handle, BigInt(mask)) !== 1n)
            throw new Error("Echo Cave could not queue simultaneous controls");
        },
        audio(pointer, capacity) {
          const length = exports.nw_echo_cave_audio(handle, pointer, capacity);
          if (length < 0n) throw new Error(`Echo Cave audio export failed (${length})`);
          if (length === 0n) return undefined;
          return {
            audio_pcm: new Uint8Array(exports.memory.buffer, Number(pointer), Number(length)).slice(),
            audio_rate: 22050, audio_channels: 2, audio_sample_width: 2,
          };
        },
      };
    },
  }, options);
}
export function createDroneHoopsEnvironment(exports, context, createArchive, options) {
  return createRungEnvironment(exports, context, createArchive, {
    name: "Drone Hoops", trials: 5, ports: 10, clocked: true, multiple: true, outcomeOnVerdict: true,
    id: exports.nw_api_v1_task_drone_hoops,
    driver(handle, frameHz) {
      const clock = clockedDriver(handle, frameHz,
        exports.nw_drone_hoops_agent_event, exports.nw_api_v1_drone_hoops_info, 10);
      return {
        ...clock,
        act(ports) {
          const mask = ports.reduce((bits, port) => bits | (1 << port), 0);
          if (exports.nw_drone_hoops_agent_mask(handle, BigInt(mask)) !== 1n)
            throw new Error("Drone Hoops could not queue simultaneous controls");
        },
        audio(pointer, capacity) {
          const length = exports.nw_drone_hoops_audio(handle, pointer, capacity);
          if (length < 0n) throw new Error(`Drone Hoops audio export failed (${length})`);
          if (length === 0n) return undefined;
          return {
            audio_pcm: new Uint8Array(exports.memory.buffer, Number(pointer), Number(length)).slice(),
            audio_rate: 22050, audio_channels: 2, audio_sample_width: 2,
          };
        },
      };
    },
  }, options);
}
export function createFieldManualEnvironment(exports, context, createArchive, options) {
  return createRungEnvironment(exports, context, createArchive, {
    name: "Field Manual", trials: 5, ports: 25, clocked: true, outcomeOnVerdict: true,
    id: exports.nw_api_v1_task_field_manual,
    driver(handle, frameHz) {
      const clock = clockedDriver(handle, frameHz,
        exports.nw_field_manual_agent_event, exports.nw_api_v1_field_manual_info, 25);
      return {
        ...clock,
        audio(pointer, capacity) {
          const length = exports.nw_field_manual_audio(handle, pointer, capacity);
          if (length < 0n) throw new Error(`Field Manual audio export failed (${length})`);
          if (length === 0n) return undefined;
          return {
            audio_pcm: new Uint8Array(exports.memory.buffer, Number(pointer), Number(length)).slice(),
            audio_rate: 22050, audio_channels: 2, audio_sample_width: 2,
          };
        },
      };
    },
  }, options);
}
export function createSafecrackerEnvironment(exports, context, createArchive, options) {
  return createRungEnvironment(exports, context, createArchive, {
    name: "Safecracker", trials: 5, ports: 41, clocked: true, outcomeOnVerdict: true,
    id: exports.nw_api_v1_task_safecracker,
    driver(handle, frameHz) {
      const clock = clockedDriver(handle, frameHz,
        exports.nw_safecracker_agent_event, exports.nw_api_v1_safecracker_info, 41);
      return {
        ...clock,
        audio(pointer, capacity) {
          const length = exports.nw_safecracker_audio(handle, pointer, capacity);
          if (length < 0n) throw new Error(`Safecracker audio export failed (${length})`);
          if (length === 0n) return undefined;
          return {
            audio_pcm: new Uint8Array(exports.memory.buffer, Number(pointer), Number(length)).slice(),
            audio_rate: 22050, audio_channels: 2, audio_sample_width: 2,
          };
        },
      };
    },
  }, options);
}
export function createStagehandEnvironment(exports, context, createArchive, options) {
  return createRungEnvironment(exports, context, createArchive, {
    name: "Stagehand", trials: 5, ports: 19, clocked: true, outcomeOnVerdict: true,
    id: exports.nw_api_v1_task_stagehand,
    driver(handle, frameHz) {
      const clock = clockedDriver(handle, frameHz,
        exports.nw_stagehand_agent_event, exports.nw_api_v1_stagehand_info, 19);
      return {
        ...clock,
        audio(pointer, capacity) {
          const length = exports.nw_stagehand_audio(handle, pointer, capacity);
          if (length < 0n) throw new Error(`Stagehand audio export failed (${length})`);
          if (length === 0n) return undefined;
          return {
            audio_pcm: new Uint8Array(exports.memory.buffer, Number(pointer), Number(length)).slice(),
            audio_rate: 22050, audio_channels: 2, audio_sample_width: 2,
          };
        },
      };
    },
  }, options);
}
export function createLoadingDockEnvironment(exports, context, createArchive, options) {
  return createRungEnvironment(exports, context, createArchive, {
    name: "Loading Dock", trials: 5, ports: 20, clocked: true, outcomeOnVerdict: true,
    id: exports.nw_api_v1_task_loading_dock,
    driver(handle, frameHz) {
      const clock = clockedDriver(handle, frameHz,
        exports.nw_loading_dock_agent_event, exports.nw_api_v1_loading_dock_info, 20);
      return {
        ...clock,
        audio(pointer, capacity) {
          const length = exports.nw_loading_dock_audio(handle, pointer, capacity);
          if (length < 0n) throw new Error(`Loading Dock audio export failed (${length})`);
          if (length === 0n) return undefined;
          return {
            audio_pcm: new Uint8Array(exports.memory.buffer, Number(pointer), Number(length)).slice(),
            audio_rate: 22050, audio_channels: 2, audio_sample_width: 2,
          };
        },
      };
    },
  }, options);
}
export function createGunslingerEnvironment(exports, context, createArchive, options) {
  return createRungEnvironment(exports, context, createArchive, {
    name: "Gunslinger", trials: 5, ports: 15, clocked: true, outcomeOnVerdict: true,
    id: exports.nw_api_v1_task_gunslinger,
    driver(handle, frameHz) {
      const clock = clockedDriver(handle, frameHz,
        exports.nw_gunslinger_agent_event, exports.nw_api_v1_gunslinger_info, 15);
      return {
        ...clock,
        audio(pointer, capacity) {
          const length = exports.nw_gunslinger_audio(handle, pointer, capacity);
          if (length < 0n) throw new Error(`Gunslinger audio export failed (${length})`);
          if (length === 0n) return undefined;
          return {
            audio_pcm: new Uint8Array(exports.memory.buffer, Number(pointer), Number(length)).slice(),
            audio_rate: 22050, audio_channels: 2, audio_sample_width: 2,
          };
        },
      };
    },
  }, options);
}

export function createDrShapeEnvironment(exports, context, createArchive, options) {
  return createRungEnvironment(exports, context, createArchive, {
    name: "Dr Shape", trials: 5, ports: 6, clocked: true, outcomeOnVerdict: true,
    frameCapacity: 1048576n,
    id: exports.nw_api_v1_task_dr_shape,
    driver(handle, frameHz) {
      const clock = clockedDriver(handle, frameHz,
        exports.nw_drshape_agent_event, exports.nw_api_v1_drshape_info, 6);
      return {
        ...clock,
        audio(pointer, capacity) {
          const length = exports.nw_drshape_audio(handle, pointer, capacity);
          if (length < 0n) throw new Error(`Dr Shape audio export failed (${length})`);
          if (length === 0n) return undefined;
          return {
            audio_pcm: new Uint8Array(exports.memory.buffer, Number(pointer), Number(length)).slice(),
            audio_rate: 22050, audio_channels: 2, audio_sample_width: 2,
          };
        },
      };
    },
  }, options);
}

export function createShadowPlayEnvironment(exports, context, createArchive, options) {
  return createRungEnvironment(exports, context, createArchive, {
    name: "Shadow Play", trials: 5, ports: 6, clocked: true, outcomeOnVerdict: true,
    frameCapacity: 1048576n,
    id: exports.nw_api_v1_task_shadow_play,
    driver(handle, frameHz) {
      const clock = clockedDriver(handle, frameHz,
        exports.nw_shadow_play_agent_event, exports.nw_api_v1_shadow_play_info, 6);
      return {
        ...clock,
        audio(pointer, capacity) {
          const length = exports.nw_shadow_play_audio(handle, pointer, capacity);
          if (length < 0n) throw new Error(`Shadow Play audio export failed (${length})`);
          if (length === 0n) return undefined;
          return {
            audio_pcm: new Uint8Array(exports.memory.buffer, Number(pointer), Number(length)).slice(),
            audio_rate: 22050, audio_channels: 2, audio_sample_width: 2,
          };
        },
      };
    },
  }, options);
}

export function createTunerEnvironment(exports, context, createArchive, options) {
  return createRungEnvironment(exports, context, createArchive, {
    name: "Tuner", trials: 5, ports: 6, clocked: true, outcomeOnVerdict: true,
    frameCapacity: 1048576n,
    id: exports.nw_api_v1_task_tuner,
    driver(handle, frameHz) {
      const clock = clockedDriver(handle, frameHz,
        exports.nw_tuner_agent_event, exports.nw_api_v1_tuner_info, 6);
      return {
        ...clock,
        audio(pointer, capacity) {
          const length = exports.nw_tuner_audio(handle, pointer, capacity);
          if (length < 0n) throw new Error(`Tuner audio export failed (${length})`);
          if (length === 0n) return undefined;
          return {
            audio_pcm: new Uint8Array(exports.memory.buffer, Number(pointer), Number(length)).slice(),
            audio_rate: 22050, audio_channels: 2, audio_sample_width: 2,
          };
        },
      };
    },
  }, options);
}

export function createBalanceEnvironment(exports, context, createArchive, options) {
  return createRungEnvironment(exports, context, createArchive, {
    name: "Balance", trials: 5, ports: 2, clocked: true,
    id: exports.nw_api_v1_task_balance,
    driver: (handle, frameHz) => clockedDriver(handle, frameHz,
      exports.nw_balance_agent_event, exports.nw_api_v1_balance_info),
  }, options);
}
export function createJugglerEnvironment(exports, context, createArchive, options) {
  return createRungEnvironment(exports, context, createArchive, {
    name: "Juggler", trials: 5, ports: 2, clocked: true,
    id: exports.nw_api_v1_task_juggler,
    driver: (handle, frameHz) => clockedDriver(handle, frameHz,
      exports.nw_juggler_agent_event, exports.nw_api_v1_juggler_info),
  }, options);
}
export function createLanderEnvironment(exports, context, createArchive, options) {
  return createRungEnvironment(exports, context, createArchive, {
    name: "Lander", trials: 5, ports: 5, clocked: true,
    id: exports.nw_api_v1_task_lander,
    driver: (handle, frameHz) => clockedDriver(handle, frameHz,
      exports.nw_lander_agent_event, exports.nw_api_v1_lander_info, 5),
  }, options);
}
export function createGliderEnvironment(exports, context, createArchive, options) {
  return createRungEnvironment(exports, context, createArchive, {
    name: "Glider", trials: 5, ports: 1, clocked: true,
    id: exports.nw_api_v1_task_glider,
    driver: (handle, frameHz) => clockedDriver(handle, frameHz,
      exports.nw_glider_agent_event, exports.nw_api_v1_glider_info, 1),
  }, options);
}
