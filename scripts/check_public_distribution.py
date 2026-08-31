"""Read-only checks of anonymous release downloads and GHCR manifest access."""

import argparse
import hashlib
import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

REPOSITORY = "Science-Experimental-Technologies/Exoplanet-Search"
IMAGE = REPOSITORY.lower()


def fetch(url, headers=None):
    return urlopen(Request(url, headers={"User-Agent": "SXS-release-check", **(headers or {})}), timeout=60)


def release_check(tag):
    with fetch(f"https://api.github.com/repos/{REPOSITORY}/releases/tags/{tag}") as response:
        release = json.load(response)
    assets = {item["name"]: item["browser_download_url"] for item in release["assets"]}
    with fetch(assets["SHA256SUMS.txt"]) as response:
        manifest = response.read().decode()
    expected = {
        f"sxs-{tag}-windows-python.zip", f"sxs-{tag}-macos-python.tar.gz",
        f"sxs-{tag}-linux-python.tar.gz",
        f"scix_exoplanet_search-{tag.removeprefix('v')}-py3-none-any.whl",
        "sxs_preprint_v1.0.0.pdf",
    }
    checksums = {}
    for line in manifest.splitlines():
        digest, name = line.split(maxsplit=1)
        checksums[name] = digest
    if set(checksums) != expected or set(assets) != expected | {"SHA256SUMS.txt"}:
        raise ValueError("Published assets/checksum manifest do not match the required release payloads")
    verified = []
    for name in sorted(expected):
        digest = hashlib.sha256()
        with fetch(assets[name]) as response:
            for block in iter(lambda: response.read(1024 * 1024), b""):
                digest.update(block)
        if digest.hexdigest() != checksums[name]:
            raise ValueError(f"Checksum mismatch: {name}")
        verified.append(name)
    return {"status": "passed", "url": release["html_url"], "verified_assets": verified}


def container_check(tag):
    with fetch(f"https://ghcr.io/token?service=ghcr.io&scope=repository:{IMAGE}:pull") as response:
        token = json.load(response)["token"]
    with fetch(f"https://ghcr.io/v2/{IMAGE}/manifests/{tag}", {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.oci.image.manifest.v1+json, application/vnd.docker.distribution.manifest.v2+json",
    }) as response:
        return {"status": "passed", "digest": response.headers.get("Docker-Content-Digest"),
                "scope": "anonymous manifest access; not a full image pull/runtime test"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", default="v1.2.0")
    args = parser.parse_args()
    results = {"tag": args.tag}
    for name, check in (("release", release_check), ("container", container_check)):
        try:
            results[name] = check(args.tag)
        except HTTPError as exc:
            results[name] = {"status": "blocked", "http_status": exc.code}
        except (URLError, OSError, ValueError, KeyError) as exc:
            results[name] = {"status": "failed", "error": str(exc)}
    print(json.dumps(results, indent=2))
    return 0 if all(results[key]["status"] == "passed" for key in ("release", "container")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
