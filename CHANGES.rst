.. Red changelogs

Redbot 3.5.13 (2024-08-27)
==========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`aikaterna`, :ghuser:`Guyonsteroids`, :ghuser:`Jackenmen`, :ghuser:`Kowlin`

Read before updating
--------------------

#. Information for Audio users that are using an external Lavalink instance (if you don't know what that is, you should skip this point):

    We've updated our default application.yml file and you should update your instance's ``application.yml`` accordingly.
    More specifically, we bumped the version of YT source plugin.
    `Download Red 3.5.13's default application.yml file <https://github.com/Cog-Creators/Red-DiscordBot/releases/download/3.5.13/Red-DiscordBot-3.5.13-default-lavalink-application.yml>`__

End-user changelog
------------------

Changes
*******

- **Core - Dependencies** - Red's dependencies have been bumped (:issue:`6436`)

Fixes
*****

- **Cogs - Audio** - Updated Audio to support planned changes to Discord API scheduled for November (:issue:`6435`)
- **Cogs - Audio** - Fixed YT live stream detection (:issue:`6435`)
- **Cogs - Audio** - Fixed Red erroneously trying to send a message to a notification channel when one is not set (:issue:`6429`)
- **Cogs - Trivia - Lists** - Fixed spelling of Steven Spielberg's first name in the ``entertainment`` trivia list (:issue:`6434`)

----

Redbot 3.5.12 (2024-08-08)
==========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`aikaterna`, :ghuser:`Jackenmen`

Read before updating
--------------------

#. Information for Audio users that are using an external Lavalink instance (if you don't know what that is, you should skip this point):

    We've updated our default application.yml file and you should update your instance's ``application.yml`` accordingly.
    More specifically, we bumped the version of YT source plugin.
    `Download Red 3.5.12's default application.yml file <https://github.com/Cog-Creators/Red-DiscordBot/releases/download/3.5.12/Red-DiscordBot-3.5.12-default-lavalink-application.yml>`__

End-user changelog
------------------

Fixes
*****

- **Cogs - Audio** - Fixed the ``[p]llset secured`` command failing to send the response message (:issue:`6423`)
- **Cogs - Audio** - Fixed some age-restricted YT tracks not playing (:issue:`6424`)

----

Redbot 3.5.11 (2024-08-04)
==========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`aikaterna`, :ghuser:`anopem`, :ghuser:`Flame442`, :ghuser:`japandotorg`, :ghuser:`Jackenmen`, :ghuser:`Kowlin`, :ghuser:`palmtree5`, :ghuser:`yamikaitou`

Read before updating
--------------------

#. Information for Audio users that are using an external Lavalink instance (if you don't know what that is, you should skip this point):

    We've updated our default application.yml file and you should update your instance's ``application.yml`` accordingly.
    More specifically, we bumped the version of YT source plugin and added new plugin configuration.
    `Download Red 3.5.11's default application.yml file <https://github.com/Cog-Creators/Red-DiscordBot/releases/download/3.5.11/Red-DiscordBot-3.5.11-default-lavalink-application.yml>`__

End-user changelog
------------------

Changes
*******

- **Core** - Menus sent in ephemeral messages will now be deleted the same way menus in normal messages do (:issue:`6304`)
- **Core - Dependencies** - Red's dependencies have been bumped (:issue:`6417`)

Fixes
*****

- **Core - RPC** - RPC is now forcefully shut down after 2 minutes, if it cannot shutdown gracefully (:issue:`6391`, :issue:`6412`)
- |cool| **Cogs - Audio** - Fixed some of the recent YT playback issues (:issue:`6414`, :issue:`6415`)
- **Cogs - Mutes** - Fixed the cog failing to unmute a user, if they were muted by someone who no longer has permissions to mute that user (:issue:`6376`, :issue:`6411`)
- **Cogs - Streams** - Fixed the viewer count for Twitch streams (:issue:`6413`)

Developer changelog
-------------------

Additions
*********

- **Core - App Commands Package** - Added `app_commands.UserFeedbackCheckFailure` exception allowing the cog creators to return non-default error message when the check fails (:issue:`6397`)

Documentation changes
---------------------

Changes
*******

- Updated instructions for installing the development version of Red in `guide_cog_creation` (:issue:`6408`)
- Updated the contents of the ``red.plist`` file in the `autostart_mac` document to use no resource limitations, same as regular applications (:issue:`6416`)

----

Redbot 3.5.10 (2024-07-10)
==========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`aikaterna`, :ghuser:`Flame442`, :ghuser:`Jackenmen`, :ghuser:`Kowlin`, :ghuser:`SeaswimmerTheFsh`, :ghuser:`TrustyJAID`, :ghuser:`yamikaitou`

Read before updating
--------------------

#. This release fixes a security issue in one of the APIs we provide for 3rd-party cog creators. See `Security changelog below <important-3510-1>` for more information.
#. Following operating systems are no longer supported as they have already reached their end of life:

    - CentOS 7
    - CentOS Stream 8
    - Fedora 38
    - versions of RHEL/Alma Linux/Oracle Linux/Rocky Linux 8 older than 8.8
    - versions of RHEL/Alma Linux/Oracle Linux/Rocky Linux 9 older than 9.2

#. Information for Audio users that are using an external Lavalink instance (if you don't know what that is, you should skip this point):

    We've updated our default application.yml file and you should update your instance's ``application.yml`` accordingly.
    More specifically, we switched from using the built-in YT source to YT source plugin.
    `Download Red 3.5.10's default application.yml file <https://github.com/Cog-Creators/Red-DiscordBot/releases/download/3.5.10/Red-DiscordBot-3.5.10-default-lavalink-application.yml>`__

End-user changelog
------------------

.. _important-3510-1:

Security
********

- **Core** - Fixed incorrect authorization in one of the utilities provided to 3rd-party cog creators (`commands.can_manage_channel()`) resulting in anyone being authorized to run a command using it, if the command has no other permission controls. None of the core commands or core cogs are affected. The maintainers of the project are not aware of any public 3rd-party cog utilizing this API at the time of writing this changelog. `Full security advisory can be found on our GitHub <https://github.com/Cog-Creators/Red-DiscordBot/security/advisories/GHSA-5jq8-q6rj-9gq4>`__.

Additions
*********

- **Core - Bot Commands** - Added ``[p]set bot banner`` command for setting the bot's banner (:issue:`6321`, :issue:`6401`)

Changes
*******

- **Core** - Red's ``--team-members-are-owners`` flag now only considers Team Owner, Admins, and Developers as bot owners (:issue:`6401`)
- **Core - Dependencies** - Red's dependencies have been bumped (:issue:`6402`)
- **Cogs - Audio** - Updated the cog to configure managed Lavalink node to use YT source plugin instead of the built-in, no longer supported, implementation (:issue:`6373`)
- **Cogs - Filter** - The cog now checks poll contents and attachment alt text for filtered words (:issue:`6401`)

Fixes
*****

- **Core** - Fixed command autocompletion not showing any proper result (error message) when bot's global checks (channel/server ignores, allowlist/blocklist) do not pass (:issue:`6374`, :issue:`6375`)
- **Cogs - Audio** - Fixed one of the recent YT playback issues (:issue:`6373`)

Developer changelog
-------------------

Changes
*******

- |cool| **Core - Dependencies** - Bumped ``discord.py`` to version 2.4.0 (:issue:`6401`)

Documentation changes
---------------------

Additions
*********

- Added Ubuntu 24.04 install guide (:issue:`6364`)

Changes
*******

- Bumped Python version used by Arch Linux, RHEL 8, and RHEL 9 install guides to 3.11 (:issue:`6386`)
- Removed a mention of the Atom editor from the list of the recommended editor now that it's discontinued (:issue:`6388`)

Removals
********

- Removed all mentions of pyenv now that the last OS using it (CentOS 7) is no longer supported (:issue:`6386`)

Fixes
*****

- Fixed Java instructions in macOS install guide (:issue:`6368`)
- Fixed list of required ``info.json`` keys from the `guide_cog_creators` document (:issue:`6382`)

----

Redbot 3.5.9 (2024-04-21)
=========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`aikaterna`, :ghuser:`giplgwm`, :ghuser:`Jackenmen`, :ghuser:`Kuro-Rui`, :ghuser:`Kowlin`, :ghuser:`palmtree5`, :ghuser:`TrustyJAID`, :ghuser:`Zephyrkul`

Read before updating
--------------------

#. Information for Audio users that are using an external Lavalink instance (if you don't know what that is, you should skip this point):

    Red 3.5.9 uses a new Lavalink jar that you will need to manually update from `our GitHub <https://github.com/Cog-Creators/Lavalink-Jars/releases/tag/3.7.11%2Bred.3>`__.

End-user changelog
------------------

Fixes
*****

- **Core** - Fixed inaccuracies in error messages shown when the user passes a time duration outside accepted range (:issue:`6357`)
- **Core** - Commands that ask the user to "Type ``more`` to continue" when they return long output will now typically wait for 60 seconds rather than just 15 (:issue:`6346`, :issue:`6352`)
- |cool| **Cogs - Audio** - Resolved recent issues where the player would be stuck at 0:00 on some tracks (:issue:`6358`)
- **Cogs - Mutes** - The Mutes cog will no longer erroneously accept very large values (i.e. hundreds of years) for mute durations (:issue:`6353`)
- **Cogs - Mutes** - To avoid ambiguity, the Mutes cog will now parse the time only when it's placed at the beginning, the end, or directly after ``t=``/``time=`` prefix in the mute command arguments (:issue:`6274`, :issue:`6349`)
- **Cogs - Streams** - The schedule announcements for YT streams will now use relative Discord timestamps (:issue:`6257`, :issue:`6264`)

Developer changelog
-------------------

Changes
*******

- **Core - Commands Package** - Functions and converters for parsing text into `datetime.timedelta` or `dateutil.relativedelta.relativedelta` in the `redbot.core.commands.converter` package now support negative values when ``minimum`` parameter is set accordingly (:issue:`6349`)
- **Core - Utils Package** - The `redbot.core.utils.chat_formatting.humanize_timedelta()` function now allows specifying the maximum number of different units that will be present in the final string with the ``maximum_units`` parameter (:issue:`6350`)
- **Core - Utils Package** - The `redbot.core.utils.chat_formatting.humanize_timedelta()` function now supports formatting negative `datetime.timedelta` instances. New ``negative_format`` parameter was added to allow specifying a different way of formatting negative `datetime.timedelta` instances (:issue:`6350`)

Documentation changes
---------------------

Fixes
*****

- Updated links to the Lavalink repository (:issue:`6356`)

----

Redbot 3.5.8 (2024-04-01)
=========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`aikaterna`, :ghuser:`Flame442`, :ghuser:`Jackenmen`, :ghuser:`Kreusada`, :ghuser:`TrustyJAID`

Read before updating
--------------------

#. Server-wide mutes in the Mutes cog can no longer be performed using channel permissions (overrides). Instead, the cog will now use Discord's native server timeout functionality when a mute role is not set. Role mutes and channel-specific mutes are not affected.

    Red 3.5.7 and lower allowed usage of channel permissions (overrides) for server-wide mutes when ``[p]muteset forcerole`` setting was explicitly disabled and no mute role was set for the server. This behavior is no longer available and now, when mute role is not set, server-wide mutes will be performed using Discord's native server timeouts.

    If you were one of the few users that chose to use channel permissions (overrides) for server-wide mutes, please note that the existing server mutes will now be considered channel-specific mutes and can only be removed with ``[p]channelunmute`` (and will be automatically removed after timeout elapses, if they have one set). If you want to quickly remove all channel-specific mutes (that were previously server-wide mutes) for a user, you can use the hidden ``[p]forceunmute <user>`` command that has been provided to ease the migration.

#. Information for Audio users that are using an external Lavalink instance (if you don't know what that is, you should skip this point):

    Red 3.5.8 uses a new Lavalink jar that you will need to manually update from `our GitHub <https://github.com/Cog-Creators/Lavalink-Jars/releases/tag/3.7.11%2Bred.2>`__.

End-user changelog
------------------

Additions
*********

- |cool| **Cogs - Mutes** - Added support for Discord's native server timeouts. The cog will now use those when a mute role is not set or, when the new ``[p]timeout`` command is used (:issue:`5604`)
- **Cogs - Trivia** - Trivia lists can now have a description as documented in :ref:`guide_trivia_list_creation` (:issue:`5897`)
- |cool| **Cogs - Trivia** - Added ``[p]trivia info`` command for getting information about the specified Trivia list, including its setting overrides (:issue:`3978`, :issue:`5897`)

Changes
*******

- **Core - Bot Commands** - The ``[p]addpath`` command will now detect potentially incorrect paths and prompt for confirmation (:issue:`6330`)
- **Core - Bot Commands** - The ``[p]addpath`` command will now error out when the user tries adding a path that's part of the core path or instance's data path (:issue:`6330`)
- **Core - Dependencies** - Red's dependencies have been bumped (:issue:`6333`)
- **Cogs - Audio** - The cog will now log the reason for Lavalink.jar being re-downloaded (:issue:`6334`)
- |cool| **Cogs - Mutes** - The ``[p]activemutes`` command will now use menus for pagination (:issue:`6266`)

Removals
********

- **Cogs - Mutes** - Server-wide mutes can no longer be performed using channel permissions (overrides). Server timeouts or mute role can be used instead (:issue:`5604`)
- **Cogs - Mutes** - The ``[p]muteset forcerole`` command and the setting it adjusted has been removed. Server timeouts will now be used for a server, if it has no mute role set (:issue:`5604`)

Fixes
*****

- |cool| **Cogs - Audio** - Resolves recent issues where the wrong video was served for YT playback (:issue:`6337`, :issue:`6340`)
- **Cogs - Audio** - Fixed Lavalink.jar downloading for RC and Red-specific versions (:issue:`6334`)

Documentation changes
---------------------

Additions
*********

- |cool| Added install instructions for Amazon Linux 2023 (:issue:`6331`)

----

Redbot 3.5.7 (2024-03-24)
=========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`aikaterna`, :ghuser:`Flame442`, :ghuser:`karlsbjorn`, :ghuser:`Jackenmen`

This is a hotfix release fixing a bug with Red's reaction-based menus introduced in the previous release.

End-user changelog
------------------

Fixes
*****

- **Core** - Fixed an issue with Red's reaction-based menus *with custom controls* not working properly (:issue:`6324`)
- **Core - Bot Commands** - Updated supported image formats in ``[p]set bot avatar``'s error messages to include GIFs (:issue:`6323`)

----

Redbot 3.5.6 (2024-03-22)
=========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`aikaterna`, :ghuser:`BlizzardTheWolf`, :ghuser:`DJTOMATO`, :ghuser:`Dav-Git`, :ghuser:`Flame442`, :ghuser:`goettner`, :ghuser:`Jackenmen`, :ghuser:`Jan200101`, :ghuser:`japandotorg`, :ghuser:`Kowlin`, :ghuser:`Kreusada`, :ghuser:`laggron42`, :ghuser:`madebylydia`, :ghuser:`michael-is-qcde`, :ghuser:`scarecr0w12`, :ghuser:`yeetbruises`, :ghuser:`Zephyrkul`

Read before updating
--------------------

#. macOS 11 (Big Sur), Fedora 37, Ubuntu 22.10 (Kinetic Kudu), 23.04 (Lunar Lobster), openSUSE Leap 15.4, and Raspberry Pi OS (Legacy) 10 Buster are no longer supported as they have already reached their end of life.
#. Information for Audio users that are using an external Lavalink instance (if you don't know what that is, you should skip this point):

    Red 3.5.6 uses a new Lavalink jar that you will need to manually update from `our GitHub <https://github.com/Cog-Creators/Lavalink-Jars/releases/tag/3.7.11>`__.

End-user changelog
------------------

Additions
*********

- **Cogs - Trivia - Lists** - Added a ``doom`` trivia about the whole Doom video game franchise (:issue:`4803`)
- **Cogs - Trivia - Lists** - Added a trivia about Star Trek (:issue:`2946`)

Changes
*******

- Improved handling of very large numbers in various areas of the bot (:issue:`4619`, :issue:`6283`)
- **Core** - Empty (server) prefixes are now disallowed (:issue:`6013`)
- |cool| **Core** - Menu-based help will now be sent to DMs when max number of pages (``[p]helpset maxpages``) is set to 0, similarly to non-menu help (:issue:`5093`, :issue:`5375`)
- |cool| **Core** - Prefix can now be automatically inserted into help tagline by putting ``[p]`` at the position that the prefix should appear at (:issue:`4669`, :issue:`4972`)
- **Core - Command-line Interfaces** - Improved first-time user experience when setting up new instance by asking for confirmation after user enters the prefix (:issue:`6287`)
- **Core - Dependencies** - Red's dependencies have been bumped (:issue:`6312`)
- **Core - Modlog** - Case auto-creation for bans and unbans now relies directly on recently introduced audit log events which should make it work more reliably (:issue:`5970`)
- |cool| **Cogs - Alias** - Fixed a long-known issue with aliases not retaining new lines from the arguments they are passed (:issue:`2704`, :issue:`4656`)
- **Cogs - Downloader** - Downloader commands will now try to detect potential Git authentication failures and report them more clearly (:issue:`5420`)
- **Cogs - Modlog** - The cog help now mentions how the user can change the modlog settings (:issue:`6300`)
- **Cogs - Trivia - Lists** - Updated FIFA World Cup list to include outcomes of the 2022 tournament (:issue:`5931`)

Removals
********

- **Core - OS Support** - macOS 11 (Big Sur), Fedora 37, Ubuntu 22.10 (Kinetic Kudu), 23.04 (Lunar Lobster), openSUSE Leap 15.4, and Raspberry Pi OS (Legacy) 10 Buster are no longer supported as they have already reached end of life (:issue:`6309`)

Fixes
*****

- **Cogs - Admin** - Fixed the ``[p]editrole colour`` command erroring out whenever it's ran (:issue:`6270`)
- |cool| **Cogs - Audio** - Fixed YT playback (:issue:`6305`)
- **Cogs - Audio** - Fixed not being able to seek when player is paused (:issue:`6305`)
- **Cogs - Audio** - Fixed handling of file name suffixes in ``[p]playlist upload`` caused by changes in Discord API (:issue:`6279`, :issue:`6280`)
- |cool| **Cogs - General** - Fixed issues with ``[p]lmgtfy`` command once and for all by deploying an equivalent service as part of Cog-Creators' infrastructure (:issue:`6255`, :issue:`6268`, :issue:`6269`)
- **Cogs - Streams** - Fixed markdown formatting in the ``[p]streamalert list`` command to be compliant with newer Discord markdown renderer (:issue:`6292`)

Developer changelog
-------------------

Changes
*******

- **Core - Utils Package** - Added `SimpleMenu.start_dm()` method for sending the menu to the given user rather than `Context` (:issue:`6286`)
- **Core - Utils Package** - The `menu()` utility function received a new `provisional <developer-guarantees-exclusions>` ``user`` parameter for defining who can interact with the menu (instead of the default ``ctx.author``) (:issue:`4913`)

    If no issues arise, we plan on including this parameter under developer guarantees
    in the first release made after 2024-05-24.

- **Core - Utils Package** - The `SimpleMenu.start()` method received a new `provisional <developer-guarantees-exclusions>` ``user`` parameter for defining who can interact with the menu (instead of the default ``ctx.author``) (:issue:`4913`)

    If no issues arise, we plan on including this parameter under developer guarantees
    in the first release made after 2024-05-24.

Fixes
*****

- **Core - Commands Package** - Fixed an edge case where the permission names passed as keyword arguments were not validated in Red's custom decorators (:issue:`6291`)
- **Core - Utils Package** - Tracebacks from custom control functions are no longer suppressed by ``menu()`` when ``[p]set usebuttons`` option is enabled (:issue:`6310`)

Documentation changes
---------------------

Additions
*********

- |cool| Added install guide for Raspberry Pi OS 12 Bookworm (:issue:`6309`)
- Added a tip in `guide_slash_and_interactions` about forcing the client to see the new commands after syncing (:issue:`6298`)

Changes
*******

- Install guide for Raspberry Pi OS Legacy now describes installation for Raspberry Pi OS (Legacy) 11 (:issue:`6309`)
- Updated Python versions used in Arch Linux and openSUSE Leap instructions to 3.10 and 3.11 respectively (:issue:`6309`)
- Clarified the meaning of the word `"provisional" <developer-guarantees-exclusions>` that is used across the documentation to refer to APIs excluded from version guarantees (:issue:`6311`)
- Added ``force_registration=True`` to all `Config.get_conf()` usage examples in `framework_config` documentation to reflect our current recommendations (:issue:`6259`)

Fixes
*****

- Fixed the "Edit on GitHub" links in Red's online documentation (:issue:`6258`)

----

Redbot 3.5.5 (2023-09-14)
=========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`Flame442`, :ghuser:`Jackenmen`, :ghuser:`karlsbjorn`, :ghuser:`Kreusada`, :ghuser:`ltzmax`, :ghuser:`palmtree5`

End-user changelog
------------------

Changes
*******

- **Core - Dependencies** - Red's dependencies have been bumped (:issue:`6248`)
- **Cogs - Downloader** - Cogs in the ``[p]cog list`` command are now listed alphabetically (:issue:`6214`, :issue:`6215`)

Fixes
*****

- **Core - Bot Commands** - Fixed handling of an edge case in the ``[p]diagnoseissues`` command that involved commands without a cog (:issue:`6237`)
- **Core - Bot Commands** - Fixed the formatting of nested result lists in the ``[p]diagnoseissues`` command (:issue:`6238`)
- **Cogs - Mod** - Fixed the formatting of the help description for the ``[p]ban``, ``[p]kick``, and ``[p]tempban`` commands (:issue:`6245`)
- |cool| **Cogs - Streams** - Updated the implementation of Twitch streams to no longer use the "Get Users Follows" endpoint that was deprecated in February 2023 (:issue:`6246`, :issue:`6247`)

Documentation changes
---------------------

Changes
*******

- Updated Python version in ``pyenv`` instructions (:issue:`6241`)

----

Redbot 3.5.4 (2023-08-12)
=========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`aikaterna`, :ghuser:`Jackenmen`, :ghuser:`laggron42`, :ghuser:`Leo40Git`, :ghuser:`PredaaA`, :ghuser:`TrustyJAID`

Read before updating
--------------------

#. Information for Audio users that are using an external Lavalink instance (if you don't know what that is, you should skip this point):

    Red 3.5.4 uses a new Lavalink jar that you will need to manually update from `our GitHub <https://github.com/Cog-Creators/Lavalink-Jars/releases/tag/3.7.8>`__.

End-user changelog
------------------

Additions
*********

- |cool| **Core - Bot Commands** - Added ``[p]set status custom`` command allowing the bot owner to change the bot's custom status (:issue:`6226`)

Changes
*******

- **Core - Dependencies** - Red's dependencies have been bumped (:issue:`6225`)

Fixes
*****

- **Core** - Fixed errors showing in logs when the button menu timed out and the original message no longer existed (:issue:`6228`, :issue:`6229`)
- |cool| **Cogs - Audio** - Fixed YT playback (:issue:`6221`)
- **Cogs - Audio** - Fixed poor quality of ``[p]local/queue search``'s results when case sensitive matching was involved (:issue:`6129`, :issue:`6224`)
- **Cogs - Audio** - Fixed ``[p]local search`` resorting to YT playback when file name involved certain characters such as ``-`` (:issue:`6223`)
- **Cogs - CustomCommands** - Fixed poor quality of ``[p]customcom search``'s results when case sensitive matching was involved (:issue:`6224`)
- **Cogs - Streams** - Fixed Picarto channels showing without the channel avatar (:issue:`6230`)

----

Redbot 3.5.3 (2023-07-24)
=========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`AAA3A-AAA3A`, :ghuser:`aikaterna`, :ghuser:`Drapersniper`, :ghuser:`Flame442`, :ghuser:`flaree`, :ghuser:`Jackenmen`, :ghuser:`Kowlin`, :ghuser:`Kreusada`, :ghuser:`Om1609`, :ghuser:`PredaaA`, :ghuser:`TrustyJAID`, :ghuser:`Zephyrkul`

Read before updating
--------------------

#. Fedora 36, Ubuntu 18.04 LTS and versions of RHEL/Alma Linux/Oracle Linux/Rocky Linux older than 8.6 are no longer supported as they have already reached their end of life.

End-user changelog
------------------

Changes
*******

- |cool| Red has been updated to support `Discord's new username system <https://discord.com/blog/usernames>`__ (:issue:`6130`)

  This means that we now support passing the new usernames as arguments
  and properly display usernames/global display names in core commands and cogs where applicable.

- **Core** - All bots are are now considered to be immune to auto-moderation (:issue:`6130`)
- **Core** - Added list of command-line arguments to ``redbot --debuginfo <instance_name>`` and ``[p]debuginfo`` (:issue:`6164`)
- **Core - Bot Commands** - The ``[p]set api`` command will now hide the button once the time to open the modal to set API keys elapses (:issue:`6166`)
- **Core - Command-line Interfaces** - Multiple arguments to ``--co-owner``, ``--load-cogs``, and ``--unload-cogs`` flags can now be specified both by passing multiple arguments right after the flag and by repeating the flag multiple times with different arguments (:issue:`6200`)
- **Core - Dependencies** - Red's dependencies have been bumped (:issue:`6185`)
- |cool| **Cogs - Audio** - The managed Lavalink server can now be run with either Java 11 or Java 17 (:issue:`6190`)
- **Cogs - Audio** - Added an option to auto-use default HTTP/HTTPS port for unmanaged Lavalink server (:issue:`5629`)
- **Cogs - Mod** - The cog now tracks both the usernames *and* global display names (:issue:`6130`)

Removals
********

- **Core - OS Support** - Fedora 36, Ubuntu 18.04 LTS and versions of RHEL/Alma Linux/Oracle Linux/Rocky Linux older than 8.6 are no longer supported as they have already reached end of life (:issue:`6189`)

Fixes
*****

- **Core** - Red's menu timeout is now consistent between reaction and button menus (:issue:`6173`)
- **Core - Bot Commands** - Fixed message too long error in the ``[p]slash list`` command (:issue:`6167`)
- **Core - Command-line Interfaces** - Red will now properly exit with code ``1`` (``CRITICAL``) when the bot fails after connecting to Discord but before becoming ready instead of indefinitely hanging in non-working condition (:issue:`6202`)
- **Cogs - Audio** - Fixed playlist selection in the picker used by the playlist-related commands (:issue:`6169`, :issue:`6170`)
- **Cogs - Cleanup** - Fixed an issue with ``[p]cleanup self`` not working in DMs (:issue:`6196`, :issue:`6197`)
- **Cogs - Downloader** - Fixed ``CancelledError`` tracebacks showing up in logs when the bot is shut down quickly after the cog is loaded (:issue:`6203`)
- **Cogs - Mutes** - Fixed ``CancelledError`` tracebacks showing up in logs when the bot is shut down quickly after the cog is loaded (:issue:`6203`)

Developer changelog
-------------------

Additions
*********

- |cool| **Core - Utils Package** - Added new view (`ConfirmView`) that can be used to ask for confirmation (:issue:`6174`, :issue:`6176`)
- **Core - Commands Package** - Added `Command.is_enabled()` method allowing to check whether the command is disabled in a guild/globally (:issue:`4130`, :issue:`5552`, :issue:`6209`)

Fixes
*****

- **Core - Commands Package** - Fixed handling of cases where the string returned by `Cog.format_help_for_context()`/`Command.format_help_for_context()` starts with ``"\n\n"`` (:issue:`5941`)
- **Cogs - Dev** - Fixed issues with exception formatting in ``[p]eval/repl/debug`` commands not including the code for chained/grouped exceptions (:issue:`6178`)

Documentation changes
---------------------

Additions
*********

- Added usage example to `get_end_user_data_statement_or_raise()` (:issue:`6171`)

Changes
*******

- |cool| Added install instructions for Debian 12 Bookworm (:issue:`6190`)
- |cool| The install guides have been updated to install Java 17 when possible (:issue:`6190`)


----

Redbot 3.5.2 (2023-05-14)
=========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`aikaterna`, :ghuser:`flaree`, :ghuser:`Flame442`, :ghuser:`Jackenmen`, :ghuser:`karlsbjorn`, :ghuser:`rramboer`, :ghuser:`synrg`, :ghuser:`TrustyJAID`, :ghuser:`Vexed01`

End-user changelog
------------------

Changes
*******

- **Core** - Added list of global prefixes to ``redbot --debuginfo <instance_name>`` and ``[p]debuginfo`` (:issue:`6153`)
- **Core - Dependencies** - Red's dependencies have been bumped (:issue:`6155`)
- **Cogs - Downloader** - Updated the code block style in ``[p]repo list`` and ``[p]cog list`` to account for Discord client changes (:issue:`6003`, :issue:`6152`)
- **Cogs - Trivia** - Updated the code block style in the scoreboard to account for Discord client changes (:issue:`6152`)

Fixes
*****

- Fixed visual issues with numbered and unnumbered lists caused by Discord's new Markdown support (:issue:`6101`)
- **Core** - Fixed handling of cooldown errors for application commands (:issue:`6159`)
- **Core - Bot Commands** - Added missing backtick to the help of ``[p]set serverprefix`` (:issue:`6004`)
- **Core - Command-line Interfaces** - Fixed ``redbot --debuginfo`` trying to start/starting the bot (:issue:`6131`)
- **Cogs - Audio** - Fixed Audio's managed node trying to allocate 4 GB of memory on 32-bit platforms regardless of how much is actually available (:issue:`6137`, :issue:`6150`)
- **Cogs - Audio** - Fixed song selection in ``[p]search`` always picking the first option when buttons are used (:issue:`6136`, :issue:`6143`)
- **Cogs - CustomCommands** - Fixed parameter handling (:issue:`6138`, :issue:`6149`)
- **Cogs - Mutes** - Fixed ``[p]channelmute`` returning "That user is already muted" error when the user is not actually muted (:issue:`6144`)
- **Cogs - Mutes** - Fixed unexpected error in automatic channel unmuting when the relevant channel is not available (:issue:`6140`, :issue:`6144`)
- **Cogs - Reports** - Fixed ``[p]report`` command not working in DMs (:issue:`6148`)
- **Vendored Packages** - Fixed menus breaking in DMs (:issue:`6139`)


Developer changelog
-------------------

Additions
*********

- **Core - Data Manager** - Added a new `data_manager.instance_name()` public function (:issue:`6146`)

Fixes
*****

- **Core - Utils Package** - Fixed ``menu()`` passing an instance of `discord.PartialEmoji` instead of `str` when a button with a unicode emoji is used (:issue:`6143`)
- **Cogs - Dev** - Fixed issues with exception formatting in ``[p]eval/repl/debug`` commands failing when code from a previous invocation of any of those commands was used (:issue:`6135`)


Documentation changes
---------------------

Fixes
*****

- Fixed the search box on the documentation page returning no results (:issue:`6185`)
- Fixed command choices example in `Slash Commands and Interactions guide <guide_slash_and_interactions>` (:issue:`6154`)
- Updated `the 3.5.0 changelog <redbot-3-5-0-2023-05-04>`, `incompatible-changes-3.5`, and `end-user-guarantees` documents to mention the new ``x86-64-v2`` instruction set requirement (:issue:`6141`, :issue:`6147`)


----

Redbot 3.5.1 (2023-05-04)
=========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`Flame442`, :ghuser:`Jackenmen`

This is a hotfix release fixing documentation issues and a bug with the update notification logic
that caused Red to crash.

End-user changelog
------------------

Fixes
*****

- **Core** - Fixed a crash in the Red update notification logic (:issue:`6124`)


Documentation changes
---------------------

Fixes
*****

- Fix the instructions for updating Red (:issue:`6123`)

----

.. _redbot-3-5-0-2023-05-04:

Redbot 3.5.0 (2023-05-04)
=========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`AAA3A-AAA3A`, :ghuser:`aikaterna`, :ghuser:`alexratman`, :ghuser:`AntonioNarra`, :ghuser:`Arman0334`, :ghuser:`Dav-Git`, :ghuser:`Drapersniper`, :ghuser:`Flame442`, :ghuser:`Honkertonken`, :ghuser:`i-am-zaidali`, :ghuser:`Jackenmen`, :ghuser:`japandotorg`, :ghuser:`karlsbjorn`, :ghuser:`keqking`, :ghuser:`Kowlin`, :ghuser:`Kreusada`, :ghuser:`Kuro-Rui`, :ghuser:`leetfin`, :ghuser:`npc203`, :ghuser:`palmtree5`, :ghuser:`PredaaA`, :ghuser:`Predeactor`, :ghuser:`TrustyJAID`, :ghuser:`Vexed01`, :ghuser:`yuansheng1549`

