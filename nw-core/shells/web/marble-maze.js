// Browser-side Marble Maze runtime.
//
// The reference uses MuJoCo for the rigid-body solve. That native dependency
// cannot be loaded by a standalone browser page, so this module keeps the
// reference's SI constants, tray geometry, hole rules, speed cap, tilt
// convention, and fixed-step discipline while solving the small 2D contact
// problem locally. The tray itself is not approximated: it is decoded from
// the certified board produced by tasks/marblemaze.elisa.

const MAGIC = 826496845; // "MWC1" little-endian (format v1)
const VERSION = 1;
const BOARD_FIXED_BYTES = 64;
const BOARD_MAX_WALLS = 4096;
const BOARD_MAX_HOLES = 96;
const BOARD_MAX_STARTS = 64;
const BOARD_MAX_CELLS = 120;
const BOARD_MIN_RUNG = 1;
const BOARD_MAX_RUNG = 16;
const BOARD_MIN_COLS = 4;
const BOARD_MAX_COLS = 12;
const BOARD_MIN_ROWS = 4;
const BOARD_MAX_ROWS = 10;
const BOARD_GEOMETRY_EPSILON = 1e-5;

export const MARBLE = Object.freeze({
  GRAVITY: 9.80665,
  RADIUS: 0.0075,
  SPHERE_INERTIA: 2 / 5,
  SLIP_SHARE: 2 / 7,
  FRICTION_STATIC: 0.50,
  // A solid sphere's rolling acceleration is 5/7 of the plane's
  // tangential gravity. MuJoCo gets this from the sphere inertia and
  // contact solve; the browser solver keeps the same measured factor.
  ROLL_FACTOR: 5 / 7,
  ROLLING_RESISTANCE: 0.008,
  VISCOUS_DRAG: 0.22,
  SPIN_GRIP: 0.005,
  REST_SPEED: 0.006,
  SPEED_CAP: 1.0,
  SUBSTEPS: 4,
  MAX_TILT: 0.140,
  TILT_STEP: 0.006,
  WALL_RESTITUTION: 0.28,
  WALL_FRICTION: 0.08,
  BALL_RESTITUTION: 0.92,
  BALL_FRICTION: 0.05,
});

// These labels and measurements are the public Marble Maze options contract
// from neural_workshop.ui.taskoptions. The native note uses Python's
// round(2 * 7.5 * Grade.slack), so the tie cases are stored after Python has
// rounded them rather than being recomputed with JavaScript Math.round().
export const MARBLE_GRADES = Object.freeze([
  "the tray", "first hole", "three holes", "the long way", "two marbles",
  "narrow", "narrow, twice", "the sieve", "three marbles", "tight",
  "tight, in pairs", "the labyrinth", "four marbles", "a hole a cell",
  "the gauntlet", "inhuman",
]);
export const MARBLE_CORRIDOR_MM = Object.freeze([
  51, 52, 51, 49, 50, 46, 47, 44,
  45, 42, 43, 40, 42, 39, 38, 36,
]);
export const MARBLE_GRADE_HOLES = Object.freeze([
  0, 1, 3, 5, 4, 7, 8, 11,
  9, 14, 13, 18, 14, 24, 30, 38,
]);
export const MARBLE_GRADE_MARBLES = Object.freeze([
  1, 1, 1, 1, 2, 1, 2, 1,
  3, 1, 2, 1, 4, 1, 2, 3,
]);

export function marbleOptionNoteLines(rung, board) {
  const supplied = Number(rung);
  const level = Number.isFinite(supplied)
    ? Math.max(1, Math.min(MARBLE_GRADES.length, Math.trunc(supplied))) : 1;
  if (!board || !Array.isArray(board.holes) || !Array.isArray(board.starts)) {
    throw new Error("marble options note requires a decoded board");
  }
  // The native note describes the selected Grade, not the number of holes
  // that happened to survive placement on this particular certified tray.
  // Those values differ on some seeds, so reading board.holes here would make
  // the explanatory options screen nondeterministically diverge from Python.
  const holes = MARBLE_GRADE_HOLES[level - 1];
  const marbles = MARBLE_GRADE_MARBLES[level - 1];
  const holeWord = holes === 1 ? "hole" : "holes";
  const marbleWord = marbles === 1 ? "marble" : "marbles";
  return [
    `Level ${level}, "${MARBLE_GRADES[level - 1]}": a ${board.cols}x${board.rows} maze in corridors ${MARBLE_CORRIDOR_MM[level - 1]}mm wide, with ${holes} ${holeWord} to miss and ${marbles} ${marbleWord} to bring home, in ${Math.trunc(board.seconds)}s.`,
    "The marble is a 15mm steel one and it behaves like it: it accelerates at five sevenths of gravity down the slope, because the other two sevenths go into spin, and it keeps rolling after you level the tray.",
    "A hole only takes a marble that is over it long enough to fall in. Sent across fast enough, a marble clears the far rim and lands with a clatter — which is the only reason to ever go fast.",
    ...(marbles > 1 ? [`There is one tray and one pair of knobs, so all ${marbles} marbles feel every tilt. They start nose to tail along the same route, and they knock each other about.`] : []),
    "Every tray is generated and then certified: a sweep of every place the marble may legally stand proves there is a way through before it is dealt.",
  ];
}

