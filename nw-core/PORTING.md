# Porting conventions: Python → Elisa

Hard-won notes from porting `bwaccel` and the n-back core. Read this before
writing Elisa in this repo; every item below cost a compile-fail cycle to find.

## Toolchain

```bash
./nw-core/scripts/build-toolchain.sh   # our own compilers -> nw-core/toolchain/
source nw-core/scripts/env.sh          # pins them; gate ON
./nw-core/scripts/check.sh             # every differential suite, both stages
./nw-core/scripts/check.sh stage0      # fast inner loop
```

**The compilers are ours, and they live in `nw-core/toolchain/`.** Three
artefacts, because stage1 bootstraps through stage0: `elisac-stage0` (Go +
cgo), `elisacore_runtime.o` (compiled by stage0), `elisac-stage1` (seeded by
stage0). `toolchain/PROVENANCE` records which branch and commit each came
from. The directory is gitignored — rebuild it, don't commit it.

- **Never** use `~/.elisac/elisac`. It is shared, and it is rebuilt behind your
  back: elisa-core installs git hooks that reinstall it on every commit, merge
  and checkout in **any** worktree of the repository, from whatever branch that
  worktree happens to be on. Another agent committing in their tree silently
  swaps your compiler. Two sessions were spent chasing results that came from
  it.
- The hooks are disabled in our worktree via a worktree-scoped
  `core.hooksPath`. Don't re-enable them. Any git command that reads the
  compiler repos from a script should pass `-c core.hooksPath=/dev/null`, so
  that reading a commit id cannot rebuild someone else's binary.
- `env.sh` **refuses to source** if any of the three is missing, and
  `check.sh` exits on that. Without the guard a missing compiler falls through
  to a downstream script's own `${ELISAC:-$HOME/.elisac/elisac}` default —
  which is how a suite once compared the other agent's compiler against itself
  and passed.
- **Do not build the toolchain from the compilers' `work` branch.** `nw-port`
  carries compiler fixes that `work` does not, and the port depends on one of
  them: without `-fstrict-fp`, stage0 contracts `a + b * c` into an fma and
  twohands, buzzwire and marblemaze stop matching CPython. Check with
  `git log --oneline work..nw-port` before assuming the branches agree.
- Stage0 (`$ELISACORE_BIN`) has **no `-emit exe`** — use `-emit obj` then
  `clang -o out out.o`. Stage1 (`elisac_stage1`) does have `-emit exe`.
- Always compile with `ELISA_STAGE1_SEMANTIC_GATE=1` (env.sh sets it). With the
  gate off, stage1 emits code **without semantic analysis** and accepts
  programs stage0 rejects.
- Verify on **both** stages. A divergence is by definition a compiler bug:
  minimise it, save it under `worktrees/elisa-core-nw/repro/`, and report it.

## Language gotchas

**Reserved words.** The full list met so far: `tail`, `move`, `stack`, `to`,
`heap`, `emit`. Most do not announce themselves — a local called `move` fails
at its *next* use with `unexpected token < in expression`, not at the
declaration. If you get that or `expected IDENT, got <name>`, rename the
identifier and look at the line ABOVE the one the error points at.

**Locals are immutable by default.** Reassigning needs `x: mutable i64 = 0`.
The diagnostic says so plainly.

**Loops need capture lists when they touch outer state.**

```elisa
for item in items |accumulator, limit|:      # names read/written inside
while index < count |index, total, values|:
```

**Indexing needs provable bounds.** Inside a `while index < count` loop the
compiler proves it; across an early-return guard it does not, and you get
*"implicit `else` index fallback has been removed"*. Use the explicit form:

```elisa
value: i64 = get history[position.usize()] else 0
```

**Arenas are explicit, not ambient.** Functions that allocate take
`a: mutable Arena&` and wrap allocation in `in a:`. Building a `darray` in a
callee without `in a:` produces dangling storage. A scoped `region` must be
consumed — `destroy work` before scope exit — and `&work` is a `stack Arena&`,
so cast it: `arena: mutable Arena& = (&work).cast[mutable Arena&]`.