Read before updating
--------------------

#. ``[p]bankset`` is now a core command and as a consequence, the bank cog has been removed. This means that when you start the bot for the first time after the update, you'll see a "Failed to load package bank" message. That is perfectly normal and this message can be ignored.
#. Red 3.5 comes with breaking changes for users. Look at `Backward incompatible changes in Red 3.5 document <incompatible-changes-3.5>` and `End-user changelog <important-350-1>` for full details.

    Note that because this release also comes with breaking changes for developers,
    the cogs you're currently using will likely not work with the new release
    until you update (and that's *if* they have been updated).

    `Our update instructions <update_red>` include instructions on how you can safely update
    your bot and cogs from versions before 3.5. **Make sure** that you look at the instructions
    for **the version you currently have**, not the version you're updating to.

    Note that any cogs that have not yet been updated will likely not work
    until their author releases an update.

#. Red 3.5 comes with breaking changes for cog developers. Look at `Backward incompatible changes in Red 3.5 document <incompatible-changes-3.5>` and `Developer changelog <important-350-2>` for full details.
#. Fedora 35 and Debian 10 (Buster) are no longer supported as they have already reached their end of life.
#. On x86-64 systems, we now require that the CPU supports x86-64-v2 instruction set. This roughly translates to us dropping support for Intel CPUs that have been released before 2009 and AMD CPUs that have been released before 2012.

.. _important-350-1:

End-user changelog
------------------

Breaking Changes
****************

- **Core** - The bot will no longer launch without an owner set (:issue:`4926`)
- **Core - OS support** - On x86-64 systems, we now require that the CPU supports x86-64-v2 instruction set. This roughly translates to us dropping support for Intel CPUs that have been released before 2009 and AMD CPUs that have been released before 2012 (:issue:`6100`)

Additions
*********

- |cool| **Core** - Preference for button menus over reaction menus can now be set with ``[p]set usebuttons``. While this depends on the cog, this should allow users to replace most existing reaction menus with button menus (:issue:`5683`, :issue:`5885`)
- **Core** - The error message for uncaught bot errors is now configurable. See help of ``[p]set errormsg`` for more details (:issue:`5622`, :issue:`5894`)
- |cool| **Core - Bot Commands** - Added ``[p]slash`` command for managing application commands (:issue:`5672`, :issue:`5992`, :issue:`6015`)
- **Core - Command-line Interfaces** - Added new launch flag ``--unload-cogs`` (:issue:`5796`, :issue:`5802`)
- **Cogs - Streams** - Added ``[p]streamset livebutton`` to add a link button under stream alerts (:issue:`5646`, :issue:`5856`)

Changes
*******

- **Core** - The home directory is now always preferred for the metadata file on Linux, even for system users (:issue:`5022`)
- **Core** - Bot prefixes can no longer start with ``/`` (:issue:`5693`)
- **Core** - Cooldown messages now use relative discord timestamps (:issue:`5893`)
- |cool| **Core** - Added the option to request a ``file`` containing all content remaining in interactive prompts (:issue:`5901`, :issue:`5902`)
- **Core** - Parsing errors for integer and number arguments are now more user-friendly (:issue:`5600`)
- |cool| **Core** - Reaction menus now trigger both when adding and removing the reaction (:issue:`4517`)
- **Core** - Threads will now inherit parent channel's embed settings (:issue:`5600`)
- |cool| **Core** - Commands can now be used in threads, voice channels, and stage channels (:issue:`5600`, :issue:`5709`)
- **Core** - Voice and stage channels can now be a destination for owner notifications (``[p]set ownernotifications adddestination``) (:issue:`5709`)
- **Core** - Channel embed settings can now be applied to forum, voice, and stage channels (:issue:`5709`)
- **Core** - Command invocations in specific threads can now be ignored with ``[p]ignore channel``. See `incompatible-changes-3.5` for details (:issue:`5600`)
- **Core - Bot Commands** - ``[p]modlogset`` and ``[p]bankset`` are now core commands (:issue:`4128`, :issue:`4486`)
- **Core - Bot Commands** - Moved ``[p]set`` subcommands: ``username``, ``nickname``, ``avatar``, ``description``, and ``custominfo`` to ``[p]set bot`` subgroup (:issue:`4612`, :issue:`5432`)
- **Core - Bot Commands** - Moved activity related ``[p]set`` subcommands to ``[p]set status`` (:issue:`4612`, :issue:`5432`)
- **Core - Bot Commands** - Moved status related ``[p]set`` subcommands to ``[p]set status`` (:issue:`4612`, :issue:`5432`)
- **Core - Bot Commands** - Moved ``[p]set globallocale`` to ``[p]set locale global`` (:issue:`4612`, :issue:`5432`)
- **Core - Bot Commands** - ``[p]set locale`` can now also be used through ``[p]set locale server`` (:issue:`4612`, :issue:`5432`)
- **Core - Bot Commands** - Moved ``[p]set globalregionalformat`` to ``[p]set regionalformat global`` (:issue:`4612`, :issue:`5432`)
- **Core - Bot Commands** - ``[p]set regionalformat`` can now also be used through ``[p]set regionalformat server`` (:issue:`4612`, :issue:`5432`)
- |cool| **Core - Bot Commands** - Help can now use buttons and/or select menus instead of reaction menus. See the help of ``[p]helpset usemenus`` command for more information (:issue:`5634`, :issue:`5886`)
- **Core - Bot Commands** - ``[p]set api`` now sends a modal to securely set api tokens when no arguments are passed (:issue:`5637`)
- **Core - Bot Commands** - ``[p]traceback`` now prompts to continue if the output requires multiple messages (:issue:`5621`, :issue:`5851`)
- **Core - Bot Commands** - ``[p]removepath`` now allows passing more than one path at once (:issue:`5820`, :issue:`5859`)
- **Core - Bot Commands** - Always available commands such as ``[p]licenseinfo`` now always accept a mention prefix (:issue:`5460`, :issue:`5865`)
- **Core - Bot Commands** - Added an optional ``server`` parameter to ``[p]set showsettings`` and ``[p]set serverprefix`` to prevent lock outs in servers after forgetting a prefix (:issue:`5891`, :issue:`5918`)
- **Core - Command-line Interfaces** - ``-v`` and ``--verbose`` are now aliased to ``--debug``, and the flag can be passed up to 3 times to increase the verbosity of the debugging logs (:issue:`5613`)
- **Core - Command-line Interfaces** - Updated the output of ``--debuginfo`` to be consistent with ``[p]debuginfo`` and allow passing the instance name for additional information (:issue:`5662`)
- **Core - Command-line Interfaces** - Added new exit codes ``2`` (invalid CLI usage) and ``78`` (configuration error) (:issue:`5069`, :issue:`5674`)
- **Core - Command-line Interfaces** - Instance names must now start and end with a letter or number (:issue:`5680`)
- **Core - Command-line Interfaces** - Instance names can no longer consecutive underscores (_) and periods (.) (:issue:`5680`)
- **Core - Command-line Interfaces** - Added descriptions for the ``--overwrite-existing-instance`` and ``--debug`` flags in ``redbot-setup --help`` (:issue:`5808`, :issue:`5818`)
- **Core - Command-line Interfaces** - Modified the console messages for shutting down the bot to be more consistent (:issue:`6095`)
- |cool| **Core - Dependencies** - Bumped ``discord.py`` to version 2.2.3 (:issue:`5600`, :issue:`5709`, :issue:`5920`, :issue:`5998`, :issue:`6100`, :issue:`6109`)
- **Core - Dependencies** - Added support for Python versions 3.10 and 3.11 (:issue:`5611`)
- **Core - Dependencies** - Red's other dependencies have been bumped (:issue:`5611`, :issue:`5631`, :issue:`6100`)
- **Core - Modlog** - Modlog channel can now be set to a voice or stage channel with the ``[p]modlogset channel`` command (:issue:`5709`)
- **Cogs - Admin** - Announcement channel can now be set to a voice or stage channel with the ``[p]announceset channel`` command (:issue:`5709`)
- **Cogs - Audio** - Expanded ``[p]llset`` to allow configuring the backend options of the internal/managed node (Lavalink) (:issue:`5593`)
- **Cogs - Audio** - The cog now uses verbose and trace level logging to improve readability of the debug logs (:issue:`5618`)
- **Cogs - Audio** - Swapped references from "internal"/"external" to "managed"/"unmanaged" (:issue:`5944`, :issue:`5952`)
- **Cogs - Cleanup** - Cleanups now include a message in the audit log detailing who triggered the deletion (:issue:`5861`, :issue:`5863`)
- **Cogs - CustomCommands** - ``{channel}`` substitution parameter may now be a thread, voice channel, or stage channel (:issue:`5600`)
- **Cogs - Downloader** - Added an argument allowing to automatically reload cogs after updating with ``[p]cog update`` (:issue:`3539`, :issue:`5623`)
- **Cogs - Economy** - Moved ``[p]economyset registeramount`` to ``[p]bankset registeramount`` (:issue:`4128`, :issue:`4486`)
- **Cogs - Economy** - Moved ``[p]bank reset`` to ``[p]bankset reset`` (:issue:`4128`, :issue:`4486`)
- **Cogs - Economy** - Moved ``[p]bank prune`` to ``[p]bankset prune`` (:issue:`4128`, :issue:`4486`)
- **Cogs - Filter** - Messages in threads will now be checked for the filtered words of thread's parent channel and server (:issue:`5600`)
- **Cogs - Filter** - Messages in voice or stage channels will now be checked for the filtered words and have their own channel word list (:issue:`5709`)
- **Cogs - General** - Added stage channel information to the extended output of ``[p]serverinfo`` (:issue:`5785`)
- **Cogs - Mutes** - Usage of ``[p]channelmute`` and ``[p]channelunmute`` commands in a thread will now mute the user in thread's parent channel (:issue:`5600`)
- **Cogs - Mutes** - The cog will now deny Send Messages in Threads, Create Public Threads, Create Private Threads, and Use Application Commands permissions in the generated mute role and channel overrides (:issue:`5600`, :issue:`5709`)
- **Cogs - Mutes** - Notification channel can now be set to a voice or stage channel with the ``[p]muteset notification`` command (:issue:`5709`)
- **Cogs - Mutes** - Channel/voice mutes will now behave differently for voice/stage channels: voice mute will only deny the Speak permission while channel mute will deny message permissions as well (:issue:`5709`)
- **Cogs - Permissions** - Red's command permission system will now use thread's parent channel for resolving rules (:issue:`5600`)
- **Cogs - Reports** - Reports channel can now be set to a voice or stage channel with the ``[p]reportset output`` command (:issue:`5709`)
- **Cogs - Streams** - ``[p]streamalert list`` now shows the platform of each channel (:issue:`3866`, :issue:`5160`)
- **Cogs - Streams** - ``[p]streamalert`` subcommands now accept an additional argument to toggle alerts in a particular channel (:issue:`3866`, :issue:`5160`)
- **Cogs - Streams** - Stream alerts can now be sent to a voice or stage channel (:issue:`5709`)
- **Cogs - Warnings** - Warn channel can now be set to a voice or stage channel with the ``[p]warningset warnchannel`` command (:issue:`5709`)

Removals
********

- **Core** - Removed ``redbot-launcher`` (:issue:`5999`)
- **Core - OS Support** - Fedora 35 and Debian 10 (Buster) are no longer supported as they have already reached end of life (:issue:`5974`, :issue:`6110`)
- **Cogs - Audio** - Removed the ``[p]llsetup`` alias of ``[p]llset`` (:issue:`5953`)
- **Cogs - Bank** - Removed the bank cog as its only command - ``[p]bankset`` - is now a core command (:issue:`4128`, :issue:`4486`)

Fixes
*****

- **Core** - Duration parsing in command arguments no longer matches on certain kinds of invalid data (:issue:`5385`, :issue:`5393`)
- **Core** - Optimized how disabled commands are checked when cogs are loaded (:issue:`5550`)
- **Core - Bot Commands** - The core path is now always an absolute path in ``[p]paths`` (:issue:`5142`)
- **Core - Command-line Interfaces** - Fixed an unintended suppression of exceptions in Red's shutdown logic (:issue:`5661`, :issue:`5673`)
- |cool| **Core - Modlog** - Fixed enormous performance issues with commands that have to gather a lot of cases such as ``[p]casesfor`` and ``[p]listcases`` (:issue:`4977`)
- **Core - Modlog** - Case messages are no longer edited immediately after being sent (:issue:`5577`)
- **Cogs - Audio** - Fixed a RAM allocation warning happening in unintended cases (:issue:`5643`)
- **Cogs - Audio** - Fixed the Audio's managed node becoming unresponsive after it's been used for a while (:issue:`5903`)
- **Cogs - Downloader** - Fixed a missing space to an output of ``[p]cog install`` (:issue:`5531`)
- **Cogs - Trivia - Lists** - Fixed some inaccuracies in the ``worldflags`` list (:issue:`5684`)
- **Cogs - Trivia - Lists** - Fixed some inaccuracies in the ``geography`` list (:issue:`5743`)
- **Cogs - Trivia - Lists** - Fixed some inaccuracies in the ``clashroyale`` list (:issue:`5771`)

.. _important-350-2:

Developer changelog
-------------------

Breaking Changes
****************

- **Core** - Fixed edge cases in the ordering logic of ``VersionInfo`` (:issue:`5932`)
- **Core** - Removed ``is_mod_or_superior()``, ``is_admin_or_superior()``, and ``check_permissions()`` from ``redbot.core.checks`` (:issue:`6016`)
- **Core - Bot Class** - Merged ``RedBase`` with the `Red` class (:issue:`5159`)
- **Core - Bot Class** - Removed the ``guild_id`` parameter from `Red.allowed_by_whitelist_blacklist()`. Use the ``guild`` parameter instead (:issue:`4905`, :issue:`4914`, :issue:`5433`)
- **Core - Bot Class** - Removed the ``user`` parameter from `Red.embed_requested()` (:issue:`5576`)
- **Core - Bot Class** - The ``command`` parameter of `Red.embed_requested()` is now keyword-only (:issue:`5576`)
- **Core - Bot Class** - The ``check_permissions`` parameter of `Red.embed_requested()` now defaults to ``True`` (:issue:`5576`)
- **Core - Bot Class** - `Red.add_cog()` will now raise `discord.ClientException` rather than `RuntimeError` when a cog with the same name is already loaded (:issue:`5600`)
- **Core - Bot Class** - Some of the method arguments in the `Red` class have been made positional-only. See `incompatible-changes-3.5` for more information (:issue:`5600`)
- **Core - Bot Class** - `Red.add_cog()` and `Red.remove_cog()` are now asynchronous methods (:issue:`5600`)
- **Core - Bot Class** - ``setup()`` and ``teardown()`` functions in cog packages are now required to be asynchronous (:issue:`5600`)
- **Core - Bot Class** - The list returned by `Red.get_owner_notification_destinations()` may now contain instances of `discord.VoiceChannel` and `discord.StageChannel` (:issue:`5709`)
- **Core - Commands Package** - `Context.maybe_send_embed()` now raises a `ValueError` if the message's length is not between 1 and 2000 characters (:issue:`4383`, :issue:`4465`)
- **Core - Commands Package** - Removed ``GuildConverter`` from the `redbot.core.commands.converter` namespace. Use ``discord.Guild`` or ``commands.GuildConverter`` as the converter instead (:issue:`4928`, :issue:`5433`)
- **Core - Commands Package** - :class:`~discord.ext.commands.BadArgument` is no longer wrapped with a ``ConversionFailure`` class (:issue:`5600`)
- **Core - Commands Package** - Some of the method arguments in the `commands.Command` and ``commands.CogMixin`` class have been made positional-only. See `incompatible-changes-3.5` for more information (:issue:`5600`)
- **Core - Commands Package** - Removed ``commands.requires.DM_PERMS`` (:issue:`5709`)
- **Core - Commands Package** - ``ctx.channel`` can now be a `discord.PartialMessageable` if it represents a DM channel (:issue:`5995`, :issue:`6005`)
- **Core - Config** - Unserializable values can no longer be registered as config defaults (:issue:`5557`)
- **Core - Config** - ``_from_id`` methods now raise a `TypeError` if the provided value is not an ``int`` (:issue:`5459`, :issue:`5564`)
- **Core - Modlog** - `Case.message` is now a `discord.PartialMessage` unless the case object is created with `modlog.create_case()` (:issue:`4977`)
- **Core - Modlog** - `modlog.get_modlog_channel()` may now return an instance of `discord.VoiceChannel` or `discord.StageChannel` (:issue:`5709`)
- **Core - Modlog** - `modlog.create_case()` now raises a `ValueError` when an invalid casetype is passed (:issue:`3346`, :issue:`5386`)
- **Core - Modlog** - `modlog.create_case()` now raises a `RuntimeError` when a bot user is passed as the ``user`` argument (:issue:`5386`)
- **Core - Utils Package** - `redbot.core.utils.menus.menu()` now listens to both reaction add and remove events (:issue:`4517`)
- **Core - Utils Package** - Removed ``redbot.core.utils.mod.is_allowed_by_hierarchy()`` (:issue:`4435`, :issue:`5433`)
- **Core - Utils Package** - Removed the ``caching`` and ``safety`` modules (:issue:`5653`)
- **Core - Utils Package** - `DEFAULT_CONTROLS`, `ALPHABET_EMOJIS`, and `NUMBER_EMOJIS` are now immutable (:issue:`5586`, :issue:`5666`)

Additions
*********

- **Core** - Added an ``on_cog_remove`` event which is dispatched when cogs are unloaded (:issue:`5570`)
- **Core** - Added `RedTree` and general app command support (:issue:`5672`, :issue:`5992`, :issue:`6015`)
- **Core** - Added ``redbot.core.app_commands`` package shadowing ``discord.app_commands``. We expect developers to use it instead of ``discord.app_commands`` when working with Red (:issue:`6006`)
- **Core - App Commands Package** - Allowed setting ``red_force_enable`` in ``extras`` to ``True`` in an app command to bypass ``[p]slash enable`` (:issue:`6018`)
- **Core - Bot Class** - Added `Red.send_interactive()` - a port of `Context.send_interactive()` that can be used with any `discord.abc.Messageable` (:issue:`5851`)
- **Core - Bot Class** - Added `Red.enable_app_command()`, `Red.disable_app_command()`, and `Red.list_enabled_app_commands()` (:issue:`5992`)
- **Core - Bank** - Added `redbot.core.bank.is_owner_if_bank_global()` (:issue:`3709`, :issue:`4486`)
- **Core - Commands Package** - Added `RawUserIdConverter` (:issue:`4486`)
- |cool| **Core - Commands Package** - Added support for hybrid commands (:issue:`5681`)
- **Core - Commands Package** - Added `positive_int` and `finite_float` converters (:issue:`5939`, :issue:`5969`)
- **Core - Commands Package** - Added new checks for proper permission resolution in both channels and threads: `bot_can_manage_channel()`, `bot_can_react()`, `can_manage_channel()`, `guildowner_or_can_manage_channel()`, `admin_or_can_manage_channel()`, `mod_or_can_manage_channel()` (:issue:`5600`)
- **Core - Dependencies** - Added ``red_commons`` as a dependency (:issue:`5624`)
- **Core - Modlog** - Added `Case.parent_channel` and `Case.parent_channel_id` (support for threads) (:issue:`5600`)
- **Core - Utils Package** - Added `SimpleMenu`, a template view subclass (:issue:`5634`)
- **Core - Utils Package** - Added `SetApiModal` and `SetApiView` (:issue:`5637`)
- **Core - Utils Package** - Added new utilities for proper permissions resolution in both channels and threads: `can_user_send_messages_in()`, `can_user_manage_channel()`, `can_user_react_in()` (:issue:`5600`)

Changes
*******

- |cool| **Core** - :func:`logging.getLogger()` now returns a custom logger subclass with support for ``verbose`` and ``trace`` level logging (:issue:`5613`)
- **Core** - Added extra information to version info for dev versions of Red (:issue:`5664`)
- **Core** - Modernized packaging-related things (:issue:`5924`)
- **Core** - Modified `developer-guarantees`, privatizing many APIs that were not intended to be public. See `incompatible-changes-3.5` for more details (:issue:`6021`)
- **Core - Bot Class** - `Red.ignored_channel_or_guild()` now accepts `discord.Interaction` objects (:issue:`6015`)
- **Core - Bot Class** - The ``channel`` parameter of `Red.embed_requested()` now accepts any messageable guild channel (:issue:`5576`)
- **Core - Bot Class** - The bot's color is now set earlier in the launch process (:issue:`5627`)
- **Core - Bot Class** - `Red.remove_cog()` returns a `commands.Cog` instance now (:issue:`5600`)
- **Core - Commands Package** - The `provisional <developer-guarantees-exclusions>` ``Literal`` converter has been replaced with discord.py's own `typing.Literal` implementation (:issue:`5600`)
- **Core - Commands Package** - Added a ``join_character`` parameter to `Red.send_interactive()` and `Context.send_interactive()` to allow choosing the character messages are joined with (:issue:`5901`, :issue:`5902`)
- **Core - Modlog** - `modlog.set_modlog_channel()` can now accept `discord.VoiceChannel` and `discord.StageChannel` (:issue:`5709`)
- **Core - Utils Package** - `menu()` now defaults to `DEFAULT_CONTROLS` if the ``controls`` argument is not passed (:issue:`5678`)
- **Core - Utils Package** - Removed ``bordered()`` (:issue:`5692`)
- **Core - Utils Package** - Optimized the performance of `pagify()` to better handle large inputs (:issue:`5698`)
- **Core - Utils Package** - ``channel`` parameter in `MessagePredicate`'s methods now accepts any `discord.abc.Messageable` (:issue:`5942`)
- |cool| **Cogs - Dev** - Tracebacks for code ran with ``[p]eval``, ``[p]debug``, and ``[p]repl`` commands now include source lines (:issue:`5843`)

Fixes
*****

- **Core - Commands Package** - Fixed decorator order inconsistencies in permissions checks (:issue:`5625`)
- **Core - Modlog** - Fixed `modlog.get_case()` and `modlog.get_all_cases()` raising a runtime error when no modlog channel is configured (:issue:`5644`, :issue:`5866`)
- **Core - Utils Package** - Fixed an unintended `IndexError` in menus when page number is below 0 or above last page number (:issue:`5430`)
- **Cogs - Dev** - Fixed line numbers in tracebacks (:issue:`5843`)
- **Cogs - Dev** - ``[p]mock`` only works in servers now (:issue:`5923`, :issue:`5926`)


Documentation changes
---------------------

Additions
*********

- Added `end-user-guarantees` codifying our support policy for different operating system versions (:issue:`5437`, :issue:`5677`)
- Added a list of currently supported operating system versions and architectures (:issue:`5437`, :issue:`5677`, :issue:`5803`, :issue:`5974`, :issue:`6110`)
- Added documentation for the `redbot.core.utils.antispam` module (:issue:`5641`)
- |cool| Added a cog guide for the Audio cog (:issue:`5871`, :issue:`5895`)
- Added documentation for creating app commands with Red (:issue:`6008`)
- Added documentation listing past and future breaking changes (:issue:`5603`)

Changes
*******

- Linux install guides have been updated to, if possible, use the Python versions already distributed through the official repositories (:issue:`5611`)

Fixes
*****

- Removed references to the ``master`` discord.py docs (:issue:`5713`)
- Removed some duplicated references (:issue:`5782`, :issue:`5778`)
- Fixed an inaccurate typehint in the documentation for `Config.user()` (:issue:`5790`, :issue:`5791`)

----

Redbot 3.4.19 (2023-04-20)
==========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`aikaterna`, :ghuser:`Ankur391`, :ghuser:`BigPeep0doo`, :ghuser:`chasehult`, :ghuser:`Flame442`, :ghuser:`Honkertonken`, :ghuser:`Jackenmen`, :ghuser:`japandotorg`, :ghuser:`Kowlin`, :ghuser:`Kreusada`, :ghuser:`leetfin`, :ghuser:`Lioness100`, :ghuser:`ltzmax`, :ghuser:`MHLoppy`, :ghuser:`OofChair`, :ghuser:`Ryan5453`, :ghuser:`SnappyDragon64`, :ghuser:`sravan1946`, :ghuser:`TheThomanski`, :ghuser:`TrustyJAID`, :ghuser:`vertyco`, :ghuser:`Vexed01`, :ghuser:`Visne`

Read before updating
--------------------

#. Information for Audio users that are using an external Lavalink instance (if you don't know what that is, you should skip this point):

    Red 3.4.19 uses a new Lavalink jar that you will need to manually update from `our GitHub <https://github.com/Cog-Creators/Lavalink-Jars/releases/tag/3.7.5>`__.


End-user changelog
------------------

Additions
*********

- **Cogs - Trivia - Lists** - Added a new Music Trivia List (:issue:`5687`)
- **Cogs - Trivia - Lists** - Added ``whosthatpokemon7`` trivia list containing Pokémon from the 7th generation (:issue:`5890`)
- **Cogs - Trivia - Lists** - Added ``whosthatpokemon8`` trivia list containing Pokémon from the 8th generation (:issue:`5890`)

Changes
*******

- **Core** - Updated the PostgreSQL driver to not depend on the execution of purposefully erroneous SQL queries (:issue:`3983`, :issue:`5855`)
- **Core - Bot Commands** - Updated ``[p]info`` command to link to the full contributor list instead of linking to the org (:issue:`6079`)
- **Core - Bot Commands** - Updated ``[p]invite`` command to warn the user if the bot is serverlocked (:issue:`5898`)
- **Core - Bot Commands** - ``[p]dm`` command now uses the bot's configured embed color (:issue:`5868`)
- |cool| **Cogs - Admin** - Role names are no longer case sensitive in ``[p]selfrole`` and its ``add`` and ``remove`` subcommands (:issue:`3853`, :issue:`3865`)
- **Cogs - Admin** - ``[p]addrole`` and ``[p]removerole`` commands will now add an audit log reason to when applying/removing roles (:issue:`5927`)
- **Cogs - Audio** - Updated enqueued track message to show track's album or playlist if present (:issue:`5569`)
- **Cogs - Downloader** - Updated ``[p]findcog`` command to show both the cog and cog package name (:issue:`5443`, :issue:`5772`)
- **Cogs - General** - Changed ``[p]serverinfo`` command to not require an update whenever a new server feature is added (:issue:`5830`, :issue:`5919`)
- **Cogs - Mod** - Hid ``[p]movedeletedelay`` and ``[p]moveignoredchannels`` commands to prevent accidental use (:issue:`5870`)
- **Cogs - Mod** - Updated mention spam handling to count role mentions. Such mentions are counted as a single mention (:issue:`4471`, :issue:`5388`)
- **Cogs - Modlog** - Improved clarity of the help of the ``[p]modlogset cases`` command (:issue:`5352`)
- **Cogs - Trivia** - Changed the validation of custom trivia lists to match the restrictions from ``[p]triviaset`` commands (:issue:`5947`, :issue:`5949`)
- **Cogs - Trivia** - Improved error messages for schema errors in custom lists (:issue:`5947`)
- **Cogs - Trivia** - Added JSON schema for Trivia's custom list format and allowed the usage of ``$schema`` key (:issue:`5565`)
- **Cogs - Trivia - Lists** - Added over 30 new questions to the ``harrypotter`` trivia list (:issue:`5887`)
- **Cogs - Trivia - Lists** - Renamed the country of Turkey to Türkiye as per the United Nations' name change (:issue:`5795`)
- **Cogs - Trivia - Lists** - Improved the topography trivia by adding/removing correct/incorrect answers and fixing inconsistencies (:issue:`5572`)

Fixes
*****

- Fixed various typos across Red's codebase (:issue:`5867`, :issue:`5888`, :issue:`5977`, :issue:`5989`)
- **Core** - Resolved an edge case in the PostgreSQL driver that made it fail to clear an entire Config scope when it had no data (:issue:`5855`)
- **Cogs - Admin** - Fixed ``[p]selfroleset add/remove`` commands not showing the help when they're invoked with no arguments (:issue:`6084`)
- |cool| **Cogs - Audio** - Fixed Twitch playback (:issue:`6033`)
- |cool| **Cogs - Audio** - Fixed plain word search queries (:issue:`6033`)
- **Cogs - Audio** - Prevented formatting from being escaped on Playlist Enqueued message (:issue:`6025`)
- **Cogs - Audio** - Fixed command usage help for the ``[p]audioset autoplay playlist`` command (:issue:`5592`)
- **Cogs - CustomCommands** - Fixed the documentation of ``[p]cc cooldown``'s arguments (:issue:`5914`)
- **Cogs - Downloader** - Fixed handling of repo names containing dots (:issue:`5937`, :issue:`5938`)
- **Cogs - General** - Fixed the URL generated by ``[p]lmgtfy`` command (:issue:`5908`, :issue:`5909`)
- **Cogs - Mutes** - Fixed a bug where muting a member in one voice channel would unintentionally move them between other voice channels (:issue:`4993`, :issue:`5854`)
- **Cogs - Trivia** - Fixed error handling for long file names in ``[p]triviaset custom upload`` (:issue:`5948`, :issue:`5950`)


Developer changelog
-------------------

Changes
*******

- **Core** - Improved asyncio loop's exception handling to allow it to show resource warnings (:issue:`5813`)

Fixes
*****

- **Core - Utils Package** - Fixed `Tunnel.message_forwarder`'s handling of strings larger than 2000 characters (:issue:`5844`)
- **Cogs - Dev** - Fixed ``__repr__()`` errors in ``[p]repl`` when referencing an instance of a class with a faulty ``__repr__()`` (:issue:`5794`)


Documentation changes
---------------------

Additions
*********

- |cool| Added `a guide for making auto-restart script on Windows <autostart_windows>` using the Startup folder (:issue:`5996`)
- |cool| Added `cog guide for Dev cog <cog_guides/dev>` (:issue:`1734`, :issue:`5869`)
- Added ``brew shellenv`` call to shell profile in macOS install guide to ensure proper ``PATH`` setup on Apple Silicon (:issue:`5993`)

Changes
*******

- |cool| Improved the format and consistency of the changelogs A LOT! (:issue:`5602`)
- |cool| Highlights of a release are now prepended in the changelog with |cool| emoji (:issue:`5602`)
- Merged all changelogs into a single page (:issue:`5602`)
- Added changelogs for 3.0.1-3.1.9 releases to the documentation (:issue:`5602`)
- Documented the ``CONFIG`` key in the Trivia List Creation Guide (:issue:`3977`, :issue:`5390`)
- Updated Python version in ``pyenv`` instructions (:issue:`5960`)
- Changed Windows install instructions to use python39 package rather than python3 package with a version pin (:issue:`5960`)
- Updated the screenshot showing what intents need to be selected (:issue:`5935`, :issue:`5936`)
- Updated bot hosting list with the new location for Contabo and addition of AlphaVPS (:issue:`5928`)
- Updated installation URLs for Homebrew and Chocolatey (:issue:`5776`)
- Updated the auto-restart script for Linux to only restart when there's a critical error (crash) or the restart command is ran (:issue:`5069`, :issue:`5674`)

----

Redbot 3.4.18 (2022-08-15)
==========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`aikaterna`, :ghuser:`Flame442`, :ghuser:`jack1142`, :ghuser:`Kowlin`, :ghuser:`RheingoldRiver`

Read before updating
--------------------

#. openSUSE Leap 15.2 is no longer supported as it has already reached its end of life.
#. Information for Audio users that are using an external Lavalink instance (if you don't know what that is, you should skip this point):

    - Red 3.4.18 uses a new Lavalink jar that you will need to manually update from `our GitHub <https://github.com/Cog-Creators/Lavalink-Jars/releases/tag/3.4.0_1350>`__.
    - We've updated our `application.yml file <https://github.com/Cog-Creators/Red-DiscordBot/blob/3.4.18/redbot/cogs/audio/data/application.yml>`__ and you should update your instance's ``application.yml`` appropriately.


End-user changelog
------------------

Removals
********

- **Core - OS Support** - openSUSE Leap 15.2 is no longer supported as it has already reached its end of life (:issue:`5777`)

Fixes
*****

- |cool| **Cogs - Audio** - Addressed a cipher change that made it impossible to find tracks (:issue:`5822`)
- **Cogs - Audio** - Fixed an issue with ``[p]llset external`` making the bot completely unresponsive when switching to an external Lavalink server (:issue:`5804`, :issue:`5828`)


Documentation changes
---------------------

Changes
*******

- Updated the screenshot in `bot_application_guide` to include the message content intent (:issue:`5798`)
- Unpinned Temurin version on Windows as a fixed version is now available (:issue:`5815`)

----

Redbot 3.4.17 (2022-06-07)
==========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`aikaterna`, :ghuser:`Drapersniper`, :ghuser:`Flame442`, :ghuser:`jack1142`, :ghuser:`Kowlin`, :ghuser:`Kreusada`, :ghuser:`ltzmax`, :ghuser:`matcha19`, :ghuser:`mina9999`, :ghuser:`ponte-vecchio`, :ghuser:`PredaaA`, :ghuser:`TrustyJAID`, :ghuser:`untir-l`, :ghuser:`Vexed01`

Read before updating
--------------------

#. Fedora 34 is no longer supported as it has already reached its end of life.
#. Information for Audio users that are using an external Lavalink instance (if you don't know what that is, you should skip this point):

    Red 3.4.17 uses a new Lavalink jar that you will need to manually update from `our GitHub <https://github.com/Cog-Creators/Lavalink-Jars/releases/tag/3.4.0_1347>`__.


End-user changelog
------------------

Additions
*********

- **Cogs - Trivia - Lists** - Added a trivia list for the FIFA World Cup with questions based on hosts, placements, venues, continental confederations, number of participants, top goal scorers, qualification shocks, and more (:issue:`5639`)

Changes
*******

- **Core - Bot Commands** - Added instructions on how to respond to the message received from ``[p]contact`` in the embed footer of the message sent to the bot owner (:issue:`5528`, :issue:`5529`)
- **Core - Bot Commands** - Updated ``[p]servers`` command to escape Discord markdown in server names (:issue:`5696`, :issue:`5744`)
- **Cogs - Audio** - Added timestamps to all embeds sent by Audio cog (:issue:`5632`)
- **Cogs - Audio** - Improved handling of voice connection close codes received from Discord (:issue:`5712`)
- |cool| **Cogs - Downloader** - Added information about the commit hash at which the cog is pinned in the output of ``[p]cog listpinned`` command (:issue:`5551`, :issue:`5563`)
- **Cogs - General** - Updated features list in ``[p]serverinfo`` with the latest changes from Discord (:issue:`5655`)
- **Cogs - Mod** - Updated Red's ban commands to address the breaking change that Discord made in their ban list API endpoint (:issue:`5656`)
- **Cogs - Mutes** - Added proper error handling for VERY long durations in mute commands (:issue:`5605`)
- **Cogs - Permissions** - Updated ``[p]permissions acl setglobal`` and ``[p]permissions acl setserver`` to allow sending the file in a follow-up message (:issue:`5473`, :issue:`5685`)
- **Cogs - Permissions** - ``[p]permissions canrun`` now prepends an emoji to the response to better differentiate between the positive and negative results (:issue:`5711`)
- **Cogs - Trivia** - Allowed passing ``use_spoilers`` setting in the CONFIG section of the trivia list file (:issue:`5566`)
- **Cogs - Trivia - Lists** - Updated ``geography`` trivia list with up-to-date answers and removed questions that lack sources for their claimed answers (:issue:`5638`)
- **Cogs - Trivia - Lists** - Updated Kazakhstan's capital city in the ``worldcapitals`` trivia list (:issue:`5598`, :issue:`5599`)

Removals
********

- **Core - OS Support** - Fedora 34 is no longer supported as it has already reached its end of life (:issue:`5701`)

Fixes
*****

- **Core - Bot Commands** - Fixed grammar in the ``[p]uptime`` command (:issue:`5596`)
- **Core - Command-line Interfaces** - Fixed a bug that prevented users from changing the name and data location with ``redbot --edit`` command (:issue:`5545`, :issue:`5540`, :issue:`5541`)
- **Core - Modlog** - Modlog's automated case creation for bans now properly checks that the guild is available before further processing (:issue:`5647`)
- |cool| **Cogs - Audio** - Fixed plain word YT searching with ``[p]play`` and ``[p]search`` commands (:issue:`5712`)
- |cool| **Cogs - Audio** - Fixed YT age-restricted track playback (:issue:`5712`)
- **Cogs - Audio** - Fixed the cog not sending any Track Error message on track decoding errors (:issue:`5716`)
- **Cogs - Audio** - Fixed the ``UnboundLocalError`` exception happening when using ``[p]playlist list`` with an empty playlist (:issue:`5378`, :issue:`5394`)
- **Cogs - Filter** - Fixed a potential memory leak in Filter cog (:issue:`5578`)
- **Cogs - Trivia - Lists** - Fixed spelling error in the answer to one of the questions in ``computers`` trivia list (:issue:`5587`, :issue:`5588`)


Developer changelog
-------------------

Changes
*******

- **Vendored Packages** - Updated ``discord.ext.menus`` vendor (:issue:`5579`)


Documentation changes
---------------------

Additions
*********

- Added CentOS Stream 9, RHEL 9, Alma Linux 9, Oracle Linux 9, and Rocky Linux 9 install guides (:issue:`5537`, :issue:`5721`)
- Added Ubuntu 22.04 install guide (:issue:`5720`)

Changes
*******

- Changed the recommended operating system for hosting Red from Ubuntu 20.04 LTS to Ubuntu 22.04 LTS (:issue:`5720`)
- Updated Python version in ``pyenv`` and Windows instructions (:issue:`5719`)
- Replaced install instructions for discontinued AdoptOpenJDK package with Temurin 11 package in the macOS install guide (:issue:`5718`)
- Updated Visual Studio Build Tools version in Windows install guide (:issue:`5702`)
- Updated systemd guide to use the absolute path to ``which`` command to avoid triggering shell aliases on some OSes (:issue:`5547`)
- Emphasized lines that contain text that needs to be replaced by the user (:issue:`5548`)
- Prevented Google and other search engines from indexing versioned documentation (:issue:`5549`)

Fixes
*****

- Pinned Temurin version on Windows until a fixed version becomes available (:issue:`5717`)
- Fixed git installation instructions in CentOS 7 install guide (:issue:`5700`)

----

Redbot 3.4.16 (2021-12-31)
==========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`jack1142`, :ghuser:`PredaaA`

This is a hotfix release fixing issues with invite URL API that caused
``[p]invite`` command and ``CORE__INVITE_URL`` RPC method to not work.

End-user changelog
------------------

Fixes
*****

- **Core - Bot Commands** - Fixed ``[p]invite`` command (:issue:`5517`)


Developer changelog
-------------------

Fixes
*****

- **RPC methods** - Fixed ``CORE__INVITE_URL`` RPC method (:issue:`5517`)


Documentation changes
---------------------

Changes
*******

- Changed Arch install guide to temporarily use ``python39`` AUR package instead of ``python`` package as Red does not currently support Python 3.10 (:issue:`5518`)

----

Redbot 3.4.15 (2021-12-31)
==========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`aikaterna`, :ghuser:`aleclol`, :ghuser:`Arman0334`, :ghuser:`Crossedfall`, :ghuser:`Dav-Git`, :ghuser:`fixator10`, :ghuser:`Flame442`, :ghuser:`jack1142`, :ghuser:`Jan200101`, :ghuser:`Just-Jojo`, :ghuser:`Kowlin`, :ghuser:`Kreusada`, :ghuser:`laggron42`, :ghuser:`ltzmax`, :ghuser:`Parnassius`, :ghuser:`PredaaA`, :ghuser:`Predeactor`, :ghuser:`RasmusWL`, :ghuser:`sravan1946`, :ghuser:`Stonedestroyer`, :ghuser:`the-krak3n`, :ghuser:`Tobotimus`, :ghuser:`vertyco`, :ghuser:`Vexed01`, :ghuser:`WreckRox`, :ghuser:`yamikaitou`

Read before updating
--------------------

#. Fedora 33 and CentOS 8 are no longer supported as they have already reached end of life.
#. Information for Audio users that are using an external Lavalink instance (if you don't know what that is, you should skip this point):

    Red 3.4.15 uses a new Lavalink jar that you MUST manually update from `our GitHub <https://github.com/Cog-Creators/Lavalink-Jars/releases/tag/3.4.0_1275>`__ to be able to continue using Audio.


End-user changelog
------------------

Additions
*********

- |cool| **Core - Command-line Interfaces** - Added new CLI options for non-interactive usage of ``redbot-setup`` (:issue:`2396`, :issue:`5448`)

    See output of ``redbot-setup --help`` for more information.

- **Cogs - Admin** - Added ``[p]selfroleset clear`` command which can be used to clear the list of available selfroles in the server (:issue:`5387`)
- **Cogs - Audio** - Added native Mac M1 support for Java runtimes supporting Mac M1 (:issue:`5474`)

Changes
*******

- **Core - Bot Commands** - Updated prefix length limit to ``25`` to allow setting bot mention as a prefix (:issue:`5476`)
- **Core - Bot Commands** - Improved ``[p]helpset showaliases`` responses (:issue:`5376`)
- **Core - Bot Commands** - Added plural forms to the responses of ``[p]leave`` command (:issue:`5391`)
- **Core - Bot Commands** - The embed setting for ``[p]help`` command set with ``[p]embedset command`` will now affect all help messages, not just the ones sent when invoking ``[p]help`` command directly (:issue:`5452`)
- **Core - Bot Commands** - ``[p]traceback`` command now indicates that it DMed the command caller with a tick reaction (:issue:`5353`)
- **Core - Command-line Interfaces** - JSON is now more strongly recommended and is used by default for new instances in ``redbot-setup`` (:issue:`5448`)
- **Cogs - Audio** - Enabled JDA-NAS on all system architectures which should limit stuttering/buffering issues on some machines (:issue:`5474`)
- **Cogs - Audio** - The bot will now disconnect from the voice channel when all members are bots if the auto-disconnect setting is enabled (:issue:`5421`)
- **Cogs - CustomCommands** - Added 2000 character limit for custom command responses to prevent Nitro users from adding longer responses than a Discord bot can send (:issue:`5499`)
- **Cogs - Downloader** - Added repo name to the response of ``[p]findcog`` command (:issue:`5382`, :issue:`5383`)
- **Cogs - Mod** - ``[p]voicekick`` now sends a response when the action succeeds (:issue:`5367`)
- |cool| **Cogs - Modlog** - Added the new native Discord timestamps in ``[p]case``, ``[p]casesfor``, and ``[p]listcases`` commands (:issue:`5395`)

Removals
********

- **Core - OS Support** - Fedora 33 and CentOS 8 are no longer supported as they have already reached end of life (:issue:`5440`)
- **Cogs - General** - Removed voice region field from ``[p]serverinfo`` command as Discord no longer provides this setting for servers (:issue:`5449`)

Fixes
*****

- Fixed short help for some of the commands in Core Red (:issue:`5502`)
- Confirmation prompts (accepting "yes/no" or "I agree" as the answer) no longer wrongfully translate the answer that needs to be sent when only English answers are accepted by the bot (:issue:`5363`, :issue:`5364`, :issue:`5404`)
- **Core - Bot Commands** - Corrected usage examples in help of ``[p]set api`` and ``[p]set api remove`` (:issue:`5444`)
- **Core - Bot Commands** - ``[p]command enable guild`` and ``[p]command disable guild`` commands no longer error out for commands that *only* check for user permissions, not caller's roles (:issue:`5477`)
- **Core - Command-line Interfaces** - Fixed an issue with instance backup failing for non-JSON storage backends (:issue:`5315`)
- **Core - Command-line Interfaces** - Running Red with ``--no-instance`` CLI flag no longer fails when no instance was ever created by the user (:issue:`5415`, :issue:`5416`)
- **Core - Modlog** - Fixed issues with rendering of modlog cases with usernames written in a right-to-left language (:issue:`5422`)
- |cool| **Cogs - Audio** - Fixed an issue with resuming playback after changing voice channels (:issue:`5170`)
- |cool| **Cogs - Audio** - Fixed issues with Soundcloud private playlists and mobile links (:issue:`5474`)
- |cool| **Cogs - Audio** - Fixed searching music with some of the queries containing quotes or backslashes (:issue:`5474`)
- |cool| **Cogs - Audio** - Fixed an exception caused by unavailable YT tracks in Mix playlists (:issue:`5474`)
- **Cogs - Audio** - Fixed ``IndexError`` in ``[p]queue`` command which occurred when the user provides negative integer as the page number (:issue:`5429`)
- **Cogs - Cleanup** - Restricted ``[p]cleanupset notify`` to only be invokable in server channels (:issue:`5466`)
- **Cogs - Economy** - ``[p]economyset showsettings`` now includes configured role payday amounts (:issue:`5455`, :issue:`5457`)
- **Cogs - Mod** - Fixed an error with ``[p]tempban`` failing to send an invite link when a server has an unset vanity URL (:issue:`5472`)
- **Cogs - Mod** - Fixed explanations of example usage for ``[p]ban``, ``[p]kick``, and ``[p]tempban`` commands (:issue:`5372`)
- **Cogs - Mod** - Fixed a typo in one of ``[p]unban``'s error messages (:issue:`5470`)
- **Cogs - Warnings** - Warning actions no longer error out when the action is set to use a command that *only* checks for user permissions, not caller's roles (:issue:`5477`)


Developer changelog
-------------------

Additions
*********

- **Core - Bot Class** - Added optional ``check_permissions`` keyword-only argument to `Red.embed_requested()` which, if ``True``, will make the method also check whether the bot can send embeds in the given channel (:issue:`5452`)
- |cool| **Core - Bot Class** - Added `Red.get_invite_url()` and `Red.is_invite_url_public()` that expose the functionality of ``[p]invite`` programmatically (:issue:`5152`, :issue:`5424`)
- |cool| **Core - Commands Package** - Added optional ``message`` argument to `Context.tick()` and `Context.react_quietly()` which is used if adding the reaction doesn't succeed (:issue:`3359`, :issue:`4092`)

Changes
*******

- **Cogs - Dev** - ``[p]mockmsg`` now allows mocking attachment-only messages (:issue:`5446`)
- **RPC methods** - Changed the output of ``CORE__LOAD``, ``CORE__RELOAD``, and ``CORE__UNLOAD`` RPC methods to a dictionary (:issue:`5451`, :issue:`5453`)


Documentation changes
---------------------

Additions
*********

- |cool| Added install guide for Alma Linux 8.4-8.x and Raspberry Pi OS 11 Bullseye (:issue:`5440`)
- Specified that Red currently requires Python 3.8.1 - 3.9.x (:issue:`5403`)

Changes
*******

- Updated the Java distribution used in the Windows install guide to Temurin - rebranded AdoptOpenJDK (:issue:`5403`)
- Improved Mac and pyenv instructions to address common issues with load path configuration (:issue:`5356`)
- Updated the server locations for Hetzner and Contabo in :ref:`host-list` document (:issue:`5475`)
- Updated Python version in ``pyenv`` and Windows instructions (:issue:`5447`)
- Removed LXC from unsupported hosting platforms as many VPS providers utilize that technology (:issue:`5351`)

Fixes
*****

- Removed inaccurate note from Unix install guides about install commands also being used for updating Red (:issue:`5439`)

----

Redbot 3.4.14 (2021-09-23)
==========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`aikaterna`, :ghuser:`jack1142`, :ghuser:`Kowlin`, :ghuser:`L33Tech`, :ghuser:`maxbooiii`, :ghuser:`RheingoldRiver`

Read before updating
--------------------

#. Versions of RHEL older than 8.4 (including 7) and versions of CentOS older than 8.4 (excluding 7) are no longer supported.
#. Information for Audio users that are using an external Lavalink instance (if you don't know what that is, you should skip this point):

    Red 3.4.14 uses a new Lavalink jar that you will need to manually update from `our GitHub <https://github.com/Cog-Creators/Lavalink-Jars/releases/tag/3.3.2.3_1239>`__.


End-user changelog
------------------

Additions
*********

- |cool| **Core - Bot Commands** - Added the new native Discord timestamp in the ``[p]uptime`` command (:issue:`5323`)

Changes
*******

- **Core - Command-line Interfaces** - ``redbot-setup delete`` command no longer requires database connection if the data deletion was not requested (:issue:`5312`, :issue:`5313`)

Fixes
*****

- |cool| **Cogs - Audio** - Fixed intermittent 403 Forbidden errors (:issue:`5329`)
- **Cogs - Modlog** - Fixed formatting of **Last modified at** field in Modlog cases (:issue:`5317`)


Documentation changes
---------------------

Additions
*********

- |cool| Added install guide for CentOS Stream 8, Oracle Linux 8.4-8.x, and Rocky Linux 8 (:issue:`5328`)

Changes
*******

- |cool| Each operating system now has a dedicated install guide (:issue:`5328`)
- Install guides for RHEL derivatives no longer require the use of pyenv (:issue:`5328`)

Fixes
*****

- Fixed Raspberry Pi OS install guide (:issue:`5314`, :issue:`5328`)

----

Redbot 3.4.13 (2021-09-09)
==========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`aikaterna`, :ghuser:`Arman0334`, :ghuser:`Flame442`, :ghuser:`flaree`, :ghuser:`fredster33`, :ghuser:`Injabie3`, :ghuser:`jack1142`, :ghuser:`Just-Jojo`, :ghuser:`Kowlin`, :ghuser:`Kreusada`, :ghuser:`leblancg`, :ghuser:`maxbooiii`, :ghuser:`npc203`, :ghuser:`palmtree5`, :ghuser:`phenom4n4n`, :ghuser:`PredaaA`, :ghuser:`qenu`, :ghuser:`TheDataLeek`, :ghuser:`Twentysix26`, :ghuser:`TwinDragon`, :ghuser:`Vexed01`

Read before updating
--------------------

#. If you're hosting a public/big bot (>75 servers) or strive to scale your bot at that level, you should read :doc:`our stance on (privileged) intents and public bots <intents>`.
#. Fedora 32 is no longer supported as it has already reached end of life.
#. Information for Audio users that are using an external Lavalink instance (if you don't know what that is, you should skip this point):

    Red 3.4.13 uses a new Lavalink jar that you will need to manually update from `our GitHub <https://github.com/Cog-Creators/Lavalink-Jars/releases/tag/3.3.2.3_1238>`__.


End-user changelog
------------------

Additions
*********

- |cool| **Core** - Red 3.4.13 is the first release to (finally) support Python 3.9! (:issue:`4655`, :issue:`5121`)
- |cool| **Core - Bot Commands** - Added a new ``[p]diagnoseissues`` command to allow the bot owners to diagnose issues with various command checks with ease (:issue:`4717`, :issue:`5243`)

    Since some of us are pretty excited about this feature, here's a very small teaser showing a part of what it can do:

    .. figure:: https://user-images.githubusercontent.com/6032823/132610057-d6c65d67-c244-4f0b-9458-adfbe0c68cab.png
- **Core - Bot Commands** - Added a setting for ``[p]help``'s reaction timeout (:issue:`5205`)

    This can be changed with ``[p]helpset reacttimeout`` command
- **Cogs - Alias** - Added commands for editing existing aliases (:issue:`5108`)
- **Cogs - Audio** - Added a per-guild max volume setting (:issue:`5165`)

    This can be changed with the ``[p]audioset maxvolume`` command
- |cool| **Cogs - Cleanup** - All ``[p]cleanup`` commands will now send a notification with the number of deleted messages. The notification is deleted automatically after 5 seconds (:issue:`5218`)

    This can be disabled with the ``[p]cleanupset notify`` command
- **Cogs - Filter** - Added ``[p]filter clear`` and ``[p]filter channel clear`` commands for clearing the server's/channel's filter list (:issue:`4841`, :issue:`4981`)

Changes
*******

- **Core - Bot Commands** - Revamped the ``[p]debuginfo`` to make it more useful for... You guessed it, debugging! (:issue:`4997`, :issue:`5156`)

    More specifically, added information about CPU and RAM, bot's instance name and owners
- |cool| **Core - Bot Commands** - Added the new native Discord timestamps in Modlog cases, ``[p]userinfo``, ``[p]serverinfo``, and ``[p]tempban`` (:issue:`5155`, :issue:`5241`)
- **Core - Bot Commands** - The ``[p]invite`` command will now add a tick reaction after it DMs an invite link to the user (:issue:`5184`)
- |cool| **Core - Command-line Interfaces** - The formatting of Red's console logs has been updated to make it more copy-paste friendly (:issue:`4868`, :issue:`5181`)
- **Core - Command-line Interfaces** - The console error about missing Privileged Intents stands out more now (:issue:`5184`)
- **Core - Dependencies** - Upgraded all Red's dependencies (:issue:`5121`)
- **Cogs - Admin** - The ``[p]selfroleset add`` and ``[p]selfroleset remove`` commands can now be used to add multiple selfroles at once (:issue:`5237`, :issue:`5238`)
- **Cogs - Audio** - ``[p]summon`` will now indicate that it has succeeded or failed to summon the bot (:issue:`5186`)
- |cool| **Cogs - Cleanup** - The ``[p]cleanup user`` command can now be used to clean messages of a user that is no longer in the server (:issue:`5169`)
- **Cogs - Downloader** - The dot character (``.``) can now be used in repo names. No more issues with adding repositories using the commands provided by the Cog Index! (:issue:`5214`)
- |cool| **Cogs - Mod** - The DM message from the ``[p]tempban`` command will now include the ban reason if ``[p]modset dm`` setting is enabled (:issue:`4836`, :issue:`4837`)
- **Cogs - Streams** - Made small optimizations in regards to stream alerts (:issue:`4968`)
- **Cogs - Trivia** - Added schema validation of the custom trivia files (:issue:`4571`, :issue:`4659`)

Removals
********

- **Core - OS Support** - Fedora 32 is no longer supported as it has already reached end of life (:issue:`5121`)

Fixes
*****

- **Core - Bot Commands** - Fixed a bunch of errors related to the missing permissions and channels/messages no longer existing (:issue:`5109`, :issue:`5163`, :issue:`5172`, :issue:`5191`)
- **Cogs - Audio** - Fixed an issue with short clips being cutoff when auto-disconnect on queue end is enabled (:issue:`5158`, :issue:`5188`)
- |cool| **Cogs - Audio** - Fixed fetching of age-restricted tracks (:issue:`5233`)
- |cool| **Cogs - Audio** - Fixed searching of YT Music (:issue:`5233`)
- |cool| **Cogs - Audio** - Fixed playback from SoundCloud (:issue:`5233`)
- **Cogs - Downloader** - Added a few missing line breaks (:issue:`5185`, :issue:`5187`)
- **Cogs - Mod** - Fixed an error with handling of temporary ban expirations while the guild is unavailable due to Discord outage (:issue:`5173`)
- **Cogs - Mod** - The ``[p]rename`` command will no longer permit changing nicknames of members that are not lower in the role hierarchy than the command caller (:issue:`5187`, :issue:`5211`)
- **Cogs - Streams** - Fixed an issue with some YouTube streamers getting removed from stream alerts after a while (:issue:`5195`, :issue:`5223`)
- |cool| **Cogs - Warnings** - 0 point warnings are, once again, allowed. (:issue:`5177`, :issue:`5178`)


Developer changelog
-------------------

Additions
*********

- |cool| **Core - Bot Class** - Added more APIs for allowlists and blocklists (:issue:`5206`)

    Here's the list of the methods that were added to the ``bot`` object:

        - `Red.add_to_blacklist()`
        - `Red.remove_from_blacklist()`
        - `Red.get_blacklist()`
        - `Red.clear_blacklist()`
        - `Red.add_to_whitelist()`
        - `Red.remove_from_whitelist()`
        - `Red.get_whitelist()`
        - `Red.clear_whitelist()`
- |cool| **Core - Commands Package** - Added `RelativedeltaConverter` and `parse_relativedelta` to the ``redbot.core.commands`` package (:issue:`5000`)

    This converter and function return `dateutil.relativedelta.relativedelta` object that represents a relative delta.
    In addition to regular timedelta arguments, it also accepts months and years!
- **Core - Commands Package** - Added `CommandConverter` and `CogConverter` to the ``redbot.core.commands`` package (:issue:`5037`)


Documentation changes
---------------------

Additions
*********

- Added a document about (privileged) intents and our stance regarding "public bots" (:issue:`5216`, :issue:`5221`)
- |cool| Added install instructions for Debian 11 Bullseye (:issue:`5213`, :issue:`5217`)
- Added Oracle Cloud's Always Free offering to the :ref:`host-list` (:issue:`5225`)

Changes
*******

- |cool| Updated the commands in the install guide for Mac OS to work properly on Apple Silicon devices (:issue:`5234`)

Fixes
*****

- Fixed the examples of commands that are only available to people with the mod role (:issue:`5180`)
- Fixed few other small issues with the documentation :) (:issue:`5048`, :issue:`5092`, :issue:`5149`, :issue:`5207`, :issue:`5209`, :issue:`5215`, :issue:`5219`, :issue:`5220`)