export function clamp(value, low, high) {
  return Math.max(low, Math.min(high, value));
}

export function marbleBoardBudgetSeconds(board, overrideSeconds = 0) {
  return overrideSeconds > 0 ? overrideSeconds : board.seconds;
}

// Python's round(float) uses round-to-nearest, ties-to-even. JavaScript's
// Math.round() rounds a half away from zero, so the two UIs disagree at exact
// half-degree display boundaries (notably for negative tray pitch). Keep the
// source rule in the shared adapter instead of baking a browser-only rounding
// convention into the status renderer.
export function marbleSourceRound(value) {
  if (!Number.isFinite(value)) return 0;
  const lower = Math.floor(value);
  const fraction = value - lower;
  const epsilon = Number.EPSILON * Math.max(1, Math.abs(value)) * 8;
  if (fraction < 0.5 - epsilon) return lower;
  if (fraction > 0.5 + epsilon) return lower + 1;
  return lower % 2 === 0 ? lower : lower + 1;
}

// The source UI checks `sim.settled` before it checks the active-time budget.
// That ordering is observable when the final physics frame both settles a
// marble and reaches the deadline: a physical hole result is reported as a
// hole result, not as a timeout. Keep the classification in the shared Marble
// module so the browser chrome and its result ledger cannot accidentally grow
// different boundary rules.
export function marbleFeedbackKind(game, verdict, boardSeconds) {
  if (Number(verdict) === 1) return "won";
  if (!game?.settled && Number(game?.elapsed) >= Number(boardSeconds)) {
    return "timeout";
  }
  return Number(game?.lost) === 1 ? "lost-single" : "lost-multiple";
}

function hypot2(x, y) {
  return Math.hypot(x, y);
}

// Decode the compact board ABI. Everything is copied out of the WASM view so
// memory growth or the next frame cannot invalidate an in-flight run.
export function decodeMarbleBoard(bytes) {
  if (!(bytes instanceof Uint8Array) || bytes.byteLength < BOARD_FIXED_BYTES + 4) {
    throw new Error("marble board: truncated data");
  }
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  let at = 0;
  const u32 = () => {
    if (at + 4 > bytes.byteLength) throw new Error("marble board: truncated data");
    const value = view.getUint32(at, true);
    at += 4;
    return value;
  };
  const f32 = (label) => {
    if (at + 4 > bytes.byteLength) throw new Error("marble board: truncated data");
    const value = view.getFloat32(at, true);
    at += 4;
    if (!Number.isFinite(value)) throw new Error(`marble board: non-finite ${label}`);
    return value;
  };
  if (bytes.byteLength < 24 || u32() !== MAGIC || u32() !== VERSION) {
    throw new Error("marble board: bad header");
  }
  const builtValue = u32();
  if (builtValue > 1) throw new Error("marble board: invalid built flag");
  const built = builtValue === 1;
  const rung = u32();
  const cols = u32();
  const rows = u32();
  const board = {
    built, rung, cols, rows,
    width: f32("width"), depth: f32("depth"), cell: f32("cell"),
    thickness: f32("thickness"), height: f32("height"),
    home: { x: f32("home.x"), y: f32("home.y"), radius: f32("home.radius") },
    seconds: f32("seconds"), route: f32("route"), walls: [], holes: [], starts: [],
  };
  const wallCount = u32();
  if (wallCount > BOARD_MAX_WALLS) throw new Error("marble board: wall count too large");
  if (at + wallCount * 16 > bytes.byteLength) throw new Error("marble board: truncated walls");
  for (let index = 0; index < wallCount; index++) {
    board.walls.push({ x0: f32("wall.x0"), y0: f32("wall.y0"),
      x1: f32("wall.x1"), y1: f32("wall.y1") });
  }
  const holeCount = u32();
  if (holeCount > BOARD_MAX_HOLES) throw new Error("marble board: hole count too large");
  if (at + holeCount * 16 > bytes.byteLength) throw new Error("marble board: truncated holes");
  for (let index = 0; index < holeCount; index++) {
    const x = f32("hole.x");
    const y = f32("hole.y");
    const radius = f32("hole.radius");
    const homeValue = u32();
    if (homeValue > 1) throw new Error("marble board: invalid home flag");
    board.holes.push({ x, y, radius, home: homeValue === 1 });
  }
  const startCount = u32();
  if (startCount > BOARD_MAX_STARTS) throw new Error("marble board: start count too large");
  if (at + startCount * 8 > bytes.byteLength) throw new Error("marble board: truncated starts");
  for (let index = 0; index < startCount; index++) {
    board.starts.push({ x: f32("start.x"), y: f32("start.y") });
  }
  if (at !== bytes.byteLength) throw new Error("marble board: trailing data");
  validateMarbleBoard(board);
  return board;
}

