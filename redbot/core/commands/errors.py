"""Errors module for the commands package."""
import inspect
import discord
from discord.ext import commands

__all__ = (
    "BotMissingPermissions",
    "UserFeedbackCheckFailure",
    "ArgParserFailure",
)


class BotMissingPermissions(commands.CheckFailure):
    """Raised if the bot is missing permissions required to run a command."""

    def __init__(self, missing: discord.Permissions, *args):
        self.missing: discord.Permissions = missing
        super().__init__(*args)


class UserFeedbackCheckFailure(commands.CheckFailure):
    """A version of CheckFailure which isn't suppressed."""

    def __init__(self, message=None, *args):
        self.message = message
        super().__init__(message, *args)


class ArgParserFailure(UserFeedbackCheckFailure):
    """Raised when parsing an argument fails."""

    def __init__(
        self, cmd: str, user_input: str, custom_help: str = None, ctx_send_help: bool = False
    ):
        self.cmd = cmd
        self.user_input = user_input
        self.send_cmd_help = ctx_send_help
        self.custom_help_msg = custom_help
        super().__init__()