**f-strings only interpolate string-likes** (`sview`/`dstr`/`cstr`). Integers
must be converted explicitly.

**Printing integers currently declines under stage1.** `print(42)`,
`printr(i64)` and `int_to_string_scratch` all reach the std's generic `Store`
impls, which stage1's backend declines (see
`repro/nw_generic_protocol_impl_stage1.elisa`). Until that's fixed, sweeps
carry a hand-rolled `print_i64` writing digits into a stack buffer. Copy it
from any existing `*_sweep.elisa`.

**Struct literals** are `Point{x: 1, y: 2}`; fixed arrays inside them
initialise with `cats: zeroed`. Enums match with indented arms and **no `case`
keyword**; exhaustiveness is a hard error.

**Struct fields are immutable too**, separately from the local holding them:
`count: mutable i64` or `record.count <- n` fails with *field "count" is
immutable*. Assigning *into* a fixed-array field (`record.cats[i] <- v`) does
not need it.

**There is no `continue`.** Restructure the loop body as `if … else …`.

**`try value else fallback`** works for value-carrying error unions. A brace
literal as the fallback confuses the parser — call a helper instead. `catch`
as an *expression* needs a block form; prefer `try … else`.

## Floating point

Settled by measurement, not by reading the source. Four findings, each of which
cost a wrong port before it was found:

- **Compile with `-fstrict-fp`** (env.sh sets `ELISACORE_STRICT_FP=1`).
  Stage0 stamps LLVM's `contract` flag on every FP op, so `a + b * c` may fuse
  into a single-rounding fma; stage1 never has. The two stages therefore
  disagreed. Python's `uniform(a, b)` is `a + (b - a) * random()`, and for a
  negative `a` the add cancels: 37 of 160 draws came out different.
- **`math.hypot` is not libm's and is not correctly rounded.** Use `py_hypot`
  (`src/pymath.elisa`), which is the classic `max * sqrt(1 + (min/max)^2)` and
  matches this CPython exactly. Where a hypot is only *compared* the difference
  is invisible; where its value is *kept* it is not.
- **`math.radians` is one multiply**, by a precomputed `pi/180`. Writing
  `x * pi / 180.0` is two roundings and differs for a third of arguments.
- **Everything else in libm agrees.** sin, cos, exp, atan2, sqrt, asin and pow
  all matched CPython bit-for-bit over 300 random arguments each.

When a module's floats worry you, do what these did: monkey-patch the suspect
function in the *reference*, re-run a few thousand cases, and see whether any
output changes. That answers the question; reading the C source only raises it.

## Structs: pre-size buffers, do not grow them through a helper

`helper(&thing.buffer, x)` — handing a container FIELD of a struct ref to a
function that grows it — is rejected with "cannot infer region parameter", and
the obvious compiler fix is unsound (elisa-core
`docs/REGION_FIELD_FORWARD_GAP.md` records the measurement). Growing the field
*in place* is fine, and so is building a local `dstr` and returning it.

So: pre-size with `Ints::zeros` / `Bytes::zeros` and write by index, keeping
the used length beside it. Every task module here does this.

## Fidelity rules

These are what the differential harnesses are for. The job is behavioural
identity, not improvement.

- **Python's `round()` is half-to-even.** Use libm `rint`, never `round`.
- **Python's negative list indexing wraps to the end.** `xs[-1]` is the last
  element, not an error. `matching.elisa` reproduces a reference site where
  this happens by accident; see `nback_trial_index_checked`.
- **Reproduce upstream bugs, don't fix them silently.** If the reference does
  something wrong, port it faithfully, document it in a comment, and surface it
  in the summary. Fixing it is a separate, deliberate decision in both trees.
