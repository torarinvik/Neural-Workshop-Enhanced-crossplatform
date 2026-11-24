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

## `~/.elisac/elisac` WAS replaced at 16:23 — but not by these hooks

Correcting an earlier draft of this note, which claimed it was untouched.

Every git operation here passed `-c core.hooksPath=<empty dir>`, and that
suppression demonstrably works: a controlled `git checkout work` under the same
override left the binary's mtime unchanged. The hooks' own log,
`/tmp/elisac-autoinstall.log`, is still stamped **11:52** — `install-elisac.sh`
has not run since. So the rebuild did not come from the hook path.

What IS certain is what the binary now contains. Two feature probes, each
isolating a commit that only the consolidation carries:

    -fstrict-fp accepted                       -> present (nw-port's commit)
    test/repro/generic_optional_helpers.elisa  -> compiles, no LLVM PHI crash
                                                  (codex/stage0-idiomatic's fix)

The pre-landing `work` (`da8cb230`) had neither. So the binary at 16:23 was
built from the landed `work` (`c84f1429`) or an identical tree — it is CURRENT,
not stale, and it matches the branch this note describes.

What is NOT certain is what invoked it. It was not the git hook and not a
scripted step here (the only writer in either repository is
`install-elisac.sh`). The likeliest explanation is a build run by hand or by
another session out of the main worktree after the fast-forward landed.

If you want certainty rather than inference, rebuild it yourself from a clean
tree:

    go build -C "$(git rev-parse --show-toplevel)/compiler" -o ~/.elisac/elisac ./src

## Note on `codex/stage0-idiomatic`

Left alone — it is checked out in your `Elisa-core-codex` worktree. Its one
commit is fully contained in `work` now, so the branch is redundant, but
deleting it would strand that worktree.
