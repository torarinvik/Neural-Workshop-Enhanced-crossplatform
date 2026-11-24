#!/usr/bin/env bash
# Generate Elisa field offsets from the MuJoCo headers used for this build.
set -euo pipefail
headers="${1:?pass the MuJoCo include directory}"
output="${2:?pass the generated Elisa source path}"
probe="$output.probe.exe"
trap 'rm -f -- "$probe"' EXIT
cc -x c -std=c11 -I"$headers" -o "$probe" - <<'C'
#include <stddef.h>
#include <stdio.h>
#include <mujoco/mujoco.h>

int main(void) {
    _Static_assert(sizeof(mjtNum) == sizeof(double), "Marble requires double-precision MuJoCo");
    _Static_assert(sizeof(int) == 4, "Marble requires 32-bit MuJoCo integer fields");
    printf("const MUJOCO_HEADER_VERSION: i32 = %d\n", mjVERSION_HEADER);
    printf("const MUJOCO_MODEL_TIMESTEP: usize = %zu.usize()\n", offsetof(mjModel, opt) + offsetof(mjOption, timestep));
    printf("const MUJOCO_MODEL_GRAVITY: usize = %zu.usize()\n", offsetof(mjModel, opt) + offsetof(mjOption, gravity));
    printf("const MUJOCO_MODEL_GEOM_CONTYPE: usize = %zu.usize()\n", offsetof(mjModel, geom_contype));
    printf("const MUJOCO_MODEL_GEOM_CONAFFINITY: usize = %zu.usize()\n", offsetof(mjModel, geom_conaffinity));
    return 0;
}
C
"$probe" > "$output"
