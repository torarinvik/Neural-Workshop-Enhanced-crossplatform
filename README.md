# Neural Workshop — cross-platform edition

[![License: 0BSD](https://img.shields.io/badge/license-0BSD-blue.svg)](LICENSE)
![Platforms: browser, macOS, Linux, Windows](https://img.shields.io/badge/platforms-browser%20%7C%20macOS%20%7C%20Linux%20%7C%20Windows-lightgrey.svg)
![Status: work in progress](https://img.shields.io/badge/status-work%20in%20progress-orange.svg)

**Neural Workshop** is a collection of brain-training tasks: short games
that exercise memory, attention, perception, reasoning, planning,
self-control, decision making and the reading of emotions. It grew out of
[Brain Workshop](http://brainworkshop.sourceforge.net), the Dual N-Back
trainer.

This repository makes Neural Workshop run everywhere from a single code
base. The game logic of the [original Python
application](https://github.com/torarinvik/neural-workshop) is ported to
[Elisa](https://github.com/torarinvik/Elisa-compiler), a compiled language.
The result runs:

- **in a web browser**, compiled to WebAssembly;
- **as a native desktop app** on macOS, Linux and Windows, using SDL3;
- **inside Python**, as a native extension module.

Every ported task is tested against the original Python code. Given the same
inputs, both must produce the same scores, timings and screens.

## Contents

- [What's included](#whats-included)
- [Quick start](#quick-start)
- [How it works](#how-it-works)
- [Requirements](#requirements)
- [Setup](#setup)
- [Playing](#playing)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)
- [Repository layout](#repository-layout)
- [Documentation](#documentation)
- [Glossary](#glossary)
- [Contributing](#contributing)
- [License](#license)

## What's included

The browser build offers **146 tasks in twelve categories**:

| Category | Tasks | Examples |
| --- | ---: | --- |
| Working memory | 6 | 3D N-Back, Monkey Ladder, Fog of War |
| Long-term memory | 5 | Concentration, Trivia, Where Was It? |
| Attention | 39 | Reflex, N-Cup Monte, Buzz Wire, Marble Maze |
| Perception | 20 | Count, Mr. Time, Same or Mirror?, Will It Fall? |
| Reasoning | 28 | Matrix Reasoning, Sudoku, Jigsaw Puzzle, Hidden Rule |
| Planning | 18 | Tower of Hanoi, Sokoban, Freeform Tetris, 3D Maze |
| Self-control | 5 | Cookie Thief, Stop & Switch, Hold It |
| Decisions | 9 | Sonar, Gamble, Bluff, Explore or Exploit |
| Emotion | 6 | Which Feeling, Reading People, Tone of Voice |
| Social | 2 | Between the Lines, Social Sense |
| Rationality | 2 | Bad Argument, Second Thoughts |
| Computer use | 6 | Desktop, Forms, Manual, Browser, Errands, Spreadsheet |

Desktop, the sixth *Computer use* task of the original, has not been ported
yet. The native SDL and Python shells support a subset of the tasks; see
[`nw-core/docs/port-status.md`](nw-core/docs/port-status.md) for details.

## Quick start

On macOS with [Homebrew](https://brew.sh), once the [requirements](#requirements)
are installed, these commands build everything and open the browser version.
Each step is explained under [Setup](#setup) and [Playing](#playing).

```bash
# 1. Get this repository and its three companions, side by side
git clone https://github.com/torarinvik/Neural-Workshop-Enhanced-crossplatform.git
git clone https://github.com/torarinvik/neural-workshop.git
git clone https://github.com/torarinvik/Elisa-core.git
git clone https://github.com/torarinvik/Elisa-compiler.git
cd Neural-Workshop-Enhanced-crossplatform

# 2. Link the companions in
ln -s ../neural-workshop original-neural-workshop-enhanced
ln -s ../Elisa-core      stage0-elisa-compiler
ln -s ../Elisa-compiler  stage1-elisa-compiler

# 3. Set up the reference app, then build the compilers
python3 -m venv original-neural-workshop-enhanced/.venv
original-neural-workshop-enhanced/.venv/bin/pip install -r original-neural-workshop-enhanced/requirements.txt
nw-core/scripts/build-toolchain.sh
source nw-core/scripts/env.sh

# 4. Build and serve the browser version
nw-core/scripts/build_latest_stage1_wasm.sh
nw-core/scripts/serve_web.sh
```

Then open <http://127.0.0.1:8000/shells/web/index.html>.

## How it works

```
                 original Python app
                          │  reference for every test
                          ▼
 nw-core/src/*.elisa ──Elisa compiler──┬──► WebAssembly    ──► shells/web     (browser)
 (rules, state, scenes)                ├──► native object  ──► shells/sdl3    (desktop)
                                       └──► Python module  ──► shells/python  (pyglet)
```

- **The core** (`nw-core/src`) holds each task's rules, state and scoring.
  For every frame it also produces a *display list*: a compact description
  of what to draw.
- **A shell** is a thin front end. It passes keyboard and mouse input to the
  core and draws the display list it gets back. Shells contain no game rules,
  so every platform plays the same game.
- **The Elisa compiler** comes in two stages. Stage 0 is written in Go.
  Stage 1 is written in Elisa itself and is built by Stage 0. Release builds
  use Stage 1; the tests compile with both and compare.

## Requirements

Development happens on macOS (Apple silicon). Linux works with the
equivalent packages. Windows builds are produced with the cross-packaging
scripts in `nw-core/scripts/`.

| Tool | Needed for | macOS install |
| --- | --- | --- |
| Git, Bash, Make | Fetching sources and running the scripts | Xcode Command Line Tools |
| [Go](https://go.dev) 1.25 or newer | Building the Stage 0 compiler | `brew install go` |
| LLVM and Clang | Compiler back end and linking | `brew install llvm` |
| Python 3.13 | The reference app and helper scripts | `brew install python@3.13` |
| [Node.js](https://nodejs.org) | Browser tests | `brew install node` |
| SDL3 and `pkg-config` | The desktop app *(optional)* | `brew install sdl3 pkg-config` |

After installing LLVM with Homebrew, put it on your `PATH` as the
[Elisa-core README](https://github.com/torarinvik/Elisa-core) describes.

## Setup

### 1. Get the companion repositories

The build needs three other repositories: the original Python app, which
the tests use as the reference, and the two compiler stages. Clone all four
side by side:

```bash
git clone https://github.com/torarinvik/Neural-Workshop-Enhanced-crossplatform.git
git clone https://github.com/torarinvik/neural-workshop.git
git clone https://github.com/torarinvik/Elisa-core.git
git clone https://github.com/torarinvik/Elisa-compiler.git
```

### 2. Link them into this checkout

The scripts look for the companions under fixed names in the repository
root:

```bash
cd Neural-Workshop-Enhanced-crossplatform
ln -s ../neural-workshop original-neural-workshop-enhanced
ln -s ../Elisa-core      stage0-elisa-compiler
ln -s ../Elisa-compiler  stage1-elisa-compiler
```

Git ignores these links. If you keep the compilers somewhere else, set
`ELISA_CORE` (Stage 0) and `ELISA_STAGE1_ROOT` (Stage 1) instead.

### 3. Prepare the reference app

The tests run the original app in its own virtual environment, which
`env.sh` finds automatically:

```bash
python3 -m venv original-neural-workshop-enhanced/.venv
original-neural-workshop-enhanced/.venv/bin/pip install -r original-neural-workshop-enhanced/requirements.txt
```

### 4. Build the compilers

```bash
nw-core/scripts/build-toolchain.sh
```

The compilers go into `nw-core/toolchain/`. Running the script again only
rebuilds what is missing or out of date; add `--force` to rebuild
everything.

### 5. Load the toolchain

Run this in every new terminal before building or testing:

```bash
source nw-core/scripts/env.sh
```

It stops with an error if a compiler is missing. That is deliberate: it
keeps a build from silently picking up a different `elisac` installed
elsewhere on your system.

## Playing

### In the browser

```bash
nw-core/scripts/build_latest_stage1_wasm.sh
```

```bash
nw-core/scripts/serve_web.sh
```

The first command builds `nw-core/build/nwcore.wasm` and runs the browser
tests. The second starts a local web server. Open
<http://127.0.0.1:8000/shells/web/index.html>, or set `NW_WEB_PORT` to use
another port.

### On the desktop

```bash
nw-core/scripts/build_sdl3.sh
```

```bash
nw-core/build/nw-sdl3
```

The build finishes with a headless self-test. In the app:

| Key | Action |
| --- | --- |
| **Space** | Open the task hub from the title screen |
| **Arrow keys** or mouse | Choose a category and task |
| **Enter** or click | Start the task |
| **Escape** | Leave the task, then the hub |

To open one task directly, name it: `nw-core/build/nw-sdl3 --screen sokoban`.
The [desktop shell README](nw-core/shells/sdl3/README.md) lists every
option, including sound and photo libraries and how to package the app.

### In the Python shell

```bash
nw-core/scripts/build_pymodule.sh
```

```bash
python3 nw-core/shells/python/app.py --screen tetris
```

Run it with `--help` to list the supported tasks. See the [Python shell
README](nw-core/shells/python/README.md) for more.

## Testing

Each ported module has a **differential suite**. It runs the Elisa build and
the original Python code on the same inputs and compares their output line
by line.

```bash
nw-core/scripts/check.sh                        # every suite, both compiler stages
nw-core/scripts/check.sh stage0                 # faster: Stage 0 only
SUITE=sokoban nw-core/scripts/check.sh stage1   # one suite
```

A passing run ends with `All differential suites match the Python
reference.` The full run takes a while, so use `SUITE=` while you work on a
single task.

| Area | How it is tested |
| --- | --- |
| Task logic | `nw-core/scripts/check.sh` |
| Browser build | Smoke and contract tests, run by `build_latest_stage1_wasm.sh` |
| Desktop build | Headless self-tests, run by `build_sdl3.sh` |
| Python shell | `python3 -m pytest nw-core/shells/python` |

## Troubleshooting

**`nw-core: missing …/toolchain/…` when sourcing `env.sh`.**
The compilers have not been built yet. Run
`nw-core/scripts/build-toolchain.sh`.

**`ModuleNotFoundError` (for example `pyglet` or `mujoco`) during tests.**
The reference app's virtual environment is missing or incomplete. Repeat
[step 3](#3-prepare-the-reference-app), then run `source
nw-core/scripts/env.sh` again so it is picked up.

**The browser page stays on "loading…".**
Open the page through `serve_web.sh` rather than as a local file. Browsers
will not load WebAssembly from a `file://` page.

**`build_sdl3.sh` cannot find SDL3.**
Install SDL3 and `pkg-config` (`brew install sdl3 pkg-config`), and check
that `pkg-config --cflags sdl3` prints a path.

**Every suite fails right away on macOS after a system update.**
Accept the Xcode license (`sudo xcodebuild -license`) or reinstall the
Command Line Tools (`xcode-select --install`).

## Repository layout

```
.
├── README.md                this file
├── CONTRIBUTING.md          how to contribute
├── AGENTS.md                code-style rules
├── THIRD_PARTY_NOTICES.md   licenses of bundled third-party material
├── LICENSE
└── nw-core/
    ├── src/                 Elisa sources
    │   ├── tasks/           one module per task: rules, state, scoring
    │   ├── native/          desktop (SDL3) bindings
    │   └── wasm/            WebAssembly exports and runtime protocol
    ├── shells/
    │   ├── web/             browser front end (HTML and JavaScript)
    │   ├── sdl3/            desktop front end (C and SDL3)
    │   └── python/          pyglet front end and its tests
    ├── test/                differential suites, smoke tests and fixtures
    ├── scripts/             build, test, packaging and code-generation scripts
    ├── res/                 images, shaders and sounds
    └── docs/                documentation (see below)
```

The scripts create `nw-core/build/` (build output) and `nw-core/toolchain/`
(the compilers). Git ignores both, and you can delete them at any time.

## Documentation

The [documentation index](nw-core/docs/README.md) lists everything. The most
useful starting points:

| Document | What it covers |
| --- | --- |
| [Porting guide](nw-core/docs/porting.md) | **Read before writing Elisa.** Toolchain rules and conventions. |
| [Port status](nw-core/docs/port-status.md) | What has been ported and verified |
| [Runtime protocol](nw-core/docs/runtime-protocol.md) | The interface between the core and the shells |
| [Display list](nw-core/docs/display-list.md) | How scenes describe what to draw |
| [Implementation plan](nw-core/docs/implementation-plan.md) | Full backlog and dated progress log |

## Glossary

| Term | Meaning |
| --- | --- |
| **Elisa** | The compiled language the core is written in |
| **Stage 0 / Stage 1** | The two Elisa compilers. Stage 0 is written in Go; Stage 1 is written in Elisa and built by Stage 0. |
| **Core** | The shared game logic in `nw-core/src` |
| **Shell** | A front end (browser, desktop or Python) that runs the core |
| **Scene** | The part of a task that turns its state into a display list |
| **Display list** | A compact, platform-neutral description of one frame |
| **Reference** | The original Python application, which defines correct behaviour |
| **Differential suite** | A test that runs the same inputs through the port and the reference and compares the results |

## Contributing

Contributions of every size are welcome. See
[CONTRIBUTING.md](CONTRIBUTING.md) to get started.

## License

Neural Workshop is released under the [Zero-Clause BSD license](LICENSE).
Bundled third-party material keeps its own license; see
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
