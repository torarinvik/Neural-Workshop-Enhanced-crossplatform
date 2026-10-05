import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { spawnSync } from "node:child_process";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { decodeMarbleBoard, MARBLE } from "../shells/web/marble-maze.js";
import { loadMarbleMazeMuJoCo } from "../shells/web/marble-maze-mujoco.js";

const testDirectory = path.dirname(fileURLToPath(import.meta.url));
const repositoryRoot = path.resolve(testDirectory, "../..");
const referenceRoot = process.env.NW_REFERENCE_ROOT ??
  path.resolve(repositoryRoot, "../../Python Projects/neural-workshop-enhanced");
const python = process.env.NW_REFERENCE_PYTHON ??
  path.join(referenceRoot, ".venv/bin/python3");
if (!fs.existsSync(python)) {
  throw new Error(`Python reference interpreter not found: ${python}; set NW_REFERENCE_PYTHON`);
}

const wasmPath = process.env.NWCORE_WASM_PATH ??
  path.resolve(testDirectory, "../build/nwcore.wasm");
const wasm = fs.readFileSync(wasmPath);
const { exports, instance } = await instantiateElisa(wasm, { warn: false });
const boardPointer = Number(exports.nw_frame_alloc(65536n));
const boardLength = Number(exports.nw_marble_board_write(
  BigInt(boardPointer), 65536n, 1n, 17n));
assert.ok(boardLength > 0, "WASM failed to produce the canonical trajectory board");
const canonicalBoard = decodeMarbleBoard(
  new Uint8Array(instance.exports.memory.buffer, boardPointer, boardLength));

function emptyBoard(overrides = {}) {
  return {
    built: true, rung: 1, cols: 1, rows: 1, width: 1, depth: 1,
    cell: 1, thickness: 0.01, height: 0.01, seconds: 45, route: 1,
    home: { x: 0.8, y: 0.5, radius: 0.08 },
    walls: [], holes: [], starts: [{ x: 0.1, y: 0.5 }], ...overrides,
  };
}

function frames(count, dt = 1 / 60, actionsAt = {}) {
  return Array.from({ length: count }, (_, index) => ({
    dt,
    actions: actionsAt[index] ?? [],
  }));
}

