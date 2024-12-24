from red_commons.logging import getLogger

from ..cog_utils import CompositeMetaClass
from .lavalink import LavalinkTasks
from .player import PlayerTasks
from .startup import StartUpTasks

log = getLogger("red.cogs.Audio.cog.Tasks")


class Tasks(LavalinkTasks, PlayerTasks, StartUpTasks, metaclass=CompositeMetaClass):
    """Class joining all task subclasses"""
