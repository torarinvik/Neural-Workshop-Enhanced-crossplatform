#!/usr/bin/env python3
"""Headless SDL/Python Syllogism settings compatibility and validation."""
import argparse
import os
import ctypes
import random
import itertools
import json
import re
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path
parser = argparse.ArgumentParser()
parser.add_argument('--runtime-object', type=Path)
parser.add_argument('--compiler', type=Path)
args = parser.parse_args()
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'shells/python'))
import app
flags=shlex.split(subprocess.check_output(['pkg-config','--cflags','--libs','sdl3'],text=True))
with tempfile.TemporaryDirectory() as temp:
    tmp=Path(temp); path=tmp/'settings'
    os.environ['NW_SYLLOGISM_SETTINGS_PATH']=str(path)
    object_file=tmp/'syllogism-options.o'
    compiler = args.compiler or Path(os.environ.get('ELISACORE_BIN', root / 'toolchain/elisac-stage0-seed'))
    subprocess.run([str(compiler),'-emit','obj','-O2','-o',str(object_file),
                    str(root/'src/native/sdl_host.elisa')],check=True)
    shared=tmp/'options.dylib'
    runtime = args.runtime_object or root / 'toolchain/elisacore_runtime.o'
    subprocess.run(['cc','-shared','-o',str(shared),str(object_file),str(runtime),*flags],check=True)
    library=ctypes.CDLL(str(shared))
    input_key=library.nw_syllogism_input_key
    input_key.argtypes=[ctypes.c_int64]*4+[ctypes.POINTER(ctypes.c_int64)]
    input_key.restype=ctypes.c_int64
    input_pointer=library.nw_syllogism_input_pointer
    input_pointer.argtypes=[ctypes.c_double,ctypes.c_double,ctypes.c_int64,ctypes.c_int64]
    input_pointer.restype=ctypes.c_int64
    value=ctypes.c_int64()
    def key(symbol,phase=1,opened=0,selected=0):
        action=input_key(symbol,phase,opened,selected,ctypes.byref(value))
        return action,value.value
    assert key(32,0)==(0,0) and key(32,1)==(1,0)
    assert key(13,1)==(1,0) and key(13,2)==(-1,0)
    assert [key(symbol)[0] for symbol in (0x40000050,0x4000004f,0x40000052,0x40000051)]==[2,3,4,5]
    assert key(ord('9'))==(6,8) and key(ord('o'),2)==(105,0) and key(ord('o'),1)==(-1,0)
    assert key(27,opened=1)==(100,0) and key(13,opened=1)==(104,0)
    assert key(0x40000050,opened=1)==(103,-1) and key(0x4000004f,opened=1)==(103,1)
    assert key(0x40000052,opened=1,selected=0)==(-1,0)
    assert key(0x40000051,opened=1,selected=4)==(-1,0)
    for row in range(5): assert input_pointer(200,474-row*48,1,0)==110+row
    assert input_pointer(200,100,1,0)==100 and input_pointer(600,100,1,0)==104
    assert input_pointer(100,474,1,0)==-1 and input_pointer(0,0,0,2)==0
    start=library.nw_syllogism_results_start
    start.argtypes=[ctypes.POINTER(ctypes.c_size_t),ctypes.POINTER(ctypes.c_int64)]
    judge=library.nw_syllogism_results_judge
    judge.argtypes=[ctypes.POINTER(ctypes.c_size_t)]+[ctypes.c_int64]*4
    finish=library.nw_syllogism_results_finish
    finish.argtypes=[ctypes.POINTER(ctypes.c_size_t)]+[ctypes.c_int64]*3
    close=library.nw_syllogism_results_close
    close.argtypes=[ctypes.POINTER(ctypes.c_size_t)]
    manager=(ctypes.c_size_t*2)()
    options=(ctypes.c_int64*5)(3,1,1,1,1)
    prior=os.environ.get('NW_SYLLOGISM_RESULTS_DIR')
    failed=tmp/'not-a-directory'; failed.write_text('retain me')
    saved=tmp/'syllogism-results'
    try:
        os.environ['NW_SYLLOGISM_RESULTS_DIR']=str(failed)
        start(manager,options)
        judge(manager,1,3,1,1250)
        judge(manager,1,3,1,1250)
        finish(manager,1,3,1)
        start(manager,options)
        assert manager[1]
        os.environ['NW_SYLLOGISM_RESULTS_DIR']=str(saved)
        judge(manager,1,3,0,2500)
        close(manager)
        assert list(manager)==[0,0]
        records=[json.loads(path.read_text()) for path in saved.glob('*.json')]
        assert len(records)==2 and len({record['id'] for record in records})==2
        completed=next(record for record in records if record['completed'])
        partial=next(record for record in records if not record['completed'])
        assert completed['options']==[3,1,1,1,1] and completed['right']==1 and completed['best_level']==3
        assert completed['results'][0]['elapsed_ms']==1250 and len(completed['results'])==1
        assert partial['results'][0]['correct'] is False and failed.read_text()=='retain me'
        assert not list(saved.glob('*.tmp'))
    finally:
        if prior is None: os.environ.pop('NW_SYLLOGISM_RESULTS_DIR',None)
        else: os.environ['NW_SYLLOGISM_RESULTS_DIR']=prior
    allowed=library.nw_syllogism_option_allowed
    allowed.argtypes=[ctypes.c_int64,ctypes.c_int64]; allowed.restype=ctypes.c_int64
    cycle=library.nw_syllogism_option_cycle
    cycle.argtypes=[ctypes.c_int64,ctypes.c_int64,ctypes.c_int64]; cycle.restype=ctypes.c_int64
    choices=[tuple(range(1,13)),app.SYLLOGISM_TRIALS,(0,1),(0,1),(0,1)]
    for row,values in enumerate(choices):
        for value in range(-2,18):
            assert bool(allowed(row,value)) == (value in values)
            for step in (-1,0,1):
                expected=values[(values.index(value)+(-1 if step<0 else 1))%len(values)] if value in values else value
                assert cycle(row,value,step)==expected, (row,value,step)
    assert allowed(-1,1)==0 and allowed(5,1)==0 and cycle(5,1,1)==1
    read_file=library.nw_syllogism_options_read_file
    read_file.argtypes=[ctypes.c_int64,ctypes.c_int64]; read_file.restype=ctypes.c_int64
    write_file=library.nw_syllogism_options_write_file
    write_file.argtypes=[ctypes.c_int64]*7; write_file.restype=ctypes.c_int64
    target=tmp/'ffi-settings'; staging=tmp/'ffi-settings.tmp'
    target_ptr=ctypes.create_string_buffer(os.fsencode(target))
    staging_ptr=ctypes.create_string_buffer(os.fsencode(staging))
    def write(values, final=target_ptr, temporary=staging_ptr):
        return write_file(ctypes.addressof(final),ctypes.addressof(temporary),*values)
    assert write((3,6,1,1,1))==1 and target.read_text()=='3 6 1 1 1\n'
    assert write((12,15,0,1,0))==1 and target.read_text()=='12 15 0 1 0\n'
    out=(ctypes.c_int64*5)(*([-7]*5))
    assert read_file(ctypes.addressof(target_ptr),ctypes.addressof(out))==1
    assert tuple(out)==(12,15,0,1,0)
    staging.write_text('do not overwrite')
    assert write((1,1,1,1,1))==0
    assert staging.read_text()=='do not overwrite' and target.read_text()=='12 15 0 1 0\n'
    staging.unlink()
    duplicate_path=ctypes.create_string_buffer(os.fsencode(target))
    assert write((1,1,1,1,1),temporary=duplicate_path)==0
    assert target.read_text()=='12 15 0 1 0\n'
    assert write((13,1,1,1,1))==0 and not staging.exists()
    target.write_bytes(b'3 6 1 1 1\0bad')
    out=(ctypes.c_int64*5)(*([-7]*5))
    assert read_file(ctypes.addressof(target_ptr),ctypes.addressof(out))==0 and list(out)==[-7]*5
    target.write_bytes(b'3 6 1 1 1\n'+b' '*300)
    assert read_file(ctypes.addressof(target_ptr),ctypes.addressof(out))==0 and list(out)==[-7]*5

    encode=library.nw_syllogism_option_encode
    encode.argtypes=[ctypes.c_int64]*7; encode.restype=ctypes.c_int64
    for values in itertools.product(*choices):
        expected=(' '.join(map(str,values))+'\n').encode()
        buffer=ctypes.create_string_buffer(b'X'*32,32)
        assert encode(ctypes.addressof(buffer),len(expected)-1,*values)==-1
        assert buffer.raw==b'X'*32, 'short capacity must not modify the destination'
        assert encode(ctypes.addressof(buffer),len(expected),*values)==len(expected)
        assert buffer.raw[:len(expected)]==expected and buffer.raw[len(expected):]==b'X'*(32-len(expected))
    buffer=ctypes.create_string_buffer(b'X'*32,32)
    assert encode(ctypes.addressof(buffer),32,13,6,1,1,1)==-1 and buffer.raw==b'X'*32

    decode=library.nw_syllogism_option_decode
    decode.argtypes=[ctypes.c_int64,ctypes.c_int64,ctypes.c_int64]; decode.restype=ctypes.c_int64
    def decode_values(data):
        buffer=ctypes.create_string_buffer(data)
        return tuple(decode(ctypes.addressof(buffer),len(data),row) for row in range(5))
    def reference(data):
        if not data or len(data)>256: return (-1,)*5
        parts=data.split()
        if len(parts)!=5 or any(not re.fullmatch(rb'[+-]?[0-9]+',part) for part in parts): return (-1,)*5
        values=tuple(int(part) for part in parts)
        return values if all(value in choices[row] for row,value in enumerate(values)) else (-1,)*5
    corpus=[b'3 6 1 1 1\n',b'+03 006 -0 +1 1',b'3 6 1 1 1\0hidden',
            b'3 6 1 1 1 0',b'3 6 1 1',b'3 6 1 1 1\n'*50,b'3 6 1 1 +']
    rng=random.Random(19)
    alphabet=b'0123456789 +-\t\n\r\x00x'
    corpus += [bytes(rng.choice(alphabet) for _ in range(rng.randrange(1,70))) for _ in range(1000)]
    for data in corpus:
        assert decode_values(data)==reference(data), repr(data)

    class Options(ctypes.Structure):
        _fields_=[(name,ctypes.c_int64) for name in ('level','trials','working','adaptive','real_words')]
        def values(self): return (self.level,self.trials,self.working,self.adaptive,self.real_words)
    parse=library.nw_syllogism_options_parse
    parse.argtypes=[ctypes.c_int64,ctypes.POINTER(ctypes.c_char_p),ctypes.POINTER(Options),ctypes.c_int64]
    parse.restype=ctypes.c_int64
    save=library.nw_syllogism_options_save
    save.argtypes=[ctypes.POINTER(Options)]; save.restype=ctypes.c_int64
    modify=library.nw_syllogism_options_modify
    modify.argtypes=[ctypes.POINTER(Options),ctypes.c_int64,ctypes.c_int64]; modify.restype=ctypes.c_int64
    os.environ['NW_SYLLOGISM_SETTINGS_PATH']=str(path)
    def call(*args):
        arguments=[b'nw-test',*(value.encode() for value in args)]
        argv=(ctypes.c_char_p*len(arguments))(*arguments)
        options=Options()
        status=parse(len(arguments),argv,ctypes.byref(options),1)
        return status,options
    status,o=call(); assert status==0 and o.values()==(3,6,1,1,1)
    status,o=call('--syllogism-level','12','--syllogism-trials','3','--syllogism-no-working',
                  '--syllogism-no-adaptive','--syllogism-invented-words')
    assert status==0 and save(ctypes.byref(o))==1 and app.read_syllogism_settings()==(12,3,0,0,0)
    assert app.write_syllogism_settings((7,8,1,0,1))
    status,o=call(); assert status==0 and o.values()==(7,8,1,0,1)
    assert modify(ctypes.byref(o),0,1)==1 and o.level==8
    assert call('--syllogism-level','13')[0]==2
    assert call('--syllogism-level','  +3')[1].level==3
    status,o=call('--syllogism-level','3 '); assert status==0 and o.level==3
    assert call('--syllogism-level','0'*300+'3')[1].level==3
    path.write_text('7 4 1 0 1\n'); assert call()[1].values()==(3,6,1,1,1)
    path.write_bytes(b'3 6 1 1 1\x00trailing'); assert call()[1].values()==(3,6,1,1,1)
    fallback_env=os.environ.copy(); fallback_env.pop('NW_SYLLOGISM_SETTINGS_PATH',None)
    fallback_env['HOME']=str(tmp/'home'); (tmp/'home').mkdir()
    child = """import ctypes,sys
library=ctypes.CDLL(sys.argv[1])
save=library.nw_syllogism_options_save
save.argtypes=[ctypes.POINTER(ctypes.c_int64)]; save.restype=ctypes.c_int64
values=(ctypes.c_int64*5)(9,6,1,1,1)
assert save(values)==1
"""
    subprocess.run([sys.executable,'-c',child,str(shared)],env=fallback_env,check=True)
    assert (tmp/'home/.neural-workshop/syllogism-options').read_text()=='9 6 1 1 1\n'

print('Syllogism SDL settings: defaults, validation and Python round-trip pass')
