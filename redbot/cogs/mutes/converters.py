from __future__ import annotations

import logging
import re
from typing import Optional, TypedDict
from datetime import timedelta, datetime, timezone
from typing_extensions import Annotated

from discord.ext.commands.converter import Converter
from redbot.core import commands
from redbot.core import i18n
from redbot.core.commands.converter import TIME_RE

_ = i18n.Translator("Mutes", __file__)
log = logging.getLogger("red.cogs.mutes")

TIME_SPLIT = re.compile(r"t(?:ime\s?)?=\s*")


def _edgematch(pattern: re.Pattern[str], argument: str) -> Optional[re.Match[str]]:
    """Internal utility to match at either end of the argument string"""
    # precondition: pattern does not end in $
    # precondition: argument does not end in whitespace
    return pattern.match(argument) or re.search(
        pattern.pattern + "$", argument, flags=pattern.flags
    )


class _MuteTime(TypedDict, total=False):
    duration: timedelta
    reason: str
    until: datetime


class _MuteTimeConverter(Converter):
    """
    This will parse my defined multi response pattern and provide usable formats
    to be used in multiple responses
    """

    async def convert(self, ctx: commands.Context, argument: str) -> _MuteTime:
        time_split = TIME_SPLIT.search(argument)
        result: _MuteTime = {}
        if time_split:
            maybe_time = argument[time_split.end() :]
            strategy = re.match
        else:
            maybe_time = argument
            strategy = _edgematch

        match = strategy(TIME_RE, maybe_time)
        if match:
            time_data = {k: int(v) for k, v in match.groupdict().items() if v is not None}
            for k in time_data:
                if k in ("years", "months"):
                    raise commands.BadArgument(
                        _("`{unit}` is not a valid unit of time for this command").format(unit=k)
                    )
            try:
                result["duration"] = duration = timedelta(**time_data)
                result["until"] = ctx.message.created_at + duration
                # Catch if using the timedelta with the current date will also result in an Overflow error
            except OverflowError:
                raise commands.BadArgument(
                    _("The time provided is too long; use a more reasonable time.")
                )
            if duration <= timedelta(seconds=0):
                raise commands.BadArgument(_("The time provided must not be in the past."))
            if time_split:
                start, end = time_split.span()
                end += match.end()
            else:
                start, end = match.span()
            argument = argument[:start] + argument[end:]
        result["reason"] = argument.strip()
        return result


MuteTime = Annotated[_MuteTime, _MuteTimeConverter]
