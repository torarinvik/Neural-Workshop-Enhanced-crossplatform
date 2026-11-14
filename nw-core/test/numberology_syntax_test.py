#!/usr/bin/env python3
"""Parse Numberology source with Stage0 without loading compiler runtime files."""
import os
import subprocess
from pathlib import Path

root = Path(__file__).resolve().parents[1]
compiler = Path(os.environ.get('ELISACORE_BIN', root / 'toolchain/elisac-stage0-seed'))
for relative in ('src/tasks/numberology_exact.elisa', 'src/tasks/numberology_game.elisa',
                 'src/scene_numberology.elisa'):
    subprocess.run([str(compiler), '-emit', 'ast', str(root / relative)],
                   check=True, stdout=subprocess.DEVNULL)
print('Numberology source syntax: Stage0 parser accepts generator, controller and scene')
