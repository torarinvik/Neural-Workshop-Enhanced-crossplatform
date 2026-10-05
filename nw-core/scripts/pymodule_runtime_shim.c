/* The runtime object stand-in for the pymodule link.
 *
 * pymodule_exports.elisa includes the runtime's Elisa SOURCE (it must: the
 * stage1 backend only lowers the sview builtins when it can see their bodies),
 * so the module object already defines the whole runtime. Linking the prebuilt
 * elisacore_runtime.o on top of that gives 130 duplicate symbols, so
 * build_pymodule.sh points ELISA_RUNTIME_OBJ here instead.
 *
 * What remains are the optional native-callback and varargs hooks, which the
 * runtime declares but expects an executable host to define. These are the
 * documented fallbacks -- return the caller's fallback value, or do nothing --
 * copied from the shim elisac_stage1.sh itself compiles when it auto-builds a
 * runtime object. Without them the extension links (macOS uses
 * -undefined dynamic_lookup) and fails at import instead.
 */
#include <stddef.h>
#include <stdint.h>

/* Newer Elisa runtimes call the optional allocation-profiler ABI even when
 * profiling is disabled. Keep the native pymodule link self-contained: the
 * production shell does not install a profiler, so negotiation declines the
 * ABI and event delivery becomes a no-op. */
uint32_t elisa_profile_allocation_negotiate(uint32_t requested_version) {
    (void)requested_version;
    return 0;
}
uint32_t elisa_profile_region_layout_negotiate(uint32_t requested_version) {
    (void)requested_version;
    return 0;
}
void elisa_profile_region_layout_v1(uintptr_t arena, size_t region,
                                    uintptr_t header, uintptr_t data,
                                    size_t capacity) {
    (void)arena;
    (void)region;
    (void)header;
    (void)data;
    (void)capacity;
}
void elisa_profile_allocation_event_v1(uint32_t kind, uintptr_t address,
                                       size_t size, uintptr_t old_address,
                                       size_t old_size, uintptr_t arena,
                                       size_t region) {
    (void)kind;
    (void)address;
    (void)size;
    (void)old_address;
    (void)old_size;
    (void)arena;
    (void)region;
}

void *elisa_native_callback_ptr(uint8_t *name) {
    (void)name;
    return NULL;
}
uint32_t elisa_native_callback_call_u32_voidp(uint8_t *name, void *arg, uint32_t fallback) {
    (void)name; (void)arg; return fallback;
}
int32_t elisa_native_callback_call_i32_voidp(uint8_t *name, void *arg, int32_t fallback) {
    (void)name; (void)arg; return fallback;
}
uintptr_t elisa_native_callback_call_usize_voidp(uint8_t *name, void *arg, uintptr_t fallback) {
    (void)name; (void)arg; return fallback;
}
intptr_t elisa_native_callback_call_isize_voidp(uint8_t *name, void *arg, intptr_t fallback) {
    (void)name; (void)arg; return fallback;
}
uint32_t elisa_native_callback_spawn_join_u32_voidp(uint8_t *name, void *arg, uint32_t fallback) {
    (void)name; (void)arg; return fallback;
}
void *elisa_native_callback_context_new_u32_voidp(uint8_t *name, void *arg, uint32_t fallback) {
    (void)name; (void)arg; (void)fallback; return NULL;
}
void *elisa_native_callback_context_entry_u32_voidp(void) {
    return NULL;
}
int32_t elisa_native_callback_context_start_u32_voidp(void *ctx, uintptr_t *thread) {
    (void)ctx; (void)thread; return -1;
}
uint32_t elisa_native_callback_context_join_u32_voidp(uintptr_t handle, void *ctx, uint32_t fallback) {
    (void)handle; (void)ctx; return fallback;
}
uint32_t elisa_native_callback_context_spawn_join_u32_voidp(void *ctx, uint32_t fallback) {
    (void)ctx; return fallback;
}
uint32_t elisa_native_callback_context_result_u32(void *ctx, uint32_t fallback) {
    (void)ctx; return fallback;
}
void elisa_native_callback_context_free(void *ctx) {
    (void)ctx;
}
void va_copy(void *destination, void *source) {
    (void)destination; (void)source;
}
void va_end(void *argument) {
    (void)argument;
}
