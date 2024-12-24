"""Module for command helpers and classes.

This module contains extended classes and functions which are intended to
be used instead of those from the `discord.ext.commands` module.
"""
from __future__ import annotations

import inspect
import io
import re
import functools
import weakref
from typing import (
    Any,
    Awaitable,
    Callable,
    ClassVar,
    Dict,
    List,
    Literal,
    Optional,
    Tuple,
    TypeVar,
    Union,
    MutableMapping,
    TYPE_CHECKING,
)

import discord
from discord.ext.commands import (
    BadArgument,
    CommandError,
    CheckFailure,
    DisabledCommand,
    command as dpy_command_deco,
    Command as DPYCommand,
    GroupCog as DPYGroupCog,
    HybridCommand as DPYHybridCommand,
    HybridGroup as DPYHybridGroup,
    Cog as DPYCog,
    CogMeta as DPYCogMeta,
    Group as DPYGroup,
    Greedy,
)

from .requires import PermState, PrivilegeLevel, Requires, PermStateAllowedStates
from .. import app_commands
from ..i18n import Translator

_T = TypeVar("_T")
_CogT = TypeVar("_CogT", bound="Cog")


if TYPE_CHECKING:
    # circular import avoidance
    from .context import Context
    from typing_extensions import ParamSpec, Concatenate
    from discord.ext.commands._types import ContextT, Coro

    _P = ParamSpec("_P")

    CommandCallback = Union[
        Callable[Concatenate[_CogT, ContextT, _P], Coro[_T]],
        Callable[Concatenate[ContextT, _P], Coro[_T]],
    ]
else:
    _P = TypeVar("_P")


__all__ = (
    "Cog",
    "CogMixin",
    "CogCommandMixin",
    "CogGroupMixin",
    "Command",
    "Group",
    "GroupCog",
    "GroupMixin",
    "HybridCommand",
    "HybridGroup",
    "command",
    "group",
    "hybrid_command",
    "hybrid_group",
    "RESERVED_COMMAND_NAMES",
    "RedUnhandledAPI",
)

#: The following names are reserved for various reasons
RESERVED_COMMAND_NAMES = (
    "cancel",  # reserved due to use in ``redbot.core.utils.MessagePredicate``
)

_ = Translator("commands.commands", __file__)


class RedUnhandledAPI(Exception):
    """An exception which can be raised to signal a lack of handling specific APIs"""

    pass