----

Redbot 3.4.12 (2021-06-17)
==========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`aikaterna`, :ghuser:`Flame442`, :ghuser:`jack1142`, :ghuser:`Just-Jojo`, :ghuser:`Kowlin`, :ghuser:`Kreusada`, :ghuser:`npc203`, :ghuser:`PredaaA`, :ghuser:`retke`, :ghuser:`Stonedestroyer`

This is a hotfix release related to Red ceasing to use the Audio Global API service.

End-user changelog
------------------

Additions
*********

- **Core - Bot Commands** - ``applications.commands`` scope can now be included in the invite URL returned from ``[p]invite`` by enabling it with``[p]inviteset commandscope``

Changes
*******

- **Core - Bot Commands** - ``[p]set serverprefix`` command will now prevent the user from setting a prefix with length greater than 20 characters (:issue:`5091`, :issue:`5117`)
- **Core - Bot Commands** - ``[p]set prefix`` command will now warn the user when trying to set a prefix with length greater than 20 characters (:issue:`5091`, :issue:`5117`)
- |cool| **Cogs - Audio** - All local caches are now enabled by default (:issue:`5140`)

Removals
********

- **Cogs - Audio** - Global API service will no longer be used in Audio and as such support for it has been removed from the cog (:issue:`5143`)

Fixes
*****

- **Cogs - Audio** - Updated URL of the curated playlist (:issue:`5135`)
- **Cogs - Filter** - Fixed an edge case that caused the cog to sometimes check contents of DM messages (:issue:`5125`)
- **Cogs - Warnings** - Prevented users from applying 0 or less points in custom warning reasons (:issue:`5119`, :issue:`5120`)

Developer changelog
-------------------

Changes
*******

- **Cogs - Dev** - ``[p]debug`` command will now confirm the code finished running with a tick reaction (:issue:`5107`)

----

Redbot 3.4.11 (2021-06-12)
==========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`jack1142`, :ghuser:`Kowlin`, :ghuser:`Onii-Chan-Discord`

This is a hotfix release fixing a crash involving guild uploaded stickers.

End-user changelog
------------------

Changes
*******

- **Core - Dependencies** - discord.py version has been bumped to 1.7.3 (:issue:`5129`)


Documentation changes
---------------------

Fixes
*****

- Links to the CogBoard in Red's documentation have been updated to use the new domain (:issue:`5124`)

----

Redbot 3.4.10 (2021-05-28)
==========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`aikaterna`, :ghuser:`aleclol`, :ghuser:`benno1237`, :ghuser:`bobloy`, :ghuser:`BoyDownTown`, :ghuser:`Danstr5544`, :ghuser:`DeltaXWizard`, :ghuser:`Drapersniper`, :ghuser:`Fabian-Evolved`, :ghuser:`fixator10`, :ghuser:`Flame442`, :ghuser:`flaree`, :ghuser:`jack1142`, :ghuser:`Kowlin`, :ghuser:`Kreusada`, :ghuser:`Lifeismana`, :ghuser:`Obi-Wan3`, :ghuser:`OofChair`, :ghuser:`palmtree5`, :ghuser:`plofts`, :ghuser:`PredaaA`, :ghuser:`Predeactor`, :ghuser:`TrustyJAID`, :ghuser:`Vexed01`

Read before updating
--------------------

#. PM2 process manager is no longer supported as it is not a viable solution due to certain parts of its behavior.

    We highly recommend you to switch to one of the other supported solutions:
        - `autostart_systemd`
        - `autostart_mac`

    If you experience any issues when trying to configure it, you can join `our discord server <https://discord.gg/red>`__ and ask in the **support** channel for help.
#. Information for Audio users that are using an external Lavalink instance (if you don't know what that is, you should skip this point):

    - Red 3.4.10 uses a new Lavalink jar that you will need to manually update from `our GitHub <https://github.com/Cog-Creators/Lavalink-Jars/releases/tag/3.3.2.3_1233>`__.
    - We've updated our `application.yml file <https://github.com/Cog-Creators/Red-DiscordBot/blob/3.4.10/redbot/cogs/audio/data/application.yml>`__ and you should update your instance's ``application.yml`` appropriately.


End-user changelog
------------------

Additions
*********

- **Cogs - Streams** - In message template, ``{stream.display_name}`` can now be used to refer to streamer's display name (:issue:`5050`, :issue:`5066`)

    - This is not always the same as ``{stream}`` which refers to the streamer's channel or username

Changes
*******

- Rephrased a few strings and fixed maaaaany grammar issues and typos (:issue:`4793`, :issue:`4832`, :issue:`4955`, :issue:`4966`, :issue:`5015`, :issue:`5019`, :issue:`5029`, :issue:`5038`, :issue:`5055`, :issue:`5080`, :issue:`5081`)
- **Cogs - Admin** - The cog will now log when it leaves a guild due to the serverlock (:issue:`5008`, :issue:`5073`)
- **Cogs - Audio** - The ``[p]audiostats`` command can now only be used by bot owners (:issue:`5017`)
- **Cogs - Audio** - The cog will now check whether it has speak permissions in the channel before performing any actions (:issue:`5012`)
- **Cogs - Audio** - Improved logging in Audio cog (:issue:`5044`)
- **Cogs - Cleanup** - Clarified that ``[p]cleanup`` commands only delete the messages from the current channel (:issue:`5070`)
- **Cogs - Downloader** - ``[p]repo remove`` can now remove multiple repos at the same time (:issue:`4765`, :issue:`5082`)
- **Cogs - General** - The ``[p]urban`` command will now use the default embed color of the bot (:issue:`5014`)
- **Cogs - Modlog** - Modlog will no longer try editing the case's Discord message once it knows that it no longer exists (:issue:`4975`)
- **Cogs - Modlog** - ``[p]modlogset resetcases`` will now ask for confirmation before proceeding (:issue:`4976`)
- **Cogs - Streams** - - Improved logging of API errors in Streams cog (:issue:`4995`)

Removals
********

- **Cogs - Streams** - Smashcast service has been closed and for that reason we have removed support for it from the cog (:issue:`5039`, :issue:`5040`)

Fixes
*****

- **Core - Bot Commands** - Added missing information about the ``showaliases`` setting in ``[p]helpset showsettings`` (:issue:`4971`)
- **Core - Bot Commands** - The help command no longer errors when it doesn't have permission to read message history and menus are enabled (:issue:`4959`, :issue:`5030`)
- **Core - Bot Commands** - Fixed a bug in ``[p]embedset user`` that made it impossible to reset the user's embed setting (:issue:`4962`)
- **Core - Bot Commands** - ``[p]embedset command`` and its subcommands now properly check whether any of the passed command's parents require Embed Links permission (:issue:`4962`)
- **Core - Bot Commands** - Fixed an issue with Red reloading unrelated modules when using ``[p]load`` and ``[p]reload`` (:issue:`4956`, :issue:`4958`)
- |cool| **Core - Command-line Interfaces** - Fixed terminal colors on Windows (:issue:`5063`)
- **Core - Command-line Interfaces** - Fixed the ``--rich-traceback-extra-lines`` flag (:issue:`5028`)
- **Cogs - Audio** - Fixed an issue that made it possible to remove Aikaterna's curated tracks playlist (:issue:`5018`)
- |cool| **Cogs - Audio** - Fixed auto-resume of auto play after Lavalink restart (:issue:`5051`)
- **Cogs - Audio** - Fixed an error with ``[p]audiostats`` caused by players not always having their connection time stored (:issue:`5046`)
- **Cogs - Audio** - Fixed track resuming in a certain edge case (:issue:`4996`)
- **Cogs - Audio** - Fixed an error in ``[p]audioset restart`` (:issue:`4987`)
- **Cogs - Audio** - Fixed an issue with Audio failing when it's missing permissions to send a message in the notification channel (:issue:`4960`)
- |cool| **Cogs - Audio** - Fixed fetching of age-restricted tracks (:issue:`5085`)
- **Cogs - Audio** - Fixed an issue with SoundCloud URLs that ended with a slash (``/``) character (:issue:`5085`)
- **Cogs - CustomCommands** - ``[p]customcom create simple`` no longer errors for a few specific names (:issue:`5026`, :issue:`5027`)
- **Cogs - Downloader** - ``[p]cog install`` now properly shows the repo name rather than ``{repo.name}`` (:issue:`4954`)
- **Cogs - Mod** - ``[p]mute`` no longer errors on muting a bot user if the ``senddm`` option is enabled (:issue:`5071`)
- **Cogs - Mutes** - Forbidden errors during the channel mute are now handled properly in a rare edge case (:issue:`4994`)
- |cool| **Cogs - Streams** - Fixed Picarto support (:issue:`4969`, :issue:`4970`)
- **Cogs - Streams** - ``[p]twitchstream``, ``[p]youtubestream``, and ``[p]picarto`` commands can no longer be run in DMs (:issue:`5036`, :issue:`5035`)
- |cool| **Cogs - Streams** - Fixed Twitch stream alerts for streams that use localized display names (:issue:`5050`, :issue:`5066`)
- **Cogs - Streams** - The cog no longer errors when trying to delete a cached message from a channel that no longer exists (:issue:`5032`, :issue:`5031`)
- **Cogs - Warnings** - The warn action is now taken *after* sending the warn message to the member (:issue:`4713`, :issue:`5004`)


