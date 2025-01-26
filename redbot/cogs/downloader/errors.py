from __future__ import annotations

from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from .repo_manager import Candidate


__all__ = [
    "DownloaderException",
    "GitException",
    "InvalidRepoName",
    "CopyingError",
    "ExistingGitRepo",
    "MissingGitRepo",
    "AuthenticationError",
    "CloningError",
    "CurrentHashError",
    "HardResetError",
    "UpdateError",
    "GitDiffError",
    "NoRemoteURL",
    "UnknownRevision",
    "AmbiguousRevision",
    "PipError",
]


class DownloaderException(Exception):
    """
    Base class for Downloader exceptions.
    """

    pass


class GitException(DownloaderException):
    """
    Generic class for git exceptions.
    """

    def __init__(self, message: str, git_command: str) -> None:
        self.git_command = git_command
        super().__init__(f"Git command failed: {git_command}\nError message: {message}")


class InvalidRepoName(DownloaderException):
    """
    Throw when a repo name is invalid. Check
    the message for a more detailed reason.
    """

    pass


class CopyingError(DownloaderException):
    """
    Throw when there was an issue
    during copying of module's files.
    """

    pass


class ExistingGitRepo(DownloaderException):
    """
    Thrown when trying to clone into a folder where a
    git repo already exists.
    """

    pass


class MissingGitRepo(DownloaderException):
    """
    Thrown when a git repo is expected to exist but
    does not.
    """

    pass


class AuthenticationError(GitException):
    """
    Thrown when git failed to authenticate with
    the server
    """

    pass


class CloningError(GitException):
    """
    Thrown when git clone returns a non zero exit code.
    """

    pass


class CurrentHashError(GitException):
    """
    Thrown when git returns a non zero exit code attempting
    to determine the current commit hash.
    """

    pass


class HardResetError(GitException):
    """
    Thrown when there is an issue trying to execute a hard reset
    (usually prior to a repo update).
    """

    pass


class UpdateError(GitException):
    """
    Thrown when git pull returns a non zero error code.
    """

    pass


class GitDiffError(GitException):
    """
    Thrown when a git diff fails.
    """

    pass


class NoRemoteURL(GitException):
    """
    Thrown when no remote URL exists for a repo.
    """

    pass


class UnknownRevision(GitException):
    """
    Thrown when specified revision cannot be found.
    """

    pass


class AmbiguousRevision(GitException):
    """
    Thrown when specified revision is ambiguous.
    """

    def __init__(self, message: str, git_command: str, candidates: List[Candidate]) -> None:
        super().__init__(message, git_command)
        self.candidates = candidates


class PipError(DownloaderException):
    """
    Thrown when pip returns a non-zero return code.
    """

    pass