- **CPython `random` is reproducible from Elisa** — `elisacore_rng` gives the
  exact MT19937 and `random()`; `nw-core/src/pyrandom.elisa` adds
  `getrandbits`/`_randbelow`/`shuffle`/`sample`. Use them rather than inventing
  a generator, or seeded sessions will diverge.
- **Prefer exact integers over floats** where the reference's float use is
  incidental. `board.elisa` scales squared distances by 4 to keep the centre-out
  ordering integral; `pyrandom.elisa` computes `sample`'s setsize heuristic as
  an integer ceil-log4 rather than `4 ** ceil(log(k*3, 4))`.
- **Compare integers in harnesses.** Emit floats scaled and truncated
  (`(value * 100000.0).i64()`) so a formatting difference never masquerades as
  a logic difference.

## Order, everywhere

Python's containers are ordered and the reference leans on it constantly.
Three distinct things, and conflating them is the most common way a port
diverges while still looking right:

- **Dict insertion order.** `for k in d`, `list(d)`, `min(d, key=...)` all
  follow the order keys were first inserted. Model it with an ordered list plus
  a lookup table. No hashing is involved. (twohands' solver layers, syllogism's
  `_askable`.)
- **`sorted(d)` sorts the KEYS.** When those keys are label strings, the order
  is alphabetical over what is *printed*, which is rarely the order of any
  index you have chosen. Render and compare.
- **Set iteration order IS hashed**, and there you have to model CPython's
  table exactly — see `src/tasks/pyset.elisa`. Check whether the reference
  actually iterates the set or only tests membership; membership needs no
  order at all.

## Adding a suite

1. `nw-core/src/<name>.elisa` — the port. No I/O, no globals; state arrives as
   an explicit context struct.
2. `nw-core/test/<name>_sweep.elisa` — prints one CSV line per case over a
   deterministic grid.
3. `nw-core/test/<name>_diff.py` — runs the same grid through the original
   module and diffs line by line.
4. Add `<name>` to `SUITES` in `scripts/check.sh`.

**Drive the real Python module where you can.** Modules under
`neural_workshop/` import cleanly with no side effects (only `brainworkshop.py`
creates a window on import), so a harness can inject stand-in `state.mode` /
`state.cfg` objects and test the *actual* reference code rather than a
transcription. `matching_diff.py` shows the pattern.

**Score divergences explicitly.** Where the reference raises, emit an agreed
code on both sides (`matching` uses `9`) rather than skipping the row — a
skipped row is an untested row.

## Module blocks: use them

Elisa has real namespaces -- `module Name:` with `::` for namespace members and
`.` for value members. They are the right tool and the `maze_`/`nar_`/`cw_`
prefixes scattered through src/tasks are not; prefixes are C-style scoping in a
language that has the real thing.

This section used to say converting the six task modules was NOT safe: all six
passed on stage0 and all six failed on stage1, one of them with a SILENT WRONG
ANSWER. That was the constant-collision bug (two modules each declaring `SIZE`
collapsed onto one table row), and it is fixed --
repro/nw_stage1_module_member_wrong_answer.elisa now prints the same thing on
both compilers. So does every other blocker that was recorded here; see
"Module blocks: what actually works today" below for what each one turned out
to be.

The mechanical transform is straightforward. Three traps, all of them paid for:

  * Substitutions must be applied in a SINGLE pass. Rewriting `MazeWork` to
    `Maze::Work` and then letting a `Maze` rule fire again on its own output
    gives `Maze::Dealt::Work`.
  * A qualifier must not be added to a NAME that merely spells the same word:
    `.` before it is member access (`found.rgba.r`), `:` after it is a binding
    (`ColorLookup{rgba: ...}`). The Display conversion's first pass qualified
    gamemode.elisa's `rgba` field and every use of it.
  * A column-0 comment inside a module body is a DEDENT. A sed-based conversion
    leaves them behind and they read as ordinary comments.

## Screens: measure the original, do not read it

