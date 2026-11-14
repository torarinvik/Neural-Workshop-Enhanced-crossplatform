# Neural Workshop runtime protocol

**Status (2026-11-10):** common WASM v1 remains partial. The reviewed
capability manifest records 43 stateful web controllers, one web stateless
entry, and the host-owned Marble physics prototype; Python and SDL each record
24 stateful controllers and 21 not-yet-integrated entries. The web menu is now
generated from the schema-v5 reviewed catalog, and controller dispatch uses
stable task IDs. The catalog audit attributes every common-v1 export to a task
or the two global exports; native and non-v1 export inventories remain open.
Python and SDL task hubs expose only their explicitly implemented controllers;
unintegrated entries remain inert. No generic or
non-3D N-Back mode is part of the port.

The current application artifact was promoted on 2026-11-10 using the
source-fresh Elisa-compiler Stage1 product at commit
`d3b2e657d57c159c77b9523542f21fd67a93b916`, source fingerprint
`9de69658a554a61ac1679e3cd52398ea73800adf700fb0c51d7a636324dceef9`, product
SHA-256 `eaa65de1651631e703365e46a39ede6f1bcee123c3653755c368c59f51725f0f`.
The promoted `build/nwcore.wasm` is 1,629,226 bytes, SHA-256
`a99f7d098a76f495b94505873a283c7f6cdcdab25c279c5c04e996228069b30d`; the
linked Stage1 object SHA-256 is
`c7761d5729d0e66493a6587c1b66f1c497b9c7ef8cd3986b376ab6f9f4bc9837`. The
complete latest-Stage1 application build and artifact suite passed before
promotion, including Go rules, browser interaction, and original-source replay,
the Sudoku 186-action original-source replay, common-v1 contracts, browser
contracts, and 275 Marble trajectory scenarios / 33,982 frame states. No
Stage0 or Stage1 compiler product was rebuilt. The older 2026-10-07 Count v6 artifact and
receipt remain in
`output/verification/count-v6-snapshot-promotion-20261007/`; the full compiler
gate result recorded there is historical and is not a current Stage1 compiler
gate claim.

The immediately previous 2026-10-07 artifact was the Tetris v3-only product
with WASM SHA-256
`a43f716d4607c6b1311ee2d53ece0d70a3b10b330cedb8f11e8f27d930ebc960` and
Stage1 object SHA-256
`1a72c08372e63168fb68d21035ab0ce2e5d8159de8321718ffa19c6b3350ce26`; its
previous files are preserved in the current promotion receipt directory. The
preceding 2026-10-07 artifact was
`125d831827b15c94366aef3bfdc33ed052ad9d99e03da52fc2d2292bc53133b3`
(1,652,353 bytes, Stage1 object
`3ee4f8ee193b84ca1b487d44677d1e875a281bceedef7ebb0eb288aabf47a8d8`). Its
Tetris snapshots used the legacy raw v1 format. The older production artifact
was promoted on 2026-10-05 by
`scripts/build_latest_stage1_wasm.sh` from Elisa-compiler Stage1 commit
`541788548651d43dd466d0b5210955eb966eb18e` and Elisa-core Stage0 commit
`f84b9c1034f708f69d048bd6cafb813e88c8210f`. Its exact build products were
Stage1 SHA-256
`5459f03e7efbaa228936223931bfca61a96e6b4ad0558aeb8bf495b861cab81a`, Stage0
SHA-256 `5f2c14780bb91b25feeef3e4dce685ba9199d264ab75f335b064741a138ea84e`,
and runtime-object SHA-256
`b51e6114f0576681e432e1162a3dbdcdac46c140d3b7e7256c0069be0bd11897`. The
deployed `build/nwcore.wasm` SHA-256 is
`292800bf992e1cc61bce540ad53c0fa1f89f18de0ae35641166f5bd6d92e73c0`; its
linked object is
`a8e8d596ad07afa2005b266c66e5770e31d2f102ba781e71a62b7908bd8bab01`. The
artifact gate, provenance guard, and served-byte comparison passed. On
2026-10-06, the separate Stage1 checkout received the initializer-shadowing
compiler correction and was rebuilt to product SHA-256
`7da8c73a339457f81e8274ef8a4def07cd6c30545818dd84a7e7c55f1daf2c3f`; this
identity was superseded by the 2026-10-07 build above. Stage0 remains the
oracle build for source parity. Schema v5 now records source-derived option contracts for all 45 task IDs.
Complete per-task service/input and native-export declarations remain open, and
the browser does not yet apply or persist every catalogued option. Monkey
Ladder v5, 3D N-Back v4, and Count v6 snapshots use little-endian field
serializers for controller state, RNG/history, geometry, and protocol ordering metadata.
Legacy raw v1 snapshots for Monkey Ladder, 3D N-Back, and Tetris remain
restore-only same-build compatibility. Sokoban v2, Tetris v3, and Count v6
snapshots also use little-endian field serializers. Cross-version migration,
task-neutral effect production, snapshots for the other tasks, full text/IME
transport, and exact all-shell acceptance remain open. Task-specific exports
alone are not evidence of common-v1 support.

## 1. Ownership boundaries

- **Kernel:** deterministic task rules and task-domain generation.
- **Controller:** a run's phase, options, RNG, score, deadline, semantic input,
  and state transitions. Controller actions are the only production path that
  may grade a response or advance a task.
- **Scene:** a read-only projection of controller state into display commands.
  Rendering must not grade, consume randomness, change a deadline, or write a
  result.
- **Export adapter:** validate scalar ABI inputs, resolve an opaque state
  handle, call the controller/scene, and return explicit success/failure.
- **Shell:** create the run from user options and a seed; map physical input to
  typed semantic events; supply monotonic time and host replies; render frames;
  cancel scheduled callbacks and destroy the run on replacement/exit.

No task may keep the authoritative phase, answer, adaptive difficulty, or
score in both a shell and its controller. Shell caches are presentation-only
and must be reconstructible from public controller state.

## 2. Required common v1 lifecycle

The common adapter must provide these operations, with a versioned ABI and
task-neutral error representation. WASM API v1 currently implements the
operations for twenty-six controller lifecycles listed below; unsupported
operations return an explicit error rather than pretending to succeed:

1. `create(task_id, options, seed) -> handle | error`
2. `dispatch(handle, event) -> accepted | ignored | error`
3. `advance(handle, logical_time, elapsed_time) -> state_change | error`
4. `read_state(handle, output_buffer) -> bytes_written | error`
5. `render(handle, viewport, output_buffer) -> bytes_written | error`
6. `drain_effects(handle, output_buffer) -> bytes_written | error`
7. `snapshot(handle, output_buffer) -> bytes_written | unsupported | error`
8. `restore(snapshot, options) -> handle | unsupported | error`
9. `destroy(handle) -> success | error`, idempotent for a valid handle.

### 2.1 Current WASM v1 ABI

All `nw_api_v1_*` exports use signed `i64` scalar arguments because this Elisa
WASM toolchain lowers the host ABI through that type. Callers must use JS
`BigInt` for every `i64`; handles are opaque positive integers, never linear
memory pointers. The fixed registry admits at most 64 simultaneously live
runs. Handle values increase monotonically. Destroy retains a tombstone so a
repeat destroy succeeds until the slot is reused; afterward that stale handle
returns `ERR_INVALID_HANDLE`.

Stable task IDs are the unsigned 32-bit FNV-1a hash of the UTF-8 stable ID,
returned as positive `i64` values:

| Stable ID | Value | v1 support |
| --- | ---: | --- |
| `nback` (catalog identity; port scope is 3D only) | `2864510421` | yes; 3D only |
| `monkey_ladder` | `4150660153` | yes |
| `graph_mapping` | `921237686` | yes; browser controller |
| `matrix_reasoning` | `3934003723` | yes; browser controller |
| `crossed_wires` | `2239133075` | yes; browser, Python and SDL controllers |
| `sudoku` | `4211466488` | yes; browser controller |
| `sokoban` | `498559474` | yes |
| `count` | `967958004` | yes |
| `mr_time` | `337138730` | yes |
| `marble_maze` | `642986` | lifecycle yes; render is host-owned/unsupported |
| `tetris` | `679042920` | yes; source-backed controller, state ABI, display-list render, and browser route |
| `tower_of_hanoi` | `1419634454` | yes |
| `maze` | `3848665378` | yes |
| `n_in_a_row` | `3456348074` | yes |
| `numberology` | `1263422208` | yes |
| `in_the_dark` | `1343235803` | yes |
| `fog_of_war` | `703034768` | yes |
| `concentration` | `1179922742` | yes |
| `recognition` | `3372563504` | yes |
| `trivia` | `200484614` | yes |
| `removals` | `2704363772` | yes |
| `chain_of_custody` | `1119512566` | yes |
| `ncup_monte` | `704181153` | yes |
| `reflex` | `2070613823` | yes |
| `moving_targets` | `228173702` | yes |
| `lookout` | `3096915418` | yes |
| `buzz_wire` | `747330860` | yes |
| `pursuit` | `250940285` | yes |
| `out_of_sight` | `1771687311` | yes |
| `two_hands` | `1665677052` | yes |
| `overrun` | `1156693128` | yes |

`nw_api_v1_create(task, options_version, a, b, c, d, e, f, seed)` returns a
positive handle or a negative error. `options_version` must be 1. The six
task-specific scalar slots are deliberately documented here and reserved
slots must be zero:

| Task | `a` | `b` | `c` | `d` | `e` | `f` |
| --- | --- | --- | --- | --- | --- | --- |
| 3D N-Back (port scope only) | N: 1–8 | cubes: 1–6 | trials: 4–100 | interval ms: 100–600000 | stimulus ms: 1–interval | feedback ms: 0–600000 |
| Monkey Ladder | grid, 3–10 | initial length, 2–grid² | adaptive, 0/1 | show ms, 0–600000 | per-tile ms, 0–600000 | reveal answer, 0/1 |
| Sokoban | starting rung, 1–16 | trial count, 1–1000 | adaptive, 0/1 | show traps, 0/1 | 0 | 0 |
| Count | shape kind, 0–4 | start count: 2, 4, 6, 8, 10, 12, 16, 20, 25, 30, 40, 50, 60 | trials: 5, 10, 15, 20, 30, 50, 80, 100 | exposure ms: 0, 200, 350, 500, 750, 1000, 2000, 4000 | adaptive, 0/1 | show answer, 0/1 |
| Mr. Time | mode: recall `0`, produce `1`, both `2` | starting rung: 1–6 | trials: 5, 10, 15, 20, 30, 50, 80 | maximum gap ms: 500, 1000, 2000, 3000, 5000, 8000, 15000 | flash ms: 100, 200, 400, 800, 1500 | adaptive, 0/1 |
| Graph Mapping | nodes: 4, 5, 6, 7, 8, 9, 10, 12, 14, 16 | density: sparse `0`, medium `1`, dense `2` | trials: 5, 10, 15, 20, 30, 50, 80, 100 | exposure ms: 0, 3000, 5000, 8000, 12000, 20000 | adaptive, 0/1 | subtle, 0/1 |
| Find the Winning Move (Go) | starting level: 1–10 | positions per run: 1, 3, 5, 8, 10, 15, 20, 30, 50 | 0 | 0 | 0 | 0 |
| Matrix Reasoning | level: 1–12 | trials: 5, 10, 15, 20, 30, 50, 80, 100 | exposure ms: 0, 10000, 20000, 30000, 45000, 60000 | adaptive, 0/1 | `e` bit 0 feedback and bit 1 explanation | color, 0/1 |
| Jigsaw Puzzle | starting side: 2, 3, 4, 5, 6, 7, 8, 10 | puzzles: 1, 2, 3, 5, 8, 12, 20 | adaptive, 0/1 | preview, 0/1 | mark placed, 0/1 | 0 |
| Scramble | starting level: 1–12 | lines per run: 1–100 | show word count, 0/1 | adaptive, 0/1 | 0 | 0 |
| Scrabble | starting level: 1–10 | boards per run: 1, 2, 3, 5, 8, 10, 15 | show premiums, 0/1 | adaptive, 0/1 | 0 | 0 |
| Crossed Wires | rung: 1–12 | rounds: 1, 2, 3, 5, 8, 10, 15, 20 | adaptive, 0/1 | draw grid, 0/1 | 0 | 0 |
| Sudoku | rung: 1–12 | trials: 1, 2, 3, 5, 8, 10 | show clashes, 0/1 | adaptive, 0/1 | 0 | 0 |
| Marble Maze | starting rung, 1–16 | trial count, 1–1000 | adaptive, 0/1 | feedback ms, 0–600000 | time override ms: 0 or 15000, 30000, 45000, 60000, 90000, 120000 | cast shadows, 0/1 |
| Tower of Hanoi | starting disks, 3–12 | towers per run: 1, 2, 3, 5, 8, 10 | adaptive, 0/1 | 0 | 0 | 0 |
| Maze | starting rung, 1–15 | trial count: 1, 2, 3, 5, 8, 10, 15, 20 | adaptive, 0/1 | show trail, 0/1 | 0 | 0 |
| N-in-a-row | starting level, 1–9 | positions per run: 1, 2, 3, 5, 8, 10, 15 | grid: 0, 5, 6, 8, 12, 16, 24, 32, 64, 128 | pellets: 0, 7, 12, 22, 45, 80, 150, 300, 1200, 6000 | line: 0, 3, 4, 5, 8, 15, 40, 100 | `f` bit 0 shows answer and bit 1 enables adaptive difficulty |
| Numberology | starting level, >=1 | trials: 1, 2, 3, 5, 6, 8, 10, 15 | adaptive, 0/1 | 0 | 0 | 0 |
| In the Dark | starting rung, 1–12 | trials: 1, 2, 3, 5, 8, 10, 15, 20 | room duration ms: 500, 800, 1000, 1200, 1500, 2000, 3000 | adaptive, 0/1 | 0 | 0 |
| Fog of War | radius: 1, 2, 3, 4, 5 | moves: 100, 200, 300, 400, 600, 800, 1200 | worlds: 1, 2, 3, 5, 8, 10 | persist reveal, 0/1 | 0 | 0 |
| Concentration | pairs: 4, 6, 8, 10, 12, 15, 18, 21, 24, 30, 36, 42, 50 | medium: picture `0` or sound `1` | peek ms: 0, 500, 1000, 2000, 3000, 5000 | hide ms: 300, 500, 700, 900, 1200, 1600, 2000 | show turns, 0/1 | coach, 0/1 |
| Seen It Before? | trials: 10, 20, 30, 40, 60, 80, 100, 150, 200, 300, 500 | medium: picture `0` or sound `1` | repeat percent: 20, 30, 40, 50 | minimum lag: 1, 2, 3, 4, 6, 8, 12, 20, 30, 50, 80 | study ms: 0, 500, 1000, 1500, 2000, 3000 | feedback, 0/1 |
| Trivia | starting rung: 1–7 | trials: 1, 2, 3, 5, 10, 15, 25, 50 | show answer, 0/1 | adaptive, 0/1 | 0 | 0 |
| Removals | starting rung, 1–10 | trials: 1, 2, 3, 5, 8, 10, 15, 20 | move ms: 500, 800, 1000, 1200, 1500, 2000, 3000 | adaptive, 0/1 | 0 | 0 |
| Chain of Custody | starting rung, 1–10 | trials: 1, 2, 3, 5, 8, 10, 15, 20 | belt ms: 150, 250, 400, 600, 900, 1500 | marking ms: 400, 800, 1200, 1600, 2500, 4000 | adaptive, 0/1 | 0 |
| N-Cup Monte | start cups: 3, 4, 5, 6, 7, 8, 10, 12, 14, 16 | maximum cups: 3, 4, 5, 6, 7, 8, 10, 12, 14, 16, 18, 20 | adaptive, 0/1 | swaps: 2, 4, 6, 8, 12, 16, 24, 32, 48, 64, 100 | swap ms: 60, 100, 160, 220, 280, 340, 500, 750, 1000 | reveal ms: 300, 500, 750, 1150, 1500, 2000, 3000 |
| Reflex | targets: 10, 20, 30, 40, 60, 80, 120, 200, 300, 500 | lifetime ms: 400, 600, 800, 1200, 1600, 2200, 3000, 4000 | spawn gap ms: 150, 250, 400, 550, 700, 1000, 1500, 2000 | maximum active: 1, 2, 3, 4, 5, 6, 8, 10, 12 | start size: 60, 80, 100, 130, 170, 220, 280 | adaptive, 0/1 |
| Moving Targets | balls: 3, 4, 5, 6, 8, 10, 12, 15, 20, 25, 30 | targets: 1, 2, 3, 4, 5, 6, 8, 10, 12, 15 (clamped below balls) | cue seconds: 3, 5, 8, 10, 15, 20, 30, 45, 60 | speed percent: 8, 12, 16, 22, 30, 40, 55, 75 | rounds: 3, 5, 8, 10, 15, 20, 30, 50 | adaptive, 0/1 |
| Lookout | shapes: 3, 4, 5, 6, 8, 10, 12, 15, 20, 25, 30 | watching: colour `0`, form `1`, both `2` | speed percent: 8, 12, 16, 22, 30, 40, 55, 75 | morph ms: 800, 1200, 2000, 3000, 5000, 8000 | cues: 5, 10, 15, 20, 30, 50 | adaptive, 0/1 |
| Buzz Wire | starting rung: 1–12 | trials: 1, 2, 3, 5, 8, 10 | adaptive, 0/1 | show meter, 0/1 | show beads, 0/1 | show sight, 0/1 |
| Pursuit | speed percent: 4, 6, 8, 10, 12, 14, 16, 18, 20, 25, 30, 35, 40, 50, 60, 75, 90 | surge percent: 0, 20, 40, 60, 80, 100, 150, 200, 300 | turn gap ms: 200, 300, 400, 600, 900, 1200, 1600, 2200, 3000, 5000 | turn degrees: 30, 45, 60, 90, 120, 150, 180 | base size: 10, 13, 16, 19, 22, 26, 31, 38, 46, 60 | packed `f`: wobble `0..6`, morph `0..6`, seconds `0..7`, rounds `0..7`, adaptive bit |
| Out of Sight | dots: 3, 4, 5, 6, 8, 10, 12, 15, 20, 25, 30 | targets: 1, 2, 3, 4, 5, 6, 8, 10, 12, 15 | speed percent: 8, 12, 16, 22, 30, 40, 55, 75 | crossing gap ms: 0, 600, 900, 1200, 1600, 2200, 3000, 5000 | blind slabs: 0, 1, 2, 3, 4, 5, 6, 8 | packed `f`: blind width × probes × rounds × adaptive |
| Overrun | starting rung: 1–12 | waves: 3, 5, 8, 12, 20, 30 | adaptive, 0/1 | 0 | coach/reserved, 0 | reserved, 0 |
| Two Hands | starting rung: 1–10 | trials: 1, 2, 3, 5, 8, 10, 15, 20 | beat ms: 150, 250, 400, 600, 900, 1400 | setting ms: 0, 400, 800, 1200, 2000, 3000 | adaptive, 0/1 | reserved, 0 |

