import asyncio
from pathlib import Path

import lavalink
from red_commons.logging import getLogger

from redbot.core import data_manager
from redbot.core.i18n import Translator
from ...manager import ServerManager
from ..abc import MixinMeta
from ..cog_utils import CompositeMetaClass

log = getLogger("red.cogs.Audio.cog.Tasks.lavalink")
_ = Translator("Audio", Path(__file__))


class LavalinkTasks(MixinMeta, metaclass=CompositeMetaClass):
    def lavalink_restart_connect(self, manual: bool = False) -> None:
        lavalink.unregister_event_listener(self.lavalink_event_handler)
        lavalink.unregister_update_listener(self.lavalink_update_handler)
        if self.lavalink_connect_task:
            self.lavalink_connect_task.cancel()
        if self._restore_task:
            self._restore_task.cancel()

        self._restore_task = None
        lavalink.register_event_listener(self.lavalink_event_handler)
        lavalink.register_update_listener(self.lavalink_update_handler)
        self.lavalink_connect_task = asyncio.create_task(
            self.lavalink_attempt_connect(manual=manual)
        )

    async def lavalink_attempt_connect(self, timeout: int = 50, manual: bool = False) -> None:
        self.lavalink_connection_aborted = False
        max_retries = 5
        retry_count = 0
        if nodes := lavalink.get_all_nodes():
            for node in nodes:
                await node.disconnect()
        # This ensures that the restore task is ended before this connect attempt is started up.
        if self._restore_task:
            self._restore_task.cancel()
        if self.managed_node_controller is not None:
            if not self.managed_node_controller._shutdown:
                await self.managed_node_controller.shutdown()
                await asyncio.sleep(5)
        await lavalink.close(self.bot)
        while retry_count < max_retries:
            configs = await self.config.all()
            external = configs["use_external_lavalink"]
            java_exec = configs["java_exc_path"]
            if external is False:
                # Change these values to use whatever is set on the YAML
                host = configs["yaml"]["server"]["address"]
                port = configs["yaml"]["server"]["port"]
                password = configs["yaml"]["lavalink"]["server"]["password"]
                secured = False
                # Make this timeout customizable for lower powered machines?
                self.managed_node_controller = ServerManager(
                    self.config, timeout=60, download_timeout=60 * 3, cog=self
                )
                try:
                    await self.managed_node_controller.start(java_exec)
                    # timeout is the same as ServerManager.timeout -
                    # 60s in case of ServerManager(self.config, timeout=60)
                    await self.managed_node_controller.wait_until_ready()
                except asyncio.TimeoutError:
                    if self.managed_node_controller is not None:
                        await self.managed_node_controller.shutdown()
                    if self.lavalink_connection_aborted is not True:
                        log.critical(
                            "Managed node startup timeout, aborting managed node startup."
                        )
                    self.lavalink_connection_aborted = True
                    return
                except Exception as exc:
                    log.exception(
                        "Unhandled exception whilst starting managed Lavalink node, "
                        "aborting...",
                        exc_info=exc,
                    )
                    self.lavalink_connection_aborted = True
                    if self.managed_node_controller is not None:
                        await self.managed_node_controller.shutdown()
                    return
                else:
                    break
            else:
                host = configs["host"]
                password = configs["password"]
                port = configs["ws_port"]
                secured = configs["secured_ws"]
                break
        else:
            log.critical(
                "Setting up the managed Lavalink node failed after multiple attempts. "
                "See above logs for details."
            )
            self.lavalink_connection_aborted = True
            if self.managed_node_controller is not None:
                await self.managed_node_controller.shutdown()
            return
        log.debug("Attempting to initialize Red-Lavalink")
        retry_count = 0
        while retry_count < max_retries:
            try:
                await lavalink.initialize(
                    bot=self.bot,
                    host=host,
                    password=password,
                    port=port,
                    timeout=timeout,
                    resume_key=f"Red-Core-Audio-{self.bot.user.id}-{data_manager.instance_name()}",
                    secured=secured,
                )
            except lavalink.AbortingNodeConnection:
                await lavalink.close(self.bot)
                log.warning("Connection attempt to Lavalink node aborted")
                return
            except asyncio.TimeoutError:
                await lavalink.close(self.bot)
                log.warning("Connecting to Lavalink node timed out, retrying...")
                retry_count += 1
                await asyncio.sleep(1)  # prevent busylooping
            except Exception as exc:
                log.exception(
                    "Unhandled exception whilst connecting to Lavalink node, aborting...",
                    exc_info=exc,
                )
                await lavalink.close(self.bot)
                self.lavalink_connection_aborted = True
                return
            else:
                break
        else:
            self.lavalink_connection_aborted = True
            log.critical(
                "Connecting to the Lavalink node failed after multiple attempts. "
                "See above tracebacks for details."
            )
            await lavalink.close(self.bot)
            return
        if external:
            await asyncio.sleep(5)
        self._restore_task = asyncio.create_task(self.restore_players())
