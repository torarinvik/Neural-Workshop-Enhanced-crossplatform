#!/usr/bin/env python3
"""Keep the embedded offline pool identical to the original source ordering."""
import ast
from pathlib import Path
import re

root = Path(__file__).resolve().parents[1]
original = root.parent / 'original-neural-workshop-enhanced/neural_workshop/wordlist.py'
tree = ast.parse(original.read_text(encoding='utf-8'))
node = next(n for n in tree.body if isinstance(n, ast.Assign) and
            any(isinstance(t, ast.Name) and t.id == 'SEED_WORDS' for t in n.targets))
words = list(dict.fromkeys(ast.literal_eval(node.value.func.value).split()))
expected = ''.join(f'{word}\t{index + 1}\t\n' for index, word in enumerate(words))
source = (root / 'src/tasks/scrabble_lexicon.elisa').read_text(encoding='utf-8')
match = re.search(r'def seed_text\(\) -> sview:\s*return sview\(("(?:[^"\\]|\\.)*"), 0, -1\)', source)
assert match and ast.literal_eval(match.group(1)) == expected, 'embedded source seed words drifted'
print(f'scrabble_seed_integrity: PASS ({len(words)} source entries)')