`scene_title.elisa` and `scene_menu.elisa` were built from numbers MEASURED off
the running application (`scripts/extract_title.py`, `scripts/extract_menu.py`),
not from the constants written in `ui/hud.py` and `ui/menu.py`. Three things
make reading those files insufficient, and each was found the hard way:

  * **The window is retina-doubled.** Every geometry helper returns physical
    pixels, so `from_top_edge(25)` lays out at 1318 on a 1368-tall framebuffer,
    not at 659. Each extractor divides by the window's OWN measured scale rather
    than by an assumed factor, so the reference file is in 912x684 space
    whatever display it was produced on.

  * **A field can be dead.** `Menu.build_chrome` computes `self.bgcolor` and
    nothing ever reads it -- a menu's background is the GL clear colour, like
    every other screen. Porting it because it looks authoritative would have
    inverted the menu background on one theme.

  * **The flags decide the content.** The title screen's key list is assembled
    from JAEGGI_MODE and CLINICAL_MODE, so the only way to know what a build
    offers is to set them and rebuild the label. Driving the original for every
    combination is what turned up the trailing empty line clinical mode leaves
    behind.

Both harnesses drive the real class per case rather than comparing against a
stored snapshot, so they keep working when the original moves.

### Text blocks become one command per line

pyglet advances a multiline label by the FONT's ascent-minus-descent -- 16.5
reference pixels at size 12 on the title screen's face. No shell can be asked
to reproduce another toolkit's font metrics, so the core resolves a block into
one `CMD_TEXT` per line at a measured step. Wrapping is not modelled because
nothing on these screens wraps; a screen that needs it should carry the width
in the command rather than have four renderers each guess.

### `CMD_SPRITE_FIT`

The core cannot know an image's pixel size -- artwork is a resource anyone may
replace -- so it names a ROOM and the shell fits into it:
`scale = min(room_w/image_w, room_h/image_h)`, drawn centred. That is
`bootstrap._place_splash` exactly, and it is why a 2000x500 logo lands in the
same gap as a square one.

## Constructors: overload the type name

A builder that returns a struct is spelled as the type, not as `foo_new`:

    def MenuLayout(selpos: i64) -> MenuLayout:

42 of the port's 44 builders are written that way. Two are not, and the reasons
are worth keeping:

  * **`fog_work_new` / `maze_work_new`** both build a `MazeWork` from two
    arguments. Two overloads with the same name AND arity are ambiguous, so
    only one of them could take the type's name and neither does.
  * **`nar_lines_new`** is region-POLYMORPHIC. Renamed to `NarLines`, its call
    sites stopped inferring a region -- same body, same callers, only the name
    changed. The overload spelling and region inference interact; left alone
    until that is understood.

A struct with an **`sview` field cannot have a working constructor overload at
all**: the compiler does not recognise it and reads `Row(...)` as positional
construction, asking for the constructor that is defined three lines above.
Measured across field types -- `i64`, `f64`, `bool`, `cstr` all fine, only
`sview` breaks -- and it happens at top level with no module involved. Use the
brace form. See `repro/nw_ctor_overload_sview_field.elisa`.

## Module blocks: what actually works today

`src/display.elisa` is `module Display:` and `src/menu_model.elisa` is
`module MenuText:`; both pass on both stages. Display is the significant one --
its whole API is `mutable DisplayList&`, which is what a module block could not
carry until the region fix below.

