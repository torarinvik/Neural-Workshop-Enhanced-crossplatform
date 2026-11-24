# Region inference, and why nw-core no longer threads `Arena&`

Roughly 100 functions across 37 files used to take `a: mutable Arena&` as their
first parameter. stage0 warned on every one:

    warning: internal runtime carrier type "Arena" is not supported in
    user-facing code; use "region scopes and inferred container regions" instead

They no longer do. A caller opens a region and the callee allocates into it:

    region work(64 * 1024 * 1024)
    in work:
        sweep_variable()
        sweep_bt()
    destroy work

## Why the first attempt failed, and what was actually wrong

An earlier attempt at this concluded the parameter was load-bearing and reverted.
That conclusion was wrong, and the write-up it produced (the previous version of
this file) recorded a compiler bug as a fact about the port. Three separate
compiler bugs were doing the blocking:

1. **`interleaved object lifetimes ... stack budget (64) exhausted`** on THREE
   containers. The budget was never the issue: all three had landed on stack 0,
   the shared fixed/reserved stack, because the compiler synthesizes a
   pre-reserve for a counting loop and any reserved container goes there.
   Crossing lifetimes on stack 0 cannot conflict -- bulk reclaim, relocating
   backing -- so the rejection was a false positive. It also explains why
   `reserve()`, the diagnostic's own advertised remedy, did not help: reserving
   is what moves a container onto stack 0.

2. **A silent use-after-free**, which is why the first mechanical sweep
   SIGSEGV'd in ten suites. A container allocated in a callee, stored into a
   struct FIELD, and returned with the struct was not recognized as escaping,
   so the callee allocated into a per-call arena and freed it before `ret`. The
   struct-LITERAL spelling of the same function was recognized and worked.

3. **Two gaps in growing a container owned by a caller**: the documented
   `param.f[i].push(..)` shape was not actually matched, and a call site could
   not thread a struct local's region through a field path (`&buffers.history`).

All three are fixed in Elisa-core (`nw-port`), each with a regression test.

## What is left

`test/config_sweep.elisa` still binds one `Arena&`, because
`read_entire_file_cstr(a: mutable Arena&, path: cstr)` is a std file-IO API that
takes the carrier explicitly. Nothing of ours threads an arena any more.

## One shape the compiler still cannot express

Growth of an element of a NESTED container reached through a by-ref struct param:

    h.xs[0].push(v)        # where xs: darray[darray[i64]]

The region stamped on the param propagates to the field (`xs`) but not through
it to the inner darray, so the push cannot name an allocation region at all.
The flat-field form (`h.xs.push(v)` where `xs: darray[i64]`) works.

`SessionHistory` was the one place in the port that needed this. It is now a
flat trial-major buffer -- `flat[trial * STIMULUS_FIELD_COUNT + field]` -- which
is exactly equivalent because every field is appended once per recorded trial,
and is one allocation instead of STIMULUS_FIELD_COUNT + 1. The 25,725-case
session suite is unchanged, which is the evidence that the representation swap
preserved behaviour.
