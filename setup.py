"""Include the canonical configuration directory in built distributions."""

from pathlib import Path
import shutil
from setuptools import setup
from setuptools.command.build_py import build_py


class BuildPy(build_py):
    def run(self):
        super().run()
        source = Path(__file__).parent / "configs"
        destination = Path(self.build_lib) / "src" / "default_configs"
        destination.mkdir(parents=True, exist_ok=True)
        for path in source.glob("*.yaml"):
            shutil.copy2(path, destination / path.name)


setup(cmdclass={"build_py": BuildPy})
