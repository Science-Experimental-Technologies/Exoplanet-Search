# Container package

SXS is a Python scientific application. Its GitHub Packages distribution is a
Docker/OCI image in GitHub Container Registry (GHCR), not an npm, NuGet, Maven,
or RubyGems library. Those registries would require separate, tested language
integrations; none are provided by this repository.

## What the image contains

- Python 3.11 and the complete `requirements.txt` scientific environment,
  including TensorFlow and MLflow.
- The SXS source, default YAML configurations, attribution, and license files.
- A non-root runtime user (UID/GID `10001:10001`).

The image does **not** contain downloaded mission products, trained models,
the archived research outputs, or the documentation build tools. Reproduce
training before candidate screening, or supply compatible, independently
verified model artifacts. Installing an image does not reproduce the reported
research results automatically.

Only `linux/amd64` is built and smoke-tested. Linux can run it directly with
Docker Engine. Windows and macOS need a Linux-container runtime such as Docker
Desktop. Apple Silicon requires amd64 emulation (`--platform linux/amd64`),
which is not separately validated and may be slower. This is a command-line,
CPU environment, not a desktop application or a GPU-configured image.

## Pull and inspect

```bash
docker pull ghcr.io/science-experimental-technologies/exoplanet-search:main
docker run --rm ghcr.io/science-experimental-technologies/exoplanet-search:main --help
docker run --rm ghcr.io/science-experimental-technologies/exoplanet-search:main baseline --dry-run
```

The `main` tag follows successful builds of the default branch. Each publication
also has a `sha-<full-git-commit>` tag. Future `v*` tags containing the container
workflow publish a matching version tag; the earlier `v1.1.0` source release
is not retroactively assigned a container. There is no implicit `latest` tag.

For an exact reproduction, record the image digest printed by `docker pull`
and replace `:main` with `@sha256:<digest>` in subsequent commands. A branch
tag is mutable, and rebuilding the same source can resolve different base-image
or transitive-dependency updates. Direct Python requirements are pinned, but
this is not a claim of a fully locked or bit-for-bit reproducible container build.

## Persist research outputs

Without mounts, `--rm` discards outputs when the container exits. Use separate
named volumes for a new research run, and reuse those same names for later
commands in that run. These commands work on one line in PowerShell or a POSIX
shell:

```bash
docker volume create sxs-data
docker volume create sxs-models
docker volume create sxs-reports
docker run --rm --mount source=sxs-data,target=/opt/sxs/data --mount source=sxs-models,target=/opt/sxs/models --mount source=sxs-reports,target=/opt/sxs/reports ghcr.io/science-experimental-technologies/exoplanet-search:main baseline --to-stage 0
```

This example checks the environment and creates output directories; it does
not download photometry or run the complete baseline. Replace
`baseline --to-stage 0` with the desired [workflow command](../reference/cli.md).
Keep the three mounts on every command that needs the same artifacts. Public
archive access requires network connectivity, and complete runs can consume
substantial CPU time, memory, and disk space.

For a custom configuration, bind-mount its containing directory to
`/opt/sxs/configs` read-only and pass `--config configs/your-file.yaml`.
Relative data paths resolve under `/opt/sxs`. Some workflows still use fixed
relative output paths; read the [configuration reference](../reference/configuration.md)
before changing them. Bind-mounted output directories must be writable by UID
10001; named volumes avoid many host-permission differences. Do not run
concurrent experiments against the same volumes.

## Build locally

From a checkout of the repository:

```bash
docker build --platform linux/amd64 -t sxs:local .
docker run --rm sxs:local baseline --dry-run
docker run --rm sxs:local baseline --to-stage 0
```

The allowlisted build context excludes mission data, local model files,
credentials, and research reports. No host Git credential or registry token is
needed inside the image. Dependencies are downloaded during the build.

## Publication and visibility (maintainers)

The `Container package` GitHub Actions workflow builds the image, checks CLI
help and baseline planning, verifies the environment and dependencies, imports
TensorFlow/MLflow, and runs the non-network tests before publishing that same
image. Pull requests build and test but never log in to GHCR or publish.
Publication uses the repository's `GITHUB_TOKEN` with `packages: write` and an
OCI source label linking the package to this repository.

GitHub initially creates container packages as **private**, even for public
repositories. After the first successful publication, a package administrator
must open the organization's **Packages → exoplanet-search → Package settings →
Change visibility → Public** if anonymous downloads are intended. Check the
package's repository link and Actions access there as well. Repository access
inheritance and package visibility are different settings. See GitHub's
[Container registry documentation](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry).

An unauthenticated `docker pull` must succeed before announcing public access.
An authorization error can mean that first-time visibility setup is still
pending; it does not necessarily indicate an invalid image tag. Do not paste
tokens into Dockerfiles, issue reports, or configuration files.

## Licensing and contact

The SXS application remains under the SXS Source-Available Commercial License
1.0, including its attribution and commercial-use terms. Container distribution
does not replace the licenses of Python, Debian, or third-party dependencies.
Read the [license guide](../project/license-security.md) before redistributing
or using the application commercially.

Contact: **scix.official@gmail.com**. Official website:
[SXS Documentation](https://science-experimental-technologies.github.io/Exoplanet-Search/).
