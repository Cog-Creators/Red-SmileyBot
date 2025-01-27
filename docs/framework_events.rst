.. framework events list

=============
Custom Events
=============

Bank
^^^^

.. py:method:: red_bank_set_global(global_state: bool)

    Dispatched when the Bank gets toggled between Global and Local. :code:`global_state` will be True if the Bank is being set to Global or False if the bank is being set to Local

.. py:method:: red_bank_set_balance(payload: redbot.core.bank.BankSetBalanceInformation)

    Dispatched when a user has their balance changed.

.. py:method:: red_bank_transfer_credits(payload: redbot.core.bank.BankTransferInformation)

    Dispatched when credits gets transfered from one user to another.

.. py:method:: red_bank_wipe(guild_id: int)
    
    Dispatched when the Bank gets wiped. :code:`guild_id` will be the ID of the Guild that was wiped, 0 if all Guilds were wiped (Bank is Local), or -1 if all Users were wiped (Bank is Global)

.. py:method:: red_bank_prune_accounts(payload: redbot.core.bank.BankPruneInformation)

    Dispatched when users get pruned from the Bank

RPC Server
^^^^^^^^^^

.. py:method:: Red.on_shutdown()

    Dispatched when the bot begins it's shutdown procedures.
