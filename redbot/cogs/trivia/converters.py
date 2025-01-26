import math

from redbot.core import commands
from redbot.core.i18n import Translator

__all__ = ("finite_float",)

_ = Translator("Trivia", __file__)


MAX_VALUE = 2**63 - 1


def finite_float(arg: str) -> float:
    try:
        ret = float(arg)
    except ValueError:
        raise commands.BadArgument(_("`{arg}` is not a number.").format(arg=arg))
    if not math.isfinite(ret):
        raise commands.BadArgument(_("`{arg}` is not a finite number.").format(arg=ret))
    return ret
