"""Errors module for the app_commands package."""
from discord import app_commands


class UserFeedbackCheckFailure(app_commands.CheckFailure):
    """A version of CheckFailure responding with a custom error message."""

    def __init__(self, message=None, *args):
        self.message = message
        super().__init__(message, *args)