const cases = [
  {
    name: "canonical rung-1 stationary and four-direction tilt sequence",
    board: canonicalBoard,
    initial: [],
    frames: frames(180, 1 / 60, {
      0: Array(20).fill("E"),
      35: Array(50).fill("W"),
      70: Array(20).fill("N"),
      105: Array(50).fill("S"),
      140: ["N", "S", "E", "W"],
      145: ["level"],
    }),
    coverage: "tilt-saturation",
  },
  {
    name: "rest threshold, low residual speed, and tiny dt accumulation",
    board: emptyBoard(),
    initial: [{ vx: 0.005, vy: 0.002, wx: -0.2, wy: 0.3, wz: 0.1 }],
    frames: [...Array.from({ length: 90 }, () => ({ dt: 1 / 144, actions: [] })),
      { dt: 1e-7, actions: [] }, { dt: 1e-7, actions: [] }],
    coverage: "rest",
  },
  {
    name: "speed cap and spin scaling",
    board: emptyBoard(),
    initial: [{ vx: 3, vy: 4, wx: -4 / 0.0075, wy: 3 / 0.0075, wz: 3 }],
    frames: [{ dt: 1e-6, actions: [] }, ...frames(12, 1 / 60)],
    coverage: "speed-cap",
  },
  {
    name: "normal wall impact",
    board: emptyBoard({
      walls: [{ x0: 0.3, y0: 0.02, x1: 0.31, y1: 0.40 }],
      starts: [{ x: 0.20, y: 0.20 }],
    }),
    initial: [{ vx: 0.5, wy: 0.5 / 0.0075 }],
    frames: frames(100),
    coverage: "wall-impact",
  },
  {
    name: "glancing wall impact under diagonal tilt",
    board: emptyBoard({
      walls: [{ x0: 0.3, y0: 0.02, x1: 0.31, y1: 0.40 }],
      starts: [{ x: 0.20, y: 0.22 }],
    }),
    initial: [{ vx: 0.42, vy: 0.08, wx: -0.6 / 0.0075, wy: 0.42 / 0.0075 }],
    frames: frames(90, 1 / 60, { 0: [...Array(12).fill("E"), ...Array(9).fill("N")] }),
    coverage: "wall-impact",
  },
  {
    name: "three-body contact chain",
    board: emptyBoard({
      starts: [{ x: 0.15, y: 0.25 }, { x: 0.20, y: 0.25 }, { x: 0.25, y: 0.25 }],
    }),
    initial: [
      { vx: 0.32, wy: 0.32 / 0.0075 },
      {},
      { vx: -0.32, wy: -0.32 / 0.0075 },
    ],
    frames: frames(80, 1 / 120),
    coverage: "ball-impact",
  },
  {
    name: "two marbles begin touching with one at rest",
    board: emptyBoard({
      starts: [{ x: 0.20, y: 0.25 }, { x: 0.215, y: 0.25 }],
    }),
    initial: [{}, { vx: -0.12, wy: -0.12 / 0.0075 }],
    frames: frames(45, 1 / 120),
    coverage: "ball-impact",
  },
  {
    name: "simultaneous orthogonal corner impact",
    board: emptyBoard({
      walls: [
        { x0: 0.30, y0: 0.0, x1: 0.31, y1: 0.31 },
        { x0: 0.0, y0: 0.30, x1: 0.31, y1: 0.31 },
      ],
      starts: [{ x: 0.20, y: 0.20 }],
    }),
    initial: [{ vx: 0.42, vy: 0.42, wx: -0.42 / 0.0075, wy: 0.42 / 0.0075 }],
    frames: frames(80, 1 / 120),
    coverage: "wall-impact",
  },
  {
    name: "narrow corridor glancing contact",
    board: emptyBoard({
      walls: [
        { x0: 0.25, y0: 0.30, x1: 0.75, y1: 0.305 },
        { x0: 0.25, y0: 0.335, x1: 0.75, y1: 0.34 },
      ],
      starts: [{ x: 0.20, y: 0.315 }],
    }),
    initial: [{ vx: 0.38, vy: -0.03, wx: 0.03 / 0.0075, wy: 0.38 / 0.0075 }],
    frames: frames(90, 1 / 120),
    coverage: "wall-impact",
  },
  {
    name: "simultaneous wall and ball-pair impact",
    board: emptyBoard({
      walls: [{ x0: 0.30, y0: 0.10, x1: 0.31, y1: 0.90 }],
      starts: [{ x: 0.2924, y: 0.50 }, { x: 0.2774, y: 0.50 }],
    }),
    initial: [
      { vx: 0.25, wy: 0.25 / 0.0075 },
      { vx: 0.25, wy: 0.25 / 0.0075 },
    ],
    frames: frames(120, 1 / 240),
    coverage: "multi-impact",
  },
  {
    name: "four-marble simultaneous central contact",
    board: emptyBoard({
      starts: [
        { x: 0.4825, y: 0.50 }, { x: 0.5175, y: 0.50 },
        { x: 0.50, y: 0.4825 }, { x: 0.50, y: 0.5175 },
      ],
    }),
    initial: [
      { vx: 0.25, wy: 0.25 / 0.0075 },
      { vx: -0.25, wy: -0.25 / 0.0075 },
      { vy: 0.25, wx: -0.25 / 0.0075 },
      { vy: -0.25, wx: 0.25 / 0.0075 },
    ],
    frames: frames(120, 1 / 240),
    coverage: "multi-impact",
  },
  {
    name: "slow marble swallowed by pit",
    board: emptyBoard({
      holes: [{ x: 0.5, y: 0.5, radius: 0.012, home: false }],
      starts: [{ x: 0.45, y: 0.5 }],
    }),
    initial: [{ vx: 0.4, wy: 0.4 / 0.0075 }],
    frames: frames(180, 1 / 60),
    coverage: "lost",
  },
  {
    name: "fast marble clears pit lip",
    board: emptyBoard({
      holes: [{ x: 0.5, y: 0.5, radius: 0.012, home: false }],
      starts: [{ x: 0.45, y: 0.5 }],
    }),
    initial: [{ vx: 0.95, wy: 0.95 / 0.0075 }],
    frames: frames(90, 1 / 60),
    coverage: "cleared-pit",
  },
  {
    name: "falling marble collides with explicit wall pair",
    board: emptyBoard({
      holes: [{ x: 0.5, y: 0.5, radius: 0.014, home: false }],
      walls: [{ x0: 0.512, y0: 0.43, x1: 0.517, y1: 0.57 }],
      starts: [{ x: 0.45, y: 0.5 }],
    }),
    initial: [{ vx: 0.95, wy: 0.95 / 0.0075 }],
    frames: frames(45, 1 / 120),
    coverage: "falling-wall",
  },
  {
    name: "falling marble retains an explicit ball-pair contact",
    board: emptyBoard({
      holes: [{ x: 0.5, y: 0.5, radius: 0.014, home: false }],
      starts: [{ x: 0.45, y: 0.5 }, { x: 0.52, y: 0.5 }],
    }),
    initial: [
      { vx: 0.95, wy: 0.95 / 0.0075 },
      { vx: -0.18, wy: -0.18 / 0.0075 },
    ],
    frames: frames(60, 1 / 120),
    coverage: "falling-ball",
  },
  {
    name: "falling marble at simultaneous wall and ball contacts",
    board: emptyBoard({
      holes: [{ x: 0.5, y: 0.5, radius: 0.014, home: false }],
      walls: [{ x0: 0.512, y0: 0.43, x1: 0.517, y1: 0.57 }],
      starts: [{ x: 0.45, y: 0.5 }, { x: 0.52, y: 0.5 }],
    }),
    initial: [
      { vx: 0.95, wy: 0.95 / 0.0075 },
      { vx: -0.18, wy: -0.18 / 0.0075 },
    ],
    frames: frames(60, 1 / 120),
    coverage: "falling-multi-impact",
  },
  {
    name: "home cup capture",
    board: emptyBoard({
      holes: [{ x: 0.5, y: 0.5, radius: 0.08, home: true }],
      home: { x: 0.5, y: 0.5, radius: 0.08 },
      starts: [{ x: 0.42, y: 0.5 }],
    }),
    initial: [{ vx: 0.4, wy: 0.4 / 0.0075 }],
    frames: frames(90, 1 / 60),
    coverage: "home",
  },
  {
    name: "terminal marble parks while another marble remains live",
    board: emptyBoard({ starts: [{ x: 0.2, y: 0.2 }, { x: 0.3, y: 0.2 }] }),
    initial: [
      { x: -4, y: -7, vx: 2, vy: -1, state: "home" },
      { vx: 0.12, wy: 0.12 / 0.0075 },
    ],
    frames: frames(45, 1 / 120),
    coverage: "terminal-park",
  },
  {
    name: "already-lost marble stays parked while another marble moves",
    board: emptyBoard({ starts: [{ x: 0.2, y: 0.2 }, { x: 0.3, y: 0.2 }] }),
    initial: [
      { x: -6, y: -8, state: "lost" },
      { vx: 0.12, wy: 0.12 / 0.0075 },
    ],
    frames: frames(45, 1 / 120),
    coverage: "terminal-lost-park",
  },
  {
    name: "irregular frame partition with long capped-sized frames",
    board: emptyBoard(),
    initial: [{ vx: 0.03, vy: -0.02, wx: 1, wy: 3, wz: 0.4 }],
    frames: Array.from({ length: 120 }, (_, index) => ({
      dt: [0.05, 1 / 30, 1 / 60, 1 / 120, 1 / 144, 0.0073][index % 6],
      actions: index === 0 ? Array(24).fill("W") :
        index === 25 ? ["E", ...Array(24).fill("N")] : [],
    })),
    coverage: "tilt-saturation",
  },
  {
    name: "source UI frame clamp, held-key accumulator, and sub-nanosecond frame",
    board: emptyBoard(),
    initial: [],
    frames: [
      { advance: true, dt: 0.10, held: ["E"] },
      { advance: true, dt: 0.05, held: ["E", "N"] },
      { advance: true, dt: 0.0000000005, held: [] },
      { advance: true, dt: 0.012, held: ["W"] },
      { advance: true, dt: 0.003, held: ["W"] },
      { advance: true, dt: 0.021, held: ["S", "E"] },
      { advance: true, dt: 0.05, held: [] },
    ],
    coverage: "advance",
  },
  {
    name: "source clock boundaries: 60Hz nudge threshold, 50ms clamp, release, and wall impact",
    board: emptyBoard({
      walls: [{ x0: 0.24, y0: 0.08, x1: 0.25, y1: 0.92 }],
      starts: [{ x: 0.22, y: 0.50 }],
    }),
    initial: [{ vx: 0.40, wy: 0.40 / MARBLE.RADIUS }],
    frames: [
      { advance: true, dt: 1 / 60 - 1e-12, held: ["E"] },
      { advance: true, dt: 1e-12, held: ["E"] },
      { advance: true, dt: 1e-12, held: ["E"] },
      { advance: true, dt: 1 / 60 - 1e-12, held: ["E"] },
      { advance: true, dt: 0.004, held: [] },
      { advance: true, dt: 1 / 60, held: ["N"] },
      { advance: true, dt: 0.05 - 1e-12, held: ["N", "E"] },
      { advance: true, dt: 0.05, held: ["N", "E"] },
      { advance: true, dt: 0.05 + 1e-12, held: ["W"] },
      { advance: true, dt: 5e-10, held: ["W"] },
      { advance: true, dt: 0, held: ["W"] },
      { advance: true, dt: 1 / 120, held: ["W"] },
      { advance: true, dt: 1 / 120, held: ["W"] },
      { advance: true, dt: 1 / 120, held: [] },
      { advance: true, dt: 0.05, held: [] },
    ],
    coverage: "advance-boundary",
  },
];

