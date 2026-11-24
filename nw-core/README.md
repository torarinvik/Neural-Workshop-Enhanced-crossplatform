# nw-core

The shared core of the Neural Workshop port, plus the front ends ("shells")
that run it. See the [repository README](../README.md) for setup and usage.

| Folder | Contents |
| --- | --- |
| [`src/`](src) | Elisa sources: task rules and state, scenes and display lists |
| [`shells/`](shells) | Front ends: [web](shells/web), [SDL3 desktop](shells/sdl3) and [Python](shells/python) |
| [`test/`](test) | Differential suites against the Python reference, smoke tests and fixtures |
| [`scripts/`](scripts) | Build, test, packaging and code-generation scripts |
| [`res/`](res) | Images, shaders and sounds used by the shells |
| [`docs/`](docs) | Design notes, status and history ([index](docs/README.md)) |

`build/` (build output) and `toolchain/` (the compilers) are created by the
scripts and are not tracked.
