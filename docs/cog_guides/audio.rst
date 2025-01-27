.. _audio:

=====
Audio
=====

This is the cog guide for the audio cog. You will
find detailed docs about usage and commands.

``[p]`` is considered as your prefix.

.. note:: To use this cog, load it by typing this::

    	[p]load audio


You can see additional help for any command in this guide by using ``[p]help`` with the
command name, like ``[p]help playlist append``.

In this guide, you will see references to "Lavalink" or the "Lavalink.jar". `Lavalink <https://github.com/lavalink-devs/Lavalink/>`_ is the
Java-based audio backend we use to be able to play music through the bot. Most users will
not have to worry much about Lavalink or what it is, as Audio manages this process for you
by default. Advanced users can read more about Lavalink and special cases under the 
:ref:`Lavalink - Red Community-Supported Advanced Usage<advanced-usage>` section below.

You will also see references to ``managed`` or ``unmanaged`` in regards to the Lavalink.jar.
The default is ``managed``, as Audio manages the Lavalink.jar in this state. If it is run as an
``unmanaged`` process, this means you as the bot owner will be managing the Lavalink process yourself.

When the Audio cog is first loaded, it will contact GitHub and download the newest Lavalink.jar file
for your bot to use. Any time Red is updated and you update your bot, it will probably download a new,
updated Lavalink.jar for your bot. It is important to keep your bot updated as fixes are provided for Lavalink frequently.

.. warning::
    
    All commands should be used in a Discord server, and not in Direct Messages as Audio is not available there.

.. _basic-audio-use:

----------------
Basic Audio Use
----------------

The following commands are used for controlling the audio being played, such as starting, stopping, and altering volume.

* ``[p]play`` - Play a single song or a playlist URL or use this command with words to search for a song.
* ``[p]search`` - Search for a track on YouTube. Searching on Soundcloud can be done with ``[p]search sc`` and the keywords to search for.
* ``[p]stop`` - Stops playback and clears the queue.
* ``[p]pause`` - This is a toggle. Use ``[p]pause`` again to resume the music.
* ``[p]prev`` - Stops playback of the current song and returns to the start of the previous song played.
* ``[p]skip`` - Skip to the next song in the queue, if there is one.
* ``[p]seek`` - Seek ahead to a specific track time, or seek ahead by seconds.
* ``[p]now`` - Show what song is currently playing.
* ``[p]volume`` - Set the volume from 0% to 150%. 100% is the default. Discord server owners can set a limit to the volume with ``[p]audioset maxvolume``.

.. note::

	The following services are currently supported through ``[p]play``:

	* Bandcamp
	* HTTPS Icecast Streams
	* HTTPS Shoutcast Streams
	* Local file playback (:ref:`see here<local-tracks>`)
	* SoundCloud
	* Spotify links via YouTube (:ref:`see here<spotify-playback-and-api-keys>`)
	* Twitch
	* Vimeo
	* YouTube
	* Other AAC, MP3, or OGG-encoded streams

.. note::

	``[p]audioset restrict`` is a toggle that only allows commercial site (YouTube, Soundcloud, etc) playback by default.
	When toggled off, users will be able to play songs from HTTPS streams or arbitrary sites, but this could be a
	security issue as your bot's IP address will be sent to any site it's connecting to, per standard internet protocol.

.. _faq:

--------------------------
Frequently Asked Questions
--------------------------

**Q: I used a playlist link with some of the playlist related commands and it tells me that it can't find it. 
How can I use this playlist link with playlist commands in audio?**

	Audio uses Red playlists in its commands that take playlist arguments. 
	These playlists can be created and modified using the ``[p]playlist`` group command.
	When a playlist or song(s) are saved as a Red playlist, it is assigned an ID automatically,
	and it is also assigned the one-word name you provided it when creating the playlist.
	Either one of these identifiers can be used with playlist-related commands.

    .. tip::

        If you have a playlist URL, use ``[p]playlist save <url>`` to save it as a Playlist
        with Audio.

**Q: How do I turn off autoplay?**

	Use the ``[p]audioset autoplay toggle`` command.

**Q: How do I get the bot to disconnect from the channel when it's done playing?**

	``[p]audioset dc`` will make the bot auto-disconnect when playback completes and the 
	queue is empty. 
	``[p]audioset emptydisconnect`` with a seconds argument greater than 0 will make the bot 
	auto-disconnect once it's alone in the channel, after the amount of seconds given to the 
	command. This setting takes precedence over ``[p]audioset dc`` if both settings are active.

**Q: How do I use localtracks?**

	See the :ref:`local tracks section<local-tracks>`.
    
**Q: My console is saying that "Port 2333 is already in use". How can I fix this?**

    If you are trying to run multiple bots with Audio, you should follow our guide on
    :ref:`setting up Audio for multiple bots<multibots>`. Otherwise, another process is using the 
    port, so you need to figure out what is using port 2333 and terminate/disconnect it yourself.
    
**Q: My terminal is saying that I "must install Java 17 or 11 for Lavalink to run". How can I fix this?**

    You are getting this error because you have a different version of Java installed, or you don't have
    Java installed at all. As the error states, Java 17 or 11 is required, and can be installed from
    `here <https://adoptium.net/temurin/releases/?version=17>`__.
    
    If you have Java 17 or 11 installed, and are still getting this error, you will have to manually tell Audio where your Java install is located.
    Use ``[p]llset java <path_to_java_17_or_11_executable>``, to make Audio launch Lavalink with a
    specific Java binary. To do this, you will need to locate your ``java.exe``/``java`` file
    in your **Java 17 or 11 install**.
    
    Alternatively, update your PATH settings so that Java 17 or 11 is the one used by ``java``. However,
    you should confirm that nothing other than Red is running on the machine that requires Java.

.. _queue_commands:

----------------------
Queue Related Commands
----------------------

* ``[p]queue`` - Shows the queue of playing songs and current settings for the server for shuffle and repeat.
* ``[p]remove`` - Remove a song from the queue. This command uses the track position in the queue for identification, e.g. ``[p]remove 10`` will remove
  the 10th song in the queue.
* ``[p]shuffle`` - Toggle random song playback from the queue.
* ``[p]queue shuffle`` - Shuffles the queue.
* ``[p]repeat`` - Toggle adding songs back into the queue when they are finished playing.
* ``[p]playlist queue`` - Save the current queue to a Red playlist.
* ``[p]audioset persistqueue`` - Can be used to reinstate existing queues when the bot is restarted. This is an owner-only command.
* ``[p]audioset globaldailyqueue`` - Will toggle saving the day's worth of tracks to a Global-level Red playlist, for every day. This is an owner-only command.

.. _playlist_commands:

-----------------
Playlist Commands
-----------------

Playlists can be saved locally on the bot in a variety of different scopes:

* Global - The playlist will be available on all servers.
* Guild (default scope) - The playlist will be available only in a specified guild.
* User - The playlist will be available in any guild that the user shares with the bot.

Some of the most relevant playlist commands include:

* ``[p]playlist append`` - Add a track URL, playlist link, or quick search to a playlist.
* ``[p]playlist create`` - Creates an empty playlist.
* ``[p]playlist delete`` - Delete a saved playlist.
* ``[p]playlist info`` - Retrieve information about a saved playlist.
* ``[p]playlist list`` - List saved playlists.
* ``[p]playlist queue`` - Save the currently playing queue to a playlist.
* ``[p]playlist remove`` - Remove a track from a playlist by URL.

As always, you can run ``[p]help playlist <command>`` for more information.

.. _owner-audioset-commands:

----------------------------
Owner-Only Audioset Commands
----------------------------

* ``[p]audioset cache`` - This sets the local metadata caching level for Audio. By default, this is set to on as it helps
  reduce 429 Forbidden errors from song services, and also caches Spotify song lookups. Most users will not need to touch this option.
* ``[p]audioset cacheage`` - How long the entries in the cache last. By default, song metadata is cached for 365 days (1 year).
* ``[p]audioset status`` - Show the now playing song in the bot's status, or show how many servers the bot is playing music on, if more than one.
* ``[p]audioset restrictions global`` - Manage the keyword blocklist/allowlist for the whole bot.

.. _guild-audioset-commands:

-----------------------------
Guild-based Audioset Commands
-----------------------------

* ``[p]audioset notify`` - Toggle extra messages: Audio will display a notification message when a track starts, 
  showing the song title, artist, and the thumbnail (if enabled and present). This notify message follows the last 
  invoking Audio command - if an Audio command is used in one channel and this setting is on, the notify messages
  will start to appear in the channel where the command was used. If another Audio command is used in another 
  channel, notify messages will start appearing in the second channel instead of the first command channel.
* ``[p]audioset maxvolume`` - Set the max volume for the guild.
* ``[p]audioset autodeafen`` - Toggle the bot being auto-deafened upon voice channel join.
* ``[p]audioset restrictions`` - Manage the keyword blocklist/allowlist for the guild.
* ``[p]audioset lyrics`` - Searching for tracks will prefer songs with 'lyrics' in the name, to avoid videos with long story intros or outros.

.. _spotify-playback-and-api-keys:

------------------------------
Spotify Playback and API Keys
------------------------------

We will never be able to play directly from Spotify itself as it is against their Terms of Service. Audio can play 
single tracks or playlists from Spotify by looking up the song(s) on YouTube and playing those tracks instead.
This is possible by providing your bot with a YouTube API key and a Spotify API key. Instructions for setting both 
can be found under ``[p]audioset youtubeapi`` and ``[p]audioset spotifyapi``.

The YouTube API keys that are being given out currently only have 10000 units of quota per day, which is equivalent to
100 Spotify song lookups. There is a local metadata cache that Audio uses to be able to retain information about song
lookups. For example, with a 500 song Spotify playlist, the bot will be able to fetch the first 100 songs the
first day the Spotify playlist URL is used with Audio, then the next day it will be able to use the first 100 lookups
from the local cache, and use the API credits to look up the next 100 songs. After 5 days of playing the Spotify playlist
through Audio, that playlist will be fully cached locally until the cached entries are set to expire and will not require  
any API credits to play songs.

