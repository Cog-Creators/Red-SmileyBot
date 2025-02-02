.. framework events list

=============
Custom Events
=============

Audio
^^^^^

.. py:method:: Red.on_red_audio_audio_disconnect(guild)

    Dispatched when a player disconnects from a channel

    :param discord.Guild guild: The guild in which the player disconnected

.. py:method:: Red.on_red_audio_queue_end(guild, prev_track, prev_requester)

    Dispatched when the queue ends

    :param discord.Guild guild: The guild in which the queue ended
    :param lavalink.Track prev_track: The last track
    :param discord.Member prev_requester: The track's requester

.. py:method:: Red.on_red_audio_skip_track(guild, prev_track, prev_requester)

    Dispatched when a track is skipped

    :param discord.Guild guild: The guild in which the track was skipped
    :param lavalink.Track prev_track: The track that was skipped
    :param discord.Member prev_requester: The track's requester

.. py:method:: Red.on_red_audio_track_auto_play(guild, track, requester, player)

    Dispatched when a track is auto-played

    :param discord.Guild guild: The guild in which the track was auto-played
    :param lavalink.Track track: The track that was started
    :param discord.Member requester: The track's requester: :py:meth:`discord.Guild.me` in this case
    :param lavalink.Player player: The player associated to this event

.. py:method:: Red.on_red_audio_track_enqueue(guild, track, requester)

    Dispatched when a track is enqueued

    :param discord.Guild guild: The guild in which the track was enqueued
    :param lavalink.Track track: The track that was enqueued
    :param discord.Member requester: The track's requester

.. py:method:: Red.on_red_audio_track_end(guild, track, requester)

    Dispatched when a playing track ends

    :param discord.Guild guild: The guild in which the track ended
    :param lavalink.Track track: The track that ended
    :param discord.Member requester: The track's requester

.. py:method:: Red.on_red_audio_track_start(guild, track, requester)

    Dispatched when an enqueued track starts playing

    :param discord.Guild guild: The guild in which the track started
    :param lavalink.Track track: The track that was started
    :param discord.Member requester: The track's requester

.. py:method:: Red.on_red_audio_unload(cog)

    Dispatched when the audio cog starts it's unloading task

    :param cog: Audio cog instance: similar to :py:func:`redbot.core.bot.Red.get_cog()`

Filter
^^^^^^

.. py:method:: Red.on_filter_message_delete(message, hits)

    Dispatched when a message is deleted by the filter cog

    :param discord.Message message: The message that was deleted
    :param Set[str] hits: Words which got detected in the message

Modlog
^^^^^^

.. py:method:: Red.on_modlog_case_create(case)

    Dispatched when a new modlog case is created

    :param redbot.core.modlog.Case case: The modlog case associated with this event.

.. py:method:: Red.on_modlog_case_edit(case)

    Dispatched when a modlog case is edited

    :param redbot.core.modlog.Case case: The modlog case associated with this event.

RPC Server
^^^^^^^^^^

.. py:method:: Red.on_shutdown()

    Dispatched when the bot begins it's shutdown procedures.