const heldInputBoardLength = Number(exports.nw_marble_board_write(
  BigInt(boardPointer), 65536n, 16n, 889418965n));
assert.ok(heldInputBoardLength > 0,
  "WASM failed to produce the high-rung held-input replay board");
const heldInputBoard = decodeMarbleBoard(new Uint8Array(
  instance.exports.memory.buffer, boardPointer, heldInputBoardLength));
for (const [name, held] of [
  ["ArrowLeft and ArrowRight", ["E", "W"]],
  ["ArrowUp and ArrowDown", ["N", "S"]],
]) {
  cases.push({
    name: `rung-16 opposing ${name} held for 30 source-sized frames`,
    board: heldInputBoard,
    initial: [],
    frames: Array.from({ length: 30 }, () => ({
      advance: true, dt: 1 / 60, held,
    })),
    coverage: "opposed-held-input",
    seed: 889418965,
  });
}
cases.push({
  name: "rung-16 ArrowUp held for 30 source-sized frames",
  board: heldInputBoard,
  initial: [],
  frames: Array.from({ length: 30 }, () => ({
    advance: true, dt: 1 / 60, held: ["N"],
  })),
  coverage: "trace",
  seed: 889418965,
});
cases.push({
  name: "rung-16 opposing-key release preserves the remaining held direction",
  board: heldInputBoard,
  initial: [],
  frames: [
    ...Array.from({ length: 12 }, () => ({
      advance: true, dt: 1 / 60, held: ["E", "W"],
    })),
    ...Array.from({ length: 20 }, () => ({
      advance: true, dt: 1 / 60, held: ["E"],
    })),
    { advance: true, dt: 1 / 60, held: [] },
    ...Array.from({ length: 40 }, () => ({
      advance: true, dt: 1 / 60, held: ["W"],
    })),
  ],
  coverage: "held-key-rollover",
  seed: 889418965,
});

// One corner orientation is not enough to catch a sign error in the tray
// transform or a direction-dependent contact impulse. Exercise all four
// rotations of the same L-shaped rail with the corresponding incoming
// velocity and rolling spin. The Python reference and the browser adapter
// receive the same compact board, so these remain genuine source-vs-MuJoCo
// differential cases rather than symmetry assumptions in the assertion code.
for (const [name, vertical, horizontal, start, vx, vy] of [
  ["south-west", { x0: 0.30, y0: 0.0, x1: 0.31, y1: 0.31 },
    { x0: 0.0, y0: 0.30, x1: 0.31, y1: 0.31 }, { x: 0.20, y: 0.20 }, 0.42, 0.42],
  ["north-west", { x0: 0.30, y0: 0.69, x1: 0.31, y1: 1.0 },
    { x0: 0.0, y0: 0.69, x1: 0.31, y1: 0.71 }, { x: 0.20, y: 0.80 }, 0.42, -0.42],
  ["south-east", { x0: 0.69, y0: 0.0, x1: 0.71, y1: 0.31 },
    { x0: 0.69, y0: 0.30, x1: 1.0, y1: 0.31 }, { x: 0.80, y: 0.20 }, -0.42, 0.42],
  ["north-east", { x0: 0.69, y0: 0.69, x1: 0.71, y1: 1.0 },
    { x0: 0.69, y0: 0.69, x1: 1.0, y1: 0.71 }, { x: 0.80, y: 0.80 }, -0.42, -0.42],
]) {
  for (const [order, walls] of [
    ["vertical-first", [vertical, horizontal]],
    ["horizontal-first", [horizontal, vertical]],
  ]) {
    cases.push({
      name: `mirrored ${name} corner contact (${order})`,
      board: emptyBoard({ walls, starts: [start] }),
      initial: [{ vx, vy, wx: -vy / MARBLE.RADIUS, wy: vx / MARBLE.RADIUS }],
      frames: frames(120, 1 / 120),
      coverage: "corner-permutation",
    });
  }
}

cases.push({
  name: "three marbles converge on one L-corner",
  board: emptyBoard({
    walls: [
      { x0: 0.30, y0: 0.18, x1: 0.31, y1: 0.82 },
      { x0: 0.18, y0: 0.30, x1: 0.82, y1: 0.31 },
    ],
    starts: [
      { x: 0.25, y: 0.25 },
      { x: 0.24, y: 0.37 },
      { x: 0.37, y: 0.24 },
    ],
  }),
  initial: [
    { vx: 0.34, vy: 0.34, wx: -0.34 / MARBLE.RADIUS, wy: 0.34 / MARBLE.RADIUS },
    { vx: 0.34, wy: 0.34 / MARBLE.RADIUS },
    { vy: 0.34, wx: -0.34 / MARBLE.RADIUS },
  ],
  frames: frames(180, 1 / 240),
  coverage: "multi-corner-impact",
});

// Hand-authored scenes are excellent for isolating a known contact, but they
// can accidentally leave whole regions of the collision space unvisited.
// Add a deterministic stress matrix with varied rail positions, rail order,
// start spacing, initial spin, and irregular frame partitions.  The generator
// is deliberately a tiny local PRNG rather than Math.random so a failure is
// replayable from the case index and seed.
function seededRandom(seed) {
  let state = seed >>> 0;
  return () => {
    state = (Math.imul(state, 1664525) + 1013904223) >>> 0;
    return state / 0x100000000;
  };
}

