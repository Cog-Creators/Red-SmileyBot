"""
The original implementation of this cog was heavily based on
RoboDanny's REPL cog which can be found here:
https://github.com/Rapptz/RoboDanny/blob/f13e1c9a6a7205e50de6f91fa5326fc7113332d3/cogs/repl.py

Copyright (c) 2017-present Cog Creators
Copyright (c) 2016-2017 Rapptz

The original copy was distributed under MIT License and this derivative work
is distributed under GNU GPL Version 3.
"""

from __future__ import annotations

import ast
import asyncio
import aiohttp
import inspect
import io
import textwrap
import traceback
import types
import re
import sys
from copy import copy
from typing import Any, Awaitable, Dict, Iterator, List, Literal, Tuple, Type, TypeVar, Union
from types import CodeType, TracebackType

import discord

from . import commands
from .commands import NoParseOptional as Optional
from .i18n import Translator, cog_i18n
from .utils import chat_formatting
from .utils.chat_formatting import pagify
from .utils.predicates import MessagePredicate

_ = Translator("Dev", __file__)

# we want to match either:
# - "```lang\n"
# - or "```" and potentially also strip a single "\n" if it follows it immediately
START_CODE_BLOCK_RE = re.compile(r"^((```[\w.+\-]+\n+(?!```))|(```\n*))")

T = TypeVar("T")


def get_pages(msg: str) -> Iterator[str]:
    """Pagify the given message for output to the user."""
    return pagify(msg, delims=["\n", " "], priority=True, shorten_by=10)


def sanitize_output(ctx: commands.Context, to_sanitize: str) -> str:
    """Hides the bot's token from a string."""
    token = ctx.bot.http.token
    if token:
        return re.sub(re.escape(token), "[EXPUNGED]", to_sanitize, re.I)
    return to_sanitize


def async_compile(source: str, filename: str, mode: Literal["eval", "exec"]) -> CodeType:
    return compile(
        source, filename, mode, flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT, optimize=0, dont_inherit=True
    )


async def maybe_await(coro: Union[T, Awaitable[T], Awaitable[Awaitable[T]]]) -> T:
    for i in range(2):
        if inspect.isawaitable(coro):
            coro = await coro
        else:
            break
    return coro  # type: ignore


def cleanup_code(content: str) -> str:
    """Automatically removes code blocks from the code."""
    # remove ```py\n```
    if content.startswith("```") and content.endswith("```"):
        return START_CODE_BLOCK_RE.sub("", content)[:-3].rstrip("\n")

    # remove `foo`
    return content.strip("` \n")


class SourceCache:
    MAX_SIZE = 1000

    def __init__(self) -> None:
        # estimated to take less than 100 kB
        self._data: Dict[str, Tuple[str, int]] = {}
        # this just keeps going up until the bot is restarted, shouldn't really be an issue
        self._next_index = 0

    def take_next_index(self) -> int:
        next_index = self._next_index
        self._next_index += 1
        return next_index

    def __getitem__(self, key: str) -> Tuple[List[str], int]:
        value = self._data.pop(key)  # pop to put it at the end as most recent
        self._data[key] = value
        # To mimic linecache module's behavior,
        # all lines (including the last one) should end with \n.
        source_lines = [f"{line}\n" for line in value[0].splitlines()]
        # Note: while it might seem like a waste of time to always calculate the list of source lines,
        # this is a necessary memory optimization. If all of the data in `self._data` were list,
        # it could theoretically take up to 1000x as much memory.
        return source_lines, value[1]

    def __setitem__(self, key: str, value: Tuple[str, int]) -> None:
        self._data.pop(key, None)
        self._data[key] = value
        if len(self._data) > self.MAX_SIZE:
            del self._data[next(iter(self._data))]


