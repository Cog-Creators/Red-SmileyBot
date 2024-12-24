import contextlib
import glob
import ntpath
import os
import posixpath
import re

from pathlib import Path, PosixPath, WindowsPath
from typing import (
    AsyncIterator,
    Callable,
    Final,
    Iterator,
    MutableMapping,
    Optional,
    Pattern,
    Tuple,
    Union,
)
from urllib.parse import urlparse

import lavalink
from red_commons.logging import getLogger

from redbot.core.i18n import Translator
from redbot.core.utils import AsyncIter

_ = Translator("Audio", Path(__file__))

_RE_REMOVE_START: Final[Pattern] = re.compile(r"^(sc|list) ")
_RE_YOUTUBE_TIMESTAMP: Final[Pattern] = re.compile(r"[&|?]t=(\d+)s?")
_RE_YOUTUBE_INDEX: Final[Pattern] = re.compile(r"&index=(\d+)")
_RE_SPOTIFY_URL: Final[Pattern] = re.compile(r"(http[s]?://)?(open\.spotify\.com)/")
_RE_SPOTIFY_TIMESTAMP: Final[Pattern] = re.compile(r"#(\d+):(\d+)")
_RE_SOUNDCLOUD_TIMESTAMP: Final[Pattern] = re.compile(r"#t=(\d+):(\d+)s?")
_RE_TWITCH_TIMESTAMP: Final[Pattern] = re.compile(r"\?t=(\d+)h(\d+)m(\d+)s")
_PATH_SEPS: Final[Tuple[str, str]] = (posixpath.sep, ntpath.sep)

_FULLY_SUPPORTED_MUSIC_EXT: Final[Tuple[str, ...]] = (".mp3", ".flac", ".ogg")
_PARTIALLY_SUPPORTED_MUSIC_EXT: Tuple[str, ...] = (
    ".m3u",
    ".m4a",
    ".aac",
    ".ra",
    ".wav",
    ".opus",
    ".wma",
    ".ts",
    ".au",
    # These do not work
    # ".mid",
    # ".mka",
    # ".amr",
    # ".aiff",
    # ".ac3",
    # ".voc",
    # ".dsf",
)
_PARTIALLY_SUPPORTED_VIDEO_EXT: Tuple[str, ...] = (
    ".mp4",
    ".mov",
    ".flv",
    ".webm",
    ".mkv",
    ".wmv",
    ".3gp",
    ".m4v",
    ".mk3d",  # https://github.com/Devoxin/lavaplayer
    ".mka",  # https://github.com/Devoxin/lavaplayer
    ".mks",  # https://github.com/Devoxin/lavaplayer
    # These do not work
    # ".vob",
    # ".mts",
    # ".avi",
    # ".mpg",
    # ".mpeg",
    # ".swf",
)
_PARTIALLY_SUPPORTED_MUSIC_EXT += _PARTIALLY_SUPPORTED_VIDEO_EXT


log = getLogger("red.cogs.Audio.audio_dataclasses")