for (let caseIndex = 0; caseIndex < 48; caseIndex++) {
  const random = seededRandom(0x4d4d0000 + caseIndex * 7919);
  const walls = [];
  const wallCount = 3 + Math.floor(random() * 5);
  for (let wallIndex = 0; wallIndex < wallCount; wallIndex++) {
    const horizontal = random() < 0.5;
    const thickness = 0.006 + random() * 0.014;
    const start = 0.10 + random() * 0.68;
    const length = 0.16 + random() * 0.55;
    if (horizontal) {
      const y = 0.10 + random() * 0.80;
      walls.push({ x0: start, y0: y, x1: Math.min(0.94, start + length), y1: Math.min(0.99, y + thickness) });
    } else {
      const x = 0.10 + random() * 0.80;
      walls.push({ x0: x, y0: start, x1: Math.min(0.99, x + thickness), y1: Math.min(0.94, start + length) });
    }
  }
  const marbleCount = 1 + Math.floor(random() * 4);
  const starts = [];
  const initial = [];
  for (let marbleIndex = 0; marbleIndex < marbleCount; marbleIndex++) {
    const x = 0.08 + random() * 0.84;
    const y = 0.08 + random() * 0.84;
    starts.push({ x, y });
    const vx = (random() - 0.5) * 0.72;
    const vy = (random() - 0.5) * 0.72;
    initial.push({
      vx, vy,
      wx: -vy / MARBLE.RADIUS + (random() - 0.5) * 18,
      wy: vx / MARBLE.RADIUS + (random() - 0.5) * 18,
      wz: (random() - 0.5) * 2,
    });
  }
  const actionKeys = ["N", "S", "E", "W"];
  const actionAt = {};
  for (let frameIndex = 0; frameIndex < 96; frameIndex += 12) {
    actionAt[frameIndex] = [actionKeys[Math.floor(random() * actionKeys.length)]];
    if (random() < 0.35) actionAt[frameIndex].push("level");
  }
  cases.push({
    name: `seeded arbitrary-contact stress ${caseIndex}`,
    board: emptyBoard({ walls, starts }),
    initial,
    frames: Array.from({ length: 96 }, (_, frameIndex) => ({
      dt: [1 / 30, 1 / 120, 0.05, 1 / 144, 1 / 60][frameIndex % 5],
      actions: actionAt[frameIndex] ?? [],
    })),
    coverage: "arbitrary-contact",
    seed: 0x4d4d0000 + caseIndex * 7919,
  });
}

// Stress the source UI's held-input accumulator and capped stepping on actual
// generated boards, not only on empty hand-built physics trays. Every rung is
// represented once; the deterministic schedule mixes values immediately
// around the 60Hz nudge and 50ms frame-clamp boundaries with ordinary frame
// rates, tiny/zero updates, changing/opposing held keys, and release.
const clockPartitionDts = [
  1 / 60 - 1e-12, 1 / 60, 1 / 60 + 1e-12,
  1 / 120 - 1e-12, 1 / 120, 1 / 120 + 1e-12,
  0.05 - 1e-12, 0.05, 0.05 + 1e-12,
  5e-10, 0, 1 / 144, 1 / 30, 0.0073,
];
const clockHeldSets = [
  [], ["E"], ["W"], ["N"], ["S"], ["E", "N"], ["W", "S"],
  ["E", "W"], ["N", "S"], ["E", "S"], ["W", "N"],
];
for (let caseIndex = 0; caseIndex < 16; caseIndex++) {
  const rung = caseIndex + 1;
  const seed = 0x434c0000 + caseIndex * 7919;
  const length = Number(exports.nw_marble_board_write(
    BigInt(boardPointer), 65536n, BigInt(rung), BigInt(seed)));
  assert.ok(length > 0,
    `WASM failed to produce clock-partition board for rung ${rung}, seed ${seed}`);
  const board = decodeMarbleBoard(
    new Uint8Array(instance.exports.memory.buffer, boardPointer, length));
  const random = seededRandom(seed ^ 0x74696d65);
  const schedule = Array.from({ length: 72 }, (_, frameIndex) => ({
    advance: true,
    dt: clockPartitionDts[(caseIndex + frameIndex) % 9 === 0
      ? (caseIndex + frameIndex) % clockPartitionDts.length
      : Math.floor(random() * clockPartitionDts.length)],
    held: frameIndex === 71 ? [] :
      clockHeldSets[Math.floor(random() * clockHeldSets.length)],
  }));
  cases.push({
    name: `rung-${rung} generated-board clock partition stress (seed ${seed})`,
    board,
    initial: [],
    frames: schedule,
    coverage: "clock-partition-stress",
    seed,
  });
}

// The generated-board and clock-partition matrices begin from dealt start
// poses. Sample the other side of MM-003 explicitly: seeded valid quaternions,
// contact-height positions, free translational/spin velocities, and occasional
// initially intersecting marbles on actual generated trays. Compare every
// state to the original oracle; this is randomized regression coverage, not an
// assumption that two different time partitions should produce the same path.
const initialStateDts = [
  5e-10, 0.0005, 0.004, 1 / 120, 1 / 60, 1 / 30,
  0.05 - 1e-12, 0.05, 0.05 + 1e-12,
];
for (let caseIndex = 0; caseIndex < 16; caseIndex++) {
  const rung = caseIndex + 1;
  const seed = 0x49530000 + caseIndex * 7919;
  const random = seededRandom(seed ^ 0x61726269);
  const length = Number(exports.nw_marble_board_write(
    BigInt(boardPointer), 65536n, BigInt(rung), BigInt(seed)));
  assert.ok(length > 0,
    `WASM failed to produce arbitrary-state board for rung ${rung}, seed ${seed}`);
  const board = decodeMarbleBoard(
    new Uint8Array(instance.exports.memory.buffer, boardPointer, length));
  const initial = board.starts.map((start) => {
    let qw = random() - 0.5;
    let qx = random() - 0.5;
    let qy = random() - 0.5;
    let qz = random() - 0.5;
    const quaternionLength = Math.hypot(qw, qx, qy, qz);
    qw /= quaternionLength;
    qx /= quaternionLength;
    qy /= quaternionLength;
    qz /= quaternionLength;
    return {
      x: Math.max(MARBLE.RADIUS, Math.min(board.width - MARBLE.RADIUS,
        start.x + (random() - 0.5) * 0.028)),
      y: Math.max(MARBLE.RADIUS, Math.min(board.depth - MARBLE.RADIUS,
        start.y + (random() - 0.5) * 0.028)),
      z: MARBLE.RADIUS + (random() - 0.5) * 0.004,
      vx: (random() - 0.5) * 2.4,
      vy: (random() - 0.5) * 2.4,
      vz: (random() - 0.5) * 0.3,
      qw, qx, qy, qz,
      wx: (random() - 0.5) * 180,
      wy: (random() - 0.5) * 180,
      wz: (random() - 0.5) * 30,
      state: "rolling",
    };
  });
  const actionKeys = ["N", "S", "E", "W"];
  const framesForState = Array.from({ length: 72 }, (_, frameIndex) => {
    const dt = initialStateDts[Math.floor(random() * initialStateDts.length)];
    if (frameIndex % 3 === 0) {
      const actions = [];
      if (random() < 0.7) {
        actions.push(actionKeys[Math.floor(random() * actionKeys.length)]);
      }
      if (random() < 0.15) actions.push("level");
      return { dt, actions };
    }
    const held = frameIndex === 71 ? [] :
      clockHeldSets[Math.floor(random() * clockHeldSets.length)];
    return { advance: true, dt, held };
  });
  framesForState[71] = { advance: true, dt: framesForState[71].dt, held: [] };
  cases.push({
    name: `rung-${rung} generated-board arbitrary initial-state stress (seed ${seed})`,
    board,
    initial,
    frames: framesForState,
    coverage: "initial-state-stress",
    seed,
  });
}

