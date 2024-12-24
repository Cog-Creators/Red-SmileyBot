.. _streams:

=======
Streams
=======

This is the cog guide for the Streams cog. You will
find detailed docs about usage and commands.

``[p]`` is considered as your prefix.

.. note:: To use this cog, load it by typing this::

        [p]load streams

.. _streams-usage:

-----
Usage
-----

This cog provides commands to check if a channel 
on a supported streaming service is live as well 
as to create and manage alerts for channels.

Supported streaming services are:

- Twitch
- Youtube
- Picarto

Youtube and Twitch both require setting authentication 
details for commands for those services to work. See 
:ref:`[p]streamset twitchtoken <streams-command-streamset-twitchtoken>` and 
:ref:`[p]streamset youtubekey <streams-command-streamset-youtubekey>`
for more information.

.. _streams-commands:

--------
Commands
--------

.. _streams-command-streamset:

^^^^^^^^^
streamset
^^^^^^^^^

**Syntax**

.. code-block:: none
    
    [p]streamset

**Description**

Manage stream alert settings.

.. _streams-command-streamset-autodelete:

^^^^^^^^^^^^^^^^^^^^
streamset autodelete
^^^^^^^^^^^^^^^^^^^^

**Syntax**

.. code-block:: none
    
    [p]streamset autodelete <on_off>

**Description**

Toggles automatic deletion of stream alerts when the 
stream goes offline.

**Arguments**

* ``<on_off>``: Whether to turn on or off

.. _streams-command-streamset-ignorereruns:

^^^^^^^^^^^^^^^^^^^^^^
streamset ignorereruns
^^^^^^^^^^^^^^^^^^^^^^

**Syntax**

.. code-block:: none
    
    [p]streamset ignorereruns

**Description**

Toggles excluding reruns from the alerts.

At this time, this functionality only applies to Twitch stream alerts.

.. _streams-command-streamset-mention:

^^^^^^^^^^^^^^^^^
streamset mention
^^^^^^^^^^^^^^^^^

**Syntax**

.. code-block:: none
    
    [p]streamset mention

**Description**

Toggle mentions for stream alerts.

.. _streams-command-streamset-mention-all:

^^^^^^^^^^^^^^^^^^^^^
streamset mention all
^^^^^^^^^^^^^^^^^^^^^

**Syntax**

.. code-block:: none
    
    [p]streamset mention all

**Description**

Toggle mentioning ``@everyone`` for stream alerts.

.. _streams-command-streamset-mention-online:

^^^^^^^^^^^^^^^^^^^^^^^^
streamset mention online
^^^^^^^^^^^^^^^^^^^^^^^^

**Syntax**

.. code-block:: none
    
    [p]streamset mention online

**Description**

Toggle mentioning ``@here`` for stream alerts.

.. _streams-command-streamset-mention-role:

^^^^^^^^^^^^^^^^^^^^^^
streamset mention role
^^^^^^^^^^^^^^^^^^^^^^

**Syntax**

.. code-block:: none
    
    [p]streamset mention role <role>

**Description**

Toggle mentioning a role for stream alerts.

**Arguments**

* ``<role>``: The role to toggle a mention for. |role-input|

.. _streams-command-streamset-message:

^^^^^^^^^^^^^^^^^
streamset message
^^^^^^^^^^^^^^^^^

**Syntax**

.. code-block:: none
    
    [p]streamset message

**Description**

Manage custom messages for stream alerts.

.. _streams-command-streamset-message-mention:

^^^^^^^^^^^^^^^^^^^^^^^^^
streamset message mention
^^^^^^^^^^^^^^^^^^^^^^^^^

**Syntax**

.. code-block:: none
    
    [p]streamset message mention <message>

**Description**

Sets a stream alert message for when mentions are enabled.

Use ``{mention}`` in the message to insert the selected mentions.

Use ``{stream}`` in the message to insert the channel or user name.

Use ``{stream.display_name}`` in the message to insert the channel's display name
(on Twitch, this may be different from ``{stream}``).

For example: ``[p]streamset message mention {mention}, {stream.display_name} is live!``

**Arguments**

* ``<message>``: Your alert message

.. _streams-command-streamset-message-nomention:

^^^^^^^^^^^^^^^^^^^^^^^^^^^
streamset message nomention
^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Syntax**

.. code-block:: none
    
    [p]streamset message nomention <message>

**Description**

Sets a stream alert message for when mentions are disabled.

Use ``{stream}`` in the message to insert the channel or user name.

Use ``{stream.display_name}`` in the message to insert the channel's display name
(on Twitch, this may be different from ``{stream}``).

For example: ``[p]streamset message nomention {stream.display_name} is live!``

**Arguments**

* ``<message>``: Your alert message

.. _streams-command-streamset-message-clear:

^^^^^^^^^^^^^^^^^^^^^^^
streamset message clear
^^^^^^^^^^^^^^^^^^^^^^^

**Syntax**

.. code-block:: none
    
    [p]streamset message clear

**Description**

Resets the stream alert messages for the server.

.. _streams-command-streamset-timer:

^^^^^^^^^^^^^^^
streamset timer
^^^^^^^^^^^^^^^

**Syntax**

.. code-block:: none
    
    [p]streamset timer <refresh_timer>

**Description**

Sets the refresh time for stream alerts (how frequently they will be checked).

