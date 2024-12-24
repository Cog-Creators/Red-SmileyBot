.. _permissions:

===========
Permissions
===========

This is the cog guide for the permissions cog. You will
find detailed docs about usage and commands.

``[p]`` is considered as your prefix.

.. note:: To use this cog, load it by typing this::

        [p]load permissions

.. _permissions-usage:

-----
Usage
-----

Customise permissions for commands and cogs.

This cog extends the default permission model of the bot. By default, many commands are restricted based on what the command can do.
This cog allows you to refine some of those restrictions. You can allow wider or narrower access to most commands using it. You cannot, however, change the restrictions on owner-only commands.

When additional rules are set using this cog, those rules will be checked prior to checking for the default restrictions of the command.
Global rules (set by the owner) are checked first, then rules set for servers. If multiple global or server rules apply to the case, the order they are checked in is:

1. Rules about a user.
2. Rules about the voice channel a user is in.
3. Rules about the text channel or a parent of the thread a command was issued in.
4. Rules about a role the user has (The highest role they have with a rule will be used).
5. Rules about the server a user is in (Global rules only).


.. _permissions-commands:

--------
Commands
--------

.. _permissions-command-permissions:

^^^^^^^^^^^
permissions
^^^^^^^^^^^

**Syntax**

.. code-block:: none

    [p]permissions 

**Description**

Command permission management tools.

.. _permissions-command-permissions-acl:

"""""""""""""""
permissions acl
"""""""""""""""

.. note:: |guildowner-lock|

**Syntax**

.. code-block:: none

    [p]permissions acl 

**Description**

Manage permissions with YAML files.

.. tip:: See :ref:`here <cog_permissions>` for more information with configuring these yaml files.

.. _permissions-command-permissions-acl-getglobal:

"""""""""""""""""""""""""
permissions acl getglobal
"""""""""""""""""""""""""

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]permissions acl getglobal 

**Description**

Get a YAML file detailing all global rules.

.. _permissions-command-permissions-acl-getserver:

"""""""""""""""""""""""""
permissions acl getserver
"""""""""""""""""""""""""

.. note:: |guildowner-lock|

**Syntax**

.. code-block:: none

    [p]permissions acl getserver 

**Description**

Get a YAML file detailing all rules in this server.

.. _permissions-command-permissions-acl-setglobal:

"""""""""""""""""""""""""
permissions acl setglobal
"""""""""""""""""""""""""

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]permissions acl setglobal 

**Description**

Set global rules with a YAML file.

.. warning::    
    This will override reset *all* global rules
    to the rules specified in the uploaded file.

This does not validate the names of commands and cogs before
setting the new rules.

.. _permissions-command-permissions-acl-setserver:

"""""""""""""""""""""""""
permissions acl setserver
"""""""""""""""""""""""""

.. note:: |guildowner-lock|

**Syntax**

.. code-block:: none

    [p]permissions acl setserver 

**Description**

Set rules for this server with a YAML file.

.. warning::    
    This will override reset *all* rules in this
    server to the rules specified in the uploaded file.

.. _permissions-command-permissions-acl-updateglobal:

""""""""""""""""""""""""""""
permissions acl updateglobal
""""""""""""""""""""""""""""

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]permissions acl updateglobal 

**Description**

Update global rules with a YAML file.

This won't touch any rules not specified in the YAML
file.

.. _permissions-command-permissions-acl-updateserver:

""""""""""""""""""""""""""""
permissions acl updateserver
""""""""""""""""""""""""""""

.. note:: |guildowner-lock|

**Syntax**

.. code-block:: none

    [p]permissions acl updateserver 

**Description**

Update rules for this server with a YAML file.

This won't touch any rules not specified in the YAML
file.

.. _permissions-command-permissions-acl-yamlexample:

"""""""""""""""""""""""""""
permissions acl yamlexample
"""""""""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]permissions acl yamlexample 

**Description**

Sends an example of the yaml layout for permissions

.. _permissions-command-permissions-addglobalrule:

"""""""""""""""""""""""""
permissions addglobalrule
"""""""""""""""""""""""""

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]permissions addglobalrule <allow_or_deny> <cog_or_command> <who_or_what...>