class CogCommandMixin:
    """A mixin for cogs and commands."""

    @property
    def help(self) -> str:
        """To be defined by subclasses"""
        ...

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if isinstance(self, Command):
            decorated = self.callback
        else:
            decorated = self
        self.requires: Requires = Requires(
            privilege_level=getattr(
                decorated, "__requires_privilege_level__", PrivilegeLevel.NONE
            ),
            user_perms=getattr(decorated, "__requires_user_perms__", {}),
            bot_perms=getattr(decorated, "__requires_bot_perms__", {}),
            checks=getattr(decorated, "__requires_checks__", []),
        )

    def format_text_for_context(self, ctx: "Context", text: str) -> str:
        """
        This formats text based on values in context

        The steps are (currently, roughly) the following:

            - substitute ``[p]`` with ``ctx.clean_prefix``
            - substitute ``[botname]`` with ``ctx.me.display_name``

        More steps may be added at a later time.

        Cog creators should only override this if they want
        help text to be modified, and may also want to
        look at `format_help_for_context` and (for commands only)
        ``format_shortdoc_for_context``

        Parameters
        ----------
        ctx: Context
        text: str

        Returns
        -------
        str
            text which has had some portions replaced based on context
        """
        formatting_pattern = re.compile(r"\[p\]|\[botname\]")

        def replacement(m: re.Match) -> str:
            s = m.group(0)
            if s == "[p]":
                return ctx.clean_prefix
            if s == "[botname]":
                return ctx.me.display_name
            # We shouldn't get here:
            return s

        return formatting_pattern.sub(replacement, text)

    def format_help_for_context(self, ctx: "Context") -> str:
        """
        This formats the help string based on values in context

        The steps are (currently, roughly) the following:

            - get the localized help
            - substitute ``[p]`` with ``ctx.clean_prefix``
            - substitute ``[botname]`` with ``ctx.me.display_name``

        More steps may be added at a later time.

        Cog creators may override this in their own command classes
        as long as the method signature stays the same.

        Parameters
        ----------
        ctx: Context

        Returns
        -------
        str
            Localized help with some formatting
        """

        help_str = self.help
        if not help_str:
            # Short circuit out on an empty help string
            return help_str

        return self.format_text_for_context(ctx, help_str)

    def allow_for(self, model_id: Union[int, str], guild_id: int) -> None:
        """Actively allow this command for the given model.

        Parameters
        ----------
        model_id : Union[int, str]
            Must be an `int` if supplying an ID. `str` is only valid
            for "default".
        guild_id : int
            The guild ID to allow this cog or command in. For global
            rules, use ``0``.

        """
        self.requires.set_rule(model_id, PermState.ACTIVE_ALLOW, guild_id=guild_id)

    def deny_to(self, model_id: Union[int, str], guild_id: int) -> None:
        """Actively deny this command to the given model.

        Parameters
        ----------
        model_id : Union[int, str]
            Must be an `int` if supplying an ID. `str` is only valid
            for "default".
        guild_id : int
            The guild ID to deny this cog or command in. For global
            rules, use ``0``.

        """
        cur_rule = self.requires.get_rule(model_id, guild_id=guild_id)
        if cur_rule is PermState.PASSIVE_ALLOW:
            self.requires.set_rule(model_id, PermState.CAUTIOUS_ALLOW, guild_id=guild_id)
        else:
            self.requires.set_rule(model_id, PermState.ACTIVE_DENY, guild_id=guild_id)

    def clear_rule_for(
        self, model_id: Union[int, str], guild_id: int
    ) -> Tuple[PermState, PermState]:
        """Clear the rule which is currently set for this model.

        Parameters
        ----------
        model_id : Union[int, str]
            Must be an `int` if supplying an ID. `str` is only valid
            for "default".
        guild_id : int
            The guild ID. For global rules, use ``0``.

        """
        cur_rule = self.requires.get_rule(model_id, guild_id=guild_id)
        if cur_rule is PermState.ACTIVE_ALLOW:
            new_rule = PermState.NORMAL
        elif cur_rule is PermState.ACTIVE_DENY:
            new_rule = PermState.NORMAL
        elif cur_rule is PermState.CAUTIOUS_ALLOW:
            new_rule = PermState.PASSIVE_ALLOW
        else:
            return cur_rule, cur_rule
        self.requires.set_rule(model_id, new_rule, guild_id=guild_id)
        return cur_rule, new_rule

    def set_default_rule(self, rule: Optional[bool], guild_id: int) -> None:
        """Set the default rule for this cog or command.

        Parameters
        ----------
        rule : Optional[bool]
            The rule to set as default. If ``True`` for allow,
            ``False`` for deny and ``None`` for normal.
        guild_id : int
            The guild to set the default rule in. When ``0``, this will
            set the global default rule.

        """
        if rule is None:
            self.clear_rule_for(Requires.DEFAULT, guild_id=guild_id)
        elif rule is True:
            self.allow_for(Requires.DEFAULT, guild_id=guild_id)
        elif rule is False:
            self.deny_to(Requires.DEFAULT, guild_id=guild_id)


