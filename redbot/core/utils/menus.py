# Original source of reaction-based menu idea from
# https://github.com/Lunar-Dust/Dusty-Cogs/blob/master/menu/menu.py
#
# Ported to Red V3 by Palm\_\_ (https://github.com/palmtree5)
import asyncio
import contextlib
import functools
from types import MappingProxyType
from typing import Callable, Dict, Iterable, List, Mapping, Optional, TypeVar, Union

import discord

from .. import commands
from .predicates import ReactionPredicate
from .views import SimpleMenu, _SimplePageSource

__all__ = (
    "menu",
    "next_page",
    "prev_page",
    "close_menu",
    "start_adding_reactions",
    "DEFAULT_CONTROLS",
)

_T = TypeVar("_T")
_PageList = TypeVar("_PageList", List[str], List[discord.Embed])
_ReactableEmoji = Union[str, discord.Emoji]
_ControlCallable = Callable[[commands.Context, _PageList, discord.Message, int, float, str], _T]

_active_menus: Dict[int, SimpleMenu] = {}


class _GenericButton(discord.ui.Button):
    def __init__(self, emoji: discord.PartialEmoji, func: _ControlCallable):
        super().__init__(emoji=emoji, style=discord.ButtonStyle.grey)
        self.func = func

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        ctx = self.view.ctx
        pages = self.view.source.entries
        controls = None
        message = self.view.message
        page = self.view.current_page
        timeout = self.view.timeout
        emoji = (
            str(self.emoji)
            if self.emoji.is_unicode_emoji()
            else (ctx.bot.get_emoji(self.emoji.id) or self.emoji)
        )
        user = self.view.author if not self.view._fallback_author_to_ctx else None
        if user is not None:
            await self.func(ctx, pages, controls, message, page, timeout, emoji, user=user)
        else:
            await self.func(ctx, pages, controls, message, page, timeout, emoji)


