from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Iterable, List, TextIO, Tuple

from packaging.markers import Marker
from packaging.requirements import Requirement


REQUIREMENTS_FOLDER = Path(__file__).parents[3].absolute() / "requirements"
os.chdir(REQUIREMENTS_FOLDER)


class RequirementData:
    def __init__(self, requirement_string: str) -> None:
        self.req = Requirement(requirement_string)
        self.comments = set()

    def __hash__(self) -> int:
        return hash(self.req)

    def __eq__(self, other: RequirementData) -> bool:
        return self.req == other.req

    @property
    def name(self) -> str:
        return self.req.name

    @property
    def marker(self) -> Marker:
        return self.req.marker

    @marker.setter
    def marker(self, value: Marker) -> None:
        self.req.marker = value


def get_requirements(fp: TextIO) -> List[RequirementData]:
    requirements = []

    current = None
    for line in fp.read().splitlines():
        annotation_prefix = "    # "
        if line.startswith(annotation_prefix) and current is not None:
            source = line[len(annotation_prefix) :].strip()
            if source == "via":
                continue
            via_prefix = "via "
            if source.startswith(via_prefix):
                source = source[len(via_prefix) :]
            current.comments.add(source)
        elif line and not line.startswith(("#", " ")):
            current = RequirementData(line)
            requirements.append(current)

    return requirements


def iter_envs(envs: Iterable[str]) -> Iterable[Tuple[str, str]]:
    for env_name in envs:
        platform, python_version = env_name.split("-", maxsplit=1)
        yield (platform, python_version)


names = ["base"]
names.extend(file.stem for file in REQUIREMENTS_FOLDER.glob("extra-*.in"))
base_requirements: List[RequirementData] = []

for name in names:
    # {req_data: {sys_platform: RequirementData}
    input_data: Dict[RequirementData, Dict[str, RequirementData]] = {}
    all_envs = set()
    all_platforms = set()
    all_python_versions = set()
    for file in REQUIREMENTS_FOLDER.glob(f"*-{name}.txt"):
        platform_name, python_version, _ = file.stem.split("-", maxsplit=2)
        env_name = f"{platform_name}-{python_version}"
        all_envs.add(env_name)
        all_platforms.add(platform_name)
        all_python_versions.add(python_version)
        with file.open(encoding="utf-8") as fp:
            requirements = get_requirements(fp)

        for req in requirements:
            envs = input_data.setdefault(req, {})
            envs[env_name] = req

    output = base_requirements if name == "base" else []
    for req, envs in input_data.items():
        # {platform: [python_versions...]}
        python_versions_per_platform: Dict[str, List[str]] = {}
        # {python_version: [platforms...]}
        platforms_per_python_version: Dict[str, List[str]] = {}
        platforms = python_versions_per_platform.keys()
        python_versions = platforms_per_python_version.keys()
        for env_name, other_req in envs.items():
            platform_name, python_version = env_name.split("-", maxsplit=1)
            python_versions_per_platform.setdefault(platform_name, []).append(python_version)
            platforms_per_python_version.setdefault(python_version, []).append(platform_name)

            req.comments.update(other_req.comments)

        base_req = next(
            (base_req for base_req in base_requirements if base_req.name == req.name), None
        )
        if base_req is not None:
            old_base_marker = base_req.marker
            old_req_marker = req.marker
            req.marker = base_req.marker = None
            if base_req.req != req.req:
                raise RuntimeError(f"Incompatible requirements for {req.name}.")

            base_req.marker = old_base_marker
            req.marker = old_req_marker
            if base_req.marker is None or base_req.marker == req.marker:
                continue

        if len(envs) == len(all_envs):
            output.append(req)
            continue

        # At this point I'm wondering why I didn't just go for
        # a more generic boolean algebra simplification (sympy.simplify_logic())...
        if (
            len(set(map(frozenset, python_versions_per_platform.values()))) == 1
            or len(set(map(frozenset, platforms_per_python_version.values()))) == 1
        ):
            # Either all platforms have the same Python version set
            # or all Python versions have the same platform set.
            # We can generate markers for platform (platform_marker) and Python
            # (python_version_marker) version sets separately and then simply require
            # that both markers are fulfilled at the same time (env_marker).

            python_version_marker = (
                # Requirement present on less Python versions than not.
                " or ".join(
                    f"python_version == '{python_version}'" for python_version in python_versions
                )
                if len(python_versions) < len(all_python_versions - python_versions)
                # Requirement present on more Python versions than not
                # This may generate an empty string when Python version is irrelevant.
                else " and ".join(
                    f"python_version != '{python_version}'"
                    for python_version in all_python_versions - python_versions
                )
            )

            platform_marker = (
                # Requirement present on less platforms than not.
                " or ".join(f"sys_platform == '{platform}'" for platform in platforms)
                if len(platforms) < len(all_platforms - platforms)
                # Requirement present on more platforms than not
                # This may generate an empty string when platform is irrelevant.
                else " and ".join(
                    f"sys_platform != '{platform}'" for platform in all_platforms - platforms
                )
            )

            if python_version_marker and platform_marker:
                env_marker = f"({python_version_marker}) and ({platform_marker})"
            else:
                env_marker = python_version_marker or platform_marker
        else:
            # Fallback to generic case.
            env_marker = (
                # Requirement present on less envs than not.
                " or ".join(
                    f"(sys_platform == '{platform}' and python_version == '{python_version}')"
                    for platform, python_version in iter_envs(envs)
                )
                if len(envs) < len(all_envs - envs.keys())
                else " and ".join(
                    f"(sys_platform != '{platform}' and python_version != '{python_version}')"
                    for platform, python_version in iter_envs(all_envs - envs.keys())
                )
            )

        new_marker = f"({req.marker}) and ({env_marker})" if req.marker is not None else env_marker
        req.marker = Marker(new_marker)
        if base_req is not None and base_req.marker == req.marker:
            continue

        output.append(req)

    output.sort(key=lambda req: (req.marker is not None, req.name))
    with open(f"{name}.txt", "w+", encoding="utf-8") as fp:
        for req in output:
            fp.write(str(req.req))
            fp.write("\n")
            comments = sorted(req.comments)

            if len(comments) == 1:
                source = comments[0]
                fp.write("    # via ")
                fp.write(source)
                fp.write("\n")
            else:
                fp.write("    # via\n")
                for source in comments:
                    fp.write("    #   ")
                    fp.write(source)
                    fp.write("\n")