The following commands are relevant:

* ``[p]genre`` - Lets users pick a Spotify music genre to queue music from.
* ``[p]audioset countrycode`` - Lets guild owners specify what country code to prefer for Spotify searches, for the guild.
* ``[p]audioset mycountrycode`` - Lets individual users pick what country code to prefer for Spotify searches of their own.

.. _local-tracks:

------------
Local Tracks
------------

Audio can play music from a ``localtracks`` folder on the device where the bot is hosted. This feature is only available
if your bot and your Lavalink.jar are on the same host, which is the default setup.

To use this feature:

1. Create a "localtracks" folder anywhere where Lavalink/your bot user has permissions to access, on the system.
2. Use ``[p]audioset localpath <localtracks path>`` to set the folder created above as the localtracks folder.
3. Create/move/copy/symlink your album folders (Subfolders containing your tracks) to the folder created in Step 1.
4. Put any of Audio's supported files in the following folders:

   * ``localtracks/<parent folder>/song.mp3``
   * ``localtracks/<parent folder>/<child folder>/song.mp3``

When using this localtracks feature, use ``[p]local`` commands. Use ``[p]play <parent folder>/song.mp3`` to play
single songs. Use ``[p]local folder <parent folder>/<child folder>`` to play the entire folder.

The following formats are supported:

* MP3
* FLAC
* Matroska/WebM (AAC, Opus or Vorbis codecs)
* MP4/M4A (AAC codec)
* OGG streams (Opus, Vorbis and FLAC codecs)
* AAC streams

The following files are partially supported:

* .ra
* .wav
* .opus
* .wma
* .ts
* .au
* .mov
* .flv
* .mkv
* .wmv
* .3gp
* .m4v
* .mk3d
* .mka
* .mks

The following files are **NOT** supported:

* .mid
* .mka
* .amr
* .aiff
* .ac3
* .voc
* .dsf
* .vob
* .mts
* .avi
* .mpg
* .mpeg
* .swf

.. _dj-role-and-voteskip:

--------------------
DJ Role and Voteskip
--------------------

Audio has an internal permissions system for restrictions to audio commands while other people are listening to
music with the bot. Bot owners, server admins and mods bypass these restrictions when they are in use.

``[p]audioset dj`` will turn on the DJ role restriction system, ``[p]audioset role`` will let you choose or
reassign the DJ role, and if you wish to make non-privileged users vote to skip songs, voteskip can be enabled
with ``[p]audioset vote``.

If a non-privileged user is listening to music alone in the channel, they can use commands without restrictions,
even if DJ role or voteskip settings are active.

.. _sound-quality-issues:

--------------------
Sound Quality Issues
--------------------

Laggy audio is most likely caused by:

* A problem with the connection between the machine that is hosting Lavalink and the Discord voice server.
* Issues with Discord.

You can try the following to resolve poor sound quality:

* Don't host on home internet, especially over a WiFi connection. Try hosting your bot elsewhere.
* Try the web browser instead of the desktop client for listening.
* Simply wait, as audio quality may improve in due course.
* Restart your bot.
* Check to make sure it's not just a bad quality song (try a different song).
* Try to listen on a different Discord server or server region.
* If not everyone is experiencing the issue, it's a Discord client issue.

.. _no-sound:

^^^^^^^^
No Sound
^^^^^^^^

If the bot's speaking light is active, but there is no sound, troubleshoot the following:

1. Is the bot's user volume turned up? (right click on the bot in Discord, see the slider).
2. Is the bot muted or deafened? Are you deafened? Are you deaf?
3. Check Discord audio device settings and volume (cog icon next to your username in the bottom left, click "Voice and Video").
4. Try dragging and dropping the bot back to the voice channel.
5. Check system audio device settings and volume.
6. Ask another member to come into the voice channel to confirm that it's not just you.

If the track progress is stuck on 00:00 when you run ``[p]now``:

1. Try to run ``[p]disconnect`` and replay the song.
2. Try to reload the audio cog with ``[p]audioset restart``.
3. Make sure the firewall on the host is configured properly.

.. _advanced-usage:

-------------------------------------------------
Lavalink - Red Community-Supported Advanced Usage
-------------------------------------------------

.. _multibots:

^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Setting up Multiple Red Instances with Audio on the Same Host
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. warning::

    This section provides instructions for setting up an unmanaged Lavalink node that is on the same machine 
    as the Red bot(s) that need to connect to it. This configuration is supported by the Red community, so 
    if you need additional help, feel free to join the `Red Support Server <https://discord.gg/red>`__ and ask in the #support channel.

    If you are looking to set up a remote, unmanaged Lavalink node on a different vps or host than the Red 
    bot(s) that will connect to it, we provide basic instructions in this guide :ref:`here<remote-lavalink>`, but that 
    configuration is partially unsupported as we do not provide help with network configuration or system 
    administration. You will be responsible for configuring your network, firewall, and other system 
    properties to enable playback and for the bot to connect to the remote unmanaged Lavalink server.

If you are wanting to use multiple bots with Audio on the same machine, you'll need to make a few
necessary modifications.

Firstly, stop all Red bots. For each bot using Audio:

1. Start the bot.
2. Run the command ``[p]llset unmanaged``.
3. Stop the bot.

Next, open a command prompt/terminal window. Navigate to ``<datapath>/cogs/Audio`` for any of your bot
instances - it doesn't matter which bot as all your bots will now use this single instance of Lavalink.
You can find your ``<datapath>`` with the ``[p]datapath`` command.

Now you need to determine your RAM needs. If your bot has 1GB RAM available, Lavalink should be restricted 
to perhaps 384MB -> 768MB, depending on the cogs you have installed. If your bot has 2GB of RAM available, 
a good amount may be 512MB -> 1GB. 

Run the following command, where ``Xmx`` specifies the RAM value you have just determined. The MB suffix 
is M and the GB suffix is G.

.. code-block:: ini

	java -jar -Xmx768M Lavalink.jar -Djdk.tls.client.protocols=TLSv1.2

Leave this command prompt/terminal window open (you will need to do this every time you want to start Lavalink
for your bots). Once Lavalink says it has fully started, you can start your bots back up.

.. note::

	If you are on Linux, this process can be automated using systemd, for unmanaged
	Lavalink backends **only**. See :ref:`here<linux-audio-autorestart>` for details.

.. warning::

	By running multiple bots that use Audio, the responsibility for keeping the Lavalink.jar updated will now be
	in your hands, as Red will no longer manage it through the Audio cog. See :ref:`here<obtaining-the-latest-lavalink>` for guidance.

.. _linux-audio-autorestart:

^^^^^^^^^^^^^^^^^^^^^^^^^^^
Linux Lavalink Auto-Restart
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Auto-restarting Lavalink is possible on Linux with systemd, for unmanaged Lavalink backends.

Firstly, find out what your datapath is with the ``[p]datapath`` command. Your Lavalink path is
``<datapath>/cogs/Audio``. Create a file named ``auto_update.sh`` in your Lavalink path.

Inside this newly created file, paste the following text:

.. code-block:: sh

	curl -LOz Lavalink.jar https://github.com/Cog-Creators/Lavalink-Jars/releases/latest/download/Lavalink.jar

Run the following, replacing ``<Lavalink path>`` with the Lavalink path you generated earlier (``<datapath>/cogs/Audio``).

.. code-block:: sh

	chmod a+rx <Lavalink path>/auto_update.sh

Now we need to create a service file so that systemd can do its magic. Run the following command:

.. code-block:: sh

	sudo -e /etc/systemd/system/lavalink.service
	
Next, paste in the example below, but replacing the following:

* ``<Jar executable path>`` - You can find your Java path by running ``which java``.
* ``<Lavalink path>`` - The parent folder where your Lavalink executable can be located (usually in ``<datapath>/cogs/Audio``).
* ``<username>`` - Your username on the host machine (run ``echo $USER``).

.. code-block:: ini

	[Unit]  
	Description=lavalink  
	After=multi-user.target  

	[Service]
	ExecStart=<Java executable path> -Djdk.tls.client.protocols=TLSv1.2 -jar < Lavalink path >/Lavalink.jar
	WorkingDirectory=<Lavalink path>
	User=<username>
	Group=<username>
	ExecStartPre=/bin/bash <Lavalink path>/auto_update.sh # Comment this line out if you did not create the auto_update.sh
	Type=idle
	Restart=always
	RestartSec=15

	[Install]
	WantedBy=multi-user.target

Finally, we need to start and enable the service. Run the following commands, separately.

.. code-block:: sh
	
	sudo systemctl start lavalink
	sudo systemctl enable lavalink

These commands always need to be ran when starting the lavalink service to ensure that the
service runs in the background.

Finally, you can run the following to retrieve logs for the service, when you need them:

.. code-block:: sh
	
	sudo journalctl -u lavalink

.. _obtaining-the-latest-lavalink:

^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Obtaining the latest Lavalink.jar on a Red update
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**To manually download the jar**

Stop your bot. Download the Lavalink.jar file from `here <https://github.com/Cog-Creators/Lavalink-Jars/releases/latest>`__,
which could alternatively be downloaded by running the following command:

.. code-block:: sh
    
    curl -LOz Lavalink.jar https://github.com/Cog-Creators/Lavalink-Jars/releases/latest/download/Lavalink.jar

Next, stop all instances of Red running on the host, and stop the Lavalink process. Move the new Lavalink.jar
to where your old Lavalink.jar is located, overwriting the old file.

Finally, start up the new Lavalink.jar process via a process manager like systemd, or by running the following command:

.. code-block:: sh
    
    java -jar Lavalink.jar -Djdk.tls.client.protocols=TLSv1.2

Start up your bots, and now they will use the latest Lavalink.jar!

.. _remote-lavalink:

---------------------------------------------------------------
Setting up an unmanaged Lavalink node on a remote VPS or server
---------------------------------------------------------------

.. attention::

    We'd like to thank BreezeQS, as this guide is a supersession of their unofficial bare-bones guide.

