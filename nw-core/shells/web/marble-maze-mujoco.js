// MuJoCo-backed Marble Maze runtime.
//
// The native game delegates the rigid-body solve to MuJoCo. This module uses
// the official single-threaded MuJoCo WebAssembly build and keeps the same
// MJCF, state adapter, and wrapper rules as neural_workshop/marblemaze.py.

import loadMujoco from "./vendor/mujoco/mujoco.js";
import { MARBLE } from "./marble-maze.js";

function clamp(value, low, high) {
  return Math.max(low, Math.min(high, value));
}

function hypot2(x, y) {
  return Math.hypot(x, y);
}

function quatRotate(q, v) {
  const [w, x, y, z] = q;
  const [vx, vy, vz] = v;
  const tx = 2 * (y * vz - z * vy);
  const ty = 2 * (z * vx - x * vz);
  const tz = 2 * (x * vy - y * vx);
  return [
    vx + w * tx + y * tz - z * ty,
    vy + w * ty + z * tx - x * tz,
    vz + w * tz + x * ty - y * tx,
  ];
}

function quatUnrotate(q, v) {
  return quatRotate([q[0], -q[1], -q[2], -q[3]], v);
}

function stateFor(start) {
  return {
    x: start.x, y: start.y, vx: 0, vy: 0, z: MARBLE.RADIUS, vz: 0,
    wx: 0, wy: 0, wz: 0, qw: 1, qx: 0, qy: 0, qz: 0,
    state: "rolling", over: null,
  };
}

function mjcf(board, count) {
  const crr = MARBLE.ROLLING_RESISTANCE * MARBLE.RADIUS;
  const parts = [
    "<mujoco>",
    `<option integrator="implicitfast" cone="elliptic" ` +
      `noslip_iterations="2" timestep="0.004" ` +
      `gravity="0 0 -${MARBLE.GRAVITY.toFixed(5)}"/>`,
    "<worldbody>",
    `<geom name="floor" type="plane" size="${Math.max(board.width, 1).toFixed(4)} ` +
      `${Math.max(board.depth, 1).toFixed(4)} 0.1" ` +
      `friction="${MARBLE.FRICTION_STATIC.toFixed(3)} ` +
      `${MARBLE.SPIN_GRIP.toFixed(4)} ${crr.toFixed(6)}" ` +
      `condim="6" contype="1" conaffinity="1"/>`,
  ];
  board.walls.forEach((wall, index) => {
    parts.push(
      `<geom name="wall${index}" type="box" ` +
      `pos="${((wall.x0 + wall.x1) / 2).toFixed(6)} ` +
      `${((wall.y0 + wall.y1) / 2).toFixed(6)} ` +
      `${(board.height / 2).toFixed(6)}" ` +
      `size="${Math.max(1e-4, (wall.x1 - wall.x0) / 2).toFixed(6)} ` +
      `${Math.max(1e-4, (wall.y1 - wall.y0) / 2).toFixed(6)} ` +
      `${(board.height / 2).toFixed(6)}" contype="0" conaffinity="0"/>`,
    );
  });
  for (let index = 0; index < count; index++) {
    const start = board.starts[index] ?? { x: 10 + index, y: 10 };
    parts.push(
      `<body name="ball${index}" pos="${start.x.toFixed(6)} ` +
      `${start.y.toFixed(6)} ${MARBLE.RADIUS.toFixed(6)}"><freejoint/>` +
      `<geom name="ball${index}" type="sphere" ` +
      `size="${MARBLE.RADIUS.toFixed(4)}" density="7800" ` +
      `friction="${MARBLE.FRICTION_STATIC.toFixed(3)} ` +
      `${MARBLE.SPIN_GRIP.toFixed(4)} ${crr.toFixed(6)}" ` +
      `condim="3" contype="1" conaffinity="1"/></body>`,
    );
  }
  parts.push("</worldbody><contact>");
  for (let ball = 0; ball < count; ball++) {
    for (let wall = 0; wall < board.walls.length; wall++) {
      parts.push(
        `<pair geom1="ball${ball}" geom2="wall${wall}" condim="3" ` +
        `solref="0.009 1.0" friction="${MARBLE.WALL_FRICTION.toFixed(3)} ` +
        `${MARBLE.WALL_FRICTION.toFixed(3)} 0.0001 0.0001 0.0001"/>`,
      );
    }
    for (let other = ball + 1; other < count; other++) {
      parts.push(
        `<pair geom1="ball${ball}" geom2="ball${other}" condim="3" ` +
        `solref="0.009 0.03" ` +
        `friction="0.05 0.05 0.0001 0.0001 0.0001"/>`,
      );
    }
  }
  parts.push("</contact></mujoco>");
  return parts.join("");
}

