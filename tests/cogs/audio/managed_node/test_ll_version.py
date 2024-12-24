import itertools
from typing import Optional

import pytest

from redbot.cogs.audio.managed_node.ll_version import LavalinkOldVersion, LavalinkVersion


ORDERED_VERSIONS = [
    LavalinkOldVersion("3.3.2.3", build_number=1239),
    LavalinkOldVersion("3.4.0", build_number=1275),
    LavalinkOldVersion("3.4.0", build_number=1350),
    # LavalinkVersion is always newer than LavalinkOldVersion
    LavalinkVersion(3, 3),
    LavalinkVersion(3, 4),
    LavalinkVersion(3, 5, rc=1),
    LavalinkVersion(3, 5, rc=2),
    LavalinkVersion(3, 5, rc=3),
    # version with `+red.N` build number is newer than an equivalent upstream version
    LavalinkVersion(3, 5, rc=3, red=1),
    LavalinkVersion(3, 5, rc=3, red=2),
    # all RC versions (including ones with `+red.N`) are older than a stable version
    LavalinkVersion(3, 5),
    # version with `+red.N` build number is newer than an equivalent upstream version
    LavalinkVersion(3, 5, red=1),
    LavalinkVersion(3, 5, red=2),
    # but newer version number without `+red.N` is still newer
    LavalinkVersion(3, 5, 1),
]


@pytest.mark.parametrize(
    "raw_version,raw_build_number,expected",
    (
        # 3-segment version number
        ("3.4.0", "1350", LavalinkOldVersion("3.4.0", build_number=1350)),
        # 4-segment version number
        ("3.3.2.3", "1239", LavalinkOldVersion("3.3.2.3", build_number=1239)),
        # 3-segment version number with 3-digit build number
        ("3.3.1", "987", LavalinkOldVersion("3.3.1", build_number=987)),
    ),
)
def test_old_ll_version_parsing(
    raw_version: str, raw_build_number: str, expected: LavalinkOldVersion
) -> None:
    line = b"Version: %b\nBuild: %b" % (raw_version.encode(), raw_build_number.encode())
    actual = LavalinkOldVersion.from_version_output(line)
    assert actual == expected
    assert str(actual) == f"{raw_version}_{raw_build_number}"


def _generate_ll_version_line(raw_version: str) -> bytes:
    return b"Version: " + raw_version.encode()


@pytest.mark.parametrize(
    "raw_version,expected_str,expected",
    (
        # older version format that allowed stripped `.0` and no dot in `rc.4`, used until LL 3.6
        ("3.5-rc4", "3.5.0-rc.4", LavalinkVersion(3, 5, rc=4)),
        ("3.5", "3.5.0", LavalinkVersion(3, 5)),
        # newer version format
        ("3.6.0-rc.1", None, LavalinkVersion(3, 6, 0, rc=1)),
        # downstream RC version with `+red.N` suffix
        ("3.7.5-rc.1+red.1", None, LavalinkVersion(3, 7, 5, rc=1, red=1)),
        ("3.7.5-rc.1+red.123", None, LavalinkVersion(3, 7, 5, rc=1, red=123)),
        # upstream stable version
        ("3.7.5", None, LavalinkVersion(3, 7, 5)),
        # downstream stable version with `+red.N` suffix
        ("3.7.5+red.1", None, LavalinkVersion(3, 7, 5, red=1)),
        ("3.7.5+red.123", None, LavalinkVersion(3, 7, 5, red=123)),
    ),
)
def test_ll_version_parsing(
    raw_version: str, expected_str: Optional[str], expected: LavalinkVersion
) -> None:
    line = _generate_ll_version_line(raw_version)
    actual = LavalinkVersion.from_version_output(line)
    expected_str = expected_str or raw_version
    assert actual == expected
    assert str(actual) == expected_str


@pytest.mark.parametrize(
    "raw_version",
    (
        # 3.5.0-rc4 is first version to not have build number
        # 3.5 stripped `.0` from version number
        "3.5",
        # RC version don't need a dot for RC versions...
        "3.5-rc4",
        # ...but that doesn't mean they can't
        "3.5-rc.5",
        # regular 3.5.x version
        "3.5.5",
        # one more RC version with non-zero patch version
        "3.5.5-rc1",
    ),
)
def test_ll_version_accepts_less_strict_below_3_6(raw_version: str) -> None:
    line = _generate_ll_version_line(raw_version)
    # check that the version can be parsed
    LavalinkVersion.from_version_output(line)


@pytest.mark.parametrize(
    "raw_version",
    (
        # `.0` releases <3.6 had their `.0` stripped so this is not valid:
        "3.5.0-rc4",
        # 3.6 is first to require stricter format
        "3.6.0-rc4",
        "3.6",
        # another single digit minor version newer than 3.6
        "3.7",
        # double digit minor version
        "3.11.3-rc1",
        # newer major version
        "4.0.0-rc5",
        # double digit major version
        "11.0.0-rc5",
    ),
)
def test_ll_version_rejects_less_strict_on_3_6_and_above(raw_version: str) -> None:
    line = _generate_ll_version_line(raw_version)

    with pytest.raises(ValueError):
        LavalinkVersion.from_version_output(line)


def test_ll_version_comparison() -> None:
    it1, it2 = itertools.tee(ORDERED_VERSIONS)
    next(it2, None)
    for a, b in zip(it1, it2):
        assert a < b