This guide explains how to set up an unmanaged Lavalink node on a separate server running Ubuntu 20.04 LTS.
It is assumed your bot currently uses a managed Lavalink server (Red's default). 

.. warning::

    This guide is provided for advice on this topic and this is generally not a supported configuration for 
    Red's usage of Lavalink, as it involves system administration and network configuration. However, if you
    run into any issues, feel free to ask for help in the `Red Support Server <https://discord.gg/red>`__, in the #general channel.

.. warning::

    For security purposes DO NOT follow this guide while logged in as the root user. You should create
    a separate non-root user instead. You can follow
    `this guide <https://www.digitalocean.com/community/tutorials/how-to-create-a-new-sudo-enabled-user-on-ubuntu-20-04-quickstart>`__
    from DigitalOcean if you need help about how this is done.

^^^^^^^^^^^^^^^^^^^^^^^^^
Prerequisite Installation
^^^^^^^^^^^^^^^^^^^^^^^^^

We will first install Lavalink and lay the foundation for our finished server. There are some prerequisites
that must be installed on the server you aim to use for running Lavalink. To set those up, run each of the
following commands one by one.

.. code-block:: sh

    sudo apt update
    sudo apt upgrade -y
    sudo apt install curl nano -y

If you have no preference in which Java version you install on your target system, Red 
uses OpenJDK 17 in the managed Lavalink configuration. It can be installed by running:

.. code-block:: sh

    sudo apt install openjdk-17-jre-headless -y

Otherwise, Lavalink works well with most versions of Java 11, 13, 15, 16, 17, and 18. Azul 
Zulu builds are suggested, see `here <https://github.com/lavalink-devs/Lavalink/#requirements>`__ for more information.

^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Setting Up The Lavalink Folder
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Lavalink itself, its configuration, and its logs will all be kept in a single directory. In this guide,
we will simply call this directory lavalink and it will be located in the home directory of the user you
are logged in as.

We need to create a new directory called **lavalink**, and then switch to it as the upcoming sections of
this guide require your current directory to be the **lavalink** folder. We can achieve this by running
the following commands one by one:

.. code-block:: sh

    cd
    mkdir lavalink
    cd lavalink

^^^^^^^^^^^^^^^^^^^
Installing Lavalink
^^^^^^^^^^^^^^^^^^^

The Lavalink executable used in Red-Discordbot is slightly modified and is not the same as stock Lavalink,
it ensures proper operation when used with Red-Discordbot and compatibility with systems and libraries that
Red uses to operate. It's required to use this Lavalink.jar when running unmanaged Lavalink servers to not
void your privilege to receive support. Assuming your current directory is the lavalink folder as you ran
the ``cd lavalink`` command in the previous section, you can run the following commands one by one to install it:

.. code-block:: sh

    curl https://raw.githubusercontent.com/lavalink-devs/Lavalink/master/LavalinkServer/application.yml.example > application.yml
    curl -LOz Lavalink.jar https://github.com/Cog-Creators/Lavalink-Jars/releases/latest/download/Lavalink.jar

If you did it properly, the files ``Lavalink.jar`` and ``application.yml`` will show up when we run ``ls``, the Linux command
to list the contents of the current directory.

^^^^^^^^^^^^^^^^^^^^
Configuring Lavalink
^^^^^^^^^^^^^^^^^^^^

Lavalink stores its settings inside the ``application.yml`` file located in the same directory as the executable jar itself.
You have to edit this file and change some settings for security purposes.

First, let's open the file. You can use any text editor you want, but in this guide we will use nano.
Run the following command:

.. code-block:: sh
    
    nano application.yml

You will be dropped into the nano text editor with ``application.yml`` opened. The two important fields that we will modify
are the ``port`` and ``password`` fields.

The ``port`` field is the TCP port your Lavalink server will be accessible at. The default value is 2333, and you can set this
to any positive integer smaller than 65535 and greater than 1000. It is advised to change it to aid in security.

The ``password`` field is the password that will be required for accessing your Lavalink server and by default the password is
``youshallnotpass``. You should absolutely change this to a secure password.

Those two fields are important and you should take note of the new values you entered, as
they will be later required to connect your bot to the Lavalink server.

At the bottom of the screen, the nano text editor displays some keys that can be used to carry out various tasks.
In this case, we want to save and exit. Keys prefixed with the caret (^) sign means they are used in conjunction
with the ctrl key. So we press Ctrl+X to exit.

Nano will ask if you want to save the changes that were made. Answer with ``y`` and hit enter to exit.

^^^^^^^^^^^^^^^^^
Starting Lavalink
^^^^^^^^^^^^^^^^^

Now that Lavalink has been installed and configured, we can start it up. To do so, run the following command, making sure
that you are inside the lavalink folder, of course:

.. code-block:: sh
    
    java -Djdk.tls.client.protocols=TLSv1.2 -jar Lavalink.jar

On successful start, Lavalink will greet you with a line mentioning that it is ready to accept connections and you can now
try connecting to it with your bot. 

Since we did not configure autostart for Lavalink, you will have to keep the console window open or it will be shut down
and all connections will be dropped. This is similar to how it happens in Red-Discordbot itself.

This also means that you will have to restart Lavalink manually each time you log on. This is often done in testing environments.
You can restart Lavalink manually by running the following commands one by one:

.. code-block:: sh

    cd
    cd lavalink
    java -Djdk.tls.client.protocols=TLSv1.2 -jar Lavalink.jar

You can stop Lavalink and reclaim the console by hitting ``CTRL+C``.

^^^^^^^^^^^^^^^^^
Updating Lavalink
^^^^^^^^^^^^^^^^^

With new releases of Red-Discordbot, sometimes new Lavalink jars are also released. Using an obsolete version of Lavalink
with newer versions of Red-Discordbot can cause all sorts of problems.

Normally, users do not have to worry about this as when Red-Discordbot is configured to use a managed Lavalink server
(the default setting) Lavalink is automatically updated when a new release comes out.

However, since you are running a Lavalink instance yourself you are responsible for keeping it up to date.
When a new release of Red-Discordbot also requires a update to the Lavalink jar, you will be informed in the changelogs
posted in our documentation.

When a new Lavalink.jar comes out, you can easily update the existing one. First, you should stop Lavalink if it's currently
running. Once you have done this, you can follow the instructions on how to :ref:`obtain the latest Lavalink.jar on a Red update<obtaining-the-latest-lavalink>`.

In the next section we will see how you can configure Lavalink to automatically update, automatically start, and run as
a background process which is much more convenient for non-testing deployments.

^^^^^^^^^^^^^^^^^^^^^^
Setting up Auto Update
^^^^^^^^^^^^^^^^^^^^^^

As previously covered, running Lavalink in a simple terminal session is fragile. Not only does it need you to manually
intervene each time you login, reboot, or just have to restart Lavalink for any reason you also have to update it manually
when a new Lavalink jar comes out.

First of all, we will configure a script for updating Lavalink that runs before each time Lavalink starts. This step is
highly recommended. But if you know what you are doing, you can skip it if you want to update Lavalink manually.

First, run the following commands:

.. code-block:: sh
    
    cd
    cd lavalink
    nano auto_update.sh

You'll see that running nano has opened a file. Paste the following code into the file:

.. code-block:: sh

    #!/bin/sh
    curl -LOz Lavalink.jar https://github.com/Cog-Creators/Lavalink-Jars/releases/latest/download/Lavalink.jar

Now save the file and exit (``CTRL+X``, then ``y``).

Now, run the following command, which will make the script possible to run:

.. code-block:: sh
    
    chmod a+rx auto_update.sh
    
If you did it right, the command itself will not output anything. And when running ``ls``, the script will show up in green.

""""""""""""""""""""""""""""""
Setting Up the Systemd Service
""""""""""""""""""""""""""""""

We will now register Lavalink as a system service, allowing it to run in the background without user intervention.
But before that, we need to gather some information. While in the lavalink folder, run the following commands one by one
and note their output somewhere, because we will need them:

.. code-block:: sh

    pwd
    which java
    echo "$USER"

Now run the following command:

.. code-block:: sh

    sudo -e /etc/systemd/system/lavalink.service

On new systems it may ask for a choice of editor. Nano is the best choice. To select it, press 1 and hit enter.
The nano text editor will now open. Now copy and paste the following text into it:

.. code-block:: ini

    [Unit]
    Description=lavalink
    After=multi-user.target

    [Service]
    ExecStart=< Java executable path > -Djdk.tls.client.protocols=TLSv1.2 -jar < Lavalink path >/Lavalink.jar
    WorkingDirectory=< Lavalink path >
    User=< username >
    Group=< username >
    ExecStartPre=/bin/bash < Lavalink path >/auto_update.sh # Comment this line out if you did not create the auto_update.sh
    Type=idle
    Restart=always
    RestartSec=15

    [Install]
    WantedBy=multi-user.target

* Replace all occurrences of ``< Lavalink path >`` with the output of ``pwd`` you noted earlier.
* Replace all occurrences of ``< Java executable path >`` with the output of ``which java`` you noted earlier.
* Replace all occurrences of ``< username >`` with the output of echo ``"$USER"`` you noted earlier.

Hit ``CTRL+X``, ``y`` and then ENTER to save and exit. We have now registered Lavalink as a service.

""""""""""""""""""""""""""""""""""""""""""
Starting and Enabling the Lavalink Service
""""""""""""""""""""""""""""""""""""""""""

Now run the following command to start the Lavalink service and wait for 10-15 seconds: 

.. code-block:: sh
    
    sudo systemctl start lavalink

You can check the service status with the following command:

.. code-block:: sh
    
    sudo journalctl -u lavalink

Keep in mind this will occupy your terminal and you have to hit CTRL+C to stop it before doing something else.
This will only close the log viewer, Lavalink itself will continue to run in the background.

You may now run the following to make Lavalink auto-restart each boot:

.. code-block:: sh

    sudo systemctl enable lavalink

.. tip::

    You can stop the Lavalink service with the following when you need to e.g. for troubleshooting:

    .. code-block:: sh

        sudo systemctl stop lavalink

    You can also check the logs Lavalink persists by checking the ``spring.log`` file in the ``lavalink/logs/`` folder.

Congratulations, you are almost ready.

^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Connecting to Your New Lavalink Server
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If your Red instance and Lavalink server will communicate over the Internet, make sure the Lavalink port is accessible
from the internet. Click `here <https://www.yougetsignal.com/tools/open-ports/>`__ and test if the port you set in the ``application.yml``
is accessible on the public ip address of your Lavalink server. This step isn't necessary if your Lavalink server and Red
instance will communicate over LAN. If you get connectivity errors, make sure there are no firewalls blocking the port and
you are using the correct port.

If successful, run each of the following commands one by one on your bot. Replace ``"yourlavalinkip"`` with the ip of your Lavalink server.
Change ``"port"`` with the port you set up in the application.yml. Change ``"password"`` with the password you set up in the application.yml.
Do not use quotes in these commands. For example, ``[p]llset host 192.168.10.101`` or ``[p]llset password ahyesverysecure``.

.. code-block:: none

    [p]llset unmanaged
    [p]llset host "yourlavalinkip"
    [p]llset port "port"
    [p]llset password "password"

Reload audio with ``[p]reload audio`` and give it a few seconds to connect.

You now (hopefully) have a functioning Lavalink server on a machine separate to the one running your Red instance. Good luck!

.. _audio-commands:

--------
Commands
--------

.. _audio-command-audioset:

^^^^^^^^
audioset
^^^^^^^^

**Syntax**

.. code-block:: none

    [p]audioset 

**Description**

Music configuration options.

.. _audio-command-audioset-autodeafen:

"""""""""""""""""""
audioset autodeafen
"""""""""""""""""""

.. note:: |mod-lock|

**Syntax**

.. code-block:: none

    [p]audioset autodeafen 

**Description**

Toggle whether the bot will be auto deafened upon joining the voice channel.

.. _audio-command-audioset-autoplay:

"""""""""""""""""
audioset autoplay
"""""""""""""""""

.. note:: |mod-lock|

**Syntax**

.. code-block:: none

    [p]audioset autoplay 

**Description**

Change auto-play setting.

.. _audio-command-audioset-autoplay-playlist:

""""""""""""""""""""""""""
audioset autoplay playlist
""""""""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]audioset autoplay playlist <playlist_name_OR_id> [args]

