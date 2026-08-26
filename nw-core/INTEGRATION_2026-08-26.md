# Integrating the compiler branches, 2026-08-26

Both `work` branches were left UNTOUCHED. Every merge happened in a scratch
worktree on a new branch, so nothing in the other agent's checkout moved and
their uncommitted work (Elisa-core 33 files, Elisa-compiler 344) is exactly as
it was found.

## What is ready to land

### Elisa-core `nw-integration-2026-08-26` — 27 commits ahead of `work`

`codex/stage0-idiomatic` (1) + `nw-port` (25). Merged with NO conflicts.

  * all 14 Go test packages pass
  * all 22 nw-core differential suites pass against it (39,757 cases)

### Elisa-compiler `nw-integration-safe-2026-08-26` — ahead of `work`

`codex/wasm-support` (2) + `nw-port` (15). One conflict, the target predicate
table (see below).

  * self-hosts to the FIXPOINT: `gen3.o == gen4.o byte-identical`
  * nw-core suites on stage1: 22/22, 39,757 cases
  * stage1 parity gate: 188 of 190, both remainders traced to other branches

### The parity gate's 7 failures, accounted for

Two were REAL and are fixed:

  * **runtime drift guard** -- arena.elisa had diverged between the repos, since
    codex/wasm-support changed only the vendored copy. Fixing it surfaced more
    than a file mismatch: Elisa-core's copy never SELECTED
    ARENA_BACKEND_WASM_HEAPBASE (defined, implemented, absent from the selection
    chain), so a wasm target fell through to LIBC_MALLOC, and its free arm was
    `pass`, leaking every region block.
  * **ELISA_TARGET_OS_WASM unknown to stage0** -- stage0 defined
    ELISA_TARGET_OS_WASI while stage1 and the std use ELISA_TARGET_OS_WASM.
    Registered as an ALIAS: the std declares that const itself for bootstrap, so
    defining a symbol makes it a duplicate and breaks every std build.

Two were MY errors running the gate, not defects:

  * **project_report_smoke** and **diagnostic breadth baseline** resolve stage0
    as `${ELISAC:-$HOME/.elisac/elisac}`, NOT `$ELISACORE_BIN`, so they compared
    against the stale shared binary. Both pass when ELISAC is pointed at the
    integration stage0 (project report: 91 passed, 0 failed).

Three belong to other branches and are catch-up items, not merge damage:

  * **diagnostics message parity** -- `aggregate values do not support ==` is a
    diagnostic codex/stage0-idiomatic ADDS (absent from `work`); stage1 has not
    implemented it yet, which is exactly what a "stage1 covers stage0" gate is
    for.
  * **emit_ast / emit_header / emit_unsafe** -- all three fail on one fixture,
    `test/repro/wasm_minimal.elisa`, which codex/wasm-support introduces. stage0
    and stage1 disagree on the AST shape of `static if ELISA_TARGET_OS_WASM`
    (15 declarations vs 16: one keeps the node, the other expands the branch).

## What is NOT ready, and why

### Elisa-compiler `nw-integration-2026-08-26` — 124 commits ahead of `work`

Everything, including `codex/idiomatic-self-hosting` (104). It merges and the
merge is repaired, but it cannot self-host, because **that branch cannot
self-host on its own**. Measured three ways with stage0 held constant:

| tree                                   | gen2 |
| -------------------------------------- | ---- |
| idiomatic alone                        | fails: `argument 1 to "getenv" expects u8, got cstr` + `argument 1 to "write" expects sview, got i64` |
| idiomatic + only the check_firm fixes  | fails: `backend emitted no functions for this unit; declined 467` |
| full integration                       | fails: `declined 467` — the same 467, same list |

The decline is byte-identical with and without the fixes, so it belongs to the
branch, not to any merge. The merge in fact removes two of its blockers:
`getenv` was already fixed on `nw-port`, and `write` is fixed here.

For whoever picks it up: the log's own note is the useful part — *"every
function in the unit is dropped when the backend declines one; the object was
not written"*. So it is ONE root cause, not 467. The decline list is dominated
by parser functions and ends at `Std_Option_expect__Token__ov273, expect`.

## Merge decisions that needed judgement

**A silently broken auto-merge.** Git combined the two
`capture_impl_generic_params` implementations as two SEPARATE definitions in one
file, at lines 12 and 90, with no conflict marker — they sat at different
offsets. They populate different parser state: the idiomatic branch's fills
`impl_generic_names`, which `record_generic_func_metadata` already turns into
per-function generic params during the normal parse; nw-port's scanned ahead
over the impl body for `def` tokens. Keeping both would double-register every
impl member. Kept the idiomatic one; nw-port's whole delta to that file was that
function plus its call site, so nothing else was lost.

**A dropped wasm arm.** The idiomatic refactor split arena platform constants
into `arena_platform.elisa` from a tree predating `codex/wasm-support`, and its
backend-selection chain (WINDOWS / MACOS / LINUX / FREEBSD / POSIX / else) has
no WASM arm at all — so `ARENA_BACKEND_WASM_HEAPBASE` was defined and
implemented but never selected, and a wasm target fell through to
`LIBC_MALLOC`. Restored. The wasm arena itself is wasm-support's deliberate
design (host allocator via malloc/free, seeded from wasm-ld's `__heap_base`)
rather than the older bump cursor over linear memory; its free arm is now a real
`free()` instead of `pass`, which had leaked every region block.

**Target predicates.** The wasm branch's table flips its rows for a real wasm
target; nw-port registers three names the wasm branch lacks. Combined: the wasm
table and its flipping, with `ELISA_TARGET_OS_WASI`, `ELISA_TARGET_ARCH_WASM64`
and `ELISA_TARGET_ARCH_WASM` APPENDED so the index-based flips still address the
same rows. Those exist for STAGE PARITY — stage0 defines them, and a predicate
that resolves under one compiler but not the other is exactly the divergence
this port exists to catch.

## One compiler fix the integration itself needed

`semantic: a name declared as both a function and an extern is unmodeled`.
`check_firm_arg_type_mismatch` looked a callee's parameter type up in both the
function-parameter chain and the extern side table, and preferred the function
whenever both answered. Neither branch is wrong alone: the idiomatic branch adds
`module Std::Console: def write(value: sview)`, and the vendored
`debug_referee.elisa` has long declared `extern write(fd, buf, count)`. Together,
the three `write(2, ..., n)` calls in that file were checked against
`Console::write`'s FIRST parameter and rejected. Same ambiguity
`extern_parameter_type_at_firm` already refuses to guess at for two conflicting
externs, so it takes the same remedy. Conservative — it only ever suppresses a
diagnostic.

## A side effect worth knowing about

Elisa-core sets `core.hooksPath = compiler/githooks`, and that config is
repo-wide, so its post-commit / post-merge / post-checkout hooks fire from EVERY
worktree — `git worktree add` included. Each one rebuilds the shared
`~/.elisac/elisac`. Creating the integration worktree therefore rebuilt that
binary from clean `work` at 08:50. If it had been built from the other agent's
uncommitted tree, that is now replaced; rebuilding from their worktree restores
it. Every git operation after that point passed
`-c core.hooksPath=<empty-dir>`, so nothing else touched it.
