# Numberology replay contract and current status

The source generator in `neural_workshop/numberology.py` uses a seeded Python
integer program. Levels 1–3 are arithmetic and multiplicative sequences,
levels 4–5 use polynomials, level 6 alternating steps, and level 7 onward a
recurrence with polynomial and periodic forcing. Displayed length grows with
level. Python integer values do not wrap at 64 bits. The UI accepts digits and
one leading minus, judges a lone minus as wrong, and advances difficulty only
after a perfect session if the advance option is enabled. The environment's
ports call the task methods directly; text events, option dialogs and pointer
input are additional host responsibilities.

`NumberologyExact` uses the selected Stage1 runtime's dynamically sized BigInt
limbs for recurrence generation. The controller retains lossless decimal
bytes in dynamically grown heap buffers, grades decimal strings exactly, and
releases them on disposal. Legacy scalar fields and `numberology_term` remain
for existing clients; an out-of-i64 scalar is reported as zero, with info
fields 17 and 18 indicating whether the answer and input fit i64. Info fields
14, 15 and 16 give byte counts for the displayed terms, judged answer and
entered digits; field 20 gives the entered sign and field 19 reports generation
failure. `numberology_value` fields 0, 1 and 2 expose those byte sequences;
the exact answer bytes are available only after judgment. Existing legacy
scalar answer behavior remains available to older clients.

`test/numberology_exact_diff.py` compares 52 source-generated cases through
level 10,000, including 12 with values outside i64. The WASM controller replay
compares ten source sessions and grades a 1,341-digit answer, including
negative values, leading zeroes, wrong answers and repeated cleanup. The
runtime's compiler-rt 128-bit multiply/divide shims preserve all 64-bit limbs.
Native Python and SDL checks use the same source fixtures.

The exact controller deliberately rejects a calculated text reservation over
1 GiB and reports generation failure; its scratch arena is currently 256 MiB.
These are resource limits, not proof of parity for every finite source level.
The selected Stage0 check fails while parsing its runtime source before this
suite is reached; Stage0 compatibility is still open. A high-level sequence is
currently rendered in one text label, so readability at extreme levels still
needs work. The browser options are covered by headless tests. Python and SDL options screens
are implemented in source, but their new shared display-list export still needs
a build and end-to-end verification with a fresh compiler. Full native headed
input, persistent session results and broader visual checkpoints remain open.
The existing Stage0 scene sweep also fails in the selected runtime before it
reaches Numberology, confirming this is not specific to the exact generator.