Developer changelog
-------------------

Changes
*******

- **Core - Dependencies** - Bumped discord.py to 1.7.2 (:issue:`5066`)
- **Cogs - Dev** - ``[p]eval``, ``[p]repl``, and ``[p]debug`` commands now, in addition to ``py``, support code blocks with ``python`` syntax (:issue:`5083`)

Fixes
*****

- **Core - Command-line Interfaces** - The log messages shown by the global error handler will now show the trace properly for task done callbacks (:issue:`4980`)
- **Cogs - Dev** - ``[p]eval``, ``[p]repl``, and ``[p]debug`` commands no longer fail to send very long syntax errors (:issue:`5041`)


Documentation changes
---------------------

Additions
*********

- |cool| Added `a guide for making auto-restart service on Mac <autostart_mac>` (:issue:`4082`, :issue:`5020`)
- |cool| Added `cog guide for core commands <cog_guides/core>` (:issue:`1734`, :issue:`4597`)
- |cool| Added `cog guide for Mod cog <cog_guides/mod>` (:issue:`1734`, :issue:`4886`)
- |cool| Added `cog guide for Modlog cog <cog_guides/modlog>` (:issue:`1734`, :issue:`4919`)
- |cool| Added `cog guide for Mutes cog <cog_guides/mutes>` (:issue:`1734`, :issue:`4875`)
- |cool| Added `cog guide for Permissions cog <cog_guides/permissions>` (:issue:`1734`, :issue:`4985`)
- |cool| Added `cog guide for Reports cog <cog_guides/reports>` (:issue:`1734`, :issue:`4882`)
- |cool| Added `cog guide for Warnings cog <cog_guides/warnings>` (:issue:`1734`, :issue:`4920`)
- |cool| Added :ref:`a guide about Trivia list creation <guide_trivia_list_creation>` (:issue:`4595`, :issue:`5023`)
- Added the documentation for `redbot.core.modlog.Case` (:issue:`4979`)
- Added information on how to set the bot not to start on boot anymore to auto-restart docs (:issue:`5020`)

Changes
*******

- Updated Python version in ``pyenv`` and Windows instructions (:issue:`5025`)
- Cog creation guide now includes the ``bot`` as an argument to the cog class (:issue:`4988`)

Removals
********

- Removed PM2 guide (:issue:`4991`)

----

Redbot 3.4.9 (2021-04-06)
=========================

This is a hotfix release fixing an issue with command error handling.

discord.py version has been bumped to 1.7.1.

Thanks again to :ghuser:`Rapptz` for quick response on this issue.

----

Redbot 3.4.8 (2021-04-06)
=========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`6days9weeks`, :ghuser:`aikaterna`, :ghuser:`Drapersniper`, :ghuser:`fixator10`, :ghuser:`Flame442`, :ghuser:`flaree`, :ghuser:`jack1142`, :ghuser:`kingslayer268`, :ghuser:`Kowlin`, :ghuser:`Kreusada`, :ghuser:`Obi-Wan3`, :ghuser:`OofChair`, :ghuser:`palmtree5`, :ghuser:`phenom4n4n`, :ghuser:`PredaaA`, :ghuser:`Predeactor`, :ghuser:`rijusougata13`, :ghuser:`TheDiscordHistorian`, :ghuser:`Tobotimus`, :ghuser:`TrustyJAID`, :ghuser:`Twentysix26`, :ghuser:`Vexed01`

Read before updating
--------------------

#. Information for Audio users that are using an external Lavalink instance (if you don't know what that is, you should skip this point):

    Red 3.4.8 uses a new Lavalink jar that you will need to manually update from `our GitHub <https://github.com/Cog-Creators/Lavalink-Jars/releases/tag/3.3.2.3_1212>`__.

#. Fedora 31 and OpenSUSE Leap 15.1 are no longer supported as they have already reached end of life.


End-user changelog
------------------

Additions
*********

- |cool| **Core** - Added per-command embed settings (:issue:`4049`)

    - See help of ``[p]embedset`` and ``[p]embedset command`` command group for more information
- **Core** - An error message will now be shown when a command that is only available in NSFW channels is used in a non-NSFW channel (:issue:`4933`)
- |cool| **Core - Bot Commands** - ``[p]leave`` accepts server IDs now (:issue:`4831`)
- |cool| **Cogs - Trivia** - Added a new option for hiding the answer to the Trivia answer in a spoiler (:issue:`4700`, :issue:`4877`)

    - ``[p]triviaset usespoilers`` command can be used to enable/disable this option

Changes
*******

- |cool| **Core - Bot Commands** - The ``[p]servers`` command uses menus now (:issue:`4720`, :issue:`4831`)
- |cool| **Core - Bot Commands** - Commands for listing global and local allowlists and blocklists will now, in addition to IDs, contain user/role names (:issue:`4839`)
- **Core - Bot Commands** - Added more singular and plural forms in a bunch of commands in the bot (:issue:`4004`, :issue:`4898`)
- |cool| **Core - Command-line Interfaces** - Added a progress bar to ``redbot-setup convert`` (:issue:`2952`)
- **Cogs - Audio** - Improved playlist extraction (:issue:`4932`)
- |cool| **Cogs - Cleanup** - ``[p]cleanup before`` and ``[p]cleanup after`` commands can now be used without a message ID if the invocation message replies to some message (:issue:`4790`)
- **Cogs - Filter** - Added meaningful error messages for incorrect arguments in the ``[p]bank set`` command (:issue:`4789`, :issue:`4801`)
- **Cogs - Mod** - Improved performance of checking tempban expirations (:issue:`4907`)
- **Cogs - Mutes** - Vastly improved performance of automatic unmute handling (:issue:`4906`)
- **Cogs - Streams** - Streams cog should now load faster on bots that have many stream alerts set up (:issue:`4731`, :issue:`4742`)
- **Cogs - Streams** - Checking Twitch streams will now make less API calls (:issue:`4938`)
- **Cogs - Streams** - Ratelimits from Twitch API are now properly handled (:issue:`4808`, :issue:`4883`)
- **Cogs - Warnings** - Embeds now use the default embed color of the bot (:issue:`4878`)

Removals
********

- **Core - Command-line Interfaces** - Removed the option to drop the entire PostgreSQL database in ``redbot-setup delete`` due to limitations of PostgreSQL (:issue:`3699`, :issue:`3833`)

Fixes
*****

- |cool| **Core** - Messages sent interactively in DM channels no longer fail (:issue:`4876`)
- **Core - Help** - Fixed how the command signature is shown in help for subcommands that have group args (:issue:`4928`)
- **Cogs - Alias** - Fixed issues with command aliases for commands that take an arbitrary, but non-zero, number of arguments (e.g. ``[p]load``) (:issue:`4766`, :issue:`4871`)
- |cool| **Cogs - Audio** - Fixed stuttering (:issue:`4565`)
- |cool| **Cogs - Audio** - Fixed random disconnects (:issue:`4565`)
- |cool| **Cogs - Audio** - Fixed the issues causing the player to be stuck on 00:00 (:issue:`4565`)
- |cool| **Cogs - Audio** - Fixed ghost players (:issue:`4565`)
- |cool| **Cogs - Audio** - Audio will no longer stop playing after a while (:issue:`4565`)
- **Cogs - Audio** - Fixed playlist loading for playlists with over 100 songs (:issue:`4932`)
- **Cogs - Audio** - Fixed an issue with alerts causing errors in playlists being loaded (:issue:`4932`)
- **Cogs - Audio** - Fixed an issue with consent pages appearing while trying to load songs or playlists (:issue:`4932`)
- **Cogs - Downloader** - Improved compatibility with Git 2.31 and newer (:issue:`4897`)
- **Cogs - Mod** - Fixed tracking of nicknames that were set just before nick reset (:issue:`4830`)
- **Cogs - Streams** - Fixed possible memory leak related to automatic message deletion (:issue:`4731`, :issue:`4742`)
- **Cogs - Streams** - Streamer accounts that no longer exist are now properly handled (:issue:`4735`, :issue:`4746`)
- **Cogs - Streams** - Fixed stream alerts being sent even after unloading Streams cog (:issue:`4940`)
- **Cogs - Warnings** - Fixed output of ``[p]warnings`` command for members that are no longer in the server (:issue:`4900`, :issue:`4904`)


Developer changelog
-------------------

Changes
*******

- **Core - Dependencies** - Bumped discord.py version to 1.7.0 (:issue:`4928`)

Deprecations
************

- **Core - Bot Class** - Added ``guild`` parameter to `bot.allowed_by_whitelist_blacklist() <Red.allowed_by_whitelist_blacklist()>` which is meant to replace the deprecated ``guild_id`` parameter (:issue:`4905`, :issue:`4914`)

    - Read the method's documentation for more information
- **Core - Commands Package** - Deprecated importing ``GuildConverter`` from ``redbot.core.commands.converter`` namespace (:issue:`4928`)

    - ``discord.Guild`` or ``GuildConverter`` from ``redbot.core.commands`` should be used instead

Fixes
*****

- **Core - Bot Class** - Fixed ``on_red_api_tokens_update`` not being dispatched when the tokens were removed with ``[p]set api remove`` (:issue:`4916`, :issue:`4917`)


Documentation changes
---------------------

Additions
*********

- |cool| Added `cog guide for Image cog <cog_guides/image>` (:issue:`4821`)

Changes
*******

- Added a note about updating cogs in update message and documentation (:issue:`4910`)
- `getting-started` now contains an explanation of parameters that can take an arbitrary number of arguments (:issue:`4888`, :issue:`4889`)
- All shell commands in the documentation are now prefixed with an unselectable prompt (:issue:`4908`)
- `systemd-service-guide` now asks the user to create the new service file using ``nano`` text editor (:issue:`4869`, :issue:`4870`)

    - Instructions for all Linux-based operating systems now recommend to install ``nano``
- Updated Python version in ``pyenv`` and Windows instructions (:issue:`4864`, :issue:`4942`)
- Added a warning to Arch Linux install guide about the instructions being out-of-date (:issue:`4866`)

Fixes
*****

- Updated Mac install guide with new ``brew`` commands (:issue:`4865`)

----

Redbot 3.4.7 (2021-02-26)
=========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`elijabesu`, :ghuser:`Flame442`, :ghuser:`flaree`, :ghuser:`jack1142`, :ghuser:`Kowlin`, :ghuser:`kreusada`, :ghuser:`palmtree5`, :ghuser:`TrustyJAID`

End-user changelog
------------------

Security
********

- **Cogs - Mutes** - Added proper permission checks to ``[p]muteset senddm`` and ``[p]muteset showmoderator`` (:issue:`4849`)

Changes
*******

- **Core - Bot Commands** - Updated the ``[p]info`` command to more clearly indicate that the instance is owned by a team (:issue:`4851`)

Fixes
*****

- **Cogs - General** - Updated the ``[p]lmgtfy`` command to use the new domain (:issue:`4840`)
- **Cogs - Mutes** - Fixed minor issues with error messages in Mutes cog (:issue:`4847`, :issue:`4850`, :issue:`4853`)


Documentation changes
---------------------

Additions
*********

- |cool| Added `cog guide for General cog <cog_guides/general>` (:issue:`4797`)
- |cool| Added `cog guide for Trivia cog <cog_guides/trivia>` (:issue:`4566`)

----

Redbot 3.4.6 (2021-02-16)
=========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`aikaterna`, :ghuser:`aleclol`, :ghuser:`Andeeeee`, :ghuser:`bobloy`, :ghuser:`BreezeQS`, :ghuser:`Danstr5544`, :ghuser:`Dav-Git`, :ghuser:`Elysweyr`, :ghuser:`Fabian-Evolved`, :ghuser:`fixator10`, :ghuser:`Flame442`, :ghuser:`Injabie3`, :ghuser:`jack1142`, :ghuser:`Kowlin`, :ghuser:`kreusada`, :ghuser:`leblancg`, :ghuser:`maxbooiii`, :ghuser:`NeuroAssassin`, :ghuser:`phenom4n4n`, :ghuser:`PredaaA`, :ghuser:`Predeactor`, :ghuser:`retke`, :ghuser:`siu3334`, :ghuser:`Strafee`, :ghuser:`TheWyn`, :ghuser:`TrustyJAID`, :ghuser:`Vexed01`, :ghuser:`yamikaitou`

Read before updating
--------------------

#. Information for Audio users that are using an external Lavalink instance (if you don't know what that is, you should skip this point):

    Red 3.4.6 uses a new Lavalink jar that you will need to manually update from `our GitHub <https://github.com/Cog-Creators/Lavalink-Jars/releases/tag/3.3.2.3_1199>`__.


End-user changelog
------------------

Security
********

- **Cogs - Mutes** - Added more role hierarchy checks to ensure permission escalations cannot occur on servers with a careless configuration (:issue:`4741`)

Additions
*********

- |cool| **Core - Help** - Help now includes command aliases in the command help (:issue:`3040`)

    - This can be disabled with ``[p]helpset showaliases`` command
- **Cogs - Mod** - Added two new settings for disabling username and nickname tracking (:issue:`4799`)

    - Added a command ``[p]modset trackallnames`` that disables username tracking and overrides the nickname tracking setting for all guilds
    - Added a command ``[p]modset tracknicknames`` that disables nickname tracking in a specific guild
- **Cogs - Mod** - Added a command ``[p]modset deletenames`` that deletes all stored usernames and nicknames (:issue:`4827`)
- **Cogs - Modlog** - Added a command ``[p]listcases`` that allows you to see multiple cases for a user at once (:issue:`4426`)
- |cool| **Cogs - Mutes** - A DM can now be sent to the (un)muted user on mute and unmute (:issue:`3752`, :issue:`4563`)

    - Added ``[p]muteset senddm`` to set whether the DM should be sent (function disabled by default)
    - Added ``[p]muteset showmoderator`` to set whether the DM sent to the user should include the name of the moderator that muted the user (function disabled by default)
- **Cogs - Trivia - Lists** - Added new Who's That Pokémon - Gen. VI trivia list (:issue:`4785`)

Changes
*******

- **Core - Bot Commands** - Added a friendly error message to ``[p]load`` that is shown when trying to load a cog with a command name that is already taken by a different cog (:issue:`3870`)
- |cool| **Core - Command-line Interfaces** - Improvements and fixes for our new (colorful) logging (:issue:`4702`, :issue:`4726`)

    - The colors used have been adjusted to be readable on many more terminal applications
    - The ``NO_COLOR`` environment variable can now be set to forcefully disable all colors in the console output
    - Tracebacks will now use the full width of the terminal again
    - Tracebacks no longer contain multiple lines per stack level (this can now be changed with the flag ``--rich-traceback-extra-lines``)
    - Disabled syntax highlighting on the log messages
    - Dev cog no longer captures logging output
    - Added some cool features for developers

        - Added the flag ``--rich-traceback-extra-lines`` which can be used to set the number of additional lines in tracebacks
        - Added the flag ``--rich-traceback-show-locals`` which enables showing local variables in tracebacks

    - Improved and fixed a few other minor things
- **Core - Dependencies** - Red's dependencies have been bumped (:issue:`4572`)
- **Cogs - Admin** - ``[p]selfrole`` can now be used without a subcommand and passed with a selfrole directly to add/remove it from the user running the command (:issue:`4826`)
- **Cogs - Audio** - Improved detection of embed players for fallback on age-restricted YT tracks (:issue:`4818`, :issue:`4819`)
- **Cogs - Audio** - Improved MP4/AAC decoding (:issue:`4818`, :issue:`4819`)
- **Cogs - Audio** - Requests for YT tracks are now retried if the initial request causes a connection reset (:issue:`4818`, :issue:`4819`)
- **Cogs - Cleanup** - Renamed the ``[p]cleanup spam`` command to ``[p]cleanup duplicates``, with the old name kept as an alias for the time being (:issue:`4814`)
- **Cogs - Economy** - ``[p]economyset rolepaydayamount`` can now remove the previously set payday amount (:issue:`4661`, :issue:`4758`)
- **Cogs - Filter** - Added a case type ``filterhit`` which is used to log filter hits (:issue:`4676`, :issue:`4739`)
- **Cogs - Mod** - Added usage examples to ``[p]kick``, ``[p]ban``, ``[p]massban``, and ``[p]tempban`` (:issue:`4712`, :issue:`4715`)
- **Cogs - Mod** - Updated DM on kick/ban to use bot's default embed color (:issue:`4822`)
- **Cogs - Modlog** - Added typing indicator to ``[p]casesfor`` command (:issue:`4426`)
- **Cogs - Reports** - Reports now use the default embed color of the bot (:issue:`4800`)
- **Cogs - Trivia** - Payout for trivia sessions ending in a tie now gets split between all the players with the highest score (:issue:`3931`, :issue:`4649`)
- **Cogs - Trivia - Lists** - Updated answers regarding some of the hero's health and abilities in the ``overwatch`` trivia list (:issue:`4805`)

Fixes
*****

- Various grammar fixes (:issue:`4705`, :issue:`4748`, :issue:`4750`, :issue:`4763`, :issue:`4788`, :issue:`4792`, :issue:`4810`)
- **Core - Bot Commands** - Fixed command usage in the help messages for few commands in Red (:issue:`4599`, :issue:`4733`)
- **Core - Bot Commands** - Fixed errors in ``[p]command defaultdisablecog`` and ``[p]command defaultenablecog`` commands (:issue:`4767`, :issue:`4768`)
- **Core - Bot Commands** - ``[p]command listdisabled guild`` can no longer be run in DMs (:issue:`4771`, :issue:`4772`)
- |cool| **Core - Command-line Interfaces** - Fixed the rotation of Red's logs that could before result in big disk usage (:issue:`4405`, :issue:`4738`)
- **Core - Command-line Interfaces** - Fixed errors appearing when using Ctrl+C to interrupt ``redbot --edit`` (:issue:`3777`, :issue:`4572`)
- **Cogs - Cleanup** - Fixed an error from passing an overly large integer as a message ID to ``[p]cleanup after`` and ``[p]cleanup before`` (:issue:`4791`)
- **Cogs - Mod** - The ``[p]tempban`` command no longer errors out when trying to ban a user in a guild with the vanity url feature that doesn't have a vanity url set (:issue:`4714`)
- **Cogs - Mod** - Fixed an edge case in role hierarchy checks (:issue:`4740`)
- **Cogs - Mutes** - Fixed an edge case in role hierarchy checks (:issue:`4740`)
- **Cogs - Mutes** - The modlog reason no longer contains leading whitespace when it's passed *after* the mute time (:issue:`4749`)
- **Cogs - Mutes** - Help descriptions of the cog and its commands now get translated properly (:issue:`4815`)
- **Cogs - Streams** - Fixed incorrect timezone offsets for some YouTube stream schedules (:issue:`4693`, :issue:`4694`)
- **Cogs - Streams** - Fixed meaningless errors happening when the YouTube API key becomes invalid or when the YouTube quota is exceeded (:issue:`4745`)


Developer changelog
-------------------

Additions
*********

- **Core - Bot Class** - Added an event ``on_red_before_identify`` that is dispatched before IDENTIFYing a session (:issue:`4647`)
- **Core - Utils Package** - Added a function `redbot.core.utils.chat_formatting.spoiler()` that wraps the given text in a spoiler (:issue:`4754`)
- |cool| **Cogs - Dev** - Cogs can now add their own variables to the environment of ``[p]debug``, ``[p]eval``, and ``[p]repl`` commands (:issue:`4667`)

    - Variables can be added and removed from the environment of Dev cog using two new methods:

        - `bot.add_dev_env_value() <Red.add_dev_env_value()>`
        - `bot.remove_dev_env_value() <Red.remove_dev_env_value()>`

Changes
*******

- **Core - Dependencies** - Updated versions of the libraries used in Red: discord.py to 1.6.0, aiohttp to 3.7.3 (:issue:`4728`)

Fixes
*****

- **Cogs - Dev** - Help descriptions of the cog and its commands now get translated properly (:issue:`4815`)

Documentation changes
---------------------

Additions
*********

- |cool| Added `cog guide for Filter cog <cog_guides/filter>` (:issue:`4579`)

Changes
*******

- Added information about the Red Index to `guide_publish_cogs` (:issue:`4778`)
- Restructured the host list (:issue:`4710`)
- Clarified how to use pm2 with ``pyenv virtualenv`` (:issue:`4709`)
- Updated Python version in ``pyenv`` and Windows instructions (:issue:`4770`)

Fixes
*****

- Updated the pip command for Red with the postgres extra in Linux/macOS install guide to work on zsh shell (:issue:`4697`)

----

Redbot 3.4.5 (2020-12-24)
=========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`Injabie3`, :ghuser:`NeuroAssassin`

This is a hotfix release fixing an issue with Streams cog failing to load.

End-user changelog
------------------

Fixes
*****

- **Cogs - Streams** - Fixed Streams failing to load and work properly (:issue:`4687`, :issue:`4688`)

----

Redbot 3.4.4 (2020-12-24)
=========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`aikaterna`, :ghuser:`bobloy`, :ghuser:`Flame442`, :ghuser:`flaree`, :ghuser:`jack1142`, :ghuser:`Kowlin`, :ghuser:`kreus7`, :ghuser:`NeuroAssassin`, :ghuser:`npc203`, :ghuser:`palmtree5`, :ghuser:`phenom4n4n`, :ghuser:`Predeactor`, :ghuser:`retke`, :ghuser:`siu3334`, :ghuser:`Vexed01`, :ghuser:`yamikaitou`

Read before updating
--------------------

#. Information for Audio users that are using an external Lavalink instance (if you don't know what that is, you should skip this point):

    Red 3.4.4 uses a new Lavalink jar that you will need to manually update from `our GitHub <https://github.com/Cog-Creators/Lavalink-Jars/releases/tag/3.3.2.2_1170>`__.

#. Ubuntu 16.04 is no longer supported as it will soon reach its end of life and it is no longer viable for us to maintain support for it.

    While you might still be able to run Red on it, we will no longer put any resources into supporting it. If you're using Ubuntu 16.04, we highly recommend that you upgrade to the latest LTS version of Ubuntu.


End-user changelog
------------------

Additions
*********

- |cool| **Core - Command-line Interfaces** - Red's logging will now shine in your terminal more than ever (:issue:`4577`)
- |cool| **Cogs - Streams** - YouTube stream schedules are now announced before the stream (:issue:`4615`)

    - Alerts about YouTube stream schedules can be disabled with a new ``[p]streamset ignoreschedule`` command (:issue:`4615`)
- **Cogs - Trivia - Lists** - Added ``whosthatpokemon5`` trivia list containing Pokémon from the 5th generation (:issue:`4646`)
- **Cogs - Trivia - Lists** - Added ``geography`` trivia list (:issue:`4618`)

Changes
*******

- **Core** - Added a friendly error when the duration provided to commands that use the ``commands.TimedeltaConverter`` converter is out of the maximum bounds allowed by Python interpreter (:issue:`4019`, :issue:`4628`, :issue:`4630`)
- **Core - Bot Commands** - Improved consistency of command usage in the help messages within all commands in Core Red (:issue:`4589`)
- **Cogs - Audio** - Added more friendly messages for 429 errors to let users know they have been temporarily banned from accessing the service instead of a generic Lavalink error (:issue:`4683`)
- **Cogs - Audio** - Environment information will now be appended to Lavalink tracebacks in the spring.log (:issue:`4683`)
- **Cogs - Cleanup** - ``[p]cleanup self`` will now delete the command message when the bot has permissions to do so (:issue:`4640`)
- **Cogs - Economy** - ``[p]economyset slotmin`` and ``[p]economyset slotmax`` now warn when the new value will cause the slots command to not work (:issue:`4583`)
- **Cogs - General** - Updated features list in ``[p]serverinfo`` with the latest changes from Discord (:issue:`4678`)
- **Cogs - Streams** - Improved error logging (:issue:`4680`)

Fixes
*****

- **Core - Bot Commands** - Fixed an error when removing path from a different operating system than the bot is currently running on with ``[p]removepath`` (:issue:`2609`, :issue:`4662`, :issue:`4466`)
- **Cogs - Audio** - Fixed ``[p]llset java`` failing to set the Java executable path (:issue:`4621`, :issue:`4624`)
- |cool| **Cogs - Audio** - Fixed SoundCloud playback (:issue:`4683`)
- |cool| **Cogs - Audio** - Fixed YouTube age-restricted track playback (:issue:`4683`)
- **Cogs - Mod** - ``[p]ban`` command will no longer error out when the given reason is too long (:issue:`4187`, :issue:`4189`)
- |cool| **Cogs - Streams** - Scheduled YouTube streams now work properly with the cog (:issue:`3691`, :issue:`4615`)


Developer changelog
-------------------

Additions
*********

- **Core - Utils Package** - `get_audit_reason()` can now be passed a ``shorten`` keyword argument which will automatically shorten the returned audit reason to fit the max length allowed by Discord audit logs (:issue:`4189`)
- |cool| **Cogs - Dev** - Added new ``[p]bypasscooldown`` command that allows owners to bypass command cooldowns (:issue:`4440`)

Changes
*******

- **Core - Bot Class** - ``bot.remove_command()`` now returns the command object of the removed command as does the equivalent method from `discord.ext.commands.Bot` class (:issue:`4636`)


Documentation changes
---------------------

Additions
*********

- |cool| Added `cog guide for Downloader cog <cog_guides/downloader>` (:issue:`4511`)
- |cool| Added `cog guide for Economy cog <cog_guides/economy>` (:issue:`4519`)
- |cool| Added `cog guide for Streams cog <cog_guides/streams>` (:issue:`4521`)
- Added `guide_cog_creators` document (:issue:`4637`)

Removals
********

- Removed install instructions for Ubuntu 16.04 (:issue:`4650`)

----

Redbot 3.4.3 (2020-11-16)
=========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`aikaterna`, :ghuser:`bobloy`, :ghuser:`Flame442`, :ghuser:`jack1142`, :ghuser:`KianBral`, :ghuser:`maxbooiii`, :ghuser:`phenom4n4n`, :ghuser:`Predeactor`, :ghuser:`retke`

Read before updating
--------------------

#. Information for Audio users that are using an external Lavalink instance (if you don't know what that is, you should skip this point):

    Red 3.4.3 uses a new Lavalink jar that you will need to manually update from `our GitHub <https://github.com/Cog-Creators/Lavalink-Jars/releases/tag/3.3.1.4_1132>`__.

End-user changelog
------------------

Additions
*********

- **Core - Bot Commands** - Added ``[p]set competing`` command that allows users to set the bot's competing status (:issue:`4607`, :issue:`4609`)
- |cool| **Cogs - Audio** - Added support for SoundCloud HLS streams (:issue:`4608`)

Changes
*******

- **Cogs - Audio** - Improved AAC audio handling (:issue:`4608`)
- **Cogs - Trivia** - ``[p]triviaset custom upload`` now ensures that the filename is lowercase when uploading (:issue:`4594`)

Fixes
*****

- **Cogs - Audio** - Volume changes on ARM systems running a 64 bit OS will now work again (:issue:`4608`)
- |cool| **Cogs - Audio** - Fixed only 100 results being returned on a Youtube playlist (:issue:`4608`)
- |cool| **Cogs - Audio** - Fixed YouTube VOD duration being set to unknown (:issue:`3885`, :issue:`4608`)
- |cool| **Cogs - Audio** - Fixed some YouTube livestreams getting stuck (:issue:`4608`)
- **Cogs - Audio** - Fixed internal Lavalink manager failing for Java with untypical version formats (:issue:`4608`)
- **Cogs - Economy** - The ``[p]leaderboard`` command no longer fails in DMs when a global bank is used (:issue:`4569`)
- **Cogs - Mod** - The ban reason is now properly set in the audit log and modlog when using the ``[p]massban`` command (:issue:`4575`)
- **Cogs - Mod** - The ``[p]userinfo`` command now shows the new Competing activity (:issue:`4610`, :issue:`4611`)
- **Cogs - Modlog** - The ``[p]case`` and ``[p]casesfor`` commands no longer fail when the bot doesn't have Read Message History permission in the modlog channel (:issue:`4587`, :issue:`4588`)
- **Cogs - Mutes** - Fixed automatic remuting on member join for indefinite mutes (:issue:`4568`)


Developer changelog
-------------------

Fixes
*****

- **Core - Modlog** - ``modlog.get_case()`` and methods using it no longer raise when the bot doesn't have Read Message History permission in the modlog channel (:issue:`4587`, :issue:`4588`)


Documentation changes
---------------------

Additions
*********

- |cool| Added `guide for Cog Manager UI <cogmanagerui>` (:issue:`4152`)
- |cool| Added `cog guide for CustomCommands cog <customcommands>` (:issue:`4490`)

----

Redbot 3.4.2 (2020-10-28)
=========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`aikaterna`, :ghuser:`Drapersniper`, :ghuser:`jack1142`, :ghuser:`Kowlin`, :ghuser:`PredaaA`, :ghuser:`Stonedestroyer`

Read before updating
--------------------

#. Information for Audio users that are using an external Lavalink instance (if you don't know what that is, you should skip this point):

    Red 3.4.2 uses a new Lavalink jar that you will need to manually update from `our GitHub <https://github.com/Cog-Creators/Lavalink-Jars/releases/tag/3.3.1.4_1128>`__.

End-user changelog
------------------

Changes
*******

- **Core - Command-line Interfaces** - Added info about the metadata file to ``redbot --debuginfo`` (:issue:`4557`)
- **Cogs - Audio** - Commands in ``[p]llset`` group can now be used in DMs (:issue:`4562`)
- **Cogs - Streams** - Added error messages when exceeding the YouTube quota in the Streams cog (:issue:`4552`)
- **Cogs - Streams** - Improved logging for unexpected errors in the Streams cog (:issue:`4552`)

Fixes
*****

- **Cogs - Audio** - Fixed the ``[p]local search`` command (:issue:`4553`)
- |cool| **Cogs - Audio** - Fixed random "Something broke when playing the track." errors for YouTube tracks (:issue:`4559`)
- **Cogs - Mod** - Fixed ``[p]massban`` not working for banning members that are in the server (:issue:`4556`, :issue:`4555`)


Documentation changes
---------------------

Additions
*********

- |cool| Added `cog guide for Cleanup cog <cleanup>` (:issue:`4488`)

Changes
*******

- Removed multi-line commands from Linux install guides to avoid confusing readers (:issue:`4550`)

----

Redbot 3.4.1 (2020-10-27)
=========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`absj30`, :ghuser:`aikaterna`, :ghuser:`bobloy`, :ghuser:`chloecormier`, :ghuser:`Dav-Git`, :ghuser:`Drapersniper`, :ghuser:`fixator10`, :ghuser:`Flame442`, :ghuser:`flaree`, :ghuser:`Generaleoley`, :ghuser:`hisztendahl`, :ghuser:`jack1142`, :ghuser:`KaiGucci`, :ghuser:`Kowlin`, :ghuser:`maxbooiii`, :ghuser:`MeatyChunks`, :ghuser:`NeuroAssassin`, :ghuser:`nfitzen`, :ghuser:`palmtree5`, :ghuser:`phenom4n4n`, :ghuser:`PredaaA`, :ghuser:`Predeactor`, :ghuser:`PythonTryHard`, :ghuser:`SharkyTheKing`, :ghuser:`Stonedestroyer`, :ghuser:`thisisjvgrace`, :ghuser:`TrustyJAID`, :ghuser:`TurnrDev`, :ghuser:`Vexed01`, :ghuser:`Vuks69`, :ghuser:`xBlynd`, :ghuser:`zephyrkul`

Read before updating
--------------------

