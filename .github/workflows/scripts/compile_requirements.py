import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


EXCLUDE_STEM_RE = re.compile(r".*-3\.(?!8-)(\d+)-extra-(doc|style)")
GITHUB_OUTPUT = os.environ["GITHUB_OUTPUT"]
REQUIREMENTS_FOLDER = Path(__file__).parents[3].absolute() / "requirements"
os.chdir(REQUIREMENTS_FOLDER)


def pip_compile(version: str, name: str) -> None:
    stem = f"{sys.platform}-{version}-{name}"
    if EXCLUDE_STEM_RE.fullmatch(stem):
        return

    executable = ("py", f"-{version}") if sys.platform == "win32" else (f"python{version}",)
    subprocess.check_call(
        (
            *executable,
            "-m",
            "piptools",
            "compile",
            "--upgrade",
            "--resolver=backtracking",
            "--verbose",
            f"{name}.in",
            "--output-file",
            f"{stem}.txt",
        )
    )


for minor in range(8, 11 + 1):
    version = f"3.{minor}"
    pip_compile(version, "base")
    shutil.copyfile(f"{sys.platform}-{version}-base.txt", "base.txt")
    for file in REQUIREMENTS_FOLDER.glob("extra-*.in"):
        pip_compile(version, file.stem)

with open(GITHUB_OUTPUT, "a", encoding="utf-8") as fp:
    fp.write(f"sys_platform={sys.platform}\n")