class Command(CogCommandMixin, DPYCommand):
    """Command class for Red.

    This should not be created directly, and instead via the decorator.

    This class inherits from `discord.ext.commands.Command`. The
    attributes listed below are simply additions to the ones listed
    with that class.

    .. warning::

        If you subclass this command, attributes and methods
        must remain compatible.

        None of your methods should start with ``red_`` or
        be dunder names which start with red (eg. ``__red_test_thing__``)
        unless to override behavior in a method designed to be overridden,
        as this prefix is reserved for future methods in order to be
        able to add features non-breakingly.

    Attributes
    ----------
    checks : List[`coroutine function`]
        A list of check predicates which cannot be overridden, unlike
        `Requires.checks`.
    translator : Translator
        A translator for this command's help docstring.
    ignore_optional_for_conversion : bool
        A value which can be set to not have discord.py's
        argument parsing behavior for ``typing.Optional``
        (type used will be of the inner type instead)
    """

    def __init__(self, *args, **kwargs):
        self.ignore_optional_for_conversion = kwargs.pop("ignore_optional_for_conversion", False)
        self._disabled_in: discord.utils.SnowflakeList = discord.utils.SnowflakeList([])
        self._help_override = kwargs.pop("help_override", None)
        self.translator = kwargs.pop("i18n", None)
        super().__init__(*args, **kwargs)
        if self.parent is None:
            for name in (self.name, *self.aliases):
                if name in RESERVED_COMMAND_NAMES:
                    raise RuntimeError(
                        f"The name `{name}` cannot be set as a command name. It is reserved for internal use."
                    )
        if len(self.qualified_name) > 60:
            raise RuntimeError(
                f"This command ({self.qualified_name}) has an excessively long qualified name, "
                "and will not be added to the bot to prevent breaking tools and menus. (limit 60)"
            )

    def _ensure_assignment_on_copy(self, other):
        super()._ensure_assignment_on_copy(other)

        # Red specific
        other.requires = self.requires
        other.ignore_optional_for_conversion = self.ignore_optional_for_conversion
        return other

    @property
    def callback(self):
        return self._callback

    @callback.setter
    def callback(self, function):
        # Below should be mostly the same as discord.py
        #
        # Here's the list of cases where the behavior differs:
        #   - `typing.Optional` behavior is changed
        #      when `ignore_optional_for_conversion` option is used
        super(Command, Command).callback.__set__(self, function)

        if not self.ignore_optional_for_conversion:
            return

        _NoneType = type(None)
        for key, value in self.params.items():
            origin = getattr(value.annotation, "__origin__", None)
            if origin is not Union:
                continue
            args = value.annotation.__args__
            if _NoneType in args:
                args = tuple(a for a in args if a is not _NoneType)
                # typing.Union is automatically deduplicated and flattened
                # so we don't need to anything else here
                self.params[key] = value = value.replace(annotation=Union[args])

    @property
    def help(self):
        """Help string for this command.

        If the :code:`help` kwarg was passed into the decorator, it will
        default to that. If not, it will attempt to translate the docstring
        of the command's callback function.
        """
        if self._help_override is not None:
            return self._help_override
        if self.translator is None:
            translator = getattr(self.cog, "__translator__", lambda s: s)
        else:
            translator = self.translator
        command_doc = self.callback.__doc__
        if command_doc is None:
            return ""
        return inspect.cleandoc(translator(command_doc))

    @help.setter
    def help(self, value):
        # We don't want our help property to be overwritten, namely by super()
        pass

    @property
    def parents(self) -> List["Group"]:
        """List[commands.Group] : Returns all parent commands of this command.

        This is sorted by the length of :attr:`.qualified_name` from highest to lowest.
        If the command has no parents, this will be an empty list.
        """
        cmd = self.parent
        entries = []
        while cmd is not None:
            entries.append(cmd)
            cmd = cmd.parent
        return sorted(entries, key=lambda x: len(x.qualified_name), reverse=True)

    # noinspection PyMethodOverriding
    async def can_run(
        self,
        ctx: "Context",
        /,
        *,
        check_all_parents: bool = False,
        change_permission_state: bool = False,
    ) -> bool:
        """Check if this command can be run in the given context.

        This function first checks if the command can be run using
        discord.py's method `discord.ext.commands.Command.can_run`,
        then will return the result of `Requires.verify`.

        Keyword Arguments
        -----------------
        check_all_parents : bool
            If ``True``, this will check permissions for all of this
            command's parents and its cog as well as the command
            itself. Defaults to ``False``.
        change_permission_state : bool
            Whether or not the permission state should be changed as
            a result of this call. For most cases this should be
            ``False``. Defaults to ``False``.
        """
        ret = await super().can_run(ctx)
        if ret is False:
            return False

        # This is so contexts invoking other commands can be checked with
        # this command as well
        original_command = ctx.command
        original_state = ctx.permission_state
        ctx.command = self

        if check_all_parents is True:
            # Since we're starting from the beginning, we should reset the state to normal
            ctx.permission_state = PermState.NORMAL
            for parent in reversed(self.parents):
                try:
                    result = await parent.can_run(ctx, change_permission_state=True)
                except CommandError:
                    result = False

                if result is False:
                    return False

        if self.parent is None and self.cog is not None:
            # For top-level commands, we need to check the cog's requires too
            ret = await self.cog.requires.verify(ctx)
            if ret is False:
                return False

        try:
            return await self.requires.verify(ctx)
        finally:
            ctx.command = original_command
            if not change_permission_state:
                ctx.permission_state = original_state

    def is_enabled(self, guild: Optional[discord.abc.Snowflake] = None) -> bool:
        """
        Check if the command is enabled globally or in a guild.

        When guild is provided, this method checks whether
        the command is enabled both globally and in the guild.

        This is generally set by the settings managed with
        the ``[p]command enable/disable global/server`` commands.

        Parameters
        ----------
        guild : discord.abc.Snowflake, optional
            The guild to check that the command is enabled in.
            If this is ``None``, this will check whether
            the command is enabled globally.

        Returns
        -------
        bool
            ``True`` if the command is enabled.
        """
        if not self.enabled:
            return False
        if guild is not None:
            if self._disabled_in.has(guild.id):
                return False

        return True

    async def prepare(self, ctx, /):
        ctx.command = self

        cmd_enabled = self.is_enabled(ctx.guild)
        if not cmd_enabled:
            raise DisabledCommand(f"{self.name} command is disabled")

        if not await self.can_run(ctx, change_permission_state=True):
            raise CheckFailure(f"The check functions for command {self.qualified_name} failed.")

        if self._max_concurrency is not None:
            await self._max_concurrency.acquire(ctx)

        try:
            if self.cooldown_after_parsing:
                await self._parse_arguments(ctx)
                self._prepare_cooldowns(ctx)
            else:
                self._prepare_cooldowns(ctx)
                await self._parse_arguments(ctx)

            await self.call_before_hooks(ctx)
        except:
            if self._max_concurrency is not None:
                await self._max_concurrency.release(ctx)
            raise

    async def can_see(self, ctx: "Context"):
        """Check if this command is visible in the given context.

        In short, this will verify whether the user can run the
        command, and also whether the command is hidden or not.

        Parameters
        ----------
        ctx : `Context`
            The invocation context to check with.

        Returns
        -------
        bool
            ``True`` if this command is visible in the given context.

        """
        for cmd in (self, *self.parents):
            if cmd.hidden:
                return False
            try:
                can_run = await self.can_run(
                    ctx, check_all_parents=True, change_permission_state=False
                )
            except (CheckFailure, DisabledCommand):
                return False
            else:
                if can_run is False:
                    return False

        return True

    def disable_in(self, guild: discord.Guild) -> bool:
        """
        Disable this command in the given guild.

        This is generally called by the settings managed with
        the ``[p]command disable global/server`` commands.
        Any changes made outside of that will not persist after cog
        reload and may also be affected when either of those commands
        is called on this command. It is not recommended to rely on
        this method, if you want a consistent behavior.

        Parameters
        ----------
        guild : discord.Guild
            The guild to disable the command in.

        Returns
        -------
        bool
            ``True`` if the command wasn't already disabled.
        """
        if self._disabled_in.has(guild.id):
            return False

        self._disabled_in.add(guild.id)
        return True

    def enable_in(self, guild: discord.Guild) -> bool:
        """Enable this command in the given guild.

        This is generally called by the settings managed with
        the ``[p]command disable global/server`` commands.
        Any changes made outside of that will not persist after cog
        reload and may also be affected when either of those commands
        is called on this command. It is not recommended to rely on
        this method, if you want a consistent behavior.

        Parameters
        ----------
        guild : discord.Guild
            The guild to enable the command in.

        Returns
        -------
        bool
            ``True`` if the command wasn't already enabled.
        """
        try:
            self._disabled_in.remove(guild.id)
        except ValueError:
            return False

        return True

    def allow_for(self, model_id: Union[int, str], guild_id: int) -> None:
        super().allow_for(model_id, guild_id=guild_id)
        parents = self.parents
        if self.cog is not None:
            parents.append(self.cog)
        for parent in parents:
            cur_rule = parent.requires.get_rule(model_id, guild_id=guild_id)
            if cur_rule is PermState.NORMAL:
                parent.requires.set_rule(model_id, PermState.PASSIVE_ALLOW, guild_id=guild_id)
            elif cur_rule is PermState.ACTIVE_DENY:
                parent.requires.set_rule(model_id, PermState.CAUTIOUS_ALLOW, guild_id=guild_id)

    def clear_rule_for(
        self, model_id: Union[int, str], guild_id: int
    ) -> Tuple[PermState, PermState]:
        old_rule, new_rule = super().clear_rule_for(model_id, guild_id=guild_id)
        if old_rule is PermState.ACTIVE_ALLOW:
            parents = self.parents
            if self.cog is not None:
                parents.append(self.cog)
            for parent in parents:
                should_continue = parent.reevaluate_rules_for(model_id, guild_id=guild_id)[1]
                if not should_continue:
                    break
        return old_rule, new_rule

    def error(self, coro, /):
        """
        A decorator that registers a coroutine as a local error handler.

        A local error handler is an :func:`.on_command_error` event limited to
        a single command.

        The on_command_error event is still dispatched
        for commands with a dedicated error handler.

        Red's global error handler will ignore commands with a registered error handler.

        To have red handle specific errors with the default behavior,
        call ``Red.on_command_error`` with ``unhandled_by_cog`` set to True.

        Due to how discord.py wraps exceptions, the exception you are expecting here
        is likely in ``error.original`` despite that the normal event handler for bot
        wide command error handling has no such wrapping.

        For example:

            .. code-block:: python

                @a_command.error
                async def a_command_error_handler(self, ctx, error):
                    if isinstance(error.original, MyErrorType):
                        self.log_exception(error.original)
                    else:
                        await ctx.bot.on_command_error(ctx, error.original, unhandled_by_cog=True)

        Parameters
        -----------
        coro : :term:`coroutine function`
            The coroutine to register as the local error handler.

        Raises
        -------
        discord.ClientException
            The coroutine is not actually a coroutine.
        """
        return super().error(coro)

    def format_shortdoc_for_context(self, ctx: "Context") -> str:
        """
        This formats the short version of the help
        string based on values in context

        See ``format_text_for_context`` for the actual implementation details

        Cog creators may override this in their own command and cog classes
        as long as the method signature stays the same.

        Parameters
        ----------
        ctx: Context

        Returns
        -------
        str
            Localized help with some formatting
        """
        sh = self.short_doc
        return self.format_text_for_context(ctx, sh) if sh else sh


