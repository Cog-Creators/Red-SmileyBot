.. rpc docs

===
RPC
===

.. important::

  RPC support is included in Red on a `provisional <developer-guarantees-exclusions>` basis.
  Backwards incompatible changes (up to and including removal of the RPC) may occur if deemed necessary.

V3 comes default with an internal RPC server that may be used to remotely control the bot in various ways.
Cogs must register functions to be exposed to RPC clients.
Each of those functions must only take JSON serializable parameters and must return JSON serializable objects.

To enable the internal RPC server you must start the bot with the ``--rpc`` flag.

********
Examples
********

.. code-block:: Python

    async def setup(bot):
        c = Cog()
        await bot.add_cog(c)
        bot.register_rpc_handler(c.rpc_method)

*******************************
Interacting with the RPC Server
*******************************

The RPC server opens a websocket bound to port ``6133`` on ``127.0.0.1``.
This is not configurable for security reasons as broad access to this server gives anyone complete control over your bot.
To access the server you must find a library that implements websocket based JSONRPC in the language of your choice.

There are a few built-in RPC methods to note:

* ``GET_METHODS`` - Returns a list of available RPC methods.
* ``GET_METHOD_INFO`` - Will return the docstring for an available RPC method. Useful for finding information about the method's parameters and return values.
* ``GET_TOPIC`` - Returns a list of available RPC message topics.
* ``GET_SUBSCRIPTIONS`` - Returns a list of RPC subscriptions.
* ``SUBSCRIBE`` - Subscribes to an available RPC message topic.
* ``UNSUBSCRIBE`` - Unsubscribes from an RPC message topic.

All RPC methods accept a list of parameters.
The built-in methods above expect their parameters to be in list format.

All cog-based methods expect their parameter list to take one argument, a JSON object, in the following format::

    params = [
        {
            "args": [],  # A list of positional arguments
            "kwargs": {},  # A dictionary of keyword arguments
        }
    ]

    # As an example, here's a call to "get_method_info"
    rpc_call("GET_METHOD_INFO", ["get_methods",])

    # And here's a call to "core__load"
    rpc_call("CORE__LOAD", {"args": [["general", "economy", "downloader"],], "kwargs": {}})

*************
API Reference
*************

Please see the :class:`redbot.core.bot.Red` class for details on the RPC handler register and unregister methods.
