from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Literal, Union, Optional, cast, TYPE_CHECKING

import discord

from redbot.core import Config
from .utils import AsyncIter
from .utils.common_filters import (
    filter_invites,
    filter_mass_mentions,
    filter_urls,
    escape_spoilers,
)
from .utils.chat_formatting import bold, pagify
from .i18n import Translator, set_contextual_locales_from_guild

from .generic_casetypes import all_generics

if TYPE_CHECKING:
    from redbot.core.bot import Red

log = logging.getLogger("red.core.modlog")

__all__ = (
    "Case",
    "CaseType",
    "get_case",
    "get_latest_case",
    "get_all_cases",
    "get_cases_for_member",
    "create_case",
    "get_casetype",
    "get_all_casetypes",
    "register_casetype",
    "register_casetypes",
    "get_modlog_channel",
    "set_modlog_channel",
    "reset_cases",
)

_config: Optional[Config] = None
_bot_ref: Optional[Red] = None

_CASETYPES = "CASETYPES"
_CASES = "CASES"
_SCHEMA_VERSION = 4

_data_deletion_lock = asyncio.Lock()

_ = Translator("ModLog", __file__)


async def _process_data_deletion(
    *, requester: Literal["discord_deleted_user", "owner", "user", "user_strict"], user_id: int
):
    if requester != "discord_deleted_user":
        return

    # Oh, how I wish it was as simple as I wanted...

    key_paths = []

    async with _data_deletion_lock:
        all_cases = await _config.custom(_CASES).all()
        async for guild_id_str, guild_cases in AsyncIter(all_cases.items(), steps=100):
            async for case_num_str, case in AsyncIter(guild_cases.items(), steps=100):
                for keyname in ("user", "moderator", "amended_by"):
                    if (case.get(keyname, 0) or 0) == user_id:  # this could be None...
                        key_paths.append((guild_id_str, case_num_str))

        async with _config.custom(_CASES).all() as all_cases:
            for guild_id_str, case_num_str in key_paths:
                case = all_cases[guild_id_str][case_num_str]
                if (case.get("user", 0) or 0) == user_id:
                    case["user"] = 0xDE1
                    case.pop("last_known_username", None)
                if (case.get("moderator", 0) or 0) == user_id:
                    case["moderator"] = 0xDE1
                if (case.get("amended_by", 0) or 0) == user_id:
                    case["amended_by"] = 0xDE1


async def _init(bot: Red):
    global _config
    global _bot_ref
    _bot_ref = bot
    _config = Config.get_conf(None, 1354799444, cog_name="ModLog")
    _config.register_global(schema_version=1)
    _config.register_guild(mod_log=None, casetypes={}, latest_case_number=0)
    _config.init_custom(_CASETYPES, 1)
    _config.init_custom(_CASES, 2)
    _config.register_custom(_CASETYPES)
    _config.register_custom(_CASES)
    await _migrate_config(from_version=await _config.schema_version(), to_version=_SCHEMA_VERSION)
    await register_casetypes(all_generics)

    async def on_audit_log_entry_create(entry: discord.AuditLogEntry):
        guild = entry.guild
        if guild.unavailable:
            return
        if entry.action not in (discord.AuditLogAction.ban, discord.AuditLogAction.unban):
            return

        try:
            await get_modlog_channel(guild)
        except RuntimeError:
            return  # No modlog channel so no point in continuing

        # Don't create modlog entires for the bot's own bans, cogs do this.
        if entry.user_id == guild.me.id:
            return

        mod, reason, date = entry.user, entry.reason, entry.created_at
        await create_case(_bot_ref, guild, date, entry.action.name, entry.target, mod, reason)

    bot.add_listener(on_audit_log_entry_create)


async def _handle_audit_type_key():
    all_casetypes = {
        casetype_name: {
            inner_key: inner_value
            for inner_key, inner_value in casetype_data.items()
            if inner_key != "audit_type"
        }
        for casetype_name, casetype_data in (await _config.custom(_CASETYPES).all()).items()
    }
    await _config.custom(_CASETYPES).set(all_casetypes)