function approximatelyEqual(left, right) {
  return Math.abs(left - right) <= BOARD_GEOMETRY_EPSILON;
}

function insideBoard(value, limit, margin = 0) {
  return value >= -BOARD_GEOMETRY_EPSILON + margin &&
    value <= limit + BOARD_GEOMETRY_EPSILON - margin;
}

function validateMarbleBoard(board) {
  if (!board.built) throw new Error("marble board: board is not built");
  if (!Number.isInteger(board.rung) || board.rung < BOARD_MIN_RUNG ||
      board.rung > BOARD_MAX_RUNG) {
    throw new Error("marble board: rung out of range");
  }
  if (!Number.isInteger(board.cols) || board.cols < BOARD_MIN_COLS ||
      board.cols > BOARD_MAX_COLS || !Number.isInteger(board.rows) ||
      board.rows < BOARD_MIN_ROWS || board.rows > BOARD_MAX_ROWS ||
      board.cols * board.rows > BOARD_MAX_CELLS) {
    throw new Error("marble board: dimensions out of range");
  }
  for (const [label, value] of [
    ["width", board.width], ["depth", board.depth], ["cell", board.cell],
    ["thickness", board.thickness], ["height", board.height],
    ["home.radius", board.home.radius], ["seconds", board.seconds],
    ["route", board.route],
  ]) {
    if (!(value > 0)) throw new Error(`marble board: ${label} must be positive`);
  }
  if (board.route < 0) throw new Error("marble board: route must be non-negative");
  if (!approximatelyEqual(board.width, board.cols * board.cell + 0.008) ||
      !approximatelyEqual(board.depth, board.rows * board.cell + 0.008)) {
    throw new Error("marble board: dimensions do not match cell geometry");
  }
  if (!(board.thickness < board.cell) ||
      board.cell - board.thickness <= 2 * MARBLE.RADIUS ||
      board.height > board.cell + BOARD_GEOMETRY_EPSILON) {
    throw new Error("marble board: invalid wall geometry");
  }
  if (!insideBoard(board.home.x, board.width, board.home.radius) ||
      !insideBoard(board.home.y, board.depth, board.home.radius)) {
    throw new Error("marble board: home cup is out of bounds");
  }
  if (!board.walls.length) throw new Error("marble board: no walls");
  for (const wall of board.walls) {
    if (!(wall.x0 < wall.x1 && wall.y0 < wall.y1) ||
        !insideBoard(wall.x0, board.width) || !insideBoard(wall.x1, board.width) ||
        !insideBoard(wall.y0, board.depth) || !insideBoard(wall.y1, board.depth)) {
      throw new Error("marble board: wall geometry out of bounds");
    }
  }
  if (!board.holes.length) throw new Error("marble board: no holes");
  let homeCount = 0;
  for (const hole of board.holes) {
    if (!(hole.radius > 0) ||
        !insideBoard(hole.x, board.width, hole.radius) ||
        !insideBoard(hole.y, board.depth, hole.radius)) {
      throw new Error("marble board: hole geometry out of bounds");
    }
    if (hole.home) homeCount++;
  }
  const cup = board.holes.at(-1);
  if (homeCount !== 1 || !cup.home ||
      !approximatelyEqual(cup.x, board.home.x) ||
      !approximatelyEqual(cup.y, board.home.y) ||
      !approximatelyEqual(cup.radius, board.home.radius)) {
    throw new Error("marble board: home cup ordering or geometry is invalid");
  }
  if (!board.starts.length) throw new Error("marble board: no starts");
  for (const start of board.starts) {
    if (!insideBoard(start.x, board.width, MARBLE.RADIUS) ||
        !insideBoard(start.y, board.depth, MARBLE.RADIUS)) {
      throw new Error("marble board: start is out of bounds");
    }
  }
}

