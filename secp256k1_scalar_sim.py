#!/usr/bin/env python3
"""secp256k1 scalar-space research simulator (Python standard library only).

Models the exact valid scalar domain, performs real secp256k1 point arithmetic,
creates/verifies balanced interval manifests, and reports interval-level
coverage metadata. It deliberately does not enumerate candidates, search for
wallets, match addresses, or recover private keys.

Examples:
  python secp256k1_scalar_sim.py info
  python secp256k1_scalar_sim.py verify
  python secp256k1_scalar_sim.py visualize --parts 32 --width 64
  python secp256k1_scalar_sim.py plan --parts 32 --workers 4 --output plan.json
  python secp256k1_scalar_sim.py check-manifest --manifest plan.json
  python secp256k1_scalar_sim.py coverage --manifest plan.json --completed 0,1,2
  python secp256k1_scalar_sim.py locate --parts 32 --scalar 0x2
  python secp256k1_scalar_sim.py multiply --scalar 0x2
"""
from __future__ import annotations

import argparse
import hashlib
import json
import secrets
import string
import sys
import tempfile
from dataclasses import dataclass
from decimal import Decimal, getcontext
from pathlib import Path
from typing import Iterable, Optional, Tuple

# SEC 2 secp256k1 domain parameters.
P = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
A = 0
B = 7
N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
GX = 0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798
GY = 0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8
G = (GX, GY)
MANIFEST_VERSION = 1
CURVE_ID = "secp256k1"

Jacobian = Tuple[int, int, int]
Affine = Optional[Tuple[int, int]]
_INFINITY: Jacobian = (0, 1, 0)


