########## SENSITIVE SECTION WARNING ###########
################################################
# Any edits of any of the exported names       #
# may result in a breaking change.             #
# Ensure no names are removed without warning. #
################################################

### DEP-WARN: Check this *every* discord.py update
from discord.app_commands.checks import (
    bot_has_permissions,
    cooldown,
    dynamic_cooldown,
    has_any_role,
    has_role,
    has_permissions,
)

import discord
import enum
from typing import Dict, Optional
from . import BotMissingPermissions, check

__all__ = (
    "bot_has_permissions",
    "cooldown",
    "dynamic_cooldown",
    "has_any_role",
    "has_role",
    "has_permissions",
    "is_owner",
    "guildowner",
    "admin",
    "mod",
    "guildowner_or_permissions",
    "admin_or_permissions",
    "mod_or_permissions",
    "can_manage_channel",
    "admin_or_can_manage_channel",
    "mod_or_can_manage_channel",
    "bot_can_manage_channel",
    "bot_can_react",
    "bot_in_a_guild",
)


class PrivilegeLevel(enum.IntEnum):
    """Enumeration for special privileges."""

    # Maintainer Note: do NOT re-order these.
    # Each privilege level also implies access to the ones before it.
    # Inserting new privilege levels at a later point is fine if that is considered.

    NONE = enum.auto()
    """No special privilege level."""

    MOD = enum.auto()
    """User has the mod role."""

    ADMIN = enum.auto()
    """User has the admin role."""

    GUILD_OWNER = enum.auto()
    """User is the guild level."""

    BOT_OWNER = enum.auto()
    """User is a bot owner."""

    @classmethod
    async def from_interaction(cls, interaction: discord.Interaction) -> "PrivilegeLevel":
        """Get a command author's PrivilegeLevel based on an interaction."""
        if await interaction.client.is_owner(interaction.user):
            return cls.BOT_OWNER
        elif interaction.guild is None:
            return cls.NONE
        elif interaction.user == interaction.guild.owner:
            return cls.GUILD_OWNER

        # The following is simply an optimised way to check if the user has the
        # admin or mod role.
        guild_settings = interaction.client._config.guild(interaction.guild)

        for snowflake in await guild_settings.admin_role():
            if interaction.user.get_role(snowflake):
                return cls.ADMIN
        for snowflake in await guild_settings.mod_role():
            if interaction.user.get_role(snowflake):
                return cls.MOD

        return cls.NONE

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}.{self.name}>"


def _validate_perms_dict(perms: Dict[str, bool]) -> None:
    invalid_keys = set(perms.keys()) - set(discord.Permissions.VALID_FLAGS)
    if invalid_keys:
        raise TypeError(f"Invalid perm name(s): {', '.join(invalid_keys)}")
    for perm, value in perms.items():
        if value is not True:
            # We reject any permission not specified as 'True', since this is the only value which
            # makes practical sense.
            raise TypeError(f"Permission {perm} may only be specified as 'True', not {value}")


def _permissions_deco(
    *,
    privilege_level: Optional[PrivilegeLevel] = None,
    user_perms: Optional[Dict[str, bool]] = None,
):
    if user_perms is not None:
        _validate_perms_dict(user_perms)

    async def predicate(interaction: discord.Interaction) -> bool:
        if privilege_level is not None:
            if await PrivilegeLevel.from_interaction(interaction) >= privilege_level:
                return True

        if user_perms is not None:
            permissions = interaction.permissions
            missing = [
                perm for perm, value in user_perms.items() if getattr(permissions, perm) != value
            ]

            if not missing:
                return True

        return False

    return check(predicate)


def is_owner():
    """
    Restrict the command to bot owners.

    You probably should not use this check, since slash commands are not designed to be owner only.

    .. note::

        This is different from the permission system that Discord provides for
        application commands. This is done entirely locally in the program rather
        than being handled by Discord.
    """
    return _permissions_deco(privilege_level=PrivilegeLevel.BOT_OWNER)


def guildowner():
    """
    Restrict the command to the guild owner.

    .. note::

        This is different from the permission system that Discord provides for
        application commands. This is done entirely locally in the program rather
        than being handled by Discord.
    """
    return _permissions_deco(privilege_level=PrivilegeLevel.GUILD_OWNER)


def admin():
    """
    Restrict the command to users with the admin role.

    .. note::

        This is different from the permission system that Discord provides for
        application commands. This is done entirely locally in the program rather
        than being handled by Discord.
    """
    return _permissions_deco(privilege_level=PrivilegeLevel.ADMIN)


def mod():
    """
    Restrict the command to users with the mod role.

    .. note::

        This is different from the permission system that Discord provides for
        application commands. This is done entirely locally in the program rather
        than being handled by Discord.
    """
    return _permissions_deco(privilege_level=PrivilegeLevel.MOD)


def guildowner_or_permissions(**perms: bool):
    """
    Restrict the command to the guild owner or users with these permissions.

    .. note::

        This is different from the permission system that Discord provides for
        application commands. This is done entirely locally in the program rather
        than being handled by Discord.
    """
    return _permissions_deco(privilege_level=PrivilegeLevel.GUILD_OWNER, user_perms=perms)


def admin_or_permissions(**perms: bool):
    """
    Restrict the command to users with the admin role or these permissions.

    .. note::

        This is different from the permission system that Discord provides for
        application commands. This is done entirely locally in the program rather
        than being handled by Discord.
    """
    return _permissions_deco(privilege_level=PrivilegeLevel.ADMIN, user_perms=perms)