class GroupMixin(discord.ext.commands.GroupMixin):
    """Mixin for `Group` and `Red` classes.

    This class inherits from :class:`discord.ext.commands.GroupMixin`.
    """

    def command(self, *args, **kwargs):
        """A shortcut decorator that invokes :func:`.command` and adds it to
        the internal command list via :meth:`~.GroupMixin.add_command`.
        """

        def decorator(func):
            kwargs.setdefault("parent", self)
            result = command(*args, **kwargs)(func)
            self.add_command(result)
            return result

        return decorator

    def group(self, *args, **kwargs):
        """A shortcut decorator that invokes :func:`.group` and adds it to
        the internal command list via :meth:`~.GroupMixin.add_command`.
        """

        def decorator(func):
            kwargs.setdefault("parent", self)
            result = group(*args, **kwargs)(func)
            self.add_command(result)
            return result

        return decorator


class CogGroupMixin:
    requires: Requires

    def reevaluate_rules_for(
        self, model_id: Union[str, int], guild_id: int = 0
    ) -> Tuple[PermState, bool]:
        """Re-evaluate a rule by checking subcommand rules.

        This is called when a subcommand is no longer actively allowed.

        Parameters
        ----------
        model_id : Union[int, str]
            Must be an `int` if supplying an ID. `str` is only valid
            for "default".
        guild_id : int
            The guild ID. For global rules, use ``0``.

        Returns
        -------
        Tuple[PermState, bool]
            A 2-tuple containing the new rule and a bool indicating
            whether or not the rule was changed as a result of this
            call.

        :meta private:
        """
        cur_rule = self.requires.get_rule(model_id, guild_id=guild_id)
        if cur_rule not in (PermState.NORMAL, PermState.ACTIVE_ALLOW, PermState.ACTIVE_DENY):
            # The above three states are unaffected by subcommand rules
            # Remaining states can be changed if there exists no actively-allowed
            # subcommand (this includes subcommands multiple levels below)

            all_commands: Dict[str, Command] = getattr(self, "all_commands", {})

            if any(
                cmd.requires.get_rule(model_id, guild_id=guild_id) in PermStateAllowedStates
                for cmd in all_commands.values()
            ):
                return cur_rule, False
            elif cur_rule is PermState.PASSIVE_ALLOW:
                self.requires.set_rule(model_id, PermState.NORMAL, guild_id=guild_id)
                return PermState.NORMAL, True
            elif cur_rule is PermState.CAUTIOUS_ALLOW:
                self.requires.set_rule(model_id, PermState.ACTIVE_DENY, guild_id=guild_id)
                return PermState.ACTIVE_DENY, True

        # Default return value
        return cur_rule, False


