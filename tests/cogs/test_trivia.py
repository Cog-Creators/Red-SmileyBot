import textwrap
from typing import Any

import pytest
import yaml
from schema import And, Optional, SchemaError

from redbot.cogs.trivia.schema import (
    ALWAYS_MATCH,
    MATCH_ALL_BUT_STR,
    NO_QUESTIONS_ERROR_MSG,
    TRIVIA_LIST_SCHEMA,
    format_schema_error,
)


def test_trivia_lists():
    from redbot.cogs.trivia import InvalidListError, get_core_lists, get_list

    list_names = get_core_lists()
    assert list_names
    problem_lists = []
    for l in list_names:
        try:
            get_list(l)
        except InvalidListError as exc:
            e = exc.__cause__
            if isinstance(e, SchemaError):
                problem_lists.append((l.stem, f"SCHEMA error:\n{format_schema_error(e)}"))
            else:
                problem_lists.append((l.stem, f"YAML error:\n{e!s}"))

    if problem_lists:
        msg = "\n".join(
            f"- {name}:\n{textwrap.indent(error, '    ')}" for name, error in problem_lists
        )
        raise TypeError("The following lists contain errors:\n" + msg)


def _get_error_message(*keys: Any, key: str = "UNKNOWN", parent_key: str = "UNKNOWN") -> str:
    if not keys:
        return TRIVIA_LIST_SCHEMA._error

    current = TRIVIA_LIST_SCHEMA.schema
    for key_name in keys:
        if isinstance(current, And):
            current = current.args[0]
        current = current[key_name]
    return str(current._error).format(key=repr(key), parent_key=repr(parent_key))


@pytest.mark.parametrize(
    "data,error_msg",
    (
        ("text", _get_error_message()),
        ({"AUTHOR": 123}, _get_error_message(Optional("AUTHOR"), key="AUTHOR")),
        ({"CONFIG": 123}, _get_error_message(Optional("CONFIG"), key="CONFIG")),
        (
            {"CONFIG": {"key": "value"}},
            _get_error_message(Optional("CONFIG"), ALWAYS_MATCH, key="key", parent_key="CONFIG"),
        ),
        (
            {"CONFIG": {"bot_plays": "wrong type"}},
            _get_error_message(
                Optional("CONFIG"), Optional("bot_plays"), key="bot_plays", parent_key="CONFIG"
            ),
        ),
        ({"AUTHOR": "Correct type but no questions."}, NO_QUESTIONS_ERROR_MSG),
        ({"Question": "wrong type"}, _get_error_message(str, key="Question")),
        ({"Question": [{"wrong": "type"}]}, _get_error_message(str, key="Question")),
        ({123: "wrong key type"}, _get_error_message(MATCH_ALL_BUT_STR, key="123")),
    ),
)
def test_trivia_schema_error_messages(data: Any, error_msg: str):
    with pytest.raises(SchemaError) as exc:
        TRIVIA_LIST_SCHEMA.validate(data)

    assert format_schema_error(exc.value) == error_msg