async def _migrate_config(from_version: int, to_version: int):
    if from_version == to_version:
        return

    if from_version < 2 <= to_version:
        # casetypes go from GLOBAL -> casetypes to CASETYPES
        all_casetypes = await _config.get_raw("casetypes", default={})
        if all_casetypes:
            await _config.custom(_CASETYPES).set(all_casetypes)

        # cases go from GUILD -> guild_id -> cases to CASES -> guild_id -> cases
        all_guild_data = await _config.all_guilds()
        all_cases = {}
        for guild_id, guild_data in all_guild_data.items():
            guild_cases = guild_data.pop("cases", None)
            if guild_cases:
                all_cases[str(guild_id)] = guild_cases
        await _config.custom(_CASES).set(all_cases)

        # new schema is now in place
        await _config.schema_version.set(2)

        # migration done, now let's delete all the old stuff
        await _config.clear_raw("casetypes")
        for guild_id in all_guild_data:
            await _config.guild(cast(discord.Guild, discord.Object(id=guild_id))).clear_raw(
                "cases"
            )

    if from_version < 3 <= to_version:
        await _handle_audit_type_key()
        await _config.schema_version.set(3)

    if from_version < 4 <= to_version:
        # set latest_case_number
        for guild_id, cases in (await _config.custom(_CASES).all()).items():
            if cases:
                await _config.guild(
                    cast(discord.Guild, discord.Object(id=guild_id))
                ).latest_case_number.set(max(map(int, cases.keys())))

        await _config.schema_version.set(4)


