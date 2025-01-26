from __future__ import annotations

import asyncio
import contextlib
import os
import re
from typing import Iterable, List, Union, Optional, TYPE_CHECKING
import discord
from discord.ext.commands import Context as DPYContext

from .requires import PermState
from ..utils import can_user_react_in

if TYPE_CHECKING:
    from .commands import Command
    from ..bot import Red

TICK = "\N{WHITE HEAVY CHECK MARK}"

__all__ = ["Context", "GuildContext", "DMContext"]


class Context(DPYContext):
    """Command invocation context for Red.

    All context passed into commands will be of this type.

    This class inherits from `discord.ext.commands.Context`.

    Attributes
    ----------
    assume_yes: bool
        Whether or not interactive checks should
        be skipped and assumed to be confirmed.

        This is intended for allowing automation of tasks.

        An example of this would be scheduled commands
        not requiring interaction if the cog developer
        checks this value prior to confirming something interactively.

        Depending on the potential impact of a command,
        it may still be appropriate not to use this setting.
    permission_state: PermState
        The permission state the current context is in.
    """

    command: "Command"
    invoked_subcommand: "Optional[Command]"
    bot: "Red"

    def __init__(self, **attrs):
        self.assume_yes = attrs.pop("assume_yes", False)
        super().__init__(**attrs)
        self.permission_state: PermState = PermState.NORMAL

    async def send(self, content=None, **kwargs):
        """Sends a message to the destination with the content given.

        This acts the same as `discord.ext.commands.Context.send`, with
        one added keyword argument as detailed below in *Other Parameters*.

        Parameters
        ----------
        content : str
            The content of the message to send.

        Other Parameters
        ----------------
        filter : callable (`str`) -> `str`, optional
            A function which is used to filter the ``content`` before
            it is sent.
            This must take a single `str` as an argument, and return
            the processed `str`. When `None` is passed, ``content`` won't be touched.
            Defaults to `None`.
        **kwargs
            See `discord.ext.commands.Context.send`.

        Returns
        -------
        discord.Message
            The message that was sent.

        """

        _filter = kwargs.pop("filter", None)

        if _filter and content:
            content = _filter(str(content))

        return await super().send(content=content, **kwargs)

    async def send_help(self, command=None):
        """Send the command help message."""
        # This allows people to manually use this similarly
        # to the upstream d.py version, while retaining our use.
        command = command or self.command
        await self.bot.send_help_for(self, command)

    async def tick(self, *, message: Optional[str] = None) -> bool:
        """Add a tick reaction to the command message.

        Keyword Arguments
        -----------------
        message : str, optional
            The message to send if adding the reaction doesn't succeed.

        Returns
        -------
        bool
            :code:`True` if adding the reaction succeeded.

        """
        return await self.react_quietly(TICK, message=message)

    async def react_quietly(
        self,
        reaction: Union[discord.Emoji, discord.Reaction, discord.PartialEmoji, str],
        *,
        message: Optional[str] = None,
    ) -> bool:
        """Adds a reaction to the command message.

        Parameters
        ----------
        reaction : Union[discord.Emoji, discord.Reaction, discord.PartialEmoji, str]
            The emoji to react with.

        Keyword Arguments
        -----------------
        message : str, optional
            The message to send if adding the reaction doesn't succeed.

        Returns
        -------
        bool
            :code:`True` if adding the reaction succeeded.
        """
        try:
            if not can_user_react_in(self.me, self.channel):
                raise RuntimeError
            await self.message.add_reaction(reaction)
        except (RuntimeError, discord.HTTPException):
            if message is not None:
                await self.send(message)
            return False
        else:
            return True

    async def send_interactive(
        self,
        messages: Iterable[str],
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
        messages : `iterable` of `str`
            The messages to send.
        box_lang : str
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
        return await self.bot.send_interactive(
            channel=self.channel,
            messages=messages,
            user=self.author,
            box_lang=box_lang,
            timeout=timeout,
            join_character=join_character,
        )

    async def embed_colour(self):
        """
        Helper function to get the colour for an embed.

        Returns
        -------
        discord.Colour:
            The colour to be used
        """
        return await self.bot.get_embed_color(self)

    @property
    def embed_color(self):
        # Rather than double awaiting.
        return self.embed_colour

    async def embed_requested(self):
        """
        Short-hand for calling bot.embed_requested with permission checks.

        Equivalent to:

        .. code:: python

            await ctx.bot.embed_requested(ctx)

        Returns
        -------
        bool:
            :code:`True` if an embed is requested
        """
        return await self.bot.embed_requested(self)

    async def maybe_send_embed(self, message: str) -> discord.Message:
        """
        Simple helper to send a simple message to context
        without manually checking ctx.embed_requested
        This should only be used for simple messages.

        Parameters
        ----------
        message: `str`
            The string to send

        Returns
        -------
        discord.Message:
            the message which was sent

        Raises
        ------
        discord.Forbidden
            see `discord.abc.Messageable.send`
        discord.HTTPException
            see `discord.abc.Messageable.send`
        ValueError
            when the message's length is not between 1 and 2000 characters.
        """
        if not message or len(message) > 2000:
            raise ValueError("Message length must be between 1 and 2000")
        if await self.embed_requested():
            return await self.send(
                embed=discord.Embed(description=message, color=(await self.embed_colour()))
            )
        else:
            return await self.send(
                message,
                allowed_mentions=discord.AllowedMentions(everyone=False, roles=False, users=False),
            )

    @property
    def me(self) -> Union[discord.ClientUser, discord.Member]:
        """
        discord.abc.User: The bot member or user object.

        If the context is DM, this will be a `discord.User` object.
        """
        if self.guild is not None:
            return self.guild.me
        else:
            return self.bot.user


if TYPE_CHECKING or os.getenv("BUILDING_DOCS", False):

    class DMContext(Context):
        """
        At runtime, this will still be a normal context object.

        This lies about some type narrowing for type analysis in commands
        using a dm_only decorator.

        It is only correct to use when those types are already narrowed
        """

        @property
        def author(self) -> discord.User:
            ...

        @property
        def channel(self) -> discord.DMChannel:
            ...

        @property
        def guild(self) -> None:
            ...

        @property
        def me(self) -> discord.ClientUser:
            ...

    class GuildContext(Context):
        """
        At runtime, this will still be a normal context object.

        This lies about some type narrowing for type analysis in commands
        using a guild_only decorator.

        It is only correct to use when those types are already narrowed
        """

        @property
        def author(self) -> discord.Member:
            ...

        @property
        def channel(
            self,
        ) -> Union[
            discord.TextChannel, discord.VoiceChannel, discord.StageChannel, discord.Thread
        ]:
            ...

        @property
        def guild(self) -> discord.Guild:
            ...

        @property
        def me(self) -> discord.Member:
            ...

else:
    GuildContext = Context
    DMContext = Context
