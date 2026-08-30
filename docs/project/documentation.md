# Documentation Maintenance

The repository README is the front door. `docs/` contains the task guides,
scientific explanations, and reference material. `reports/` remains the
authoritative frozen research record; editing a guide must not rewrite a result.

## Build and preview

From an activated Python 3.11 or 3.12 environment in the repository root:

```bash
python -m pip install -r requirements-docs.txt
python -m mkdocs build --strict
python scripts/check_documentation.py --site-dir site
python -m mkdocs serve --dev-addr 127.0.0.1:8000
```

Open the address printed by the preview server. Generated HTML goes to `site/`,
which is ignored by Git. Stop the preview server with Ctrl+C.

`scripts/docs_hooks.py` includes the existing banner and two research figures
as local site assets during the build. The site does not depend on loading
those images from GitHub's raw-content server.

## CLI preview assets

The [CLI preview gallery](../getting-started/cli-preview.md) uses local SVGs
generated from actual command output. After changing CLI help or the baseline
plan, run `python scripts/build_cli_previews.py`, then commit the updated assets
with the code. CI runs the generator with `--check` to detect stale previews.

## Page organization

| Section | Responsibility |
|---|---|
| Getting Started | Installation, first safe commands, configuration habits |
| Research | Questions, experimental design, results, and limitations |
| Concepts | System architecture, algorithms, and data flow |
| Guides | Task-oriented operating and troubleshooting instructions |
| Reference | Exact CLI options, configuration, artifacts, and Python entry points |
| Project | Reproducibility, citation, contributions, and licensing |

Add every new page to `nav` in `mkdocs.yml`. Use relative Markdown links for
other docs pages and full GitHub links for files outside `docs/`. Do not add
credentials, private logs, or raw mission caches to the documentation tree.

## Pull-request checks

The Documentation workflow builds with `--strict` for matching pull requests.
It does not deploy a pull request. Before submitting:

1. verify examples against the current command parsers and source paths;
2. cross-check scientific numbers against the accepted reports/artifacts;
3. run the strict build;
4. preview navigation, code tabs, diagrams, and narrow-screen layout; and
5. preserve the distinction between configured values and effective behavior.

## Publishing

The repository uses GitHub Pages with **GitHub Actions** as its publishing
source. On matching pushes to `main`, or a manual run on `main`, the workflow
builds the site, uploads the Pages artifact, and deploys it to the `github-pages`
environment. Deployment is restricted to `main`; other refs can only build.

Public site:

<https://science-experimental-technologies.github.io/Exoplanet-Search/>

For a new repository, a maintainer must first enable Pages and choose GitHub
Actions as the source. A workflow success alone is not proof of availability:
check the deployment result and the live URL.

## Versioning

This site documents the default branch. The initial site was added after
release 1.1.0. For an exact release audit, use that tag's source and reports;
do not assume a later documentation update exists in an earlier download.

Theme and build dependencies are pinned in `requirements-docs.txt`. Upgrade
them in a reviewed change and rebuild before deployment.
