// Two-coordinate norm following CPython 3.13's compensated vector_norm.
// Reference: https://github.com/python/cpython/blob/v3.13.12/Modules/mathmodule.c
// JS has no fused multiply-add: Dekker splitting recovers squared-product
// residuals after power-of-two scaling. This module does not alter rendering.
const exponentBuffer = new DataView(new ArrayBuffer(8));
const MIN_NORMAL = 2 ** -1022;

function squareParts(value) {
  const split = value * 134217729;
  const high = split - (split - value);
  const low = value - high;
  const product = value * value;
  const error = ((high * high - product) + 2 * high * low) + low * low;
  return [product, error];
}

export function pythonHypot2(x, y) {
  x = Math.abs(x);
  y = Math.abs(y);
  if (x === Infinity || y === Infinity) return Infinity;
  if (Number.isNaN(x) || Number.isNaN(y)) return NaN;
  const maximum = Math.max(x, y);
  if (maximum === 0) return 0;
  exponentBuffer.setFloat64(0, maximum, false);
  let exponent = ((exponentBuffer.getUint32(0, false) >>> 20) & 2047) - 1022;
  if (maximum < MIN_NORMAL) {
    exponentBuffer.setFloat64(0, maximum / MIN_NORMAL, false);
    exponent = ((exponentBuffer.getUint32(0, false) >>> 20) & 2047) - 2044;
  }
  if (exponent < -1023) {
    return MIN_NORMAL * pythonHypot2(x / MIN_NORMAL, y / MIN_NORMAL);
  }
  const scale = 2 ** -exponent;
  let total = 1;
  let productErrors = 0;
  let sumErrors = 0;
  for (const coordinate of [x, y]) {
    const [product, error] = squareParts(coordinate * scale);
    const next = total + product;
    sumErrors += (total - next) + product;
    productErrors += error;
    total = next;
  }
  let root = Math.sqrt(total - 1 + (productErrors + sumErrors));
  const [square, squareError] = squareParts(root);
  const next = total - square;
  sumErrors += (total - next) - square;
  productErrors -= squareError;
  const remainder = next - 1 + (productErrors + sumErrors);
  root += remainder / (2 * root);
  return root / scale;
}
