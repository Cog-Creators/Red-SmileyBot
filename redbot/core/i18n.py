from __future__ import annotations

import contextlib
import functools
import io
import os
import logging
import discord

from pathlib import Path
from typing import Callable, TYPE_CHECKING, Union, Dict, Optional, TypeVar

import babel.localedata
from babel.core import Locale

from redbot.core import _i18n
from redbot.core._i18n import (
    current_locale as _current_locale,
    current_regional_format as _current_regional_format,
    set_contextual_locale as _set_contextual_locale,
    set_contextual_regional_format as _set_contextual_regional_format,
)

if TYPE_CHECKING:
    from redbot.core.bot import Red


__all__ = (
    "get_locale",
    "get_regional_format",
    "set_contextual_locale",
    "set_contextual_regional_format",
    "get_locale_from_guild",
    "get_regional_format_from_guild",
    "set_contextual_locales_from_guild",
    "Translator",
    "get_babel_locale",
    "get_babel_regional_format",
    "cog_i18n",
)

log = logging.getLogger("red.i18n")

WAITING_FOR_MSGID = 1
IN_MSGID = 2
WAITING_FOR_MSGSTR = 3
IN_MSGSTR = 4

MSGID = 'msgid "'
MSGSTR = 'msgstr "'


def get_locale() -> str:
    """
    Get locale in a current context.

    Returns
    -------
    str
        Current locale's language code with country code included, e.g. "en-US".
    """
    return _current_locale.get(_i18n.current_locale_default)


def get_regional_format() -> str:
    """
    Get regional format in a current context.

    Returns
    -------
    str
        Current regional format's language code with country code included, e.g. "en-US".
    """
    regional_format = _current_regional_format.get(_i18n.current_regional_format_default)
    if regional_format is None:
        return _current_locale.get(_i18n.current_locale_default)
    return regional_format


def set_contextual_locale(language_code: str, /) -> str:
    """
    Set contextual locale (without regional format) to the given value.

    Parameters
    ----------
    language_code: str
        Locale's language code with country code included, e.g. "en-US".

    Returns
    -------
    str
        Standardized locale name.

    Raises
    ------
    ValueError
        Language code is invalid.
    """
    return _set_contextual_locale(language_code, verify_language_code=True)


def set_contextual_regional_format(language_code: Optional[str], /) -> Optional[str]:
    """
    Set contextual regional format to the given value.

    Parameters
    ----------
    language_code: str, optional
        Contextual regional's language code with country code included, e.g. "en-US"
        or ``None`` if regional format should inherit the contextual locale's value.

    Returns
    -------
    str
        Standardized locale name or ``None`` if ``None`` was passed.

    Raises
    ------
    ValueError
        Language code is invalid.
    """
    return _set_contextual_regional_format(language_code, verify_language_code=True)


async def get_locale_from_guild(bot: Red, guild: Optional[discord.Guild]) -> str:
    """
    Get locale set for the given guild.

    Parameters
    ----------
    bot: Red
         The bot's instance.
    guild: Optional[discord.Guild]
         The guild contextual locale is set for.
         Use `None` if the context doesn't involve guild.

    Returns
    -------
    str
        Guild locale's language code with country code included, e.g. "en-US".
    """
    return await bot._i18n_cache.get_locale(guild)


async def get_regional_format_from_guild(bot: Red, guild: Optional[discord.Guild]) -> str:
    """
    Get regional format for the given guild.

    Parameters
    ----------
    bot: Red
         The bot's instance.
    guild: Optional[discord.Guild]
         The guild contextual locale is set for.
         Use `None` if the context doesn't involve guild.

    Returns
    -------
    str
        Guild regional format's language code with country code included, e.g. "en-US".
    """
    return await bot._i18n_cache.get_regional_format(guild)


async def set_contextual_locales_from_guild(bot: Red, guild: Optional[discord.Guild]) -> None:
    """
    Set contextual locales (locale and regional format) for given guild context.

    Parameters
    ----------
    bot: Red
         The bot's instance.
    guild: Optional[discord.Guild]
         The guild contextual locale is set for.
         Use `None` if the context doesn't involve guild.
    """
    locale = await get_locale_from_guild(bot, guild)
    regional_format = await get_regional_format_from_guild(bot, guild)
    _set_contextual_locale(locale)
    _set_contextual_regional_format(regional_format)


def _parse(translation_file: io.TextIOWrapper) -> Dict[str, str]:
    """
    Custom gettext parsing of translation files.

    Parameters
    ----------
    translation_file : io.TextIOWrapper
        An open text file containing translations.

    Returns
    -------
    Dict[str, str]
        A dict mapping the original strings to their translations. Empty
        translated strings are omitted.

    """
    step = None
    untranslated = ""
    translated = ""
    translations = {}
    locale = get_locale()

    translations[locale] = {}

    for line in translation_file:
        line = line.strip()

        if line.startswith(MSGID):
            # New msgid
            if step is IN_MSGSTR and translated:
                # Store the last translation
                translations[locale][_unescape(untranslated)] = _unescape(translated)
            step = IN_MSGID
            untranslated = line[len(MSGID) : -1]
        elif line.startswith('"') and line.endswith('"'):
            if step is IN_MSGID:
                # Line continuing on from msgid
                untranslated += line[1:-1]
            elif step is IN_MSGSTR:
                # Line continuing on from msgstr
                translated += line[1:-1]
        elif line.startswith(MSGSTR):
            # New msgstr
            step = IN_MSGSTR
            translated = line[len(MSGSTR) : -1]

    if step is IN_MSGSTR and translated:
        # Store the final translation
        translations[locale][_unescape(untranslated)] = _unescape(translated)
    return translations