**Description**

Set a playlist to auto-play songs from.

**Args**

The following are all optional:

* --scope <scope>
* --author [user]
* --guild [guild] (**only the bot owner can use this**)

**Scope** is one of the following:

* Global
* Guild
* User

**Author** can be one of the following:

* User ID
* User Mention
* User Name#123

**Guild** can be one of the following:

* Guild ID
* Exact guild name

**Example Usage**

* ``[p]audioset autoplay playlist MyGuildPlaylist``
* ``[p]audioset autoplay playlist MyGlobalPlaylist --scope Global``
* ``[p]audioset autoplay playlist PersonalPlaylist --scope User --author Draper``

.. _audio-command-audioset-autoplay-reset:

"""""""""""""""""""""""
audioset autoplay reset
"""""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]audioset autoplay reset 

**Description**

Resets auto-play to the default playlist.

.. _audio-command-audioset-autoplay-toggle:

""""""""""""""""""""""""
audioset autoplay toggle
""""""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]audioset autoplay toggle 

**Description**

Toggle auto-play when there are no songs in the queue.

.. _audio-command-audioset-cache:

""""""""""""""
audioset cache
""""""""""""""

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]audioset cache [level]

**Description**

Sets the caching level.

Level can be one of the following:

* ``0``: Disables all caching
* ``1``: Enables Spotify Cache
* ``2``: Enables YouTube Cache
* ``3``: Enables Lavalink Cache
* ``5``: Enables all Caches

If you wish to disable a specific cache use a negative number.

.. _audio-command-audioset-cacheage:

"""""""""""""""""
audioset cacheage
"""""""""""""""""

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]audioset cacheage <age>

**Description**

Sets the cache max age. This commands allows you to set the max number of
days before an entry in the cache becomes invalid.

.. _audio-command-audioset-countrycode:

""""""""""""""""""""
audioset countrycode
""""""""""""""""""""

.. note:: |mod-lock|

**Syntax**

.. code-block:: none

    [p]audioset countrycode <country>

**Description**

Set the country code for Spotify searches.

.. _audio-command-audioset-dailyqueue:

"""""""""""""""""""
audioset dailyqueue
"""""""""""""""""""

.. note:: |admin-lock|

**Syntax**

.. code-block:: none

    [p]audioset dailyqueue 

**Description**

Toggle daily queues. Daily queues creates a playlist for all tracks played today.

.. _audio-command-audioset-dc:

"""""""""""
audioset dc
"""""""""""

.. note:: |mod-lock|

**Syntax**

.. code-block:: none

    [p]audioset dc 

**Description**

Toggle the bot auto-disconnecting when done playing. This setting takes precedence
over ``[p]audioset emptydisconnect``.

.. _audio-command-audioset-dj:

"""""""""""
audioset dj
"""""""""""

.. note:: |admin-lock|

**Syntax**

.. code-block:: none

    [p]audioset dj 

**Description**

Toggle DJ mode. DJ mode allows users with the DJ role to use audio commands.

.. _audio-command-audioset-emptydisconnect:

""""""""""""""""""""""""
audioset emptydisconnect
""""""""""""""""""""""""

.. note:: |mod-lock|

**Syntax**

.. code-block:: none

    [p]audioset emptydisconnect <seconds>

**Description**

Auto-disconnect from channel when bot is alone in it for x seconds, 0 to disable.
``[p]audioset dc`` takes precedence over this setting.

.. _audio-command-audioset-emptypause:

"""""""""""""""""""
audioset emptypause
"""""""""""""""""""

.. note:: |mod-lock|

**Syntax**

.. code-block:: none

    [p]audioset emptypause <seconds>

**Description**

Auto-pause after x seconds when the channel is empty, 0 to disable.

.. _audio-command-audioset-globaldailyqueue:

"""""""""""""""""""""""""
audioset globaldailyqueue
"""""""""""""""""""""""""

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]audioset globaldailyqueue 

**Description**

Toggle global daily queues. Global daily queues creates a playlist
for all tracks played today.

.. _audio-command-audioset-jukebox:

""""""""""""""""
audioset jukebox
""""""""""""""""

.. note:: |mod-lock|

**Syntax**

.. code-block:: none

    [p]audioset jukebox <price>

**Description**

Set a price for queueing tracks for non-mods, 0 to disable.

.. _audio-command-audioset-localpath:

""""""""""""""""""
audioset localpath
""""""""""""""""""

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]audioset localpath [local_path]

**Description**

Set the localtracks path if the Lavalink.jar is not run from the Audio data folder.
Leave the path blank to reset the path to the default, the Audio data directory.

.. _audio-command-audioset-logs:

"""""""""""""
audioset logs
"""""""""""""

.. note:: |owner-lock|

.. note::

    This command is only available for managed Lavalink servers.

**Syntax**

.. code-block:: none

    [p]audioset logs 

**Description**

Sends the Lavalink server logs to your DMs.

.. _audio-command-audioset-lyrics:

"""""""""""""""
audioset lyrics
"""""""""""""""

.. note:: |mod-lock|

**Syntax**

.. code-block:: none

    [p]audioset lyrics 

**Description**

Prioritise tracks with lyrics.

.. _audio-command-audioset-maxlength:

""""""""""""""""""
audioset maxlength
""""""""""""""""""

.. note:: |mod-lock|

**Syntax**

.. code-block:: none

    [p]audioset maxlength <seconds>

**Description**

Max length of a track to queue in seconds, 0 to disable. Accepts seconds or a value
formatted like 00:00:00 (``hh:mm:ss``) or 00:00 (``mm:ss``). Invalid input will turn
the max length setting off.

.. _audio-command-audioset-maxvolume:

""""""""""""""""""
audioset maxvolume
""""""""""""""""""

.. note:: |admin-lock|

**Syntax**

.. code-block:: none

    [p]audioset maxvolume <maximum volume>

**Description**

Set the maximum volume allowed in this server.

.. _audio-command-audioset-mycountrycode:

""""""""""""""""""""""
audioset mycountrycode
""""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]audioset mycountrycode <country>

**Description**

Set the country code for Spotify searches.

.. _audio-command-audioset-notify:

"""""""""""""""
audioset notify
"""""""""""""""

.. note:: |mod-lock|

**Syntax**

.. code-block:: none

    [p]audioset notify 

**Description**

Toggle track announcement and other bot messages.

.. _audio-command-audioset-persistqueue:

"""""""""""""""""""""
audioset persistqueue
"""""""""""""""""""""

.. note:: |admin-lock|

**Syntax**

.. code-block:: none

    [p]audioset persistqueue 

**Description**

Toggle persistent queues. Persistent queues allows the current queue
to be restored when the queue closes.

.. _audio-command-audioset-restart:

""""""""""""""""
audioset restart
""""""""""""""""

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]audioset restart 

**Description**

Restarts the lavalink connection.

.. _audio-command-audioset-restrict:

"""""""""""""""""
audioset restrict
"""""""""""""""""

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]audioset restrict 

**Description**

Toggle the domain restriction on Audio.

When toggled off, users will be able to play songs from non-commercial websites and links.
When toggled on, users are restricted to YouTube, SoundCloud, Vimeo, Twitch, and
Bandcamp links.

.. _audio-command-audioset-restrictions:

"""""""""""""""""""""
audioset restrictions
"""""""""""""""""""""

.. note:: |mod-lock|

**Syntax**

.. code-block:: none

    [p]audioset restrictions 

**Description**

Manages the keyword whitelist and blacklist.

.. _audio-command-audioset-restrictions-blacklist:

"""""""""""""""""""""""""""""""
audioset restrictions blacklist
"""""""""""""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]audioset restrictions blacklist 

**Description**

Manages the keyword blacklist.

.. _audio-command-audioset-restrictions-blacklist-add:

"""""""""""""""""""""""""""""""""""
audioset restrictions blacklist add
"""""""""""""""""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]audioset restrictions blacklist add <keyword>

