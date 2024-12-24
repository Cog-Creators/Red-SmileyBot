.. _reports:

=======
Reports
=======

This is the cog guide for the reports cog. You will
find detailed docs about usage and commands.

``[p]`` is considered as your prefix.

.. note:: To use this cog, load it by typing this::

        [p]load reports

.. _reports-usage:

-----
Usage
-----

Create user reports that server staff can respond to.

Users can open reports using ``[p]report``. These are then sent
to a channel in the server for staff, and the report creator
gets a DM. Both can be used to communicate.


.. _reports-commands:

--------
Commands
--------

.. _reports-command-report:

^^^^^^
report
^^^^^^

**Syntax**

.. code-block:: none

    [p]report [text]

**Description**

Send a report.

Use without arguments for interactive reporting, or do
``[p]report [text]`` to use it non-interactively.

**Arguments**

* ``[text]``: The content included within the report.

.. _reports-command-report-interact:

"""""""""""""""
report interact
"""""""""""""""

.. note:: |mod-lock|

**Syntax**

.. code-block:: none

    [p]report interact <ticket_number>

**Description**

Open a message tunnel.

This tunnel will forward things you say in this channel or thread
to the ticket opener's direct messages.

Tunnels do not persist across bot restarts.

**Arguments**

* ``<ticket_number>``: The ticket number to open the tunnel in.

.. _reports-command-reportset:

^^^^^^^^^
reportset
^^^^^^^^^

.. note:: |admin-lock|

**Syntax**

.. code-block:: none

    [p]reportset 

**Description**

Manage Reports.

.. _reports-command-reportset-output:

""""""""""""""""
reportset output
""""""""""""""""

.. note:: |admin-lock|

**Syntax**

.. code-block:: none

    [p]reportset output <channel>

**Description**

Set the channel where reports will be sent.

**Arguments**

* ``<channel>``: |channel-input|

.. _reports-command-reportset-toggle:

""""""""""""""""
reportset toggle
""""""""""""""""

.. note:: |admin-lock|

**Syntax**

.. code-block:: none

    [p]reportset toggle 

**Description**

Enable or disable reporting for this server.  
