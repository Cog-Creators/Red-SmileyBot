.. Cog Creator Applications

.. role:: python(code)
    :language: python

================================
Becoming an Approved Cog Creator
================================

This guide serves to explain the Cog Creator Application process and lays out the requirements to be a Cog Creator.

----------------------------------
Creating a Cog Creator Application
----------------------------------

.. note::
  You will need to have created and published your cogs before you create a Cog Creator Application!
  See `guide_cog_creation` and `guide_publish_cogs` for more information.

Cog Creator Applications are hosted on the `cogboard <https://cogboard.discord.red/c/apps/12>`__.
To create an application, start a new topic in the "Applications" category and fill out all of the required information.
QA reviews Cog Creator Applications for security and functionality on a first come, first serve basis.
Once your application is reviewed, you will have 14 days to make any requested changes, or to check in with the member of QA who is reviewing your application.

-----------------------------
Requirements for Cog Creators
-----------------------------

The following is a list of the requirements for approved Cog Creators.
QA uses this list to request changes for Cog Creator Applications.
Handling these requirements before submitting your application can streamline the review process.
Any Cog Creator that does not follow these requirements will have their repo removed from approved listings and may have their Cog Creator status revoked.

- Readme that contains

  - Repository name
  - Installation instructions
  - Extra setup instructions (if applicable)
  - Credits (if applicable)

- Repo-wide ``info.json`` file with the keys

  - ``author``
  - ``short``
  - ``description``

- Cog ``info.json`` files with the keys

  - ``author``
  - ``short``
  - ``requirements`` (if applicable)
  - ``description``
  - ``min_python_version`` (if applicable)

  See `info-json-format` for more information on how to set up ``info.json`` files.

- No cog contains malicious code.
- No cog contains code that could impact the stability of the bot, such as blocking the event loop for an extended period of time, unreasonably high IO usage, etc.
- No cog contains copied code that does not respect the license of the source.
- Disclose in the ``install_msg`` key of the ``info.json`` file of each cog that contains any of the following:

  - Heavy memory or I/O usage.
  - Any NSFW material.
  - Bundled data.
  - Stored data (outside of using Config).
  - Interactions with outside services.
  - Any extra setup instructions required.

- No cog breaks the Discord TOS.
- No cog conflicts with any core cogs (e.g., causing a core cog to fail to load) unless it is intended to replace that cog.
- Your repo shows an understanding of a range of common cog practices. This requirement exists to ensure QA can trust the safety and functionality of any future code you will create. This is handled on a case-by-case basis, however the following points should outline what we are looking to see:

  - Cogs that are more than what is able to be run in a simple eval.
  - Cogs that are more than just a simple API access request.
  - Cogs that properly use Red utilities, for example Config, or any other utility functions.
  - Cogs that use event listeners (bot.wait_for or cog-wide listeners) or custom tasks that are efficient and handle exceptions appropriately.
  - Cogs that handle errors properly.
  - Cogs that handle permissions properly.

  *While we're looking for these things to qualify your code, you don't need to apply all of them in order to qualify.*

