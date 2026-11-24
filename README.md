# Neural Workshop — cross-platform edition

Neural Workshop is a cognitive-training workshop: a collection of small
games and tasks that exercise working memory, attention, perception,
reasoning, planning, self-control, decision making and emotional
understanding. It grew out of [Brain Workshop](http://brainworkshop.sourceforge.net),
the Dual N-Back trainer.

The [original Neural Workshop](https://github.com/torarinvik/neural-workshop)
is a Python desktop application. This repository is a **port of its game
logic to [Elisa](https://github.com/torarinvik/Elisa-compiler)**, a compiled
language, so that one shared core can run:

- **in a web browser**, compiled to WebAssembly;
- **as a native desktop app**, using SDL3;
- **inside Python**, as a native extension module.

Every ported task is checked against the original Python code: the same
inputs must produce the same scores, timings and screens, tick by tick.

> **Status: work in progress.** The browser build registers 140 tasks in
> eleven categories. The *Computer use* category has not been ported yet.
> See [`nw-core/docs/port-status.md`](nw-core/docs/port-status.md) for details.

## Contents

- [How it fits together](#how-it-fits-together)
- [Requirements](#requirements)
- [Setup](#setup)
- [Playing](#playing)
- [Testing](#testing)
- [Repository layout](#repository-layout)
- [Documentation](#documentation)
- [Contributing](#contributing)
- [License](#license)

## How it fits together

```
           original Python app  ──(reference for every test)──┐
                                                               │
 nw-core/src/*.elisa  ──Elisa compiler──►  WebAssembly  ──►  shells/web     (browser)
  (game logic, scenes,                ├─►  native object ──►  shells/sdl3    (desktop)
   task state)                        └─►  Python module ──►  shells/python  (pyglet)
```

- The **core** (`nw-core/src`) holds each task's rules, state and scoring,
  plus a *scene* that describes what to draw as a display list.
- A **shell** is a thin front end. It forwards input to the core and draws
  the display list it returns. Shells hold no game rules.
- The **Elisa compiler** comes in two stages. Stage 0 is written in Go;
  Stage 1 is self-hosted and is built with Stage 0. Release artifacts are
  built with Stage 1, and the tests compile with both.

## Requirements

The build has been used on macOS (Apple silicon). Linux should work with the
equivalent packages; Windows builds are produced by cross-packaging scripts.

| Tool | Used for |
| --- | --- |
| Git, Bash, Make | Fetching sources and running the build scripts |
| [Go](https://go.dev) 1.25+ | Building the Stage 0 Elisa compiler |
| LLVM development libraries and Clang | Compiler back end and linking (`brew install llvm`) |
| Python 3.13 | Running the original app as the test reference, and helper scripts |
| [Node.js](https://nodejs.org) | Browser-build tests |
| SDL3 and `pkg-config` *(optional)* | The native desktop app (`brew install sdl3 pkg-config`) |

## Setup

The build needs three companion repositories: the original Python app (the
test reference) and the two compiler stages. Clone them side by side:

```bash
git clone https://github.com/torarinvik/Neural-Workshop-Enhanced-crossplatform.git
git clone https://github.com/torarinvik/neural-workshop.git
git clone https://github.com/torarinvik/Elisa-core.git
git clone https://github.com/torarinvik/Elisa-compiler.git
```

Then link them into this checkout under the names the scripts expect:

```bash
cd Neural-Workshop-Enhanced-crossplatform
ln -s ../neural-workshop  original-neural-workshop-enhanced
ln -s ../Elisa-core       stage0-elisa-compiler
ln -s ../Elisa-compiler   stage1-elisa-compiler
```

The links are ignored by Git. If your checkouts live elsewhere, you can
instead set `ELISA_CORE` (Stage 0 checkout) and `ELISA_STAGE1_ROOT`
(Stage 1 checkout).

Give the reference app its own virtual environment. The tests use it
automatically:

```bash
python3 -m venv original-neural-workshop-enhanced/.venv
original-neural-workshop-enhanced/.venv/bin/pip install -r original-neural-workshop-enhanced/requirements.txt
```

Build the compilers. This writes them to `nw-core/toolchain/`, which is
ignored by Git, and only rebuilds what is missing or out of date:

```bash
nw-core/scripts/build-toolchain.sh
```

Finally, load the toolchain into your shell. Do this in every new terminal
before building or testing:

```bash
source nw-core/scripts/env.sh
```

`env.sh` stops with an error if a compiler is missing. That is deliberate:
it prevents a build from silently picking up some other `elisac` on your
system.

## Playing

### In the browser

```bash
nw-core/scripts/build_latest_stage1_wasm.sh
```

```bash
nw-core/scripts/serve_web.sh
```

The first command builds `nw-core/build/nwcore.wasm` and runs the browser
test suite. The second serves the page locally. Open
<http://127.0.0.1:8000/shells/web/index.html>. Set `NW_WEB_PORT` to use
another port.

### On the desktop (SDL3)

```bash
nw-core/scripts/build_sdl3.sh
```

```bash
nw-core/build/nw-sdl3
```

The build also runs a headless self-test. Press **Space** on the title
screen to open the task hub. Use the arrow keys or the mouse to pick a task,
**Enter** to start it, and **Escape** to go back. To open one task directly,
pass its screen name, for example `nw-core/build/nw-sdl3 --screen sokoban`.
[`nw-core/shells/sdl3/README.md`](nw-core/shells/sdl3/README.md) lists every
option, including sound and photo libraries and packaging.

### In the Python shell

```bash
nw-core/scripts/build_pymodule.sh
```

```bash
python3 nw-core/shells/python/app.py --screen tetris
```

The Python shell supports a smaller set of tasks. Run it with `--help` to
see them.

## Testing

Each ported module has a *differential suite*. The suite runs the Elisa
build and the original Python code on the same inputs and compares their
output line by line.

```bash
nw-core/scripts/check.sh           # every suite, with both compiler stages
nw-core/scripts/check.sh stage0    # quicker: Stage 0 only
SUITE=sokoban nw-core/scripts/check.sh stage1   # a single suite
```

A run ends with `All differential suites match the Python reference.` when
everything agrees. The full run takes a while, so use `SUITE=` while working
on one task.

Other test groups:

- **Browser:** `build_latest_stage1_wasm.sh` runs the WebAssembly smoke and
  contract tests after building.
- **Desktop:** `build_sdl3.sh` runs the headless SDL self-tests.
- **Python shell:** `python3 -m pytest nw-core/shells/python`.

## Repository layout

```
.
├── README.md               this file
├── IMPLEMENTATION_PLAN.md  detailed backlog and dated progress log
├── CONTRIBUTING.md
├── LICENSE
└── nw-core/
    ├── src/                Elisa sources: core logic, scenes, display lists
    │   ├── tasks/          one module per task (rules, state, scoring)
    │   ├── native/         SDL3 desktop bindings
    │   └── wasm/           WebAssembly exports and runtime protocol
    ├── shells/
    │   ├── web/            browser front end (HTML and JavaScript)
    │   ├── sdl3/           native desktop front end (C and SDL3)
    │   └── python/         pyglet front end and its tests
    ├── test/               differential suites, smoke tests and fixtures
    ├── scripts/            build, test, packaging and code-generation scripts
    ├── res/                images and sounds bundled with the app
    └── docs/               design notes and status (see below)
```

Generated output goes to `nw-core/build/` and compilers to
`nw-core/toolchain/`. Both are ignored by Git and can be deleted at any time.

## Documentation

| Document | What it covers |
| --- | --- |
| [`nw-core/docs/porting.md`](nw-core/docs/porting.md) | **Start here before writing Elisa.** Toolchain rules and porting conventions. |
| [`nw-core/docs/port-status.md`](nw-core/docs/port-status.md) | What has been ported and verified, with build evidence |
| [`nw-core/docs/runtime-protocol.md`](nw-core/docs/runtime-protocol.md) | The interface between the core and the shells |
| [`nw-core/docs/display-list.md`](nw-core/docs/display-list.md) | How scenes describe what to draw |
| [`nw-core/docs/arena-threading.md`](nw-core/docs/arena-threading.md) | Memory arenas in the core |
| [`nw-core/docs/compiler-issues.md`](nw-core/docs/compiler-issues.md) | Known compiler limitations and their workarounds |
| [`nw-core/docs/python-elisa-port.md`](nw-core/docs/python-elisa-port.md) | Port-wide design notes |
| [`nw-core/docs/replays/`](nw-core/docs/replays) | Recorded play-throughs used as tests |
| [`nw-core/docs/history/`](nw-core/docs/history) | Past integration notes, kept for reference only |
| [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md) | Full backlog and dated progress log |

Recorded evidence such as test fixtures may show paths starting with
`/workspace/`. That stands for the folder that holds the checkouts listed in
[Setup](#setup). Paths starting with `/opt/python/` stand for the Python
installation the evidence was recorded with.

## Contributing

Contributions of every size are welcome. See
[`CONTRIBUTING.md`](CONTRIBUTING.md), and read
[`nw-core/docs/porting.md`](nw-core/docs/porting.md) before changing Elisa
code. [`AGENTS.md`](AGENTS.md) lists the code-style rules the project follows.

## License

Zero-Clause BSD. See [`LICENSE`](LICENSE).
