from typing import Tuple, Dict, Optional, List, Union
from re import findall

import discord
from discord.ext.commands.view import StringView  # DEP-WARN
from redbot.core import commands, Config
from redbot.core.i18n import Translator
from redbot.core.utils import AsyncIter

_ = Translator("Alias", __file__)


class ArgParseError(Exception):
    pass


class AliasEntry:
    """An object containing all required information about an alias"""

    name: str
    command: Union[Tuple[str], str]
    creator: int
    guild: Optional[int]
    uses: int

    def __init__(
        self, name: str, command: Union[Tuple[str], str], creator: int, guild: Optional[int]
    ):
        super().__init__()
        self.name = name
        self.command = command
        self.creator = creator

        self.guild = guild
        self.uses = 0

    def inc(self):
        """
        Increases the `uses` stat by 1.
        :return: new use count
        """
        self.uses += 1
        return self.uses

    def get_extra_args_from_alias(self, message: discord.Message, prefix: str) -> str:
        """
        When an alias is executed by a user in chat this function tries
            to get any extra arguments passed in with the call.
            Whitespace will be trimmed from both ends.
        :param message:
        :param prefix:
        :param alias:
        :return:
        """
        known_content_length = len(prefix) + len(self.name)
        extra = message.content[known_content_length:]
        view = StringView(extra)
        view.skip_ws()
        extra = []
        while not view.eof:
            prev = view.index
            word = view.get_quoted_word()
            if len(word) < view.index - prev:
                word = "".join((view.buffer[prev], word, view.buffer[view.index - 1]))
            extra.append(word.strip(" "))
        return extra

    def to_json(self) -> dict:
        return {
            "name": self.name,
            "command": self.command,
            "creator": self.creator,
            "guild": self.guild,
            "uses": self.uses,
        }

    @classmethod
    def from_json(cls, data: dict):
        ret = cls(data["name"], data["command"], data["creator"], data["guild"])
        ret.uses = data.get("uses", 0)
        return ret


