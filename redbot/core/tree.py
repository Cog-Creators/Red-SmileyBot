import discord
from discord.abc import Snowflake
from discord.utils import MISSING

from .app_commands import (
    AppCommand,
    AppCommandError,
    BotMissingPermissions,
    CheckFailure,
    Command,
    CommandAlreadyRegistered,
    CommandInvokeError,
    CommandNotFound,
    CommandOnCooldown,
    CommandTree,
    ContextMenu,
    Group,
    NoPrivateMessage,
    TransformerError,
    UserFeedbackCheckFailure,
)
from .i18n import Translator
from .utils.chat_formatting import humanize_list, inline

import logging
import traceback
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Tuple, Union, Optional, Sequence

__all__ = ("RedTree",)

log = logging.getLogger("red")

_ = Translator(__name__, __file__)


class RedTree(CommandTree):
    """A container that holds application command information.

    Internally does not actually add commands to the tree unless they are
    enabled with ``[p]slash enable``, to support Red's modularity.
    See ``discord.app_commands.CommandTree`` for more information.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Same structure as superclass
        self._disabled_global_commands: Dict[str, Union[Command, Group]] = {}
        self._disabled_context_menus: Dict[Tuple[str, Optional[int], int], ContextMenu] = {}

    def add_command(
        self,
        command: Union[Command, ContextMenu, Group],
        /,
        *args,
        guild: Optional[Snowflake] = MISSING,
        guilds: Sequence[Snowflake] = MISSING,
        override: bool = False,
        **kwargs,
    ) -> None:
        """Adds an application command to the tree.

        Commands will be internally stored until enabled by ``[p]slash enable``.
        """
        # Allow guild specific commands to bypass the internals for development
        if (
            guild is not MISSING
            or guilds is not MISSING
            or command.extras.get("red_force_enable", False)
        ):
            return super().add_command(
                command, *args, guild=guild, guilds=guilds, override=override, **kwargs
            )

        if isinstance(command, ContextMenu):
            name = command.name
            type = command.type.value
            key = (name, None, type)

            # Handle cases where the command already is in the tree
            if not override and key in self._disabled_context_menus:
                raise CommandAlreadyRegistered(name, None)
            if key in self._context_menus:
                if not override:
                    raise CommandAlreadyRegistered(name, None)
                del self._context_menus[key]

            self._disabled_context_menus[key] = command
            return

        if not isinstance(command, (Command, Group)):
            raise TypeError(
                f"Expected an application command, received {command.__class__.__name__} instead"
            )

        root = command.root_parent or command
        name = root.name

        # Handle cases where the command already is in the tree
        if not override and name in self._disabled_global_commands:
            raise CommandAlreadyRegistered(name, None)
        if name in self._global_commands:
            if not override:
                raise CommandAlreadyRegistered(name, None)
            del self._global_commands[name]

        self._disabled_global_commands[name] = root

    def remove_command(
        self,
        command: str,
        /,
        *args,
        guild: Optional[Snowflake] = None,
        type: discord.AppCommandType = discord.AppCommandType.chat_input,
        **kwargs,
    ) -> Optional[Union[Command, ContextMenu, Group]]:
        """Removes an application command from this tree."""
        if guild is not None:
            return super().remove_command(command, *args, guild=guild, type=type, **kwargs)
        if type is discord.AppCommandType.chat_input:
            return self._disabled_global_commands.pop(command, None) or super().remove_command(
                command, *args, guild=guild, type=type, **kwargs
            )
        elif type in (discord.AppCommandType.user, discord.AppCommandType.message):
            key = (command, None, type.value)
            return self._disabled_context_menus.pop(key, None) or super().remove_command(
                command, *args, guild=guild, type=type, **kwargs
            )

    def clear_commands(
        self,
        *args,
        guild: Optional[Snowflake],
        type: Optional[discord.AppCommandType] = None,
        **kwargs,
    ) -> None:
        """Clears all application commands from the tree."""
        if guild is not None:
            return super().clear_commands(*args, guild=guild, type=type, **kwargs)

        if type is None or type is discord.AppCommandType.chat_input:
            self._global_commands.clear()
            self._disabled_global_commands.clear()

        if type is None:
            self._disabled_context_menus.clear()
        else:
            self._disabled_context_menus = {
                (name, _guild_id, value): cmd
                for (name, _guild_id, value), cmd in self._disabled_context_menus.items()
                if value != type.value
            }
        return super().clear_commands(*args, guild=guild, type=type, **kwargs)

    async def sync(self, *args, guild: Optional[Snowflake] = None, **kwargs) -> List[AppCommand]:
        """Wrapper to store command IDs when commands are synced."""
        commands = await super().sync(*args, guild=guild, **kwargs)
        if guild:
            return commands
        async with self.client._config.all() as cfg:
            for command in commands:
                if command.type is discord.AppCommandType.chat_input:
                    cfg["enabled_slash_commands"][command.name] = command.id
                elif command.type is discord.AppCommandType.message:
                    cfg["enabled_message_commands"][command.name] = command.id
                elif command.type is discord.AppCommandType.user:
                    cfg["enabled_user_commands"][command.name] = command.id
        return commands

    async def red_check_enabled(self) -> None:
        """Restructures the commands in this tree, enabling commands that are enabled and disabling commands that are disabled.

        After running this function, the tree will be populated with enabled commands only.
        If commands are manually added to the tree outside of the standard cog loading process, this must be run
        for them to be usable.
        """
        enabled_commands = await self.client.list_enabled_app_commands()

        to_add_commands = set()
        to_add_context = set()
        to_remove_commands = set()
        to_remove_context = set()

        # Add commands
        for command in enabled_commands["slash"]:
            if command in self._disabled_global_commands:
                to_add_commands.add(command)

        # Add context
        for command in enabled_commands["message"]:
            key = (command, None, discord.AppCommandType.message.value)
            if key in self._disabled_context_menus:
                to_add_context.add(key)
        for command in enabled_commands["user"]:
            key = (command, None, discord.AppCommandType.user.value)
            if key in self._disabled_context_menus:
                to_add_context.add(key)

        # Add force enabled commands
        for command, command_obj in self._disabled_global_commands.items():
            if command_obj.extras.get("red_force_enable", False):
                to_add_commands.add(command)

        # Add force enabled context
        for key, command_obj in self._disabled_context_menus.items():
            if command_obj.extras.get("red_force_enable", False):
                to_add_context.add(key)

        # Remove commands
        for command, command_obj in self._global_commands.items():
            if command not in enabled_commands["slash"] and not command_obj.extras.get(
                "red_force_enable", False
            ):
                to_remove_commands.add((command, discord.AppCommandType.chat_input))

        # Remove context
        for key, command_obj in self._context_menus.items():
            command, guild_id, command_type = key
            if guild_id is not None:
                continue
            if (
                discord.AppCommandType(command_type) is discord.AppCommandType.message
                and command not in enabled_commands["message"]
                and not command_obj.extras.get("red_force_enable", False)
            ):
                to_remove_context.add((command, discord.AppCommandType.message))
            elif (
                discord.AppCommandType(command_type) is discord.AppCommandType.user
                and command not in enabled_commands["user"]
                and not command_obj.extras.get("red_force_enable", False)
            ):
                to_remove_context.add((command, discord.AppCommandType.user))

        # Actually add/remove
        for command in to_add_commands:
            super().add_command(self._disabled_global_commands[command])
            del self._disabled_global_commands[command]
        for key in to_add_context:
            super().add_command(self._disabled_context_menus[key])
            del self._disabled_context_menus[key]
        for command, type in to_remove_commands:
            com = super().remove_command(command, type=type)
            self._disabled_global_commands[command] = com
        for command, type in to_remove_context:
            com = super().remove_command(command, type=type)
            self._disabled_context_menus[(command, None, type.value)] = com

    @staticmethod
    async def _send_from_interaction(interaction, *args, **kwargs):
        """Util for safely sending a message from an interaction."""
        if interaction.response.is_done():
            if interaction.is_expired():
                return await interaction.channel.send(*args, **kwargs)
            delete_after = kwargs.pop("delete_after", None)
            kwargs["wait"] = True
            msg = await interaction.followup.send(*args, ephemeral=True, **kwargs)
            if delete_after is not None:
                await msg.delete(delay=delete_after)
            return msg
        return await interaction.response.send_message(*args, ephemeral=True, **kwargs)

    @staticmethod
    def _is_submodule(parent: str, child: str):
        return parent == child or child.startswith(parent + ".")

    async def on_error(
        self, interaction: discord.Interaction, error: AppCommandError, /, *args, **kwargs
    ) -> None:
        """Fallback error handler for app commands."""
        if isinstance(error, CommandNotFound):
            await self._send_from_interaction(interaction, _("Command not found."))
            log.warning(
                f"Application command {error.name} could not be resolved. "
                "It may be from a cog that was updated or unloaded. "
                "Consider running [p]slash sync to resolve this issue."
            )
        elif isinstance(error, CommandInvokeError):
            log.exception(
                "Exception in command '{}'".format(error.command.qualified_name),
                exc_info=error.original,
            )
            exception_log = "Exception in command '{}'\n" "".format(error.command.qualified_name)
            exception_log += "".join(
                traceback.format_exception(type(error), error, error.__traceback__)
            )
            interaction.client._last_exception = exception_log

            message = await interaction.client._config.invoke_error_msg()
            if not message:
                if interaction.user.id in interaction.client.owner_ids:
                    message = inline(
                        _("Error in command '{command}'. Check your console or logs for details.")
                    )
                else:
                    message = inline(_("Error in command '{command}'."))
            await self._send_from_interaction(
                interaction, message.replace("{command}", error.command.qualified_name)
            )
        elif isinstance(error, TransformerError):
            if error.__cause__:
                log.exception("Error in an app command transformer.", exc_info=error.__cause__)
            await self._send_from_interaction(interaction, str(error))
        elif isinstance(error, BotMissingPermissions):
            formatted = [
                '"' + perm.replace("_", " ").title() + '"' for perm in error.missing_permissions
            ]
            formatted = humanize_list(formatted).replace("Guild", "Server")
            if len(error.missing_permissions) == 1:
                msg = _("I require the {permission} permission to execute that command.").format(
                    permission=formatted
                )
            else:
                msg = _("I require {permission_list} permissions to execute that command.").format(
                    permission_list=formatted
                )
            await self._send_from_interaction(interaction, msg)
        elif isinstance(error, NoPrivateMessage):
            # Seems to be only called normally by the has_role check
            await self._send_from_interaction(
                interaction, _("That command is not available in DMs.")
            )
        elif isinstance(error, CommandOnCooldown):
            relative_time = discord.utils.format_dt(
                datetime.now(timezone.utc) + timedelta(seconds=error.retry_after), "R"
            )
            msg = _("This command is on cooldown. Try again {relative_time}.").format(
                relative_time=relative_time
            )
            await self._send_from_interaction(interaction, msg, delete_after=error.retry_after)
        elif isinstance(error, UserFeedbackCheckFailure):
            if error.message:
                await self._send_from_interaction(interaction, error.message)
        elif isinstance(error, CheckFailure):
            await self._send_from_interaction(
                interaction, _("You are not permitted to use this command.")
            )
        else:
            log.exception(type(error).__name__, exc_info=error)

    async def _send_interaction_check_failure(
        self, interaction: discord.Interaction, message: str
    ):
        """Handles responding to interaction check failures.
        Mainly used for when an interaction is an autocomplete and
        providing the message in the autocomplete response.
        """
        if interaction.type is discord.InteractionType.autocomplete:
            await interaction.response.autocomplete(
                [discord.app_commands.Choice(name=message[:80], value="None")]
            )
            return
        await interaction.response.send_message(message, ephemeral=True)

    async def interaction_check(self, interaction: discord.Interaction):
        """Global checks for app commands."""
        if interaction.user.bot:
            return False

        if interaction.guild:
            if not (await self.client.ignored_channel_or_guild(interaction)):
                await self._send_interaction_check_failure(
                    interaction, _("This channel or server is ignored.")
                )
                return False

        if not (await self.client.allowed_by_whitelist_blacklist(interaction.user)):
            await self._send_interaction_check_failure(
                interaction,
                _("You are not permitted to use commands because of an allowlist or blocklist."),
            )
            return False

        return True

    # DEP-WARN
    def _remove_with_module(self, name: str, *args, **kwargs) -> None:
        """Handles cases where a module raises an exception in the loading process, but added commands to the tree.

        Duplication of the logic in the super class, but for the containers used by this subclass.
        """
        super()._remove_with_module(name, *args, **kwargs)
        remove = []
        for key, cmd in self._disabled_context_menus.items():
            if cmd.module is not None and self._is_submodule(name, cmd.module):
                remove.append(key)

        for key in remove:
            del self._disabled_context_menus[key]

        remove = []
        for key, cmd in self._disabled_global_commands.items():
            if cmd.module is not None and self._is_submodule(name, cmd.module):
                remove.append(key)

        for key in remove:
            del self._disabled_global_commands[key]