class Case:
    """
    Case()

    A single mod log case

    This class should ONLY be instantiated by the modlog itself.

    Attributes
    ----------
    bot: Red
        The bot object.
    guild: discord.Guild
        The guild the action was taken in.
    created_at: int
        The UNIX time the action occurred at.
    action_type: str
        The type of action that was taken.
    user: Union[discord.abc.User, int]
        The user target by the action.

        .. note::
            This attribute will be of type `int`
            if the Discord user can no longer be found.
    moderator: Optional[Union[discord.abc.User, int]]
        The moderator who took the action.
        `None` if the moderator is unknown.

        .. note::
            This attribute will be of type `int`
            if the Discord user can no longer be found.
    case_number: int
        The case's number.
    reason: Optional[str]
        The reason the action was taken.
        `None` if the reason was not specified.
    until: Optional[int]
        The UNIX time the action is in effect until.
        `None` if the action is permanent.
    channel: Optional[Union[discord.abc.GuildChannel, discord.Thread, int]]
        The channel the action was taken in.
        `None` if the action was not related to a channel.

        .. note::
            This attribute will be of type `int`
            if the channel seems to no longer exist.
    parent_channel_id: Optional[int]
        The parent channel ID of the thread in ``channel``.
        `None` if the action was not done in a thread.
    amended_by: Optional[Union[discord.abc.User, int]]
        The moderator who made the last change to the case.
        `None` if the case was never edited.

        .. note::
            This attribute will be of type `int`
            if the Discord user can no longer be found.
    modified_at: Optional[float]
        The UNIX time of the last change to the case.
        `None` if the case was never edited.
    message: Optional[Union[discord.PartialMessage, discord.Message]]
        The message created by Modlog for this case.
        Instance of `discord.Message` *if* the Case object was returned from
        `modlog.create_case()`, otherwise `discord.PartialMessage`.

        `None` if we know that the message no longer exists
        (note: it might not exist regardless of whether this attribute is `None`)
        or if it has never been created.
    last_known_username: Optional[str]
        The last known user handle (``username`` / ``username#1234``) of the user.
        `None` if the handle of the user was never saved
        or if their data had to be anonymized.
    """

    def __init__(
        self,
        bot: Red,
        guild: discord.Guild,
        created_at: int,
        action_type: str,
        user: Union[discord.Object, discord.abc.User, int],
        moderator: Optional[Union[discord.Object, discord.abc.User, int]],
        case_number: int,
        reason: Optional[str] = None,
        until: Optional[int] = None,
        channel: Optional[Union[discord.abc.GuildChannel, discord.Thread, int]] = None,
        parent_channel_id: Optional[int] = None,
        amended_by: Optional[Union[discord.Object, discord.abc.User, int]] = None,
        modified_at: Optional[float] = None,
        message: Optional[Union[discord.PartialMessage, discord.Message]] = None,
        last_known_username: Optional[str] = None,
    ):
        self.bot = bot
        self.guild = guild
        self.created_at = created_at
        self.action_type = action_type
        self.user = user
        if isinstance(user, discord.Object):
            self.user = user.id
        self.last_known_username = last_known_username
        self.moderator = moderator
        if isinstance(moderator, discord.Object):
            self.moderator = moderator.id
        self.reason = reason
        self.until = until
        self.channel = channel
        self.parent_channel_id = parent_channel_id
        self.amended_by = amended_by
        if isinstance(amended_by, discord.Object):
            self.amended_by = amended_by.id
        self.modified_at = modified_at
        self.case_number = case_number
        self.message = message

    @property
    def parent_channel(self) -> Optional[Union[discord.TextChannel, discord.ForumChannel]]:
        """
        The parent text/forum channel of the thread in `channel`.

        This will be `None` if `channel` is not a thread
        and when the parent text/forum channel is not in cache (probably due to removal).
        """
        if self.parent_channel_id is None:
            return None
        return self.guild.get_channel(self.parent_channel_id)

    async def _set_message(self, message: discord.Message, /) -> None:
        # This should only be used for setting the message right after case creation
        # in order to avoid making an API request to "edit" the message with changes.
        # In all other cases, edit() is correct method.
        self.message = message
        await _config.custom(_CASES, str(self.guild.id), str(self.case_number)).set(self.to_json())

    async def edit(self, data: dict):
        """
        Edits a case

        Parameters
        ----------
        data: dict
            The attributes to change

        """
        # We don't want case_number to be changed
        data.pop("case_number", None)
        # last username is set based on passed user object
        data.pop("last_known_username", None)
        for item, value in data.items():
            if item == "channel" and isinstance(value, discord.PartialMessageable):
                raise TypeError("Can't use PartialMessageable as the channel for a modlog case.")
            if isinstance(value, discord.Object):
                # probably expensive to call but meh should capture all cases
                setattr(self, item, value.id)
            else:
                setattr(self, item, value)

        # update last known user handle
        if not isinstance(self.user, int):
            self.last_known_username = str(self.user)

        if isinstance(self.channel, discord.Thread):
            self.parent_channel_id = self.channel.parent_id

        await _config.custom(_CASES, str(self.guild.id), str(self.case_number)).set(self.to_json())
        self.bot.dispatch("modlog_case_edit", self)
        if not self.message:
            return
        try:
            use_embed = await self.bot.embed_requested(self.message.channel)
            case_content = await self.message_content(use_embed)
            if use_embed:
                await self.message.edit(embed=case_content)
            else:
                await self.message.edit(content=case_content)
        except discord.Forbidden:
            log.info(
                "Modlog failed to edit the Discord message for"
                " the case #%s from guild with ID %s due to missing permissions.",
                self.case_number,
                self.guild.id,
            )
        except discord.NotFound:
            log.info(
                "Modlog failed to edit the Discord message for"
                " the case #%s from guild with ID %s as it no longer exists."
                " Clearing the message ID from case data...",
                self.case_number,
                self.guild.id,
            )
            await self.edit({"message": None})
        except Exception:
            log.exception(
                "Modlog failed to edit the Discord message for"
                " the case #%s from guild with ID %s due to unexpected error.",
                self.case_number,
                self.guild.id,
            )

    async def message_content(self, embed: bool = True):
        """
        Format a case message

        Parameters
        ----------
        embed: bool
            Whether or not to get an embed

        Returns
        -------
        discord.Embed or `str`
            A rich embed or string representing a case message

        """
        casetype = await get_casetype(self.action_type)
        title = "{}".format(
            _("Case #{} | {} {}").format(self.case_number, casetype.case_str, casetype.image)
        )
        reason = _("**Reason:** Use the `reason` command to add it")

        if self.moderator is None:
            moderator = _("Unknown")
        elif isinstance(self.moderator, int):
            # can't use _() inside f-string expressions, see bpo-36310 and red#3818
            if self.moderator == 0xDE1:
                moderator = _("Deleted User.")
            else:
                translated = _("Unknown or Deleted User")
                moderator = f"[{translated}] ({self.moderator})"
        else:
            moderator = escape_spoilers(f"{self.moderator} ({self.moderator.id})")
        until = None
        duration = None
        if self.until:
            start = datetime.fromtimestamp(self.created_at, tz=timezone.utc)
            end = datetime.fromtimestamp(self.until, tz=timezone.utc)
            end_fmt = discord.utils.format_dt(end)
            duration = end - start
            dur_fmt = _strfdelta(duration)
            until = end_fmt
            duration = dur_fmt

        if self.amended_by is None:
            amended_by = None
        elif isinstance(self.amended_by, int):
            # can't use _() inside f-string expressions, see bpo-36310 and red#3818
            if self.amended_by == 0xDE1:
                amended_by = _("Deleted User.")
            else:
                translated = _("Unknown or Deleted User")
                amended_by = f"[{translated}] ({self.amended_by})"
        else:
            amended_by = escape_spoilers(f"{self.amended_by} ({self.amended_by.id})")

        last_modified = None
        if self.modified_at:
            last_modified = discord.utils.format_dt(
                datetime.fromtimestamp(self.modified_at, tz=timezone.utc)
            )

        if isinstance(self.user, int):
            if self.user == 0xDE1:
                user = _("Deleted User.")
            elif self.last_known_username is None:
                # can't use _() inside f-string expressions, see bpo-36310 and red#3818
                translated = _("Unknown or Deleted User")
                user = f"[{translated}] ({self.user})"
            # Handle pomelo usernames stored before we updated our implementation
            elif self.last_known_username.endswith("#0"):
                user = f"{self.last_known_username[:-2]} ({self.user})"
            # New usernames can't contain `#` and old usernames couldn't either.
            elif len(self.last_known_username) <= 5 or self.last_known_username[-5] != "#":
                user = f"{self.last_known_username} ({self.user})"
            # Last known user handle is a legacy username with a discriminator
            else:
                # isolate the name so that the direction of the discriminator and ID aren't changed
                # See usage explanation here: https://www.unicode.org/reports/tr9/#Formatting
                name = self.last_known_username[:-5]
                discriminator = self.last_known_username[-4:]
                user = (
                    f"\N{FIRST STRONG ISOLATE}{name}"
                    f"\N{POP DIRECTIONAL ISOLATE}#{discriminator} ({self.user})"
                )
        elif self.user.discriminator == "0":
            user = f"{self.user} ({self.user.id})"
        else:
            # isolate the name so that the direction of the discriminator and ID aren't changed
            # See usage explanation here: https://www.unicode.org/reports/tr9/#Formatting
            user = escape_spoilers(
                filter_invites(
                    f"\N{FIRST STRONG ISOLATE}{self.user.name}"
                    f"\N{POP DIRECTIONAL ISOLATE}#{self.user.discriminator} ({self.user.id})"
                )
            )  # Invites and spoilers get rendered even in embeds.

        channel_value = None
        if isinstance(self.channel, int):
            if self.parent_channel_id is not None:
                if (parent_channel := self.parent_channel) is not None:
                    channel_value = _(
                        "Deleted or archived thread ({thread_id}) in {channel_name}"
                    ).format(thread_id=self.channel, channel_name=parent_channel)
                else:
                    channel_value = _("Thread {thread_id} in {channel_id} (deleted)").format(
                        thread_id=self.channel, channel_id=self.parent_channel_id
                    )
            else:
                channel_value = _("{channel_id} (deleted)").format(channel_id=self.channel)
        elif self.channel is not None:
            channel_value = self.channel.name
            if self.parent_channel_id is not None:
                if (parent_channel := self.parent_channel) is not None:
                    channel_value = _("Thread {thread_name} in {channel_name}").format(
                        thread_name=self.channel, channel_name=parent_channel
                    )
                else:
                    channel_value = _("Thread {thread_name} in {channel_id} (deleted)").format(
                        thread_name=self.channel, channel_id=self.parent_channel_id
                    )

        if embed:
            if self.reason:
                reason = f"{bold(_('Reason:'))} {self.reason}"
                if len(reason) > 2048:
                    reason = (
                        next(
                            pagify(
                                reason,
                                delims=[" ", "\n"],
                                page_length=2000,
                            )
                        )
                        + "..."
                    )
            emb = discord.Embed(title=title, description=reason)
            emb.set_author(name=user)
            emb.add_field(name=_("Moderator"), value=moderator, inline=False)
            if until and duration:
                emb.add_field(name=_("Until"), value=until)
                emb.add_field(name=_("Duration"), value=duration)
            if channel_value:
                emb.add_field(name=_("Channel"), value=channel_value, inline=False)
            if amended_by:
                emb.add_field(name=_("Amended by"), value=amended_by)
            if last_modified:
                emb.add_field(name=_("Last modified at"), value=last_modified)
            emb.timestamp = datetime.fromtimestamp(self.created_at, tz=timezone.utc)
            return emb
        else:
            if self.reason:
                reason = f"{bold(_('Reason:'))} {self.reason}"
                if len(reason) > 1000:
                    reason = (
                        next(
                            pagify(
                                reason,
                                delims=[" ", "\n"],
                                page_length=1000,
                            )
                        )
                        + "..."
                    )
            user = filter_mass_mentions(filter_urls(user))  # Further sanitization outside embeds
            case_text = ""
            case_text += "{}\n".format(title)
            case_text += f"{bold(_('User:'))} {user}\n"
            case_text += f"{bold(_('Moderator:'))} {moderator}\n"
            case_text += "{}\n".format(reason)
            if until and duration:
                case_text += f"{bold(_('Until:'))} {until}\n{bold(_('Duration:'))} {duration}\n"
            if self.channel:
                if isinstance(self.channel, int):
                    case_text += f"{bold(_('Channel:'))} {channel_value}\n"
                else:
                    case_text += f"{bold(_('Channel:'))} {channel_value}\n"
            if amended_by:
                case_text += f"{bold(_('Amended by:'))} {amended_by}\n"
            if last_modified:
                case_text += f"{bold(_('Last modified at:'))} {last_modified}\n"
            return case_text.strip()

    def to_json(self) -> dict:
        """Transform the object to a dict

        Returns
        -------
        dict
            The case in the form of a dict

        """
        if self.moderator is None or isinstance(self.moderator, int):
            mod = self.moderator
        else:
            mod = self.moderator.id
        if self.amended_by is None or isinstance(self.amended_by, int):
            amended_by = self.amended_by
        else:
            amended_by = self.amended_by.id
        if isinstance(self.user, int):
            user_id = self.user
        else:
            user_id = self.user.id
        data = {
            "case_number": self.case_number,
            "action_type": self.action_type,
            "guild": self.guild.id,
            "created_at": self.created_at,
            "user": user_id,
            "last_known_username": self.last_known_username,
            "moderator": mod,
            "reason": self.reason,
            "until": self.until,
            "channel": self.channel.id if hasattr(self.channel, "id") else None,
            "parent_channel": self.parent_channel_id,
            "amended_by": amended_by,
            "modified_at": self.modified_at,
            "message": self.message.id if hasattr(self.message, "id") else None,
        }
        return data

    @classmethod
    async def from_json(
        cls,
        mod_channel: Union[discord.TextChannel, discord.VoiceChannel, discord.StageChannel],
        bot: Red,
        case_number: int,
        data: dict,
        **kwargs,
    ):
        """Get a Case object from the provided information

        Parameters
        ----------
        mod_channel: `discord.TextChannel` or `discord.VoiceChannel`, `discord.StageChannel`
            The mod log channel for the guild
        bot: Red
            The bot's instance. Needed to get the target user
        case_number: int
            The case's number.
        data: dict
            The JSON representation of the case to be gotten
        **kwargs
            Extra attributes for the Case instance which override values
            in the data dict. These should be complete objects and not
            IDs, where possible.

        Returns
        -------
        Case
            The case object for the requested case

        Raises
        ------
        `discord.NotFound`
            The user the case is for no longer exists
        `discord.Forbidden`
            Cannot read message history to fetch the original message.
        `discord.HTTPException`
            A generic API issue
        """
        guild = kwargs.get("guild") or mod_channel.guild

        message = kwargs.get("message")
        if message is None:
            message_id = data.get("message")
            if message_id is not None:
                if mod_channel is not None:
                    message = mod_channel.get_partial_message(message_id)

        user_objects = {"user": None, "moderator": None, "amended_by": None}
        for user_key in tuple(user_objects):
            user_object = kwargs.get(user_key)
            if user_object is None:
                user_id = data.get(user_key)
                if user_id is None:
                    user_object = None
                else:
                    user_object = bot.get_user(user_id) or user_id
            user_objects[user_key] = user_object

        channel = (
            kwargs.get("channel")
            or guild.get_channel_or_thread(data["channel"])
            or data["channel"]
        )
        case_guild = kwargs.get("guild") or bot.get_guild(data["guild"])
        return cls(
            bot=bot,
            guild=case_guild,
            created_at=data["created_at"],
            action_type=data["action_type"],
            case_number=case_number,
            reason=data["reason"],
            until=data["until"],
            channel=channel,
            parent_channel_id=data.get("parent_channel_id"),
            modified_at=data["modified_at"],
            message=message,
            last_known_username=data.get("last_known_username"),
            **user_objects,
        )


