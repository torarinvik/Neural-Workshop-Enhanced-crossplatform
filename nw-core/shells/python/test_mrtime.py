#!/usr/bin/env python3
"""Focused native Mr. Time adapter lifecycle and timing smoke."""
import sys

sys.path.insert(0, "nw-core/build/pymod")
import nwcore  # noqa: E402


handle = nwcore.mr_time_create(0, 1, 5, 3000, 400, 1, 17)
assert handle > 0
assert nwcore.mr_time_info(handle, 0) == 0
assert len(nwcore.mr_time_frame(handle, 0, 912, 684)) > 0

assert nwcore.mr_time_action(handle, 0, 0, 1000) == 1
assert nwcore.mr_time_info(handle, 0) == 1
assert nwcore.mr_time_advance(handle, 1000 + 10000) == 1
assert nwcore.mr_time_info(handle, 0) == 3, "recall trial reaches asking phase"

assert nwcore.mr_time_action(handle, 1, 0, 12000) == 1
assert nwcore.mr_time_action(handle, 4, 0, 12001) == 1
assert nwcore.mr_time_info(handle, 0) == 5
assert len(nwcore.mr_time_frame(handle, 0, 1280, 720)) > 0
assert nwcore.mr_time_destroy(handle) == 0
print("PASS: native Python Mr. Time lifecycle, timing, render, and cleanup")