The current browser defaults are 3D N-Back `(2, 1, 24, 3000, 500, 200)` with
seed 1, Monkey Ladder `(5, 3, 1, 700, 280, 1)` with
seed 1, Sokoban `(2, 5, 1, 0, 0, 0)` with seed 17, Count
`(0, 8, 15, 0, 1, 1)` with a run seed from browser entropy, Find the Winning
Move `(1, 10, 0, 0, 0, 0)` with seed 17, Marble Maze
`(1, 5, 1, 2600, 0, 1)` with a run seed from browser entropy, and Tower of
Hanoi `(4, 3, 1, 0, 0, 0)` with seed 1. Marble's `e=0`
uses the original rung-specific time limit; a positive supported value overrides
it. `f=1` enables the source-default shadows setting. Count accepts
`?count-seed=<nonnegative-i64>` for deterministic replay. New browser profiles
use the source defaults `(0, 8, 15, 0, 1, 1)`; the real task menu and the task
screen in READY/DONE open six source-defined options with `C`. Accepted values
are validated and persisted under `neural-workshop.count.options.v1`, then
passed to a fresh controller. Escape cancels the draft, and timed shape
exposure follows the selected duration. The browser requests Count display
lists in the shared 912×684 reference space; the canvas applies device-pixel
scaling once, keeping text, prompts, and generated shapes in the viewport.
Mr. Time accepts `?mrtime-seed=<nonnegative-i64>` for deterministic
recall/produce replays; the browser defaults recall mode, rung 1, 15 trials,
a 3-second hidden gap, 400 ms flash, and adaptive difficulty. The real task
menu opens Mr. Time options with `C`; its six source-defined settings are
validated, saved under `neural-workshop.mr-time.options.v1`, and applied to a
fresh controller when accepted. Escape cancels the draft. The task screen also
opens options with `C` while READY or DONE, matching the reference UI.
Overrun uses `(4, 3, 1, 0, 0, 0)` with seed 17 in the browser route. Its
fallback sentence pool is the original offline seed bank filtered by the
source 24–44 character lane band; the fetched corpus remains a planned host
integration rather than an implicit browser dependency.
Two Hands uses `(3, 5, 400, 1200, 1, 0)` with seed 17 in the browser route.
Its controller calls the source road generator, wheel/ride transition,
advance, overrun, and sighting rules; the browser supplies only normalized
keyboard/pointer events, monotonic time, and display-list presentation. The
source road, sky target, ride, scoring, verdict, and result fields remain
owned by the controller.
Jigsaw defaults to `(3, 3, 1, 1, 0, 0)`, matching the original side, puzzle
count, adaptive, preview, and mark-placed settings. Its browser options panel
validates and persists all five values and recreates the controller when
applied. The `e` slot carries `mark_placed`; `f` is reserved. The shell can
import the external DIV2K directory into IndexedDB, stores its unseen-photo
rotation across sessions, and renders the source tile crops and centered-square
preview. The coloured-tile fallback remains available when no photos are
imported.
N-Cup Monte uses `(3, 8, 1, 6, 340, 1150)` with seed 17 in the browser
route. Its source-default cup numbers remain enabled because the shared six-
slot options ABI has no seventh `show_numbers` field; the controller documents
that compatibility choice through `INFO_SHOW_NUMBERS=1`. Adaptive success and
miss preserve the source's current cup count for the next round, clamped to
the configured maximum and the source minimum of three.
Reflex uses `(40, 1600, 700, 3, 130, 1)` with seed 17 in the browser route:
forty targets, a 1.6-second base lifetime, a 700 ms spawn gap, three active
targets, a 130 px starting size, and adaptive difficulty. The browser supplies
a deterministic synthetic image pool, while target identity, placement,
shrinking time, pointer hit-testing, score, and adaptive lifetime remain in
the controller.
Moving Targets uses `(8, 2, 8, 16, 5, 1)` with seed 17 in the browser route:
eight balls, two targets, an eight-second tracking window, sixteen-percent
speed, five rounds, and adaptive target-count adjustment. Its controller keeps
the source's cue, tracking, picking, revealing, and done deadlines in WASM;
the browser supplies only a monotonic animation clock and pointer coordinates.
Lookout uses `(8, 0, 16, 2000, 10, 1)` with seed 17 in the browser route:
eight shapes, colour watching, sixteen-percent drift, a two-second morph gap,
ten cues, and adaptive shape-count adjustment. `F` answers the form channel
and `J` answers the colour channel, matching the source footer. The controller
keeps the shuffled absent cue, seen timestamps, signal-detection score, morph
clock, feedback deadline, and adaptive flock in WASM; the browser supplies only
keyboard events, a monotonic animation clock, and display-list presentation.
Pursuit uses `(18, 60, 900, 120, 22, 4049)` with seed 17 in the browser route:
eighteen-percent quarry speed, sixty-percent surge, a 900 ms turn gap, 120
degree turns, a 22 px base size, and the packed default described in the option
table. Its `f` decoder uses wobble index `0..6`, morph index `0..6`, seconds
index `0..7` mapping to 10, 15, 20, 30, 45, 60, 90, or 120 seconds, round
index `0..7` mapping to 1, 2, 3, 5, 8, 10, 15, or 20 rounds, and an adaptive
bit. The controller keeps source fractional quarry
coordinates, continuous on/off timing, turn/surge/morph deadlines, sampled
results, and adaptive multiplier in WASM; the browser supplies only a
monotonic clock, normalized pointer coordinates, keyboard actions, and scene
presentation.
Out of Sight uses `(8, 2, 16, 1600, 3, 476)` with seed 17 in the browser route:
eight moving dots, two target dots, sixteen-percent speed, a 1600 ms crossing
gap, three blind slabs, and the packed default of nine-unit blind width, six
probes per round, five rounds, and adaptive difficulty. The packed `f` decoder is
`width_index + 6 * probes_index + 42 * rounds_index + 336 * adaptive`, with
widths `4,6,9,12,16,20`, probes `2,4,6,8,10,15,20`, and rounds
`1,2,3,5,8,10,15,20`. The controller keeps flock positions/velocities,
source blind slabs, crossing schedules, probe timing, mine/not-mine grading,
reaction results, and round transitions in WASM; the browser supplies only the
monotonic clock, J/F semantic actions, and scene presentation.
Marble uses a
persistent CPython-compatible MT19937 stream to draw each board seed with
`randrange(1 << 30)`, as the reference does; `?marble-seed=<nonnegative-i64>`
provides a deterministic run stream for regression replays. Count still lacks
its source-derived options screen and persistence. Marble's task-specific options
screen exposes the original rung, trial count, adaptive, shadows, and
seconds-per-tray choices and persists them in browser local storage. Maze uses
`(2, 5, 1, 1, 0, 0)` with seed 17 in the current browser route; `d=1` enables
the source trail option. Maze's browser options UI and persistence remain open.

Numberology uses `(1, 6, 1, 0, 0, 0)` with seed 17 in the current browser
route; its starting level is unbounded above one, trial choices follow the
source set, and adaptive promotion occurs after a perfect session.

In the Dark uses `(2, 5, 1200, 1, 0, 0)` with seed 17 in the current browser
route. The source-compatible options are starting rung 1–12, the listed trial
counts, room duration in milliseconds, and adaptive difficulty. Its per-run
MT19937 stream deals the room walk and hidden questions; no shell answer table
is authoritative.

Concentration uses `(8, 0, 0, 900, 1, 0)` with seed 17 in the current browser
route. The source-compatible options are pair count, picture/sound medium,
initial peek duration, mismatch-hide duration, turn-counter visibility, and
coach feedback. Picture mode deals the source card identities and shows the
whole board until the peek deadline; sound mode skips the visual peek. The
controller retains the source identity sets so lapse scoring distinguishes a
previously exposed physical card from merely seeing another card of the same
pair. Space/Enter starts READY or replays DONE; primary pointer-down selects a
card while PLAYING. `ACTION_START=0` and `ACTION_SELECT=1`, with `value` equal
to the zero-based card slot.

Seen It Before? uses `(40, 0, 40, 4, 0, 1)` with seed 17 in the current
browser route. The source-compatible options are trial count, picture/sound
medium, repeat percentage, minimum repeat lag, picture study duration, and
per-answer feedback. The controller plans a full stream before presentation:
fresh identities are shuffled with the source-compatible MT19937 stream, a
repeat is eligible only after the minimum lag and only once per fresh identity,
and the browser receives stable synthetic asset IDs `2000..2499` because the
source filesystem media pool is not part of the WASM ABI. Picture trials move
from SHOWING to HIDDEN at the study deadline; sound trials remain SHOWING and
support replay. `START=0`, `SEEN=1`, `NEW=2`, and `REPLAY=3`; Space/Enter starts
READY or replays DONE, left/S/Y answers Seen, right/N answers New, R replays,
and the two buttons use the same reference coordinates as the scene.

Removals uses `(3, 5, 1200, 1, 0, 0)` with seed 17 in the current browser
route. The moving phase advances exactly one source move at each move
deadline, then asks for the missing van; Space/Enter starts READY, moves to
the next trial after the scored deadline, and keys `1`–`5` select the
source-generated van. Its `nw_api_v1_removals_info` and
`nw_api_v1_removals_value` accessors expose copied controller arrays, not
temporary generation storage.

Chain of Custody uses `(3, 5, 400, 1600, 1, 0)` with seed 17 in the current
browser route. The controller preserves the source's separate layout-seed and
box-deal streams, marking interval, belt deadline, claw position, held-box
ownership, machine treatment, delivery predicate, adaptive history, and
one-second verdict gate. Space/Enter starts READY or advances SCORED at its
deadline; left/right (or A/D) move the claw; up/down or Z pick up/put down.
`nw_api_v1_custody_info` exposes additive deadlines and score fields, and
`nw_api_v1_custody_value` exposes copied machine/box values.

Fog of War uses `(2, 400, 3, 0, 0, 0)` with seed 17 in the current browser
route. The source-compatible options are visibility radius, moves per world,
worlds per run, and per-world reveal persistence. Its per-run MT19937 stream
draws one `randrange(1 << 30)` deal seed per world; the controller copies the
25×15 generated open mask out of the temporary generation region before that
region is destroyed. `START=0`, `STAY=1`, `UP=2`, `DOWN=3`, `LEFT=4`, and
`RIGHT=5`; Space/Enter starts READY, advances FINISHED, and starts a new DONE
run, while arrows/WASD walk only during EXPLORING. Bumps consume a directional
move but change neither the walker nor the revealed picture. Coverage counts
unique walked open cells, not revealed cells.

Count semantic action codes are `START=0`, `DIGIT=1`, `BACKSPACE=2`,
`SUBMIT=3`. A digit action carries its numeric value in `value`; browser
keyboard text is sent as `EVENT_TEXT`, which Count accepts only for ASCII
digits `0`–`9`. Space starts or replays from READY/DONE, Enter submits, and
Backspace/Delete removes one typed digit. Input is capped at three digits and
follows the reference's leading-zero normalization.

Scrabble hosts send `START_CLOCK=10` with a fresh monotonic timestamp immediately
after a start action or pointer event successfully creates a playing board.
This one-time action excludes synchronous deal generation from the elapsed
time. It is ignored after the first synchronization or another action; hosts
that do not send it retain the start event's timestamp for compatibility.

Scramble uses the same post-generation clock handoff with `START_CLOCK=5`.
The action is accepted once immediately after a deal starts; hosts that omit
it retain the start-event timestamp. Scramble info field 16 reports the sum of
answered-line elapsed times in whole seconds, truncated after accumulation.

Mr. Time semantic action codes are `START=0`, `DIGIT=1`, `POINT=2`,
`BACKSPACE=3`, `SUBMIT=4`, and `ACT=5`. Digit, point, and backspace actions
edit the controller-owned decimal response; `SUBMIT` grades recall duration
and `ACT` settles produce mode at the source target/deadline. Space/Enter
starts READY or DONE, digits and `.`/`,` arrive through ordered text events,
and duplicate actions are ignored outside the phase that accepts them.

Numberology semantic action codes are `START=0`, `WRITE=1`, `BACKSPACE=2`,
and `SUBMIT=3`. Space starts READY, advances JUDGED, and starts a new DONE
session; Enter submits the typed answer while WORKING; Backspace/Delete removes
one typed digit; and text events carrying ASCII digits or `-` append to the
controller-owned signed answer buffer. Numeric overflow is rejected rather
than allowing the displayed text and the i64 grading value to diverge. Each
trial is generated by the source `Numberology::generate` kernel using the
persistent per-run MT19937 stream. Fixed controller storage copies the
generated terms out of the temporary generation region before it is destroyed,
and the scene renders the source sequence, rule explanation, typed answer, and
feedback message.

