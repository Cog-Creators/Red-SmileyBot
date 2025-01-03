from __future__ import annotations

import datetime
import itertools
import math
import textwrap
from io import BytesIO, StringIO
from typing import Any, Iterator, List, Literal, Optional, Sequence, SupportsInt, Union

import discord
from babel.lists import format_list as babel_list
from babel.numbers import format_decimal
from rich.console import Console

from redbot.core.i18n import Translator, get_babel_locale, get_babel_regional_format

__all__ = (
    "error",
    "warning",
    "info",
    "success",
    "question",
    "bold",
    "box",
    "header",
    "hyperlink",
    "inline",
    "italics",
    "spoiler",
    "pagify",
    "strikethrough",
    "subtext",
    "underline",
    "quote",
    "escape",
    "humanize_list",
    "format_perms_list",
    "humanize_timedelta",
    "humanize_number",
    "text_to_file",
    "rich_markup",
)

_ = Translator("UtilsChatFormatting", __file__)


def hyperlink(text: str, url: str) -> str:
    """Create hyperlink markdown with text and a URL.

    Parameters
    ----------
    text : str
        The text which will contain the link.
    url : str
        The URL used for the hyperlink.

    Returns
    -------
    str
        The new message.

    """
    return f"[{text}]({url})"


def header(text: str, size: Literal["small", "medium", "large"]) -> str:
    """Formats a header.

    Parameters
    ----------
    text : str
        The text for the header.
    size : Literal['small', 'medium', 'large']
        The size of the header ('small', 'medium' or 'large')

    Returns
    -------
    str
        The new message.

    """
    if size == "small":
        multiplier = 3
    elif size == "medium":
        multiplier = 2
    elif size == "large":
        multiplier = 1
    else:
        raise ValueError(f"Invalid size '{size}'")
    return "#" * multiplier + " " + text


def subtext(text: str) -> str:
    """Formats subtext from the given text.

    Parameters
    ----------
    text : str
        The text to format as subtext.

    Returns
    -------
    str
        The new message.

    """
    return "-# " + text


def error(text: str) -> str:
    """Get text prefixed with an error emoji.

    Parameters
    ----------
    text : str
        The text to be prefixed.

    Returns
    -------
    str
        The new message.

    """
    return f"\N{NO ENTRY SIGN} {text}"


def warning(text: str) -> str:
    """Get text prefixed with a warning emoji.

    Parameters
    ----------
    text : str
        The text to be prefixed.

    Returns
    -------
    str
        The new message.

    """
    return f"\N{WARNING SIGN}\N{VARIATION SELECTOR-16} {text}"


def info(text: str) -> str:
    """Get text prefixed with an info emoji.

    Parameters
    ----------
    text : str
        The text to be prefixed.

    Returns
    -------
    str
        The new message.

    """
    return f"\N{INFORMATION SOURCE}\N{VARIATION SELECTOR-16} {text}"


def success(text: str) -> str:
    """Get text prefixed with a success emoji.

    Parameters
    ----------
    text : str
        The text to be prefixed.

    Returns
    -------
    str
        The new message.

    """
    return f"\N{WHITE HEAVY CHECK MARK} {text}"


def question(text: str) -> str:
    """Get text prefixed with a question emoji.

    Parameters
    ----------
    text : str
        The text to be prefixed.

    Returns
    -------
    str
        The new message.

    """
    return f"\N{BLACK QUESTION MARK ORNAMENT}\N{VARIATION SELECTOR-16} {text}"


def bold(text: str, escape_formatting: bool = True) -> str:
    """Get the given text in bold.

    Note: By default, this function will escape ``text`` prior to emboldening.

    Parameters
    ----------
    text : str
        The text to be marked up.
    escape_formatting : `bool`, optional
        Set to :code:`False` to not escape markdown formatting in the text.

    Returns
    -------
    str
        The marked up text.

    """
    return f"**{escape(text, formatting=escape_formatting)}**"


def box(text: str, lang: str = "") -> str:
    """Get the given text in a code block.

    Parameters
    ----------
    text : str
        The text to be marked up.
    lang : `str`, optional
        The syntax highlighting language for the codeblock.

    Returns
    -------
    str
        The marked up text.

    """
    return f"```{lang}\n{text}\n```"


def inline(text: str) -> str:
    """Get the given text as inline code.

    Parameters
    ----------
    text : str
        The text to be marked up.

    Returns
    -------
    str
        The marked up text.

    """
    if "`" in text:
        return f"``{text}``"
    else:
        return f"`{text}`"


def italics(text: str, escape_formatting: bool = True) -> str:
    """Get the given text in italics.

    Note: By default, this function will escape ``text`` prior to italicising.

    Parameters
    ----------
    text : str
        The text to be marked up.
    escape_formatting : `bool`, optional
        Set to :code:`False` to not escape markdown formatting in the text.

    Returns
    -------
    str
        The marked up text.

    """
    return f"*{escape(text, formatting=escape_formatting)}*"


