from redbot.core.commands import BadArgument, Context, Converter
from redbot.core.i18n import Translator

_ = Translator("Cleanup", __file__)

SNOWFLAKE_THRESHOLD = 2**63


class RawMessageIds(Converter):
    async def convert(self, ctx: Context, argument: str) -> int:
        if argument.isnumeric() and len(argument) >= 17 and int(argument) < SNOWFLAKE_THRESHOLD:
            return int(argument)

        raise BadArgument(_("{} doesn't look like a valid message ID.").format(argument))