In the Dark semantic action codes are `START=0` and colour answers `1..5`
(answer actions carry no additional payload). Space starts READY/DONE, waits
through the timed room walk, then exposes ASKING; keys `1`–`5` answer the
current question. The controller gathers all questions before grading, enters
SCORED for 800 ms, and only then accepts Space for the next trial. Correct
answers promote adaptive difficulty; fewer than half correct demote it. The
source-generated room operations, asked lamp positions, answers, and submitted
colours are exposed only through read-only test/debug accessors; hidden answers
are not rendered during ASKING.

Seen It Before? semantic actions are `START=0`, `SEEN=1`, `NEW=2`, and
`REPLAY=3`. Space/Enter starts READY or DONE; left/S/Y and right/N answer the
current item while SHOWING or HIDDEN; R requests source-style replay. Picture
study deadlines enter HIDDEN through `advance`; sound has no visual concealment
deadline. A correct answer enters FEEDBACK for 350 ms when feedback is enabled,
then presents the next planned item or enters DONE. The controller's repeat
stream and four-way score are authoritative; a host must not replace them with
an answer table or a JavaScript random generator.

Removals semantic actions are `START=0` and missing-van answers `1..5`.
Space/Enter starts READY or DONE and advances SCORED only at its one-second
verdict deadline; the controller's move clock, generated answer, and verdict
are authoritative. Chain of Custody semantic actions are `START=0`,
`LEFT=1`, `RIGHT=2`, and `GRAB=3`. Space/Enter starts READY or DONE and
advances SCORED at its verdict deadline; left/right move the claw only while
RUNNING, and up/down/Z invoke the grab/put-down action. `advance` first ends
MARKING at its deadline and then applies one source belt step per belt
deadline, settling to SCORED when the source action budget is exhausted.

Concentration semantic action codes are `START=0` and `SELECT=1`. Space and
Enter start a READY run or replay a DONE run; a primary pointer-down selects a
card while PLAYING. The source `Concentration::deal`, `flip`, `peek_over`, and
`resolve` kernels remain authoritative for shuffling, pair identity, match
resolution, and identity-aware lapse accounting. Picture mode enters PEEK and
`advance` hides the board at the configured deadline; sound mode enters
PLAYING immediately. After two unmatched cards are up, `advance` resolves the
pair at `hide_until_ms`; completed boards enter DONE with a clean/lapse verdict.
The additive `nw_api_v1_concentration_info` accessor exposes the phase,
options, counters, deadlines, and timestamps; `nw_api_v1_concentration_card`
returns the card identity, face-up flag, or matched flag for one slot.

Marble Maze semantic action codes are `START=0`, `RESTART=1`, `LEVEL=2`,
`REPORT=3`, `BOARD_READY=4`, `NEXT=5`, held North/East/South/West as
`6..9`, `SCORE=10`, and the host-only `SYNC_SETTLE_TIME=11`. For `REPORT`, `value` is a result bitmask: bit 0 is
the physical all-home verdict and bit 1 is the source `score()` win (zero lost
marbles); an all-home report must set both bits. `aux` is par ms. A timeout
enters feedback with its physical verdict immediately, then the host commits
the source score exactly once with `SCORE` after inspecting the physics-owned
lost count. `SYNC_SETTLE_TIME` is also accepted once in timeout feedback before
`SCORE`/`ACTION_RECORD_RESULT`, allowing the host to preserve measured physics
elapsed time slightly beyond the controller's deterministic timeout boundary.
With `e=0`, board duration is derived from the same source grade table as
`MarbleMaze::deal`; a nonzero `e` applies one of the source-supported
seconds-per-tray overrides. The additive
`nw_api_v1_marble_apply_options(handle, start_rung, total_trials, adaptive,
time_override_ms)` operation mirrors native `apply_options()`: it resets the
controller to undealt READY, clears the visible run result, and preserves the
already-advanced CPython-compatible RNG stream. The browser disposes only the
host physics pair before the next Space action deals the next source board.

`ACTION_RECORD_RESULT=12` is the host-only completion boundary: its `value`
is the physics-owned home count and its `aux` is the lost count. It is valid
only once in FEEDBACK after `REPORT` or timeout `SCORE`. The controller keeps
the completed source row through DONE and exposes `INFO_RESULT_COUNT=12` via
`nw_api_v1_marble_info`, while `nw_api_v1_marble_value` fields 100–106 return
the row's rung, elapsed milliseconds, home count, lost count, physical verdict,
source-score win bit, and board seed. This adds result history without
changing the common twelve-field state envelope. `ACTION_NEXT` and automatic
feedback expiry are blocked until both score commitment and result-row
commitment have succeeded, so a stalled host cannot silently skip a source
result between trays.

Find the Winning Move (Go) semantic action codes are `START=0`, `ANSWER=1`,
`NEXT=2`, `UP=3`, `DOWN=4`, `LEFT=5`, `RIGHT=6`, and `LEVEL=7`. The common
create options are starting level and positions per run; defaults are level 1
and 10 positions, and the accepted trial counts are exactly 1, 3, 5, 8, 10,
15, 20, 30, and 50. Phases are READY, SOLVING, JUDGED, and DONE. Space starts
READY or advances JUDGED; Enter submits the cursor intersection; arrows move
the cursor; number keys set levels 1–9 or 10 with `0` in READY/DONE; `C` opens
the source options UI; Escape returns to the task hub. A primary pointer-down
maps to the nearest Go intersection in the 912×684 reference canvas and is
accepted only when each axis is strictly within 0.42 of one board step. The
pointer mapper converts the source bottom-origin board geometry to row-major
cell order. `ANSWER.value` is that row-major cell. The source Go kernel grades
captures, occupied points, suicide, and its stateless immediate-ko behavior;
the puzzle environment itself supplies no ko history. Correct moves place the
stone and report captured stones, while misses distinguish occupied points,
non-captures, and captures below the puzzle target. The common public state
reports score and capture/verdict fields without exposing the winning point.
The browser persists options under `neural-workshop.go.options.v1`; Python and
SDL host launchers accept the same validated level/trial options.

Tower of Hanoi semantic action codes are `START=0`, `PICK_0=1`, `PICK_1=2`,
and `PICK_2=3`. Space and Enter start from READY/DONE; number keys 1–3 and
primary pointer-down events select a peg while SOLVING. Selecting a source peg
raises its top disk, selecting it again cancels the lift, a legal second peg
increments the move count, and an illegal set-down cancels the lift without
changing the board or score. A solved round remains in FEEDBACK for 1600 ms;
`advance` then starts the next tower or enters DONE. The optimum is the exact
source formula `2^disks - 1`; adaptive mode grows after efficiency at least
0.8 and shrinks below 0.5, with the source's clamping at 3–12 disks.

N-in-a-row semantic action codes are `START=0`, `SELECT=1`, `UP=2`,
`DOWN=3`, `LEFT=4`, `RIGHT=5`, and `SUBMIT=6`. `SELECT` carries an empty
flat board cell in `value` and only moves the source selection; `SUBMIT` grades
that selection. Space starts a READY or DONE run and advances JUDGED feedback
to the next position; arrows move the selected empty cell with source clamping;
Enter submits while ASKING. Primary pointer-down maps to the same cell
selection using the source board layout. Each dealt board is generated by the
ported `NinaRow::generate` kernel with the persistent per-run MT19937 stream,
and the controller copies its temporary board into fixed storage before the
generation region is destroyed. A correct answer raises the adaptive level by
one and a miss lowers it by one, both clamped to 1–9. The controller reports
`No unique position at this setting` as a completed unavailable trial when the
source generator exhausts its attempts.

Maze semantic action codes are `START=0`, `UP=1`, `DOWN=2`, `LEFT=3`,
`RIGHT=4`, and `RESTART=5`. Space and Enter start from READY/DONE and move
from SOLVED to the next trial; arrows and WASD walk one cell; `R` restarts the
current walk; and a move into a locked door is accepted as an attempted input
but leaves the walker and step count unchanged. Maze generation, walls, keys,
doors, exact shortest-path minimum, adaptive rung, and aggregate efficiency
are controller-owned. The additive `nw_api_v1_maze_info` accessor exposes
fields outside the fixed common envelope, while `nw_api_v1_maze_cell` returns
wall, walked, door-colour, or key-colour data for the current board.

Status values are `OK=0`, `ACCEPTED=1`, and `IGNORED=2`; errors are
`ERR_INVALID_HANDLE=-1`, `ERR_UNSUPPORTED_TASK=-2`, `ERR_BAD_OPTIONS=-3`,
`ERR_NO_MEMORY=-4`, `ERR_TABLE_FULL=-5`, `ERR_BAD_EVENT=-6`,
`ERR_EVENT_ORDER=-7`, `ERR_BUFFER=-8`, `ERR_UNSUPPORTED=-9`,
`ERR_TIME=-10`, and `ERR_VERSION=-11`. Functions returning a byte count return
a positive count on output, zero for a successful empty effect queue, or one
of these negative errors.

`nw_api_v1_dispatch` takes, in order,
`handle, kind, timestamp_ms, sequence, code, value, modifiers, flags,
x_millionths, y_millionths, aux`. Timestamps are nonnegative milliseconds
from the shell's monotonic clock. Sequence numbers begin at zero and strictly
increase per handle. Timestamps may tie but may not decrease. Valid ignored
events still consume their timestamp/sequence position; malformed events do
not. Modifiers use Shift/Ctrl/Alt/Meta bits 0–3. Flags reserve repeat bit 0,
primary-pointer bit 1, and IME-composition bit 2; only the key-repeat bit
currently changes dispatch behavior. Pointer-down `code` is the button index
(0 is primary). Pointer coordinates have a bottom-left origin in the logical
task viewport and range 0–1,000,000.

