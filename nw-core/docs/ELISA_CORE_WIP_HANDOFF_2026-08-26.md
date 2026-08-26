# Elisa-core `work` moved under you — what happened to your 33 files

`work` fast-forwarded `da8cb230` -> `c84f1429` (36 commits: the consolidation of
`nw-port`, `codex/stage0-idiomatic` and the wasm work). Your uncommitted tree had
to be stashed for it, because git will not merge over locally-modified files.

**31 of your 33 files are back in place.** Nothing was lost, and there are no
conflict markers anywhere in your tree.

## The 2 that need your hand

Both conflicted with the incoming commits. Rather than guess your intent, they
were restored to the landed version, and your version is here as a patch:

    nw-core/docs/reapply-parser_estimate.patch
    nw-core/docs/reapply-analyzer_expr_operators.patch

Apply with `git apply <patch>` from the Elisa-core root, or read and re-do.

  * **`compiler/src/parser/parser_estimate.go`** — a real behavioural
    difference, not a formatting one: the landed tree returns
    `boundedEstimate(count)`, yours returns `count`. You also have an untracked
    `parser_estimate_test.go`, so this looked like live work with an intent only
    you know.

  * **`compiler/src/semantic/analyzer_expr_operators_...go`** — comment rewrites
    around `IsAggregateValueEqualityUnsupported`, plus a note about StringView
    carriers having their own content-equality lowering. Yours is the fuller
    text; the landed version came in with `codex/stage0-idiomatic`.

## One of your files needed nothing

`compiler/src/backend/llvm_aggregate_abi.go` is now byte-identical to your
version — the same change arrived through `codex/stage0-idiomatic`, which the
consolidation merged. You and it had converged.

## Full backups, three ways

    nw-core/docs/elisa-core-uncommitted-2026-08-26.tar.gz   all 33 files verbatim
    nw-core/docs/their-tracked.diff                          the 925-line tracked diff
    git tag wip-snapshot-2026-08-26-core                     the stash commit itself

The stash is also still on the stash list. `git stash list` will show it.

## `~/.elisac/elisac` was NOT rebuilt

Hooks were suppressed for every git operation here, so the shared binary is
exactly as you left it (`e2f0caf5...`, mtime 11:52) — built from the OLD `work`.
It is now stale relative to `work`. Your next commit in this repo will fire the
post-commit hook and rebuild it; that was left to you deliberately rather than
swapping your compiler out from under you mid-session.

## Note on `codex/stage0-idiomatic`

Left alone — it is checked out in your `Elisa-core-codex` worktree. Its one
commit is fully contained in `work` now, so the branch is redundant, but
deleting it would strand that worktree.
