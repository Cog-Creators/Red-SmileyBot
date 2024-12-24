from pathlib import Path

from typing import List, MutableMapping, Optional, Union

import discord
import lavalink
from red_commons.logging import getLogger

from redbot.core import Config, commands
from redbot.core.bot import Red
from redbot.core.i18n import Translator
from redbot.core.utils import AsyncIter

from ..errors import NotAllowed
from ..utils import PlaylistScope
from .api_utils import PlaylistFetchResult, prepare_config_scope, standardize_scope
from .playlist_wrapper import PlaylistWrapper

log = getLogger("red.cogs.Audio.api.PlaylistsInterface")
_ = Translator("Audio", Path(__file__))


class Playlist:
    """A single playlist."""

    def __init__(
        self,
        bot: Red,
        playlist_api: PlaylistWrapper,
        scope: str,
        author: int,
        playlist_id: int,
        name: str,
        playlist_url: Optional[str] = None,
        tracks: Optional[List[MutableMapping]] = None,
        guild: Union[discord.Guild, int, None] = None,
    ):
        self.bot = bot
        self.guild = guild
        self.scope = standardize_scope(scope)
        self.config_scope = prepare_config_scope(self.bot, self.scope, author, guild)
        self.scope_id = self.config_scope[-1]
        self.author = author
        self.author_id = getattr(self.author, "id", self.author)
        self.guild_id = (
            getattr(guild, "id", guild) if self.scope == PlaylistScope.GLOBAL.value else None
        )
        self.id = playlist_id
        self.name = name
        self.url = playlist_url
        self.tracks = tracks or []
        self.tracks_obj = [lavalink.Track(data=track) for track in self.tracks]
        self.playlist_api = playlist_api

    def __repr__(self):
        return (
            f"Playlist(name={self.name}, id={self.id}, scope={self.scope}, "
            f"scope_id={self.scope_id}, author={self.author_id}, "
            f"tracks={len(self.tracks)}, url={self.url})"
        )

    async def edit(self, data: MutableMapping):
        """
        Edits a Playlist.
        Parameters
        ----------
        data: dict
            The attributes to change.
        """
        # Disallow ID editing
        if "id" in data:
            raise NotAllowed("Playlist ID cannot be edited.")

        for item in list(data.keys()):
            setattr(self, item, data[item])
        await self.save()
        return self

    async def save(self):
        """Saves a Playlist."""
        scope, scope_id = self.config_scope
        await self.playlist_api.upsert(
            scope,
            playlist_id=int(self.id),
            playlist_name=self.name,
            scope_id=scope_id,
            author_id=self.author_id,
            playlist_url=self.url,
            tracks=self.tracks,
        )

    def to_json(self) -> MutableMapping:
        """Transform the object to a dict.
        Returns
        -------
        dict
            The playlist in the form of a dict.
        """
        data = dict(
            id=self.id,
            author=self.author_id,
            guild=self.guild_id,
            name=self.name,
            playlist_url=self.url,
            tracks=self.tracks,
        )

        return data

    @classmethod
    async def from_json(
        cls,
        bot: Red,
        playlist_api: PlaylistWrapper,
        scope: str,
        playlist_number: int,
        data: PlaylistFetchResult,
        **kwargs,
    ) -> "Playlist":
        """Get a Playlist object from the provided information.
        Parameters
        ----------
        bot: Red
            The bot's instance. Needed to get the target user.
        playlist_api: PlaylistWrapper
            The Playlist API interface.
        scope:str
            The custom config scope. One of 'GLOBALPLAYLIST', 'GUILDPLAYLIST' or 'USERPLAYLIST'.
        playlist_number: int
            The playlist's number.
        data: PlaylistFetchResult
            The PlaylistFetchResult representation of the playlist to be gotten.
        **kwargs
            Extra attributes for the Playlist instance which override values
            in the data dict. These should be complete objects and not
            IDs, where possible.
        Returns
        -------
        Playlist
            The playlist object for the requested playlist.
        Raises
        ------
        `InvalidPlaylistScope`
            Passing a scope that is not supported.
        `MissingGuild`
            Trying to access the Guild scope without a guild.
        `MissingAuthor`
            Trying to access the User scope without an user id.
        """
        guild = data.scope_id if scope == PlaylistScope.GUILD.value else kwargs.get("guild")
        author = data.author_id
        playlist_id = data.playlist_id or playlist_number
        name = data.playlist_name
        playlist_url = data.playlist_url
        tracks = data.tracks

        return cls(
            bot=bot,
            playlist_api=playlist_api,
            guild=guild,
            scope=scope,
            author=author,
            playlist_id=playlist_id,
            name=name,
            playlist_url=playlist_url,
            tracks=tracks,
        )