**Description**

Adds a keyword to the blacklist.

.. _audio-command-audioset-restrictions-blacklist-clear:

"""""""""""""""""""""""""""""""""""""
audioset restrictions blacklist clear
"""""""""""""""""""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]audioset restrictions blacklist clear 

**Description**

Clear all keywords added to the blacklist.

.. _audio-command-audioset-restrictions-blacklist-delete:

""""""""""""""""""""""""""""""""""""""
audioset restrictions blacklist delete
""""""""""""""""""""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]audioset restrictions blacklist delete <keyword>

**Description**

Removes a keyword from the blacklist.

.. _audio-command-audioset-restrictions-blacklist-list:

""""""""""""""""""""""""""""""""""""
audioset restrictions blacklist list
""""""""""""""""""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]audioset restrictions blacklist list 

**Description**

List all keywords added to the blacklist.

.. _audio-command-audioset-restrictions-global:

""""""""""""""""""""""""""""
audioset restrictions global
""""""""""""""""""""""""""""

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]audioset restrictions global 

**Description**

Manages the global keyword whitelist/blacklist.

.. _audio-command-audioset-restrictions-global-blacklist:

""""""""""""""""""""""""""""""""""""""
audioset restrictions global blacklist
""""""""""""""""""""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]audioset restrictions global blacklist 

**Description**

Manages the global keyword blacklist.

.. _audio-command-audioset-restrictions-global-blacklist-add:

""""""""""""""""""""""""""""""""""""""""""
audioset restrictions global blacklist add
""""""""""""""""""""""""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]audioset restrictions global blacklist add <keyword>

**Description**

Adds a keyword to the blacklist.

.. _audio-command-audioset-restrictions-global-blacklist-clear:

""""""""""""""""""""""""""""""""""""""""""""
audioset restrictions global blacklist clear
""""""""""""""""""""""""""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]audioset restrictions global blacklist clear 

**Description**

Clear all keywords added to the blacklist.

.. _audio-command-audioset-restrictions-global-blacklist-delete:

"""""""""""""""""""""""""""""""""""""""""""""
audioset restrictions global blacklist delete
"""""""""""""""""""""""""""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]audioset restrictions global blacklist delete <keyword>

**Description**

Removes a keyword from the blacklist.

.. _audio-command-audioset-restrictions-global-blacklist-list:

"""""""""""""""""""""""""""""""""""""""""""
audioset restrictions global blacklist list
"""""""""""""""""""""""""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]audioset restrictions global blacklist list 

**Description**

List all keywords added to the blacklist.

.. _audio-command-audioset-restrictions-global-whitelist:

""""""""""""""""""""""""""""""""""""""
audioset restrictions global whitelist
""""""""""""""""""""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]audioset restrictions global whitelist 

**Description**

Manages the global keyword whitelist.

.. _audio-command-audioset-restrictions-global-whitelist-add:

""""""""""""""""""""""""""""""""""""""""""
audioset restrictions global whitelist add
""""""""""""""""""""""""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]audioset restrictions global whitelist add <keyword>

**Description**

Adds a keyword to the whitelist. If anything is added to whitelist,
it will blacklist everything else.

.. _audio-command-audioset-restrictions-global-whitelist-clear:

""""""""""""""""""""""""""""""""""""""""""""
audioset restrictions global whitelist clear
""""""""""""""""""""""""""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]audioset restrictions global whitelist clear 

**Description**

Clear all keywords from the whitelist.

.. _audio-command-audioset-restrictions-global-whitelist-delete:

"""""""""""""""""""""""""""""""""""""""""""""
audioset restrictions global whitelist delete
"""""""""""""""""""""""""""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]audioset restrictions global whitelist delete <keyword>

**Description**

Removes a keyword from the whitelist.

.. _audio-command-audioset-restrictions-global-whitelist-list:

"""""""""""""""""""""""""""""""""""""""""""
audioset restrictions global whitelist list
"""""""""""""""""""""""""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]audioset restrictions global whitelist list 

**Description**

List all keywords added to the whitelist.

.. _audio-command-audioset-restrictions-whitelist:

"""""""""""""""""""""""""""""""
audioset restrictions whitelist
"""""""""""""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]audioset restrictions whitelist 

**Description**

Manages the keyword whitelist.

.. _audio-command-audioset-restrictions-whitelist-add:

"""""""""""""""""""""""""""""""""""
audioset restrictions whitelist add
"""""""""""""""""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]audioset restrictions whitelist add <keyword>

**Description**

Adds a keyword to the whitelist. If anything is added to whitelist,
it will blacklist everything else.

.. _audio-command-audioset-restrictions-whitelist-clear:

"""""""""""""""""""""""""""""""""""""
audioset restrictions whitelist clear
"""""""""""""""""""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]audioset restrictions whitelist clear 

**Description**

Clear all keywords from the whitelist.

.. _audio-command-audioset-restrictions-whitelist-delete:

""""""""""""""""""""""""""""""""""""""
audioset restrictions whitelist delete
""""""""""""""""""""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]audioset restrictions whitelist delete <keyword>

**Description**

Removes a keyword from the whitelist.

.. _audio-command-audioset-restrictions-whitelist-list:

""""""""""""""""""""""""""""""""""""
audioset restrictions whitelist list
""""""""""""""""""""""""""""""""""""

**Syntax**

.. code-block:: none

    [p]audioset restrictions whitelist list 

**Description**

List all keywords added to the whitelist.

.. _audio-command-audioset-role:

"""""""""""""
audioset role
"""""""""""""

.. note:: |admin-lock|

**Syntax**

.. code-block:: none

    [p]audioset role <role_name>

**Description**

Set the role to use for DJ mode.

.. _audio-command-audioset-settings:

"""""""""""""""""
audioset settings
"""""""""""""""""

**Syntax**

.. code-block:: none

    [p]audioset settings 

**Description**

Show the current settings.

.. _audio-command-audioset-spotifyapi:

"""""""""""""""""""
audioset spotifyapi
"""""""""""""""""""

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]audioset spotifyapi 

**Description**

Instructions to set the Spotify API tokens.

.. _audio-command-audioset-status:

"""""""""""""""
audioset status
"""""""""""""""

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]audioset status 

**Description**

Enable/disable tracks' titles as status.

.. _audio-command-audioset-thumbnail:

""""""""""""""""""
audioset thumbnail
""""""""""""""""""

.. note:: |mod-lock|

**Syntax**

.. code-block:: none

    [p]audioset thumbnail 

**Description**

Toggle displaying a thumbnail on audio messages.

.. _audio-command-audioset-vote:

"""""""""""""
audioset vote
"""""""""""""

.. note:: |mod-lock|

**Syntax**

.. code-block:: none

    [p]audioset vote <percent>

**Description**

Percentage needed for non-mods to skip tracks, 0 to disable.

.. _audio-command-audioset-youtubeapi:

"""""""""""""""""""
audioset youtubeapi
"""""""""""""""""""

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]audioset youtubeapi 

**Description**

Instructions to set the YouTube API key.

.. _audio-command-audiostats:

^^^^^^^^^^
audiostats
^^^^^^^^^^

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]audiostats 

**Description**

Audio stats.

.. _audio-command-autoplay:

^^^^^^^^
autoplay
^^^^^^^^

.. note:: |mod-lock|

**Syntax**

.. code-block:: none

    [p]autoplay 

**Description**

Starts auto play.

.. _audio-command-bump:

^^^^
bump
^^^^

**Syntax**

.. code-block:: none

    [p]bump <index>

**Description**

Bump a track number to the top of the queue.

.. _audio-command-bumpplay:

^^^^^^^^
bumpplay
^^^^^^^^

**Syntax**

.. code-block:: none

    [p]bumpplay [play_now=False] <query>

**Description**

Force play a URL or search for a track.

.. _audio-command-disconnect:

^^^^^^^^^^
disconnect
^^^^^^^^^^

**Syntax**

.. code-block:: none

    [p]disconnect 

**Description**

Disconnect from the voice channel.

.. _audio-command-eq:

^^
eq
^^

**Syntax**

.. code-block:: none

    [p]eq 

**Description**

Equalizer management.

Band positions are 1-15 and values have a range of -0.25 to 1.0.
Band names are 25, 40, 63, 100, 160, 250, 400, 630, 1k, 1.6k, 2.5k, 4k,
6.3k, 10k, and 16k Hz.
Setting a band value to -0.25 nullifies it while +0.25 is double.

.. _audio-command-eq-delete:

"""""""""
eq delete
"""""""""

**Syntax**

.. code-block:: none

    [p]eq delete <eq_preset>

**Description**

Delete a saved eq preset.

.. _audio-command-eq-list:

"""""""
eq list
"""""""

**Syntax**

.. code-block:: none

    [p]eq list 

**Description**

List saved eq presets.

.. _audio-command-eq-load:

"""""""
eq load
"""""""

**Syntax**

.. code-block:: none

    [p]eq load <eq_preset>

**Description**

Load a saved eq preset.

.. _audio-command-eq-reset:

""""""""
eq reset
""""""""

**Syntax**

.. code-block:: none

    [p]eq reset 

**Description**

Reset the eq to 0 across all bands.

.. _audio-command-eq-save:

"""""""
eq save
"""""""

**Syntax**

.. code-block:: none

    [p]eq save [eq_preset]

**Description**

Save the current eq settings to a preset.

.. _audio-command-eq-set:

""""""
eq set
""""""

**Syntax**

.. code-block:: none

    [p]eq set <band_name_or_position> <band_value>

**Description**

Set an eq band with a band number or name and value.

Band positions are 1-15 and values have a range of -0.25 to 1.0.
Band names are 25, 40, 63, 100, 160, 250, 400, 630, 1k, 1.6k, 2.5k, 4k,
6.3k, 10k, and 16k Hz.
Setting a band value to -0.25 nullifies it while +0.25 is double.

.. _audio-command-genre:

^^^^^
genre
^^^^^

**Syntax**

.. code-block:: none

    [p]genre 

**Description**

Pick a Spotify playlist from a list of categories to start playing.