def spoiler(text: str, escape_formatting: bool = True) -> str:
    """Get the given text as a spoiler.

    Note: By default, this function will escape ``text`` prior to making the text a spoiler.

    Parameters
    ----------
    text : str
        The text to be marked up.
    escape_formatting : `bool`, optional
        Set to :code:`False` to not escape markdown formatting in the text.

    Returns
    -------
    str
        The marked up text.

    """
    return f"||{escape(text, formatting=escape_formatting)}||"


class pagify(Iterator[str]):
    """Generate multiple pages from the given text.

    The returned iterator supports length estimation with :func:`operator.length_hint()`.

    Note
    ----
    This does not respect code blocks or inline code.

    Parameters
    ----------
    text : str
        The content to pagify and send.
    delims : `sequence` of `str`, optional
        Characters where page breaks will occur. If no delimiters are found
        in a page, the page will break after ``page_length`` characters.
        By default this only contains the newline.

    Other Parameters
    ----------------
    priority : `bool`
        Set to :code:`True` to choose the page break delimiter based on the
        order of ``delims``. Otherwise, the page will always break at the
        last possible delimiter.
    escape_mass_mentions : `bool`
        If :code:`True`, any mass mentions (here or everyone) will be
        silenced.
    shorten_by : `int`
        How much to shorten each page by. Defaults to 8.
    page_length : `int`
        The maximum length of each page. Defaults to 2000.

    Yields
    ------
    `str`
        Pages of the given text.

    """

    # when changing signature of this method, please update it in docs/framework_utils.rst as well
    def __init__(
        self,
        text: str,
        delims: Sequence[str] = ("\n",),
        *,
        priority: bool = False,
        escape_mass_mentions: bool = True,
        shorten_by: int = 8,
        page_length: int = 2000,
    ) -> None:
        self._text = text
        self._delims = delims
        self._priority = priority
        self._escape_mass_mentions = escape_mass_mentions
        self._shorten_by = shorten_by
        self._page_length = page_length - shorten_by

        self._start = 0
        self._end = len(text)

    def __repr__(self) -> str:
        text = self._text
        if len(text) > 20:
            text = f"{text[:19]}\N{HORIZONTAL ELLIPSIS}"
        return (
            "pagify("
            f"{text!r},"
            f" {self._delims!r},"
            f" priority={self._priority!r},"
            f" escape_mass_mentions={self._escape_mass_mentions!r},"
            f" shorten_by={self._shorten_by!r},"
            f" page_length={self._page_length + self._shorten_by!r}"
            ")"
        )

    def __length_hint__(self) -> int:
        return math.ceil((self._end - self._start) / self._page_length)

    def __iter__(self) -> pagify:
        return self

    def __next__(self) -> str:
        text = self._text
        escape_mass_mentions = self._escape_mass_mentions
        page_length = self._page_length
        start = self._start
        end = self._end

        while (end - start) > page_length:
            stop = start + page_length
            if escape_mass_mentions:
                stop -= text.count("@here", start, stop) + text.count("@everyone", start, stop)
            closest_delim_it = (text.rfind(d, start + 1, stop) for d in self._delims)
            if self._priority:
                closest_delim = next((x for x in closest_delim_it if x > 0), -1)
            else:
                closest_delim = max(closest_delim_it)
            stop = closest_delim if closest_delim != -1 else stop
            if escape_mass_mentions:
                to_send = escape(text[start:stop], mass_mentions=True)
            else:
                to_send = text[start:stop]
            start = self._start = stop
            if len(to_send.strip()) > 0:
                return to_send

        if len(text[start:end].strip()) > 0:
            self._start = end
            if escape_mass_mentions:
                return escape(text[start:end], mass_mentions=True)
            else:
                return text[start:end]

        raise StopIteration


def strikethrough(text: str, escape_formatting: bool = True) -> str:
    """Get the given text with a strikethrough.

    Note: By default, this function will escape ``text`` prior to applying a strikethrough.

    Parameters
    ----------
    text : str
        The text to be marked up.
    escape_formatting : `bool`, optional
        Set to :code:`False` to not escape markdown formatting in the text.

    Returns
    -------
    str
        The marked up text.

    """
    return f"~~{escape(text, formatting=escape_formatting)}~~"


def underline(text: str, escape_formatting: bool = True) -> str:
    """Get the given text with an underline.

    Note: By default, this function will escape ``text`` prior to underlining.

    Parameters
    ----------
    text : str
        The text to be marked up.
    escape_formatting : `bool`, optional
        Set to :code:`False` to not escape markdown formatting in the text.

    Returns
    -------
    str
        The marked up text.

    """
    return f"__{escape(text, formatting=escape_formatting)}__"


