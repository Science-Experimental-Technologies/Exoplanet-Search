# Software release 1.2.0 verification

Date: 2026-08-31. This is a software-delivery audit, not a new scientific result.
The archived research tables, metrics, candidate classifications, and PDF are
not changed by this release.

## Implemented delivery requirements

| Requirement | Implementation / evidence |
|---|---|
| Numbered release | Version 1.2.0 in pyproject/CFF/changelog; tag workflow rejects inconsistent metadata |
| Standalone installation | Wheel includes YAML defaults; clean-venv checker installs declared dependencies and exercises the actual console script outside the checkout |
| Platform CI | Ubuntu, Windows, macOS × Python 3.11/3.12; hosted outcomes are recorded in GitHub Actions |
| Failure and progress handling | Shared CLI exit codes, lifecycle JSON, handled interruption status, per-stage checkpoints, and partial experiment outputs |
| Concurrent-write protection | OS-backed workspace locks; subprocess regression proves exclusion and release on process exit |
| Runtime identity | Expanded scientific dependency versions, Python/platform/architecture, and source hashes |
| FAP restart fidelity | Regression interrupts after 25 saved draws and verifies resumed output equals an uninterrupted 27-draw run |
| Public distribution audit | Read-only checker hashes every release payload and separately tests anonymous GHCR manifest access |
| Independent user testing | Published protocol and issue form; no external trial results are fabricated |

## Local verification

- Deterministic suite: **69 passed, 1 network test deselected**.
- Targeted CLI/execution/pipeline tests also passed after lifecycle cleanup.
- Strict MkDocs build passed; generated-site link check found no broken links.
- Repository Markdown audit and recorded CLI-preview check passed.
- Release metadata check agrees on version 1.2.0.
- The wheel's module layout, entry point, and packaged defaults pass the wheel
  inspection. The separate clean-install check is also a required CI/release step.

Run the exact revision's checks rather than relying on this dated record:

```bash
python -m pytest -m "not network"
python scripts/check_release_metadata.py 1.2.0
python -m pip wheel --no-deps --wheel-dir dist/wheels .
python scripts/check_wheel.py dist/wheels
python scripts/check_installed_package.py dist/wheels
python -m mkdocs build --strict
python scripts/check_documentation.py
python scripts/check_repository_docs.py
python scripts/build_cli_previews.py --check
```

Use a clean source tree for package builds to avoid stale build output. Hosted
CI and release results are available in
[GitHub Actions](https://github.com/Science-Experimental-Technologies/Exoplanet-Search/actions).
The release workflow attaches three source bundles, the wheel, the unchanged
archived PDF, and a checksum manifest covering all five payloads.

## External acceptance still required

At this audit checkpoint, anonymous GHCR token access returned **HTTP 401**.
The available browser was signed out of GitHub; changing package visibility
requires an authenticated owner/admin. An authenticated image push is not proof
of public availability. Recheck after the owner enables public visibility:

```bash
python scripts/check_public_distribution.py --tag v1.2.0
```

Independent user trials require people outside the maintainer team. The
[protocol](../docs/project/user-testing.md) describes the evidence to collect.
Preparing that protocol does not complete those trials.

## Operational boundaries

Core CI does not reproduce full TensorFlow/CNN training on every platform.
Workspaces and their parent lock directories must be writable. Local OS locks
are not a distributed locking service for unreliable network filesystems.
Hard kills cannot guarantee a final status or a compatible checkpoint.
Partial injection/evaluation output is inspectable but is not automatically
resumable. Older fingerprints are deliberately incompatible with the expanded
runtime identity. No unsafe resume override is provided.