.. _audio-command-local:

^^^^^
local
^^^^^

**Syntax**

.. code-block:: none

    [p]local 

**Description**

Local playback commands.

.. _audio-command-local-folder:

""""""""""""
local folder
""""""""""""

**Syntax**

.. code-block:: none

    [p]local folder [folder]

**Description**

Play all songs in a localtracks folder.

**Example usage**

* ``[p]local folder`` - Open a menu to pick a folder to queue.
* ``[p]local folder folder_name`` - Queues all of the tracks inside the folder_name folder.

.. _audio-command-local-play:

""""""""""
local play
""""""""""

**Syntax**

.. code-block:: none

    [p]local play 

**Description**

Play a local track.

To play a local track, either use the menu to choose a track or enter in the track path directly
with the play command. To play an entire folder, use ``[p]help local folder`` for instructions.

**Example usage**

* ``[p]local play`` - Open a menu to pick a track.
* ``[p]play localtracks\album_folder\song_name.mp3``
* ``[p]play album_folder\song_name.mp3`` - Use a direct link relative to the localtracks folder.

.. _audio-command-local-search:

""""""""""""
local search
""""""""""""

**Syntax**

.. code-block:: none

    [p]local search <search_words>

**Description**

Search for songs across all localtracks folders.

.. _audio-command-now:

^^^
now
^^^

**Syntax**

.. code-block:: none

    [p]now 

**Description**

Now playing.

.. _audio-command-pause:

^^^^^
pause
^^^^^

**Syntax**

.. code-block:: none

    [p]pause 

**Description**

Pause or resume a playing track.

.. _audio-command-percent:

^^^^^^^
percent
^^^^^^^

**Syntax**

.. code-block:: none

    [p]percent 

**Description**

Queue percentage.

.. _audio-command-play:

^^^^
play
^^^^

**Syntax**

.. code-block:: none

    [p]play <query>

**Description**

Play the specified track or search for a close match.

To play a local track, the query should be ``<parentfolder>\<filename>``.
If you are the bot owner, use ``[p]audioset info`` to display your localtracks path.

.. _audio-command-playlist:

^^^^^^^^
playlist
^^^^^^^^

**Syntax**

.. code-block:: none

    [p]playlist 

**Description**

Playlist configuration options.

**Scope information**

* Global: Visible to all users of this bot. Only editable by bot owner.
* Guild: Visible to all users in this guild. Editable by bot owner, guild owner,
  guild admins, guild mods, DJ role and playlist creator.
* User: Visible to all bot users, if ``--author`` is passed. Editable by bot owner and playlist creator.

.. _audio-command-playlist-append:

"""""""""""""""
playlist append
"""""""""""""""

**Syntax**

.. code-block:: none

    [p]playlist append <playlist_name_OR_id> <track_name_OR_url> [args]

**Description**

Add a track URL, playlist link, or quick search to a playlist. The track(s) will be
appended to the end of the playlist.

**Args**

The following are all optional:

* --scope <scope>
* --author [user]
* --guild [guild] (**only the bot owner can use this**)

**Scope** is one of the following:

* Global
* Guild
* User

**Author** can be one of the following:

* User ID
* User Mention
* User Name#123

**Guild** can be one of the following:

* Guild ID
* Exact guild name

**Example usage**

* ``[p]playlist append MyGuildPlaylist Hello by Adele``
* ``[p]playlist append MyGlobalPlaylist Hello by Adele --scope Global``
* ``[p]playlist append MyGlobalPlaylist Hello by Adele --scope Global --Author Draper#6666``

.. _audio-command-playlist-copy:

"""""""""""""
playlist copy
"""""""""""""

**Syntax**

.. code-block:: none

    [p]playlist copy <id_or_name> [args]

**Description**

Copy a playlist from one scope to another.

**Args**

The following are all optional:

* --from-scope <scope>
* --from-author [user]
* --from-guild [guild] (**only the bot owner can use this**)
* --to-scope <scope>
* --to-author [user]
* --to-guild [guild] (**only the bot owner can use this**)

**Scope** is one of the following:

* Global
* Guild
* User

**Author** can be one of the following:

* User ID
* User Mention
* User Name#123

**Guild** can be one of the following:

* Guild ID
* Exact guild name

**Example usage**

* ``[p]playlist copy MyGuildPlaylist --from-scope Guild --to-scope Global``
* ``[p]playlist copy MyGlobalPlaylist --from-scope Global --to-author Draper#6666 --to-scope User``
* ``[p]playlist copy MyPersonalPlaylist --from-scope user --to-author Draper#6666 --to-scope Guild --to-guild Red - Discord Bot``

.. _audio-command-playlist-create:

"""""""""""""""
playlist create
"""""""""""""""

**Syntax**

.. code-block:: none

    [p]playlist create <name> [args]

**Description**

Create an empty playlist.

**Args**

The following are all optional:

* --scope <scope>
* --author [user]
* --guild [guild] (**only the bot owner can use this**)

**Scope** is one of the following:

* Global
* Guild
* User

**Author** can be one of the following:

* User ID
* User Mention
* User Name#123

**Guild** can be one of the following:

* Guild ID
* Exact guild name

**Example usage**

* ``[p]playlist create MyGuildPlaylist``
* ``[p]playlist create MyGlobalPlaylist --scope Global``
* ``[p]playlist create MyPersonalPlaylist --scope User``

.. _audio-command-playlist-dedupe:

"""""""""""""""
playlist dedupe
"""""""""""""""

**Syntax**

.. code-block:: none

    [p]playlist dedupe <playlist_name_OR_id> [args]

**Description**

Remove duplicate tracks from a saved playlist.

**Args**

The following are all optional:

* --scope <scope>
* --author [user]
* --guild [guild] (**only the bot owner can use this**)

**Scope** is one of the following:

* Global
* Guild
* User

**Author** can be one of the following:

* User ID
* User Mention
* User Name#123

**Guild** can be one of the following:

* Guild ID
* Exact guild name

**Example usage**

* ``[p]playlist dedupe MyGuildPlaylist``
* ``[p]playlist dedupe MyGlobalPlaylist --scope Global``
* ``[p]playlist dedupe MyPersonalPlaylist --scope User``

.. _audio-command-playlist-delete:

"""""""""""""""
playlist delete
"""""""""""""""

**Syntax**

.. code-block:: none

    [p]playlist delete <playlist_name_OR_id> [args]

**Description**

Delete a saved playlist.

**Args**

The following are all optional:

* --scope <scope>
* --author [user]
* --guild [guild] (**only the bot owner can use this**)

**Scope** is one of the following:

* Global
* Guild
* User

**Author** can be one of the following:

* User ID
* User Mention
* User Name#123

**Guild** can be one of the following:

* Guild ID
* Exact guild name

**Example usage**

* ``[p]playlist delete MyGuildPlaylist``
* ``[p]playlist delete MyGlobalPlaylist --scope Global``
* ``[p]playlist delete MyPersonalPlaylist --scope User``

.. _audio-command-playlist-download:

"""""""""""""""""
playlist download
"""""""""""""""""

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]playlist download <playlist_name_OR_id> [v2=False] [args]

**Description**

Download a copy of a playlist.

These files can be used with the ``[p]playlist upload`` command.
Red v2-compatible playlists can be generated by passing True
for the v2 variable.

**Args**

The following are all optional:

* --scope <scope>
* --author [user]
* --guild [guild] (**only the bot owner can use this**)

**Scope** is one of the following:

* Global
* Guild
* User

**Author** can be one of the following:

* User ID
* User Mention
* User Name#123

**Guild** can be one of the following:

* Guild ID
* Exact guild name

**Example usage**

* ``[p]playlist download MyGuildPlaylist True``
* ``[p]playlist download MyGlobalPlaylist False --scope Global``
* ``[p]playlist download MyPersonalPlaylist --scope User``

.. _audio-command-playlist-info:

"""""""""""""
playlist info
"""""""""""""

**Syntax**

.. code-block:: none

    [p]playlist info <playlist_name_OR_id> [args]

**Description**

Retrieve information from a saved playlist.

**Args**

The following are all optional:

* --scope <scope>
* --author [user]
* --guild [guild] (**only the bot owner can use this**)

**Scope** is one of the following:

* Global
* Guild
* User

**Author** can be one of the following:

* User ID
* User Mention
* User Name#123

**Guild** can be one of the following:

* Guild ID
* Exact guild name

**Example usage**

* ``[p]playlist info MyGuildPlaylist``
* ``[p]playlist info MyGlobalPlaylist --scope Global``
* ``[p]playlist info MyPersonalPlaylist --scope User``

.. _audio-command-playlist-list:

"""""""""""""
playlist list
"""""""""""""

**Syntax**

.. code-block:: none

    [p]playlist list [args]

**Description**

List saved playlists.

**Args**

The following are all optional:

* --scope <scope>
* --author [user]
* --guild [guild] (**only the bot owner can use this**)

**Scope** is one of the following:

* Global
* Guild
* User

**Author** can be one of the following:

* User ID
* User Mention
* User Name#123

**Guild** can be one of the following:

* Guild ID
* Exact guild name

**Example usage**

* ``[p]playlist list``
* ``[p]playlist list --scope Global``
* ``[p]playlist list --scope User``

.. _audio-command-playlist-queue:

""""""""""""""
playlist queue
""""""""""""""

**Syntax**

.. code-block:: none

    [p]playlist queue <name> [args]

**Description**

Save the queue to a playlist.

**Args**

The following are all optional:

* --scope <scope>
* --author [user]
* --guild [guild] (**only the bot owner can use this**)

**Scope** is one of the following:

* Global
* Guild
* User

**Author** can be one of the following:

* User ID
* User Mention
* User Name#123

**Guild** can be one of the following:

* Guild ID
* Exact guild name

**Example usage**

* ``[p]playlist queue MyGuildPlaylist``
* ``[p]playlist queue MyGlobalPlaylist --scope Global``
* ``[p]playlist queue MyPersonalPlaylist --scope User``

.. _audio-command-playlist-remove:

"""""""""""""""
playlist remove
"""""""""""""""