// Exercise real generated hole geometry directly. The existing hand-authored
// pit cases prove the state machine in isolation, while generated-board traces
// may never enter a particular pit during their short fixed input sequence.
// Find a deterministic clear approach ray on the same five generated-board
// seeds used by the board/MJCF matrix, at every rung, and require the active
// marble to enter that exact hole and reach its expected terminal state. Rung
// 1 has only its home cup, so it validates cup capture; all higher rungs
// target an ordinary pit.
function generatedHoleApproach(board) {
  const targets = board.holes
    .map((hole, index) => ({ hole, index }))
    .filter(({ hole }) => !hole.home);
  if (targets.length === 0) {
    targets.push(...board.holes.map((hole, index) => ({ hole, index }))
      .filter(({ hole }) => hole.home));
  }
  for (const { hole, index: holeIndex } of targets) {
    const startRadius = hole.radius + MARBLE.RADIUS + 0.01;
    for (let directionIndex = 0; directionIndex < 64; directionIndex++) {
      const angle = directionIndex * Math.PI * 2 / 64;
      const outwardX = Math.cos(angle);
      const outwardY = Math.sin(angle);
      const start = {
        x: hole.x + outwardX * startRadius,
        y: hole.y + outwardY * startRadius,
      };
      if (start.x < MARBLE.RADIUS || start.y < MARBLE.RADIUS ||
          start.x > board.width - MARBLE.RADIUS ||
          start.y > board.depth - MARBLE.RADIUS) continue;

      let clear = true;
      for (let sample = 0; sample <= 48 && clear; sample++) {
        const amount = sample / 48;
        const x = start.x + (hole.x - start.x) * amount;
        const y = start.y + (hole.y - start.y) * amount;
        if (board.walls.some((wall) =>
          x >= wall.x0 - MARBLE.RADIUS && x <= wall.x1 + MARBLE.RADIUS &&
          y >= wall.y0 - MARBLE.RADIUS && y <= wall.y1 + MARBLE.RADIUS)) {
          clear = false;
          break;
        }
        if (board.holes.some((other) => other !== hole &&
            Math.hypot(x - other.x, y - other.y) <
              other.radius + MARBLE.RADIUS)) {
          clear = false;
          break;
        }
        if (board.starts.slice(1).some((otherStart) =>
          Math.hypot(x - otherStart.x, y - otherStart.y) <
            2.5 * MARBLE.RADIUS)) {
          clear = false;
        }
      }
      if (clear) {
        return {
          hole,
          holeIndex,
          start,
          direction: { x: -outwardX, y: -outwardY },
        };
      }
    }
  }
  return null;
}

const generatedHoleSeeds = [0, 1, 17, 314159, 1073741823];
for (const seed of generatedHoleSeeds) {
  for (let rung = 1; rung <= 16; rung++) {
    const length = Number(exports.nw_marble_board_write(
      BigInt(boardPointer), 65536n, BigInt(rung), BigInt(seed)));
    assert.ok(length > 0,
      `WASM failed to produce generated-hole board for rung ${rung}, seed ${seed}`);
    const board = decodeMarbleBoard(
      new Uint8Array(instance.exports.memory.buffer, boardPointer, length));
    const approach = generatedHoleApproach(board);
    assert.ok(approach,
      `rung ${rung} seed ${seed} has no unobstructed generated-hole approach`);
    const speed = 0.25;
    const vx = approach.direction.x * speed;
    const vy = approach.direction.y * speed;
    const initial = board.starts.map((_, marbleIndex) => marbleIndex === 0 ? ({
      x: approach.start.x,
      y: approach.start.y,
      z: MARBLE.RADIUS,
      vx,
      vy,
      wx: -vy / MARBLE.RADIUS,
      wy: vx / MARBLE.RADIUS,
      state: "rolling",
    }) : ({}));
    cases.push({
      name: `rung-${rung} generated ${approach.hole.home ? "home-cup" : "pit"} approach (seed ${seed})`,
      board,
      initial,
      frames: frames(180, 1 / 60),
      coverage: "generated-hole-approach",
      targetHoleIndex: approach.holeIndex,
      targetOutcome: approach.hole.home ? "home" : "lost",
      seed,
    });
  }
}

// The board/MJCF oracle certifies five seeds per rung. Exercise the same
// generated boards through the full source/native-vs-browser/WASM trajectory
// comparison as well: decoding and compiling a board can agree while a
// particular generated wall order, hole placement, or multi-marble start
// still exposes a runtime mismatch. Keep the action trace deterministic and
// identical for every board; it is deliberately not a hand-authored solution
// for one seed, but it is long enough to reach the first walls/holes on more
// than just the opening frame of a generated tray.
const generatedBoardSeeds = [0, 1, 17, 314159, 1073741823];
for (const seed of generatedBoardSeeds) {
  for (let rung = 1; rung <= 16; rung++) {
    const length = Number(exports.nw_marble_board_write(
      BigInt(boardPointer), 65536n, BigInt(rung), BigInt(seed)));
    assert.ok(length > 0,
      `WASM failed to produce trajectory board for rung ${rung}, seed ${seed}`);
    const board = decodeMarbleBoard(
      new Uint8Array(instance.exports.memory.buffer, boardPointer, length));
    cases.push({
      name: `rung-${rung} generated-board trajectory (seed ${seed})`,
      board,
      initial: [],
      frames: frames(120, 1 / 60, {
        0: Array(10).fill("E"),
        30: Array(12).fill("W"),
        70: Array(8).fill("N"),
        90: Array(10).fill("S"),
        110: ["level"],
      }),
      coverage: "trace",
      seed,
    });
  }
}

