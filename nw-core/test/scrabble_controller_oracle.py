#!/usr/bin/env python3
"""Original Scrabble generation for the controller's first seeded trial."""
import json
import ast
import os
from pathlib import Path
import random
import runpy

ref = runpy.run_path(str(Path(__file__).with_name('scrabble_diff.py')), run_name='scrabble_reference')
level = int(os.environ.get('NW_SCRABBLE_LEVEL', '1'))
grade = ref['REF']['grade_of'](level)
if os.environ.get('NW_SCRABBLE_SEED') == '1':
    source = Path(__file__).resolve().parents[2] / 'original-neural-workshop-enhanced/neural_workshop/wordlist.py'
    tree = ast.parse(source.read_text(encoding='utf-8'))
    node = next(node for node in tree.body if isinstance(node, ast.Assign) and
                any(isinstance(target, ast.Name) and target.id == 'SEED_WORDS' for target in node.targets))
    words = [word for word in dict.fromkeys(ast.literal_eval(node.value.func.value).split()) if 2 <= len(word) <= grade.size]
elif os.environ.get('NW_SCRABBLE_LEXICON'):
    entries = []
    for line in Path(os.environ['NW_SCRABBLE_LEXICON']).read_text(encoding='utf-8').splitlines():
        word, rank, _clue = line.split('\t')
        if int(rank) < grade.top_rank and 2 <= len(word) <= grade.size:
            entries.append((int(rank), word))
    entries.sort(key=lambda item: item[0])
    words = [word for _, word in entries]
else:
    words, _ = ref['build_lexicon'](120)
lexicon = ref['Lexicon'](words)
seed = random.Random(17).randrange(1 << 30)
deal = ref['REF']['deal_one'](grade, random.Random(seed), lexicon)
assert deal is not None
candidates = ref['REF']['plays'](deal.board, deal.rack, lexicon)
lower = next((play for play in candidates if play.score < deal.best.score * deal.grade.share * 0.6), None)
repeated = next((play for play in candidates if len({letter for _, letter in play.laid}) < len(play.laid)), None)
invalid = None
for cell in ref['REF']['anchors'](deal.board):
    for slot, letter in enumerate(deal.rack):
        laid = ((cell, letter),)
        runs = [ref['REF']['_run'](deal.board, cell, down, dict(laid))[0] for down in (False, True)]
        if any(len(word) > 1 and not lexicon.valid(word) for word in runs) and not any(
                ref['REF']['legal'](deal.board, laid, down, lexicon) for down in (False, True)):
            invalid = {'cell': cell, 'slot': slot, 'words': runs}
            break
    if invalid is not None:
        break
print(json.dumps({'lower': None if lower is None else {'score': lower.score, 'laid': [[cell, ord(letter)] for cell, letter in lower.laid], 'message': '/'.join(word.upper() for word in lower.words) + f' for {lower.score}; the best was {deal.best.word.upper()} for {deal.best.score}'}, 'board': [ord(c) if c else 0 for c in deal.board.letters],
                  'rack': [ord(c) for c in deal.rack], 'score': deal.best.score,
                  'invalid': invalid,
                  'repeated': None if repeated is None else {'score': repeated.score, 'laid': [[cell, ord(letter)] for cell, letter in repeated.laid], 'message': '/'.join(word.upper() for word in repeated.words) + f' for {repeated.score}; the best was {deal.best.word.upper()} for {deal.best.score}'},
                  'best': [[cell, ord(letter)] for cell, letter in deal.best.laid],
                  'message': '/'.join(word.upper() for word in deal.best.words) +
                  f' for {deal.best.score}; the best was {deal.best.word.upper()} for {deal.best.score}'}))