class DevOutput:
    def __init__(
        self,
        ctx: commands.Context,
        *,
        source_cache: SourceCache,
        filename: str,
        source: str,
        env: Dict[str, Any],
    ) -> None:
        self.ctx = ctx
        self.source_cache = source_cache
        self.filename = filename
        self.source_line_offset = 0
        #: raw source - as received from the command after stripping the code block
        self.raw_source = source
        self.set_compilable_source(source)
        self.env = env
        self.always_include_result = False
        self._stream = io.StringIO()
        self.formatted_exc = ""
        self.result: Any = None
        self._old_streams = []

    @property
    def compilable_source(self) -> str:
        """Source string that we pass to async_compile()."""
        return self._compilable_source

    def set_compilable_source(self, compilable_source: str, *, line_offset: int = 0) -> None:
        self._compilable_source = compilable_source
        self.source_line_offset = line_offset
        self.source_cache[self.filename] = (compilable_source, line_offset)

    def __str__(self) -> str:
        output = []
        printed = self._stream.getvalue()
        if printed:
            output.append(printed)
        if self.formatted_exc:
            output.append(self.formatted_exc)
        elif self.always_include_result or self.result is not None:
            try:
                output.append(str(self.result))
            except Exception as exc:
                output.append(self.format_exception(exc))
        return sanitize_output(self.ctx, "".join(output))

    async def send(self, *, tick: bool = True) -> None:
        await self.ctx.send_interactive(get_pages(str(self)), box_lang="py")
        if tick and not self.formatted_exc:
            await self.ctx.tick()

    def set_exception(self, exc: Exception, *, skip_frames: int = 1) -> None:
        self.formatted_exc = self.format_exception(exc, skip_frames=skip_frames)

    def __enter__(self) -> None:
        self._old_streams.append(sys.stdout)
        sys.stdout = self._stream

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_value: Optional[BaseException],
        exc_tb: Optional[TracebackType],
        /,
    ) -> None:
        sys.stdout = self._old_streams.pop()

    @classmethod
    async def from_debug(
        cls, ctx: commands.Context, *, source: str, source_cache: SourceCache, env: Dict[str, Any]
    ) -> DevOutput:
        output = cls(
            ctx,
            source=source,
            source_cache=source_cache,
            filename=f"<debug command - snippet #{source_cache.take_next_index()}>",
            env=env,
        )
        await output.run_debug()
        return output

    @classmethod
    async def from_eval(
        cls, ctx: commands.Context, *, source: str, source_cache: SourceCache, env: Dict[str, Any]
    ) -> DevOutput:
        output = cls(
            ctx,
            source=source,
            source_cache=source_cache,
            filename=f"<eval command - snippet #{source_cache.take_next_index()}>",
            env=env,
        )
        await output.run_eval()
        return output

    @classmethod
    async def from_repl(
        cls, ctx: commands.Context, *, source: str, source_cache: SourceCache, env: Dict[str, Any]
    ) -> DevOutput:
        output = cls(
            ctx,
            source=source,
            source_cache=source_cache,
            filename=f"<repl session - snippet #{source_cache.take_next_index()}>",
            env=env,
        )
        await output.run_repl()
        return output

    async def run_debug(self) -> None:
        self.always_include_result = True
        self.set_compilable_source(self.raw_source)
        try:
            compiled = self.async_compile_with_eval()
        except SyntaxError as exc:
            self.set_exception(exc, skip_frames=3)
            return

        try:
            self.result = await maybe_await(eval(compiled, self.env))
        except Exception as exc:
            self.set_exception(exc)

    async def run_eval(self) -> None:
        self.always_include_result = False
        self.set_compilable_source(
            "async def func():\n%s" % textwrap.indent(self.raw_source, "  "), line_offset=1
        )
        try:
            compiled = self.async_compile_with_exec()
            exec(compiled, self.env)
        except SyntaxError as exc:
            self.set_exception(exc, skip_frames=3)
            return

        func = self.env["func"]
        try:
            with self:
                self.result = await func()
        except Exception as exc:
            self.set_exception(exc)

    async def run_repl(self) -> None:
        self.always_include_result = False
        self.set_compilable_source(self.raw_source)
        executor = None
        if self.raw_source.count("\n") == 0:
            # single statement, potentially 'eval'
            try:
                code = self.async_compile_with_eval()
            except SyntaxError:
                pass
            else:
                executor = eval

        if executor is None:
            try:
                code = self.async_compile_with_exec()
            except SyntaxError as exc:
                self.set_exception(exc, skip_frames=3)
                return

        try:
            with self:
                if executor is None:
                    result = types.FunctionType(code, self.env)()
                else:
                    result = executor(code, self.env)
                self.result = await maybe_await(result)
        except Exception as exc:
            self.set_exception(exc)
        else:
            if self.result is not None:
                self.env["_"] = self.result

    def async_compile_with_exec(self) -> CodeType:
        return async_compile(self.compilable_source, self.filename, "exec")

    def async_compile_with_eval(self) -> CodeType:
        return async_compile(self.compilable_source, self.filename, "eval")

    def format_exception(self, exc: Exception, *, skip_frames: int = 1) -> str:
        """
        Format an exception to send to the user.

        This function makes a few alterations to the traceback:
        - First `skip_frames` frames are skipped so that we don't show the frames
          that are part of Red's code to the user
        - `FrameSummary` objects that we get from traceback module are updated
          with the string for the corresponding line of code as otherwise
          the generated traceback string wouldn't show user's code.
        - If `line_offset` is passed, this function subtracts it from line numbers
          in `FrameSummary` objects so that those numbers properly correspond to
          the code that was provided by the user. This is needed for cases where
          we wrap user's code in an async function before exec-ing it.
        """
        exc_type = type(exc)
        tb = exc.__traceback__
        for x in range(skip_frames):
            if tb is None:
                break
            tb = tb.tb_next

        filename = self.filename
        # sometimes SyntaxError.text is None, sometimes it isn't
        if issubclass(exc_type, SyntaxError) and exc.lineno is not None:
            try:
                source_lines, line_offset = self.source_cache[exc.filename]
            except KeyError:
                pass
            else:
                if exc.text is None:
                    try:
                        # line numbers are 1-based, the list indexes are 0-based
                        exc.text = source_lines[exc.lineno - 1]
                    except IndexError:
                        # the frame might be pointing at a different source code, ignore...
                        pass
                    else:
                        exc.lineno -= line_offset
                        if sys.version_info >= (3, 10) and exc.end_lineno is not None:
                            exc.end_lineno -= line_offset
                else:
                    exc.lineno -= line_offset
                    if sys.version_info >= (3, 10) and exc.end_lineno is not None:
                        exc.end_lineno -= line_offset

        top_traceback_exc = traceback.TracebackException(exc_type, exc, tb)
        py311_or_above = sys.version_info >= (3, 11)
        queue = [  # actually a stack but 'stack' is easy to confuse with actual traceback stack
            top_traceback_exc,
        ]
        seen = {id(top_traceback_exc)}
        while queue:
            traceback_exc = queue.pop()

            # handle exception groups; this uses getattr() to support `exceptiongroup` backport lib
            exceptions: List[traceback.TracebackException] = (
                getattr(traceback_exc, "exceptions", None) or []
            )
            # handle exception chaining
            if traceback_exc.__cause__ is not None:
                exceptions.append(traceback_exc.__cause__)
            if traceback_exc.__context__ is not None:
                exceptions.append(traceback_exc.__context__)
            for te in exceptions:
                if id(te) not in seen:
                    queue.append(te)
                    seen.add(id(te))

            stack_summary = traceback_exc.stack
            for idx, frame_summary in enumerate(stack_summary):
                try:
                    source_lines, line_offset = self.source_cache[frame_summary.filename]
                except KeyError:
                    continue
                lineno = frame_summary.lineno
                if lineno is None:
                    continue

                try:
                    # line numbers are 1-based, the list indexes are 0-based
                    line = source_lines[lineno - 1]
                except IndexError:
                    # the frame might be pointing at a different source code, ignore...
                    continue
                lineno -= line_offset
                # support for enhanced error locations in tracebacks
                if py311_or_above:
                    end_lineno = frame_summary.end_lineno
                    if end_lineno is not None:
                        end_lineno -= line_offset
                    frame_summary = traceback.FrameSummary(
                        frame_summary.filename,
                        lineno,
                        frame_summary.name,
                        line=line,
                        end_lineno=end_lineno,
                        colno=frame_summary.colno,
                        end_colno=frame_summary.end_colno,
                    )
                else:
                    frame_summary = traceback.FrameSummary(
                        frame_summary.filename, lineno, frame_summary.name, line=line
                    )
                stack_summary[idx] = frame_summary

        return "".join(top_traceback_exc.format())


