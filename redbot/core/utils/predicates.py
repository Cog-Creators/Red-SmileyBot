from __future__ import annotations

import re
from typing import Callable, ClassVar, List, Optional, Pattern, Sequence, Tuple, Union, cast

import discord
from discord.ext import commands as dpy_commands

from redbot.core import commands

__all__ = ("MessagePredicate", "ReactionPredicate")

_ID_RE = re.compile(r"([0-9]{15,20})$")
_USER_MENTION_RE = re.compile(r"<@!?([0-9]{15,20})>$")
_CHAN_MENTION_RE = re.compile(r"<#([0-9]{15,20})>$")
_ROLE_MENTION_RE = re.compile(r"<@&([0-9]{15,20})>$")


class MessagePredicate(Callable[[discord.Message], bool]):
    """A simple collection of predicates for message events.

    These predicates intend to help simplify checks in message events
    and reduce boilerplate code.

    This class should be created through the provided classmethods.
    Instances of this class are callable message predicates, i.e. they
    return ``True`` if a message matches the criteria.

    All predicates are combined with :meth:`MessagePredicate.same_context`.

    Examples
    --------
    Waiting for a response in the same channel and from the same
    author::

        await bot.wait_for("message", check=MessagePredicate.same_context(ctx))

    Waiting for a response to a yes or no question::

        pred = MessagePredicate.yes_or_no(ctx)
        await bot.wait_for("message", check=pred)
        if pred.result is True:
            # User responded "yes"
            ...

    Getting a member object from a user's response::

        pred = MessagePredicate.valid_member(ctx)
        await bot.wait_for("message", check=pred)
        member = pred.result

    Attributes
    ----------
    result : Any
        The object which the message content matched with. This is
        dependent on the predicate used - see each predicate's
        documentation for details, not every method will assign this
        attribute. Defaults to ``None``.

    """

    def __init__(self, predicate: Callable[["MessagePredicate", discord.Message], bool]) -> None:
        self._pred: Callable[["MessagePredicate", discord.Message], bool] = predicate
        self.result = None

    def __call__(self, message: discord.Message) -> bool:
        return self._pred(self, message)

    @classmethod
    def same_context(
        cls,
        ctx: Optional[commands.Context] = None,
        channel: Optional[discord.abc.Messageable] = None,
        user: Optional[discord.abc.User] = None,
    ) -> "MessagePredicate":
        """Match if the message fits the described context.

        Parameters
        ----------
        ctx : Optional[Context]
            The current invocation context.
        channel : Optional[discord.abc.Messageable]
            The messageable object we expect a message in. If unspecified,
            defaults to ``ctx.channel``. If ``ctx`` is unspecified
            too, the message's channel will be ignored.
        user : Optional[discord.abc.User]
            The user we expect a message from. If unspecified,
            defaults to ``ctx.author``. If ``ctx`` is unspecified
            too, the message's author will be ignored.

        Returns
        -------
        MessagePredicate
            The event predicate.

        """
        check_dm_channel = False
        # using dpy_commands.Context to keep the Messageable contract in full
        if isinstance(channel, dpy_commands.Context):
            channel = channel.channel
        elif isinstance(channel, (discord.User, discord.Member)):
            check_dm_channel = True

        if ctx is not None:
            channel = channel or ctx.channel
            user = user or ctx.author

        return cls(
            lambda self, m: (user is None or user.id == m.author.id)
            and (
                channel is None
                or (
                    channel.id == m.author.id and isinstance(m.channel, discord.DMChannel)
                    if check_dm_channel
                    else channel.id == m.channel.id
                )
            )
        )

    @classmethod
    def cancelled(
        cls,
        ctx: Optional[commands.Context] = None,
        channel: Optional[discord.abc.Messageable] = None,
        user: Optional[discord.abc.User] = None,
    ) -> "MessagePredicate":
        """Match if the message is ``[p]cancel``.

        Parameters
        ----------
        ctx : Optional[Context]
            Same as ``ctx`` in :meth:`same_context`.
        channel : Optional[discord.abc.Messageable]
            Same as ``channel`` in :meth:`same_context`.
        user : Optional[discord.abc.User]
            Same as ``user`` in :meth:`same_context`.

        Returns
        -------
        MessagePredicate
            The event predicate.

        """
        same_context = cls.same_context(ctx, channel, user)
        return cls(
            lambda self, m: (same_context(m) and m.content.lower() == f"{ctx.prefix}cancel")
        )

    @classmethod
    def yes_or_no(
        cls,
        ctx: Optional[commands.Context] = None,
        channel: Optional[discord.abc.Messageable] = None,
        user: Optional[discord.abc.User] = None,
    ) -> "MessagePredicate":
        """Match if the message is "yes"/"y" or "no"/"n".

        This will assign ``True`` for *yes*, or ``False`` for *no* to
        the `result` attribute.

        Parameters
        ----------
        ctx : Optional[Context]
            Same as ``ctx`` in :meth:`same_context`.
        channel : Optional[discord.abc.Messageable]
            Same as ``channel`` in :meth:`same_context`.
        user : Optional[discord.abc.User]
            Same as ``user`` in :meth:`same_context`.

        Returns
        -------
        MessagePredicate
            The event predicate.

        """
        same_context = cls.same_context(ctx, channel, user)

        def predicate(self: MessagePredicate, m: discord.Message) -> bool:
            if not same_context(m):
                return False
            content = m.content.lower()
            if content in ("yes", "y"):
                self.result = True
            elif content in ("no", "n"):
                self.result = False
            else:
                return False
            return True

        return cls(predicate)

    @classmethod
    def valid_int(
        cls,
        ctx: Optional[commands.Context] = None,
        channel: Optional[discord.abc.Messageable] = None,
        user: Optional[discord.abc.User] = None,
    ) -> "MessagePredicate":
        """Match if the response is an integer.

        Assigns the response to `result` as an `int`.

        Parameters
        ----------
        ctx : Optional[Context]
            Same as ``ctx`` in :meth:`same_context`.
        channel : Optional[discord.abc.Messageable]
            Same as ``channel`` in :meth:`same_context`.
        user : Optional[discord.abc.User]
            Same as ``user`` in :meth:`same_context`.

        Returns
        -------
        MessagePredicate
            The event predicate.

        """
        same_context = cls.same_context(ctx, channel, user)

        def predicate(self: MessagePredicate, m: discord.Message) -> bool:
            if not same_context(m):
                return False
            try:
                self.result = int(m.content)
            except ValueError:
                return False
            else:
                return True

        return cls(predicate)

    @classmethod
    def valid_float(
        cls,
        ctx: Optional[commands.Context] = None,
        channel: Optional[discord.abc.Messageable] = None,
        user: Optional[discord.abc.User] = None,
    ) -> "MessagePredicate":
        """Match if the response is a float.

        Assigns the response to `result` as a `float`.

        Parameters
        ----------
        ctx : Optional[Context]
            Same as ``ctx`` in :meth:`same_context`.
        channel : Optional[discord.abc.Messageable]
            Same as ``channel`` in :meth:`same_context`.
        user : Optional[discord.abc.User]
            Same as ``user`` in :meth:`same_context`.

        Returns
        -------
        MessagePredicate
            The event predicate.

        """
        same_context = cls.same_context(ctx, channel, user)

        def predicate(self: MessagePredicate, m: discord.Message) -> bool:
            if not same_context(m):
                return False
            try:
                self.result = float(m.content)
            except ValueError:
                return False
            else:
                return True

        return cls(predicate)

    @classmethod
    def positive(
        cls,
        ctx: Optional[commands.Context] = None,
        channel: Optional[discord.abc.Messageable] = None,
        user: Optional[discord.abc.User] = None,
    ) -> "MessagePredicate":
        """Match if the response is a positive number.

        Assigns the response to `result` as a `float`.

        Parameters
        ----------
        ctx : Optional[Context]
            Same as ``ctx`` in :meth:`same_context`.
        channel : Optional[discord.abc.Messageable]
            Same as ``channel`` in :meth:`same_context`.
        user : Optional[discord.abc.User]
            Same as ``user`` in :meth:`same_context`.

        Returns
        -------
        MessagePredicate
            The event predicate.

        """
        same_context = cls.same_context(ctx, channel, user)

        def predicate(self: MessagePredicate, m: discord.Message) -> bool:
            if not same_context(m):
                return False
            try:
                number = float(m.content)
            except ValueError:
                return False
            else:
                if number > 0:
                    self.result = number
                    return True
                else:
                    return False

        return cls(predicate)

    @classmethod
    def valid_role(
        cls,
        ctx: Optional[commands.Context] = None,
        channel: Optional[
            Union[discord.TextChannel, discord.VoiceChannel, discord.StageChannel, discord.Thread]
        ] = None,
        user: Optional[discord.abc.User] = None,
    ) -> "MessagePredicate":
        """Match if the response refers to a role in the current guild.

        Assigns the matching `discord.Role` object to `result`.

        This predicate cannot be used in DM.

        Parameters
        ----------
        ctx : Optional[Context]
            Same as ``ctx`` in :meth:`same_context`.
        channel : Optional[Union[`discord.TextChannel`, `discord.VoiceChannel`, `discord.StageChannel`, `discord.Thread`]]
            Same as ``channel`` in :meth:`same_context`.
        user : Optional[discord.abc.User]
            Same as ``user`` in :meth:`same_context`.

        Returns
        -------
        MessagePredicate
            The event predicate.

        """
        same_context = cls.same_context(ctx, channel, user)
        guild = cls._get_guild(ctx, channel, cast(discord.Member, user))

        def predicate(self: MessagePredicate, m: discord.Message) -> bool:
            if not same_context(m):
                return False

            role = self._find_role(guild, m.content)
            if role is None:
                return False

            self.result = role
            return True

        return cls(predicate)

    @classmethod
    def valid_member(
        cls,
        ctx: Optional[commands.Context] = None,
        channel: Optional[
            Union[discord.TextChannel, discord.VoiceChannel, discord.StageChannel, discord.Thread]
        ] = None,
        user: Optional[discord.abc.User] = None,
    ) -> "MessagePredicate":
        """Match if the response refers to a member in the current guild.

        Assigns the matching `discord.Member` object to `result`.

        This predicate cannot be used in DM.

        Parameters
        ----------
        ctx : Optional[Context]
            Same as ``ctx`` in :meth:`same_context`.
        channel : Optional[Union[`discord.TextChannel`, `discord.VoiceChannel`, `discord.StageChannel`, `discord.Thread`]]
            Same as ``channel`` in :meth:`same_context`.
        user : Optional[discord.abc.User]
            Same as ``user`` in :meth:`same_context`.

        Returns
        -------
        MessagePredicate
            The event predicate.

        """
        same_context = cls.same_context(ctx, channel, user)
        guild = cls._get_guild(ctx, channel, cast(discord.Member, user))

        def predicate(self: MessagePredicate, m: discord.Message) -> bool:
            if not same_context(m):
                return False

            match = _ID_RE.match(m.content) or _USER_MENTION_RE.match(m.content)
            if match:
                result = guild.get_member(int(match.group(1)))
            else:
                result = guild.get_member_named(m.content)

            if result is None:
                return False
            self.result = result
            return True

        return cls(predicate)

    @classmethod
    def valid_text_channel(
        cls,
        ctx: Optional[commands.Context] = None,
        channel: Optional[
            Union[discord.TextChannel, discord.VoiceChannel, discord.StageChannel, discord.Thread]
        ] = None,
        user: Optional[discord.abc.User] = None,
    ) -> "MessagePredicate":
        """Match if the response refers to a text channel in the current guild.

        Assigns the matching `discord.TextChannel` object to `result`.

        This predicate cannot be used in DM.

        Parameters
        ----------
        ctx : Optional[Context]
            Same as ``ctx`` in :meth:`same_context`.
        channel : Optional[Union[`discord.TextChannel`, `discord.VoiceChannel`, `discord.StageChannel`, `discord.Thread`]]
            Same as ``channel`` in :meth:`same_context`.
        user : Optional[discord.abc.User]
            Same as ``user`` in :meth:`same_context`.

        Returns
        -------
        MessagePredicate
            The event predicate.

        """
        same_context = cls.same_context(ctx, channel, user)
        guild = cls._get_guild(ctx, channel, cast(discord.Member, user))

        def predicate(self: MessagePredicate, m: discord.Message) -> bool:
            if not same_context(m):
                return False

            match = _ID_RE.match(m.content) or _CHAN_MENTION_RE.match(m.content)
            if match:
                result = guild.get_channel(int(match.group(1)))
            else:
                result = discord.utils.get(guild.text_channels, name=m.content)

            if not isinstance(result, discord.TextChannel):
                return False
            self.result = result
            return True

        return cls(predicate)

    @classmethod
    def has_role(
        cls,
        ctx: Optional[commands.Context] = None,
        channel: Optional[
            Union[discord.TextChannel, discord.VoiceChannel, discord.StageChannel, discord.Thread]
        ] = None,
        user: Optional[discord.abc.User] = None,
    ) -> "MessagePredicate":
        """Match if the response refers to a role which the author has.

        Assigns the matching `discord.Role` object to `result`.

        One of ``user`` or ``ctx`` must be supplied. This predicate
        cannot be used in DM.

        Parameters
        ----------
        ctx : Optional[Context]
            Same as ``ctx`` in :meth:`same_context`.
        channel : Optional[Union[`discord.TextChannel`, `discord.VoiceChannel`, `discord.StageChannel`, `discord.Thread`]]
            Same as ``channel`` in :meth:`same_context`.
        user : Optional[discord.abc.User]
            Same as ``user`` in :meth:`same_context`.

        Returns
        -------
        MessagePredicate
            The event predicate.

        """
        same_context = cls.same_context(ctx, channel, user)
        guild = cls._get_guild(ctx, channel, cast(discord.Member, user))
        if user is None:
            if ctx is None:
                raise TypeError(
                    "One of `user` or `ctx` must be supplied to `MessagePredicate.has_role`."
                )
            user = ctx.author

        def predicate(self: MessagePredicate, m: discord.Message) -> bool:
            if not same_context(m):
                return False

            role = self._find_role(guild, m.content)
            if role is None or user.get_role(role.id) is None:
                return False

            self.result = role
            return True

        return cls(predicate)

    @classmethod
    def equal_to(
        cls,
        value: str,
        ctx: Optional[commands.Context] = None,
        channel: Optional[discord.abc.Messageable] = None,
        user: Optional[discord.abc.User] = None,
    ) -> "MessagePredicate":
        """Match if the response is equal to the specified value.

        Parameters
        ----------
        value : str
            The value to compare the response with.
        ctx : Optional[Context]
            Same as ``ctx`` in :meth:`same_context`.
        channel : Optional[discord.abc.Messageable]
            Same as ``channel`` in :meth:`same_context`.
        user : Optional[discord.abc.User]
            Same as ``user`` in :meth:`same_context`.

        Returns
        -------
        MessagePredicate
            The event predicate.

        """
        same_context = cls.same_context(ctx, channel, user)
        return cls(lambda self, m: same_context(m) and m.content == value)

    @classmethod
    def lower_equal_to(
        cls,
        value: str,
        ctx: Optional[commands.Context] = None,
        channel: Optional[discord.abc.Messageable] = None,
        user: Optional[discord.abc.User] = None,
    ) -> "MessagePredicate":
        """Match if the response *as lowercase* is equal to the specified value.

        Parameters
        ----------
        value : str
            The value to compare the response with.
        ctx : Optional[Context]
            Same as ``ctx`` in :meth:`same_context`.
        channel : Optional[discord.abc.Messageable]
            Same as ``channel`` in :meth:`same_context`.
        user : Optional[discord.abc.User]
            Same as ``user`` in :meth:`same_context`.

        Returns
        -------
        MessagePredicate
            The event predicate.

        """
        same_context = cls.same_context(ctx, channel, user)
        return cls(lambda self, m: same_context(m) and m.content.lower() == value)

    @classmethod
    def less(
        cls,
        value: Union[int, float],
        ctx: Optional[commands.Context] = None,
        channel: Optional[discord.abc.Messageable] = None,
        user: Optional[discord.abc.User] = None,
    ) -> "MessagePredicate":
        """Match if the response is less than the specified value.

        Parameters
        ----------
        value : Union[int, float]
            The value to compare the response with.
        ctx : Optional[Context]
            Same as ``ctx`` in :meth:`same_context`.
        channel : Optional[discord.abc.Messageable]
            Same as ``channel`` in :meth:`same_context`.
        user : Optional[discord.abc.User]
            Same as ``user`` in :meth:`same_context`.

        Returns
        -------
        MessagePredicate
            The event predicate.

        """
        valid_int = cls.valid_int(ctx, channel, user)
        valid_float = cls.valid_float(ctx, channel, user)
        return cls(lambda self, m: (valid_int(m) or valid_float(m)) and float(m.content) < value)

    @classmethod
    def greater(
        cls,
        value: Union[int, float],
        ctx: Optional[commands.Context] = None,
        channel: Optional[discord.abc.Messageable] = None,
        user: Optional[discord.abc.User] = None,
    ) -> "MessagePredicate":
        """Match if the response is greater than the specified value.

        Parameters
        ----------
        value : Union[int, float]
            The value to compare the response with.
        ctx : Optional[Context]
            Same as ``ctx`` in :meth:`same_context`.
        channel : Optional[discord.abc.Messageable]
            Same as ``channel`` in :meth:`same_context`.
        user : Optional[discord.abc.User]
            Same as ``user`` in :meth:`same_context`.

        Returns
        -------
        MessagePredicate
            The event predicate.

        """
        valid_int = cls.valid_int(ctx, channel, user)
        valid_float = cls.valid_float(ctx, channel, user)
        return cls(lambda self, m: (valid_int(m) or valid_float(m)) and float(m.content) > value)

    @classmethod
    def length_less(
        cls,
        length: int,
        ctx: Optional[commands.Context] = None,
        channel: Optional[discord.abc.Messageable] = None,
        user: Optional[discord.abc.User] = None,
    ) -> "MessagePredicate":
        """Match if the response's length is less than the specified length.

        Parameters
        ----------
        length : int
            The value to compare the response's length with.
        ctx : Optional[Context]
            Same as ``ctx`` in :meth:`same_context`.
        channel : Optional[discord.abc.Messageable]
            Same as ``channel`` in :meth:`same_context`.
        user : Optional[discord.abc.User]
            Same as ``user`` in :meth:`same_context`.

        Returns
        -------
        MessagePredicate
            The event predicate.

        """
        same_context = cls.same_context(ctx, channel, user)
        return cls(lambda self, m: same_context(m) and len(m.content) <= length)

    @classmethod
    def length_greater(
        cls,
        length: int,
        ctx: Optional[commands.Context] = None,
        channel: Optional[discord.abc.Messageable] = None,
        user: Optional[discord.abc.User] = None,
    ) -> "MessagePredicate":
        """Match if the response's length is greater than the specified length.

        Parameters
        ----------
        length : int
            The value to compare the response's length with.
        ctx : Optional[Context]
            Same as ``ctx`` in :meth:`same_context`.
        channel : Optional[discord.abc.Messageable]
            Same as ``channel`` in :meth:`same_context`.
        user : Optional[discord.abc.User]
            Same as ``user`` in :meth:`same_context`.

        Returns
        -------
        MessagePredicate
            The event predicate.

        """
        same_context = cls.same_context(ctx, channel, user)
        return cls(lambda self, m: same_context(m) and len(m.content) >= length)

    @classmethod
    def contained_in(
        cls,
        collection: Sequence[str],
        ctx: Optional[commands.Context] = None,
        channel: Optional[discord.abc.Messageable] = None,
        user: Optional[discord.abc.User] = None,
    ) -> "MessagePredicate":
        """Match if the response is contained in the specified collection.

        The index of the response in the ``collection`` sequence is
        assigned to the `result` attribute.

        Parameters
        ----------
        collection : Sequence[str]
            The collection containing valid responses.
        ctx : Optional[Context]
            Same as ``ctx`` in :meth:`same_context`.
        channel : Optional[discord.abc.Messageable]
            Same as ``channel`` in :meth:`same_context`.
        user : Optional[discord.abc.User]
            Same as ``user`` in :meth:`same_context`.

        Returns
        -------
        MessagePredicate
            The event predicate.

        """
        same_context = cls.same_context(ctx, channel, user)

        def predicate(self: MessagePredicate, m: discord.Message) -> bool:
            if not same_context(m):
                return False
            try:
                self.result = collection.index(m.content)
            except ValueError:
                return False
            else:
                return True

        return cls(predicate)

    @classmethod
    def lower_contained_in(
        cls,
        collection: Sequence[str],
        ctx: Optional[commands.Context] = None,
        channel: Optional[discord.abc.Messageable] = None,
        user: Optional[discord.abc.User] = None,
    ) -> "MessagePredicate":
        """Same as :meth:`contained_in`, but the response is set to lowercase before matching.

        Parameters
        ----------
        collection : Sequence[str]
            The collection containing valid lowercase responses.
        ctx : Optional[Context]
            Same as ``ctx`` in :meth:`same_context`.
        channel : Optional[discord.abc.Messageable]
            Same as ``channel`` in :meth:`same_context`.
        user : Optional[discord.abc.User]
            Same as ``user`` in :meth:`same_context`.

        Returns
        -------
        MessagePredicate
            The event predicate.

        """
        same_context = cls.same_context(ctx, channel, user)

        def predicate(self: MessagePredicate, m: discord.Message) -> bool:
            if not same_context(m):
                return False
            try:
                self.result = collection.index(m.content.lower())
            except ValueError:
                return False
            else:
                return True

        return cls(predicate)

    @classmethod
    def regex(
        cls,
        pattern: Union[Pattern[str], str],
        ctx: Optional[commands.Context] = None,
        channel: Optional[discord.abc.Messageable] = None,
        user: Optional[discord.abc.User] = None,
    ) -> "MessagePredicate":
        """Match if the response matches the specified regex pattern.

        This predicate will use `re.search` to find a match. The
        resulting `match object <match-objects>` will be assigned
        to `result`.

        Parameters
        ----------
        pattern : Union[`pattern object <re-objects>`, str]
            The pattern to search for in the response.
        ctx : Optional[Context]
            Same as ``ctx`` in :meth:`same_context`.
        channel : Optional[discord.abc.Messageable]
            Same as ``channel`` in :meth:`same_context`.
        user : Optional[discord.abc.User]
            Same as ``user`` in :meth:`same_context`.

        Returns
        -------
        MessagePredicate
            The event predicate.

        """
        same_context = cls.same_context(ctx, channel, user)

        def predicate(self: MessagePredicate, m: discord.Message) -> bool:
            if not same_context(m):
                return False

            if isinstance(pattern, str):
                pattern_obj = re.compile(pattern)
            else:
                pattern_obj = pattern

            match = pattern_obj.search(m.content)
            if match:
                self.result = match
                return True
            return False

        return cls(predicate)

    @staticmethod
    def _find_role(guild: discord.Guild, argument: str) -> Optional[discord.Role]:
        match = _ID_RE.match(argument) or _ROLE_MENTION_RE.match(argument)
        if match:
            result = guild.get_role(int(match.group(1)))
        else:
            result = discord.utils.get(guild.roles, name=argument)
        return result

    @staticmethod
    def _get_guild(
        ctx: Optional[commands.Context],
        channel: Optional[
            Union[discord.TextChannel, discord.VoiceChannel, discord.StageChannel, discord.Thread]
        ],
        user: Optional[discord.Member],
    ) -> discord.Guild:
        if ctx is not None:
            return ctx.guild
        elif channel is not None:
            return channel.guild
        elif user is not None:
            return user.guild