class PlaylistCompat23:
    """A single playlist, migrating from Schema 2 to Schema 3"""

    def __init__(
        self,
        bot: Red,
        playlist_api: PlaylistWrapper,
        scope: str,
        author: int,
        playlist_id: int,
        name: str,
        playlist_url: Optional[str] = None,
        tracks: Optional[List[MutableMapping]] = None,
        guild: Union[discord.Guild, int, None] = None,
    ):
        self.bot = bot
        self.guild = guild
        self.scope = standardize_scope(scope)
        self.author = author
        self.id = playlist_id
        self.name = name
        self.url = playlist_url
        self.tracks = tracks or []

        self.playlist_api = playlist_api

    @classmethod
    async def from_json(
        cls,
        bot: Red,
        playlist_api: PlaylistWrapper,
        scope: str,
        playlist_number: int,
        data: MutableMapping,
        **kwargs,
    ) -> "PlaylistCompat23":
        """Get a Playlist object from the provided information.
        Parameters
        ----------
        bot: Red
            The Bot instance.
        playlist_api: PlaylistWrapper
            The Playlist API interface.
        scope:str
            The custom config scope. One of 'GLOBALPLAYLIST', 'GUILDPLAYLIST' or 'USERPLAYLIST'.
        playlist_number: int
            The playlist's number.
        data: MutableMapping
            The JSON representation of the playlist to be gotten.
        **kwargs
            Extra attributes for the Playlist instance which override values
            in the data dict. These should be complete objects and not
            IDs, where possible.
        Returns
        -------
        Playlist
            The playlist object for the requested playlist.
        Raises
        ------
        `InvalidPlaylistScope`
            Passing a scope that is not supported.
        `MissingGuild`
            Trying to access the Guild scope without a guild.
        `MissingAuthor`
            Trying to access the User scope without an user id.
        """
        guild = data.get("guild") or kwargs.get("guild")
        author: int = data.get("author") or kwargs.get("author") or 0
        playlist_id = data.get("id") or playlist_number
        name = data.get("name", "Unnamed")
        playlist_url = data.get("playlist_url", None)
        tracks = data.get("tracks", [])

        return cls(
            bot=bot,
            playlist_api=playlist_api,
            guild=guild,
            scope=scope,
            author=author,
            playlist_id=playlist_id,
            name=name,
            playlist_url=playlist_url,
            tracks=tracks,
        )

    async def save(self):
        """Saves a Playlist to SQL."""
        scope, scope_id = prepare_config_scope(self.bot, self.scope, self.author, self.guild)
        await self.playlist_api.upsert(
            scope,
            playlist_id=int(self.id),
            playlist_name=self.name,
            scope_id=scope_id,
            author_id=self.author,
            playlist_url=self.url,
            tracks=self.tracks,
        )


async def get_all_playlist_for_migration23(
    bot: Red,
    playlist_api: PlaylistWrapper,
    config: Config,
    scope: str,
    guild: Union[discord.Guild, int] = None,
) -> List[PlaylistCompat23]:
    """
    Gets all playlist for the specified scope.
    Parameters
    ----------
    bot: Red
        The Bot instance.
    playlist_api: PlaylistWrapper
        The Playlist API interface.
    config: Config
        The Audio cog Config instance.
    scope: str
        The custom config scope. One of 'GLOBALPLAYLIST', 'GUILDPLAYLIST' or 'USERPLAYLIST'.
    guild: discord.Guild
        The guild to get the playlist from if scope is GUILDPLAYLIST.
    Returns
    -------
    list
        A list of all playlists for the specified scope
    Raises
    ------
    `InvalidPlaylistScope`
        Passing a scope that is not supported.
    `MissingGuild`
        Trying to access the Guild scope without a guild.
    `MissingAuthor`
        Trying to access the User scope without an user id.
    """
    playlists = await config.custom(scope).all()
    if scope == PlaylistScope.GLOBAL.value:
        return [
            await PlaylistCompat23.from_json(
                bot,
                playlist_api,
                scope,
                playlist_number,
                playlist_data,
                guild=guild,
                author=int(playlist_data.get("author", 0)),
            )
            async for playlist_number, playlist_data in AsyncIter(playlists.items())
        ]
    elif scope == PlaylistScope.USER.value:
        return [
            await PlaylistCompat23.from_json(
                bot,
                playlist_api,
                scope,
                playlist_number,
                playlist_data,
                guild=guild,
                author=int(user_id),
            )
            async for user_id, scopedata in AsyncIter(playlists.items())
            async for playlist_number, playlist_data in AsyncIter(scopedata.items())
        ]
    else:
        return [
            await PlaylistCompat23.from_json(
                bot,
                playlist_api,
                scope,
                playlist_number,
                playlist_data,
                guild=int(guild_id),
                author=int(playlist_data.get("author", 0)),
            )
            async for guild_id, scopedata in AsyncIter(playlists.items())
            async for playlist_number, playlist_data in AsyncIter(scopedata.items())
        ]