function setVector(vector, values) {
  for (let index = 0; index < values.length; index++) vector[index] = values[index];
}

export function makeMarbleMazeMuJoCoGame(mujoco) {
  return class MarbleMazeMuJoCoGame {
    constructor(board) {
      if (!board || !board.built || !board.starts.length) {
        throw new Error("marble board is not built");
      }
      this.mujoco = mujoco;
      this.board = board;
      this.roll = 0;
      this.pitch = 0;
      this.elapsed = 0;
      this.cuppedThisStep = 0;
      this.lostThisStep = 0;
      this.struckThisStep = 0;
      this.nudgeDue = 0;
      this.model = null;
      this.data = null;
      this.ballGeoms = [];
      this.builtFor = -1;
      this.reset();
    }

    reset() {
      this.disposeEngine();
      this.marbles = this.board.starts.map(stateFor);
      this.roll = 0;
      this.pitch = 0;
      this.elapsed = 0;
      this.cuppedThisStep = 0;
      this.lostThisStep = 0;
      this.struckThisStep = 0;
      this.nudgeDue = 0;
    }

    restart() {
      const elapsed = this.elapsed;
      this.reset();
      this.elapsed = elapsed;
    }

    disposeEngine() {
      if (this.data) this.data.delete();
      if (this.model) this.model.delete();
      this.data = null;
      this.model = null;
      this.ballGeoms = [];
      this.builtFor = -1;
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
      const amount = Number(dt) || 0;
      if (amount <= 0 || this.settled) return;
      this.cuppedThisStep = 0;
      this.lostThisStep = 0;
      this.struckThisStep = 0;
      this.elapsed += amount;
      const piece = amount / MARBLE.SUBSTEPS;
      for (let index = 0; index < MARBLE.SUBSTEPS; index++) this.substep(piece);
    }

    ensureEngine() {
      const count = this.marbles.length;
      if (this.model && count === this.builtFor) return;
      this.disposeEngine();
      this.model = this.mujoco.MjModel.from_xml_string(mjcf(this.board, count));
      this.data = new this.mujoco.MjData(this.model);
      // MJCF emits floor, walls, then one sphere geom per ball.
      const firstBall = 1 + this.board.walls.length;
      this.ballGeoms = Array.from({ length: count }, (_, index) => firstBall + index);
      this.builtFor = count;
    }

    substep(dt) {
      this.ensureEngine();
      const { model, data } = this;
      const sinRoll = Math.sin(this.roll), cosRoll = Math.cos(this.roll);
      const sinPitch = Math.sin(this.pitch), cosPitch = Math.cos(this.pitch);
      const gx = MARBLE.GRAVITY * sinRoll;
      const gy = -MARBLE.GRAVITY * cosRoll * sinPitch;
      const gn = MARBLE.GRAVITY * cosRoll * cosPitch;
      setVector(model.opt.gravity, [gx, gy, -gn]);
      model.opt.timestep = dt;

      for (let index = 0; index < this.marbles.length; index++) {
        const marble = this.marbles[index];
        const geom = this.ballGeoms[index];
        if (marble.state === "rolling") {
          const hole = this.holeUnder(marble);
          if (hole) {
            marble.state = "falling";
            marble.over = hole;
          }
        }
        const base = index * 7;
        const vbase = index * 6;
        if (marble.state === "rolling" || marble.state === "falling") {
          const grounded = marble.state === "rolling" ? 1 : 0;
          model.geom_contype[geom] = grounded;
          model.geom_conaffinity[geom] = grounded;
          setVector(data.qpos.subarray(base, base + 7), [
            marble.x, marble.y, marble.z, marble.qw, marble.qx, marble.qy, marble.qz,
          ]);
          setVector(data.qvel.subarray(vbase, vbase + 6), [
            marble.vx, marble.vy, marble.vz,
            ...quatUnrotate([marble.qw, marble.qx, marble.qy, marble.qz],
              [marble.wx, marble.wy, marble.wz]),
          ]);
        } else {
          model.geom_contype[geom] = 0;
          model.geom_conaffinity[geom] = 0;
          setVector(data.qpos.subarray(base, base + 7), [10 + index, 10, 1, 1, 0, 0, 0]);
          setVector(data.qvel.subarray(vbase, vbase + 6), [0, 0, 0, 0, 0, 0]);
        }
      }

      const before = this.marbles.map((marble) =>
        (marble.state === "rolling" || marble.state === "falling") ? [marble.vx, marble.vy] : null);
      this.mujoco.mj_step(model, data);

      for (let index = 0; index < this.marbles.length; index++) {
        const marble = this.marbles[index];
        if (marble.state !== "rolling" && marble.state !== "falling") continue;
        const base = index * 7;
        const vbase = index * 6;
        marble.x = Number(data.qpos[base]);
        marble.y = Number(data.qpos[base + 1]);
        marble.z = Number(data.qpos[base + 2]);
        marble.qw = Number(data.qpos[base + 3]);
        marble.qx = Number(data.qpos[base + 4]);
        marble.qy = Number(data.qpos[base + 5]);
        marble.qz = Number(data.qpos[base + 6]);
        marble.vx = Number(data.qvel[vbase]);
        marble.vy = Number(data.qvel[vbase + 1]);
        marble.vz = Number(data.qvel[vbase + 2]);
        [marble.wx, marble.wy, marble.wz] = quatRotate(
          [marble.qw, marble.qx, marble.qy, marble.qz],
          [Number(data.qvel[vbase + 3]), Number(data.qvel[vbase + 4]), Number(data.qvel[vbase + 5])],
        );
      }

      for (const marble of this.marbles) {
        if (marble.state !== "falling") continue;
        const over = this.holeUnder(marble);
        if (!over) this.overTheLip(marble, gn);
        else {
          marble.over = over;
          if (marble.z <= 0) this.swallow(marble, over);
        }
      }

      const restingTilt = hypot2(gx, gy) <= MARBLE.ROLLING_RESISTANCE * gn;
      for (let index = 0; index < this.marbles.length; index++) {
        const marble = this.marbles[index];
        if (marble.state !== "rolling" && marble.state !== "falling") continue;
        const keep = 1 - MARBLE.VISCOUS_DRAG * dt;
        marble.vx *= keep;
        marble.vy *= keep;
        const speed = hypot2(marble.vx, marble.vy);
        if (speed > MARBLE.SPEED_CAP) {
          const scale = MARBLE.SPEED_CAP / speed;
          marble.vx *= scale;
          marble.vy *= scale;
          marble.wx *= scale;
          marble.wy *= scale;
        }
        if (marble.state === "rolling") {
          if (Math.abs(marble.wz) < MARBLE.REST_SPEED / MARBLE.RADIUS) marble.wz = 0;
          if (restingTilt && hypot2(marble.vx, marble.vy) < MARBLE.REST_SPEED &&
              hypot2(marble.wx, marble.wy) < MARBLE.REST_SPEED / MARBLE.RADIUS) {
            marble.vx = 0;
            marble.vy = 0;
            marble.wx = 0;
            marble.wy = 0;
          }
        }
        const was = before[index];
        if (was) {
          const jolt = hypot2(marble.vx - was[0] - gx * dt,
            marble.vy - was[1] - gy * dt);
          if (jolt > 0.02) this.struckThisStep = Math.max(this.struckThisStep, Math.min(1, jolt * 1.6));
        }
      }
    }

    holeUnder(marble) {
      return this.board.holes.find((hole) =>
        hypot2(marble.x - hole.x, marble.y - hole.y) < hole.radius) || null;
    }

    overTheLip(marble, gn) {
      const hole = marble.over;
      const drop = MARBLE.RADIUS - marble.z;
      if (hole && drop > 0) {
        const have = marble.vx * marble.vx + marble.vy * marble.vy;
        const need = 2 * gn * drop;
        if (have <= need) {
          this.swallow(marble, hole);
          return;
        }
        const keep = Math.sqrt((have - need) / have);
        marble.vx *= keep;
        marble.vy *= keep;
        this.struckThisStep = Math.max(this.struckThisStep, Math.min(1, drop / MARBLE.RADIUS));
      }
      marble.z = MARBLE.RADIUS;
      marble.vz = 0;
      marble.over = null;
      marble.state = "rolling";
      this.rollWithTravel(marble);
    }

    swallow(marble, hole) {
      marble.state = hole.home ? "home" : "lost";
      marble.over = null;
      if (hole.home) this.cuppedThisStep += 1;
      else this.lostThisStep += 1;
    }

    rollWithTravel(marble) {
      marble.wy = marble.vx / MARBLE.RADIUS;
      marble.wx = -marble.vy / MARBLE.RADIUS;
    }

    slipping(marble) {
      return hypot2(marble.vx - MARBLE.RADIUS * marble.wy,
        marble.vy + MARBLE.RADIUS * marble.wx);
    }
  };
}

export async function loadMarbleMazeMuJoCo() {
  return makeMarbleMazeMuJoCoGame(await loadMujoco());
}
