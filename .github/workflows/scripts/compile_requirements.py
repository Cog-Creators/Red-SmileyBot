import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Tuple


EXCLUDE_STEM_RE = re.compile(r".*-3\.(?!8-)(\d+)-extra-(doc|style)")
GITHUB_OUTPUT = os.environ["GITHUB_OUTPUT"]
REQUIREMENTS_FOLDER = Path(__file__).parents[3].absolute() / "requirements"
os.chdir(REQUIREMENTS_FOLDER)


def _get_global_executable(version: str) -> Tuple[str, ...]:
    return ("py", f"-{version}") if sys.platform == "win32" else (f"python{version}",)


def _get_venv_executable(venv_dir: str) -> str:
    return (
        f"{venv_dir}{os.sep}Scripts{os.sep}python.exe"
        if sys.platform == "win32"
        else f"{venv_dir}{os.sep}bin{os.sep}python"
    )


def pip_compile(version: str, name: str) -> None:
    stem = f"{sys.platform}-{version}-{name}"
    if EXCLUDE_STEM_RE.fullmatch(stem):
        return

    executable = _get_global_executable(version)
    subprocess.check_call(
        (
            *executable,
            "-m",
            "piptools",
            "compile",
            "--pip-args",
            "--python-version=3.8.1",
            "--upgrade",
            "--resolver=backtracking",
            "--verbose",
            f"{name}.in",
            "--output-file",
            f"{stem}.txt",
        )
    )


def validate_requirements(version: str) -> None:
    files_it = REQUIREMENTS_FOLDER.glob(f"{sys.platform}-{version}-*.txt")

    executable = _get_global_executable(version)
    with tempfile.TemporaryDirectory() as venv_dir:
        subprocess.check_call((*executable, "-m", "venv", venv_dir))
        venv_executable = _get_venv_executable(venv_dir)

        subprocess.check_call((venv_executable, "-m", "pip", "install", "pip-tools"))
        subprocess.check_call((venv_executable, "-m", "piptools", "sync", *map(str, files_it)))


for minor in range(8, 11 + 1):
    version = f"3.{minor}"
    pip_compile(version, "base")
    shutil.copyfile(f"{sys.platform}-{version}-base.txt", "base.txt")
    for file in REQUIREMENTS_FOLDER.glob("extra-*.in"):
        pip_compile(version, file.stem)
    validate_requirements(version)

with open(GITHUB_OUTPUT, "a", encoding="utf-8") as fp:
    fp.write(f"sys_platform={sys.platform}\n")