This cannot be set to anything less than 60 seconds.

**Arguments**

* ``<refresh_timer>``: The frequency with which streams should be checked, in seconds

.. _streams-command-streamset-youtubekey:

^^^^^^^^^^^^^^^^^^^^
streamset youtubekey
^^^^^^^^^^^^^^^^^^^^

**Syntax**

.. code-block:: none
    
    [p]streamset youtubekey

**Description**

Explains how to set the YouTube token.

To get one, do the following:

1. Create a project
(see https://support.google.com/googleapi/answer/6251787 for details)

2. Enable the YouTube Data API v3
(see https://support.google.com/googleapi/answer/6158841 for instructions)

3. Set up your API key
(see https://support.google.com/googleapi/answer/6158862 for instructions)

4. Copy your API key and run the command ``[p]set api youtube api_key <your_api_key_here>``

.. attention:: These tokens are sensitive and should only be 
               used in a private channel or in DM with the bot.

.. _streams-command-streamset-twitchtoken:

^^^^^^^^^^^^^^^^^^^^^
streamset twitchtoken
^^^^^^^^^^^^^^^^^^^^^

**Syntax**

.. code-block:: none
    
    [p]streamset twitchtoken

**Description**

Explains how to set the Twitch token.

To set the Twitch API tokens, follow these steps:

1. Go to this page: https://dev.twitch.tv/dashboard/apps.

2. Click Register Your Application.

3. Enter a name, set the OAuth Redirect URI to http://localhost, and select an Application Category of your choosing.

4. Click Register.

5. Copy your client ID and your client secret into:
``[p]set api twitch client_id <your_client_id_here> client_secret <your_client_secret_here>``

.. attention:: These tokens are sensitive and should only be 
               used in a private channel or in DM with the bot.

.. _streams-command-streamset-usebuttons:

^^^^^^^^^^^^^^^^^^^^
streamset usebuttons
^^^^^^^^^^^^^^^^^^^^

**Syntax**

.. code-block:: none

    [p]streamset usebuttons

**Description**

Toggle whether to use buttons for stream alerts.

.. _streams-command-picarto:

^^^^^^^
picarto
^^^^^^^

**Syntax**

.. code-block:: none

    [p]picarto <channel_name>

**Description**

Check if a Picarto channel is live.

**Arguments**

* ``<channel_name>``: The Picarto channel to check.

.. _streams-command-twitchstream:

^^^^^^^^^^^^
twitchstream
^^^^^^^^^^^^

**Syntax**

.. code-block:: none

    [p]twitchstream <channel_name>

**Description**

Check if a Twitch channel is live.

**Arguments**

* ``<channel_name>``: The Twitch channel to check.

.. _streams-command-youtubestream:

^^^^^^^^^^^^^
youtubestream
^^^^^^^^^^^^^

**Syntax**

.. code-block:: none
    
    [p]youtubestream <channel_id_or_name>

**Description**

Check if a YouTube channel is live.

**Arguments**

* ``<channel_id_or_name>``: The name or id of the YouTube channel to be checked.

.. _streams-command-streamalert:

^^^^^^^^^^^
streamalert
^^^^^^^^^^^

**Syntax**

.. code-block:: none
    
    [p]streamalert

**Description**

Manage automated stream alerts.

.. _streams-command-streamalert-list:

^^^^^^^^^^^^^^^^
streamalert list
^^^^^^^^^^^^^^^^

**Syntax**

.. code-block:: none
    
    [p]streamalert list

**Description**

Lists all active alerts in the current server.

.. _streams-command-streamalert-picarto:

^^^^^^^^^^^^^^^^^^^
streamalert picarto
^^^^^^^^^^^^^^^^^^^

**Syntax**

.. code-block:: none
    
    [p]streamalert picarto <channel_name>

**Description**

Toggle alerts in the current channel for the 
specified Picarto channel.

**Arguments**

* ``<channel_name>``: The Picarto channel to toggle the alert for.

.. _streams-command-streamalert-twitch-channel:

^^^^^^^^^^^^^^^^^^^^^^^^^^
streamalert twitch channel
^^^^^^^^^^^^^^^^^^^^^^^^^^

**Syntax**

.. code-block:: none
    
    [p]streamalert twitch channel <channel_name>

**Description**

Toggle alerts in the current channel for the 
specified Twitch channel.

**Arguments**

* ``<channel_name>``: The Twitch channel to toggle the alert for.

.. _streams-command-streamalert-youtube:

^^^^^^^^^^^^^^^^^^^
streamalert youtube
^^^^^^^^^^^^^^^^^^^

**Syntax**

.. code-block:: none
    
    [p]streamalert youtube <channel_name>

**Description**

Toggle alerts in the current channel for the 
specified Picarto channel.

**Arguments**

* ``<channel_id_or_name>``: The name or id of the YouTube channel to be checked.

.. _streams-command-streamalert-stop:

^^^^^^^^^^^^^^^^
streamalert stop
^^^^^^^^^^^^^^^^

**Syntax**

.. code-block:: none
    
    [p]streamalert stop [disable-all=No]

**Description**

Disable all stream alerts for this channel or server.

**Arguments**

* ``[disable-all]``: Defaults to ``no``. If this is set to ``yes``, all 
  stream alerts in the current server will be disabled. 
  If ``no`` or unspecified, all stream alerts in the 
  current channel will be stopped. 
