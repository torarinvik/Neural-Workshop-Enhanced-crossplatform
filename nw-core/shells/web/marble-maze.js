// Browser-side Marble Maze runtime.
//
// The reference uses MuJoCo for the rigid-body solve. That native dependency
// cannot be loaded by a standalone browser page, so this module keeps the
// reference's SI constants, tray geometry, hole rules, speed cap, tilt
// convention, and fixed-step discipline while solving the small 2D contact
// problem locally. The tray itself is not approximated: it is decoded from
// the certified board produced by tasks/marblemaze.elisa.

const MAGIC = 826496845; // "MMB1" little-endian
const VERSION = 1;

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

function clamp(value, low, high) {
  return Math.max(low, Math.min(high, value));
}

function hypot2(x, y) {
  return Math.hypot(x, y);
}

// Decode the compact board ABI. Everything is copied out of the WASM view so
// memory growth or the next frame cannot invalidate an in-flight run.
export function decodeMarbleBoard(bytes) {
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  let at = 0;
  const u32 = () => {
    const value = view.getUint32(at, true);
    at += 4;
    return value;
  };
  const f32 = () => {
    const value = view.getFloat32(at, true);
    at += 4;
    return value;
  };
  if (bytes.byteLength < 24 || u32() !== MAGIC || u32() !== VERSION) {
    throw new Error("marble board: bad header");
  }
  const built = u32() !== 0;
  const rung = u32();
  const cols = u32();
  const rows = u32();
  const board = {
    built, rung, cols, rows,
    width: f32(), depth: f32(), cell: f32(), thickness: f32(), height: f32(),
    home: { x: f32(), y: f32(), radius: f32() },
    seconds: f32(), route: f32(), walls: [], holes: [], starts: [],
  };
  const wallCount = u32();
  for (let index = 0; index < wallCount; index++) {
    board.walls.push({ x0: f32(), y0: f32(), x1: f32(), y1: f32() });
  }
  const holeCount = u32();
  for (let index = 0; index < holeCount; index++) {
    board.holes.push({ x: f32(), y: f32(), radius: f32(), home: u32() !== 0 });
  }
  const startCount = u32();
  for (let index = 0; index < startCount; index++) {
    board.starts.push({ x: f32(), y: f32() });
  }
  if (at > bytes.byteLength) throw new Error("marble board: truncated data");
  return board;
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

  // Match the native UI's restart contract: recreate the physical state and
  // level the tray, but keep the run clock. Restarting is not a free retry.
  restart() {
    const elapsed = this.elapsed;
    this.reset();
    this.elapsed = elapsed;
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
    if (!piece || this.settled) return;
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
    let left = piece;
    while (left > 1e-9) {
      const bite = Math.min(left, 1 / 60);
      this.step(bite);
      left -= bite;
      if (this.settled) break;
    }
  }

  step(dt) {
    this.cuppedThisStep = 0;
    this.lostThisStep = 0;
    this.struckThisStep = 0;
    this.elapsed += dt;
    // Keep contact impulses bounded even when a test or a paused tab asks for
    // a multi-second step. The native driver feeds 60 Hz bites, and this
    // preserves that same four-contact-substep cadence for direct callers.
    const slices = Math.max(1, Math.ceil(Math.max(0, dt) * 60));
    const piece = dt / slices / MARBLE.SUBSTEPS;
    for (let slice = 0; slice < slices; slice++) {
      for (let index = 0; index < MARBLE.SUBSTEPS; index++) this.substep(piece);
    }
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
      }
      // The browser's explicit impulse solver has a small residual below
      // MuJoCo's regularised contact noise floor; use the same visible
      // millimetre-scale stopping band rather than leaving a barely moving
      // marble crawling during a levelled-tray command.
      if (restingTilt && hypot2(marble.vx, marble.vy) < 1.5 * MARBLE.REST_SPEED &&
          hypot2(marble.wx, marble.wy) < 1.5 * MARBLE.REST_SPEED / MARBLE.RADIUS) {
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
      marble.state = "lost";
      this.lostThisStep++;
      return;
    }
    const stillOver = hypot2(marble.x - hole.x, marble.y - hole.y) < hole.radius;
    if (stillOver && marble.z <= 0) {
      marble.state = hole.home ? "home" : "lost";
      marble.over = null;
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
      marble.over = null;
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
        this.struckThisStep = Math.max(this.struckThisStep, Math.min(1, -intoWall * 1.6));
      }
    }
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