function marbleState(x, y) {
  return { x, y, vx: 0, vy: 0, z: MARBLE.RADIUS, vz: 0,
    wx: 0, wy: 0, wz: 0, qw: 1, qx: 0, qy: 0, qz: 0,
    state: "rolling", over: null };
}

function normalizeQuaternion(marble) {
  const length = Math.hypot(marble.qw, marble.qx, marble.qy, marble.qz);
  if (length < 1e-12) {
    marble.qw = 1;
    marble.qx = marble.qy = marble.qz = 0;
    return;
  }
  marble.qw /= length;
  marble.qx /= length;
  marble.qy /= length;
  marble.qz /= length;
}

function integrateOrientation(marble, dt) {
  const { qw, qx, qy, qz, wx, wy, wz } = marble;
  const half = 0.5 * dt;
  // Angular velocity is expressed in tray coordinates, so this is the
  // world/tray-frame quaternion product [0, omega] * q.
  marble.qw += half * (-wx * qx - wy * qy - wz * qz);
  marble.qx += half * ( wx * qw + wy * qz - wz * qy);
  marble.qy += half * (-wx * qz + wy * qw + wz * qx);
  marble.qz += half * ( wx * qy - wy * qx + wz * qw);
  normalizeQuaternion(marble);
}

function applyFloorFriction(marble, gn, dt) {
  // A sphere's contact-point slip is v -/+ R*omega. A friction impulse p
  // changes slip by p / SLIP_SHARE, where SLIP_SHARE is I/(I+1)=2/7.
  // Applying that impulse after gravity produces the reference's 5/7
  // acceleration for a clean roll and also lets a wall/ball impact skid
  // until the floor has dragged the spin back into agreement.
  const slipX = marble.vx - MARBLE.RADIUS * marble.wy;
  const slipY = marble.vy + MARBLE.RADIUS * marble.wx;
  const slip = Math.hypot(slipX, slipY);
  if (slip < 1e-12) return;
  const maxImpulse = MARBLE.FRICTION_STATIC * gn * dt;
  const wanted = Math.min(slip, maxImpulse / MARBLE.SLIP_SHARE);
  const factor = -wanted / slip;
  const correctionX = slipX * factor;
  const correctionY = slipY * factor;
  const impulseX = correctionX * MARBLE.SLIP_SHARE;
  const impulseY = correctionY * MARBLE.SLIP_SHARE;
  marble.vx += impulseX;
  marble.vy += impulseY;
  marble.wy -= impulseX / (MARBLE.SPHERE_INERTIA * MARBLE.RADIUS);
  marble.wx += impulseY / (MARBLE.SPHERE_INERTIA * MARBLE.RADIUS);
}

function applyRollingResistance(marble, gn, dt) {
  const speed = hypot2(marble.vx, marble.vy);
  if (speed < 1e-12) return;
  const cleanRoll = hypot2(marble.vx - MARBLE.RADIUS * marble.wy,
    marble.vy + MARBLE.RADIUS * marble.wx) < 0.003;
  const reduced = Math.max(0, speed - MARBLE.ROLL_FACTOR *
    MARBLE.ROLLING_RESISTANCE * gn * dt);
  const scale = reduced / speed;
  marble.vx *= scale;
  marble.vy *= scale;
  if (cleanRoll) {
    // Rolling resistance is a torque at the contact patch. When the sphere
    // is already rolling, its travel and roll spin lose the same fraction;
    // leaving the spin untouched would make a levelled marble re-accelerate
    // itself indefinitely through the floor's no-slip correction.
    marble.wx *= scale;
    marble.wy *= scale;
  }
}

function applySpinGrip(marble, gn, dt) {
  // MuJoCo's torsional coefficient is a contact-length coefficient. This
  // exponential form is stable at all frame rates and reaches the native
  // rest clamp quickly without changing the visible rolling travel.
  const keep = Math.exp(-MARBLE.SPIN_GRIP * gn / MARBLE.RADIUS * dt);
  marble.wz *= keep;
}