async def menu(
    ctx: commands.Context,
    pages: _PageList,
    controls: Optional[Mapping[str, _ControlCallable]] = None,
    message: Optional[discord.Message] = None,
    page: int = 0,
    timeout: float = 30.0,
    *,
    user: Optional[discord.User] = None,
) -> _T:
    """
    An emoji-based menu

    All functions for handling what a particular emoji does
    should be coroutines (i.e. :code:`async def`). Additionally,
    they must take all of the parameters of this function, in
    addition to a string representing the emoji reacted with.
    This parameter should be the 7th one, and none of the
    parameters in the handling functions are optional.

    .. warning::

        The ``user`` parameter is considered `provisional <developer-guarantees-exclusions>`.
        If no issues arise, we plan on including it under developer guarantees
        in the first release made after 2024-05-24.

    .. warning::

        If you're using the ``user`` param, you need to pass it
        as a keyword-only argument, and set :obj:`None` as the
        default in your function.

    Examples
    --------

    Simple menu using default controls::

        from redbot.core.utils.menus import menu

        pages = ["Hello", "Hi", "Bonjour", "Salut"]
        await menu(ctx, pages)

    Menu with a custom control performing an action (deleting an item from pages list)::

        from redbot.core.utils import menus

        items = ["Apple", "Banana", "Cucumber", "Dragonfruit"]

        def generate_pages():
            return [f"{fruit} is an awesome fruit!" for fruit in items]

        async def delete_item_action(ctx, pages, controls, message, page, timeout, emoji):
            fruit = items.pop(page)  # lookup and remove corresponding fruit name
            await ctx.send(f"I guess you don't like {fruit}, huh? Deleting...")
            pages = generate_pages()
            if not pages:
                return await menus.close_menu(ctx, pages, controls, message, page, timeout)
            page = min(page, len(pages) - 1)
            return await menus.menu(ctx, pages, controls, message, page, timeout)

        pages = generate_pages()
        controls = {**menus.DEFAULT_CONTROLS, "\\N{NO ENTRY SIGN}": delete_item_action}
        await menus.menu(ctx, pages, controls)

    Menu with custom controls that output a result (confirmation prompt)::

        from redbot.core.utils.menus import menu

        async def control_yes(*args, **kwargs):
            return True

        async def control_no(*args, **kwargs):
            return False

        msg = "Do you wish to continue?"
        controls = {
            "\\N{WHITE HEAVY CHECK MARK}": control_yes,
            "\\N{CROSS MARK}": control_no,
        }
        reply = await menu(ctx, [msg], controls)
        if reply:
            await ctx.send("Continuing...")
        else:
            await ctx.send("Okay, I'm not going to perform the requested action.")

    Parameters
    ----------
    ctx: commands.Context
        The command context
    pages: Union[List[str], List[discord.Embed]]
        The pages of the menu.
        All pages need to be of the same type (either `str` or `discord.Embed`).
    controls: Optional[Mapping[str, Callable]]
        A mapping of emoji to the function which handles the action for the
        emoji. The signature of the function should be the same as of this function
        and should additionally accept an ``emoji`` parameter of type `str`.
        If not passed, `DEFAULT_CONTROLS` is used *or*
        only a close menu control is shown when ``pages`` is of length 1.
    message: Optional[discord.Message]
        The message representing the menu. Usually :code:`None` when first opening
        the menu
    page: int
        The current page number of the menu
    timeout: float
        The time (in seconds) to wait for a reaction
    user: Optional[discord.User]
        The user allowed to interact with the menu. Defaults to ``ctx.author``.

        .. warning::

            This parameter is `provisional <developer-guarantees-exclusions>`.
            If no issues arise, we plan on including it under developer guarantees
            in the first release made after 2024-05-24.

    Raises
    ------
    RuntimeError
        If either of the notes above are violated
    """
    if message is not None and message.id in _active_menus:
        # prevents the expected callback from going any further
        # our custom button will always pass the message the view is
        # attached to, allowing one to send multiple menus on the same
        # context.
        view = _active_menus[message.id]
        if pages != view.source.entries:
            view._source = _SimplePageSource(pages)
        new_page = await view.get_page(page)
        view.current_page = page
        view.timeout = timeout
        await view.message.edit(**new_page)
        return
    if not isinstance(pages[0], (discord.Embed, str)):
        raise RuntimeError("Pages must be of type discord.Embed or str")
    if not all(isinstance(x, discord.Embed) for x in pages) and not all(
        isinstance(x, str) for x in pages
    ):
        raise RuntimeError("All pages must be of the same type")
    if controls is None:
        if len(pages) == 1:
            controls = {"\N{CROSS MARK}": close_menu}
        else:
            controls = DEFAULT_CONTROLS
    for key, value in controls.items():
        maybe_coro = value
        if isinstance(value, functools.partial):
            maybe_coro = value.func
        if not asyncio.iscoroutinefunction(maybe_coro):
            raise RuntimeError("Function must be a coroutine")

    if await ctx.bot.use_buttons() and message is None:
        # Only send the button version if `message` is None
        # This is because help deals with this menu in weird ways
        # where the original message is already sent prior to starting.
        # This is not normally the way we recommend sending this because
        # internally we already include the emojis we expect.
        view = SimpleMenu(pages, timeout=timeout)
        if controls == DEFAULT_CONTROLS:
            await view.start(ctx, user=user)
            await view.wait()
            return
        else:
            view.remove_item(view.last_button)
            view.remove_item(view.first_button)
            has_next = False
            has_prev = False
            has_close = False
            to_add = {}
            for emoji, func in controls.items():
                part_emoji = discord.PartialEmoji.from_str(str(emoji))
                if func == next_page:
                    has_next = True
                    if part_emoji != view.forward_button.emoji:
                        view.forward_button.emoji = part_emoji
                elif func == prev_page:
                    has_prev = True
                    if part_emoji != view.backward_button.emoji:
                        view.backward_button.emoji = part_emoji
                elif func == close_menu:
                    has_close = True
                else:
                    to_add[part_emoji] = func
            if not has_next:
                view.remove_item(view.forward_button)
            if not has_prev:
                view.remove_item(view.backward_button)
            if not has_close:
                view.remove_item(view.stop_button)
            for emoji, func in to_add.items():
                view.add_item(_GenericButton(emoji, func))
            await view.start(ctx, user=user)
            _active_menus[view.message.id] = view
            await view.wait()
            del _active_menus[view.message.id]
            return
    current_page = pages[page]

    if not message:
        if isinstance(current_page, discord.Embed):
            message = await ctx.send(embed=current_page)
        else:
            message = await ctx.send(current_page)
        # Don't wait for reactions to be added (GH-1797)
        # noinspection PyAsyncCall
        start_adding_reactions(message, controls.keys())
    else:
        try:
            if isinstance(current_page, discord.Embed):
                await message.edit(embed=current_page)
            else:
                await message.edit(content=current_page)
        except discord.NotFound:
            return

    try:
        predicates = ReactionPredicate.with_emojis(
            tuple(controls.keys()), message, user or ctx.author
        )
        tasks = [
            asyncio.create_task(ctx.bot.wait_for("reaction_add", check=predicates)),
            asyncio.create_task(ctx.bot.wait_for("reaction_remove", check=predicates)),
        ]
        done, pending = await asyncio.wait(
            tasks, timeout=timeout, return_when=asyncio.FIRST_COMPLETED
        )
        for task in pending:
            task.cancel()

        if len(done) == 0:
            raise asyncio.TimeoutError()
        react, __ = done.pop().result()
    except asyncio.TimeoutError:
        if not ctx.me:
            return
        try:
            if (
                isinstance(message.channel, discord.PartialMessageable)
                or message.channel.permissions_for(ctx.me).manage_messages
            ):
                await message.clear_reactions()
            else:
                raise RuntimeError
        except (discord.Forbidden, RuntimeError):  # cannot remove all reactions
            for key in controls.keys():
                try:
                    await message.remove_reaction(key, ctx.bot.user)
                except discord.Forbidden:
                    return
                except discord.HTTPException:
                    pass
        except discord.NotFound:
            return
    else:
        if user is not None:
            return await controls[react.emoji](
                ctx, pages, controls, message, page, timeout, react.emoji, user=user
            )
        else:
            return await controls[react.emoji](
                ctx, pages, controls, message, page, timeout, react.emoji
            )


