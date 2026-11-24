# Third-party notices

Neural Workshop's own code is licensed under the [Zero-Clause BSD
license](LICENSE). This repository also contains the third-party material
listed below, which keeps its own license.

| Component | Location | License |
| --- | --- | --- |
| [MuJoCo](https://github.com/google-deepmind/mujoco) 3.12.0, browser build with a parity patch | `nw-core/shells/web/vendor/mujoco/` | Apache License 2.0 ([`LICENSE`](nw-core/shells/web/vendor/mujoco/LICENSE)) |
| Applause sound effect, inherited from Brain Workshop | `nw-core/res/misc/applause/` | GNU GPL version 2 ([`LICENSE.md`](nw-core/res/misc/applause/LICENSE.md)) |

## Not included in this repository

These are used at build or run time but are fetched or installed
separately, under their own licenses:

- **SDL3** and, optionally, **SDL3_ttf** and **TurboJPEG**: native desktop
  shell. Packaging scripts copy the libraries and their notices into release
  packages.
- **Python packages** used by the reference application and the Python shell,
  such as pyglet and MuJoCo.
- **Optional media libraries** such as the ESC-50 sound clips and Tiny
  ImageNet photographs. Only an index of ESC-50 clip timings
  (`nw-core/res/misc/esc50/index.tsv`) is stored here; the clips are not.