Event kinds are action 1, key-down 2, key-up 3, pointer-move 4,
pointer-down 5, pointer-up 6, wheel 7, text scalar 8, focus 9, visibility 10,
and cancel 11. For action events, `code` is the task's action enum and `value`
is its action payload. For key events, logical key codes are Space 1, Enter 2,
Left 3, Up 4, Right 5, Down 6, Escape 7, Undo 8, Restart 9, and Options 10;
Marble-specific Level is 11; Tower-of-Hanoi peg keys 1, 2, and 3 are 12, 13,
and 14. In the Dark uses numeric key codes 12–16 (keys `1`–`5`) for its five
colour-answer actions. Maze uses the same directional and restart key codes.
Scrabble maps arrows, Undo, keys 1–7, and Tab (logical key code 23) to its
movement, tile placement, and turn actions; the numeric key selects the rack
slot independently of the event's `value` field.
`value` carries the physical code. A text event
carries one Unicode scalar in `value`; a host would split longer UTF-8 text
into scalar events in order.
Focus and visibility payloads are booleans in `value`. The controllers
consume actions, supported key-downs, Monkey Ladder and Concentration primary
pointer-downs, Count and Numberology ASCII text events, and task-specific
deadlines/clocks.
Other valid
text events are ordered and ignored by Count. Maze maps arrow/WASD key-downs to
one-cell actions and `R` to restart; its pointer-down path is explicitly
ignored because the source screen is keyboard-only. Marble Maze maps arrow/WASD
key-down/up to a controller-owned held-direction bitmask, `R` to restart, and `L` to level;
focus loss, hidden visibility, and cancel clear held directions. The host
reports a settled physics outcome once as `ACTION_REPORT` with bit 0 set for
all marbles home and bit 1 set when the source score row has zero lost
marbles; `aux` equals the board's par time in milliseconds. A timeout is
finalized by the controller clock and then receives one `ACTION_SCORE` with
value `1` or `0` after the host reads the lost count. On a physical settlement,
the host sends `SYNC_SETTLE_TIME` immediately before `ACTION_REPORT` because
physics completes the final frame before the controller clock; this makes the
source elapsed time authoritative without changing the stable state envelope.
Duplicate reports or score commits are ignored outside their active phase. Other valid event kinds
are ordered and explicitly ignored. IME range replacement
and pointer capture are not yet implemented.

`nw_api_v1_advance(handle, logical_time_ms, elapsed_active_ms, sequence)`
shares the per-run sequence stream with dispatch. Logical time is monotonic;
elapsed active time is nonnegative and overflow-checked. Monkey Ladder
advances SHOW to INPUT when logical time is at or beyond its stored deadline.
Count advances SHOWING to HIDDEN at its configured exposure deadline. After a
submitted answer, FEEDBACK lasts 800 ms before the next generated tangle or
DONE; with answer display disabled, submission deals the next trial
immediately. Rendering does not consume the persistent shape-generation RNG.
Mr. Time's recall phase is SHOWING until `flash_ms`, WAITING until the
source-derived `ask_at` timestamp, and ASKING thereafter; the interval is
frozen while the answer is entered. In produce mode COUNTING ends at the
target duration or its late-grace deadline, `ACT` settles the response, and
feedback lasts 1200 ms before the next trial or DONE. The browser scheduler
uses the controller's `advance` clock rather than deciding phase transitions.
Marble Maze consumes elapsed active time in RUNNING and FEEDBACK. Running time
is capped at the dealt rung's source duration; expiry produces a timeout
verdict. FEEDBACK lasts the configured duration, then the controller either
enters DONE or advances trial/rung and draws the next per-board seed from its
persistent CPython-compatible run RNG before exposing PREPARING. Each board
also consumes the source UI's following `random()` draw for its wood-grain
seed; `nw_api_v1_marble_grain_seed(handle)` exposes that exact value as an
additive scalar without changing the twelve-field state envelope. The host
accessor returns a value in `[0.0, 4.0)` for a live Marble handle, `-1.0` for
an invalid/destroyed handle, and `-2.0` for another task type. Space starts
from READY/DONE and may skip FEEDBACK into the next tray; Enter is ignored for
Marble Maze, matching the native screen. The host
deals the board named by the public board generation/rung/seed, creates a fresh
physics service, then sends `ACTION_BOARD_READY`; only that transition starts
the next trial clock. Restart preserves controller elapsed time and
clears held directions before the host resets the physical simulation.
Tower of Hanoi advances SOLVED to the next round at its 1600 ms feedback
deadline. Maze has no timed controller phase; its `advance` call only participates
in event ordering and currently leaves the walk unchanged. In the Dark advances
each room at its configured deadline, enters ASKING after the final room, and
holds SCORED for 800 ms before accepting the next-trial Space action. Sokoban
currently has no timed controller phase. Concentration advances PEEK to PLAYING
at `peek_until_ms` and resolves a two-card mismatch at `hide_until_ms`; matching
pairs are applied by the source kernel when the second card is selected. The
controller clock is supplied by the browser's monotonic `performance.now()`
adapter. Seen It Before? advances picture SHOWING to HIDDEN at its study
deadline and FEEDBACK to the next presentation or DONE at its 350 ms deadline;
sound SHOWING has no study deadline. Its source-shaped score fields separate
hits, misses, false alarms, correct rejections, and answered trials. `read_state` writes exactly
112 bytes: four little-endian `u32` values (`NWR1` magic, state version 1,
task ID, twelve-field count), followed by twelve little-endian `i64` fields.
Monkey Ladder's fields are phase, grid, adaptive level, round level, round
length, next index, wrong cell, cursor cell, cursor-enabled flag, adaptive
flag, reveal flag, and deadline ms. The sequence itself is intentionally
private. Sokoban's fields are phase, rung, trial, total trials, player cell,
pushes, moves, verdict, width, height, solved count, and lost count. Count's
fields are phase (`READY=0`, `SHOWING=1`, `HIDDEN=2`, `FEEDBACK=3`, `DONE=4`),
shape kind, current adaptive count, trial, total trials, correct count, typed
numeric answer, normalized answer length, shown count, verdict (-1/0/1),
adaptive flag, and deadline ms. Task-specific info fields additionally expose
answer-display, exposure, total absolute error, and generated shape count.

Mr. Time's twelve common fields are phase (READY=0, SHOWING=1, WAITING=2,
ASKING=3, COUNTING=4, FEEDBACK=5, DONE=6), current rung, trial, total trials,
correct count, trial mode, answer count, target duration, measured interval,
verdict (-1/0/1), result count, and adaptive flag.
The additive `nw_api_v1_mr_time_info` fields expose mode, start rung,
deadline, feedback deadline, maximum gap, flash duration, appeared-at time,
and ask-at time without moving those authoritative values into JavaScript.

Tower of Hanoi's twelve common fields are phase (`READY=0`, `SOLVING=1`,
`SOLVED=2`, `DONE=3`), current tower disk count, round, total rounds, moves,
exact minimum, picked peg (`-1` when no disk is lifted), verdict (-1/0/1),
adaptive flag, completed rounds, rounded mean efficiency percent, and largest
tower completed. The additive `nw_api_v1_hanoi_info` accessor exposes the
start-disk option, feedback deadline, and last round duration without changing
the common envelope.

N-in-a-row's twelve common fields are phase (`READY=0`, `ASKING=1`,
`JUDGED=2`, `DONE=3`), current adaptive level, trial, total trials, board size,
selected cell, answer cell, pellet count, line length, verdict (-1/0/1),
answer-display flag, and adaptive flag. The controller-specific info fields
also expose right/asked counts, highest correct level, elapsed seconds, and
the raw grid/pellet/line options.

Numberology's twelve common fields are phase (`READY=0`, `WORKING=1`,
`JUDGED=2`, `DONE=3`), current level, trial, total trials, shown-term count,
answer, typed numeric value, typed digit count, verdict (-1/0/1), adaptive
flag, correct count, and rule complexity. The additive
`nw_api_v1_numberology_info` accessor exposes the generated rule ID/parameters,
the next adaptive level, and the source explanation fields; the term accessor
returns each displayed sequence term without exposing a shell-owned answer
table.

In the Dark's twelve common fields are phase (`READY=0`, `WALKING=1`,
`ASKING=2`, `SCORED=3`, `DONE=4`), current rung, trial, total trials, lamp
count, colour count, current room cursor, question cursor, verdict (-1/0/1),
adaptive flag, cumulative correct answers, and room count. The additive
`nw_api_v1_in_the_dark_info` accessor exposes the current room operation,
question metadata, deadline, total questions, best rung, room duration, and
current round question count. `nw_api_v1_in_the_dark_room` returns copied room
operations; `nw_api_v1_in_the_dark_asked` returns asked-lamp, answer, or
submitted-colour fields for deterministic smoke/reference checks.

Concentration's twelve common fields are phase (`READY=0`, `PEEK=1`,
`PLAYING=2`, `DONE=3`), pair count, card count, medium (`PICTURE=0`,
`SOUND=1`), turns, lapses, currently flipped-card count, matched-pair count,
verdict (`-1/0/1`), cursor card, show-turns flag, and coach flag. The additive
`nw_api_v1_concentration_info` fields `0..15` are phase, pair count, card
count, medium, turns, lapses, flipped count, matched pairs, verdict, cursor,
show-turns, coach, peek deadline, mismatch-hide deadline, start timestamp, and
finish timestamp. `nw_api_v1_concentration_card` fields are card identity,
face-up flag, and matched flag. These accessors expose fixed controller storage;
they do not return pointers into the temporary source board.

Seen It Before?'s twelve common fields are phase (`READY=0`, `SHOWING=1`,
`HIDDEN=2`, `FEEDBACK=3`, `DONE=4`), total trials, current index, medium,
repeat percentage, minimum lag, study duration, feedback flag, current item,
current repeat flag, last-correct flag, and active deadline. The additive
`nw_api_v1_recognition_info` fields `0..18` additionally expose shown time,
hits, misses, false alarms, correct rejections, answered count, and synthetic
asset ID. `nw_api_v1_recognition_item` exposes item identity, repeat flag,
answered flag, and selected choice for deterministic controller tests; these
values are not reconstructed by the browser shell.

Removals' twelve common fields are phase (`READY=0`, `MOVING=1`, `ASKING=2`,
`SCORED=3`, `DONE=4`), rung, trial, total trials, van count, box count, item
count, moves, cursor, asking cursor, verdict, and deadline. The additive
`nw_api_v1_removals_info` fields expose adaptive/session totals and move
configuration; `nw_api_v1_removals_value` returns the source-generated kind,
thing, other, asked, answer, and given values for a van/item slot.

Chain of Custody's twelve common fields are phase (`READY=0`, `MARKING=1`,
`RUNNING=2`, `SCORED=3`, `DONE=4`), rung, trial, total trials, layout width,
slot count, box count, bay slot, claw slot, held box, spent belt actions, and
action budget. `nw_api_v1_custody_info` additionally exposes the verdict,
marking/belt deadlines, timing options, machine constraints, moving flag,
right count, best rung, and guessing-floor percentage. The
`nw_api_v1_custody_value` accessor returns machine kind or copied box look,
charge, heat, slot, held, and delivered fields. Rendering reconstructs the
existing `SceneCustody` arrays from fixed controller storage; it does not
regenerate the layout or consult the RNG.

