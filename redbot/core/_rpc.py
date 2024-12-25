import asyncio
import sys
from typing import Optional

from aiohttp import web
from aiohttp_json_rpc import JsonRpc
from aiohttp_json_rpc.rpc import JsonRpcMethod

import logging

from redbot.core._cli import ExitCodes

log = logging.getLogger("red.rpc")

__all__ = ("RPC", "RPCMixin", "get_name")


def get_name(func, prefix=""):
    class_name = prefix or func.__self__.__class__.__name__.lower()
    func_name = func.__name__.strip("_")
    if class_name == "redrpc":
        return func_name.upper()
    return f"{class_name}__{func_name}".upper()


class RedRpc(JsonRpc):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_methods(("", self.get_method_info))

    def _add_method(self, method, name="", prefix=""):
        if not asyncio.iscoroutinefunction(method):
            return

        name = name or get_name(method, prefix)

        self.methods[name] = JsonRpcMethod(method)

    def remove_method(self, method):
        meth_name = get_name(method)
        new_methods = {}
        for name, meth in self.methods.items():
            if name != meth_name:
                new_methods[name] = meth
        self.methods = new_methods

    def remove_methods(self, prefix: str):
        new_methods = {}
        for name, meth in self.methods.items():
            splitted = name.split("__")
            if len(splitted) < 2 or splitted[0] != prefix:
                new_methods[name] = meth
        self.methods = new_methods

    async def get_method_info(self, request):
        method_name = request.params[0]
        if method_name in self.methods:
            return self.methods[method_name].__doc__
        return "No docstring available."


class RPC:
    """
    RPC server manager.
    """

    app: web.Application
    _rpc: RedRpc
    _runner: web.AppRunner

    def __init__(self):
        self._site: Optional[web.TCPSite] = None
        self._started = False

    async def _pre_login(self) -> None:
        self.app = web.Application()
        self._rpc = RedRpc()
        self.app.router.add_route("*", "/", self._rpc.handle_request)

        self._runner = web.AppRunner(self.app)

    async def initialize(self, port: int):
        """
        Finalizes the initialization of the RPC server and allows it to begin
        accepting queries.
        """
        try:
            # This ensures self._started can't be assigned
            # except with both other functions
            # and isn't subject to a really really stupid but complex
            # issue on windows with catching specific
            # exceptions related to shutdown conditions in asyncio applications.
            self._started, _discard, self._site = (
                True,
                await self._runner.setup(),
                web.TCPSite(
                    self._runner,
                    host="127.0.0.1",
                    port=port,
                    shutdown_timeout=120
                    # Give the RPC server 2 minutes to finish up, else slap it!
                    # Seems like a reasonable time. See Red#6391
                ),
            )
        except Exception as exc:
            log.exception("RPC setup failure", exc_info=exc)
            sys.exit(ExitCodes.CRITICAL)
        else:
            await self._site.start()
            log.debug("Created RPC server listener on port %s", port)

    async def close(self):
        """
        Closes the RPC server.
        """
        if self._started:
            await self.app.shutdown()
            await self._runner.cleanup()

    def add_method(self, method, prefix: str = None):
        if prefix is None:
            prefix = method.__self__.__class__.__name__.lower()

        if not asyncio.iscoroutinefunction(method):
            raise TypeError("RPC methods must be coroutines.")

        self._rpc.add_methods((prefix, method))

    def add_multi_method(self, *methods, prefix: str = None):
        if not all(asyncio.iscoroutinefunction(m) for m in methods):
            raise TypeError("RPC methods must be coroutines.")

        for method in methods:
            self.add_method(method, prefix=prefix)

    def remove_method(self, method):
        self._rpc.remove_method(method)

    def remove_methods(self, prefix: str):
        self._rpc.remove_methods(prefix)


class RPCMixin:
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.rpc = RPC()

        self.rpc_handlers = {}  # Uppercase cog name to method

    async def _pre_login(self) -> None:
        await self.rpc._pre_login()

    def register_rpc_handler(self, method):
        """
        Registers a method to act as an RPC handler if the internal RPC server is active.

        When calling this method through the RPC server, use the naming scheme
        "cogname__methodname".

        .. important::

            All parameters to RPC handler methods must be JSON serializable objects.
            The return value of handler methods must also be JSON serializable.

        .. important::
            RPC support is included in Red on a `provisional <developer-guarantees-exclusions>` basis.
            Backwards incompatible changes (up to and including removal of the RPC) may occur if deemed necessary.

        Parameters
        ----------
        method : coroutine
            The method to register with the internal RPC server.
        """
        self.rpc.add_method(method)

        cog_name = method.__self__.__class__.__name__.upper()

        if cog_name not in self.rpc_handlers:
            self.rpc_handlers[cog_name] = []

        self.rpc_handlers[cog_name].append(method)

    def unregister_rpc_handler(self, method):
        """
        Deregisters an RPC method handler.

        This will be called automatically for you on cog unload and will pass silently if the
        method is not previously registered.

        .. important::
            RPC support is included in Red on a `provisional <developer-guarantees-exclusions>` basis.
            Backwards incompatible changes (up to and including removal of the RPC) may occur if deemed necessary.

        Parameters
        ----------
        method : coroutine
            The method to unregister from the internal RPC server.
        """
        self.rpc.remove_method(method)

        name = get_name(method)
        cog_name = name.split("__")[0]

        if cog_name in self.rpc_handlers:
            try:
                self.rpc_handlers[cog_name].remove(method)
            except ValueError:
                pass
