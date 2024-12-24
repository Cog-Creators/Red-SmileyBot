import inspect

import pytest
from discord import app_commands as dpy_app_commands

from redbot.core import app_commands


def test_dpy_app_commands_reexports():
    dpy_attrs = set()
    for attr_name, attr_value in dpy_app_commands.__dict__.items():
        if attr_name.startswith("_") or inspect.ismodule(attr_value):
            continue

        dpy_attrs.add(attr_name)

    missing_attrs = dpy_attrs - set(app_commands.__dict__.keys())

    if missing_attrs:
        pytest.fail(
            "redbot.core.app_commands is missing these names from discord.app_commands: "
            + ", ".join(missing_attrs)
        )


def test_dpy_app_commands_checks_reexports():
    dpy_attrs = set(dpy_app_commands.checks.__all__)
    missing_attrs = dpy_attrs - set(app_commands.checks.__dict__.keys())

    if missing_attrs:
        pytest.fail(
            "redbot.core.app_commands.checks is missing these names from discord.app_commands: "
            + ", ".join(missing_attrs)
        )
