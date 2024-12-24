import contextlib

from pathlib import Path
from typing import List, Union

import discord
import lavalink
from red_commons.logging import getLogger

import rapidfuzz
from redbot.core import commands
from redbot.core.i18n import Translator
from redbot.core.utils import AsyncIter

from ...audio_dataclasses import LocalPath, Query
from ...errors import TrackEnqueueError
from ..abc import MixinMeta
from ..cog_utils import CompositeMetaClass

log = getLogger("red.cogs.Audio.cog.Utilities.local_tracks")
_ = Translator("Audio", Path(__file__))


class LocalTrackUtilities(MixinMeta, metaclass=CompositeMetaClass):
    async def get_localtracks_folders(
        self, ctx: commands.Context, search_subfolders: bool = True
    ) -> List[Union[Path, LocalPath]]:
        audio_data = LocalPath(None, self.local_folder_current_path)
        if not await self.localtracks_folder_exists(ctx):
            return []

        return (
            await audio_data.subfolders_in_tree()
            if search_subfolders
            else await audio_data.subfolders()
        )

    async def get_localtrack_folder_list(self, ctx: commands.Context, query: Query) -> List[Query]:
        """Return a list of folders per the provided query."""
        if not await self.localtracks_folder_exists(ctx):
            return []
        query = Query.process_input(query, self.local_folder_current_path)
        if not query.is_local or query.local_track_path is None:
            return []
        if not query.local_track_path.exists():
            return []
        return (
            await query.local_track_path.tracks_in_tree()
            if query.search_subfolders
            else await query.local_track_path.tracks_in_folder()
        )

    async def get_localtrack_folder_tracks(
        self, ctx, player: lavalink.player.Player, query: Query
    ) -> List[lavalink.rest_api.Track]:
        """Return a list of tracks per the provided query."""
        if not await self.localtracks_folder_exists(ctx) or self.api_interface is None:
            return []

        audio_data = LocalPath(None, self.local_folder_current_path)
        try:
            if query.local_track_path is not None:
                query.local_track_path.path.relative_to(audio_data.to_string())
            else:
                return []
        except ValueError:
            return []
        local_tracks = []
        async for local_file in AsyncIter(await self.get_all_localtrack_folder_tracks(ctx, query)):
            with contextlib.suppress(IndexError, TrackEnqueueError):
                trackdata, called_api = await self.api_interface.fetch_track(
                    ctx, player, local_file
                )
                local_tracks.append(trackdata.tracks[0])
        return local_tracks

    async def _local_play_all(
        self, ctx: commands.Context, query: Query, from_search: bool = False
    ) -> None:
        if not await self.localtracks_folder_exists(ctx) or query.local_track_path is None:
            return None
        if from_search:
            query = Query.process_input(
                query.local_track_path.to_string(),
                self.local_folder_current_path,
                invoked_from="local folder",
            )
        await ctx.invoke(self.command_search, query=query)

    async def get_all_localtrack_folder_tracks(
        self, ctx: commands.Context, query: Query
    ) -> List[Query]:
        if not await self.localtracks_folder_exists(ctx) or query.local_track_path is None:
            return []
        return (
            await query.local_track_path.tracks_in_tree()
            if query.search_subfolders
            else await query.local_track_path.tracks_in_folder()
        )

    async def localtracks_folder_exists(self, ctx: commands.Context) -> bool:
        folder = LocalPath(None, self.local_folder_current_path)
        if folder.localtrack_folder is None:
            return False
        elif folder.localtrack_folder.exists():
            return True
        elif ctx.invoked_with != "start":
            await self.send_embed_msg(
                ctx, title=_("Invalid Environment"), description=_("No localtracks folder.")
            )
        return False

    async def _build_local_search_list(
        self, to_search: List[Query], search_words: str
    ) -> List[str]:
        to_search_string = {
            i.local_track_path.name for i in to_search if i.local_track_path is not None
        }
        search_results = rapidfuzz.process.extract(
            search_words, to_search_string, limit=50, processor=rapidfuzz.utils.default_process
        )
        search_list = []
        async for track_match, percent_match, __ in AsyncIter(search_results):
            if percent_match > 85:
                search_list.extend(
                    [
                        i.to_string_user()
                        for i in to_search
                        if i.local_track_path is not None
                        and i.local_track_path.name == track_match
                    ]
                )
        return search_list