class Group(GroupMixin, Command, CogGroupMixin, DPYGroup):
    """Group command class for Red.

    This class inherits from `Command`, with :class:`GroupMixin` and
    `discord.ext.commands.Group` mixed in.
    """

    def __init__(self, *args, **kwargs):
        self.autohelp = kwargs.pop("autohelp", True)
        super().__init__(*args, **kwargs)

    async def invoke(self, ctx: "Context", /):
        # we skip prepare in some cases to avoid some things
        # We still always want this part of the behavior though
        ctx.command = self
        ctx.subcommand_passed = None
        # Our re-ordered behavior below.
        view = ctx.view
        previous = view.index
        view.skip_ws()
        trigger = view.get_word()
        if trigger:
            ctx.subcommand_passed = trigger
            ctx.invoked_subcommand = self.all_commands.get(trigger, None)
        view.index = previous
        view.previous = previous

        if ctx.invoked_subcommand is None or self == ctx.invoked_subcommand:
            if self.autohelp and not self.invoke_without_command:
                if not await self.can_run(ctx, change_permission_state=True):
                    raise CheckFailure()
                # This ordering prevents sending help before checking `before_invoke` hooks
                await super().invoke(ctx)
                return await ctx.send_help()
        elif self.invoke_without_command:
            # So invoke_without_command when a subcommand of this group is invoked
            # will skip the invocation of *this* command. However, because of
            # how our permissions system works, we don't want it to skip the checks
            # as well.
            if not await self.can_run(ctx, change_permission_state=True):
                raise CheckFailure()
            # this is actually why we don't prepare earlier.

        await super().invoke(ctx)


