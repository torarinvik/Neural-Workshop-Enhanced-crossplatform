# Contributing

Contributions of every size are welcome: bug reports, documentation,
examples, tests, refactoring and new task ports. Contributions written in
whole or in part by a large language model are welcome without restriction
or disclosure requirements.

## Reporting a problem or proposing an idea

[Open an issue](../../issues/new/choose). For a bug, include the shell
(browser, desktop or Python), the task, your operating system, and the
command you ran with its output.

## Making a change

1. Follow the [Setup](README.md#setup) steps in the README, and check that
   `nw-core/scripts/check.sh stage0` passes before you start.
2. Read [`nw-core/docs/porting.md`](nw-core/docs/porting.md) before writing
   Elisa. It records compiler behaviour and conventions that are easy to trip
   over.
3. Make the change on a branch.
4. Verify it (see below).
5. Open a pull request. The template asks what you changed and how you
   checked it.

## Verifying a change

The original Python application is the reference for behaviour. A change to
task logic is ready when its differential suite matches that reference with
both compiler stages:

```bash
source nw-core/scripts/env.sh
SUITE=<name> nw-core/scripts/check.sh
```

A suite that compiles but has not been run proves nothing. Run it, and
check that it reports a match.

Also build and try the shell your change affects:

| Change | Check |
| --- | --- |
| Browser shell or WebAssembly exports | `nw-core/scripts/build_latest_stage1_wasm.sh` |
| Desktop shell or native bindings | `nw-core/scripts/build_sdl3.sh` |
| Python shell | `python3 -m pytest nw-core/shells/python` |

## Porting a new task

A task port usually adds these pieces. Copy an existing task of a similar
kind as a starting point:

| Piece | Location |
| --- | --- |
| Rules, state and scoring | `nw-core/src/tasks/<task>.elisa` |
| Scene (what to draw) | `nw-core/src/scene_<task>.elisa` |
| Differential sweep and diff | `nw-core/test/<task>_sweep.elisa` and `<task>_diff.py` |
| Browser smoke test | `nw-core/test/<task>_wasm_smoke.mjs` |
| Desktop binding | `nw-core/src/native/sdl_<task>.elisa` |

Register the suite in `nw-core/scripts/check.sh`. Add the task to
`nw-core/test/fixtures/task_catalog.json`, then regenerate the browser
registry with `nw-core/scripts/generate_task_registry.py`.

## Code style

[`AGENTS.md`](AGENTS.md) lists the rules the code base follows. In short:

- Keep each source file at or under 600 lines, and functions no larger than
  they need to be.
- Use explicit names without abbreviations.
- Prefer expressions, and pass values in and out of functions rather than
  mutating through references.
- Keep documentation up to date with the code, and do not commit temporary
  scripts or notes.

Formatting basics such as indentation and line endings are set in
[`.editorconfig`](.editorconfig).

## License

By contributing, you agree that your contribution is licensed under the
project's [Zero-Clause BSD license](LICENSE).