#. This release fixes a security issue in Mod cog. See `Security changelog below <important-341-2>` for more information.
#. This Red update bumps discord.py to version 1.5.1, which explicitly requests Discord intents. Red requires all Privileged Intents to be enabled. More information can be found at :ref:`enabling-privileged-intents`.
#. Mutes functionality has been moved from the Mod cog to a new separate cog (Mutes) featuring timed and role-based mutes. If you were using it (or want to start now), you can load the new cog with ``[p]load mutes``. You can see the full `Removals changelog below <important-341-1>`.
#. Information for Audio users that are using an external Lavalink instance (if you don't know what that is, you should skip this point):

   We've updated our `application.yml file <https://github.com/Cog-Creators/Red-DiscordBot/blob/3.4.1/redbot/cogs/audio/data/application.yml>`__ and you should update your instance's ``application.yml`` appropriately.
   Please ensure that the WS port in Audio's settings (``[p]llset wsport``) is set to the port from the ``application.yml``.

End-user changelog
------------------

.. _important-341-2:

Security
********

**NOTE:** If you can't update immediately, we recommend globally disabling the affected command until you can.

- **Cogs - Mod** - Fixed unauthorized privilege escalation exploit in ``[p]massban`` (also called ``[p]hackban``) command. Full security advisory `can be found on our GitHub <https://github.com/Cog-Creators/Red-DiscordBot/security/advisories/GHSA-mp9m-g7qj-6vqr>`__.

Additions
*********

- **Core - Bot Commands** - Added ``[p]set api list`` to list all currently set API services, without tokens (:issue:`4370`)
- **Core - Bot Commands** - Added ``[p]set api remove`` to remove API services, including tokens (:issue:`4370`)
- **Core - Bot Commands** - Added ``[p]helpset usetick``, toggling command message being ticked when help is sent to DM (:issue:`4467`, :issue:`4075`)
- |cool| **Core - i18n** - Locales and regional formats can now be set in individual guilds using ``[p]set locale`` and ``[p]set regionalformat`` (:issue:`3896`, :issue:`1970`)

    - Global locale and regional format setters have been renamed to ``[p]set globallocale`` and ``[p]set globalregionalformat``
- **Cogs - Audio** - Added the Global Audio API, to cut down on Youtube 429 errors and allow Spotify playback past user's quota. (:issue:`4446`)
- |cool| **Cogs - Audio** - Added persistent queues, allowing for queues to be restored on a bot restart or cog reload (:issue:`4446`)
- **Cogs - Audio** - Added ``[p]audioset restart``, allowing for Lavalink connection to be restarted (:issue:`4446`)
- |cool| **Cogs - Audio** - Added ``[p]audioset autodeafen``, allowing for bot to auto-deafen itself when entering voice channel (:issue:`4446`)
- **Cogs - Audio** - Added ``[p]audioset mycountrycode``, allowing Spotify search locale per user (:issue:`4446`)
- **Cogs - Audio** - Added ``[p]llset java``, allowing for a custom Java executable path (:issue:`4446`)
- **Cogs - Audio** - Added ``[p]llset info`` to show Lavalink settings (:issue:`4527`)
- **Cogs - Audio** - Added ``[p]audioset logs`` to download Lavalink logs if the Lavalink server is set to internal (:issue:`4527`)
- **Cogs - Mod** - Added ``[p]modset mentionspam strict`` allowing for duplicated mentions to count towards the mention spam cap (:issue:`4359`)
- |cool| **Cogs - Mod** - Added a default tempban duration for ``[p]tempban`` (:issue:`4473`, :issue:`3992`)
- |cool| **Cogs - Mutes** - Added ``[p]muteset forcerole`` to make mutes role based, instead of permission based (:issue:`3634`)
- |cool| **Cogs - Mutes** - Added an optional time argument to all mutes, to specify when the user should be unmuted (:issue:`3634`)
- **Cogs - Trivia - Lists** - Added new MLB trivia list (:issue:`4455`)
- **Cogs - Trivia - Lists** - Added new Who's That Pokémon - Gen. IV trivia list (:issue:`4434`)
- **Cogs - Trivia - Lists** - Added new Hockey trivia list (:issue:`4384`)

Changes
*******

- Replaced a few instances of Red with the bot name in command docstrings (:issue:`4470`)
- **Core - Bot Commands** - Added a default color field to ``[p]set showsettings`` (:issue:`4498`, :issue:`4497`)
- **Core - Bot Commands** - Added the datapath and metadata file to ``[p]debuginfo`` (:issue:`4524`)
- **Core - Bot Commands** - Added a list of disabled intents to ``[p]debuginfo`` (:issue:`4423`)
- **Core - Dependencies** - Bumped discord.py dependency to version 1.5.1 (:issue:`4423`)
- **Cogs - Audio** - Removed lavalink logs from being added to backup (:issue:`4453`, :issue:`4452`)
- **Cogs - Audio** - Removed stream durations from being in queue duration (:issue:`4513`)
- **Cogs - Cleanup** - Allowed ``[p]cleanup self`` to work in DMs for all users (:issue:`4481`)
- **Cogs - Economy** - Added an embed option for ``[p]leaderboard`` (:issue:`4184`, :issue:`4104`)
- |cool| **Cogs - Mod** - Added an option to ban users not in the guild to ``[p]ban`` (:issue:`4422`, :issue:`4419`)
- **Cogs - Mod** - Renamed ``[p]hackban`` to ``[p]massban``, keeping ``[p]hackban`` as an alias, allowing for multiple users to be banned at once (:issue:`4422`, :issue:`4419`)
- **Cogs - Mutes** - Changed ``[p]mute`` to only handle serverwide muting, ``[p]mute voice`` and ``[p]mute channel`` have been moved to separate commands called ``[p]mutechannel`` and ``[p]mutevoice`` (:issue:`3634`)
- |cool| **Cogs - Mutes** - Mute commands can now take multiple user arguments, to mute multiple users at a time (:issue:`3634`)
- **Cogs - Warnings** - Added bool arguments to toggle commands to improve consistency (:issue:`4409`)

.. _important-341-1:

Removals
********

- **Cogs - Mod** - Moved mutes to a separate, individual cog (:issue:`3634`)

Fixes
*****

- Fixed grammar in places scattered throughout bot (:issue:`4500`)
- **Core** - Fixed an ungraceful error being raised when a bot left a guild while a menu was open (:issue:`3902`)
- **Core - Bot Commands** - Fixed an incorrect error being reported on ``[p]set name`` when the passed name was longer than 32 characters (:issue:`4364`, :issue:`4363`)
- **Core - Bot Commands** - Fixed ``[p]set nickname`` erroring when the passed name was longer than 32 characters (:issue:`4364`, :issue:`4363`)
- **Core - Bot Commands** - Fixed an ungraceful error being raised when running ``[p]traceback`` with closed DMs (:issue:`4329`)
- **Core - Bot Commands** - Fixed errors that could arise from invalid URLs in ``[p]set avatar`` (:issue:`4437`)
- **Core - Bot Commands** - Fixed an error being raised with ``[p]set nickname`` when no nickname was provided (:issue:`4451`)
- **Core - Bot Commands** - Fixed and clarified errors being raised with ``[p]set username`` (:issue:`4463`)
- **Core - Bot Commands** - Fixed an ungraceful error being raised when the output of ``[p]unload`` is larger than 2k characters (:issue:`4469`)
- **Core - Bot Commands** - Fixed an ungraceful error being raised when running ``[p]choose`` with empty options (:issue:`4499`)
- **Core - Bot Commands** - Fixed info missing on the non-embed version of ``[p]debuginfo`` (:issue:`4524`)
- **Core - Dependencies** - Properly define supported Python versions to be lower than 3.9 (:issue:`4538`)
- **Cogs - Audio** - Scattered grammar and typo fixes (:issue:`4446`)
- |cool| **Cogs - Audio** - Fixed Bandcamp playback (:issue:`4504`)
- |cool| **Cogs - Audio** - Fixed YouTube playlist playback (:issue:`4504`)
- |cool| **Cogs - Audio** - Fixed YouTube searching issues (:issue:`4504`)
- |cool| **Cogs - Audio** - Fixed YouTube age restricted track playback (:issue:`4504`)
- **Cogs - Audio** - Fixed the Audio cog not being translated when setting locale (:issue:`4492`, :issue:`4495`)
- |cool| **Cogs - Audio** - Fixed tracks getting stuck at 0:00 after long player sessions (:issue:`4529`)
- **Cogs - CustomCommands** - Fixed an ungraceful error being thrown on ``[p]cc edit`` (:issue:`4325`)
- **Cogs - General** - Fixed issues with text not being properly URL encoded (:issue:`4024`)
- **Cogs - General** - Fixed an ungraceful error occurring when a title is longer than 256 characters in ``[p]urban`` (:issue:`4474`)
- **Cogs - General** - Changed "boosters" to "boosts" in ``[p]serverinfo`` to clarify what the number represents (:issue:`4507`)
- **Cogs - Mod** - Fixed nicknames not being properly stored and logged (:issue:`4131`)
- **Cogs - Mod** - Fixed plural typos in ``[p]userinfo`` (:issue:`4397`, :issue:`4379`)
- **Cogs - Modlog** - Fixed an error being raised when running ``[p]casesfor`` and ``[p]case`` (:issue:`4415`)
- **Cogs - Modlog** - Long reasons in Modlog are now properly shortened in message content (:issue:`4541`)
- **Cogs - Trivia - Lists** - Fixed incorrect order of Machamp and Machoke questions (:issue:`4424`)
- **Cogs - Warnings** - Fixed users being able to warn users above them in hierarchy (:issue:`4100`)


Developer changelog
-------------------

| **Important:**
| 1. Red now allows users to set locale per guild, which requires 3rd-party cogs to set contextual locale manually in code ran outside of command's context. See the `Additions changelog below <important-dev-341-1>` for more information.

.. _important-dev-341-1:

Additions
*********

- **Core - Bot Class** - Added `bot.get_or_fetch_user() <Red.get_or_fetch_user()>` and `bot.get_or_fetch_member() <Red.get_or_fetch_member()>` methods (:issue:`4403`, :issue:`4402`)
- **Core - Bot Class** - Added `bot.remove_shared_api_services() <Red.remove_shared_api_services()>` to remove all keys and tokens associated with an API service (:issue:`4370`)
- **Core - Bot Class** - Added an option to return all tokens for an API service if ``service_name`` is not specified in `bot.get_shared_api_tokens() <Red.get_shared_api_tokens()>` (:issue:`4370`)
- **Core - Dependencies** - Added ``[all]`` and ``[dev]`` extras to the ``Red-DiscordBot`` package (:issue:`4443`)
- |cool| **Core - i18n** - Added API for setting contextual locales (:issue:`3896`, :issue:`1970`)

    - New function added: `redbot.core.i18n.set_contextual_locales_from_guild()`
    - Contextual locale is automatically set for commands and only needs to be done manually for things like event listeners; see `recommendations-for-cog-creators` for more information
- **Core - Modlog** - Added ``last_known_username`` parameter to `modlog.create_case()` function (:issue:`4326`)
- |cool| **Core - Utils Package** - Added `redbot.core.utils.get_end_user_data_statement()` and `redbot.core.utils.get_end_user_data_statement_or_raise()` to attempt to fetch a cog's End User Data Statement (:issue:`4404`)
- **Core - Utils Package** - Added `redbot.core.utils.chat_formatting.quote()` to quote text in a message (:issue:`4425`)
- |cool| **Cogs - Dev** - Added ``[p]repl pause`` to pause/resume the REPL session in the current channel (:issue:`4366`)
- |cool| **Cogs - Downloader** - Added JSON schema files for ``info.json`` files (:issue:`4375`)

Changes
*******

- **Core - Bank** - Bank API methods now consistently throw TypeError if a non-integer amount is supplied (:issue:`4376`)
- **Core - Commands Package** - Moved ``redbot.core.checks.bot_in_a_guild()`` to `redbot.core.commands.bot_in_a_guild()` (old name has been left as an alias) (:issue:`4515`, :issue:`4510`)
- |cool| **Core - Modlog** - Added an option to accept a ``discord.Object`` in `modlog.create_case()` (:issue:`4326`)

Deprecations
************

- **Core - Utils Package** - Deprecated ``redbot.core.utils.mod.is_allowed_by_hierarchy()`` (:issue:`4435`)

Fixes
*****

- **Core - Modlog** - Fixed an error being raised with a deleted channel in `Case.message_content()` (:issue:`4415`)


Documentation changes
---------------------

Additions
*********

- Added custom group documentation and tutorial (:issue:`4416`, :issue:`2896`)
- Added guide to creating a Bot Application in Discord Developer Portal, with enabling intents (:issue:`4502`)

Changes
*******

- Clarified that naive ``datetime`` objects will be treated as local times for parameters ``created_at`` and ``until`` in `modlog.create_case()` (:issue:`4389`)
- Replaced the link to the approved repository list on CogBoard and references to ``cogs.red`` with a link to new Red Index (:issue:`4439`)
- Improved documentation about arguments in command syntax (:issue:`4058`)

----

Redbot 3.4.0 (2020-08-17)
=========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`Dav-Git`, :ghuser:`DevilXD`, :ghuser:`douglas-cpp`, :ghuser:`Drapersniper`, :ghuser:`flaree`, :ghuser:`jack1142`, :ghuser:`kablekompany`, :ghuser:`Kowlin`, :ghuser:`maxbooiii`, :ghuser:`MeatyChunks`, :ghuser:`mikeshardmind`, :ghuser:`NeuroAssassin`, :ghuser:`PredaaA`, :ghuser:`Predeactor`, :ghuser:`retke`, :ghuser:`SharkyTheKing`, :ghuser:`thisisjvgrace`, :ghuser:`Tinonb`, :ghuser:`TrustyJAID`, :ghuser:`Twentysix26`, :ghuser:`Vexed01`, :ghuser:`zephyrkul`

Read before updating
--------------------

#. Red 3.4 comes with support for data deletion requests. Bot owners should read `red_core_data_statement` to ensure they know what information about their users is stored by the bot.
#. Debian Stretch, Fedora 30 and lower, and OpenSUSE Leap 15.0 and lower are no longer supported as they have already reached end of life.
#. There's been a change in behavior of ``[p]tempban``. Look at `Changes changelog for Mod cog <important-340-1>` for full details.
#. There's been a change in behavior of announcements in Admin cog. Look at `Changes changelog for Admin cog <important-340-1>` for full details.
#. Red 3.4 comes with breaking changes for cog developers. Look at `Developer changelog <important-340-3>` for full details.

End-user changelog
------------------

Security
********

- **Cogs - Streams** - Fixed critical vulnerability that could allow remote code execution (CVE-2020-15147), see `security advisory GHSA-7257-96vg-qf6x <https://github.com/Cog-Creators/Red-DiscordBot/security/advisories/GHSA-7257-96vg-qf6x>`__ for more information (:issue:`4183`)

Additions
*********

- |cool| **Core** - Added per-guild cog disabling (:issue:`4043`, :issue:`3945`)

    - Bot owners can set the default state for a cog using ``[p]command defaultdisablecog`` and ``[p]command defaultenablecog`` commands
    - Guild owners can enable/disable cogs for their guild using ``[p]command disablecog`` and ``[p]command enablecog`` commands
    - Cogs disabled in the guild can be listed with ``[p]command listdisabledcogs``
- |cool| **Core** - Added support for data deletion requests; see `red_core_data_statement` for more information (:issue:`4045`)
- **Core - Bot Commands** - Added ``[p]helpset showsettings`` command (:issue:`4013`, :issue:`4022`)
- |cool| **Cogs - Mod** - Users can now set mention spam triggers which will warn or kick the user. See ``[p]modset mentionspam`` for more information (:issue:`3786`, :issue:`4038`)
- **Cogs - Trivia - Lists** - Added ``whosthatpokemon2`` trivia containing Pokémons from 2nd generation (:issue:`4102`)
- **Cogs - Trivia - Lists** - Added ``whosthatpokemon3`` trivia containing Pokémons from 3rd generation (:issue:`4141`)

.. _important-340-1:

Changes
*******

- ``[p]set nickname``, ``[p]set serverprefix``, ``[p]streamalert``, and ``[p]streamset`` commands now can be run by users with permissions related to the actions they're making (:issue:`4109`)
- Updated Red's emoji usage to ensure consistent rendering accross different devices (:issue:`4106`, :issue:`4105`, :issue:`4127`)
- **Core - Bot Commands** - ``[p]licenseinfo`` now has a 3 minute cooldown to prevent a single user from spamming channel by using it (:issue:`4110`)
- **Core - Bot Commands** - Whitelist and blacklist are now called allowlist and blocklist. Old names have been left as aliases (:issue:`4138`)
- **Core - Command-line Interfaces** - Red now logs clearer error if it can't find package to load in any cog path during bot startup (:issue:`4079`)
- |cool| **Cogs - Admin** - ``[p]announce`` will now only send announcements to guilds that have explicitly configured text channel to send announcements to using ``[p]announceset channel`` command (:issue:`4088`, :issue:`4089`)
- |cool| **Cogs - Downloader** - ``[p]cog info`` command now shows end user data statement made by the cog creator (:issue:`4169`)
- |cool| **Cogs - Downloader** - ``[p]cog update`` command will now notify the user if cog's end user data statement has changed since last update (:issue:`4169`)
- **Cogs - General** - Updated features list in ``[p]serverinfo`` with the latest changes from Discord (:issue:`4116`)
- **Cogs - General** - Simple version of ``[p]serverinfo`` now shows info about more detailed ``[p]serverinfo 1`` (:issue:`4121`)
- **Cogs - Mod** - ``[p]tempban`` now respects default days setting (``[p]modset defaultdays``) (:issue:`3993`)
- |cool| **Cogs - Mod** - ``[p]mute voice`` and ``[p]unmute voice`` now take action instantly if bot has Move Members permission (:issue:`4064`)
- **Cogs - Mod** - Added typing to ``[p](un)mute guild`` to indicate that mute is being processed (:issue:`4066`, :issue:`4172`)
- **Cogs - Modlog** - Added timestamp to text version of ``[p]casesfor`` and ``[p]case`` commands (:issue:`4118`, :issue:`4137`)
- **Cogs - Streams** - Stream alerts will no longer make roles temporarily mentionable if bot has "Mention @everyone, @here, and All Roles" permission in the channel (:issue:`4182`)
- **Cogs - Streams** - Hitbox commands have been renamed to smashcast (:issue:`4161`)
- **Cogs - Streams** - Improve error messages for invalid channel names/IDs (:issue:`4147`, :issue:`4148`)

Removals
********

- **Cogs - Streams** - Mixer service has been closed and for that reason we've removed support for it from the cog (:issue:`4072`)

Fixes
*****

- Fixed timestamp storage in few places in Red (:issue:`4017`)


.. _important-340-3:

Developer changelog
-------------------

| **Important:**
| 1. Red now offers cog disabling API, which should be respected by 3rd-party cogs in guild-related actions happening outside of command's context. See the `Additions changelog below <important-dev-340-1>` for more information.
| 2. Red now provides data request API, which should be supported by all 3rd-party cogs. See the changelog entries in the `Additions changelog below <important-dev-340-1>` for more information.

Breaking Changes
****************

- |cool| By default, none of the ``.send()`` methods mention roles or ``@everyone/@here`` (:issue:`3845`)

    - see `discord.AllowedMentions` and ``allowed_mentions`` kwarg of ``.send()`` methods, if your cog requires to mention roles or ``@everyone/@here``
- Method/attribute names starting with ``red_`` or being in the form of ``__red_*__`` are now reserved. See `version_guarantees` for more information (:issue:`4085`)
- Removed things past deprecation time: (:issue:`4163`)

    - ``redbot.core.commands.APIToken``
    - ``loop`` kwarg from `bounded_gather_iter()`, `bounded_gather()`, and `start_adding_reactions()`
- **Core** - Cog package names (i.e. name of the folder the cog is in and the name used when loading the cog) now have to be `valid Python identifiers <https://docs.python.org/3/reference/lexical_analysis.html#identifiers>`__ (:issue:`3605`, :issue:`3679`)
- **Core - Commands Package** - `Context.maybe_send_embed()` now supresses all mentions, including user mentions (:issue:`4192`)
- **Core - Commands Package** - The default value of the ``filter`` keyword argument in `Context.send()` has been changed to ``None`` (:issue:`3845`)
- **Core - Utils Package** - `humanize_list()` no longer raises `IndexError` for empty sequences (:issue:`2982`)

.. _important-dev-340-1:

Additions
*********

- |cool| **Core** - Added cog disabling API (:issue:`4043`, :issue:`3945`)

    - New methods added: `bot.cog_disabled_in_guild() <Red.cog_disabled_in_guild()>`, `bot.cog_disabled_in_guild_raw() <Red.cog_disabled_in_guild_raw()>`
    - Cog disabling is automatically applied for commands and only needs to be done manually for things like event listeners; see `recommendations-for-cog-creators` for more information
- |cool| **Core** - Added data request API (:issue:`4045`,  :issue:`4169`)

    - New special methods added to `redbot.core.commands.Cog`: `red_get_data_for_user()` (documented `provisionally <developer-guarantees-exclusions>`), `red_delete_data_for_user()`
    - New special module level variable added: ``__red_end_user_data_statement__``
    - These methods and variables should be added by all cogs according to their documentation; see `recommendations-for-cog-creators` for more information
    - New ``info.json`` key added: ``end_user_data_statement``; see `Info.json format documentation <info-json-format>` for more information
- **Core - Bot Class** - Added `bot.message_eligible_as_command() <Red.message_eligible_as_command()>` utility method which can be used to determine if a message may be responded to as a command (:issue:`4077`)
- |cool| **Core - Commands Package** - Added a `provisional API <developer-guarantees-exclusions>` for replacing the help formatter. See `documentation <framework-commands-help>` for more details (:issue:`4011`)
- **Core - Commands Package** - `commands.NoParseOptional <NoParseOptional>` is no longer `provisional <developer-guarantees-exclusions>` and is now fully supported part of API (:issue:`4142`)

Changes
*******

- **Core - Bot Class** - `bot.ignored_channel_or_guild() <Red.ignored_channel_or_guild()>` now accepts `discord.Message` objects (:issue:`4077`)
- |cool| **Core - Commands Package** - Autohelp in group commands is now sent *after* invoking the group, which allows before invoke hooks to prevent autohelp from getting triggered (:issue:`4129`)
- **Core - Utils Package** - `humanize_list()` now accepts ``locale`` and ``style`` keyword arguments. See its documentation for more information (:issue:`2982`)
- |cool| **Core - Utils Package** - `humanize_list()` is now properly localized (:issue:`2906`, :issue:`2982`)
- **Core - Utils Package** - `humanize_list()` now accepts empty sequences (:issue:`2982`)
- **Core - Utils Package** - ``bordered()`` now uses ``+`` for corners if keyword argument ``ascii_border`` is set to `True` (:issue:`4097`)
- **Vendored Packages** - Updated ``discord.ext.menus`` vendor (:issue:`4167`)

Fixes
*****

- **Core - Commands Package** - Red no longer fails to run subcommands of a command group allowed or denied by permission hook (:issue:`3956`)
- **Core - RPC** - RPC functionality no longer makes Red hang for a minute on shutdown (:issue:`4134`, :issue:`4143`)


Documentation changes
---------------------

Additions
*********

- |cool| Added admin user guide (:issue:`3081`)
- |cool| Added alias user guide (:issue:`3084`)
- |cool| Added bank user guide (:issue:`4149`)

Removals
********

- Removed install instructions for Debian Stretch (:issue:`4099`)

----

Redbot 3.3.12 (2020-08-18)
==========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`Dav-Git`, :ghuser:`douglas-cpp`, :ghuser:`flaree`, :ghuser:`jack1142`, :ghuser:`Kowlin`, :ghuser:`MeatyChunks`, :ghuser:`PredaaA`, :ghuser:`Predeactor`, :ghuser:`thisisjvgrace`, :ghuser:`Vexed01`, :ghuser:`zephyrkul`

End-user changelog
------------------

Security
********

- **Cogs - Streams** - Fixed critical vulnerability that could allow remote code execution (CVE-2020-15147), see `security advisory GHSA-7257-96vg-qf6x <https://github.com/Cog-Creators/Red-DiscordBot/security/advisories/GHSA-7257-96vg-qf6x>`__ for more information (:issue:`4183`)

Additions
*********

- **Cogs - Trivia - Lists** - Added ``whosthatpokemon2`` trivia containing Pokémons from 2nd generation (:issue:`4102`)
- **Cogs - Trivia - Lists** - Added ``whosthatpokemon3`` trivia containing Pokémons from 3rd generation (:issue:`4141`)

Changes
*******

- **Core - Command-line Interfaces** - Red now logs clearer error if it can't find package to load in any cog path during bot startup (:issue:`4079`)
- **Cogs - General** - Updated features list in ``[p]serverinfo`` with the latest changes from Discord (:issue:`4116`)
- **Cogs - General** - Simple version of ``[p]serverinfo`` now shows info about more detailed ``[p]serverinfo 1`` (:issue:`4121`)
- **Cogs - Mod** - ``[p]mute voice`` and ``[p]unmute voice`` now take action instantly if bot has Move Members permission (:issue:`4064`)
- **Cogs - Mod** - Added typing to ``[p](un)mute guild`` to indicate that mute is being processed (:issue:`4066`, :issue:`4172`)
- **Cogs - Streams** - Improve error messages for invalid channel names/IDs (:issue:`4147`, :issue:`4148`)

----

Redbot 3.3.11 (2020-08-10)
==========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`douglas-cpp`, :ghuser:`Drapersniper`, :ghuser:`Flame`, :ghuser:`jack1142`, :ghuser:`MeatyChunks`, :ghuser:`Vexed01`, :ghuser:`yamikaitou`

End-user changelog
------------------

Security
********

- **Cogs - Trivia** - Fixed critical vulnerability that could allow remote code execution (CVE-2020-15140), see `security advisory GHSA-7257-96vg-qf6x <https://github.com/Cog-Creators/Red-DiscordBot/security/advisories/GHSA-55j9-849x-26h4>`__ for more information (:issue:`4175`)

Fixes
*****

- **Cogs - Audio** - Audio should now work again on all voice regions (:issue:`4162`, :issue:`4168`)
- **Cogs - Audio** - Removed an edge case where an unfriendly error message was sent in Audio cog (:issue:`3879`)
- **Cogs - Cleanup** - Fixed a bug causing ``[p]cleanup`` commands to clear all messages within last 2 weeks when ``0`` is passed as the amount of messages to delete (:issue:`4114`, :issue:`4115`)
- **Cogs - CustomCommands** - ``[p]cc show`` now sends an error message when command with the provided name couldn't be found (:issue:`4108`)
- **Cogs - Downloader** - ``[p]findcog`` no longer fails for 3rd-party cogs without any author (:issue:`4032`, :issue:`4042`)
- **Cogs - Downloader** - Update commands no longer crash when a different repo is added under a repo name that was once used (:issue:`4086`)
- **Cogs - Permissions** - ``[p]permissions removeserverrule`` and ``[p]permissions removeglobalrule`` no longer error when trying to remove a rule that doesn't exist (:issue:`4028`, :issue:`4036`)
- **Cogs - Warnings** - ``[p]warn`` now sends an error message (instead of no feedback) when an unregistered reason is used by someone who doesn't have Administrator permission (:issue:`3839`, :issue:`3840`)

----

Redbot 3.3.10 (2020-07-09)
==========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`aikaterna`, :ghuser:`bobloy`, :ghuser:`Dav-Git`, :ghuser:`Drapersniper`, :ghuser:`Flame442`, :ghuser:`flaree`, :ghuser:`Injabie3`, :ghuser:`jack1142`, :ghuser:`mikeshardmind`, :ghuser:`MiniJennJenn`, :ghuser:`NeuroAssassin`, :ghuser:`thisisjvgrace`, :ghuser:`Vexed01`

End-user changelog
------------------

Additions
*********

- **Cogs - Downloader** - Added ``[p]cog listpinned`` subcommand to see currently pinned cogs (:issue:`3974`)
- **Cogs - Filter** - Added ``[p]filter list`` to show filtered words, and removed DMs when no subcommand was passed (:issue:`3973`)
- **Cogs - Trivia - Lists** - Added new ``lotr`` trivia list (:issue:`3980`)
- **Cogs - Trivia - Lists** - Added new ``r6seige`` trivia list (:issue:`4026`)

Changes
*******

- **Core - Bot Commands** - Added settings view commands for nearly all cogs. (:issue:`4041`)
- **Core - Bot Commands** - Added more strings to be fully translatable by i18n. (:issue:`4044`)
- **Core - Bot Commands** - Clarified that ``[p]embedset user`` only affects commands executed in DMs (:issue:`3972`, :issue:`3953`)
- **Core - Command-line Interfaces** - Red now prints a link to Getting Started guide if the bot isn't in any server (:issue:`3906`)
- **Core - Command-line Interfaces** - Added the option of using dots in the instance name when creating your instances (:issue:`3920`)
- **Core - Command-line Interfaces** - Added a confirmation when using hyphens in instance names to discourage the use of them (:issue:`3920`)
- **Core - Dependencies** - Bumped the Discord.py requirement from 1.3.3 to 1.3.4 (:issue:`4053`)
- **Cogs - Audio** - Added information about internally managed jar to ``[p]audioset info`` (:issue:`3915`)
- **Cogs - Downloader** - Added embed version of ``[p]findcog`` (:issue:`3965`, :issue:`3944`)
- **Cogs - Mod** - Added option to delete messages within the passed amount of days with ``[p]tempban`` (:issue:`3958`)
- **Cogs - Mod** - Reduced the number of API calls made to the storage APIs (:issue:`3910`)
- **Cogs - Mod** - Prevented an issue whereby the author may lock themself out of using the bot via whitelists (:issue:`3903`)
- **Cogs - Mod** - Improved error response in ``[p]modset banmentionspam`` (:issue:`3951`, :issue:`3949`)
- **Cogs - Modlog** - Improved error response in ``[p]modlogset modlog`` (:issue:`3951`, :issue:`3949`)
- **Cogs - Permissions** - Uploaded YAML files now accept integer commands without quotes (:issue:`3987`, :issue:`3185`)
- **Cogs - Permissions** - Uploaded YAML files now accept command rules with empty dictionaries (:issue:`3987`, :issue:`3961`)
- **Cogs - Trivia - Lists** - Updated ``greekmyth`` to include more answer variations (:issue:`3970`)

Fixes
*****

- **Core - Bot Commands** - Fixed delayed help when ``[p]set deletedelay`` is enabled (:issue:`3884`, :issue:`3883`)
- **Core - Bot Commands** - Fixed grammar errors and added full stops in various core commands (:issue:`4023`)
- **Cogs - Audio** - Twitch playback and YouTube searching should be functioning again. (:issue:`4055`)
- **Cogs - Downloader** - Fixed unnecessary typing when running downloader commands (:issue:`3964`, :issue:`3948`)
- **Cogs - Downloader** - Fixed ``[p]findcog`` not differentiating between core cogs and local cogs(:issue:`3969`, :issue:`3966`)
- **Cogs - Image** - Updated instructions for obtaining and setting the GIPHY API key (:issue:`3994`)
- **Cogs - Mod** - Added the ability to permanently ban a temporarily banned user with ``[p]hackban`` (:issue:`4025`)
- **Cogs - Mod** - Fixed the passed reason not being used when using ``[p]tempban`` (:issue:`3958`)
- **Cogs - Mod** - Fixed invite being sent with ``[p]tempban`` even when no invite was set (:issue:`3991`)
- **Cogs - Mod** - Fixed exceptions being ignored or not sent to log files in special cases (:issue:`3895`)
- **Cogs - Mod** - Fixed migration owner notifications being sent even when migration was not necessary (:issue:`3911`. :issue:`3909`)
- **Cogs - Streams** - Fixed Streams cog sending multiple owner notifications about twitch secret not set (:issue:`3901`, :issue:`3587`)
- **Cogs - Streams** - Fixed old bearer tokens not being invalidated when the API key is updated (:issue:`3990`, :issue:`3917`)
- **Cogs - Streams** - Fixed commands being translated where they should not be (:issue:`3938`, :issue:`3919`)
- **Cogs - Trivia - Lists** - Fixed URLs in ``whosthatpokemon`` (:issue:`3975`, :issue:`3023`)
- **Cogs - Trivia - Lists** - Fixed trivia files ``leagueults`` and ``sports`` (:issue:`4026`)


Developer changelog
-------------------

Additions
*********

- **Core - Utils Package** - Added the methods `map() <AsyncIter.map()>`, `find() <AsyncIter.find()>`, and `next() <AsyncIter.next()>` to `AsyncIter` (:issue:`3921`, :issue:`3887`)
- **Vendored Packages** - Vendored the ``discord.ext.menus`` module (:issue:`4039`)

Changes
*******

- **Core - Utils Package** - Added new ``discord.com`` domain to ``INVITE_URL_RE`` common filter (:issue:`4012`)

Deprecations
************

