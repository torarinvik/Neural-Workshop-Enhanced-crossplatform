# Algebra replay contract and gaps

Source: `neural_workshop/ui/algebra.py`, `neural_workshop/algebra.py`,
`neural_workshop/expressions.py`, `neural_workshop/ui/taskoptions.py`, and
`nwenv/algebra.py` in the original application.

The UI has ready, working, judged and done phases. Space or a click starts a
run or advances from feedback; Enter submits only while working, Backspace or
Delete erases, and O opens options outside the working phase. Text events are
lowercased and accept digits, x, y, `+ - * / ^ ( )` and single non-leading
spaces. A blank submission is ignored. The environment has 21 ports: those
same characters except space, followed by erase and submit. It drives methods
directly and therefore does not exercise text events, clicks, or the options UI.

The original defaults are level 3, six questions, working shown and adaptive
level changes enabled; the level range is 1–12 and the selectable question
counts are 1, 2, 3, 5, 6, 8, 10 and 15. Correct answers increase the level and
wrong answers decrease it, clamped to that range. The numeric checker compares
exact fractions; the expression checker requires polynomial equivalence and
already-collected terms. Incorrect feedback gives the exact answer and, when
enabled, the source derivation. The search-space note is the base-ten log of
the generated candidate count.

`test/algebra_exact_game_test.mjs` covers equivalent fractions, higher-level
construction, long text and erase. `test/algebra_feedback_test.mjs` checks
that exact answers are hidden until judgment, round-trip through all twelve
levels, and that excessive nesting and enormous exponents return without a
trap or unbounded work. `test/algebra_diff.py` compares the kernel with the
source oracle. The Stage1 Expressions differential passed 342 source-oracle
cases after updating its driver for the current compiler effect grants. These
are controller and kernel tests, not evidence of native headed input.

The original-generated fixture and its WASM/native replay tests compare 48
questions and complete derivations across all twelve levels. The derivation
is hidden until judgment; each shell splits the shared multiline label for
rendering. `scene_algebra` matches all 28 original scene frames and 196
commands. The Stage1 Algebra differential also matches 318 source cases;
the SDL self-test covers fractional and top-rung CRT working. Native headed
rendering remains unverified.

The shared controller supports the source options and adaptive rung changes;
`test/algebra_options_game_test.mjs` covers level bounds, working visibility,
restart and seed progression. Common-v1 option `c` is 1 to hide working (zero
preserves the earlier ABI default), while `d` enables adaptation. Python and
SDL options self-tests cover controller wiring; Python also checks settings
persistence and cancel/apply behavior. A headed browser replay opened options
from the menu, saved level 12 with one question and both toggles off, started
a run with those settings, and verified cancel preserved its judged state and
saved values. Screenshot: `output/playwright/algebra-options.png`.

`test/algebra_score_game_test.mjs` checks the source summary, answer count,
highest correct rung, accumulated response time, and timing reset. The three
hosts synchronize the response clock after generating a question. The browser
uses a dedicated text field for input, composition and paste; a headed replay
typed an expression and delivered a simulated paste input, while
`test/algebra_input_events_test.mjs` exercises composition event ordering.
Python and SDL clipboard paths are covered with mocked or direct text tests.

Remaining: native headed options, persistence and real clipboard/IME
verification; browser real clipboard/physical IME verification; durable
session/result integration and broader rendering checkpoints. The expression parser has a 24-factor nesting bound to keep
untrusted text within the WASM/native stack; this is a known divergence from
the original's available recursion depth.