N-Cup Monte's twelve common fields are phase (`READY=0`, `REVEAL=1`,
`SHUFFLE=2`, `GUESS=3`, `RESULT=4`), current cup count, configured maximum,
adaptive flag, configured swap count, swap duration, reveal duration, cup-number
display flag, hidden ball identity, selected cup identity, planned swap count,
and settled swap index. `nw_api_v1_ncup_monte_info` fields `0..20` additionally
expose the reveal/shuffle deadline, active swap start and elapsed time, the two
slots in the active swap, round number, hit/miss totals, and the last-correct
flag. `nw_api_v1_ncup_monte_value` exposes copied visual-slot identity, current
X, target X, and planned swap entries. These values are fixed-storage copies;
the temporary source `NCupMonte::Table` never crosses an ABI call boundary.

Reflex's twelve common fields are phase (`READY=0`, `RUNNING=1`, `DONE=2`),
total targets, spawned count, maximum active targets, hit count, miss count,
rounded accuracy percentage, rounded mean reaction time, active-target count,
current adaptive lifetime in milliseconds, adaptive flag, and next-spawn
deadline. `nw_api_v1_reflex_info` fields `0..18` additionally expose the
source options, controller clock, verdict (`-1/0/1`), and last reaction time.
`nw_api_v1_reflex_value` exposes active-target identity, normalized centre X/Y
in parts per million, born timestamp, target lifetime, remaining-life fraction
in parts per million, and synthetic/source asset ID. Pointer-down hit-testing
uses each target's current shrunken rectangle; if targets overlap, the
smallest visible target wins.

Moving Targets' twelve common fields are phase (`READY=0`, `CUEING=1`,
`TRACKING=2`, `PICKING=3`, `REVEALING=4`, `DONE=5`), current round, total
rounds, ball count, asked target count, tracked target count, total caught,
total asked, current picked count, current caught count, verdict (`-1/0/1`),
and the active deadline. `nw_api_v1_tracking_info` fields `0..18` additionally
expose the source options, tracked count, round counters, controller clock,
ball-count limits, and phase-specific counters. The value accessor fields
`0..6` return the current ball's stable identity, normalized position,
velocity, target flag, and picked flag from fixed controller storage. `START` is the only
semantic action; Space and Enter map to it in READY and DONE, while pointer
input is accepted only during PICKING. A completed round is scored only after
the configured target count has been picked; adaptive mode changes the next
round's target count by one on a perfect or missed round, clamped to the source
option bounds.

Lookout's twelve common fields are phase (`READY=0`, `WATCHING=1`,
`FEEDBACK=2`, `DONE=3`), cue number, total cues, live shape count, watching
mode (`COLOR=0`, `FORM=1`, `BOTH=2`), hits, misses, false alarms, reaction
count, verdict (`-1/0/1`), feedback deadline, and controller clock.
`nw_api_v1_lookout_info` fields `0..20` additionally expose the source options,
cue colour/form, mean and last reaction, deadlines, and shape count.
`nw_api_v1_lookout_value` fields `0..6` return normalized X/Y, velocity,
colour, form, and next-morph timestamp for each live shape. `START=0`,
`COLOR=1`, and `FORM=2`; Space/Enter start READY/DONE, while `J` and `F`
answer their respective live channels only during WATCHING. A missed signal,
false alarm, or hit enters the source 1.4-second feedback phase; adaptive hits
and misses change the next flock count by one within 3..30.

Pursuit's twelve common fields are phase (`READY=0`, `CHASING=1`,
`FEEDBACK=2`, `DONE=3`), round, total rounds, speed percentage, result count,
on-target percentage, run time, off-target sample count, verdict (`-1/0/1`),
adaptive multiplier in parts per million, feedback deadline, and controller
clock. `nw_api_v1_pursuit_info` fields `0..24` expose the six validated source
options, phase timing, turn parameters, score totals, feedback/result summary,
and normalized pointer coordinates. `nw_api_v1_pursuit_value` fields `0..10`
return quarry position, heading, surge, radius, form, colour, and scheduled
turn/surge/resize/morph times. `nw_api_v1_pursuit_value` fields `100..102`
return result share percentage, drift pixels, and multiplier; the disjoint
namespace is required because quarry fields occupy `0..10`. `START=0`,
`UP=1`, `DOWN=2`, `LEFT=3`, and `RIGHT=4`; Space/Enter start READY/DONE,
source-compatible arrow/pointer cursor updates may occur outside CHASING, but
only CHASING samples them for the score, and pointer coordinates are normalized
before the source hit test. Feedback is observational through `ScenePursuit`; it never
recomputes continuous score or consumes the controller RNG.

Out of Sight's twelve common fields are phase (`READY=0`, `CUEING=1`,
`TRACKING=2`, `REVEALING=3`, `DONE=4`), current round, total rounds, dot count,
held target count, completed probes, probes per round, hits, wrong answers,
late answers, verdict (`-1/0/1`), and the active deadline. The additive
`nw_api_v1_out_of_sight_info` fields `0..29` expose the six options, current
flock/target counts, reaction statistics, blind/probe schedule, controller
clock, and last-round result. `nw_api_v1_out_of_sight_value` fields `0..7`
return each dot's normalized position, velocity, target marker, busy/risky
deadlines, and hidden marker; fields `100..103` return generated blind slab
geometry; fields `200..202` return held, asked, and right counts by completed
round. `START=0`, `MINE=1`, and `NOT_MINE=2`; Space/Enter start READY/DONE,
while `J` and `F` map to MINE and NOT_MINE during TRACKING. The source's
crossing deadline, blind slab generation, hidden target state, answer grading,
reaction timing, and adaptive target count remain controller-owned. Rendering
projects copied source state through `SceneOutOfSight` and does not advance the
clock or consume RNG.

The source deal consumes one CPython-compatible MT19937 `randbelow(cups)` draw
when a round starts. After the reveal deadline, the source plans exactly
`max(1, swap_count + cups)` distinct slot pairs from the same persistent RNG
stream. Each pair is animated for the configured duration with the source
smoothstep function `t²(3−2t)`; the slot permutation changes only at the exact
animation boundary. A click is converted from normalized viewport coordinates
to the source cup identity, not treated as a slot index. Correct adaptive
results add one cup and misses remove one, clamped to 3..maximum; the current
cup count is retained for the next round. Space/Enter starts READY and RESULT;
input during reveal/shuffle is ignored.

Fog of War's twelve common fields are phase (`READY=0`, `EXPLORING=1`,
`FINISHED=2`, `DONE=3`), world number, total worlds, walker cell, moves,
move budget, width, height, start cell, open-cell count, unique walked-cell
count, and persist-reveal flag. The additive `nw_api_v1_fog_info` accessor
exposes radius, visible-cell count, coverage in parts per million, completed
world count, total moves, rounded average percentage, bump count, and the
numeric coverage/message value. `nw_api_v1_fog_cell` exposes wall, revealed,
and walked flags for deterministic controller tests; browser rendering uses
only the controller's scene projection and does not reconstruct hidden world
state in JavaScript.

Maze's twelve common fields are phase (`READY=0`, `WALKING=1`, `SOLVED=2`,
`DONE=3`, `UNAVAILABLE=4`), current rung, trial, total trials, walker cell,
steps, verdict (-1/0/1), width, height, held-key mask, solved count, and
highest rung. The additive `nw_api_v1_maze_info` accessor exposes the start,
exit, door count, exact minimum, greedy comparison, adaptive/trail flags,
aggregate par/steps, elapsed whole seconds, message kind, and other source
fields. `nw_api_v1_maze_cell(handle, field, cell)` returns wall and walked
flags or one-based door/key colour identifiers; out-of-board cells return 0.

Marble Maze's fields are phase (`READY=0`, `RUNNING=1`, `FEEDBACK=2`,
`PREPARING=3`, `DONE=4`), current rung, trial, total trials, board generation,
board seed, elapsed board ms, remaining board/feedback ms, verdict (-1/0/1),
wins, losses, and held-direction mask (N/E/S/W are bits 0/1/2/3). The browser
does not keep duplicate phase, timeout, trial, verdict, rung, seed, or held-key
state. Its physics object is a host service and is replaced only when the
controller publishes a new board generation.

