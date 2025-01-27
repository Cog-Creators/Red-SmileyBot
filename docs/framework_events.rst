.. framework events list

=============
Custom Events
=============

RPC Server
^^^^^^^^^^

.. py:method:: Red.on_shutdown()

    Dispatched when the bot begins its shutdown procedures.

Economy
^^^^^^^

.. py:method:: red_economy_payday_claim(payload: redbot.core.bank.PaydayClaimInformation)

    Dispatched when a user successfully claims a payday.

    :type payload: redbot.core.bank.PaydayClaimInformation
    :param payload.member: The member who is claiming their payday. (:class:`discord.Member`)
    :param payload.channel: The channel where the payday claim is made. (:class:`discord.TextChannel`, :class:`discord.Thread`, :class:`discord.ForumChannel`)
    :param payload.message: The command message that triggered the payday claim. (:class:`discord.Message`)
    :param payload.amount: The amount of currency claimed in the payday. (:class:`int`)
    :param payload.old_balance: The old balance of the user before the payday claim. (:class:`int`)
    :param payload.new_balance: The new balance of the user after the payday claim. (:class:`int`)
    :method payload.to_dict: Returns a serializable dictionary representation of the payload. (:class:`dict`)
    :method payload.to_json: Returns the payload as JSON. (:class:`str`)


Bank
^^^^

.. py:method:: red_bank_set_balance(payload: redbot.core.bank.BankSetBalanceInformation)

    Dispatched when a user's balance is changed.

    :type payload: redbot.core.bank.BankSetBalanceInformation
    :param payload.recipient: The member whose balance is being set. (:class:`discord.Member`, :class:`discord.User`)
    :param payload.guild: The guild where the balance is being set. (:class:`discord.Guild`, :class:`NoneType`)
    :param payload.recipient_old_balance: The old balance of the user before the change. (:class:`int`)
    :param payload.recipient_new_balance: The new balance of the user after the change. (:class:`int`)
    :method payload.to_dict: Returns a serializable dictionary representation of the payload. (:class:`dict`)
    :method payload.to_json: Returns the payload as JSON. (:class:`str`)

.. py:method:: red_bank_transfer_credits(payload: redbot.core.bank.BankTransferInformation)

    Dispatched when a user transfers currency to another user.

    :type payload: redbot.core.bank.BankTransferInformation
    :param payload.sender: The member who is sending currency. (:class:`discord.Member`, :class:`discord.User`)
    :param payload.recipient: The member who is receiving currency. (:class:`discord.Member`, :class:`discord.User`)
    :param payload.guild: The guild where the transfer is taking place. (:class:`discord.Guild`, :class:`NoneType`)
    :param payload.transfer_amount: The amount of currency being transferred. (:class:`int`)
    :param payload.sender_new_balance: The new balance of the sender after the transfer. (:class:`int`)
    :param payload.recipient_new_balance: The new balance of the recipient after the transfer. (:class:`int`)
    :method payload.to_dict: Returns a serializable dictionary representation of the payload. (:class:`dict`)
    :method payload.to_json: Returns the payload as JSON. (:class:`str`)


.. py:method:: red_bank_prune(payload: redbot.core.bank.BankPruneInformation)

    Dispatched when a user is pruned from the bank.

    :type payload: redbot.core.bank.BankPruneInformation
    :param payload.guild: The guild where the user is being pruned. (:class:`discord.Guild`, :class:`NoneType`)
    :param payload.user_id: The ID of the user being pruned. (:class:`int`, :class:`NoneType`)
    :param payload.pruned_users: Dict of pruned user accounts {user_id: {name: str, balance: int, created_at: int}}. (:class:`dict`)
    :method payload.to_dict: Returns a serializable dictionary representation of the payload. (:class:`dict`)
    :method payload.to_json: Returns the payload as JSON. (:class:`str`)


.. py:method:: red_bank_wipe(guild_id: int)

    Dispatched when a guild's bank is wiped. :code:`guild_id` will be the ID of the Guild that was wiped, -1 if all users were wiped (global bank), or None if all Guilds were wiped (local bank).

.. py:method:: red_bank_set_global(global_state: bool)

    Dispatched when the global bank is enabled or disabled. :code:`global_state` will be True if the Bank is being set to Global or False if the bank is being set to Local
