# Syllogisms source and replay contract

The source is `original-neural-workshop-enhanced/neural_workshop/ui/syllogism.py`,
`neural_workshop/syllogism.py`, and `nwenv/syllogism.py`. The shared controller
is `src/tasks/syllogism_game.elisa`; its stable task ID is `syllogism`.

A run begins ready. Space or a click deals the first question; the source draws
one seed per question from `Random(session_seed).randrange(1 << 30)` and calls
`generate(level, seed=question_seed, made_up=not real_words)`. A generation
failure ends the run with an error message. While asking, left/up and right/down
wrap through the available answers. Enter or Space submits the selection;
number keys 1–9 choose and submit the corresponding zero-based answer. A click
does not answer. On judgment, the source records the level before adaptation,
correctness and elapsed time, shows the selected answer and (if enabled) the
working. A correct answer raises the next level and a wrong answer lowers it,
clamped to the level range, when adaptation is enabled. Space or a click advances
after judgment. At the end, the summary reports right, asked and highest level
answered correctly; restarting clears the score and result rows. The source
`score()` also reports the sum of judged durations truncated to seconds.

The environment exposes 27 answer ports and calls `choose(index)` directly;
ports beyond the current question's option count do nothing. It does not use
the UI's relative selection movement. The common protocol therefore has both
navigation actions and direct choose-and-submit action 6; fields 14–15 and
value fields 2–4 expose elapsed seconds, result count, and each result's level,
correctness and milliseconds. The correct answer remains hidden until judgment.

`test/syllogism_session_oracle.py --check` compares checked-in fixtures with the
original generator. They cover two successive session seeds on every level,
including relation, order, category, two-dimensional, three-dimensional and
compound questions, with 2–14 premise lines and 3–27 options. The separate
invented-word fixture covers levels 1, 7, 9 and 12. The web replay checks
selection wrap, invalid ports, direct answers, feedback, disabled working,
adaptive movement and restart. The SDL native ABI replay checks all 12 source
sessions, working, score, timing, and clock regression. Both use the original
question data rather than a fixed substitute question.

The temporary SDL diagnostic compiled with the existing stale Stage1 product
passed the native ABI replay; the same evidence does not prove freshness of a
production artifact or the desktop event-loop route. The fresh compiler gate,
web and Python artifact replays, headless desktop lifecycle against the fresh
artifact, cross-platform execution, and result integration remain open. No
browser interaction is required by these replays.