class ReactionPredicate(Callable[[discord.Reaction, discord.abc.User], bool]):
    """A collection of predicates for reaction events.

    All checks are combined with :meth:`ReactionPredicate.same_context`.

    Examples
    --------
    Confirming a yes/no question with a tick/cross reaction::

        from redbot.core.utils.predicates import ReactionPredicate
        from redbot.core.utils.menus import start_adding_reactions

        msg = await ctx.send("Yes or no?")
        start_adding_reactions(msg, ReactionPredicate.YES_OR_NO_EMOJIS)

        pred = ReactionPredicate.yes_or_no(msg, ctx.author)
        await ctx.bot.wait_for("reaction_add", check=pred)
        if pred.result is True:
            # User responded with tick
            ...
        else:
            # User responded with cross
            ...

    Waiting for the first reaction from any user with one of the first
    5 letters of the alphabet::

        from redbot.core.utils.predicates import ReactionPredicate
        from redbot.core.utils.menus import start_adding_reactions

        msg = await ctx.send("React to me!")
        emojis = ReactionPredicate.ALPHABET_EMOJIS[:5]
        start_adding_reactions(msg, emojis)

        pred = ReactionPredicate.with_emojis(emojis, msg)
        await ctx.bot.wait_for("reaction_add", check=pred)
        # pred.result is now the index of the letter in `emojis`

    Attributes
    ----------
    result : Any
        The object which the reaction matched with. This is
        dependent on the predicate used - see each predicate's
        documentation for details, not every method will assign this
        attribute. Defaults to ``None``.

    """

    YES_OR_NO_EMOJIS: ClassVar[Tuple[str, str]] = (
        "\N{WHITE HEAVY CHECK MARK}",
        "\N{NEGATIVE SQUARED CROSS MARK}",
    )
    """Tuple[str, str] : A tuple containing the tick emoji and cross emoji, in that order."""

    ALPHABET_EMOJIS: ClassVar[Tuple[str, ...]] = tuple(
        chr(code)
        for code in range(
            ord("\N{REGIONAL INDICATOR SYMBOL LETTER A}"),
            ord("\N{REGIONAL INDICATOR SYMBOL LETTER Z}") + 1,
        )
    )
    """Tuple[str, ...] : A tuple of all 26 alphabetical letter emojis."""

    NUMBER_EMOJIS: ClassVar[Tuple[str, ...]] = tuple(
        chr(code) + "\N{COMBINING ENCLOSING KEYCAP}" for code in range(ord("0"), ord("9") + 1)
    )
    """Tuple[str, ...] : A tuple of all single-digit number emojis, 0 through 9."""

    def __init__(
        self, predicate: Callable[["ReactionPredicate", discord.Reaction, discord.abc.User], bool]
    ) -> None:
        self._pred: Callable[
            ["ReactionPredicate", discord.Reaction, discord.abc.User], bool
        ] = predicate
        self.result = None

    def __call__(self, reaction: discord.Reaction, user: discord.abc.User) -> bool:
        return self._pred(self, reaction, user)

    # noinspection PyUnusedLocal
    @classmethod
    def same_context(
        cls, message: Optional[discord.Message] = None, user: Optional[discord.abc.User] = None
    ) -> "ReactionPredicate":
        """Match if a reaction fits the described context.

        This will ignore reactions added by the bot user, regardless
        of whether or not ``user`` is supplied.

        Parameters
        ----------
        message : Optional[discord.Message]
            The message which we expect a reaction to. If unspecified,
            the reaction's message will be ignored.
        user : Optional[discord.abc.User]
            The user we expect to react. If unspecified, the user who
            added the reaction will be ignored.

        Returns
        -------
        ReactionPredicate
            The event predicate.

        """
        # noinspection PyProtectedMember
        # DEP-WARN
        me_id = message._state.self_id
        return cls(
            lambda self, r, u: u.id != me_id
            and (message is None or r.message.id == message.id)
            and (user is None or u.id == user.id)
        )

    @classmethod
    def with_emojis(
        cls,
        emojis: Sequence[Union[str, discord.Emoji, discord.PartialEmoji]],
        message: Optional[discord.Message] = None,
        user: Optional[discord.abc.User] = None,
    ) -> "ReactionPredicate":
        """Match if the reaction is one of the specified emojis.

        Parameters
        ----------
        emojis : Sequence[Union[str, discord.Emoji, discord.PartialEmoji]]
            The emojis of which one we expect to be reacted.
        message : discord.Message
            Same as ``message`` in :meth:`same_context`.
        user : Optional[discord.abc.User]
            Same as ``user`` in :meth:`same_context`.

        Returns
        -------
        ReactionPredicate
            The event predicate.

        """
        same_context = cls.same_context(message, user)

        def predicate(self: ReactionPredicate, r: discord.Reaction, u: discord.abc.User):
            if not same_context(r, u):
                return False

            try:
                self.result = emojis.index(r.emoji)
            except ValueError:
                return False
            else:
                return True

        return cls(predicate)

    @classmethod
    def yes_or_no(
        cls, message: Optional[discord.Message] = None, user: Optional[discord.abc.User] = None
    ) -> "ReactionPredicate":
        """Match if the reaction is a tick or cross emoji.

        The emojis used are in
        `ReactionPredicate.YES_OR_NO_EMOJIS`.

        This will assign ``True`` for *yes*, or ``False`` for *no* to
        the `result` attribute.

        Parameters
        ----------
        message : discord.Message
            Same as ``message`` in :meth:`same_context`.
        user : Optional[discord.abc.User]
            Same as ``user`` in :meth:`same_context`.

        Returns
        -------
        ReactionPredicate
            The event predicate.

        """
        same_context = cls.same_context(message, user)

        def predicate(self: ReactionPredicate, r: discord.Reaction, u: discord.abc.User) -> bool:
            if not same_context(r, u):
                return False

            try:
                self.result = not bool(self.YES_OR_NO_EMOJIS.index(r.emoji))
            except ValueError:
                return False
            else:
                return True

        return cls(predicate)
