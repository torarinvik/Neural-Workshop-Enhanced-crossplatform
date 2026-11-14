# Numberology replay contract and current status

The source generator in `neural_workshop/numberology.py` uses a seeded Python
integer program. Levels 1–3 are arithmetic and multiplicative sequences,
levels 4–5 use polynomials, level 6 alternating steps, and level 7 onward a
recurrence with polynomial and periodic forcing. Displayed length grows with
level. Python integer values do not wrap at 64 bits. The UI accepts digits and
one leading minus, judges a lone minus as wrong, and advances difficulty only
after a perfect session if the advance option is enabled. The environment's
ports call the task methods directly; text events, option dialogs and pointer
input are additional host responsibilities. The source starts in `ready`; an
advance starts a run and deals a puzzle, entering `working`. Digits and a single
leading minus append to the entry, backspace removes one character, and an
empty submission does nothing. Submission records one result and enters
`judged`, displaying the rule and verdict. Advancing deals the next trial or
enters `done` after the configured count; advancing from `done` starts another
run. The environment maps ports 0–10 to `0123456789-`, 11 to erase, and 12 to
submit; it does not itself drive the UI's advance, options, or pointer events.
Each question is generated using a new `randrange(1 << 30)` draw from the
session RNG. Scores count correct judgments and adaptive progression increases
the next starting level only when every configured trial is correct.

`NumberologyExact` uses the selected Stage1 runtime's dynamically sized BigInt
limbs for recurrence generation. The controller retains lossless decimal
bytes in dynamically grown heap buffers, grades decimal strings exactly, and
releases them on disposal. Legacy scalar fields and `numberology_term` remain
for existing clients; an out-of-i64 scalar is reported as zero, with info
fields 17 and 18 indicating whether the answer and input fit i64. The answer
and its fit flag are hidden until judgment, including through common state. Info fields
14, 15 and 16 give byte counts for the displayed terms, judged answer and
entered digits; field 20 gives the entered sign and field 19 reports generation
failure. `numberology_value` fields 0, 1 and 2 expose those byte sequences;
the exact answer bytes and legacy scalar answer are available only after judgment.

`test/numberology_exact_diff.py` compares 52 source-generated cases through
level 10,000, including 12 with values outside i64. The WASM controller replay
compares ten source sessions and grades a 1,341-digit answer, including
negative values, leading zeroes, wrong answers and repeated cleanup. The
runtime's compiler-rt 128-bit multiply/divide shims preserve all 64-bit limbs.
Native Python and SDL checks use the same source fixtures. The separate
`numberology_session_oracle.py` executes the original UI controller methods
without opening a window. `numberology_session_replay_test.mjs` compares five
complete sessions against that oracle, including empty submission, mixed and
perfect scores, exact rule and feedback text, and adaptive and fixed-level
summaries. These replays currently use the existing WASM artifact; a fresh
current-source artifact remains to be promoted.

The exact controller deliberately rejects a calculated text reservation over
1 GiB and reports generation failure; its scratch arena is currently 256 MiB.
These are resource limits, not proof of parity for every finite source level.
The selected Stage0 check fails while parsing its runtime source before this
suite is reached; Stage0 compatibility is still open. A high-level sequence
is now paged in the shared controller, with Page Up, Page Down and pointer
controls in all three shells. Long wrong answers get their own pages after
judgment; the input line shows its most recent digits while retaining the full
exact entry. This source change still needs a fresh compiled artifact and the
page-reconstruction replay before the display is verified. SDL no longer discards
text solely because it exceeds 4,095 bytes;
a software-renderer self-test checks a 5,000-byte label without opening a
window. The browser options are covered by headless tests. Python and SDL options screens
are implemented in source, but their new shared display-list export still needs
a build and end-to-end verification with a fresh compiler. The web shell writes each judged trial to its shared result ledger, updating
the same record on session completion; a headless test covers failure and
retry, restart, partial sessions, and disposal. The Python shell also atomically stores per-session JSON records, including
partial sessions, with retry on a failed write; its headless tests cover a
failed replacement and disposal. SDL writes the same per-session JSON format and retries unsaved records on
subsequent activity; headless tests cover partial and complete runs, duplicate
notifications and a storage failure followed by recovery. Full native headed
input and broader visual checkpoints remain open.
The existing Stage0 scene sweep also fails in the selected runtime before it
reaches Numberology, confirming this is not specific to the exact generator. The standalone
`numberology_syntax_test.py` now verifies that the selected Stage0 parser accepts
the generator, controller, and scene individually; it does not establish
semantic or full-build compatibility with the selected runtime.

The source now hides the legacy scalar answer and its fit flag before judgment;
the current promoted WASM still exposes the scalar answer. The new assertions
intentionally fail against that older artifact until the fixed source is built
and verified with a fresh compiler.