export class MarbleMazeGame {
  constructor(board) {
    if (!board || !board.built || !board.starts.length) {
      throw new Error("marble board is not built");
    }
    this.board = board;
    this.roll = 0;
    this.pitch = 0;
    this.elapsed = 0;
    this.cuppedThisStep = 0;
    this.lostThisStep = 0;
    this.struckThisStep = 0;
    this.nudgeDue = 0;
    this.reset();
  }

  reset() {
    this.marbles = this.board.starts.map((start) => marbleState(start.x, start.y));
    this.roll = 0;
    this.pitch = 0;
    this.elapsed = 0;
    this.cuppedThisStep = 0;
    this.lostThisStep = 0;
    this.struckThisStep = 0;
    this.nudgeDue = 0;
  }

  // Replacing the source Simulation resets its elapsed clock. The held-key
  // fractional nudge belongs to the UI and survives until an idle update.
  restart() {
    const nudgeDue = this.nudgeDue;
    this.reset();
    this.nudgeDue = nudgeDue;
  }

  tilt(which) {
    if (which === "N") this.pitch = Math.max(-MARBLE.MAX_TILT, this.pitch - MARBLE.TILT_STEP);
    else if (which === "S") this.pitch = Math.min(MARBLE.MAX_TILT, this.pitch + MARBLE.TILT_STEP);
    else if (which === "E") this.roll = Math.min(MARBLE.MAX_TILT, this.roll + MARBLE.TILT_STEP);
    else if (which === "W") this.roll = Math.max(-MARBLE.MAX_TILT, this.roll - MARBLE.TILT_STEP);
  }

  level() {
    this.roll = 0;
    this.pitch = 0;
  }

  get home() {
    return this.marbles.filter((marble) => marble.state === "home").length;
  }

  get lost() {
    return this.marbles.filter((marble) => marble.state === "lost").length;
  }

  get settled() {
    return !this.marbles.some((marble) => marble.state === "rolling" || marble.state === "falling");
  }

  get won() {
    return this.marbles.every((marble) => marble.state === "home");
  }

  get speed() {
    return this.marbles.reduce((fastest, marble) =>
      Math.max(fastest, hypot2(marble.vx, marble.vy)), 0);
  }

  get secondsLeft() {
    return Math.max(0, this.board.seconds - this.elapsed);
  }

  // Advance the same way the native UI does: held controls nudge at 60 Hz,
  // while the physical solve itself is split into four fixed substeps.
  advance(dt, held = []) {
    const piece = clamp(Number(dt) || 0, 0, 0.05);
    const keys = held instanceof Set ? held : new Set(held);
    if (keys.size) {
      this.nudgeDue += piece;
      while (this.nudgeDue >= 1 / 60) {
        this.nudgeDue -= 1 / 60;
        for (const which of keys) this.tilt(which);
      }
    } else {
      this.nudgeDue = 0;
    }
    if (!piece) return;
    let left = piece;
    // Match the Python UI: advance every positive remainder, however small.
    while (left > 0) {
      const bite = Math.min(left, 1 / 60);
      this.step(bite);
      left -= bite;
    }
  }

  step(dt) {
    const amount = Number(dt) || 0;
    // Direct callers may use step() for deterministic replays and tests, so
    // keep the fallback adapter's boundary identical to the MuJoCo adapter:
    // a non-positive or non-finite step is a no-op rather than a
    // backwards-time solve or an unbounded infinite-time loop.
    if (!(amount > 0) || !Number.isFinite(amount)) return;
    this.cuppedThisStep = 0;
    this.lostThisStep = 0;
    this.struckThisStep = 0;
    this.elapsed += amount;
    // Match Simulation.step exactly: the UI's 50 ms clamp and positive
    // remainder loop belong to advance(), while one direct step is always
    // four equal MuJoCo/fallback substeps. Adding an extra 60 Hz partition
    // here changes the public step contract for replay callers and makes the
    // fallback disagree with the source whenever a caller supplies a longer
    // deterministic step.
    const piece = amount / MARBLE.SUBSTEPS;
    for (let index = 0; index < MARBLE.SUBSTEPS; index++) this.substep(piece);
  }

