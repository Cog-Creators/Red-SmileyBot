import datetime
import json
from collections import namedtuple
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, MutableMapping, Optional, Union

import discord
import lavalink
from red_commons.logging import getLogger

from redbot.core.bot import Red
from redbot.core.i18n import Translator
from redbot.core.utils.chat_formatting import humanize_list

from ..errors import InvalidPlaylistScope, MissingAuthor, MissingGuild
from ..utils import PlaylistScope

log = getLogger("red.cogs.Audio.api.utils")
_ = Translator("Audio", Path(__file__))


@dataclass
class YouTubeCacheFetchResult:
    query: Optional[str]
    last_updated: int

    def __post_init__(self):
        if isinstance(self.last_updated, int):
            self.updated_on: datetime.datetime = datetime.datetime.fromtimestamp(self.last_updated)


@dataclass
class SpotifyCacheFetchResult:
    query: Optional[str]
    last_updated: int

    def __post_init__(self):
        if isinstance(self.last_updated, int):
            self.updated_on: datetime.datetime = datetime.datetime.fromtimestamp(self.last_updated)


@dataclass
class LavalinkCacheFetchResult:
    query: Optional[MutableMapping]
    last_updated: int

    def __post_init__(self):
        if isinstance(self.last_updated, int):
            self.updated_on: datetime.datetime = datetime.datetime.fromtimestamp(self.last_updated)

        if isinstance(self.query, str):
            self.query = json.loads(self.query)


@dataclass
class LavalinkCacheFetchForGlobalResult:
    query: str
    data: MutableMapping

    def __post_init__(self):
        if isinstance(self.data, str):
            self.data_string = str(self.data)
            self.data = json.loads(self.data)


@dataclass
class PlaylistFetchResult:
    playlist_id: int
    playlist_name: str
    scope_id: int
    author_id: int
    playlist_url: Optional[str] = None
    tracks: List[MutableMapping] = field(default_factory=lambda: [])

    def __post_init__(self):
        if isinstance(self.tracks, str):
            self.tracks = json.loads(self.tracks)


@dataclass
class QueueFetchResult:
    guild_id: int
    room_id: int
    track: dict = field(default_factory=lambda: {})
    track_object: lavalink.Track = None

    def __post_init__(self):
        if isinstance(self.track, str):
            self.track = json.loads(self.track)
        if self.track:
            self.track_object = lavalink.Track(self.track)


def standardize_scope(scope: str) -> str:
    """Convert any of the used scopes into one we are expecting."""
    scope = scope.upper()
    valid_scopes = ["GLOBAL", "GUILD", "AUTHOR", "USER", "SERVER", "MEMBER", "BOT"]

    if scope in PlaylistScope.list():
        return scope
    elif scope not in valid_scopes:
        raise InvalidPlaylistScope(
            f'"{scope}" is not a valid playlist scope.'
            f" Scope needs to be one of the following: {humanize_list(valid_scopes)}"
        )

    if scope in ["GLOBAL", "BOT"]:
        scope = PlaylistScope.GLOBAL.value
    elif scope in ["GUILD", "SERVER"]:
        scope = PlaylistScope.GUILD.value
    elif scope in ["USER", "MEMBER", "AUTHOR"]:
        scope = PlaylistScope.USER.value

    return scope


def prepare_config_scope(
    bot: Red,
    scope,
    author: Union[discord.abc.User, int] = None,
    guild: Union[discord.Guild, int] = None,
):
    """Return the scope used by Playlists."""
    scope = standardize_scope(scope)
    if scope == PlaylistScope.GLOBAL.value:
        config_scope = [PlaylistScope.GLOBAL.value, bot.user.id]
    elif scope == PlaylistScope.USER.value:
        if author is None:
            raise MissingAuthor("Invalid author for user scope.")
        config_scope = [PlaylistScope.USER.value, int(getattr(author, "id", author))]
    else:
        if guild is None:
            raise MissingGuild("Invalid guild for guild scope.")
        config_scope = [PlaylistScope.GUILD.value, int(getattr(guild, "id", guild))]
    return config_scope


def prepare_config_scope_for_migration23(  # TODO: remove me in a future version ?
    scope, author: Union[discord.abc.User, int] = None, guild: discord.Guild = None
):
    """Return the scope used by Playlists."""
    scope = standardize_scope(scope)

    if scope == PlaylistScope.GLOBAL.value:
        config_scope = [PlaylistScope.GLOBAL.value]
    elif scope == PlaylistScope.USER.value:
        if author is None:
            raise MissingAuthor("Invalid author for user scope.")
        config_scope = [PlaylistScope.USER.value, str(getattr(author, "id", author))]
    else:
        if guild is None:
            raise MissingGuild("Invalid guild for guild scope.")
        config_scope = [PlaylistScope.GUILD.value, str(getattr(guild, "id", guild))]
    return config_scope


FakePlaylist = namedtuple("Playlist", "author scope")
