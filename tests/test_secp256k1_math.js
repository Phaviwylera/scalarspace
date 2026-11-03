'use strict';

const assert = require('node:assert/strict');
const curve = require('../secp256k1_math.js');

const twoG = [
  BigInt('0xc6047f9441ed7d6d3045406e95c07cd85c778e4b8cef3ca7abac09b95c709ee5'),
  BigInt('0x1ae168fea63dc339a3c58419466ceaeef7f632653266d0e1236431a950cfe52a'),
];

assert.deepEqual(curve.scalarMultiply(1n), curve.G);
assert.deepEqual(curve.scalarMultiply(2n), twoG);
assert.deepEqual(curve.scalarMultiply(curve.N - 1n), [curve.G[0], curve.P - curve.G[1]]);
assert.equal(curve.isOnCurve(curve.G), true);
assert.equal(curve.isOnCurve(twoG), true);
assert.equal(curve.isOnCurve([1n, 1n]), false);
assert.equal(curve.isOnCurve(null), true);
assert.equal(
  curve.encodePublicPoint(curve.G),
  '0279be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798',
);
assert.equal(
  curve.encodePublicPoint(twoG),
  '02c6047f9441ed7d6d3045406e95c07cd85c778e4b8cef3ca7abac09b95c709ee5',
);
assert.equal(
  curve.encodePublicPoint(curve.G, false),
  '0479be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798' +
    '483ada7726a3c4655da4fbfc0e1108a8fd17b448a68554199c47d08ffb10d4b8',
);
assert.throws(() => curve.scalarMultiply(0n), RangeError);
assert.throws(() => curve.scalarMultiply(curve.N), RangeError);
assert.throws(() => curve.scalarMultiply(-1n), RangeError);
assert.throws(() => curve.scalarMultiply(1), TypeError);
assert.throws(() => curve.encodePublicPoint(null), TypeError);

console.log('secp256k1 math tests passed');