class AliasCache:
    def __init__(self, config: Config, cache_enabled: bool = True):
        self.config = config
        self._cache_enabled = cache_enabled
        self._loaded = False
        self._aliases: Dict[Optional[int], Dict[str, AliasEntry]] = {None: {}}

    async def anonymize_aliases(self, user_id: int):
        async with self.config.entries() as global_aliases:
            for a in global_aliases:
                if a.get("creator", 0) == user_id:
                    a["creator"] = 0xDE1
                    if self._cache_enabled:
                        self._aliases[None][a["name"]] = AliasEntry.from_json(a)

        all_guilds = await self.config.all_guilds()
        async for guild_id, guild_data in AsyncIter(all_guilds.items(), steps=100):
            for a in guild_data["entries"]:
                if a.get("creator", 0) == user_id:
                    break
            else:
                continue
            # basically, don't build a context manager without a need.
            async with self.config.guild_from_id(guild_id).entries() as entry_list:
                for a in entry_list:
                    if a.get("creator", 0) == user_id:
                        a["creator"] = 0xDE1
                        if self._cache_enabled:
                            self._aliases[guild_id][a["name"]] = AliasEntry.from_json(a)

    async def load_aliases(self):
        if not self._cache_enabled:
            self._loaded = True
            return
        for alias in await self.config.entries():
            self._aliases[None][alias["name"]] = AliasEntry.from_json(alias)

        all_guilds = await self.config.all_guilds()
        async for guild_id, guild_data in AsyncIter(all_guilds.items(), steps=100):
            if guild_id not in self._aliases:
                self._aliases[guild_id] = {}
            for alias in guild_data["entries"]:
                self._aliases[guild_id][alias["name"]] = AliasEntry.from_json(alias)
        self._loaded = True

    async def get_aliases(self, ctx: commands.Context) -> List[AliasEntry]:
        """Returns all possible aliases with the given context"""
        global_aliases: List[AliasEntry] = []
        server_aliases: List[AliasEntry] = []
        global_aliases = await self.get_global_aliases()
        if ctx.guild and ctx.guild.id in self._aliases:
            server_aliases = await self.get_guild_aliases(ctx.guild)
        return global_aliases + server_aliases

    async def get_guild_aliases(self, guild: discord.Guild) -> List[AliasEntry]:
        """Returns all guild specific aliases"""
        aliases: List[AliasEntry] = []

        if self._cache_enabled:
            if guild.id in self._aliases:
                for _, alias in self._aliases[guild.id].items():
                    aliases.append(alias)
        else:
            aliases = [AliasEntry.from_json(d) for d in await self.config.guild(guild).entries()]
        return aliases

    async def get_global_aliases(self) -> List[AliasEntry]:
        """Returns all global specific aliases"""
        aliases: List[AliasEntry] = []
        if self._cache_enabled:
            for _, alias in self._aliases[None].items():
                aliases.append(alias)
        else:
            aliases = [AliasEntry.from_json(d) for d in await self.config.entries()]
        return aliases

    async def get_alias(
        self, guild: Optional[discord.Guild], alias_name: str
    ) -> Optional[AliasEntry]:
        """Returns an AliasEntry object if the provided alias_name is a registered alias"""
        server_aliases: List[AliasEntry] = []

        if self._cache_enabled:
            if alias_name in self._aliases[None]:
                return self._aliases[None][alias_name]
            if guild is not None:
                if guild.id in self._aliases:
                    if alias_name in self._aliases[guild.id]:
                        return self._aliases[guild.id][alias_name]
        else:
            if guild:
                server_aliases = [
                    AliasEntry.from_json(d) for d in await self.config.guild(guild.id).entries()
                ]
            global_aliases = [AliasEntry.from_json(d) for d in await self.config.entries()]
            all_aliases = global_aliases + server_aliases

            for alias in all_aliases:
                if alias.name == alias_name:
                    return alias

        return None

    @staticmethod
    def format_command_for_alias(command: str) -> str:
        # This was present in add_alias previously
        # Made this into a separate method so as to reuse the same code in edit_alias
        indices = findall(r"{(\d*)}", command)
        if indices:
            try:
                indices = [int(a[0]) for a in indices]
            except IndexError:
                raise ArgParseError(_("Arguments must be specified with a number."))
            low = min(indices)
            indices = [a - low for a in indices]
            high = max(indices)
            gaps = set(indices).symmetric_difference(range(high + 1))
            if gaps:
                raise ArgParseError(
                    _("Arguments must be sequential. Missing arguments: ")
                    + ", ".join(str(i + low) for i in gaps)
                )
            command = command.format(*(f"{{{i}}}" for i in range(-low, high + low + 1)))
        return command

    async def add_alias(
        self, ctx: commands.Context, alias_name: str, command: str, global_: bool = False
    ) -> AliasEntry:
        command = self.format_command_for_alias(command)

        if global_:
            alias = AliasEntry(alias_name, command, ctx.author.id, None)
            settings = self.config
            if self._cache_enabled:
                self._aliases[None][alias.name] = alias
        else:
            alias = AliasEntry(alias_name, command, ctx.author.id, ctx.guild.id)
            settings = self.config.guild(ctx.guild)
            if self._cache_enabled:
                if ctx.guild.id not in self._aliases:
                    self._aliases[ctx.guild.id] = {}
                self._aliases[ctx.guild.id][alias.name] = alias

        async with settings.entries() as curr_aliases:
            curr_aliases.append(alias.to_json())

        return alias

    async def edit_alias(
        self, ctx: commands.Context, alias_name: str, command: str, global_: bool = False
    ) -> bool:
        command = self.format_command_for_alias(command)

        if global_:
            settings = self.config
        else:
            settings = self.config.guild(ctx.guild)

        async with settings.entries() as aliases:
            for index, alias in enumerate(aliases):
                if alias["name"] == alias_name:
                    alias_edited = AliasEntry.from_json(alias)
                    alias_edited.command = command
                    aliases[index] = alias_edited.to_json()

                    if self._cache_enabled:
                        if global_:
                            self._aliases[None][alias_edited.name] = alias_edited
                        else:
                            self._aliases[ctx.guild.id][alias_edited.name] = alias_edited
                    return True

        return False

    async def delete_alias(
        self, ctx: commands.Context, alias_name: str, global_: bool = False
    ) -> bool:
        if global_:
            settings = self.config
        else:
            settings = self.config.guild(ctx.guild)

        async with settings.entries() as aliases:
            for alias in aliases:
                if alias["name"] == alias_name:
                    aliases.remove(alias)
                    if self._cache_enabled:
                        if global_:
                            del self._aliases[None][alias_name]
                        else:
                            del self._aliases[ctx.guild.id][alias_name]
                    return True

        return False
