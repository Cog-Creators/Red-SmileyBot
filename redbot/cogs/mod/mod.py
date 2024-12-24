import asyncio
import logging
import re
from abc import ABC
from collections import defaultdict
from typing import Literal

from redbot.core import Config, commands
from redbot.core.bot import Red
from redbot.core.i18n import Translator, cog_i18n
from redbot.core.utils import AsyncIter
from redbot.core.utils._internal_utils import send_to_owners_with_prefix_replaced
from redbot.core.utils.chat_formatting import inline
from .events import Events
from .kickban import KickBanMixin
from .names import ModInfo
from .slowmode import Slowmode
from .settings import ModSettings

_ = T_ = Translator("Mod", __file__)

__version__ = "1.2.0"


class CompositeMetaClass(type(commands.Cog), type(ABC)):
    """
    This allows the metaclass used for proper type detection to
    coexist with discord.py's metaclass
    """

    pass


@cog_i18n(_)
class Mod(
    ModSettings,
    Events,
    KickBanMixin,
    ModInfo,
    Slowmode,
    commands.Cog,
    metaclass=CompositeMetaClass,
):
    """Moderation tools."""

    default_global_settings = {
        "version": "",
        "track_all_names": True,
    }

    default_guild_settings = {
        "mention_spam": {"ban": None, "kick": None, "warn": None, "strict": False},
        "delete_repeats": -1,
        "ignored": False,
        "respect_hierarchy": True,
        "delete_delay": -1,
        "reinvite_on_unban": False,
        "current_tempbans": [],
        "dm_on_kickban": False,
        "require_reason": False,
        "default_days": 0,
        "default_tempban_duration": 60 * 60 * 24,
        "track_nicknames": True,
    }

    default_channel_settings = {"ignored": False}

    default_member_settings = {"past_nicks": [], "perms_cache": {}, "banned_until": False}

    default_user_settings = {"past_names": [], "past_display_names": []}

    def __init__(self, bot: Red):
        super().__init__()
        self.bot = bot

        self.config = Config.get_conf(self, 4961522000, force_registration=True)
        self.config.register_global(**self.default_global_settings)
        self.config.register_guild(**self.default_guild_settings)
        self.config.register_channel(**self.default_channel_settings)
        self.config.register_member(**self.default_member_settings)
        self.config.register_user(**self.default_user_settings)
        self.cache: dict = {}
        self.tban_expiry_task = asyncio.create_task(self.tempban_expirations_task())
        self.last_case: dict = defaultdict(dict)

    async def red_delete_data_for_user(
        self,
        *,
        requester: Literal["discord_deleted_user", "owner", "user", "user_strict"],
        user_id: int,
    ):
        if requester != "discord_deleted_user":
            return

        all_members = await self.config.all_members()

        async for guild_id, guild_data in AsyncIter(all_members.items(), steps=100):
            if user_id in guild_data:
                await self.config.member_from_ids(guild_id, user_id).clear()

        await self.config.user_from_id(user_id).clear()

        guild_data = await self.config.all_guilds()

        async for guild_id, guild_data in AsyncIter(guild_data.items(), steps=100):
            if user_id in guild_data["current_tempbans"]:
                async with self.config.guild_from_id(guild_id).current_tempbans() as tbs:
                    try:
                        tbs.remove(user_id)
                    except ValueError:
                        pass
                    # possible with a context switch between here and getting all guilds

    async def cog_load(self) -> None:
        await self._maybe_update_config()

    def cog_unload(self):
        self.tban_expiry_task.cancel()

    async def _maybe_update_config(self):
        """Maybe update `delete_delay` value set by Config prior to Mod 1.0.0."""
        if not await self.config.version():
            guild_dict = await self.config.all_guilds()
            async for guild_id, info in AsyncIter(guild_dict.items(), steps=25):
                delete_repeats = info.get("delete_repeats", False)
                if delete_repeats:
                    val = 3
                else:
                    val = -1
                await self.config.guild_from_id(guild_id).delete_repeats.set(val)
            await self.config.version.set("1.0.0")  # set version of last update
        if await self.config.version() < "1.1.0":
            message_sent = False
            async for e in AsyncIter((await self.config.all_channels()).values(), steps=25):
                if e["ignored"] is not False:
                    msg = _(
                        "Ignored guilds and channels have been moved. "
                        "Please use {command} to migrate the old settings."
                    ).format(command=inline("[p]moveignoredchannels"))
                    asyncio.create_task(send_to_owners_with_prefix_replaced(self.bot, msg))
                    message_sent = True
                    break
            if message_sent is False:
                async for e in AsyncIter((await self.config.all_guilds()).values(), steps=25):
                    if e["ignored"] is not False:
                        msg = _(
                            "Ignored guilds and channels have been moved. "
                            "Please use {command} to migrate the old settings."
                        ).format(command=inline("[p]moveignoredchannels"))
                        asyncio.create_task(send_to_owners_with_prefix_replaced(self.bot, msg))
                        break
            await self.config.version.set("1.1.0")
        if await self.config.version() < "1.2.0":
            async for e in AsyncIter((await self.config.all_guilds()).values(), steps=25):
                if e["delete_delay"] != -1:
                    msg = _(
                        "Delete delay settings have been moved. "
                        "Please use {command} to migrate the old settings."
                    ).format(command=inline("[p]movedeletedelay"))
                    asyncio.create_task(send_to_owners_with_prefix_replaced(self.bot, msg))
                    break
            await self.config.version.set("1.2.0")
        if await self.config.version() < "1.3.0":
            guild_dict = await self.config.all_guilds()
            async for guild_id in AsyncIter(guild_dict.keys(), steps=25):
                async with self.config.guild_from_id(guild_id).all() as guild_data:
                    current_state = guild_data.pop("ban_mention_spam", False)
                    if current_state is not False:
                        if "mention_spam" not in guild_data:
                            guild_data["mention_spam"] = {}
                        guild_data["mention_spam"]["ban"] = current_state
            await self.config.version.set("1.3.0")

    @commands.command(hidden=True)
    @commands.is_owner()
    async def moveignoredchannels(self, ctx: commands.Context) -> None:
        """Move ignored channels and servers to core"""
        all_guilds = await self.config.all_guilds()
        all_channels = await self.config.all_channels()
        for guild_id, settings in all_guilds.items():
            await self.bot._config.guild_from_id(guild_id).ignored.set(settings["ignored"])
            await self.config.guild_from_id(guild_id).ignored.clear()
        for channel_id, settings in all_channels.items():
            await self.bot._config.channel_from_id(channel_id).ignored.set(settings["ignored"])
            await self.config.channel_from_id(channel_id).clear()
        await ctx.send(_("Ignored channels and guilds restored."))

    @commands.command(hidden=True)
    @commands.is_owner()
    async def movedeletedelay(self, ctx: commands.Context) -> None:
        """
        Move deletedelay settings to core
        """
        all_guilds = await self.config.all_guilds()
        for guild_id, settings in all_guilds.items():
            await self.bot._config.guild_from_id(guild_id).delete_delay.set(
                settings["delete_delay"]
            )
            await self.config.guild_from_id(guild_id).delete_delay.clear()
        await ctx.send(_("Delete delay settings restored."))
