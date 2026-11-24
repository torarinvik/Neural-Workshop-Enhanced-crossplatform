# Are all the branches' gains in `work`? — an audit, 2026-08-26

Short answer: **no, and now they are** — except one branch, for a reason that
has not changed.

Both `work` branches were left UNTOUCHED by this audit. Every merge happened on
a new branch in a scratch worktree, so nothing in the other agent's checkouts
moved.

## The audit

Ancestry alone is not the question — a cherry-picked or rebased commit is a gain
that has landed under a different id, and a branch can be "ahead" while carrying
nothing anyone wants. So each branch was checked by ancestry AND by content.

### Elisa-core (stage0) — was missing 29 commits, now complete

`work` lacked the whole of `nw-integration-2026-08-26` (verified by a prior
session, never landed) and our four newest `nw-port` commits, `-fstrict-fp`
among them. `nw-consolidate-2026-08-26` now contains **every branch in the
repository and every detached-HEAD worktree commit** — nothing is outstanding.

### Elisa-compiler (stage1) — was missing 3 commits plus a stranded fixture

`work` had already absorbed the "safe" integration, so the gap was small: our
three `nw-port` commits, and one orphaned test fixture (below). Landing diff is
6 files, +138 lines.

### What was NOT a gain, and why

| branch | ahead | verdict |
| --- | --- | --- |
| `codex/worktree-save-elisa-qol-validation{,2}` | 1, 2 | earlier DRAFTS of the stdlib that `codex/idiomatic-self-hosting` later committed properly; `-validation2` also commits 78 build droppings (`probe_bytes.stdout`, `final-stage1-*.stderr`) |
| `codex/worktree-save-integration-idio` | 105 | `codex/idiomatic-self-hosting` plus one wip tip |
| `codex/worktree-save-structpy-stage1-codex2` | 46 | its 45-commit body is INSIDE `codex/idiomatic-self-hosting` |
| `codex/wasm-support`, `integration`, `worktree-agent-*`, both `main`s | 0 | already contained |

The four `codex/worktree-save-*` branches are parking snapshots — an agent
committing a dirty worktree so it could be moved — not curated work.

## The one branch still out: `codex/idiomatic-self-hosting` (105)

Its payload is real and large: **85 new stdlib modules** — json, http, net,
regex, uuid, base64, datetime, process, concurrency, utf8, path, iter — plus a
lexer/parser refactor.

It stays out because **it cannot self-host**, which was measured three ways in
`integration-2026-08-26.md` and is unchanged. Landing it costs `work` its
fixpoint, which is the opposite of a gain.

The cost has since gone UP, and that is new. `work`'s 23 newest commits
(`refactor: share quoted literal scanning machine`, `scan f-strings with a lexer
machine`, `classify keywords with a when table`, ...) rewrite the lexer, and
that branch rewrites the same lexer. Merging it today conflicts in **15 files**
— `lexer_core`, `lexer_numbers`, `lexer_strings`, `lexer_tokens`, `tokens`,
`parser_decl_impl`, six `codegen_*`, `elisac.elisa`, `arena.elisa`. This is a
project, not a consolidation step, and it grows every day both sides move.

## A gain worth naming

`codex/stage0-idiomatic` is one commit, and it fixes a real stage0 crash. The
fixture that reproduces it was stranded on a WIP branch
(`test/repro/generic_optional_helpers.elisa`, 10 lines, on no other branch):

    def choose[T](value: T?, fallback: T) -> T:
        return present if value is present else fallback

On the pre-merge stage0 that is not a diagnostic, it is a compiler crash:

    error: PHI node operands are not the same type as the result!
      %termp = phi i64 [ %present, %ternary.then ], [ %fallback1, %ternary.else ]

The consolidated stage0 compiles it, and stage1 agrees. The fixture was carried
across as the regression test it should always have been.

## Merge decisions that needed judgement

**The same fix, twice, in two voices.** The one conflict in Elisa-core was
`emitStringViewStaticLiteralEqual`: both `work` and `nw-port` had independently
found the sview-through-a-reference crash, and the CODE was identical
(`emitStringCompareOperandValue`) — only the comments differed. Ours recorded
the SIGSEGV symptom, theirs the triggering expression. Kept one comment carrying
both facts; taking either side alone would have thrown away a real explanation.

**A stale generated artefact, caught by a test.**
`TestRuntimeCollectionsInterfaceMatchesImplementation` failed after the merge.
`collections.elisa` is byte-identical on every branch — but the INTERFACE the
compiler emits from it changed, because the merge changed what the compiler
knows about wasm: `ELISA_TARGET_OS_WASM` is now a known target constant, and
`ARENA_BACKEND_WASM_HEAPBASE` is now actually SELECTED rather than merely
defined, so the emitted interface carries `ARENA_WASM_USES_HOST_ALLOCATOR`
instead of the older bump-pointer externs. Regenerated. The generator's input
never moved; its behaviour did.