**Syntax**

.. code-block:: none

    [p]playlist remove <playlist_name_OR_id> <url> [args]

**Description**

Remove a track from a playlist by URL.

**Args**

The following are all optional:

* --scope <scope>
* --author [user]
* --guild [guild] (**only the bot owner can use this**)

**Scope** is one of the following:

* Global
* Guild
* User

**Author** can be one of the following:

* User ID
* User Mention
* User Name#123

**Guild** can be one of the following:

* Guild ID
* Exact guild name

**Example usage**

* ``[p]playlist remove MyGuildPlaylist https://www.youtube.com/watch?v=MN3x-kAbgFU``
* ``[p]playlist remove MyGlobalPlaylist https://www.youtube.com/watch?v=MN3x-kAbgFU --scope Global``
* ``[p]playlist remove MyPersonalPlaylist https://www.youtube.com/watch?v=MN3x-kAbgFU --scope User``

.. _audio-command-playlist-rename:

"""""""""""""""
playlist rename
"""""""""""""""

**Syntax**

.. code-block:: none

    [p]playlist rename <playlist_name_OR_id> <new_name> [args]

**Description**

Rename an existing playlist.

**Args**

The following are all optional:

* --scope <scope>
* --author [user]
* --guild [guild] (**only the bot owner can use this**)

**Scope** is one of the following:

* Global
* Guild
* User

**Author** can be one of the following:

* User ID
* User Mention
* User Name#123

**Guild** can be one of the following:

* Guild ID
* Exact guild name

**Example usage**

* ``[p]playlist rename MyGuildPlaylist RenamedGuildPlaylist``
* ``[p]playlist rename MyGlobalPlaylist RenamedGlobalPlaylist --scope Global``
* ``[p]playlist rename MyPersonalPlaylist RenamedPersonalPlaylist --scope User``

.. _audio-command-playlist-save:

"""""""""""""
playlist save
"""""""""""""

**Syntax**

.. code-block:: none

    [p]playlist save <name> <url> [args]

**Description**

Save a playlist from a URL.

The following are all optional:

* --scope <scope>
* --author [user]
* --guild [guild] (**only the bot owner can use this**)

**Scope** is one of the following:

* Global
* Guild
* User

**Author** can be one of the following:

* User ID
* User Mention
* User Name#123

**Guild** can be one of the following:

* Guild ID
* Exact guild name

**Example usage**

* ``[p]playlist save MyGuildPlaylist https://www.youtube.com/playlist?list=PLx0sYbCqOb8Q_CLZC2BdBSKEEB59BOPUM``
* ``[p]playlist save MyGlobalPlaylist https://www.youtube.com/playlist?list=PLx0sYbCqOb8Q_CLZC2BdBSKEEB59BOPUM --scope Global``
* ``[p]playlist save MyPersonalPlaylist https://open.spotify.com/playlist/1RyeIbyFeIJVnNzlGr5KkR --scope User``

.. _audio-command-playlist-start:

""""""""""""""
playlist start
""""""""""""""

**Syntax**

.. code-block:: none

    [p]playlist start <playlist_name_OR_id> [args]

**Description**

Load a playlist into the queue.

**Args**

The following are all optional:

* --scope <scope>
* --author [user]
* --guild [guild] (**only the bot owner can use this**)

**Scope** is one of the following:

* Global
* Guild
* User

**Author** can be one of the following:

* User ID
* User Mention
* User Name#123

**Guild** can be one of the following:

* Guild ID
* Exact guild name

**Example usage**

* ``[p]playlist start MyGuildPlaylist``
* ``[p]playlist start MyGlobalPlaylist --scope Global``
* ``[p]playlist start MyPersonalPlaylist --scope User``

.. _audio-command-playlist-update:

"""""""""""""""
playlist update
"""""""""""""""

**Syntax**

.. code-block:: none

    [p]playlist update <playlist_name_OR_id> [args]

**Description**

Updates all tracks in a playlist.

**Args**

The following are all optional:

* --scope <scope>
* --author [user]
* --guild [guild] (**only the bot owner can use this**)

**Scope** is one of the following:

* Global
* Guild
* User

**Author** can be one of the following:

* User ID
* User Mention
* User Name#123

**Guild** can be one of the following:

* Guild ID
* Exact guild name

**Example usage**

* ``[p]playlist update MyGuildPlaylist``
* ``[p]playlist update MyGlobalPlaylist --scope Global``
* ``[p]playlist update MyPersonalPlaylist --scope User``

.. _audio-command-playlist-upload:

"""""""""""""""
playlist upload
"""""""""""""""

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]playlist upload [args]

**Description**

Uploads a playlist file as a playlist for the bot.

V2 and old V3 playlist will be slow.
V3 Playlist made with ``[p]playlist download`` will load a lot faster.

**Args**

The following are all optional:

* --scope <scope>
* --author [user]
* --guild [guild] (**only the bot owner can use this**)

**Scope** is one of the following:

* Global
* Guild
* User

**Author** can be one of the following:

* User ID
* User Mention
* User Name#123

**Guild** can be one of the following:

* Guild ID
* Exact guild name

**Example usage**

* ``[p]playlist upload``
* ``[p]playlist upload --scope Global``
* ``[p]playlist upload --scope User``

.. _audio-command-prev:

^^^^
prev
^^^^

**Syntax**

.. code-block:: none

    [p]prev 

**Description**

Skip to the start of the previously played track.

.. _audio-command-queue:

^^^^^
queue
^^^^^

**Syntax**

.. code-block:: none

    [p]queue [page=1]

**Description**

List the songs in the queue.

.. _audio-command-queue-clean:

"""""""""""
queue clean
"""""""""""

**Syntax**

.. code-block:: none

    [p]queue clean 

**Description**

Removes songs from the queue if the requester is not in the voice channel.

.. _audio-command-queue-cleanself:

"""""""""""""""
queue cleanself
"""""""""""""""

**Syntax**

.. code-block:: none

    [p]queue cleanself 

**Description**

Removes all tracks you requested from the queue.

.. _audio-command-queue-clear:

"""""""""""
queue clear
"""""""""""

**Syntax**

.. code-block:: none

    [p]queue clear 

**Description**

Clears the queue.

.. _audio-command-queue-search:

""""""""""""
queue search
""""""""""""

**Syntax**

.. code-block:: none

    [p]queue search <search_words>

**Description**

Search the queue.

.. _audio-command-queue-shuffle:

"""""""""""""
queue shuffle
"""""""""""""

**Syntax**

.. code-block:: none

    [p]queue shuffle 

**Description**

Shuffles the queue.

.. _audio-command-remove:

^^^^^^
remove
^^^^^^

**Syntax**

.. code-block:: none

    [p]remove <index_or_url>

**Description**

Remove a specific track number from the queue.

.. _audio-command-repeat:

^^^^^^
repeat
^^^^^^

**Syntax**

.. code-block:: none

    [p]repeat 

**Description**

Toggle repeat.

.. _audio-command-search:

^^^^^^
search
^^^^^^

**Syntax**

.. code-block:: none

    [p]search <query>

**Description**

Pick a track with a search.

Use ``[p]search list <search term>`` to queue all tracks found on YouTube. Use ``[p]search sc
<search term>`` to search on SoundCloud instead of YouTube.

.. _audio-command-seek:

^^^^
seek
^^^^

**Syntax**

.. code-block:: none

    [p]seek <seconds>

**Description**

Seek ahead or behind on a track by seconds or to a specific time. Accepts seconds or
a value formatted like 00:00:00 (``hh:mm:ss``) or 00:00 (``mm:ss``).

.. _audio-command-shuffle:

^^^^^^^
shuffle
^^^^^^^

**Syntax**

.. code-block:: none

    [p]shuffle 

**Description**

Toggle shuffle.

.. _audio-command-shuffle-bumped:

""""""""""""""
shuffle bumped
""""""""""""""

**Syntax**

.. code-block:: none

    [p]shuffle bumped 

**Description**

Toggle bumped track shuffle.

Set this to disabled if you wish to avoid bumped songs being shuffled. This takes priority
over ``[p]shuffle``.

.. _audio-command-sing:

^^^^
sing
^^^^

**Syntax**

.. code-block:: none

    [p]sing 

**Description**

Make Red sing one of her songs.

.. _audio-command-skip:

^^^^
skip
^^^^

**Syntax**

.. code-block:: none

    [p]skip [skip_to_track]

**Description**

Skip to the next track, or to a given track number.

.. _audio-command-stop:

^^^^
stop
^^^^

**Syntax**

.. code-block:: none

    [p]stop 

**Description**

Stop playback and clear the queue.

.. _audio-command-summon:

^^^^^^
summon
^^^^^^

**Syntax**

.. code-block:: none

    [p]summon [voice_channel]

**Description**

Summon the bot to a voice channel.

You can specify a personalised voice room with an ID. Otherwise, the bot will join the voice room you are in.
To learn how to get a channel ID please read `this help article <https://support.discord.com/hc/en-us/articles/206346498-Where-can-I-find-my-User-Server-Message-ID>`__.

.. _audio-command-volume:

^^^^^^
volume
^^^^^^

**Syntax**

.. code-block:: none

    [p]volume [vol]

**Description**

Set the volume, 1% - 150%.

.. _llset-commands:

-----------------------
Lavalink Setup Commands
-----------------------

``[p]llset`` group commands are used for advanced management of the connection to the Lavalink 
server. The subcommands are dynamically available depending on whether Red is managing your 
Lavalink node or if you are connecting to one you manage yourself, or a service that offers Lavalink
nodes.

Commands specifically for managed Lavalink nodes can be found in :ref:`this section<managed-node-management-commands>`, 
whilst commands for unmanaged Lavalink nodes can be found :ref:`here<unmanaged-node-management-commands>`.

.. _audio-command-llset:

^^^^^
llset
^^^^^

.. note:: |owner-lock|

**Syntax**

.. code-block:: none

    [p]llset 

**Description**

Manage Lavalink node configuration settings. This command holds all commands to
manage an unmanaged (user-managed) or managed (bot-managed) Lavalink node.