class CaseType:
    """
    A single case type

    This class should ONLY be instantiated by the modlog itself.

    Attributes
    ----------
    name: str
        The name of the case
    default_setting: bool
        Whether the case type should be on (if `True`)
        or off (if `False`) by default
    image: str
        The emoji to use for the case type (for example, :boot:)
    case_str: str
        The string representation of the case (example: Ban)

    """

    def __init__(
        self,
        name: str,
        default_setting: bool,
        image: str,
        case_str: str,
        guild: Optional[discord.Guild] = None,
        **kwargs,
    ):
        self.name = name
        self.default_setting = default_setting
        self.image = image
        self.case_str = case_str
        self.guild = guild

        if "audit_type" in kwargs:
            kwargs.pop("audit_type", None)
            log.warning(
                "Fix this using the hidden command: `modlogset fixcasetypes` in Discord: "
                "Got outdated key in casetype: audit_type"
            )
        if kwargs:
            log.warning("Got unexpected key(s) in casetype: %s", ",".join(kwargs.keys()))

    async def to_json(self):
        """Transforms the case type into a dict and saves it"""
        data = {
            "default_setting": self.default_setting,
            "image": self.image,
            "case_str": self.case_str,
        }
        await _config.custom(_CASETYPES, self.name).set(data)

    async def is_enabled(self) -> bool:
        """
        Determines if the case is enabled.
        If the guild is not set, this will always return False

        Returns
        -------
        bool:
            True if the guild is set and the casetype is enabled for the guild

            False if the guild is not set or if the guild is set and the type
            is disabled
        """
        if not self.guild:
            return False
        return await _config.guild(self.guild).casetypes.get_raw(
            self.name, default=self.default_setting
        )

    async def set_enabled(self, enabled: bool):
        """
        Sets the case as enabled or disabled

        Parameters
        ----------
        enabled: bool
            True if the case should be enabled, otherwise False"""
        if not self.guild:
            return
        await _config.guild(self.guild).casetypes.set_raw(self.name, value=enabled)

    @classmethod
    def from_json(cls, name: str, data: dict, **kwargs):
        """

        Parameters
        ----------
        name : str
            The casetype's name.
        data : dict
            The JSON data to create an instance from
        **kwargs
            Values for other attributes of the instance

        Returns
        -------
        CaseType
            The case type object created from given data.
        """
        data_copy = data.copy()
        data_copy.pop("name", None)
        return cls(name=name, **data_copy, **kwargs)


