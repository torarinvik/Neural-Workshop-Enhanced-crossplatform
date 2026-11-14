#!/usr/bin/env python3
"""Verify the real native Numberology options display-list export."""
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / 'shells/python'))
import app
from display_decode import decode

core = app.load_core('numberology_options_frame')
for black in (0, 1):
    for selected in range(3):
        commands = decode(core.numberology_options_frame(black, selected, 10000, 3, 0))
        text = [item['text'] for item in commands if item['kind'] == 'text']
        assert text[:7] == ['Numberology options', 'Level', '10000',
                            'Questions per run', '3', 'Climb after a perfect run', 'No']
        highlights = [item for item in commands if item['kind'] == 'rect'
                      and item['x'] == 102 and item['w'] == 708]
        assert len(highlights) == 1 and highlights[0]['y'] == 456 - selected * 48
print('Numberology options frame: labels, values, themes and selection passed')
