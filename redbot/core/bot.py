from __future__ import annotations
import asyncio
import inspect
import logging
import os
import platform
import shutil
import sys
import contextlib
import weakref
import functools
from collections import namedtuple, OrderedDict
from datetime import datetime
from importlib.machinery import ModuleSpec
from pathlib import Path
from typing import (
    Optional,
    Union,
    List,
    Iterable,
    Dict,
    NoReturn,
    Set,
    TypeVar,
    Callable,
    Awaitable,
    Any,
    Literal,
    MutableMapping,
    Set,
    overload,
    TYPE_CHECKING,
)
from types import MappingProxyType

import discord
from discord.ext import commands as dpy_commands
from discord.ext.commands import when_mentioned_or

from . import Config, i18n, app_commands, commands, errors, _drivers, modlog, bank
from ._cli import ExitCodes
from ._cog_manager import CogManager, CogManagerUI
from .core_commands import Core
from .data_manager import cog_data_path
from .dev_commands import Dev
from ._events import init_events
from ._global_checks import init_global_checks
from ._settings_caches import (
    PrefixManager,
    IgnoreManager,
    WhitelistBlacklistManager,
    DisabledCogCache,
    I18nManager,
)
from .utils.predicates import MessagePredicate
from ._rpc import RPCMixin
from .tree import RedTree
from .utils import can_user_send_messages_in, common_filters, AsyncIter
from .utils.chat_formatting import box, text_to_file
from .utils._internal_utils import send_to_owners_with_prefix_replaced

if TYPE_CHECKING:
    from discord.ext.commands.hybrid import CommandCallback, ContextT, P


_T = TypeVar("_T")

CUSTOM_GROUPS = "CUSTOM_GROUPS"
COMMAND_SCOPE = "COMMAND"
SHARED_API_TOKENS = "SHARED_API_TOKENS"

log = logging.getLogger("red")

__all__ = ("Red",)

NotMessage = namedtuple("NotMessage", "guild")

DataDeletionResults = namedtuple("DataDeletionResults", "failed_modules failed_cogs unhandled")

PreInvokeCoroutine = Callable[[commands.Context], Awaitable[Any]]
T_BIC = TypeVar("T_BIC", bound=PreInvokeCoroutine)
UserOrRole = Union[int, discord.Role, discord.Member, discord.User]

_ = i18n.Translator("Core", __file__)


def _is_submodule(parent, child):
    return parent == child or child.startswith(parent + ".")


class _NoOwnerSet(RuntimeError):
    """Raised when there is no owner set for the instance that is trying to start."""