**`.DS_Store` is tracked in Elisa-compiler** (`.DS_Store` and `src/.DS_Store`,
while `.gitignore` covers only `test/.DS_Store`), so it churns whenever two
checkouts meet. The merge carried a meaningless binary delta; it was dropped so
the landing diff is 6 real files.

## Verification

Not "it merged cleanly" — the merged trees were BUILT and RUN. A clean merge has
silently duplicated a function in this repository before.

### Elisa-core `nw-consolidate-2026-08-26`

  * `go build ./src` — clean
  * `go test ./...` — **14/14 packages ok, 0 failures**
  * `-fstrict-fp` survived intact: both arg parsers, the backend tier that beats
    every other, and `strict_fp_test.go`. Three ported modules depend on it.

### Elisa-compiler `nw-consolidate-2026-08-26`

  * seeds from the consolidated stage0, then `self_host_gen2 OK`
  * **FIXPOINT: `gen3.o == gen4.o` byte-identical**
    (`01121904a46b58cef0451505e3270235a9325003261d7292f6dda08acb52b480`)

### The port, on the consolidated toolchain

  * **60/60 differential suite runs, 0 failures** — every module, both compilers,
    against the Python reference. Run TWICE: once before the `collections.elisai`
    regeneration and once after, since that file is read from the source tree at
    runtime rather than embedded, so the first run had not exercised it.

  * all three repro fixtures compile, link AND return the right value on stage1 --
    not merely "it compiles":

        cross_module_const        18   (documented in the fixture)
        inline_loop_value         17   (9 + 8, with a -1 guard proving the inline
                                        and block loop forms agree)
        generic_optional_helpers   4   (choose[i64](maybe_value(4), 10))

### Nothing was disturbed

  * `~/.elisac/elisac` byte-identical before and after (`e2f0caf537fc143372c57ec5`),
    mtime unchanged. Elisa-compiler has no hooks; Elisa-core's were bypassed with
    `-c core.hooksPath=<empty>` on every git operation.
  * Elisa-core `work` still `da8cb230`, still 26 modified + 7 untracked.
  * Elisa-compiler `work` still `3fa962a5`, still clean.

## Landing: two different costs

**Elisa-compiler — cheap.** No git hooks in that repo, the main worktree is
CLEAN, and the landing is a 6-file fast-forward. Reversible with a branch reset.

**Elisa-core — not cheap.** `core.hooksPath` is repo-wide and its post-merge /
post-commit / post-checkout hooks rebuild the shared `~/.elisac/elisac` from
whatever tree they fire in. And `work` is checked out in the other agent's
worktree with 33 files of live work, which git will not merge over: landing
means stashing their work and having them reapply it. That cost was paid once
already this week and produced 10 conflicts.

Neither was done. Both wait on a decision.

---

# LANDED on Elisa-compiler `work`, and the branch sweep

## `work`: `3fa962a5` -> `6921b84a`, 7 commits

Two fast-forwards, each gated on its own before it moved:

  1. **`3fa962a5 -> 6207394f`** (6 commits) — the consolidation: our three
     `nw-port` commits plus the stranded crash fixture. Verified IN THE MAIN
     WORKTREE after landing, not only in the scratch checkout: 60/60 suites.

  2. **`6207394f -> 6921b84a`** (1 commit) — a fix SALVAGED from a branch that
     was then deleted (below).

The main worktree was clean and the repo has no git hooks, so nothing was
stashed and `~/.elisac/elisac` never moved (`e2f0caf537fc143372c57ec5`, mtime
unchanged throughout).

## The salvage: reading the wip branches before deleting them

The `codex/worktree-save-*` branches looked like parking snapshots, and mostly
were. But "delete the non-gains" still requires OPENING them, and two carried
content that existed nowhere else:

  * `codex/worktree-save-integration-idio`'s tip added `push`/`extend` to the
    discarded-call list — **already in `work`** under a different sha. Nothing
    to save.

  * `codex/worktree-save-structpy-stage1-codex2`'s tip was NOT in work, and
    all four files it touches exist on `work`. Cherry-picked onto `work` ALONE
    — independent of the 105-commit stack it was sitting on — and it applied
    cleanly:

      - `struct_contains_darray` was a tree walk over a GRAPH. Recursive and
        mutually recursive records are legal, so it could fail to terminate;
        now memoized (0 unknown / 1 visiting / 2 no / 3 yes), which both breaks
        the cycle and makes later ABI queries O(1).
      - a string literal is a static `u8` reference and stage0 merges it with
        the plain `u8&` spelling; the coarse table saw `u8` and reported a FALSE
        ternary mismatch. The exception is narrow by design: only a direct
        identifier recorded as `u8&`, never an arbitrary numeric expression,
        cstr or sview.

    Gated on its own: `self_host_gen2 OK`, **`gen3.o == gen4.o` byte-identical**,
    60/60 suites. Its commit message was `wip: save stage1 backend changes`;
    rewritten to say what it does, authorship preserved.

## Branches: 20 -> 4

Deleted 8 with `git branch -d` (git itself refused to delete anything not fully
merged): `codex/wasm-support`, `integration`, `nw-integration-safe-2026-08-26`,
and five August-8 `worktree-agent-*` snapshots.