async def get_playlist(
    playlist_number: int,
    scope: str,
    bot: Red,
    playlist_api: PlaylistWrapper,
    guild: Union[discord.Guild, int] = None,
    author: Union[discord.abc.User, int] = None,
) -> Playlist:
    """
    Gets the playlist with the associated playlist number.
    Parameters
    ----------
    playlist_number: int
        The playlist number for the playlist to get.
    playlist_api: PlaylistWrapper
        The Playlist API interface.
    scope: str
        The custom config scope. One of 'GLOBALPLAYLIST', 'GUILDPLAYLIST' or 'USERPLAYLIST'.
    guild: discord.Guild
        The guild to get the playlist from if scope is GUILDPLAYLIST.
    author: int
        The ID of the user to get the playlist from if scope is USERPLAYLIST.
    bot: Red
        The bot's instance.
    Returns
    -------
    Playlist
        The playlist associated with the playlist number.
    Raises
    ------
    `RuntimeError`
        If there is no playlist for the specified number.
    `InvalidPlaylistScope`
        Passing a scope that is not supported.
    `MissingGuild`
        Trying to access the Guild scope without a guild.
    `MissingAuthor`
        Trying to access the User scope without an user id.
    """
    scope_standard, scope_id = prepare_config_scope(bot, scope, author, guild)
    playlist_data = await playlist_api.fetch(scope_standard, playlist_number, scope_id)

    if not (playlist_data and playlist_data.playlist_id):
        raise RuntimeError(f"That playlist does not exist for the following scope: {scope}")
    return await Playlist.from_json(
        bot,
        playlist_api,
        scope_standard,
        playlist_number,
        playlist_data,
        guild=guild,
        author=author,
    )


async def get_all_playlist(
    scope: str,
    bot: Red,
    playlist_api: PlaylistWrapper,
    guild: Union[discord.Guild, int] = None,
    author: Union[discord.abc.User, int] = None,
    specified_user: bool = False,
) -> List[Playlist]:
    """
    Gets all playlist for the specified scope.
    Parameters
    ----------
    scope: str
        The custom config scope. One of 'GLOBALPLAYLIST', 'GUILDPLAYLIST' or 'USERPLAYLIST'.
    guild: discord.Guild
        The guild to get the playlist from if scope is GUILDPLAYLIST.
    author: int
        The ID of the user to get the playlist from if scope is USERPLAYLIST.
    bot: Red
        The bot's instance
    playlist_api: PlaylistWrapper
        The Playlist API interface.
    specified_user:bool
        Whether or not user ID was passed as an argparse.
    Returns
    -------
    list
        A list of all playlists for the specified scope
    Raises
    ------
    `InvalidPlaylistScope`
        Passing a scope that is not supported.
    `MissingGuild`
        Trying to access the Guild scope without a guild.
    `MissingAuthor`
        Trying to access the User scope without an user id.
    """
    scope_standard, scope_id = prepare_config_scope(bot, scope, author, guild)

    if specified_user:
        user_id = getattr(author, "id", author)
        playlists = await playlist_api.fetch_all(scope_standard, scope_id, author_id=user_id)
    else:
        playlists = await playlist_api.fetch_all(scope_standard, scope_id)

    playlist_list = []
    async for playlist in AsyncIter(playlists):
        playlist_list.append(
            await Playlist.from_json(
                bot,
                playlist_api,
                scope,
                playlist.playlist_id,
                playlist,
                guild=guild,
                author=author,
            )
        )
    return playlist_list


async def get_all_playlist_converter(
    scope: str,
    bot: Red,
    playlist_api: PlaylistWrapper,
    arg: str,
    guild: Union[discord.Guild, int] = None,
    author: Union[discord.abc.User, int] = None,
) -> List[Playlist]:
    """
    Gets all playlist for the specified scope.
    Parameters
    ----------
    scope: str
        The custom config scope. One of 'GLOBALPLAYLIST', 'GUILDPLAYLIST' or 'USERPLAYLIST'.
    guild: discord.Guild
        The guild to get the playlist from if scope is GUILDPLAYLIST.
    author: int
        The ID of the user to get the playlist from if scope is USERPLAYLIST.
    bot: Red
        The bot's instance
    arg:str
        The value to lookup.
    playlist_api: PlaylistWrapper
        The Playlist API interface.
    Returns
    -------
    list
        A list of all playlists for the specified scope
    Raises
    ------
    `InvalidPlaylistScope`
        Passing a scope that is not supported.
    `MissingGuild`
        Trying to access the Guild scope without a guild.
    `MissingAuthor`
        Trying to access the User scope without an user id.
    """
    scope_standard, scope_id = prepare_config_scope(bot, scope, author, guild)
    playlists = await playlist_api.fetch_all_converter(
        scope_standard, playlist_name=arg, playlist_id=arg
    )
    playlist_list = []
    async for playlist in AsyncIter(playlists):
        playlist_list.append(
            await Playlist.from_json(
                bot,
                playlist_api,
                scope,
                playlist.playlist_id,
                playlist,
                guild=guild,
                author=author,
            )
        )
    return playlist_list


