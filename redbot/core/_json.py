import json
from typing import Any, Callable, Optional, TextIO

try:
    import orjson
except (ModuleNotFoundError, ImportError):
    HAS_ORJSON = False
else:
    HAS_ORJSON = True


__all__ = (
    "JSONEncodeError",
    "JSONDecodeError",
    "dumps",
    "dump",
    "loads",
    "load"
)


if HAS_ORJSON:
    JSONEncodeError = orjson.JSONEncodeError  # type: ignore
    JSONDecodeError = orjson.JSONDecodeError  # type: ignore
else:
    JSONEncodeError = ValueError, TypeError
    JSONDecodeError = json.JSONDecodeError


def dumps(
    obj: Any,
    *,
    default: Optional[Callable[[Any], Any]] = None,
    orjson_option: Optional[int] = None,
    **json_kwargs: Any,
) -> str:
    if HAS_ORJSON:
        return orjson.dumps(  # type: ignore
            obj,
            default=default,
            option=orjson_option,
        ).decode("utf-8")
    else:
        return json.dumps(obj, default=default, **json_kwargs)


def dump(
    obj: Any,
    fp: TextIO,
    *,
    default: Optional[Callable[[Any], Any]] = None,
    orjson_option: Optional[int] = None,
    **kwargs: Any,
) -> None:
    fp.write(dumps(obj, default=default, orjson_option=orjson_option, **kwargs))


def loads(obj: Any, **json_kwargs: Any) -> Any:
    if HAS_ORJSON:
        return orjson.loads(obj)  # type: ignore
    else:
        return json.loads(obj, **json_kwargs)


def load(fp: TextIO, **kwargs: Any) -> Any:
    return loads(fp.read(), **kwargs)