- Any unusable or broken commands or cogs are hidden.
- The default locale must be English.
- The main cog class and every command must have a doc-string.
- No cog allows for escalation of permissions. (e.g., sending a mass ping through the bot without having permission to do so)
- Respect the role hierarchy. Don't let a lower role have a way to grant a higher role.
- If your cog install comes with any pre-packaged data, use `bundled_data_path()` to access it.
- If your cog install creates any non-config data, use `cog_data_path()` to store it.
- Unless the cog is intentionally designed to listen to certain input from bots, cogs should ignore input from bots.
- Cogs use public methods of Red where possible.
- Use the proper method if one exists. (and ask for one if it doesn't exist)

  - If that's not possible, don't break anything in core or any other cog with your code.
  - If you have to use private methods, lock the cog to specific Red versions you can guarantee it works on without breaking anything using the ``min_bot_version`` and ``max_bot_version`` keys in that cog's ``info.json`` file.

.. _recommendations-for-cog-creators:

--------------------------------
Recommendations for Cog Creators
--------------------------------

The following is a list of recommendations for Cog Creators.
While not required for approved Cog Creators, they are still recommended in order to ensure consistency between repos.

- Cogs should follow a few naming conventions for consistency.

  - Cog classes should be TitleCased, using alphabetic characters only.
  - Commands should be lower case, using alphanumeric characters only.
  - Cog modules should be lower case, using alphabetic characters only.

- If your cog uses logging:

  - The namespace for logging should be: ``red.your_repo_name.cog_name``.
  - Print statements are not a substitute for proper logging.

- If you use asyncio.create_task, your tasks should:

  - Be cancelled on cog unload.
  - Handle errors.

- | Event listeners should exit early if it is an event you don't need.
  | This makes your events less expensive in terms of CPU time. Examples below:

  - Checking that you are in a guild before interacting with config for an antispam command.
  - Checking that you aren't reacting to a bot message (``not message.author.bot``) early on.

- Use .gitignore (or something else) to keep unwanted files out of your cog repo.
- Put a license on your cog repo.

  - By default, in most jurisdictions, without a license that at least offers the code for use,
    users cannot legally use your code.

- Use botwide features when they apply. Some examples of this:

  - ``ctx.embed_color``
  - ``bot.is_automod_immune``

- Use decorators to limit command use, restrict usage, or define whether the bot needs special permissions.
  You can find all of the permission and cooldown related decorators under the ``redbot.core.commands`` namespace.
- Check against user input before doing things. Common things to check:

  - Resulting output is safe.
  - Values provided make sense. (eg. no negative numbers for payday)
  - Don't unsafely use user input for things like database input.

- Check events against `bot.cog_disabled_in_guild() <Red.cog_disabled_in_guild()>`\

  - Not all events need to be checked, only those that interact with a guild.
  - Some discretion may apply, for example,
    a cog which logs command invocation errors could choose to ignore this
    but a cog which takes actions based on messages should not.

- Respect settings when treating non-command messages as commands.
- Handle user data responsibly

  - Don't do unexpected things with user data.
  - Don't expose user data to additional audiences without permission.
  - Don't collect data your cogs don't need.
  - | Don't store data in unexpected locations.
    | Utilize the cog data path, Config, or if you need something more
      prompt the owner to provide it.

- Utilize the data deletion and statement APIs

  - See `redbot.core.commands.Cog.red_delete_data_for_user()`
  - | Make a statement about what data your cogs use with the module level
      variable ``__red_end_user_data_statement__``.
    | This should be a string containing a user friendly explanation of what data
      your cog stores and why.

- Set contextual locales in events and other background tasks that use i18n APIs

  - See `redbot.core.i18n.set_contextual_locales_from_guild()`
  - Usage of i18n APIs within commands automatically has proper contextual locales set.

----------------------------
Perks of being a Cog Creator
----------------------------

- Added to a growing, curated list of approved repositories hosted on the `Red Index <https://index.discord.red/>`__.
- The Cog Creator role on the main Red Server and the Cog Support Server.
- Access to an additional testing channel and the #advanced-coding channel on the main Red Server.
- Write permission in the #v3-burndown channel on the main Red Server.
- Access to an additional testing channel and the Cog Creators channel on the Support Server.
- Alerted about breaking changes in Red before anyone else.
- Ability to request a channel in the Cog Support Server if you feel like the traffic/question volume for your cogs warrants it.

-------------
Other Details
-------------

- Once a QA member has conducted a final review, you will have up to 14 days to make the necessary changes.
- The reviewer of your application has the final word.
- Hidden cogs will not be explicitly reviewed, however they are not allowed to contain malicious or ToS breaking code.
- QA reserves the right to revoke these roles and all privileges if you are found to be in gross negligence, malicious intent, or reckless abandonment of your repository.
- Cogs must be functionally working to the quality of an approved cog on the latest minor version of Red to be listed on the Red Index. Cogs that are not updated within 1 month of initial breakage will be delisted from the index until they are updated. Examples of potential breakage include, but are not limited to:

  - A dependency without version constraints receiving a breaking update
  - An API changing the schema of its endpoints
  - Red itself releasing a new minor version

- Only 1 person is allowed to be the Cog Creator for a particular repo. Multiple people are allowed to maintain the repo, however the "main" owner (and the Cog Creator) is responsible for any code on the repo.
- The Cog Creator status for a repo can be transferred to another user if the Cog Creator requests it.
- An approved Cog Creator can ask QA to add additional repos they have created to the approved pool.