def _require_int(value: int, name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")


def is_on_curve(point: Affine) -> bool:
    """Return whether an affine point satisfies y^2 = x^3 + 7 (mod p)."""
    if point is None:
        return True
    x, y = point
    if not (0 <= x < P and 0 <= y < P):
        return False
    return (y * y - (x * x * x + B)) % P == 0


def _jacobian_double(point: Jacobian) -> Jacobian:
    x1, y1, z1 = point
    if z1 == 0 or y1 == 0:
        return _INFINITY
    yy = y1 * y1 % P
    yyyy = yy * yy % P
    s = 4 * x1 * yy % P
    m = 3 * x1 * x1 % P
    x3 = (m * m - 2 * s) % P
    y3 = (m * (s - x3) - 8 * yyyy) % P
    z3 = 2 * y1 * z1 % P
    return x3, y3, z3


def _jacobian_add_mixed(point: Jacobian, other: Tuple[int, int]) -> Jacobian:
    x1, y1, z1 = point
    x2, y2 = other
    if z1 == 0:
        return x2, y2, 1
    z1z1 = z1 * z1 % P
    u2 = x2 * z1z1 % P
    s2 = y2 * z1 * z1z1 % P
    h = (u2 - x1) % P
    r = (s2 - y1) % P
    if h == 0:
        return _jacobian_double(point) if r == 0 else _INFINITY
    hh = h * h % P
    i = 4 * hh % P
    j = h * i % P
    r2 = 2 * r % P
    v = x1 * i % P
    x3 = (r2 * r2 - j - 2 * v) % P
    y3 = (r2 * (v - x3) - 2 * y1 * j) % P
    z3 = ((z1 + h) * (z1 + h) - z1z1 - hh) % P
    return x3, y3, z3


def _to_affine(point: Jacobian) -> Affine:
    x, y, z = point
    if z == 0:
        return None
    z_inv = pow(z, P - 2, P)
    z2 = z_inv * z_inv % P
    z3 = z2 * z_inv % P
    return x * z2 % P, y * z3 % P


def scalar_multiply(scalar: int, point: Tuple[int, int] = G) -> Affine:
    """Compute scalar*point with exact integer arithmetic (not constant-time)."""
    _require_int(scalar, "scalar")
    if scalar < 0:
        raise ValueError("scalar must be non-negative")
    if not is_on_curve(point) or point is None:
        raise ValueError("point must be a finite point on secp256k1")
    k = scalar % N
    result = _INFINITY
    for bit in bin(k)[2:]:
        result = _jacobian_double(result)
        if bit == "1":
            result = _jacobian_add_mixed(result, point)
    return _to_affine(result)


def encode_public_point(point: Affine, compressed: bool = True) -> str:
    """Serialize a finite affine point in SEC1 format (hex, no 0x prefix)."""
    if point is None or not is_on_curve(point):
        raise ValueError("cannot encode infinity or an invalid curve point")
    x, y = point
    xb = x.to_bytes(32, "big")
    if compressed:
        return ((bytes([2]) if y % 2 == 0 else bytes([3])) + xb).hex()
    return (bytes([4]) + xb + y.to_bytes(32, "big")).hex()


def parse_scalar(value: str) -> int:
    try:
        return int(value, 16 if value.lower().startswith("0x") else 10)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("scalar must be decimal or 0x-prefixed hexadecimal") from exc


@dataclass(frozen=True)
class ScalarInterval:
    """Half-open interval [start, stop) of valid secp256k1 scalars."""
    index: int
    start: int
    stop: int

    @property
    def count(self) -> int:
        return self.stop - self.start

    def as_dict(self, worker: Optional[int] = None) -> dict:
        data = {
            "index": self.index,
            "start_decimal": str(self.start),
            "stop_exclusive_decimal": str(self.stop),
            "start_hex": hex(self.start),
            "stop_exclusive_hex": hex(self.stop),
            "count_decimal": str(self.count),
        }
        if worker is not None:
            data["worker_id"] = worker
        return data


class Secp256k1ScalarSpace:
    """The exact valid private-scalar set {1, 2, ..., N-1}."""
    MIN_SCALAR = 1
    STOP_SCALAR = N

    @property
    def size(self) -> int:
        return N - 1

    def contains(self, scalar: int) -> bool:
        return isinstance(scalar, int) and not isinstance(scalar, bool) and 1 <= scalar < N

    def random_scalar(self) -> int:
        """Uniformly sample one valid scalar. For demonstration only."""
        return secrets.randbelow(N - 1) + 1

    def interval(self, index: int, parts: int) -> ScalarInterval:
        _require_int(index, "index")
        _require_int(parts, "parts")
        if parts <= 0 or parts > self.size:
            raise ValueError("parts must be between 1 and n-1")
        if not 0 <= index < parts:
            raise ValueError("index must satisfy 0 <= index < parts")
        q, r = divmod(self.size, parts)
        start = 1 + index * q + min(index, r)
        length = q + (1 if index < r else 0)
        return ScalarInterval(index, start, start + length)

    def partitions(self, parts: int) -> Iterable[ScalarInterval]:
        _require_int(parts, "parts")
        if parts <= 0 or parts > self.size:
            raise ValueError("parts must be between 1 and n-1")
        for index in range(parts):
            yield self.interval(index, parts)

    def locate(self, scalar: int, parts: int) -> int:
        """Return the balanced-partition index containing scalar; no scanning."""
        if not self.contains(scalar):
            raise ValueError("scalar must satisfy 1 <= k < n")
        _require_int(parts, "parts")
        if parts <= 0 or parts > self.size:
            raise ValueError("parts must be between 1 and n-1")
        q, r = divmod(self.size, parts)
        offset = scalar - 1
        larger_region = r * (q + 1)
        if offset < larger_region:
            return offset // (q + 1)
        return r + (offset - larger_region) // q

    def verify_partition(self, parts: int) -> bool:
        chunks = list(self.partitions(parts))
        if not chunks or chunks[0].start != 1 or chunks[-1].stop != N:
            return False
        return (
            all(a.stop == b.start for a, b in zip(chunks, chunks[1:]))
            and sum(c.count for c in chunks) == self.size
            and max(c.count for c in chunks) - min(c.count for c in chunks) <= 1
        )


def _canonical_json(data: dict) -> bytes:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def _manifest_payload(parts: int, workers: int) -> dict:
    if workers <= 0 or workers > parts:
        raise ValueError("workers must be between 1 and parts")
    space = Secp256k1ScalarSpace()
    assignments = []
    for interval in space.partitions(parts):
        assignments.append(interval.as_dict(worker=interval.index % workers))
    return {
        "manifest_version": MANIFEST_VERSION,
        "curve": CURVE_ID,
        "domain": {"start_inclusive": "1", "stop_exclusive": str(N), "notation": "[1, n)"},
        "parts": parts,
        "workers": workers,
        "assignment_policy": "round_robin_partition_index_mod_worker_count",
        "purpose": "interval bookkeeping only; no candidate enumeration or key search",
        "partitions": assignments,
    }


def create_manifest(parts: int, workers: int) -> dict:
    payload = _manifest_payload(parts, workers)
    payload["sha256"] = hashlib.sha256(_canonical_json(payload)).hexdigest()
    return payload


def validate_manifest(data: dict) -> Tuple[bool, str]:
    if not isinstance(data, dict):
        return False, "manifest root must be a JSON object"
    supplied_hash = data.get("sha256")
    if not isinstance(supplied_hash, str):
        return False, "missing manifest sha256"
    payload = {k: v for k, v in data.items() if k != "sha256"}
    expected_hash = hashlib.sha256(_canonical_json(payload)).hexdigest()
    if not secrets.compare_digest(supplied_hash, expected_hash):
        return False, "manifest SHA-256 checksum mismatch"
    try:
        parts = data["parts"]
        workers = data["workers"]
        expected = create_manifest(parts, workers)
    except (KeyError, TypeError, ValueError) as exc:
        return False, f"invalid manifest parameters: {exc}"
    # Compare canonical structures, including exact expected intervals/worker IDs.
    if _canonical_json(data) != _canonical_json(expected):
        return False, "manifest metadata or interval assignments do not match the canonical plan"
    return True, "manifest checksum and exact interval plan are valid"


def write_manifest(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(data, indent=2, sort_keys=True) + "\n"
    # Atomic replace prevents leaving a partial JSON file on interruption.
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as tmp:
        tmp.write(content)
        temp_name = tmp.name
    Path(temp_name).replace(path)


def coverage_report(manifest: dict, completed_indices: Iterable[int]) -> dict:
    valid, reason = validate_manifest(manifest)
    if not valid:
        raise ValueError(f"refusing invalid manifest: {reason}")
    parts = manifest["parts"]
    completed = sorted(set(completed_indices))
    if any(isinstance(i, bool) or not isinstance(i, int) or i < 0 or i >= parts for i in completed):
        raise ValueError("completed partition indexes must be integers in [0, parts)")
    intervals = [manifest["partitions"][i] for i in completed]
    covered = sum(int(row["count_decimal"]) for row in intervals)
    total = N - 1
    getcontext().prec = 40
    percent = (Decimal(covered) * Decimal(100) / Decimal(total)) if total else Decimal(0)
    # Completed partition IDs are disjoint by manifest construction.
    completed_set = set(completed)
    remaining = [i for i in range(parts) if i not in completed_set]
    return {
        "metric": "intervals marked complete; does not measure candidate computations",
        "completed_partition_indexes": completed,
        "completed_partition_count": len(completed),
        "total_partition_count": parts,
        "covered_scalar_count_decimal": str(covered),
        "total_valid_scalar_count_decimal": str(total),
        "coverage_percent": format(percent, ".24f"),
        "remaining_partition_indexes": remaining,
        "remaining_partition_count": len(remaining),
        "complete": len(completed) == parts,
    }



def exact_analysis(parts: int = 128, workers: int = 8, bins: int = 16) -> dict:
    """Return exact interval/bin/worker counts without enumerating scalar values."""
    for value, name, upper in ((parts, "parts", 10000), (workers, "workers", 128), (bins, "bins", 256)):
        _require_int(value, name)
        if not 1 <= value <= upper:
            raise ValueError(f"{name} must be between 1 and {upper}")
    if workers > parts:
        raise ValueError("workers must not exceed parts")

    space = Secp256k1ScalarSpace()
    q, r = divmod(space.size, parts)
    worker_rows = [{"worker_id": i, "partition_count": 0, "scalar_count_decimal": "0"}
                   for i in range(workers)]
    worker_counts = [0] * workers
    for idx in range(parts):
        worker_counts[idx % workers] += q + (1 if idx < r else 0)
        worker_rows[idx % workers]["partition_count"] += 1
    for row, count in zip(worker_rows, worker_counts):
        row["scalar_count_decimal"] = str(count)

    bin_q, bin_r = divmod(space.size, bins)
    bin_rows = []
    cursor = 1
    for idx in range(bins):
        count = bin_q + (1 if idx < bin_r else 0)
        stop = cursor + count
        bin_rows.append({
            "bin_index": idx, "start_inclusive_decimal": str(cursor),
            "stop_exclusive_decimal": str(stop), "scalar_count_decimal": str(count),
        })
        cursor = stop

    return {
        "curve": CURVE_ID, "domain": "[1, n)",
        "domain_size_decimal": str(space.size),
        "partition_analysis": {
            "parts": parts, "minimum_partition_size_decimal": str(q),
            "maximum_partition_size_decimal": str(q + (1 if r else 0)),
            "large_partition_count": r, "small_partition_count": parts - r,
            "max_minus_min_decimal": str(1 if r else 0),
            "exact_gap_free_coverage": space.verify_partition(parts),
        },
        "worker_analysis": worker_rows,
        "equal_as_possible_bins": bin_rows,
        "interpretation": "All counts are exact interval arithmetic; no scalar candidates were enumerated.",
    }


def verify_implementation() -> dict:
    space = Secp256k1ScalarSpace()
    two_g_expected = (
        int("c6047f9441ed7d6d3045406e95c07cd85c778e4b8cef3ca7abac09b95c709ee5", 16),
        int("1ae168fea63dc339a3c58419466ceaeef7f632653266d0e1236431a950cfe52a", 16),
    )
    checks = {
        "generator_is_on_curve": is_on_curve(G),
        "one_times_generator_equals_generator": scalar_multiply(1) == G,
        "two_times_generator_matches_known_vector": scalar_multiply(2) == two_g_expected,
        "three_times_generator_is_on_curve": is_on_curve(scalar_multiply(3)),
        "group_order_times_generator_is_infinity": scalar_multiply(N) is None,
        "zero_times_generator_is_infinity": scalar_multiply(0) is None,
        "compressed_generator_encoding_matches_SEC1": encode_public_point(G) == "0279be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798",
        "minimum_scalar_is_valid": space.contains(1),
        "maximum_scalar_is_valid": space.contains(N - 1),
        "zero_is_invalid": not space.contains(0),
        "group_order_is_invalid": not space.contains(N),
        "raw_256_bit_max_is_outside_curve_scalar_domain": not space.contains((1 << 256) - 1),
    }
    partition_counts = (1, 2, 3, 7, 16, 64, 257, 1000)
    checks["partition_sizes_balanced_and_gap_free"] = all(space.verify_partition(p) for p in partition_counts)
    checks["locate_matches_partition_edges"] = all(
        space.locate(space.interval(i, 97).start, 97) == i
        and space.locate(space.interval(i, 97).stop - 1, 97) == i
        for i in range(97)
    )
    manifest = create_manifest(parts=17, workers=4)
    checks["manifest_round_trip_valid"] = validate_manifest(manifest)[0]
    tampered = json.loads(json.dumps(manifest))
    tampered["partitions"][0]["worker_id"] = 3
    checks["manifest_tampering_detected"] = not validate_manifest(tampered)[0]
    coverage = coverage_report(manifest, [0, 1, 2, 3, 4])
    checks["coverage_bookkeeping_exact"] = (
        int(coverage["covered_scalar_count_decimal"])
        == sum(int(manifest["partitions"][i]["count_decimal"]) for i in range(5))
        and coverage["remaining_partition_count"] == 12
    )
    checks["all_pass"] = all(checks.values())
    return checks


def _json_print(obj: dict) -> None:
    print(json.dumps(obj, indent=2, sort_keys=True))


def cmd_info(_args: argparse.Namespace) -> int:
    space = Secp256k1ScalarSpace()
    raw_count = 1 << 256
    _json_print({
        "curve": CURVE_ID,
        "field_prime_p_hex": hex(P),
        "group_order_n_hex": hex(N),
        "generator": {"x": hex(GX), "y": hex(GY)},
        "raw_256_bit_integer_space": {
            "range": "0 <= x < 2^256", "count_decimal": str(raw_count),
            "max_hex": hex(raw_count - 1),
        },
        "valid_curve_scalar_domain": {
            "range": "1 <= k < n", "min_decimal": "1",
            "max_decimal": str(N - 1), "count_decimal": str(space.size),
        },
        "raw_values_excluded_from_valid_scalar_domain": str(raw_count - space.size),
        "warning": "The simulator models the full domain; it does not enumerate it.",
    })
    return 0


def cmd_verify(_args: argparse.Namespace) -> int:
    checks = verify_implementation()
    _json_print(checks)
    return 0 if checks["all_pass"] else 1


def cmd_partition(args: argparse.Namespace) -> int:
    space = Secp256k1ScalarSpace()
    chunks = [space.interval(args.index, args.parts)] if args.index is not None else list(space.partitions(args.parts))
    _json_print({
        "domain": "[1, n)", "parts_requested": args.parts,
        "partition_verification": space.verify_partition(args.parts),
        "partitions": [c.as_dict() for c in chunks],
    })
    return 0


def cmd_visualize(args: argparse.Namespace) -> int:
    if args.parts > 62:
        raise ValueError("visualize supports up to 62 partitions so every partition has a unique symbol")
    if args.width < args.parts or args.width > 240:
        raise ValueError("width must be between parts and 240")
    symbols = string.ascii_uppercase + string.ascii_lowercase + string.digits
    q, r = divmod(args.width, args.parts)
    bar = "".join(symbols[i] * (q + (1 if i < r else 0)) for i in range(args.parts))
    space = Secp256k1ScalarSpace()
    print("Valid scalar-domain interval map: [1, n)")
    print("1 " + bar + " n-1")
    print("Legend: symbol = balanced interval index; intervals are half-open [start, stop).")
    for i in range(args.parts):
        it = space.interval(i, args.parts)
        print(f"{symbols[i]} = partition {i:>3}: {hex(it.start)} .. {hex(it.stop - 1)} ({it.count} scalars)")
    print(f"Verified exact coverage: {space.verify_partition(args.parts)}")
    return 0


def cmd_plan(args: argparse.Namespace) -> int:
    manifest = create_manifest(args.parts, args.workers)
    out = Path(args.output)
    write_manifest(out, manifest)
    _json_print({
        "saved": str(out.resolve()), "parts": args.parts, "workers": args.workers,
        "sha256": manifest["sha256"], "exact_partition_coverage": True,
        "note": "This file assigns intervals only; it contains no key-search worker.",
    })
    return 0


def cmd_check_manifest(args: argparse.Namespace) -> int:
    data = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    valid, reason = validate_manifest(data)
    digest = data.get("sha256") if isinstance(data, dict) else None
    _json_print({"valid": valid, "result": reason, "sha256": digest})
    return 0 if valid else 1


def cmd_coverage(args: argparse.Namespace) -> int:
    data = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    if args.completed.strip():
        try:
            done = [int(part.strip()) for part in args.completed.split(",") if part.strip()]
        except ValueError as exc:
            raise ValueError("--completed must be comma-separated zero-based integer indexes") from exc
    else:
        done = []
    _json_print(coverage_report(data, done))
    return 0


def cmd_locate(args: argparse.Namespace) -> int:
    space = Secp256k1ScalarSpace()
    idx = space.locate(args.scalar, args.parts)
    interval = space.interval(idx, args.parts)
    _json_print({"scalar_hex": hex(args.scalar), "partition_index": idx, "interval": interval.as_dict()})
    return 0


def cmd_sample(args: argparse.Namespace) -> int:
    if not 1 <= args.count <= 100:
        raise ValueError("count must be between 1 and 100")
    space = Secp256k1ScalarSpace()
    rows = []
    for _ in range(args.count):
        scalar = space.random_scalar()
        point = scalar_multiply(scalar)
        rows.append({
            "scalar_hex": hex(scalar),
            "scalar_bit_length": scalar.bit_length(),
            "public_point_compressed_sec1": encode_public_point(point),
        })
    _json_print({"sampling": "uniform over valid scalars [1, n)", "samples": rows})
    return 0


def cmd_multiply(args: argparse.Namespace) -> int:
    if not 1 <= args.scalar < N:
        raise ValueError("scalar must satisfy 1 <= k < n")
    point = scalar_multiply(args.scalar)
    _json_print({
        "scalar_hex": hex(args.scalar), "scalar_bit_length": args.scalar.bit_length(),
        "curve": CURVE_ID,
        "public_point_sec1": encode_public_point(point, args.encoding == "compressed"),
        "point_is_on_curve": is_on_curve(point),
        "warning": "Educational arithmetic only; this implementation is not constant-time.",
    })
    return 0


def cmd_analyze(args: argparse.Namespace) -> int:
    _json_print(exact_analysis(args.parts, args.workers, args.bins))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Exact secp256k1 scalar-space model and interval research tools.")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("analyze", help="calculate exact partition, worker, and bin statistics")
    p.add_argument("--parts", type=int, default=128)
    p.add_argument("--workers", type=int, default=8)
    p.add_argument("--bins", type=int, default=16)
    p.set_defaults(func=cmd_analyze)
    p = sub.add_parser("info", help="show exact raw and valid scalar domains")
    p.set_defaults(func=cmd_info)
    p = sub.add_parser("verify", help="run curve, group, partition, manifest, and coverage checks")
    p.set_defaults(func=cmd_verify)
    p = sub.add_parser("partition", help="print the exact balanced interval partition")
    p.add_argument("--parts", type=int, required=True)
    p.add_argument("--index", type=int)
    p.set_defaults(func=cmd_partition)
    p = sub.add_parser("visualize", help="draw a compact ASCII interval map")
    p.add_argument("--parts", type=int, default=16)
    p.add_argument("--width", type=int, default=64)
    p.set_defaults(func=cmd_visualize)
    p = sub.add_parser("plan", help="write a checksummed interval-to-worker assignment manifest")
    p.add_argument("--parts", type=int, required=True)
    p.add_argument("--workers", type=int, required=True)
    p.add_argument("--output", default="scalar_interval_plan.json")
    p.set_defaults(func=cmd_plan)
    p = sub.add_parser("check-manifest", help="verify manifest checksum and exact assignments")
    p.add_argument("--manifest", required=True)
    p.set_defaults(func=cmd_check_manifest)
    p = sub.add_parser("coverage", help="report interval-level bookkeeping for marked-complete partitions")
    p.add_argument("--manifest", required=True)
    p.add_argument("--completed", default="", help="comma-separated partition indexes, e.g. 0,1,2")
    p.set_defaults(func=cmd_coverage)
    p = sub.add_parser("locate", help="find which balanced interval contains a scalar")
    p.add_argument("--parts", type=int, required=True)
    p.add_argument("--scalar", type=parse_scalar, required=True)
    p.set_defaults(func=cmd_locate)
    p = sub.add_parser("sample", help="sample valid scalars and calculate their curve points")
    p.add_argument("--count", type=int, default=1)
    p.set_defaults(func=cmd_sample)
    p = sub.add_parser("multiply", help="calculate kG for a supplied valid scalar")
    p.add_argument("--scalar", type=parse_scalar, required=True)
    p.add_argument("--encoding", choices=("compressed", "uncompressed"), default="compressed")
    p.set_defaults(func=cmd_multiply)
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except (TypeError, ValueError, OverflowError, OSError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
