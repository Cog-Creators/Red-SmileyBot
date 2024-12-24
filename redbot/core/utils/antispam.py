from datetime import datetime, timedelta
from typing import Tuple, List
from collections import namedtuple

__all__ = ("AntiSpam",)

_AntiSpamInterval = namedtuple("_AntiSpamInterval", ["period", "frequency"])


class AntiSpam:
    """
    A class that can be used to count the number of events that happened
    within specified intervals. Later, it can be checked whether the specified
    maximum count for any of the specified intervals has been exceeded.

    Examples
    --------
    Tracking whether the number of reports sent by a user within a single guild is spammy:

    .. code-block:: python

        class MyCog(commands.Cog):
            INTERVALS = [
                # More than one report within last 5 seconds is considered spam.
                (datetime.timedelta(seconds=5), 1),
                # More than 3 reports within the last 5 minutes are considered spam.
                (datetime.timedelta(minutes=5), 3),
                # More than 10 reports within the last hour are considered spam.
                (datetime.timedelta(hours=1), 10),
                # More than 24 reports within a single day (last 24 hours) are considered spam.
                (datetime.timedelta(days=1), 24),
            ]

            def __init__(self, bot):
                self.bot = bot
                self.antispam = {}

            @commands.guild_only()
            @commands.command()
            async def report(self, ctx, content):
                # We want to track whether a single user within a single guild
                # sends a spammy number of reports.
                key = (ctx.guild.id, ctx.author.id)

                if key not in self.antispam:
                    # Create an instance of the AntiSpam class with given intervals.
                    self.antispam[key] = AntiSpam(self.INTERVALS)
                    # If you want to use the default intervals, you can use: AntiSpam([])

                # Check if the user sent too many reports recently.
                # The `AntiSpam.spammy` property is `True` if, for any interval,
                # the number of events that happened within that interval
                # exceeds the number specified for that interval.
                if self.antispam[key].spammy:
                    await ctx.send(
                        "You've sent too many reports recently, please try again later."
                    )
                    return

                # Make any other early-return checks.

                # Record the event.
                self.antispam[key].stamp()

                # Save the report.
                # self.config...

                # Send a message to the user.
                await ctx.send("Your report has been submitted.")

    Parameters
    ----------
    intervals : List[Tuple[datetime.timedelta, int]]
        A list of tuples in the format (timedelta, int),
        where the timedelta represents the length of the interval,
        and the int represents the maximum number of times something
        can happen within that interval.

        If an empty list is provided, the following defaults will be used:

        * 3 per 5 seconds
        * 5 per 1 minute
        * 10 per 1 hour
        * 24 per 1 day
    """

    # TODO : Decorator interface for command check using `spammy`
    # with insertion of the antispam element into context
    # for manual stamping on successful command completion

    default_intervals = [
        (timedelta(seconds=5), 3),
        (timedelta(minutes=1), 5),
        (timedelta(hours=1), 10),
        (timedelta(days=1), 24),
    ]

    def __init__(self, intervals: List[Tuple[timedelta, int]]):
        self.__event_timestamps = []
        _itvs = intervals or self.default_intervals
        self.__intervals = [_AntiSpamInterval(*x) for x in _itvs]
        self.__discard_after = max([x.period for x in self.__intervals])

    def __interval_check(self, interval: _AntiSpamInterval):
        return (
            len([t for t in self.__event_timestamps if (t + interval.period) > datetime.utcnow()])
            >= interval.frequency
        )

    @property
    def spammy(self):
        """
        Whether, for any interval, the number of events that happened
        within that interval exceeds the number specified for that interval.
        """
        return any(self.__interval_check(x) for x in self.__intervals)

    def stamp(self):
        """
        Mark an event timestamp against the list of antispam intervals happening right now.
        Use this after all checks have passed, and your action is taking place.

        The stamp will last until the corresponding interval duration
        has expired (set when this AntiSpam object was initiated).
        """
        self.__event_timestamps.append(datetime.utcnow())
        self.__event_timestamps = [
            t for t in self.__event_timestamps if t + self.__discard_after > datetime.utcnow()
        ]