async def get_case(case_number: int, guild: discord.Guild, bot: Red) -> Case:
    """
    Gets the case with the associated case number

    Parameters
    ----------
    case_number: int
        The case number for the case to get
    guild: discord.Guild
        The guild to get the case from
    bot: Red
        The bot's instance

    Returns
    -------
    Case
        The case associated with the case number

    Raises
    ------
    RuntimeError
        If there is no case for the specified number

    """

    case = await _config.custom(_CASES, str(guild.id), str(case_number)).all()
    if not case:
        raise RuntimeError("That case does not exist for guild {}".format(guild.name))
    try:
        mod_channel = await get_modlog_channel(guild)
    except RuntimeError:
        mod_channel = None
    return await Case.from_json(mod_channel, bot, case_number, case, guild=guild)


async def get_latest_case(guild: discord.Guild, bot: Red) -> Optional[Case]:
    """Get the latest case for the specified guild.

    Parameters
    ----------
    guild : discord.Guild
        The guild to get the latest case for.
    bot : Red
        The bot object.

    Returns
    -------
    Optional[Case]
        The latest case object. `None` if it the guild has no cases.

    """
    case_number = await _config.guild(guild).latest_case_number()
    if case_number:
        return await get_case(case_number, guild, bot)


async def get_all_cases(guild: discord.Guild, bot: Red) -> List[Case]:
    """
    Gets all cases for the specified guild

    Parameters
    ----------
    guild: `discord.Guild`
        The guild to get the cases from
    bot: Red
        The bot's instance

    Returns
    -------
    list
        A list of all cases for the guild

    """
    cases = await _config.custom(_CASES, str(guild.id)).all()
    try:
        mod_channel = await get_modlog_channel(guild)
    except RuntimeError:
        mod_channel = None
    return [
        await Case.from_json(mod_channel, bot, case_number, case_data, guild=guild)
        for case_number, case_data in cases.items()
    ]


