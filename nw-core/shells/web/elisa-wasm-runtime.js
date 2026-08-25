// Host imports for an Elisa module compiled to wasm32.
//
// Elisa's runtime bottoms out in a small, fixed set of C calls: an allocator
// (malloc/mmap for arena backing), mem/string primitives, stdio formatting,
// abort/backtrace for diagnostics, and pthread for the concurrency std. On a
// native target libc supplies these. In the browser there is no libc, so this
// module supplies them over WebAssembly linear memory.
//
// Phase 1 scope, deliberately: SINGLE-THREADED. The pthread entry points are
// present so modules link and run, and they behave correctly for a program
// with one thread (locks always succeed, condvars are never waited on). A
// multi-threaded build needs SharedArrayBuffer and real atomics — that is a
// later phase, and the core game does not need it.

const PAGE = 65536;

export function createElisaRuntime() {
    let memory = null;
    let heapNext = 0;
    let heapEnd = 0;

    const u8 = () => new Uint8Array(memory.buffer);
    const dv = () => new DataView(memory.buffer);

    // Bump allocator over the region above __heap_base. Elisa allocates
    // arenas, not individual objects, so the arena is the unit that is reused
    // and this never needs a free list. `free`/`munmap` are honest no-ops:
    // memory returns when the whole instance is dropped.
    function grow(bytes) {
        const needed = heapNext + bytes;
        if (needed > heapEnd) {
            const pages = Math.ceil((needed - heapEnd) / PAGE) + 16;
            memory.grow(pages);
            heapEnd += pages * PAGE;
        }
    }

    function alloc(bytes, align = 16) {
        const size = Number(bytes);
        heapNext = (heapNext + align - 1) & ~(align - 1);
        grow(size);
        const at = heapNext;
        heapNext += size;
        return at;
    }

    function readCString(ptr) {
        const bytes = u8();
        let end = ptr;
        while (bytes[end] !== 0) end++;
        return new TextDecoder().decode(bytes.subarray(ptr, end));
    }

    let stdout = "";
    const flushLine = (text) => {
        stdout += text;
        let nl;
        while ((nl = stdout.indexOf("\n")) >= 0) {
            console.log(stdout.slice(0, nl));
            stdout = stdout.slice(nl + 1);
        }
    };

    const env = {
        // --- allocation -------------------------------------------------
        malloc: (size) => alloc(size),
        free: () => {},
        // Arena backing. prot/flags/fd are ignored: there is one flat address
        // space and no file mapping in the browser.
        mmap: (_addr, length) => alloc(length, PAGE),
        munmap: () => 0,

        // --- mem / string -----------------------------------------------
        memcpy: (dest, src, n) => {
            u8().copyWithin(dest, src, src + Number(n));
            return dest;
        },
        memmove: (dest, src, n) => {
            u8().copyWithin(dest, src, src + Number(n));
            return dest;
        },
        memset: (dest, value, n) => {
            u8().fill(value & 0xff, dest, dest + Number(n));
            return dest;
        },
        strlen: (ptr) => {
            const bytes = u8();
            let end = ptr;
            while (bytes[end] !== 0) end++;
            return end - ptr;
        },

        // --- stdio ------------------------------------------------------
        // Only the fixed-string and %s/%d/%lld cases the runtime actually
        // emits are formatted; anything else prints the raw format so a gap is
        // visible rather than silent.
        printf: (fmt) => {
            const text = readCString(fmt);
            flushLine(text);
            return text.length;
        },
        snprintf: (dest, size, fmt) => writeFormatted(dest, size, readCString(fmt)),
        vsnprintf: (dest, size, fmt) => writeFormatted(dest, size, readCString(fmt)),
        va_copy: () => 0,
        va_end: () => 0,

        // --- diagnostics ------------------------------------------------
        abort: () => {
            throw new Error("elisa: abort() called");
        },
        backtrace: () => 0,
        backtrace_symbols_fd: () => 0,

        // --- write(2), used for console output ---------------------------
        write: (_fd, ptr, len) => {
            flushLine(new TextDecoder().decode(u8().subarray(ptr, ptr + Number(len))));
            return len;
        },

        // --- pthread: single-threaded stubs ------------------------------
        pthread_mutex_init: () => 0,
        pthread_mutex_destroy: () => 0,
        pthread_mutex_lock: () => 0,
        pthread_mutex_unlock: () => 0,
        pthread_mutex_trylock: () => 0,
        pthread_cond_init: () => 0,
        pthread_cond_destroy: () => 0,
        pthread_cond_wait: () => 0,
        pthread_cond_signal: () => 0,
        pthread_cond_broadcast: () => 0,
        pthread_create: () => 1, // EPERM: no threads in phase 1
        pthread_join: () => 0,
        pthread_detach: () => 0,
        pthread_self: () => 0,
        sched_yield: () => 0,

        // --- misc libc ---------------------------------------------------
        memcmp: (a, b, n) => {
            const bytes = u8();
            for (let i = 0; i < Number(n); i++) {
                const d = bytes[a + i] - bytes[b + i];
                if (d !== 0) return d < 0 ? -1 : 1;
            }
            return 0;
        },
        strcmp: (a, b) => {
            const x = readCString(a), y = readCString(b);
            return x < y ? -1 : x > y ? 1 : 0;
        },
        puts: (ptr) => { flushLine(readCString(ptr) + "\n"); return 0; },
        exit: (code) => { throw new Error(`elisa: exit(${code})`); },
        getenv: () => 0,           // no environment in the browser
        getpid: () => 1,
        kill: () => 0,
        signal: () => 0,
        sigaction: () => 0,
        sysctlbyname: () => -1,    // no sysctl; callers fall back
        usleep: () => 0,           // cannot block the main thread

        // libm
        rint: (x) => {
            // Round half to EVEN, matching the default FP mode the port relies
            // on for CPython round() parity.
            const r = Math.round(x);
            return (Math.abs(x % 1) === 0.5 && r % 2 !== 0) ? r - Math.sign(x) : r;
        },

        // compiler-rt: 128-bit multiply, result written through a pointer.
        __multi3: (out, aLo, aHi, bLo, bHi) => {
            const mask = (1n << 64n) - 1n;
            const a = (BigInt.asUintN(64, BigInt(aHi)) << 64n) | BigInt.asUintN(64, BigInt(aLo));
            const b = (BigInt.asUintN(64, BigInt(bHi)) << 64n) | BigInt.asUintN(64, BigInt(bLo));
            const product = BigInt.asUintN(128, a * b);
            const view = dv();
            view.setBigUint64(out, product & mask, true);
            view.setBigUint64(out + 8, (product >> 64n) & mask, true);
        },
    };

    function writeFormatted(dest, size, text) {
        const bytes = new TextEncoder().encode(text);
        const limit = Math.min(bytes.length, Math.max(0, Number(size) - 1));
        if (dest !== 0) {
            u8().set(bytes.subarray(0, limit), dest);
            u8()[dest + limit] = 0;
        }
        return bytes.length;
    }

    return {
        imports: { env },
        // Called once after instantiation so the shim can see linear memory
        // and place its heap above the module's static data.
        attach(instance) {
            memory = instance.exports.memory;
            const base = instance.exports.__heap_base;
            heapNext = typeof base === "number" ? base : 65536;
            heapEnd = memory.buffer.byteLength;
            if (instance.exports.__wasm_call_ctors) instance.exports.__wasm_call_ctors();
            return instance;
        },
        flush() {
            if (stdout) {
                console.log(stdout);
                stdout = "";
            }
        },
    };
}

// Fill any import this shim does not implement with a stub that THROWS when
// called. A module then links and runs, and an unported runtime call announces
// itself by name at the moment it happens instead of failing at instantiation
// with no indication of which symbol was missing.
function completeImports(module, imports) {
    const missing = [];
    for (const entry of WebAssembly.Module.imports(module)) {
        const table = (imports[entry.module] ||= {});
        if (table[entry.name] === undefined) {
            missing.push(entry.name);
            table[entry.name] = (...args) => {
                throw new Error(`elisa: unimplemented host call ${entry.name}(${args.length} args)`);
            };
        }
    }
    return missing;
}

export async function instantiateElisa(bytes, { warn = true } = {}) {
    const runtime = createElisaRuntime();
    const module = await WebAssembly.compile(bytes);
    const missing = completeImports(module, runtime.imports);
    if (warn && missing.length) {
        console.warn(`elisa: ${missing.length} host calls stubbed: ${missing.join(", ")}`);
    }
    const instance = await WebAssembly.instantiate(module, runtime.imports);
    runtime.attach(instance);
    return { instance, runtime, exports: instance.exports, stubbed: missing };
}
