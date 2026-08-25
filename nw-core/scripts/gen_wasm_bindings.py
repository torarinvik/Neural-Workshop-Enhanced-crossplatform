#!/usr/bin/env python3
"""Generate typed JS/TypeScript bindings for an Elisa wasm module.

This is the web twin of `-emit pymodule-pyi`: from one build you get a typed
surface, so a shell calls `core.msToTicks(250, 100)` with numbers instead of
hand-managing BigInt at every call site.

It reads the signatures out of the wasm binary rather than out of the Elisa
source, which means it needs no compiler support and cannot drift from what was
actually emitted. When `export wasmmodule` lands in the compiler this becomes
its `.d.ts` writer; the shape of the output is the contract either way.

    python3 scripts/gen_wasm_bindings.py build/nwcore.wasm --out build/nwcore

writes build/nwcore.js and build/nwcore.d.ts.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

VALUE_TYPES = {0x7F: "i32", 0x7E: "i64", 0x7D: "f32", 0x7C: "f64"}

# wasm i64 crosses the JS boundary as BigInt; everything else is a number.
TS_TYPE = {"i32": "number", "i64": "bigint", "f32": "number", "f64": "number"}


def read_leb(data: bytes, at: int) -> tuple[int, int]:
    result = shift = 0
    while True:
        byte = data[at]
        at += 1
        result |= (byte & 0x7F) << shift
        shift += 7
        if not byte & 0x80:
            return result, at


def parse_exports(blob: bytes):
    """(types, exported functions, imported function count)."""
    at = 8
    types: list[tuple[list[str], list[str]]] = []
    functions: list[int] = []   # type index per defined function
    imported = 0
    exports: list[tuple[str, int]] = []

    while at < len(blob):
        section = blob[at]
        at += 1
        size, at = read_leb(blob, at)
        end = at + size

        if section == 1:                                   # types
            count, at = read_leb(blob, at)
            for _ in range(count):
                at += 1                                    # 0x60 func form
                n, at = read_leb(blob, at)
                params = [VALUE_TYPES[blob[at + i]] for i in range(n)]
                at += n
                n, at = read_leb(blob, at)
                results = [VALUE_TYPES[blob[at + i]] for i in range(n)]
                at += n
                types.append((params, results))
        elif section == 2:                                 # imports
            count, at = read_leb(blob, at)
            for _ in range(count):
                n, at = read_leb(blob, at); at += n        # module name
                n, at = read_leb(blob, at); at += n        # field name
                kind = blob[at]; at += 1
                if kind == 0:
                    _, at = read_leb(blob, at)
                    imported += 1
                else:
                    break
        elif section == 3:                                 # function decls
            count, at = read_leb(blob, at)
            for _ in range(count):
                index, at = read_leb(blob, at)
                functions.append(index)
        elif section == 7:                                 # exports
            count, at = read_leb(blob, at)
            for _ in range(count):
                n, at = read_leb(blob, at)
                name = blob[at:at + n].decode("utf-8")
                at += n
                kind = blob[at]; at += 1
                index, at = read_leb(blob, at)
                if kind == 0:
                    exports.append((name, index))
        at = end
    return types, functions, imported, exports


def camel(name: str) -> str:
    """nw_ms_to_ticks -> msToTicks. The nw_ prefix is the C-ABI namespace; JS
    has modules, so it is dropped."""
    stem = re.sub(r"^nw_", "", name)
    head, *rest = stem.split("_")
    return head + "".join(part.capitalize() for part in rest)


def generate(wasm_path: Path, out_stem: Path, module_name: str, runtime_import: str):
    blob = wasm_path.read_bytes()
    types, functions, imported, exports = parse_exports(blob)

    api = []
    for name, index in sorted(exports):
        if name.startswith("__") or index < imported:
            continue                                       # runtime internals
        params, results = types[functions[index - imported]]
        api.append((name, camel(name), params, results))

    if not api:
        sys.exit(f"{wasm_path}: no exported functions found")

    ts = [
        "// Generated from {} — do not edit.".format(wasm_path.name),
        "//",
        "// Every wasm i64 is a JS bigint. The wrapper accepts plain numbers",
        "// too and converts, so call sites stay readable.",
        "",
        "export interface {}Exports {{".format(module_name.capitalize()),
    ]
    js = [
        "// Generated from {} — do not edit.".format(wasm_path.name),
        f'import {{ instantiateElisa }} from "{runtime_import}";',
        "",
        "export async function load(source) {",
        "    const { exports, instance, runtime } = await instantiateElisa(source);",
        "    const api = {",
    ]

    for raw, nice, params, results in api:
        arg_names = [f"a{i}" for i in range(len(params))]
        ts_args = ", ".join(
            f"{arg}: {'number | bigint' if TS_TYPE[p] == 'bigint' else 'number'}"
            for arg, p in zip(arg_names, params))
        ts_ret = TS_TYPE[results[0]] if results else "void"
        ts.append(f"    {nice}({ts_args}): {ts_ret};")

        coerced = ", ".join(
            f"BigInt({arg})" if TS_TYPE[p] == "bigint" else arg
            for arg, p in zip(arg_names, params))
        js.append(f"        {nice}: ({', '.join(arg_names)}) => "
                  f"exports.{raw}({coerced}),")

    ts += [
        "    /** The module's linear memory, for zero-copy reads. */",
        "    memory: WebAssembly.Memory;",
        "}",
        "",
        "export function load(source: BufferSource): Promise<{}Exports>;"
        .format(module_name.capitalize()),
        "",
    ]
    js += [
        "        memory: instance.exports.memory,",
        "        __instance: instance,",
        "        __runtime: runtime,",
        "    };",
        "    return api;",
        "}",
        "",
    ]

    out_stem.with_suffix(".d.ts").write_text("\n".join(ts))
    out_stem.with_suffix(".js").write_text("\n".join(js))
    print(f"wrote {out_stem.with_suffix('.js').name} and "
          f"{out_stem.with_suffix('.d.ts').name} ({len(api)} functions)")
    for _, nice, params, results in api:
        signature = ", ".join(TS_TYPE[p] for p in params)
        ret = TS_TYPE[results[0]] if results else "void"
        print(f"    {nice}({signature}) -> {ret}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wasm", type=Path)
    parser.add_argument("--out", type=Path, required=True,
                        help="output path stem (.js and .d.ts are appended)")
    parser.add_argument("--name", default="nwcore")
    parser.add_argument("--runtime-import",
                        default="../shells/web/elisa-wasm-runtime.js",
                        help="module specifier for the host-import shim, "
                             "relative to the generated file")
    args = parser.parse_args()
    generate(args.wasm, args.out, args.name, args.runtime_import)


if __name__ == "__main__":
    main()