async def get_cases_for_member(
    guild: discord.Guild, bot: Red, *, member: discord.Member = None, member_id: int = None
) -> List[Case]:
    """
    Gets all cases for the specified member or member id in a guild.

    Parameters
    ----------
    guild: `discord.Guild`
        The guild to get the cases from
    bot: Red
        The bot's instance
    member: `discord.Member`
        The member to get cases about
    member_id: int
        The id of the member to get cases about

    Returns
    -------
    list
        A list of all matching cases.

    Raises
    ------
    ValueError
        If at least one of member or member_id is not provided
    `discord.Forbidden`
        The bot does not have permission to fetch the modlog message which was sent.
    `discord.HTTPException`
        Fetching the user failed.
    """

    cases = await _config.custom(_CASES, str(guild.id)).all()

    if not (member_id or member):
        raise ValueError("Expected a member or a member id to be provided.") from None

    if not member_id:
        member_id = member.id

    if not member:
        member = bot.get_user(member_id) or member_id

    try:
        modlog_channel = await get_modlog_channel(guild)
    except RuntimeError:
        modlog_channel = None

    cases = [
        await Case.from_json(modlog_channel, bot, case_number, case_data, user=member, guild=guild)
        for case_number, case_data in cases.items()
        if case_data["user"] == member_id
    ]

    return cases


