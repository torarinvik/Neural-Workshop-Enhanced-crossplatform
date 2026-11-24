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

The application artifact promoted on 2026-11-10 used the
source-fresh Elisa-compiler Stage1 product at commit
`d3b2e657d57c159c77b9523542f21fd67a93b916`, source fingerprint
`9de69658a554a61ac1679e3cd52398ea73800adf700fb0c51d7a636324dceef9`, product
SHA-256 `eaa65de1651631e703365e46a39ede6f1bcee123c3653755c368c59f51725f0f`.
That promoted `build/nwcore.wasm` was 1,629,226 bytes, SHA-256
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
| `cookie_thief` | `2851280360` | yes |
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
positive handle or a negative error. The options version is 1 for the table
below. The Jigsaw task ID also accepts version 2 for Video Jigsaw. The six
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
| Jigsaw Puzzle | starting side, 2–10 | puzzles per run | adaptive, 0/1 | preview, 0/1 | mark placed, 0/1 | requested pieces, at least 2, or 0 for side mode |
| Video Sequence | pieces per clip, 3–9 | clips per run, 1/3/5/8/12/20 | adaptive, 0/1 | mark placed, 0/1 | 0 | 0 |
| Hidden Rule | starting rung, 1/2/3/4/6/8/10/12/13/16/19/25/30 | rounds, 1/3/5/8/12 | adaptive, 0/1 | 0 | 0 |
| Hidden Wiring | starting rung, 1/3/5/7/10/12/16/20/25/30 | rounds, 1/3/5/8/12 | adaptive, 0/1 | 0 | 0 |
| Triage | starting rung | rounds | adaptive, 0/1 | stepped dials, 0/1 | 0 |
| Delay | starting rung | runs | adaptive, 0/1 | stepped dials, 0/1 | 0 |
| Notebook | starting rung, 1/3/6/8/12/16/20/25/30 | rounds, 1/3/5/8 | adaptive, 0/1 | 0 | 0 | 0 |
| Hold It | starting rung | holds | adaptive, 0/1 | stepped dials, 0/1 | 0 | 0 |
| Stop & Switch | starting rung | blocks | adaptive, 0/1 | stepped dials, 0/1 | 0 |
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
applied. The `e` slot carries `mark_placed`. A nonzero `f` selects the
Python piece-count grid and its adaptive progression. Photo Jigsaw caps the
board at 277×277 tiles and fits smaller photographs to their pixel dimensions.
Saved browser side settings are migrated
to their square piece count. The shell can
import the external DIV2K directory into IndexedDB, stores its unseen-photo
rotation across sessions, and renders the source tile crops and centered-square
preview. The coloured-tile fallback remains available when no photos are
imported.

Video Jigsaw uses the same slots with version 2 and requires a nonzero `f`.
Slot `f` accepts custom counts of at least two. The requested count selects
a 4:3 grid and its adaptive progression. Video grids fit the decoded
320×240 dimensions, with a maximum of 76,800 tiles. The 2,500-piece preset
fits a 58×44 grid of 2,552 tiles. Rendering emits a 4:3 board and preview
with sprite IDs for the source tiles. The preview retains ID 5500, and
tiles past index 2,499 use IDs 5501 through 79800. A host must supply
and play the clip for those sprites. Action `6` with zero value and auxiliary
fields returns an unloaded Video Jigsaw puzzle to the ready screen, restores
its pre-deal random state, and rolls back the puzzle number. This action is
accepted only before the clip-ready action has started the solve clock.

Video Sequence uses version 1 and the task ID `3061430628`. Space or action
`0` starts the run and enters loading phase `4`. After loading a clip at
15 frames per second, the host sends action `2` with its frame count in
the value field (3–120) or action `3` with zero value if loading fails.
The clip-ready action starts the solve clock and truncates any remainder
when it divides the clip into equal segments. Pointer input uses normalized
coordinates, and action `1` picks a zero-based tile position directly.
Advancing after the solve verdict enters loading for the next clip or ends
the run.

The scene emits sprite IDs `100000 + piece` for segments. The host can use
`nw_api_v1_video_sequence_source_frame(handle, piece, time_ms)` to resolve
the current frame index in the source clip. The fields accepted by
`nw_api_v1_video_sequence_info` and returned in the state payload, in order,
are phase, active pieces, clip number, clips per run, minimum swaps, actual
swaps, picked position, frames per segment, solve start time, and hovered
position.

Hidden Rule uses version 1 and task ID `189731380`. Action `10` starts
a run. Actions `0`–`5` cycle the corresponding builder properties, `6`
tests the object, `7` starts the exam, and `8` and `9` answer lit and
dark. Space and the keys 1–6 also work through the keyboard event path.
Pointer events pass normalized coordinates to the same scene hit testing
as the native task. The phase sequence is ready, testing, examining,
judged, and done. The info fields and state payload give phase, rung,
round number, rounds per run, tests, exam answers, revealed wrong answers,
rounds passed, highest rung passed, and the verdict deadline in milliseconds.
The wrong-answer count is revealed at judgment. The host advances at the
deadline to start the next round or show the score.

Hidden Wiring uses version 1 and task ID `462267443`. Actions `0`–`7`
toggle switches, `8` records a lamp observation, `9` starts the exam, `10`
submits the current switch settings, and `11` starts a run. Pointer input
uses the shared scene hit tests. The state payload reports phase, rung,
round number, rounds per run, observations, answers, revealed wrong
answers, rounds passed, highest rung passed, and the verdict deadline in
milliseconds. The host advances after the four-second verdict.

Triage uses version 1 and task ID `166983937`. Actions `0`–`7` open
cards, `8`–`15` swap neighboring digits, `16` ends the round, and `17`
starts a run. Space, the keys 1–8, and Enter map to the same actions.
Pointer events use the shared scene's card, swap, and Done hit tests.
The 12-field state reports phase (ready, playing, judged, finished),
current rung, round number, rounds per run, move budget, moves used,
payout, active card index (`-1` if none), rounds passed, highest rung
passed, verdict deadline in milliseconds, and the face-up card mask.
The task-specific info export also exposes the solved card mask as
field 12. The host advances after the 2.5-second verdict.
For the stepped environment, action `18` flags a playing round as out of
time. The controller shows a red verdict until the next advance, which
deals the next round without changing the rung or scored-round tally.
Phase `4` represents the flag, and task info field `13` reports the number
of rounds judged by their gameplay results.
With the stepped-dials option off, the starting rung must be one of
1/3/5/8/12/16/20/21/25/30 and the round count one of 1/3/5/8/12. With
it on, both accept signed 64-bit integers. Rungs below 1 start at rung
1 and nonpositive round counts finish immediately. Negative signed
seeds use their magnitude, as in Python.
The `nw_triage_options_note(dest, capacity, rung)` export writes the
UTF-8 starting-rung preview without a trailing NUL and returns its byte
length. The preview uses the same formatter as the native options menu.

Native Triage callers use `nw_triage_create(rung, trials, adaptive, seed)`
and release the returned handle with `nw_triage_destroy`. Creation
accepts stepped dials and returns zero on failure. `nw_triage_action`
and `nw_triage_advance` take caller-provided milliseconds and return
whether they changed the run. `nw_triage_info` uses the field order
above. Callers can write a display list with `nw_triage_frame_write`
or render tightly packed RGBA8 pixels with
`nw_triage_rgba_write(output, capacity, handle, black, width, height)`.
Both return a byte count or zero on failure. The RGBA writer uses an
offscreen SDL renderer and caller-owned memory.

Both native and WebAssembly stepped hosts configure the think bank with
`nw_triage_think_configure(handle, capacity_seconds, refill_seconds)`
before starting. `nw_triage_step(handle, elapsed_seconds)` charges the
bank during play, presents a timeout on expiry, and holds a scored
verdict for one stepped frame before dealing again. Each new deal
refills the bank up to capacity. `nw_triage_think_left` returns seconds
remaining and info field `14` counts forfeits. Hosts own the publication
of frames and action receipts when using those controller exports directly.

The native agent adapter handles that publication with
`nw_triage_agent_create`, `nw_triage_agent_act`,
`nw_triage_agent_publish`, and `nw_triage_agent_destroy`. Creation
takes the rung, rounds, adaptive flag, seed, think capacity and refill
in seconds, port count (at least 17), and neutral-outcomes flag.
The first publication draws the opening frame. Each subsequent call
advances one step and writes an NWFB header followed by tightly packed
RGBA8 pixels. Callers supply the buffer, dimensions, elapsed seconds,
and a monotonic timestamp in nanoseconds. An action returns its receipt
ID, or zero if rejected. Only one action may be finalized per open
receipt.

The publication metadata is an 80-byte header followed by two 64-byte
lowercase SHA-256 strings. In order, the header contains frame sequence,
timestamp, finished flag, open receipt ID, outcome receipt ID, outcome
scalar, action port, receipt frame sequence, receipt timestamp, and round
number. The scalar is a double and the other fields are signed 64-bit
integers. Receipt ID zero means absent and port `-1` means no action.
The strings identify the current frame and, for an outcome, the opening
stimulus. Callers retain historical frames for evidence verification.

The SDL build emits `libnw-agent.dylib` on macOS, `libnw-agent.so` on
Linux, or `nw-agent.dll` on Windows. Desktop packages stage the library
when it is available. The packaged declarations are in
`include/nw_triage_agent.h`. The library uses SDL and the Elisa runtime
and can be loaded by an agent host without Python.

Delay uses version 1 and task ID `1322381784`. Actions `0`, `1`, and
`2` take or give up, wait, and start, respectively. Space and the left
and right arrow keys use the same actions. Pointer events hit the
shared cards. Hosts advance the logical clock throughout active play
and the three-second verdict. The state reports phase, adaptive rung,
current run number, number of runs, offer mode, coins, zero-based offer
index, runs passed, highest rung passed, run start time, pause or
verdict deadline, and run duration. The last three fields are in
milliseconds. Rendering uses the most recent logical timestamp, and
hidden offer durations are absent from the state payload.

Interactive Delay accepts rungs 1/4/7/10/13/16/20/25/30 and run counts
1/3/5/10. The stepped-dials flag accepts signed 64-bit integers for those
two fields.

The browser agent uses `nw_delay_agent_event(handle, seconds, port)`
for its fractional-second clock. Ports `0` and `1` take or wait, port
`2` starts, and port `-1` advances a frame. The first tick that settles
a round displays the verdict. The next tick deals or finishes the run
without consuming the interactive three-second verdict delay.
Agent-managed and interactive-clock calls should use separate handles.

The native agent library exposes the same clocked task through
`nw_delay_agent_create(rung, trials, adaptive, seed, ports, neutral)`
and the matching `nw_delay_agent_act`, `nw_delay_agent_publish`, and
`nw_delay_agent_destroy` functions. Publish takes elapsed seconds and
returns the same NWFB payload and `NWAgentPublication` metadata as
Triage. Delay advances its own clock from elapsed seconds and has no
separate think bank.

Stop & Switch uses version 1 and task ID `1769824260`. Actions `0` and
`1` answer left and right, and `2` starts a run. Space and the left and
right arrow keys map to those actions. A primary pointer press starts an
idle run. Advance drives the cue, response window, stop ring, and
2.5-second verdict.

The state payload reports phase, adaptive rung, current block, configured
blocks, completed stimuli in the block, correct responses, correct-answer
bit mask, stimulus visibility, stop-ring visibility, rule, shape, and
colour. Rule, shape, and colour return `-1` until their visible cue.
Task-specific fields 12–16 expose the shown side, block length, blocks
passed, highest rung passed, and the verdict deadline in milliseconds.
The side field is `-1` for left or a hidden stimulus, distinguished by
the visibility field. Future stop signals are absent from public state.
Interactive rungs are 1/4/7/10/13/16/20/25/30 and block counts are
1/3/6/10/20. The stepped-dials flag accepts signed 64-bit integers.
`nw_stop_switch_options_note` writes the rung preview as UTF-8. The browser
maps F and J to the left and right actions and defaults to rung 1, six
blocks, and adaptive difficulty.

The browser exposes `createStopAndSwitchEnvironment(context, options)`.
Its `nw_stop_switch_agent_event(handle, seconds, port)` clock takes port
`2` to start, ports `0` and `1` for answers, and `-1` for a step without
an action. The first step that sees a verdict publishes it and the next
step deals or ends the run. Use separate handles for the interactive and
stepped clocks.

The native agent library exports `nw_stop_switch_agent_create`,
`nw_stop_switch_agent_act`, `nw_stop_switch_agent_publish`, and
`nw_stop_switch_agent_destroy` with the Delay agent signatures and
NWFB publication format. Both agents use fractional elapsed seconds and
two answer ports. The Stop & Switch default is six blocks.

Hold It uses version 1 and task ID `3702462192`. Action `0` presses the
key, `1` releases it, and `2` starts a run. Space starts and holds,
a primary click starts, and focus loss, tab hiding, or cancel release the
held input. Advance supplies the time for the model's clamped substeps.
The state reports phase, rung, trial, total, instruction kind, factor in
thousandths, lamp count, two lamp visibility flags, whether the turn to
hold has begun, whether the key is holding a lamp, and the result code.
Result codes are 0 pending, 1 pass, 2 too short, 3 too long, and 4 no hold.
Fields 12–15 report pass count, best rung, target milliseconds, and held
milliseconds. The durations return `-1` until a hold has been judged.
Interactive rungs are 1/4/7/10/13/16/20/25/30 and trial counts are
1/3/5/10/20. The browser defaults to rung 1, five holds, and adaptive
difficulty. `nw_hold_it_options_note` writes the selected rung preview.
`nw_hold_it_audio(handle, dest, capacity)` consumes elapsed audio in
at most one-second chunks. It returns the number of bytes written as
22,050 Hz stereo signed 16-bit little-endian PCM. A second read without
any elapsed model time returns zero. Each new hold resets the audio
cursor. The browser routes elapsed chunks to Web Audio and SDL queues
the trial's synthesised audio through FFI.

The browser's `createHoldItEnvironment` exposes one action port.
Sending port `0` holds for the next frame. Omitting it releases the key
on that frame. The clock advances through `nw_hold_it_agent_event`
with absolute seconds and port `0` for held, `-1` for idle, or `2`
to start. The first judged frame carries the verdict and the next
frame deals or ends the run. When audio elapsed, the observation includes
`audio_pcm`, `audio_rate`, `audio_channels`, and `audio_sample_width`.

The native agent library exposes `nw_hold_it_agent_create`,
`nw_hold_it_agent_act`, `nw_hold_it_agent_publish`, and
`nw_hold_it_agent_destroy` with the clocked agent signatures.
`nw_hold_it_agent_audio` copies and consumes elapsed PCM after a
successful publication. Its format matches the browser's audio.

Notebook uses version 1 and task ID `1307337504`. Actions 0–3
answer, 4–11 write to a line, 12 advances a fact card, and 13 starts.
Shift+1–8 writes, 1–4 answers, and Enter or N advances a fact card.
Space starts the run. Pointer hits use the same bounds as the display
list. The state reports phase, rung, round, total, zero-based card index,
card count, line count, answered count, correct count, last answer,
passes, and best rung. Fields 12–15 expose the displayed choices, field
16 gives the verdict deadline in milliseconds, and field 17 gives the
current card kind. Field 18 gives the think-clock forfeit count. Upcoming facts and correct answer indices stay
private. `nw_notebook_options_note` writes the selected rung preview.

The browser's `createNotebookEnvironment` exposes all 13 ports and an
optional think clock. Its stepped handle uses option slot 4 set to 1
and accepts signed trial counts and starting rungs up to 4096. The
controller bounds adaptive growth at 4096 to bound the size of the
noise-card sample. Configure the clock with
`nw_notebook_think_configure` before starting, pass elapsed seconds to
`nw_notebook_step`, and read the bank with `nw_notebook_think_left`.
A score or forfeit is visible for one publication before the next deal.

The native library exposes `nw_notebook_agent_create`,
`nw_notebook_agent_act`, `nw_notebook_agent_publish`, and
`nw_notebook_agent_destroy` with the Triage agent signatures and
NWFB frame format. Both hosts derive verdicts from the rendered frame.

Where Was It? uses version 1 and task ID `1679726570`. Actions 0–29
choose a floor cell during the test, 30 advances the study room, and
31 starts. Space starts or advances, Enter advances, and pointer hits
use the projected floor and solids in paint order. The state exposes
the phase, rung, trial, trial total, study stage, room count, floor
dimensions, chosen cell, and outcome counters. Future rooms and the
answer are private. Browser agents use `createWhereWasItEnvironment`
with 31 ports and the optional think clock. The WASM step calls are
`nw_where_was_it_think_configure`, `nw_where_was_it_step`, and
`nw_where_was_it_think_left`. The stepped handle sets option slot 4 to
1 to accept integer rungs and trial counts outside the interactive
options menu. `nw_where_was_it_options_note` writes the starting-rung
preview used by the Long-term memory menu. The native library exports
`nw_where_was_it_agent_create`, `nw_where_was_it_agent_act`,
`nw_where_was_it_agent_publish`, and `nw_where_was_it_agent_destroy`
with the Notebook signatures and NWFB frame format.

Same or Mirror? uses version 1 and task ID `2468745517`. Actions 0–4
choose the numbered answer, with 0 and 1 meaning Same and Mirror on
paired trials, and action 5 starts. The paired keyboard shortcuts
use key codes 20 and 9 in the common event ABI. The state reports the
figure count, cube count, lighting, chosen answer, and outcome counts
without exposing the correct port. Browser agents use five ports and
an optional think clock through `createSameOrMirrorEnvironment`.
The low-level clock calls are `nw_same_or_mirror_think_configure`,
`nw_same_or_mirror_step`, and `nw_same_or_mirror_think_left`. The native
agent library exposes `nw_same_or_mirror_agent_create`,
`nw_same_or_mirror_agent_act`, `nw_same_or_mirror_agent_publish`, and
`nw_same_or_mirror_agent_destroy` with the Notebook ABI and NWFB frames.