const pythonProgram = String.raw`
import json, os
from neural_workshop import marblemaze as mm

with open(os.environ["NW_MARBLE_ORACLE_INPUT"], encoding="utf-8") as input_file:
    payload = json.load(input_file)
directions = {"N": mm.TILT_NORTH, "S": mm.TILT_SOUTH,
              "E": mm.TILT_EAST, "W": mm.TILT_WEST}

def make_tray(spec):
    source = mm.deal(spec["board"]["rung"], seed=spec["seed"])
    board = spec["board"]
    return source._replace(
        rung=board["rung"], cols=board["cols"], rows=board["rows"],
        width=board["width"], depth=board["depth"], cell=board["cell"],
        thickness=board["thickness"], height=board["height"],
        walls=tuple(mm.Wall(w["x0"], w["y0"], w["x1"], w["y1"])
                    for w in board["walls"]),
        holes=tuple(mm.Hole(h["x"], h["y"], h["radius"], h["home"])
                    for h in board["holes"]),
        starts=tuple((p["x"], p["y"]) for p in board["starts"]),
        home=(board["home"]["x"], board["home"]["y"], board["home"]["radius"]),
        seconds=board["seconds"], route=board["route"])

def snapshot(sim, nudge_due):
    marbles = []
    for marble in sim.marbles:
        over = None
        if marble.over is not None:
            over = next(i for i, hole in enumerate(sim.tray.holes)
                        if hole == marble.over)
        marbles.append({
            "values": [marble.x, marble.y, marble.z, marble.vx, marble.vy,
                       marble.vz, marble.qw, marble.qx, marble.qy, marble.qz,
                       marble.wx, marble.wy, marble.wz],
            "state": marble.state, "over": over,
        })
    return {
        "marbles": marbles, "roll": sim.roll, "pitch": sim.pitch,
        "elapsed": sim.elapsed, "struck": sim.struck_this_step,
        "cupped": sim.cupped_this_step, "lostThisStep": sim.lost_this_step,
        "home": sim.home, "lost": sim.lost, "nudgeDue": nudge_due,
    }

results = []
for spec in payload:
    sim = mm.Simulation(make_tray(spec))
    nudge_due = 0.0
    for index, override in enumerate(spec["initial"]):
        marble = sim.marbles[index]
        for key, value in override.items():
            if key == "over":
                marble.over = sim.tray.holes[value]
            else:
                setattr(marble, key, value)
    trace = []
    for frame in spec["frames"]:
        if frame.get("advance"):
            piece = min(frame["dt"], 0.05)
            held = frame.get("held", [])
            if held:
                nudge_due += piece
                while nudge_due >= 1 / 60.:
                    nudge_due -= 1 / 60.
                    for key in held: sim.tilt(directions[key])
            else:
                nudge_due = 0.0
            left = piece
            while left > 0.0:
                bite = min(left, 1 / 60.)
                sim.step(bite)
                left -= bite
        else:
            for action in frame.get("actions", []):
                if action == "level": sim.level()
                else: sim.tilt(directions[action])
            sim.step(frame["dt"])
        trace.append(snapshot(sim, nudge_due))
    results.append(trace)
print(json.dumps(results, allow_nan=False, separators=(",", ":")))
`;

// Keep the large oracle payload out of spawnSync's stdin pipe. On macOS, the
// synchronous Node runner can retain that pipe while the child is waiting for
// EOF, leaving json.load(sys.stdin) blocked indefinitely. A private temporary
// input file gives the oracle a deterministic EOF and lets the test enforce a
// bounded failure instead of hanging the whole artifact gate.
const oracleInputDirectory = fs.mkdtempSync(
  path.join(os.tmpdir(), "nw-marble-trajectory-"));
const oracleInputPath = path.join(oracleInputDirectory, "cases.json");
fs.writeFileSync(oracleInputPath, JSON.stringify(cases.map((testCase) => ({
  ...testCase, seed: testCase.seed ?? 17,
}))), "utf8");

let oracle;
try {
  oracle = spawnSync(python, ["-c", pythonProgram], {
    cwd: referenceRoot,
    env: { ...process.env, NW_MARBLE_ORACLE_INPUT: oracleInputPath },
    encoding: "utf8",
    maxBuffer: 32 * 1024 * 1024,
    timeout: 120000,
  });
} finally {
  fs.rmSync(oracleInputDirectory, { recursive: true, force: true });
}
if (oracle.error || oracle.status !== 0) {
  const reason = oracle.error?.message ?? `exit status ${oracle.status}`;
  throw new Error(`Python Marble trajectory oracle failed (${reason}):\n${oracle.stderr ?? ""}`);
}
const expected = JSON.parse(oracle.stdout);
const alternateMuJoCoModule = process.env.NW_MUJOCO_WASM_MODULE;
const moduleLoader = alternateMuJoCoModule
  ? async () => (await import(pathToFileURL(
      path.resolve(alternateMuJoCoModule)).href)).default()
  : undefined;
const Game = await loadMarbleMazeMuJoCo(moduleLoader);
const tolerance = {
  position: 1e-8,
  linearVelocity: 1e-8,
  quaternion: 1e-8,
  // Native and WASM MuJoCo can take slightly different last-bit paths after
  // a long multi-marble contact chain. Keep the controlled-contact gate at
  // its measured tight scale while allowing the generated-board trace to
  // characterize that platform-level drift separately below.
  generatedTracePosition: 1e-8,
  generatedTraceLinearVelocity: 1e-7,
  generatedTraceQuaternion: 2e-8,
  angularVelocity: 1e-7,
  generatedTraceAngularVelocity: 2e-7,
  scalar: 1e-10,
  struck: 1e-8,
};
const fields = ["x", "y", "z", "vx", "vy", "vz", "qw", "qx", "qy", "qz", "wx", "wy", "wz"];
const maxima = Object.fromEntries(fields.map((field) => [field, 0]));
maxima.struck = 0;
let comparisons = 0;

function fieldTolerance(field, coverage = null) {
  if (["x", "y", "z"].includes(field)) {
    return coverage === "trace" ? tolerance.generatedTracePosition : tolerance.position;
  }
  if (["vx", "vy", "vz"].includes(field)) {
    return coverage === "trace" ? tolerance.generatedTraceLinearVelocity : tolerance.linearVelocity;
  }
  if (["qw", "qx", "qy", "qz"].includes(field)) {
    return coverage === "trace" ? tolerance.generatedTraceQuaternion : tolerance.quaternion;
  }
  if (coverage === "trace") return tolerance.generatedTraceAngularVelocity;
  return tolerance.angularVelocity;
}