`render` writes the task's existing binary display list into a caller-owned
buffer and checks the full range against current WASM linear-memory size,
capacity, and task viewport bounds before rendering. Count projects its
controller-owned shapes through the existing `SceneCounting` display list.
Numberology projects its controller-owned terms and explanation through the
existing `SceneNumberology` display list.
In the Dark projects its phase-appropriate room/question presentation through
the existing `SceneInTheDark` display list; the render path receives the
controller-owned submitted colours but does not draw hidden answer colours
while the task is ASKING.
Concentration projects its controller-owned card faces, matched state, medium,
turn counter, and phase/verdict message through the existing
`SceneConcentration` display list. Rendering is observational and does not
consume the controller RNG or alter a deadline. The browser installs a
self-contained 64-card fallback image pool for picture mode; sound mode uses
the source's text-style card projection, so replacing that fallback with the
original media assets remains a separate fidelity task.
Seen It Before? projects its title, source-shaped status/counter, current
picture or sound plate, answer buttons, feedback verdict, and DONE summary
through `SceneRecognition`. The renderer receives the controller's synthetic
asset ID but never decides whether an item is old or new. Feedback and DONE
are mapped to the scene's terminal presentation phase so no answer buttons or
stale trial counter remain visible after an answer. Original dataset/media
parity and sound playback effects remain open; the controller's stable item
identity and repeat/scoring trace are authoritative.
Removals projects the source moving-yard, missing-van prompt, submitted answer,
per-item verdict glyphs, feedback, and DONE summary through `SceneRemovals`.
Chain of Custody projects the source belt, machines, boxes, claw, bay, marking
highlight, machine-state labels, verdict, and DONE summary through
`SceneCustody`. Both display-list renderers are observational; timed
advancement and scoring occur only in their controllers.
N-Cup Monte projects the source cup row through `SceneNCupMonte`: visual slots
are rendered in slot order while cup labels and result colours follow the
controller's identity permutation. Reveal, shuffle, guess, and result messages
are selected from the controller phase; the scene never advances the swap clock,
changes the permutation, or computes the correct answer.
Reflex projects the source title, target counter, score line, footer, verdict,
and live target sprites through `SceneReflex`. Rendering is observational: it
does not expire targets, spawn targets, score clicks, or consume RNG. The
browser owns only the deterministic synthetic image pool; it never owns the
target list or the adaptive clock.
Moving Targets projects the source title, cue/tracking/picking instruction,
round status, ball positions, target highlights, picked marks, and verdict
through `SceneTracking`. Rendering is observational: it does not move balls,
select a ball, score a round, or consume RNG. Ball motion uses the same
source bounce helper and fixed reference coordinate system as the controller;
the browser only scales the resulting display list and schedules `advance`.
Lookout projects the source title, cue status, live cue glyph, drifting flock,
source footer, verdict, and feedback text through `SceneLookout`. Rendering is
observational: it does not morph a shape, mark a channel seen, score an answer,
select a cue, or consume RNG. The browser only scales the display list and
schedules `advance`; `F` and `J` are translated into the controller's FORM and
COLOR actions.
Pursuit projects the source title, round/status line, quarry, target field,
continuous score, result feedback, and footer through `ScenePursuit`. Rendering
is observational: it does not move the quarry, apply a pointer hit, update
on-target time, schedule a turn, or consume RNG. The browser scales the source
912×684 display list and supplies normalized pointer/keyboard events; the
controller alone converts them to source coordinates and owns the score.
Graph Mapping projects the source title/status, two independently ring-placed
graphs, divider, answer buttons, question text, and verdict through
`SceneGraphMapping`. On compact browser canvases, the shell asks the controller
for the original 640×480-point minimum layout (scaled by device-pixel ratio)
and then scales the complete display list into the available 4:3 canvas; this
keeps the source's fixed minimum controls proportional to the graphs. The
controller owns the balanced same/different deck,
graph-pair generation, actual equivalence truth, exposure hiding, 900 ms
feedback deadline, adaptive node count, score counters, and RNG stream. The
browser supplies only normalized keyboard/pointer events, monotonic time, and
display-list scaling. `nw_api_v1_graph_mapping_info` exposes additive timing,
option, score, and replay fields; `nw_api_v1_graph_mapping_value` exposes the
copied edge and ring-point values. The `really_same` field is a diagnostic
accessor for deterministic tests and is never included in the common state
envelope or used by the scene to reveal an answer.
Matrix Reasoning projects the source title, trial/level status, generated
matrix cards, missing-cell marker, numbered alternatives, feedback, source
explanation text, and DONE verdict through `SceneRavens`. The controller uses
the source `Ravens::generate` path, including its real figure geometry, rule
parameters, palette selection, and shuffled answer identity; it copies the
temporary panels into fixed run storage before returning them to the browser.
The browser route starts with source defaults (level 1, fifteen trials, no
exposure, adaptive scoring, feedback, explanation disabled, and colour
enabled), maps Space/Enter to start, 1–8 to answer, C to the source options
surface, and normalized pointer clicks through the same two-column choice
geometry. Exposure and feedback deadlines are advanced by the common clock,
and task replacement destroys the controller and timer. The common state
envelope deliberately omits the correct answer; additive diagnostics expose
figure/panel values for deterministic tests. The focused smoke covers seeded
generation/replay, real figure data, choice order, keyboard/pointer grading,
exposure/feedback boundaries, rendering, and idempotent cleanup. The browser
contract covers export wiring, task-hub placement, defaults, real rendering,
input routing, scheduling, and cleanup. The Stage0 and Stage1 source
differential sweeps cover the geometry, palette, layouts, rule families, and
whole-puzzle generator in 729 identical cases; the scene placement sweep also
matches 40 frames and 379 commands on both stages. The original options panel,
headed original-vs-port replays, and native Python/SDL3 adapters remain open.
Crossed Wires projects the source title/status, wrapped grid, target ring,
marker, optional grid lines, remaining-budget bar, and source verdict label
through `SceneCrossedWires`. The fixed-storage controller keeps the wiring,
drift turn, dead-port choice, target sequence, and source budget private. It
delegates deal and press semantics to `CrossedWires`, including the source
four/eight-key families, wrapped movement, wasted-press accounting, and
budget/target settlement; the common 12-field state exposes only the marker,
current target, goal count, and presses left. The browser maps the source's
WASD/arrow/letter/keypad controls to zero-based semantic ports, starts at the
source default rung 3 with five adaptive rounds and grid enabled, and destroys
the controller when leaving the task. The focused smoke and browser contract
tests cover seeded replay, hidden-wiring non-leakage, physical-port transport,
budget exhaustion, verdict rendering, completion, and idempotent cleanup.
The browser persists all four source settings and applies or cancels them from
the menu or task. Applying settings resets the run while preserving its random
stream. Python and SDL accept the same settings through validated startup flags;
their interactive settings dialog remains unimplemented. The additive
`nw_api_v1_crossed_wires_info` accessor exposes public counters and score
aggregates, with no wiring or dead-port field. The original UI and environment
replay compares key and port actions, adaptive climb/stay/drop, score, and the
800 ms verdict boundary against the promoted WASM controller.
Crossword uses the shared controller to load a clued TSV index and stably sort
entries by rank,
deal source puzzles, navigate and edit cells, and settle correct grids. The
browser stores an imported index locally and exposes the source level, grid
count, mistake marking, and adaptive settings. Python and SDL load an explicit index or
the standard local data path and accept the same settings as startup flags.
The index setter copies validated input into controller-owned storage; a missing
index leaves the task in its ready state with an explanatory message. SDL routes menu/direct entry, keyboard, and pointer events to the same controller.
Both native hosts provide an O-key options screen outside solving and share a
validated settings file across restarts. Explicit startup options take precedence.
Sudoku projects the source title, grade/technique prompt, immutable givens,
filled values, pencil masks, conflict washes, cursor, trial summary, solved
message, and DONE verdict through `SceneSudoku`. The controller uses the
source `Sudoku::generate`/rating path and copies each selected puzzle out of
temporary generation storage into fixed run arrays. Rejection-sampling deals
use a bounded temporary region per attempt so abandoned candidate grids do not
accumulate across the source's default rung budget or exhaust browser linear
memory. Common-v1 state exposes only public board metadata; the solution and
given/filled/mark arrays are available only through additive diagnostic
accessors for focused tests, never through the browser renderer. The browser
route defaults to rung 3, three trials, visible clashes, and adaptive scoring;
it persists the four source settings and opens their options screen from the
task menu or task screen. O always opens options; C opens them only below level
12, where C is not digit twelve. The browser maps arrows, 1–9/A–G, 0,
Backspace/Delete, N, and Space/Enter, and destroys the run on task replacement.
Python and SDL use the same source defaults, accept the four Sudoku settings as
validated startup flags, and map 1–9/A–G, erase keys, and N to the controller;
SDL also accepts Jigsaw settings. Native options are startup-only, not
interactive or persisted. The focused smoke covers seeded replay, immutable
givens, pencil/erase behavior, wrong-entry accounting, a real full solve,
verdict preservation, rendering, completion, and idempotent cleanup. The
original-source differential replays 186 `SudokuEnv.drive` ports through the
source UI and controller and compares generation, state, cells, pencil masks,
clashes, incorrect full-grid handling, score, and DONE. The browser contract
and headed options replay cover defaults, input, rendering, apply/cancel,
persistence, active-run preservation, and task exit. The Python 3.13 extension was rebuilt against the selected Stage1 runtime
object and passes the Marble lifecycle smoke, Sudoku host-options/key contract,
and direct Sudoku settings/start/frame/pencil/cleanup smoke. SDL was rebuilt
from the same source-fresh Stage1 product and its complete headless native
self-test matrix passes, including Sudoku, Jigsaw, and task-option parsing. The
full latest-Stage1 WASM artifact suite passed before promotion. A headed replay dispatched synthetic blur/hidden/visible/focus events and
confirmed state preservation. A native Chrome tab-strip switch away/back
preserved the complete public Sudoku state, and ArrowRight worked after
restoration. The automation-launched Chrome kept `document.visibilityState`
visible and emitted no blur/focus/visibilitychange events, so browser
lifecycle-event propagation remains open in this harness; see
`output/verification/sudoku-focus-check-20261109/`.
Mr. Time projects its title, source mode/rung/trial line, recall or produce
clock, target/response values, decimal answer buffer, verdict feedback, and
DONE summary through `SceneMrTime`. The controller owns the phase, timing,
answer parsing, tolerance, score, and adaptive state; the browser supplies
only monotonic time, keyboard/text/pointer events, and display-list scaling.
Fog of War projects the source's title/status, one painted fog rectangle,
revealed cells in ascending cell order, and the walker through the existing
`SceneFogOfWar` display list. Rendering is observational; a wall bump leaves
the display list byte-identical even though the move and bump counters advance.
Marble Maze returns
`ERR_UNSUPPORTED` for that operation because the physics-aware renderer is a
host service; the browser currently projects the live MuJoCo state through its
custom 3D canvas renderer, and original-source visual parity is still a fidelity
gap. `drain_effects` returns zero because the current controllers do not emit
host effects. `snapshot` and `restore(snapshot_pointer, snapshot_bytes)`
support Sokoban v2, Freeform Tetris v3, 3D N-Back v4, Monkey Ladder v5, and
Count v6.
New snapshots use little-endian fields, and restore allocates a fresh opaque
handle. Every snapshot begins with a little-endian 16-byte header (`NWR1`,
snapshot version, task ID, payload byte count). Sokoban v2 serializes options,
seed, MT19937 state, board arrays, run state, event ordering, and undo history.
Tetris v3 serializes its RNG, options, board/hand, placement/scoring state, and
event clock/order. N-Back v4, Monkey Ladder v5, and Count v6 payload layouts
are specified below. Legacy raw v1 remains restore-only same-build
compatibility. A future schema change must preserve its version meaning or
add a migration path before changing the format.
Tetris v3's payload is exactly 28,436 bytes. In order it contains the 624
little-endian u32 MT words and u32 cursor; i64 `cols`, `rows`, `start_rung`,
`rung`, `target`, `queue_size`, `phase`, `piece`, `score`, `selected`,
`quarter`, `column`, `row`, and `remainder`; the 2,304 row-major board cells;
the six-entry `queue_count`, `queue_fits`, and `queue_recut` arrays; the
384-entry slot-major `queue_x` and `queue_y` arrays; `active_count`; the
64-entry `active_x` and `active_y` arrays; `clean`, `buried`, `lines`,
`streak`, `slips`, and `best_rung`; then `slot_last_time`,
`slot_last_sequence`, and `slot_elapsed`. All array elements and scalar i64s
are little-endian i64 values. The 16-byte envelope is not included in that
payload size.
N-Back v4 has a fixed 1,800-byte payload of 225 little-endian i64 values.
In order: seed, N-back value, cube count, total trials, interval/stimulus/
feedback durations, trial index, trial start/deadline and current deadline,
paused remaining time, resume phase; 100 position-history values; 100
color-history values; phase, verdict, answered/paused/failed flags, hits,
misses, false alarms, correct rejections; then last event time, last event
sequence, and elapsed time. Restore validates option ranges, phase and flag
relationships, score bounds, history domains, and protocol clock/order.