async def create_case(
    bot: Red,
    guild: discord.Guild,
    created_at: datetime,
    action_type: str,
    user: Union[discord.Object, discord.abc.User, int],
    moderator: Optional[Union[discord.Object, discord.abc.User, int]] = None,
    reason: Optional[str] = None,
    until: Optional[datetime] = None,
    channel: Optional[Union[discord.abc.GuildChannel, discord.Thread]] = None,
    last_known_username: Optional[str] = None,
) -> Optional[Case]:
    """
    Creates a new case.

    This fires an event :code:`on_modlog_case_create`

    Parameters
    ----------
    bot: Red
        The bot object
    guild: discord.Guild
        The guild the action was taken in
    created_at: datetime
        The time the action occurred at.
        If naive `datetime` object is passed, it's treated as a local time
        (similarly to how Python treats naive `datetime` objects).
    action_type: str
        The type of action that was taken
    user: Union[discord.Object, discord.abc.User, int]
        The user target by the action
    moderator: Optional[Union[discord.Object, discord.abc.User, int]]
        The moderator who took the action
    reason: Optional[str]
        The reason the action was taken
    until: Optional[datetime]
        The time the action is in effect until.
        If naive `datetime` object is passed, it's treated as a local time
        (similarly to how Python treats naive `datetime` objects).
    channel: Optional[Union[discord.abc.GuildChannel, discord.Thread]]
        The channel the action was taken in
    last_known_username: Optional[str]
        The last known user handle (``username`` / ``username#1234``) of the user
        Note: This is ignored if a Member or User object is provided
        in the user field

    Raises
    ------
    ValueError
        If the action type is not a valid action type.
    RuntimeError
        If user is the bot itself.
    TypeError
        If ``channel`` is of type `discord.PartialMessageable`.
    """
    case_type = await get_casetype(action_type, guild)
    if case_type is None:
        raise ValueError(f"{action_type} is not a valid action type.")

    if not await case_type.is_enabled():
        return

    user_id = user if isinstance(user, int) else user.id
    if user_id == bot.user.id:
        raise RuntimeError("The bot itself can not be the target of a modlog entry.")

    if isinstance(channel, discord.PartialMessageable):
        raise TypeError("Can't use PartialMessageable as the channel for a modlog case.")

    parent_channel_id = channel.parent_id if isinstance(channel, discord.Thread) else None

    async with _config.guild(guild).latest_case_number.get_lock():
        # We're getting the case number from config, incrementing it, awaiting something, then
        # setting it again. This warrants acquiring the lock.
        next_case_number = await _config.guild(guild).latest_case_number() + 1

        case = Case(
            bot,
            guild,
            int(created_at.timestamp()),
            action_type,
            user,
            moderator,
            next_case_number,
            reason,
            int(until.timestamp()) if until else None,
            channel,
            parent_channel_id,
            amended_by=None,
            modified_at=None,
            message=None,
            last_known_username=last_known_username,
        )
        await _config.custom(_CASES, str(guild.id), str(next_case_number)).set(case.to_json())
        await _config.guild(guild).latest_case_number.set(next_case_number)

    await set_contextual_locales_from_guild(bot, guild)
    bot.dispatch("modlog_case_create", case)
    try:
        mod_channel = await get_modlog_channel(case.guild)
        use_embeds = await case.bot.embed_requested(mod_channel)
        case_content = await case.message_content(use_embeds)
        if use_embeds:
            msg = await mod_channel.send(embed=case_content)
        else:
            msg = await mod_channel.send(case_content)
        await case._set_message(msg)
    except RuntimeError:  # modlog channel isn't set
        pass
    except discord.Forbidden:
        log.info(
            "Modlog failed to edit the Discord message for"
            " the case #%s from guild with ID due to missing permissions."
        )
    except Exception:
        log.exception(
            "Modlog failed to send the Discord message for"
            " the case #%s from guild with ID %s due to unexpected error.",
            case.case_number,
            case.guild.id,
        )
    return case


async def get_casetype(name: str, guild: Optional[discord.Guild] = None) -> Optional[CaseType]:
    """
    Gets the case type

    Parameters
    ----------
    name: str
        The name of the case type to get
    guild: Optional[discord.Guild]
        If provided, sets the case type's guild attribute to this guild

    Returns
    -------
    Optional[CaseType]
        Case type with provided name. If such case type doesn't exist this will be `None`.
    """
    data = await _config.custom(_CASETYPES, name).all()
    if not data:
        return
    casetype = CaseType.from_json(name, data)
    casetype.guild = guild
    return casetype


async def get_all_casetypes(guild: discord.Guild = None) -> List[CaseType]:
    """
    Get all currently registered case types

    Returns
    -------
    list
        A list of case types

    """
    return [
        CaseType.from_json(name, data, guild=guild)
        for name, data in (await _config.custom(_CASETYPES).all()).items()
    ]


