// Smoke-test the stateless task-frame ABI. This only proves rendering for the
// explicitly supplied state; it does not prove that a controller accepted an
// action or reached the state. Stateful game replays belong in controller and
// shell E2E tests.
import fs from "fs";
import { spawnSync } from "child_process";
import { fileURLToPath } from "url";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { decode, Kind } from "../shells/web/display-list.js";

const wasm = fileURLToPath(new URL("../build/nwcore.wasm", import.meta.url));
const { exports, instance } = await instantiateElisa(fs.readFileSync(wasm), { warn: false });
const ptr = Number(exports.nw_frame_alloc(1048576n));

const cards = [
  [0, ["N-Back", "Monkey Ladder", "In the Dark", "Fog of War", "Removals", "Chain of Custody"]],
  [1, ["Concentration", "Seen It Before?", "Trivia"]],
  [2, ["Reflex", "N-Cup Monte", "Moving Targets", "Lookout", "Pursuit", "Buzz Wire", "Out of Sight", "Donkey", "Two Hands", "Overrun", "Marble Maze"]],
  [3, ["Count", "Mr. Time"]],
  [4, ["Graph Mapping", "Matrix Reasoning", "Jigsaw Puzzle", "Sudoku", "Find the Winning Move", "Crossed Wires", "Crossword", "Scrabble", "Scramble", "Algebra", "Numberology", "Syllogisms", "Winning Move", "Verbal Reasoning"]],
  [5, ["Tower of Hanoi", "Traveling Salesman", "Sokoban", "Maze", "3D Maze", "3D Sokoban", "Freeform Tetris", "N-in-a-row"]],
  [6, ["Cookie Thief"]],
];

function frame(category, selected, phase, action, cursor, value, steps, verdict) {
  const length = Number(exports.nw_task_game_input_write(
    BigInt(ptr), 1024n * 1024n, BigInt(category), BigInt(selected), 0n,
    BigInt(phase), BigInt(action), BigInt(cursor), BigInt(value),
    BigInt(steps), BigInt(verdict), 912n, 684n));
  if (length <= 0) throw new Error(`empty frame ${category}:${selected}`);
  return new Uint8Array(instance.exports.memory.buffer, ptr, length).slice();
}

function sameBytes(left, right) {
  if (left.length !== right.length) return false;
  for (let index = 0; index < left.length; index++) {
    if (left[index] !== right[index]) return false;
  }
  return true;
}

const failures = [];
let cardsChecked = 0;
for (const [category, names] of cards) {
  for (let selected = 0; selected < names.length; selected++) {
    const readyBytes = frame(category, selected, 0, 0, 0, 0, 0, -1);
    let runningBytes = frame(category, selected, 1, 1, selected, 0, 0, -1);
    const movedBytes = frame(category, selected, 1, 2, selected + 1, 7, 1, -1);
    const judgedBytes = frame(category, selected, 2, 8, selected + 2, 42, 2, 0);
    if (process.env.NW_TEST_MUTATE_READY_AS_RUNNING === "1" &&
        category === 0 && selected === 0) {
      runningBytes = readyBytes.slice();
    }
    const readyCommands = decode(readyBytes);
    const runningCommands = decode(runningBytes);
    const movedCommands = decode(movedBytes);
    const judgedCommands = decode(judgedBytes);
    const title = names[selected];
    const text = (commands) => commands.filter((c) => c.kind === Kind.TEXT).map((c) => c.text);
    if (!text(runningCommands).some((line) => line.includes(title.split(" ")[0]))) {
      failures.push(`${category}:${selected} missing task title`);
    }
    if (sameBytes(readyBytes, runningBytes)) {
      failures.push(`${category}:${selected} ready and running frames identical`);
    }
    if (sameBytes(movedBytes, runningBytes)) {
      failures.push(`${category}:${selected} supplied input frame is identical to running frame`);
    }
    if (judgedBytes.length === 0 || judgedCommands.length === 0) {
      failures.push(`${category}:${selected} judged frame empty`);
    }
    if (readyCommands.length === 0 || movedCommands.length === 0) {
      failures.push(`${category}:${selected} ready or input frame has no decoded commands`);
    }
    cardsChecked++;
  }
}

// Boundary values must remain total: a shell can briefly send an out-of-range
// cursor while a pointer or keyboard event is being normalised.
for (const [category, names] of cards) {
  for (let selected = 0; selected < names.length; selected++) {
    frame(category, selected, 1, 2, -1, -1, 0, -1);
    frame(category, selected, 1, 2, 9999, 999999, 9999, 1);
  }
}

if (failures.length) {
  console.log(failures.slice(0, 20).join("\n"));
  console.log(`FAIL: ${failures.length} task-frame ABI failures across ${cardsChecked} cards`);
  process.exit(1);
}
if (process.env.NW_TEST_MUTATE_READY_AS_RUNNING !== "1") {
  const mutation = spawnSync(process.execPath, [fileURLToPath(import.meta.url)], {
    encoding: "utf8",
    env: { ...process.env, NW_TEST_MUTATE_READY_AS_RUNNING: "1" },
  });
  if (mutation.error || mutation.status === 0) {
    console.error("FAIL: identical-ready/running mutation was not detected");
    if (mutation.error) console.error(mutation.error.message);
    process.exit(1);
  }
  if (!mutation.stdout.includes("ready and running frames identical")) {
    console.error("FAIL: mutation subprocess failed for an unrelated reason");
    console.error(mutation.stdout);
    console.error(mutation.stderr);
    process.exit(1);
  }
}
console.log(`PASS: ${cardsChecked} task-frame ABI cases and identical-frame mutation check`);