  substep(dt) {
    const sinRoll = Math.sin(this.roll), cosRoll = Math.cos(this.roll);
    const sinPitch = Math.sin(this.pitch), cosPitch = Math.cos(this.pitch);
    const gx = MARBLE.GRAVITY * sinRoll;
    const gy = -MARBLE.GRAVITY * cosRoll * sinPitch;
    const gn = MARBLE.GRAVITY * cosRoll * cosPitch;
    const restingTilt = Math.hypot(gx, gy) <= MARBLE.ROLLING_RESISTANCE * gn;

    for (const marble of this.marbles) {
      if (marble.state === "rolling") {
        const hole = this.holeUnder(marble);
        if (hole) {
          marble.state = "falling";
          marble.over = hole;
          marble.z = MARBLE.RADIUS;
          marble.vz = 0;
        }
      }
      if (marble.state === "falling") {
        marble.x += marble.vx * dt;
        marble.y += marble.vy * dt;
        marble.z += marble.vz * dt;
        marble.vz -= gn * dt;
        this.resolveWalls(marble);
        this.finishFall(marble, gn);
        continue;
      }
      if (marble.state !== "rolling") continue;

      const beforeVx = marble.vx, beforeVy = marble.vy;
      // Gravity first creates contact-patch slip. The floor impulse then
      // spends two sevenths on sphere rotation and leaves five sevenths as
      // travel, while retaining independent spin after impacts.
      marble.vx += gx * dt;
      marble.vy += gy * dt;
      applyFloorFriction(marble, gn, dt);
      applyRollingResistance(marble, gn, dt);
      applySpinGrip(marble, gn, dt);
      const keep = Math.max(0, 1 - MARBLE.VISCOUS_DRAG * dt);
      marble.vx *= keep;
      marble.vy *= keep;
      const speed = hypot2(marble.vx, marble.vy);
      if (speed > MARBLE.SPEED_CAP) {
        const scale = MARBLE.SPEED_CAP / speed;
        marble.vx *= scale;
        marble.vy *= scale;
        // The native Simulation scales the rolling spin with the capped
        // travel as well. Leaving wx/wy untouched makes the fallback resume
        // with a source-inconsistent contact-point speed on the next floor
        // solve, especially after a deliberately staged high-speed replay.
        marble.wx *= scale;
        marble.wy *= scale;
      }
      // Match Simulation._substep in the original Python task exactly. The
      // explicit browser solver must not enlarge the source's rest band: doing
      // so makes a marble stop early after a wall contact and changes whether a
      // certified route reaches its cup.
      if (Math.abs(marble.wz) < MARBLE.REST_SPEED / MARBLE.RADIUS) {
        marble.wz = 0;
      }
      if (restingTilt && hypot2(marble.vx, marble.vy) < MARBLE.REST_SPEED &&
          hypot2(marble.wx, marble.wy) < MARBLE.REST_SPEED / MARBLE.RADIUS) {
        marble.vx = 0;
        marble.vy = 0;
        marble.wx = 0;
        marble.wy = 0;
      }
      marble.x += marble.vx * dt;
      marble.y += marble.vy * dt;
      this.resolveWalls(marble);
      if (marble.state === "rolling") {
        const jolt = hypot2(marble.vx - beforeVx - gx * dt,
                            marble.vy - beforeVy - gy * dt);
        if (jolt > 0.02) this.struckThisStep = Math.max(this.struckThisStep, Math.min(1, jolt * 1.6));
      }
    }
    this.resolveMarbleContacts();
    // Pair separation can move a second marble back into a rail after the
    // first wall pass. MuJoCo solves both contact families together; one
    // bounded projection here keeps the fallback's final state outside every
    // wall without turning this small solver into an unbounded iteration.
    for (const marble of this.marbles) {
      if (marble.state === "rolling" || marble.state === "falling") {
        this.resolveWalls(marble);
      }
    }
    for (const marble of this.marbles) {
      if (marble.state === "rolling") {
        const hole = this.holeUnder(marble);
        if (hole) {
          marble.state = "falling";
          marble.over = hole;
          marble.z = MARBLE.RADIUS;
          marble.vz = 0;
        }
      }
    }
    // Contacts can change spin (especially a rail graze), so integrate the
    // visible orientation only after all contacts for this substep settle.
    for (const marble of this.marbles) {
      if (marble.state === "rolling" || marble.state === "falling") {
        integrateOrientation(marble, dt);
      }
    }
  }

  holeUnder(marble) {
    return this.board.holes.find((hole) => hypot2(marble.x - hole.x, marble.y - hole.y) < hole.radius) || null;
  }