async def register_casetype(
    name: str, default_setting: bool, image: str, case_str: str
) -> CaseType:
    """
    Registers a case type. If the case type exists and
    there are differences between the values passed and
    what is stored already, the case type will be updated
    with the new values

    Parameters
    ----------
    name: str
        The name of the case
    default_setting: bool
        Whether the case type should be on (if `True`)
        or off (if `False`) by default
    image: str
        The emoji to use for the case type (for example, :boot:)
    case_str: str
        The string representation of the case (example: Ban)

    Returns
    -------
    CaseType
        The case type that was registered

    Raises
    ------
    RuntimeError
        If the case type is already registered
    TypeError
        If a parameter is missing
    ValueError
        If a parameter's value is not valid

    """
    if not isinstance(name, str):
        raise ValueError("The 'name' is not a string! Check the value!")
    if not isinstance(default_setting, bool):
        raise ValueError("'default_setting' needs to be a bool!")
    if not isinstance(image, str):
        raise ValueError("The 'image' is not a string!")
    if not isinstance(case_str, str):
        raise ValueError("The 'case_str' is not a string!")

    ct = await get_casetype(name)
    if ct is None:
        casetype = CaseType(name, default_setting, image, case_str)
        await casetype.to_json()
        return casetype
    else:
        # Case type exists, so check for differences
        # If no differences, raise RuntimeError
        changed = False
        if ct.default_setting != default_setting:
            ct.default_setting = default_setting
            changed = True
        if ct.image != image:
            ct.image = image
            changed = True
        if ct.case_str != case_str:
            ct.case_str = case_str
            changed = True
        if changed:
            await ct.to_json()
            return ct
        else:
            raise RuntimeError("That case type is already registered!")


async def register_casetypes(new_types: List[dict]) -> List[CaseType]:
    """
    Registers multiple case types

    Parameters
    ----------
    new_types: list
        The new types to register

    Returns
    -------
    bool
        `True` if all were registered successfully

    Raises
    ------
    KeyError
    ValueError
    AttributeError

    See Also
    --------
    redbot.core.modlog.register_casetype

    """
    type_list = []
    for new_type in new_types:
        try:
            ct = await register_casetype(**new_type)
        except RuntimeError:
            # We pass here because RuntimeError signifies the case was
            # already registered.
            pass
        else:
            type_list.append(ct)
    else:
        return type_list


async def get_modlog_channel(
    guild: discord.Guild,
) -> Union[discord.TextChannel, discord.VoiceChannel, discord.StageChannel]:
    """
    Get the current modlog channel.

    Parameters
    ----------
    guild: `discord.Guild`
        The guild to get the modlog channel for.

    Returns
    -------
    `discord.TextChannel`, `discord.VoiceChannel`, or `discord.StageChannel`
        The channel object representing the modlog channel.

    Raises
    ------
    RuntimeError
        If the modlog channel is not found.

    """
    if hasattr(guild, "get_channel"):
        channel = guild.get_channel(await _config.guild(guild).mod_log())
    else:
        # For unit tests only
        channel = await _config.guild(guild).mod_log()
    if channel is None:
        raise RuntimeError("Failed to get the mod log channel!")
    return channel


async def set_modlog_channel(
    guild: discord.Guild,
    channel: Union[discord.TextChannel, discord.VoiceChannel, discord.StageChannel, None],
) -> bool:
    """
    Changes the modlog channel

    Parameters
    ----------
    guild: `discord.Guild`
        The guild to set a mod log channel for
    channel: `discord.TextChannel`, `discord.VoiceChannel`, `discord.StageChannel`, or `None`
        The channel to be set as modlog channel

    Returns
    -------
    bool
        `True` if successful

    """
    await _config.guild(guild).mod_log.set(channel.id if hasattr(channel, "id") else None)
    return True


async def reset_cases(guild: discord.Guild) -> None:
    """
    Wipes all modlog cases for the specified guild.

    Parameters
    ----------
    guild: `discord.Guild`
        The guild to reset cases for

    """
    await _config.custom(_CASES, str(guild.id)).clear()
    await _config.guild(guild).latest_case_number.clear()


def _strfdelta(delta):
    s = []
    if delta.days:
        ds = "%i day" % delta.days
        if delta.days > 1:
            ds += "s"
        s.append(ds)
    hrs, rem = divmod(delta.seconds, 60 * 60)
    if hrs:
        hs = "%i hr" % hrs
        if hrs > 1:
            hs += "s"
        s.append(hs)
    mins, secs = divmod(rem, 60)
    if mins:
        s.append("%i min" % mins)
    if secs:
        s.append("%i sec" % secs)
    return " ".join(s)