- **Core - Commands Package** - Updated deprecation times for ``APIToken``, and loops being passed to various functions to the first minor release (represented by ``X`` in ``3.X.0``) after 2020-08-05 (:issue:`3608`)
- **Cogs - Downloader** - Updated deprecation warnings for shared libs to reflect that they have been moved for an undefined time (:issue:`3608`)

Fixes
*****

- **Core - Utils Package** - Fixed incorrect role mention regex in `MessagePredicate` (:issue:`4030`)

----

Redbot 3.3.9 (2020-06-12)
=========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`aikaterna`, :ghuser:`Dav-Git`, :ghuser:`Drapersniper`, :ghuser:`Flame442`, :ghuser:`mikeshardmind`, :ghuser:`NeuroAssassin`, :ghuser:`Predeactor`, :ghuser:`Vexed01`

Read before updating
--------------------

#. Bot owners can no longer restrict access to some commands in Permissions cog using global permissions rules. Look at `Security changelog <important-339-2>` for full details.
#. There's been a change in behavior of warning messages. Look at `Additions changelog <important-339-1>` for full details.


End-user changelog
------------------

.. _important-339-2:

Security
********

- **Cogs - Mod** - ``[p]tempban`` now properly respects Discord's hierarchy rules (:issue:`3957`)

    **NOTE**: If you can't update immediately, we recommend disabling the affected command until you can.
- **Cogs - Permissions** - **Both global and server rules** can no longer prevent guild owners from accessing commands for changing server rules. Bot owners can still use ``[p]command disable`` if they wish to completely disable any command in Permissions cog (:issue:`3955`, :issue:`3107`)

  Full list of affected commands:

  - ``[p]permissions acl getserver``
  - ``[p]permissions acl setserver``
  - ``[p]permissions acl updateserver``
  - ``[p]permissions addserverrule``
  - ``[p]permissions removeserverrule``
  - ``[p]permissions setdefaultserverrule``
  - ``[p]permissions clearserverrules``
  - ``[p]permissions canrun``
  - ``[p]permissions explain``

.. _important-339-1:

Additions
*********

- **Cogs - Warnings** - Warnings sent to users don't show the moderator who warned the user by default now. Newly added ``[p]warningset showmoderators`` command can be used to switch this behaviour (:issue:`3781`)

Changes
*******

- **Core - Bot Commands** - ``[p]info`` command can now be used when bot doesn't have Embed Links permission (:issue:`3907`, :issue:`3102`)
- **Core - Bot Commands** - Improved instructions on obtaining user ID in help of ``[p]dm`` command (:issue:`3946`)
- **Core - Command-line Interfaces** - Red's start up message now shows storage type (:issue:`3935`)
- **Cogs - Alias** - ``[p]alias global`` group, ``[p]alias help``, and ``[p]alias show`` commands can now be used in DMs (:issue:`3941`, :issue:`3940`)
- **Cogs - Bank** - ``[p]bankset`` now displays bank's scope (:issue:`3954`)

Fixes
*****

- Added missing help message for Downloader, Reports and Streams cogs (:issue:`3892`)
- **Core - Bot Commands** - Fixed ungraceful error that happened in ``[p]set custominfo`` when provided text was too long (:issue:`3923`)
- **Core - Bot Commands** - Cooldown in ``[p]contact`` no longer applies when it's used without any arguments (:issue:`3942`)
- **Cogs - Audio** - Audio now properly ignores streams when max length is enabled (:issue:`3878`, :issue:`3877`)
- **Cogs - Audio** - Commands that should work in DMs no longer error (:issue:`3880`)
- **Cogs - Audio** - Fixed ``[p]audioset autoplay`` being available in DMs (:issue:`3899`)
- **Cogs - Audio** - Typo fix (:issue:`3889`, :issue:`3900`)
- **Cogs - Filter** - Fixed behavior of detecting quotes in commands for adding/removing filtered words (:issue:`3925`)
- **Cogs - Mod** - Preemptive fix for d.py 1.4 (:issue:`3891`)
- **Cogs - Warnings** - Warn channel functionality has been fixed (:issue:`3781`)


Developer changelog
-------------------

Additions
*********

- **Core - Bot Class** - Added `bot.set_prefixes() <Red.set_prefixes()>` method that allows developers to set global/server prefixes (:issue:`3890`)


Documentation changes
---------------------

Changes
*******

- Added Oracle Cloud to free hosting section in :ref:`host-list` (:issue:`3916`)

----

Redbot 3.3.8 (2020-05-29)
=========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`aikaterna`, :ghuser:`Bakersbakebread`, :ghuser:`DariusStClair`, :ghuser:`Dav-Git`, :ghuser:`Drapersniper`, :ghuser:`Flame442`, :ghuser:`jack1142`, :ghuser:`mikeshardmind`, :ghuser:`NeuroAssassin`, :ghuser:`PredaaA`, :ghuser:`Predeactor`, :ghuser:`qaisjp`, :ghuser:`Tobotimus`

End-user changelog
------------------

Additions
*********

- **Cogs - Audio** - Added new option (settable with ``[p]audioset lyrics``) that makes Audio cog prefer (prioritize) tracks with lyrics (:issue:`3519`)
- **Cogs - Audio** - Added global daily (historical) queues (:issue:`3518`)
- **Cogs - Audio** - Added ``[p]audioset countrycode`` that allows to set the country code for spotify searches (:issue:`3528`)

Changes
*******

- Few clarifications and typo fixes in few command help docstrings (:issue:`3817`, :issue:`3823`, :issue:`3837`, :issue:`3851`, :issue:`3861`)
- **Core** - Red now includes information on how to update when sending information about being out of date (:issue:`3744`)
- **Cogs - Alias** - ``[p]alias help`` should now work more reliably (:issue:`3864`)
- **Cogs - Audio** - ``[p]local play`` no longer enqueues tracks from nested folders (:issue:`3528`)
- **Cogs - Audio** - ``[p]disconnect`` now allows to disconnect if both DJ mode and voteskip aren't enabled (:issue:`3502`, :issue:`3485`)
- **Cogs - Audio** - Many UX improvements and fixes, including, among other things:

  - Creating playlists without explicitly passing ``-scope`` no longer causes errors (:issue:`3500`)
  - ``[p]playlist list`` now shows all accessible playlists if ``--scope`` flag isn't used (:issue:`3518`)
  - ``[p]remove`` now also accepts a track URL in addition to queue index (:issue:`3201`)
  - ``[p]playlist upload`` now accepts a playlist file uploaded in the message with a command (:issue:`3251`)
  - Commands now send friendly error messages for common errors like lost Lavalink connection or bot not connected to voice channel (:issue:`3503`, :issue:`3528`, :issue:`3353`, :issue:`3712`)
- **Cogs - Mod** - ``[p]userinfo`` now shows default avatar when no avatar is set (:issue:`3819`)

Fixes
*****

- **Core** - Made important fixes to how PostgreSQL data backend saves data in bulks (:issue:`3829`)
- **Core** - Using backslashes in bot's username/nickname no longer causes issues (:issue:`3826`, :issue:`3825`)
- **Core - Bot Commands** - Fixed ``[p]localwhitelist`` and ``[p]localblacklist`` commands (:issue:`3857`)
- **Cogs - Admin** - Fixed server lock (:issue:`3815`, :issue:`3814`)
- **Cogs - Alias** - Added pagination to ``[p]alias list`` and ``[p]alias global list`` to avoid errors for users with a lot of aliases (:issue:`3844`, :issue:`3834`)
- **Cogs - Audio** - Twitch playback is functional once again (:issue:`3873`)
- **Cogs - Audio** - Recent errors with YouTube playback should be resolved (:issue:`3873`)
- **Cogs - Audio** - Fixed ``[p]local search`` (:issue:`3528`, :issue:`3501`)
- **Cogs - Audio** - Local folders with special characters should work properly now (:issue:`3528`, :issue:`3467`)
- **Cogs - Audio** - Audio no longer fails to take the last spot in the voice channel with user limit (:issue:`3528`)
- **Cogs - Audio** - Fixed ``[p]playlist dedupe`` not removing tracks (:issue:`3518`)
- **Cogs - CustomCommands** - ``[p]customcom create`` no longer allows spaces in custom command names (:issue:`3816`)
- **Cogs - Modlog** - Fixed (again) ``AttributeError`` for cases whose moderator doesn't share the server with the bot (:issue:`3805`, :issue:`3784`, :issue:`3778`)
- **Cogs - Permissions** - Commands for settings ACL using yaml files now properly works on PostgreSQL data backend (:issue:`3829`, :issue:`3796`)
- **Cogs - Warnings** - Warnings cog no longer allows to warn bot users (:issue:`3855`, :issue:`3854`)


Developer changelog
-------------------

| **Important:**
| If you're using RPC, please see the full annoucement about current state of RPC in main Red server
  `by clicking here <https://discord.com/channels/133049272517001216/411381123101491200/714560168465137694>`__.

Changes
*******

