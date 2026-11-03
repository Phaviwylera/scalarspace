# Scalar Lab — secp256k1 Research Workbench

A browser-based mathematical research dashboard for visualizing and analysing the **exact valid secp256k1 scalar domain**. Includes a dependency-free Python CLI for exact interval arithmetic and educational elliptic-curve verification.

## Live site

After the GitHub Pages workflow succeeds, the site is expected at:

**https://phaviwylera.github.io/scalarspace/**

The workflow in `.github/workflows/pages.yml` publishes the repository root on pushes to `main` or `master`, and supports manual runs from the Actions tab. In the repository, set **Settings → Pages → Build and deployment → Source → GitHub Actions** if Pages is not already configured for Actions.

## Dashboard

The `index.html` file is self-contained and is suitable for GitHub Pages. It uses browser `BigInt` for exact 256-bit interval calculations and browser-local storage for experiment snapshots. No external services or third-party JavaScript libraries are required.

## Run locally

Python 3.9+; no third-party packages required.

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
```

## Tests

```bash
python -m unittest discover -s tests -v
python secp256k1_scalar_sim.py verify
```

## Mathematical model

For secp256k1, the valid scalar values are the integers in `[1, n)`, where `n` is the group order. The program uses exact integer arithmetic for interval boundaries, bin counts, partition sizes, and coverage checks. The dashboard's interval view is a representation of the complete domain; it does not iterate every scalar.

## Scope and safety notes

- This project models and visualizes the scalar domain; it does not enumerate private-key candidates, search wallets, match addresses, or recover private keys.
- Worker assignments and manually marked intervals are bookkeeping metadata, not proof that any computation was performed.
- The included pure-Python elliptic-curve implementation is educational and is not constant-time. Do not use it to protect production secrets.
- SHA-256 checksums detect accidental changes; they are not digital signatures or identity attestations.

## Project files

- `index.html` — self-contained browser dashboard.
- `secp256k1_scalar_sim.py` — exact Python domain arithmetic and educational ECC verification.
- `dashboard_server.py` — loopback-only local web server with restrictive response headers.
- `tests/` — unit and package tests.
- `.github/workflows/pages.yml` — automatic GitHub Pages deployment workflow.
- `CHANGELOG.md` and `VERSION.txt` — release history and version.
"# scalarspace" 
