import asyncio
import contextlib
import math
import platform
import re
import sys
import time

from enum import Enum, unique
from pathlib import Path
from typing import Any, MutableMapping, Tuple, Union

import discord
import psutil
from red_commons.logging import getLogger

from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.i18n import Translator

from .managed_node.ll_server_config import DEFAULT_LAVALINK_YAML, change_dict_naming_convention

log = getLogger("red.cogs.Audio.task.callback")
_ = Translator("Audio", Path(__file__))


def get_max_allocation_size(exec) -> Tuple[int, bool]:
    if platform.architecture(exec)[0] == "64bit":
        max_heap_allowed = psutil.virtual_memory().total
        thinks_is_64_bit = True
    else:
        max_heap_allowed = min(4 * 1024**3, psutil.virtual_memory().total)
        thinks_is_64_bit = False
    return max_heap_allowed, thinks_is_64_bit


def get_jar_ram_defaults() -> Tuple[str, str]:
    min_ram = 64 * 1024**2
    # We don't know the java executable at this stage - not worth the extra work required here
    max_allocation, is_64bit = get_max_allocation_size(sys.executable)
    max_ram_allowed = min(max_allocation, psutil.virtual_memory().total * 0.5)
    max_ram = max(min_ram, max_ram_allowed)
    size_name = ("", "K", "M", "G", "T")
    i = int(math.floor(math.log(min_ram, 1024)))
    p = math.pow(1024, i)
    s = int(min_ram // p)
    min_ram = f"{s}{size_name[i]}"

    i = int(math.floor(math.log(max_ram, 1024)))
    p = math.pow(1024, i)
    s = int(max_ram // p)
    max_ram = f"{s}{size_name[i]}"

    return min_ram, max_ram


MIN_JAVA_RAM, MAX_JAVA_RAM = get_jar_ram_defaults()

DEFAULT_LAVALINK_SETTINGS = {
    "host": DEFAULT_LAVALINK_YAML["yaml__server__address"],
    "rest_port": DEFAULT_LAVALINK_YAML["yaml__server__port"],
    "ws_port": DEFAULT_LAVALINK_YAML["yaml__server__port"],
    "password": DEFAULT_LAVALINK_YAML["yaml__lavalink__server__password"],
    "secured_ws": False,
    "java__Xms": MIN_JAVA_RAM,
    "java__Xmx": MAX_JAVA_RAM,
}


def sizeof_fmt(num: Union[float, int]) -> str:
    for unit in ["", "K", "M", "G", "T", "P", "E", "Z"]:
        if abs(num) < 1024.0:
            return f"{num:3.1f}{unit}"
        num /= 1024.0
    return f"{num:.1f}Y"


class CacheLevel:
    __slots__ = ("value",)

    def __init__(self, level=0):
        if not isinstance(level, int):
            raise TypeError(
                f"Expected int parameter, received {level.__class__.__name__} instead."
            )
        elif level < 0:
            level = 0
        elif level > 0b11111:
            level = 0b11111

        self.value = level

    def __eq__(self, other):
        return isinstance(other, CacheLevel) and self.value == other.value

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self.value)

    def __add__(self, other):
        return CacheLevel(self.value + other.value)

    def __radd__(self, other):
        return CacheLevel(other.value + self.value)

    def __sub__(self, other):
        return CacheLevel(self.value - other.value)

    def __rsub__(self, other):
        return CacheLevel(other.value - self.value)

    def __str__(self):
        return "{0:b}".format(self.value)

    def __format__(self, format_spec):
        return "{r:{f}}".format(r=self.value, f=format_spec)

    def __repr__(self):
        return f"<CacheLevel value={self.value}>"

    def is_subset(self, other):
        """Returns ``True`` if self has the same or fewer caching levels as other."""
        return (self.value & other.value) == self.value

    def is_superset(self, other):
        """Returns ``True`` if self has the same or more caching levels as other."""
        return (self.value | other.value) == self.value

    def is_strict_subset(self, other):
        """Returns ``True`` if the caching level on other are a strict subset of those on self."""
        return self.is_subset(other) and self != other

    def is_strict_superset(self, other):
        """Returns ``True`` if the caching level on
        other are a strict superset of those on self."""
        return self.is_superset(other) and self != other

    __le__ = is_subset
    __ge__ = is_superset
    __lt__ = is_strict_subset
    __gt__ = is_strict_superset

    @classmethod
    def all(cls):
        """A factory method that creates a :class:`CacheLevel` with max caching level."""
        return cls(0b11111)

    @classmethod
    def none(cls):
        """A factory method that creates a :class:`CacheLevel` with no caching."""
        return cls(0)

    @classmethod
    def set_spotify(cls):
        """A factory method that creates a :class:`CacheLevel` with Spotify caching level."""
        return cls(0b00011)

    @classmethod
    def set_youtube(cls):
        """A factory method that creates a :class:`CacheLevel` with YouTube caching level."""
        return cls(0b00100)

    @classmethod
    def set_lavalink(cls):
        """A factory method that creates a :class:`CacheLevel` with lavalink caching level."""
        return cls(0b11000)

    def _bit(self, index):
        return bool((self.value >> index) & 1)

    def _set(self, index, value):
        if value is True:
            self.value |= 1 << index
        elif value is False:
            self.value &= ~(1 << index)
        else:
            raise TypeError("Value to set for CacheLevel must be a bool.")

    @property
    def lavalink(self):
        """:class:`bool`: Returns ``True`` if a user can deafen other users."""
        return self._bit(4)

    @lavalink.setter
    def lavalink(self, value):
        self._set(4, value)

    @property
    def youtube(self):
        """:class:`bool`: Returns ``True`` if a user can move users between other voice
        channels."""
        return self._bit(2)

    @youtube.setter
    def youtube(self, value):
        self._set(2, value)

    @property
    def spotify(self):
        """:class:`bool`: Returns ``True`` if a user can use voice activation in voice channels."""
        return self._bit(1)

    @spotify.setter
    def spotify(self, value):
        self._set(1, value)


class Notifier:
    def __init__(
        self, ctx: commands.Context, message: discord.Message, updates: MutableMapping, **kwargs
    ):
        self.context = ctx
        self.message = message
        self.updates = updates
        self.color = None
        self.last_msg_time = 0
        self.cooldown = 5

    async def notify_user(
        self,
        current: int = None,
        total: int = None,
        key: str = None,
        seconds_key: str = None,
        seconds: str = None,
    ):
        """This updates an existing message.

        Based on the message found in :variable:`Notifier.updates` as per the `key` param
        """
        if self.last_msg_time + self.cooldown > time.time() and not current == total:
            return
        if self.color is None:
            self.color = await self.context.embed_colour()
        embed2 = discord.Embed(
            colour=self.color,
            title=self.updates.get(key, "").format(num=current, total=total, seconds=seconds),
        )
        if seconds and seconds_key:
            embed2.set_footer(text=self.updates.get(seconds_key, "").format(seconds=seconds))
        try:
            await self.message.edit(embed=embed2)
            self.last_msg_time = int(time.time())
        except discord.errors.NotFound:
            pass

    async def update_text(self, text: str):
        embed2 = discord.Embed(colour=self.color, title=text)
        try:
            await self.message.edit(embed=embed2)
        except discord.errors.NotFound:
            pass

    async def update_embed(self, embed: discord.Embed):
        try:
            await self.message.edit(embed=embed)
            self.last_msg_time = int(time.time())
        except discord.errors.NotFound:
            pass


@unique
class PlaylistScope(Enum):
    GLOBAL = "GLOBALPLAYLIST"
    GUILD = "GUILDPLAYLIST"
    USER = "USERPLAYLIST"

    def __str__(self):
        return "{0}".format(self.value)

    @staticmethod
    def list():
        return list(map(lambda c: c.value, PlaylistScope))


def has_managed_server():
    async def pred(ctx: commands.Context):
        if ctx.cog is None:
            return True
        external = await ctx.cog.config.use_external_lavalink()
        return not external

    return commands.check(pred)


def has_unmanaged_server():
    async def pred(ctx: commands.Context):
        if ctx.cog is None:
            return True
        external = await ctx.cog.config.use_external_lavalink()
        return external

    return commands.check(pred)


async def replace_p_with_prefix(bot: Red, message: str) -> str:
    """Replaces [p] with the bot prefix"""
    prefixes = await bot.get_valid_prefixes()
    prefix = re.sub(rf"<@!?{bot.user.id}>", f"@{bot.user.name}".replace("\\", r"\\"), prefixes[0])
    return message.replace("[p]", prefix)
