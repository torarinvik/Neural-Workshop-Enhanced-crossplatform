#!/usr/bin/env python3
"""Exercise SDL lexicon loading through the real native task controllers."""
import ctypes
import os
import sys
import tempfile
from pathlib import Path

base_env = 'APPDATA' if os.name == 'nt' else 'HOME'
lib = ctypes.CDLL(os.environ['NW_SDL_NATIVE_LIBRARY'])
load = lib.nw_sdl_load_word_index
load.argtypes = [ctypes.c_int64, ctypes.c_char_p, ctypes.c_int64]
load.restype = ctypes.c_int64
create_word = lib.nw_sdl_create_word_task
create_word.argtypes = [ctypes.c_int64] * 5 + [ctypes.c_char_p]
create_word.restype = ctypes.c_int64
for task in ('crossword', 'scrabble'):
    create = getattr(lib, 'nw_' + task + '_create')
    create.argtypes = [ctypes.c_int64] * 5
    create.restype = ctypes.c_int64
    destroy = getattr(lib, 'nw_' + task + '_destroy')
    destroy.argtypes = [ctypes.c_int64]
    destroy.restype = ctypes.c_int64
    with tempfile.TemporaryDirectory() as tmp:
        old_home = os.environ.get(base_env)
        os.environ[base_env] = tmp
        try:
            handle = create(1, 1, 1, 1, 17)
            assert handle > 0
            try:
                folder = Path(tmp)
                assert load(handle, None, task == 'scrabble') == 0
                assert load(handle, os.fsencode(folder / 'missing'), task == 'scrabble') == -1
                index = folder / 'index.tsv'
                index.write_bytes(b'')
                assert load(handle, os.fsencode(index), task == 'scrabble') == -1
                index.write_bytes(b'bad')
                assert load(handle, os.fsencode(index), task == 'scrabble') == -1
                index.write_bytes(b'aaa\t1\tThree-letter fixture clue\naaaa\t2\tFour-letter fixture clue\n')
                assert load(handle, os.fsencode(index), task == 'scrabble') == 0
                created = create_word(task == 'scrabble', 1, 1, 1, 1, os.fsencode(index))
                assert created > 0 and destroy(created) == 0
                assert create_word(task == 'scrabble', 1, 1, 1, 1, os.fsencode(folder / 'missing')) == 0
                index.unlink()
            finally:
                assert destroy(handle) == 0
        finally:
            if old_home is None: os.environ.pop(base_env, None)
            else: os.environ[base_env] = old_home
print('SDL word index: missing, invalid and valid files pass for both controllers')

create_scramble = lib.nw_sdl_create_scramble
create_scramble.argtypes = [ctypes.c_int64] * 4 + [ctypes.c_char_p, ctypes.c_char_p]
create_scramble.restype = ctypes.c_int64
scramble_info = lib.nw_scramble_info
scramble_info.argtypes = [ctypes.c_int64, ctypes.c_int64]
scramble_info.restype = ctypes.c_int64
scramble_destroy = lib.nw_scramble_destroy
scramble_destroy.argtypes = [ctypes.c_int64]
scramble_destroy.restype = ctypes.c_int64
with tempfile.TemporaryDirectory() as tmp:
    previous = os.environ.get(base_env)
    os.environ[base_env] = tmp
    try:
        root = Path(tmp)
        missing = os.fsencode(root / 'missing')
        assert create_scramble(1, 1, 1, 1, missing, None) == 0
        assert create_scramble(1, 1, 1, 1, None, missing) == 0
        index, sentences = root / 'index', root / 'sentences'
        index.write_bytes(b'cat\t1\t\na\t2\t\n')
        sentences.write_bytes(b'a cat a cat a cat\n')
        for index_path, sentence_path, has_index, has_sentences in (
            (None, None, 0, 0),
            (os.fsencode(index), None, 1, 0),
            (None, os.fsencode(sentences), 0, 1),
            (os.fsencode(index), os.fsencode(sentences), 1, 1),
        ):
            handle = create_scramble(1, 1, 1, 1, index_path, sentence_path)
            assert handle > 0
            try:
                assert scramble_info(handle, 14) == has_index
                assert scramble_info(handle, 15) == has_sentences
            finally:
                assert scramble_destroy(handle) == 0
        default_dir = root / ('Brain Workshop/data/words' if os.name == 'nt' else ('Library/Application Support/Brain Workshop/data/words' if sys.platform == 'darwin' else '.brainworkshop/data/words'))
        default_dir.mkdir(parents=True)
        default_sentences = default_dir / 'sentences.txt'
        for length, expected in ((4096, 0), (4097, 1)):
            default_sentences.write_bytes((b'a cat a cat a cat\n' * 300)[:length])
            handle = create_scramble(1, 1, 1, 1, None, None)
            assert handle > 0
            try:
                assert scramble_info(handle, 15) == expected
            finally:
                assert scramble_destroy(handle) == 0
    finally:
        if previous is None: os.environ.pop(base_env, None)
        else: os.environ[base_env] = previous
print('SDL Scramble corpus: missing, fallback and explicit files pass')