class CogMixin(CogGroupMixin, CogCommandMixin):
    """Mixin class for a cog, intended for use with discord.py's cog class"""

    @property
    def help(self):
        doc = self.__doc__
        translator = getattr(self, "__translator__", lambda s: s)
        if doc:
            return inspect.cleandoc(translator(doc))

    async def red_get_data_for_user(self, *, user_id: int) -> MutableMapping[str, io.BytesIO]:
        """

        .. note::

            This method is documented `provisionally <developer-guarantees-exclusions>`
            and may have minor changes made to it.
            It is not expected to undergo major changes,
            but nothing utilizes this method yet and the inclusion of this method
            in documentation in advance is solely to allow cog creators time to prepare.


        This should be overridden by all cogs.

        Overridden implementations should return a mapping of filenames to io.BytesIO
        containing a human-readable version of the data
        the cog has about the specified user_id or an empty mapping
        if the cog does not have end user data.

        The data should be easily understood for what it represents to
        most users of age to use Discord.

        You may want to include a readme file
        which explains specifics about the data.

        This method may also be implemented for an extension.

        Parameters
        ----------
        user_id: int

        Returns
        -------
        MutableMapping[str, io.BytesIO]
            A mapping of filenames to BytesIO objects
            suitable to send as a files or as part of an archive to a user.

            This may be empty if you don't have data for users.

        Raises
        ------
        RedUnhandledAPI
            If the method was not overridden,
            or an overridden implementation is not handling this

        """
        raise RedUnhandledAPI()

    async def red_delete_data_for_user(
        self,
        *,
        requester: Literal["discord_deleted_user", "owner", "user", "user_strict"],
        user_id: int,
    ):
        """
        This should be overridden by all cogs.

        If your cog does not store data, overriding and doing nothing should still
        be done to indicate that this has been considered.

        .. note::
                This may receive other strings in the future without warning
                you should safely handle
                any string value (log a warning if needed)
                as additional requester types may be added
                in the future without prior warning.
                (see what this method can raise for details)


        This method can currently be passed one of these strings:


            - ``"discord_deleted_user"``:

                The request should be processed as if
                Discord has asked for the data removal
                This then additionally must treat the
                user ID itself as something to be deleted.
                The user ID is no longer operational data
                as the ID no longer refers to a valid user.

            - ``"owner"``:

                The request was made by the bot owner.
                If removing the data requested by the owner
                would be an operational hazard
                (such as removing a user id from a blocked user list)
                you may elect to inform the user of an alternative way
                to remove that ID to ensure the process can not be abused
                by users to bypass anti-abuse measures,
                but there must remain a way for them to process this request.

            - ``"user_strict"``:

                The request was made by a user,
                the bot settings allow a user to request their own data
                be deleted, and the bot is configured to respect this
                at the cost of functionality.
                Cogs may retain data needed for anti abuse measures
                such as IDs and timestamps of interactions,
                but should not keep EUD such
                as user nicknames if receiving a request of this nature.

            - ``"user"``:

                The request was made by a user,
                the bot settings allow a user to request their own data
                be deleted, and the bot is configured to let cogs keep
                data needed for operation.
                Under this case, you may elect to retain data which is
                essential to the functionality of the cog. This case will
                only happen if the bot owner has opted into keeping
                minimal EUD needed for cog functionality.


        Parameters
        ----------
        requester: Literal["discord_deleted_user", "owner", "user", "user_strict"]
            See above notes for details about this parameter
        user_id: int
            The user ID which needs deletion handling

        Raises
        ------
        RedUnhandledAPI
            If the method was not overridden,
            or an overridden implementation is not handling this
        """
        raise RedUnhandledAPI()

    async def can_run(self, ctx: "Context", /, **kwargs) -> bool:
        """
        This really just exists to allow easy use with other methods using can_run
        on commands and groups such as help formatters.

        kwargs used in that won't apply here as they don't make sense to,
        but will be swallowed silently for a compatible signature for ease of use.

        Parameters
        ----------
        ctx : `Context`
            The invocation context to check with.

        Returns
        -------
        bool
            ``True`` if this cog is usable in the given context.

        :meta private:
        """

        try:
            can_run = await self.requires.verify(ctx)
        except CommandError:
            return False

        return can_run

    async def can_see(self, ctx: "Context", /) -> bool:
        """Check if this cog is visible in the given context.

        In short, this will verify whether
        the user is allowed to access the cog by permissions.

        This has an identical signature to the one used by commands, and groups,
        but needs a different underlying mechanism.

        Parameters
        ----------
        ctx : `Context`
            The invocation context to check with.

        Returns
        -------
        bool
            ``True`` if this cog is visible in the given context.

        :meta private:
        """

        return await self.can_run(ctx)