Which Is Nearer? uses version 1 and task ID `3493829017`. Actions 0–5
choose a visible solid by its numbered port, and action 6 starts.
A moving-eye trial uses the host's logical time for its sway. During
ordered trials a repeated choice is ignored, and the first wrong
choice settles the round. The answer order stays private until the
verdict. The browser's `createWhichIsNearerEnvironment` takes six
ports and a frame rate of at least 10 Hz. Its clock uses
`nw_which_is_nearer_agent_event(handle, seconds, port)` with port
−1 to advance. The interactive handle uses slot 4 set to 0 and the
agent sets it to 1 to accept integer dials outside the menu. Native
`libnw-agent` provides the same six-port clocked task through
`nw_which_is_nearer_agent_create`, `nw_which_is_nearer_agent_act`,
`nw_which_is_nearer_agent_publish`, and `nw_which_is_nearer_agent_destroy`
with the Delay ABI and NWFB frame format.

Point of View uses version 1 and task ID `2761162517`. Actions 0–4
choose pictures in reading order and action 5 starts. The map is a
visual cue. Public state includes the picture count, number of solids,
colour mode, and scored outcomes. The answer port remains private.
Browser agents use `createPointOfViewEnvironment` with five ports and
an optional think clock. WASM calls for that clock are
`nw_point_of_view_think_configure`, `nw_point_of_view_step`, and
`nw_point_of_view_think_left`. Native `libnw-agent` exports
`nw_point_of_view_agent_create`, `nw_point_of_view_agent_act`,
`nw_point_of_view_agent_publish`, and `nw_point_of_view_agent_destroy`
with the Notebook ABI and NWFB frames.

Inside or Out? uses version 1 and task ID `3450025504`. Actions 0 and 1
choose Inside/Yes and Outside/No. Action 2 starts the run. Public
information fields 4–6 contain the paired-dot flag, closed-line vertex
count, and number of decoys. The answer is private until feedback.
`createInsideOrOutEnvironment` and the native
`nw_inside_or_out_agent_*` exports provide two answer ports and an
optional think clock.

Touching? uses version 1 and task ID `4278212208`. Action 6 starts the
run. Actions 0–2 choose Apart, Touching, or Overlapping in the two-shape
mode. Actions 0–5 select a count in the touching-pairs mode. Information
fields 4–6 give the available choice count, shape count, and thick-outline
flag. The answer stays private until feedback.
`createTouchingEnvironment` and the native `nw_touching_agent_*`
exports provide a six-port stepped agent with an optional think clock.

Crossings uses version 1 and task ID `3322789258`. Action 7 starts the
run. Actions 0–6 submit crossing counts, with the maximum varying by
rung. Information fields 4–6 give the number of choices, red-line
point count, and decoy count. The crossing markers appear on the
judged frame. `createCrossingsEnvironment` and native
`nw_crossings_agent_*` exports provide seven stepped ports and an
optional think clock.

Time It uses version 1 and task ID `46880388`. Action 1 starts a run
and action 0 presses at the most recent simulation time. Fields 4–6
give the motion kind, elapsed milliseconds, and tolerance window.
Fields 7, 10, and 11 expose the result, the feedback deadline, and the
signed timing error during judgement. Browser and native agents use one
clocked port. They can read elapsed 22,050 Hz stereo S16LE PCM through
`nw_time_it_audio` and `nw_time_it_agent_audio`, respectively.

Juggler uses version 1 and task ID `178836257`. Action 2 starts an act.
Interactive actions 0 and 1 hold the left and right controls. Actions 3
and 4 release them, and action 5 clears both. Fields 4–6 expose time in
milliseconds, tray position in millimetres, and velocity in millimetres
per second. Agent ports 0 and 1 push for one frame, and the tray brakes
when an agent sends no action.

Balance uses version 1 and task ID `2560266987`. Action 2 starts a
course. Actions 0 and 1 hold the left or right push in interactive
sessions. Actions 3 and 4 release them, and action 5 clears both.
Fields 4–6 give elapsed milliseconds, cart position in millimetres,
and pole angle in microradians. Fields 11–13 give collected flags,
total flags, and the latest push direction. The browser and native
clocked agents treat ports 0 and 1 as pushes for a single frame.

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

Syllogism create options are level, trial count, disable-working,
disable-adaptive, use-invented-words, and zero. The three boolean switches are
zero by default, matching the source defaults of showing working, adapting, and
using real words. Actions 0–5 start, submit, or move the selection; action 6
selects and submits the zero-based option in `value`. The answer accessor is
hidden until judgment. Info fields 9–13 expose best correct level, the three
configured flags, and generation failure. Fields 14 and 15 expose total judged
time in whole seconds and the number of judged questions. The task-specific
value accessor fields 2, 3, and 4 expose each judged question’s level, correctness,
and elapsed milliseconds; unfinished questions have no result row. The source
changes require a fresh artifact before these fields and actions are available.

Numberology's twelve common fields are phase (`READY=0`, `WORKING=1`,
`JUDGED=2`, `DONE=3`), current level, trial, total trials, shown-term count,
answer, typed numeric value, typed digit count, verdict (-1/0/1), adaptive
flag, correct count, and rule complexity. The answer field is -1 until judgment;
its i64 fit flag is likewise hidden until judgment. The additive
`nw_api_v1_numberology_info` accessor exposes rule ID, complexity, next adaptive
level, exact-text lengths and fit flags. `nw_api_v1_numberology_value` returns
bytes for displayed terms and typed digits, and returns answer bytes only
after judgment. The term accessor returns displayed terms as i64 values.
Out-of-range legacy scalars return zero; exact decimal bytes avoid narrowing. Numberology actions 4 and 5 move
between visible pages; info fields 21–24 report the current page, total pages,
sequence pages, and revealed-answer pages. Answer pages exist only after an
incorrect judgment.

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
aggregate par/steps, elapsed whole seconds, message kind, and the number of
perfect solves at field `23`. `nw_api_v1_maze_cell(handle, field, cell)` returns wall and walked
flags or one-based door/key colour identifiers; out-of-board cells return 0.

Cookie Thief takes a level, round count, beat duration in milliseconds, setup
duration in milliseconds, adaptive flag, and a coaching flag. Set the coaching
flag to one for per-beat labels in an environment that pays dense outcomes.
SDL and web gameplay use zero. Actions
are start/next (`0`), grab (`1`), leave (`2`), lunge (`3`), and wait (`4`). Wait
leaves the simulation unchanged until the host advances the clock. Space or
Enter starts or advances, while Up, Down, and Right map to grab, leave, and
lunge. Each `advance` processes at most one phase transition or beat. The common
state includes phase (`READY=0`, `SETTING=1`, `RUNNING=2`, `SCORED=3`, `DONE=4`),
rung, round, total rounds, beat duration, setup duration, adaptive flag, beat
index, eaten cookies, caught count, verdict, and clean rounds. The additive
`nw_api_v1_cookie_thief_info` accessor also exposes points and the guessing
baseline at fields `12` and `13`. Field `14` is the coaching flag. Field `15`
reports the visible verdict as absent (`-1`), negative (`0`), or positive
(`1`). A round verdict overrides any coaching label on the final beat.

The options screen reads each row’s choices from `nw_cookie_thief_option_value`
and renders through `nw_cookie_thief_options_frame`. The frame includes the
400-round guessing estimate for the selected level. Applying options through
`nw_api_v1_cookie_thief_apply_options` is accepted on the ready and results
screens and resets the run while preserving the random stream.

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

### Public outcome pixel reader

`nw_public_outcome_read(rgba, bytes, width, height, output)` derives the
standard verdict scalar from a top-down RGBA framebuffer. It scans the bottom
quarter of the image, classifies occupied columns by feedback colour, and
joins same-colour runs across gaps shorter than `max(8, width / 40)`. Alpha
does not affect classification. The 32-byte output contains signed 64-bit
positive, negative, and oops label counts followed by a 64-bit floating-point
scalar. The scalar subtracts both negative and oops labels from positive labels
and divides by the total label count.

The result is `1` when labels are present, `0` when the selected band is
empty of labels, and `-1` for an invalid buffer or dimensions. Invalid calls
leave the output untouched. In WebAssembly, `rgba` and `output` are linear
memory addresses and the output requires eight-byte alignment. The native
export takes pointers to readable input and writable output. This entry point
reads pixels independently of receipt and frame archive verification.

`nw_public_frame_digest(input, bytes, output)` writes the SHA-256 digest of
the supplied bytes as 64 lowercase ASCII hex digits. The output has no
terminator. It returns `1` for success or `-1` for invalid input.
`nw_public_outcome_verify_frame(rgba, bytes, width, height, expected, scalar)`
returns `1` when the last evidence frame has the expected digest and yields
the supplied scalar, `0` for a mismatch or absent verdict, and `-1` for an
invalid buffer or dimensions. The caller supplies the full evidence buffer,
including alpha. The digest covers every supplied byte. These operations
verify the final frame. Checking earlier evidence frames and binding receipts
to an evidence sequence require the archive and ledger.

`nw_public_outcome_verify_evidence(rgba, bytes, width, height, evidence, count,
archive, receipt_id, receipt, scalar)` checks the ordered evidence and receipt
before verifying the final frame. `evidence` points to `count` consecutive
64-byte ASCII digests. `archive` points to `count` rows of two signed 64-bit
words, the archived frame address and byte length, in digest order. Address
zero denotes a missing frame. Pass a null archive for a single receipt-free
frame.

The host resolves the ledger lookup by receipt ID. Pass `-1` as the receipt
ID for a receipt-free outcome. The receipt row contains seven signed 64-bit
words in order:

1. Ledger lookup key
2. Stored receipt ID or `-1` if absent
3. Trial sequence or `-1` if absent
4. Stimulus digest address
5. Feedback digest address or zero if absent
6. Bound evidence list address or zero if absent
7. Bound evidence digest count

Each named receipt requires both an archive and a ledger record. The verifier
checks the stimulus, optional feedback, complete bound sequence when present,
and the original stored receipt ID and trial sequence rule. All archived frames
are hashed against their declared digests. The result is `1` for a verified
outcome, `0` for missing or mismatched evidence, and `-1` for invalid memory
ranges or malformed ABI input. The host owns archive and ledger storage and
validates external outcome object fields before marshalling the typed ABI.

The web runtime returned by `instantiateElisa` exposes
`verifyPublicOutcome(outcome, rgba, width, height, archive, ledger)`. It
accepts top-down RGBA byte arrays and archives and ledgers keyed by digest and
receipt ID as Maps or plain objects. It validates the public outcome fields,
marshals the evidence into WebAssembly memory, and frees the temporary
buffers after verification. It returns a boolean. The browser host supplies
the frame and owns the archive and receipt ledger.

The web runtime also exposes `createPublicFrameArchive(context)` for a 2D
canvas context. The shell binds its main context at
`window.__nw.createPublicFrameArchive()`. The host calls `capture()` after
drawing a significant frame. The result includes the backing-buffer
dimensions, top-down RGBA bytes, SHA-256 digest, sequence number, and
monotonic timestamp in nanoseconds. `get(digest)` returns a copy of archived
bytes. `verify(outcome, frame, ledger)` uses the private archive, and
`clear()` releases its entries. Receipts are supplied by the caller.

The archive's `createReceiptSession({ ports, drive, neutralOutcomes })` lets a
host bind a response to the rendered stimulus. Call `open()` after drawing
the stimulus, then call `act(port, logp)` to dispatch one zero-based action
through the synchronous driver. After the driver returns, call `publish()`
on rendered frames to capture evidence. By default the receipt settles on the
first frame with a readable verdict. With `neutralOutcomes` enabled, the first
published frame after the action can settle the receipt with a scalar of zero.
The generic archive verifier requires a readable pixel verdict for that
scalar. The task verifier described below can also verify a concession.
`getReceipt(id)` returns a copy of the receipt, and `verify(outcome, frame)`
checks it against the session ledger and archived pixels. `closeWindow()`
ends the current response window. `clear()` also removes the ledger and
archived frames.

`createCookieThiefEnvironment(context, options)` is available from the
instantiated runtime and from the web shell's `window.__nw` interface. Pass
a dedicated 2D canvas context. The stepped run starts immediately, uses a
virtual 60 Hz clock, and accepts zero-based grab, leave, lunge, and wait
ports. The default setup and beat durations use 16 ms to fit one virtual
tick at the controller's millisecond resolution. Call `observe()` to read
the current frame and `advance()` to tick and draw the next frame. The
`act(port, logp)`, `getReceipt(id)`, and `verify(outcome, frame)` methods
use the same receipt protocol as the archive. The following advance deals
from a scored frame. Call `close()` to release the controller and evidence.

Cookie Thief observations expose `frame_seq`, `timestamp_ns`, `width`,
`height`, `rgba`, and `done`, plus an `outcome` when one is published.
`step(ports)` returns the observation, queued events, and completion flag
as a three-element array. It drains the event queue, including the final
`run_end` event. A sparse verdict binds to the full round's evidence even
if the caller left its response window idle. `reset(seed)` clears that
run's receipts, evidence, events, and counters. `accounting.snapshot()`
reports trial, frame, outcome, and latency counters. The browser returns a
copy of every observation synchronously, so the dropped and duplicate frame
counters remain zero. Use `frameHz` to configure the virtual clock and
`runtimePorts` to configure the advertised action count. Extra ports are
accepted as inert actions in neutral-outcome mode.

The native and WebAssembly `nw_public_outcome_verify_task_evidence` export
takes the same arguments as `nw_public_outcome_verify_evidence`. It accepts a
zero concession on any valid frame with matching digests and receipt
evidence. Nonzero claims still require a matching pixel verdict. Browser
hosts can call `verifyTaskOutcome` on the instantiated runtime. Cookie
Thief uses this verifier, and its session requires the receipt to have
settled before accepting a claim. The generic verifier retains its
pixel-derived scalar rule for all claims.

Cookie Thief accepts an optional `frameExport` SharedArrayBuffer. Allocate
at least 36 bytes plus four bytes per canvas pixel and pass the same buffer
to the reader. Each published frame writes the Python NWFB version 1
header followed by top-down RGBA. The writer leaves the most recent frame
in the caller-owned buffer on close. The buffer is a one-way observation
channel. Readers must coordinate reads with completed publications when
they need a consistent snapshot. Browsers require a cross-origin isolated
page for SharedArrayBuffer use. Set `NW_WEB_SHARED_FRAMES=1` when running
`serve_web.sh` to enable the isolation headers on the local server.

The native and WebAssembly `nw_frame_export_header` export writes 36 bytes
to a caller-supplied destination. Its arguments after the destination and
capacity are unsigned 64-bit frame sequence and timestamp, unsigned 32-bit
width and height, and the consumed flag. It returns 36 on success and -1
for an invalid destination. Cookie Thief publishes frames with the consumed
flag clear, matching the Python environment, and rejects positive
`thinkSeconds` because the task already has its own clock.

Native hosts can call `nw_frame_shared_create(name, capacity)` to create a
named NWFB mapping and receive an opaque owner handle. The name uses UTF-8
and the capacity includes the header and pixel bytes. Creation returns
zero if the name is occupied or the OS cannot allocate the mapping.
`nw_frame_shared_publish(handle, sequence, timestamp_ns, width, height,
pixels, bytes, consumed)` copies a tightly packed top-down RGBA frame and
returns the bytes written, or -1 for invalid dimensions or capacity.
`nw_frame_shared_release(&handle)` releases ownership and clears the
handle. POSIX release unlinks the name, and a Windows mapping persists
until the last process releases its view and handle. Callers coordinate
reads and choose a capacity large enough for the frames they will publish.

Set `NW_SHM` to a free shared-memory name to publish desktop SDL frames.
The desktop reads back the rendered pixels before presentation and
publishes a sequence number and SDL monotonic timestamp with each frame.
The mapping is released when its renderer closes. If the framebuffer grows
beyond the allocation, a reader must reattach to the replacement mapping.
On Windows, an attached reader must close its old view before a replacement
can use the same name. A failed mapping creation is logged and leaves the
desktop running.

Marble Maze composites its WebGL stage into the main 2D canvas before
archive capture. For a graphical archive check, open the web shell in a
headless Playwright session with `marble-test-hooks=1` and
`marble-test-freeze-clock=1`, then pass
`test/marble_frame_archive_browser_replay.js` to Playwright CLI
`run-code --filename`. The replay compares archived stage pixels to the
WebGL canvas and recomputes the archived frame's SHA-256.

For a Linux graphical desktop check, run
`test/sdl_marble_shared_frame_x11_test.py` under `xvfb-run` with a
MuJoCo-enabled desktop binary as its argument. The replay uses Python 3.13
or later, X11, and XTest. It starts a tray, reads the composited stage
through NWFB, and checks that normal quit releases the named mapping.


### Lander

Lander uses task ID `2771681963`. Create options 0–2 select the
starting rung, landings per run, and adaptive difficulty. Up, Left, and
Right take key-down and key-up events. Focus loss and cancellation
clear held controls. Agent ports 0–4 fire, turn left, turn right, fire
while turning left, and fire while turning right for one frame.

`nw_api_v1_lander_info` exposes phase, rung, trial, total, flight time
in milliseconds, position in millimetres, verdict, landings passed,
highest rung passed, verdict deadline in milliseconds, velocity in
millimetres per second, tilt in degrees, remaining fuel in milliseconds
(`-1` for unlimited), and whether the engine is firing. Outside the
relevant phase, verdict and deadline read as `-1`.


