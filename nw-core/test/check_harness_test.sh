#!/usr/bin/env bash
# Exercise check.sh lock/scratch behavior against isolated build directories.
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
# Fail early if a fixture has regressed to the deleted historical compiler
# worktree. The compiler environment is the source of truth for the canonical
# Elisa-core location, and the include audit is intentionally independent of
# any particular compiler binary.
# shellcheck source=/dev/null
source "$ROOT/scripts/env.sh"
[[ -f "$ELISA_CORE/compiler/runtime/elisacore_std/elisacore_runtime.elisa" ]] || {
    echo "check_harness_test: canonical Elisa-core runtime is missing: $ELISA_CORE" >&2
    exit 1
}
if rg -q --glob '*.elisa' 'worktrees/elisa-core-nw/compiler/runtime/elisacore_std' \
    "$ROOT/src" "$ROOT/test"; then
    echo "check_harness_test: stale Elisa-core worktree include remains" >&2
    exit 1
fi
TEST_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/nw-check-harness.XXXXXX")"
keeper_pid=""
waiter_pid=""

cleanup() {
    if [[ -n "$waiter_pid" ]] && kill -0 "$waiter_pid" 2>/dev/null; then
        kill -TERM "$waiter_pid" 2>/dev/null || true
        wait "$waiter_pid" 2>/dev/null || true
    fi
    if [[ -n "$keeper_pid" ]] && kill -0 "$keeper_pid" 2>/dev/null; then
        kill -TERM "$keeper_pid" 2>/dev/null || true
        wait "$keeper_pid" 2>/dev/null || true
    fi
    rm -rf "$TEST_ROOT"
}
trap cleanup EXIT

process_start() {
    ps -p "$1" -o lstart= 2>/dev/null | sed 's/^[[:space:]]*//;s/[[:space:]]*$//'
}

run_pyset() {
    local build_dir="$1" log_file="$2" lock_path="${3:-$1/.check.lock}"
    NW_CHECK_BUILD_DIR="$build_dir" NW_CHECK_LOCK_PATH="$lock_path" SUITE=pyset \
        bash "$ROOT/scripts/check.sh" stage0 >"$log_file" 2>&1
}

assert_suite_passed() {
    local log_file="$1" expected_cases="$2"
    if ! rg -q "PASS: ${expected_cases} cases identical" "$log_file" ||
       ! rg -q 'All differential suites match the Python reference\.' "$log_file"; then
        echo "check_harness_test: expected ${expected_cases}-case run to pass: $log_file" >&2
        sed -n '1,120p' "$log_file" >&2
        return 1
    fi
}

# Recover an ownerless lock only after its directory has aged past the
# production threshold. The subsequent run must execute the requested suite.
ownerless_build="$TEST_ROOT/ownerless-build"
ownerless_lock="$ownerless_build/.check.lock"
mkdir -p "$ownerless_lock"
touch -t 200001010000 "$ownerless_lock"
run_pyset "$ownerless_build" "$TEST_ROOT/ownerless.log"
assert_suite_passed "$TEST_ROOT/ownerless.log" 1000
[[ ! -e "$ownerless_lock" ]] || {
    echo "check_harness_test: ownerless lock remained after recovery" >&2
    exit 1
}

# A live PID whose recorded start time differs is a reused/stale identity, not
# authority to keep the old lock. Recovery must not signal that live process.
stale_build="$TEST_ROOT/stale-build"
stale_lock="$stale_build/.check.lock"
mkdir -p "$stale_lock"
sleep 30 &
keeper_pid=$!
printf '%s\n%s\n%s\n' "$keeper_pid" "not-the-current-process-start" \
    "simulated-reused-pid" > "$stale_lock/owner"
run_pyset "$stale_build" "$TEST_ROOT/stale.log"
assert_suite_passed "$TEST_ROOT/stale.log" 1000
kill -0 "$keeper_pid" 2>/dev/null || {
    echo "check_harness_test: stale-lock recovery disturbed a live PID" >&2
    exit 1
}
[[ ! -e "$stale_lock" ]] || {
    echo "check_harness_test: stale lock remained after recovery" >&2
    exit 1
}
kill -TERM "$keeper_pid" 2>/dev/null || true
wait "$keeper_pid" 2>/dev/null || true
keeper_pid=""

