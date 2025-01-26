.. _modlog:

======
ModLog
======

This is the cog guide for the modlog cog. You will
find detailed docs about usage and commands.

``[p]`` is considered as your prefix.

.. note:: To use this cog, load it by typing this::

        [p]load modlog

.. _modlog-usage:

-----
Usage
-----

Browse and manage modlog cases. To manage modlog settings, use ``[p]modlogset``.


.. _modlog-commands:

--------
Commands
--------

.. _modlog-command-case:

^^^^
case
^^^^

**Syntax**

.. code-block:: none

    [p]case <number>

**Description**

Show the specified case.

**Arguments**

* ``<case>``: The case number to get information for.

.. _modlog-command-casesfor:

^^^^^^^^
casesfor
^^^^^^^^

**Syntax**

.. code-block:: none

    [p]casesfor <member>

**Description**

Display cases for the specified member.

**Arguments**

* ``<member>``: The member to get cases for. |member-input|

.. _modlog-command-listcases:

^^^^^^^^^
listcases
^^^^^^^^^

**Syntax**

.. code-block:: none

    [p]listcases <member>

**Description**

List cases for the specified member.

**Arguments**

* ``<member>``: The member to get cases for. |member-input|

.. _modlog-command-reason:

^^^^^^
reason
^^^^^^

**Syntax**

.. code-block:: none

    [p]reason [case] <reason>

**Description**

Specify a reason for a modlog case.

Please note that you can only edit cases you are
the owner of unless you are a mod, admin or server owner.

**Arguments**

* ``[case]``: The case number to update the reason for.
* ``<reason>``: The new reason for the specified case.

.. note:: If no case number is specified, the latest case will be used.
