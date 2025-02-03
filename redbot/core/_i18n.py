from __future__ import annotations

from contextvars import ContextVar
from typing import TYPE_CHECKING, List, Optional

from babel.core import Locale, UnknownLocaleError

if TYPE_CHECKING:
    from redbot.core.i18n import Translator


__all__ = (
    "current_locale",
    "current_locale_default",
    "current_regional_format",
    "current_regional_format_default",
    "translators",
    "set_global_locale",
    "set_global_regional_format",
    "set_contextual_locale",
    "set_contextual_regional_format",
)


FRESH_INSTALL_LOCALE = "en-US"
current_locale = ContextVar("current_locale")
current_locale_default = FRESH_INSTALL_LOCALE
current_regional_format = ContextVar("current_regional_format")
current_regional_format_default = None

translators: List[Translator] = []


def _reload_locales() -> None:
    for translator in translators:
        translator.load_translations()


def _get_standardized_locale_name(language_code: str) -> str:
    try:
        locale = Locale.parse(language_code, sep="-")
    except (ValueError, UnknownLocaleError):
        raise ValueError("Invalid language code. Use format: `en-US`")
    if locale.territory is None:
        raise ValueError(
            "Invalid format - language code has to include country code, e.g. `en-US`"
        )
    return f"{locale.language}-{locale.territory}"


def set_global_locale(language_code: str, /) -> str:
    global current_locale_default
    current_locale_default = _get_standardized_locale_name(language_code)
    _reload_locales()
    return current_locale_default


def set_global_regional_format(language_code: Optional[str], /) -> Optional[str]:
    global current_regional_format_default
    if language_code is not None:
        language_code = _get_standardized_locale_name(language_code)
    current_regional_format_default = language_code
    return language_code


def set_contextual_locale(language_code: str, /, verify_language_code: bool = False) -> str:
    if verify_language_code:
        language_code = _get_standardized_locale_name(language_code)
    current_locale.set(language_code)
    _reload_locales()
    return language_code


def set_contextual_regional_format(
    language_code: str, /, verify_language_code: bool = False
) -> str:
    if verify_language_code and language_code is not None:
        language_code = _get_standardized_locale_name(language_code)
    current_regional_format.set(language_code)
    return language_code