.. warning::

    You should not change any command settings in this group command unless you 
    have a valid reason to, e.g. been told by someone in the Red-Discord Bot support 
    server to do so. Changing llset command settings have the potential to break 
    Audio cog connection and playback if the wrong settings are used.

"""""""""""""""
llset unmanaged
"""""""""""""""

**Syntax**

.. code-block:: none

    [p]llset unmanaged

or 

.. code-block:: none

    [p]llsetup unmanaged

**Description**

Toggle using unmanaged (user-managed) Lavalink nodes - requires an existing Lavalink 
node for Audio to work, if enabled. This command disables the managed (bot-managed) 
Lavalink server: if you do not have an unmanaged Lavalink node set up, you will be 
unable to use Audio while this is enabled.

""""""""""
llset info
""""""""""

**Syntax**

.. code-block:: none

    [p]llset info

**Description**

Display Lavalink connection settings.

"""""""""""
llset reset
"""""""""""

**Syntax**

.. code-block:: none

    [p]llset reset

**Description**

Reset all ``[p]llset`` changes back to their default values.

.. _managed-node-management-commands:

--------------------------------
Managed Node Management Commands
--------------------------------

.. _audio-command-llset-config:

^^^^^^^^^^^^
llset config
^^^^^^^^^^^^

**Syntax**

.. code-block:: none

    [p]llset config

**Description**

Configure the managed Lavalink node runtime options.

All settings under this group will likely cause Audio to malfunction if changed
from their defaults, only change settings here if you have been advised to by #support.

.. _audio-command-llset-config-bind:

^^^^^^^^^^^^^^^^^
llset config bind
^^^^^^^^^^^^^^^^^

**Syntax**

.. code-block:: none

    [p]llset config bind [host=localhost]

**Description**

Set the managed Lavalink node's binding IP address.

**Arguments**

* ``[host]``: The node's binding IP address, defaulting to "localhost".

.. _audio-command-llset-config-port:

^^^^^^^^^^^^^^^^^
llset config port
^^^^^^^^^^^^^^^^^

**Syntax**

.. code-block:: none

    [p]llset config port [port=2333]

**Description**

Set the managed Lavalink node's connection port.

This port is the port the managed Lavalink node binds to, you should
only change this if there is a conflict with the default port because
you already have an application using port 2333 on this device.

**Arguments**

* ``[port]``: The node's connection port, defaulting to 2333.

.. _audio-command-llset-config-server:

^^^^^^^^^^^^^^^^^^^
llset config server
^^^^^^^^^^^^^^^^^^^

**Syntax**

.. code-block:: none

    [p]llset config server

**Description**

Configure the managed node authorization and connection settings.

.. _audio-command-llset-config-server-buffer:

^^^^^^^^^^^^^^^^^^^^^^^^^^
llset config server buffer
^^^^^^^^^^^^^^^^^^^^^^^^^^

**Syntax**

.. code-block:: none

    [p]llset config server buffer [milliseconds=400]

**Description**

Set the managed Lavalink node JDA-NAS buffer size. Only
change this if you have been directly advised to,
changing it can cause significant playback issues.

**Arguments**

* ``[milliseconds]`` - The buffer size, defaults to 400.

.. _audio-command-llset-config-server-framebuffer:

^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
llset config server framebuffer
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Syntax**

.. code-block:: none

    [p]llset config server framebuffer [milliseconds=1000]

**Description**

Set the managed Lavalink node framebuffer size. Only
change this if you have been directly advised to,
changing it can cause significant playback issues.

**Arguments**

* ``[milliseconds]`` - The framebuffer size, defaults to 1000.

.. _audio-command-llset-config-source:

^^^^^^^^^^^^^^^^^^^
llset config source 
^^^^^^^^^^^^^^^^^^^

**Syntax**

.. code-block:: none

    [p]llset config source

**Description**

Toggle audio sources on/off.

By default, all sources are enabled, you should only use commands here to
disable a specific source if you have been advised to, disabling sources
without background knowledge can cause Audio to break.

.. _audio-command-llset-config-source-bandcamp:

^^^^^^^^^^^^^^^^^^^^^^^^^^^^
llset config source bandcamp
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Syntax**

.. code-block:: none

    [p]llset config source bandcamp

**Description**

Toggle Bandcamp source on or off. This toggle controls the playback
of all Bandcamp related content.

.. _audio-command-llset-config-source-http:

^^^^^^^^^^^^^^^^^^^^^^^^
llset config source http
^^^^^^^^^^^^^^^^^^^^^^^^

**Syntax**

.. code-block:: none

    [p]llset config source http

**Description**

Toggle HTTP direct URL usage on or off. This source is used to
allow playback from direct HTTP streams (this does not affect direct URL
playback for the other sources).

.. _audio-command-llset-config-source-local:

^^^^^^^^^^^^^^^^^^^^^^^^^
llset config source local
^^^^^^^^^^^^^^^^^^^^^^^^^

**Syntax**

.. code-block:: none

    [p]llset config source local

**Description**

Toggle local file usage on or off.
This toggle controls the playback of all local track content,
usually found inside the ``localtracks`` folder.

.. _audio-command-llset-config-source-soundcloud:

^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
llset config source soundcloud
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Syntax**

.. code-block:: none

    [p]llset config source soundcloud

**Description**

Toggle SoundCloud source on or off.
This toggle controls the playback of all SoundCloud related content.

.. _audio-command-llset-config-source-twitch:

^^^^^^^^^^^^^^^^^^^^^^^^^^
llset config source twitch
^^^^^^^^^^^^^^^^^^^^^^^^^^

**Syntax**

.. code-block:: none

    [p]llset config source twitch

**Description**

Toggle Twitch source on or off.
This toggle controls the playback of all Twitch related content.

.. _audio-command-llset-config-source-vimeo:

^^^^^^^^^^^^^^^^^^^^^^^^^
llset config source vimeo
^^^^^^^^^^^^^^^^^^^^^^^^^

**Syntax**

.. code-block:: none

    [p]llset config source vimeo

**Description**

Toggle Vimeo source on or off.
This toggle controls the playback of all Vimeo related content.

.. _audio-command-llset-config-source-youtube:

^^^^^^^^^^^^^^^^^^^^^^^^^^^
llset config source youtube
^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Syntax**

.. code-block:: none

    [p]llset config source youtube

**Description**

Toggle YouTube source on or off (**this includes Spotify**).
This toggle controls the playback of all YouTube and Spotify related content.

.. _audio-command-llset-config-token:

^^^^^^^^^^^^^^^^^^
llset config token
^^^^^^^^^^^^^^^^^^

**Syntax**

.. code-block:: none

    [p]llset config token [password=youshallnotpass]

**Description**

Set the managed Lavalink node's connection password.
This is the password required for Audio to connect to the managed Lavalink node.
The value by default is ``youshallnotpass``.

**Arguments**

* ``[password]`` - The node's connection password, defaulting to ``youshallnotpass``.

.. _audio-command-llset-heapsize:

^^^^^^^^^^^^^^
llset heapsize
^^^^^^^^^^^^^^

**Syntax**

.. code-block:: none

    [p]llset heapsize [size=3G]

**Description**

Set the managed Lavalink node maximum heap-size.

By default, this value is 50% of available RAM in the host machine
represented by [1-1024][M|G] (256M, 256G for example).

This value only represents the maximum amount of RAM allowed to be
used at any given point, and does not mean that the managed Lavalink
node will always use this amount of RAM.

**Arguments**

* ``[size]`` - The node's maximum heap-size, defaulting to ``3G``.

.. _audio-command-llset-java:

^^^^^^^^^^
llset java
^^^^^^^^^^

**Syntax**

.. code-block:: none

    [p]llset java [javapath]

**Description**

Change your Java executable path.

This command shouldn't need to be used most of the time,
and is only useful if the host machine has conflicting Java versions.

If changing this make sure that the Java executable you set is supported by Audio.
The current supported versions are Java 17 and 11.

**Arguments**

* ``[java]`` - The java executable path, leave blank to reset it back to default.

.. _audio-command-llset-yaml:

^^^^^^^^^^
llset yaml
^^^^^^^^^^

**Syntax**

.. code-block:: none

    [p]llset yaml

**Description**

Uploads a copy of the application.yml file used by the managed Lavalink node.

.. _unmanaged-node-management-commands:

----------------------------------
Unmanaged Node Management Commands
----------------------------------

.. note::

    A normal Red user should never have to use these commands unless they are :ref:`managing multiple Red bots with Audio<multibots>`.

.. _audio-command-llset-host:

^^^^^^^^^^
llset host
^^^^^^^^^^

**Syntax**

.. code-block:: none

    [p]llset host [host=localhost]

**Description**

Set the Lavalink node host. This command sets the connection host which
Audio will use to connect to an unmanaged Lavalink node.

**Arguments**

* ``[host]`` - The connection host, defaulting to "localhost".

.. _audio-command-llset-password:

^^^^^^^^^^^^^^
llset password
^^^^^^^^^^^^^^

**Syntax**

.. code-block:: none

    [p]llset password [password=youshallnotpass]

**Description**

Set the Lavalink node password. This command sets the connection password which
Audio will use to connect to an unmanaged Lavalink node.

**Arguments**

* ``[password]`` - The connection password, defaulting to "youshallnotpass".

.. _audio-command-llset-port:

^^^^^^^^^^
llset port
^^^^^^^^^^

**Syntax**

.. code-block:: none

    [p]llset port [port=2333]

**Description**

Set the Lavalink node port. This command sets the connection port which
Audio will use to connect to an unmanaged Lavalink node.

Set port to ``-1`` to disable the port and connect to the specified host via ports ``80``/``443``.

**Arguments**

* ``[password]`` - The connection password, defaulting to 2333.

.. _audio-command-llset-secured:

^^^^^^^^^^^^^
llset secured
^^^^^^^^^^^^^

**Syntax**

.. code-block:: none

    [p]llset secured

**Description**

Set the Lavalink node connection to secured. This toggle sets the connection type
to secured or unsecured when connecting to an unmanaged Lavalink node.