# Interrupt a checker blocked behind a genuine live owner. It must terminate
# with signal-derived status, leave the other process's lock untouched, and
# never reach a suite or emit a false PASS.
wait_build="$TEST_ROOT/wait-build"
wait_lock="$wait_build/.check.lock"
mkdir -p "$wait_lock"
sleep 30 &
keeper_pid=$!
wait_start="$(process_start "$keeper_pid")"
[[ -n "$wait_start" ]] || {
    echo "check_harness_test: could not inspect live lock owner" >&2
    exit 1
}
wait_token="test-owner-$keeper_pid"
printf '%s\n%s\n%s\n' "$keeper_pid" "$wait_start" "$wait_token" > "$wait_lock/owner"
NW_CHECK_BUILD_DIR="$wait_build" NW_CHECK_LOCK_PATH="$wait_lock" SUITE=pyset \
    bash "$ROOT/scripts/check.sh" stage0 >"$TEST_ROOT/interrupted.log" 2>&1 &
waiter_pid=$!
sleep 0.2
kill -TERM "$waiter_pid" 2>/dev/null || true
wait_status=0
wait "$waiter_pid" 2>/dev/null || wait_status=$?
waiter_pid=""
[[ "$wait_status" -eq 143 ]] || {
    echo "check_harness_test: interrupted waiter exited $wait_status, expected 143" >&2
    exit 1
}
[[ -f "$wait_lock/owner" ]] &&
    [[ "$(sed -n '3p' "$wait_lock/owner")" == "$wait_token" ]] || {
    echo "check_harness_test: interrupted waiter removed or changed the live owner's lock" >&2
    exit 1
}
if rg -q '== stage|PASS:|All differential suites match' "$TEST_ROOT/interrupted.log"; then
    echo "check_harness_test: interrupted waiter reached a suite or printed a false PASS" >&2
    sed -n '1,80p' "$TEST_ROOT/interrupted.log" >&2
    exit 1
fi
if find "$wait_build" -maxdepth 1 -type d -name 'check.*' -print -quit | rg -q .; then
    echo "check_harness_test: waiter created a run directory before acquiring the lock" >&2
    exit 1
fi
kill -TERM "$keeper_pid" 2>/dev/null || true
wait "$keeper_pid" 2>/dev/null || true
keeper_pid=""

# Two simultaneous invocations share neither scratch outputs nor oracle state;
# both must finish with counted passes and distinct structured result paths.
concurrent_a_build="$TEST_ROOT/concurrent-build-a"
concurrent_b_build="$TEST_ROOT/concurrent-build-b"
concurrent_tmp="$TEST_ROOT/concurrent-tmp"
mkdir -p "$concurrent_tmp"
concurrent_lock="$concurrent_tmp/nw-core-check-${UID}.lock"
TMPDIR="$concurrent_tmp" NW_CHECK_BUILD_DIR="$concurrent_a_build" SUITE=expressions \
    bash "$ROOT/scripts/check.sh" stage0 >"$TEST_ROOT/concurrent-a.log" 2>&1 &
first_pid=$!
TMPDIR="$concurrent_tmp" NW_CHECK_BUILD_DIR="$concurrent_b_build" SUITE=expressions \
    bash "$ROOT/scripts/check.sh" stage0 >"$TEST_ROOT/concurrent-b.log" 2>&1 &
second_pid=$!
first_status=0
second_status=0
wait "$first_pid" || first_status=$?
wait "$second_pid" || second_status=$?
[[ "$first_status" -eq 0 && "$second_status" -eq 0 ]] || {
    echo "check_harness_test: concurrent runs exited $first_status and $second_status" >&2
    sed -n '1,120p' "$TEST_ROOT/concurrent-a.log" >&2
    sed -n '1,120p' "$TEST_ROOT/concurrent-b.log" >&2
    exit 1
}
assert_suite_passed "$TEST_ROOT/concurrent-a.log" 342
assert_suite_passed "$TEST_ROOT/concurrent-b.log" 342
python3 -c 'import re,sys; logs=[open(p).read() for p in sys.argv[1:]]; paths=[re.search(r"result: (.+?); cases:", s).group(1) for s in logs]; assert len(paths)==2 and paths[0]!=paths[1], paths' \
    "$TEST_ROOT/concurrent-a.log" "$TEST_ROOT/concurrent-b.log"
[[ ! -e "$concurrent_lock" ]] || {
    echo "check_harness_test: concurrent run left a lock behind" >&2
    exit 1
}

echo "PASS: isolated check harness handles ownerless/stale locks, interruption, and concurrent runs"
