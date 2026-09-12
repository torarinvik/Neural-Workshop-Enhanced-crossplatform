# MuJoCo WebAssembly runtime

This directory vendors the single-threaded browser build of the official
`@mujoco/mujoco` package, version 3.12.0, so the local web shell can run the
same rigid-body engine as the native Marble Maze implementation without a
package manager or cross-origin isolation.

Source: <https://github.com/google-deepmind/mujoco/tree/main/wasm>
Package: <https://www.npmjs.com/package/@mujoco/mujoco/v/3.12.0>
License: Apache-2.0 (MuJoCo / Google DeepMind)

To refresh the two runtime files, run `npm pack @mujoco/mujoco@3.12.0`, unpack
the package, and copy its `mujoco.js` and `mujoco.wasm` here. Keep both files
from the same package version.
