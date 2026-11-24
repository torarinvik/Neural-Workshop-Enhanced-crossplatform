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

import { createDispatchEnvironment, createFirebreakEnvironment, createCrossroadsEnvironment, createRailYardEnvironment, createAirTrafficEnvironment, createEscortEnvironment, createSokobanLiveEnvironment, createKitchenEnvironment, createCraneEnvironment, createFerryEnvironment, createDockingEnvironment, createUnicycleEnvironment, createMorningRoundEnvironment, createHeavierEnvironment, createCrazyCogEnvironment, createPotterEnvironment, createConductorEnvironment, createTightropeEnvironment, createSignPainterEnvironment, createBartenderEnvironment, createLockPickEnvironment, createAirHockeyEnvironment, createSemaphoreEnvironment, createShadowPuppetsEnvironment, createNightWatchEnvironment, createKerbsideEnvironment, createSteadicamEnvironment, createFreeKickEnvironment, createByEarEnvironment, createPianoTunerEnvironment, createCricketHuntEnvironment, createClawMachineEnvironment, createGloveEnvironment, createCipherAbyssEnvironment, createFullStopEnvironment, createMissingWordEnvironment, createProofreaderEnvironment, createFiguresOfSpeechEnvironment, createBetweenTheLinesEnvironment, createSecondThoughtsEnvironment, createBadArgumentEnvironment, createSocialSenseEnvironment, createWhichFeelingEnvironment, createHowStronglyEnvironment, createReadingPeopleEnvironment, createWhyTheyFeelEnvironment, createToneOfVoiceEnvironment, createBrowserEnvironment, createSpreadsheetEnvironment, createErrandsEnvironment, createManualEnvironment, createFormsEnvironment, createDesktopEnvironment, createEmotionEnvironment, createRoverEnvironment, createGambleEnvironment, createBluffEnvironment, createExploreOrExploitEnvironment, createSonarEnvironment, createDamKeeperEnvironment, createDelayEnvironment, createHoldItEnvironment, createTimeItEnvironment, createBeatEnvironment, createCatchEnvironment, createEchoCaveEnvironment, createDroneHoopsEnvironment, createFieldManualEnvironment, createSafecrackerEnvironment, createStagehandEnvironment, createLoadingDockEnvironment, createGunslingerEnvironment, createDrShapeEnvironment, createShadowPlayEnvironment, createTunerEnvironment, createBalanceEnvironment, createJugglerEnvironment, createLanderEnvironment, createGliderEnvironment, createNotebookEnvironment, createStopAndSwitchEnvironment, createTriageEnvironment, createWhereWasItEnvironment, createWhichIsNearerEnvironment, createShapeFromMotionEnvironment, createSameOrMirrorEnvironment, createPointOfViewEnvironment, createInsideOrOutEnvironment, createWillItFallEnvironment, createCaptchaEnvironment, createSignalsEnvironment, createFoldItEnvironment, createWhoKnowsWhatEnvironment, createTouchingEnvironment, createCrossingsEnvironment } from "./rung-env.js";
import { createCookieThiefEnvironment } from "./cookie-thief-env.js";
import { createPublicFrameArchive, createPublicOutcomeVerifier } from "./public-outcome.js";

const PAGE = 65536;

