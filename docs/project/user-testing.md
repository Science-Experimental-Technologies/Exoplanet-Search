# Independent user testing

Automated CI is not independent usability evidence. This protocol is ready for
external testers; no completed external trials are claimed by preparing it.
Aim for at least one tester on each supported operating system, using a clean
Python 3.11 or 3.12 environment and no previous SXS checkout.

## Test the published software

1. Read the license and download the wheel and `SHA256SUMS.txt` from
   [the release page](https://github.com/Science-Experimental-Technologies/Exoplanet-Search/releases/latest).
2. Verify the checksum and follow the [wheel installation instructions](../getting-started/installation.md#standalone-wheel-and-installed-command).
3. Run `sxs --help` and `sxs demo --output demo`. Confirm a zero exit code,
   `best_period_recovered: true` in `demo/expected.json`, and `completed` in
   `demo/operation.json`.
4. Open `demo/report.html` offline. Check that plots and text are legible and
   clearly describe synthetic, unconfirmed data.
5. Run `sxs analyze --input demo/input.csv --time-system relative --output analysis`.
   Confirm completion and open its HTML report.
6. Run `sxs baseline --workspace research-a --dry-run`. Confirm bundled
   `research-a/configs/base.yaml` exists; no archive download should occur.
7. Run `sxs unknown-command`. Expect code 2 and a concise stderr error.
8. Repeat `sxs demo --output demo`. Expect a nonzero refusal to overwrite.

On PowerShell inspect `$LASTEXITCODE` immediately after the command; on a POSIX
shell use `echo $?`. Installing dependencies requires internet access, but the
demo and CSV example do not. Do not submit private photometry or credentials.

## Report evidence

Use the **Independent user test** issue template in
[GitHub Issues](https://github.com/Science-Experimental-Technologies/Exoplanet-Search/issues/new/choose).
Record release/commit, OS/architecture, Python version, installation method,
each passed/failed step, exact error output, and time to the first useful report.
Attach a redacted screenshot if helpful. Report failures as well as successes;
do not count maintainer runs or CI jobs as independent user trials.

## Public container acceptance

The GHCR package was made public with owner approval on 2026-08-31.
Test from a client without saved registry credentials and record the
image digest and exact tag. A successful authenticated CI push alone does not
establish public access. See the [container guide](../getting-started/container.md).

Maintainers can run `python scripts/check_public_distribution.py --tag v1.2.0`
from a checkout. It verifies all published release checksums through anonymous
downloads and separately checks anonymous GHCR manifest access. A successful
manifest request is not a full image pull or runtime test; any failed component
produces a nonzero exit status. The checker never changes package permissions.