def _unescape(string):
    string = string.replace(r"\\", "\\")
    string = string.replace(r"\t", "\t")
    string = string.replace(r"\r", "\r")
    string = string.replace(r"\n", "\n")
    string = string.replace(r"\"", '"')
    return string


def _get_locale_path(cog_folder: Path, extension: str) -> Path:
    """
    Gets the folder path containing localization files.

    :param Path cog_folder:
        The cog folder that we want localizations for.
    :param str extension:
        Extension of localization files.
    :return:
        Path of possible localization file, it may not exist.
    """
    return cog_folder / "locales" / "{}.{}".format(get_locale(), extension)


class Translator(Callable[[str], str]):
    """Function to get translated strings at runtime."""

    def __init__(self, name: str, file_location: Union[str, Path, os.PathLike]):
        """
        Initializes an internationalization object.

        Parameters
        ----------
        name : str
            Your cog name.
        file_location : `str` or `pathlib.Path`
            This should always be ``__file__`` otherwise your localizations
            will not load.

        """
        self.cog_folder = Path(file_location).resolve().parent
        self.cog_name = name
        self.translations = {}

        _i18n.translators.append(self)

        self.load_translations()

    def __call__(self, untranslated: str) -> str:
        """Translate the given string.

        This will look for the string in the translator's :code:`.pot` file,
        with respect to the current locale.
        """
        locale = get_locale()
        try:
            return self.translations[locale][untranslated]
        except KeyError:
            return untranslated

    def load_translations(self):
        """
        Loads the current translations.
        """
        locale = get_locale()

        if locale.lower() == "en-us":
            # Red is written in en-US, no point in loading it
            return
        if locale in self.translations:
            # Locales cannot be loaded twice as they have an entry in
            # self.translations
            return

        locale_path = _get_locale_path(self.cog_folder, "po")
        with contextlib.suppress(IOError, FileNotFoundError):
            with locale_path.open(encoding="utf-8") as file:
                self._parse(file)

    def _parse(self, translation_file):
        self.translations.update(_parse(translation_file))

    def _add_translation(self, untranslated, translated):
        untranslated = _unescape(untranslated)
        translated = _unescape(translated)
        if translated:
            self.translations[untranslated] = translated


@functools.lru_cache()
def _get_babel_locale(red_locale: str) -> babel.core.Locale:
    supported_locales = babel.localedata.locale_identifiers()
    try:  # Handles cases where red_locale is already Babel supported
        babel_locale = Locale(*babel.parse_locale(red_locale))
    except (ValueError, babel.core.UnknownLocaleError):
        try:
            babel_locale = Locale(*babel.parse_locale(red_locale, sep="-"))
        except (ValueError, babel.core.UnknownLocaleError):
            # ValueError is Raised by `parse_locale` when an invalid Locale is given to it
            # Lets handle it silently and default to "en_US"
            try:
                # Try to find a babel locale that's close to the one used by red
                babel_locale = Locale(Locale.negotiate([red_locale], supported_locales, sep="-"))
            except (ValueError, TypeError, babel.core.UnknownLocaleError):
                # If we fail to get a close match we will then default to "en_US"
                babel_locale = Locale("en", "US")
    return babel_locale


def get_babel_locale(locale: Optional[str] = None) -> babel.core.Locale:
    """Function to convert a locale to a `babel.core.Locale`.

    Parameters
    ----------
    locale : Optional[str]
        The locale to convert, if not specified it defaults to the bot's locale.

    Returns
    -------
    babel.core.Locale
        The babel locale object.
    """
    if locale is None:
        locale = get_locale()
    return _get_babel_locale(locale)


def get_babel_regional_format(regional_format: Optional[str] = None) -> babel.core.Locale:
    """Function to convert a regional format to a `babel.core.Locale`.

    If ``regional_format`` parameter is passed, this behaves the same as `get_babel_locale`.

    Parameters
    ----------
    regional_format : Optional[str]
        The regional format to convert, if not specified it defaults to the bot's regional format.

    Returns
    -------
    babel.core.Locale
        The babel locale object.
    """
    if regional_format is None:
        regional_format = get_regional_format()
    return _get_babel_locale(regional_format)


# This import to be down here to avoid circular import issues.
# This will be cleaned up at a later date
# noinspection PyPep8
from . import commands

_TypeT = TypeVar("_TypeT", bound=type)


def cog_i18n(translator: Translator) -> Callable[[_TypeT], _TypeT]:
    """Get a class decorator to link the translator to this cog."""

    def decorator(cog_class: _TypeT) -> _TypeT:
        cog_class.__translator__ = translator
        for name, attr in cog_class.__dict__.items():
            if isinstance(attr, (commands.Group, commands.Command)):
                attr.translator = translator
                setattr(cog_class, name, attr)
        return cog_class

    return decorator
