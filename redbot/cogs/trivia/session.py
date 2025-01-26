"""Module to manage trivia sessions."""
import asyncio
import time
import random
from collections import Counter
import discord
from redbot.core import bank, errors
from redbot.core.i18n import Translator
from redbot.core.utils.chat_formatting import box, bold, humanize_list, humanize_number
from redbot.core.utils.common_filters import normalize_smartquotes
from .converters import MAX_VALUE
from .log import LOG

__all__ = ["TriviaSession"]

T_ = Translator("TriviaSession", __file__)


_ = lambda s: s
_REVEAL_MESSAGES = (
    _("I know this one! {answer}!"),
    _("Easy: {answer}."),
    _("Oh really? It's {answer} of course."),
)

SPOILER_REVEAL_MESSAGES = (
    _("I know this one! ||{answer}!||"),
    _("Easy: ||{answer}.||"),
    _("Oh really? It's ||{answer}|| of course."),
)

_FAIL_MESSAGES = (
    _("To the next one I guess..."),
    _("Moving on..."),
    _("I'm sure you'll know the answer of the next one."),
    _("\N{PENSIVE FACE} Next one."),
)
_ = T_


class TriviaSession:
    """Class to run a session of trivia with the user.

    To run the trivia session immediately, use `TriviaSession.start` instead of
    instantiating directly.

    Attributes
    ----------
    ctx : `commands.Context`
        Context object from which this session will be run.
        This object assumes the session was started in `ctx.channel`
        by `ctx.author`.
    question_list : `dict`
        A list of tuples mapping questions (`str`) to answers (`list` of
        `str`).
    settings : `dict`
        Settings for the trivia session, with values for the following:
         - ``max_score`` (`int`)
         - ``delay`` (`float`)
         - ``timeout`` (`float`)
         - ``reveal_answer`` (`bool`)
         - ``bot_plays`` (`bool`)
         - ``allow_override`` (`bool`)
         - ``payout_multiplier`` (`float`)
         - ``use_spoilers`` (`bool`)
    scores : `collections.Counter`
        A counter with the players as keys, and their scores as values. The
        players are of type `discord.Member`.
    count : `int`
        The number of questions which have been asked.

    """

    def __init__(self, ctx, question_list: dict, settings: dict):
        self.ctx = ctx
        list_ = list(question_list.items())
        random.shuffle(list_)
        self.question_list = list_
        self.settings = settings
        self.scores = Counter()
        self.count = 0
        self._last_response = time.time()
        self._task = None

    @classmethod
    def start(cls, ctx, question_list, settings):
        """Create and start a trivia session.

        This allows the session to manage the running and cancellation of its
        own tasks.

        Parameters
        ----------
        ctx : `commands.Context`
            Same as `TriviaSession.ctx`
        question_list : `dict`
            Same as `TriviaSession.question_list`
        settings : `dict`
            Same as `TriviaSession.settings`

        Returns
        -------
        TriviaSession
            The new trivia session being run.

        """
        session = cls(ctx, question_list, settings)
        session._task = asyncio.create_task(session.run())
        session._task.add_done_callback(session._error_handler)
        return session

    def _error_handler(self, fut):
        """Catches errors in the session task."""
        try:
            fut.result()
        except asyncio.CancelledError:
            pass
        except (discord.NotFound, discord.Forbidden):
            self.stop()
        except Exception as exc:
            LOG.error("A trivia session has encountered an error.\n", exc_info=exc)
            msg = _("An unexpected error occurred in the trivia session.")
            if self.ctx.author.id in self.ctx.bot.owner_ids:
                msg = _(
                    "An unexpected error occurred in the trivia session.\nCheck your console or logs for details."
                )
            asyncio.create_task(self.ctx.send(msg))
            self.stop()

    async def run(self):
        """Run the trivia session.

        In order for the trivia session to be stopped correctly, this should
        only be called internally by `TriviaSession.start`.
        """
        await self._send_startup_msg()
        max_score = self.settings["max_score"]
        delay = self.settings["delay"]
        timeout = self.settings["timeout"]
        for question, answers in self._iter_questions():
            async with self.ctx.typing():
                await asyncio.sleep(3)
            self.count += 1
            msg = bold(_("Question number {num}!").format(num=self.count)) + "\n\n" + question
            await self.ctx.send(msg)
            continue_ = await self.wait_for_answer(answers, delay, timeout)
            if continue_ is False:
                break
            if any(score >= max_score for score in self.scores.values()):
                await self.end_game()
                break
        else:
            await self.ctx.send(_("There are no more questions!"))
            await self.end_game()

    async def _send_startup_msg(self):
        list_names = []
        for idx, tup in enumerate(self.settings["lists"].items()):
            name, author = tup
            if author:
                title = _("{trivia_list} (by {author})").format(trivia_list=name, author=author)
            else:
                title = name
            list_names.append(title)
        await self.ctx.send(
            _("Starting Trivia: {list_names}").format(list_names=humanize_list(list_names))
        )

    def _iter_questions(self):
        """Iterate over questions and answers for this session.

        Yields
        ------
        `tuple`
            A tuple containing the question (`str`) and the answers (`tuple` of
            `str`).

        """
        for question, answers in self.question_list:
            answers = _parse_answers(answers)
            yield question, answers

    async def wait_for_answer(self, answers, delay: float, timeout: float):
        """Wait for a correct answer, and then respond.

        Scores are also updated in this method.

        Returns False if waiting was cancelled; this is usually due to the
        session being forcibly stopped.

        Parameters
        ----------
        answers : `iterable` of `str`
            A list of valid answers to the current question.
        delay : float
            How long users have to respond (in seconds).
        timeout : float
            How long before the session ends due to no responses (in seconds).

        Returns
        -------
        bool
            :code:`True` if the session wasn't interrupted.

        """
        try:
            message = await self.ctx.bot.wait_for(
                "message", check=self.check_answer(answers), timeout=delay
            )
        except asyncio.TimeoutError:
            if time.time() - self._last_response >= timeout:
                await self.ctx.send(_("Guys...? Well, I guess I'll stop then."))
                self.stop()
                return False
            if self.settings["reveal_answer"]:
                if self.settings["use_spoilers"]:
                    reply = T_(random.choice(SPOILER_REVEAL_MESSAGES)).format(answer=answers[0])
                else:
                    reply = T_(random.choice(_REVEAL_MESSAGES)).format(answer=answers[0])
            else:
                reply = T_(random.choice(_FAIL_MESSAGES))
            if self.settings["bot_plays"]:
                reply += _(" **+1** for me!")
                self.scores[self.ctx.guild.me] += 1
            await self.ctx.send(reply)
        else:
            self.scores[message.author] += 1
            reply = _("You got it {user}! **+1** to you!").format(user=message.author.display_name)
            await self.ctx.send(reply)
        return True

    def check_answer(self, answers):
        """Get a predicate to check for correct answers.

        The returned predicate takes a message as its only parameter,
        and returns ``True`` if the message contains any of the
        given answers.

        Parameters
        ----------
        answers : `iterable` of `str`
            The answers which the predicate must check for.

        Returns
        -------
        function
            The message predicate.

        """
        answers = tuple(s.lower() for s in answers)

        def _pred(message: discord.Message):
            early_exit = (
                message.channel.id != self.ctx.channel.id or message.author == self.ctx.guild.me
            )
            if early_exit:
                return False

            self._last_response = time.time()
            guess = message.content.lower()
            guess = normalize_smartquotes(guess)
            for answer in answers:
                if " " in answer and answer in guess:
                    # Exact matching, issue #331
                    return True
                elif any(word == answer for word in guess.split(" ")):
                    return True
            return False

        return _pred

    async def end_game(self):
        """End the trivia session and display scores."""
        if self.scores:
            await self.send_table()
        multiplier = self.settings["payout_multiplier"]
        if multiplier > 0:
            await self.pay_winners(multiplier)
        self.stop()

    async def send_table(self):
        """Send a table of scores to the session's channel."""
        table = "Results:\n\n"
        for user, score in self.scores.most_common():
            table += "+ {}\t{}\n".format(user, score)
        await self.ctx.send(box(table, lang="markdown"))

    def stop(self):
        """Stop the trivia session, without showing scores."""
        self.ctx.bot.dispatch("trivia_end", self)

    def force_stop(self):
        """Cancel whichever tasks this session is running."""
        self._task.cancel()
        channel = self.ctx.channel
        LOG.debug("Force stopping trivia session; #%s in %s", channel, channel.guild.id)

    async def pay_winners(self, multiplier: float):
        """Pay the winner(s) of this trivia session.

        Payout only occurs if there are at least 3 human contestants.
        If a tie occurs the payout is split evenly among the winners.

        Parameters
        ----------
        multiplier : float
            The coefficient of the winning score, used to determine the amount
            paid.

        """
        if not self.scores:
            return
        top_score = self.scores.most_common(1)[0][1]
        winners = []
        num_humans = 0
        for player, score in self.scores.items():
            if not player.bot:
                if score == top_score:
                    winners.append(player)
                num_humans += 1
        if not winners or num_humans < 3:
            return
        payout = int(top_score * multiplier / len(winners))
        payout = MAX_VALUE if payout > MAX_VALUE else payout
        if payout <= 0:
            return
        for winner in winners:
            LOG.debug("Paying trivia winner: %d credits --> %s", payout, winner)
            try:
                await bank.deposit_credits(winner, payout)
            except errors.BalanceTooHigh as e:
                await bank.set_balance(winner, e.max_balance)
        if len(winners) > 1:
            msg = _(
                "Congratulations {users}! You have each received {num} {currency} for winning!"
            ).format(
                users=humanize_list([bold(winner.display_name) for winner in winners]),
                num=payout,
                currency=await bank.get_currency_name(self.ctx.guild),
            )
        else:
            msg = _(
                "Congratulations {user}! You have received {num} {currency} for winning!"
            ).format(
                user=bold(winners[0].display_name),
                num=payout,
                currency=await bank.get_currency_name(self.ctx.guild),
            )
        await self.ctx.send(msg)


def _parse_answers(answers):
    """Parse the raw answers to readable strings.

    The reason this exists is because of YAML's ambiguous syntax. For example,
    if the answer to a question in YAML is ``yes``, YAML will load it as the
    boolean value ``True``, which is not necessarily the desired answer. This
    function aims to undo that for bools, and possibly for numbers in the
    future too.

    Parameters
    ----------
    answers : `iterable` of `str`
        The raw answers loaded from YAML.

    Returns
    -------
    `tuple` of `str`
        The answers in readable/ guessable strings.

    """
    ret = []
    for answer in answers:
        if isinstance(answer, bool):
            if answer is True:
                ret.extend(["True", "Yes", "On"])
            else:
                ret.extend(["False", "No", "Off"])
        else:
            ret.append(str(answer))
    # Uniquify list
    seen = set()
    return tuple(x for x in ret if not (x in seen or seen.add(x)))