def mod_or_permissions(**perms: bool):
    """
    Restrict the command to users with the mod role or these permissions.

    .. note::

        This is different from the permission system that Discord provides for
        application commands. This is done entirely locally in the program rather
        than being handled by Discord.
    """
    return _permissions_deco(privilege_level=PrivilegeLevel.MOD, user_perms=perms)


def _can_manage_channel_deco(
    *, privilege_level: Optional[PrivilegeLevel] = None, allow_thread_owner: bool = False
):
    async def predicate(interaction: discord.Interaction) -> bool:
        perms = interaction.permissions
        if isinstance(interaction.channel, discord.Thread):
            if perms.manage_threads or (
                allow_thread_owner and interaction.channel.owner_id == interaction.user.id
            ):
                return True
        else:
            if perms.manage_channels:
                return True

        if privilege_level is not None:
            if await PrivilegeLevel.from_interaction(interaction) >= privilege_level:
                return True

        return False

    return check(predicate)


def can_manage_channel(*, allow_thread_owner: bool = False):
    """
    Restrict the command to users with permissions to manage channel.

    This check properly resolves the permissions for `discord.Thread` as well.

    .. note::

        This is different from the permission system that Discord provides for
        application commands. This is done entirely locally in the program rather
        than being handled by Discord.

    Parameters
    ----------
    allow_thread_owner: bool
        If ``True``, the command will also be allowed to run if the author is a thread owner.
        This can, for example, be useful to check if the author can edit a channel/thread's name
        as that, in addition to members with manage channel/threads permission,
        can also be done by the thread owner.
    """
    return _can_manage_channel_deco(allow_thread_owner=allow_thread_owner)


def admin_or_can_manage_channel(*, allow_thread_owner: bool = False):
    """
    Restrict the command to users with the admin role or permissions to manage channel.

    This check properly resolves the permissions for `discord.Thread` as well.

    .. note::

        This is different from the permission system that Discord provides for
        application commands. This is done entirely locally in the program rather
        than being handled by Discord.

    Parameters
    ----------
    allow_thread_owner: bool
        If ``True``, the command will also be allowed to run if the author is a thread owner.
        This can, for example, be useful to check if the author can edit a channel/thread's name
        as that, in addition to members with manage channel/threads permission,
        can also be done by the thread owner.
    """
    return _can_manage_channel_deco(
        privilege_level=PrivilegeLevel.ADMIN, allow_thread_owner=allow_thread_owner
    )


def mod_or_can_manage_channel(*, allow_thread_owner: bool = False):
    """
    Restrict the command to users with the mod role or permissions to manage channel.

    This check properly resolves the permissions for `discord.Thread` as well.

    .. note::

        This is different from the permission system that Discord provides for
        application commands. This is done entirely locally in the program rather
        than being handled by Discord.

    Parameters
    ----------
    allow_thread_owner: bool
        If ``True``, the command will also be allowed to run if the author is a thread owner.
        This can, for example, be useful to check if the author can edit a channel/thread's name
        as that, in addition to members with manage channel/threads permission,
        can also be done by the thread owner.
    """
    return _can_manage_channel_deco(
        privilege_level=PrivilegeLevel.MOD, allow_thread_owner=allow_thread_owner
    )


def bot_can_manage_channel(*, allow_thread_owner: bool = False):
    """
    Complain if the bot is missing permissions to manage channel.

    This check properly resolves the permissions for `discord.Thread` as well.

    .. note::

        This is different from the permission system that Discord provides for
        application commands. This is done entirely locally in the program rather
        than being handled by Discord.

    Parameters
    ----------
    allow_thread_owner: bool
        If ``True``, the command will also be allowed to run if the bot is a thread owner.
        This can, for example, be useful to check if the bot can edit a channel/thread's name
        as that, in addition to members with manage channel/threads permission,
        can also be done by the thread owner.
    """

    def predicate(interaction: discord.Interaction) -> bool:
        if interaction.guild is None:
            return False

        perms = interaction.app_permissions
        if isinstance(interaction.channel, discord.Thread):
            if not (
                perms.manage_threads
                or (
                    allow_thread_owner
                    and interaction.channel.owner_id == interaction.client.user.id
                )
            ):
                # This is a slight lie - thread owner *might* also be allowed
                # but we just say that bot is missing the Manage Threads permission.
                raise BotMissingPermissions(["manage_threads"])
        else:
            if not perms.manage_channels:
                raise BotMissingPermissions(["manage_channels"])

        return True

    return check(predicate)


def bot_can_react():
    """
    Complain if the bot is missing permissions to react.

    This check properly resolves the permissions for `discord.Thread` as well.

    .. note::

        This is different from the permission system that Discord provides for
        application commands. This is done entirely locally in the program rather
        than being handled by Discord.
    """

    async def predicate(interaction: discord.Interaction) -> bool:
        return not (
            isinstance(interaction.channel, discord.Thread) and interaction.channel.archived
        )

    def decorator(func):
        func = bot_has_permissions(read_message_history=True, add_reactions=True)(func)
        func = check(predicate)(func)
        return func

    return decorator


def bot_in_a_guild():
    """
    Deny the command if the bot is not in a guild.

    .. note::

        This is different from the permission system that Discord provides for
        application commands. This is done entirely locally in the program rather
        than being handled by Discord.
    """

    async def predicate(interaction: discord.Interaction) -> bool:
        return len(interaction.client.guilds) > 0

    return check(predicate)