def quote(text: str) -> str:
    """Quotes the given text.

    Parameters
    ----------
    text : str
        The text to be marked up.

    Returns
    -------
    str
        The marked up text.

    """
    return textwrap.indent(text, "> ", lambda l: True)


def escape(text: str, *, mass_mentions: bool = False, formatting: bool = False) -> str:
    """Get text with all mass mentions or markdown escaped.

    Parameters
    ----------
    text : str
        The text to be escaped.
    mass_mentions : `bool`, optional
        Set to :code:`True` to escape mass mentions in the text.
    formatting : `bool`, optional
        Set to :code:`True` to escape any markdown formatting in the text.

    Returns
    -------
    str
        The escaped text.

    """
    if mass_mentions:
        text = text.replace("@everyone", "@\u200beveryone")
        text = text.replace("@here", "@\u200bhere")
    if formatting:
        text = discord.utils.escape_markdown(text)
    return text


def humanize_list(
    items: Sequence[str], *, locale: Optional[str] = None, style: str = "standard"
) -> str:
    """Get comma-separated list, with the last element joined with *and*.

    Parameters
    ----------
    items : Sequence[str]
        The items of the list to join together.
    locale : Optional[str]
        The locale to convert, if not specified it defaults to the bot's locale.
    style : str
        The style to format the list with.

        Note: Not all styles are necessarily available in all locales,
        see documentation of `babel.lists.format_list` for more details.

        standard
            A typical 'and' list for arbitrary placeholders.
            eg. "January, February, and March"
        standard-short
             A short version of a 'and' list, suitable for use with short or
             abbreviated placeholder values.
             eg. "Jan., Feb., and Mar."
        or
            A typical 'or' list for arbitrary placeholders.
            eg. "January, February, or March"
        or-short
            A short version of an 'or' list.
            eg. "Jan., Feb., or Mar."
        unit
            A list suitable for wide units.
            eg. "3 feet, 7 inches"
        unit-short
            A list suitable for short units
            eg. "3 ft, 7 in"
        unit-narrow
            A list suitable for narrow units, where space on the screen is very limited.
            eg. "3′ 7″"

    Raises
    ------
    ValueError
        The locale does not support the specified style.

    Examples
    --------
    .. testsetup::

        from redbot.core.utils.chat_formatting import humanize_list

    .. doctest::

        >>> humanize_list(['One', 'Two', 'Three'])
        'One, Two, and Three'
        >>> humanize_list(['One'])
        'One'
        >>> humanize_list(['omena', 'peruna', 'aplari'], style='or', locale='fi')
        'omena, peruna tai aplari'

    """

    return babel_list(items, style=style, locale=get_babel_locale(locale))


def format_perms_list(perms: discord.Permissions) -> str:
    """Format a list of permission names.

    This will return a humanized list of the names of all enabled
    permissions in the provided `discord.Permissions` object.

    Parameters
    ----------
    perms : discord.Permissions
        The permissions object with the requested permissions to list
        enabled.

    Returns
    -------
    str
        The humanized list.

    """
    perm_names: List[str] = []
    for perm, value in perms:
        if value is True:
            perm_name = '"' + perm.replace("_", " ").title() + '"'
            perm_names.append(perm_name)
    return humanize_list(perm_names).replace("Guild", "Server")


