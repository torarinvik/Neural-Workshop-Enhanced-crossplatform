# Why `Arena&` is threaded through nw-core signatures, and what it would take to stop

Roughly 80 functions across 15 files take `a: mutable Arena&` as their first
parameter. stage0 warns on every one:

    warning: internal runtime carrier type "Arena" is not supported in
    user-facing code; use "region scopes and inferred container regions" instead

The warning is right that `Arena` is the runtime's internal carrier and does not
belong in a user-facing signature. What the warning does NOT say -- and what an
attempt to follow it revealed -- is that in this codebase the parameter is
LOAD-BEARING, not decoration.

## What was tried

A mechanical transform: drop the parameter, drop the `in a:` block inside each
function, drop `a` from capture lists, drop the argument at every call site, and
replace the callers' `arena: mutable Arena& = (&work).cast[mutable Arena&]` with
an `in work:` scope.

It worked for `board.elisa`: eight functions, zero Arena mentions left, and the
board suite still passed all 328 cases on stage0.

It broke `stimulus`, `config`, `session` (compile) and `maze` (SIGSEGV).

## Why it broke

    stimulus.elisa:81: interleaved object lifetimes in an inferred region:
    "positions" is created while "kinds" is still live and their live ranges
    overlap, and the region's stack budget (64) is exhausted, so they cannot
    share a bump-stack.

`compute_bt_sequence` builds three containers whose live ranges overlap. Two of
them (`positions`, `audio`) ESCAPE in the return value; the third (`kinds`) is
scratch that is iterated by the same loop that fills the other two. The `in a:`
block was giving all three one explicit region so they could share a bump-stack.
Remove it and region inference has to place three interleaved containers on its
own budget, which it cannot.

`reserve()`ing the scratch container -- the diagnostic's own second suggestion --
did NOT clear it. Tried and measured, not assumed.

## What a real fix needs

Per-function design, not a sweep:

  * functions whose containers all escape -> the mechanical transform is correct
    and `board.elisa` proves it;
  * functions with escaping AND scratch containers whose ranges interleave ->
    need the scratch hoisted into its own nested region, which means
    restructuring the loop so the lifetimes actually nest, OR a region-inference
    change so a reserved container really is excluded from the stack budget.

The second bullet is a compiler question as much as a port question, and the
diagnostic advertising `reserve()` as a remedy that then does not work is worth
a repro in its own right.

## Status

REVERTED. All 13 suites pass on both stages; nothing here is half-applied. The
warnings stay until this is done properly.

A caveat on the earlier framing of this: it was first written up (in
worktrees/elisa-core-nw/repro/pending_nw_core_patches/README.md item 7) as
"board.elisa simply predates the right pattern and was never brought in line".
That was wrong. display.elisa can use the inferred-region pattern because
`display_list_new` builds containers that all escape together; the modules that
thread `Arena&` are the ones with interleaved scratch. The difference is
structural, not historical.
