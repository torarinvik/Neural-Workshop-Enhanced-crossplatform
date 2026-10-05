import assert from "node:assert/strict";
import {
  MarbleMazeGame, MARBLE, marbleBoardBudgetSeconds, marbleFeedbackKind,
  marbleSourceRound,
} from "../shells/web/marble-maze.js";

function board(overrides = {}) {
  return {
    built: true, rung: 1, cols: 1, rows: 1, width: 1, depth: 1,
    cell: 1, thickness: 0.01, height: 0.01, seconds: 45, route: 1,
    home: { x: 0.8, y: 0.5, radius: 0.08 },
    walls: [], holes: [], starts: [{ x: 0.1, y: 0.5 }], ...overrides,
  };
}

assert.equal(marbleBoardBudgetSeconds(board(), 0), 45);
assert.equal(marbleBoardBudgetSeconds(board(), 15), 15);
assert.equal(marbleBoardBudgetSeconds(board(), 120), 120);

// The native UI uses Python's ties-to-even round() when it prints tilt. JS
// Math.round() would turn the negative half tie -1.5 into -1 instead of -2.
assert.equal(marbleSourceRound(1.5), 2);
assert.equal(marbleSourceRound(2.5), 2);
assert.equal(marbleSourceRound(-1.5), -2);
assert.equal(marbleSourceRound(-2.5), -2);
assert.equal(marbleSourceRound(1.5000000000000004), 2);

// MarbleMaze.update() checks physical settlement before the deadline. A
// marble that falls into a hole on the boundary frame is therefore a physical
// loss, not a timeout; only an unsettled tray at the deadline is timed out.
{
  const game = new MarbleMazeGame(board());
  game.marbles[0].state = "lost";
  game.elapsed = game.board.seconds;
  assert.equal(marbleFeedbackKind(game, 0, game.board.seconds), "lost-single");
  assert.equal(marbleFeedbackKind(game, 1, game.board.seconds), "won");

  const timeout = new MarbleMazeGame(board());
  timeout.elapsed = timeout.board.seconds;
  assert.equal(marbleFeedbackKind(timeout, 0, timeout.board.seconds), "timeout");
}

// The native Simulation scales rolling spin together with a speed-capped
// marble. The fallback must not leave a stale wy that the next floor contact
// can feed back into motion.
{
  const game = new MarbleMazeGame(board());
  game.marbles[0].vx = 3;
  game.marbles[0].wy = 400;
  game.step(1 / 60);
  assert.ok(game.speed <= MARBLE.SPEED_CAP + 1e-9);
  assert.ok(game.marbles[0].wy < 380,
    "speed cap must scale the fallback's rolling spin");
}

// Direct stepping is a forward-time API in both browser adapters. Zero and
// negative/non-finite values must not rewind elapsed time, run a backwards
// physics solve, or create an unbounded loop from malformed replay data.
{
  const game = new MarbleMazeGame(board());
  game.step(1 / 60);
  const elapsed = game.elapsed;
  const x = game.marbles[0].x;
  game.step(0);
  game.step(-1);
  game.step(Number.POSITIVE_INFINITY);
  game.step(Number.NaN);
  assert.equal(game.elapsed, elapsed);
  assert.equal(game.marbles[0].x, x);
}

// Arrow names must have the same compass signs as the original
// Simulation.tilt(): north increases y and east increases x.
{
  const game = new MarbleMazeGame(board());
  for (let index = 0; index < 30; index++) game.tilt("N");
  game.step(0.5);
  assert.equal(game.pitch, -MARBLE.MAX_TILT);
  assert.ok(game.marbles[0].y > 0.5);
}

// Leveling a tilted tray must restore the reference's rest clamp.
{
  const game = new MarbleMazeGame(board());
  for (let index = 0; index < 30; index++) game.tilt("E");
  game.step(0.5);
  assert.ok(game.marbles[0].vx > 0.05);
  game.level();
  // The source clamp uses REST_SPEED, not the fallback's former 1.5x band;
  // with the exact source threshold this trajectory crosses the band just
  // after five seconds. Use the UI's 60 Hz advance partition rather than
  // asking the direct four-substep API to integrate a multi-second frame.
  for (let index = 0; index < 306; index++) game.advance(1 / 60);
  assert.ok(Math.hypot(game.marbles[0].vx, game.marbles[0].vy) < MARBLE.REST_SPEED);
}