Of the four things that blocked converting the rest, three are fixed. Repros are
in `worktrees/elisa-core-nw/repro/`.

  1. **Constants were not namespaced** -- FIXED. Two modules each declaring
     `SIZE` collapsed onto one table row and the second silently overwrote the
     first. A wrong answer, and qualifying the use site did not help because the
     collision was in the table. Constants are now keyed by (owner, name).

     A second half turned up when Display became a module: the qualified fix
     covered expression USE sites, but the two const FOLDERS still matched
     `Expr.Ident` alone, so `const ROWS_TOP: f64 = Display::REFERENCE_HEIGHT * 8.0 / 10.0`
     never resolved -- and an unresolved const declines every function that
     reads it, which drops the whole unit. Also fixed;
     `test/repro/module_const_in_const_initializer.elisa` in the compiler repo.

  2. **Region inference did not forward through a qualified call** -- FIXED.
     A function holding `mutable X&` could not pass it to
     `Module::helper(x, ...)`, so `Display::rect(list, ...)` was unreachable
     from any function that received `list` as a parameter, which is every
     renderer.

     This was recorded here as a language-level gap affecting both compilers.
     That was wrong: stage0 rejected it, stage1 compiled and ran it correctly.
     Region-param inference keyed call targets by the FuncDecl's bare name
     ("stow") while `Box::stow(...)` parses to one joined Ident ("Box.stow"), so
     no module member ever matched.

     Fixing it exposed a second defect in the same pass, which the fix itself
     introduced: the region-valued PROBE resolves a callee's declared return
     type, and a module member's return type is written BARE inside its module.
     Resolved from the caller's namespace it does not resolve -- and
     `resolveType` REPORTS, so a probe emitted a real "unknown type Row" against
     the callee's own signature. It needs a darray PARAMETER to reach:

         def fill(rows: mutable darray[M::Row]&):
             rows.push(M::spacer())

     Worth knowing how it was caught: `scripts/check.sh` was 66/66 green with the
     regression in place. `scripts/gate.sh` found it, because the wasm build is a
     gate step and not a check step. 66/66 is not the gate.

  3. **A constructor overload was refused for an `sview` parameter** -- FIXED.
     `def Row(k: i64, s: sview) -> Row` was not recognised, and `Row(3, "x")`
     fell through to the all-fields positional path, which rejected it while
     asking for the constructor defined three lines above.

     Recorded here as "it is the view type, not the arity". Closer: it is a
     string LITERAL passed to an `sview` parameter. A literal approximates to
     `u8& static`, which is not `AssignableTo` an sview, so the overload was
     discarded as a candidate -- the overload FILTER disagreeing with the
     language, since the ordinary call path accepts the same literal. Passing an
     `sview` LOCAL always worked, and the struct having an sview FIELD had
     nothing to do with it.

  4. **A sibling call lost to a stdlib generic on stage0** -- FIXED. Inside a
     module, an unqualified `add(...)` bound to `Flags[T]::add` rather than the
     module's own `add`. stage1 already got this right, so the two compilers
     disagreed about a module member calling its own sibling by its own name.

     Identifier resolution reaches the global scope through the ordinary scope
     chain, so the stdlib's `add` was found there and returned before the
     enclosing module was ever consulted. The namespace-aware lookup already
     existed; nothing on the call path used it.

     It RENAMES the callee rather than just resolving its type. The first
     attempt preferred the member in ident analysis alone, and the call then
     type-checked against the module's signature while codegen still emitted the
     stdlib symbol -- the repro compiled clean and returned 0 instead of 7. Only
     running it showed that, which is why the guard is a runtime test.

  5. **Struct names were not namespaced** -- FIXED. Two modules may now each
     declare a `Work`, which is what the task modules want (SyWork, GoWork,
     MazeWork, SokWork, RemWork).

     Three phases each keyed structs by bare name. The parser records an owner
     column (it has to come from there: struct member spans are keyed
     POSITIONALLY by the struct-names index). The backend keys rows by
     (owner, name) and mangles the LLVM type name per owner -- without that,
     LLVMGetTypeByName2 hands the second module the first module's type, the
     same collapse one level down. The semantic phase, which is where the
     diagnostic actually came from, gained a parallel module column consulted by
     the construct-site field checks.

All five are closed. The task modules can now be modules.

One formatting trap, since it cost real time: a comment at column 0 inside a
module body is a dedent. The sed-based MenuText conversion left three, and they
read as ordinary comments. `src/menu_model.elisa` is fixed; the check is "a
column-0 comment whose next code line is indented".
