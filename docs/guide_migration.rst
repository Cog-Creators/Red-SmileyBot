.. V3 Migration Guide

.. role:: python(code)
    :language: python

==========================
Migrating cogs from Red V2
==========================

First, be sure to read :dpy_docs:`discord.py's migration guide <migrating_to_v1.html>`
as that covers all of the changes to discord.py that will affect the migration process

----------------
Red as a package
----------------

V3 makes Red a package that is installed with :code:`pip`. Please
keep this in mind when writing cogs as this affects how imports 
should be done (for example, to import :code:`pagify` in V2, one
would do :code:`from .utils.chat_formatting import pagify`; in
V3, this becomes :code:`from redbot.core.utils.chat_formatting import pagify`)

----------------
Cogs as packages
----------------

V3 makes cogs into packages. See :doc:`/guide_cog_creation`
for more on how to create packages for V3.

------
Config
------

Config is V3's replacement for :code:`dataIO`. Instead of fiddling with
creating config directories and config files as was done in V2, V3's
Config handles that whilst allowing for easy storage of settings on a
per-server/member/user/role/channel or global basis. Be sure to check
out :doc:`/framework_config` for the API docs for Config as well as a
tutorial on using Config.

----
Bank
----

Bank in V3 has been split out from Economy. V3 introduces the ability
to have a global bank as well as the ability to change the bank name
and the name of the currency. Be sure to checkout :doc:`/framework_bank`
for more on Bank

-------
Mod Log
-------

V3 introduces Mod Log as an API, thus allowing for cogs to add custom case
types that will appear in a server's mod log channel. Be sure to checkout
:doc:`/framework_modlog` for more on Mod Log` 