Deleted 7 more as non-gains, each archived as a tag FIRST — a convention this
repo already used (`archive/niche-optional-abi-wip` predates this sweep):

    archive/idiomatic-self-hosting     archive/nw-integration-full
    archive/integration-idio           archive/structpy-stage1-codex2
    archive/qol-validation             archive/qol-validation2
    archive/generic-debug-fixture

Nothing was destroyed. Every deleted tip is still reachable by tag, and any of
them comes back with `git branch <name> <tag>`. To purge one for real:
`git tag -d archive/<name>`.

Remaining: `work`, `main`, `codex/main-worktree` (the other agent's checkout),
`nw-port` (ours, now identical to `work`).

**`codex/idiomatic-self-hosting` is the one to think about again later.** It is
archived rather than merged because it still cannot self-host, but its 85 stdlib
modules — json, http, net, regex, uuid, base64, datetime, process, concurrency —
exist in no other ref. The salvage above shows the shape of the cheap win:
individual fixes on that stack can be cherry-picked onto `work` and gated one at
a time, without taking the branch as a whole.

## Elisa-core is untouched and still pending

Its `work` is `da8cb230`, 36 commits behind `nw-consolidate-2026-08-26`, with 33
files of the other agent's live work in the checkout. Landing there means
stashing their work AND its hooks rebuild the shared binary. Deferred by
request.

Our own stage0 worktree was moved onto `nw-consolidate-2026-08-26` so the port
builds against the consolidated compiler, which is what all of the above was
verified with.

---

# LANDED on Elisa-core `work` (2026-08-26)

`work` fast-forwarded `da8cb230` -> `c84f1429`, 36 commits. The landed tree is
BYTE-IDENTICAL to the branch already verified above (14/14 Go packages, 60/60
differential suites), so the landing carried no untested content.

## The other agent's 33 files: 31 back in place, 2 handed back

Backed up three ways BEFORE anything moved — tarball, tracked diff, and a stash
tagged `wip-snapshot-2026-08-26-core` — then reapplied.

Only **2 conflicts**, down from the 10 the previous landing hit, because the
consolidation already contained most of what they had been working against.
Neither was resolved by guessing:

  * `parser_estimate.go` — a real behavioural difference (`boundedEstimate(count)`
    landed, `count` theirs) next to an untracked `parser_estimate_test.go`. That
    is live work with an intent only its author knows.
  * `analyzer_expr_operators_...go` — comment rewrites around
    `IsAggregateValueEqualityUnsupported`.

Both were restored to the landed version, so their tree has NO conflict markers,
and each was extracted as an apply-ready patch. See
`elisa-core-wip-handoff-2026-08-26.md`.

**One of their files needed nothing at all**: `llvm_aggregate_abi.go` is now
byte-identical to their edit, because the same change arrived via
`codex/stage0-idiomatic`. They had converged with the branch independently.

Worth noting for later: their untracked `ternary_byte_ref_literal_runtime_test.go`
is the stage0 counterpart of the ternary byte-ref fix salvaged into stage1 above.
Both stages were being fixed for the same gap, in two repositories, by two agents.

## `~/.elisac/elisac`: replaced at 16:23, and I cannot attribute it

Reported here rather than quietly, because an earlier draft of the handoff note
asserted the binary was untouched, and that turned out to be wrong.

Hooks were suppressed on every git operation, and that suppression works — a
controlled `git checkout work` under the same override left the mtime unchanged,
and `/tmp/elisac-autoinstall.log` is still stamped 11:52, so `install-elisac.sh`
has not run since. Yet the binary's mtime is 16:23.

Two feature probes place its provenance exactly. `-fstrict-fp` is accepted, and
`generic_optional_helpers.elisa` compiles instead of dying on the LLVM PHI
verifier — the first commit is nw-port's, the second is
`codex/stage0-idiomatic`'s, and pre-landing `work` had neither. So it was built
from the landed tree: current, not stale.

The first fingerprint attempt got this WRONG in the safe-looking direction. The
probe was written `elisac ... 2>&1 | head -3; echo rc=$?`, which reports HEAD's
status, not the compiler's — the same shell trap already recorded in
integration-2026-08-26.md, in its pipeline form. Both probes were rerun without
a pipe before anything above was concluded.

## Branches: core 6 -> 4

Deleted `nw-consolidate-2026-08-26` and `nw-integration-2026-08-26` (both fully
merged; the latter's stale scratch worktree was removed first).
`codex/stage0-idiomatic` is redundant now but was LEFT — it is checked out in
their `Elisa-core-codex` worktree and deleting it would strand that worktree.

Remaining: `work`, `main`, `nw-port` (ours, identical to `work`),
`codex/stage0-idiomatic` (theirs).

# Final state

    Elisa-core     work c84f1429   (was da8cb230, +36)
    Elisa-compiler work 6921b84a   (was 3fa962a5, +7)

Both `work` branches are now supersets of every branch in their repository. The
port builds from them and passes **60/60 differential suite runs**, with
`gen3.o == gen4.o` byte-identical.
