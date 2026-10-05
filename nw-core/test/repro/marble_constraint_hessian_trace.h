// Diagnostic-only MuJoCo 3.12 recorder; never included in production builds.
// Captures only fully written active cone Hessians. It never reads incoming H
// or unused storage outside dim*dim, and performs no floating-point arithmetic.
#ifndef MARBLE_CONSTRAINT_HESSIAN_TRACE_H_
#define MARBLE_CONSTRAINT_HESSIAN_TRACE_H_

#define MARBLE_CONE_HESSIAN_TRACE_CAPACITY 300000
static mjtNum marble_cone_hessian_trace[MARBLE_CONE_HESSIAN_TRACE_CAPACITY];
static int marble_cone_hessian_trace_size;
static int marble_cone_hessian_trace_enabled;
static int marble_cone_hessian_trace_overflow;
static int marble_cone_hessian_trace_calls;

static void marble_cone_hessian_trace_begin(void) {
  marble_cone_hessian_trace_size = 0;
  marble_cone_hessian_trace_overflow = 0;
  marble_cone_hessian_trace_calls = 0;
  marble_cone_hessian_trace_enabled = 1;
}

static void marble_cone_hessian_trace_end(void) {
  marble_cone_hessian_trace_enabled = 0;
}

static int marble_cone_hessian_trace_call(void) {
  return marble_cone_hessian_trace_enabled ? marble_cone_hessian_trace_calls++ : -1;
}

MJAPI int mj_constraint_hessian_trace_size(void) {
  return marble_cone_hessian_trace_size;
}

MJAPI int mj_constraint_hessian_trace_overflow(void) {
  return marble_cone_hessian_trace_overflow;
}

MJAPI int mj_constraint_hessian_trace_calls(void) {
  return marble_cone_hessian_trace_calls;
}

MJAPI void mj_constraint_hessian_trace_copy(mjtNum* output) {
  if (output && marble_cone_hessian_trace_size) {
    memcpy(output, marble_cone_hessian_trace,
           (size_t)marble_cone_hessian_trace_size * sizeof(mjtNum));
  }
}

#if defined(__GNUC__) || defined(__clang__)
__attribute__((noinline))
#endif
static void marble_cone_hessian_trace_record(
    int call, int row, int nefc, int dim, int contact_id, int has_cost,
    mjtNum mu, mjtNum N, mjtNum T, mjtNum Dm, mjtNum NmT,
    const mjtNum* friction, const mjtNum* jar, const mjtNum* D,
    const mjtNum* R, const mjtNum* force, const mjtNum* H) {
  if (!marble_cone_hessian_trace_enabled || call < 0) return;
  const int width = 17 + 4*dim + dim*dim;
  if ((dim != 3 && dim != 4 && dim != 6) || row < 0 ||
      row + dim > nefc ||
      marble_cone_hessian_trace_size + width > MARBLE_CONE_HESSIAN_TRACE_CAPACITY) {
    marble_cone_hessian_trace_overflow = 1;
    marble_cone_hessian_trace_enabled = 0;
    return;
  }
  mjtNum* out = marble_cone_hessian_trace + marble_cone_hessian_trace_size;
  // Schema 1. Call ordinal counts every impl entry, including non-cone calls.
  out[0] = 1;
  out[1] = call;
  out[2] = row;
  out[3] = nefc;
  out[4] = dim;
  out[5] = contact_id;
  out[6] = has_cost;
  out[7] = mu;
  out[8] = N;
  out[9] = T;
  out[10] = Dm;
  out[11] = NmT;
  int cursor = 12;
#define MARBLE_HESSIAN_COPY(values, count) do { \
    memcpy(out + cursor, values, (size_t)(count)*sizeof(mjtNum)); \
    cursor += count; \
  } while (0)
  MARBLE_HESSIAN_COPY(friction, 5);
  MARBLE_HESSIAN_COPY(jar, dim);
  MARBLE_HESSIAN_COPY(D, dim);
  MARBLE_HESSIAN_COPY(R, dim);
  MARBLE_HESSIAN_COPY(force, dim);
  MARBLE_HESSIAN_COPY(H, dim*dim);
#undef MARBLE_HESSIAN_COPY
  marble_cone_hessian_trace_size += width;
}

#endif  // MARBLE_CONSTRAINT_HESSIAN_TRACE_H_