export function createElisaRuntime() {
    let memory = null;
    let heapNext = 0;
    let heapEnd = 0;
    let heapBase = 0;   // __heap_base: static data lives below it, never reclaim past it

    const u8 = () => new Uint8Array(memory.buffer);
    const dv = () => new DataView(memory.buffer);

    // Bump allocator over the region above __heap_base. Elisa allocates
    // ARENAS, not individual objects, so a general free list would be dead
    // weight -- but the top block MUST be reclaimable. A program that builds a
    // frame in a scratch region per tick calls mmap/munmap once per frame, and
    // with a no-op munmap the heap grew ~33MB per frame AND later frames came
    // back corrupted. Rewinding the bump pointer when the freed block is the
    // most recent allocation keeps a per-frame region flat in both respects.
    function grow(bytes) {
        const needed = heapNext + bytes;
        if (needed > heapEnd) {
            const pages = Math.ceil((needed - heapEnd) / PAGE) + 16;
            // memory.grow returns -1 rather than throwing. Ignoring that and
            // advancing heapEnd anyway hands out addresses PAST the end of
            // linear memory, and the failure then surfaces as an unrelated
            // "memory access out of bounds" deep inside arena_alloc. Fail here,
            // where the cause is still legible.
            if (memory.grow(pages) < 0) {
                throw new RangeError(
                    `elisa: out of wasm memory (wanted ${pages} more pages, ` +
                    `have ${heapEnd / PAGE})`);
            }
            heapEnd += pages * PAGE;
        }
    }

    // Live blocks, innermost last. A stack rather than a single `lastBlock`,
    // because regions nest: a frame opens a region, opens a second one inside
    // it, then frees them innermost-first. With only the top block rewindable,
    // the OUTER free was silently dropped and its bytes leaked -- and since
    // alloc() aligns heapNext UP before recording `at`, the alternative
    // `start + length === heapNext` test can never match once any padding has
    // been inserted between two blocks. A frame leaked its whole outer region
    // every tick until memory.grow failed.
    const blocks = [];

    function alloc(bytes, align = 16) {
        const size = Number(bytes);
        heapNext = Math.ceil(heapNext / align) * align;
        grow(size);
        const at = heapNext;
        heapNext += size;
        blocks.push({ at, size });
        return at;
    }

    // Reclaim `at`, and with it any already-freed blocks it was holding down.
    // Freeing out of order is legal and common (the runtime frees a region
    // chain in list order, not address order), so a freed block that is not
    // currently on top is marked dead and collected when the block below it
    // goes; that keeps a LIFO workload -- which is what every per-frame region
    // is -- exactly flat.
    function release(at, size) {
        const start = Number(at);
        const index = blocks.findIndex((b) => b !== null && b.at === start);
        if (index < 0) return 0;
        blocks[index] = null;
        while (blocks.length && blocks[blocks.length - 1] === null) {
            blocks.pop();
        }
        const top = blocks[blocks.length - 1];
        heapNext = top ? top.at + top.size : heapBase;
        return 0;
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
        free: (ptr) => release(ptr, 0),
        realloc: (ptr, size) => {
            const old = Number(ptr);
            const nextSize = Number(size);
            if (old === 0) return alloc(nextSize);
            if (nextSize === 0) {
                release(old, 0);
                return 0;
            }
            const block = blocks.find((entry) => entry !== null && entry.at === old);
            if (!block) throw new Error(`elisa: realloc of unknown heap block ${old}`);
            const next = alloc(nextSize);
            u8().copyWithin(next, old, old + Math.min(block.size, nextSize));
            release(old, block.size);
            return next;
        },
        // Arena backing. prot/flags/fd are ignored: there is one flat address
        // space and no file mapping in the browser.
        //
        // Widths are handled by adapt(): on wasm32 stage0 lowers some
        // pointer/size externs as i64 and others as i32 (see
        // repro/nw_wasm32_usize_width.md), so the shim reads each import's
        // declared signature rather than assuming a convention.
        mmap: (_addr, length) => alloc(length, PAGE),
        munmap: (addr, length) => release(addr, length),

        // --- optional allocation profiler ABI -------------------------
        // Native standalone builds link these weak no-op definitions from
        // compiler/runtime/profile_hooks.c. Keep the same contract in the
        // browser: negotiate returns 0 (unsupported), and event callbacks
        // intentionally have no side effects. These are real imports used by
        // arena allocation, not missing functions to defer-fail on first use.
        elisa_profile_allocation_negotiate: (_version) => 0,
        elisa_profile_region_layout_negotiate: (_version) => 0,
        elisa_profile_region_layout_v1: () => 0,
        elisa_profile_allocation_event_v1: () => 0,
        // Stage1 emits this runtime helper for explicit region creation. The
        // helper only reports an event after the negotiation above succeeds;
        // because this browser host advertises profiling as unsupported, the
        // equivalent host implementation is intentionally a no-op.
        arena_profile_explicit_create: () => 0,

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
        // Elisa's JSON parser passes a validated, NUL-terminated decimal token.
        strtod: (pointer) => Number(readCString(pointer)),
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
        cos: (x) => Math.cos(x),
        sin: (x) => Math.sin(x),
        sqrt: (x) => Math.sqrt(x),
        hypot: (x, y) => Math.hypot(x, y),
        fmod: (x, y) => x % y,
        fmin: (x, y) => Number.isNaN(x) ? y : (Number.isNaN(y) ? x : Math.min(x, y)),
        fmax: (x, y) => Number.isNaN(x) ? y : (Number.isNaN(y) ? x : Math.max(x, y)),
        exp: (x) => Math.exp(x),
        exp2: (x) => 2 ** x,
        tan: (x) => Math.tan(x),
        tanh: (x) => Math.tanh(x),
        log: (x) => Math.log(x),
        log2: (x) => Math.log2(x),
        log10: (x) => Math.log10(x),
        asin: (x) => Math.asin(x),
        acos: (x) => Math.acos(x),
        atan: (x) => Math.atan(x),
        atan2: (y, x) => Math.atan2(y, x),
        pow: (base, exponent) => Math.pow(base, exponent),
        fabs: (x) => Math.abs(x),
        copysign: (magnitude, sign) => Math.abs(magnitude) * (sign < 0 || Object.is(sign, -0) ? -1 : 1),

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
        // compiler-rt unsigned 128-bit quotient; both operands and the
        // result use the wasm32 lowered (pointer, low, high) ABI.
        __udivti3: (out, aLo, aHi, bLo, bHi) => {
            const mask = (1n << 64n) - 1n;
            const a = (BigInt.asUintN(64, aHi) << 64n) | BigInt.asUintN(64, aLo);
            const b = (BigInt.asUintN(64, bHi) << 64n) | BigInt.asUintN(64, bLo);
            if (b === 0n) throw new RangeError("128-bit division by zero");
            const quotient = a / b;
            const view = dv();
            view.setBigUint64(out, quotient & mask, true);
            view.setBigUint64(out + 8, (quotient >> 64n) & mask, true);
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
            // __heap_base comes across as a WebAssembly.Global, not a number.
            // The old `typeof base === "number"` test was therefore ALWAYS false
            // and the 65536 fallback always fired, putting the heap on top of the
            // module's static data: string literals were overwritten mid-run, and
            // the damage read as corrupt program logic rather than a bad heap
            // base. Guessing here is worse than failing, so it fails.
            const raw = instance.exports.__heap_base;
            const base = raw instanceof WebAssembly.Global ? raw.value
                       : typeof raw === "number" ? raw : null;
            if (base === null) {
                throw new Error(
                    "elisa: module does not export __heap_base -- link with " +
                    "`wasm-ld --export=__heap_base`. Refusing to guess a heap " +
                    "base: a wrong one silently overwrites static data.");
            }
            heapNext = base;
            heapBase = base;
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

// Minimal parser for the type and import sections. The shim needs the DECLARED
// signature of each import so it can hand back i64 results as BigInt: on wasm32
// stage0 lowers some pointer/size externs as i64 and others as i32 (see
// repro/nw_wasm32_usize_width.md), so a fixed convention cannot satisfy the
// module. Reading the signatures adapts to whatever the compiler emitted.
function importSignatures(bytes) {
    const VALUE_TYPES = { 0x7f: "i32", 0x7e: "i64", 0x7d: "f32", 0x7c: "f64" };
    let at = 8; // past the magic and version words
    const types = [];
    const signatures = new Map();
    const leb = () => {
        let result = 0, shift = 0, byte;
        do { byte = bytes[at++]; result |= (byte & 0x7f) << shift; shift += 7; } while (byte & 0x80);
        return result >>> 0;
    };
    while (at < bytes.length) {
        const id = bytes[at++];
        const size = leb();
        const end = at + size;
        if (id === 1) {
            const count = leb();
            for (let i = 0; i < count; i++) {
                at++; // 0x60 function form
                const params = [];
                for (let n = leb(), j = 0; j < n; j++) params.push(VALUE_TYPES[bytes[at++]]);
                const results = [];
                for (let n = leb(), j = 0; j < n; j++) results.push(VALUE_TYPES[bytes[at++]]);
                types.push({ params, results });
            }
        } else if (id === 2) {
            const count = leb();
            for (let i = 0; i < count; i++) {
                const moduleLen = leb();
                at += moduleLen;
                const nameLen = leb();
                const name = new TextDecoder().decode(bytes.subarray(at, at + nameLen));
                at += nameLen;
                const kind = bytes[at++];
                if (kind !== 0) break; // only function imports need wrapping
                signatures.set(name, types[leb()]);
            }
        }
        at = end;
    }
    return signatures;
}

// Adapt one implementation to its declared signature: i64 parameters arrive as
// BigInt and are handed on as Numbers, and an i64 result goes back as BigInt.
function adapt(fn, signature, preserveI64 = false) {
    if (!signature) return fn;
    const returnsI64 = signature.results[0] === "i64";
    return (...args) => {
        const result = fn(...args.map((a) => (typeof a === "bigint" && !preserveI64 ? Number(a) : a)));
        if (!returnsI64) return result;
        return BigInt(result === undefined || result === null ? 0 : result);
    };
}

// Fill any import this shim does not implement with a stub that THROWS when
// called. A module then links and runs, and an unported runtime call announces
// itself by name at the moment it happens instead of failing at instantiation
// with no indication of which symbol was missing.
function completeImports(module, imports, signatures) {
    const missing = [];
    for (const entry of WebAssembly.Module.imports(module)) {
        const table = (imports[entry.module] ||= {});
        const signature = signatures.get(entry.name);
        if (table[entry.name] === undefined) {
            missing.push(entry.name);
            table[entry.name] = adapt((...args) => {
                throw new Error(`elisa: unimplemented host call ${entry.name}(${args.length} args)`);
            }, signature);
        } else {
            table[entry.name] = adapt(table[entry.name], signature,
                entry.name === "__multi3" || entry.name === "__udivti3");
        }
    }
    return missing;
}

export async function instantiateElisa(source, { warn = true } = {}) {
    // fetch() hands back an ArrayBuffer and fs.readFileSync a Buffer; the
    // signature parser indexes bytes, so normalise before touching it.
    const bytes = source instanceof Uint8Array ? source : new Uint8Array(source);
    const runtime = createElisaRuntime();
    const module = await WebAssembly.compile(bytes);
    const missing = completeImports(module, runtime.imports, importSignatures(bytes));
    if (warn && missing.length) {
        console.warn(`elisa: ${missing.length} host calls stubbed: ${missing.join(", ")}`);
    }
    const instance = await WebAssembly.instantiate(module, runtime.imports);
    runtime.attach(instance);
    const exports = instance.exports;
    const verifyPublicOutcome = createPublicOutcomeVerifier(exports, exports.memory);
    const verifyTaskOutcome = createPublicOutcomeVerifier(exports, exports.memory, { allowConcessions: true });
    const frameArchive = (context) =>
        createPublicFrameArchive(context, exports, exports.memory, verifyPublicOutcome);
    return {
        instance, runtime, exports, stubbed: missing, verifyPublicOutcome, verifyTaskOutcome,
        createPublicFrameArchive: frameArchive,
        createDelayEnvironment: (context, options) =>
            createDelayEnvironment(exports, context, () =>
                createPublicFrameArchive(context, exports, exports.memory, verifyTaskOutcome), options),
        createHoldItEnvironment: (context, options) =>
            createHoldItEnvironment(exports, context, () =>
                createPublicFrameArchive(context, exports, exports.memory, verifyTaskOutcome), options),
        createTimeItEnvironment: (context, options) =>
            createTimeItEnvironment(exports, context, () =>
                createPublicFrameArchive(context, exports, exports.memory, verifyTaskOutcome), options),
        createBeatEnvironment: (context, options) =>
            createBeatEnvironment(exports, context, () =>
                createPublicFrameArchive(context, exports, exports.memory, verifyTaskOutcome), options),
        createCatchEnvironment: (context, options) =>
            createCatchEnvironment(exports, context, () =>
                createPublicFrameArchive(context, exports, exports.memory, verifyTaskOutcome), options),
        createEchoCaveEnvironment: (context, options) =>
            createEchoCaveEnvironment(exports, context, () =>
                createPublicFrameArchive(context, exports, exports.memory, verifyTaskOutcome), options),
        createDroneHoopsEnvironment: (context, options) =>
            createDroneHoopsEnvironment(exports, context, () =>
                createPublicFrameArchive(context, exports, exports.memory, verifyTaskOutcome), options),
        createFieldManualEnvironment: (context, options) =>
            createFieldManualEnvironment(exports, context, () =>
                createPublicFrameArchive(context, exports, exports.memory, verifyTaskOutcome), options),
        createSafecrackerEnvironment: (context, options) =>
            createSafecrackerEnvironment(exports, context, () =>
                createPublicFrameArchive(context, exports, exports.memory, verifyTaskOutcome), options),
        createStagehandEnvironment: (context, options) =>
            createStagehandEnvironment(exports, context, () =>
                createPublicFrameArchive(context, exports, exports.memory, verifyTaskOutcome), options),
        createLoadingDockEnvironment: (context, options) =>
            createLoadingDockEnvironment(exports, context, () =>
                createPublicFrameArchive(context, exports, exports.memory, verifyTaskOutcome), options),
        createGunslingerEnvironment: (context, options) =>
            createGunslingerEnvironment(exports, context, () =>
                createPublicFrameArchive(context, exports, exports.memory, verifyTaskOutcome), options),
        createDrShapeEnvironment: (context, options) =>
            createDrShapeEnvironment(exports, context, () =>
                createPublicFrameArchive(context, exports, exports.memory, verifyTaskOutcome), options),
        createShadowPlayEnvironment: (context, options) =>
            createShadowPlayEnvironment(exports, context, () =>
                createPublicFrameArchive(context, exports, exports.memory, verifyTaskOutcome), options),
        createTunerEnvironment: (context, options) =>
            createTunerEnvironment(exports, context, () =>
                createPublicFrameArchive(context, exports, exports.memory, verifyTaskOutcome), options),
        createBalanceEnvironment: (context, options) =>
            createBalanceEnvironment(exports, context, () =>
                createPublicFrameArchive(context, exports, exports.memory, verifyTaskOutcome), options),
        createJugglerEnvironment: (context, options) =>
            createJugglerEnvironment(exports, context, () =>
                createPublicFrameArchive(context, exports, exports.memory, verifyTaskOutcome), options),
        createLanderEnvironment: (context, options) =>
            createLanderEnvironment(exports, context, () =>
                createPublicFrameArchive(context, exports, exports.memory, verifyTaskOutcome), options),
        createGliderEnvironment: (context, options) =>
            createGliderEnvironment(exports, context, () =>
                createPublicFrameArchive(context, exports, exports.memory, verifyTaskOutcome), options),
        createStopAndSwitchEnvironment: (context, options) =>
            createStopAndSwitchEnvironment(exports, context, () =>
                createPublicFrameArchive(context, exports, exports.memory, verifyTaskOutcome), options),
        createNotebookEnvironment: (context, options) =>
            createNotebookEnvironment(exports, context, () =>
                createPublicFrameArchive(context, exports, exports.memory, verifyTaskOutcome), options),
        createTriageEnvironment: (context, options) =>
            createTriageEnvironment(exports, context, () =>
                createPublicFrameArchive(context, exports, exports.memory, verifyTaskOutcome), options),
        createWhereWasItEnvironment: (context, options) =>
            createWhereWasItEnvironment(exports, context, () =>
                createPublicFrameArchive(context, exports, exports.memory, verifyTaskOutcome), options),
        createSameOrMirrorEnvironment: (context, options) =>
            createSameOrMirrorEnvironment(exports, context, () =>
                createPublicFrameArchive(context, exports, exports.memory, verifyTaskOutcome), options),
        createPointOfViewEnvironment: (context, options) =>
            createPointOfViewEnvironment(exports, context, () =>
                createPublicFrameArchive(context, exports, exports.memory, verifyTaskOutcome), options),
        createWillItFallEnvironment: (context, options) =>
            createWillItFallEnvironment(exports, context, () =>
                createPublicFrameArchive(context, exports, exports.memory, verifyTaskOutcome), options),
        createCaptchaEnvironment: (context, options) =>
            createCaptchaEnvironment(exports, context, () =>
                createPublicFrameArchive(context, exports, exports.memory, verifyTaskOutcome), options),
        createSignalsEnvironment: (context, options) =>
            createSignalsEnvironment(exports, context, () =>
                createPublicFrameArchive(context, exports, exports.memory, verifyTaskOutcome), options),
        createFoldItEnvironment: (context, options) =>
            createFoldItEnvironment(exports, context, () =>
                createPublicFrameArchive(context, exports, exports.memory, verifyTaskOutcome), options),
        createWhoKnowsWhatEnvironment: (context, options) =>
            createWhoKnowsWhatEnvironment(exports, context, () =>
                createPublicFrameArchive(context, exports, exports.memory, verifyTaskOutcome), options),
        createSonarEnvironment: (context, options) =>
            createSonarEnvironment(exports, context, () =>
                createPublicFrameArchive(context, exports, exports.memory, verifyTaskOutcome), options),
        createGambleEnvironment: (context, options) =>
            createGambleEnvironment(exports, context, () =>
                createPublicFrameArchive(context, exports, exports.memory, verifyTaskOutcome), options),
        createBluffEnvironment: (context, options) =>
            createBluffEnvironment(exports, context, () =>
                createPublicFrameArchive(context, exports, exports.memory, verifyTaskOutcome), options),
        createExploreOrExploitEnvironment: (context, options) =>
            createExploreOrExploitEnvironment(exports, context, () =>
                createPublicFrameArchive(context, exports, exports.memory, verifyTaskOutcome), options),
        createInsideOrOutEnvironment: (context, options) =>
            createInsideOrOutEnvironment(exports, context, () =>
                createPublicFrameArchive(context, exports, exports.memory, verifyTaskOutcome), options),
        createTouchingEnvironment: (context, options) =>
            createTouchingEnvironment(exports, context, () =>
                createPublicFrameArchive(context, exports, exports.memory, verifyTaskOutcome), options),
        createCrossingsEnvironment: (context, options) =>
            createCrossingsEnvironment(exports, context, () =>
                createPublicFrameArchive(context, exports, exports.memory, verifyTaskOutcome), options),
        createWhichIsNearerEnvironment: (context, options) =>
            createWhichIsNearerEnvironment(exports, context, () =>
                createPublicFrameArchive(context, exports, exports.memory, verifyTaskOutcome), options),
        createShapeFromMotionEnvironment: (context, options) =>
            createShapeFromMotionEnvironment(exports, context, () =>
                createPublicFrameArchive(context, exports, exports.memory, verifyTaskOutcome), options),
        createDamKeeperEnvironment: (context, options) =>
            createDamKeeperEnvironment(exports, context, () =>
                createPublicFrameArchive(context, exports, exports.memory, verifyTaskOutcome), options),
        createDispatchEnvironment: (context, options) =>
            createDispatchEnvironment(exports, context, () =>
                createPublicFrameArchive(context, exports, exports.memory, verifyTaskOutcome), options),
        createFirebreakEnvironment: (context, options) =>
            createFirebreakEnvironment(exports, context, () =>
                createPublicFrameArchive(context, exports, exports.memory, verifyTaskOutcome), options),
        createCrossroadsEnvironment: (context, options) =>
            createCrossroadsEnvironment(exports, context, () =>
                createPublicFrameArchive(context, exports, exports.memory, verifyTaskOutcome), options),
        createRailYardEnvironment: (context, options) =>
            createRailYardEnvironment(exports, context, () =>
                createPublicFrameArchive(context, exports, exports.memory, verifyTaskOutcome), options),
        createAirTrafficEnvironment: (context, options) =>
            createAirTrafficEnvironment(exports, context, () =>
                createPublicFrameArchive(context, exports, exports.memory, verifyTaskOutcome), options),
        createEscortEnvironment: (context, options) =>
            createEscortEnvironment(exports, context, () =>
                createPublicFrameArchive(context, exports, exports.memory, verifyTaskOutcome), options),
        createSokobanLiveEnvironment: (context, options) =>
            createSokobanLiveEnvironment(exports, context, () =>
                createPublicFrameArchive(context, exports, exports.memory, verifyTaskOutcome), options),
        createKitchenEnvironment: (context, options) =>
            createKitchenEnvironment(exports, context, () =>
                createPublicFrameArchive(context, exports, exports.memory, verifyTaskOutcome), options),
        createCraneEnvironment: (context, options) =>
            createCraneEnvironment(exports, context, () =>
                createPublicFrameArchive(context, exports, exports.memory, verifyTaskOutcome), options),
        createFerryEnvironment: (context, options) =>
            createFerryEnvironment(exports, context, () =>
                createPublicFrameArchive(context, exports, exports.memory, verifyTaskOutcome), options),
        createDockingEnvironment: (context, options) =>
            createDockingEnvironment(exports, context, () =>
                createPublicFrameArchive(context, exports, exports.memory, verifyTaskOutcome), options),
        createUnicycleEnvironment: (context, options) =>
            createUnicycleEnvironment(exports, context, () =>
                createPublicFrameArchive(context, exports, exports.memory, verifyTaskOutcome), options),
        createRoverEnvironment: (context, options) =>
            createRoverEnvironment(exports, context, () =>
                createPublicFrameArchive(context, exports, exports.memory, verifyTaskOutcome), options),
        createMorningRoundEnvironment: (context, options) =>
            createMorningRoundEnvironment(exports, context, () =>
                createPublicFrameArchive(context, exports, exports.memory, verifyTaskOutcome), options),
        createHeavierEnvironment: (context, options) =>
            createHeavierEnvironment(exports, context, () =>
                createPublicFrameArchive(context, exports, exports.memory, verifyTaskOutcome), options),
        createCrazyCogEnvironment: (context, options) =>
            createCrazyCogEnvironment(exports, context, () =>
                createPublicFrameArchive(context, exports, exports.memory, verifyTaskOutcome), options),
        createPotterEnvironment: (context, options) =>
            createPotterEnvironment(exports, context, () =>
                createPublicFrameArchive(context, exports, exports.memory, verifyTaskOutcome), options),
        createConductorEnvironment: (context, options) =>
            createConductorEnvironment(exports, context, () =>
                createPublicFrameArchive(context, exports, exports.memory, verifyTaskOutcome), options),
        createTightropeEnvironment: (context, options) =>
            createTightropeEnvironment(exports, context, () =>
                createPublicFrameArchive(context, exports, exports.memory, verifyTaskOutcome), options),
        createSignPainterEnvironment: (context, options) =>
            createSignPainterEnvironment(exports, context, () =>
                createPublicFrameArchive(context, exports, exports.memory, verifyTaskOutcome), options),
        createBartenderEnvironment: (context, options) =>
            createBartenderEnvironment(exports, context, () =>
                createPublicFrameArchive(context, exports, exports.memory, verifyTaskOutcome), options),
        createLockPickEnvironment: (context, options) =>
            createLockPickEnvironment(exports, context, () =>
                createPublicFrameArchive(context, exports, exports.memory, verifyTaskOutcome), options),
        createAirHockeyEnvironment: (context, options) =>
            createAirHockeyEnvironment(exports, context, () =>
                createPublicFrameArchive(context, exports, exports.memory, verifyTaskOutcome), options),
        createSemaphoreEnvironment: (context, options) =>
            createSemaphoreEnvironment(exports, context, () =>
                createPublicFrameArchive(context, exports, exports.memory, verifyTaskOutcome), options),
        createShadowPuppetsEnvironment: (context, options) =>
            createShadowPuppetsEnvironment(exports, context, () =>
                createPublicFrameArchive(context, exports, exports.memory, verifyTaskOutcome), options),
        createNightWatchEnvironment: (context, options) =>
            createNightWatchEnvironment(exports, context, () =>
                createPublicFrameArchive(context, exports, exports.memory, verifyTaskOutcome), options),
        createKerbsideEnvironment: (context, options) =>
            createKerbsideEnvironment(exports, context, () =>
                createPublicFrameArchive(context, exports, exports.memory, verifyTaskOutcome), options),
        createSteadicamEnvironment: (context, options) =>
            createSteadicamEnvironment(exports, context, () =>
                createPublicFrameArchive(context, exports, exports.memory, verifyTaskOutcome), options),
        createFreeKickEnvironment: (context, options) =>
            createFreeKickEnvironment(exports, context, () =>
                createPublicFrameArchive(context, exports, exports.memory, verifyTaskOutcome), options),
        createByEarEnvironment: (context, options) =>
            createByEarEnvironment(exports, context, () =>
                createPublicFrameArchive(context, exports, exports.memory, verifyTaskOutcome), options),
        createPianoTunerEnvironment: (context, options) =>
            createPianoTunerEnvironment(exports, context, () =>
                createPublicFrameArchive(context, exports, exports.memory, verifyTaskOutcome), options),
        createCricketHuntEnvironment: (context, options) =>
            createCricketHuntEnvironment(exports, context, () =>
                createPublicFrameArchive(context, exports, exports.memory, verifyTaskOutcome), options),
        createClawMachineEnvironment: (context, options) =>
            createClawMachineEnvironment(exports, context, () =>
                createPublicFrameArchive(context, exports, exports.memory, verifyTaskOutcome), options),
        createGloveEnvironment: (context, options) =>
            createGloveEnvironment(exports, context, () =>
                createPublicFrameArchive(context, exports, exports.memory, verifyTaskOutcome), options),
        createCipherAbyssEnvironment: (context, options) =>
            createCipherAbyssEnvironment(exports, context, () =>
                createPublicFrameArchive(context, exports, exports.memory, verifyTaskOutcome), options),
        createFullStopEnvironment: (context, options) =>
            createFullStopEnvironment(exports, context, () =>
                createPublicFrameArchive(context, exports, exports.memory, verifyTaskOutcome), options),
        createMissingWordEnvironment: (context, options) =>
            createMissingWordEnvironment(exports, context, () =>
                createPublicFrameArchive(context, exports, exports.memory, verifyTaskOutcome), options),
        createProofreaderEnvironment: (context, options) =>
            createProofreaderEnvironment(exports, context, () =>
                createPublicFrameArchive(context, exports, exports.memory, verifyTaskOutcome), options),
        createFiguresOfSpeechEnvironment: (context, options) =>
            createFiguresOfSpeechEnvironment(exports, context, () =>
                createPublicFrameArchive(context, exports, exports.memory, verifyTaskOutcome), options),
        createBetweenTheLinesEnvironment: (context, options) =>
            createBetweenTheLinesEnvironment(exports, context, () =>
                createPublicFrameArchive(context, exports, exports.memory, verifyTaskOutcome), options),
        createSecondThoughtsEnvironment: (context, options) =>
            createSecondThoughtsEnvironment(exports, context, () =>
                createPublicFrameArchive(context, exports, exports.memory, verifyTaskOutcome), options),
        createBadArgumentEnvironment: (context, options) =>
            createBadArgumentEnvironment(exports, context, () =>
                createPublicFrameArchive(context, exports, exports.memory, verifyTaskOutcome), options),
        createSocialSenseEnvironment: (context, options) =>
            createSocialSenseEnvironment(exports, context, () =>
                createPublicFrameArchive(context, exports, exports.memory, verifyTaskOutcome), options),
        createWhichFeelingEnvironment: (context, options) =>
            createWhichFeelingEnvironment(exports, context, () =>
                createPublicFrameArchive(context, exports, exports.memory, verifyTaskOutcome), options),
        createHowStronglyEnvironment: (context, options) =>
            createHowStronglyEnvironment(exports, context, () =>
                createPublicFrameArchive(context, exports, exports.memory, verifyTaskOutcome), options),
        createReadingPeopleEnvironment: (context, options) =>
            createReadingPeopleEnvironment(exports, context, () =>
                createPublicFrameArchive(context, exports, exports.memory, verifyTaskOutcome), options),
        createWhyTheyFeelEnvironment: (context, options) =>
            createWhyTheyFeelEnvironment(exports, context, () =>
                createPublicFrameArchive(context, exports, exports.memory, verifyTaskOutcome), options),
        createToneOfVoiceEnvironment: (context, options) =>
            createToneOfVoiceEnvironment(exports, context, () =>
                createPublicFrameArchive(context, exports, exports.memory, verifyTaskOutcome), options),
        createBrowserEnvironment: (context, options) =>
            createBrowserEnvironment(exports, context, () =>
                createPublicFrameArchive(context, exports, exports.memory, verifyTaskOutcome), options),
        createSpreadsheetEnvironment: (context, options) =>
            createSpreadsheetEnvironment(exports, context, () =>
                createPublicFrameArchive(context, exports, exports.memory, verifyTaskOutcome), options),
        createErrandsEnvironment: (context, options) =>
            createErrandsEnvironment(exports, context, () =>
                createPublicFrameArchive(context, exports, exports.memory, verifyTaskOutcome), options),
        createManualEnvironment: (context, options) =>
            createManualEnvironment(exports, context, () =>
                createPublicFrameArchive(context, exports, exports.memory, verifyTaskOutcome), options),
        createFormsEnvironment: (context, options) =>
            createFormsEnvironment(exports, context, () =>
                createPublicFrameArchive(context, exports, exports.memory, verifyTaskOutcome), options),
        createDesktopEnvironment: (context, options) =>
            createDesktopEnvironment(exports, context, () =>
                createPublicFrameArchive(context, exports, exports.memory, verifyTaskOutcome), options),
        createEmotionEnvironment: (context, options) =>
            createEmotionEnvironment(exports, context, () =>
                createPublicFrameArchive(context, exports, exports.memory, verifyTaskOutcome), options),
        createCookieThiefEnvironment: (context, options) =>
            createCookieThiefEnvironment(exports, context, () =>
                createPublicFrameArchive(context, exports, exports.memory, verifyTaskOutcome), options),
    };
}
