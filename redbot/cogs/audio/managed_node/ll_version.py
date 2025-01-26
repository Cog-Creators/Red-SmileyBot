from __future__ import annotations

import re
from typing import Final, Optional, Pattern, Tuple

__all__ = (
    "LAVALINK_BUILD_LINE",
    "LavalinkOldVersion",
    "LavalinkVersion",
)


# present until Lavalink 3.5-rc4
LAVALINK_BUILD_LINE: Final[Pattern] = re.compile(rb"^Build:\s+(?P<build>\d+)$", re.MULTILINE)
# we don't actually care about what the version format before 3.5-rc4 is exactly
# as the comparison is based entirely on the build number
_LAVALINK_VERSION_LINE_PRE35: Final[Pattern] = re.compile(
    rb"^Version:\s+(?P<version>\S+)$", re.MULTILINE | re.VERBOSE
)
# used for LL versions >=3.5-rc4 but below 3.6.
# Since this only applies to historical version, this regex is based only on
# version numbers that actually existed, not ones that technically could.
_LAVALINK_VERSION_LINE_PRE36: Final[Pattern] = re.compile(
    rb"""
    ^
    Version:\s+
    (?P<version>
        (?P<major>3)\.(?P<minor>[0-5])
        # Before LL 3.6, when patch version == 0, it was stripped from the version string
        (?:\.(?P<patch>[1-9]\d*))?
        # Before LL 3.6, the dot in rc.N was optional
        (?:-rc\.?(?P<rc>0|[1-9]\d*))?
        # additional build metadata, can be used by our downstream Lavalink
        # if we need to alter an upstream release
        (?:\+red\.(?P<red>[1-9]\d*))?
    )
    $
    """,
    re.MULTILINE | re.VERBOSE,
)
# used for LL 3.6 and newer
# This regex is limited to the realistic usage in the LL version number,
# not everything that could be a part of it according to the spec.
# We can easily release an update to this regex in the future if it ever becomes necessary.
_LAVALINK_VERSION_LINE: Final[Pattern] = re.compile(
    rb"""
    ^
    Version:\s+
    (?P<version>
        (?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)
        (?:-rc\.(?P<rc>0|[1-9]\d*))?
        # additional build metadata, can be used by our downstream Lavalink
        # if we need to alter an upstream release
        (?:\+red\.(?P<red>[1-9]\d*))?
    )
    $
    """,
    re.MULTILINE | re.VERBOSE,
)


class LavalinkOldVersion:
    def __init__(self, raw_version: str, *, build_number: int) -> None:
        self.raw_version = raw_version
        self.build_number = build_number

    def __str__(self) -> str:
        return f"{self.raw_version}_{self.build_number}"

    @classmethod
    def from_version_output(cls, output: bytes) -> LavalinkOldVersion:
        build_match = LAVALINK_BUILD_LINE.search(output)
        if build_match is None:
            raise ValueError(
                "Could not find 'Build' line in the given `--version` output,"
                " or invalid build number given."
            )
        version_match = _LAVALINK_VERSION_LINE_PRE35.search(output)
        if version_match is None:
            raise ValueError(
                "Could not find 'Version' line in the given `--version` output,"
                " or invalid version number given."
            )
        return cls(
            raw_version=version_match["version"].decode(),
            build_number=int(build_match["build"]),
        )

    def __eq__(self, other: object) -> bool:
        if isinstance(other, LavalinkOldVersion):
            return self.build_number == other.build_number
        if isinstance(other, LavalinkVersion):
            return False
        return NotImplemented

    def __lt__(self, other: object) -> bool:
        if isinstance(other, LavalinkOldVersion):
            return self.build_number < other.build_number
        if isinstance(other, LavalinkVersion):
            return True
        return NotImplemented

    def __le__(self, other: object) -> bool:
        if isinstance(other, LavalinkOldVersion):
            return self.build_number <= other.build_number
        if isinstance(other, LavalinkVersion):
            return True
        return NotImplemented

    def __gt__(self, other: object) -> bool:
        if isinstance(other, LavalinkOldVersion):
            return self.build_number > other.build_number
        if isinstance(other, LavalinkVersion):
            return False
        return NotImplemented

    def __ge__(self, other: object) -> bool:
        if isinstance(other, LavalinkOldVersion):
            return self.build_number >= other.build_number
        if isinstance(other, LavalinkVersion):
            return False
        return NotImplemented


class LavalinkVersion:
    def __init__(
        self,
        major: int,
        minor: int,
        patch: int = 0,
        *,
        rc: Optional[int] = None,
        red: int = 0,
    ) -> None:
        self.major = major
        self.minor = minor
        self.patch = patch
        self.rc = rc
        self.red = red

    def __str__(self) -> str:
        version = f"{self.major}.{self.minor}.{self.patch}"
        if self.rc is not None:
            version += f"-rc.{self.rc}"
        if self.red:
            version += f"+red.{self.red}"
        return version

    @classmethod
    def from_version_output(cls, output: bytes) -> LavalinkVersion:
        match = _LAVALINK_VERSION_LINE.search(output)
        if match is None:
            # >=3.5-rc4, <3.6
            match = _LAVALINK_VERSION_LINE_PRE36.search(output)
        if match is None:
            raise ValueError(
                "Could not find 'Version' line in the given `--version` output,"
                " or invalid version number given."
            )
        return cls(
            major=int(match["major"]),
            minor=int(match["minor"]),
            patch=int(match["patch"] or 0),
            rc=int(match["rc"]) if match["rc"] is not None else None,
            red=int(match["red"] or 0),
        )

    def _get_comparison_tuple(self) -> Tuple[int, int, int, bool, int, int]:
        return self.major, self.minor, self.patch, self.rc is None, self.rc or 0, self.red

    def __eq__(self, other: object) -> bool:
        if isinstance(other, LavalinkVersion):
            return self._get_comparison_tuple() == other._get_comparison_tuple()
        if isinstance(other, LavalinkOldVersion):
            return False
        return NotImplemented

    def __lt__(self, other: object) -> bool:
        if isinstance(other, LavalinkVersion):
            return self._get_comparison_tuple() < other._get_comparison_tuple()
        if isinstance(other, LavalinkOldVersion):
            return False
        return NotImplemented

    def __le__(self, other: object) -> bool:
        if isinstance(other, LavalinkVersion):
            return self._get_comparison_tuple() <= other._get_comparison_tuple()
        if isinstance(other, LavalinkOldVersion):
            return False
        return NotImplemented

    def __gt__(self, other: object) -> bool:
        if isinstance(other, LavalinkVersion):
            return self._get_comparison_tuple() > other._get_comparison_tuple()
        if isinstance(other, LavalinkOldVersion):
            return True
        return NotImplemented

    def __ge__(self, other: object) -> bool:
        if isinstance(other, LavalinkVersion):
            return self._get_comparison_tuple() >= other._get_comparison_tuple()
        if isinstance(other, LavalinkOldVersion):
            return True
        return NotImplemented