  finishFall(marble, gn) {
    const hole = marble.over;
    if (!hole) {
      // Match Simulation._over_the_lip: a falling state without an owning
      // hole is recovered onto the tray, not converted into an unrelated
      // loss. The normal path always has a hole, but this keeps malformed or
      // externally staged states source-compatible too.
      marble.z = MARBLE.RADIUS;
      marble.vz = 0;
      marble.state = "rolling";
      this.rollWithTravel(marble);
      return;
    }
    const stillOver = hypot2(marble.x - hole.x, marble.y - hole.y) < hole.radius;
    if (stillOver && marble.z <= 0) {
      marble.state = hole.home ? "home" : "lost";
      if (hole.home) this.cuppedThisStep++;
      else this.lostThisStep++;
      return;
    }
    if (stillOver) return;

    // The far lip costs the potential energy needed to climb back out. This
    // is the same energy toll used by Simulation._over_the_lip in the source.
    const drop = MARBLE.RADIUS - marble.z;
    const speed2 = marble.vx * marble.vx + marble.vy * marble.vy;
    const need = Math.max(0, 2 * gn * drop);
    if (speed2 <= need) {
      marble.state = hole.home ? "home" : "lost";
      if (hole.home) this.cuppedThisStep++;
      else this.lostThisStep++;
      return;
    }
    const keep = Math.sqrt(Math.max(0, (speed2 - need) / speed2));
    marble.vx *= keep;
    marble.vy *= keep;
    marble.z = MARBLE.RADIUS;
    marble.vz = 0;
    marble.over = null;
    marble.state = "rolling";
    this.rollWithTravel(marble);
    this.struckThisStep = Math.max(this.struckThisStep, Math.min(1, drop / MARBLE.RADIUS));
  }

  rollWithTravel(marble) {
    marble.wy = marble.vx / MARBLE.RADIUS;
    marble.wx = -marble.vy / MARBLE.RADIUS;
  }

  slipping(marble) {
    return hypot2(marble.vx - MARBLE.RADIUS * marble.wy,
      marble.vy + MARBLE.RADIUS * marble.wx);
  }

  resolveWalls(marble) {
    // MuJoCo solves the floor and a rail in one coupled contact problem. The
    // fallback resolves them in two small passes, so a diagonal rail impact
    // can otherwise leave the rebound velocity pointing out of the wall
    // while the old rolling spin makes the next floor-friction pass consume
    // that velocity. Remember only mixed (normal + tangential) impacts; a
    // square hit must retain its deliberate wall skid.
    let restoreRollingAfterImpact = false;
    for (const wall of this.board.walls) {
      // A wall is a vertical box, so its explicit contact remains active for
      // a falling marble while the sphere overlaps the box's height. The
      // floor contact is the only contact that falling disables.
      const verticalGap = marble.z < 0 ? -marble.z :
        (marble.z > this.board.height ? marble.z - this.board.height : 0);
      if (verticalGap >= MARBLE.RADIUS) continue;
      const closestX = clamp(marble.x, wall.x0, wall.x1);
      const closestY = clamp(marble.y, wall.y0, wall.y1);
      let nx = marble.x - closestX, ny = marble.y - closestY;
      let distance = hypot2(nx, ny);
      if (distance >= MARBLE.RADIUS) continue;
      if (distance < 1e-10) {
        const left = Math.abs(marble.x - wall.x0), right = Math.abs(wall.x1 - marble.x);
        const bottom = Math.abs(marble.y - wall.y0), top = Math.abs(wall.y1 - marble.y);
        if (Math.min(left, right) < Math.min(bottom, top)) {
          nx = left < right ? -1 : 1; ny = 0;
        } else {
          nx = 0; ny = bottom < top ? -1 : 1;
        }
        distance = 0;
      } else {
        nx /= distance; ny /= distance;
      }
      const push = MARBLE.RADIUS - distance;
      marble.x += nx * push;
      marble.y += ny * push;
      const intoWall = marble.vx * nx + marble.vy * ny;
      let normalImpulse = 0;
      if (intoWall < 0) {
        normalImpulse = -(1 + MARBLE.WALL_RESTITUTION) * intoWall;
        marble.vx += normalImpulse * nx;
        marble.vy += normalImpulse * ny;
        // The wall's low friction changes the spin about the tray normal,
        // but deliberately does not slave the sphere's rolling axes to its
        // new rebound velocity. That surviving skid is visible in the
        // native game's wall-hug behavior.
        const tx = -ny, ty = nx;
        const tangentialSlip = marble.vx * tx + marble.vy * ty -
          MARBLE.RADIUS * marble.wz;
        const wanted = -tangentialSlip * MARBLE.SLIP_SHARE;
        const tangentImpulse = clamp(wanted,
          -MARBLE.WALL_FRICTION * normalImpulse,
          MARBLE.WALL_FRICTION * normalImpulse);
        marble.vx += tangentImpulse * tx;
        marble.vy += tangentImpulse * ty;
        marble.wz -= tangentImpulse /
          (MARBLE.SPHERE_INERTIA * MARBLE.RADIUS);

        // The source wall pair is `condim=3`: besides the tray-plane
        // tangent above, MuJoCo solves the wall's vertical tangent too. A
        // marble resting on the floor has no useful vertical translation,
        // but that contact impulse still changes wx/wy through the sphere's
        // lever arm. Omitting it leaves the old roll spin on a wall, and the
        // floor solver then removes the small outward velocity that should
        // carry the marble away from a corner.
        const verticalSlip = marble.vz + MARBLE.RADIUS *
          (marble.wy * nx - marble.wx * ny);
        const verticalImpulse = clamp(-verticalSlip * MARBLE.SLIP_SHARE,
          -MARBLE.WALL_FRICTION * normalImpulse,
          MARBLE.WALL_FRICTION * normalImpulse);
        marble.vz += verticalImpulse;
        marble.wx -= ny * verticalImpulse /
          (MARBLE.SPHERE_INERTIA * MARBLE.RADIUS);
        marble.wy += nx * verticalImpulse /
          (MARBLE.SPHERE_INERTIA * MARBLE.RADIUS);
        const outgoing = marble.vx * nx + marble.vy * ny;
        const tangent = Math.abs(marble.vx * -ny + marble.vy * nx);
        if (outgoing > 0.0 && tangent > 0.02) {
          restoreRollingAfterImpact = true;
        }
        this.struckThisStep = Math.max(this.struckThisStep, Math.min(1, -intoWall * 1.6));
      }
    }
    if (restoreRollingAfterImpact) this.rollWithTravel(marble);
  }