Monkey Ladder v5 has a fixed 4,252-byte payload. It begins with all 624
little-endian u32 MT19937 words and the u32 cursor, followed by 100 sequence
cells and 100 clicked cells as little-endian i64 values. The remaining 19 i64
values are grid, start level, adaptive level, round level, reveal and per-tile
durations, sequence length, next and clicked indices, wrong cell, cursor cell,
deadline, phase, adaptive/reveal/cursor-enabled flags, then last event time,
last event sequence, and elapsed time. Restore validates RNG cursor, options,
booleans, array/cell bounds, unique dealt cells, phase/index consistency, and
protocol clock/order.

Count v6 has a variable payload: a 2,668-byte fixed portion plus 72 bytes per
active shape, up to 6,988 bytes. It begins with 624 little-endian u32 MT19937
words and the u32 cursor, followed by the shape-count i64. Each active shape
stores its kind and point count as i64, three x coordinates and three y
coordinates as f64, and its radius as f64. The fixed controller tail stores
the 17 i64 fields `kind`, `start_count`, `total_trials`, `exposure_ms`,
`adaptive`, `show_answer`, `count`, `shown_count`, `trial`, `correct`,
`total_error`, `answer`, `answer_length`, `phase`, `verdict`, `shown_at_ms`,
and `deadline_ms`; the final three i64 values are `slot_last_time`,
`slot_last_sequence`, and `slot_elapsed`. Floats are serialized by their
little-endian IEEE-754 bits. Restore validates exact size, RNG cursor, shape
count and geometry, options, answer/controller bounds, phase relationships,
and protocol clock/order.

The conformance smoke restores a live Sokoban move, compares public state and
frame, rejects mismatched history length, malformed booleans, an out-of-board
undo record, and a pushing phase without a board, then applies the same undo
action to both handles. It also restores a live Tetris hand, checks the schema
size and header, rejects an invalid MT cursor and phase, preserves event-order
metadata, and compares the next RNG-driven hand after a matching drop. It also
snapshots 3D N-Back
during its second active stimulus, compares restored state/frame, and
continues both handles through the same match, deadline, and next-trial path.
It checks exact payload versions/sizes, rejects invalid N-Back flags, and
continues both Monkey Ladder handles through the saved RNG-dealt answer after a
live pointer selection. Count checks exact dynamic size, malformed shape count
and non-finite geometry, restored state/frame, and identical RNG/adaptive
continuation. Other pointer-backed controllers remain explicitly
unsupported until they have field-level serializers. `destroy` disposes Sokoban's heap-backed undo
history and frees the controller record; it is safe to repeat for a retained
tombstone. The module is single-threaded; the registry is not a concurrent API.

The lifecycle must distinguish controller states as each game requires; do
not constrain every game to a shared three-state enum. A semantic action may
be ignored without changing state. Invalid handles, unsupported task IDs,
malformed options, and undersized buffers must fail explicitly and must not
trap or mutate another run.

### Handle and value rules

- A handle is opaque. Native shells use a native-width pointer or an integer
  table index; they must not assume pointers fit in WASM32 or in signed `i64`.
- WASM exports may carry a 32-bit linear-memory offset in an `i64` slot for
  toolchain ABI compatibility. Reject zero, out-of-memory, misaligned, and
  undersized handles before dereferencing. Never treat that representation as
  the native ABI.
- Use fixed-width signed integers only for bounded counts, timestamps, and
  enum values; booleans are `0` or `1`. Document every enum and field number
  next to its export. No magic sentinel may be overloaded as both a valid
  value and an error.
- Use monotonic integer nanoseconds or milliseconds per API version. A single
  API version must not mix epoch time, frame counts, and elapsed time.
- Strings are UTF-8 byte sequences with explicit lengths. No caller may infer
  capacity by scanning a non-terminated buffer.
- Each operation reports both status and output length (or uses an unambiguous
  zero/error convention that cannot collide with valid empty output).

## 3. Event and time contract

The common event schema must preserve the facts shells otherwise lose:

- key down and key up are separate; include logical key, physical code when
  relevant, modifiers, repeat, and monotonic timestamp;
- pointer move, button down/up, wheel, drag, and cancel are distinct, with
  normalized viewport coordinates and the active viewport/DPR mapping;
- text input and IME composition are separate from hotkeys;
- focus loss, visibility change, pause/resume, cancel, and task replacement
  are explicit lifecycle events.

Each controller documents which semantic actions it accepts and the exact
boundary rule. The host sends events in sequence-number order. At equal
timestamps, event sequence number is the tie-breaker; a controller must not
silently reorder a key/click and timeout. Replay cases must include one event
just before, exactly at, and just after each deadline.

`advance` receives logical time and elapsed active time separately. Pausing or
backgrounding must follow the original task's policy. Physics may subdivide a
large elapsed interval only when the original integration policy does so, and
must retain/account for any remainder rather than silently dropping it.

Current Monkey Ladder behavior is explicitly narrower: the browser owns a
monotonic millisecond clock and schedules a wake-up at the controller's
reveal deadline; `ACTION_TICK` changes SHOW to INPUT only when
`now_ms >= deadline_ms`. A selection received before that tick is ignored.
The host's event order therefore decides a same-timestamp race today; common
v1 replay ordering and original UI comparison remain open work.

## 4. State, frames, and effects

- Public state excludes unrevealed answers and other private grading data.
  Internal test-only reads must not be exposed through production UI or host
  services.
- Read-state and render are observational. Repeating either operation against
  unchanged state must return semantically identical output and must not
  consume RNG, move a timer, grade input, or emit an effect.
- Frame bytes live in the caller-owned output buffer. The shell must copy or
  consume them before that buffer is reused. After `memory.grow`, refresh every
  typed-array/DataView over WASM memory before reading or writing again.
- Effects (sound, persistence, media, engine requests) have stable IDs and a
  run-generation ID. They are drained once. A delayed host reply for a prior
  generation is ignored after restart, options change, or exit.
- Snapshots include schema version, task ID, options, phase, RNG state, logical
  clock state, and any task-owned progress required for exact continuation.
  Unsupported snapshots are reported, not approximated.

## 5. Ownership and cleanup

- The creator owns each run handle and releases it exactly once. `destroy` is
  safe to call more than once for the same still-known handle.
- A controller may retain only explicitly owned state across ABI calls. Do
  not store an arena-backed slice/string whose region ends at function return.
- Frame buffers, state allocations, per-run dynamic allocations, audio voices,
  physics model/data, timers, listeners, and pending callbacks each have an
  identified owner and teardown path.
- Reset, next run, options apply, menu exit, load failure, and application
  shutdown must release or reinitialize resources according to the original
  lifecycle. Generation IDs prevent late callbacks from writing to a new run.
- Tests must repeatedly open/play/exit/reopen and measure live allocations or
  equivalent ownership counters; JavaScript garbage collection is not proof
  that native or WASM allocations were released.

## 6. Existing provisional WASM ABIs

These are task-specific adapters, not the common v1 contract. Keep them stable
for current artifact tests; new task controllers should not copy their
differences without updating this document and the shared adapter design.

### Sokoban

- `nw_sokoban_run_init(run_ptr, start_rung, total_trials, adaptive,
  show_traps, seed)` initializes a host-owned fixed-layout run.
- `nw_sokoban_run_action(run_ptr, action, now_ms)` dispatches source-mapped
  semantic input. Action values are declared in `index.html` and
  `SokobanGame`.
- `nw_sokoban_run_info` and `nw_sokoban_run_cell` expose scalar state needed
  for status and board rendering; `nw_sokoban_run_frame_write` serializes the
  current scene. `nw_sokoban_run_dispose` releases controller-owned history.
- The current web host allocates 600,000 bytes once and reinitializes it for a
  new run. This is a tested host allocation, not a size-discovery ABI. Error
  validation and cross-shell wrappers remain open.

### Monkey Ladder

- `nw_monkey_ladder_run_init(run_ptr, grid, start_level, adaptive, show_ms,
  per_tile_ms, reveal_answer, seed)` initializes a fixed-layout run.
- `nw_monkey_ladder_run_action(run_ptr, action, value, now_ms)` supports
  START, TICK, SELECT, four cursor moves, and COMMIT. Exact integer values are
  the `ACTION_*` constants in `MonkeyLadderGame` and `MONKEY_ACTION` in the
  web adapter.
- `nw_monkey_ladder_run_info` fields and `nw_monkey_ladder_run_cell` kinds are
  declared in `MonkeyLadderGame`. The cell read is currently an internal/test
  ABI; production rendering uses `nw_monkey_ladder_run_frame_write` so hidden
  sequence state is not reconstructed in JavaScript.
- The current web host allocates 8,192 bytes once and initializes the source
  defaults (5×5, length 3, adaptive, 700 ms base + 280 ms per tile, reveal
  enabled, seed 1). Its controller has no heap-owned suballocations and thus
  no per-run disposer yet. Config UI/persistence, checked handle registry,
  native-width adapters, and Python/SDL integration remain open.

## 7. Migration and acceptance

1. Add explicit null/capacity/error checks to the provisional exports without
   changing valid task traces.
2. Introduce a versioned common handle registry and task dispatch table; retain
   provisional exports as compatibility wrappers until every shell migrates.
3. Add normalized event records and controller-level time advancement, then
   convert each web controller from direct task-specific ABI calls to v1.
   Monkey Ladder, Sokoban, Count, Marble Maze, and Tower of Hanoi have common-v1
   lifecycle controllers; the other task routes still use their legacy/generic path.
4. Add one-shot effect and snapshot protocols before tasks requiring audio,
   external engines, persistence, or resume are declared complete.
5. Migrate Sokoban, Monkey Ladder, Count, Marble Maze, and Tower of Hanoi as conformance
   examples; their v1 handle, option, ordering, state/frame buffer, unsupported
   snapshot, and disposal tests are in `test/runtime_protocol_v1_smoke.mjs`
   and the dedicated Count replay. The effect/stale-reply mutation tests
   remain required before API-001
   closes.
6. Implement native/Python and SDL adapters using native-width handles; run
   identical semantic replays through each shell.

API-001 remains open until v1 schemas and error codes are implemented, all
five current conformance tasks use them, and ownership/invalid-handle tests
pass. The
current task-specific ABI documentation is a migration aid, not a completion
claim.