### Keep the Beat

Keep the Beat uses task ID `4282310537`. Create options 0–2 select
the starting rung, songs per run, and adaptive difficulty. Agent
port 0 taps at the last published model time. `nw_beat_audio`
reads elapsed stereo signed 16-bit little-endian PCM at 22,050 Hz.

`nw_api_v1_beat_info` exposes phase, rung, song number, total,
silent beat count, elapsed milliseconds, scoring window in
milliseconds, verdict, songs passed, highest rung passed, verdict
deadline in milliseconds, tap count, curtain state, hits, stray
taps, and song end in milliseconds, in field order 0–15.


### Shadow Play

Shadow Play uses task ID `2286122724`. Create options 0–2 select
the starting rung, trials per run, and adaptive difficulty. Option 3
enables agent dials, which accept any positive rung and trial count.

`nw_shadow_play_advance(handle, seconds, held)` takes an absolute clock
in seconds and a six-bit held-control mask. From bit 0 to bit 5 the
controls turn left, turn right, pitch down, pitch up, roll left, and
roll right. The same order applies to the six agent ports in
`nw_shadow_play_agent_event`. Port 6 starts and port -1 advances one
agent frame. Use separate handles for interactive and agent clocks.

`nw_shadow_play_drag(handle, dx, dy, roll)` takes deltas in reference
canvas coordinates with positive y upward. Set `roll` to 1 for roll
and 0 for turn and pitch. `nw_shadow_play_audio` reads elapsed stereo
signed 16-bit little-endian PCM at 22,050 Hz.

`nw_api_v1_shadow_play_info` exposes phase, rung, trial, total trials,
elapsed milliseconds, fit per thousand, available axes, verdict,
trials passed, highest rung passed, verdict deadline in milliseconds,
fit start in elapsed milliseconds, and floor shadow, in field order
0–12.

The native agent library provides `nw_shadow_play_agent_create`,
`nw_shadow_play_agent_act`, `nw_shadow_play_agent_publish`,
`nw_shadow_play_agent_audio`, and `nw_shadow_play_agent_destroy`.
Its first publication opens the initial trial without advancing its
clock. Subsequent publications take elapsed seconds and return a frame
and receipt metadata using the native agent ABI.

### Captcha

Captcha uses task ID `1314221109`. Create options 0–2 select the starting
rung, trials, and adaptive difficulty. Option 3 enables unrestricted
positive rung and trial dials. Action ports 0–22 type
`ACDEFGHJKMNPQRTUVWXY347` in order. Port 23 erases, port 24 submits,
and port 25 starts. Common advance uses the interactive 2,500 ms feedback
deadline.

`nw_api_v1_captcha_info` exposes phase, rung, trial, total trials, typed
length, verdict, passed count, highest rung passed, feedback deadline
in milliseconds, and forfeits, in field order 0–9. The answer is present in the verdict
frame when the trial settles. The scene carries clockwise glyph rotation
in the text command's `e` field and the one-based typeface slot in `f`.

The stepped browser environment uses the same action ports.
`nw_captcha_think_configure` configures the bank before start.
`nw_captcha_step` consumes elapsed seconds while the trial is open
and publishes one frame of the verdict before dealing again. A forfeit
uses phase 4, displays “Out of time”, and leaves the rung and graded
answer count unchanged. The clock refills after the new deal is
published. `nw_captcha_think_left` returns the remaining seconds.
Use separate handles for stepped and interactive clocks.

The native agent library exposes `nw_captcha_agent_create`,
`nw_captcha_agent_act`, `nw_captcha_agent_publish`, and
`nw_captcha_agent_destroy`. The first publication opens the receipt
without charging elapsed time. Native agent frames use SDL's rotated
bitmap glyphs.

### Signals

Signals uses task ID `3284569614`. Create options 0–2 select the starting
rung, games per run, and adaptive difficulty. Ports 0–7 pick an object,
ports 8–15 send a glyph, and port 16 starts or restarts a run. An exchange
with a two-glyph message settles after the second glyph. Advance observes
the 2,800 ms result deadline.

`nw_api_v1_signals_info` exposes phase, rung, trial, configured games,
completed exchanges, verdict, games passed, highest rung passed, feedback
deadline in milliseconds, understood exchanges, total exchanges, and role
in fields 0–11. Role 0 is listening and role 1 is speaking. The display list
shows the partner's message or the player's target and partial message.
SDL uses screen 83 for `--screen signals` and exposes the same fields
in `--dump`.

The stepped Signals environment uses 16 action ports and starts the run
automatically. Configure the bank before starting with
`nw_signals_think_configure`. `nw_signals_step` publishes one verdict
frame and then deals the next game. A think-clock forfeit paints
“Out of time,” consumes one game, and leaves the rung unchanged.
Field 12 counts forfeits and `nw_signals_think_left` returns the
remaining bank in seconds. The browser runtime exposes
`createSignalsEnvironment`. The native agent library exposes
`nw_signals_agent_create`, `nw_signals_agent_act`,
`nw_signals_agent_publish`, and `nw_signals_agent_destroy`.

### Fold It

Fold It uses task ID `3561462226`. Create options 0–2 select the starting
rung, nets per run, and adaptive difficulty. Option 3 enables positive
integer dials beyond the interactive options menu. Ports 0–5 choose
answers and port 6 starts or restarts the run. Interactive advance
observes the 2,500 ms feedback deadline.

`nw_api_v1_fold_it_info` exposes phase, rung, trial, total, choice count,
net index, revealed answer, chosen answer, pass verdict, passed count,
highest rung passed, scored count, forfeits, and deadline in fields
0–13. The revealed answer is available after grading.

The browser’s `createFoldItEnvironment` uses the same six answer ports.
Configure its bank with `nw_fold_it_think_configure` before starting.
`nw_fold_it_step` retains the verdict for one publication and then
deals the next net. `nw_fold_it_think_left` reports the remaining bank
in seconds. SDL uses screen 84 for `--screen fold-it` and exposes the
same fields in `--dump`. The native library exposes
`nw_fold_it_agent_create`, `nw_fold_it_agent_act`,
`nw_fold_it_agent_publish`, and `nw_fold_it_agent_destroy`.

### Who Knows What?

Who Knows What? uses task ID `163698951`. Create options 0–2 select the
starting rung, stories per run, and adaptive difficulty. Option 3 enables
positive integer dials beyond the interactive options menu. Ports 0–3
choose answers and port 4 starts or restarts the run. Interactive advance
uses the 2,500 ms feedback deadline.

`nw_api_v1_who_knows_what_info` exposes phase, rung, trial, total, choice
count, panel count, revealed answer, chosen answer, pass verdict, passed
count, highest rung passed, scored count, forfeits, and deadline in fields
0–13. The answer is available after grading.

The browser’s `createWhoKnowsWhatEnvironment` starts automatically.
`nw_who_knows_what_think_configure` configures the bank before start,
`nw_who_knows_what_step` advances the stepped controller, and
`nw_who_knows_what_think_left` reports the remaining seconds.
With a think clock, a timeout consumes the story without changing
the rung or the graded answer count. SDL uses screen 85 for
`--screen who-knows-what` and exposes the same fields in `--dump`.
The native library exposes `nw_who_knows_what_agent_create`,
`nw_who_knows_what_agent_act`, `nw_who_knows_what_agent_publish`,
and `nw_who_knows_what_agent_destroy`.

### Sonar

Sonar uses task ID `3424761748`. Create options 0–2 select the
starting rung, rounds per run, and adaptive difficulty. Option 3
enables positive integer dials outside the interactive choices.
Options 4 and 5 are zero.

Action ports 0–3 move the cursor up, down, left, and right. Port 4 pings,
port 5 digs, and port 6 starts or restarts. Arrow keys move the cursor.
P and Space ping during a round, and D and Enter dig. P and D use logical
key codes 32 and 33. A primary board press pings. A secondary press or
Shift-primary press digs. The controller advances after 1,800 ms of
feedback.

`nw_api_v1_sonar_info` fields 0–14 return phase, current rung, round
number, total rounds, board side, cursor cell, actions used, cost,
twice par, passes, best rung passed, last pass flag, feedback deadline
in milliseconds, elapsed trial milliseconds, and forfeits. Cells are numbered
from the top-left in row-major order. The pass flag and elapsed time
are available after judgment, and the deadline is available during
feedback. `nw_sonar_options_note` writes the source option preview as
UTF-8.

SDL uses screen 87 for `--screen sonar` and exposes the same fields
in `--dump`. It reads `SONAR_RUNG`, `SONAR_TRIALS`, and
`SONAR_ADAPTIVE` from the profile and saves edits to the profile's
`.sonar-options` sidecar.

The browser's `createSonarEnvironment` starts automatically with six
action ports. `nw_sonar_think_configure` sets the optional bank before
start, `nw_sonar_step` advances one publication, and
`nw_sonar_think_left` reports seconds remaining. A timeout publishes
one red verdict frame and consumes a round. The rung and scored-round
count stay as they were before the timeout. The next round refills the
bank up to capacity.

The native library exports `nw_sonar_agent_create`,
`nw_sonar_agent_act`, `nw_sonar_agent_publish`, and
`nw_sonar_agent_destroy`. The publish call returns the standard
receipt and frame packet and supports the 24×24 board.

### Dispatch

Dispatch uses task ID `2857709163`. Create options 0–2 select starting
rung, rounds per run, and adaptive difficulty. Option 3 permits positive
integer rung and round counts outside the interactive choices. Option 4
enables per-incident coaching for stepped callers using option 3. Option 5
is zero.

Action ports 0–3 select a unit, 4–11 target incidents, 12–14 target
stations, 15–17 target refits, and 18 starts or restarts. Logical
key codes 35–42 represent A–H, and 43–45 represent J/K/L. The Shift
modifier changes a station order into a refit. Pointer targets use the
same coordinates, and clicking away from every target clears selection.

`nw_api_v1_advance` takes elapsed active milliseconds. Running rounds
advance in 50 ms simulation steps with carry between calls and a
250 ms cap per call. Judgment uses a 2,200 ms logical deadline.
`nw_dispatch_options_note` writes the starting-rung description as
UTF-8. The web shell saves options under `nw.dispatch.options.v1`
and accepts a non-negative signed 64-bit `dispatch-seed` URL parameter.

SDL assigns screen 89 to `--screen dispatch` and includes it after Sonar
in Decisions. Space starts or restarts a run. Keys 1–4 select units,
A–H target incident slots, J/K/L target stations, and Shift+J/K/L
target refits. Mouse orders follow the map hit targets and use the
same station modifier.

SDL reads `DISPATCH_RUNG`, `DISPATCH_TRIALS`, and
`DISPATCH_ADAPTIVE` from the profile and saves edits in its
`.dispatch-options` sidecar. The WASM state packet,
`nw_api_v1_dispatch_info`, and SDL `--dump` fields are phase,
current rung, round number, total rounds, selected unit, open reports,
reports seen, rounded damage, passes, best rung passed, starting rung,
and adaptive flag. The selected unit is `-1` when the selection is clear.
The task-specific WASM info export also reports the active coaching cue
at field 12. It returns 0 without a cue, 1 for a save, and 2 for a loss.

`createDispatchEnvironment` exposes the 18 agent ports. The town advances
with every step, including an idle step. `nw_dispatch_agent_event` takes
absolute virtual seconds, with port `-1` for a tick. A judgment paints one
frame before the next step moves on to the following round or completion.
The browser and native agent hosts enable coaching only with neutral
outcomes and the coach option. They derive event and round rewards from
the painted verdict and attach them to the action's receipt.

The native library exports `nw_dispatch_agent_create`,
`nw_dispatch_agent_act`, `nw_dispatch_agent_publish`, and
`nw_dispatch_agent_destroy`. The constructor accepts the starting rung,
round count, adaptive flag, seed, runtime port count, neutral-outcomes
flag, and coach flag.

### Gamble

Gamble uses task ID `816838233`. Create options 0–2 select starting rung,
rounds per run, and adaptive difficulty. Option 3 permits positive integer
rungs and round counts beyond the interactive choices. Options 4 and 5
are zero.

Ports 0–7 pull the corresponding machine, port 8 stops a paid round, and
port 9 starts or restarts. Keyboard controls use Space, digits 1–8, and
S. The logical key code for S is 34. A primary press starts from the
ready or finished screen, or activates a machine or Stop during play.
Judgment advances after 3,000 ms.

`nw_api_v1_gamble_info` fields 0–10 return phase, current rung, round number,
total rounds, pulls used, net coins, passes, best rung passed, starting rung,
the adaptive flag, and think-clock forfeits. The state packet carries the
same values in its first eleven fields.
`nw_gamble_options_note` writes the starting-rung description as UTF-8.

The web shell stores options under `nw.gamble.options.v1` and accepts a
non-negative signed 64-bit `gamble-seed` URL parameter for replay. SDL
assigns screen 88 to `--screen gamble`, exposes fields 0–9 in `--dump`,
and reads `GAMBLE_RUNG`, `GAMBLE_TRIALS`, and `GAMBLE_ADAPTIVE` from the
profile. It saves edits in the profile's `.gamble-options` sidecar.

The browser's `createGambleEnvironment` starts automatically with nine
action ports. `nw_gamble_think_configure`, `nw_gamble_step`, and
`nw_gamble_think_left` expose the stepped clock. Each forfeit paints one
red verdict frame, consumes a round, and leaves the rung and scored-round
count unchanged. The next round refills the clock up to capacity.

The native library exports `nw_gamble_agent_create`,
`nw_gamble_agent_act`, `nw_gamble_agent_publish`, and
`nw_gamble_agent_destroy`. Publication returns the shared frame format
and the receipt that identifies the action or expired response window.

### Bluff

Bluff uses task ID `3952940662`. Create options 0–2 select the starting
rung, rounds per run, and adaptive progression. Option 3 permits the agent
interface to use positive rungs and round counts outside the interactive
choices. Options 4 and 5 are zero.

Action ports 0 and 1 select the passive and aggressive moves. Port 2
starts or restarts. The browser maps the original keyboard shortcuts
to logical keys 12 and 13, accepts only primary pointer presses, and
stores options under `nw.bluff.options.v1`. Use `bluff-seed` to replay a
non-negative signed 64-bit seed.

SDL assigns screen 90 to `--screen bluff` and lists it in Decisions.
Press Space or click to start or restart. During play, 1, K, or F chooses
the passive action, and 2, B, or C chooses the aggressive action. A primary
click activates the visible action button. Round feedback lasts 3,000 ms.

C opens options from the ready or finished screen. SDL reads `BLUFF_RUNG`,
`BLUFF_TRIALS`, and `BLUFF_ADAPTIVE` from the profile and saves edits in its
`.bluff-options` sidecar. The `--dump` fields 0–9 give the phase, current
rung, round number, total rounds, completed hands, chips, passes, best rung
passed, starting rung, and adaptive flag.

The WASM state packet and `nw_api_v1_bluff_info` include a forfeit count
in field 10. `createBluffEnvironment` starts automatically and exposes
two ports. `nw_bluff_think_configure`, `nw_bluff_step`, and
`nw_bluff_think_left` drive its think clock. An expired clock publishes
one red verdict frame, consumes the round, and leaves the rung unchanged.
Starting the next round refills the clock up to capacity.

The native library exposes `nw_bluff_agent_create`, `nw_bluff_agent_act`,
`nw_bluff_agent_publish`, and `nw_bluff_agent_destroy` through the shared
frame and receipt protocol.

### Explore or Exploit

Explore or Exploit uses task ID `3798735432`. Create options 0–2 select
the starting rung, runs, and adaptive progression. Option 3 allows agent
sessions to use positive rungs and run counts outside the interactive
choices. Options 4 and 5 are zero.

Ports 0–7 pull the corresponding machine. Ports beyond the current
machine count leave the deal unchanged. Port 8 starts or restarts.
The desktop and browser accept Space, digits 1–8, and primary clicks.
Batch rounds reveal pending coins and machine history every five pulls.
The desktop and browser advance from the verdict after 3,000 ms.

SDL assigns screen 91 to `--screen explore-exploit`. It reads
`EXPLORE_EXPLOIT_RUNG`, `EXPLORE_EXPLOIT_TRIALS`, and
`EXPLORE_EXPLOIT_ADAPTIVE` from profiles and stores edits in the
`.explore-exploit-options` sidecar. The browser stores options under
`nw.explore_exploit.options.v1` and accepts an `explore_exploit-seed`
query parameter. Applying options preserves the current random stream.

State fields 0–9 give the phase, current rung, run number, total runs,
pull count, revealed coins, passes, highest rung passed, starting rung,
and adaptive flag. The WASM info export and state packet also give the
forfeit count in field 10.

`createExploreOrExploitEnvironment` starts automatically with eight ports.
Its think clock publishes one red verdict when it expires, consumes the
run, and refills up to capacity on the next deal. The native library exports
`nw_explore_exploit_agent_create`, `nw_explore_exploit_agent_act`,
`nw_explore_exploit_agent_publish`, and `nw_explore_exploit_agent_destroy`
through the shared frame and receipt protocol.

### Firebreak

Firebreak uses task ID `2288460636`. Create options 0–2 select the starting
rung, fires per run, and adaptive progression. Option 3 permits positive
rungs and run counts outside the interactive choices for agent sessions.
Options 4 and 5 are zero.

Ports 0–3 move the cursor up, down, left, and right. Port 4 digs. Ports
5–8 move four cells in those same directions. Port 9 starts or restarts.
Interactive ports 10–579 place the cursor on a row-major board cell and
attempt a dig. Shift-arrow moves four cells. Space starts from the ready
or finished screen. Space, Enter, and board clicks dig during play.