class LocalPath:
    """Local tracks class.

    Used to handle system dir trees in a cross system manner. The only use of this class is for
    `localtracks`.
    """

    _all_music_ext = _FULLY_SUPPORTED_MUSIC_EXT + _PARTIALLY_SUPPORTED_MUSIC_EXT

    def __init__(self, path, localtrack_folder, **kwargs):
        self._localtrack_folder = localtrack_folder
        self._path = path
        if isinstance(path, (Path, WindowsPath, PosixPath, LocalPath)):
            path = str(path.absolute())
        elif path is not None:
            path = str(path)

        self.cwd = Path.cwd()
        _lt_folder = Path(self._localtrack_folder) if self._localtrack_folder else self.cwd
        _path = Path(path) if path else self.cwd
        if _lt_folder.parts[-1].lower() == "localtracks" and not kwargs.get("forced"):
            self.localtrack_folder = _lt_folder
        elif kwargs.get("forced"):
            if _path.parts[-1].lower() == "localtracks":
                self.localtrack_folder = _path
            else:
                self.localtrack_folder = _path / "localtracks"
        else:
            self.localtrack_folder = _lt_folder / "localtracks"

        try:
            _path = Path(path)
            _path.relative_to(self.localtrack_folder)
            self.path = _path
        except (ValueError, TypeError):
            for sep in _PATH_SEPS:
                if path and path.startswith(f"localtracks{sep}{sep}"):
                    path = path.replace(f"localtracks{sep}{sep}", "", 1)
                elif path and path.startswith(f"localtracks{sep}"):
                    path = path.replace(f"localtracks{sep}", "", 1)
            self.path = self.localtrack_folder.joinpath(path) if path else self.localtrack_folder

        try:
            if self.path.is_file():
                parent = self.path.parent
            else:
                parent = self.path
            self.parent = Path(parent)
        except OSError:
            self.parent = None

    @property
    def name(self):
        return str(self.path.name)

    @property
    def suffix(self):
        return str(self.path.suffix)

    def is_dir(self):
        try:
            return self.path.is_dir()
        except OSError:
            return False

    def exists(self):
        try:
            return self.path.exists()
        except OSError:
            return False

    def is_file(self):
        try:
            return self.path.is_file()
        except OSError:
            return False

    def absolute(self):
        try:
            return self.path.absolute()
        except OSError:
            return self._path

    @classmethod
    def joinpath(cls, localpath, *args):
        modified = cls(None, localpath)
        modified.path = modified.path.joinpath(*args)
        return modified

    def rglob(self, pattern, folder=False) -> Iterator[str]:
        if folder:
            return glob.iglob(f"{glob.escape(self.path)}{os.sep}**{os.sep}", recursive=True)
        else:
            return glob.iglob(
                f"{glob.escape(self.path)}{os.sep}**{os.sep}*{pattern}", recursive=True
            )

    def glob(self, pattern, folder=False) -> Iterator[str]:
        if folder:
            return glob.iglob(f"{glob.escape(self.path)}{os.sep}*{os.sep}", recursive=False)
        else:
            return glob.iglob(f"{glob.escape(self.path)}{os.sep}*{pattern}", recursive=False)

    async def _multiglob(self, pattern: str, folder: bool, method: Callable):
        async for rp in AsyncIter(method(pattern)):
            rp_local = LocalPath(rp, self._localtrack_folder)
            if (
                (folder and rp_local.is_dir() and rp_local.exists())
                or (not folder and rp_local.suffix in self._all_music_ext and rp_local.is_file())
                and rp_local.exists()
            ):
                yield rp_local

    async def multiglob(self, *patterns, folder=False) -> AsyncIterator["LocalPath"]:
        async for p in AsyncIter(patterns):
            async for path in self._multiglob(p, folder, self.glob):
                yield path

    async def multirglob(self, *patterns, folder=False) -> AsyncIterator["LocalPath"]:
        async for p in AsyncIter(patterns):
            async for path in self._multiglob(p, folder, self.rglob):
                yield path

    def __str__(self):
        return self.to_string()

    def __repr__(self):
        return str(self)

    def to_string(self):
        try:
            return str(self.path.absolute())
        except OSError:
            return str(self._path)

    def to_string_user(self, arg: str = None):
        string = str(self.absolute()).replace(
            (str(self.localtrack_folder.absolute()) + os.sep) if arg is None else arg, ""
        )
        chunked = False
        while len(string) > 145 and os.sep in string:
            string = string.split(os.sep, 1)[-1]
            chunked = True

        if chunked:
            string = f"...{os.sep}{string}"
        return string

    async def tracks_in_tree(self):
        tracks = []
        async for track in self.multirglob(*[f"{ext}" for ext in self._all_music_ext]):
            with contextlib.suppress(ValueError):
                if track.path.parent != self.localtrack_folder and track.path.relative_to(
                    self.path
                ):
                    tracks.append(Query.process_input(track, self._localtrack_folder))
        return sorted(tracks, key=lambda x: x.to_string_user().lower())

    async def subfolders_in_tree(self):
        return_folders = []
        async for f in self.multirglob("", folder=True):
            with contextlib.suppress(ValueError):
                if (
                    f not in return_folders
                    and f.is_dir()
                    and f.path != self.localtrack_folder
                    and f.path.relative_to(self.path)
                ):
                    return_folders.append(f)
        return sorted(return_folders, key=lambda x: x.to_string_user().lower())

    async def tracks_in_folder(self):
        tracks = []
        async for track in self.multiglob(*[f"{ext}" for ext in self._all_music_ext]):
            with contextlib.suppress(ValueError):
                if track.path.parent != self.localtrack_folder and track.path.relative_to(
                    self.path
                ):
                    tracks.append(Query.process_input(track, self._localtrack_folder))
        return sorted(tracks, key=lambda x: x.to_string_user().lower())

    async def subfolders(self):
        return_folders = []
        async for f in self.multiglob("", folder=True):
            with contextlib.suppress(ValueError):
                if (
                    f not in return_folders
                    and f.path != self.localtrack_folder
                    and f.path.relative_to(self.path)
                ):
                    return_folders.append(f)
        return sorted(return_folders, key=lambda x: x.to_string_user().lower())

    def __eq__(self, other):
        if isinstance(other, LocalPath):
            return self.path._cparts == other.path._cparts
        elif isinstance(other, Path):
            return self.path._cparts == other._cpart
        return NotImplemented

    def __hash__(self):
        try:
            return self._hash
        except AttributeError:
            self._hash = hash(tuple(self.path._cparts))
            return self._hash

    def __lt__(self, other):
        if isinstance(other, LocalPath):
            return self.path._cparts < other.path._cparts
        elif isinstance(other, Path):
            return self.path._cparts < other._cpart
        return NotImplemented

    def __le__(self, other):
        if isinstance(other, LocalPath):
            return self.path._cparts <= other.path._cparts
        elif isinstance(other, Path):
            return self.path._cparts <= other._cpart
        return NotImplemented

    def __gt__(self, other):
        if isinstance(other, LocalPath):
            return self.path._cparts > other.path._cparts
        elif isinstance(other, Path):
            return self.path._cparts > other._cpart
        return NotImplemented

    def __ge__(self, other):
        if isinstance(other, LocalPath):
            return self.path._cparts >= other.path._cparts
        elif isinstance(other, Path):
            return self.path._cparts >= other._cpart
        return NotImplemented