for (let caseIndex = 0; caseIndex < cases.length; caseIndex++) {
  const testCase = cases[caseIndex];
  const game = new Game(testCase.board);
  for (let index = 0; index < testCase.initial.length; index++) {
    for (const [key, value] of Object.entries(testCase.initial[index])) {
      game.marbles[index][key] = key === "over" ? testCase.board.holes[value] : value;
    }
  }
  const observed = {
    maxRoll: 0, maxPitch: 0, maxSpeed: 0, maxStruck: 0,
    rollTrace: [], capSpinError: Infinity, cupped: 0, lost: 0, states: new Set(),
    holesSeen: new Set(),
  };
  try {
    for (let frameIndex = 0; frameIndex < testCase.frames.length; frameIndex++) {
      const frame = testCase.frames[frameIndex];
      if (frame.advance) {
        game.advance(frame.dt, new Set(frame.held));
      } else {
        for (const action of frame.actions) {
          if (action === "level") game.level();
          else game.tilt(action);
        }
        game.step(frame.dt);
      }
      observed.maxRoll = Math.max(observed.maxRoll, Math.abs(game.roll));
      observed.rollTrace.push(game.roll);
      observed.maxPitch = Math.max(observed.maxPitch, Math.abs(game.pitch));
      observed.maxSpeed = Math.max(observed.maxSpeed, game.speed);
      observed.maxStruck = Math.max(observed.maxStruck, game.struckThisStep);
      if (testCase.coverage === "speed-cap" &&
          Math.abs(game.speed - MARBLE.SPEED_CAP) < 1e-6) {
        observed.capSpinError = Math.min(observed.capSpinError,
          Math.abs(Math.hypot(game.marbles[0].wx, game.marbles[0].wy) -
            MARBLE.SPEED_CAP / MARBLE.RADIUS));
      }
      observed.cupped += game.cuppedThisStep;
      observed.lost += game.lostThisStep;
      for (const marble of game.marbles) {
        observed.states.add(marble.state);
        if (marble.over !== null) {
          observed.holesSeen.add(testCase.board.holes.indexOf(marble.over));
        }
      }
      const got = {
        marbles: game.marbles.map((marble) => ({
          values: fields.map((field) => marble[field]),
          state: marble.state,
          over: marble.over === null ? null : testCase.board.holes.indexOf(marble.over),
        })),
        roll: game.roll,
        pitch: game.pitch,
        elapsed: game.elapsed,
        struck: game.struckThisStep,
        cupped: game.cuppedThisStep,
        lostThisStep: game.lostThisStep,
        home: game.home,
        lost: game.lost,
        nudgeDue: game.nudgeDue,
      };
      const want = expected[caseIndex][frameIndex];
      assert.equal(got.marbles.length, want.marbles.length, testCase.name);
      for (let marbleIndex = 0; marbleIndex < got.marbles.length; marbleIndex++) {
        const actualMarble = got.marbles[marbleIndex];
        const expectedMarble = want.marbles[marbleIndex];
        assert.equal(actualMarble.state, expectedMarble.state,
          `${testCase.name}, frame ${frameIndex}, marble ${marbleIndex}: state`);
        assert.equal(actualMarble.over, expectedMarble.over,
          `${testCase.name}, frame ${frameIndex}, marble ${marbleIndex}: hole identity`);
        for (let valueIndex = 0; valueIndex < fields.length; valueIndex++) {
          const field = fields[valueIndex];
          const difference = Math.abs(actualMarble.values[valueIndex] - expectedMarble.values[valueIndex]);
          maxima[field] = Math.max(maxima[field], difference);
          assert.ok(difference <= fieldTolerance(field, testCase.coverage),
            `${testCase.name}, frame ${frameIndex}, marble ${marbleIndex}, ${field}: ` +
            `${actualMarble.values[valueIndex]} vs ${expectedMarble.values[valueIndex]} ` +
            `(absolute error ${difference}, tolerance ${fieldTolerance(field, testCase.coverage)})`);
        }
      }
      for (const key of ["cupped", "lostThisStep", "home", "lost"]) {
        assert.equal(got[key], want[key], `${testCase.name}, frame ${frameIndex}: ${key}`);
      }
      for (const key of ["roll", "pitch", "elapsed", "nudgeDue"]) {
        assert.ok(Math.abs(got[key] - want[key]) <= tolerance.scalar,
          `${testCase.name}, frame ${frameIndex}: ${key} differs`);
      }
      const struckDifference = Math.abs(got.struck - want.struck);
      maxima.struck = Math.max(maxima.struck, struckDifference);
      assert.ok(struckDifference <= tolerance.struck,
        `${testCase.name}, frame ${frameIndex}: impact signal differs by ${struckDifference}`);
      comparisons++;
    }
    switch (testCase.coverage) {
      case "tilt-saturation":
        assert.ok(observed.maxRoll >= MARBLE.MAX_TILT - 1e-12 &&
          observed.maxPitch >= MARBLE.MAX_TILT - 1e-12,
        `${testCase.name} did not reach both tilt stops`);
        break;
      case "rest":
        assert.ok(game.speed < 1e-8, `${testCase.name} did not settle below rest threshold`);
        break;
      case "speed-cap":
        assert.ok(observed.maxSpeed >= MARBLE.SPEED_CAP - 1e-6,
          `${testCase.name} did not exercise the speed cap (max=${observed.maxSpeed})`);
        assert.ok(observed.capSpinError < 1e-4,
          `${testCase.name} did not scale rolling angular velocity with the cap`);
        break;
      case "wall-impact":
      case "ball-impact":
        assert.ok(observed.maxStruck > 0.02, `${testCase.name} did not produce an impact`);
        break;
      case "multi-impact":
        assert.ok(observed.maxStruck > 0.02,
          `${testCase.name} did not produce a measurable multi-contact impact`);
        assert.ok(observed.states.has("rolling"),
          `${testCase.name} did not retain a live rolling state after contact`);
        break;
      case "corner-permutation":
        assert.ok(observed.maxStruck > 0.02,
          `${testCase.name} did not produce a measurable corner impact`);
        assert.ok(observed.states.has("rolling"),
          `${testCase.name} did not retain a live rolling state after contact`);
        break;
      case "multi-corner-impact":
        assert.ok(observed.maxStruck > 0.02,
          `${testCase.name} did not produce a measurable multi-marble corner impact`);
        assert.ok(observed.states.has("rolling"),
          `${testCase.name} did not retain a live rolling state after contact`);
        break;
      case "arbitrary-contact":
        assert.ok(Number.isFinite(game.elapsed),
          `${testCase.name} produced a non-finite elapsed time`);
        assert.ok([...observed.states].every((state) =>
          ["rolling", "falling", "home", "lost"].includes(state)),
        `${testCase.name} produced an unknown marble state`);
        break;
      case "falling-ball":
        assert.ok(observed.states.has("falling") || observed.states.has("lost"),
          `${testCase.name} did not enter a terminal fall path`);
        break;
      case "lost":
        assert.equal(game.lost, 1, `${testCase.name} did not swallow the marble`);
        assert.equal(game.marbles[0].over, testCase.board.holes[0],
          `${testCase.name} did not retain its last hole after swallowing`);
        break;
      case "cleared-pit":
        assert.ok(observed.states.has("falling"), `${testCase.name} never fell into the pit`);
        assert.equal(game.marbles[0].state, "rolling", `${testCase.name} did not clear the far lip`);
        assert.equal(game.marbles[0].over, null, `${testCase.name} retained a cleared hole`);
        break;
      case "home":
        assert.equal(game.home, 1, `${testCase.name} did not reach home`);
        assert.equal(observed.cupped, 1, `${testCase.name} did not emit exactly one cup event`);
        break;
      case "trace":
        assert.ok(observed.maxSpeed > 0, `${testCase.name} did not move any marble`);
        break;
      case "advance":
        assert.ok(game.elapsed > 0, `${testCase.name} did not advance elapsed time`);
        assert.equal(game.nudgeDue, 0, `${testCase.name} did not clear the released-key remainder`);
        break;
      case "advance-boundary":
        assert.ok(game.elapsed > 0, `${testCase.name} did not advance elapsed time`);
        assert.notEqual(observed.rollTrace[1], 0,
          `${testCase.name} did not apply the nudge at the exact 60Hz boundary`);
        assert.notEqual(game.pitch, 0,
          `${testCase.name} did not apply the held second-axis direction`);
        assert.equal(game.nudgeDue, 0,
          `${testCase.name} did not clear the accumulator on key release`);
        assert.ok(observed.maxStruck > 0.02,
          `${testCase.name} did not exercise the wall contact during capped frames`);
        break;
      case "clock-partition-stress":
        assert.ok(game.elapsed > 0, `${testCase.name} did not advance elapsed time`);
        assert.equal(game.nudgeDue, 0,
          `${testCase.name} did not reset the accumulator on the final release`);
        assert.ok([...observed.states].every((state) =>
          ["rolling", "falling", "home", "lost"].includes(state)),
        `${testCase.name} produced an unknown marble state`);
        break;
      case "initial-state-stress":
        assert.ok(game.elapsed > 0, `${testCase.name} did not advance elapsed time`);
        assert.equal(game.nudgeDue, 0,
          `${testCase.name} did not reset the accumulator on the final release`);
        assert.ok([...observed.states].every((state) =>
          ["rolling", "falling", "home", "lost"].includes(state)),
        `${testCase.name} produced an unknown marble state`);
        break;
      case "generated-hole-approach":
        assert.ok(observed.holesSeen.has(testCase.targetHoleIndex),
          `${testCase.name} did not enter its intended generated hole`);
        assert.equal(game.marbles[0].state, testCase.targetOutcome,
          `${testCase.name} did not reach ${testCase.targetOutcome}`);
        assert.equal(game.home, testCase.targetOutcome === "home" ? 1 : 0,
          `${testCase.name} has the wrong home count`);
        assert.equal(game.lost, testCase.targetOutcome === "lost" ? 1 : 0,
          `${testCase.name} has the wrong lost count`);
        break;
      case "opposed-held-input":
        assert.ok(game.elapsed > 0, `${testCase.name} did not advance elapsed time`);
        assert.equal(game.roll, 0, `${testCase.name} failed to cancel opposing roll input`);
        assert.equal(game.pitch, 0, `${testCase.name} changed the unpressed tilt axis`);
        assert.equal(game.nudgeDue, 0, `${testCase.name} left a held-key accumulator remainder`);
        break;
      case "held-key-rollover": {
        const afterOpposed = observed.rollTrace[11];
        const afterEast = observed.rollTrace[31];
        const afterRelease = observed.rollTrace[32];
        assert.equal(afterOpposed, 0,
          `${testCase.name} did not cancel both directions before release`);
        assert.ok(Math.abs(afterEast) > 0,
          `${testCase.name} did not keep tilting after releasing only W`);
        assert.equal(afterRelease, afterEast,
          `${testCase.name} changed tilt after the last held key was released`);
        assert.ok(game.roll * afterEast < 0,
          `${testCase.name} did not reverse tilt after the remaining direction changed`);
        assert.equal(game.nudgeDue, 0,
          `${testCase.name} retained a stale held-key accumulator remainder`);
        break;
      }
      case "falling-wall":
        assert.ok(observed.states.has("falling"), `${testCase.name} did not enter a pit`);
        assert.ok(observed.maxStruck > 0.02, `${testCase.name} did not register the explicit wall contact`);
        break;
      case "falling-multi-impact":
        assert.ok(observed.states.has("falling") || observed.states.has("lost"),
          `${testCase.name} did not enter a terminal fall path`);
        assert.ok(observed.maxStruck > 0.02,
          `${testCase.name} did not register the explicit simultaneous contacts`);
        break;
      case "terminal-park":
        assert.equal(game.home, 1, `${testCase.name} changed terminal marble count`);
        assert.equal(game.marbles[0].x, -4, `${testCase.name} mutated the parked marble state`);
        break;
      case "terminal-lost-park":
        assert.equal(game.lost, 1, `${testCase.name} changed terminal marble count`);
        assert.equal(game.marbles[0].state, "lost", `${testCase.name} changed parked state`);
        assert.equal(game.marbles[0].x, -6, `${testCase.name} mutated the parked marble state`);
        break;
      default:
        assert.fail(`missing coverage assertion for ${testCase.name}`);
    }
  } finally {
    game.disposeEngine();
  }
}

console.log(`PASS: Python/native vs browser/WASM Marble trajectories (${cases.length} scenarios, ` +
  `${comparisons} per-frame states); maximum absolute errors ` +
  `${JSON.stringify(maxima)}; tolerances ${JSON.stringify(tolerance)}`);