SDL assigns screen 92 to `--screen firebreak`, reads the Python profile's
`FIREBREAK_RUNG`, `FIREBREAK_TRIALS`, and `FIREBREAK_ADAPTIVE` values,
and saves edits in its `.firebreak-options` sidecar. The browser stores
options under `nw.firebreak.options.v1` and accepts a `firebreak-seed` query
parameter. Applying options preserves the current random stream.

State fields 0–11 give the phase, current rung, round number, total rounds,
cursor column and row, shovels, verdict, passes, highest rung passed,
starting rung, and adaptive flag. The verdict is zero during play, one
for a burned town, two for a saved town, and three for timeout.

`createFirebreakEnvironment` starts automatically with nine ports.
`nw_firebreak_agent_event` advances the fire on port −1 and accepts the
nine crew actions between ticks. The native library exposes
`nw_firebreak_agent_create`, `nw_firebreak_agent_act`,
`nw_firebreak_agent_publish`, and `nw_firebreak_agent_destroy`.

### Crossroads

Crossroads uses task ID `601803310`. Create options 0–2 select the
starting rung, shifts per run, and adaptive progression. Option 3
permits positive rungs and trial counts outside the interactive choices
for agent sessions. Options 4 and 5 are zero.

Ports 0–3 request a light switch at the corresponding junction. Port
4 starts or restarts the run. Interactive players use Space to start
and number keys 1–4 or a junction click to switch its lights. The
interactive clock clamps elapsed time to 100 ms and subdivides it into
steps no larger than 1/60 s. A verdict stays visible for three seconds.

SDL assigns screen 93 to `--screen crossroads`, reads
`CROSSROADS_RUNG`, `CROSSROADS_TRIALS`, and `CROSSROADS_ADAPTIVE`
from the selected profile, and saves edits to `.crossroads-options`.
The browser stores options under `nw.crossroads.options.v1` and
accepts a `crossroads-seed` query parameter.

State fields 0–11 give the phase, current rung, shift number, total
shifts, active cars, processed arrivals, served cars, verdict, wins,
highest rung passed, starting rung, and adaptive flag. The verdict is
zero during play, one for a clear shift, two for gridlock, and three
for an ambulance held up.

`createCrossroadsEnvironment` starts automatically with four ports.
`nw_crossroads_agent_event` advances on port −1 and accepts light
switch requests between ticks. The native library exposes
`nw_crossroads_agent_create`, `nw_crossroads_agent_act`,
`nw_crossroads_agent_publish`, and `nw_crossroads_agent_destroy`.

### Rail Yard

Rail Yard uses task ID `3428277734`. Create options 0–2 select the
starting rung, yards per run, and adaptive progression. Set option 3
to one to use positive rungs and trial counts outside the interactive
choices. Options 4 and 5 are zero.

Ports 0–14 throw the points numbered 1–15. Ports 15–16 toggle the
two tunnel signals. Available controls depend on the yard layout.
Port 17 starts or restarts. Interactive players can press 1–9 for
points, Q or W for signals, or click any point or signal. The
interactive clock clamps frames to 100 ms, splits them into
simulation steps no longer than 1/60 s, and advances after three
seconds of verdict feedback.

SDL assigns screen 94 to `--screen rail-yard`. It reads
`RAILYARD_RUNG`, `RAILYARD_TRIALS`, and `RAILYARD_ADAPTIVE`
from the selected profile and writes `.railyard-options`. The
browser stores options under `nw.railyard.options.v1` and accepts
a `rail-yard-seed` query parameter.

State fields 0–11 report the phase, current rung, yard number,
yards per run, scheduled trains, trains that reached a station,
trains home, verdict, passing yards, highest rung passed, starting
rung, and adaptive flag. Verdict values 0–6 represent play in
progress, a pass, a routing loss, a failed timeout, derailment,
collision, and a passing timeout. The finished screen keeps the
last verdict visible.

`createRailYardEnvironment` starts with 17 action ports.
`nw_railyard_agent_event` accepts actions between clock ticks and
advances time on port −1. The native library exposes
`nw_railyard_agent_create`, `nw_railyard_agent_act`,
`nw_railyard_agent_publish`, and `nw_railyard_agent_destroy`.

### Air Traffic

Air Traffic uses task ID `3001039441`. Create options 0–2 select the
starting rung, skies per run, and adaptive progression. Option 3
permits positive rungs and trial counts outside the interactive
choices. Options 4 and 5 are zero.

Ports 0–7 select aircraft slots. Ports 8–11 order hold, left, right,
and land. Port 12 starts or restarts. Interactive players select
with 1–8 or click an aircraft, hold with H, turn with A/D or the
arrow keys, and land with L or by clicking the selected aircraft’s
assigned runway. The interactive clock clamps frames to 100 ms and
splits them into steps no longer than 1/60 s. Verdict feedback lasts
three seconds.

SDL assigns screen 95 to `--screen air-traffic`. It reads
`AIRTRAFFIC_RUNG`, `AIRTRAFFIC_TRIALS`, and `AIRTRAFFIC_ADAPTIVE`
from the profile and saves edits to `.airtraffic-options`. The
browser stores options under `nw.airtraffic.options.v1` and accepts
the `air-traffic-seed` query parameter.

State fields 0–11 report phase, current rung, sky number, skies per
run, scheduled aircraft, aircraft aloft, aircraft landed, verdict,
passes, highest rung passed, starting rung, and adaptive flag.
Verdict values 0–6 represent play in progress, a clear sky, timeout,
fuel loss, airspace loss, storm loss, and collision.

`createAirTrafficEnvironment` starts with 12 ports.
`nw_airtraffic_agent_event` accepts orders between ticks and advances
time on port −1. The native library exposes
`nw_airtraffic_agent_create`, `nw_airtraffic_agent_act`,
`nw_airtraffic_agent_publish`, and `nw_airtraffic_agent_destroy`.

### Escort

Escort uses task ID `3128828853`. Create options 0–2 select the
starting rung, temples per run, and adaptive progression. Option 3
permits positive rungs and trial counts outside the interactive
choices. Options 4 and 5 are zero.

Ports 0–5 pull the corresponding lever when present. Port 6 starts
or restarts. Interactive players use keys 1–6 or click a lever or its
linked device. A lever can switch two devices at higher rungs.
The clock clamps interactive frames to 100 ms, subdivides them into
steps no longer than 1/60 s, and shows verdict feedback for three seconds.

SDL assigns screen 96 to `--screen escort`. It reads `ESCORT_RUNG`,
`ESCORT_TRIALS`, and `ESCORT_ADAPTIVE` from the profile and saves
edits to `.escort-options`. The browser stores options under
`nw.escort.options.v1` and accepts the `escort-seed` query parameter.

State fields 0–11 give phase, current rung, temple number, temples
per run, walkers, levers, walkers through, verdict, wins, highest
rung passed, starting rung, and adaptive flag. Verdict values 0–4
represent play in progress, a successful crossing, a pit fall,
a flame loss, and timeout.

`createEscortEnvironment` starts with six ports.
`nw_escort_agent_event` handles lever pulls and advances the clock
on port −1. The native library exposes `nw_escort_agent_create`,
`nw_escort_agent_act`, `nw_escort_agent_publish`, and
`nw_escort_agent_destroy`.

### Sokoban Live

Task ID `95000669` uses create options 0–2 for the starting rung,
warehouse count, and adaptive mode. The settings menu offers rungs
1, 4, 7, 10, 13, 16, 20, 25, and 30 and counts 1, 3, 5, 10, and 20.
Option 3 enables stepped agent mode. SDL opens screen 97 via
`--screen sokoban-live`,
reads the original `SOKOBANLIVE_RUNG`, `SOKOBANLIVE_TRIALS`, and
`SOKOBANLIVE_ADAPTIVE` profile keys, and saves edits to
`.sokobanlive-options`. The browser uses `sokoban-live-seed` and
`nw.sokobanlive.options.v1`.

Movement actions 0–3 map to up, down, left, and right, using the
arrow keys or WASD. Action 4 starts or restarts a run, as does a
left click on the ready or done scene. Moves recover for 0.18 s.

State fields 0–11 contain phase, current rung, trial, total trials,
pushes, steps, covered pads, verdict, wins, best rung, starting rung,
and adaptive mode. Verdict values 0–4 mean live, success, caught by
a guard, stuck crate, and timeout.

`createSokobanLiveEnvironment` exposes four ports.
`nw_sokobanlive_agent_event` accepts movement on ports 0–3 and
advances the clock on port −1. The native library exports
`nw_sokobanlive_agent_create`, `nw_sokobanlive_agent_act`,
`nw_sokobanlive_agent_publish`, and `nw_sokobanlive_agent_destroy`.

### Kitchen

Task ID `870733615` uses create options 0–2 for the starting rung,
shifts per run, and adaptive mode. Option 3 enables stepped agent
mode. The SDL route is screen 98, also available as `--screen kitchen`.
SDL reads `KITCHEN_RUNG`, `KITCHEN_TRIALS`, and `KITCHEN_ADAPTIVE` from
the existing profile and saves edits to `.kitchen-options`. The browser
uses `kitchen-seed` and `nw.kitchen.options.v1`.

Action ports 0–12 select crates 1–4, boards Q and W, stoves E, R and T,
plates A and S, the pass D, and the bin F. The keyboard dispatch codes are
12–15 for the crates and 68–76 for the remaining stations. A pointer
press selects the nearest station within one walking unit. Action 13,
Space, or a left click starts from the ready or done screen.

State fields 0–11 contain phase, current rung, trial, total trials,
served tickets, lapsed tickets, total tickets in the current shift,
verdict, wins, best rung, starting rung, and adaptive mode. Verdict
values 0–2 mean live, cleared, and ticket expiration.

`createKitchenEnvironment` exposes 13 ports. `nw_kitchen_agent_event`
accepts station orders and advances the clock on port −1. The native
library exports `nw_kitchen_agent_create`, `nw_kitchen_agent_act`,
`nw_kitchen_agent_publish`, and `nw_kitchen_agent_destroy`.

### Crane

Task ID `462731910` uses create options 0–2 for the starting rung, yards
per run, and adaptive mode. Option 3 enables stepped agent mode. SDL
opens screen 99 with `--screen crane`, reads the existing `CRANE_RUNG`,
`CRANE_TRIALS`, and `CRANE_ADAPTIVE` profile keys, and saves to
`.crane-options`. The browser uses `crane-seed` and `nw.crane.options.v1`.

Ports 0–3 drive left, drive right, hoist up, and hoist down. Port 4
grabs or releases, and port 5 starts a run. Arrows and WASD can be held,
with left, right, up, and down in priority order. Key release clears that
physical key, and focus loss clears all held controls. A left click or
Space starts from the ready or done screen. Space and Enter grab or
release during play.

Fields 0–14 report phase, current rung, trial, total trials, containers
placed, container count, elapsed milliseconds, verdict, wins, best
rung, starting rung, adaptive mode, trolley position in millimeters,
cable length in millimeters, and held container index (−1 for empty).
Verdict codes 0–6 represent live, clear, hard drop, wrong bay, outside
bay, collision, and timeout.

`createCraneEnvironment` exposes the five control ports.
`nw_crane_agent_event` advances on port −1. The native library exports
`nw_crane_agent_create`, `nw_crane_agent_act`, `nw_crane_agent_publish`,
and `nw_crane_agent_destroy`.

### Ferry

Task ID `709946811` uses create options 0–2 for the starting rung, rivers
per run, and adaptive mode. Option 3 enables stepped agent mode. SDL
opens screen 100 with `--screen ferry`, reads `FERRY_RUNG`, `FERRY_TRIALS`,
and `FERRY_ADAPTIVE`, and saves to `.ferry-options`. The browser uses
`ferry-seed` and `nw.ferry.options.v1`.

Ports 0–5 are ahead, astern, left, right, ahead-left, and ahead-right.
A left click or port 6 (Space) starts from the ready or done screen.
Arrows and WASD use independent held keys. Up combines with either turn,
with left taking precedence when both turns are held. Focus loss clears
held controls.

Fields 0–14 report phase, rung, trial, total trials, current crossing,
crossing count, elapsed milliseconds, verdict, wins, best rung, starting
rung, adaptive mode, x and y in millimeters, and heading in millidegrees.
Verdict codes 0–5 mean live, clear, aground, swept out, barge collision,
and timeout.

`createFerryEnvironment` exposes six control ports.
`nw_ferry_agent_event` advances on port −1. The native exports are
`nw_ferry_agent_create`, `nw_ferry_agent_act`, `nw_ferry_agent_publish`,
and `nw_ferry_agent_destroy`.

### Docking

Task ID `935767654` uses create options 0–2 for the starting rung,
dockings per run, and adaptive mode. Option 3 enables stepped agent
mode. SDL opens screen 101 with `--screen docking`, reads the original
`BERTH_RUNG`, `BERTH_TRIALS`, and `BERTH_ADAPTIVE` settings, and saves to
`.docking-options`. The browser uses `docking-seed` and
`nw.docking.options.v1`.

Ports 0–5 translate left, right, down, up, forward, and back. Ports 6–11
turn the nose left, right, down, and up, then roll left and right. Held
controls use the first port in that order. Space, a primary click, or
action 12 starts a run. Focus loss clears held controls.

Fields 0–9 report phase, rung, trial, total trials, wins, best rung,
starting rung, adaptive mode, verdict, and clearance flags. Verdict
codes 0–3 mean live, clear, contact failure, and drift. Clearance flags
1, 2, 4, and 8 mean off centre, too fast, nose off, and roll off. Fields
10–17 report elapsed milliseconds, fuel milliseconds, position in
millimeters along x, y, and z, and yaw, pitch, and roll in milliradians.

`createDockingEnvironment` exposes 12 control ports.
`nw_docking_agent_event` advances on port −1. The native exports are
`nw_docking_agent_create`, `nw_docking_agent_act`,
`nw_docking_agent_publish`, and `nw_docking_agent_destroy`.
`nw_docking_contact_audio` writes the judged contact cue as 0.8 seconds
of 22,050 Hz stereo little-endian PCM16, requiring 70,560 bytes.

### Rover

Task ID `3976448863` uses create options 0–2 for the starting rung,
drives per run, and adaptive mode. Option 3 enables stepped agent mode.
SDL launches with `--screen rover`, reads `ROVER_RUNG`, `ROVER_TRIALS`,
and `ROVER_ADAPTIVE`, and saves to `.rover-options`. The browser uses
`rover-seed` and `nw.rover.options.v1`.

Ports 0–3 drive, brake or reverse, turn left, and turn right. Controls
take priority in that order. The arrow and WASD aliases track each
physical key independently. Focus loss clears held keys. Space, a
primary click, or action 4 starts a run.

Fields 0–8 report phase, current rung, trial, total trials, wins, best
rung, starting rung, adaptive mode, and verdict. Verdicts 0–4 mean live,
clear, rock collision, tipped, and timeout. Fields 9–13 report reached
flags, total flags, commands in transit, elapsed milliseconds, and
signal delay in milliseconds. Fields 14–19 report true x and z, observed
x and z, observed heading, and observed speed. These values use
millimeters, milliradians, and millimeters per second.

`createRoverEnvironment` exposes four control ports. Port −1 advances
`nw_rover_agent_event` at the supplied time. The native agent uses
`nw_rover_agent_create`, `nw_rover_agent_act`, `nw_rover_agent_publish`,
and `nw_rover_agent_destroy`. `nw_rover_audio_window` renders up to one
second of stereo little-endian PCM16 at 22,050 Hz for a trial-time interval.

### Unicycle

Task ID `2516562765` uses create options 0–2 for the starting rung,
rides per run, and adaptive mode. Option 3 enables stepped agent mode.
SDL launches with `--screen unicycle`, reads `UNI_RUNG`, `UNI_TRIALS`,
and `UNI_ADAPTIVE`, and saves to `.unicycle-options`. The browser uses
`unicycle-seed` and `nw.unicycle.options.v1`.

Ports 0–3 pedal, back-pedal, lean back, and lean forward. Ports 4–7
combine pedal or back-pedal with either lean direction. Arrows and WASD
are independent held keys. Opposing directions on the same axis cancel
and focus loss clears held keys. Space, a primary click, or action 8
starts a run.

Fields 0–8 report phase, current rung, trial, total trials, wins, best
rung, starting rung, adaptive mode, and verdict. Verdicts 0–4 mean live,
clear, head over heels, fell off, and timeout. Fields 9–16 report last
port, elapsed milliseconds, allotted milliseconds, wheel x and y in
millimeters, horizontal speed in millimeters per second, tilt in
milliradians, and finish position in millimeters.

`createUnicycleEnvironment` exposes eight control ports. Port −1
advances `nw_unicycle_agent_event` at the supplied time. Native agents
use the `nw_unicycle_agent_create`, `nw_unicycle_agent_act`,
`nw_unicycle_agent_publish`, and `nw_unicycle_agent_destroy` exports.
`nw_unicycle_contact_audio` writes the finish or fall cue as 0.8 seconds
of 22,050 Hz stereo little-endian PCM16, requiring 70,560 bytes.

### Full Stop

Full Stop uses task ID `3891758761`. The common-v1 create parameters are
starting rung, runs per session, and adaptive difficulty. The renderer uses
the standard 912 × 684 reference frame. A left click or Space starts a
session. Pointer events move the cursor and place stops. Enter submits and
R clears the stops.