class Query:
    """Query data class.

    Use: Query.process_input(query, localtrack_folder) to generate the Query object.
    """

    def __init__(self, query: Union[LocalPath, str], local_folder_current_path: Path, **kwargs):
        query = kwargs.get("queryforced", query)
        self._raw: Union[LocalPath, str] = query
        self._local_folder_current_path = local_folder_current_path
        _localtrack: LocalPath = LocalPath(query, local_folder_current_path)

        self.valid: bool = query != "InvalidQueryPlaceHolderName"
        self.is_local: bool = kwargs.get("local", False)
        self.is_spotify: bool = kwargs.get("spotify", False)
        self.is_youtube: bool = kwargs.get("youtube", False)
        self.is_soundcloud: bool = kwargs.get("soundcloud", False)
        self.is_bandcamp: bool = kwargs.get("bandcamp", False)
        self.is_vimeo: bool = kwargs.get("vimeo", False)
        self.is_mixer: bool = kwargs.get("mixer", False)
        self.is_twitch: bool = kwargs.get("twitch", False)
        self.is_other: bool = kwargs.get("other", False)
        self.is_pornhub: bool = kwargs.get("pornhub", False)
        self.is_playlist: bool = kwargs.get("playlist", False)
        self.is_album: bool = kwargs.get("album", False)
        self.is_search: bool = kwargs.get("search", False)
        self.is_stream: bool = kwargs.get("stream", False)
        self.single_track: bool = kwargs.get("single", False)
        self.id: Optional[str] = kwargs.get("id", None)
        self.invoked_from: Optional[str] = kwargs.get("invoked_from", None)
        self.local_name: Optional[str] = kwargs.get("name", None)
        self.search_subfolders: bool = kwargs.get("search_subfolders", False)
        self.spotify_uri: Optional[str] = kwargs.get("uri", None)
        self.uri: Optional[str] = kwargs.get("url", None)
        self.is_url: bool = kwargs.get("is_url", False)

        self.start_time: int = kwargs.get("start_time", 0)
        self.track_index: Optional[int] = kwargs.get("track_index", None)
        if self.invoked_from == "sc search":
            self.is_youtube = False
            self.is_soundcloud = True

        if (_localtrack.is_file() or _localtrack.is_dir()) and _localtrack.exists():
            self.local_track_path: Optional[LocalPath] = _localtrack
            self.track: str = str(_localtrack.absolute())
            self.is_local: bool = True
            self.uri = self.track
        else:
            self.local_track_path: Optional[LocalPath] = None
            self.track: str = str(query)

        self.lavalink_query: str = self._get_query()

        if self.is_playlist or self.is_album:
            self.single_track = False
        self._hash = hash(
            (
                self.valid,
                self.is_local,
                self.is_spotify,
                self.is_youtube,
                self.is_soundcloud,
                self.is_bandcamp,
                self.is_vimeo,
                self.is_mixer,
                self.is_twitch,
                self.is_other,
                self.is_playlist,
                self.is_album,
                self.is_search,
                self.is_stream,
                self.single_track,
                self.id,
                self.spotify_uri,
                self.start_time,
                self.track_index,
                self.uri,
            )
        )

    def __str__(self):
        return str(self.lavalink_query)

    @classmethod
    def process_input(
        cls,
        query: Union[LocalPath, lavalink.Track, "Query", str],
        _local_folder_current_path: Path,
        **kwargs,
    ) -> "Query":
        """Process the input query into its type.

        Parameters
        ----------
        query : Union[Query, LocalPath, lavalink.Track, str]
            The query string or LocalPath object.
        _local_folder_current_path: Path
            The Current Local Track folder
        Returns
        -------
        Query
            Returns a parsed Query object.
        """
        if not query:
            query = "InvalidQueryPlaceHolderName"
        possible_values = {}

        if isinstance(query, str):
            query = query.strip("<>")
            while "ytsearch:" in query:
                query = query.replace("ytsearch:", "")
            while "scsearch:" in query:
                query = query.replace("scsearch:", "")

        elif isinstance(query, Query):
            for key, val in kwargs.items():
                setattr(query, key, val)
            return query
        elif isinstance(query, lavalink.Track):
            possible_values["stream"] = query.is_stream
            query = query.uri

        possible_values.update(dict(**kwargs))
        possible_values.update(cls._parse(query, _local_folder_current_path, **kwargs))
        return cls(query, _local_folder_current_path, **possible_values)

    @staticmethod
    def _parse(track, _local_folder_current_path: Path, **kwargs) -> MutableMapping:
        """Parse a track into all the relevant metadata."""
        returning: MutableMapping = {}
        if (
            type(track) == type(LocalPath)
            and (track.is_file() or track.is_dir())
            and track.exists()
        ):
            returning["local"] = True
            returning["name"] = track.name
            if track.is_file():
                returning["single"] = True
            elif track.is_dir():
                returning["album"] = True
        else:
            track = str(track)
            if track.startswith("spotify:"):
                returning["spotify"] = True
                if ":playlist:" in track:
                    returning["playlist"] = True
                elif ":album:" in track:
                    returning["album"] = True
                elif ":track:" in track:
                    returning["single"] = True
                _id = track.split(":", 2)[-1]
                _id = _id.split("?")[0]
                returning["id"] = _id
                if "#" in _id:
                    match = re.search(_RE_SPOTIFY_TIMESTAMP, track)
                    if match:
                        returning["start_time"] = (int(match.group(1)) * 60) + int(match.group(2))
                returning["uri"] = track
                return returning
            if track.startswith("sc ") or track.startswith("list "):
                if track.startswith("sc "):
                    returning["invoked_from"] = "sc search"
                    returning["soundcloud"] = True
                elif track.startswith("list "):
                    returning["invoked_from"] = "search list"
                track = _RE_REMOVE_START.sub("", track, 1)
                returning["queryforced"] = track

            _localtrack = LocalPath(track, _local_folder_current_path)
            if _localtrack.exists():
                if _localtrack.is_file():
                    returning["local"] = True
                    returning["single"] = True
                    returning["name"] = _localtrack.name
                    return returning
                elif _localtrack.is_dir():
                    returning["album"] = True
                    returning["local"] = True
                    returning["name"] = _localtrack.name
                    return returning
            try:
                query_url = urlparse(track)
                if all([query_url.scheme, query_url.netloc, query_url.path]):
                    returning["url"] = track
                    returning["is_url"] = True
                    url_domain = ".".join(query_url.netloc.split(".")[-2:])
                    if not query_url.netloc:
                        url_domain = ".".join(query_url.path.split("/")[0].split(".")[-2:])
                    if url_domain in ["youtube.com", "youtu.be"]:
                        returning["youtube"] = True
                        _has_index = "&index=" in track
                        if "&t=" in track or "?t=" in track:
                            match = re.search(_RE_YOUTUBE_TIMESTAMP, track)
                            if match:
                                returning["start_time"] = int(match.group(1))
                        if _has_index:
                            match = re.search(_RE_YOUTUBE_INDEX, track)
                            if match:
                                returning["track_index"] = int(match.group(1)) - 1
                        if all(k in track for k in ["&list=", "watch?"]):
                            returning["track_index"] = 0
                            returning["playlist"] = True
                            returning["single"] = False
                        elif all(x in track for x in ["playlist?"]):
                            returning["playlist"] = not _has_index
                            returning["single"] = _has_index
                        elif any(k in track for k in ["list="]):
                            returning["track_index"] = 0
                            returning["playlist"] = True
                            returning["single"] = False
                        else:
                            returning["single"] = True
                    elif url_domain == "spotify.com":
                        returning["spotify"] = True
                        if "/playlist/" in track:
                            returning["playlist"] = True
                        elif "/album/" in track:
                            returning["album"] = True
                        elif "/track/" in track:
                            returning["single"] = True
                        val = re.sub(_RE_SPOTIFY_URL, "", track).replace("/", ":")
                        if "user:" in val:
                            val = val.split(":", 2)[-1]
                        _id = val.split(":", 1)[-1]
                        _id = _id.split("?")[0]

                        if "#" in _id:
                            _id = _id.split("#")[0]
                            match = re.search(_RE_SPOTIFY_TIMESTAMP, track)
                            if match:
                                returning["start_time"] = (int(match.group(1)) * 60) + int(
                                    match.group(2)
                                )

                        returning["id"] = _id
                        returning["uri"] = f"spotify:{val}"
                    elif url_domain == "soundcloud.com":
                        returning["soundcloud"] = True
                        if "#t=" in track:
                            match = re.search(_RE_SOUNDCLOUD_TIMESTAMP, track)
                            if match:
                                returning["start_time"] = (int(match.group(1)) * 60) + int(
                                    match.group(2)
                                )
                        if "/sets/" in track:
                            if "?in=" in track:
                                returning["single"] = True
                            else:
                                returning["playlist"] = True
                        else:
                            returning["single"] = True
                    elif url_domain == "bandcamp.com":
                        returning["bandcamp"] = True
                        if "/album/" in track:
                            returning["album"] = True
                        else:
                            returning["single"] = True
                    elif url_domain == "vimeo.com":
                        returning["vimeo"] = True
                    elif url_domain == "twitch.tv":
                        returning["twitch"] = True
                        if "?t=" in track:
                            match = re.search(_RE_TWITCH_TIMESTAMP, track)
                            if match:
                                returning["start_time"] = (
                                    (int(match.group(1)) * 60 * 60)
                                    + (int(match.group(2)) * 60)
                                    + int(match.group(3))
                                )

                        if not any(x in track for x in ["/clip/", "/videos/"]):
                            returning["stream"] = True
                    else:
                        returning["other"] = True
                        returning["single"] = True
                else:
                    if kwargs.get("soundcloud", False):
                        returning["soundcloud"] = True
                    else:
                        returning["youtube"] = True
                    returning["search"] = True
                    returning["single"] = True
            except Exception:
                returning["search"] = True
                returning["youtube"] = True
                returning["single"] = True
        return returning

    def _get_query(self):
        if self.is_local:
            return self.local_track_path.to_string()
        elif self.is_spotify:
            return self.spotify_uri
        elif self.is_search and self.is_youtube:
            return f"ytsearch:{self.track}"
        elif self.is_search and self.is_soundcloud:
            return f"scsearch:{self.track}"
        return self.track

    def to_string_user(self):
        if self.is_local:
            return str(self.local_track_path.to_string_user())
        return str(self._raw)

    @property
    def suffix(self):
        if self.is_local:
            return self.local_track_path.suffix
        return None

    def __eq__(self, other):
        if not isinstance(other, Query):
            return NotImplemented
        return self.to_string_user() == other.to_string_user()

    def __hash__(self):
        try:
            return self._hash
        except AttributeError:
            self._hash = hash(
                (
                    self.valid,
                    self.is_local,
                    self.is_spotify,
                    self.is_youtube,
                    self.is_soundcloud,
                    self.is_bandcamp,
                    self.is_vimeo,
                    self.is_mixer,
                    self.is_twitch,
                    self.is_other,
                    self.is_playlist,
                    self.is_album,
                    self.is_search,
                    self.is_stream,
                    self.single_track,
                    self.id,
                    self.spotify_uri,
                    self.start_time,
                    self.track_index,
                    self.uri,
                )
            )
            return self._hash

    def __lt__(self, other):
        if not isinstance(other, Query):
            return NotImplemented
        return self.to_string_user() < other.to_string_user()

    def __le__(self, other):
        if not isinstance(other, Query):
            return NotImplemented
        return self.to_string_user() <= other.to_string_user()

    def __gt__(self, other):
        if not isinstance(other, Query):
            return NotImplemented
        return self.to_string_user() > other.to_string_user()

    def __ge__(self, other):
        if not isinstance(other, Query):
            return NotImplemented
        return self.to_string_user() >= other.to_string_user()
