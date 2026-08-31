"""Install a wheel into an isolated venv and exercise its real console script."""

import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import venv


def check(wheel: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="sxs-installed-") as temporary:
        root = Path(temporary)
        environment = root / "venv"
        # Install declared dependencies too: neither the checkout nor the
        # caller's virtualenv may provide undeclared runtime requirements.
        venv.EnvBuilder(with_pip=True).create(environment)
        scripts = environment / ("Scripts" if sys.platform == "win32" else "bin")
        python = scripts / ("python.exe" if sys.platform == "win32" else "python")
        cli = scripts / ("sxs.exe" if sys.platform == "win32" else "sxs")
        subprocess.run([str(python), "-m", "pip", "install", str(wheel.resolve())], cwd=root, check=True)
        subprocess.run([str(python), "-m", "pip", "check"], cwd=root, check=True)
        for arguments in (["--help"], ["demo", "--output", "demo"],
                          ["baseline", "--workspace", "workspace", "--dry-run"]):
            subprocess.run([str(cli), *arguments], cwd=root, check=True)
        assert json.loads((root / "demo/expected.json").read_text())["best_period_recovered"]
        assert (root / "demo/report.html").is_file()
        assert json.loads((root / "demo/operation.json").read_text())["status"] == "completed"
        assert (root / "workspace/configs/base.yaml").is_file()
        origin = subprocess.check_output([str(python), "-I", "-c", "import src; print(src.__file__)"], cwd=root, text=True).strip()
        assert Path(origin).resolve().is_relative_to(environment.resolve()), origin
    print("Installed console script, offline demo, and packaged workspace defaults passed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    wheels = list(args.directory.glob("scix_exoplanet_search-*.whl"))
    if len(wheels) != 1:
        parser.error("Expected exactly one wheel")
    check(wheels[0])