`nw_full_stop_load` accepts three pointer/byte-length pairs in the order
`passages.txt`, `sentences.txt`, and `lexicon.tsv`. Pass a zero pair for
each omitted file. The import copies the parsed corpus into the run's arena,
so callers can release their buffers after the call. Import is available
once, before play. Bundled seed data supplies the omitted files.

`nw_full_stop_audio_window` writes interleaved stereo PCM at 22,050 Hz.
The stepped agent has sixteen ports. Ports 0–13 use the shared hand
controls, 14 submits, and 15 resets. The WebAssembly agent entry uses
16 to start and −1 to advance a frame. The native agent ABI uses the
standard create, act, publish, and destroy calls.

### The Missing Word

The Missing Word uses task ID `2323823752`. Its common-v1 parameters are
starting rung, passages per session, and adaptive difficulty. Pointer input
opens the choices under a gap or strikes out a word. Enter submits and R
restores the original damage. Feedback lasts four seconds in interactive
play. State field 10 reports that the corpus has no eligible passage.

`nw_missing_word_load` uses the same three cache spans as `nw_full_stop_load`.
Import is available before play. The browser agent accepts those files as
`passageCaches` with optional `passages`, `sentences`, and `lexicon` byte
buffers. Native agents read the existing files in the Workshop data directory.
The agents use ports 0–13 for the pointer, 14 to submit, and 15 to reset.
The WebAssembly agent entry uses 16 to start and −1 to advance a frame.

### The Proofreader

The Proofreader uses task ID `2105479234`. Its first three create options
are starting rung, passages per run, and adaptive difficulty. Option 3
allows positive integer dials beyond the options menu when set to 1.
Options 4 and 5 are zero. Field 11 reports the number of dealt changes
including sentence order. Field 12 counts edits made during the passage.

Drag a row by its number or a word within its row. Click a word to show
its forms, then click an offered form to replace it. Enter submits and R
restores the original damage. Cancellation clears any held tile.
Interactive feedback lasts four seconds. Cache spans, agent ports, and
byte buffers use the same format as The Missing Word. The web agent
factory is `createProofreaderEnvironment`.

### Figures of Speech

Figures of Speech uses task ID `2703097653`. Create options 0–2 are
starting rung, rounds per run, and adaptive difficulty. Option 3 permits
positive integer dials beyond the interactive menu when set to 1.
Options 4 and 5 are zero. State fields 10–12 are the current question
index, correct answers, and wrong answers.

Space or a primary click starts the run. Number keys 1–8 and pointer
presses choose answers. The right answer stays up for 1.4 seconds between
questions, and a completed round has 2.5 seconds of interactive feedback.
`nw_figures_of_speech_load` accepts an original `questions.jsonl` byte
span before play. Imported questions replace bundled questions by kind.

The web factory is `createFiguresOfSpeechEnvironment`, with optional
`questionCache` bytes. Agent ports 0–7 correspond to answers in display
order. The WebAssembly agent entry uses 8 to start and −1 to advance.

### Between the Lines

Between the Lines is the first card under Social, one of the four tabs
after Decisions (Computer use, Emotion, Social and Rationality, as in
the original hub; a tab with no card yet says so). It uses task ID
`4294934071`. Create options 0–2 are starting rung, rounds per run, and
adaptive difficulty; option 3 permits positive integer dials beyond the
menu when set to 1. Options 4 and 5 are zero. State fields 10–12 are
the current question index, correct answers, and wrong answers.

A round is 20 questions: what a reply implies, from rung 4 which remark
is sarcastic, and from rung 7 whether a sentence is ironic. The answers
keep the order they were written in. Space or a primary click starts the
run; number keys 1–8 and pointer presses choose answers. The right
answer stays up for 1.4 seconds, and a finished round has 2.5 seconds of
feedback. `nw_between_the_lines_load` accepts the original
`questions.jsonl`, the file Figures of Speech reads too; the browser
keeps one imported copy for both. Imported questions replace the bundled
ones by kind.

The web factory is `createBetweenTheLinesEnvironment`, with optional
`questionCache` bytes. Agent ports 0–7 are the answers in display order;
the agent entry uses 8 to start and −1 to advance. SDL uses screen 130
for `--screen between-the-lines`, reads `LINES_RUNG`, `LINES_TRIALS`
and `LINES_ADAPTIVE`, saves changes to the profile's
`.between-the-lines-options` sidecar, and reads
`datasets/social/questions.jsonl` from the data directory. The native
library exports `nw_between_the_lines_agent_{create,act,publish,destroy}`.

### Second Thoughts

Second Thoughts is the second card under Rationality. It uses task ID
`2360688716`. Create options 0–2 are starting rung, rounds per run, and
adaptive difficulty; option 3 permits positive integer dials beyond the
menu when set to 1. Options 4 and 5 are zero. State fields 10–12 are
the current question index, correct answers, and wrong answers.

A round is ten puzzles, made with fresh numbers and names; the first
answer that comes to mind is always one of the choices. Space or a
primary click starts the run; number keys 1–8 and pointer presses
choose answers. The right answer stays up for 1.4 seconds, and a
finished round has 2.5 seconds of feedback. Nothing is imported, so
there is no load export.

The web factory is `createSecondThoughtsEnvironment`. Agent ports 0–7
are the answers in display order; the agent entry uses 8 to start and
−1 to advance. SDL uses screen 131 for `--screen second-thoughts`,
reads `SECOND_RUNG`, `SECOND_TRIALS` and `SECOND_ADAPTIVE`, and saves
changes to the profile's `.second-thoughts-options` sidecar. The native
library exports `nw_second_thoughts_agent_{create,act,publish,destroy}`.

### Emotion

Emotion is the first card under Emotion, before Which Feeling. It uses
task ID `1337504642`. Its options and state fields are those of Why They
Feel, with the current face at field 10. It draws its own faces and has
no load export; FER-2013's photographs are not read yet.

A round is 12 faces. Rung 1 asks happy or sad, rung 2 adds surprise,
rung 3 anger and neutral, rungs 4–5 offer seven emotions and rung 6 on
all eight. From rung 8 the face is covered after 1.6 s, 0.12 s less a
rung down to 0.15 s; from rung 10 some faces show only the eyes or the
mouth; from rung 14 each face asks the strongest emotion and then the
next. The answer time is 10 s a step at rung 1, 0.35 s less a rung down
to 2.5 s. `nw_emotion_audio_window` returns the quiz's notes.

The web factory is `createEmotionEnvironment`. SDL uses screen 139 for
`--screen emotion`, reads `EMO_RUNG`, `EMO_TRIALS` and `EMO_ADAPTIVE`,
and saves changes to the profile's `.emotion-options` sidecar. The
native library exports `nw_emotion_agent_{create,act,publish,destroy}`.

### Which Feeling

Which Feeling is the second card under Emotion, after Emotion. It uses task ID `2151530893`. Create
options 0–2 are starting rung, rounds per run, and adaptive difficulty;
option 3 permits positive integer dials beyond the menu when set to 1.
Options 4 and 5 are zero. State fields 10–12 are the current comment
index, correct answers, and wrong answers.

A round is ten comments, with 2 to 8 shuffled answers depending on the
rung and a fixed time each. Space or a primary click starts the run;
number keys 1–8 and pointer presses choose answers. The right answer
stays up for 1.4 seconds, and a finished round has 2.5 seconds of
feedback. `nw_which_feeling_load` takes the text of `goemotions.tsv`: a
label, a tab and the comment on each line. Labels the task does not ask
about are ignored, and a file without a line holding a tab gives the
bundled comments.

The web factory is `createWhichFeelingEnvironment`, whose
`commentCache` option takes the file's bytes. The browser keeps the
imported file under its own storage key. Agent ports 0–7 are the answers
in display order; the agent entry uses 8 to start and −1 to advance. SDL
uses screen 134 for `--screen which-feeling`, reads
`datasets/emotion/goemotions.tsv` from the workshop data directory, reads
`FEEL_RUNG`, `FEEL_TRIALS` and `FEEL_ADAPTIVE`, and saves changes to the
profile's `.which-feeling-options` sidecar. The native library exports
`nw_which_feeling_agent_{create,act,publish,destroy}`.

### How Strongly

How Strongly is the third card under Emotion, after Which Feeling. It
uses task ID `1500838626`. Create options 0–2 are starting rung, rounds
per run, and adaptive difficulty; option 3 permits positive integer dials
beyond the menu when set to 1. Options 4 and 5 are zero. State fields
10–12 are the current dialogue index, correct answers, and wrong answers.

Rungs 1–3 deal eight dialogues and ask which of the speaker's emotions is
strongest. From rung 4 a round is six dialogues; each emotion is asked in
turn on a scale of 0, 2, …, 10, and the dialogue counts right when the
misses together stay within the rung's tolerance (8 at rung 4, narrowing
by 2 every other rung to 0). Each dialogue has 60 seconds at rung 1, two
fewer a rung down to 20. Space or a primary click starts the run; number
keys 1–8 and pointer presses choose answers. Feedback names the strongest
emotion, or every emotion with its reference level, and hides the scale.
`nw_how_strongly_load` takes the text of `eqbench.jsonl`: one JSON object
a line with `text`, `who`, `emotions` and `scores`. Lines that do not
decode, or whose emotions and scores differ in number, are skipped, and a
file with no usable line gives the bundled dialogues.

The web factory is `createHowStronglyEnvironment`, whose `dialogueCache`
option takes the file's bytes. The browser keeps the imported file under
its own storage key. Agent ports 0–7 are the answers in display order;
the agent entry uses 8 to start and −1 to advance. SDL uses screen 135
for `--screen how-strongly`, reads `datasets/emotion/eqbench.jsonl` from
the workshop data directory, reads `STRONG_RUNG`, `STRONG_TRIALS` and
`STRONG_ADAPTIVE`, and saves changes to the profile's
`.how-strongly-options` sidecar. The native library exports
`nw_how_strongly_agent_{create,act,publish,destroy}`.

### Reading People

Reading People is the fourth card under Emotion. It uses task ID
`249251215`. Create options 0–2 are starting rung, rounds per run, and
adaptive difficulty; option 3 permits positive integer dials beyond the
menu when set to 1. Options 4 and 5 are zero. State fields 10–12 are the
current story index, correct answers, and wrong answers.

A round is six stories. Rungs 1–3 ask how the subject feels, rungs 4–6
ask that and then why (two steps, both needed), rungs 7–9 ask what would
help most, and later rungs mix all three. Each step has 45 seconds at
rung 1, two fewer a rung down to 15. `nw_reading_people_load` takes the
text of `emobench.jsonl`: one JSON object a line with `kind`
(`understand` or `act`), `scenario`, `subject`, `choices` and `answer`,
and for `understand` also `causes` and `cause`. Unreadable lines are
skipped, and a file with no usable line gives the bundled stories.

The web factory is `createReadingPeopleEnvironment`, whose `storyCache`
option takes the file's bytes. Agent ports 0–7 are the answers in
display order; the agent entry uses 8 to start and −1 to advance. SDL
uses screen 136 for `--screen reading-people`, reads
`datasets/emotion/emobench.jsonl`, reads `READ_RUNG`, `READ_TRIALS` and
`READ_ADAPTIVE`, and saves changes to the profile's
`.reading-people-options` sidecar. The native library exports
`nw_reading_people_agent_{create,act,publish,destroy}`.

### Why They Feel

Why They Feel is the fifth card under Emotion. It uses task ID
`3835238973`. Its options and state fields are those of Reading People,
with the current story at field 10. It makes its own stories and has no
load export.

A round is ten stories, each asking how someone feels, or from rung 15
what one person thinks another thinks someone feels. Rungs offer 2 to 8
answers and 30 seconds a story at rung 1, one fewer a rung down to 8.
The web factory is `createWhyTheyFeelEnvironment`. SDL uses screen 137
for `--screen why-they-feel`, reads `WHY_RUNG`, `WHY_TRIALS` and
`WHY_ADAPTIVE`, and saves changes to the profile's `.why-they-feel-options`
sidecar. The native library exports
`nw_why_they_feel_agent_{create,act,publish,destroy}`.

### Tone of Voice

Tone of Voice is the sixth and last card under Emotion, after Why They Feel. It
uses task ID `529523398`. Its options and state fields are those of Why
They Feel, with the current voice at field 10. It makes its own voices
(hums) and has no load export; CREMA-D clips are not read yet.

A round is 20 voices at two choices and 10 otherwise. Rung 1 offers two
emotions, rungs 2–3 three, 4–6 four, and from rung 7 all six with the
plain voice. A hiss joins from rung 10, and from rung 13 only 1.2 s
(0.9 s from rung 16) of each voice is kept. Each voice starts 0.4 s into
its item and plays twice with 0.6 s between. The answer time adds 6 s
at rung 1, 0.2 s less a rung down to 2.5 s. `nw_tone_of_voice_audio_window`
returns the voices, hiss and notes as stereo 16-bit PCM, on the run's
own clock (field 9).

The web factory is `createToneOfVoiceEnvironment`. SDL uses screen 138
for `--screen tone-of-voice`, reads `VOICE_RUNG`, `VOICE_TRIALS` and
`VOICE_ADAPTIVE`, and saves changes to the profile's
`.tone-of-voice-options` sidecar. The native library exports
`nw_tone_of_voice_agent_{create,act,publish,destroy}`.

### Desktop

Desktop is the first card under Computer use. It uses task ID
`3716188083`. Create options 0–2 are starting rung (1–6, 8, 11, 13, 15,
16, 18, 20, 25 or 30), rounds per run (1, 3, 5, 8 or 12) and adaptive
difficulty. Options 3–5 are zero. State fields 0–8 are phase (0 ready,
1 working, 2 judged, 3 done), rung, round, rounds per run, passes,
highest rung passed, starting rung, adaptive, and the round's verdict
(0 under way, 1 passed, 2 failed). Fields 9–15 are clicks, par in
tenths, the click budget, settings and files on the card that hold, the
card's goal count, whether everything on the card holds, and whether the
mouse button is held. Outside a round fields 9–15 are 0.

Each round deals a desktop from desktop.py's ladder: windows with
switches, dropdowns and fields to set, and from later rungs tabs,
scrolling, menus and dialogs, overlapping and minimised windows,
greyed-out controls, Apply buttons, popups, sticky notes, windows off
the screen or closed, submenus, a file explorer with files to move,
delete, restore or copy, list views, and a card that hides. Par is the
clicks desktop.py's reference takes on the same deal (two more when the
card hides), times a factor that falls from 2 at rung 1 to 1 at rung 12
and below 1 from rung 21, plus slack; the budget is three times par plus
20 clicks. A round
passes when every setting and file on the card holds in no more clicks
than par, and it ends when Done is pressed or the budget is spent. The
verdict stays up for 2.2 seconds.

Space or a primary click starts the run. During a round the mouse moves
the pointer; a primary press and release is a click, or a drag when the
two are apart by more than 6 reference pixels (a release closer than
that is taken at the press point); a secondary press right-clicks.
Arrows step the pointer: Shift a long step (80), none a medium one (20),
Alt a short one (5). Space clicks, Enter presses Done, and the text
events `r`/`R` right-click and `d`/`D` press or let go. Moving is free;
each click, right-click and drag costs one. Actions 0–11 move the
pointer up, down, left and right by a long, medium or short step (port
= direction × 3 + size), 12 clicks, 13 presses, 14 lets go, 15 presses
Done, 16 right-clicks and 17 starts a run.
`nw_desktop_options_note` gives the starting rung's note. The web factory
is `createDesktopEnvironment`; its agent entry uses 17 to start and −1 to
advance. SDL uses screen 145 for `--screen desktop`, reads
`DESKTOP_RUNG`, `DESKTOP_TRIALS` and `DESKTOP_ADAPTIVE`, and saves
changes to the profile's `.desktop-options` sidecar. There, `r` and `d`
arrive as keys, and SDL's button-up events reach Desktop alone. The
native library exports `nw_desktop_agent_{create,act,publish,destroy}`.

### Forms

Forms is the second card under Computer use, after Desktop. It uses task ID
`2143393500`. Create options 0–2 are starting rung (1, 2, 4, 6, 8, 10,
12, 14, 16, 18, 20 or 25), forms per run (1, 3, 5, 8 or 12) and adaptive
difficulty; option 3 permits positive integer dials beyond the menu when
set to 1. Options 4 and 5 are zero. State fields 0–8 are phase (0 ready,
1 filling, 2 judged, 3 done), rung, form, forms per run, passes, highest
rung passed, starting rung, adaptive, and the form's verdict (0 under
way, 1 right and within par, 2 not). Fields 9–14 are keys pressed, pages
sent back, the page in view, the field in focus (forms.py's order: first
name, last name, city, email, date of birth, phone, country, plan,
newsletter, company checkbox, company name; −1 for none), cost (keys
plus the rung's penalty per page sent back), and par in tenths.

Each form is dealt from a person on a card: one field at rung 1, up to
twelve from rung 22, with dates to rewrite (rung 4), phone numbers to
strip to digits (5), a country list that completes as it is typed (6),
checkboxes and radio buttons (8), a company name that appears only when
its checkbox is ticked (10), two pages and then three (12, 18), and the
card written as a letter (14) that mentions a sister's details too (16).
Par is the keys forms.py's reference typist presses on the same form,
times a factor that falls to 1 by rung 21, plus slack. Space or a
primary click starts the run. Characters arrive as text events (letters,
digits, space and `@ . - /`; anything else is ignored); Backspace, Tab,
Enter, Up and Down arrive as keys, and Space as a key does nothing while
a form is being filled. A primary press on a field's row moves the focus
there for one key. A page with an empty field, a malformed date, a phone
number that is not 6–12 digits or a malformed email comes back with
those fields framed red. The verdict stays up for three seconds. Actions
0–45 are ui/forms.py's keys (a–z, 0–9, space, `@`, `.`, `-`, `/`,
Backspace, Tab, Enter, Up, Down) and 46 starts a run.
`nw_forms_options_note` gives the starting rung's note. The web factory
is `createFormsEnvironment`; its agent entry uses 46 to start and −1 to
advance. SDL uses screen 144 for `--screen forms`, reads `FORMS_RUNG`,
`FORMS_TRIALS` and `FORMS_ADAPTIVE`, saves changes to the profile's
`.forms-options` sidecar, and starts SDL text input when Forms opens.
The native library exports `nw_forms_agent_{create,act,publish,destroy}`.