# Order of inheritance here matters.
# d.py autoshardedbot should be at the end
# all of our mixins should happen before,
# and must include a call to super().__init__ unless they do not provide an init
class Red(
    commands.GroupMixin, RPCMixin, dpy_commands.bot.AutoShardedBot
):  # pylint: disable=no-member # barely spurious warning caused by shadowing
    """Our subclass of discord.ext.commands.AutoShardedBot"""

    def __init__(self, *args, cli_flags=None, bot_dir: Path = Path.cwd(), **kwargs):
        self._shutdown_mode = ExitCodes.CRITICAL
        self._cli_flags = cli_flags
        self._config = Config.get_core_conf(force_registration=False)
        self.rpc_enabled = cli_flags.rpc
        self.rpc_port = cli_flags.rpc_port
        self._last_exception = None
        self._config.register_global(
            token=None,
            prefix=[],
            packages=[],
            owner=None,
            whitelist=[],
            blacklist=[],
            locale="en-US",
            regional_format=None,
            embeds=True,
            color=15158332,
            fuzzy=False,
            custom_info=None,
            help__page_char_limit=1000,
            help__max_pages_in_guild=2,
            help__delete_delay=0,
            help__use_menus=0,
            help__show_hidden=False,
            help__show_aliases=True,
            help__verify_checks=True,
            help__verify_exists=False,
            help__tagline="",
            help__use_tick=False,
            help__react_timeout=30,
            description="Red V3",
            invite_public=False,
            invite_perm=0,
            invite_commands_scope=False,
            disabled_commands=[],
            disabled_command_msg="That command is disabled.",
            invoke_error_msg=None,
            extra_owner_destinations=[],
            owner_opt_out_list=[],
            last_system_info__python_version=[3, 7],
            last_system_info__machine=None,
            last_system_info__system=None,
            schema_version=0,
            datarequests__allow_user_requests=True,
            datarequests__user_requests_are_strict=True,
            use_buttons=False,
            enabled_slash_commands={},
            enabled_user_commands={},
            enabled_message_commands={},
        )

        self._config.register_guild(
            prefix=[],
            whitelist=[],
            blacklist=[],
            admin_role=[],
            mod_role=[],
            embeds=None,
            ignored=False,
            use_bot_color=False,
            fuzzy=False,
            disabled_commands=[],
            autoimmune_ids=[],
            delete_delay=-1,
            locale=None,
            regional_format=None,
        )

        self._config.register_channel(embeds=None, ignored=False)
        self._config.register_user(embeds=None)

        self._config.init_custom("COG_DISABLE_SETTINGS", 2)
        self._config.register_custom("COG_DISABLE_SETTINGS", disabled=None)

        self._config.init_custom(CUSTOM_GROUPS, 2)
        self._config.register_custom(CUSTOM_GROUPS)

        # {COMMAND_NAME: {GUILD_ID: {...}}}
        # GUILD_ID=0 for global setting
        self._config.init_custom(COMMAND_SCOPE, 2)
        self._config.register_custom(COMMAND_SCOPE, embeds=None)
        # TODO: add cache for embed settings

        self._config.init_custom(SHARED_API_TOKENS, 2)
        self._config.register_custom(SHARED_API_TOKENS)
        self._prefix_cache = PrefixManager(self._config, cli_flags)
        self._disabled_cog_cache = DisabledCogCache(self._config)
        self._ignored_cache = IgnoreManager(self._config)
        self._whiteblacklist_cache = WhitelistBlacklistManager(self._config)
        self._i18n_cache = I18nManager(self._config)
        self._bypass_cooldowns = False

        async def prefix_manager(bot, message) -> List[str]:
            prefixes = await self._prefix_cache.get_prefixes(message.guild)
            if cli_flags.mentionable:
                return when_mentioned_or(*prefixes)(bot, message)
            return prefixes

        if "command_prefix" not in kwargs:
            kwargs["command_prefix"] = prefix_manager

        if "owner_id" in kwargs:
            raise RuntimeError("Red doesn't accept owner_id kwarg, use owner_ids instead.")

        if "intents" not in kwargs:
            intents = discord.Intents.all()
            for intent_name in cli_flags.disable_intent:
                setattr(intents, intent_name, False)
            kwargs["intents"] = intents

        self._owner_id_overwrite = cli_flags.owner

        if "owner_ids" in kwargs:
            kwargs["owner_ids"] = set(kwargs["owner_ids"])
        else:
            kwargs["owner_ids"] = set()
        kwargs["owner_ids"].update(cli_flags.co_owner)

        if "command_not_found" not in kwargs:
            kwargs["command_not_found"] = "Command {} not found.\n{}"

        if "allowed_mentions" not in kwargs:
            kwargs["allowed_mentions"] = discord.AllowedMentions(everyone=False, roles=False)

        message_cache_size = cli_flags.message_cache_size
        if cli_flags.no_message_cache:
            message_cache_size = None
        kwargs["max_messages"] = message_cache_size
        self._max_messages = message_cache_size

        self._uptime = None
        self._checked_time_accuracy = None

        self._main_dir = bot_dir
        self._cog_mgr = CogManager()
        self._use_team_features = cli_flags.use_team_features
        super().__init__(*args, help_command=None, tree_cls=RedTree, **kwargs)
        # Do not manually use the help formatter attribute here, see `send_help_for`,
        # for a documented API. The internals of this object are still subject to change.
        self._help_formatter = commands.help.RedHelpFormatter()
        self.add_command(commands.help.red_help)

        self._permissions_hooks: List[commands.CheckPredicate] = []
        self._red_ready = asyncio.Event()
        self._red_before_invoke_objs: Set[PreInvokeCoroutine] = set()

        self._deletion_requests: MutableMapping[int, asyncio.Lock] = weakref.WeakValueDictionary()

    def set_help_formatter(self, formatter: commands.help.HelpFormatterABC):
        """
        Set's Red's help formatter.

        .. warning::
            This method is `provisional <developer-guarantees-exclusions>`.


        The formatter must implement all methods in
        ``commands.help.HelpFormatterABC``

        Cogs which set a help formatter should inform users of this.
        Users should not use multiple cogs which set a help formatter.

        This should specifically be an instance of a formatter.
        This allows cogs to pass a config object or similar to the
        formatter prior to the bot using it.

        See ``commands.help.HelpFormatterABC`` for more details.

        Raises
        ------
        RuntimeError
            If the default formatter has already been replaced
        TypeError
            If given an invalid formatter
        """

        if not isinstance(formatter, commands.help.HelpFormatterABC):
            raise TypeError(
                "Help formatters must inherit from `commands.help.HelpFormatterABC` "
                "and implement the required interfaces."
            )

        # do not switch to isinstance, we want to know that this has not been overridden,
        # even with a subclass.
        if type(self._help_formatter) is commands.help.RedHelpFormatter:
            self._help_formatter = formatter
        else:
            raise RuntimeError("The formatter has already been overridden.")

    def reset_help_formatter(self):
        """
        Resets Red's help formatter.

        .. warning::
            This method is `provisional <developer-guarantees-exclusions>`.


        This exists for use in ``cog_unload`` for cogs which replace the formatter
        as well as for a rescue command in core_commands.

        """
        self._help_formatter = commands.help.RedHelpFormatter()

    def add_dev_env_value(self, name: str, value: Callable[[commands.Context], Any]):
        """
        Add a custom variable to the dev environment (``[p]debug``, ``[p]eval``, and ``[p]repl`` commands).
        If dev mode is disabled, nothing will happen.

        Example
        -------

        .. code-block:: python

            class MyCog(commands.Cog):
                def __init__(self, bot):
                    self.bot = bot
                    bot.add_dev_env_value("mycog", lambda ctx: self)
                    bot.add_dev_env_value("mycogdata", lambda ctx: self.settings[ctx.guild.id])

                def cog_unload(self):
                    self.bot.remove_dev_env_value("mycog")
                    self.bot.remove_dev_env_value("mycogdata")

        Once your cog is loaded, the custom variables ``mycog`` and ``mycogdata``
        will be included in the environment of dev commands.

        Parameters
        ----------
        name: str
            The name of your custom variable.
        value: Callable[[commands.Context], Any]
            The function returning the value of the variable.
            It must take a `commands.Context` as its sole parameter

        Raises
        ------
        TypeError
            ``value`` argument isn't a callable.
        ValueError
            The passed callable takes no or more than one argument.
        RuntimeError
            The name of the custom variable is either reserved by a variable
            from the default environment or already taken by some other custom variable.
        """
        signature = inspect.signature(value)
        if len(signature.parameters) != 1:
            raise ValueError("Callable must take exactly one argument for context")
        dev = self.get_cog("Dev")
        if dev is None:
            return
        if name in [
            "bot",
            "ctx",
            "channel",
            "author",
            "guild",
            "message",
            "asyncio",
            "aiohttp",
            "discord",
            "commands",
            "_",
            "__name__",
            "__builtins__",
        ]:
            raise RuntimeError(f"The name {name} is reserved for default environment.")
        if name in dev.env_extensions:
            raise RuntimeError(f"The name {name} is already used.")
        dev.env_extensions[name] = value

    def remove_dev_env_value(self, name: str):
        """
        Remove a custom variable from the dev environment.

        Parameters
        ----------
        name: str
            The name of the custom variable.

        Raises
        ------
        KeyError
            The custom variable was never set.
        """
        dev = self.get_cog("Dev")
        if dev is None:
            return
        del dev.env_extensions[name]

    def get_command(self, name: str, /) -> Optional[commands.Command]:
        com = super().get_command(name)
        assert com is None or isinstance(com, commands.Command)
        return com

    def get_cog(self, name: str, /) -> Optional[commands.Cog]:
        cog = super().get_cog(name)
        assert cog is None or isinstance(cog, commands.Cog)
        return cog

    @property
    def _before_invoke(self):  # DEP-WARN
        return self._red_before_invoke_method

    @_before_invoke.setter
    def _before_invoke(self, val):  # DEP-WARN
        """Prevent this from being overwritten in super().__init__"""
        pass

    async def _red_before_invoke_method(self, ctx):
        await self.wait_until_red_ready()
        return_exceptions = isinstance(ctx.command, commands.commands._RuleDropper)
        if self._red_before_invoke_objs:
            await asyncio.gather(
                *(coro(ctx) for coro in self._red_before_invoke_objs),
                return_exceptions=return_exceptions,
            )

    async def cog_disabled_in_guild(
        self, cog: commands.Cog, guild: Optional[discord.Guild]
    ) -> bool:
        """
        Check if a cog is disabled in a guild

        Parameters
        ----------
        cog: commands.Cog
        guild: Optional[discord.Guild]

        Returns
        -------
        bool
        """
        if guild is None:
            return False
        return await self._disabled_cog_cache.cog_disabled_in_guild(cog.qualified_name, guild.id)

    async def cog_disabled_in_guild_raw(self, cog_name: str, guild_id: int) -> bool:
        """
        Check if a cog is disabled in a guild without the cog or guild object

        Parameters
        ----------
        cog_name: str
            This should be the cog's qualified name, not necessarily the classname
        guild_id: int

        Returns
        -------
        bool
        """
        return await self._disabled_cog_cache.cog_disabled_in_guild(cog_name, guild_id)

    def remove_before_invoke_hook(self, coro: PreInvokeCoroutine) -> None:
        """
        Functional method to remove a `before_invoke` hook.
        """
        self._red_before_invoke_objs.discard(coro)

    def before_invoke(self, coro: T_BIC, /) -> T_BIC:
        """
        Overridden decorator method for Red's ``before_invoke`` behavior.

        This can safely be used purely functionally as well.

        3rd party cogs should remove any hooks which they register at unload
        using `remove_before_invoke_hook`

        Below behavior shared with discord.py:

        .. note::
            The ``before_invoke`` hooks are
            only called if all checks and argument parsing procedures pass
            without error. If any check or argument parsing procedures fail
            then the hooks are not called.

        Parameters
        ----------
        coro: Callable[[commands.Context], Awaitable[Any]]
            The coroutine to register as the pre-invoke hook.

        Raises
        ------
        TypeError
            The coroutine passed is not actually a coroutine.
        """
        if not asyncio.iscoroutinefunction(coro):
            raise TypeError("The pre-invoke hook must be a coroutine.")

        self._red_before_invoke_objs.add(coro)
        return coro

    async def before_identify_hook(self, shard_id, *, initial=False):
        """A hook that is called before IDENTIFYing a session.
        Same as in discord.py, but also dispatches "on_red_identify" bot event."""
        self.dispatch("red_before_identify", shard_id, initial)
        return await super().before_identify_hook(shard_id, initial=initial)

    @property
    def cog_mgr(self) -> NoReturn:
        raise AttributeError("Please don't mess with the cog manager internals.")

    @property
    def uptime(self) -> datetime:
        """Allow access to the value, but we don't want cog creators setting it"""
        return self._uptime

    @uptime.setter
    def uptime(self, value) -> NoReturn:
        raise RuntimeError(
            "Hey, we're cool with sharing info about the uptime, but don't try and assign to it please."
        )

    @property
    def db(self) -> NoReturn:
        raise AttributeError(
            "We really don't want you touching the bot config directly. "
            "If you need something in here, take a look at the exposed methods "
            "and use the one which corresponds to your needs or "
            "open an issue if you need an additional method for your use case."
        )

    @property
    def counter(self) -> NoReturn:
        raise AttributeError(
            "Please make your own counter object by importing ``Counter`` from ``collections``."
        )

    @property
    def color(self) -> NoReturn:
        raise AttributeError("Please fetch the embed color with `get_embed_color`")

    @property
    def colour(self) -> NoReturn:
        raise AttributeError("Please fetch the embed colour with `get_embed_colour`")

    @property
    def max_messages(self) -> Optional[int]:
        return self._max_messages

    async def add_to_blacklist(
        self, users_or_roles: Iterable[UserOrRole], *, guild: Optional[discord.Guild] = None
    ):
        """
        Add users or roles to the global or local blocklist.

        Parameters
        ----------
        users_or_roles : Iterable[Union[int, discord.Role, discord.Member, discord.User]]
            The items to add to the blocklist.
            Roles and role IDs should only be passed when updating a local blocklist.
        guild : Optional[discord.Guild]
            The guild, whose local blocklist should be modified.
            If not passed, the global blocklist will be modified.

        Raises
        ------
        TypeError
            The values passed were not of the proper type.
        """
        to_add: Set[int] = {getattr(uor, "id", uor) for uor in users_or_roles}
        await self._whiteblacklist_cache.add_to_blacklist(guild, to_add)

    async def remove_from_blacklist(
        self, users_or_roles: Iterable[UserOrRole], *, guild: Optional[discord.Guild] = None
    ):
        """
        Remove users or roles from the global or local blocklist.

        Parameters
        ----------
        users_or_roles : Iterable[Union[int, discord.Role, discord.Member, discord.User]]
            The items to remove from the blocklist.
            Roles and role IDs should only be passed when updating a local blocklist.
        guild : Optional[discord.Guild]
            The guild, whose local blocklist should be modified.
            If not passed, the global blocklist will be modified.

        Raises
        ------
        TypeError
            The values passed were not of the proper type.
        """
        to_remove: Set[int] = {getattr(uor, "id", uor) for uor in users_or_roles}
        await self._whiteblacklist_cache.remove_from_blacklist(guild, to_remove)

    async def get_blacklist(self, guild: Optional[discord.Guild] = None) -> Set[int]:
        """
        Get the global or local blocklist.

        Parameters
        ----------
        guild : Optional[discord.Guild]
            The guild to get the local blocklist for.
            If this is not passed, the global blocklist will be returned.

        Returns
        -------
        Set[int]
            The IDs of the blocked users/roles.
        """
        return await self._whiteblacklist_cache.get_blacklist(guild)

    async def clear_blacklist(self, guild: Optional[discord.Guild] = None):
        """
        Clears the global or local blocklist.

        Parameters
        ----------
        guild : Optional[discord.Guild]
            The guild, whose local blocklist should be cleared.
            If not passed, the global blocklist will be cleared.
        """
        await self._whiteblacklist_cache.clear_blacklist(guild)

    async def add_to_whitelist(
        self, users_or_roles: Iterable[UserOrRole], *, guild: Optional[discord.Guild] = None
    ):
        """
        Add users or roles to the global or local allowlist.

        Parameters
        ----------
        users_or_roles : Iterable[Union[int, discord.Role, discord.Member, discord.User]]
            The items to add to the allowlist.
            Roles and role IDs should only be passed when updating a local allowlist.
        guild : Optional[discord.Guild]
            The guild, whose local allowlist should be modified.
            If not passed, the global allowlist will be modified.

        Raises
        ------
        TypeError
            The passed values were not of the proper type.
        """
        to_add: Set[int] = {getattr(uor, "id", uor) for uor in users_or_roles}
        await self._whiteblacklist_cache.add_to_whitelist(guild, to_add)

    async def remove_from_whitelist(
        self, users_or_roles: Iterable[UserOrRole], *, guild: Optional[discord.Guild] = None
    ):
        """
        Remove users or roles from the global or local allowlist.

        Parameters
        ----------
        users_or_roles : Iterable[Union[int, discord.Role, discord.Member, discord.User]]
            The items to remove from the allowlist.
            Roles and role IDs should only be passed when updating a local allowlist.
        guild : Optional[discord.Guild]
            The guild, whose local allowlist should be modified.
            If not passed, the global allowlist will be modified.

        Raises
        ------
        TypeError
            The passed values were not of the proper type.
        """
        to_remove: Set[int] = {getattr(uor, "id", uor) for uor in users_or_roles}
        await self._whiteblacklist_cache.remove_from_whitelist(guild, to_remove)

    async def get_whitelist(self, guild: Optional[discord.Guild] = None):
        """
        Get the global or local allowlist.

        Parameters
        ----------
        guild : Optional[discord.Guild]
            The guild to get the local allowlist for.
            If this is not passed, the global allowlist will be returned.

        Returns
        -------
        Set[int]
            The IDs of the allowed users/roles.
        """
        return await self._whiteblacklist_cache.get_whitelist(guild)

    async def clear_whitelist(self, guild: Optional[discord.Guild] = None):
        """
        Clears the global or local allowlist.

        Parameters
        ----------
        guild : Optional[discord.Guild]
            The guild, whose local allowlist should be cleared.
            If not passed, the global allowlist will be cleared.
        """
        await self._whiteblacklist_cache.clear_whitelist(guild)

    async def allowed_by_whitelist_blacklist(
        self,
        who: Optional[Union[discord.Member, discord.User]] = None,
        *,
        who_id: Optional[int] = None,
        guild: Optional[discord.Guild] = None,
        role_ids: Optional[List[int]] = None,
    ) -> bool:
        """
        This checks if a user or member is allowed to run things,
        as considered by Red's allowlist and blocklist.

        If given a user object, this function will check the global lists

        If given a member, this will additionally check guild lists

        If omitting a user or member, you must provide a value for ``who_id``

        You may also provide a value for ``guild`` in this case

        If providing a member by guild and member ids,
        you should supply ``role_ids`` as well

        Parameters
        ----------
        who : Optional[Union[discord.Member, discord.User]]
            The user or member object to check

        Other Parameters
        ----------------
        who_id : Optional[int]
            The id of the user or member to check
            If not providing a value for ``who``, this is a required parameter.
        guild : Optional[discord.Guild]
            When used in conjunction with a provided value for ``who_id``, checks
            the lists for the corresponding guild as well.
            This is ignored when ``who`` is passed.
        role_ids : Optional[List[int]]
            When used with both ``who_id`` and ``guild``, checks the role ids provided.
            This is required for accurate checking of members in a guild if providing ids.
            This is ignored when ``who`` is passed.

        Raises
        ------
        TypeError
            Did not provide ``who`` or ``who_id``

        Returns
        -------
        bool
            `True` if user is allowed to run things, `False` otherwise
        """
        # Contributor Note:
        # All config calls are delayed until needed in this section
        # All changes should be made keeping in mind that this is also used as a global check

        mocked = False  # used for an accurate delayed role id expansion later.
        if not who:
            if not who_id:
                raise TypeError("Must provide a value for either `who` or `who_id`")
            mocked = True
            who = discord.Object(id=who_id)
        else:
            guild = getattr(who, "guild", None)

        if await self.is_owner(who):
            return True

        global_whitelist = await self.get_whitelist()
        if global_whitelist:
            if who.id not in global_whitelist:
                return False
        else:
            # blacklist is only used when whitelist doesn't exist.
            global_blacklist = await self.get_blacklist()
            if who.id in global_blacklist:
                return False

        if guild:
            if guild.owner_id == who.id:
                return True

            # The delayed expansion of ids to check saves time in the DM case.
            # Converting to a set reduces the total lookup time in section
            if mocked:
                ids = {i for i in (who.id, *(role_ids or [])) if i != guild.id}
            else:
                # DEP-WARN
                # This uses member._roles (getattr is for the user case)
                # If this is removed upstream (undocumented)
                # there is a silent failure potential, and role blacklist/whitelists will break.
                ids = {i for i in (who.id, *(getattr(who, "_roles", []))) if i != guild.id}

            guild_whitelist = await self.get_whitelist(guild)
            if guild_whitelist:
                if ids.isdisjoint(guild_whitelist):
                    return False
            else:
                guild_blacklist = await self.get_blacklist(guild)
                if not ids.isdisjoint(guild_blacklist):
                    return False

        return True

    async def message_eligible_as_command(self, message: discord.Message) -> bool:
        """
        Runs through the things which apply globally about commands
        to determine if a message may be responded to as a command.

        This can't interact with permissions as permissions is hyper-local
        with respect to command objects, create command objects for this
        if that's needed.

        This also does not check for prefix or command conflicts,
        as it is primarily designed for non-prefix based response handling
        via on_message_without_command

        Parameters
        ----------
        message
            The message object to check

        Returns
        -------
        bool
            Whether or not the message is eligible to be treated as a command.
        """

        channel = message.channel
        guild = message.guild

        if message.author.bot:
            return False

        # We do not consider messages with PartialMessageable channel as eligible.
        # See `process_commands()` for our handling of it.

        # 27-03-2023: Addendum, DMs won't run into the same issues that guild partials will,
        # so we can safely continue to execute the command.
        if (
            isinstance(channel, discord.PartialMessageable)
            and channel.type is not discord.ChannelType.private
        ):
            return False

        if guild:
            assert isinstance(
                channel,
                (discord.TextChannel, discord.VoiceChannel, discord.StageChannel, discord.Thread),
            )
            if not can_user_send_messages_in(guild.me, channel):
                return False
            if not (await self.ignored_channel_or_guild(message)):
                return False

        if not (await self.allowed_by_whitelist_blacklist(message.author)):
            return False

        return True

    async def ignored_channel_or_guild(
        self, ctx: Union[commands.Context, discord.Message, discord.Interaction]
    ) -> bool:
        """
        This checks if the bot is meant to be ignoring commands in a channel or guild,
        as considered by Red's whitelist and blacklist.

        Parameters
        ----------
        ctx :
            Context object of the command which needs to be checked prior to invoking
            or a Message object which might be intended for use as a command
            or an Interaction object which might be intended for use with a command.

        Returns
        -------
        bool
            `True` if commands are allowed in the channel, `False` otherwise

        Raises
        ------
        TypeError
            ``ctx.channel`` is a `discord.PartialMessageable` with a ``type`` other
            than ``discord.ChannelType.private``
        """
        if isinstance(ctx, discord.Interaction):
            author = ctx.user
        else:
            author = ctx.author

        is_private = isinstance(ctx.channel, discord.abc.PrivateChannel)
        if isinstance(ctx.channel, discord.PartialMessageable):
            if ctx.channel.type is not discord.ChannelType.private:
                raise TypeError("Can't check permissions for non-private PartialMessageable.")
            is_private = True
        perms = ctx.channel.permissions_for(author)
        surpass_ignore = (
            is_private
            or perms.manage_guild
            or await self.is_owner(author)
            or await self.is_admin(author)
        )
        # guild-wide checks
        if surpass_ignore:
            return True

        guild_ignored = await self._ignored_cache.get_ignored_guild(ctx.guild)
        if guild_ignored:
            return False

        # (parent) channel checks
        if perms.manage_channels:
            return True

        if isinstance(ctx.channel, discord.Thread):
            channel = ctx.channel.parent
            thread = ctx.channel
        else:
            channel = ctx.channel
            thread = None

        chann_ignored = await self._ignored_cache.get_ignored_channel(channel)
        if chann_ignored:
            return False
        if thread is None:
            return True

        # thread checks
        if perms.manage_threads:
            return True
        thread_ignored = await self._ignored_cache.get_ignored_channel(
            thread,
            check_category=False,  # already checked for parent
        )
        return not thread_ignored

    async def get_valid_prefixes(self, guild: Optional[discord.Guild] = None) -> List[str]:
        """
        This gets the valid prefixes for a guild.

        If not provided a guild (or passed None) it will give the DM prefixes.

        This is just a fancy wrapper around ``get_prefix``

        Parameters
        ----------
        guild : Optional[discord.Guild]
            The guild you want prefixes for. Omit (or pass None) for the DM prefixes

        Returns
        -------
        List[str]
            If a guild was specified, the valid prefixes in that guild.
            If a guild was not specified, the valid prefixes for DMs
        """
        return await self.get_prefix(NotMessage(guild))

    async def set_prefixes(self, prefixes: List[str], guild: Optional[discord.Guild] = None):
        """
        Set global/server prefixes.

        If ``guild`` is not provided (or None is passed), this will set the global prefixes.

        Parameters
        ----------
        prefixes : List[str]
            The prefixes you want to set. Passing empty list will reset prefixes for the ``guild``
        guild : Optional[discord.Guild]
            The guild you want to set the prefixes for. Omit (or pass None) to set the global prefixes

        Raises
        ------
        TypeError
            If ``prefixes`` is not a list of strings
        ValueError
            If empty list is passed to ``prefixes`` when setting global prefixes
        """
        await self._prefix_cache.set_prefixes(guild=guild, prefixes=prefixes)

    async def get_embed_color(self, location: discord.abc.Messageable) -> discord.Color:
        """
        Get the embed color for a location. This takes into account all related settings.

        Parameters
        ----------
        location : `discord.abc.Messageable`
            Location to check embed color for.

        Returns
        -------
        discord.Color
            Embed color for the provided location.
        """

        guild = getattr(location, "guild", None)

        if (
            guild
            and await self._config.guild(guild).use_bot_color()
            and not isinstance(location, discord.Member)
        ):
            return guild.me.color

        return self._color

    async def get_or_fetch_user(self, user_id: int) -> discord.User:
        """
        Retrieves a `discord.User` based on their ID.
        You do not have to share any guilds
        with the user to get this information, however many operations
        do require that you do.

        .. warning::

            This method may make an API call if the user is not found in the bot cache. For general usage, consider ``bot.get_user`` instead.

        Parameters
        -----------
        user_id: int
            The ID of the user that should be retrieved.

        Raises
        -------
        Errors
            Please refer to `discord.Client.fetch_user`.

        Returns
        --------
        discord.User
            The user you requested.
        """

        if (user := self.get_user(user_id)) is not None:
            return user
        return await self.fetch_user(user_id)

    async def get_or_fetch_member(self, guild: discord.Guild, member_id: int) -> discord.Member:
        """
        Retrieves a `discord.Member` from a guild and a member ID.

        .. warning::

            This method may make an API call if the user is not found in the bot cache. For general usage, consider ``discord.Guild.get_member`` instead.

        Parameters
        -----------
        guild: discord.Guild
            The guild which the member should be retrieved from.
        member_id: int
            The ID of the member that should be retrieved.

        Raises
        -------
        Errors
            Please refer to `discord.Guild.fetch_member`.

        Returns
        --------
        discord.Member
            The user you requested.
        """
        if (member := guild.get_member(member_id)) is not None:
            return member
        return await guild.fetch_member(member_id)

    get_embed_colour = get_embed_color

    # start config migrations
    async def _maybe_update_config(self):
        """
        This should be run prior to loading cogs or connecting to discord.
        """
        schema_version = await self._config.schema_version()

        if schema_version == 0:
            await self._schema_0_to_1()
            schema_version += 1
            await self._config.schema_version.set(schema_version)
        if schema_version == 1:
            await self._schema_1_to_2()
            schema_version += 1
            await self._config.schema_version.set(schema_version)
        if schema_version == 2:
            await self._schema_2_to_3()
            schema_version += 1
            await self._config.schema_version.set(schema_version)

    async def _schema_2_to_3(self):
        log.info("Migrating help menus to enum values")
        old = await self._config.help__use_menus()
        if old is not None:
            await self._config.help__use_menus.set(int(old))

    async def _schema_1_to_2(self):
        """
        This contains the migration of shared API tokens to a custom config scope
        """

        log.info("Moving shared API tokens to a custom group")
        all_shared_api_tokens = await self._config.get_raw("api_tokens", default={})
        for service_name, token_mapping in all_shared_api_tokens.items():
            service_partial = self._config.custom(SHARED_API_TOKENS, service_name)
            async with service_partial.all() as basically_bulk_update:
                basically_bulk_update.update(token_mapping)

        await self._config.clear_raw("api_tokens")

    async def _schema_0_to_1(self):
        """
        This contains the migration to allow multiple mod and multiple admin roles.
        """

        log.info("Begin updating guild configs to support multiple mod/admin roles")
        all_guild_data = await self._config.all_guilds()
        for guild_id, guild_data in all_guild_data.items():
            guild_obj = discord.Object(id=guild_id)
            mod_roles, admin_roles = [], []
            maybe_mod_role_id = guild_data["mod_role"]
            maybe_admin_role_id = guild_data["admin_role"]

            if maybe_mod_role_id:
                mod_roles.append(maybe_mod_role_id)
                await self._config.guild(guild_obj).mod_role.set(mod_roles)
            if maybe_admin_role_id:
                admin_roles.append(maybe_admin_role_id)
                await self._config.guild(guild_obj).admin_role.set(admin_roles)
        log.info("Done updating guild configs to support multiple mod/admin roles")

    # end Config migrations

    async def _pre_login(self) -> None:
        """
        This should only be run once, prior to logging in to Discord REST API.
        """
        await super()._pre_login()

        await self._maybe_update_config()
        self.description = await self._config.description()
        self._color = discord.Colour(await self._config.color())

        init_global_checks(self)
        init_events(self, self._cli_flags)

        if self._owner_id_overwrite is None:
            self._owner_id_overwrite = await self._config.owner()
        if self._owner_id_overwrite is not None:
            self.owner_ids.add(self._owner_id_overwrite)

        i18n_locale = await self._config.locale()
        i18n.set_locale(i18n_locale)
        i18n_regional_format = await self._config.regional_format()
        i18n.set_regional_format(i18n_regional_format)

    async def _pre_connect(self) -> None:
        """
        This should only be run once, prior to connecting to Discord gateway.
        """
        await self.add_cog(Core(self))
        await self.add_cog(CogManagerUI())
        if self._cli_flags.dev:
            await self.add_cog(Dev())

        await modlog._init(self)
        await bank._init()

        packages = OrderedDict()

        last_system_info = await self._config.last_system_info()

        ver_info = list(sys.version_info[:2])
        python_version_changed = False
        LIB_PATH = cog_data_path(raw_name="Downloader") / "lib"
        if ver_info != last_system_info["python_version"]:
            await self._config.last_system_info.python_version.set(ver_info)
            if any(LIB_PATH.iterdir()):
                shutil.rmtree(str(LIB_PATH))
                LIB_PATH.mkdir()
                asyncio.create_task(
                    send_to_owners_with_prefix_replaced(
                        self,
                        "We detected a change in minor Python version"
                        " and cleared packages in lib folder.\n"
                        "The instance was started with no cogs, please load Downloader"
                        " and use `[p]cog reinstallreqs` to regenerate lib folder."
                        " After that, restart the bot to get"
                        " all of your previously loaded cogs loaded again.",
                    )
                )
                python_version_changed = True
        else:
            if self._cli_flags.no_cogs is False:
                packages.update(dict.fromkeys(await self._config.packages()))

            if self._cli_flags.load_cogs:
                packages.update(dict.fromkeys(self._cli_flags.load_cogs))
            if self._cli_flags.unload_cogs:
                for package in self._cli_flags.unload_cogs:
                    packages.pop(package, None)

        system_changed = False
        machine = platform.machine()
        system = platform.system()
        if last_system_info["machine"] is None:
            await self._config.last_system_info.machine.set(machine)
        elif last_system_info["machine"] != machine:
            await self._config.last_system_info.machine.set(machine)
            system_changed = True

        if last_system_info["system"] is None:
            await self._config.last_system_info.system.set(system)
        elif last_system_info["system"] != system:
            await self._config.last_system_info.system.set(system)
            system_changed = True

        if system_changed and not python_version_changed:
            asyncio.create_task(
                send_to_owners_with_prefix_replaced(
                    self,
                    "We detected a possible change in machine's operating system"
                    " or architecture. You might need to regenerate your lib folder"
                    " if 3rd-party cogs stop working properly.\n"
                    "To regenerate lib folder, load Downloader and use `[p]cog reinstallreqs`.",
                )
            )

        if packages:
            # Load permissions first, for security reasons
            try:
                packages.move_to_end("permissions", last=False)
            except KeyError:
                pass

            to_remove = []
            log.info("Loading packages...")
            for package in packages:
                try:
                    spec = await self._cog_mgr.find_cog(package)
                    if spec is None:
                        log.error(
                            "Failed to load package %s (package was not found in any cog path)",
                            package,
                        )
                        await self.remove_loaded_package(package)
                        to_remove.append(package)
                        continue
                    await asyncio.wait_for(self.load_extension(spec), 30)
                except asyncio.TimeoutError:
                    log.exception("Failed to load package %s (timeout)", package)
                    to_remove.append(package)
                except Exception as e:
                    log.exception("Failed to load package %s", package, exc_info=e)
                    await self.remove_loaded_package(package)
                    to_remove.append(package)
            for package in to_remove:
                del packages[package]
        if packages:
            log.info("Loaded packages: " + ", ".join(packages))
        else:
            log.info("No packages were loaded.")

        if self.rpc_enabled:
            await self.rpc.initialize(self.rpc_port)

    def _setup_owners(self) -> None:
        if self.application.team:
            if self._use_team_features:
                self.owner_ids.update(
                    m.id
                    for m in self.application.team.members
                    if m.role in (discord.TeamMemberRole.admin, discord.TeamMemberRole.developer)
                )
        elif self._owner_id_overwrite is None:
            self.owner_ids.add(self.application.owner.id)

        if not self.owner_ids:
            raise _NoOwnerSet("Bot doesn't have any owner set!")

    async def start(self, token: str) -> None:
        # Overriding start to call _pre_login() before login()
        await self._pre_login()
        await self.login(token)
        # Pre-connect actions are done by setup_hook() which is called at the end of d.py's login()
        await self.connect()

    async def setup_hook(self) -> None:
        self._setup_owners()
        await self._pre_connect()

    async def send_help_for(
        self,
        ctx: commands.Context,
        help_for: Union[commands.Command, commands.GroupMixin, str],
        *,
        from_help_command: bool = False,
    ):
        """
        Invokes Red's helpformatter for a given context and object.
        """
        return await self._help_formatter.send_help(
            ctx, help_for, from_help_command=from_help_command
        )

    async def embed_requested(
        self,
        channel: Union[
            discord.TextChannel,
            discord.VoiceChannel,
            discord.StageChannel,
            commands.Context,
            discord.User,
            discord.Member,
            discord.Thread,
        ],
        *,
        command: Optional[commands.Command] = None,
        check_permissions: bool = True,
    ) -> bool:
        """
        Determine if an embed is requested for a response.

        Arguments
        ---------
        channel : Union[`discord.TextChannel`, `discord.VoiceChannel`, `discord.StageChannel`, `commands.Context`, `discord.User`, `discord.Member`, `discord.Thread`]
            The target messageable object to check embed settings for.

        Keyword Arguments
        -----------------
        command : `redbot.core.commands.Command`, optional
            The command ran.
            This is auto-filled when ``channel`` is passed with command context.
        check_permissions : `bool`
            If ``True``, this method will also check whether the bot can send embeds
            in the given channel and if it can't, it will return ``False`` regardless of
            the bot's embed settings.

        Returns
        -------
        bool
            :code:`True` if an embed is requested

        Raises
        ------
        TypeError
            When the passed channel is of type `discord.GroupChannel`,
            `discord.DMChannel`, or `discord.PartialMessageable`.
        """

        async def get_command_setting(guild_id: int) -> Optional[bool]:
            if command is None:
                return None
            scope = self._config.custom(COMMAND_SCOPE, command.qualified_name, guild_id)
            return await scope.embeds()

        # using dpy_commands.Context to keep the Messageable contract in full
        if isinstance(channel, dpy_commands.Context):
            command = command or channel.command
            channel = (
                channel.author
                if isinstance(channel.channel, discord.DMChannel)
                else channel.channel
            )

        if isinstance(
            channel, (discord.GroupChannel, discord.DMChannel, discord.PartialMessageable)
        ):
            raise TypeError(
                "You cannot pass a GroupChannel, DMChannel, or PartialMessageable to this method."
            )

        if isinstance(
            channel,
            (discord.TextChannel, discord.VoiceChannel, discord.StageChannel, discord.Thread),
        ):
            channel_id = channel.parent_id if isinstance(channel, discord.Thread) else channel.id

            if check_permissions and not channel.permissions_for(channel.guild.me).embed_links:
                return False

            channel_setting = await self._config.channel_from_id(channel_id).embeds()
            if channel_setting is not None:
                return channel_setting

            if (command_setting := await get_command_setting(channel.guild.id)) is not None:
                return command_setting

            if (guild_setting := await self._config.guild(channel.guild).embeds()) is not None:
                return guild_setting
        else:
            user = channel
            if (user_setting := await self._config.user(user).embeds()) is not None:
                return user_setting

        if (global_command_setting := await get_command_setting(0)) is not None:
            return global_command_setting

        global_setting = await self._config.embeds()
        return global_setting

    async def use_buttons(self) -> bool:
        """
        Determines whether the bot owner has enabled use of buttons instead of
        reactions for basic menus.

        Returns
        -------
        bool
        """
        return await self._config.use_buttons()

    async def is_owner(self, user: Union[discord.User, discord.Member], /) -> bool:
        """
        Determines if the user should be considered a bot owner.

        This takes into account CLI flags and application ownership.

        By default,
        application team members are not considered owners,
        while individual application owners are.

        Parameters
        ----------
        user: Union[discord.User, discord.Member]

        Returns
        -------
        bool
        """
        return user.id in self.owner_ids

    async def get_invite_url(self) -> str:
        """
        Generates the invite URL for the bot.

        Does not check if the invite URL is configured to be public
        with ``[p]inviteset public``. To check if invites are public,
        use `Red.is_invite_url_public()`.

        Returns
        -------
        str
            Invite URL.
        """
        data = await self._config.all()
        commands_scope = data["invite_commands_scope"]
        scopes = ("bot", "applications.commands") if commands_scope else ("bot",)
        perms_int = data["invite_perm"]
        permissions = discord.Permissions(perms_int)
        return discord.utils.oauth_url(self.application_id, permissions=permissions, scopes=scopes)

    async def is_invite_url_public(self) -> bool:
        """
        Determines if invite URL is configured to be public with ``[p]inviteset public``.

        Returns
        -------
        bool
            :code:`True` if the invite URL is public.
        """
        return await self._config.invite_public()

    async def is_admin(self, member: discord.Member) -> bool:
        """Checks if a member is an admin of their guild."""
        try:
            for snowflake in await self._config.guild(member.guild).admin_role():
                if member.get_role(snowflake):
                    return True
        except AttributeError:  # someone passed a webhook to this
            pass
        return False

    async def is_mod(self, member: discord.Member) -> bool:
        """Checks if a member is a mod or admin of their guild."""
        try:
            for snowflake in await self._config.guild(member.guild).admin_role():
                if member.get_role(snowflake):
                    return True
            for snowflake in await self._config.guild(member.guild).mod_role():
                if member.get_role(snowflake):
                    return True
        except AttributeError:  # someone passed a webhook to this
            pass
        return False

    async def get_admin_roles(self, guild: discord.Guild) -> List[discord.Role]:
        """
        Gets the admin roles for a guild.
        """
        ret: List[discord.Role] = []
        for snowflake in await self._config.guild(guild).admin_role():
            r = guild.get_role(snowflake)
            if r:
                ret.append(r)
        return ret

    async def get_mod_roles(self, guild: discord.Guild) -> List[discord.Role]:
        """
        Gets the mod roles for a guild.
        """
        ret: List[discord.Role] = []
        for snowflake in await self._config.guild(guild).mod_role():
            r = guild.get_role(snowflake)
            if r:
                ret.append(r)
        return ret

    async def get_admin_role_ids(self, guild_id: int) -> List[int]:
        """
        Gets the admin role ids for a guild id.
        """
        return await self._config.guild(discord.Object(id=guild_id)).admin_role()

    async def get_mod_role_ids(self, guild_id: int) -> List[int]:
        """
        Gets the mod role ids for a guild id.
        """
        return await self._config.guild(discord.Object(id=guild_id)).mod_role()

    @overload
    async def get_shared_api_tokens(self, service_name: str = ...) -> Dict[str, str]:
        ...

    @overload
    async def get_shared_api_tokens(self, service_name: None = ...) -> Dict[str, Dict[str, str]]:
        ...

    async def get_shared_api_tokens(
        self, service_name: Optional[str] = None
    ) -> Union[Dict[str, Dict[str, str]], Dict[str, str]]:
        """
        Gets the shared API tokens for a service, or all of them if no argument specified.

        Parameters
        ----------
        service_name: str, optional
            The service to get tokens for. Leave empty to get tokens for all services.

        Returns
        -------
        Dict[str, Dict[str, str]] or Dict[str, str]
            A Mapping of token names to tokens.
            This mapping exists because some services have multiple tokens.
            If ``service_name`` is `None`, this method will return
            a mapping with mappings for all services.
        """
        if service_name is None:
            return await self._config.custom(SHARED_API_TOKENS).all()
        else:
            return await self._config.custom(SHARED_API_TOKENS, service_name).all()

    async def set_shared_api_tokens(self, service_name: str, **tokens: str):
        """
        Sets shared API tokens for a service

        In most cases, this should not be used. Users should instead be using the
        ``set api`` command

        This will not clear existing values not specified.

        Parameters
        ----------
        service_name: str
            The service to set tokens for
        **tokens
            token_name -> token

        Examples
        --------
        Setting the api_key for youtube from a value in a variable ``my_key``

        >>> await ctx.bot.set_shared_api_tokens("youtube", api_key=my_key)
        """

        async with self._config.custom(SHARED_API_TOKENS, service_name).all() as group:
            group.update(tokens)
        self.dispatch("red_api_tokens_update", service_name, MappingProxyType(group))

    async def remove_shared_api_tokens(self, service_name: str, *token_names: str):
        """
        Removes shared API tokens

        Parameters
        ----------
        service_name: str
            The service to remove tokens for
        *token_names: str
            The name of each token to be removed

        Examples
        --------
        Removing the api_key for youtube

        >>> await ctx.bot.remove_shared_api_tokens("youtube", "api_key")
        """
        async with self._config.custom(SHARED_API_TOKENS, service_name).all() as group:
            for name in token_names:
                group.pop(name, None)
        self.dispatch("red_api_tokens_update", service_name, MappingProxyType(group))

    async def remove_shared_api_services(self, *service_names: str):
        """
        Removes shared API services, as well as keys and tokens associated with them.

        Parameters
        ----------
        *service_names: str
            The services to remove.

        Examples
        ----------
        Removing the youtube service

        >>> await ctx.bot.remove_shared_api_services("youtube")
        """
        async with self._config.custom(SHARED_API_TOKENS).all() as group:
            for service in service_names:
                group.pop(service, None)
        # dispatch needs to happen *after* it actually updates
        for service in service_names:
            self.dispatch("red_api_tokens_update", service, MappingProxyType({}))

    async def get_context(self, message, /, *, cls=commands.Context):
        return await super().get_context(message, cls=cls)

    async def process_commands(self, message: discord.Message, /):
        """
        Same as base method, but dispatches an additional event for cogs
        which want to handle normal messages differently to command
        messages,  without the overhead of additional get_context calls
        per cog.
        """
        if not message.author.bot:
            ctx = await self.get_context(message)

            # The licenseinfo command must always be available, even in a slash only bot.
            # To get around not having the message content intent, a mention prefix
            # will always work for it.
            if not ctx.valid:
                for m in (f"<@{self.user.id}> ", f"<@!{self.user.id}> "):
                    if message.content.startswith(m):
                        ctx.view.undo()
                        ctx.view.skip_string(m)
                        invoker = ctx.view.get_word()
                        command = self.all_commands.get(invoker, None)
                        if isinstance(command, commands.commands._AlwaysAvailableMixin):
                            ctx.command = command
                            ctx.prefix = m
                        break

            if (
                ctx.invoked_with
                and isinstance(message.channel, discord.PartialMessageable)
                and message.channel.type is not discord.ChannelType.private
            ):
                log.warning(
                    "Discarded a command message (ID: %s) with PartialMessageable channel: %r",
                    message.id,
                    message.channel,
                )
            else:
                await self.invoke(ctx)
        else:
            ctx = None

        if ctx is None or ctx.valid is False:
            self.dispatch("message_without_command", message)

    @staticmethod
    def list_packages():
        """Lists packages present in the cogs folder"""
        return os.listdir("cogs")

    async def save_packages_status(self, packages):
        await self._config.packages.set(packages)

    async def add_loaded_package(self, pkg_name: str):
        async with self._config.packages() as curr_pkgs:
            if pkg_name not in curr_pkgs:
                curr_pkgs.append(pkg_name)

    async def remove_loaded_package(self, pkg_name: str):
        async with self._config.packages() as curr_pkgs:
            while pkg_name in curr_pkgs:
                curr_pkgs.remove(pkg_name)

    async def load_extension(self, spec: ModuleSpec):
        # NB: this completely bypasses `discord.ext.commands.Bot._load_from_module_spec`
        name = spec.name.split(".")[-1]
        if name in self.extensions:
            raise errors.PackageAlreadyLoaded(spec)

        lib = spec.loader.load_module()
        if not hasattr(lib, "setup"):
            del lib
            raise discord.ClientException(f"extension {name} does not have a setup function")

        try:
            await lib.setup(self)
            await self.tree.red_check_enabled()
        except Exception as e:
            await self._remove_module_references(lib.__name__)
            await self._call_module_finalizers(lib, name)
            raise
        else:
            self._BotBase__extensions[name] = lib

    async def remove_cog(
        self,
        cogname: str,
        /,
        *,
        guild: Optional[discord.abc.Snowflake] = discord.utils.MISSING,
        guilds: List[discord.abc.Snowflake] = discord.utils.MISSING,
    ) -> Optional[commands.Cog]:
        cog = self.get_cog(cogname)
        if cog is None:
            return

        for cls in inspect.getmro(cog.__class__):
            try:
                hook = getattr(cog, f"_{cls.__name__}__permissions_hook")
            except AttributeError:
                pass
            else:
                self.remove_permissions_hook(hook)

        await super().remove_cog(cogname, guild=guild, guilds=guilds)
        self.dispatch("cog_remove", cog)

        cog.requires.reset()

        for meth in self.rpc_handlers.pop(cogname.upper(), ()):
            self.unregister_rpc_handler(meth)

        return cog

    async def enable_app_command(
        self,
        command_name: str,
        command_type: discord.AppCommandType = discord.AppCommandType.chat_input,
    ) -> None:
        """
        Mark an application command as being enabled.

        Enabled commands are able to be added to the bot's tree, are able to be synced, and can be invoked.

        Raises
        ------
        CommandLimitReached
            Raised when attempting to enable a command that would exceed the command limit.
        """
        if command_type is discord.AppCommandType.chat_input:
            cfg = self._config.enabled_slash_commands()
            limit = 100
        elif command_type is discord.AppCommandType.message:
            cfg = self._config.enabled_message_commands()
            limit = 5
        elif command_type is discord.AppCommandType.user:
            cfg = self._config.enabled_user_commands()
            limit = 5
        else:
            raise TypeError("command type must be one of chat_input, message, user")
        async with cfg as curr_commands:
            if len(curr_commands) >= limit:
                raise app_commands.CommandLimitReached(None, limit, type=command_type)
            if command_name not in curr_commands:
                curr_commands[command_name] = None

    async def disable_app_command(
        self,
        command_name: str,
        command_type: discord.AppCommandType = discord.AppCommandType.chat_input,
    ) -> None:
        """
        Mark an application command as being disabled.

        Disabled commands are not added to the bot's tree, are not able to be synced, and cannot be invoked.
        """
        if command_type is discord.AppCommandType.chat_input:
            cfg = self._config.enabled_slash_commands()
        elif command_type is discord.AppCommandType.message:
            cfg = self._config.enabled_message_commands()
        elif command_type is discord.AppCommandType.user:
            cfg = self._config.enabled_user_commands()
        else:
            raise TypeError("command type must be one of chat_input, message, user")
        async with cfg as curr_commands:
            if command_name in curr_commands:
                del curr_commands[command_name]

    async def list_enabled_app_commands(self) -> Dict[str, Dict[str, Optional[int]]]:
        """List the currently enabled application command names."""
        curr_slash_commands = await self._config.enabled_slash_commands()
        curr_message_commands = await self._config.enabled_message_commands()
        curr_user_commands = await self._config.enabled_user_commands()
        return {
            "slash": curr_slash_commands,
            "message": curr_message_commands,
            "user": curr_user_commands,
        }

    async def is_automod_immune(
        self, to_check: Union[discord.Message, commands.Context, discord.abc.User, discord.Role]
    ) -> bool:
        """
        Checks if the user, message, context, or role should be considered immune from automated
        moderation actions.

        Bot users are considered immune.

        This will return ``False`` in direct messages.

        Parameters
        ----------
        to_check : `discord.Message` or `commands.Context` or `discord.abc.User` or `discord.Role`
            Something to check if it would be immune

        Returns
        -------
        bool
            ``True`` if immune

        """
        guild = getattr(to_check, "guild", None)
        if not guild:
            return False

        if isinstance(to_check, discord.Role):
            ids_to_check = {to_check.id}
        else:
            author = getattr(to_check, "author", to_check)
            if author.bot:
                return True
            ids_to_check = set()
            try:
                ids_to_check = {r.id for r in author.roles}
            except AttributeError:
                # cheaper than isinstance(author, discord.User)
                pass
            ids_to_check.add(author.id)

        immune_ids = await self._config.guild(guild).autoimmune_ids()

        return not ids_to_check.isdisjoint(immune_ids)

    @staticmethod
    async def send_filtered(
        destination: discord.abc.Messageable,
        filter_mass_mentions=True,
        filter_invite_links=True,
        filter_all_links=False,
        **kwargs,
    ):
        """
        This is a convenience wrapper around

        discord.abc.Messageable.send

        It takes the destination you'd like to send to, which filters to apply
        (defaults on mass mentions, and invite links) and any other parameters
        normally accepted by destination.send

        This should realistically only be used for responding using user provided
        input. (unfortunately, including usernames)
        Manually crafted messages which don't take any user input have no need of this

        Returns
        -------
        discord.Message
            The message that was sent.
        """

        content = kwargs.pop("content", None)

        if content:
            if filter_mass_mentions:
                content = common_filters.filter_mass_mentions(content)
            if filter_invite_links:
                content = common_filters.filter_invites(content)
            if filter_all_links:
                content = common_filters.filter_urls(content)

        return await destination.send(content=content, **kwargs)

    async def add_cog(
        self,
        cog: commands.Cog,
        /,
        *,
        override: bool = False,
        guild: Optional[discord.abc.Snowflake] = discord.utils.MISSING,
        guilds: List[discord.abc.Snowflake] = discord.utils.MISSING,
    ) -> None:
        if not isinstance(cog, commands.Cog):
            raise RuntimeError(
                f"The {cog.__class__.__name__} cog in the {cog.__module__} package does "
                f"not inherit from the commands.Cog base class. The cog author must update "
                f"the cog to adhere to this requirement."
            )
        cog_name = cog.__cog_name__
        if cog_name in self.cogs:
            if not override:
                raise discord.ClientException(f"Cog named {cog_name!r} already loaded")
            await self.remove_cog(cog_name, guild=guild, guilds=guilds)

        if not hasattr(cog, "requires"):
            commands.Cog.__init__(cog)

        added_hooks = []

        try:
            for cls in inspect.getmro(cog.__class__):
                try:
                    hook = getattr(cog, f"_{cls.__name__}__permissions_hook")
                except AttributeError:
                    pass
                else:
                    self.add_permissions_hook(hook)
                    added_hooks.append(hook)

            await super().add_cog(cog, guild=guild, guilds=guilds)
            self.dispatch("cog_add", cog)
            if "permissions" not in self.extensions:
                cog.requires.ready_event.set()
        except Exception:
            for hook in added_hooks:
                try:
                    self.remove_permissions_hook(hook)
                except Exception:
                    # This shouldn't be possible
                    log.exception(
                        "A hook got extremely screwed up, "
                        "and could not be removed properly during another error in cog load."
                    )
            del cog
            raise

    def add_command(self, command: commands.Command, /) -> None:
        if not isinstance(command, commands.Command):
            raise RuntimeError("Commands must be instances of `redbot.core.commands.Command`")

        super().add_command(command)

        permissions_not_loaded = "permissions" not in self.extensions
        self.dispatch("command_add", command)
        if permissions_not_loaded:
            command.requires.ready_event.set()
        if isinstance(command, commands.Group):
            for subcommand in command.walk_commands():
                self.dispatch("command_add", subcommand)
                if permissions_not_loaded:
                    subcommand.requires.ready_event.set()
        if isinstance(command, (commands.HybridCommand, commands.HybridGroup)):
            command.app_command.extras = command.extras

    def remove_command(self, name: str, /) -> Optional[commands.Command]:
        command = super().remove_command(name)
        if command is None:
            return None
        command.requires.reset()
        if isinstance(command, commands.Group):
            for subcommand in command.walk_commands():
                subcommand.requires.reset()
        return command

    def hybrid_command(
        self,
        name: Union[str, app_commands.locale_str] = discord.utils.MISSING,
        with_app_command: bool = True,
        *args: Any,
        **kwargs: Any,
    ) -> Callable[[CommandCallback[Any, ContextT, P, _T]], commands.HybridCommand[Any, P, _T]]:
        """A shortcut decorator that invokes :func:`~redbot.core.commands.hybrid_command` and adds it to
        the internal command list via :meth:`add_command`.

        Returns
        --------
        Callable[..., :class:`HybridCommand`]
            A decorator that converts the provided method into a Command, adds it to the bot, then returns it.
        """

        def decorator(func: CommandCallback[Any, ContextT, P, _T]):
            kwargs.setdefault("parent", self)
            result = commands.hybrid_command(
                name=name, *args, with_app_command=with_app_command, **kwargs
            )(func)
            self.add_command(result)
            return result

        return decorator

    def hybrid_group(
        self,
        name: Union[str, app_commands.locale_str] = discord.utils.MISSING,
        with_app_command: bool = True,
        *args: Any,
        **kwargs: Any,
    ) -> Callable[[CommandCallback[Any, ContextT, P, _T]], commands.HybridGroup[Any, P, _T]]:
        """A shortcut decorator that invokes :func:`~redbot.core.commands.hybrid_group` and adds it to
        the internal command list via :meth:`add_command`.

        Returns
        --------
        Callable[..., :class:`HybridGroup`]
            A decorator that converts the provided method into a Group, adds it to the bot, then returns it.
        """

        def decorator(func: CommandCallback[Any, ContextT, P, _T]):
            kwargs.setdefault("parent", self)
            result = commands.hybrid_group(
                name=name, *args, with_app_command=with_app_command, **kwargs
            )(func)
            self.add_command(result)
            return result

        return decorator

    def clear_permission_rules(self, guild_id: Optional[int], **kwargs) -> None:
        """Clear all permission overrides in a scope.

        Parameters
        ----------
        guild_id : Optional[int]
            The guild ID to wipe permission overrides for. If
            ``None``, this will clear all global rules and leave all
            guild rules untouched.

        **kwargs
            Keyword arguments to be passed to each required call of
            ``commands.Requires.clear_all_rules``

        """
        for cog in self.cogs.values():
            cog.requires.clear_all_rules(guild_id, **kwargs)
        for command in self.walk_commands():
            command.requires.clear_all_rules(guild_id, **kwargs)

    def add_permissions_hook(self, hook: commands.CheckPredicate) -> None:
        """Add a permissions hook.

        Permissions hooks are check predicates which are called before
        calling `Requires.verify`, and they can optionally return an
        override: ``True`` to allow, ``False`` to deny, and ``None`` to
        default to normal behaviour.

        Parameters
        ----------
        hook
            A command check predicate which returns ``True``, ``False``
            or ``None``.

        """
        self._permissions_hooks.append(hook)

    def remove_permissions_hook(self, hook: commands.CheckPredicate) -> None:
        """Remove a permissions hook.

        Parameters are the same as those in `add_permissions_hook`.

        Raises
        ------
        ValueError
            If the permissions hook has not been added.

        """
        self._permissions_hooks.remove(hook)

    async def verify_permissions_hooks(self, ctx: commands.Context) -> Optional[bool]:
        """Run permissions hooks.

        Parameters
        ----------
        ctx : commands.Context
            The context for the command being invoked.

        Returns
        -------
        Optional[bool]
            ``False`` if any hooks returned ``False``, ``True`` if any
            hooks return ``True`` and none returned ``False``, ``None``
            otherwise.

        """
        hook_results = []
        for hook in self._permissions_hooks:
            result = await discord.utils.maybe_coroutine(hook, ctx)
            if result is not None:
                hook_results.append(result)
        if hook_results:
            if all(hook_results):
                ctx.permission_state = commands.PermState.ALLOWED_BY_HOOK
                return True
            else:
                ctx.permission_state = commands.PermState.DENIED_BY_HOOK
                return False

    async def get_owner_notification_destinations(
        self,
    ) -> List[
        Union[discord.TextChannel, discord.VoiceChannel, discord.StageChannel, discord.User]
    ]:
        """
        Gets the users and channels to send to
        """
        await self.wait_until_red_ready()
        destinations = []
        opt_outs = await self._config.owner_opt_out_list()
        for user_id in self.owner_ids:
            if user_id not in opt_outs:
                user = self.get_user(user_id)
                if user and not user.bot:  # user.bot is possible with flags and teams
                    destinations.append(user)
                else:
                    log.warning(
                        "Owner with ID %s is missing in user cache,"
                        " ignoring owner notification destination.",
                        user_id,
                    )

        channel_ids = await self._config.extra_owner_destinations()
        for channel_id in channel_ids:
            channel = self.get_channel(channel_id)
            if channel:
                destinations.append(channel)
            else:
                log.warning(
                    "Channel with ID %s is not available,"
                    " ignoring owner notification destination.",
                    channel_id,
                )

        return destinations

    async def send_to_owners(self, content=None, **kwargs):
        """
        This sends something to all owners and their configured extra destinations.

        This takes the same arguments as discord.abc.Messageable.send

        This logs failing sends
        """
        destinations = await self.get_owner_notification_destinations()

        async def wrapped_send(location, content=None, **kwargs):
            try:
                await location.send(content, **kwargs)
            except Exception as _exc:
                log.error(
                    "I could not send an owner notification to %s (%s)",
                    location,
                    location.id,
                    exc_info=_exc,
                )

        sends = [wrapped_send(d, content, **kwargs) for d in destinations]
        await asyncio.gather(*sends)

    async def wait_until_red_ready(self):
        """Wait until our post connection startup is done."""
        await self._red_ready.wait()

    async def _delete_delay(self, ctx: commands.Context):
        """
        Currently used for:
          * delete delay
        """
        guild = ctx.guild
        if guild is None:
            return
        message = ctx.message
        delay = await self._config.guild(guild).delete_delay()

        if delay == -1:
            return

        async def _delete_helper(m):
            with contextlib.suppress(discord.HTTPException):
                await m.delete()
                log.debug("Deleted command msg {}".format(m.id))

        await asyncio.sleep(delay)
        await _delete_helper(message)

    async def close(self):
        """Logs out of Discord and closes all connections."""
        await super().close()
        await _drivers.get_driver_class().teardown()
        try:
            if self.rpc_enabled:
                await self.rpc.close()
        except AttributeError:
            pass

    async def shutdown(self, *, restart: bool = False):
        """Gracefully quit Red.

        The program will exit with code :code:`0` by default.

        Parameters
        ----------
        restart : bool
            If :code:`True`, the program will exit with code :code:`26`. If the
            launcher sees this, it will attempt to restart the bot.

        """
        if not restart:
            self._shutdown_mode = ExitCodes.SHUTDOWN
        else:
            self._shutdown_mode = ExitCodes.RESTART

        await self.close()
        sys.exit(self._shutdown_mode)

    async def _core_data_deletion(
        self,
        *,
        requester: Literal["discord_deleted_user", "owner", "user", "user_strict"],
        user_id: int,
    ):
        if requester != "discord_deleted_user":
            return

        await self._config.user_from_id(user_id).clear()
        all_guilds = await self._config.all_guilds()

        async for guild_id, guild_data in AsyncIter(all_guilds.items(), steps=100):
            if user_id in guild_data.get("autoimmune_ids", []):
                async with self._config.guild_from_id(guild_id).autoimmune_ids() as ids:
                    # prevent a racy crash here without locking
                    # up the vals in all guilds first
                    with contextlib.suppress(ValueError):
                        ids.remove(user_id)

        await self._whiteblacklist_cache.discord_deleted_user(user_id)

    async def handle_data_deletion_request(
        self,
        *,
        requester: Literal["discord_deleted_user", "owner", "user", "user_strict"],
        user_id: int,
    ) -> DataDeletionResults:
        """
        This tells each cog and extension, as well as any APIs in Red
        to go delete data

        Calling this should be limited to interfaces designed for it.

        See ``redbot.core.commands.Cog.delete_data_for_user``
        for details about the parameters and intent.

        Parameters
        ----------
        requester
        user_id

        Returns
        -------
        DataDeletionResults
            A named tuple ``(failed_modules, failed_cogs, unhandled)``
            containing lists with names of failed modules, failed cogs,
            and cogs that didn't handle data deletion request.
        """
        await self.wait_until_red_ready()
        lock = self._deletion_requests.setdefault(user_id, asyncio.Lock())
        async with lock:
            return await self._handle_data_deletion_request(requester=requester, user_id=user_id)

    async def _handle_data_deletion_request(
        self,
        *,
        requester: Literal["discord_deleted_user", "owner", "user", "user_strict"],
        user_id: int,
    ) -> DataDeletionResults:
        """
        Actual interface for the above.

        Parameters
        ----------
        requester
        user_id

        Returns
        -------
        DataDeletionResults
        """
        extension_handlers = {
            extension_name: handler
            for extension_name, extension in self.extensions.items()
            if (handler := getattr(extension, "red_delete_data_for_user", None))
        }

        cog_handlers = {
            cog_qualname: cog.red_delete_data_for_user for cog_qualname, cog in self.cogs.items()
        }

        special_handlers = {
            "Red Core Modlog API": modlog._process_data_deletion,
            "Red Core Bank API": bank._process_data_deletion,
            "Red Core Bot Data": self._core_data_deletion,
        }

        failures = {
            "extension": [],
            "cog": [],
            "unhandled": [],
        }

        async def wrapper(func, stype, sname):
            try:
                await func(requester=requester, user_id=user_id)
            except commands.commands.RedUnhandledAPI:
                log.warning(f"{stype}.{sname} did not handle data deletion ")
                failures["unhandled"].append(sname)
            except Exception as exc:
                log.exception(f"{stype}.{sname} errored when handling data deletion ")
                failures[stype].append(sname)

        handlers = [
            *(wrapper(coro, "extension", name) for name, coro in extension_handlers.items()),
            *(wrapper(coro, "cog", name) for name, coro in cog_handlers.items()),
            *(wrapper(coro, "extension", name) for name, coro in special_handlers.items()),
        ]

        await asyncio.gather(*handlers)

        return DataDeletionResults(
            failed_modules=failures["extension"],
            failed_cogs=failures["cog"],
            unhandled=failures["unhandled"],
        )

    async def send_interactive(
        self,
        channel: discord.abc.Messageable,
        messages: Iterable[str],
        *,
        user: Optional[discord.User] = None,
        box_lang: Optional[str] = None,
        timeout: int = 60,
        join_character: str = "",
    ) -> List[discord.Message]:
        """
        Send multiple messages interactively.

        The user will be prompted for whether or not they would like to view
        the next message, one at a time. They will also be notified of how
        many messages are remaining on each prompt.

        Parameters
        ----------
        channel : discord.abc.Messageable
            The channel to send the messages to.
        messages : `iterable` of `str`
            The messages to send.
        user : discord.User
            The user that can respond to the prompt.
            When this is ``None``, any user can respond.
        box_lang : Optional[str]
            If specified, each message will be contained within a code block of
            this language.
        timeout : int
            How long the user has to respond to the prompt before it times out.
            After timing out, the bot deletes its prompt message.
        join_character : str
            The character used to join all the messages when the file output
            is selected.

        Returns
        -------
        List[discord.Message]
            A list of sent messages.
        """
        messages = tuple(messages)
        ret = []
        # using dpy_commands.Context to keep the Messageable contract in full
        if isinstance(channel, dpy_commands.Context):
            # this is only necessary to ensure that `channel.delete_messages()` works
            # when `ctx.channel` has that method
            channel = channel.channel

        for idx, page in enumerate(messages, 1):
            if box_lang is None:
                msg = await channel.send(page)
            else:
                msg = await channel.send(box(page, lang=box_lang))
            ret.append(msg)
            n_remaining = len(messages) - idx
            if n_remaining > 0:
                if n_remaining == 1:
                    prompt_text = _(
                        "There is still one message remaining. Type {command_1} to continue"
                        " or {command_2} to upload all contents as a file."
                    )
                else:
                    prompt_text = _(
                        "There are still {count} messages remaining. Type {command_1} to continue"
                        " or {command_2} to upload all contents as a file."
                    )
                query = await channel.send(
                    prompt_text.format(count=n_remaining, command_1="`more`", command_2="`file`")
                )
                pred = MessagePredicate.lower_contained_in(
                    ("more", "file"), channel=channel, user=user
                )
                try:
                    resp = await self.wait_for(
                        "message",
                        check=pred,
                        timeout=timeout,
                    )
                except asyncio.TimeoutError:
                    with contextlib.suppress(discord.HTTPException):
                        await query.delete()
                    break
                else:
                    try:
                        await channel.delete_messages((query, resp))
                    except (discord.HTTPException, AttributeError):
                        # In case the bot can't delete other users' messages,
                        # or is not a bot account
                        # or channel is a DM
                        with contextlib.suppress(discord.HTTPException):
                            await query.delete()
                    if pred.result == 1:
                        ret.append(
                            await channel.send(file=text_to_file(join_character.join(messages)))
                        )
                        break
        return ret