class Cog(CogMixin, DPYCog, metaclass=DPYCogMeta):
    """
    Red's Cog base class

    This includes a metaclass from discord.py

    .. warning::

        None of your methods should start with ``red_`` or
        be dunder names which start with red (eg. ``__red_test_thing__``)
        unless to override behavior in a method designed to be overridden,
        as this prefix is reserved for future methods in order to be
        able to add features non-breakingly.

        Attributes and methods must remain compatible
        with discord.py and with any of red's methods and attributes.

    """

    __cog_commands__: Tuple[Command]

    @property
    def all_commands(self) -> Dict[str, Command]:
        """
        This does not have identical behavior to
        Group.all_commands but should return what you expect

        :meta private:
        """
        return {cmd.name: cmd for cmd in self.__cog_commands__}


class GroupCog(Cog, DPYGroupCog):
    """
    Red's Cog base class with app commands group as the base.

    This class inherits from `Cog` and `discord.ext.commands.GroupCog`
    """


class HybridCommand(Command, DPYHybridCommand[_CogT, _P, _T]):
    """HybridCommand class for Red.

    This should not be created directly, and instead via the decorator.

    This class inherits from `Command` and `discord.ext.commands.HybridCommand`.

    .. warning::

        This class is not intended to be subclassed.
    """


class HybridGroup(Group, DPYHybridGroup[_CogT, _P, _T]):
    """HybridGroup command class for Red.

    This should not be created directly, and instead via the decorator.

    This class inherits from `Group` and `discord.ext.commands.HybridGroup`.

    .. note::
        Red's HybridGroups differ from `discord.ext.commands.HybridGroup`
        by setting `discord.ext.commands.Group.invoke_without_command` to be `False` by default.
        If `discord.ext.commands.HybridGroup.fallback` is provided then
        `discord.ext.commands.Group.invoke_without_command` is
        set to `True`.

    .. warning::

        This class is not intended to be subclassed.
    """

    def __init__(self, *args: Any, **kwargs: Any):
        fallback = "fallback" in kwargs and kwargs["fallback"] is not None
        invoke_without_command = kwargs.pop("invoke_without_command", False) or fallback
        kwargs["invoke_without_command"] = invoke_without_command
        super().__init__(*args, **kwargs)
        self.invoke_without_command = invoke_without_command

    @property
    def callback(self):
        return self._callback

    @callback.setter
    def callback(self, function):
        # Below should be mostly the same as discord.py
        super(__class__, __class__).callback.__set__(self, function)

        if not self.invoke_without_command and self.params:
            raise TypeError(
                "You cannot have a group command with callbacks and `invoke_without_command` set to False."
            )

    def command(self, name: str = discord.utils.MISSING, *args: Any, **kwargs: Any):
        def decorator(func):
            kwargs.setdefault("parent", self)
            result = hybrid_command(name=name, *args, **kwargs)(func)
            self.add_command(result)
            return result

        return decorator

    def group(
        self,
        name: str = discord.utils.MISSING,
        *args: Any,
        **kwargs: Any,
    ):
        def decorator(func):
            kwargs.setdefault("parent", self)
            result = hybrid_group(name=name, *args, **kwargs)(func)
            self.add_command(result)
            return result

        return decorator