### Manual

Manual is the third card under Computer use, after Forms. It uses task ID
`563151331`. Create options 0–2 are starting rung (1, 2, 5, 9, 13, 17,
20, 25 or 30), procedures per run (1, 3, 5, 8 or 12) and adaptive
difficulty; option 3 permits positive integer dials beyond the menu when
set to 1. Options 4 and 5 are zero. State fields 0–8 are phase, rung,
procedure, procedures per run, passes, highest rung passed, starting
rung, adaptive, and the procedure's verdict (0 under way, 1 done exactly
as written, 2 not). Fields 9–11 are the procedure's step count, the
moves made so far, and the digit the display shows.

Each procedure deals a panel never seen before -- switches, knobs from 0
to 4, buttons, coloured lamps and a one-digit display, wired at random
so the lamps and display answer the controls -- and up to ten written
steps: set or flip a switch, turn a knob, press a button, and at higher
rungs steps that depend on a lamp, read the display, copy one control
to another, press until a lamp changes, put a control back as it
started, or skip the next step. From rung 17 the controls are drawn in
shuffled order. Finish passes when every control stands exactly where
following the procedure leaves it. Space or a primary click starts the
run; a press on a switch flips it, on a knob's minus or plus turns it a
step, and on a button presses it; Enter or a press on Finish ends the
procedure. A judged procedure outlines every control left wrong in red,
and its verdict stays up for 2.5 seconds. Actions 0–5 flip the
switches in drawn order, 6–13 turn the knobs (down, then up, two to a
knob), 14–19 press the buttons, 20 is Finish and 21 starts a run.
`nw_manual_options_note` gives the starting rung's note. The web factory
is `createManualEnvironment`; its agent entry uses 21 to start and −1 to
advance. SDL uses screen 143 for `--screen manual`, reads `MANUAL_RUNG`,
`MANUAL_TRIALS` and `MANUAL_ADAPTIVE`, and saves changes to the
profile's `.manual-options` sidecar. The native library exports
`nw_manual_agent_{create,act,publish,destroy}`.

### Browser

Browser is the fourth card under Computer use, after Manual. It uses task ID
`122887567`. Create options 0–2 are starting rung (1, 3, 6, 9, 12, 15,
18, 21, 25 or 30), shopping trips per run (1, 3, 5, 8 or 12) and
adaptive difficulty; option 3 permits positive integer dials beyond the
menu when set to 1. Options 4 and 5 are zero. State fields 0–8 are
phase, rung, trip, trips per run, passes, highest rung passed, starting
rung, adaptive, and the trip's verdict (0 under way, 1 bought within
par, 2 the right things over par, 3 the wrong things). Fields 9–15 are
clicks, par, the page kind, items in the cart, the in-page pointer's x
and y, and the scroll offset, all in the 1000 by 640 page's units.

Each trip deals a small shop and a shopping list; a trip passes when
checkout buys exactly the list in no more clicks than par, which allows
a share of a thorough shopper's extra clicks that shrinks with the rung.
Space or a primary click starts the run. A pointer press on the page
clicks there; the wheel and Up/Down scroll; Backspace goes back and
counts as a click. A verdict stays up for 2.5 seconds. Actions 0–14 are
the agent ports (twelve pointer moves, a click, scroll up, scroll down)
and 15 starts a run. `nw_browser_options_note` gives the starting
rung's note. The web factory is `createBrowserEnvironment`; its agent
entry uses 15 to start and −1 to advance. SDL uses screen 140 for
`--screen browser`, reads `BROWSER_RUNG`, `BROWSER_TRIALS` and
`BROWSER_ADAPTIVE`, and saves changes to the profile's `.browser-options`
sidecar. The native library exports
`nw_browser_agent_{create,act,publish,destroy}`.

### Errands

Errands is the fifth card under Computer use, after Browser. It uses
task ID `1095090106`. Create options 0–2 are starting rung (1, 3, 6, 9,
12, 15, 18, 21, 25 or 30), errand days per run (1, 3, 5 or 8) and
adaptive difficulty; option 3 permits positive integer dials beyond the
menu when set to 1. Options 4 and 5 are zero. State fields 0–8 are
phase, rung, day, days per run, passes, highest rung passed, starting
rung, adaptive, and the day's verdict (0 under way, 1 all done within
par, 2 all done over par, 3 not done). Fields 9–15 are clicks, par, the
app in front (0 Mail, 1 Shop, 2 Expenses), claims filed, the in-page
pointer's x and y, and orders placed, in the 1000 by 640 page's units.

Each day deals an inbox: receipts to claim, orders to place in
Browser's shop (each bought on its own, then claimed), a policy mail
that sets the categories, a later mail that changes a request, and mail
that needs nothing. An app strip switches between Mail, Shop and
Expenses, whose claim form takes an order number and an amount from an
on-screen keypad, a category and Submit. Done ends the day; it passes
when every claim is right, nothing wrong was bought or claimed, and the
clicks are within par. Space or a primary click starts the run. A
pointer press on the page clicks there; the wheel and Up/Down scroll
the shop; digits and Backspace type into the claim form while Expenses
is in front and count as clicks. A verdict stays up for 2.5 seconds.
Actions 0–14 are Browser's agent ports and 15 starts a run.
`nw_errands_options_note` gives the starting rung's note. The web
factory is `createErrandsEnvironment`; its agent entry uses 15 to start
and −1 to advance. SDL uses screen 142 for `--screen errands`, reads
`ERRANDS_RUNG`, `ERRANDS_TRIALS` and `ERRANDS_ADAPTIVE`, and saves
changes to the profile's `.errands-options` sidecar. The native library
exports `nw_errands_agent_{create,act,publish,destroy}`.

### Spreadsheet

Spreadsheet is the sixth card under Computer use, after Errands. It
uses task ID `36128217`. Create options 0–2 are starting rung (1, 4, 7,
10, 13, 16, 20, 25 or 30), questions per run (1, 3, 5, 10 or 20) and
adaptive difficulty; option 3 permits positive integer dials beyond the
menu when set to 1. Options 4 and 5 are zero. State fields 0–8 are
phase, rung, question, questions per run, passes, highest rung passed,
starting rung, adaptive, and the question's verdict (0 under way, 1
right within par, 2 right over par, 3 wrong). Fields 9–15 are clicks,
par, the number typed so far, how many digits it has, the in-page
pointer's x and y, and the first visible row, in the 1000 by 640 page's
units.

Each question deals a table of orders: look up a total, find the
highest, sum or count a category, or find or correct the one wrong
total. Category filters, sortable headers, Sum buttons under Qty, Price
and Total, and a keypad with Submit are the tools; Submit takes one
answer, and a question passes when it is right in no more clicks than
par. Space or a primary click starts the run. A pointer press on the
page clicks there; the wheel and Up/Down scroll the rows; digits,
Backspace and Enter work the keypad and count as clicks. A verdict
stays up for 2.5 seconds. Actions 0–14 are Browser's agent ports and 15
starts a run. `nw_spreadsheet_options_note` gives the starting rung's
note. The web factory is `createSpreadsheetEnvironment`; its agent entry
uses 15 to start and −1 to advance. SDL uses screen 141 for
`--screen spreadsheet`, reads `SPREADSHEET_RUNG`, `SPREADSHEET_TRIALS`
and `SPREADSHEET_ADAPTIVE`, and saves changes to the profile's
`.spreadsheet-options` sidecar. The native library exports
`nw_spreadsheet_agent_{create,act,publish,destroy}`.

### Social Sense

Social Sense is the second card under Social, after Between the Lines.
It uses task ID `2281393555`. Create options 0–2 are starting rung,
rounds per run, and adaptive difficulty; option 3 permits positive
integer dials beyond the menu when set to 1. Options 4 and 5 are zero.
State fields 10–12 are the current question index, correct answers, and
wrong answers.

A round is 12 situations, and passing takes at least 9 right. From rung 13 an item asks two
questions about one situation, and both must be right. Space or a
primary click starts the run; number keys 1–8 and pointer presses choose
answers, which are shuffled. The right answer stays up for 1.4 seconds,
and a finished round has 2.5 seconds of feedback.
`nw_social_sense_load` takes the text of `questions.jsonl`; any question
of kind `social` or `social:<what>` replaces all the bundled ones, and
other kinds are ignored. A rung whose kinds have no questions deals no
round, and the run stays ready.

The web factory is `createSocialSenseEnvironment`, with the same
`questionCache` option as Between the Lines. Agent ports 0–7 are the
answers in display order; the agent entry uses 8 to start and −1 to
advance. SDL uses screen 133 for `--screen social-sense`, reads
`SENSE_RUNG`, `SENSE_TRIALS` and `SENSE_ADAPTIVE`, and saves changes to
the profile's `.social-sense-options` sidecar. The native library
exports `nw_social_sense_agent_{create,act,publish,destroy}`.

### Bad Argument

Bad Argument is the first card under Rationality, before Second
Thoughts. It uses task ID `2769191638`. Create options 0–2 are starting
rung, rounds per run, and adaptive difficulty; option 3 permits positive
integer dials beyond the menu when set to 1. Options 4 and 5 are zero.
State fields 10–12 are the current question index, correct answers, and
wrong answers.

A round is 20 arguments, and passing takes at least 15 right. Space or a primary click starts
the run; number keys 1–8 and pointer presses choose answers. The answers
are "it follows" and "it does not follow" in that order, or, on the
rungs that ask what is wrong, the five names of a flaw in shuffled
order. The right answer stays up for 1.4 seconds, and a finished round
has 2.5 seconds of feedback. `nw_bad_argument_load` takes the text of
`questions.jsonl`; its `fallacy` and `formal` questions replace the
bundled ones of the same kind, and other kinds are ignored.

The web factory is `createBadArgumentEnvironment`, with the same
`questionCache` option as Between the Lines. Agent ports 0–7 are the
answers in display order; the agent entry uses 8 to start and −1 to
advance. SDL uses screen 132 for `--screen bad-argument`, reads
`ARGUE_RUNG`, `ARGUE_TRIALS` and `ARGUE_ADAPTIVE`, and saves changes to
the profile's `.bad-argument-options` sidecar. The native library
exports `nw_bad_argument_agent_{create,act,publish,destroy}`.

### Crazy Cog

Crazy Cog uses task ID `205861782`. Create options 0–2 are starting
rung, machines per run, and adaptive difficulty. Set option 3 to 1 to
use positive integer rung and trial counts beyond the menu. Options 4
and 5 are zero.

Space or a primary click starts the run. Drag cogs and chains from
the tray. Tab and F go one plane deeper. Shift+Tab and G go one plane
nearer. Keys 1–5 select a plane and R clears the board. Logical key
codes 87 and 88 are the F and G aliases. Interactive feedback lasts
2.5 seconds.

`nw_api_v1_crazy_cog_info` fields 0–9 are phase, current rung, trial,
trial count, wins, best passing rung, starting rung, adaptive flag,
verdict, and simulation milliseconds. Fields 10–12 are the zero-based
active plane, plane count, and carried item (zero for none, −1 for a
chain, or the cog radius). Verdicts 0–3 mean active, bucket up, fan
incorrect, and out of time.

The web factory is `createCrazyCogEnvironment`. Ports 0–11 move the
pointer, 12 presses, 13 releases, 14 clears the board, 15 moves deeper,
and 16 moves nearer. The agent entry uses 17 to start and −1 to advance.
`nw_crazy_cog_audio_window` writes interleaved signed 16-bit stereo PCM
at 22,050 Hz for a run-relative time window.

SDL uses screen 110 for `--screen crazy-cog`. Its profile loader reads
`COG_RUNG`, `COG_TRIALS`, and `COG_ADAPTIVE` from the original
configuration. Edits use the selected profile’s `.crazy-cog-options`
sidecar. The native agent library exposes the
`nw_crazy_cog_agent_{create,act,publish,destroy}` entry points.

### Potter’s Wheel

Potter’s Wheel uses task ID `4292812816`. Create options 0–2 are the
starting rung, pots per run, and adaptive difficulty. Set option 3 to 1
for positive integer rung and trial counts beyond the menu. Options 4
and 5 are zero.

Space, Enter, or a primary click starts a session. Hold the pointer
against a band to shape it. Up and W spin the wheel faster, Down and
S slow it, and Space wets the clay. Feedback lasts 2.5 seconds.

`nw_api_v1_potters_wheel_info` fields 0–9 are phase, current rung, trial,
trial count, wins, best passing rung, starting rung, adaptive flag,
verdict, and simulation milliseconds. Fields 10–14 are wheel speed,
band count, wetness in thousandths, touched band (−1 when none), and
the pressed-pointer flag. Verdicts 0–3 are active, finished, collapsed,
and hardened.

The web factory is `createPotterEnvironment`. Agent ports 0–11 move
the pointer, 12 presses, 13 releases, 14 speeds up, 15 slows down, and
16 adds water. The agent entry uses 17 to start and −1 to advance.
`nw_potters_wheel_audio_window` writes interleaved signed 16-bit stereo
PCM at 22,050 Hz.

SDL uses screen 112 for `--screen potters-wheel`. It loads
`POTTER_RUNG`, `POTTER_TRIALS`, and `POTTER_ADAPTIVE` from the selected
profile and saves edits in its `.potters-wheel-options` sidecar. The
native agent exports `nw_potters_wheel_agent_{create,act,publish,destroy}`.

### Conductor

Conductor uses task ID `3161448022`. Create options 0–2 are the
starting rung, pieces per run, and adaptive difficulty. Set option 3 to
1 for positive integer rung and trial counts beyond the menu. Options 4
and 5 are zero.

Space, Enter, or primary click starts a run. Flick the pointer down on
each beat and click the indicated section for an entrance or cutoff.
Up or W gives the louder cue, and Down or S gives the softer cue.
Feedback lasts 2.5 seconds.

`nw_api_v1_conductor_info` fields 0–9 report phase, rung, trial, trial
count, wins, best passing rung, starting rung, adaptive flag, verdict,
and simulation milliseconds. Fields 10–14 report volume, sounded beats,
slips, judged beats, and the pressed-pointer flag. Verdicts 0–2 are
active, Bravo, and the orchestra fell apart.

The web factory is `createConductorEnvironment`. Agent ports 0–11 move
the pointer, 12 presses, 13 releases, and 14 and 15 request louder and
softer. The agent entry uses 16 to start and −1 to advance.
`nw_conductor_audio_window` writes signed 16-bit stereo PCM at 22,050 Hz.

SDL uses screen 113 for `--screen conductor`. It reads `CONDUCT_RUNG`,
`CONDUCT_TRIALS`, and `CONDUCT_ADAPTIVE`, and saves changes in the
selected profile’s `.conductor-options` sidecar. The native library
exports `nw_conductor_agent_{create,act,publish,destroy}`.

### Tightrope

The Tightrope card is in Attention. The three creation options are the
starting rung, crossings per run, and adaptive difficulty. Option 3 can
be set to 1 for positive rung and trial counts outside the menu.

Space, Enter, or primary click starts a run. Move the pointer to balance
left to right and front to back, press Space, Up, or W to take a step,
and click a perched bird to shoo it. Feedback lasts 2.5 seconds.

`nw_api_v1_tightrope_info` fields 0–9 report phase, rung, trial, trial
count, wins, best passing rung, starting rung, adaptive flag, verdict,
and simulation milliseconds. Fields 10–14 report steps taken, steps
required, lean and pitch in milliradians, and the pressed-pointer flag.
Verdicts 0–5 are active, across, fell sideways, fell forward, fell
backward, and out of time.

The web factory is `createTightropeEnvironment`. Ports 0–11 move the
pointer, 12 presses, 13 releases, and 14 steps. The agent entry uses 15
to start and −1 to advance. `nw_tightrope_audio_window` writes signed
16-bit stereo PCM at 22,050 Hz.

SDL uses screen 114 for `--screen tightrope`. It reads `ROPE_RUNG`,
`ROPE_TRIALS`, and `ROPE_ADAPTIVE`, then saves changes in the profile's
`.tightrope-options` sidecar. The native library exports
`nw_tightrope_agent_{create,act,publish,destroy}`.

### Sign Painter

The Sign Painter card is in Attention. The three creation options are
the starting rung, signs per run, and adaptive difficulty. Set option
3 to 1 to accept positive rung and trial counts outside the menu.

Space, Enter, or primary click starts a run. Hold the button and trace
each stroke. Use 1–4 or R, G, B, and Y to choose a colour, then Space
with the brush lifted to dip it. Feedback lasts 2.5 seconds.

`nw_api_v1_sign_painter_info` fields 0–9 report phase, rung, trial,
trial count, wins, best passing rung, starting rung, adaptive flag,
verdict, and simulation milliseconds. Fields 10–16 report the current
stroke and sample indices, selected colour, paint remaining, the
pressed-pointer flag, smudge count, and stroke count. Verdicts 0–4
are active, handsome sign, mess, wrong colour, and dried paint.

The web factory is `createSignPainterEnvironment`. Ports 0–11 move
the pointer, 12 presses, 13 releases, 14–17 select colour, and 18 dips.
The agent entry uses 19 to start and −1 to advance.
`nw_sign_painter_audio_window` writes signed 16-bit stereo PCM at
22,050 Hz.