- **Core - Bot Class** - Red now inherits from `discord.ext.commands.AutoShardedBot` for better compatibility with code expecting d.py bot (:issue:`3822`)
- **Core - Bot Class** - All bot owner IDs can now be found under ``bot.owner_ids`` attribute (:issue:`3793`)

  -  Note: If you want to use this on bot startup (e.g. in cog's initialisation), you need to await ``bot.wait_until_red_ready()`` first

Fixes
*****

- Libraries using ``pkg_resources`` (like ``humanize`` or ``google-api-python-client``) that were installed through Downloader should now work properly (:issue:`3843`)
- **Cogs - Downloader** - Downloader no longer removes the repo when it fails to load it (:issue:`3867`)


Documentation changes
---------------------

Changes
*******

- Added information about `provisional <developer-guarantees-exclusions>` status of RPC (:issue:`3862`)
- Revised install instructions (:issue:`3847`)
- Improved navigation in `document about updating Red <update_red>` (:issue:`3856`, :issue:`3849`)

----

Redbot 3.3.7 (2020-04-28)
=========================

This is a hotfix release fixing issue with generating messages for new cases in Modlog.

----

Redbot 3.3.6 (2020-04-27)
=========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`aikaterna`, :ghuser:`Drapersniper`, :ghuser:`jack1142`, :ghuser:`Kowlin`, :ghuser:`MiniJennJenn`, :ghuser:`NeuroAssassin`, :ghuser:`PredaaA`, :ghuser:`TrustyJAID`, :ghuser:`yamikaitou`

End-user changelog
------------------

Additions
*********

- **Core - Bot Commands** - Added ``[p]set avatar remove`` subcommand for removing bot's avatar (:issue:`3757`)
- **Cogs - CustomCommands** - Added ``[p]cc raw`` command that gives you the raw response of a custom command for ease of copy pasting (:issue:`3795`)

Changes
*******

- **Core** - Various optimizations

  - Reduced calls to data backend when loading bot's commands (:issue:`3764`)
  - Reduced calls to data backend when showing help for cogs/commands (:issue:`3766`)
  - Improved performance for bots with big amount of guilds (:issue:`3767`)
  - Mod cog no longer fetches guild's bans every 60 seconds when handling unbanning for tempbans (:issue:`3783`)
  - Reduced the bot load for messages starting with a prefix when fuzzy search is disabled (:issue:`3718`)
  - Aliases in Alias cog are now cached for better performance (:issue:`3788`)
- **Core - Bot Commands** - ``[p]set avatar`` now supports setting avatar using attachment (:issue:`3747`)
- **Core - Bot Commands** - ``[p]debuginfo`` now shows used storage type (:issue:`3794`)
- **Cogs - Trivia - Lists** - Updated ``leagueoflegends`` list with new changes to League of Legends (`b8ac70e <https://github.com/Cog-Creators/Red-DiscordBot/commit/b8ac70e59aa1328f246784f14f992d6ffe00d778>`__)

Fixes
*****

- **Core** - Fixed big delays in commands that happened when the bot was owner-less (or if it only used co-owners feature) and command caller wasn't the owner (:issue:`3782`)
- **Core - Bot Commands** - Fixed list of ignored channels that is shown in ``[p]ignore``/``[p]unignore`` (:issue:`3746`)
- **Core - Command-line Interfaces** - Converting from and to Postgres driver with ``redbot-setup convert`` have been fixed (:issue:`3714`, :issue:`3115`)
- **Cogs - Audio** - Age-restricted tracks, live streams, and mix playlists from YouTube should work in Audio again (:issue:`3791`)
- **Cogs - Audio** - SoundCloud sets and playlists with more than 50 tracks should work in Audio again (:issue:`3791`)
- **Cogs - Modlog** - Fixed ``AttributeError`` for cases whose moderator doesn't share the server with the bot (:issue:`3784`, :issue:`3778`)
- **Cogs - Streams** - Fixed incorrect stream URLs for Twitch channels that have localised display name (:issue:`3773`, :issue:`3772`)
- **Cogs - Trivia** - Fixed the error in ``[p]trivia stop`` that happened when there was no ongoing trivia session in the channel (:issue:`3774`)
- **Cogs - Trivia - Lists** - Corrected spelling of Compact Disc in ``games`` list (:issue:`3759`, :issue:`3758`)


Developer changelog
-------------------

Additions
*********

- **Core - Utils Package** - Added `redbot.core.utils.AsyncIter` utility class which allows you to wrap regular iterable into async iterator yielding items and sleeping for ``delay`` seconds every ``steps`` items (:issue:`3767`, :issue:`3776`)

Changes
*******

- **Core - Utils Package** - `bold()`, `italics()`, `strikethrough()`, and `underline()` now accept ``escape_formatting`` argument that can be used to disable escaping of markdown formatting in passed text (:issue:`3742`)

Fixes
*****

- **Core - Config** - JSON driver will now properly have only one lock per cog name (:issue:`3780`)


Documentation changes
---------------------

Additions
*********

- Added `document about updating Red <update_red>` (:issue:`3790`)
- Updated install docs to include Ubuntu 20.04 (:issue:`3792`)

Changes
*******

- ``pyenv`` instructions will now update ``pyenv`` if it's already installed (:issue:`3740`)
- Updated Python version in ``pyenv`` instructions (:issue:`3740`)

----

Redbot 3.3.5 (2020-04-09)
=========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`jack1142`, :ghuser:`Kowlin`

End-user changelog
------------------

Changes
*******

- **Core - Bot Commands** - "Outdated" field no longer shows in ``[p]info`` when Red is up-to-date (:issue:`3730`)

Fixes
*****

- **Cogs - Alias** - Fixed regression in ``[p]alias add`` that caused it to reject commands containing arguments (:issue:`3734`)

----

Redbot 3.3.4 (2020-04-05)
=========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`jack1142`, :ghuser:`kennnyshiwa`

End-user changelog
------------------

Changes
*******

- **Cogs - Alias** - ``[p]alias add`` now sends an error when command user tries to alias doesn't exist (:issue:`3710`, :issue:`3545`)

Fixes
*****

- **Core - Bot Commands** - Fixed checks related to bank's global state that were used in commands in Bank, Economy and Trivia cogs (:issue:`3707`)


Developer changelog
-------------------

Changes
*******

- **Core - Dependencies** - Bump dependencies, including update to discord.py 1.3.3 (:issue:`3723`)
- **Core - Utils Package** - `redbot.core.utils.common_filters.filter_invites` now filters ``discord.io/discord.li`` invites links (:issue:`3717`)

Fixes
*****

- **Core - Utils Package** - Fixed false-positives in `redbot.core.utils.common_filters.filter_invites` (:issue:`3717`)


Documentation changes
---------------------

Changes
*******

- Versions of pre-requirements are now included in Windows install guide (:issue:`3708`)

----

Redbot 3.3.3 (2020-03-28)
=========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`AnonGuy`, :ghuser:`Dav-Git`, :ghuser:`FancyJesse`, :ghuser:`Ianardo-DiCaprio`, :ghuser:`jack1142`, :ghuser:`kennnyshiwa`, :ghuser:`Kowlin`, :ghuser:`NeuroAssassin`, :ghuser:`PredaaA`, :ghuser:`Stonedestroyer`, :ghuser:`TrustyJAID`

End-user changelog
------------------

Security
********

- **Cogs - Cleanup** - Removed regex support in ``[p]cleanup self`` (:issue:`3704`)

Additions
*********

- **Core - i18n** - Added ``[p]set regionalformat`` command that allows users to set regional formatting that is different from bot's locale (:issue:`3677`, :issue:`3588`)
- **Cogs - Cleanup** - Added ``[p]cleanup spam`` command that deletes duplicate messages from the last X messages and keeps only one copy (:issue:`3688`)
- **Cogs - CustomCommands** - Added ``[p]cc search`` command that allows users to search through created custom commands (:issue:`2573`)
- **Cogs - Trivia** - Added ``[p]triviaset custom upload/delete/list`` commands for managing custom trivia lists from Discord (:issue:`3420`, :issue:`3307`)
- **Cogs - Warnings** - Sending warnings to warned user can now be disabled with ``[p]warnset toggledm`` command (:issue:`2929`, :issue:`2800`)
- **Cogs - Warnings** - Added ``[p]warnset warnchannel`` command that allows to set a channel where warnings should be sent to instead of the channel command was called in (:issue:`2929`, :issue:`2800`)
- **Cogs - Warnings** - Added ``[p]warnset togglechannel`` command that allows to disable sending warn message in guild channel (:issue:`2929`, :issue:`2800`)

Changes
*******

- **Core** - Delete delay for command messages has been moved from Mod cog to Core (:issue:`3638`, :issue:`3636`)
- **Core** - Command errors (i.e. command on cooldown, dm-only and guild-only commands, etc) can now be translated (:issue:`3665`, :issue:`2988`)
- **Core - Bot Commands** - ``[p]set locale`` allows any valid locale now, not just locales for which Red has translations (:issue:`3676`, :issue:`3596`)
- **Core - Bot Commands** - Permissions for commands in Bank, Economy and Trivia cogs can now be overridden by Permissions cog (:issue:`3672`, :issue:`3233`)
- **Core - Bot Commands** - Added ``[p]set playing`` and ``[p]set streaming`` aliases for respectively ``[p]set game`` and ``[p]set stream`` (:issue:`3646`, :issue:`3590`)
- **Core - Command-line Interfaces** - ``redbot-setup`` now prints link to Getting started guide at the end of the setup (:issue:`3027`)
- **Cogs - Downloader** - ``[p]cog checkforupdates`` now includes information about cogs that can't be installed due to Red/Python version requirements (:issue:`3678`, :issue:`3448`)
- **Cogs - Downloader** - Improved error messages for unexpected errors in ``[p]repo add`` (:issue:`3656`)
- **Cogs - General** - Added more detailed mode to ``[p]serverinfo`` command that can be accessed with ``[p]serverinfo 1`` (:issue:`2382`, :issue:`3659`)
- **Cogs - Image** - Users can now specify how many images should be returned in ``[p]imgur search`` and ``[p]imgur subreddit`` using ``[count]`` argument (:issue:`3667`, :issue:`3044`)
- **Cogs - Image** - ``[p]imgur search`` and ``[p]imgur subreddit`` now return one image by default (:issue:`3667`, :issue:`3044`)
- **Cogs - Mod** - ``[p]userinfo`` now shows user's activities (:issue:`3669`)
- **Cogs - Mod** - ``[p]userinfo`` now shows status icon near the username (:issue:`3669`)
- **Cogs - Modlog** - Modlog's cases now keep last known username to prevent losing that information from case's message on edit (:issue:`3674`, :issue:`3443`)
- **Cogs - Permissions** - Commands for setting default rules now error when user tries to deny access to command designated as being always available (:issue:`3504`, :issue:`3465`)
- **Cogs - Streams** - Preview picture for YouTube stream alerts is now bigger (:issue:`3689`, :issue:`3685`)
- **Cogs - Streams** - Failures in Twitch API authentication are now logged (:issue:`3657`)
- **Cogs - Warnings** - ``[p]warn`` now tells the moderator when bot wasn't able to send the warning to the user (:issue:`3653`, :issue:`3633`)

Fixes
*****

- All owner notifications in core cogs now use proper prefixes in messages (:issue:`3632`)
- **Core** - Fixed various bugs with blacklist and whitelist (:issue:`3643`, :issue:`3642`)
- **Core** - Outages of ``pypi.org`` no longer prevent the bot from starting (:issue:`3663`)
- **Core** - Fixed formatting of help strings in fuzzy search results (:issue:`3673`, :issue:`3507`)
- **Core** - Fixed few deprecation warnings related to menus and uvloop (:issue:`3644`, :issue:`3700`)
- **Core - Bot Commands** - ``[p]set game`` no longer errors when trying to clear the status (:issue:`3630`, :issue:`3628`)
- **Core - Bot Commands** - Whitelist and blacklist commands now properly require passing at least one user (or role in case of local whitelist/blacklist) (:issue:`3652`, :issue:`3645`)
- **Cogs - Downloader** - Fix misleading error appearing when repo name is already taken in ``[p]repo add`` (:issue:`3695`)
- **Cogs - Downloader** - Prevent encoding errors from crashing ``[p]cog update`` (:issue:`3639`, :issue:`3637`)
- **Cogs - Mod** - Muting no longer fails if user leaves while applying overwrite (:issue:`3627`)
- **Cogs - Mod** - Fixed error that happened when Mod cog was loaded for the first time during bot startup (:issue:`3632`, :issue:`3626`)
- **Cogs - Streams** - Fixed an error that happened when no game was set on Twitch stream (:issue:`3631`)
- **Cogs - Streams** - YouTube channels with a livestream that doesn't have any current viewer are now properly showing as streaming (:issue:`3690`)
- **Cogs - Trivia** - Trivia sessions no longer error on payout when winner's balance would exceed max balance (:issue:`3666`, :issue:`3584`)
- **Cogs - Trivia** - Non-finite numbers can no longer be passed to ``[p]triviaset timelimit``, ``[p]triviaset stopafter`` and ``[p]triviaset payout`` (:issue:`3668`, :issue:`3583`)


Developer changelog
-------------------

Fixes
*****

- Deprecation warnings issued by Red now use correct stack level so that the cog developers can find the cause of them (:issue:`3644`)
- **Core - Utils Package** - `redbot.core.utils.menus.menu()` now checks permissions *before* trying to clear reactions (:issue:`3589`, :issue:`3145`)
- **Cogs - Dev** - Added ``__name__`` to environment's globals (:issue:`3649`, :issue:`3648`)


Documentation changes
---------------------

Changes
*******

- Windows install instructions now use ``choco upgrade`` commands instead of ``choco install`` to ensure up-to-date packages (:issue:`3684`)

Fixes
*****

- Fixed install instructions for Mac (:issue:`3675`, :issue:`3436`)

----

Redbot 3.3.2 (2020-02-28)
=========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`aikaterna`, :ghuser:`chasehult`, :ghuser:`Dav-Git`, :ghuser:`DiscordLiz`, :ghuser:`Drapersniper`, :ghuser:`fixator10`, :ghuser:`Flame442`, :ghuser:`Hedlund01`, :ghuser:`jack1142`, :ghuser:`Kowlin`, :ghuser:`mikeshardmind`, :ghuser:`PredaaA`, :ghuser:`Stonedestroyer`, :ghuser:`trundler-dev`, :ghuser:`TrustyJAID`, :ghuser:`zephyrkul`

End-user changelog
------------------

Additions
*********

- **Cogs - Streams** - Added ``[p]streamset timer`` command which can be used to control how often the cog checks for live streams (:issue:`3237`)

Changes
*******

- **Core** - Ignored guilds/channels and whitelist/blacklist are now cached for performance (:issue:`3472`)
- **Core** - Ignored guilds/channels have been moved from Mod cog to Core (:issue:`3472`)
- **Core - Bot Commands** - ``[p]ignore channel`` command can now also ignore channel categories (:issue:`3472`)
- **Core - Bot Commands** - Improved user experience of ``[p]set game/listening/watching/`` commands (:issue:`3562`)
- **Core - Bot Commands** - Added ``[p]licenceinfo`` alias for ``[p]licenseinfo`` command to conform with non-American English (:issue:`3460`)
- **Cogs - Downloader** - Added better logging of errors when Downloader fails to add a repo (:issue:`3558`)
- **Cogs - Mod** - ``[p]hackban`` and ``[p]unban`` commands support user mentions now (:issue:`3524`)
- **Cogs - Streams** - Significantly reduce the quota usage for YouTube stream alerts (:issue:`3237`)
- **Cogs - Warnings** - Users can now pass a reason to ``[p]unwarn`` command (:issue:`3490`, :issue:`3093`)
- **Cogs - Warnings** - Use more reliant way of checking if command is bot owner only in ``[p]warnaction`` (Warnings cog) (:issue:`3516`, :issue:`3515`)

Fixes
*****

- Core cogs will now send bot mention prefix properly in places where discord doesn't render mentions (:issue:`3579`, :issue:`3591`, :issue:`3499`)
- **Core** - Stop using deprecated code in Core (:issue:`3610`)
- **Core - Bot Commands** - Fixed a bug with ``[p]blacklist add`` that made it impossible to blacklist users that bot doesn't share a server with (:issue:`3472`, :issue:`3220`)
- **Core - Bot Commands** - Update PyPI domain in ``[p]info`` and update checker (:issue:`3607`)
- **Cogs - Admin** - ``[p]announce`` will now only send error message if an actual errors occurs (:issue:`3514`, :issue:`3513`)
- **Cogs - Alias** - ``[p]alias help`` will now properly work in non-English locales (:issue:`3546`)
- **Cogs - Audio** - Users should be able to play age-restricted tracks from YouTube again (:issue:`3620`)
- **Cogs - Downloader** - Downloader will no longer fail because of invalid ``info.json`` files (:issue:`3533`, :issue:`3456`)
- **Cogs - Economy** - Next payday time will now be adjusted for users when payday time is changed (:issue:`3496`, :issue:`3438`)
- **Cogs - Image** - Fixed load error for users that updated Red from version lower than 3.1 to version 3.2 or newer (:issue:`3617`)
- **Cogs - Streams** - Fixed stream alerts for Twitch (:issue:`3487`)
- **Cogs - Trivia** - Added better handling for errors in trivia session (:issue:`3606`)
- **Cogs - Trivia - Lists** - Removed empty answers in trivia lists (:issue:`3581`)


Developer changelog
-------------------

Security
********

- **Core - Commands Package** - Subcommands of command group with ``invoke_without_command=True`` will again inherit this group's checks (:issue:`3614`)

Additions
*********

- **Cogs - Dev** - Allow for top-level `await`, `async for` and `async with` in ``[p]debug`` and ``[p]repl`` commands (:issue:`3508`)

Changes
*******

- **Core - Command-line Interfaces** - Added traceback logging to task exception handling (:issue:`3517`)
- **Core - Command-line Interfaces** - Bot will now show deprecation warnings in logs (:issue:`3527`, :issue:`3615`)
- **Core - Commands Package** - Developers can now create a command from an async function wrapped in `functools.partial` (:issue:`3542`)
- **Core - Dependencies** - Updated all our dependencies - we're using discord.py 1.3.2 now (:issue:`3609`)
- **Core - Utils Package** - Added clearer error when page is of a wrong type in `redbot.core.utils.menus.menu()` (:issue:`3571`)
- **Cogs - Downloader** - Downloader will now replace ``[p]`` with clean prefix same as it does in help command (:issue:`3592`)
- **Cogs - Downloader** - Added schema validation to ``info.json`` file processing - it should now be easier to notice any issues with those files (:issue:`3533`, :issue:`3442`)

Fixes
*****

- **Core - Config** - Fixed Config's singletons (:issue:`3137`, :issue:`3136`)


Documentation changes
---------------------

Additions
*********

- Added guidelines for Cog Creators in `guide_cog_creation` document (:issue:`3568`)

Changes
*******

- Restructured virtual environment instructions to improve user experience (:issue:`3495`, :issue:`3411`, :issue:`3412`)
- Getting started guide now explains use of quotes for arguments with spaces (:issue:`3555`, :issue:`3111`)
- ``latest`` version of docs now displays a warning about possible differences from current stable release (:issue:`3570`)
- Made systemd guide clearer on obtaining username and python path (:issue:`3537`, :issue:`3462`)
- Improved indication of instructions for different venv types in systemd guide (:issue:`3538`)
- Service file in `autostart_systemd` now also waits for network connection to be ready (:issue:`3549`)
- Hid alias of ``randomize_colour`` in docs (:issue:`3491`)
- Added separate headers for each event predicate class for better navigation (:issue:`3595`, :issue:`3164`)
- Improved wording of explanation for ``required_cogs`` key in `guide_publish_cogs` (:issue:`3520`)

----

Redbot 3.3.1 (2020-02-05)
=========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`aikaterna`, :ghuser:`Flame442`, :ghuser:`flyingmongoose`, :ghuser:`jack1142`, :ghuser:`Kowlin`, :ghuser:`mikeshardmind`, :ghuser:`palmtree5`, :ghuser:`PredaaA`

End-user changelog
------------------

Additions
*********

- **Core - Command-line Interfaces** - Added a cli flag (``--message-cache-size``) for setting a max size of message cache (:issue:`3473`, :issue:`3474`)

Changes
*******

- Some functions have been changed to no longer use deprecated asyncio functions (:issue:`3509`)
- **Core - Command-line Interfaces** - Prefix can now be edited from command line using ``redbot --edit`` (:issue:`3481`, :issue:`3486`)
- **Cogs - Mod** - The short help text for ``[p]modset dm`` has been made more useful (:issue:`3488`)

Fixes
*****

- **Core - Bot Commands** - ``[p]dm`` no longer allows owners to have the bot attempt to DM itself (:issue:`3477`, :issue:`3478`)
- **Cogs - Mod** - Hackban now works properly without being provided a number of days (:issue:`3476`, :issue:`3475`)


Developer changelog
-------------------

Deprecations
************

- **Core - Utils Package** - Passing the event loop explicitly in `bounded_gather()`, `bounded_gather_iter()`, and `start_adding_reactions()` is deprecated and will be removed in 3.4 (:issue:`3509`)


Documentation changes
---------------------

Additions
*********

- Added section to install docs for CentOS 8 (:issue:`3461`, :issue:`3463`)

Changes
*******

- Added ``-e`` flag to ``journalctl`` command in systemd guide so that it takes the user to the end of logs automatically (:issue:`3483`)
- Improved usage of apt update in docs (:issue:`3464`)

----

Redbot 3.3.0 (2020-01-26)
=========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`DevilXD`, :ghuser:`Drapersniper`, :ghuser:`Flame442`, :ghuser:`Ianardo-DiCaprio`, :ghuser:`jack1142`, :ghuser:`Kowlin`, :ghuser:`mikeshardmind`, :ghuser:`Stonedestroyer`, :ghuser:`zephyrkul`

End-user changelog
------------------

Additions
*********

- **Core** - Team applications are now supported (:issue:`2781`, :issue:`3445`)

    - Added new ``--team-members-are-owners`` flag that will make Red treat owners of the team application as bot owners
- **Core - Bot Commands** - Embed use can now be configured per channel with new ``[p]embedset channel`` command (:issue:`3152`, :issue:`3418`)
- **Cogs - Mod** - You can set a default amount of days to clean up when banning with ``[p]ban`` and ``[p]tempban`` (:issue:`2441`, :issue:`2930`, :issue:`3437`)
- **Cogs - Mod** - Users can now optionally be DMed their ban reason (:issue:`2649`, :issue:2990`)

Changes
*******

- **Core - Help** - Help is now self consistent in the extra formatting used (:issue:`3451`)
- **Cogs - Admin** - Role granting/removing commands will now notify when the user already has/doesn't have a role when attempting to add/remove it (:issue:`3010`, :issue:`3408`)
- **Cogs - Audio** - Playlist searching is now more intuitive (:issue:`3430`)
- **Cogs - Downloader** - Some user facing messages were improved (:issue:`3409`)
- **Cogs - Mod** - ``[p]slowmode`` should no longer error on nonsensical time quantities (:issue:`3453`)

Fixes
*****

- **Cogs - Audio** - ``[p]audioset dc`` and ``[p]repeat`` commands no longer interfere with each other (:issue:`3425`, :issue:`3426`)
- **Cogs - Cleanup** - Fixed a rare edge case involving messages that were deleted during cleanup (:issue:`3414`)
- **Cogs - CustomCommands** - ``[p]cc create random`` no longer errors when exiting an interactive menu (:issue:`3416`, :issue:`3417`)
- **Cogs - Downloader** - Downloader's initialization can no longer time out at startup (:issue:`3415`, :issue:`3440`, :issue:`3444`)
- **Cogs - General** - ``[p]roll`` command will no longer attempt to roll obscenely large amounts (:issue:`3284`, :issue:`3395`)
- **Cogs - Permissions** - Now has stronger enforcement of prioritizing botwide settings


Developer changelog
-------------------

Breaking Changes
****************

- **Core - Commands Package** - Importing submodules of ``discord.ext.commands`` from ``redbot.core.commands`` will no longer work (:issue:`3410`)
- **Core - Commands Package** - ``PermState.ALLOWED_STATES`` from ``redbot.core.commands.requires`` has been moved to a global variable called ``PermStateAllowedStates`` in the same module (:issue:`3410`)
- **Core - Commands Package** - ``PermState.TRANSITIONS`` from ``redbot.core.commands.requires`` has been moved to a global variable called ``PermStateAllowedStates`` in the same module (:issue:`3410`)
- **Core - Commands Package** - Use of ``@asyncio.coroutine`` is no longer supported. Use ``async def`` instead (:issue:`3410`)

Changes
*******

- **Core - Commands Package** - The commands module has been slightly restructured to provide more useful data to developers (:issue:`3410`)
- **Core - Dependencies** - We now use discord.py 1.3.1 (:issue:`3445`)

Deprecations
************

- **Cogs - Downloader** - Updated deprecation warnings for shared libs to reflect that they will instead be removed in 3.4 (:issue:`3449`)

Fixes
*****

- **Core - Commands Package** - Fixed an issue with default units in `TimedeltaConverter` (:issue:`3453`)


Documentation changes
---------------------

Fixes
*****

- We've made some small fixes to inaccurate instructions about installing with pyenv (:issue:`3434`)

----

Redbot 3.2.3 (2020-01-17)
=========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`Dav-Git`, :ghuser:`Drapersniper`, :ghuser:`Flame442`, :ghuser:`flaree`, :ghuser:`jack1142`, :ghuser:`Kowlin`, :ghuser:`mikeshardmind`, :ghuser:`Redjumpman`, :ghuser:`Stonedestroyer`, :ghuser:`TrustyJAID`

End-user changelog
------------------

Additions
*********

- **Core** - The bot's description is now configurable through ``[p]set description`` (:issue:`3340`)

Changes
*******

- **Core** - Further improvements have been made to bot startup and shutdown (:issue:`3358`, :issue:`3392`)
- **Core** - Prefixes are now cached for performance (:issue:`3148`, :issue:`3150`)
- **Core** - The bot now ensures it has at least the bare neccessary permissions before running commands (:issue:`3304`, :issue:`3305`, :issue:`3361`)
- **Core - Bot Commands** - The ``[p]servers`` command now also shows the ids (:issue:`3224`, :issue:`3393`)
- **Cogs - Audio** - Reduced cooldowns for some of the playlist commands (:issue:`3342`)
- **Cogs - Downloader** - Improved a few user facing messages (:issue:`3343`)
- **Cogs - Downloader** - Added logging of failures (:issue:`3372`)

Fixes
*****

- **Core** - Embed settings (``[p]embedset``) for ``[p]help`` now work the same as for other commands (:issue:`3382`)
- **Core - Command-line Interfaces** - Deleting instances works as intended again (:issue:`3338`, :issue:`3384`)
- **Cogs - Admin** - The selfrole command now has reasonable expectations about hierarchy  (:issue:`3331`)
- **Cogs - Audio** - Audio now properly disconnects the bot when ``[p]audioset dc`` is turned on, even if ``[p]audioset notify`` is being used (:issue:`3349`, :issue:`3350`)
- **Cogs - Audio** - Symbolic links now work as intended for local tracks (:issue:`3332`, :issue:`3376`)
- **Cogs - Audio** - ``[p]bumpplay`` now shows the correct remaining time until the bumped track is played (:issue:`3373`, :issue:`3375`)
- **Cogs - Audio** - Multiple user facing messages have been made more correct (:issue:`3347`, :issue:`3348`, :issue:`3374`)
- **Cogs - Downloader** - Added pagination of output on cog update when it's too long for single message (:issue:`3385`, :issue:`3388`)


Developer changelog
-------------------

Additions
*********

- **Core** - Added the means for cog creators to use a global preinvoke hook (:issue:`3369`)
- **Core - Commands Package** - New features added for cog creators to further customize help behavior (:issue:`3339`)
  
  - Check out our command reference for details on new ``format_help_for_context`` method
- **Core - Commands Package** - ``[botname]`` is now replaced with the bot's display name in help text (:issue:`3339`)


Documentation changes
---------------------

Additions
*********

- Added proper support for Ubuntu non-LTS (:issue:`3330`, :issue:`3336`)
- Added link to our GitHub in the documentation (:issue:`3306`)

Changes
*******

- Added a note about how to update Red to the install guides (:issue:`3400`)
- Clarified some information about breaking changes in Red 3.2.0 changelog (:issue:`3367`)
- Improved the structure of the Linux/Mac install guide to make it more clear to the user which sections they should be following (:issue:`3365`)
- Added more details to the API key reference (:issue:`3400`)
- Updated the documentation to **require** the usage of virtual environment for installing and running Red (:issue:`3351`)
- Updated auto-restart guides to use Python's ``-O`` flag to enable assert optimizations (:issue:`3354`)

Fixes
*****

- Updated the documentation with the minimum supported git version (:issue:`3371`)
- Fixed install instructions for Debian to also work with Debian Stretch (:issue:`3352`)

----

Redbot 3.2.2 (2020-01-10)
=========================

End-user changelog
------------------

Fixes
*****

- **Core - Bot Commands** - Fixed pagination issue in ``[p]help`` command (:issue:`3323`, :issue:`3324`)


Documentation changes
---------------------

Fixes
*****

- Corrected venv docs to use the actually supported Python version (:issue:`3325`, :issue:`3324`)

----

Redbot 3.2.1 (2020-01-10)
=========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`mikeshardmind`, :ghuser:`palmtree5`

End-user changelog
------------------

Changes
*******

- **Cogs - Modlog** - Modlog will now log an error with unexpected case type key (and any other keys) rather than crash (:issue:`3318`)

Fixes
*****

- **Core - Command-line Interfaces** - Fixed Mongo conversion from being incorrectly blocked (:issue:`3316`, :issue:`3319`)
- **Cogs - Admin** - Fixed announcer not creating a message for success feedback (:issue:`3320`)

----

Redbot 3.2.0 (2020-01-09)
=========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`aikaterna`, :ghuser:`Aurorum`, :ghuser:`Bakersbakebread`, :ghuser:`DevilXD`, :ghuser:`DiscordLiz`, :ghuser:`DJtheRedstoner`, :ghuser:`Drapersniper`, :ghuser:`Flame442`, :ghuser:`flaree`, :ghuser:`Ianardo-DiCaprio`, :ghuser:`jack1142`, :ghuser:`jerbob`, :ghuser:`jonasbohmann`, :ghuser:`kennnyshiwa`, :ghuser:`Kowlin`, :ghuser:`mikeshardmind`, :ghuser:`palmtree5`, :ghuser:`PredaaA`, :ghuser:`RealFriesi`, :ghuser:`retke`, :ghuser:`Tobotimus`, :ghuser:`Vexed01`, :ghuser:`wereii`, :ghuser:`yamikaitou`, :ghuser:`ZeLarpMaster`, :ghuser:`zephyrkul`

Read before updating
--------------------

#. Red 3.2 dropped support for the MongoDB driver. When updating your instance from an older version, be sure to use instructions for **your current version** from the `document about updating Red <update_red>` to be able to still start your instance after the update.
#. Red 3.2 requires Python 3.8.1 or newer. In order to be able to update, you'll first have to install appropriate versions of your dependencies so be sure to use instructions for **your current version** from the `document about updating Red <update_red>`.

   .. note::

      You may get a notification from the downloader cog about needing to refetch dependencies.
      This is expected and it will walk you through everything and do as much as it can for you.

#. Red 3.2 comes with improvements which required breaking changes for 3rd party cogs. When you update to 3.2, your cogs may not be compatible if the author has not handled
   the changes yet. If you're a cog creator, you can look at `Developer changelog <important-320-1>` for full details.


End-user changelog
------------------

Breaking Changes
****************

- **Core** - Removed the mongo driver (:issue:`3099`, :issue:`3108`)
- **Core - Dependencies** - Updated the required minimum Python version to 3.8.1, and the required minimum JRE version to Java 11 (:issue:`3245`)

Additions
*********

- **Core** - Added a config driver for PostgreSQL (:issue:`2723`)
- **Core - Bot Commands** - Added ``[p]licenseinfo`` (:issue:`3090`)
- **Core - Bot Commands** - Added a command to list disabled commands globally or per guild (:issue:`3118`)
- **Core - Command-line Interfaces** - Added the cli flag ``redbot --edit`` which is used to edit the instance name, token, owner, and datapath (:issue:`3060`)
- **Core - Command-line Interfaces** - Added ``redbot-setup backup`` (:issue:`3235`)
- **Core - Command-line Interfaces** - Added ``redbot --debuginfo`` flag which shows useful information for debugging (:issue:`3183`)
- **Cogs - Audio** - Added support for nested folders in the localtrack folder (:issue:`270`)
- **Cogs - Audio** - Audio now auto pauses the queue when the voice channel is empty (:issue:`721`)
- **Cogs - Audio** - All playlist commands now accept optional arguments, use ``[p]help playlist <subcommand>`` for more details (:issue:`2861`)
- **Cogs - Audio** - ``[p]playlist rename`` will now allow users to rename existing playlists (:issue:`2861`)
- **Cogs - Audio** - ``[p]playlist update`` will now allow users to update non-custom Playlists to the latest available tracks (:issue:`2861`)
- **Cogs - Audio** - There are now 3 different scopes of playlist. To define them, use the ``--scope`` argument

      ``Global Playlist``

      - These playlists will be available in all servers the bot is in.
      - These can be managed by the Bot Owner only.

      ``Server Playlist``

      - These playlists will only be available in the server they were created in.
      - These can be managed by the Bot Owner, Guild Owner, Mods, Admins, DJs, and the Creator (if the DJ role is disabled).

      ``User Playlist``

      - These playlists will be available in all servers both the bot and the creator are in.
      - These can be managed by the Bot Owner and Creator only. (:issue:`2861`)
- **Cogs - Audio** - ``[p]audioset cache`` can now be used to set the cache level. **It's off by default** (:issue:`2904`)
- **Cogs - Audio** - ``[p]genre`` can now be used to play spotify playlists (:issue:`2904`)
- **Cogs - Audio** - ``[p]audioset cacheage`` can now be used to set the maximum age of an entry in the cache. **Default is 365 days** (:issue:`2904`)
- **Cogs - Audio** - ``[p]audioset autoplay`` can now be used to enable auto play once the queue runs out (:issue:`2904`)
- **Cogs - Audio** - ``[p]queue shuffle`` can now be used to shuffle the queue manually (:issue:`2904`)
- **Cogs - Audio** - ``[p]queue clean self`` can now be used to remove all songs you requested from the queue (:issue:`2904`)
- **Cogs - Audio** - ``[p]audioset restrictions`` can now be used to add or remove keywords which songs must have or are not allowed to have (:issue:`2904`)
- **Cogs - Audio** - ``[p]playlist dedupe`` can now be used to remove duplicated tracks from a playlist (:issue:`2904`)
- **Cogs - Audio** - ``[p]autoplay`` can now be used to play a random song (:issue:`2904`)
- **Cogs - Audio** - ``[p]bumpplay`` can now be used to add a song to the front of the queue (:issue:`2940`)
- **Cogs - Audio** - ``[p]shuffle`` now has an additional argument to tell the bot whether it should shuffle bumped tracks (:issue:`2940`)
- **Cogs - Audio** - Added global whitelist/blacklist commands (:issue:`3047`)
- **Cogs - Audio** - Added self-managed daily playlists in the GUILD scope, these are called "Daily playlist - YYYY-MM-DD" and auto delete after 7 days (:issue:`3199`)
- **Cogs - Bank** - Added ``[p]bankset maxbal`` to set the maximum bank balance (:issue:`2926`)
- **Cogs - Economy** - Added new commands for pruning bank accounts (:issue:`2845`)

  - ``[p]bank prune user`` - This will delete a user's bank account.
  - ``[p]bank prune local`` - This will prune the bank of accounts for users who are no longer in the server.
  - ``[p]bank prune global`` - This will prune the global bank of accounts for users who do not share any servers with the bot.
- **Cogs - Downloader** - Added ``[p]repo update [repos]`` which updates repos without updating the cogs from them (:issue:`2527`)
- **Cogs - Downloader** - Added ``[p]cog installversion <repo_name> <revision> <cogs>`` which installs cogs from a specified revision (commit, tag) of the given repo. When using this command, the cog will automatically be pinned (:issue:`2527`)
- **Cogs - Downloader** - Added ``[p]cog pin <cogs>`` and ``[p]cog unpin <cogs>`` for pinning cogs. Cogs that are pinned will not be updated when using update commands (:issue:`2527`)
- **Cogs - Downloader** - Added ``[p]cog checkforupdates`` that lists which cogs can be updated (including pinned cog) without updating them (:issue:`2527`)
- **Cogs - Downloader** - Added ``[p]cog updateallfromrepos <repos>`` that updates all cogs from the given repos (:issue:`2527`)
- **Cogs - Downloader** - Added ``[p]cog updatetoversion <repo_name> <revision> [cogs]`` that updates all cogs or ones of user's choosing to chosen revision of the given repo (:issue:`2527`)
- **Cogs - Downloader** - Added ``[p]cog reinstallreqs`` that reinstalls cog requirements and shared libraries for all installed cogs (:issue:`3167`)
- **Cogs - Trivia - Lists** - Added trivia lists for Prince and Michael Jackson lyrics (:issue:`12`)

Changes
*******

- Red now takes less time to fetch cases, unban members, and list warnings (:issue:`2964`)
- **Core** - JSON config files are now stored without indentation, this is to reduce the file size and increase the performance of write operations (:issue:`2921`)
- **Core** - Red now handles more things prior to connecting to discord to reduce issues during the initial load (:issue:`3045`)
- **Core** - Red will now send a message when the invoked command is DM-only (:issue:`3057`)
- **Core** - The lib folder is now cleared on minor Python version changes. ``[p]cog reinstallreqs`` in Downloader can be used to regenerate the lib folder for a new Python version (:issue:`3274`)
- **Core** - If Red detects operating system or architecture change, it will now warn the owner about possible problems with the lib folder (:issue:`3274`)
- **Core - Bot Commands** - Changed ``[p]info`` to say "This bot is an..." instead of "This is an..." for clarity (:issue:`3121`)
- **Core - Bot Commands** - Added the Python executable field to ``[p]debuginfo`` (:issue:`3184`)
- **Core - Command-line Interfaces** - Added the option to modify the RPC port with the ``--rpc-port`` flag (:issue:`2429`)
- **Core - Command-line Interfaces** - ``--[no-]backup``, ``--[no-]drop-db`` and ``--[no-]remove-datapath`` in the ``redbot-setup delete`` command are now on/off flags (:issue:`2958`)
- **Core - Command-line Interfaces** - The confirmation prompts in ``redbot-setup`` now have default values for user convenience (:issue:`2958`)
- **Core - Command-line Interfaces** - ``redbot-setup delete`` now has the option to leave Red's data untouched on database backends (:issue:`2962`)
- **Core - Command-line Interfaces** - All ``y/n`` confirmations in cli commands are now unified (:issue:`3060`)
- **Core - Command-line Interfaces** - ``redbot-setup`` will now use the instance name in default data paths to avoid creating a second instance with the same data path (:issue:`3171`)
- **Core - Command-line Interfaces** - Instance names can now only include characters A-z, numbers, underscores, and hyphens. Old instances are unaffected by this change (:issue:`3171`)
- **Core - Command-line Interfaces** - When Red prompts for a token, it will now print a link to the guide explaining how to obtain a token (:issue:`3204`)
- **Core - Command-line Interfaces** - ``redbot-setup`` will no longer log to disk (:issue:`3269`)
- **Core - Dependencies** - Bumped dependency versions (:issue:`3288`)
- **Core - Dependencies** - Bumped Red-Lavalink version (:issue:`3290`)
- **Core - Modlog** - Modlog no longer generates cases without being told to for actions the bot did (:issue:`2897`)
- **Core - Modlog** - Modlog is now much faster at creating cases, especially in large servers (:issue:`2908`)
- **Cogs - Admin** - Changed ``[p]announce ignore`` and ``[p]announce channel`` to ``[p]announceset ignore`` and ``[p]announceset channel`` (:issue:`3250`)
- **Cogs - Admin** - Changed ``[p]selfrole <role>`` to ``[p]selfrole add <role>``, changed ``[p]selfrole add`` to ``[p]selfroleset add`` , and changed ``[p]selfrole delete`` to ``[p]selfroleset remove`` (:issue:`3250`)
- **Cogs - Admin** - Added custom issue messages for adding and removing roles, this makes it easier to create translations (:issue:`3016`)
- **Cogs - Audio** - ``[p]playlist download`` will now compress playlists larger than the server attachment limit and attempt to send that (:issue:`3279`)
- **Cogs - Audio** - ``[p]playlist upload`` will now load playlists generated via ``[p]playlist download`` much faster if the playlist uses the new scheme (:issue:`2861`)
- **Cogs - Audio** - ``[p]playlist`` commands now can be used by everyone regardless of DJ settings, however it will respect DJ settings when creating/modifying playlists in the server scope (:issue:`2861`)
- **Cogs - Audio** - Spotify, Youtube Data, and Lavalink API calls can now be cached to avoid repeated calls in the future, see ``[p]audioset cache`` (:issue:`2890`)
- **Cogs - Audio** - Playlists will now start playing as soon as first track is loaded (:issue:`2890`)
- **Cogs - Audio** - ``[p]audioset localpath`` can set a path anywhere in your machine now. Note: This path needs to be visible by ``Lavalink.jar`` (:issue:`2904`)
- **Cogs - Audio** - ``[p]queue`` now works when there are no tracks in the queue, showing the track currently playing (:issue:`2904`)
- **Cogs - Audio** - ``[p]audioset settings`` now reports Red Lavalink version (:issue:`2904`)
- **Cogs - Audio** - Adding and removing reactions in Audio is no longer a blocking action (:issue:`2904`)
- **Cogs - Audio** - When shuffle is on, queue now shows the correct play order (:issue:`2904`)
- **Cogs - Audio** - ``[p]seek`` and ``[p]skip`` can now be used by user if they are the song requester while DJ mode is enabled and votes are disabled (:issue:`2904`)
- **Cogs - Audio** - Adding a playlist and an album to a saved playlist now skips tracks already in the playlist (:issue:`2904`)
- **Cogs - Audio** - DJ mode is now turned off if the DJ role is deleted (:issue:`2904`)
- **Cogs - Audio** - When playing a localtrack, ``[p]play`` and ``[p]bumpplay`` no longer require the use of the prefix "localtracks\\" (:issue:`2904`)

  Before: ``[p]bumpplay localtracks\ENM\501 - Inside The Machine.mp3``
  Now: ``[p]bumpplay ENM\501 - Inside The Machine.mp3``
  Now nested folders: ``[p]bumpplay Parent Folder\Nested Folder\track.mp3``
- **Cogs - Audio** - Removed commas in explanations about how to set API keys (:issue:`2905`)
- **Cogs - Audio** - Expanded local track support to all file formats (m3u, m4a, mp4, etc) (:issue:`2940`)
- **Cogs - Audio** - Cooldowns are now reset upon failure of commands that have a cooldown timer (:issue:`2940`)
- **Cogs - Audio** - Improved the explanation in the help string for ``[p]audioset emptydisconnect`` (:issue:`3051`)
- **Cogs - Audio** - Added a typing indicator to playlist dedupe (:issue:`3058`)
- **Cogs - Audio** - Exposed clearer errors to users in the play commands (:issue:`3085`)
- **Cogs - Audio** - Improved error handling when the player is unable to play multiple tracks in the sequence (:issue:`3165`)
- **Cogs - CustomCommands** - The group command ``[p]cc create`` can now be used to create simple CCs without specifying "simple" (:issue:`1767`)
- **Cogs - CustomCommands** - Added a query option for CC typehints for URL-based CCs (:issue:`3228`)
- **Cogs - CustomCommands** - Now uses the ``humanize_list()`` utility for iterable parameter results, e.g. ``{#:Role.members}`` (:issue:`3277`)
- **Cogs - Downloader** - During cog update, Downloader will now check if the Python and bot versions match requirements provided by the cog author(s) in ``info.json`` (:issue:`1866`)
- **Cogs - Downloader** - ``[p]cog install`` now accepts multiple cog names (:issue:`2527`)
- **Cogs - Downloader** - When passing cogs to ``[p]cog update``, it will now only update those cogs, not all cogs from the repo those cogs are from (:issue:`2527`)
- **Cogs - Downloader** - Added error messages for failures when installing/reinstalling requirements and copying cogs and shared libraries (:issue:`2571`)
- **Cogs - Downloader** - ``[p]findcog`` now uses sanitized urls (without HTTP Basic Auth fragments) (:issue:`3129`)
- **Cogs - Downloader** - ``[p]repo info`` will now show the repo's url, branch, and authors (:issue:`3225`)
- **Cogs - Downloader** - ``[p]cog info`` will now show cog authors (:issue:`3225`)
- **Cogs - Downloader** - ``[p]findcog`` will now show the repo's branch (:issue:`3225`)
- **Cogs - Economy** - Slots now has a 62.5% expected payout and will not inflate economy when spammed (:issue:`2875`)
- **Cogs - Image** - Updated the ``[p]giphycreds`` command to match the formatting of the other API commands (:issue:`2905`)
- **Cogs - Image** - Removed commas from explanations about how to set API keys (:issue:`2905`)
- **Cogs - Mod** - ``[p]slowmode`` now accepts integer-only inputs as seconds (:issue:`2884`)
- **Cogs - Permissions** - Better explained the usage of commands with the ``<who_or_what>`` argument (:issue:`2991`)
- **Cogs - Streams** - Removed commas from explanations about how to set API keys (:issue:`2905`)

Removals
********

- **Core - Bot Commands** - ``[p]set owner`` and ``[p]set token`` have been removed in favor of ``redbot --edit`` (:issue:`2928`)
- **Core - Bot Commands** - Removed ``[p]backup``. Use the cli command ``redbot-setup backup`` instead (:issue:`3235`)
- **Core - Command-line Interfaces** - Removed a lot of the functionality of ``redbot-launcher`` and deprecated what's left (:issue:`3289`)
- **Cogs - Downloader** - Shared libraries are marked for removal in Red 3.4 (:issue:`3106`)

Fixes
*****

- **Core** - Red no longer types infinitely when a command with a cooldown is called within the last second of a cooldown. (:issue:`2985`)
- **Core** - Added a 3rd-party lib folder to ``sys.path`` before loading cogs. This prevents issues with 3rd-party cogs failing to load when Downloader is not loaded to install requirements (:issue:`3036`)
- **Core** - Red will now properly send an error message when the invoked command is guild-only (:issue:`3057`)
- **Core** - Red now always appends the 3rd-party lib folder to the end of ``sys.path`` to avoid shadowing Red's dependencies (:issue:`3062`)
- **Core** - Guild owners are no longer affected by the local whitelist and blacklist (:issue:`3221`)
- **Core - Bot Commands** - The ``[p]invite`` command no longer errors when a user has the bot blocked or DMs disabled in the server (:issue:`2948`)
- **Core - Bot Commands** - Cleaned up the ``[p]inviteset public`` and ``[p]inviteset perms`` help strings (:issue:`2963`)
- **Core - Bot Commands** - ```[p]embedset user`` now only affects DM's (:issue:`2966`)
- **Core - Bot Commands** - Fixed the help text and response of ``[p]set usebotcolor`` to accurately reflect what the command is doing (:issue:`2974`)
- **Core - Bot Commands** - Fixed an error in ``[p]uptime`` when the uptime is under a second (:issue:`3009`)
- **Core - Bot Commands** - Added quotation marks to the response of ``[p]helpset tagline`` so that two consecutive full stops do not appear (:issue:`3010`)
- **Core - Bot Commands** - Red will now prevent users from locking themselves out with ``[p]localblacklist`` (:issue:`3207`)
- **Core - Bot Commands** - Fixed formatting issues in commands that list whitelisted/blacklisted users/roles when the list is empty (:issue:`3219`)
- **Core - Bot Commands** - Red will now prevent users from locking the guild owner out with ``[p]localblacklist`` (unless the command caller is bot owner) (:issue:`3221`)
- **Core - Command-line Interfaces** - Stopped using the ``:`` character in backup's filename - Windows doesn't accept it (:issue:`2954`)
- **Core - Command-line Interfaces** - ``redbot-setup delete`` no longer errors with "unexpected keyword argument" (:issue:`2955`)
- **Core - Command-line Interfaces** - ``redbot-setup delete`` no longer prompts about backup when the user passes the option ``--no-prompt`` (:issue:`2956`)
- **Core - Command-line Interfaces** - Fixed an unfriendly error when the provided instance name doesn't exist (:issue:`2968`)
- **Core - Command-line Interfaces** - Removed f-string usage in the launcher to prevent our error handling from causing an error (:issue:`3002`)
- **Core - Command-line Interfaces** - Arguments ``--co-owner`` and ``--load-cogs`` now properly require at least one argument to be passed (:issue:`3060`)
- **Core - Command-line Interfaces** - Fixed the generation of the ``repos.json`` file in the backup process (:issue:`3114`)
- **Core - Command-line Interfaces** - Added handling for invalid folder names in the data path gracefully in ``redbot-setup`` and ``redbot --edit`` (:issue:`3171`)
- **Core - Command-line Interfaces** - ``--owner`` and ``-p`` cli flags now work when added from launcher (:issue:`3174`)
- **Core - Help** - Help now properly hides disabled commands (:issue:`2863`)
- **Core - Help** - Fixed help ending up a little too large for Discord embed limits (:issue:`3208`)
- **Core - Modlog** - Modlog entries now show up properly without the mod cog loaded (:issue:`2897`)
- **Core - Modlog** - Removed potential for additional bad API calls per ban/unban (:issue:`2945`)
- **Cogs - Admin** - Fixed ``[p]announce`` failing after encountering an error attempting to message the bot owner (:issue:`3166`)
- **Cogs - Admin** - Improved the clarity of user facing messages when the user is not allowed to do something due to Discord hierarchy rules (:issue:`3250`)
- **Cogs - Admin** - Fixed some role managing commands not properly checking if Red had Manage Roles permission before attempting to manage roles (:issue:`3250`)
- **Cogs - Admin** - Fixed commands from ``[p]editrole`` command group not checking if roles to be edited are higher than Red's highest role before trying to edit them (:issue:`3250`)
- **Cogs - Admin** - Fixed ``[p]announce ignore`` and ``[p]announce channel`` not being able to be used by guild owners and administrators (:issue:`3250`)
- **Cogs - Audio** - ``[p]playlist remove`` now removes the playlist url if the playlist was created through ``[p]playlist save`` (:issue:`2861`)
- **Cogs - Audio** - Users are no longer able to accidentally overwrite existing playlist if a new one with the same name is created/renamed (:issue:`2861`)
- **Cogs - Audio** - ``[p]audioset settings`` no longer shows lavalink JAR version (:issue:`2904`)
- **Cogs - Audio** - Fixed a ``KeyError: loadType`` when trying to play tracks (:issue:`2904`)
- **Cogs - Audio** - ``[p]audioset settings`` now properly considers co-owners as owners (:issue:`2904`)
- **Cogs - Audio** - Fixed track indexes being off by 1 in ``[p]search`` (:issue:`2940`)
- **Cogs - Audio** - Fixed an issue where updating your Spotify and YouTube Data API tokens did not refresh them (:issue:`3047`)
- **Cogs - Audio** - Fixed an issue where the blacklist was not being applied correctly (:issue:`3047`)
- **Cogs - Audio** - Fixed an issue in ``[p]audioset restrictions blacklist list`` where it would call the list a ``Whitelist`` (:issue:`3047`)
- **Cogs - Audio** - Red's status is now properly cleared on emptydisconnect (:issue:`3050`)
- **Cogs - Audio** - Fixed a console spam caused sometimes when auto disconnect and auto pause are used (:issue:`3123`)
- **Cogs - Audio** - Fixed an error that was thrown when running ``[p]audioset dj`` (:issue:`3165`)
- **Cogs - Audio** - Fixed a crash that could happen when the bot can't connect to the Lavalink node (:issue:`3238`)
- **Cogs - Audio** - Restricted the number of songs shown in the queue to first 500 to avoid heartbeats (:issue:`3279`)
- **Cogs - Audio** - Added more cooldowns to playlist commands and restricted the queue and playlists to 10k songs to avoid bot errors (:issue:`3286`)
- **Cogs - Audio** - Lavalink will now be restarted after an unexpected shutdown (:issue:`3033`)
- **Cogs - Audio** - Track descriptions are now escaped so that they do not break markdown (:issue:`3047`)
- **Cogs - Audio** - Fixed an issue where calling Audio commands when not in a voice channel could result in a crash (:issue:`3120`)
- **Cogs - Audio** - Fixed an issue where some YouTube playlists were being recognised as single tracks (:issue:`3104`)
- **Cogs - Downloader** - Made the regex for repo names use raw strings to stop causing a ``DeprecationWarning`` for invalid escape sequences (:issue:`2571`)
- **Cogs - Downloader** - Downloader will no longer attempt to install cogs that are already installed (:issue:`2571`)
- **Cogs - Downloader** - Repo names can now only contain the characters listed in the help text (A-Z, 0-9, underscores, and hyphens) (:issue:`2827`)
- **Cogs - Downloader** - ``[p]findcog`` no longer attempts to find a cog for commands without a cog (:issue:`2902`)
- **Cogs - Downloader** - Downloader will no longer attempt to install a cog with same name as another cog that is already installed (:issue:`2927`)
- **Cogs - Downloader** - Added error handling for when a remote repository or branch is deleted; now it notifies which repository failed and continues to update the others (:issue:`2936`)
- **Cogs - Downloader** - ``[p]cog install`` will no longer error if a cog has an empty install message (:issue:`3024`)
- **Cogs - Downloader** - Fixed an error on ``[p]repo add`` from empty string values for the ``install_msg`` info.json field (:issue:`3153`)
- **Cogs - Downloader** - Disabled all git auth prompts when adding/updating a repo with Downloader (:issue:`3159`)
- **Cogs - Downloader** - ``[p]findcog`` now properly works for cogs with less typical folder structure (:issue:`3177`)
- **Cogs - Downloader** - ``[p]cog uninstall`` now fully unloads cog - the bot will not try to load it on next startup (:issue:`3179`)
- **Cogs - Economy** - Fixed a crash seen when calling economy commands in DM with a global bank (:issue:`2997`)
- **Cogs - Mod** - ``[p]userinfo`` no longer breaks when a user has an absurd number of roles (:issue:`2910`)
- **Cogs - Mod** - Fixed Mod cog not recording username changes for ``[p]names`` and ``[p]userinfo`` commands (:issue:`2918`)
- **Cogs - Mod** - Fixed ``[p]modset deletedelay`` deleting non-command messages (:issue:`2924`)
- **Cogs - Mod** - Fixed an error when reloading Mod (:issue:`2932`)
- **Cogs - Modlog** - Fixed an error in ``[p]reason`` when setting the reason for a case without a moderator (:issue:`2908`)
- **Cogs - Permissions** - Defaults are now cleared properly when clearing all rules (:issue:`3037`)
- **Cogs - Permissions** - Fixed an issue with clearing rules in permissions (:issue:`3014`)
- **Cogs - Streams** - Fixed a ``TypeError`` in the ``TwitchStream`` class when calling Twitch client_id from Red shared APIs tokens (:issue:`3042`)
- **Cogs - Streams** - Changed the ``stream_alert`` function for Twitch alerts to make it work with how the ``TwitchStream`` class works now (:issue:`3042`)
- **Cogs - Trivia** - Fixed a bug where ``[p]trivia leaderboard`` failed to run (:issue:`2911`)
- **Cogs - Trivia - Lists** - Fixed a typo in Ahsoka Tano's name in the Starwars trivia list (:issue:`2909`)
- **Cogs - Trivia - Lists** - Fixed a typo in the Greek mythology trivia list regarding Hermes' staff (:issue:`2994`)
- **Cogs - Trivia - Lists** - Fixed a question in the Overwatch trivia list that accepted blank responses (:issue:`2996`)
- **Cogs - Trivia - Lists** - Fixed questions and answers that were incorrect in the Clash Royale trivia list (:issue:`3236`)


.. _important-320-1:

Developer changelog
-------------------

Breaking Changes
****************

- **Core** - Extension's ``setup()`` function should no longer assume that we are, or even will be connected to Discord (:issue:`3073`)

    This also means that cog creators should no longer use ``bot.wait_until_ready()`` inside it
- **Core - Bank** - Removed ``bank.MAX_BALANCE``, use `redbot.core.bank.get_max_balance()` from now on (:issue:`2926`)
- **Core - Commands Package** - Reserved some command names for internal Red use. These are available programatically as ``redbot.core.commands.RESERVED_COMMAND_NAMES`` (:issue:`2973`)
- **Core - Commands Package** - Qualified command names are limited to a maximum of 60 characters (:issue:`3223`)
- **Core - Bot Class** - The main bot config is no longer directly accessible to cogs. New methods have been added for use where this is concerned (:issue:`2967`)

  New methods for this include:

    - `Red.get_shared_api_tokens()`
    - `Red.set_shared_api_tokens()`
    - `Red.get_embed_colour()` (and its alias - ``get_embed_color()``)
    - `Red.get_admin_roles()`
    - `Red.get_admin_role_ids()`
    - `Red.get_mod_roles()`
    - `Red.get_mod_role_ids()`
- **Core - Bot Class** - Removed ``bot._counter``, Made a few more attributes private (``cog_mgr``, ``main_dir``) (:issue:`2976`)
- **Core - Modlog** - Modlog casetypes no longer have an attribute for auditlog action type (:issue:`2897`)
- **Core - Modlog** - Removed ``redbot.core.modlog.get_next_case_number()`` (:issue:`2908`)

Additions
*********

- Added a few methods and classes replacing direct config access (which is no longer supported) (:issue:`2976`)

   - `Red.allowed_by_whitelist_blacklist()`
   - `Red.get_valid_prefixes()`
   - `Red.remove_shared_api_tokens()`
   - `redbot.core.commands.help.HelpSettings`
- **Core - Bot Class** - Added the method `Red.wait_until_red_ready()` that waits until Red's post connection startup is done (:issue:`3273`)
- **Core - Bot Class** - New event ``on_red_api_tokens_update`` is now dispatched when shared api keys for a service are updated (:issue:`3134`)
- **Core - Config** - Added functions to acquire locks on Config groups and values. These locks are acquired by default when calling a value as a context manager. See `Value.get_lock()` for details (:issue:`2654`)
- **Core - Config** - Added methods to Config for accessing things by id without mocked objects (:issue:`2804`)

    - `Config.guild_from_id()`
    - `Config.user_from_id()`
    - `Config.role_from_id()`
    - `Config.channel_from_id()`
    - `Config.member_from_ids()`
      - This one requires multiple ids, one for the guild, one for the user
      - Consequence of discord's object model
- **Core - Modlog** - Added ``redbot.core.modlog.get_latest_case()`` to fetch the case object for the most recent Modlog case (:issue:`2908`)
- **Core - Utils Package** - Added `redbot.core.utils.chat_formatting.humanize_number()` function to convert numbers into text that respects the current locale (:issue:`2836`)
- **Core - Utils Package** - Added the function `redbot.core.utils.chat_formatting.text_to_file()` to prepare a long text to be sent as a file (:issue:`2849`)
- **Core - Utils Package** - Added ``use_cached`` and ``images_only`` kwargs to `redbot.core.utils.tunnel.Tunnel.files_from_attach()` (:issue:`2885`)
- **Cogs - Audio** - New events dispatched by Audio (:issue:`2904`)

   - ``on_red_audio_track_start(guild: discord.Guild, track: lavalink.Track, requester: discord.Member)``
   - ``on_red_audio_track_end(guild: discord.Guild, track: lavalink.Track, requester: discord.Member)``
   - ``on_red_audio_track_enqueue(guild: discord.Guild, track: lavalink.Track, requester: discord.Member)``
   - ``on_red_audio_track_auto_play(guild: discord.Guild, track: lavalink.Track, requester: discord.Member)``
   - ``on_red_audio_queue_end(guild: discord.Guild, track: lavalink.Track, requester: discord.Member)``
   - ``on_red_audio_audio_disconnect(guild: discord.Guild)``
   - ``on_red_audio_skip_track(guild: discord.Guild, track: lavalink.Track, requester: discord.Member)``

Changes
*******

- **Core - Bot Class** - `Red.send_filtered()` now returns the message that is sent (:issue:`3052`)
- **Core - Bot Class** - `Red.send_to_owners()` and `Red.get_owner_notification_destinations()` now log when they are not able to find the owner notification destination (:issue:`3273`)
- **Core - Commands Package** - Allowed passing ``cls`` in the `redbot.core.commands.group()` decorator (:issue:`2881`)
- **Core - Modlog** - Some generic modlog casetypes are now pre-registered for cog creator use (:issue:`2897`)

Removals
********

- **Core - Utils Package** - Removed the functions ``safe_delete``, ``fuzzy_command_search``, ``format_fuzzy_results`` and ``create_backup`` from ``redbot.core.utils`` (:issue:`3240`)

Fixes
*****

- **Core - Bank** - Bank functions now check the recipient balance before transferring and stop the transfer if the recipient's balance will go above the maximum allowed balance (:issue:`2923`)
- **Core - Bot Class** - Fixed `Red.remove_command()` throwing an error when trying to remove a non-existent command (:issue:`2888`)
- **Core - Bot Class** - Fixed ``is_automod_immune``'s handling of the guild check and added support for checking webhooks (:issue:`3100`)
- **Core - Bot Class** - ``Red.owner_id`` is now set in the post connection startup (:issue:`3273`)
- **Core - Bot Class** - `Red.send_to_owners()` and `Red.get_owner_notification_destinations()` now wait until Red is done with post connection startup to ensure owner ID is available (:issue:`3273`)
- **Core - Commands Package** - `Command.can_see()` now works as intended for disabled commands (:issue:`2892`)
- **Core - Commands Package** - Fixed ``Context.clean_prefix`` issues resulting from undocumented changes from discord (:issue:`3249`)
- **Core - Utils Package** - Fixed `MessagePredicate.greater()` and `MessagePredicate.less()` allowing any valid int instead of only valid ints/floats that are greater/less than the given value (:issue:`3004`)
- **Core - Utils Package** - Fixed an attribute error that can be raised in `redbot.core.utils.chat_formatting.humanize_timedelta()` if ``seconds = 0`` (:issue:`3231`)


Documentation changes
---------------------

Additions
*********

- Started the user guides covering cogs and the user interface of the bot. This includes, for now, a "Getting started" guide (:issue:`1734`)
- Added documentation for PM2 support (:issue:`2105`)
- Updated linux install docs, adding sections for Fedora Linux, Debian/Raspbian Buster, and openSUSE (:issue:`2558`)
- Created documentation covering what we consider a developer facing breaking change and the guarantees regarding them (:issue:`2882`)
- Added notes explaining the best practices with config (:issue:`3149`)
- Added a "Publishing cogs for V3" document explaining how to make user's cogs work with Downloader (:issue:`3234`)

Changes
*******

- Reworded the virtual environment guide to make it sound less scary (:issue:`2920`)
- Added more information about `redbot.core.utils.chat_formatting.humanize_timedelta()` into the docs (:issue:`2986`)
- Added a direct link to the "Installing Red" section in "Installing using powershell and chocolatey" (:issue:`2995`)
- Updated Git PATH install (Windows), capitalized some words, stopped mentioning the launcher (:issue:`2998`)
- Added autostart documentation for Red users who installed Red inside of a virtual environment (:issue:`3005`)
- Updated the Cog Creation guide with a note regarding the Develop version as well as the folder layout for local cogs (:issue:`3021`)
- Added links to the getting started guide at the end of installation guides (:issue:`3025`)
- Added proper docstrings to enums that show in drivers docs (:issue:`3035`)
- Discord.py doc links will now always use the docs for the currently used version of discord.py (:issue:`3053`)
- Added ``|DPY_VERSION|`` substitution that will automatically get replaced by the current discord.py version (:issue:`3053`, :issue:`3082`)
- Added MS Azure to the host list (:issue:`3083`)
- Added information about ``info.json``'s ``min_python_version`` key in Downloader Framework docs (:issue:`3124`)
- Documented additional attributes in Context (:issue:`3151`)
- Updated Windows docs with up to date dependency instructions (:issue:`3188`)
- Added a line about setuptools and wheel (:issue:`3262`)
- Ensured development builds are not advertised to the wrong audience (:issue:`3292`)
- Clarified the usage intent of some of the chat formatting functions (:issue:`3292`)

Removals
********

- Removed API References for Downloader (:issue:`3234`)

Fixes
*****

- Fixed the user parameter being labeled as ``discord.TextChannel`` instead of ``discord.abc.User`` in ``redbot.core.utils.predicates`` (:issue:`2914`)
- Driver docs no longer show twice (:issue:`2972`)
- Added missing descriptions for function returns (:issue:`3054`)
- Fixed broken docs for ``redbot.core.commands.Context.react_quietly`` (:issue:`3257`)
- Updated the docs footer copyright to 2018-2019 (:issue:`3105`)
- Updated copyright notices on License and RTD config to 2020 (:issue:`3259`)

----

Redbot 3.1.9 (2020-01-08)
=========================

This is a maintenance release patching a denial of service issue with Audio.

----

Redbot 3.1.8 (2019-11-19)
=========================

This is a hotfix release updating discord.py to fix a full bot crash when emoji reaction is added/removed.
This was caused by Discord API changes.

----

Redbot 3.1.7 (2019-11-05)
=========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`aikaterna`, :ghuser:`mikeshardmind`

End-user changelog
------------------

Changes
*******

- **Cogs - Audio** - Improved handling of user facing errors (`989e16b <https://github.com/Cog-Creators/Red-DiscordBot/commit/989e16b20b814971e01a8657dedf4d9b45c23ed1>`__)

Fixes
*****

- **Core - Dependencies** - Added partial mitigation for issues with running Red on Python 3.8 (`1c64abe <https://github.com/Cog-Creators/Red-DiscordBot/commit/1c648abea21c28cd3b912d1cb2fee6cf2960e352>`__)
- **Cogs - Audio** - Fixed issues with SoundCloud playback (`989e16b <https://github.com/Cog-Creators/Red-DiscordBot/commit/989e16b20b814971e01a8657dedf4d9b45c23ed1>`__)

----

Redbot 3.1.6 (2019-10-18)
=========================

This is a hotfix release updating discord.py for a critical issue related to voice connections.

----

Redbot 3.1.5 (2019-07-31)
=========================

This is a maintenance release fixing issues with playback of YouTube tracks.

----

Redbot 3.1.4 (2019-07-16)
=========================

This is a hotfix release fixing issues with broken custom commands and modlog cases.

----

Redbot 3.1.3 (2019-07-14)
=========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`aikaterna`, :ghuser:`Bakersbakebread`, :ghuser:`DevilXD`, :ghuser:`DiscordLiz`, :ghuser:`Drapersniper`, :ghuser:`Flame442`, :ghuser:`jack1142`, :ghuser:`kennnyshiwa`, :ghuser:`Kowlin`, :ghuser:`lizzyd710`, :ghuser:`MeatyChunks`, :ghuser:`mikeshardmind`, :ghuser:`NeuroAssassin`, :ghuser:`PredaaA`, :ghuser:`retke`, :ghuser:`Tobotimus`, :ghuser:`yamikaitou`

End-user changelog
------------------

Additions
*********

- **Core - Bot Commands** - Added new settings for the invite returned by ``[p]invite`` command (:issue:`1847`)
    
    - ``[p]inviteset public`` - Defines if the command should be accessible for users that aren't bot owners.
    - ``[p]inviteset perms`` - Sets permissions for bot's managed role that can get created automatically when bot is invited.

    For more information, see help of each of the listed commands.
- **Cogs - Audio** - Added a ``[p]eq`` command group that allows to manage the Audio equalizer (:issue:`2787`, :issue:`2813`)
- **Cogs - Audio** - Added a ``[p]summon`` command that summons the bot to the voice channel (:issue:`2786`)

Changes
*******

- **Core** - A server can now have multiple admin and mod roles (:issue:`2783`)
- **Core - Dependencies** - Improved overall performance on Linux and Mac systems by swapping asyncio loop implementation to uvloop (:issue:`2819`)
- **Cogs - Audio** - Added support for armv6l, aarch32, and aarch64 architectures (:issue:`2755`)
- **Cogs - Audio** - Improved error handling and added retrying to jar download and Lavalink connection (:issue:`2764`)
- **Cogs - Audio** - Internal Lavalink manager now accepts any jar with a build number greater than or equal to our release build (:issue:`2656`, :issue:`2785`)
- **Cogs - Audio** - Increased Lavalink connection timeout to 50 seconds to ensure Lavalink manages to start before the time runs out on lower-end devices (:issue:`2784`)
- **Cogs - Filter** - Updated name filtering to be consistent with message content filtering (:issue:`2740`, :issue:`2794`)
- **Cogs - Mod** - ``[p]userinfo`` command now mentions the roles the user has (:issue:`2759`)
- **Cogs - Modlog** - Improved efficiency of case storage (:issue:`2766`)

Fixes
*****

- **Core** - Fixed broken fuzzy help (:issue:`2768`)
- **Core** - Fixed a race condition that could allow a user to run commands they are denied to run by Permissions cog for a short moment before the cog is loaded (:issue:`2857`)
- **Core - Bot Commands** - ``[p]command disable`` and its subcommands now ensure that the command to disable is not ``[p]command`` or any of its subcommands to prevent lockout (:issue:`2770`)
- **Core - Bot Commands** - Fixed an issue with error message being sent multiple times when help command was unable to DM the user (:issue:`2790`)
- **Core - Bot Commands** - Fixed broken link in help of ``[p]set color`` (:issue:`2715`, :issue:`2803`)
- **Core - Bot Commands** - Fixed user output and exception handling on cog load/reload (:issue:`2767`)
- **Core - Help** - Fixed substitution of ``[p]`` in command descriptions in non-embedded help output (:issue:`2846`)
- **Cogs - Audio** - Added missing bot permission checks to commands in Audio cog (:issue:`2756`)
- **Cogs - Audio** - Fixed an issue with jar downloading on mixed-filesystem environments (:issue:`2682`, :issue:`2765`)
- **Cogs - Audio** - Fixed an issue with ``[p]playlist copy`` and ``[p]playlist queue`` failing when the prefix contains certain characters (:issue:`2788`, :issue:`2789`)
- **Cogs - Audio** - Fixed an issue that caused ``[p]shuffle`` and ``[p]repeat`` to send an error message when the user is not in the voice channel (:issue:`2811`, :issue:`2812`, :issue:`2842`)
- **Cogs - Filter** - Fixed caching issue that caused filter to use an old list of words to filter (:issue:`2810`)
- **Cogs - Permissions** - Commands for adding/removing rules in ``[p]permissions`` command group now no longer ignore invalid arguments (:issue:`2851`, :issue:`2865`)
- **Cogs - Trivia - Lists** - Fixed answers for Beethoven-related questions in ``entertainment`` trivia list (:issue:`2318`, :issue:`2823`)


Developer changelog
-------------------

Additions
*********

- **Core** - Added ``UserFeedbackCheckFailure`` (:issue:`2761`)
- **Core - Bank** - Added `redbot.core.bank.cost()` (:issue:`2761`)
- **Core - Commands Package** - Added (optional) ``default_unit`` keyword argument to `TimedeltaConverter` (:issue:`2753`)
- **Core - Commands Package** - Added `Context.react_quietly()` (:issue:`2834`)

Fixes
*****

- **Core - Config** - Fixed cache issues with Config when the developer accidentally tries to set an object that isn't JSON serializable (:issue:`2793`, :issue:`2796`)
- **Core - Config** - Fixed an issue with identifiers that contain ``$`` or ``.`` which has caused a KeyError exception regardless of whether such key existed in the data (:issue:`2832`)


Documentation changes
---------------------

Changes
*******

- Added a warning about the PATH changes to Windows install guide (:issue:`2791`)

Fixes
*****

- Fixed code examples in Bank, Config, and ModLog API documentation (:issue:`2775`, :issue:`2780`, :issue:`2860`)
- Fixed the code example for the documentation of `Command.error` decorator and added a note with clarifications (:issue:`2760`)

----

Redbot 3.1.2 (2019-05-31)
=========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`bren0xa`, :ghuser:`DevilXD`, :ghuser:`DiscordLiz`, :ghuser:`fixator10`, :ghuser:`Flame442`, :ghuser:`jack1142`, :ghuser:`Kowlin`, :ghuser:`mikeshardmind`, :ghuser:`NeuroAssassin`, :ghuser:`palmtree5`, :ghuser:`PredaaA`, :ghuser:`retke`, :ghuser:`Stonedestroyer`, :ghuser:`Tobotimus`, :ghuser:`yamikaitou`, :ghuser:`zephyrkul`

End-user changelog
------------------

Additions
*********

- **Core** - Added a generic system that can be used by cog creators to send notifications meant for bot owners (:issue:`2665`, :issue:`2738`, :issue:`2745`)
- **Core - Bot Commands** - Added ``[p]debuginfo`` command (:issue:`2728`)

    This comes with some commands that allow to manage the destinations for the owner notifications.
    See the help of commands in ``[p]set ownernotifications`` command group for more information.
- **Core - Help** - Added a few new settings for bot's help (:issue:`2667`, :issue:`2681`, :issue:`2676`)

    - ``[p]helpset usemenus`` - Allows the help command to be sent as a paginated menu.
    - ``[p]helpset showhidden`` - Allows the help command to show hidden commands.
    - ``[p]helpset verifychecks``  - Sets if commands which can't be run in the current context should be filtered from help.
    - ``[p]helpset verifyexists`` - Allows the bot to respond indicating the existence of a specific help topic even if the user can't use it.

    For more information, see help of each of the listed commands.
- **Cogs - Mod** - Added ``[p]slowmode`` command (:issue:`2734`)

Changes
*******

- **Core - Bot Commands** - ``[p]load``, ``[p]unload``, and ``[p]reload`` commands now strip commas from the passed cogs to aid with copy-pasting (:issue:`2693`)
- **Core - Bot Commands** - Improved naming consistency of subcommands that *delete* something (:issue:`2731`)
- **Core - Bot Commands** - ``[p]set api`` command now allows the user to separate their keys and values with space in addition to commas and semicolons (:issue:`2692`)
- **Cogs - Downloader** - ``[p]pipinstall`` now indicates that it's doing something (:issue:`2700`)
- **Cogs - Mod** - ``[p]names`` command no longer requires quoting usernames that contain spaces (:issue:`2675`)
- **Cogs - Mod** - ``[p]userinfo`` command now mentions the voice channel the user is in (:issue:`2680`)

Fixes
*****

- **Core** - Fixed update notification for bots that have co-owners (:issue:`2677`)
- **Core** - Fixed an issue where bad user input didn't result in the bot sending help for the command (:issue:`2707`)
- **Core - Help** - Fixed an issue with incorrect subcommand descriptions being shown in non-embed help (:issue:`2678`)
- **Core - Help** - Fixed help for commands with no docstring (:issue:`2415`, :issue:`2722`)
- **Core - Help** - Help menu no longer blocks settings preview in command groups like ``[p]set`` (:issue:`2712`, :issue:`2725`)
- **Core - Bot Commands** - Fixed few more issues with help command (:issue:`2676`)
- **Core - Bot Commands** - Fixed error handling in ``[p]load`` command (:issue:`2686`, :issue:`2688`)
- **Core - Bot Commands** - Fixed an issue with long cog descriptions in help command (:issue:`2730`)
- **Core - Command-line Interfaces** - Fixed ``redbot-setup delete`` command failing to delete data path (:issue:`2709`)
- **Cogs - Downloader** - Fixed problems with installing a cog again after uninstalling (:issue:`2685`, :issue:`2690`)
- **Cogs - General** - Fixed ``[p]urban`` command failure for very long phrase definitions (:issue:`2683`, :issue:`2684`)
- **Cogs - General** - Fixed issues with ``[p]gif`` and ``[p]gifr`` commands. The bot owner now needs to provide an API key in order to use these commands (:issue:`2653`)
- **Cogs - Streams** - Fixed an issue with stream commands not properly dealing with stream reruns (:issue:`2679`)
- **Cogs - Streams** - Fixed a regression that caused stream alerts for non-Twitch users to not work anymore (:issue:`2724`, :issue:`2699`)


Developer changelog
-------------------

Additions
*********

- **Core - Bot Class** - Added `Red.send_to_owners()` and `Red.get_owner_notification_destinations()` (:issue:`2665`, :issue:`2738`)
- **Core - Commands Package** - Added `DictConverter` (:issue:`2692`)
- **Core - Commands Package** - Added `TimedeltaConverter` and `parse_timedelta()` (:issue:`2736`)
- **Core - Commands Package** - Added ``assume_yes`` attribute to `redbot.core.commands.Context` (:issue:`2746`)

Changes
*******

- **Core - Utils Package** - `menu()` now accepts `functools.partial` (:issue:`2718`, :issue:`2720`)

----

Redbot 3.1.1 (2019-05-15)
=========================

This is a hotfix release fixing issues related to fuzzy command search that were happening with the new help formatter.

----

Redbot 3.1.0 (2019-05-15)
=========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`aikaterna`, :ghuser:`bobloy`, :ghuser:`calebj`, :ghuser:`DiscordLiz`, :ghuser:`EgonSpengler`, :ghuser:`entchen66`, :ghuser:`FixedThink`, :ghuser:`Flame442`, :ghuser:`jack1142`, :ghuser:`kennnyshiwa`, :ghuser:`Kowlin`, :ghuser:`lionirdeadman`, :ghuser:`mikeshardmind`, :ghuser:`NeuroAssassin`, :ghuser:`NIXC`, :ghuser:`palmtree5`, :ghuser:`PredaaA`, :ghuser:`retke`, :ghuser:`Seputaes`, :ghuser:`Sitryk`, :ghuser:`tekulvw`, :ghuser:`Tobotimus`, :ghuser:`TrustyJAID`, :ghuser:`Twentysix26`, :ghuser:`zephyrkul`

End-user changelog
------------------

Known Issues
************

- **Core - Bot Commands** - Backup support for Mongo is currently broken (:issue:`2579`)

Additions
*********

- **Core - Bot Commands** - Added new ``[p]datapath`` command that prints the bot's data path (:issue:`2652`)
- **Core - Command-line Interfaces** - Added ``redbot-setup convert`` command which can be used to convert between data backends (:issue:`2579`)
- **Cogs - Audio** - Added Spotify support (:issue:`2328`)
- **Cogs - Audio** - ``[p]local folder`` now accepts folder name as (optional) argument (:issue:`2457`)
- **Cogs - Audio** - Added track length restriction (:issue:`2465`)
- **Cogs - Audio** - Added option for disconnection at queue end, see ``[p]audioset dc`` (:issue:`2472`)
- **Cogs - Audio** - Added ``[p]queue clean`` and ``[p]queue clear`` (:issue:`2476`)
- **Cogs - Audio** - Added ``[p]playlist download`` (:issue:`2482`)
- **Cogs - Mod** - Added the command ``[p]voicekick`` to kick members from a voice channel with optional modlog case (:issue:`2639`)
- **Cogs - Streams** - Added support for setting custom stream alert messages per server (:issue:`2600`)
- **Cogs - Streams** - Added ability to exclude Twitch stream reruns (:issue:`2620`)

Changes
*******

- **Core** - Error messages about cooldowns will now show more friendly representation of cooldown's expiration time (:issue:`2412`)
- **Core** - Cooldown messages are now auto-deleted after cooldown expiration expired (:issue:`2469`)
- **Core** - Updated Mongo driver to support large guilds (:issue:`2536`)
- **Core - Command-line Interfaces** - ``redbot --version`` will now give you current version of Red (:issue:`2567`)
- **Core - Help** - Redesigned help and its formatter (:issue:`2628`)
- **Cogs - Audio** - Changed ``[p]pause`` to a toggle (:issue:`2461`)
- **Cogs - Audio** - Removed command aliases (``dc``, ``np``, ``n``, ``song``, ``track``, ``q``, ``forceskip``, ``fs``, ``s``) (:issue:`2462`)
- **Cogs - Audio** - ``[p]seek`` command can now seek to position (:issue:`2470`)
- **Cogs - Audio** - Audio now matches Red V2 behavior for changing voice channels (:issue:`2521`)
- **Cogs - Downloader** - The ``[p]cog install`` command will not allow to install cogs which aren't suitable for installed version of Red anymore (:issue:`2605`)
- **Cogs - Downloader** - The ``[p]cog install`` command will now tell the user that cog has to be loaded after the install (:issue:`2523`)
- **Cogs - Downloader** - The ``[p]cog uninstall`` command allows to uninstall multiple cogs now (:issue:`2592`)
- **Cogs - Filter** - Significantly improved performance of Filter cog on large servers (:issue:`2509`)
- **Cogs - Mod** - Admins can now decide how many times message has to be repeated before cog's ``deleterepeats`` functionality removes it (:issue:`2437`)
- **Cogs - Permissions** - Removed ``[p]p`` alias for ``[p]permissions`` command (:issue:`2467`)
- **Cogs - Streams** - Twitch stream reruns are now marked as reruns in embed title (:issue:`2620`)

Removals
********

- **Cogs - DataConverter** - DataConverter has been completely removed from Red (:issue:`2554`)

Fixes
*****

- **Core - Bot Commands** - Fixed local blacklist/whitelist management commands (:issue:`2531`)
- **Core - Bot Commands** - ``[p]set locale`` now only accepts actual locales (:issue:`2553`)
- **Core - Bot Commands** - ``[p]listlocales`` now includes ``en-US`` locale (:issue:`2553`)
- **Core - Command-line Interfaces** - Fixed the list of available extras in the ``redbot-launcher`` (:issue:`2588`)
- **Core - i18n** - Changed default locale from ``en`` to ``en-US`` (:issue:`2642`)
- **Cogs - Audio** - Fixed ``[p]audioset status`` (:issue:`2481`)
- **Cogs - Audio** - Fixed an issue where queuing song from ``[p]search`` command did not do anything (:issue:`2513`)
- **Cogs - Audio** - Bot will no longer complain about permissions when trying to connect to user-limited channel, if it has "Move Members" permission (:issue:`2525`)
- **Cogs - Audio** - Fixed an issue on ``[p]audiostats`` command that occurred when there were more than 20 servers to display (:issue:`2533`)
- **Cogs - Audio** - Fixed the link shown by ``[p]prev`` command (:issue:`2556`)
- **Cogs - Audio** - Fixed an issue with ``[p]playlist queue`` that occurred when the bot was connected but wasn't playing anything (:issue:`2586`)
- **Cogs - Audio** - Fixed an issue with setting DJ role in ``[p]audioset dj`` command (:issue:`2606`)
- **Cogs - Downloader** - Fixed a bug that caused Downloader to include submodules on cog list (:issue:`2590`)
- **Cogs - Downloader** - The error message sent by ``[p]cog install`` when required libraries fail to install is now properly formatted (:issue:`2576`)
- **Cogs - Downloader** - The ``[p]cog uninstall`` command will now remove cog from installed cogs list even if it can't find the cog in install path anymore (:issue:`2595`)
- **Cogs - Mod** - Fixed ``[p]ban`` not allowing to omit ``days`` argument (:issue:`2602`)
- **Cogs - Trivia - Lists** - Fixed dead image link for Sao Tome and Principe flag in ``worldflags`` trivia (:issue:`2540`)


Developer changelog
-------------------

Breaking Changes
****************

- **Core - Config** - We now record custom group primary key lengths in the core config object (:issue:`2550`)
- **Cogs - Downloader** - Cog Developers now have to use ``min_bot_version`` key instead of ``bot_version`` to specify minimum version of Red supported by the cog in ``info.json``, see more information in :ref:`info-json-format` (:issue:`2605`)

Additions
*********

- **Core** - Added a ``on_message_without_command`` event that is dispatched when bot gets an event for a message that doesn't contain a command (:issue:`2338`)
- **Core - Config** - Introduced `Config.init_custom()` method (:issue:`2545`)
- **Core - Utils Package** - Added `chat_formatting.humanize_timedelta()` (:issue:`2412`)
- **Cogs - Downloader** - Added ``max_bot_version`` key to ``info.json`` that allows to specify maximum supported version of Red supported by the cog in ``info.json``, see more information in :ref:`info-json-format`. (:issue:`2605`)

Changes
*******

- **Core** - Usage of ``yaml.load`` will now warn about its security issues (:issue:`2326`)
- **Core - Config** - Migrated internal UUIDs to maintain cross platform consistency (:issue:`2604`)
- **Core - Utils Package** - Improved error handling of empty lists in `chat_formatting.humanize_list()` (:issue:`2597`)
- **Core - Dependencies** - Red is now no longer vendoring discord.py and installs it from PyPI (:issue:`2587`)
- **Core - Dependencies** - Upgraded discord.py dependency to version 1.0.1 (:issue:`2587`)

Fixes
*****

- **Core - Utils Package** - Fixed spelling of the `Tunnel`'s method from ``files_from_attatch()`` to `files_from_attach() <Tunnel.files_from_attach()>`; old name was left for backwards compatibility (:issue:`2496`)
- **Core - Utils Package** - Fixed behavior of ``Tunnel.react_close()`` - now when tunnel closes, the message will be sent to the other end (:issue:`2507`)

----

Redbot 3.0.2 (2019-02-24)
=========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`Tobotimus`, :ghuser:`ZeLarpMaster`

End-user changelog
------------------

Fixes
*****

- **Cogs - Permissions** - Fixed rules loading for cogs (`431cdf1 <https://github.com/Cog-Creators/Red-DiscordBot/commit/431cdf1ad4247fbe40f940e39bac4c919b470937>`__)
- **Cogs - Trivia - Lists** - Fixed a typo in ``cars`` trivia (:issue:`2475`)

----

Redbot 3.0.1 (2019-02-17)
=========================

| Thanks to all these amazing people that contributed to this release:
| :ghuser:`calebj`, :ghuser:`DiscordLiz`, :ghuser:`mikeshardmind`, :ghuser:`PredaaA`, :ghuser:`Redjumpman`, :ghuser:`Tobotimus`, :ghuser:`Twentysix26`, :ghuser:`ZeLarpMaster`, :ghuser:`zephyrkul`

End-user changelog
------------------

Changes
*******

- **Core - Bot Commands** - Improve some of the core commands to not require double quotes for arguments with spaces, if they're the last argument required by the command (:issue:`2407`)
- **Core - Bot Commands** - Using ``[p]load`` command now sends help message when it's used without arguments (:issue:`2432`)
- **Cogs - Downloader** - The ``[p]pipinstall`` command now sends help message when it's used without arguments (`eebed27 <https://github.com/Cog-Creators/Red-DiscordBot/commit/eebed27fe76aa5b51cfa38ac9a35bd182d881352>`__)
- **Cogs - Mod** - Usernames and nicknames listed in ``[p]names`` and ``[p]userinfo`` commands now have the spoiler markdown escaped (:issue:`2401`)
- **Cogs - Modlog** - Usernames listed in modlog cases now have the spoiler markdown escaped (:issue:`2401`)
- **Cogs - Warnings** - Members can now also be passed with username, nickname, or user mention to ``[p]warnings`` and ``[p]unwarn`` commands (:issue:`2403`, :issue:`2404`)

Fixes
*****

- **Core** - Messages sent interactively (i.e. prompting user whether they would like to view the next message) now no longer cause errors if bot's prompt message gets removed by other means (:issue:`2380`, :issue:`2447`)
- **Core - Bot Commands** - Fixed error in ``[p]servers`` command that was happening when bot's prompt message was deleted before the prompt time was over (:issue:`2400`)
- **Core - Command-line Interfaces** - Fixed behavior of CLI arguments in ``redbot-launcher`` (:issue:`2432`)
- **Cogs - Audio** - Fixed issues with setting external Lavalink (:issue:`2306`, :issue:`2460`)
- **Cogs - Audio** - Audio now cleans up zombie players from guilds it's no longer in (:issue:`2414`)
- **Cogs - Downloader** - Fixed issues with cloning that happened if instance's data path had spaces (:issue:`2421`)
- **Cogs - Mod** - ``[p]userinfo`` now accounts for guild's lurkers (:issue:`2406`, :issue:`2426`)
- **Cogs - Permissions** - Fixed rule precedence issues for default rules (:issue:`2313`, :issue:`2422`)


Developer changelog
-------------------

Additions
*********

- **Core - Utils Package** - Added `escape_spoilers()` and `escape_spoilers_and_mass_mentions()` methods for escaping strings with spoiler markdown (:issue:`2401`)

Fixes
*****

- **Core - Utils Package** - ``MessagePredicate.lower_contained_in()`` now actually lowers the message content before trying to match (:issue:`2399`)

----

Redbot 3.0.0 (2019-01-28)
=========================

First stable release of Red V3.
Changelogs for this and previous versions can be found on `our GitHub releases page <https://github.com/Cog-Creators/Red-DiscordBot/releases?after=3.0.1>`__.
