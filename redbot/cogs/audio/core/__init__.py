import asyncio
import datetime
import json

from collections import Counter, defaultdict
from pathlib import Path
from typing import Mapping, Dict

import aiohttp
import discord

from redbot.core import Config
from redbot.core.bot import Red
from redbot.core.commands import Cog
from redbot.core.data_manager import cog_data_path
from redbot.core.i18n import Translator, cog_i18n
from redbot.core.utils.antispam import AntiSpam

from ..utils import (
    CacheLevel,
    PlaylistScope,
    DEFAULT_LAVALINK_YAML,
    DEFAULT_LAVALINK_SETTINGS,
)
from . import abc, cog_utils, commands, events, tasks, utilities
from .cog_utils import CompositeMetaClass

_ = Translator("Audio", Path(__file__))


@cog_i18n(_)
class Audio(
    commands.Commands,
    events.Events,
    tasks.Tasks,
    utilities.Utilities,
    Cog,
    metaclass=CompositeMetaClass,
):
    """Play audio through voice channels."""

    llset_captcha_intervals = [
        (datetime.timedelta(days=1), 1),
    ]

    def __init__(self, bot: Red):
        super().__init__()
        self.bot = bot
        self.config = Config.get_conf(self, 2711759130, force_registration=True)

        self.api_interface = None
        self.managed_node_controller = None
        self.playlist_api = None
        self.local_folder_current_path = None
        self.db_conn = None

        self._error_counter = Counter()
        self._error_timer = {}
        self._disconnected_players = {}
        self._daily_playlist_cache = {}
        self._daily_global_playlist_cache = {}
        self._persist_queue_cache = {}
        self._dj_status_cache = {}
        self._dj_role_cache = {}
        self.skip_votes = {}
        self.play_lock = {}
        self.antispam: Dict[int, Dict[str, AntiSpam]] = defaultdict(lambda: defaultdict(AntiSpam))

        self.lavalink_connect_task = None
        self._restore_task = None
        self.player_automated_timer_task = None
        self.cog_cleaned_up = False
        self.lavalink_connection_aborted = False
        self.permission_cache = discord.Permissions(
            embed_links=True,
            read_messages=True,
            read_message_history=True,
            add_reactions=True,
        )

        self.session = aiohttp.ClientSession(json_serialize=json.dumps)
        self.cog_ready_event = asyncio.Event()
        self._ws_resume = defaultdict(asyncio.Event)
        self._ws_op_codes = defaultdict(asyncio.LifoQueue)

        self.cog_init_task = None
        self.global_api_user = {
            "fetched": False,
            "can_read": False,
            "can_post": False,
            "can_delete": False,
        }
        self._ll_guild_updates = set()
        self._disconnected_shard = set()
        self._last_ll_update = datetime.datetime.now(datetime.timezone.utc)

        default_global = dict(
            schema_version=1,
            bundled_playlist_version=0,
            owner_notification=0,
            cache_level=CacheLevel.all().value,
            cache_age=365,
            daily_playlists=False,
            global_db_enabled=False,
            global_db_get_timeout=5,
            status=False,
            use_external_lavalink=False,
            restrict=True,
            localpath=str(cog_data_path(raw_name="Audio")),
            url_keyword_blacklist=[],
            url_keyword_whitelist=[],
            java_exc_path="java",
            **DEFAULT_LAVALINK_YAML,
            **DEFAULT_LAVALINK_SETTINGS,
        )

        default_guild = dict(
            auto_play=False,
            currently_auto_playing_in=None,
            auto_deafen=True,
            autoplaylist=dict(
                enabled=True,
                id=42069,
                name="Aikaterna's curated tracks",
                scope=PlaylistScope.GLOBAL.value,
            ),
            persist_queue=True,
            disconnect=False,
            dj_enabled=False,
            dj_role=None,
            daily_playlists=False,
            emptydc_enabled=False,
            emptydc_timer=0,
            emptypause_enabled=False,
            emptypause_timer=0,
            jukebox=False,
            jukebox_price=0,
            maxlength=0,
            max_volume=150,
            notify=False,
            prefer_lyrics=False,
            repeat=False,
            shuffle=False,
            shuffle_bumped=True,
            thumbnail=False,
            volume=100,
            vote_enabled=False,
            vote_percent=0,
            room_lock=None,
            url_keyword_blacklist=[],
            url_keyword_whitelist=[],
            country_code="US",
        )
        _playlist: Mapping = dict(id=None, author=None, name=None, playlist_url=None, tracks=[])

        self.config.init_custom("EQUALIZER", 1)
        self.config.register_custom("EQUALIZER", eq_bands=[], eq_presets={})
        self.config.init_custom(PlaylistScope.GLOBAL.value, 1)
        self.config.register_custom(PlaylistScope.GLOBAL.value, **_playlist)
        self.config.init_custom(PlaylistScope.GUILD.value, 2)
        self.config.register_custom(PlaylistScope.GUILD.value, **_playlist)
        self.config.init_custom(PlaylistScope.USER.value, 2)
        self.config.register_custom(PlaylistScope.USER.value, **_playlist)
        self.config.register_guild(**default_guild)
        self.config.register_global(**default_global)
        self.config.register_user(country_code=None)