async def next_page(
    ctx: commands.Context,
    pages: list,
    controls: Mapping[str, _ControlCallable],
    message: discord.Message,
    page: int,
    timeout: float,
    emoji: str,
    *,
    user: Optional[discord.User] = None,
) -> _T:
    """
    Function for showing next page which is suitable
    for use in ``controls`` mapping that is passed to `menu()`.
    """
    if page >= len(pages) - 1:
        page = 0  # Loop around to the first item
    else:
        page = page + 1
    if user is not None:
        return await menu(
            ctx, pages, controls, message=message, page=page, timeout=timeout, user=user
        )
    else:
        return await menu(ctx, pages, controls, message=message, page=page, timeout=timeout)


async def prev_page(
    ctx: commands.Context,
    pages: list,
    controls: Mapping[str, _ControlCallable],
    message: discord.Message,
    page: int,
    timeout: float,
    emoji: str,
    *,
    user: Optional[discord.User] = None,
) -> _T:
    """
    Function for showing previous page which is suitable
    for use in ``controls`` mapping that is passed to `menu()`.
    """
    if page <= 0:
        page = len(pages) - 1  # Loop around to the last item
    else:
        page = page - 1
    if user is not None:
        return await menu(
            ctx, pages, controls, message=message, page=page, timeout=timeout, user=user
        )
    else:
        return await menu(ctx, pages, controls, message=message, page=page, timeout=timeout)


async def close_menu(
    ctx: commands.Context,
    pages: list,
    controls: Mapping[str, _ControlCallable],
    message: discord.Message,
    page: int,
    timeout: float,
    emoji: str,
    *,
    user: Optional[discord.User] = None,
) -> None:
    """
    Function for closing (deleting) menu which is suitable
    for use in ``controls`` mapping that is passed to `menu()`.
    """
    with contextlib.suppress(discord.NotFound):
        await message.delete()


def start_adding_reactions(
    message: discord.Message, emojis: Iterable[_ReactableEmoji]
) -> asyncio.Task:
    """Start adding reactions to a message.

    This is a non-blocking operation - calling this will schedule the
    reactions being added, but the calling code will continue to
    execute asynchronously. There is no need to await this function.

    This is particularly useful if you wish to start waiting for a
    reaction whilst the reactions are still being added - in fact,
    this is exactly what `menu()` uses to do that.

    Parameters
    ----------
    message: discord.Message
        The message to add reactions to.
    emojis : Iterable[Union[str, discord.Emoji]]
        The emojis to react to the message with.

    Returns
    -------
    asyncio.Task
        The task for the coroutine adding the reactions.

    """

    async def task():
        # The task should exit silently if the message is deleted
        with contextlib.suppress(discord.NotFound):
            for emoji in emojis:
                await message.add_reaction(emoji)

    return asyncio.create_task(task())


#: Default controls for `menu()` that contain controls for
#: previous page, closing menu, and next page.
DEFAULT_CONTROLS: Mapping[str, _ControlCallable] = MappingProxyType(
    {
        "\N{LEFTWARDS BLACK ARROW}\N{VARIATION SELECTOR-16}": prev_page,
        "\N{CROSS MARK}": close_menu,
        "\N{BLACK RIGHTWARDS ARROW}\N{VARIATION SELECTOR-16}": next_page,
    }
)