def hybrid_command(
    name: Union[str, app_commands.locale_str] = discord.utils.MISSING,
    *,
    with_app_command: bool = True,
    **attrs: Any,
) -> Callable[[CommandCallback[_CogT, ContextT, _P, _T]], HybridCommand[_CogT, _P, _T]]:
    """A decorator which transforms an async function into a `HybridCommand`.

    Same interface as `discord.ext.commands.hybrid_command`.
    """

    def decorator(func: CommandCallback[_CogT, ContextT, _P, _T]) -> HybridCommand[_CogT, _P, _T]:
        if isinstance(func, Command):
            raise TypeError("callback is already a command.")
        attrs["help_override"] = attrs.pop("help", None)
        return HybridCommand(func, name=name, with_app_command=with_app_command, **attrs)

    return decorator


def hybrid_group(
    name: Union[str, app_commands.locale_str] = discord.utils.MISSING,
    *,
    with_app_command: bool = True,
    **attrs: Any,
) -> Callable[[CommandCallback[_CogT, ContextT, _P, _T]], HybridGroup[_CogT, _P, _T]]:
    """A decorator which transforms an async function into a `HybridGroup`.

    Same interface as `discord.ext.commands.hybrid_group`.
    """

    def decorator(func: CommandCallback[_CogT, ContextT, _P, _T]):
        if isinstance(func, Command):
            raise TypeError("callback is already a command.")
        attrs["help_override"] = attrs.pop("help", None)
        return HybridGroup(func, name=name, with_app_command=with_app_command, **attrs)

    return decorator


def command(name=None, cls=Command, **attrs):
    """A decorator which transforms an async function into a `Command`.

    Same interface as `discord.ext.commands.command`.
    """
    attrs["help_override"] = attrs.pop("help", None)

    return dpy_command_deco(name, cls, **attrs)


def group(name=None, cls=Group, **attrs):
    """A decorator which transforms an async function into a `Group`.

    Same interface as `discord.ext.commands.group`.
    """
    return dpy_command_deco(name, cls, **attrs)


# The below are intentionally left out of `__all__`
# as they are not intended for general use
class _AlwaysAvailableMixin:
    """
    This should be used for commands
    which should not be disabled or removed

    These commands cannot belong to any cog except Core (core_commands.py)
    to prevent issues with the appearance of certain behavior.

    These commands do not respect most forms of checks, and
    should only be used with that in mind.

    This particular class is not supported for 3rd party use
    """

    async def can_run(self, ctx, /, *args, **kwargs) -> bool:
        return not ctx.author.bot

    can_see = can_run


class _RuleDropper(CogCommandMixin):
    """
    Objects inheriting from this, be they command or cog,
    should not be interfered with operation except by their own rules,
    or by global checks which are not tailored for these objects but instead
    on global abuse prevention
    (such as a check that disallows blocked users and bots from interacting.)

    This should not be used by 3rd-party extensions directly for their own objects.
    """

    def allow_for(self, model_id: Union[int, str], guild_id: int) -> None:
        """This will do nothing."""

    def deny_to(self, model_id: Union[int, str], guild_id: int) -> None:
        """This will do nothing."""

    def clear_rule_for(
        self, model_id: Union[int, str], guild_id: int
    ) -> Tuple[PermState, PermState]:
        """
        This will do nothing, except return a compatible rule
        """
        cur_rule = self.requires.get_rule(model_id, guild_id=guild_id)
        return cur_rule, cur_rule

    def set_default_rule(self, rule: Optional[bool], guild_id: int) -> None:
        """This will do nothing."""


class _AlwaysAvailableCommand(_AlwaysAvailableMixin, _RuleDropper, Command):
    pass


class _AlwaysAvailableGroup(_AlwaysAvailableMixin, _RuleDropper, Group):
    pass


class _ForgetMeSpecialCommand(_RuleDropper, Command):
    """
    We need special can_run behavior here
    """

    async def can_run(self, ctx, /, *args, **kwargs) -> bool:
        return await ctx.bot._config.datarequests.allow_user_requests()

    can_see = can_run
