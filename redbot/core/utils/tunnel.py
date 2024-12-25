import asyncio
import discord
from datetime import datetime
from redbot.core.utils.chat_formatting import pagify
import io
import weakref
from typing import List, Optional, Union
from .common_filters import filter_mass_mentions

__all__ = ("Tunnel",)

_instances = weakref.WeakValueDictionary({})


class TunnelMeta(type):
    """
    lets prevent having multiple tunnels with the same
    places involved.
    """

    def __call__(cls, *args, **kwargs):
        lockout_tuple = ((kwargs.get("sender"), kwargs.get("origin")), kwargs.get("recipient"))

        if lockout_tuple in _instances:
            return _instances[lockout_tuple]

        # this is needed because weakvalue dicts can
        # change size without warning if an object is discarded
        # it can raise a runtime error, so ..
        while True:
            try:
                if not (
                    any(lockout_tuple[0] == x[0] for x in _instances.keys())
                    or any(lockout_tuple[1] == x[1] for x in _instances.keys())
                ):
                    # if this isn't temporarily stored, the weakref dict
                    # will discard this before the return statement,
                    # causing a key error
                    temp = super(TunnelMeta, cls).__call__(*args, **kwargs)
                    _instances[lockout_tuple] = temp
                    return temp
            except:  # NOQA: E722
                # Am I really supposed to except a runtime error flake >.>
                continue
            else:
                return None


class Tunnel(metaclass=TunnelMeta):
    """
    A tunnel interface for messages

    This will return None on init if the destination
    or source + origin pair is already in use, or the
    existing tunnel object if one exists for the designated
    parameters

    Attributes
    ----------
    sender: `discord.Member`
        The person who opened the tunnel
    origin: `discord.TextChannel`, `discord.VoiceChannel`, `discord.StageChannel`, or `discord.Thread`
        The channel in which it was opened
    recipient: `discord.User`
        The user on the other end of the tunnel
    """

    def __init__(
        self,
        *,
        sender: discord.Member,
        origin: Union[
            discord.TextChannel, discord.VoiceChannel, discord.StageChannel, discord.Thread
        ],
        recipient: discord.User,
    ):
        self.sender = sender
        self.origin = origin
        self.recipient = recipient
        self.last_interaction = datetime.utcnow()

    async def react_close(self, *, uid: int, message: str = ""):
        send_to = self.recipient if uid == self.sender.id else self.origin
        closer = next(filter(lambda x: x.id == uid, (self.sender, self.recipient)), None)
        await send_to.send(filter_mass_mentions(message.format(closer=closer)))

    @property
    def members(self):
        return self.sender, self.recipient

    @property
    def minutes_since(self):
        return int((self.last_interaction - datetime.utcnow()).seconds / 60)

    @staticmethod
    async def message_forwarder(
        *,
        destination: discord.abc.Messageable,
        content: str = None,
        embed=None,
        files: Optional[List[discord.File]] = None,
    ) -> List[discord.Message]:
        """
        This does the actual sending, use this instead of a full tunnel
        if you are using command initiated reactions instead of persistent
        event based ones

        Parameters
        ----------
        destination: discord.abc.Messageable
            Where to send
        content: str
            The message content
        embed: discord.Embed
            The embed to send
        files: Optional[List[discord.File]]
            A list of files to send.

        Returns
        -------
        List[discord.Message]
            The messages sent as a result.

        Raises
        ------
        discord.Forbidden
            see `discord.abc.Messageable.send`
        discord.HTTPException
            see `discord.abc.Messageable.send`
        """
        rets = []
        if content:
            for page in pagify(content):
                rets.append(await destination.send(page, files=files, embed=embed))
                files = embed = None
        elif embed or files:
            rets.append(await destination.send(files=files, embed=embed))
        return rets

    @staticmethod
    async def files_from_attach(
        m: discord.Message, *, use_cached: bool = False, images_only: bool = False
    ) -> List[discord.File]:
        """
        makes a list of file objects from a message
        returns an empty list if none, or if the sum of file sizes
        is too large for the bot to send

        Parameters
        ---------
        m: `discord.Message`
            A message to get attachments from
        use_cached: `bool`
            Whether to use ``proxy_url`` rather than ``url`` when downloading the attachment
        images_only: `bool`
            Whether only image attachments should be added to returned list

        Returns
        -------
        list of `discord.File`
            A list of `discord.File` objects

        """
        files = []
        max_size = 26214400
        if m.attachments and sum(a.size for a in m.attachments) <= max_size:
            for a in m.attachments:
                if images_only and a.height is None:
                    # if this is None, it's not an image
                    continue
                try:
                    file = await a.to_file()
                except discord.HTTPException as e:
                    # this is required, because animated webp files aren't cached
                    if not (e.status == 415 and images_only and use_cached):
                        raise
                else:
                    files.append(file)
        return files

    # Backwards-compatible typo fix (GH-2496)
    files_from_attatch = files_from_attach

    async def close_because_disabled(self, close_message: str):
        """
        Sends a message to both ends of the tunnel that the tunnel is now closed.

        Parameters
        ----------
        close_message: str
            The message to send to both ends of the tunnel.
        """

        tasks = [destination.send(close_message) for destination in (self.recipient, self.origin)]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def communicate(
        self, *, message: discord.Message, topic: str = None, skip_message_content: bool = False
    ):
        """
        Forwards a message.

        Parameters
        ----------
        message : `discord.Message`
            The message to forward
        topic : `str`
            A string to prepend
        skip_message_content : `bool`
            If this flag is set, only the topic will be sent

        Returns
        -------
        `int`, `int`
            a pair of ints matching the ids of the
            message which was forwarded
            and the last message the bot sent to do that.
            useful if waiting for reactions.

        Raises
        ------
        discord.Forbidden
            This should only happen if the user's DMs are disabled
            the bot can't upload at the origin channel
            or can't add reactions there.
        """
        if message.channel.id == self.origin.id and message.author == self.sender:
            send_to = self.recipient
        elif message.author == self.recipient and message.guild is None:
            send_to = self.origin
        else:
            return None

        if not skip_message_content:
            content = "\n".join((topic, message.content)) if topic else message.content
        else:
            content = topic

        if message.attachments:
            attach = await self.files_from_attach(message)
            if not attach:
                await message.channel.send(
                    "Could not forward attachments. "
                    "Total size of attachments in a single "
                    "message must be less than 8MB."
                )
        else:
            attach = []

        rets = await self.message_forwarder(destination=send_to, content=content, files=attach)

        await message.add_reaction("\N{WHITE HEAVY CHECK MARK}")
        await message.add_reaction("\N{NEGATIVE SQUARED CROSS MARK}")
        self.last_interaction = datetime.utcnow()
        await rets[-1].add_reaction("\N{NEGATIVE SQUARED CROSS MARK}")
        return [rets[-1].id, message.id]
