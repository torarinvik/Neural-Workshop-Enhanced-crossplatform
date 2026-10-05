"""Focused native Matrix Reasoning adapter lifecycle smoke."""
import sys

sys.path.insert(0, "nw-core/build/pymod")
import nwcore  # noqa: E402
from app import MatrixReasoningSession, TaskHubSession  # noqa: E402


handle = nwcore.matrix_reasoning_create(1, 5, 0, 1, 1, 1, 17)
assert handle > 0
assert nwcore.matrix_reasoning_info(handle, 0) == 0
ready = nwcore.matrix_reasoning_frame(handle, 0, 912, 684)
assert ready.startswith(b"NKIN") and len(ready) > 0

assert nwcore.matrix_reasoning_action(handle, 0, 0, 1000) == 1
assert nwcore.matrix_reasoning_info(handle, 0) == 1
assert nwcore.matrix_reasoning_info(handle, 17) == 1
answer = nwcore.matrix_reasoning_info(handle, 6)
assert 0 <= answer < nwcore.matrix_reasoning_info(handle, 5)
assert nwcore.matrix_reasoning_action(handle, 1, answer, 1200) == 1
assert nwcore.matrix_reasoning_info(handle, 0) == 3
assert nwcore.matrix_reasoning_info(handle, 9) == 1
deadline = nwcore.matrix_reasoning_info(handle, 21)
assert nwcore.matrix_reasoning_advance(handle, deadline - 1) == 2
assert nwcore.matrix_reasoning_advance(handle, deadline) == 1
assert nwcore.matrix_reasoning_info(handle, 0) == 1
assert len(nwcore.matrix_reasoning_frame(handle, 0, 1280, 720)) > 0
assert nwcore.matrix_reasoning_destroy(handle) == 0

args = type("Args", (), {"trial": 1, "trials": 1, "adaptive": False,
                          "show_traps": True, "show_marks": True,
                          "seed": 17, "black_background": False})()
menu = TaskHubSession(nwcore, args)
for _ in range(4):
    menu.key(4, type("Keys", (), {"RIGHT": 4, "LEFT": 3, "UP": 1,
                                   "DOWN": 2, "SPACE": 5, "RETURN": 6})())
for _ in range(1):
    menu.key(2, type("Keys", (), {"RIGHT": 4, "LEFT": 3, "UP": 1,
                                   "DOWN": 2, "SPACE": 5, "RETURN": 6})())
menu.key(5, type("Keys", (), {"RIGHT": 4, "LEFT": 3, "UP": 1,
                               "DOWN": 2, "SPACE": 5, "RETURN": 6})())
assert isinstance(menu.child, MatrixReasoningSession)
menu.close()
print("PASS: native Python Matrix Reasoning lifecycle, grading, timing, render, and cleanup")
