"""Format the menurow sweep's cases with the ORIGINAL's own Menu._label_text.

    <original>/.venv/bin/python scripts/extract_menurow.py

The cases are built as the real value objects the game uses -- Cycler,
PercentCycler, AllCycler, plain bools -- and handed to a real Menu, so the
strings come out of the original's code rather than a restatement of it. That
matters most for PercentCycler, whose one-decimal / two-decimal rule is easy to
paraphrase slightly wrong.
"""
import json
import sys

sys.path.insert(0, "tests")
import uisupport  # noqa: E402

if uisupport.UI_IMPORT_ERROR is not None:
    print("UI_IMPORT_ERROR: %s" % (uisupport.UI_IMPORT_ERROR,), file=sys.stderr)
    raise SystemExit(2)

from neural_workshop.ui.menu import (AllCycler, BLANK_LINE,  # noqa: E402
                                     Cycler, Menu, PercentCycler)

INTERFERENCE = [0.0, 0.125, 0.25, 0.375, 0.5, 0.625, 0.75, 0.875, 1.0,
                0.0625, 0.9375, 0.05]

CASES = [("Use position", True), ("Use color", False),
         ("Crab-back mode (reverse order of sets of N stimuli)", False),
         ("2D grid size", Cycler([3], 0)),
         ("Trial interval (ms)", Cycler([3000], 0)),
         ("Simultaneous stimuli differentiated by", Cycler(["color"], 0)),
         ("Simultaneous stimuli differentiated by", Cycler(["image"], 0)),
         ("Active 2D position cells", AllCycler([0], 0)),
         ("Active 2D position cells", AllCycler([8], 0))]
CASES += [("Interference (tricky stimulus generation)", PercentCycler([v], 0))
          for v in INTERFERENCE]
CASES += [("A command row", None), (BLANK_LINE, None),
          ("A name that is considerably longer than fifty-one characters",
           Cycler([7], 0))]

options, values, names = [], {}, {}
for index, (name, value) in enumerate(CASES):
    key = BLANK_LINE if name == BLANK_LINE else "row%d" % index
    options.append(key)
    names[key] = name
    values[key] = value

menu = Menu(options, values, names=names, title="rows")
rows = [menu._label_text(key) for key in options]
menu.close()
print(json.dumps(rows, indent=0))
