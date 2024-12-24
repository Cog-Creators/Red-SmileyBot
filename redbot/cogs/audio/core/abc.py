from __future__ import annotations

import asyncio
import datetime

from abc import ABC, abstractmethod
from collections import Counter, defaultdict
from pathlib import Path
from typing import (
    Set,
    TYPE_CHECKING,
    Any,
    List,
    Mapping,
    MutableMapping,
    Optional,
    Tuple,
    Union,
    Dict,
)

import aiohttp
import discord
import lavalink

from redbot.core import Config, commands
from redbot.core.bot import Red
from redbot.core.commands import Context
from redbot.core.utils.antispam import AntiSpam
from redbot.core.utils.dbtools import APSWConnectionWrapper

if TYPE_CHECKING:
    from ..apis.interface import AudioAPIInterface
    from ..apis.playlist_interface import Playlist
    from ..apis.playlist_wrapper import PlaylistWrapper
    from ..audio_dataclasses import LocalPath, Query
    from ..equalizer import Equalizer
    from ..manager import ServerManager


class MixinMeta(ABC):
    """Base class for well behaved type hint detection with composite class.

    Basically, to keep developers sane when not all attributes are defined in each mixin.
    """

    bot: Red
    config: Config
    api_interface: Optional["AudioAPIInterface"]
    managed_node_controller: Optional["ServerManager"]
    playlist_api: Optional["PlaylistWrapper"]
    local_folder_current_path: Optional[Path]
    db_conn: Optional[APSWConnectionWrapper]
    session: aiohttp.ClientSession
    antispam: Dict[int, Dict[str, AntiSpam]]
    llset_captcha_intervals: List[Tuple[datetime.timedelta, int]]

    skip_votes: MutableMapping[int, Set[int]]
    play_lock: MutableMapping[int, bool]
    _daily_playlist_cache: MutableMapping[int, bool]
    _daily_global_playlist_cache: MutableMapping[int, bool]
    _persist_queue_cache: MutableMapping[int, bool]
    _dj_status_cache: MutableMapping[int, Optional[bool]]
    _dj_role_cache: MutableMapping[int, Optional[int]]
    _error_timer: MutableMapping[int, float]
    _disconnected_players: MutableMapping[int, bool]
    global_api_user: MutableMapping[str, Any]

    cog_cleaned_up: bool
    lavalink_connection_aborted: bool

    _error_counter: Counter

    lavalink_connect_task: Optional[asyncio.Task]
    _restore_task: Optional[asyncio.Task]
    player_automated_timer_task: Optional[asyncio.Task]
    cog_init_task: Optional[asyncio.Task]
    cog_ready_event: asyncio.Event
    _ws_resume: defaultdict[Any, asyncio.Event]
    _ws_op_codes: defaultdict[int, asyncio.LifoQueue]
    permission_cache = discord.Permissions

    _last_ll_update: datetime.datetime
    _ll_guild_updates: Set[int]
    _disconnected_shard: Set[int]

    @abstractmethod
    async def command_llset(self, ctx: commands.Context):
        raise NotImplementedError()

    @commands.command()
    @abstractmethod
    async def command_audioset_restart(self, ctx: commands.Context):
        raise NotImplementedError()

    @abstractmethod
    async def maybe_reset_error_counter(self, player: lavalink.Player) -> None:
        raise NotImplementedError()

    @abstractmethod
    async def update_bot_presence(self, track: lavalink.Track, playing_servers: int) -> None:
        raise NotImplementedError()

    @abstractmethod
    async def get_active_player_count(self) -> Tuple[str, int]:
        raise NotImplementedError()

    @abstractmethod
    async def increase_error_counter(self, player: lavalink.Player) -> bool:
        raise NotImplementedError()

    @abstractmethod
    async def _close_database(self) -> None:
        raise NotImplementedError()

    @abstractmethod
    async def maybe_run_pending_db_tasks(self, ctx: commands.Context) -> None:
        raise NotImplementedError()

    @abstractmethod
    def update_player_lock(self, ctx: commands.Context, true_or_false: bool) -> None:
        raise NotImplementedError()

    @abstractmethod
    async def initialize(self) -> None:
        raise NotImplementedError()

    @abstractmethod
    async def data_schema_migration(self, from_version: int, to_version: int) -> None:
        raise NotImplementedError()

    @abstractmethod
    def lavalink_restart_connect(self, manual: bool = False) -> None:
        raise NotImplementedError()

    @abstractmethod
    async def lavalink_attempt_connect(self, timeout: int = 50) -> None:
        raise NotImplementedError()

    @abstractmethod
    async def player_automated_timer(self) -> None:
        raise NotImplementedError()

    @abstractmethod
    async def lavalink_event_handler(
        self, player: lavalink.Player, event_type: lavalink.LavalinkEvents, extra
    ) -> None:
        raise NotImplementedError()

    @abstractmethod
    async def lavalink_update_handler(
        self, player: lavalink.Player, event_type: lavalink.enums.PlayerState, extra
    ) -> None:
        raise NotImplementedError()

    @abstractmethod
    async def _clear_react(
        self, message: discord.Message, emoji: MutableMapping = None
    ) -> asyncio.Task:
        raise NotImplementedError()

    @abstractmethod
    async def remove_react(
        self,
        message: discord.Message,
        react_emoji: Union[discord.Emoji, discord.Reaction, discord.PartialEmoji, str],
        react_user: discord.abc.User,
    ) -> None:
        raise NotImplementedError()

    @abstractmethod
    async def command_equalizer(self, ctx: commands.Context):
        raise NotImplementedError()

    @abstractmethod
    async def _eq_msg_clear(self, eq_message: discord.Message) -> None:
        raise NotImplementedError()

    @abstractmethod
    def _player_check(self, ctx: commands.Context) -> bool:
        raise NotImplementedError()

    @abstractmethod
    async def maybe_charge_requester(self, ctx: commands.Context, jukebox_price: int) -> bool:
        raise NotImplementedError()

    @abstractmethod
    async def _can_instaskip(self, ctx: commands.Context, member: discord.Member) -> bool:
        raise NotImplementedError()

    @abstractmethod
    async def command_search(self, ctx: commands.Context, *, query: str):
        raise NotImplementedError()

    @abstractmethod
    async def is_query_allowed(
        self,
        config: Config,
        ctx_or_channel: Optional[
            Union[
                Context,
                discord.TextChannel,
                discord.VoiceChannel,
                discord.StageChannel,
                discord.Thread,
            ]
        ],
        query: str,
        query_obj: Query,
    ) -> bool:
        raise NotImplementedError()

    @abstractmethod
    def is_track_length_allowed(self, track: Union[lavalink.Track, int], maxlength: int) -> bool:
        raise NotImplementedError()

    @abstractmethod
    async def get_track_description(
        self,
        track: Union[lavalink.rest_api.Track, "Query"],
        local_folder_current_path: Path,
        shorten: bool = False,
    ) -> Optional[str]:
        raise NotImplementedError()

    @abstractmethod
    async def get_track_description_unformatted(
        self, track: Union[lavalink.rest_api.Track, "Query"], local_folder_current_path: Path
    ) -> Optional[str]:
        raise NotImplementedError()

    @abstractmethod
    def humanize_scope(
        self, scope: str, ctx: Union[discord.Guild, discord.abc.User, str] = None, the: bool = None
    ) -> Optional[str]:
        raise NotImplementedError()

    @abstractmethod
    async def draw_time(self, ctx) -> str:
        raise NotImplementedError()

    @abstractmethod
    def rsetattr(self, obj, attr, val) -> None:
        raise NotImplementedError()

    @abstractmethod
    def rgetattr(self, obj, attr, *args) -> Any:
        raise NotImplementedError()

    @abstractmethod
    async def _check_api_tokens(self) -> MutableMapping:
        raise NotImplementedError()

    @abstractmethod
    async def send_embed_msg(
        self, ctx: commands.Context, author: Mapping[str, str] = None, **kwargs
    ) -> discord.Message:
        raise NotImplementedError()

    @abstractmethod
    def _has_notify_perms(
        self,
        channel: Union[
            discord.TextChannel, discord.VoiceChannel, discord.StageChannel, discord.Thread
        ],
    ) -> bool:
        raise NotImplementedError()

    @abstractmethod
    async def update_external_status(self) -> bool:
        raise NotImplementedError()

    @abstractmethod
    def get_track_json(
        self,
        player: lavalink.Player,
        position: Union[int, str] = None,
        other_track: lavalink.Track = None,
    ) -> MutableMapping:
        raise NotImplementedError()

    @abstractmethod
    def track_to_json(self, track: lavalink.Track) -> MutableMapping:
        raise NotImplementedError()

    @abstractmethod
    def time_convert(self, length: Union[int, str]) -> int:
        raise NotImplementedError()

    @abstractmethod
    async def queue_duration(self, ctx: commands.Context) -> int:
        raise NotImplementedError()

    @abstractmethod
    async def track_remaining_duration(self, ctx: commands.Context) -> int:
        raise NotImplementedError()

    @abstractmethod
    def get_time_string(self, seconds: int) -> str:
        raise NotImplementedError()

    @abstractmethod
    async def set_player_settings(self, ctx: commands.Context) -> None:
        raise NotImplementedError()

    @abstractmethod
    async def get_playlist_match(
        self,
        context: commands.Context,
        matches: MutableMapping,
        scope: str,
        author: discord.User,
        guild: discord.Guild,
        specified_user: bool = False,
    ) -> Tuple[Optional["Playlist"], str, str]:
        raise NotImplementedError()

    @abstractmethod
    async def is_requester_alone(self, ctx: commands.Context) -> bool:
        raise NotImplementedError()

    @abstractmethod
    async def is_requester(self, ctx: commands.Context, member: discord.Member) -> bool:
        raise NotImplementedError()

    @abstractmethod
    async def _skip_action(self, ctx: commands.Context, skip_to_track: int = None) -> None:
        raise NotImplementedError()

    @abstractmethod
    def is_vc_full(self, channel: discord.VoiceChannel) -> bool:
        raise NotImplementedError()

    @abstractmethod
    async def _has_dj_role(self, ctx: commands.Context, member: discord.Member) -> bool:
        raise NotImplementedError()

    @abstractmethod
    def match_url(self, url: str) -> bool:
        raise NotImplementedError()

    @abstractmethod
    async def _playlist_check(self, ctx: commands.Context) -> bool:
        raise NotImplementedError()

    @abstractmethod
    async def _build_bundled_playlist(self, forced: bool = None) -> None:
        raise NotImplementedError()

    @abstractmethod
    def decode_track(self, track: str, decode_errors: str = "") -> MutableMapping:
        raise NotImplementedError()

    @abstractmethod
    async def can_manage_playlist(
        self,
        scope: str,
        playlist: "Playlist",
        ctx: commands.Context,
        user,
        guild,
        bypass: bool = False,
    ) -> bool:
        raise NotImplementedError()

    @abstractmethod
    async def _maybe_update_playlist(
        self, ctx: commands.Context, player: lavalink.player.Player, playlist: "Playlist"
    ) -> Tuple[List[lavalink.Track], List[lavalink.Track], "Playlist"]:
        raise NotImplementedError()

    @abstractmethod
    def is_url_allowed(self, url: str) -> bool:
        raise NotImplementedError()

    @abstractmethod
    async def _eq_check(self, ctx: commands.Context, player: lavalink.Player) -> None:
        raise NotImplementedError()

    @abstractmethod
    async def _enqueue_tracks(
        self, ctx: commands.Context, query: Union["Query", list], enqueue: bool = True
    ) -> Union[discord.Message, List[lavalink.Track], lavalink.Track]:
        raise NotImplementedError()

    @abstractmethod
    async def _eq_interact(
        self,
        ctx: commands.Context,
        player: lavalink.Player,
        eq: "Equalizer",
        message: discord.Message,
        selected: int,
    ) -> None:
        raise NotImplementedError()

    @abstractmethod
    async def _apply_gains(self, guild_id: int, gains: List[float]) -> None:
        NotImplementedError()

    @abstractmethod
    async def _apply_gain(self, guild_id: int, band: int, gain: float) -> None:
        raise NotImplementedError()

    @abstractmethod
    async def _get_spotify_tracks(
        self, ctx: commands.Context, query: "Query", forced: bool = False
    ) -> Union[discord.Message, List[lavalink.Track], lavalink.Track]:
        raise NotImplementedError()

    @abstractmethod
    async def _genre_search_button_action(
        self, ctx: commands.Context, options: List, emoji: str, page: int, playlist: bool = False
    ) -> str:
        raise NotImplementedError()

    @abstractmethod
    async def _build_genre_search_page(
        self,
        ctx: commands.Context,
        tracks: List,
        page_num: int,
        title: str,
        playlist: bool = False,
    ) -> discord.Embed:
        raise NotImplementedError()

    @abstractmethod
    async def command_audioset_autoplay_toggle(self, ctx: commands.Context):
        raise NotImplementedError()

    @abstractmethod
    async def _search_button_action(
        self, ctx: commands.Context, tracks: List, emoji: str, page: int
    ):
        raise NotImplementedError()

    @abstractmethod
    async def get_localtrack_folder_tracks(
        self, ctx, player: lavalink.player.Player, query: "Query"
    ) -> List[lavalink.rest_api.Track]:
        raise NotImplementedError()

    @abstractmethod
    async def get_localtrack_folder_list(
        self, ctx: commands.Context, query: "Query"
    ) -> List["Query"]:
        raise NotImplementedError()

    @abstractmethod
    async def _local_play_all(
        self, ctx: commands.Context, query: "Query", from_search: bool = False
    ) -> None:
        raise NotImplementedError()

    @abstractmethod
    async def _build_search_page(
        self, ctx: commands.Context, tracks: List, page_num: int
    ) -> discord.Embed:
        raise NotImplementedError()

    @abstractmethod
    async def command_play(self, ctx: commands.Context, *, query: str):
        raise NotImplementedError()

    @abstractmethod
    async def localtracks_folder_exists(self, ctx: commands.Context) -> bool:
        raise NotImplementedError()

    @abstractmethod
    async def get_localtracks_folders(
        self, ctx: commands.Context, search_subfolders: bool = False
    ) -> List[Union[Path, "LocalPath"]]:
        raise NotImplementedError()

    @abstractmethod
    async def _build_local_search_list(
        self, to_search: List["Query"], search_words: str
    ) -> List[str]:
        raise NotImplementedError()

    @abstractmethod
    async def command_stop(self, ctx: commands.Context):
        raise NotImplementedError()

    @abstractmethod
    async def _build_queue_page(
        self,
        ctx: commands.Context,
        queue: list,
        player: lavalink.player.Player,
        page_num: int,
    ) -> discord.Embed:
        raise NotImplementedError()

    @abstractmethod
    async def command_pause(self, ctx: commands.Context):
        raise NotImplementedError()

    @abstractmethod
    async def _build_queue_search_list(
        self, queue_list: List[lavalink.Track], search_words: str
    ) -> List[Tuple[int, str]]:
        raise NotImplementedError()

    @abstractmethod
    async def _build_queue_search_page(
        self, ctx: commands.Context, page_num: int, search_list: List[Tuple[int, str]]
    ) -> discord.Embed:
        raise NotImplementedError()

    @abstractmethod
    async def fetch_playlist_tracks(
        self,
        ctx: commands.Context,
        player: lavalink.player.Player,
        query: "Query",
        skip_cache: bool = False,
    ) -> Union[discord.Message, None, List[MutableMapping]]:
        raise NotImplementedError()

    @abstractmethod
    async def _build_playlist_list_page(
        self, ctx: commands.Context, page_num: int, abc_names: List, scope: Optional[str]
    ) -> discord.Embed:
        raise NotImplementedError()

    @abstractmethod
    def match_yt_playlist(self, url: str) -> bool:
        raise NotImplementedError()

    @abstractmethod
    async def _load_v3_playlist(
        self,
        ctx: commands.Context,
        scope: str,
        uploaded_playlist_name: str,
        uploaded_playlist_url: str,
        track_list: List,
        author: Union[discord.User, discord.Member],
        guild: Union[discord.Guild],
    ) -> None:
        raise NotImplementedError()

    @abstractmethod
    async def _load_v2_playlist(
        self,
        ctx: commands.Context,
        uploaded_track_list,
        player: lavalink.player.Player,
        playlist_url: str,
        uploaded_playlist_name: str,
        scope: str,
        author: Union[discord.User, discord.Member],
        guild: Union[discord.Guild],
    ):
        raise NotImplementedError()

    @abstractmethod
    def format_time(self, time: int) -> str:
        raise NotImplementedError()

    @abstractmethod
    async def get_lyrics_status(self, ctx: Context) -> bool:
        raise NotImplementedError()

    @abstractmethod
    async def restore_players(self) -> bool:
        raise NotImplementedError()

    @abstractmethod
    async def command_skip(self, ctx: commands.Context, skip_to_track: int = None):
        raise NotImplementedError()

    @abstractmethod
    async def command_prev(self, ctx: commands.Context):
        raise NotImplementedError()

    @abstractmethod
    async def icyparser(self, url: str) -> Optional[str]:
        raise NotImplementedError()

    @abstractmethod
    async def self_deafen(self, player: lavalink.Player) -> None:
        raise NotImplementedError()

    @abstractmethod
    def can_join_and_speak(self, channel: discord.VoiceChannel) -> bool:
        raise NotImplementedError()
