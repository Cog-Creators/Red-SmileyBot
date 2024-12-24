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

__all__ = (
    "bot_has_permissions",
    "cooldown",
    "dynamic_cooldown",
    "has_any_role",
    "has_role",
    "has_permissions",
)