SDL uses screen 115 for `--screen sign-painter`. It reads `SIGN_RUNG`,
`SIGN_TRIALS`, and `SIGN_ADAPTIVE` and saves changes in the profile's
`.sign-painter-options` sidecar. The native library exports
`nw_sign_painter_agent_{create,act,publish,destroy}`.

### Bartender

The Bartender card is in Attention. Its three creation options are
starting rung, nights per run, and adaptive difficulty. Option 3 allows
positive rung and trial counts outside the menu when set to 1.

Space, Enter, or primary click starts a run. Hold a bottle above the
glass to pour. Use Space or I to toggle ice. Pull the glass back,
push it forward, and release it to slide it to the customer.
Feedback lasts 2.5 seconds.

`nw_api_v1_bartender_info` fields 0–9 report phase, rung, trial,
trial count, wins, best passing rung, starting rung, adaptive flag,
verdict, and simulation milliseconds. Fields 10–18 report customers
served, customers total, strikes, glass fill in thousandths, the
pressed-pointer flag, held item, ice flag, glass position in
millimetres, and whether the glass is sliding. A held item of −1
means an empty hand, 0–4 are bottles, and 5 is the glass. Verdicts
0–7 are active, good night, spill, broken glass, walkout, incomplete
service, wrong drink, and empty seat.

The web factory is `createBartenderEnvironment`. Ports 0–11 move the
pointer, 12 presses, 13 releases, and 14 toggles ice. The agent entry
uses 15 to start and −1 to advance. `nw_bartender_audio_window` writes
signed 16-bit stereo PCM at 22,050 Hz.

SDL uses screen 116 for `--screen bartender`. It reads `BAR_RUNG`,
`BAR_TRIALS`, and `BAR_ADAPTIVE` and saves changes to the profile's
`.bartender-options` sidecar. The native agent exports
`nw_bartender_agent_{create,act,publish,destroy}`.

### Lock Pick

The Lock Pick card is in Attention. Its creation options are starting
rung, locks per run, and adaptive difficulty. Set option 3 to 1 to use
positive rung and trial counts outside the menu.

Space, Enter, or primary click starts a run. Hold Space or T for
tension, and hold the pointer under a pin to lift it. Space and T
have independent key-down and key-up state. The API key code for T
is 98. Feedback lasts 2.5 seconds.

`nw_api_v1_lock_pick_info` fields 0–9 report phase, rung, trial, trial
count, wins, best passing rung, starting rung, adaptive flag, verdict,
and simulation milliseconds. Fields 10–16 report pins set, pins
total, tension in thousandths, slips, the pressed-pointer flag,
held-tension key bits, and the pin under the pick. The key bits are
1 for Space and 2 for T. Verdicts 0–3 are active, turned lock,
slipped wrench, and approaching someone.

The web factory is `createLockPickEnvironment`. Ports 0–11 move the
pointer, 12 presses, 13 releases, and 14 latches tension for 250 ms.
The agent entry uses 15 to start and −1 to advance.
`nw_lock_pick_audio_window` writes signed 16-bit stereo PCM at 22,050 Hz.

SDL uses screen 117 for `--screen lock-pick`. It reads `PICK_RUNG`,
`PICK_TRIALS`, and `PICK_ADAPTIVE` and saves changes to the profile's
`.lock-pick-options` sidecar. The native library exports
`nw_lock_pick_agent_{create,act,publish,destroy}`.

### Air Hockey

The Air Hockey card is in Attention, after Lock Pick. It uses task ID
`1330898689`. Its creation options are starting rung, games per run,
and adaptive difficulty. Set option 3 to 1 to use positive rung and
trial counts outside the menu.

Space, Enter, or primary click starts a run. The pointer moves your
mallet. Left or A and Right or D slide the bar in your goal; the four
keys have independent key-down and key-up state, so releasing one
leaves the others held. Left takes precedence when both directions
are held. The API key codes for A and D are 99 and 100. Key repeats
are ignored. Feedback lasts 2.5 seconds.

`nw_api_v1_air_hockey_info` fields 0–9 report phase, rung, trial, trial
count, wins, best passing rung, starting rung, adaptive flag, verdict,
and simulation milliseconds. Fields 10–17 report your score, their
score, goals needed to win, goals against that lose, the
pressed-pointer flag, held bar-key bits, the bar position in
thousandths, and whether the camera is at the far end. The key bits
are 1 for Left, 2 for A, 4 for Right, and 8 for D. Verdicts 0–3 are
active, won, lost, and time.

The web factory is `createAirHockeyEnvironment`. Ports 0–11 move the
pointer, 12 presses, 13 releases, and 14 and 15 latch the bar left
and right for 250 ms. The agent entry uses 16 to start and −1 to
advance. `nw_air_hockey_audio_window` writes signed 16-bit stereo PCM
at 22,050 Hz.

SDL uses screen 118 for `--screen air-hockey`. It reads `HOCKEY_RUNG`,
`HOCKEY_TRIALS`, and `HOCKEY_ADAPTIVE` and saves changes to the
profile's `.air-hockey-options` sidecar. The native library exports
`nw_air_hockey_agent_{create,act,publish,destroy}`.

### Semaphore

The Semaphore card is in Attention, after Air Hockey. It uses task ID
`64710845`. Its creation options are starting rung, messages per run,
and adaptive difficulty. Set option 3 to 1 to use positive rung and
trial counts outside the menu.

Space, Enter, or primary click starts a run. Drag your flags by their
tips with the pointer, then type the letter the signal stands for.
Letters arrive as text events: A–Z and a–z are the same letter, and
anything else is ignored. A letter typed while your flags do not match
the signal, or a wrong letter, is a strike, and a signal is struck at
most once. Feedback lasts 2.5 seconds.

`nw_api_v1_semaphore_info` fields 0–9 report phase, rung, trial, trial
count, wins, best passing rung, starting rung, adaptive flag, verdict,
and simulation milliseconds. Fields 10–17 report letters read, letters
in the message, strikes, strikes allowed, the pressed-pointer flag, the
signalled letter's index (−1 when none is up), the held flag (−1 when
none), and the help shown now: 0 names the letter, 1 shows the chart,
and 3 shows nothing. At peek rungs the chart shows only early in each
signal. Verdicts 0–2 are active, passed, and failed.

The web factory is `createSemaphoreEnvironment`. Ports 0–11 move the
pointer, 12 presses, 13 releases, and 14–39 type A–Z. The agent entry
uses 40 to start and −1 to advance. `nw_semaphore_audio_window` writes
signed 16-bit stereo PCM at 22,050 Hz.

SDL uses screen 119 for `--screen semaphore`. Letter keys type their
letter during play, Q included. It reads `SEMA_RUNG`, `SEMA_TRIALS`,
and `SEMA_ADAPTIVE` and saves changes to the profile's
`.semaphore-options` sidecar. The native library exports
`nw_semaphore_agent_{create,act,publish,destroy}`.

### Shadow Puppets

The Shadow Puppets card is in Attention, after Semaphore. It uses task
ID `1903607369`. Its creation options are starting rung, figures per
run, and adaptive difficulty. Set option 3 to 1 to use positive rung and
trial counts outside the menu.

Space, Enter, or primary click starts a run. Dragging with the pointer
turns the figure. Q and E roll it while held. The two keys have
independent key-down and key-up state, and Q takes precedence when both
are held. The figure rolls 2 degrees for each advance while a key is
held, as the reference rolls once a frame. The API key codes for Q and E
are 101 and 102. Key repeats are ignored. Feedback lasts 2.5 seconds.

`nw_api_v1_shadow_puppets_info` fields 0–9 report phase, rung, trial,
trial count, wins, best passing rung, starting rung, adaptive flag,
verdict, and simulation milliseconds. Fields 10–17 report shadows cast,
shadows wanted, the hold in milliseconds, the pressed-pointer flag, the
held roll-key bits (1 for Q, 2 for E), the distance from the nearest
fit in thousandths of a degree, where the wanted shadow is shown (0 on
the wall, 1 on a card, 2 only named), and whether the figure is hidden.
Verdicts 0–2 are active, passed, and failed.

The web factory is `createShadowPuppetsEnvironment`. Ports 0–11 move the
pointer, 12 presses, 13 releases, and 14 and 15 roll the figure left
and right once. The agent entry uses 16 to start and −1 to advance.
`nw_shadow_puppets_audio_window` writes signed 16-bit stereo PCM at
22,050 Hz.

SDL uses screen 120 for `--screen shadow-puppets`. During play Q rolls
the figure instead of quitting. It reads `PUPPET_RUNG`,
`PUPPET_TRIALS`, and `PUPPET_ADAPTIVE` and saves changes to the
profile's `.shadow-puppets-options` sidecar. The native library exports
`nw_shadow_puppets_agent_{create,act,publish,destroy}`.

### Night Watch

The Night Watch card is in Attention, after Shadow Puppets. It uses task
ID `981902657`. Its creation options are starting rung, nights per run,
and adaptive difficulty. Set option 3 to 1 to use positive rung and
trial counts outside the menu.

Space, Enter, or primary click starts a run. The pointer moves the torch
and a primary click blows the whistle at whoever is under it. Left and
A turn the view one way along the floor, Right and D the other. The four
keys have independent key-down and key-up state, and a left key takes
precedence when both directions are held. The API key codes for A and D
are 99 and 100, shared with Air Hockey. Key repeats are ignored. As in
the reference, a released key keeps turning the view until its
quarter-second latch runs out; cancel, focus loss, and hiding the page
stop it at once. Feedback lasts 2.5 seconds.

`nw_api_v1_night_watch_info` fields 0–9 report phase, rung, trial, trial
count, wins, best passing rung, starting rung, adaptive flag, verdict,
and simulation milliseconds. Fields 10–17 report thieves caught, thieves
tonight, strikes, strikes allowed, the pressed-pointer flag, the held
turning-key bits (1 for Left, 2 for A, 4 for Right, 8 for D), whistle
blasts left, and the view's offset along the floor in thousandths.
Verdicts 0–5 are active, every thief caught, no whistle left, the wrong
one whistled at, the safe robbed, and dawn.

The web factory is `createNightWatchEnvironment`. Ports 0–11 move the
pointer, 12 presses, 13 releases, and 14 and 15 turn the view left and
right for one latch. The agent entry uses 16 to start and −1 to advance.
`nw_night_watch_audio_window` writes signed 16-bit stereo PCM at 22,050
Hz.

SDL uses screen 121 for `--screen night-watch`. It reads `WATCH_RUNG`,
`WATCH_TRIALS`, and `WATCH_ADAPTIVE` and saves changes to the profile's
`.night-watch-options` sidecar. The native library exports
`nw_night_watch_agent_{create,act,publish,destroy}`.

### Kerbside

The Kerbside card is in Attention, after Night Watch. It uses task ID
`1420277302`. Its creation options are starting rung, crossings per run,
and adaptive difficulty. Set option 3 to 1 to use positive rung and
trial counts outside the menu.

Space or primary click starts a run; Enter does not, as in the
reference. Up and W walk forward, Down and S step back. The four keys
have independent key-down and key-up state, and walking takes precedence
when both directions are held. The API key codes for W and S are 77 and
78. Key repeats are ignored. A released key stops the walker at once.
Cancel, focus loss, and hiding the page release all four. Feedback lasts
2.5 seconds.

`nw_api_v1_kerbside_info` fields 0–9 report phase, rung, trial, trial
count, wins, best passing rung, starting rung, adaptive flag, verdict,
and simulation milliseconds. Fields 10–17 report lanes, the walker's
place across the street in millimetres from the near lane line, the far
kerb in millimetres, the time limit in milliseconds, the held walking-key
bits (1 for Up, 2 for W, 4 for Down, 8 for S), the lane that struck the
walker (1-based, 0 if none), the number of cars, and the number of
parked vans. Verdicts 0–3 are active, across, struck, and still on the
street.

The web factory is `createKerbsideEnvironment`. Port 0 walks and port 1
steps back, for the frame they are sent in. The agent entry uses 2 to
start and −1 to advance. `nw_kerbside_audio_window` writes signed 16-bit
stereo PCM at 22,050 Hz. The window holds every car's engine, the wind,
and the verdict note. The sound is worked out from the run's log on
request. The session carries each track's phase forward between windows,
so playing forward costs only the new steps. Asking for an earlier window
recounts from the start.

SDL uses screen 122 for `--screen kerbside`. It reads `KERB_RUNG`,
`KERB_TRIALS`, and `KERB_ADAPTIVE` and saves changes to the profile's
`.kerbside-options` sidecar. The native library exports
`nw_kerbside_agent_{create,act,publish,destroy}`.

### Steadicam

The Steadicam card is in Attention, after Kerbside. It uses task ID
`2305084378`. Its creation options are starting rung, takes per run,
and adaptive difficulty. Set option 3 to 1 to use positive rung and
trial counts outside the menu.

Space or primary click starts a run; Enter does not, as in the
reference. Left and A pan left, Right and D pan right, Up and W tilt
up, Down and S tilt down, E zooms in and Q zooms out. The ten keys have
independent key-down and key-up state. When several are held, the first
in that order steers, as in the reference's key poll. The API key codes
for W, S, A, D, Q, and E are 77, 78, 99, 100, 101, and 102. Key repeats
are ignored. During a take, dragging with the primary button pans by
the field of view over 900 for each reference pixel across and tilts by
as much for each pixel up. The wheel zooms by a factor of exp(−0.08)
per notch up. Cancel, focus loss, and hiding the page release every key
and end a drag. Feedback lasts 2.5 seconds.

`nw_api_v1_steadicam_info` fields 0–9 report phase, rung, trial, trial
count, wins, best passing rung, starting rung, adaptive flag, verdict,
and simulation milliseconds. Fields 10–17 report yaw, pitch, and field
of view in thousandths of a radian, the share of the counted time framed
in percent, the held camera-key bits (1 Left, 2 A, 4 Right, 8 D, 16 Up,
32 W, 64 Down, 128 S, 256 E, 512 Q), whom to follow, whether that
person is in the box now, and the number of people. Verdicts 0–3 are
active, passed, framed too little, and lost for three seconds.

The web factory is `createSteadicamEnvironment`. Ports 0–5 pan left and
right, tilt up and down, and zoom in and out, for the frame they are
sent in. The agent entry uses 6 to start and −1 to advance.
`nw_steadicam_audio_window` writes signed 16-bit stereo PCM at 22,050
Hz: the bell when the person to follow changes.

SDL uses screen 123 for `--screen steadicam`. It reads `STEADY_RUNG`,
`STEADY_TRIALS`, and `STEADY_ADAPTIVE` and saves changes to the
profile's `.steadicam-options` sidecar. During a take, Q zooms out
instead of acting as a shell shortcut. The native library exports
`nw_steadicam_agent_{create,act,publish,destroy}`.

### Free Kick

The Free Kick card is in Attention, after Steadicam. It uses task ID
`3503424810`. Its creation options are starting rung, kicks per run,
and adaptive difficulty. Set option 3 to 1 to use positive rung and
trial counts outside the menu.

Space or primary click starts a run; Enter does not, as in the
reference. During a round Space kicks, at once. Left and Right turn the
aim, Up and Down raise and lower it, A and D curl the ball, and W and S
kick harder and softer. The eight keys have independent key-down and
key-up state. When several are held, the first in that order turns its
dial, as in the reference's key poll. The API key codes for A, D, W, and
S are 99, 100, 77, and 78. Key repeats are ignored. The dials stop at
once when their key is released. Cancel, focus loss, and hiding the page
release every key. The dials do nothing once the ball is kicked.
Feedback lasts 2.5 seconds.

`nw_api_v1_free_kick_info` fields 0–9 report phase, rung, trial, trial
count, wins, best passing rung, starting rung, adaptive flag, verdict,
and simulation milliseconds. Fields 10–17 report the aim, height, curl,
and power dials in thousandths (degrees, degrees, curl, and metres a
second), the held dial-key bits (1 Left, 2 Right, 4 Up, 8 Down, 16 A,
32 D, 64 W, 128 S), whether the ball is kicked, how far a goal missed
the ring in millimetres, and the ball's distance from the goal line in
millimetres. Verdicts 0–8 are active, in the ring, into the wall, fell
short, wide of the goal, over the bar, saved, in the goal but off the
ring, and out of time.

The web factory is `createFreeKickEnvironment`. Ports 0–7 turn the
dials for the frame they are sent in: aim left and right, raise, lower,
curl left and right, harder, and softer. Port 8 kicks at once. The agent
entry uses 9 to start and −1 to advance. `nw_free_kick_audio_window`
writes signed 16-bit stereo PCM at 22,050 Hz: the thud of the kick, then
a bell for a ball in the ring or a growl for any other ending.

SDL uses screen 124 for `--screen free-kick`. It reads `KICK_RUNG`,
`KICK_TRIALS`, and `KICK_ADAPTIVE` and saves changes to the profile's
`.free-kick-options` sidecar. The native library exports
`nw_free_kick_agent_{create,act,publish,destroy}`.

### Glove

The Glove card is in Attention, after Free Kick. It uses task ID
`4083731742`. Its creation options are starting rung, innings per run,
and adaptive difficulty. Set option 3 to 1 to use positive rung and
trial counts outside the menu.

Space or primary click starts a run; Enter does not, and Space does
nothing during an inning, as in the reference. Up or W, Down or S, Left
or A, and Right or D move the glove the way the screen shows up, down,
left and right. The eight keys have independent key-down and key-up
state. When several are held, Up or W wins, then Down or S, then Left or
A, as in the reference's key poll. The API key codes for W, S, A, and D
are 77, 78, 99, and 100. Key repeats are ignored. Cancel, focus loss,
and hiding the page release every key. Every pointer move during an
inning, pressed or not, carries the glove's picture by as much as the
pointer moved, at most 0.25 m a move. Feedback lasts 2.5 seconds.