**Description**

Add a global rule to a cog or command.

**Arguments**

* ``<allow_or_deny>``: This should be one of "allow" or "deny".
* ``<cog_or_command>``: The cog or command to add the rule to. This is case sensitive.
* ``<who_or_what...>``: One or more users, channels or roles the rule is for.

.. _permissions-command-permissions-addserverrule:

"""""""""""""""""""""""""
permissions addserverrule
"""""""""""""""""""""""""

.. note:: |guildowner-lock|

**Syntax**

.. code-block:: none

    [p]permissions addserverrule <allow_or_deny> <cog_or_command> <who_or_what...>

**Description**

Add a rule to a cog or command in this server.

**Arguments**

* ``<allow_or_deny>``: This should be one of "allow" or "deny".
* ``<cog_or_command>``: The cog or command to add the rule to. This is case sensitive.
* ``<who_or_what...>``: One or more users, channels or roles the rule is for.

.. _permissions-command-permissions-canrun:

""""""""""""""""""
permissions canrun
""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]permissions canrun <user> <command>

**Description**

Check if a user can run a command.

This will take the current context into account, such as the
server and text channel.

**Arguments**

* ``<user>``: The user to check permissions for.
* ``<command>``: The command to check whether the user can run it or not.

.. _permissions-command-permissions-clearglobalrules:

""""""""""""""""""""""""""""
permissions clearglobalrules
""""""""""""""""""""""""""""

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]permissions clearglobalrules 

**Description**

Reset all global rules.

.. _permissions-command-permissions-clearserverrules:

""""""""""""""""""""""""""""
permissions clearserverrules
""""""""""""""""""""""""""""

.. note:: |guildowner-lock|

**Syntax**

.. code-block:: none

    [p]permissions clearserverrules 

**Description**

Reset all rules in this server.

.. _permissions-command-permissions-explain:

"""""""""""""""""""
permissions explain
"""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]permissions explain 

**Description**

Explain how permissions works.

.. _permissions-command-permissions-removeglobalrule:

""""""""""""""""""""""""""""
permissions removeglobalrule
""""""""""""""""""""""""""""

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]permissions removeglobalrule <cog_or_command> <who_or_what...>

**Description**

Remove a global rule from a command.

**Arguments**

* ``<cog_or_command>``: The cog or command to remove the rule from. This is case sensitive.
* ``<who_or_what...>``: One or more users, channels or roles the rule is for.

.. _permissions-command-permissions-removeserverrule:

""""""""""""""""""""""""""""
permissions removeserverrule
""""""""""""""""""""""""""""

.. note:: |guildowner-lock|

**Syntax**

.. code-block:: none

    [p]permissions removeserverrule <cog_or_command> <who_or_what...>

**Description**

Remove a server rule from a command.

**Arguments**

* ``<cog_or_command>``: The cog or command to remove the rule from. This is case sensitive.
* ``<who_or_what...>``: One or more users, channels or roles the rule is for.

.. _permissions-command-permissions-setdefaultglobalrule:

""""""""""""""""""""""""""""""""
permissions setdefaultglobalrule
""""""""""""""""""""""""""""""""

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]permissions setdefaultglobalrule <allow_or_deny> <cog_or_command>

**Description**

Set the default global rule for a command or a cog.

This is the rule a command will default to when no other rule
is found.

**Arguments**

* ``<cog_or_command>``: The cog or command to add the rule to. This is case sensitive.
* ``<who_or_what...>``: One or more users, channels or roles the rule is for.

.. _permissions-command-permissions-setdefaultserverrule:

""""""""""""""""""""""""""""""""
permissions setdefaultserverrule
""""""""""""""""""""""""""""""""

.. note:: |guildowner-lock|

**Syntax**

.. code-block:: none

    [p]permissions setdefaultserverrule <allow_or_deny> <cog_or_command>

**Description**

Set the default rule for a command or a cog in this server.

This is the rule a command will default to when no other rule
is found.

**Arguments**

* ``<cog_or_command>``: The cog or command to add the rule to. This is case sensitive.
* ``<who_or_what...>``: One or more users, channels or roles the rule is for.
