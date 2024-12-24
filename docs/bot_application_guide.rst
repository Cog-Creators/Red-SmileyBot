===========================================
Creating a bot account
===========================================

To use Red you will require a bot account and to enable privileged intents. Both these steps will be covered below.

.. _creating-a-bot-account:

-------------------------------
Creating the bot application
-------------------------------

In order to use Red, we must first create a Discord Bot account.

Creating a Bot account is a pretty straightforward process.

1. Make sure you're logged on to the `Discord website <https://discord.com>`_.
2. Navigate to the `application page <https://discord.com/developers/applications>`_
3. Click on the "New Application" button.

    .. image:: /.resources/bot-guide/discord_create_app_button.png
        :alt: The new application button.

4. Give the application a name and click "Create".

    .. image::  /.resources/bot-guide/discord_create_app_form.png
        :alt: The new application form filled in.

5. Create a Bot User by navigating to the "Bot" tab and clicking "Add Bot".

    - Click "Yes, do it!" to continue.

    .. image::  /.resources/bot-guide/discord_create_bot_user.png
        :alt: The Add Bot button.
6. If you want others to be able to invite your bot tick the **Public Bot**. Keeping it unticked will prevent others from inviting your bot to their servers and only you will be able to add the bot to servers (provided that you have needed permissions in the server you want to add the bot to).

    - Make sure **Require OAuth2 Code Grant** is unchecked.

    .. image::  /.resources/bot-guide/discord_bot_user_options.png
        :alt: How the Bot User options should look like for most people.

7. Copy the token using the "Copy" button.

    - **This is not the Client Secret at the General Information page**

    .. warning::

        Do not share your token as it is like your password.
        If you shared your token you can regenerate it.

Continue to the next section to enable privileged intents.

.. _enabling-privileged-intents:

-------------------------------
Enabling Privileged Intents
-------------------------------
.. warning::
    :ref:`Red Bot requires all intents. <intents>`
    \This section is required.

1. Make sure you're logged on to the `Discord website <https://discord.com>`_.
2. Navigate to the `application page <https://discord.com/developers/applications>`_
3. Click on the bot you want to enable privileged intents for.
4. Navigate to the bot tab on the left side of the screen.

    .. image:: /.resources/bot-guide/discord_bot_tab.png
        :alt: The bot tab in the application page.

5. Scroll down to the "Privileged Gateway Intents" section, enable all three privileged intents and save your changes.

    .. image:: /.resources/bot-guide/discord_privileged_intents.png
        :alt: The privileged gateway intents selector.

.. warning::

    Red bots with over 100 servers require `bot verification <https://support.discord.com/hc/en-us/articles/360040720412>`_ which is not covered in this guide.
    Remember that :ref:`we do not support public bots <intents>`. We encourage you to read that page before scaling up your bot.

*Parts of this guide have been adapted from* `discord.py intro <https://discordpy.readthedocs.io/en/stable/discord.html#discord-intro>`_ *and* `discord.py privileged intents <https://discordpy.readthedocs.io/en/stable/intents.html#privileged-intents>`_.