def humanize_timedelta(
    *,
    timedelta: Optional[datetime.timedelta] = None,
    seconds: Optional[SupportsInt] = None,
    negative_format: Optional[str] = None,
    maximum_units: Optional[int] = None,
) -> str:
    """
    Get a locale aware human timedelta representation.

    This works with either a timedelta object or a number of seconds.

    Fractional values will be omitted.

    Values that are less than 1 second but greater than -1 second
    will be an empty string.

    Parameters
    ----------
    timedelta: Optional[datetime.timedelta]
        A timedelta object
    seconds: Optional[SupportsInt]
        A number of seconds
    negative_format: Optional[str]
        How to format negative timedeltas, using %-formatting rules.
        Defaults to "negative %s"
    maximum_units: Optional[int]
        The maximum number of different units to output in the final string.

    Returns
    -------
    str
        A locale aware representation of the timedelta or seconds.

    Raises
    ------
    ValueError
        The function was called with neither a number of seconds nor a timedelta object,
        or with a maximum_units less than 1.

    Examples
    --------
    .. testsetup::

        from datetime import timedelta
        from redbot.core.utils.chat_formatting import humanize_timedelta

    .. doctest::

        >>> humanize_timedelta(seconds=314)
        '5 minutes, 14 seconds'
        >>> humanize_timedelta(timedelta=timedelta(minutes=3.14), maximum_units=1)
        '3 minutes'
        >>> humanize_timedelta(timedelta=timedelta(days=-3.14), negative_format="%s ago", maximum_units=3)
        '3 days, 3 hours, 21 minutes ago'
    """

    try:
        obj = seconds if seconds is not None else timedelta.total_seconds()
    except AttributeError:
        raise ValueError("You must provide either a timedelta or a number of seconds")
    if maximum_units is not None and maximum_units < 1:
        raise ValueError("maximum_units must be >= 1")

    periods = [
        (_("year"), _("years"), 60 * 60 * 24 * 365),
        (_("month"), _("months"), 60 * 60 * 24 * 30),
        (_("day"), _("days"), 60 * 60 * 24),
        (_("hour"), _("hours"), 60 * 60),
        (_("minute"), _("minutes"), 60),
        (_("second"), _("seconds"), 1),
    ]
    seconds = int(obj)
    if seconds < 0:
        seconds = -seconds
        if negative_format and "%s" not in negative_format:
            negative_format = negative_format + " %s"
        else:
            negative_format = negative_format or (_("negative") + " %s")
    else:
        negative_format = "%s"
    strings = []
    maximum_units = maximum_units or len(periods)
    for period_name, plural_period_name, period_seconds in periods:
        if seconds >= period_seconds:
            period_value, seconds = divmod(seconds, period_seconds)
            if period_value == 0:
                continue
            unit = plural_period_name if period_value > 1 else period_name
            strings.append(f"{period_value} {unit}")
            if len(strings) == maximum_units:
                break

    return negative_format % humanize_list(strings, style="unit")


def humanize_number(val: Union[int, float], override_locale=None) -> str:
    """
    Convert an int or float to a str with digit separators based on bot locale.

    Parameters
    ----------
    val : Union[int, float]
        The int/float to be formatted.
    override_locale: Optional[str]
        A value to override bot's regional format.

    Raises
    ------
    decimals.InvalidOperation
        If val is greater than 10 x 10^21 for some locales, 10 x 10^24 in others.

    Returns
    -------
    str
        Locale-aware formatted number.
    """
    return format_decimal(val, locale=get_babel_regional_format(override_locale))


def text_to_file(
    text: str, filename: str = "file.txt", *, spoiler: bool = False, encoding: str = "utf-8"
):
    """Prepares text to be sent as a file on Discord, without character limit.

    This writes text into a bytes object that can be used for the ``file`` or ``files`` parameters
    of :meth:`discord.abc.Messageable.send`.

    Parameters
    ----------
    text: str
        The text to put in your file.
    filename: str
        The name of the file sent. Defaults to ``file.txt``.
    spoiler: bool
        Whether the attachment is a spoiler. Defaults to ``False``.

    Returns
    -------
    discord.File
        The file containing your text.

    """
    file = BytesIO(text.encode(encoding))
    return discord.File(file, filename, spoiler=spoiler)


def rich_markup(
    *objects: Any,
    crop: Optional[bool] = True,
    emoji: Optional[bool] = True,
    highlight: Optional[bool] = True,
    justify: Optional[str] = None,
    markup: Optional[bool] = True,
    no_wrap: Optional[bool] = None,
    overflow: Optional[str] = None,
    width: Optional[int] = None,
) -> str:
    """Returns a codeblock with ANSI formatting for colour support.

    This supports a limited set of Rich markup, and rich helper functions. (https://rich.readthedocs.io/en/stable/index.html)

    Parameters
    ----------
    *objects: Any
        The text to convert to ANSI formatting.
    crop: Optional[bool]
        Crop output to width of virtual terminal. Defaults to ``True``.
    emoji: Optional[bool]
        Enable emoji code. Defaults to ``True``.
    highlight: Optional[bool]
        Enable automated highlighting. Defaults to ``True``.
    justify: Optional[str]
        Justify method: "default", "left", "right", "center", or "full". Defaults to ``None``.
    markup: Optional[bool]
        Boolean to enable Console Markup. Defaults to ``True``.
    no_wrap: Optional[bool]
        Disables word wrapping. Defaults to ``None``.
    overflow: Optional[str]
        Overflow method: "ignore", "crop", "fold", or "ellipsis". Defaults to None.
    width: Optional[int]
        The width of the virtual terminal. Defaults to ``80`` characters long.


    Returns
    -------
    str:
        The ANSI formatted text in a codeblock.
    """
    temp_console = Console(  # Prevent messing with STDOUT's console
        color_system="standard",  # Discord only supports 8-bit in colors
        emoji=emoji,
        file=StringIO(),
        force_terminal=True,
        force_interactive=False,
        highlight=highlight,
        markup=markup,
        width=width if width is not None else 80,
    )

    temp_console.print(
        *objects,
        crop=crop,
        justify=justify,
        no_wrap=no_wrap,
        overflow=overflow,
    )
    return box(temp_console.file.getvalue(), lang="ansi")
