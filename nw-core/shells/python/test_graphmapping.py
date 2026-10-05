#!/usr/bin/env python3
"""Focused native Graph Mapping adapter lifecycle and timing smoke."""
import sys

sys.path.insert(0, "nw-core/build/pymod")
import nwcore  # noqa: E402


handle = nwcore.graph_mapping_create(4, 0, 5, 3000, 1, 0, 17)
assert handle > 0
assert nwcore.graph_mapping_info(handle, 0) == 0
assert len(nwcore.graph_mapping_frame(handle, 0, 912, 684)) > 0

assert nwcore.graph_mapping_action(handle, 0, 1000) == 1
assert nwcore.graph_mapping_info(handle, 0) == 1
same = nwcore.graph_mapping_info(handle, 21)
choice = 1 if same else 2
assert nwcore.graph_mapping_action(handle, choice, 1200) == 1
assert nwcore.graph_mapping_info(handle, 0) == 3
assert len(nwcore.graph_mapping_frame(handle, 0, 1280, 720)) > 0

deadline = nwcore.graph_mapping_info(handle, 16)
assert nwcore.graph_mapping_advance(handle, deadline) == 1
assert nwcore.graph_mapping_info(handle, 0) == 1
assert nwcore.graph_mapping_info(handle, 4) == 2
assert nwcore.graph_mapping_destroy(handle) == 0
print("PASS: native Python Graph Mapping lifecycle, grading, timing, render, and cleanup")
