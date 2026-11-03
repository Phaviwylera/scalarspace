/*
 * Educational secp256k1 point arithmetic for Scalar Lab.
 * This module derives [k]G only when the caller already supplies k. It does
 * not search scalars, accept target points for inversion, or perform recovery.
 * Arithmetic is not constant-time and must not protect production secrets.
 */
(function (root, factory) {
  'use strict';
  const api = factory();
  if (typeof module === 'object' && module.exports) {
    module.exports = api;
  } else {
    root.ScalarLabCurve = api;
  }
})(typeof globalThis === 'object' ? globalThis : this, function () {
  'use strict';

  const P = BigInt('0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F');
  const N = BigInt('0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141');
  const G = Object.freeze([
    BigInt('0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798'),
    BigInt('0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8'),
  ]);
  const INFINITY = Object.freeze([0n, 1n, 0n]);

  function mod(value) {
    const result = value % P;
    return result < 0n ? result + P : result;
  }

  function modPow(base, exponent) {
    let result = 1n;
    let factor = mod(base);
    let power = exponent;
    while (power > 0n) {
      if (power & 1n) result = result * factor % P;
      factor = factor * factor % P;
      power >>= 1n;
    }
    return result;
  }

  function isOnCurve(point) {
    if (point === null) return true;
    if (!Array.isArray(point) || point.length !== 2) return false;
    const [x, y] = point;
    if (typeof x !== 'bigint' || typeof y !== 'bigint') return false;
    if (x < 0n || x >= P || y < 0n || y >= P) return false;
    return mod(y * y - (x * x * x + 7n)) === 0n;
  }

  function doubleJacobian(point) {
    const [x1, y1, z1] = point;
    if (z1 === 0n || y1 === 0n) return INFINITY;
    const yy = y1 * y1 % P;
    const yyyy = yy * yy % P;
    const s = 4n * x1 * yy % P;
    const m = 3n * x1 * x1 % P;
    const x3 = mod(m * m - 2n * s);
    const y3 = mod(m * (s - x3) - 8n * yyyy);
    const z3 = 2n * y1 * z1 % P;
    return [x3, y3, z3];
  }

  function addMixedJacobian(point, other) {
    const [x1, y1, z1] = point;
    const [x2, y2] = other;
    if (z1 === 0n) return [x2, y2, 1n];

    const z1z1 = z1 * z1 % P;
    const u2 = x2 * z1z1 % P;
    const s2 = y2 * z1 * z1z1 % P;
    const h = mod(u2 - x1);
    const r = mod(s2 - y1);
    if (h === 0n) return r === 0n ? doubleJacobian(point) : INFINITY;

    const hh = h * h % P;
    const i = 4n * hh % P;
    const j = h * i % P;
    const r2 = 2n * r % P;
    const v = x1 * i % P;
    const x3 = mod(r2 * r2 - j - 2n * v);
    const y3 = mod(r2 * (v - x3) - 2n * y1 * j);
    const z3 = mod((z1 + h) * (z1 + h) - z1z1 - hh);
    return [x3, y3, z3];
  }

  function toAffine(point) {
    const [x, y, z] = point;
    if (z === 0n) return null;
    const zInverse = modPow(z, P - 2n);
    const z2 = zInverse * zInverse % P;
    const z3 = z2 * zInverse % P;
    return [x * z2 % P, y * z3 % P];
  }

  function scalarMultiply(scalar) {
    if (typeof scalar !== 'bigint') {
      throw new TypeError('scalar must be a BigInt');
    }
    if (scalar < 1n || scalar >= N) {
      throw new RangeError('scalar must satisfy 1 <= k < n');
    }

    let result = INFINITY;
    for (const bit of scalar.toString(2)) {
      result = doubleJacobian(result);
      if (bit === '1') result = addMixedJacobian(result, G);
    }
    const point = toAffine(result);
    if (!isOnCurve(point)) throw new Error('internal curve arithmetic check failed');
    return point;
  }

  function encodePublicPoint(point, compressed = true) {
    if (point === null || !isOnCurve(point)) {
      throw new TypeError('point must be a finite point on secp256k1');
    }
    const [x, y] = point;
    const xHex = x.toString(16).padStart(64, '0');
    if (compressed) return `${y % 2n === 0n ? '02' : '03'}${xHex}`;
    return `04${xHex}${y.toString(16).padStart(64, '0')}`;
  }

  return Object.freeze({ P, N, G, isOnCurve, scalarMultiply, encodePublicPoint });
});
