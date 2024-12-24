import importlib.metadata
import os
import sys
from packaging.requirements import Requirement
from packaging.version import Version

import pytest

from redbot import core
from redbot.core import VersionInfo


def test_version_working():
    assert hasattr(core, "__version__")
    assert core.__version__[0] == "3"


# When adding more of these, ensure they are added in ascending order of precedence
version_tests = (
    "3.0.0.dev1",
    "3.0.0.dev2",
    "3.0.0a32.dev12",
    "3.0.0a32",
    "3.0.0a32.post10.dev12",
    "3.0.0a32.post10",
    "3.0.0b23.dev4",
    "3.0.0b23",
    "3.0.0b23.post5.dev16",
    "3.0.0b23.post5",
    "3.0.0rc1.dev1",
    "3.0.0rc1",
    "3.0.0",
    "3.0.0.post1.dev1",
    "3.0.1.dev1",
    "3.0.1.dev2+gdbaf31e",
    "3.0.1.dev2+gdbaf31e.dirty",
    "3.0.1.dev3+gae98d77",
    "3.0.1",
    "3.0.1.post1.dev1",
    "3.0.1.post1",
    "2018.10.6b21",
)


def test_version_info_str_parsing():
    for version_str in version_tests:
        assert version_str == str(VersionInfo.from_str(version_str))


def test_version_info_lt():
    for version_cls in (Version, VersionInfo.from_str):
        for next_idx, cur in enumerate(version_tests[:-1], start=1):
            cur_test = version_cls(cur)
            next_test = version_cls(version_tests[next_idx])
            assert cur_test < next_test


def test_version_info_gt():
    assert VersionInfo.from_str(version_tests[1]) > VersionInfo.from_str(version_tests[0])


def test_python_version_has_lower_bound():
    """
    Due to constant issues in support with Red being installed on a Python version that was not
    supported by any Red version, it is important that we have both an upper and lower bound set.
    """
    requires_python = importlib.metadata.metadata("Red-DiscordBot").get("Requires-Python")
    assert requires_python is not None

    # Requirement needs a regular requirement string, so "x" serves as requirement's name here
    req = Requirement(f"x{requires_python}")
    assert any(spec.operator in (">", ">=") for spec in req.specifier)


@pytest.mark.skipif(
    os.getenv("TOX_RED", False) and sys.version_info >= (3, 12),
    reason="Testing on yet to be supported Python version.",
)
def test_python_version_has_upper_bound():
    """
    Due to constant issues in support with Red being installed on a Python version that was not
    supported by any Red version, it is important that we have both an upper and lower bound set.
    """
    requires_python = importlib.metadata.metadata("Red-DiscordBot").get("Requires-Python")
    assert requires_python is not None

    # Requirement needs a regular requirement string, so "x" serves as requirement's name here
    req = Requirement(f"x{requires_python}")
    assert any(spec.operator in ("<", "<=") for spec in req.specifier)
