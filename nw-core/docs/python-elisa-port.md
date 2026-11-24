# Python desktop to Elisa migration inventory

Status: in progress. Existing SDL/Elisa routes are candidates for reuse; their presence alone does not prove Python feature parity. The Python desktop remains the behavioral reference until each item has independent evidence.

## Python runtime inventory

- `shells/python/app.py`: session lifecycle, command-line parsing, task hub, keyboard/text/mouse/focus events, window lifecycle, screenshot and dump modes, background selection, and task-specific timing and options.
- `shells/python/renderer.py`: display-list planning, viewport and pixel-ratio conversion, text, shapes, sprites, and pyglet rendering.
- `shells/python/marble_mujoco.py`: board decoding, MJCF construction, MuJoCo simulation, held inputs, collision outcomes, reset and cleanup.
- `shells/python/marble_geometry.py`: board, wall, hole and marble meshes and stage layout.
- `shells/python/marble_native_renderer.py`: OpenGL 3D rendering, shaders, textures, shadow and color targets, camera, resize and resource lifecycle.
- Python shell tests and `scripts/test_marble_native_python.sh` provide reference cases. Build and packaging currently include `scripts/build_pymodule.sh` and a Python extension; the SDL desktop uses `scripts/build_sdl3.sh` and native Elisa exports.

## Session parity checklist

For each session, compare defaults and CLI, lifecycle and hub navigation, input including release/focus, timers, state/results, frame content and cleanup. Existing native controllers and SDL input routes reduce implementation work but are not acceptance evidence by themselves.

- [ ] TitleSession
- [ ] NBack3DSession
- [ ] MarbleMazeSession
- [ ] YouAreHereSession
- [ ] SokobanSession
- [ ] MonkeyLadderSession
- [ ] TetrisSession
- [ ] CountSession
- [ ] MrTimeSession
- [ ] GraphMappingSession
- [ ] MatrixReasoningSession
- [ ] InTheDarkSession
- [ ] FogOfWarSession
- [ ] RemovalsSession
- [ ] CustodySession
- [ ] ConcentrationSession
- [ ] RecognitionSession
- [ ] TriviaSession
- [ ] ReflexSession
- [ ] AlgebraSession
- [ ] SyllogismSession
- [ ] NumberologySession
- [ ] JigsawSession
- [ ] SudokuSession
- [ ] GoSession
- [ ] ScrambleSession
- [ ] ScrabbleSession
- [ ] CrosswordSession
- [ ] CrossedWiresSession
- [ ] TrackingSession
- [ ] LookoutSession
- [ ] PursuitSession
- [ ] OutOfSightSession
- [ ] BuzzWireSession
- [ ] DonkeySession
- [ ] TwoHandsSession
- [ ] OverrunSession
- [ ] NCupMonteSession
- [ ] TaskHubSession

## Cross-cutting acceptance checklist

- [ ] Inventory and compare every command-line flag, validation, exit code, dump and screenshot mode.
- [ ] Match display-list primitives, assets, text, viewport, DPI and resize behavior across representative screens.
- [ ] Port and verify native Marble 3D geometry, rendering, MuJoCo FFI simulation, input and cleanup; the existing SDL route must not be assumed equivalent to Python's OpenGL and physics implementation.
- [ ] Preserve settings, results, corpus paths, error handling and existing saved data across both applications.
- [ ] Verify startup, task switching, teardown, repeated sessions, resource ownership and failure paths.
- [ ] Provide a packaged executable for each supported platform without requiring Python at runtime, with required native dependencies and licenses.
- [ ] Run source-versus-port replays, renderer comparisons and platform tests, then the full applicable build gates using a source-fresh compiler. Keep browser checks headless.

Each item stays open until its implementation and evidence cover the full behavior, including failures and platform differences.

## Current original task hub inventory

The Python task hub at reference commit `efd8be5760c0` lists 146 cards
across 12 categories. The Elisa browser registry has routes for 140 of
those cards, counting 3D N-Back as the route for the N-Back card. These
6 cards still need browser routes, all under Computer use. The Elisa hub already has that tab, after Decisions, and says it has no card yet.

- [ ] Computer use — Desktop, Forms, Manual, Browser, Errands, Spreadsheet

N-Back variants beyond the existing 3D mode are tracked as additional
capabilities of that card. Route counts track menu availability. The
cross-cutting checklist tracks platform, data, and feature parity.

### Task port details

Crazy Cog has an Elisa generator, gear-train simulation, drag controls, reference player, and PCM renderer. Python comparisons cover 14,000 seeded candidates across five board depths, 25,408 ticks, and 15 stereo PCM windows. An Elisa scene and session now handle layered rendering, dragging, the feedback interval, and adaptive scoring. A headless replay compares 14 frames against the Python task. The browser and SDL routes include settings, keyboard and pointer controls, PCM playback, and stepped agent access. SDL reads the original profile settings and saves changes to its profile sidecar. The SDL replay verifies menu launch, settings, layer shortcuts, dragging, and PCM output on macOS.

The Cipher Abyss has an Elisa rule interpreter and difficulty progression. A Python differential covers 163 rungs and 13,188 interpreter, notation, and rule-family cases, including state replay, formal notation round-trips, plain-language descriptions, canonical forms, seeded probes, and behavioral deduplication. The rule-family generator and reference player also match the Python source across 27 rungs, 229,233 ordered rules, 4,348 one-look rival sets, 18 experiments, and 15 test answers. Round generation now covers crack, twins, and inverse machines, including the reference-player check. Python comparisons cover 72 question selections, 108 machine candidates, and eight complete deals. For repeatable cross-host deals, Elisa uses the CPython zero hash seed for twin probes and a stable order for the inverse opponent sample. The Elisa gameplay controller includes experiments, predictions, the hypothesis board, the three test modes, notebook controls, synthesized audio, and adaptive sessions. Python comparisons cover 148 gameplay actions, 36 byte-identical stereo PCM windows, and nine round records and notebook exports. A two-round test verifies feedback timing and adaptation after a win and a loss. The Elisa scene renders the machine, hypothesis board, notebook, controls, tutorial steps, and feedback chart. Headless display-list checks cover start, test, notebook highlighting, and results, and all nine starting-rung descriptions match Python. Pointer marking follows the displayed newest-first notebook order. The web route provides settings, input, audio, tutorial state and round history in browser storage, and notebook download. A headless WebAssembly replay completes the seeded Python machine, checks the exported notebook and metrics, and verifies adaptation. A separate browser-shell test exercises storage, download, and disposal through the page’s JavaScript. SDL launches from Reasoning or with `--screen cipher-abyss`, reads the original profile settings, and saves the notebook, tutorial marker, and round records to the workshop data directory. A dummy-driver replay completes the seeded round and verifies the saved files and audio. The native 37-port agent replay verifies the same win through the raster outcome and receipt. The browser and SDL read the original version-one operator library format and update the lowest rung for each operator after a win. The feedback scene recalls matching earlier operators, with a Python differential covering nested rules, minima, and recall order.

Potter’s Wheel has an Elisa difficulty ladder, seeded pot generation,
clay shaping, drying, wheel controls, reference player, and audio.
The Python differential covers 81 grades, ten seeded deals, 9,392
simulation steps, 1,212 cues, and 30 byte-identical stereo PCM windows.
The Elisa scene and session match the Python drawing calls, timed target,
mouse controls, and two-round difficulty changes. The web route includes
profile settings, pointer and keyboard input, PCM audio, and the 17-port
stepped environment. SDL launches from Attention or via
`--screen potters-wheel` and reads the original `POTTER_*` profile values.
A dummy-driver replay covers saved options, wheel keys, pointer shaping,
audio, and feedback. The native agent verifies a collapse from the
rendered verdict pixels.

Conductor has an Elisa difficulty ladder, seeded scores, baton flicks,
section and volume cues, reference player, and stereo synthesis.
Its Python replay covers 81 grades, eleven pieces, 8,867 simulation
steps, 533 notes, and 33 stereo PCM windows. The windowless scene replay
matches the Python stage, baton, pulse, cue display, and feedback. Web and
SDL launch from Attention and include saved options, pointer and keyboard
input, audio, adaptive rounds, and the 16-port agent. SDL reads the
original `CONDUCT_*` settings and saves edits to its profile sidecar.

Tightrope has an Elisa difficulty ladder, seeded gusts and birds, pole lag,
lateral and fore-aft balance, wire motion, reference player, and stereo
synthesis. Its Python replay covers 81 grades, 13 walks, 6,528 steps,
158 notes, and 39 stereo PCM windows. The windowless scene replay
compares the city, walker, pole, wind, perched birds, and balance display
against the Python drawing code. The web and SDL controllers use the
same Elisa scene, simulation, and audio. SDL reads the original
`ROPE_*` settings and saves edits to the selected profile's sidecar.

Sign Painter ports the 20 original words and their stroke geometry, the
swinging board, brush drag, pigment and smudge rules, timeouts, and
five sound cues. The Python replay covers 81 grades, 192 seeded layouts,
3,969 simulation steps, 402 cues, and 36 stereo PCM windows. The
windowless scene replay compares the board, guides, painted strokes,
palette, paint gauge, and smudge indicators. The web and SDL routes
share the Elisa controller, scene, and audio. SDL reads the original
`SIGN_*` settings and writes changes to the selected profile's sidecar.

Bartender ports seeded orders, repeat customers, bottle grabbing,
pouring, ice, the glass slide, and the original verdicts. The Python
replay covers 81 grades, 332 orders from a rung-1000 night, 27,039
simulation steps, 870 cues, and 45 stereo PCM windows. The windowless
scene replay compares the bar, glass and pewter mug, customers, order
timers, and adaptive feedback. Web and SDL share the Elisa controller
and scene. SDL reads the original `BAR_*` settings and saves edits to
the selected profile's sidecar.

Lock Pick ports the pin heights and binding order, tension latch, pin
drop, jams, false clicks, slips, and timeout. The Python replay covers
81 grades, 8,383 simulation steps, 160 cues, and 42 stereo PCM windows.
The windowless scene replay compares the pins and springs, pick,
tension gauge, hidden-pin mode, and adaptive feedback. Web and SDL
track Space and T separately and release controls on focus loss.
SDL reads the original `PICK_*` settings and saves edits to the
selected profile's sidecar.

Air Hockey ports the puck, both mallets, the opponent, the keeper bar,
goals and scores, the swinging camera, the far-end views, and timeout.
The Python replay covers 93 cases, 26,125 simulation steps, 1,510 cues,
and 36 stereo PCM windows. The windowless scene replay compares the
table, puck and mallets, the serve blink, the bar, the far-end camera,
the score, the verdict, and the options notes. Web and SDL track Left,
A, Right, and D separately and release controls on focus loss. SDL
reads the original `HOCKEY_*` settings and saves edits to the selected
profile's sidecar.

Semaphore ports the signaller and their flags, the deal of messages, the
shuffled code, the chart and its peek, the signaller turning their back,
fog on a rolling ship, your flags and their grips, strikes, and both
kinds of verdict. The Python replay covers 94 cases, 29,694 simulation
steps, 11 strikes, 141 cues, and 36 stereo PCM windows. The windowless
scene replay compares nine frames and eleven options notes, including
the reference's `%.1f` rounding of 4.65 seconds as 4.7. Web takes
letters as text events and SDL as key-downs; in both, C opens the
options only outside play and Q is a letter during play. SDL reads the
original `SEMA_*` settings and saves edits to the selected profile's
sidecar.

Shadow Puppets ports the figure of blocks, its 24 square stances, the
shadow it throws, the deal of wanted shadows, dragging and rolling the
figure, the hold, and the timeout. Python sums with its compensated
float `sum`, and a plain left-to-right sum differs in the last bit often
enough to change a run, so the port repeats that sum exactly. The Python
replay covers 117 cases and 7,025 simulation steps, matching the
figure's matrix and its distance from the fit bit for bit, plus 298 cues
and 33 stereo PCM windows. The windowless scene replay compares ten
frames and eleven options notes. Web and SDL hold Q and E separately,
roll once a frame as the reference's held-key poll does, and release
both on focus loss; in SDL, Q during play rolls rather than quits. SDL
reads the original `PUPPET_*` settings and saves edits to the selected
profile's sidecar.

Night Watch ports the grade table, the deal of thieves, guards and the
cat with their colours and paths, the torch and whistle, the view turned
along a floor wider than the screen, the walkers' footsteps, and every
ending. Python's `min` and `max` keep the first of equal arguments, so
the view can sit at -0.0; the port keeps that sign. The Python replay
covers 94 cases and 15,410 simulation steps, matching the view, the
turning latches, each walker's place and next footstep, and who is lit
bit for bit, plus 585 cues and 39 stereo PCM windows. The windowless
scene replay compares eleven frames and eleven options notes. Web and
SDL hold Left, A, Right, and D separately; a released key's latch runs
out by itself after a quarter second, as the reference's does, and
focus loss clears it at once. SDL reads the original `WATCH_*` settings
and saves edits to the selected profile's sidecar.

Kerbside ports the grade table, the deal of cars and parked vans with the
reference's own checks (both autopilot crossings and the thirteen
walkers who do not listen), walking and stepping back, the autopilot,
and `livesound`'s tracks: one per car and one for the wind. Each car's
pitch, loudness in each ear and phase match the reference. The reference
sets every track every step, which runs to millions of settings at the
high rungs. The port instead logs each step's time and the walker's
place, and works each setting out again when a window of sound is asked
for. `livesound`'s noise table draws every entry from a fresh
`random.Random(7)`, so the reference's noise is one steady value; the
port keeps it so. The Python replay covers 53 cases and 24,125
simulation steps bit for bit, plus 48 stereo windows of live sound. The
windowless scene replay compares 25 streets and nine options notes. The
web smoke test also checks three windows of a wasm run's sound against
`kerbside.mix` by hash. Web and SDL hold Up, W, Down, and S separately.
SDL reads the original `KERB_*` settings and saves edits to the selected
profile's sidecar.

Steadicam ports the grade table, the park's walkers, trees and cues,
the camera with its heavy head, lead room and zoom, the framing rule,
the bell on each cue, and the autopilot. A shared `SceneLens` module
holds the reference's pinhole camera and its clipped faces, lines,
discs and balls. The Python replay covers 41 grades, 13 parks and their
takes: 18,877 path points and 42,922 steps bit for bit. The windowless
scene replay compares 25 viewfinders, 341 clipped polygons, and nine
options notes. The web smoke test steers a two-person take key by key
the way the reference's autopilot does. Whom to follow, the verdict and
the camera end where the reference's do, and a bell sounds on each cue.
Web and SDL hold the ten camera keys separately and take a primary-button
drag and the wheel. SDL reads the original `STEADY_*` settings and saves
edits to the selected profile's sidecar.

Free Kick ports the grade table, the ball's flight (drag, the spin's
bend, the wind, the bounce, the wall and the line), the judge and the
keeper's reach, the Newton search for an aim and a lift, the plan, the
deal with its own trial rounds, the dials, and the autopilot. The Python
replay covers 41 grades and 14 pitches: each plan, 3,150 judged kicks
(every verdict) with where and when they crossed, and 11,210 round steps
bit for bit. The windowless scene replay compares 35 pitches with their
captions, 838 clipped polygons, the dial labels, and nine options notes.
The web smoke test sets a kick by hand and then plays a rung-4 round key
by key the way the reference's autopilot does. The dials, the verdict,
the thud and the bell come where the reference's do. Web and SDL hold the
eight dial keys separately; Space kicks. SDL reads the original `KICK_*`
settings and saves edits to the selected profile's sidecar.

Glove ports the grade table, the pitches' flights and where they cross
the plate, the camera's cuts and views, the screen's axes at the glove,
the catches and misses, and the autopilot. The Python replay covers 41
grades and 13 innings: 13,773 flight points, 444 cuts and 17,879 steps
bit for bit. The windowless scene replay compares 30 ballparks with
their verdicts, including the glove's green and red flashes, 268 clipped
polygons, the order everything is drawn in (which puts the ball before
or behind the glove), and nine options notes. The web smoke test moves
the glove by keys and by the mouse, lets an inning go by, and then
catches a rung-4 inning key by key the way the reference's autopilot
does. The glove, the view and the verdict end where the reference's do,
and the thud of each catch comes on time. Web and SDL hold the eight
keys separately and move the glove's picture with the pointer. The
reference measures that move through the lens it last drew; the port
measures it through the lens of the current view, so a move made between
a cut and the next frame can differ. SDL reads the original `GLOVE_*`
settings and saves edits to the selected profile's sidecar.

