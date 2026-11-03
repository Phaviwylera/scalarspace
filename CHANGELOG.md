# Changelog

## V7 — Exact raw-domain model and local point explorer

- Added an exact comparison of the full unsigned 256-bit integer space `[0, 2^256)` and the valid secp256k1 scalar domain `[1, n)`.
- Added a browser-local, known-scalar `kG` point explorer with compressed and uncompressed SEC1 encodings.
- Added curve arithmetic test vectors in JavaScript and a Python unittest suite for scalar-domain, partition, manifest and point arithmetic behavior.
- Added V6 browser-workspace migration and V7 report/workspace exports.
- Clarified that the point explorer accepts a supplied scalar only; it does not search for or recover private keys.

## V6 — Combined V4 + V5 + V6 release

### V4: Experiment sessions
- Save named experiment snapshots to browser-local storage.
- Restore saved configurations and marked interval indexes.
- Compare two snapshots side by side.
- Import and export workspace JSON.
- Record a bounded local activity journal.

### V5: Exact mathematical analytics
- Exact equal-as-possible 16-bin domain breakdown.
- Exact partition minimum/maximum size and imbalance metrics.
- Exact scalar-position load by logical worker.
- Scalar-to-partition lookup using `BigInt`.
- Pagination and zoom presets for interval inspection.

### V6: Reproducibility and integrity
- Ten dashboard integrity checks.
- JSON research report with SHA-256 checksum when Web Crypto is available.
- CSV interval export and Markdown summary export.
- External manifest boundary/coverage validation.
- Loopback-only Python server, no-store headers, and a restrictive Content Security Policy.
- Added Python `analyze` CLI command for exact partition, worker and bin statistics.

### Scope
This remains a mathematical domain model and bookkeeping workbench. It does not enumerate scalar candidates, search wallets, match addresses, or recover private keys. Logical worker assignments and manual completion labels are not proof of computation.