async def create_playlist(
    ctx: commands.Context,
    playlist_api: PlaylistWrapper,
    scope: str,
    playlist_name: str,
    playlist_url: Optional[str] = None,
    tracks: Optional[List[MutableMapping]] = None,
    author: Optional[discord.User] = None,
    guild: Optional[discord.Guild] = None,
) -> Optional[Playlist]:
    """Creates a new Playlist.

    Parameters
    ----------
    ctx: commands.Context
        The context in which the play list is being created.
    scope: str
        The custom config scope. One of 'GLOBALPLAYLIST', 'GUILDPLAYLIST' or 'USERPLAYLIST'.
    playlist_name: str
        The name of the new playlist.
    playlist_url:str
        the url of the new playlist.
    tracks: List[MutableMapping]
        A list of tracks to add to the playlist.
    author: discord.User
        The Author of the playlist.
        If provided it will create a playlist under this user.
        This is only required when creating a playlist in User scope.
    guild: discord.Guild
        The guild to create this playlist under.
         This is only used when creating a playlist in the Guild scope
    playlist_api: PlaylistWrapper
        The Playlist API interface.

    Raises
    ------
    `InvalidPlaylistScope`
        Passing a scope that is not supported.
    `MissingGuild`
        Trying to access the Guild scope without a guild.
    `MissingAuthor`
        Trying to access the User scope without an user id.
    """

    playlist = Playlist(
        ctx.bot,
        playlist_api,
        scope,
        author.id if author else None,
        ctx.message.id,
        playlist_name,
        playlist_url,
        tracks,
        guild or ctx.guild,
    )
    await playlist.save()
    return playlist


async def reset_playlist(
    bot: Red,
    playlist_api: PlaylistWrapper,
    scope: str,
    guild: Union[discord.Guild, int] = None,
    author: Union[discord.abc.User, int] = None,
) -> None:
    """Wipes all playlists for the specified scope.

    Parameters
    ----------
    bot: Red
        The bot's instance
    scope: str
        The custom config scope. One of 'GLOBALPLAYLIST', 'GUILDPLAYLIST' or 'USERPLAYLIST'.
    guild: discord.Guild
        The guild to get the playlist from if scope is GUILDPLAYLIST.
    author: int
        The ID of the user to get the playlist from if scope is USERPLAYLIST.
    playlist_api: PlaylistWrapper
        The Playlist API interface.

    Raises
    ------
    `InvalidPlaylistScope`
        Passing a scope that is not supported.
    `MissingGuild`
        Trying to access the Guild scope without a guild.
    `MissingAuthor`
        Trying to access the User scope without an user id.
    """
    scope, scope_id = prepare_config_scope(bot, scope, author, guild)
    await playlist_api.drop(scope)
    await playlist_api.create_table()


async def delete_playlist(
    bot: Red,
    playlist_api: PlaylistWrapper,
    scope: str,
    playlist_id: Union[str, int],
    guild: discord.Guild,
    author: Union[discord.abc.User, int] = None,
) -> None:
    """Deletes the specified playlist.

    Parameters
    ----------
    bot: Red
        The bot's instance
    scope: str
        The custom config scope. One of 'GLOBALPLAYLIST', 'GUILDPLAYLIST' or 'USERPLAYLIST'.
    playlist_id: Union[str, int]
        The ID of the playlist.
    guild: discord.Guild
        The guild to get the playlist from if scope is GUILDPLAYLIST.
    author: int
        The ID of the user to get the playlist from if scope is USERPLAYLIST.
    playlist_api: PlaylistWrapper
        The Playlist API interface.

    Raises
    ------
    `InvalidPlaylistScope`
        Passing a scope that is not supported.
    `MissingGuild`
        Trying to access the Guild scope without a guild.
    `MissingAuthor`
        Trying to access the User scope without an user id.
    """
    scope, scope_id = prepare_config_scope(bot, scope, author, guild)
    await playlist_api.delete(scope, int(playlist_id), scope_id)