  resolveMarbleContacts() {
    for (let left = 0; left < this.marbles.length; left++) {
      const first = this.marbles[left];
      if (first.state !== "rolling" && first.state !== "falling") continue;
      for (let right = left + 1; right < this.marbles.length; right++) {
        const second = this.marbles[right];
        if (second.state !== "rolling" && second.state !== "falling") continue;
        let nx = second.x - first.x, ny = second.y - first.y;
        const nz = second.z - first.z;
        let distance = Math.hypot(nx, ny, nz);
        const minimum = 2 * MARBLE.RADIUS;
        if (distance >= minimum) continue;
        if (distance < 1e-10) {
          nx = 1; ny = 0; distance = 0;
        } else {
          nx /= distance; ny /= distance;
        }
        const push = (minimum - distance) / 2;
        first.x -= nx * push; first.y -= ny * push;
        second.x += nx * push; second.y += ny * push;
        const relative = (second.vx - first.vx) * nx + (second.vy - first.vy) * ny;
        let normalImpulse = 0;
        if (relative < 0) {
          normalImpulse = -(1 + MARBLE.BALL_RESTITUTION) * relative / 2;
          first.vx -= normalImpulse * nx; first.vy -= normalImpulse * ny;
          second.vx += normalImpulse * nx; second.vy += normalImpulse * ny;
        }
        if (normalImpulse > 0 && hypot2(nx, ny) > 1e-10) {
          const length = hypot2(nx, ny);
          const tx = -ny / length, ty = nx / length;
          const relativeTangential = (second.vx - first.vx) * tx +
            (second.vy - first.vy) * ty - MARBLE.RADIUS *
            (second.wz + first.wz);
          const wanted = -relativeTangential * MARBLE.SLIP_SHARE / 2;
          const tangentImpulse = clamp(wanted,
            -MARBLE.BALL_FRICTION * normalImpulse,
            MARBLE.BALL_FRICTION * normalImpulse);
          first.vx -= tangentImpulse * tx;
          first.vy -= tangentImpulse * ty;
          second.vx += tangentImpulse * tx;
          second.vy += tangentImpulse * ty;
          const spinChange = tangentImpulse /
            (MARBLE.SPHERE_INERTIA * MARBLE.RADIUS);
          first.wz -= spinChange;
          second.wz -= spinChange;
        }
        if (normalImpulse > 0) {
          this.struckThisStep = Math.max(this.struckThisStep,
            Math.min(1, normalImpulse * 1.6));
        }
      }
    }
  }
}
