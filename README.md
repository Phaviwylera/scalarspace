# Scalar Lab V7 — secp256k1 Research Workbench

A browser-based mathematical workbench for the **exact secp256k1 scalar domain**. It distinguishes all unsigned 256-bit integers from the valid curve scalars, visualizes exact interval partitions, and can derive the curve point for a known scalar. The Python CLI provides exact interval arithmetic and educational curve verification.

## Live site

After the GitHub Pages workflow succeeds, the site is expected at:

**https://phaviwylera.github.io/scalarspace/**

The workflow in `.github/workflows/pages.yml` publishes the repository root on pushes to `main` and supports manual runs from the Actions tab. Configure **Settings → Pages → Build and deployment → Source → GitHub Actions** if Pages is not already set up.

## Dashboard

The dashboard consists of `index.html` and the local `secp256k1_math.js` module. Both are static files suitable for GitHub Pages. No third-party JavaScript or network service is used. Browser `BigInt` is used for exact 256-bit counts and boundaries; experiment bookkeeping is stored in browser-local storage. V6 workspace data is migrated when V7 starts.

The **Scalar locator & point explorer** computes `Q = kG` only for a scalar the user already supplies. It runs locally, does not save or export the input scalar, and is not a private-key search or recovery feature. Use public test scalars only; do not enter wallet secrets into a browser tool.

## Run locally

Python 3.9+; the dashboard server and CLI use only the standard library.

```bash
python dashboard_server.py
```

Open the local URL printed by the launcher. Windows users can double-click `run_dashboard.bat`; macOS/Linux users can run `./run_dashboard.sh`.

## CLI

```bash
python secp256k1_scalar_sim.py info
python secp256k1_scalar_sim.py verify
python secp256k1_scalar_sim.py analyze --parts 256 --workers 8 --bins 16
python secp256k1_scalar_sim.py visualize --parts 32 --width 64
python secp256k1_scalar_sim.py plan --parts 256 --workers 8 --output plan.json
python secp256k1_scalar_sim.py check-manifest --manifest plan.json
python secp256k1_scalar_sim.py multiply --scalar 0x2
```

`multiply` computes a point for a supplied scalar; it does not solve the inverse problem of finding a scalar from a point.

## Tests

```bash
python -m unittest discover -s tests -v
python secp256k1_scalar_sim.py verify
node tests/test_secp256k1_math.js
```

## Mathematical model

The raw unsigned 256-bit integer set is `[0, 2^256)` and contains exactly `2^256` values. The valid secp256k1 scalar set is `[1, n)`, containing `n − 1` values. Zero and values at least `n` are not valid private scalars. The dashboard reports both domains and the exact difference.

The interval map is a compact mathematical representation of the complete valid domain. It calculates partitions, counts, worker allocations and bins without iterating each scalar. Elliptic-curve points use the secp256k1 generator and exact integer arithmetic.

## Scope and safety

- This project does **not** enumerate candidate keys, search wallets or addresses, invert a public point, or recover private keys.
- Exhaustively searching the 256-bit scalar domain is not a practical recovery method. Use a wallet's legitimate backup and recovery process for accounts you own.
- The point explorer and included Python implementation are educational and not constant-time. Do not use them to protect production secrets.
- Worker assignments and manual interval marks are bookkeeping metadata, not evidence of computation.
- SHA-256 checksums detect accidental changes; they are not signatures or identity attestations.

## Project files

- `index.html` — browser dashboard.
- `secp256k1_math.js` — local JavaScript point arithmetic and SEC1 point encoding.
- `secp256k1_scalar_sim.py` — exact Python domain arithmetic, manifests and educational ECC verification.
- `dashboard_server.py` — loopback-only local web server with restrictive response headers.
- `tests/` — Python domain tests and JavaScript curve-math vector tests.
- `.github/workflows/pages.yml` — GitHub Pages deployment workflow.
- `CHANGELOG.md` and `VERSION.txt` — release history and version.