@cog_i18n(_)
class Dev(commands.Cog):
    """Various development focused utilities."""

    async def red_delete_data_for_user(self, **kwargs: Any) -> None:
        """
        Because despite my best efforts to advise otherwise,
        people use ``--dev`` in production
        """
        return

    def __init__(self) -> None:
        super().__init__()
        self._last_result = None
        self.sessions = {}
        self.env_extensions = {}
        self.source_cache = SourceCache()

    def get_environment(self, ctx: commands.Context) -> dict:
        env = {
            "bot": ctx.bot,
            "ctx": ctx,
            "channel": ctx.channel,
            "author": ctx.author,
            "guild": ctx.guild,
            "message": ctx.message,
            "asyncio": asyncio,
            "aiohttp": aiohttp,
            "discord": discord,
            "commands": commands,
            "cf": chat_formatting,
            "_": self._last_result,
            "__name__": "__main__",
        }
        for name, value in self.env_extensions.items():
            try:
                env[name] = value(ctx)
            except Exception as exc:
                traceback.clear_frames(exc.__traceback__)
                env[name] = exc
        return env

    @commands.command()
    @commands.is_owner()
    async def debug(self, ctx: commands.Context, *, code: str) -> None:
        """Evaluate a statement of python code.

        The bot will always respond with the return value of the code.
        If the return value of the code is a coroutine, it will be awaited,
        and the result of that will be the bot's response.

        Note: Only one statement may be evaluated. Using certain restricted
        keywords, e.g. yield, will result in a syntax error. For multiple
        lines or asynchronous code, see [p]repl or [p]eval.

        Environment Variables:
            `ctx`      - the command invocation context
            `bot`      - the bot object
            `channel`  - the current channel object
            `author`   - the command author's member object
            `guild`    - the current guild object
            `message`  - the command's message object
            `_`        - the result of the last dev command
            `aiohttp`  - the aiohttp library
            `asyncio`  - the asyncio library
            `discord`  - the discord.py library
            `commands` - the redbot.core.commands module
            `cf`       - the redbot.core.utils.chat_formatting module
        """
        env = self.get_environment(ctx)
        source = cleanup_code(code)

        output = await DevOutput.from_debug(
            ctx, source=source, source_cache=self.source_cache, env=env
        )
        self._last_result = output.result
        await output.send()

    @commands.command(name="eval")
    @commands.is_owner()
    async def _eval(self, ctx: commands.Context, *, body: str) -> None:
        """Execute asynchronous code.

        This command wraps code into the body of an async function and then
        calls and awaits it. The bot will respond with anything printed to
        stdout, as well as the return value of the function.

        The code can be within a codeblock, inline code or neither, as long
        as they are not mixed and they are formatted correctly.

        Environment Variables:
            `ctx`      - the command invocation context
            `bot`      - the bot object
            `channel`  - the current channel object
            `author`   - the command author's member object
            `guild`    - the current guild object
            `message`  - the command's message object
            `_`        - the result of the last dev command
            `aiohttp`  - the aiohttp library
            `asyncio`  - the asyncio library
            `discord`  - the discord.py library
            `commands` - the redbot.core.commands module
            `cf`       - the redbot.core.utils.chat_formatting module
        """
        env = self.get_environment(ctx)
        source = cleanup_code(body)

        output = await DevOutput.from_eval(
            ctx, source=source, source_cache=self.source_cache, env=env
        )
        if output.result is not None:
            self._last_result = output.result
        await output.send()

    @commands.group(invoke_without_command=True)
    @commands.is_owner()
    async def repl(self, ctx: commands.Context) -> None:
        """Open an interactive REPL.

        The REPL will only recognise code as messages which start with a
        backtick. This includes codeblocks, and as such multiple lines can be
        evaluated.

        Use `exit()` or `quit` to exit the REPL session, prefixed with
        a backtick so they may be interpreted.

        Environment Variables:
            `ctx`      - the command invocation context
            `bot`      - the bot object
            `channel`  - the current channel object
            `author`   - the command author's member object
            `guild`    - the current guild object
            `message`  - the command's message object
            `_`        - the result of the last dev command
            `aiohttp`  - the aiohttp library
            `asyncio`  - the asyncio library
            `discord`  - the discord.py library
            `commands` - the redbot.core.commands module
            `cf`       - the redbot.core.utils.chat_formatting module
        """
        if ctx.channel.id in self.sessions:
            if self.sessions[ctx.channel.id]:
                await ctx.send(
                    _("Already running a REPL session in this channel. Exit it with `quit`.")
                )
            else:
                await ctx.send(
                    _(
                        "Already running a REPL session in this channel. Resume the REPL with `{}repl resume`."
                    ).format(ctx.prefix)
                )
            return

        env = self.get_environment(ctx)
        env["__builtins__"] = __builtins__
        env["_"] = None
        self.sessions[ctx.channel.id] = True
        await ctx.send(
            _(
                "Enter code to execute or evaluate. `exit()` or `quit` to exit. `{}repl pause` to pause."
            ).format(ctx.prefix)
        )

        while True:
            response = await ctx.bot.wait_for("message", check=MessagePredicate.regex(r"^`", ctx))
            env["message"] = response

            if not self.sessions[ctx.channel.id]:
                continue

            source = cleanup_code(response.content)

            if source in ("quit", "exit", "exit()"):
                await ctx.send(_("Exiting."))
                del self.sessions[ctx.channel.id]
                return

            output = await DevOutput.from_repl(
                ctx, source=source, source_cache=self.source_cache, env=env
            )
            try:
                await output.send(tick=False)
            except discord.Forbidden:
                pass
            except discord.HTTPException as exc:
                await ctx.send(_("Unexpected error: ") + str(exc))

    @repl.command(aliases=["resume"])
    async def pause(self, ctx: commands.Context, toggle: Optional[bool] = None) -> None:
        """Pauses/resumes the REPL running in the current channel."""
        if ctx.channel.id not in self.sessions:
            await ctx.send(_("There is no currently running REPL session in this channel."))
            return

        if toggle is None:
            toggle = not self.sessions[ctx.channel.id]
        self.sessions[ctx.channel.id] = toggle

        if toggle:
            await ctx.send(_("The REPL session in this channel has been resumed."))
        else:
            await ctx.send(_("The REPL session in this channel is now paused."))

    @commands.guild_only()
    @commands.command()
    @commands.is_owner()
    async def mock(self, ctx: commands.Context, user: discord.Member, *, command: str) -> None:
        """Mock another user invoking a command.

        The prefix must not be entered.
        """
        msg = copy(ctx.message)
        msg.author = user
        msg.content = ctx.prefix + command

        ctx.bot.dispatch("message", msg)

    @commands.guild_only()
    @commands.command(name="mockmsg")
    @commands.is_owner()
    async def mock_msg(
        self, ctx: commands.Context, user: discord.Member, *, content: str = ""
    ) -> None:
        """Dispatch a message event as if it were sent by a different user.

        Current message is used as a base (including attachments, embeds, etc.),
        the content and author of the message are replaced with the given arguments.

        Note: If `content` isn't passed, the message needs to contain embeds, attachments,
        or anything else that makes the message non-empty.
        """
        msg = ctx.message
        if not content and not msg.embeds and not msg.attachments and not msg.stickers:
            await ctx.send_help()
            return
        msg = copy(msg)
        msg.author = user
        msg.content = content

        ctx.bot.dispatch("message", msg)

    @commands.command()
    @commands.is_owner()
    async def bypasscooldowns(self, ctx: commands.Context, toggle: Optional[bool] = None) -> None:
        """Give bot owners the ability to bypass cooldowns.

        Does not persist through restarts."""
        if toggle is None:
            toggle = not ctx.bot._bypass_cooldowns
        ctx.bot._bypass_cooldowns = toggle

        if toggle:
            await ctx.send(_("Bot owners will now bypass all commands with cooldowns."))
        else:
            await ctx.send(_("Bot owners will no longer bypass all commands with cooldowns."))
