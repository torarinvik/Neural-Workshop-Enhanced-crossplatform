# Python shell

A [pyglet](https://pyglet.org) front end that runs the core through a
native Python extension module. It supports a subset of the tasks; the
browser shell has the complete set.

## Running

From the repository root, after the [setup](../../../README.md#setup) steps:

```bash
nw-core/scripts/build_pymodule.sh
```

```bash
python3 nw-core/shells/python/app.py
```

The first command builds the extension into `nw-core/build/pymod`. Set
`ELISA_PYMODULE_DIR` to load it from somewhere else.

Useful options:

| Option | Effect |
| --- | --- |
| `--screen NAME` | Open a task directly, for example `--screen sokoban` |
| `--screenshot FILE.png` | Render one frame to an image and exit |
| `--dump` | Print the frame as text and exit |
| `--help` | List every screen and option |

## Tests

```bash
python3 -m pytest nw-core/shells/python
```