`nw_api_v1_glove_info` fields 0–9 report phase, rung, trial, trial
count, wins, best passing rung, starting rung, adaptive flag, verdict,
and simulation milliseconds. Fields 10–17 report the glove's x and y in
millimetres, the view, the catches, the misses, the held key bits (1 Up,
2 W, 4 Down, 8 S, 16 Left, 32 A, 64 Right, 128 D), the next pitch, and
the pitch in flight (−1 for none). Verdicts 0–2 are active, caught and
missed.

The web factory is `createGloveEnvironment`. Ports 0–3 move the glove
up, down, left and right for the frame they are sent in. The agent entry
uses 4 to start and −1 to advance. `nw_glove_audio_window` writes signed
16-bit stereo PCM at 22,050 Hz: the thud of a catch or the growl of a
miss.

SDL uses screen 125 for `--screen glove`. It reads `GLOVE_RUNG`,
`GLOVE_TRIALS`, and `GLOVE_ADAPTIVE` and saves changes to the profile's
`.glove-options` sidecar. The native library exports
`nw_glove_agent_{create,act,publish,destroy}`.

### By Ear

The By Ear card is in Perception, after Captcha. It uses task ID
`2841258479`. Its creation options are starting rung, melodies per run,
and adaptive difficulty. Set option 3 to 1 to use positive rung and
trial counts outside the menu.

Space or primary click starts a run; Enter does not, and Space does
nothing during a try. The tune plays first, and keys pressed while it
plays do nothing. Then the keys A W S E D F T G Y H U J K, API key codes
103–115, play the keys from C to the C above at once, as does a primary
click on a key in play; the black keys are hit first where they cover
the white. No key is held: key-up events are ignored. Feedback lasts
2.5 seconds.

`nw_api_v1_by_ear_info` fields 0–9 report phase, rung, trial, trial
count, wins, best passing rung, starting rung, adaptive flag, verdict,
and simulation milliseconds. Fields 10–17 report the steps played back,
the steps in the tune, the bits of the keys of a pair pressed so far,
the lit first key (−1 for none), whether the tune is still playing, the
keys pressed, and when the tune ends and when the try runs out, in
milliseconds. Verdicts 0–4 are active, all played back, a wrong note,
a pair's keys too far apart, and too slow.

The web factory is `createByEarEnvironment`. Ports 0–12 press the keys
from C to C at once. The agent entry uses 13 to start and −1 to advance.
`nw_by_ear_audio_window` writes signed 16-bit stereo PCM at 22,050 Hz:
the tune, each key pressed, and the verdict's note.

SDL uses screen 126 for `--screen by-ear`. It reads `EAR_RUNG`,
`EAR_TRIALS`, and `EAR_ADAPTIVE` and saves changes to the profile's
`.by-ear-options` sidecar. The native library exports
`nw_by_ear_agent_{create,act,publish,destroy}`.

### Piano Tuner

The Piano Tuner card is in Perception, after By Ear. It uses task ID
`994919917`. Its creation options are starting rung, strings per run,
and adaptive difficulty. Set option 3 to 1 to use positive rung and
trial counts outside the menu.

Space or primary click starts a run. In play, Space or Enter says the
string is in tune at once; Enter does not start a run. Up or W and Down
or S, API key codes 4, 77, 6 and 78, are held keys that turn the pin up
and down, 60 cents a second, or 5 while Shift (code 24) is held too. A
key-up lets each go on its own. A pointer move with the primary button
down (value bit 1) after a primary press turns the pin 0.4 cents a
pixel up; a move without it, or a primary release, ends the drag.
Feedback lasts 2.5 seconds.

`nw_api_v1_piano_tuner_info` fields 0–9 report phase, rung, trial, trial
count, wins, best passing rung, starting rung, adaptive flag, verdict,
and simulation milliseconds. Fields 10–17 report the string being
tuned, the strings in the try, the strings tuned, the error in
thousandths of a cent (sharp positive), the pin's angle in thousandths
of a degree, the held-key bits (Up 1, W 2, Down 4, S 8, Shift 16), the
tolerance in thousandths of a cent, and the interval being tuned
(unison, octave, fifth, fourth, major third). Verdicts 0–4 are active,
in tune, sharp, flat, and out of time.

The web factory is `createPianoTunerEnvironment`. Ports 0–3 turn the pin
up and down quickly and slowly for the step they are sent in; port 4
says it is in tune at once. The agent entry uses 5 to start and −1 to
advance. `nw_piano_tuner_audio_window` writes signed 16-bit stereo PCM
at 22,050 Hz: the reference and the string, six partials each, sliding
between settings, and the bell or wood note of each judgment.

SDL uses screen 127 for `--screen piano-tuner`. It reads `TUNE_RUNG`,
`TUNE_TRIALS`, and `TUNE_ADAPTIVE` and saves changes to the profile's
`.piano-tuner-options` sidecar. The native library exports
`nw_piano_tuner_agent_{create,act,publish,destroy}`.

### Cricket Hunt

The Cricket Hunt card is in Perception, after Piano Tuner. It uses task
ID `3655954588`. Its creation options are starting rung, hunts per run,
and adaptive difficulty. Set option 3 to 1 to use positive rung and
trial counts outside the menu.

Space or primary click starts a run, and in play Space grabs at once.
W or Up and S or Down walk, A or Left and D or Right turn, and Q and E
look up and down; they are held keys, API key codes 77, 4, 78, 6, 99,
3, 100, 5, 101 and 102, each let go on its own key-up. When several are
down the first of that list moves. A pointer move with the primary
button down (value bit 1) after a primary press turns the head 0.006
radians a pixel right and up; a move without it, or a primary release,
ends the drag. Feedback lasts 2.5 seconds.

`nw_api_v1_cricket_hunt_info` fields 0–9 report phase, rung, trial,
trial count, wins, best passing rung, starting rung, adaptive flag,
verdict, and simulation milliseconds. Fields 10–17 report crickets
caught, crickets in the room, grabs at nothing, the position x and z,
the heading and the look's pitch (each in thousandths of a metre or
radian), and the held-key bits (W 1, Up 2, S 4, Down 8, A 16, Left 32, D
64, Right 128, Q 256, E 512). Verdicts 0–3 are active, all caught, out
of time, and three grabs at nothing.

The web factory is `createCricketHuntEnvironment`. Ports 0–5 walk forward
and back, turn left and right, and look up and down for the step they
are sent in; port 6 grabs at once. The agent entry uses 7 to start and
−1 to advance. `nw_cricket_hunt_audio_window` writes signed 16-bit
stereo PCM at 22,050 Hz: each cricket's gated chirp, panned and
brightened as it is heard, the room's hum, and the notes of hops,
catches and misses.

SDL uses screen 128 for `--screen cricket-hunt`. Q looks up during play
instead of quitting. It reads `CRICKET_RUNG`, `CRICKET_TRIALS`, and
`CRICKET_ADAPTIVE` and saves changes to the profile's
`.cricket-hunt-options` sidecar. The native library exports
`nw_cricket_hunt_agent_{create,act,publish,destroy}`.

### Claw Machine

The Claw Machine card is in Perception, after Cricket Hunt. It uses task
ID `2783635748`. Its creation options are starting rung, drops per run,
and adaptive difficulty. Set option 3 to 1 to use positive rung and
trial counts outside the menu.

Space or a primary press starts a run; Enter does not. In play Space
or Enter drops the claw, once a try. Left or A and Right or D move the trolley
across, and Up or W and Down or S move it in and out; they are held
keys, API key codes 3, 99, 5, 100, 4, 77, 6 and 78, each let go on its
own key-up. A pointer does nothing else. Feedback lasts 2.5 seconds.

`nw_api_v1_claw_machine_info` fields 0–9 report phase, rung, trial,
trial count, wins, best passing rung, starting rung, adaptive flag,
verdict, and simulation milliseconds. Fields 10–17 report whether the
claw was dropped, its depth, the trolley's x and z, the swing's offsets
x and z (each in thousandths of a metre), the prizes in the cabinet, and
the held-key bits (Left 1, A 2, Right 4, D 8, Up 16, W 32, Down 64, S
128). Verdicts 0–7 are active, got it, not the gold one, too far in, not
far enough in, to the right, to the left, and out of time.

The web factory is `createClawMachineEnvironment`. Ports 0–3 move the
trolley left, right, in and out for the step they are sent in; port 4
drops. The agent entry uses 5 to start and −1 to advance.
`nw_claw_machine_audio_window` writes signed 16-bit stereo PCM at
22,050 Hz: the run's notes (the knock of the drop, then a bell or a
growl) through the shared note synth.

SDL uses screen 129 for `--screen claw-machine`. It reads `CLAW_RUNG`,
`CLAW_TRIALS`, and `CLAW_ADAPTIVE` and saves changes to the profile's
`.claw-machine-options` sidecar. The native library exports
`nw_claw_machine_agent_{create,act,publish,destroy}`.

### The Cipher Abyss

The Cipher Abyss uses task ID `1865539977`. Create options 0–2 are the
starting rung, machines per run, and adaptive difficulty. Option 3
allows positive integer rung and trial counts beyond the menu. Option
4 enables the first-rung tutorial, and option 5 is zero.

Space, Enter, or a primary click starts a run. Keys 1–8 enter symbols,
Backspace deletes, and Enter runs an experiment or submits a test
answer. Up, Down, Space, and Z control the hypothesis board. Logical
codes 89–97 are T (test), C (check), S (submit), P (predict), PageUp,
PageDown, M (mark), N (numbers), and O (sort). X downloads the notebook
in the browser. Interactive feedback lasts nine seconds.

`nw_api_v1_cipher_abyss_info` fields 0–9 are phase, current rung,
trial, trial count, wins, best passing rung, starting rung, adaptive
flag, verdict, and simulation milliseconds. Fields 10–12 are machine
kind, experiment count, and the zero-based test index.

`nw_cipher_abyss_record` writes UTF-8 bytes to a caller-provided
buffer. Kind 0 exports the current notebook once the run starts,
kind 1 returns one newline-terminated JSON record during feedback,
and kind 2 returns the version-one operator library.
`nw_cipher_abyss_load_library` accepts that JSON while ready or after
a session ends. The browser stores the operator library, round records,
and tutorial state locally.
`nw_cipher_abyss_audio_window` writes interleaved signed 16-bit stereo
PCM at 22,050 Hz for a run-relative window.

The web factory is `createCipherAbyssEnvironment`. Agent ports 0–11
move the pointer, 12 presses, 13 releases, and 14–21 enter symbols.
Ports 22–36 perform delete, run, test, next block, previous block,
add block, undo block, check, submit, predict, scroll up, scroll down,
mark, numbers, and sort. The agent entry uses 37 to start and −1 to
advance.

SDL uses screen 111 for `--screen cipher-abyss`. The profile loader
reads `CIPHER_RUNG`, `CIPHER_TRIALS`, and `CIPHER_ADAPTIVE`. Changes
use the selected profile’s `.cipher-abyss-options` sidecar. Visible
sessions use the original data directory for the tutorial marker,
`cipher_abyss_library.json`, `cipher_abyss_rounds.jsonl`, and the X shortcut’s
`cipher_abyss_notebook.txt`. The native library exports
`nw_cipher_abyss_agent_{create,act,publish,destroy}`.

### Dam Keeper

Dam Keeper uses task ID `2780310580`. Create options 0–2 select the
starting rung, valleys per run, and adaptive difficulty. Option 3 enables
positive integer dials beyond the interactive options menu. Options 4
and 5 are zero.

Action ports 0–5 adjust the gates in open/shut pairs, one pair per dam.
Logical key codes 26–31 map to Q, A, W, S, E, and D in the same order.
Action port 6 and Space start or restart the run. A primary pointer press
on the upper half of a gate opens it a notch. A press on the lower half shuts it a notch. Interactive advance
clamps each simulation update to 100 ms and displays feedback for 3 seconds.

`nw_api_v1_dam_keeper_info` fields 0–10 return phase, rung, valley number,
valleys per run, simulation milliseconds, dam count, verdict, fault dam
index, valleys passed, highest rung passed, and feedback deadline in
milliseconds. The verdict, fault dam, and deadline are available during
feedback. `nw_dam_keeper_options_note` writes the starting-rung preview
as UTF-8.

SDL uses screen 86 for `--screen dam-keeper` and exposes the same fields
in `--dump`. It reads `DAMKEEPER_RUNG`, `DAMKEEPER_TRIALS`, and
`DAMKEEPER_ADAPTIVE` from the profile and saves edits to the profile’s
`.dam-keeper-options` sidecar.

The browser's `createDamKeeperEnvironment` starts automatically. It
uses `nw_dam_keeper_agent_event` with the virtual clock in seconds.
Port -1 advances the clock even when no gate moves. The frame that
settles a valley carries the verdict. The next stepped frame opens
the next valley or reports completion. The six action ports remain
available on two-dam valleys, with the third dam's ports acting as no-ops.
The native library provides `nw_dam_keeper_agent_create`,
`nw_dam_keeper_agent_act`, `nw_dam_keeper_agent_publish`, and
`nw_dam_keeper_agent_destroy` through the same receipt and frame ABI
used by the other clocked agents.

### Glider

Glider uses task ID `3159511168`. Create options 0–2 select the
starting rung, flights per run, and adaptive difficulty. Space
starts from ready or done and holds lift during flight. Up also
holds lift. Focus loss and cancellation release lift. Agent port 0
holds lift for one frame.

`nw_api_v1_glider_info` exposes phase, rung, flight number, total,
elapsed milliseconds, height in thousandths of a canyon unit, walls
passed, verdict, flights passed, highest rung passed, verdict deadline
in milliseconds, vertical velocity in thousandths of a canyon unit
per second, wall count, lift state, and the collided wall number.


### Catch

Catch uses task ID `1116268876`. Create options 0–2 select the
starting rung, rounds per run, and adaptive difficulty. Keys and
pointer moves update held directions and floor aim. Focus loss and
cancellation release held directions.

Ports 0–3 move the first basket left, right, nearer, and farther.
Ports 4–7 use the same order for the second basket. WASM
`nw_catch_agent_mask` and native `nw_catch_agent_act_mask` accept
one bit per port and apply the selected inputs together for one
frame. Browser receipts include the selected port numbers. In a
native verdict tied to a mask action, `action_port` is 256 plus
the submitted mask. Single-port calls keep their usual port number.

`nw_api_v1_catch_info` exposes phase, rung, round, rounds per run,
elapsed milliseconds, catches, drops, verdict, rounds passed,
highest rung passed, verdict deadline in milliseconds, ball count,
basket count, then each basket's X and Z in thousandths of a court
unit. `nw_catch_audio` reads elapsed 22,050 Hz stereo signed
16-bit little-endian PCM.


### Echo Cave

Echo Cave uses task ID `2392810020`. Create options 0–2 select
the starting rung, flights per run, and adaptive difficulty. Space
starts from ready or done and clicks during flight. Arrow keys
and pointer moves control steering. Focus loss and cancellation
clear held directions and mouse aim.

Ports 0–7 steer up, down, left, right, up-left, up-right, down-left,
and down-right. Port 8 clicks. WASM `nw_echo_cave_agent_mask` and
native `nw_echo_cave_agent_act_mask` accept one bit per port. A native
verdict tied to a mask action reports `action_port` as 512 plus the
mask. The native and WASM agent audio calls expose elapsed 22,050 Hz
stereo signed 16-bit little-endian PCM. `nw_echo_cave_speaker_audio`
applies the interactive speaker delay.

`nw_api_v1_echo_cave_info` exposes phase, rung, flight number, total,
elapsed milliseconds, moths caught, moths needed, verdict, flights
passed, highest rung passed, verdict deadline in milliseconds, X, Y,
depth, visible distance in thousandths of a cave unit, and cue count.

### Camera

The Camera render bridge uses task ID `2663290958`, returned by
`nw_api_v1_task_camera`. Create options 0–2 select the starting rung, number
of photos, and adaptive difficulty. Options 3–5 are zero. The run uses
the common create, dispatch, advance, and destroy calls.

Action codes 0–29 are the ten movement ports, with three step sizes per
movement. Code 30 submits a match and 31 starts a run. Codes 32–41 hold
a movement and 42–51 release it, in the same order as the stepped ports.
Codes 52 and 53 toggle slow movement and photo peek using value 0 or 1.
Code 54 clears controls, as do cancellation, blur, and hidden-page
events. Code 55 accepts horizontal and upward-positive vertical drag
deltas in thousandths of a logical pixel.

`nw_camera_info` fields 0–9 return the phase, current scene rung, trial
number, total trials, stepped inputs, scored trials, matches, best
matched rung, peek flag, and deal failure flag.

`nw_camera_frame` writes the shared `NWCF` frame packet for physical
canvas dimensions. It returns the byte length, zero when there is no
scene or drawable viewport, or a negative protocol error.
`nw_camera_mesh` writes a shared `NWCM` indexed mesh for a requested kind
and field size. Both write into caller-owned WASM memory. The browser
renderer reads scene and mesh packets synchronously and copies decoded
values before reusing the same buffer.

`nw_camera_chrome` writes a display list in the same canvas pixel
coordinates as the scene packet. Hosts composite the 3D scene first
and draw this list over it. The display list also covers ready and
completed runs, which have no 3D scene.

`nw_camera_options_note` writes the source-compatible starting-rung
description as UTF-8 given the rung and adaptive flag.
