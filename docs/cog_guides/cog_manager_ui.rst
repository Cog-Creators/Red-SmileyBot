.. _cogmanagerui:

==============
Cog Manager UI
==============

This is the cog guide for the core cog. You will
find detailed docs about usage and commands.

``[p]`` is considered as your prefix.

.. note:: This cog is not like the other cogs. It is loaded by default, not
    included in the cogs paths and it cannot be unloaded. It contains needed
    commands for cog management.

.. _cogmanagerui-usage:

-----
Usage
-----

This cog allows you to manage your cogs and where you can install them. Unlike
V2, which had a ``cogs`` folder where everything was installed, you can
install V3 cogs everywhere, and also make them cross-compatible with other
instances!

If you want to install your cogs using a Github repo (usually what you will
always be looking for), you need to use the downloader cog. However, if you
have the files of a cog or want to code one, this cog is what you should be
looking for.

The most basic command is :ref:`paths <cogmanagerui-command-paths>`, which
will list you all of the currently set paths.

You can add a path by using the :ref:`addpath <cogmanagerui-command-addpath>`
command. All cogs in that path will be available for the bot and listed in
the :ref:`cogs <cogmanagerui-command-cogs>`. You can then load
or unload them.

.. TODO add ref to load and unload commands

.. _cogmanagerui-usage-installation:

^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
How to install a local package without using downloader
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Let's suppose you made a cog request on the `cog board <https://cogboard.discord.red>`_
and now you want to add your own cog to Red. You should have a folder that
looks like this:

.. image:: ../.resources/cog_manager_ui/custom-cog-example.png

You will first need to add a cog path to your instance. For that, use the
:ref:`addpath <cogmanagerui-command-addpath>` command with a new directory.

Create a folder somewhere (should stay accessible) and copy its path. A path
looks like this:

*   Windows: ``C:\Users\username\Documents\MyCogs``
*   macOS: ``/Users/username/Documents/MyCogs``
*   Linux: ``/home/username/Documents/MyCogs``

You can now use the command we talked about before: type ``[p]addpath
<your_path>``.

.. attention:: A path shouldn't have spaces in it. If it does, add quotation
    marks around the path, or a backslash before the space.

In that ``MyCogs`` folder, you can drop your cog folder. You should now have
something that looks like this:

.. image:: ../.resources/cog_manager_ui/cog-path.png

Now if you type ``[p]cogs``, your new cog should be listed, and you will be
able to load it!

.. _cogmanagerui-commands:

--------
Commands
--------

.. note:: The whole cog is locked to the
    :ref:`bot owner <getting-started-permissions>`. If you are not the owner
    of the instance, you can ignore this.

.. _cogmanagerui-command-cogs:

^^^^
cogs
^^^^

**Syntax**

.. code-block:: none

    [p]cogs

**Description**

Returns a list of loaded and unloaded cogs on the bot.

Cogs are unloaded by default. This is where you can find your cogs if you
installed some recently.

All of the cogs located inside a cog path will be listed here. You can see a
list of the paths with the :ref:`paths <cogmanagerui-command-paths>` command.

.. _cogmanagerui-command-paths:

^^^^^
paths
^^^^^

**Syntax**

.. code-block:: none

    [p]paths

**Description**

Lists the registered cog paths, with the install path for the downloader and
the core path for the core cogs.

.. TODO add ref to downloader

You can use the :ref:`reorderpath <cogmanagerui-command-reorderpath>` command
to reorder the listed paths.

.. tip:: The number before a cog path can be used for the
    :ref:`removepath <cogmanagerui-command-removepath>` command.

.. _cogmanagerui-command-addpath:

^^^^^^^
addpath
^^^^^^^

**Syntax**

.. code-block:: none

    [p]addpath <path>

**Description**

Adds a path to the list of available cog paths. This means that all valid cogs
under the path will be added to the list of available cogs, listed in
:ref:`cogs <cogmanagerui-command-cogs>`.

**Arguments**

*   ``<path>``: A path that should look like this and point to a folder:

    *   Windows: ``C:\Users\username\Documents\MyCogs``
    *   macOS: ``/Users/username/Documents/MyCogs``
    *   Linux: ``/home/username/Documents/MyCogs``

    Try to avoid paths with spaces. If there are spaces, add a backslash before
    the space on Linux. Add quotation marks around the path if needed.

.. _cogmanagerui-command-removepath:

^^^^^^^^^^
removepath
^^^^^^^^^^

**Syntax**

.. code-block:: none

    [p]removepath <path_numbers...>

**Description**

Removes one or more paths from the list of available paths. Its cogs won't be
accessible anymore.

**Arguments**

*   ``<path_numbers>``: The number of the path(s) to remove. You can get it with
    the :ref:`paths <cogmanagerui-command-paths>` command.

.. _cogmanagerui-command-reorderpath:

^^^^^^^^^^^
reorderpath
^^^^^^^^^^^

**Syntax**

.. code-block:: none

    [p]reorderpath <from> <to>

**Description**

Reorders the paths listed with the :ref:`paths <cogmanagerui-command-paths>`
command. The goal of this command is to allow the discovery of different cogs.
If there are multiple packages with the same names, the one that is inside the
highest folder in the list will be kept and the other ones will be ignored.

For example, let's suppose this is the output of
:ref:`paths <cogmanagerui-command-paths>`:

    1.  ``/usr/local/lib/python3.7/site-packages/redbot/cogs``
    2.  ``/home/laggron/custom_cogs``
    3.  ``/mnt/not_suspicious_usb_drive/not_suspicious_cogs``

The folders 2 and 3 both have a package named ``leveler`` while being different
cogs, and you want to load the one located in the 3rd folder. To do that, you
have to put the 3rd path higher than the 2nd path, let's swap them! Type
``[p]reorderpath 2 3`` and the output of
:ref:`paths <cogmanagerui-command-paths>` will then be the following:

    1.  ``/usr/local/lib/python3.7/site-packages/redbot/cogs``
    2.  ``/mnt/not_suspicious_usb_drive/not_suspicious_cogs``
    3.  ``/home/laggron/custom_cogs``

**Arguments**

*   ``<from>``: The index of the path you want to move.
*   ``<to>``: The location where you want to insert the path.

.. _cogmanagerui-command-installpath:

^^^^^^^^^^^
installpath
^^^^^^^^^^^

**Syntax**

.. code-block:: none

    [p]installpath [path]

**Description**

Shows the install path, or sets a new one.

If you want to set a new path, the same rules as for
:ref:`addpath <cogmanagerui-command-addpath>` apply

.. warning:: If you edit the install path, the cogs won't be transferred.

**Arguments**

*   ``[path]``: The absolute path to set. If omitted, the current path will
    be returned instead.