// The source UI constructs a fresh Simulation on restart, resetting elapsed;
// its UI-owned fractional held-key accumulator survives until an idle update.
{
  const game = new MarbleMazeGame(board());
  game.tilt("E");
  game.step(0.75);
  assert.ok(game.elapsed > 0);
  game.nudgeDue = 1 / 120;
  game.restart();
  assert.equal(game.elapsed, 0);
  assert.equal(game.nudgeDue, 1 / 120);
  assert.equal(game.roll, 0);
  assert.equal(game.pitch, 0);
  assert.equal(game.marbles[0].x, game.board.starts[0].x);
  assert.equal(game.marbles[0].y, game.board.starts[0].y);
  game.advance(1 / 120, new Set());
  assert.equal(game.nudgeDue, 0);
}

// The native UI clears a released held-key accumulator even on an idle
// update. A zero-delta blur/release callback must not carry a stale fraction
// into the next non-zero frame.
{
  const game = new MarbleMazeGame(board());
  game.nudgeDue = 1 / 120;
  game.advance(0, new Set());
  assert.equal(game.nudgeDue, 0);
}

// Positive frame-time remainders below the old 1 ns cutoff still advance the
// source clock and simulation; the final bite is the remainder itself.
{
  const game = new MarbleMazeGame(board());
  const dt = 5e-10;
  game.advance(dt);
  assert.equal(game.elapsed, dt);
}

// Simulation.step itself is exactly four equal substeps. The UI-level 50 ms
// clamp and 60 Hz remainder partition belong to advance(), not to this
// direct deterministic API. Keep the fallback's public contract identical to
// the native source even when a replay supplies a long step.
{
  const game = new MarbleMazeGame(board());
  const bites = [];
  game.substep = (dt) => bites.push(dt);
  game.step(0.05);
  assert.deepEqual(bites, [0.0125, 0.0125, 0.0125, 0.0125]);
  assert.equal(game.elapsed, 0.05);
}

// Held controls accumulate wall-clock time: a half-tick does not nudge yet,
// the second half-tick does, and releasing the key discards leftover time.
{
  const game = new MarbleMazeGame(board());
  game.advance(1 / 120, new Set(["E"]));
  assert.equal(game.roll, 0);
  game.advance(1 / 120, new Set(["E"]));
  assert.equal(game.roll, MARBLE.TILT_STEP);
  game.advance(1 / 240, new Set(["E"]));
  game.advance(1 / 240, new Set());
  assert.equal(game.nudgeDue, 0);
}

// The native UI finishes the complete capped frame before checking whether
// the simulation settled. Its positive-remainder loop also executes the tiny
// floating-point remainder after the three nominal 60 Hz bites.
{
  const game = new MarbleMazeGame(board());
  let bites = 0;
  const step = game.step.bind(game);
  game.step = (dt) => {
    step(dt);
    bites++;
    if (bites === 1) game.marbles[0].state = "home";
  };
  game.advance(0.05);
  assert.equal(bites, 4);
  assert.ok(Math.abs(game.elapsed - 0.05) < 1e-9);
}

// A clean roll spends two sevenths of the contact impulse on angular
// velocity, and a skid converges back without ringing.
{
  const game = new MarbleMazeGame(board());
  const marble = game.marbles[0];
  marble.vx = 0.6;
  assert.ok(game.slipping(marble) > 0.59);
  let settledAt = 60;
  for (let index = 0; index < 60; index++) {
    game.step(1 / 60);
    if (game.slipping(marble) < 0.005) {
      settledAt = index;
      break;
    }
  }
  assert.ok(settledAt < 10);
  assert.ok(marble.vx < 0.6 * MARBLE.ROLL_FACTOR);
  assert.ok(marble.vx > 0.6 * MARBLE.ROLL_FACTOR - 0.03);
}

// The orientation is integrated from the independent spin state and remains
// a proper rotation. Travel in +x rolls around +y, as in the native sphere.
{
  const game = new MarbleMazeGame(board());
  const marble = game.marbles[0];
  marble.vx = 0.30;
  game.rollWithTravel(marble);
  for (let index = 0; index < 6; index++) game.step(1 / 60);
  assert.ok(marble.qy > 0.05);
  assert.ok(Math.abs(marble.qx) < 1e-9);
  assert.ok(Math.abs(marble.qz) < 1e-9);
  assert.ok(Math.abs(Math.hypot(marble.qw, marble.qx, marble.qy, marble.qz) - 1) < 1e-12);
}

