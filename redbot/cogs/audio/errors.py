from pathlib import Path

import aiohttp

from redbot.core.i18n import Translator

_ = Translator("Audio", Path(__file__))


class AudioError(Exception):
    """Base exception for errors in the Audio cog."""


class ManagedLavalinkNodeException(AudioError):
    """Base Exception for Managed Lavalink Node Exceptions"""


class NodeUnhealthy(ManagedLavalinkNodeException):
    """Exception Raised when the node health checks fail"""


class InvalidArchitectureException(ManagedLavalinkNodeException):
    """Error thrown when the Managed Lavalink node is started on an invalid arch."""


class ManagedLavalinkAlreadyRunningException(ManagedLavalinkNodeException):
    """Exception thrown when a managed Lavalink node is already running"""


class ManagedLavalinkStartFailure(ManagedLavalinkNodeException):
    """Exception thrown when a managed Lavalink node fails to start"""


class ManagedLavalinkPreviouslyShutdownException(ManagedLavalinkNodeException):
    """Exception thrown when a managed Lavalink node already has been shutdown"""


class EarlyExitException(ManagedLavalinkNodeException):
    """some placeholder text I cannot be bothered to add a meaning message atm"""


class UnsupportedJavaException(ManagedLavalinkNodeException):
    """Exception thrown when a managed Lavalink node doesn't have a supported Java"""


class UnexpectedJavaResponseException(ManagedLavalinkNodeException):
    """Exception thrown when Java returns an unexpected response"""


class NoProcessFound(ManagedLavalinkNodeException):
    """Exception thrown when the managed node process is not found"""


class LavalinkDownloadFailed(ManagedLavalinkNodeException, RuntimeError):
    """Downloading the Lavalink jar failed.

    Attributes
    ----------
    response : aiohttp.ClientResponse
        The response from the server to the failed GET request.
    should_retry : bool
        Whether or not the Audio cog should retry downloading the jar.
    """

    def __init__(self, *args, response: aiohttp.ClientResponse, should_retry: bool = False):
        super().__init__(*args)
        self.response = response
        self.should_retry = should_retry

    def __repr__(self) -> str:
        str_args = [*map(str, self.args), self._response_repr()]
        return f"LavalinkDownloadFailed({', '.join(str_args)}"

    def __str__(self) -> str:
        return f"{super().__str__()} {self._response_repr()}"

    def _response_repr(self) -> str:
        return f"[{self.response.status} {self.response.reason}]"


class QueryUnauthorized(AudioError):
    """Provided an unauthorized query to audio."""

    def __init__(self, message, *args):
        self.message = message
        super().__init__(*args)


class TrackEnqueueError(AudioError):
    """Unable to play track."""


class PlayListError(AudioError):
    """Base exception for errors related to playlists."""


class InvalidPlaylistScope(PlayListError):
    """Provided playlist scope is not valid."""


class MissingGuild(PlayListError):
    """Trying to access the Guild scope without a guild."""


class MissingAuthor(PlayListError):
    """Trying to access the User scope without an user id."""


class TooManyMatches(PlayListError):
    """Too many playlist match user input."""


class NoMatchesFound(PlayListError):
    """No entries found for this input."""


class NotAllowed(PlayListError):
    """Too many playlist match user input."""


class ApiError(AudioError):
    """Base exception for API errors in the Audio cog."""


class SpotifyApiError(ApiError):
    """Base exception for Spotify API errors."""


class SpotifyFetchError(SpotifyApiError):
    """Fetching Spotify data failed."""

    def __init__(self, message, *args):
        self.message = message
        super().__init__(*args)


class YouTubeApiError(ApiError):
    """Base exception for YouTube Data API errors."""

    def __init__(self, message, *args):
        self.message = message
        super().__init__(*args)


class DatabaseError(AudioError):
    """Base exception for database errors in the Audio cog."""


class InvalidTableError(DatabaseError):
    """Provided table to query is not a valid table."""


class LocalTrackError(AudioError):
    """Base exception for local track errors."""


class InvalidLocalTrack(LocalTrackError):
    """Base exception for local track errors."""


class InvalidLocalTrackFolder(LocalTrackError):
    """Base exception for local track errors."""