By Ear ports the grade table, the walk that deals a tune, its pairs and
its shift to another key, the notes of the tune and of every key
pressed, the judge, and the autopilot. A step of two keys is a Python
frozenset, and its order decides which note is made first and so each
note's seed; the port lays out the keys as CPython's eight-slot set
table does, signed hashes included (-1 hashes as -2). A note's pitch is
`261.63 * 2 ** (key / 12)`, CPython's C `pow`. With a base it can see is
2 the compiler calls `exp2` instead, which is an ulp off for key 11, so
the port reads the base from the text "2". The Python replay covers 41
grades, 600 dealt tunes (3,004 pairs, 465 shifted) and 47 tries over
80,550 steps bit for bit, ending in every verdict. The windowless scene
replay compares 35 keyboards (keys in play and out, blue, red and gold,
the steps' dots, in the reference's order), 5,840 clicks resolved to
keys as the reference's hit list does, black keys first, and nine
options notes. The web smoke test plays a tune back by the keys the
reference's autopilot presses, a shifted tune by clicks from the gold
key, and lets a pair fall apart. SDL reads the original `EAR_*` settings
and saves edits to the selected profile's sidecar.

Piano Tuner ports the grade table, the deal, the stiff string's
stretched partials, the pin, the judge with its notes, and the
autopilot. Its two livesound tracks keep every setting with the phase
each has reached, as `Track.set` does, and are rendered by the same
single-precision table lookup. Like By Ear, the port reads the base of
`2 ** x` from text so that the C library's `pow` is called. The Python
replay covers 41 grades, 400 deals and 47 tries over 110,843 steps bit
for bit, notes and track settings included, ending in every verdict.
Forty-seven PCM windows of the tracks and notes match `livesound.mix`
byte for byte. The windowless scene replay compares 42 pianos (frame,
felt, strings, pins, the hammer at its angle, and the marks under
strings tuned, in the reference's order) across all five endings, and
nine options notes. The web smoke test turns a string by held keys,
Shift, and a drag, has it judged sharp, and tunes rung-1 and two-string
rung-10 tries by the reference autopilot's ports. SDL holds Up, W, Down,
S, and Shift and reads the original `TUNE_*` settings, saving edits to
the selected profile's sidecar. The reference reads left and right
Shift separately; the port keeps one Shift bit, so letting go of one
Shift while the other is still down ends slow turning.

Cricket Hunt ports the grade table, the room deal (each candidate room
played through by the autopilot, as the reference checks it), walking,
turning and looking, how each cricket is heard, the aim, hops, grabs,
and the autopilot. Its distances and the look's dot product use CPython
3.12's compensated `sum()`. Each cricket's track is gated into chirps by
livesound's `Gate`, panned with `pan`, and brightened as it is heard; the
room's hum adds livesound's noise table. That table is built with a new
`Random(7)` for every sample, so the reference's "noise" is one constant
value, and the port keeps it so. The Python replay covers 41 grades, 48
rooms and 24 tries over 12,843 steps bit for bit, ending in every
verdict, with every track's settings and phases. Fifty PCM windows,
before the start included, match `crickethunt.mix` byte for byte. The
windowless scene replay compares 35 rooms (floor, ceiling, walls and
furniture far to near, the boards, crickets caught and the aim) and nine
options notes. Web and SDL hold the ten movement keys separately; SDL
lets Q look up during play instead of quitting.

Claw Machine ports the grade table, the cabinet deal (prizes placed
apart, each cabinet played through by the autopilot as the reference
checks it), the trolley, the swing, the belt, the drop and the close,
the verdicts, and the autopilot. The Python replay covers 41 grades, 63
cabinets and 45 tries over 7,758 steps bit for bit, ending in every
verdict, with the run's notes. The windowless scene replay compares 42
cabinets (back, sides and floor, the prizes far to near, the shadow, the
trolley, the claw, the glass and the side view; 179 polygons) and nine
options notes. Its notes play through the same mixer as Free Kick's;
the web smoke test checks that the knock and the growl sound where the
reference puts them, not their bytes. Web and SDL hold the eight
movement keys separately; Space or Enter drops.

Between the Lines and Second Thoughts are built on the same reading
quiz as Figures of Speech (feelings.Run and quiz: the answer buttons,
the per-item time, the 1.4 seconds of the right answer, the pass bar no
guesser reaches, and the deal that refuses a round one number pressed
throughout would pass). Between the Lines ports its grade table, its 20
questions a round with the answers in their written order, and
socialdata's own questions for what a reply implies, sarcasm and irony;
it reads the same `questions.jsonl` as Figures of Speech, and the
browser keeps one imported copy for both, as the reference keeps one
file. The Python replay matches 384 candidate deals, 7,260 questions, 72
quiz pages, nine options notes and 24,411 ticks, with bundled and with
imported questions. Second Thoughts makes all ten kinds of puzzle itself
(the race, the pond, the coin, the test in counts, the bakers, the price,
the description, the hospital, the test in percentages and after two
tests), with CPython's `%g`, `round` and `randrange` steps; the replay
matches 2,896 puzzles (300 seeds of every kind, and every one the deal
throws away), 384 candidate deals, 36 pages, nine notes and 8,186 ticks.
Its percentages under 1% are only ever priors of one decimal place, so
the `round(x, 1)` there cannot be told from no rounding by any reachable
puzzle.

Bad Argument, first under Rationality, is the same reading quiz with
arguments it writes itself: nonsense syllogisms and conditionals, ones
about real things whose conclusion is true or false of the world
independently of whether it follows, chains of four terms with one link
turned round, and the fallacy and formal questions of `questions.jsonl`
(the same file, and the same imported copy in the browser, as Figures
of Speech and Between the Lines). From rung 10 to 12, and from 16, it
asks what is wrong with the argument instead of whether it follows. The
replay matches 7,800 generated arguments (every form, both truths and
100 seeds each), 576 candidate deals, 10,980 questions, 108 pages, nine
notes and 41,110 ticks, with bundled questions, with imported ones, and
with formal questions alone, when the fallacies fall back to the bundled
ones.

Social Sense, second under Social, asks about everyday situations from
the social questions of `questions.jsonl` (`social` and
`social:<what>`); any imported social question replaces every bundled
one, as in socialdata. From rung 13 each item asks two different things
about one situation, taken from situations sorted as Python sorts its
named tuples, with the last question of a repeated ask standing. The
replay matches 576 candidate deals, 6,216 questions, 108 pages, nine
notes and 21,611 ticks with bundled questions, with imported ones of
every kind, and with a file whose rungs 1 to 3 have nothing to ask
(where Python raises, Elisa deals no round after the same 40 draws). The
reference caches its situations for the life of the process, so new
questions reach the paired rungs only after a restart; Elisa rebuilds
them from each import.

Which Feeling, the first Emotion card ported, reads GoEmotions comments
from `goemotions.tsv` (a label, a tab, and the comment) and falls back to
the 28 bundled comments when the file has no line with a tab. Lines end
as Python reads text, at `\r\n`, `\r` or `\n`, and only the first tab
splits. The grade's pass bar comes from `need_for` over ten comments,
which takes only five values; Elisa keeps them as a table, which the
differential checks at every rung, rather than repeating the binomial
sum with `pow`. The replay matches 816 candidate deals, 3,960 comments,
108 pages, nine notes and 20,037 ticks with the bundled comments, a file
of mixed labels, line ends and stray lines, and one whose first rungs
have nothing to ask.

How Strongly reads EQ-Bench dialogues from `eqbench.jsonl` (the text, who
speaks last, and paired emotions and scores) and falls back to three
bundled dialogues when no line decodes. Rungs 1–3 ask which emotion is
strongest; from rung 4 each emotion is placed on 0, 2, …, 10 and the
misses summed against a tolerance that narrows to zero. The shared
reading quiz gained scored items for this: a step carries its scale
values, and an item judges the summed miss rather than each step. The
replay matches 864 candidate deals, 5,472 dialogues, 159 pages and
28,379 ticks with the bundled dialogues and an imported file. Two inputs
differ on purpose: Python stops on a line that is not JSON, and zips
emotions with scores of unequal length, while Elisa skips both lines. The
chance-based pass bar never rises above the skill bar at any rung, so
the differential cannot observe it; Elisa keeps the computation anyway.

Reading People reads EmoBench stories from `emobench.jsonl` and falls
back to the two bundled stories. Rungs 1–3 ask what the subject feels,
4–6 also why, 7–9 the most helpful thing to do, and later rungs all
three. The kind is drawn for every story looked at, even from a list of
one, because `random.choice` still takes a bit then. The replay matches
864 candidate deals, 4,992 stories, 156 pages and 20,826 ticks with the
bundled stories, a file with repeated choices, a kind the task never
asks, more causes than choices, and `\r\n` line ends, and a file with
nothing to act on. A story whose answer is not among its choices stays
in the deck but is never asked, where the reference stops; lines that
are not JSON, or whose choices are not text, are skipped.

Why They Feel makes its own stories from appraisal theory, so it imports
nothing. Its 17 emotions, 12 goals, 10 acts and 20 names are generated
from the Python tables rather than copied by hand. From rung 12 half the
goals are twisted, and from rung 15 some stories ask what one person
thinks another thinks someone feels, up to four levels deep. The replay
matches 1,008 candidate deals, 10,080 stories, 63 pages and 12,749
ticks. Reading People and Why They Feel share `feelings.need_for` through
a small `FeelingOdds` module. A two-answer story makes it decide the pass
bar, and a negative control that drops it fails.

Tone of Voice plays each voice twice, with a gap, and asks how the
speaker feels. The Python task plays CREMA-D clips listed in
`voices.tsv` when they are installed. The Elisa port does not read them
yet: like Python without the clips, it uses the hums the task makes
itself, six syllables whose pitch, pace, loudness and fall follow the
emotion, 40 seeds for each of six emotions. A hum's length and where its
voice starts are worked out once, without the samples; the samples are
made per round. The audio window mixes the voices, the hiss from rung 10,
and the quiz's notes into the same stereo 16-bit PCM as Python. The
replay matches 240 hum shapes, 5,441 spot-checked voice samples, 256
candidate deals with 2,860 voices, 16 stereo windows byte for byte, 64
pages with the speaker's rings, and 11,142 ticks. Negative controls on
the hiss seed and the voice-start threshold fail, and so does a
reference page whose rings move.

Emotion asks which emotion a face shows. The Python task shows
FER-2013 photographs with FERPlus votes when they are installed; the
Elisa port does not read them yet, and draws the 240 faces Python draws
without them (`emotiondata._drawn_faces`, 30 of each of FERPlus's eight
emotions from `Random(7)`, with the `gauss` draw's cached half). The
votes match exactly; one of the 1,440 jittered shape values differs by
an ulp, from the platform's `log`, `sin` and `cos`, and only moves a
line by far less than a pixel. The replay matches 336 candidate deals
with 4,032 faces and their crops, 84 pages with drawn faces, crops and
the cover a flashed face leaves, and 15,954 ticks. Negative controls
that pick emotions in offered rather than alphabetical order, or move
the face a unit, fail. Emotion is the first card under Emotion, so the
other five moved one place along in the hub and in SDL's rows.

Notebook's Elisa generator deals facts, replacements, filler cards,
and questions with stale codes as decoys. Its string-set iteration
matches CPython with `PYTHONHASHSEED=0`, so Elisa seeds are repeatable
across processes. A Python process with a different hash secret can order
simultaneously pending replacements differently. The differential
checks 960 deals, 35,370 card actions, and a two-round adaptive session
with a pass and a fail. The shared scene draws the cards, notebook,
choices, and verdict. Its replay checks the write and answer hit regions
and blocks input during verdicts. The browser route adds the Notebook
card under Long-term memory, persistent settings, keyboard and pointer
input, and public choices without the answer index. The SDL host adds
the same task under Long-term memory and `--screen notebook`. Its replay
covers a shifted digit, a pointer click to advance, a correct answer,
and loading and saving the original profile options. The browser and
native stepped agents expose the 13 action ports, think-clock forfeits
and refill, and pixel-derived verdicts. The browser replay uses the
rendered notebook text to answer a question. The native ABI replay
checks the bank bar, receipt metadata, and verdict pixels. A full
comparison against the Python renderer remains open. The stepped
implementation caps starting rungs and adaptive growth at 4096 to
bound noise sampling.

Where Was It? has an Elisa deal generator, adaptive session, and shared
display-list scene. Its differential compares 816 Python deals, including
all four changes, projected polygons in paint order, colors, bounds, and
hits on the drawn floor and solids. The WASM replay checks study and test
phases, a click in a rotated room, grading, and the feedback deadline. The
stepped browser API verifies green and red outcomes and think-clock
refill. The browser hub adds the task under Long-term memory with
persisted options. Native SDL adds the same task to the hub and as
`--screen where-was-it`, using the original profile keys. Native
replays cover option save and reload, room navigation, a rotated-room
click, and feedback completion. The native agent exposes the 31 ports
and verifies rendered outcome pixels. The off-screen Python OpenGL and
SDL software replay compares 50 frames across the four change types
and both themes at 912×684. The minimum exact RGB agreement was 96.62%.
It checks the room interior separately and verifies that the last
verdict remains visible on the summary frame. Text and polygon
rasterization still differ between renderers. The replay does not
cover other viewport sizes.

Same or Mirror? has an Elisa polycube generator and turn-based
controller. The source replay compares 562 deals, including chiral
figures, one-cube distractors, rotation matrices, visible face order,
lighting, and projected vertices. The shared display list includes the
paired figures, the row of matches, the unshaded rungs, and feedback.
The browser task is available under Perception with saved options,
keyboard and pointer input, and a five-port agent with a think clock.
Native SDL adds the Perception card and `--screen same-or-mirror`,
reads the original `SAME_OR_MIRROR_*` profile keys, and exposes five
ports through the native agent library. The dummy-video replay checks
the paired keyboard shortcut, a click on the unshaded row, option
persistence, and the feedback deadline. At 912×684 the off-screen
Python/SDL replay compares 24 frames, including pairs, choice rows,
both themes and both verdicts. Every frame matched at least 96.33%
of RGB pixels exactly. Other viewport sizes remain unverified by
pixel comparison.

Which Is Nearer? has an Elisa deal generator, adaptive controller,
clipped perspective scene, and timed eye sway. The source differential
covers 1,122 deals, shading and polygon placement, visible bounds,
nearest-first hit order, and ordered picks. The browser exposes it under
Perception with source option values, keyboard and pointer controls,
and a six-port clocked agent. Native SDL adds the same Perception card,
`--screen which-is-nearer`, and the original `WHICH_IS_NEARER_*` profile
keys. A headless replay checks persisted options, motion, ordered
pointer and keyboard input, and feedback completion. The native agent
exposes the six ports and reads verdicts from NWFB pixels. At 912×684,
48 off-screen Python/SDL frames across all five cues and both themes
matched at least 96.13% of RGB pixels exactly. The comparison allows
small differences in floor-grid rasterization, checks the geometry
away from the grid separately, and covers sway and both outcomes.
Viewport sizes other than 912×684 are outside this pixel replay.

Point of View has an Elisa table generator, camera views, adaptive
controller, and shared map and picture scene. A differential compares
662 Python deals, including signed seed limits, unique distractors,
monochrome and mirrored views, map footprints, and painted polygons.
The browser task is under Perception with source option values,
numbered and pointer input, and a five-port stepped agent with a think
clock. Native SDL adds the Perception card and `--screen point-of-view`,
reads the original `POINT_OF_VIEW_*` profile keys, and exposes the five
ports through the native agent library. The dummy-video replay covers
profile persistence, a map click that leaves the trial open, a picture
click, a numbered answer, and the feedback deadline. At 912×684 the
off-screen Python/SDL replay compares 30 frames across both themes and
both verdicts, with at least 96.50% exact RGB agreement in each frame.
Other viewport sizes remain unverified by pixel comparison.

Inside or Out? runs from the Perception menu in the browser and SDL and
through the two-port agent interfaces. SDL reads the original `INSIDE_*`
profile settings. A differential checks 742 seeded Python deals for
exact boundaries, dot placements, and answers, plus the decoy coordinates.
At 912×684, 30 off-screen frames cover blob, fingers, maze, paired dots,
decoys, both themes, and both outcomes. Each frame has at least 91.58%
exact RGB agreement. The replay checks both ink masks within two pixels
and compares the paper and feedback wash separately.

Touching? runs from Perception in the browser and SDL and through the
six-port agent interfaces. SDL reads the original `TOUCHING_*` settings.
The geometry differential matched 1,034 Python deals, including shape
positions, rotations, signed gaps, and verdicts. At 912×684, 30 off-screen
Python/SDL frames across both themes covered circles, rotated squares,
filled shapes, touching-pair counts, and both verdicts. The minimum
exact RGB agreement was 93.70%.

Crossings runs from Attention in both hosts and through their
seven-port agent interfaces. SDL reads the original `CROSSINGS_*`
profile keys. The differential matched 69 seeded Python deals, including
spline points, decoys, and crossing positions. At 912×684, 30 off-screen
Python/SDL frames cover bent lines, smooth curves, zero to three decoys,
both themes, and both verdicts. Minimum exact RGB agreement was 93.47%.
The replay also checks alignment of the grid, coloured lines, and
crossing markers.

Time It runs from Perception in both hosts and through their one-port
clocked agents. SDL reads the original `TIMEIT_*` profile keys. The
differential matched 781 seeded shots, their motion, and verdicts across
roll, slow, bounce, and throw. Six stereo PCM windows matched the
Python rolling hum within one sample value. The shared PCM mixer also
matched all 400 Hold It regression windows exactly. The timed headless
replay also compared the elapsed PCM and verdicts through completion.
For 38 Python/SDL frames at 912×684, minimum exact RGB agreement was
79.46%.

Balance runs from Attention in both hosts and via two clocked agent
ports. SDL reads the original `BALANCE_*` keys. The strict-FP
differential matched 177 seeded Python courses and 21,240 scripted
integration states. The independent reference pilots reached matching
outcomes, with a maximum completion-time difference of 0.067 seconds. The
off-screen Python/SDL replay compared 36 frames at 912×684, including
a successful course, gusts, and a mid-course pole-length change. All
verdicts matched and minimum exact RGB agreement was 88.57%.

Juggler runs from Attention in the browser and SDL and through their
two-port clocked agents. SDL reads the original `JUGGLER_*` settings.
The differential matched 12 seeded Python acts, 480 sampled physics
states, and reference-pilot results covering 307 catches. The 912×684
off-screen replay compared 48 Python/SDL frames across both themes,
with catches, drops, mixed weights, and draught. The minimum exact RGB
agreement was 88.31%, and all verdicts matched.

Lander runs from Attention in the browser and SDL, with held thrust
and steering and five one-frame agent controls. SDL reads the original
`LANDER_*` settings. The differential matched 254 seeded flights,
11,430 scripted physics states, and reference-pilot outcomes. An
off-screen replay at 912×684 compared 24 frames across flat ground
and rough terrain with gusts and a moving pad. Verdicts matched and
minimum exact RGB agreement was 97.33%.

Keep the Beat runs from Attention in the browser and SDL. Both
hosts expose the metronome's stereo PCM and the single tap action
to stepped agents. SDL reads the original `BEAT_*` settings.
The Python differential matched 324 seeded song schedules,
972 scored runs, and 154 stereo PCM windows byte for byte. An
off-screen replay compared 48 Python/SDL frames at 912×684 across
both themes, with the curtain, reprise, taps, and successful
verdicts. The minimum exact RGB agreement was 82.23%.

Glider runs from Attention in the browser and SDL. Both hosts accept
held lift and expose a one-frame lift action to stepped agents. SDL
reads the original `GLIDER_*` profile keys. The Python differential
matched 202 seeded courses and 3,232 flight states, including moving
gaps, gusts, trails, and verdicts. The off-screen 912×684 replay
compared 12 Python/SDL frames in both themes, including a completed
course and a floor collision. Verdicts matched and minimum exact
RGB agreement was 92.01%.

Catch runs from Attention in the browser and SDL. Both hosts support
held keyboard controls, perspective mouse aiming, stereo audio, and
eight stepped ports that can be combined in a frame. SDL reads the
original `CATCH_*` settings. The Python differential matched 110 seeded
courts, 4,680 ball positions, 2,090 basket and verdict states, 330 camera
samples, and 800 byte-identical stereo windows. A 14-frame Python/SDL
replay matched verdicts in both themes with at least 90.01% exact RGB
agreement. Simultaneous controls entered the Python replay through the
task's held-control input because the Python agent wrapper accepts one
port per receipt.

Echo Cave runs from Attention in the browser and SDL, with mouse
steering, held keys, and clicks that reveal the cave on the applicable
rungs. Its nine agent ports can combine steering and a click in one
frame. SDL reads the original `ECHO_*` profile settings. The model
matched 107 Python caves, 1,712 flight states, and 49,598 sound cues.
All 400 sampled stereo PCM windows matched byte for byte. Speaker
playback trails the model by 150 ms, as in the Python version. A
14-frame Python/SDL replay covered the lit cave, a click-lit cave,
and both verdicts. Verdicts matched and minimum exact RGB agreement
was 79.44%.

Drone Hoops runs from Attention in the browser and SDL. It supports
held movement keys, mouse drag to steer, the wheel for altitude, and
ten combinable stepped flight ports. SDL reads the original `DRONE_*`
profile keys. The model matched 48 Python courses, 672 flight states,
and 3,572 cue records. All 723 stereo PCM comparisons matched byte for
byte. The headless WASM and SDL gates cover route access and agent
verdicts. A 12-frame Python/SDL replay matched pass and timeout verdicts
through completion, with at least 89.48% exact RGB agreement. The
browser reads verdict pixels only after judging the trial to avoid
the premature outcome observed in a Python flight.

Field Manual runs from Attention in the browser and SDL. It supports
pointer rotation and part controls, digits and held Shift, and the
25 original stepped agent ports. SDL reads the original `FIELD_*`
profile settings. The differential matched 120 Python machines,
624 instructions, 347 hand and order states, 1,351 audio cues, and
109 stereo PCM windows. A 13-frame off-screen Python/SDL replay
matched a completed machine and a wrong-key verdict through
completion, with at least 92.60% exact RGB agreement.

Safecracker runs from Attention in the browser and SDL, with
perspective dial and lever dragging, letter and Backspace input, and
the 41 original stepped agent ports. SDL reads the original `SAFE_*`
profile settings. The strict floating-point differential matched 65
seeded safes, 463 sampled gameplay states, 4,631 audio cues, and 104
stereo PCM windows. The default optimized build shifted four dial
ticks by one 60 Hz simulation step in that sample. A 14-frame
off-screen Python/SDL replay matched the open-door and alarm verdicts,
with at least 93.05% exact RGB agreement.

Stagehand runs from Attention in the browser and SDL. It supports
dragging props, clicking to aim the spotlight, and the five cue keys
across the original 19 stepped ports. SDL reads the original `STAGE_*`
profile settings. The differential matched 60 seeded shows, 330
performance states, 915 audio cues, and 222 stereo PCM windows.
A 16-frame off-screen Python/SDL replay covered prop dragging, timed
cues, a camera cut, and both verdicts through completion. Minimum
exact RGB agreement was 91.78%. Speaker playback stops when the show
receives a verdict.

Loading Dock runs from Attention in the browser and SDL, with held
Arrows/WASD, crate dragging, and lamp clicks. SDL reads the original
`DOCK_*` profile settings. Both hosts support saved options, adaptive
trial results, stereo sound, and all 20 stepped ports. The Stage1
differential checks 44 seeded docks, 1,896 gameplay states, 6,078 audio
cues, and the order board across all five camera views. The audio
differential matched 434 stereo PCM windows byte for byte.
A 14-frame headless Python/SDL replay matched both verdicts through
completion, with at least 92.35% exact RGB agreement.

Gunslinger runs from Attention in the browser and SDL. Both hosts
support mouse aim and fire, Space to cock the hammer, adaptive trials,
stereo audio, saved options, and all 15 stepped ports. SDL reads the
original `GUN_*` profile settings. The differential checks 72 seeded
duels, 1,524 gameplay states, 1,280 cues, and all six verdicts. The
PCM differential matched 126 stereo windows byte for byte.
The 15-frame headless Python/SDL replay matched both verdicts through
completion. At least 93.5% of each frame agreed within 12 RGB levels
per channel. Exact RGB agreement fell to 59.83% on the dust and
timeout overlays. The control hint wraps onto two lines in Elisa.

Camera has an Elisa field generator, pose matching, and shared trial
controller. The differential checks 65 seeded worlds and compares the
Python RNG after each deal, including retries for unsuitable photos.
It checks 5,915 objects, 3,250 movement and judgement states, adaptive
trial results, and all 31 stepped ports. The shape and ground meshes
match 5,096 source vertices and their indices. The view tests compare
live and photo layout, perspective, object transforms, and light and
shadow matrices. The standard strict floating-point build preserves
Python's framebuffer rounding. Simultaneous held movements are applied
in port order. Elisa emits shared render packets for the meshes and both
viewports, including the full-size target view during peek. The packet
test covers a seeded scene and all eight meshes. A standalone browser
WebGL 2 check rendered the live, photo, and peek views with the shared
shaders and verified 48 shadow draws. The WASM runtime now owns Camera
runs, handles controls and scoring, and supplies packets directly to the
WebGL renderer. Elisa also emits the title, instructions, photograph
border, warmth meter, status, tolerance, and verdict as shared display
commands. Headless Chrome verified their composition over the WebGL
scene. The WASM replay covers starting, walking, dragging, peeking,
focus loss, submission and cleanup. The browser exposes Camera in
Perception after Mr. Time. The headless browser replay checked menu
navigation, settings persistence and cancellation, held movement, drag,
peek, judgement, and exit. All 32 options-note combinations match the
Python source. The native Elisa renderer reuses the source shaders
and the existing OpenGL mesh, shadow, and multisample targets. A hidden
SDL3 OpenGL test on macOS verified live and reference view readback,
peek, and resize. The native Camera export object owns its run, shader
resources, and streaming SDL texture. The headless test links the export
object separately and checks scene composition, GL-context restoration,
chrome packets, and the ready-to-completed lifecycle. The SDL builds
link Camera into Perception and route held keys, drag, peek, judgement,
and focus loss. The full standard macOS SDL build
gate passed, and a hidden-window desktop replay verified launch from the
hub, OpenGL pixels, judgement, and return via Escape. SDL Camera options
read the original profile's `CAMERA_RUNG`, `CAMERA_TRIALS`, and
`CAMERA_ADAPTIVE` keys and save overrides in the profile's
`.camera-options` sidecar. A hidden-window replay verified changes,
reload, and cancellation. The Linux ARM64 offscreen desktop replay also
verified the hub, OpenGL composition, profile options, judgement, and
exit. Windows uses the shared SDL OpenGL procedure loader. The x64
standard and MuJoCo desktop executables cross-link, and the ARM64
Camera and GL wrapper objects compile. Windows runtime verification
remains open.

What Happens Next has an Elisa puzzle builder and run controller. The
builder returns source clip slices so the shell can keep decoded video
frames. The headless Python differential covered 259 clip cases,
including 175 playable cases, and compared the selected decoys, true
continuation, seeded draws, and playback frame indices. The same
sweep exercised adaptive scoring, rejected clip groups, the feedback
deadline, and restarting. The WebAssembly controller takes bounded
packets containing every 97th RGB byte and returns indices into the
decoded frames retained by the browser. The shared Elisa scene lays
out the opening and choices, handles tile hit testing, and reveals
the labels and verdict after a choice. A headless Chrome replay
decoded two WebM clips, painted all three tiles, and scored a pointer
selection at the rendered tile center. The browser Perception card
opens the task and its saved starting rung, trial count, and adaptive
settings. It uses the shared clip library and persists a separate
rotation history. Headless replays checked the empty-library message,
file import, a completed keyboard run, reloading saved clips and options,
cancelling a load, and the rung preview. The SDL media adapter reads
the Python INI and UCF-101 directory, shares the FFmpeg decoder with
Video Sequence, and writes the Python-compatible `seen_next.txt`.
An offscreen native replay loaded two AVI clips, checked each tile's
pixels, scored a pointer selection, and cleared the renderer textures.
The desktop Perception card and `--screen what-next` use that adapter.
The options screen previews rung difficulty and saves edits in a
profile-scoped `.what-next-options` sidecar. Headless SDL event
replays cover editing the options and reopening them from the hub.

Will It Fall? has an Elisa model and run controller for tower stability,
plank balance, first landing, first toppled block, and second landing.
The native differential checks 1,058 seeded scenes against Python,
including the signed seed limits. It compares geometry, stability margins,
landing positions, choice counts and answers, and also replays a five-scene
adaptive run with mixed answers and a restart. The shared scene draws the
five question types and reveals the tower result, plank tilt, or ball
trajectory during feedback. The WebAssembly replay verifies the scene,
pointer and number-key answers, scoring, and feedback timing. The browser
Perception menu exposes the task and previews the rung's question types,
deciding margin, and off-centre pivots. A headless Chrome replay checked
a completed scene and saved options after reloading. The SDL desktop
Perception card and `--screen will-it-fall` use the same controller and
scene. Desktop options read the Python INI and save in a profile-scoped
`.will-it-fall-options` sidecar. Headless SDL tests covered keyboard and
pointer choices, feedback, returning to the hub, and reopening saved
options. The WebAssembly and SDL stepped agent bindings expose eight
answer ports, a configurable think clock, and verdict frames tied to the
stimulus receipt. The clock refills when a new scene opens. An exhausted
clock publishes a red forfeiture verdict without updating adaptive
scoring.

Shape from Motion has an Elisa deal generator, animated dot field, run
controller, and shared display-list scene. The model covers all eight
solids, dot lifetimes, noise, and perspective for spin questions. The
native differential compares 552 seeded deals and 668,640 projected dots
with Python, including signed seed limits. Its controller replay checks
animation, button hit testing, a frozen verdict field, the 2.5-second
desktop transition, the stepped verdict transition, and adaptive score.
The browser Perception card opens the shared scene and saves the three
original option values. A headless Chrome replay checked settings after
reload, the moving and frozen fields, and keyboard and pointer answers.
The clocked WebAssembly and SDL agents expose six ports and tie the
published verdict to its stimulus receipt. The SDL Perception card and
`--screen shape-from-motion` use the same scene. SDL reads the Python
INI and saves the menu selections in a profile-scoped
`.shape-from-motion-options` sidecar. Dummy-video and native FFI
replays cover profile settings, direct and hub entry, keyboard and
pointer answers, animated agent frames, verdict pixels, and teardown.

Dr Shape has an Elisa difficulty ladder, weighted mode selection, and
geometry for all ten drawing families. The model preserves turtle stroke
order and branch poses, curved paths, solid faces, and the source's
geometry and colour changes for look-alikes. The Stage1 differential
matches Python for 57 difficulty inputs, 3,648 mode selections, and
1,120 original, modified, and recoloured forms. The candidate and
platform builders also preserve answer positions, decoy filtering,
viewpoints, and ground placement. The differential covers 112
candidate and stroke-to-note replays and 72 platform scenes across
the six trial modes. The assembled puzzles include instrument banks,
stereo reflection and modulation, stroke cues, repeated sound cards,
chorus timing, and overload noise. The Stage1 audio differential
checks all 18 instrument types, 32 seeded banks, 41 complete puzzles,
and 171 byte-exact stereo windows against Python. The run controller
uses the Python frame clamp and substeps, rejects answers before the
reveal, and publishes a verdict before the next stepped trial. A
three-trial adaptive replay checks wins, misses, timeouts, restart,
and byte-exact audio reads across a short buffer. The shared view
matches card geometry, orbit, floor, and platform projections,
fractional strokes, wobble, and depth ordering. The shared display
list paints all six modes, including the drawing turtle, sound-only
prompts and cards, floor depth cues, platform beacons, and overload
effects. The Stage1 replay checks pre-answer, choosing, success,
and timeout frames for every mode, including hit testing and verdict
colours. The browser Perception card saves the three original choices
and plays the Elisa stereo stream. A headless Chrome replay verified
the timer, saved settings after reload, stereo playback, pointer
answers, and verdict pixels. The WebAssembly agent publishes six
answer ports, elapsed stereo PCM, and receipt-linked verdicts.
SDL exposes the same game through Perception and `--screen dr-shape`.
The dummy-video replay covers starting and completing a run by keyboard
and by pointer, and checks the options menu, Python INI, and
`.dr-shape-options` sidecar. The SDL agent replay verifies audio,
the timed reveal, verdict pixels, and teardown. Cross-renderer
comparisons against Python remain open.


Tuner's Elisa model covers seeded fallback and recorded-bank deals,
station drift and fading, dial movement, guide replay, and locking. The
differential checks 400 deals and control replays against Python. Its
mixer reproduces guide audio, station loops, fading, and hiss in 75
byte-exact stereo windows. Three generated WAV fixtures exercise
recorded-clip trimming, channel selection, resampling, normalization,
fades, speed changes, and reversal against the Python reader. The
native loader reads the original ESC-50 index and uses the same installed
filenames and 300-clip readiness threshold. The file replay covers 400
indexed clips, missing and malformed indexes, a partial bank, WAV chunk
padding, corrupt audio fallback, and a recorded-bank stereo mix. The
shared session applies the Python 100 ms frame clamp, 120 Hz substeps,
held and discrete controls, adaptive scoring, and 2.5 second feedback.
Its display list paints the cabinet, dial and lamps, speaker, signal
meter, knob, lock progress, and clock. A three-trial replay compares
a win, a wrong lock, and a timeout with Python, and checks restart,
pointer tuning, two byte-exact PCM reads, and display-list state. The
browser Perception card persists the original three options. Its
headless replay checks held fine tuning, dial dragging, guide playback,
a correct lock, and teardown. The WebAssembly agent exposes the six
original ports, elapsed stereo PCM, and verifiable verdicts. SDL
opens Tuner from Perception or `--screen tuner`, reads the original
profile keys, and saves a profile sidecar. The dummy-device replay
exercises both synthesized tunes and a 300-clip installed bank,
including queued PCM, held tuning, a dial drag, replay, and a winning
lock. The native agent replay verifies all six ports, elapsed stereo
PCM, and the rendered verdict. The desktop command
`--fetch-esc50 500` tops up the recording bank using the original
dataset and filenames. It uses curl for HTTP and accepts `--datadir`
to select the existing data root. In the browser, choose the installed
ESC-50 folder under Tuner options. The browser uses the packaged index
and reads the selected trial's WAVs while the clock is paused. The
selection lasts for the current tab. Synthesized tunes remain available
without an installed bank. The recorded-bank WebAssembly replay checks
the Python guide row, deferred clock, lazy file reads across trials, and
stereo PCM. A headless Chrome replay checks folder import, playback,
a correct lock, and switching back to synthesized tunes.

Shadow Play's Elisa model generates the original centred, non-crossing
rods and projects them onto the wall and floor. The Stage1 differential
matches 300 rods and 37 seeded trials, including lamp swing, rotating
outlines, timed fit checks, and hum and chime cues. The shared session
implements drag and held controls, the Python frame clamp and substeps,
adaptive difficulty, feedback, and restart. Its replay covers a win and
a timeout and compares four stereo reads byte for byte. The shared
scene paints the lamplit wall, floor, target outlines, depth-sorted
copper rod, fit meter, hold ring, timer, and verdict. Its differential
compares 16 display lists with the Python camera, projected outlines
and shadows, and copper depth order. It covers still, rotating, and
swinging lamp scenes, a held fit, a win, and a timeout. The browser
route provides persisted options, held keyboard and pointer rotation,
elapsed stereo PCM, and a six-port stepped environment. The WASM
replay verifies a receipt-linked agent win, and headless Chromium
completed the seeded trial through the menu with pointer input.
SDL exposes the same session through Perception, `--screen shadow-play`,
and the native six-port agent library. The headless desktop replay checks
profile options, initial launch, held rotation, drag, PCM, and a completed
trial. The native agent replay checks receipt verification and teardown.
Twelve synchronized 912×684 frames at rungs 1 and 16 cover both themes,
a held fit, a successful verdict, and a moving lamp. Compared to Python,
95.28–97.17% of SDL pixels and 95.10–96.78% of Chromium Canvas pixels differ
by at most four levels in every RGB channel. The SDL test checks room and
rod interiors, fit-meter colour, and the public verdict. Other resolutions,
rungs, and states still need pixel comparison.

Captcha's Elisa model reproduces Python's seeded glyphs, decoys, colour
and orientation rules, paper, and noise marks. The shared session handles
typing, erasing, submit, adaptive feedback, and restart. The differential
checks 286 puzzles across ladder boundaries and extreme rungs, then
replays a session with a correct answer, an incorrect answer, and a
restart on the continuing Python random stream. The shared scene emits
the paper, background marks, turned glyphs, rule prompt, typed answer,
and verdict. The scene differential checks 20 frames across five rungs.
The browser route supports saved options and keyboard entry. Headless
Chromium completed a rung-30 trial selected from Perception. SDL serves
the same scene through Perception and `--screen captcha`, with the
original profile keys, keyboard and keypad entry, and click-to-start.
The headless SDL replay completes seeded rung 30. A software renderer
test verifies glyph rotation with SDL's bitmap fallback and distinct
Arial and Times glyphs with SDL_ttf on macOS. Eight synchronized SDL
and Python frames at 912×684, across rungs 1 and 30 and both themes,
had 88.52–95.99% of pixels within four levels in every RGB channel.
The browser and native stepped agents implement the 25 action ports,
think time, refill, forfeits, and verified verdicts. A live Python
oracle and headless Canvas replay agree on the bank, outcomes, and
completion for a correct submission and a two-forfeit run. The
native agent verifies its verdicts from SDL pixels and uses the
rotated bitmap glyphs. Broader pixel and platform verification
remains open.

Signals' shared Elisa model ports the partner's seeded code, the
listening and speaking exchanges, mid-game changes, and the reference
learner and guessing floor used to set par. The session handles partial
two-glyph messages, exchange history, adaptive scoring, the feedback
deadline, and restart. A strict floating-point differential matches
735 full reference games against Python across rungs 1–35 and replays
an adaptive session, including a perfect and a zero-score game.
The shared display list renders both roles, partial messages, the six-entry
exchange history, and the result. The browser Reasoning menu exposes the
original options and accepts both pointer and keyboard input. A headless
Chromium replay saved and reloaded the options and completed a seeded
16-exchange game. Across ten synchronized 912×684 captures of that game
in both themes, 93.32–94.37% of pixels matched the original Python RGB
values exactly. SDL now opens Signals from Reasoning and with
`--screen signals`, reads the Python profile keys, and persists option
edits in a profile sidecar. The headless SDL replay reloads the edited
options from the hub and verifies a perfect 16-exchange game through
mouse and keyboard input, including the Q glyph and the timed result.
The native and WASM stepped environments expose the original 16 action
ports, receipt-linked verdicts, and the optional think clock with refill.
Replays cover the seeded perfect game, clock forfeits, and cleanup. The
native test and headless Chromium replay verify both verdicts from
rendered pixels.

Fold It's Elisa model deals all eleven cube nets, folds their face
frames, rotates and reflects the markings, and checks distractors
against the 24 orientations of the correct cube. Its differential
matches 750 complete seeded puzzles across rungs 1–30, including each
offered cube and orientation. Two controller replays cover adaptive
scoring, restart, timed feedback, and think-clock forfeits and refill.
The shared display list draws lettered nets, shaded cube faces, oriented
and mirrored marks, and verdict borders. A 20-frame differential checks
the net and card layout, projected polygons, answer hit regions, and
verdicts against the Python source. Fold It opens from the browser’s
Reasoning menu and preserves the original option values. Headless
Chromium verified saved options, pointer and keyboard play, and
receipt-linked pass and timeout verdicts from the stepped environment.
SDL opens Fold It from Reasoning or `--screen fold-it` and reads the
original Python profile keys. Its headless replay covers saved options,
mouse and keyboard answers, and restart. The six-port native agent
publishes receipt-linked pass and think-clock timeout verdicts
verified from the rendered SDL frame.

Who Knows What?'s Elisa model tracks the actual contents, who is in the
room, what each person believes, and what each person thinks the others
believe. It generates the original story ladder, including calls, lies,
and peeks, and preserves the captions, question wording, and option
previews. A Stage1 differential matches 750 seeded stories across rungs
1–30 and compares both levels of belief after every event. The
controller replays cover adaptive scoring, invalid answers, restart,
timed feedback, and think-clock forfeits and refill. The shared display
list draws the story panels, occupants, container contents, wrapped
captions, and answer buttons. Thirty-six frames match the Python UI's
geometry and labels in both themes, including a 16-panel story with a
peek. The replay also checks answer hit regions and verdict colors.
The browser route preserves the original options, accepts both pointer
and keyboard answers, and includes the four-port stepped environment.
Headless Chromium verified saved options, a 16-panel round, and the
stepped environment’s receipt-linked pass and timeout from rendered
pixels. SDL opens the task from Reasoning or `--screen who-knows-what`.
Its headless replay covers the original profile settings, pointer and
keyboard verdicts, and restart. The native agent verifies the pass and
think-clock timeout against rendered SDL pixels.

Dispatch’s Elisa scheduler generates difficulty dials, incident bursts,
report positions, false alarms, and report-size error. The strict floating-point
differential matches every field in 56 consecutive seeded schedules and
1,072 reports against Python. The same differential replays every reference
order and world event, scripted crew redirects, and idle rounds, and
compares final damage and par. The session controller replays two
adaptive rounds against the windowless Python UI, including unit
selection, per-incident coaching, the 2.2-second feedback deadline,
completion, and restart. The scene differential compares 36 light and
dark frames at the reference viewport, including the town, refit arcs,
routes, incident markers, coach and round verdicts, and click targets.
It also checks all 13 starting-rung descriptions. The SDL desktop
exposes Dispatch in Decisions and through `--screen dispatch`. The
headless desktop replay verifies profile options, Shift+J refits,
mouse and keyboard orders, the final score, feedback timing, and
restart. The WebAssembly controller and web Decisions menu replay
the same seeded orders, and the browser shell tests check local option
persistence, active timing, and disposal on exit. Native and WebAssembly
agents replay all 766 ticks of the same seeded Python round in sparse
and coaching modes. The replay compares the save, loss, and round
verdicts, their action receipts, and the final transition.

Bluff’s Elisa model reproduces seeded card deals, coin draws, opponent
changes, check, bet, call and fold sequences, and the adaptive opponent’s
notes. The strict floating-point differential compares 60 deals, 1,884
dealt hands, and 9,420 played outcomes, including chips and expected
hand value. It compares the reference and sound players' moves and
par, plus two adaptive rounds with opponent changes, feedback timing,
completion, and restart. The scene differential compares 36 light and
dark frames at 912×684, the recent-hand log, button hit regions, verdicts,
nine starting-rung descriptions, and decimal midpoint formatting.
The SDL desktop exposes Bluff in Decisions and through `--screen bluff`.
It reads the starting rung, rounds per run, and adaptive setting from
Python profiles and persists edits to a `.bluff-options` sidecar.
The headless SDL replay covers both routes, keyboard and mouse choices,
the three-second feedback deadline, and restart.
The browser route supports the same input, feedback, and options. Applying
options preserves the running session's random stream. The browser and native
agent interfaces support both action ports, receipt-linked verdicts, and
the think clock with refill and forfeits.

Explore or Exploit's Elisa model reproduces the seeded machine means,
payouts, drift, redeals, and batched visibility. The fading reference
policy and par match Python across 64 deals and 18,320 machine payouts.
The controller replay covers invalid ports, batched coins, verdicts,
adaptive progression, the feedback deadline, completion, and restart.
The scene comparison covers 36 light and dark frames, including machine
history, pending payouts, last-pull highlights, options notes, and click
regions. The SDL desktop and browser expose the game in Decisions with
keyboard and mouse controls and persistent options. The native and WASM
agents use the same controller with eight action ports and a think clock.

Firebreak’s seeded Elisa generator matches 60 Python lands, including
34,200 terrain cells, roughness, ember draws, town placement,
ignition points, wind schedules, and shovel counts. The simulation replay
matches 8,561 Python ticks, initial arrival maps, and reference crew
orders. It covers town loss, saved towns, and timeout. The controller
replay covers pointer digging, shifted movement, frame clamping, timed
verdicts, adaptation, and restart. Twenty headless scene comparisons
cover terrain and decoration, flame and smoke positions, the shovel
cooldown, wind visibility, verdicts, and board hit regions. Desktop and
browser routes expose Firebreak in Decisions and retain saved options.
The native and WASM agents use the same simulation with nine action
ports and publish receipt-linked round verdicts.

Crossroads generates seeded towns and checks candidate deals with the
reference traffic controller. The model differential matches 25,993
Python ticks across all three layouts, including signal transitions,
vehicle movement, gridlock, ambulance delays, and completed shifts.
The controller replay covers adaptive progression, feedback, and
restart. Thirty-six scene comparisons cover street geometry, traffic,
signals, and light and dark themes. Desktop and browser launch Crossroads
from Decisions and persist its original options. Native and WebAssembly
agents expose four junction ports and publish receipt-linked verdicts.

Rail Yard’s Elisa model matches track layout, branch routes, schedules,
and time limits for 140 seeded Python deals. The differential compares
48,994 simulation ticks in 35 yards, including reference dispatcher
actions, points in motion, tunnel queues, and collision and derailment
verdicts. The session replay checks the 60 Hz substeps, adaptive rungs,
feedback, and restart. Forty-eight scene comparisons cover both themes,
scenery, train shapes, signals, results, and pointer controls. Rail Yard
opens from Planning on desktop and browser. Desktop settings use the
Python profile and a sidecar, and the browser persists them locally.
Native and WebAssembly agents expose 17 action ports.

Air Traffic’s Elisa model reproduces 160 seeded Python skies across
rungs 1–40. The differential checks 39,748 flight ticks, including the
reference controller’s orders, weather, runway closures, wind changes,
six verdicts, and six landing or go-around notices. The controller
replay covers adaptive rounds, flight trails, feedback, and restart.
Forty-eight scene comparisons cover radar, runways, storms, aircraft,
verdicts, and pointer controls. Air Traffic opens from Planning on
desktop and browser, with persisted settings and stepped agent ports
for eight plane selections and four commands.

Escort’s Elisa generator matches 720 Python temple candidates across
rungs 1–36. Its selected deals, reference lever pulls, and 17,464
simulation ticks match Python through successful crossings, pit falls,
flame losses, and timeouts. The controller differential covers trail
sampling, lever flips, adaptive rounds, and restart. Fifty-six scene
comparisons check brickwork, devices, levers, walkers, verdicts, and
pointer hit regions. Desktop and browser open Escort from Planning and
save its three settings. The native and WebAssembly agent replays
match Python’s flame verdict at tick 205.

Sokoban Live opens from Planning in SDL and the browser, with the
original keyboard movement, timed feedback, and session options.
The shared room generator matches 36 Python candidates across nine
rungs, including exact crate solution routes. Differentials match
10,196 scripted simulation ticks, 4,117 reference worker ticks across
nine selected warehouses, and 56 scene fixtures across both themes.
The stepped agent exposes the four movement directions.

Kitchen opens from Planning in SDL and the browser, with the original
station controls, timed feedback, adaptive shifts, and saved options.
The Elisa reference cook screens up to 25 candidates. The model
differential covers 99 candidates and 32,262 ticks, including a rejected
candidate, nine wins, a burnt dish, and two ticket-expiration losses.
A headless scene differential covers 48 fixtures across both themes,
including station hit testing and adaptive handoff. The stepped agent
exposes all 13 station ports.

Crane opens from Planning in SDL and the browser. The Elisa controller
preserves held arrows and WASD, one-shot grab and release, adaptive
rounds, and profile settings. The reference controller screens up to
20 seeded yards. The differential checks retry and fallback selection,
99 candidates, 93,183 ticks, all failure verdicts, and gentle contact.
A separate replay checks the harbor, rolling ship, wind, load, and
feedback across 72 scenes in both themes. The agent exposes five ports.

Ferry opens from Planning in SDL and the browser. It preserves combined
throttle and steering, saved options, adaptive crossings, and a six-port
stepped agent. Stage0 and Stage1 match Python across 99 river candidates
and 34,932 ticks, including every verdict. Stage1 also matches 64 scene
fixtures across both themes, including fog visibility and docking
feedback.

Docking’s Elisa flight model and reference pilot match Python on both
Stage0 and Stage1 across 117 seeded candidates and 18,343 ticks. The
replays cover fuel fitting, simultaneous thrust, successful approaches,
contact with each clearance violation, and drift. A controller replay
checks held-key priority, one-shot steering, 120 Hz substeps, adaptive
rungs, the 2.5-second feedback deadline, and restart. Stage1 matches
64 Python cockpit scenes with perspective clipping, rotated station
geometry, readouts, fuel, and verdicts. Thirty stereo contact and drift
windows match Python byte for byte. Docking opens from Planning in SDL
and the browser. Both hosts retain the original held-key priority and
play the contact cue during the verdict. SDL reads the original
`BERTH_*` profile keys. Both hosts expose all twelve agent ports.

Rover’s Elisa terrain and delayed control model match Python on Stage0
and Stage1 across 117 terrain candidates, 18,720 motion updates, and
5,107 delayed-control ticks. The comparison covers command overlap,
delayed observations after history compaction, every verdict, and note
timing. The reference planner reproduces 23 routes, including a blocked
route, and 28,835 pilot ticks. Nine screened deals match Python’s terrain
selection and next RNG draw. The Stage1 controller matches 130 snapshots
covering held-key priority, 120 Hz stepping, adaptive rungs, timed
feedback, and restart. Fourteen stereo cue windows match Python byte
for byte. The Stage1 display-list replay matches 80 Python scenes,
including delayed camera motion, terrain draw order, rocks and flags,
command arrival markers, and verdicts. Docking and Rover share the same
perspective clipping code. Rover opens from Planning in SDL and the
browser. Headless replays verify saved options, delayed commands, held
aliases, focus cleanup, collision audio, and all four agent ports.

Unicycle’s Elisa track generator, wheel contact and grip, rider balance,
and reference pilot match Python on Stage0 and Stage1 across 117 track
candidates, nine screened deals, and 11,150 ticks. The comparisons include
terrain interpolation, time budgets, pilot decisions, and each verdict.
Stage1 also matches 72 scenes with timed held controls, clipped terrain,
rider motion, and feedback, plus 30 stereo audio windows byte for byte.
Unicycle opens from Planning in SDL and the browser. The replay checks
the original `UNI_*` settings, independent key aliases, opposing keys,
combined pedal and lean, focus cleanup, feedback, and agent ports.

Morning Round’s difficulty settings, house attributes, block landmarks,
and static and moving traffic match Python on Stage0 and Stage1 across
57 seeded layouts, including the next RNG draw. Both compilers match
1,275 rulebook and street candidates, including 749 rejections. The
screened deals, reference rider’s inferred rules, paper physics,
deliveries, collisions, verdicts, and audio cue events match across
20,813 ticks. Both compilers also pass session checks for independent
key aliases, throw cooldown, adaptive difficulty, the feedback deadline,
and restart. Stage1 matches 568 rulebook descriptions and 21 stereo PCM
windows byte for byte. The Stage1 display-list differential matches 36
Python scenes for the street, traffic, rider, counters, and rulebook, plus
all nine starting-rung descriptions. Morning Round opens from Self-control
in both hosts and from `--screen morning-round` on SDL. SDL reads the
Python `ROUND_*` profile settings and saves edits in a profile sidecar.
Headless replays cover launching, controls, options, live stereo audio,
and the six-port agent interface.

Heavier’s Elisa board generator, crate motion, and reference player match
44 Python replays across 14,755 ticks on Stage0 and Stage1. The replay
includes wall contacts, wrong answers, timeouts, and exact RNG draw order.
Both compilers also pass session checks for held keys, pointer pushes,
adaptive difficulty, and the 2.5-second feedback deadline. Stage1
matches 13 stereo PCM windows byte for byte and 25 crate scenes,
including lane and answer-button hit regions and all nine option
descriptions. Heavier opens from Reasoning on SDL and the browser.
SDL reads the Python `HEAVY_*` settings and saves edits in a profile
sidecar. Headless replays cover keyboard and mouse controls, timed
feedback, stereo playback, and the eight-port agent interface.

Full Stop’s shared passage reader, ranked vocabulary, and word-pair index
accept the original passage, sentence, and lexicon cache formats and use
the original offline seed banks when caches are absent. Stage1 matches
832 Python candidates, including 105 rejections, and 2,693 reference
replay ticks. The checks cover casing, word wrapping, pointer input,
missing and extra stops, and timeouts. Fifteen stereo PCM windows match
byte for byte. The session and page match 42 Python frames across both
themes and all phases, including corrected passages after failure and
the four-second feedback interval. All nine option descriptions match.
Full Stop opens from Reasoning in the browser and on SDL via the hub or
`--screen full-stop`. SDL reads Python `STOP_*` settings, saves edits in a
profile sidecar, and discovers the existing caches in the words directory.
The browser can import the three cache files from the options form and
remembers them locally. Both hosts share the Elisa controller and PCM
renderer. They expose the same sixteen action ports for frame-based agents.

The Missing Word’s Elisa model deals passages and repairs them through the
original hand controls. The Python differential checks 768 seeded candidates
and their RNG states, 32 screened deal attempts, 10,767 gap options, and
2,679 reference-player ticks. The page renderer matches 63 Python pages
with no selection, a selected word, or a selected gap. All nine option
descriptions and 15 stereo PCM windows match. The task opens from Reasoning
on both SDL3 and the browser. SDL3 also accepts `--screen missing-word`,
reads the original `GAPW_*` profile settings, and discovers the passage
caches in the Workshop data directory. The browser options form remembers
imported caches and settings locally. Headless replays cover pointer repairs,
adaptive scoring, the four-second feedback interval, and the sixteen-port
agents. A repeated-edit replay verifies that edited rows and cues survive
buffer growth across WebAssembly input and render calls.

The Proofreader opens from Reasoning on the web and SDL3, including
`--screen proofreader` on SDL3. The seeded generator matches Python on
720 candidates across six damage kinds, with 12,174 word offers. The
comparisons also cover 30 screened deal attempts, 2,971 reference-player
ticks, 88 page states, nine option descriptions, and 15 stereo PCM
windows. Both hosts use the original passage-cache formats. SDL3 reads
`PROOF_*` profile values and saves edits in a profile sidecar. The browser
remembers Proofreader settings separately and shares imported caches with
The Missing Word. Headless host replays exercise settings, pointer and
keyboard editing, audio, and feedback. The WebAssembly replay also checks
cancellation during a drag and keeps editing after the cue buffer grows.

Figures of Speech opens from Reasoning in both hosts and through
`--screen figures-of-speech` on SDL3. Its shared Elisa reading quiz matches
384 Python candidates, 3,720 questions, 14,992 replay ticks, 72 quiz pages,
nine option notes, and 15 stereo PCM windows. The desktop reads the original
`FIGURE_*` settings and checks `datasets/social/questions.jsonl` for each
question kind. The browser imports the same file and retains it alongside
its independent settings. Headless replays exercise keyboard
input, option persistence, pointer answers, session timing and audio, plus
the eight-port agent interfaces. Porting the original Social dataset
download commands remains part of the migration.

Gamble’s Elisa model reproduces seeded machine deals, drifting odds,
odds swaps, payouts, bites, bankrolls, and stopped rounds. The Gaussian
cache carries across deals. The Stage1 differential checks 39 deals and
18,426 payout slots against Python and covers early stops, busts, and
rounds that exhaust their pulls. The same differential compares the
reference player’s discounted Beta sampling, every reference pull,
and par against Python. The controller replay verifies adaptive passes
and losses, the three-second feedback deadline, early stopping,
restart, and release of trial storage. The headless scene differential checks
30 light and dark screens across ready, pulling, judged, and finished
phases. It covers machine cards, recent payouts, revealed odds, colored
verdicts, pull and Stop hit regions, and all nine starting-rung descriptions.
The SDL desktop exposes Gamble in the Decisions hub and through
`--screen gamble`. It reads Python profile values for starting rung, rounds,
and adaptive difficulty, and saves desktop edits in a profile sidecar.
The headless event replay verifies options, keyboard and mouse pulls,
stopping, the feedback deadline, and restarting. Gamble also runs from the
web Decisions menu through WebAssembly. The artifact tests cover the web
options form, local persistence, keyboard and pointer input, Stop, timed
feedback, restart, and run disposal. The stepped WebAssembly and SDL
agent interfaces expose nine action ports and the optional think clock.
Agent replays check receipt-linked verdicts, timed forfeits and refills,
and completion. At rung 1, the seeded replay matches Python's 23 coins
and pull value of 22.01734116342062 against a par of 20.139652576416452.

Sonar’s Elisa model uses the original seeded target paths, noise draws,
distance bands, and ping and dig costs. The differential compares 22
deals and 4,600 actions, including target drift, exhausted budgets,
successful digs, and consecutive deals from the same RNG. The reference
solver retains the posterior’s insertion order and uses CPython 3.12+
compensated sums. The differential also compares each reference probe
and the resulting par. The controller replay covers cursor movement,
pass and loss, adaptive rungs, the 1.8-second feedback deadline, stepped
advancement, scoring, and restart. A 36-scene comparison checks the
Elisa board, aged readings, miss and target markers, cursor, verdicts,
and cell hit regions against the Python renderer. The browser Decisions
route adds saved options, keyboard controls, click and Shift-click or
right-click, and timed feedback. SDL opens Sonar from Decisions or
`--screen sonar`, reads the original `SONAR_*` settings, and saves
edits in the profile's `.sonar-options` sidecar. The headless SDL
replay checks settings, both dig gestures, the verdict, and restart.
The browser and native agents expose the six original ports and an
optional think clock. Their replays check a seeded win, expiry, refill,
and the 24×24 board. The native replay verifies the receipt-linked win
and timeout verdicts against rendered SDL pixels.

Dam Keeper's Elisa model generates the original storms and qualifying
valleys, tracks gate movement and delayed releases, and reproduces the
reference keeper's decisions. Its Stage1 differential compares nine
seeded valleys and 37,964 ticks against Python, covering a dry town and
each failure condition. The run replay checks the frame-time clamp,
three-second feedback, adaptive rungs, stepped advancement, restart,
and release of the pipe storage. The shared display list reproduces the
valley, weather, water, gates, and clock. A differential compares draw
commands and gate hit regions across 18 frames from the Python renderer.
The browser Decisions route preserves the original option choices and
defaults, keyboard and pointer gate controls, frame clock, and restart.
SDL opens Dam Keeper from Decisions or `--screen dam-keeper` and reads
the original `DAMKEEPER_*` settings. A headless desktop replay covers
saved options, keyboard and pointer gate changes, the timed verdict,
and restart. The browser and SDL agent bindings advance six gate ports
against a virtual clock. A Python-derived replay checks a loss on tick 297
and a pass on tick 901. The native agent verifies both receipt-linked
verdicts against SDL-rendered pixels.

Hold It's Elisa model covers copy, half/double, and two-lamp trials,
including the misleading clock, timeout, and proportional scoring.
The controller matches the Python frame-time clamp, fixed substeps,
adaptive difficulty, and three-second verdict. The differential compares
7,000 seeded deals and 2,506 clocked states, including pass, short, long,
and no-hold outcomes. The shared display list renders both lamps, the
clock, and the result bars. Its scene check confirms the lamps illuminate
independently during playback and together while held, and the bars
appear only after release. The browser Self-control route adds persistent
options, held Space input, release on focus loss, and cleanup. The WASM
state exposes lamp visibility without exposing durations during play.
The SDL host exposes the same scene from Self-control and
`--screen hold-it`. It reads the original profile and saves options beside
it. The dummy-video replay covers hub and options launch, persistence,
and exact held time after both Space release and focus loss. The organ
hum and wood clock ticks are synthesised in Elisa and played through
Web Audio and SDL. The differential matches 400 stereo PCM windows
byte for byte against Python. The browser and native stepped agents expose
one frame-scoped hold port and publish elapsed PCM alongside observations.
Their seeded replays verify receipt locking, release, pixel-derived reward,
and cleanup. The invisible-window replay matches sampled lamp, clock,
stage, and result-bar pixels and derives the same verdict from both
frames. At 912×684 on macOS, 78.30%–95.38% of RGB pixels match exactly
and 96.94%–97.86% are within four levels per channel. Whole-frame parity
remains open. Run `nw-core/test/hold_it_pixels.py` with the original
project's Python interpreter and the native agent library path.

Stop & Switch's Elisa rules generate the original shape, colour, side,
rule changes, and stop signals. The session controller handles the
inter-stimulus cue, delayed stop ring, response window, omissions,
grading, adaptive changes, and verdict. The native differential matches
280 seeded deals across rungs 1–35 and 3,796 timed states across eight
blocks. The shared scene draws the rule banner, fixation cross, stimulus,
stop ring, key legends, progress marks, and verdict. A headless scene
replay checks prepared and concealed rule cues, stop-ring timing,
progress, and pointer gating in both themes. The common WebAssembly
runtime supports Stop & Switch creation, input, advance, state, frame
rendering, and destruction. Its replay checks cue concealment, delayed
stop-ring visibility, withholding a response, and the result of a
complete block. The browser Self-control menu launches the game and offers
persistent starting-rung, block-count, and adaptive settings with an Elisa
rung preview. A headless browser-host test covers its menu order, settings,
keyboard timing, and cleanup. The SDL host uses the same Elisa controller
and scene for the Self-control entry and `--screen stop-and-switch`. It reads
the Python profile and saves options beside it. The dummy-video replay
checks hub launch, the options screen, saving, and reload. The browser and
native stepped agents use a fractional clock and publish one verdict frame
before dealing or ending the run. The browser replay covers timeout and
answer-triggered settlement, and the native library replay verifies a win
from its rendered pixels. The stepped differential matches 3,295 states
across four frame rates. An invisible-window framebuffer replay compares
four synchronized cues in both themes at 912×684. Stage, key face and lip,
fixation cross, rule band, circle face and rim, square, progress marks,
and stop-ring interior samples match. Whole-frame RGB identity ranges
from 95.28% to 97.31% on macOS, so exact frame parity remains open.
Run `nw-core/test/stop_switch_pixels.py` with the original project's
Python interpreter and the native agent library path as its argument.

Delay's Elisa rules generate all seven offer regimes and compute the
fixed-strategy benchmark, all-small baseline, and par. The differential
compares 112,000 offers and 560 scoring runs against Python across rungs
1–35. The clocked session controller handles taking, waiting, abandoning
an offer, expiry, adaptive difficulty, and the original three-second
verdict. A second replay compares 1,900 states across eight complete
rounds against the original Python UI's session methods. The Elisa scene
draws the purse, reward cards, wait indicator, countdown, and verdict.
A headless replay covers both themes, pointer availability in every
phase, elapsed-time formatting, and hidden wait labels. The WebAssembly
runtime can create, drive, render, and dispose of a Delay session using
the common API. Its replay covers pointer and keyboard actions, rewards,
abandonment, never-paying offers, and the exact expiry and verdict
boundaries. Delay now opens from Self-control in the browser. The options
form saves the starting rung, run count, and adaptive flag and previews the
selected waiting pattern. Headless Chromium covers persisted options,
keyboard and pointer input, a paid wait and a forfeited wait, and the
transition from run expiry through the verdict to results. The SDL
desktop launches Delay from Self-control or `--screen delay`, reads
the original INI settings, and persists changes in a profile-scoped
`.delay-options` file. The dummy-video replay checks both launch paths,
settings reload, and a complete round on an injected clock, including a
paid wait, giving up with the pointer, expiry, and the verdict.
Delay's browser agent now uses the original two action ports, fractional
virtual time, one-frame verdict publication, and the shared receipt and
evidence archive. Node verifies sparse and neutral outcomes, and
headless Chromium verifies a full winning run from actual pixels and
deterministic reset. The native agent library uses the same receipt and
frame publication code as Triage. It publishes a winning Delay verdict
after 960 ticks and verifies its reward from SDL-rendered pixels. The
macOS package includes the Delay entry points and their declarations.
Python pixel comparison, native historical evidence archival, and
Linux and Windows agent package runtime verification remain open.

The Triage kernel now deals cards with Python-compatible randomness and
budget rounding, applies card flips and swaps, and computes the original
reference strategy, optimal payout, and par. The differential compares
560 complete deal and reference transcripts at rungs 1–35. The session
controller uses the original action ports, seeded round sequence,
2.5-second verdict, adaptive rung changes, and run tally. The native replay
compares 36 rounds with the original UI's session methods, checking the
verdict deadline on both sides and restarting with the same RNG stream.
The shared display list renders hidden, open, and solved cards, swap
controls, and the verdict. A native smoke check verifies display-list
encoding and pointer hit testing. The common WebAssembly ABI exposes
creation, options validation, input, state, frames, and the verdict
timer. Its seeded replay verifies pointer and keyboard input, hidden
rows, payout, and cleanup. The browser's Decisions menu now launches
Triage and saves its three settings locally. A headless Chromium replay
covers menu pointer and keyboard navigation, completing a seeded round,
the verdict transition, cancellation, and settings persistence across
reload. SDL launches Triage from Decisions or with `--screen triage`.
It reads Python INI settings and saves changes in a profile-scoped
`.triage-options` file. The desktop options preview describes the selected
rung's card lengths, budget, and hidden-card rules. The dummy-video replay
checks both launch paths, settings reload, pointer swaps, and a complete
seeded round through the verdict and results screens. Web and SDL share
the original starting-rung preview text. The WASM replay compares all
ten selectable previews, and headless Chromium checks live updates and
cancellation. The browser stepped environment exposes all 17 action ports,
draws the optional think bank, and publishes verifiable rewards and the
out-of-time verdict. A forfeit consumes a round without affecting adaptive
difficulty or the played-round tally. The Node and headless Chromium
replays cover seeded reset, receipt locking, sparse rewards, and a think
clock forfeit. The browser stepped environment now accepts signed 64-bit
integer rungs and round counts, including values outside the interactive
menu, and applies Python's signed-seed and empty-run behavior. The
browser replays cover decimal dial strings, fractional number truncation,
and empty runs. The native Triage FFI exposes the same controls and can
render RGBA without a window. A native replay verifies a seeded win and
an out-of-time verdict from the rendered pixels and checks that only
the played round contributes to the adaptive score. Both hosts now use
Elisa for the think bank, timeout, refill, and stepped verdict hold.
The native replay also checks expiry, capped refill, and one-frame
verdict timing. The native agent FFI now publishes NWFB frames, locks
one action per receipt, and derives sparse and neutral outcomes from the
rendered pixels. The replay verifies receipt-to-frame binding, SHA-256,
timeout outcomes, and run completion. The SDL build now produces a
loadable native agent library. The macOS package includes its C header
and resolves SDL alongside the library after relocation. The full
agent replay passes against the relocated arm64 macOS package. Linux
and Windows package runtime verification, historical evidence archival,
and Python integers outside the signed 64-bit range remain open.
The shared Triage scene now uses the source's play-area clearance,
machine-card palette, recessed screens, and open and solved outlines.
WASM checks polygon completeness and both themes. The native agent
checks header and recessed-screen pixels in both themes. Full-frame
visual parity, including font rasterization and non-reference window
sizes, remains open.

CLI progress: the Elisa screen selector now recognizes `--screen` after other options, matching Python argument ordering. Headless Stage0 host tests cover all 38 named screens in both positions. Other CLI compatibility remains open.

The Python `you-are-here` screen name and initial `--width`/`--height` options now route through Elisa; positive dimensions and invalid or missing values are covered by headless host tests. The dummy-video event replay passed with the available older Stage1 product.

The Elisa title frame now starts at Python’s first banner and advances through the same four banner indices. Headless frame-byte comparisons passed. The title `--trial` option now clamps to the same four banners; task-specific uses of `--trial` remain open.

Title navigation now handles Space, Enter, arrow keys and wrapping immediately as in Python. Headless key checks and the dummy-video replay passed.

The Elisa SDL path now accepts `--black-background`, passes the theme to task and option frame writers, and clears the backing surface white or black as in Python. Headless title and Sudoku frame comparisons and the dummy-video event replay passed; broader visual parity remains open.

A headless SDL software-surface check also confirms the actual white and black backing pixels.

Direct 3D Maze and Sokoban startup now uses the Python defaults and routes `--trial`, `--trials`, `--adaptive`, `--show-marks`, `--show-traps`, and signed 64-bit `--seed` into the native controllers. Headless controller-state comparisons and the dummy-video replay passed. The parser tests cover zero, negative seeds, and both signed 64-bit boundaries. The task hub now forwards those same options to both controllers.

The native title `--dump` matched the Python CLI byte for byte in light and dark themes across five frames starting at trial 4, including banner wraparound. The comparison used the installed Python extension and existing Stage1 compiler. The task hub dump also matched Python byte for byte across two frames in both themes. SDL now exposes headless dumps for all 37 tasks. Exact Python comparisons have covered selected initial and playable frames, with discrepancies still tracked for Mr. Time, Numberology, Scramble, and Syllogism.

Go and Crossed Wires dumps matched the installed Python 3.14 extension byte for byte across the ready and first playable frames with seed 42. The Python 3.9 extension lacks Crossed Wires and exposes an older Go state layout. Building a fresh Python extension with the available Stage1 product was rejected because multiple modules declare a struct named `Grade`.

SDL rendering now honors line and box thickness, joins consecutive multiline segments, draws bitmap bold text with the Python size cap, and loads the light and dark title logos relative to the executable. Headless pixel checks cover stroke width, repeated multiline points, bold coverage, and the logo region in both themes. The current Stage1 application build passed the 37-route SDL replay. Exact font, sprite, and full-screen visual parity remain open.

Applying options in Algebra, Numberology, and Syllogism now preserves the initial session seed. The headless native test compares each first playable frame with a controller created directly from the same settings and seed. Scrabble, Scramble, and Crossword already apply options to the existing controller, as the Python shell does.

The Elisa Marble model builder generates MuJoCo XML from the shared tray generator. It uses the same float32 coordinates as the board transport and matches the Python model byte for byte for three seeds at each of the 16 rungs. Connecting the builder to the desktop MuJoCo simulation and 3D renderer remains open.

The native Elisa MuJoCo module compiles the model, manages simulation state, and reads time, positions, and velocities through FFI. Elisa implements held-key tilt, leveling, and the Python adapter's timestep partition. A C adapter sets gravity and timestep using version-checked MuJoCo headers. Run `scripts/test_marble_mujoco_ffi.sh` with the library path and, if needed, the headers directory. The desktop still needs library integration, collision and settling rules, controller synchronization, and 3D rendering.

Elisa now detects holes, switches marble contacts while falling, distinguishes cup and loss outcomes, and handles the energy threshold when a marble crosses a hole's lip. The headless FFI test exercises both terminal outcomes and checks that their reported positions stay fixed.

The Elisa engine now also applies world-space spin correction, rolling rest and speed limits, and per-step cup, loss, and impact feedback. With `NW_MARBLE_REFERENCE_PYTHON` set to a Python interpreter with the matching MuJoCo package, the FFI test compares 240 samples per board against the Python adapter. On macOS with MuJoCo 3.12.0 the three seeded boards matched within 1e-8 for position, orientation, velocity, timing, and feedback. Integration with the SDL controller and broader trajectory coverage remain open.

The Elisa Marble session adapter synchronizes MuJoCo with the shared trial controller. The headless test covers initial model creation, restart on the same board, timeout overshoot and scoring, automatic transition to the next board, result recording, and cleanup on completion. Set `NW_MUJOCO_LIBRARY` when running `scripts/build_sdl3.sh` to build the MuJoCo-enabled `nw-sdl3-mujoco` executable and exercise it with SDL's dummy video driver. The existing display-list renderer still needs to draw the live state and match the Python 3D renderer.

Elisa generates the Marble board body, frame, walls, pits, home cup, collar, and sphere meshes. The headless comparison checks positions, normals, and index order against Python for three seeded boards. The meshes still need to be uploaded and drawn by the desktop 3D renderer.

The Elisa 3D transforms cover the physical-pixel stage rectangle, perspective camera, tray tilt, and marble translation and spin. The headless comparison matches the Python renderer's matrices at an odd-sized viewport with nonzero tilt and a rotated marble.

The MuJoCo-enabled SDL build draws the live board through the shared OpenGL shaders and composites the resolved stage over the SDL display list. It uses a hidden OpenGL context and transfers stage pixels to an SDL streaming texture. The hidden-context test verifies the transfer into a software SDL renderer. Exact Python pixel parity, native Marble screenshot capture, and cross-platform presentation verification remain open.

The hidden-context comparison captures the same initial active board from Elisa through SDL and from Python through Pyglet. At 320×240 on macOS the stage differs by a mean of 12.8155 per RGB channel on the 0–255 scale. The CLI screenshot starts on the ready screen, as Python does.

The comparison also captures Elisa's resolved OpenGL stage before SDL copies it to the host surface. Every RGBA pixel matches after accounting for OpenGL's bottom-up row order, locating the measured difference before SDL presentation.

On the same 42,300-pixel stage, both renderers classify exactly the same 18,585 pixels as background within one RGB level of the clear color. The remaining difference is in the rendered board and its shading. Bulk-uploading the Python hole uniforms produced the same comparison result.

The capture now compares the active camera, board, marble, and light transforms directly against Python. Those transforms match within the test tolerance. The shadow buffers differ by more than 1e-6 at 91,375 of 1,048,576 samples on macOS. This gives a separate comparison for investigating shadow drawing before color shading.

The live renderer now generates its upload meshes and caches shader hole data from locally built trays. This works around a Stage1 issue observed when reading nested dynamic arrays from the heap-backed session. The macOS hidden capture now matches Python exactly across all 42,300 stage RGB pixels, with no shadow depth differences above 1e-6 and no RGB changes during SDL transfer. This covers one initial active board.

The 320×240 hidden capture now covers three boards across light and dark themes, including a rung-16 board after eight 20 ms east-tilt updates. All three match Python's stage RGB exactly and shadow depth within 1e-6. SDL preserves the resolved stage RGB in each capture.

Scramble's dump mismatch came from the Python dump dispatcher leaving the session on its ready screen. Adding the same start action used by the interactive Python session gives byte-for-byte parity with SDL for three seeded fallback-corpus runs in both themes. The installed Python extension still differs on Numberology's unjudged answer field and lacks Syllogism.

A CPython 3.15 extension built from the same application sources as SDL now provides a current dump oracle. Distinct task struct names resolved the pymodule backend's name collisions. With an empty settings and corpus directory, the two-frame headless dumps matched byte for byte for all 39 Python screens using seed 42. These captures cover startup and the first start action.

SDL settings readers accept signed zero and underscore-separated digits in saved Syllogism, Numberology, and shared task settings. Numeric options for Go, Syllogism, Algebra, Scramble, Scrabble, Crossword, and Numberology accept surrounding ASCII whitespace and underscores between digits. Headless checks compare the formatted and plain inputs and reject malformed separators.

The arm64 macOS packager staged the SDL_ttf and MuJoCo build with its transitive dylibs and local license notices under executable-relative paths. From outside the staging directory, it passed the Marble physics and asset checks, task-hub lifecycle, long-text rendering, and headless task-hub PNG capture. This verifies package relocation on the build host. Windows TrueType package verification remains open.

Native Concentration and Recognition sound modes use SDL audio through Elisa FFI. Both tasks keep the ready screen available when the ESC-50 library is missing or too small, and rescan it on each start attempt. The macOS headless SDL suite verified the empty-library message for both tasks, Recognition playback and replay with two clips, and Concentration's first flipped clip against Python's seeded shuffle.

Concentration card flips and Recognition answer clicks now route through the Elisa desktop event loop using the rendered layout and SDL viewport. The SDL dummy-video replay checks that a Concentration click plays the seeded clip and that each Recognition button records its answer near the inner edge of a letterboxed viewport. Motion over the opposite button and clicks in the gap leave the answer unchanged.

Recognition can load the original Tiny ImageNet JPEG library in the native desktop with `--recognition-pictures`. Elisa calls TurboJPEG and SDL directly and binds the decoded image to the current trial's display-list asset. The macOS headless replay checks the rendered pixel and graceful handling of missing and corrupt photos. Desktop packagers can bundle TurboJPEG with the BSD and IJG notices.

Concentration now deals pairs from the same Tiny ImageNet library with `--concentration-pictures`. SDL checks two simultaneous card reveals against Python’s seeded shuffle and verifies the ready-state message when the picture library is empty. Media catalogs use SDL’s sort to keep large libraries in Python filename order.

The macOS arm64 package passed its executable-relative TurboJPEG loader and symbol checks from outside the package with an empty environment. The macOS SDL build gate also passed with MuJoCo, TrueType, and the JPEG rendering fixtures enabled. The Linux and Windows TurboJPEG packaging paths passed shell syntax checks and still need native smoke runs.

The SDL Concentration and Recognition controllers now read their settings from the original Python profile INI, including quoted media choices, timing, and feedback flags. Direct and hub launches use the same reader. The headless desktop gate verified a custom INI, Concentration's configured preview duration, Recognition's settings and missing-media state, and CLI precedence. SDL stores its applied choices beside the selected profile INI. When the profile omits these settings, SDL uses the original Python defaults, including eight Concentration pairs, 40 Recognition trials with no image timeout, and the Tiny ImageNet photograph library. The headless replay checks those fresh-profile defaults and the missing-library message.

Concentration and Recognition now show their settings menus inside the SDL task. The menus expose all five and six original options, respectively. Enter applies the draft and returns the controller to its ready state with the existing RNG, while Escape cancels. The headless replay covers opening, keyboard and mouse edits, apply, and cancel on both direct screens. The task hub also opens either menu with C on the highlighted task. Apply and cancel both return to the hub, and applied choices carry over to the next task launch in the same process. The dummy-video replay exercises both paths. Applied choices also now persist across application restarts in task-specific files beside the selected profile. The original Python INI remains byte-for-byte intact, and an invalid saved file falls back to the INI.

The 3D N-Back controller now reports standard and Jaeggi percentages on completion. Both exclude the warm-up trials, while the Jaeggi result also credits correct rejections after warm-up. The completion frame shows the standard score. The macOS SDL gate replays a complete session and checks both results against the shared port of Python’s scoring kernel. The completed score now also feeds the desktop reward player.

SDL 3D N-Back can advance and fall back between sessions with `--adaptive`. It reads the original profile thresholds and trial-count formula, applies advancement after scoring, and preserves the completed session’s level in its result display. The headless gate checks promotion, delayed fallback, Jaeggi immediate fallback, the level cap, and profile-based trial counts. Adaptive progress is stored beside the selected profile.

The SDL 3D N-Back controller now plays the original applause WAV once on adaptive promotion. It uses the profile’s session feedback, applause, and SFX volume settings, and stops playback when the player leaves the task. The SDL build stages the WAV and its source license, and the dummy-audio gate verifies one playback at 25% gain plus suppression for disabled feedback, disabled applause, and a score below the promotion threshold.

The 3D N-Back reward player selects the original advance, great, or good tier and plays OGG or WAV through SDL_mixer FFI. The macOS dummy-audio gate used the original Concert OGG to verify all three tiers, muted and disabled settings, manual-mode playback, and cleanup. Desktop packagers can stage SDL_mixer and explicitly supplied tracks with their attribution notices.

The relocated arm64 macOS package loaded its staged SDL_mixer and decoder dependencies and played original OGG tracks from the advance and good tiers under dummy audio with a clean environment. The full macOS SDL gate passed with MuJoCo, TrueType, JPEG, and reward music enabled. The Linux and Windows packaging scripts passed syntax checks and still need native runs.

Starting the next 3D N-Back session fades applause and reward music in 50 ms steps using Python’s volume curve. The macOS SDL gate checks the fade arithmetic, and the dummy-audio event replay starts both reward streams, restarts the task, observes reduced applause gain and checks that both streams close at silence.

SDL 3D N-Back atomically saves the next level and fallback count after completing an adaptive session. It honors `RESET_LEVEL` and the profile’s local `ROLLOVER_HOUR` on restore. The dummy-video replay verifies promotion and fallback across separate processes, fixed-mode isolation, daily reset, and invalid-record fallback. When no valid native record is available, SDL can restore the level and fallback count from original Python position-mode history.

The 3D N-Back legacy import reuses the shared Python stats parser for comma and tab records. It selects position-mode rows and honors named-profile stats files, `STATSFILE`, `--statsfile`, and the original rollover rule. Import is read-only and takes effect when a valid native progress record is unavailable. SDL can display a position-mode history chart for recent days.

Completed SDL 3D N-Back sessions now append original-format position-mode summary rows to the selected stats file. Adaptive and fixed-level sessions record the original manual flag, and existing stats content is preserved. The headless replay covers appending both kinds of result to a file without a final newline, checking all 27 columns and confirming each result is written once. The original clinical summary log is available with `--clinical-log`.

SDL 3D N-Back also appends Python-readable trial records to the selected user’s sessions file. Each record carries the CSV summary, session metadata, cube stimuli, color, position-key input, and reaction time. The headless replay unpickles the adaptive and fixed-level records with Python, compares the summaries to the CSV, and checks the expected 125 ms response. The dump currently includes the native task’s supported configuration and streams.

SDL 3D N-Back’s opt-in `--clinical-log` writes the original 25-field protocol-2 pickle records to `logfile.dat` or the named user’s corresponding log. The headless replay checks the opt-in boundary, protocol, numeric fields, multiple appended records, and the named path. This switch covers log compatibility. Other clinical-mode behavior remains open.

Press G from the 3D N-Back ready or results screen to chart position-mode history. The view groups adaptive sessions by the profile’s rollover hour, shows each day’s mean and maximum, and includes the trailing 50-round position score. M cycles the five scoring styles. The chart covers the latest 120 calendar days, and viewing or switching styles never rewrites the stats file. N cycles through the supported game modes with recorded standard sessions.

The SDL history chart now reads all modes recognized by the original mode table, and N cycles through the modes with records in numeric order. The legend uses the original modality-to-column mapping and shows the trailing 50-round average for each active modality. The dummy-video replay covers Position, Sound, and Dual, wraparound, and per-modality scores.

Native adaptive progress now records the completion hour as well as the date, so its daily restoration uses the same rollover rule as imported Python history. Earlier date-only records remain readable and use calendar-day matching. The gate checks the rollover boundary, leap-day transition, and save/restore with both formats.

SDL 3D N-Back reads the Python profile’s cube count, tick duration, stimulus duration, and feedback duration. It uses an explicit trial interval when set and otherwise derives the interval from the Position mode’s tick count or the default tick count. The headless replay checks cube count clamping, explicit interval precedence, rounding to the configured tick, and the ten-tick startup delay. Session dumps record the effective tick duration.

SDL 3D N-Back reads the original Position level and trial-count formula for manual and adaptive sessions. In manual mode, F1/F2 adjust the level, F3/F4 adjust the base trial count, and F5/F6 adjust the interval using the shared timing rules. Changes made from the results screen apply to the next session, preserving the completed session’s level, trial count, and interval. The headless checks cover profile precedence and the SDL key routing before, during, and after a run.

SDL 3D N-Back accepts the original `--trial-ms`, `--tick-ms`, and `--stim-ms` overrides and their corresponding `NW_*` environment variables. The headless launch replay checks CLI, environment, and profile precedence, attached argument values, a zero interval falling back to the mode’s tick count, and invalid-value diagnostics.

SDL 3D N-Back uses the original fast timing defaults and suppresses reward music and applause when headless mode is selected. The launch replay covers `--headless`, `NW_HEADLESS`, and profile `HEADLESS`, including a custom tick, an explicit interval, and an adaptive promotion with reward assets present.

3D N-Back pauses the countdown during startup, stimulus, response, and feedback. It preserves the remaining time in each phase on resume. As in Python, position responses during a paused trial still count, and a later response updates the reaction time from the original stimulus onset while scoring only once. Restoring a browser snapshot also retains the session settings when restarting.

SDL 3D N-Back reads the Python profile’s `KEY_POSITION1` and displays the active binding. It translates printable ASCII and supported Pyglet navigation, function, and keypad symbols. The headless replay covers both a letter and an arrow binding and checks that the original A key stops recording matches after rebinding.

SDL accepts `--user NAME` as a launch override for Python’s remembered profile. The title, profile configuration, and 3D N-Back result paths follow the selected user. The headless replay covers Unicode and spaces in profile names, explicit selection of the default profile, and output to the selected user’s Python-readable files.

Pressing U on the SDL title screen or idle task hub opens an existing-profile picker. It lists the default and named users with configuration or stats files, updates the window caption on selection, and atomically saves the selection as the original Python pickle in `defaults.ini`. The dummy-video replay checks cancellation, selection, Python pickle decoding, and restore on the next launch.

The SDL profile picker accepts new user names through SDL text input, with UTF-8 cursor movement and Backspace. It creates the named stats file so the profile appears in Python’s user list and saves the selection using the same profile format as existing users. New profiles use built-in defaults until a profile INI exists. The dummy-video replay covers an empty submission, editing a Unicode name, Python pickle decoding, and loading the new profile’s INI on a subsequent launch.

The SDL picker discovers named profiles from both Python configuration and stats files. An existing profile with both files appears once, and a config-only profile is selectable before its first session. The headless replay checks both cases in the same catalog.

SDL stores named-profile options for Crossword, Scrabble, Algebra, Scramble, Numberology, and Syllogism beside the corresponding profile INI. The default profile retains the original sidecar paths, and explicit settings-path overrides still take precedence. Switching users in the picker reloads the six task configurations with the original CLI arguments. The replay checks named versus default sidecars and opens Scramble from the hub after switching users.

SDL imports the original INI options for Crossword, Scrabble, Algebra, Scramble, Numberology, and Syllogism. Valid profile settings layer over the built-in defaults, saved SDL options layer over the INI, and CLI overrides apply last. The headless checks compare each INI-configured launch with equivalent CLI arguments and verify the full precedence chain in Scramble.

SDL applies the Python profile’s Sudoku, Jigsaw, Go, and Crossed Wires options at startup and after switching users. CLI options can still override individual fields. Jigsaw translates a supported square piece count to the controller’s side length. Nonsquare grids and counts beyond the SDL controller’s supported sizes remain open.

SDL Jigsaw also accepts Python piece counts that produce rectangular grids, within the native 100-tile capacity. It uses the Python square-crop rule to choose columns and rows, and uses both dimensions for shuffling, rendering, and hit testing. The native check solves a two-tile board by pointer and verifies adaptive growth. The headless replay checks 1×2, 2×3, 3×4, and 9×9 profile layouts. Jigsaw dumps now include the row count after the existing fields. Larger grids remain open.

SDL Jigsaw renders DIV2K PNGs from the original data directory using SDL’s PNG loader. Each tile samples its portion of the photograph’s centered square crop. The preview shows the whole crop when enabled. A headless pixel replay checks a shuffled tray and the preview against a four-color PNG with out-of-crop margins. SDL builds without the PNG loader and sessions with missing or unreadable photographs use the existing colored tiles.

SDL Jigsaw now supports up to 1,024 tiles, including the Python configuration’s example of a 1,000-piece request producing a 32×32 board. The desktop frame buffer and decoder accommodate the complete solved grid and its tile marks. The headless replay opens the large board from a profile, and the native self-test completes the final swap and decodes the resulting frame. Counts above 1,024 remain open.

Jigsaw rendering and pointer input now share Python’s tile-spacing rule. Tiles use a 2-pixel seam at pitches of at least 24 pixels, a 1-pixel seam below that down to 10 pixels, and no seam on denser boards. Pointer input maps directly to the row and column, including seam clicks and the outer board edge. The desktop self-test checks all three spacing thresholds and both click boundaries on a 32×32 grid.

SDL Jigsaw highlights the tile under the mouse and clears the highlight when the pointer leaves the board or window. Clicks and motion both account for the letterboxed viewport. The dummy-video replay checks hover, exit, re-entry, and selection on a 1200×684 window.

SDL Jigsaw reads and updates the Python DIV2K `seen.txt` rotation. Each new puzzle draws from unseen filenames when possible. When the library is exhausted, SDL starts a fresh rotation and avoids repeating photographs already shown in the current session while alternatives remain. The headless replay seeds a Python-format history, opens two separate SDL processes, and checks the next photograph and rotation reset. SDL uses a separate seeded photograph RNG to preserve the existing puzzle shuffle stream, so the exact photograph order can differ from Python.

Jigsaw displays the original per-puzzle verdict with swaps, minimum swaps, and elapsed time. At session end it shows solved puzzles, mean swap efficiency, mean solve time, and the largest puzzle’s actual piece count. The shared controller keeps both side length and piece count for rectangular results. The WebAssembly smoke test checks both rendered messages and the desktop self-test verifies the recorded piece count for a rectangular solve.

SDL Jigsaw warns when the local DIV2K library has fewer photographs than the session needs. It distinguishes an empty library, unreadable PNGs, and a missing PNG loader. Unlike the Python photograph task, SDL keeps the board playable with colored tiles when it cannot load an image. The dummy-video replay checks the rendered notices for a small library, an empty library, and a corrupt PNG.

SDL Jigsaw uses Python’s integer photograph crop and tile bounds, translated from Pyglet’s bottom-left origin to SDL’s top-left texture coordinates. The desktop checks cover odd landscape and portrait margins and leftover pixels on rectangular grids. The headless photograph fixture also uses odd dimensions.

SDL Jigsaw now reduces an untouched puzzle to fit the photo’s pixel dimensions. It restores the shuffle state from before the deal so the smaller board uses a fresh permutation from that same point in the random stream. A one-pixel square uses the colored-tile fallback because it cannot produce a swap puzzle. The headless replay checks that a 2×2 PNG reduces a requested 3×3 board to 2×2.

SDL Jigsaw supports Python’s keyboard cursor. The arrow keys move within the grid, and Enter or Space picks the focused tile. The orange cursor outline follows the same priority as Python’s picked and hovered outlines. The native self-test checks edge clamping and selection of tile 33 on a 32×32 board.

SDL Jigsaw now opens its five-option menu with C on the ready/results screen or on Jigsaw in the hub. Arrow keys edit the draft, Enter applies it, and Escape discards it. A click selects a row, and clicking the selected row changes its value. Applied choices carry to the next Jigsaw launch in the current process. The native check verifies apply and cancel, and the dummy-video replay applies a rectangular grid from the hub and launches it.

SDL saves Jigsaw menu choices beside the selected profile as `<profile>.jigsaw-options`. The saved choices load after the Python INI and before command-line options. The headless replay applies options in the hub, restarts the process, and verifies profile isolation, CLI precedence, and fallback to the INI for an invalid record.

The SDL headless replay applies Jigsaw’s options once with the keyboard and once with a mouse click, then compares the saved settings.

SDL Sudoku exposes the four Python task options from the ready/results screen and the hub. Keyboard and mouse edits use the shared grid options screen. Applied choices save to the selected profile’s `.sudoku-options` file and load between the original INI and CLI overrides. The dummy-video replay changes the level by mouse from the hub, launches the configured puzzle, and checks the saved level and CLI precedence in separate processes.

SDL Sudoku accepts keypad digits and keypad zero for erase. O opens options mid-puzzle, and C opens options when it is outside the board’s digit range. On 12×12 and 16×16 boards C still enters digit 12. The desktop self-test checks that cancelling mid-puzzle retains the active puzzle and cursor.

The shared Sudoku controller now tracks clean solves and total solve time alongside solved puzzles, slips, and highest rung. Total time is summed in milliseconds before truncating to seconds, as in the Python score. The desktop self-test scores a clean solve followed by a five-slip solve and verifies both adaptive directions. The WebAssembly replay compares the new counters directly with the Python oracle.

SDL Go opens its level and positions-per-run menu with C from the task hub or during play. Keyboard and mouse edits stay in the menu until Enter applies them and resets the run. Escape resumes the current position. SDL saves applied settings beside the selected profile as `.go-options` and loads them after the Python INI and before the CLI overrides. The headless replay changes both values from the hub, launches Go, and verifies the settings after restarting.

SDL Crossed Wires exposes all four Python settings from the hub with C and during play with O. C also opens the menu on four-key levels. On eight-key levels it keeps its southeast binding. The draft preview updates the grid, wiring, targets, press budget, and adaptive rule as options change. Applying a draft resets the run and saves a per-profile `.wires-options` file. SDL loads it after the original Python INI and before CLI overrides. The dummy-video replay edits all four fields and verifies restart persistence, and the WebAssembly replay compares gameplay and scoring with the Python oracle.

SDL Go’s options preview updates from the draft level and run length. It reads the same difficulty table as the Go generator for board size, target stones, visible hints, and decoy sizes. The headless replay wraps the draft from level 1 to level 10, reduces three positions to one, and checks the rendered preview for the selected target and decoys.

The SDL Go menu starts from the profile’s resolved settings even after a number-key shortcut changes the current run’s level. The replay confirms that SDL leaves the Python INI intact and falls back to it when a native options file is malformed. Go renders the Python verdict text in the shared green or red band. It retains the last verdict on the results screen and clears it for a new position or run. The WebAssembly replay checks the color, text, and position against the Python reference.

The SDL executable now calls Elisa directly with a table of platform bindings. Elisa expands arguments and owns optional MuJoCo startup and diagnostic dispatch. The C entry point supplies SDL and optional library symbols and checks the event ABI against SDL’s headers. Its test bindings still allow the headless harness to drive the production entry point.

Both SDL desktop configurations now link an Elisa executable entry point. The build selects SDL PNG support from the headers and font support from the build configuration. The optional MuJoCo executable binds its Marble functions from Elisa as well. SDL header assertions and the injected event replay harness still compile C. The Windows MuJoCo OpenGL procedure bridge remains C.

The Windows ARM64 MuJoCo build generates Elisa OpenGL forwarders from the renderer’s FFI signatures. SDL supplies the procedure addresses at context startup. All 61 symbols match the C bridge. A native ARM64 callback smoke test exercised the generated forwarders, and Stage1 emitted a Windows ARM64 object. Windows runtime rendering remains unverified. Windows x86 builds keep the C bridge because the compiler interprets odd indirect function addresses as closures and its raw FFI call lowering does not yet support void returns.

Crossed Wires keeps the last round’s colored verdict on the final screen, while the status line shows the overall run score. The Python replay verifies the verdict’s text, color, and bottom-band position across 159 actions, including completed, partial, and missed rounds.

The SDL task hub accepts clicks on category tabs and task cards. Hit testing shares the rendered layout and converts logical-window coordinates through the letterboxed framebuffer. Card clicks invoke the same launch path as Enter. Dummy-video replays launch Go by mouse at 912×684 and 960×480 and verify that Escape returns to the hub. The 56-case scene sweep produced byte-identical output before and after the layout extraction.

Space opens the SDL task hub from the title. Escape returns from a task to the hub and from the idle hub to the title when launched from there. Reopening the hub keeps the category and selects its first card. Direct hub launches retain their existing Escape handling. The dummy-video replay covers key repeat, mouse task launch, restored category, and the full return path, with Go options supplied at title startup.

The Elisa SDL adapter for Tower of Hanoi reads the Python profile’s disks, towers per run, and adaptive setting. It uses the shared scene’s canvas for mouse hit testing and accepts the number row and keypad. Native self-tests solve a three-disk tower in seven moves, decode the verdict frame, and check the feedback deadline and adaptive growth. SDL launch, options-menu, and return-to-hub integration for Hanoi are still open.

Tower of Hanoi launches from the Planning category or with `--screen hanoi`. SDL routes mouse and number-key input to the controller, advances the solved-round timer, and frees the run on exit. The internal desktop tables append a 38th controller slot with the earlier slot indices preserved. The dummy-video replay solves the profile-configured three-disk tower from both entry points. The in-game options menu remains open work.

The SDL Tower of Hanoi options menu opens with C from the Planning hub or the task’s ready and results screens. It previews the minimum move count and applies disk count, towers per run, and adaptive growth. SDL saves choices in a per-profile `.hanoi-options` file. The headless replay checks the live preview, Escape cancellation, keyboard and mouse edits from the hub, and restart persistence.

Hanoi now shows the original colored verdict on a solved tower and retains it under the end-of-run summary. The WebAssembly smoke test checks a seven-move perfect solve, a nine-move solve, the final summary, and verdict clearing on restart. The diagnostic verdict field keeps its existing results-screen behavior.

Traveling Salesman launches from Planning or with `--screen salesman`. SDL reads the four original TSP settings from the selected Python profile, uses the requested seed, and shares the renderer’s canvas with city hit testing. The dummy-video replay starts and completes a five-city route from both entry points. The options overlay remains open work.

The Traveling Salesman options menu opens with C from Planning or the task’s ready and results screens. It exposes all four Python dials and explains the exact shortest-route scoring, adaptive growth, and the setup delay at 16 or more cities. SDL saves applied choices per profile. The dummy-video replay verifies keyboard and mouse editing, preview and cancellation, persistence across restart, and fallback to the Python INI for invalid saved data.

Traveling Salesman retains the last route’s colored verdict under the overall score. The WebAssembly smoke test checks a suboptimal route, an exact shortest route, the final summary, and verdict clearing when a new route starts. The diagnostic verdict field retains its existing completed-run representation.

The SDL hub and the six grid options menus accept keypad Enter. The options menus stop at the first and last rows and let Page Up and Page Down select either end of the visible list. The Traveling Salesman replay checks the row boundaries, both page keys, keypad apply, and keypad launch.

N-in-a-row launches from Planning or with `--screen ninarow`. SDL reads the Python profile’s level, trial count, board overrides, and feedback and adaptive settings. Mouse clicks use the rendered board geometry. The dummy-video replay launches both routes, selects a cell with the mouse, moves with an arrow key, and submits with keypad Enter. The options overlay remains open work.

N-in-a-row’s SDL options menu opens with C on the Planning card or O outside an active question. All seven Python settings are available, with a live board, pellet count, and line-length preview. SDL saves applied choices per profile. The dummy-video replay checks cancellation, mouse and keyboard edits, keypad apply, and restart persistence.

N-in-a-row renders a green Right or red No verdict below the board. The last verdict stays visible with the run summary and clears when a new position starts. The WebAssembly smoke test checks both verdict colors and text, final-summary retention, and restart clearing.

The top-down Maze launches from Planning or with `--screen maze` and uses the original Python profile’s level, trial count, adaptive difficulty, and trail visibility. SDL passes the launch seed to the shared controller. Both launch paths have a dummy-video replay for walking with WASD, restarting the current maze, and cleanup.

Maze opens the SDL options menu with C from Planning or during play. The menu exposes the four Python settings and previews maze dimensions, locked doors, minimum steps, and route constraints. Applying resets the run and saves the choices in the profile’s `.maze-options` file. The macOS dummy-video suite verifies live preview, cancellation, keyboard and mouse edits, keypad apply, persistence across restart, and fallback to the Python INI for malformed saved options.

Maze retains the last solve’s colored verdict underneath the end-of-run summary and exposes the perfect-solve count alongside the other Python score fields. The SDL replay completes a locked level using the original Python solver’s 57-step route. The WebAssembly replay checks the summary and retained verdict for both perfect and suboptimal solves, and confirms that restarting clears the previous verdict and perfect-solve count.

3D Sokoban launches from Planning or with `--screen sokoban3d`. SDL reads the five `SOKO3D_*` settings from the selected Python profile and uses the shared Elisa controller and renderer. The macOS dummy-video replay verifies both launch paths, seeded board startup, turning, undo, restart, and return to the hub.

3D Sokoban opens its options menu with C from Planning or during a warehouse. The preview shows the selected warehouse dimensions, box count, trap density, and fixed plan behavior. Applying resets the run and saves all five choices in a per-profile `.sokoban3d-options` file. The macOS dummy-video replay checks live preview, cancelling during a warehouse, keyboard and mouse edits, keypad apply, restart persistence, and reading the Python INI when saved SDL settings are malformed.

3D Sokoban now computes par using the first-person step solver. The controller distinguishes exact minima from proven lower bounds, grades adaptation by steps, and keeps the last verdict under the run summary. The SDL replay follows Python’s nine-step solution from Planning and repeats it with eighteen extra turns to verify the displayed verdict, efficiency, and both adaptive directions. The Stage1 WebAssembly replay independently verifies the shortest route and retained verdict. For level 11 and launch seed 42, the original Python 3.13 reference environment and Elisa generate identical walls, goals, traps, crates, and starting pose. Both report a proven lower bound of 56 steps. Running the pure Python generator with macOS’s Python 3.9 produces a different warehouse for this seed. The WebAssembly replay locks the Python 3.13 board and lower bound.

3D Sokoban now displays the Python wall and blocked-crate messages when movement fails. The WebAssembly replay exercises both cases and confirms that each failed move leaves the pose, crate positions, and step count intact.

Cookie Thief has an Elisa controller for seeded rounds, the setup and beat clocks, grab, leave, and golden-cookie inputs, and the verdict delay. Waiting advances through the same clock as other actions. The controller tracks clean rounds, cookies and points, adjusts the rung using the previous four rounds, computes the original 400-deal guessing baseline, and renders through the existing scene. The Python environment also has a coach for dense reward and an explicit wait port. The desktop UI advances time without a wait key. The standalone headless controller differential replays the original UI's lifecycle methods for 792 updates across four completed runs.

Cookie Thief now opens from Self-Control or with `--screen cookie-thief`. SDL reads the five `COOKIE_*` profile settings, passes the selected seed to the Elisa controller, and advances its timer in the desktop frame loop. The macOS dummy-video replay completes a clean round from each launch path and checks the verdict, summary, and return to the hub. The command-line dump steps through setup and waiting without starting a video driver.

Cookie Thief’s SDL options open with C from Self-Control or from the ready and results screens. The five Python settings use the original menu choices. The live preview updates quota, doorway warning, golden-cookie and decoy rules, and the 400-round guessing estimate. Apply resets the run and saves a per-profile `.cookie-thief-options` file. The headless replay verifies preview and cancellation, keyboard and mouse changes, keypad apply, process restart, and fallback to the original INI for malformed saved settings.

Cookie Thief now launches from Self-Control on the web. The browser hands keyboard actions, animation-frame timestamps, and rendering to the shared Elisa controller through common-v1 WebAssembly. The Node replay uses the production web handlers with a virtual animation clock, verifies a complete scored round and its summary through the ABI, and checks that Escape cancels the scheduled callback and disposes the controller.

Cookie Thief’s web options open with C from Self-Control or from the ready and results screens. SDL and web share the Elisa menu choices and renderer, including the level preview and measured guessing baseline. The web replay verifies keyboard and pointer edits, cancellation, applying to the active controller, browser-storage persistence, and fallback for invalid saved values.

Cookie Thief’s controller and common-v1 WebAssembly interface now support opt-in per-beat coaching. The labels follow the Python implementation’s observed state. A seen grab produces a red label, cookies that land during the beat produce a green label, and a quiet beat clears the label. The round verdict takes precedence when the round settles. The differential compares coaching enabled and disabled across 1,584 updates and eight completed runs. The WebAssembly replay checks label text, color, and clearing. The Python environment’s separate receipt and pixel-verification infrastructure is outside this controller change.

Elisa now exposes the public outcome pixel reader through the native SDL and WebAssembly ABIs. The reader uses the original bottom-band colour thresholds and label-gap rule, derives the scalar from the frame, and rejects invalid dimensions and ranges. The headless differential compares 18 RGBA fixtures with the Python reader, including ties, separated labels, empty bands, and genuine zero scores.

The native and WebAssembly evidence exports now generate lowercase SHA-256 digests and verify a final frame against both its digest and its pixel-derived verdict scalar. The differential checks Python’s digests, SHA-256 padding boundaries, and altered alpha bytes that leave the scalar intact.

The public outcome verifier now checks complete evidence sequences and receipt bindings in Elisa. The native and WebAssembly ABIs accept a host-resolved archive and ledger record. Seventeen differential cases compare the normalized verifier with Python, covering missing frames, altered bytes, swapped receipts, mismatched trial sequences, and legacy receipts.

The web runtime exposes a public-outcome verifier for JavaScript hosts. It validates public outcome objects, marshals Map or plain-object archives and ledgers into the Elisa verifier, and releases the temporary buffers. The headless suite compares both host representations against the Python oracle and checks rejection of private fields and malformed digest lists.

The web shell can now capture its main 2D canvas into a private, digest-keyed frame archive. Capture records the backing-buffer dimensions, sequence number, and monotonic timestamp. The headless replay exercises the canvas API with fixtures and verifies a receipt-bound outcome against the stored frames, including rejection after mutation or clearing. A headless replay now exercises receipt issuance and settlement through the frame archive. Most browser task routes still need to open response windows and publish rendered feedback through this API.

Cookie Thief now has a stepped browser environment backed by the Elisa
controller. The environment owns its virtual clock and uses a caller-supplied
2D canvas, so it can run alongside ordinary play. It opens response windows
from rendered frames, maps the four Python action ports, publishes sparse
verdicts and optional dense rewards, and releases its controller and evidence
on close. The Node replay exercises the production renderer's verdict
commands with synthetic RGBA. A separate headless Chrome replay verified
actual verdict glyph pixels and receipt evidence in both themes.

The stepped Cookie Thief boundary now returns the Python observation fields,
queues outcome and completion events, and exposes per-run accounting and
seeded reset. The replay covers sparse outcomes after an idle response
window, ordered round evidence across action windows, expanded dense action
ports, event draining, and reset isolation. Browser observations are
synchronous copies. Cookie Thief rejects a separate think clock, as the
Python environment does for tasks with their own clock.

The Elisa task evidence verifier now handles the Python task boundary's
zero concessions. Cookie Thief verifies these against the same archived
bytes and settled receipts used for scored outcomes. The headless
differential calls the original Python verifier for zero claims with
complete, missing, and altered evidence. The Cookie Thief replay also
rejects changed feedback pixels and an unused receipt for a quiet frame.

The stepped Cookie Thief browser environment can now publish its frames to a
caller-supplied SharedArrayBuffer. Elisa writes the exact Python NWFB
version 1 header, followed by the same top-down RGBA pixels returned by
observation. The headless replay compares the header byte for byte with
Python across publication, completion, and reset. The native ABI also
exposes the header writer.

Native Elisa callers can create, publish to, and release OS-named NWFB
mappings through FFI. A macOS SDL gate attaches with Python's own
`multiprocessing.shared_memory` reader and checks bytes, updates, ownership,
and name reuse. The native publisher requires a free name and a capacity
chosen by its caller. The SDL render loop publishes to that mapping when
`NW_SHM` is set. A separate Python process reads the actual Cookie Thief
pixels in the macOS dummy-video replay and checks unlink on desktop shutdown.
The native mapping test and the SDL desktop render-loop replay also pass
on Linux ARM64. The Linux desktop gate used a cross-compiled application
with the existing Stage1 runtime and SDL software renderer. Windows
runtime verification remains open.

An isolated headless Chrome replay checked the browser frame archive against
the live Marble Maze WebGL stage. All 1,913 sampled stage pixels matched,
and the independently recomputed SHA-256 matched the archive digest. The
replay uses the production MuJoCo run and canvas compositor.

The Linux SDL gate exposed an uninitialized starting rung in the 3D Maze
controller. The controller initializes the rung before displaying Ready,
and the native startup replay explicitly checks the CLI-selected value.
Linux desktop and replay links include libm. Native source preparation
also skips the transient entries created by concurrent WebAssembly builds.

The Linux ARM64 build and SDL gate pass with MuJoCo 3.12.0. The relocated
Linux package also passed its loader and application smoke checks with
bundled SDL_ttf. Its TrueType and bitmap fallback screenshot checks
produced distinct PNGs. Under
Xvfb the packaged Marble Maze drew its OpenGL stage, published the
composited frame to Python through NWFB, and unlinked the mapping on quit.
The Linux, macOS, and Windows packagers accept both MuJoCo third-party
notice filenames. The Linux release archive layout and the macOS legacy
layout were exercised on their respective platforms.

The Windows x64 desktop and MuJoCo variants cross-link as PE executables
against SDL 3.4.20 and the official MuJoCo 3.12.0 import libraries. The
MuJoCo build imports SDL frame readback, the Win32 named mapping calls,
and the physics step from their expected DLLs. The field offsets used by
the Elisa FFI matched MinGW's compile-time checks against the Windows
headers. Stage1 also emitted the Windows ARM64 MuJoCo module and Elisa
OpenGL forwarders. Windows still needs executable and package smoke
tests on a Windows runtime. The x64 build still uses the C OpenGL
procedure bridge.

The browser now uses the shared Elisa Jigsaw grid-fitting logic after
decoding a photograph. An image whose square crop is smaller than the
configured grid reduces the board before pointer input is accepted.
The WASM replay checks the seeded 2×2 permutation, solve, and result
count after fitting a 3×3 setup to a two-pixel crop. The browser test
checks rectangular tile sampling and colored-tile fallback when the
image cannot form a playable grid.

Browser Jigsaw now uses the shared cursor for arrow-key movement and
Enter or Space selection. Both keyboard and pointer input wait for the
photo grid to settle. Pointer hit testing uses the fitted row count.
A headless Chrome replay imported a two-pixel photo and solved the
resulting 2×2 puzzle with one keyboard-driven swap.

Browser Jigsaw starts the solve clock when the decoded photo is ready.
If loading fails, the colored board becomes playable and starts the clock
at the fallback. The controller accepts one photo-ready timestamp per
round, and the replay verifies that loading delay and a duplicate
notification do not affect the recorded solve time.

The SDL Jigsaw path uses the same photo-ready clock as the browser. SDL
settles the photo size or colored fallback before accepting solve input.
The dummy-video replay queues an early selection and delays the first
photo frame by 400 ms. It verifies that the tiny photo still fits the
board and that only the subsequent solve time is recorded.

Browser Jigsaw offers Python's piece-count presets through 900 and
preserves earlier side settings by converting them to piece counts.
The WASM API accepts requested counts up to the controller's 1,024-tile
capacity, including arbitrary requests such as 1,000. The shared display
list identifies each photograph tile and the preview by asset ID. The
WASM replay checks every sprite ID in a 1,024-tile board, and headless
Chrome verifies all six tile crops of a rectangular board.

Jigsaw now supports Python's full preset ladder through 2,500 pieces in
both SDL and the browser. The SDL frame buffer and decoder accommodate
the 50×50 board with a separate solved outline for each tile. Native
tests cover legacy profile counts of 1,600 and 2,500, and the WASM
replay checks all photo sprite IDs through tile 2,499. The custom-count
path extends the board beyond this preset ladder.

SDL Jigsaw preserves the piece-count progression for its default board
and for square counts read from Python INI files. The native replay
solves a nine-piece board in the minimum number of swaps and confirms
that the next board has three columns and four rows. It exercises both
default startup and a named profile. The explicit `--jigsaw-side` flag
continues to select the desktop's side-based mode.

The Elisa Jigsaw controller supports Video Jigsaw's 4:3 grid, adaptive
piece-count progression, preview geometry, and pointer hit testing. Web and
SDL list Video Jigsaw immediately after Jigsaw Puzzle in Reasoning and open
the task's separate options with C. The web shell stores
imported clips in IndexedDB and keeps clip rotation and options separate from
Photo Jigsaw. Every tile and the optional preview use the same center-cropped
320×240 video frame. A headless Chromium replay imported a synthetic WebM,
observed moving tile pixels, solved the 3×2 board by pointer, loaded the next
3×3 puzzle, and checked clip resource release and option persistence.

SDL Video Jigsaw launches with `--screen video-jigsaw`. Elisa uses the SDL
process API to decode UCF-101 AVIs with ffmpeg and display them through one
streaming texture. It reads Python's `VIDEO_JIGSAW_*` settings and
`seen_jigsaw.txt`, checks successive clip segments for motion, and returns
to the ready screen when it cannot load a clip. The SDL dummy-video replay
checks moving tile pixels, the source rotation file, and the empty and corrupt
library messages. The macOS, Linux, and Windows packagers can stage ffmpeg
beside the application and run a real MPEG-4 AVI decode through Elisa before
accepting the package. The app uses that copy before searching `PATH`.
Relocated ARM64 packages passed the decode on macOS and Linux with an empty
search path. The Windows packaging path still needs a native run.

The browser uses its own video codecs. UCF-101 files in unsupported AVI
encodings require conversion before import. If all candidates fail to play,
the browser returns to the ready screen so the player can replace the clips
and start again. Attempted clips count toward its independent rotation.
Like Python, the browser prefers the first visibly changing clip among up
to four candidates and falls back to the last playable still clip. The
browser samples three segment starts by seeking in the decoded media,
using the original packed-RGB sample stride and difference threshold.
Video Jigsaw supports the Python
2,500-piece preset, which rounds to 2,552 tiles on a 58×44 board. The
WebAssembly smoke test checks every sprite ID, and SDL verifies the solved
frame fits its display buffer and that the Python INI loads the preset.
Video Jigsaw also accepts custom counts through the Python INI on SDL
and through the web options field. Counts beyond the decoded 320×240
grid saturate at 76,800 tiles. Photo Jigsaw accepts custom counts through
the Python INI and web options field as well. Its shared tile storage
allows 277×277 tiles. Smaller photos reduce the grid to fit the square crop.
Python can exceed that board capacity when a sufficiently large photo is
available.

The shared Elisa Video Sequence controller and scene cover equal-length
cuts, synchronized playback indices, click-to-swap ordering, adaptive
piece counts, centered rows, and the score display. The SDL self-test
replays Python's seeded permutations through two rounds. The shared SDL
decoder supports Video Sequence's 160×120 RGB format and measures the
minimum motion between consecutive segment starts. The SDL adapter reads
Python's options and UCF-101 `seen.txt`, tries up to six clips, and prefers
the first clip that reaches the motion threshold. If none qualify, it
keeps the strongest playable candidate. The headless media replay checks
empty-library handling, corrupt clip recovery, and rotation reset. SDL
refreshes the catalog before each round, tracks attempted clips by filename,
and advances the shared RNG like Python’s media pool. The replay adds a
clip between rounds and checks that SDL loads it after rotation resets,
even though the new filename changes the sorted positions of the earlier
clips. Both rounds reproduce the original Python seeded shuffle.

Video Sequence is playable on SDL from the Reasoning hub or with
`--screen video-sequence`. Space starts the run and two clicks swap tiles.
SDL streams each segment into its own texture and releases unused textures
when the task closes or advances. The software-renderer replay checks
the decoded colors in their shuffled positions and swaps pieces by
pointer. The desktop options screen opens with C from the task or its
Reasoning card. It reads the four Video Sequence settings from Python's
INI and saves changes beside the selected profile in
`.video-sequence-options`. The options replay tests cancel, wraparound,
clicking a toggle, and reloading the saved profile. The WebAssembly API now drives the shared controller and scene. Its replay
covers loading and retry, dropped remainder frames, pointer swaps, and the
final score. The browser task is available in Reasoning and shares the
imported clip library with Video Jigsaw. It uses independent clip rotation
and settings, decodes with browser-supported codecs, and draws the source
frames selected by Elisa. The headless Chromium replay imports a WebM,
identifies the shuffled segments from canvas pixels, solves by pointer,
and checks profile options and corrupt-file recovery.

Hidden Rule’s Elisa kernel generates the original item and rule spaces,
then produces seeded free examples, noisy lamp readings, and balanced
exams. The differential sweep compares every rung from 1 through 22
with the Python source, including 110 complete rounds of notebook tests,
exam answers, and costs. Elisa’s reference player matches the original
test choices, exam answers, and par for all 110 deals. The session
controller builds the object under test, starts the exam when the
notebook fills, grades it against par, applies the original three-second
verdict interval and adaptive rungs, and reports the run score. The SDL
app launches Hidden Rule with `--screen hidden-rule` and reads its three
settings from the Python profile. Its shared scene renders the builder,
lamp notebook, exam, and verdict. The SDL event replay covers Space,
a swatch click, testing, the exam, and the rule reveal. The desktop
Reasoning menu can launch the task or open its options with C. The
options read the Python INI and write a profile-scoped
`.hidden-rule-options` file. The desktop replay checks menu routing,
stepping through the original choices, applying, and reloading. The web
Reasoning menu runs the same Elisa controller and scene through WebAssembly.
The browser saves the three options locally. The WASM replay checks seeded
low and noisy rungs, pointer swatches, deferred exam feedback, and final
scores. The legacy Python shell has no route to this Elisa controller.

Hidden Wiring’s Elisa kernel generates the ordered gate families, deals
distinct lamp circuits, and handles noisy observations and exam costs.
The differential sweep checks the ordered truth tables and 150 seeded
rounds against Python across rungs 1–30. That replay also matches the
reference player's chosen observations, exam settings, and par. The
session replay covers switch input, automatic exam start at the
observation limit, adaptive promotion and demotion, the four-second
verdict, and restart. SDL launches the shared scene with
`--screen hidden-wiring`. It renders the switch bank, lamp notebook,
exam targets, and circuit reveal. Desktop options read the Python INI
and save to a profile-scoped `.hidden-wiring-options` file. The desktop
Reasoning card sits between Hidden Rule and Jigsaw. Enter opens the
task and C opens its settings. The browser Reasoning menu uses the same
controller, scene, and pointer hit tests through WebAssembly. It stores
the three settings locally. The seeded WebAssembly replay covers rungs
1 and 20, and the headless browser replay covers launching from the menu,
applying and reopening settings, completing a round with pointer and
keyboard inputs, and returning to the menu.