// A wall is solid to the marble and never permits a frame-end overlap.
{
  const game = new MarbleMazeGame(board({
    walls: [{ x0: 0.5, y0: 0, x1: 0.51, y1: 1 }],
  }));
  for (let index = 0; index < 30; index++) game.tilt("E");
  for (let index = 0; index < 480; index++) game.step(1 / 60);
  const marble = game.marbles[0];
  assert.ok(marble.x <= 0.5 - MARBLE.RADIUS + 1e-9);
  assert.ok(marble.vx <= 0.01);
}

// A square wall hit leaves the old roll spinning, while a graze creates a
// short-lived top spin through the low-friction wall contact.
{
  const wall = { x0: 0.30, y0: 0.02, x1: 0.31, y1: 0.40 };
  const game = new MarbleMazeGame(board({
    walls: [wall], starts: [{ x: 0.20, y: 0.20 }],
  }));
  const marble = game.marbles[0];
  marble.vx = 0.5;
  game.rollWithTravel(marble);
  let bounced = false;
  for (let index = 0; index < 120; index++) {
    game.step(1 / 60);
    if (marble.vx < 0) { bounced = true; break; }
  }
  assert.equal(bounced, true);
  assert.ok(game.slipping(marble) > 0.20);

  const graze = new MarbleMazeGame(board({
    walls: [wall], starts: [{ x: 0.20, y: 0.20 }],
  }));
  const grazed = graze.marbles[0];
  grazed.vx = 0.25;
  grazed.vy = 0.43;
  graze.rollWithTravel(grazed);
  let peakSpin = 0;
  for (let index = 0; index < 40; index++) {
    graze.step(1 / 60);
    peakSpin = Math.max(peakSpin, Math.abs(grazed.wz));
  }
  assert.ok(peakSpin > 1);
  assert.ok(grazed.vy > 0.1);
}

// Slow crossings are swallowed by pits, while a fast crossing may clear a
// narrow hole, matching the source's energy-toll rule.
{
  const pit = { x: 0.5, y: 0.5, radius: 1.6 * MARBLE.RADIUS, home: false };
  const slow = new MarbleMazeGame(board({ starts: [{ x: 0.45, y: 0.5 }], holes: [pit] }));
  slow.marbles[0].vx = 0.4;
  for (let index = 0; index < 240 && !slow.settled; index++) slow.step(1 / 60);
  assert.equal(slow.marbles[0].state, "lost");

  const fast = new MarbleMazeGame(board({ starts: [{ x: 0.45, y: 0.5 }], holes: [pit] }));
  fast.marbles[0].vx = 0.95;
  for (let index = 0; index < 240 && fast.settled === false; index++) fast.step(1 / 60);
  assert.equal(fast.marbles[0].state, "rolling");
}

// The home cup is not a dead pit: reaching it settles the run as a win.
{
  const cup = { x: 0.5, y: 0.5, radius: 0.08, home: true };
  const game = new MarbleMazeGame(board({ holes: [cup] }));
  game.marbles[0].vx = 0.4;
  for (let index = 0; index < 240 && !game.settled; index++) game.step(1 / 60);
  assert.equal(game.marbles[0].state, "home");
  assert.equal(game.won, true);
}

// Pair contacts prevent two active marbles from tunnelling through each other.
{
  const game = new MarbleMazeGame(board({
    starts: [{ x: 0.4, y: 0.5 }, { x: 0.6, y: 0.5 }],
  }));
  game.marbles[0].vx = 0.5;
  for (let index = 0; index < 120; index++) game.step(1 / 60);
  assert.ok(game.marbles[1].x - game.marbles[0].x >= 2 * MARBLE.RADIUS - 1e-6);
  assert.ok(game.marbles[1].vx > 0.05);
}

// Rails and pair contacts remain active while a marble is falling through a
// hole; only the floor contact is disabled by the falling state.
{
  const game = new MarbleMazeGame(board({
    holes: [{ x: 0.5, y: 0.5, radius: 0.02, home: false }],
    walls: [{ x0: 0.52, y0: 0.45, x1: 0.53, y1: 0.55 }],
    starts: [{ x: 0.45, y: 0.5 }],
  }));
  const marble = game.marbles[0];
  marble.vx = 0.4;
  for (let index = 0; index < 20; index++) game.step(1 / 60);
  assert.notEqual(marble.state, "falling");
}

console.log("PASS: browser Marble Maze physics, holes, walls, tilt, and contacts");
