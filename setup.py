import os
import sys
from pathlib import Path

from setuptools import find_namespace_packages, setup

ROOT_FOLDER = Path(__file__).parent.absolute()
REQUIREMENTS_FOLDER = ROOT_FOLDER / "requirements"

# Since we're importing `redbot` package, we have to ensure that it's in sys.path.
sys.path.insert(0, str(ROOT_FOLDER))

from redbot import VersionInfo

version, _ = VersionInfo._get_version(ignore_installed=True)


def get_requirements(fp):
    return [
        line.strip()
        for line in fp.read().splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]


def extras_combined(*extra_names):
    return list(
        {
            req
            for extra_name, extra_reqs in extras_require.items()
            if not extra_names or extra_name in extra_names
            for req in extra_reqs
        }
    )


with open(REQUIREMENTS_FOLDER / "base.txt", encoding="utf-8") as fp:
    install_requires = get_requirements(fp)

extras_require = {}
for file in REQUIREMENTS_FOLDER.glob("extra-*.txt"):
    with file.open(encoding="utf-8") as fp:
        extras_require[file.stem[len("extra-") :]] = get_requirements(fp)

extras_require["dev"] = extras_combined()
extras_require["all"] = extras_combined("postgres")


python_requires = ">=3.8.1"
if not os.getenv("TOX_RED", False) or sys.version_info < (3, 12):
    python_requires += ",<3.12"

# Metadata and options defined in pyproject.toml
setup(
    version=version,
    python_requires=python_requires,
    # TODO: use [tool.setuptools.dynamic] table once this feature gets out of beta
    install_requires=install_requires,
    extras_require=extras_require,
    # TODO: use [project] table once PEP 639 gets accepted
    license_files=["LICENSE", "redbot/**/*.LICENSE"],
    # TODO: use [tool.setuptools.packages] table once this feature gets out of beta
    packages=find_namespace_packages(include=["redbot", "redbot.*"]),
)
