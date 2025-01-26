import re
from io import BytesIO
from pathlib import Path

import discord
import lavalink
import yaml
from red_commons.logging import getLogger

from redbot.core import commands
from redbot.core.data_manager import cog_data_path
from redbot.core.i18n import Translator
from redbot.core.utils.chat_formatting import box, humanize_list, inline

from ..abc import MixinMeta
from ..cog_utils import CompositeMetaClass
from ...managed_node import version_pins
from ...utils import (
    MAX_JAVA_RAM,
    DEFAULT_LAVALINK_YAML,
    DEFAULT_LAVALINK_SETTINGS,
    change_dict_naming_convention,
    has_managed_server,
    has_unmanaged_server,
    sizeof_fmt,
    get_max_allocation_size,
)

log = getLogger("red.cogs.Audio.cog.Commands.lavalink_setup")
_ = Translator("Audio", Path(__file__))


class LavalinkSetupJavaCommand(commands.Command):
    def format_text_for_context(self, ctx: commands.Context, text: str) -> str:
        text = super().format_text_for_context(ctx, text)
        return text.format(
            supported_java_versions=humanize_list(
                list(map(str, version_pins.SUPPORTED_JAVA_VERSIONS))
            ),
        )


class LavalinkSetupCommands(MixinMeta, metaclass=CompositeMetaClass):
    @commands.group(name="llset")
    @commands.is_owner()
    @commands.bot_has_permissions(embed_links=True)
    async def command_llset(self, ctx: commands.Context):
        """`Dangerous commands` Manage Lavalink node configuration settings.

        This command block holds all commands to configure an unmanaged (user maintained) or managed (bot maintained) Lavalink node.

        You should not mess with any command in here unless you have a valid reason to,
        i.e. been told by someone in the Red-Discord Bot support server to do so.
        All the commands in here have the potential to break the Audio cog.
        """

    @command_llset.command(name="java", cls=LavalinkSetupJavaCommand)
    @has_managed_server()
    async def command_llset_java(self, ctx: commands.Context, *, java_path: str = "java"):
        """Change your Java executable path.

        This command shouldn't need to be used most of the time, and is only useful if the host machine has conflicting Java versions.

        If changing this make sure that the Java executable you set is supported by Audio.
        The current supported versions are Java {supported_java_versions}.

        Enter nothing or "java" to reset it back to default.
        """
        if java_path == "java":
            await self.config.java_exc_path.clear()
            await self.send_embed_msg(
                ctx,
                title=_("Java Executable Reset"),
                description=_(
                    "Audio will now use `java` to run your managed Lavalink node. "
                    "Run `{p}{cmd}` for it to take effect."
                ).format(p=ctx.prefix, cmd=self.command_audioset_restart.qualified_name),
            )
        else:
            exc = Path(java_path)
            exc_absolute = exc.absolute()
            if not exc.exists() or not exc.is_file():
                return await self.send_embed_msg(
                    ctx,
                    title=_("Invalid Environment"),
                    description=_("`{java_path}` is not a valid executable").format(
                        java_path=exc_absolute
                    ),
                )
            await self.config.java_exc_path.set(str(exc_absolute))
            await self.send_embed_msg(
                ctx,
                title=_("Java Executable Changed"),
                description=_(
                    "Audio will now use `{exc}` to run your managed Lavalink node. "
                    "Run `{p}{cmd}` for it to take effect."
                ).format(
                    exc=exc_absolute,
                    p=ctx.prefix,
                    cmd=self.command_audioset_restart.qualified_name,
                ),
            )

    @command_llset.command(name="heapsize", aliases=["hs", "ram", "memory"])
    @has_managed_server()
    async def command_llset_heapsize(self, ctx: commands.Context, size: str = MAX_JAVA_RAM):
        """Set the managed Lavalink node maximum heap-size.

        By default, this value is 50% of available RAM in the host machine represented by [1-1024][M|G] (256M, 256G for example)

        This value only represents the maximum amount of RAM allowed to be used at any given point, and does not mean that the managed Lavalink node will always use this amount of RAM.

        To reset this value to the default, run the command without any input.
        """

        async def validate_input(cog, arg):
            match = re.match(r"^(\d+)([MG])$", arg, flags=re.IGNORECASE)
            if not match:
                await ctx.send(_("Heap-size must be a valid measure of size, e.g. 256M, 256G"))
                return 0
            input_in_bytes = int(match.group(1)) * 1024 ** (
                2 if match.group(2).lower() == "m" else 3
            )
            if input_in_bytes < 64 * 1024**2:
                await ctx.send(
                    _(
                        "Heap-size must be at least 64M, however it is recommended to have it set to at least 1G."
                    )
                )
                return 0
            elif (
                input_in_bytes
                > (meta := get_max_allocation_size(cog.managed_node_controller._java_exc))[0]
            ):
                if meta[1]:
                    await ctx.send(
                        _(
                            "Heap-size must be less than your system RAM. "
                            "You currently have {ram_in_bytes} of RAM available."
                        ).format(ram_in_bytes=inline(sizeof_fmt(meta[0])))
                    )
                else:
                    await ctx.send(
                        _(
                            "Heap-size must be less than {limit} due to your system limitations."
                        ).format(limit=inline(sizeof_fmt(meta[0])))
                    )
                return 0
            return 1

        if not (await validate_input(self, size)):
            return
        size = size.upper()
        await self.config.java.Xmx.set(size)
        await self.send_embed_msg(
            ctx,
            title=_("Setting Changed"),
            description=_(
                "Managed node's heap-size set to {bytes}.\n\n"
                "Run `{p}{cmd}` for it to take effect."
            ).format(
                bytes=inline(size), p=ctx.prefix, cmd=self.command_audioset_restart.qualified_name
            ),
        )

    @command_llset.command(name="unmanaged", aliases=["external"])
    async def command_llset_unmanaged(self, ctx: commands.Context):
        """Toggle using external (unmanaged) Lavalink nodes - requires an existing Lavalink node for Audio to work, if enabled.

        This command disables the managed Lavalink server. If you do not have another Lavalink node set up, you will be unable to use Audio while this is enabled.
        """
        external = await self.config.use_external_lavalink()
        await self.config.use_external_lavalink.set(not external)
        async with ctx.typing():
            if external:
                embed = discord.Embed(
                    title=_("Setting Changed"),
                    description=_("Unmanaged Lavalink server: {true_or_false}.").format(
                        true_or_false=inline(_("Enabled") if not external else _("Disabled"))
                    ),
                )
                await self.send_embed_msg(ctx, embed=embed)
            else:
                await self.send_embed_msg(
                    ctx,
                    title=_("Setting Changed"),
                    description=_("Unmanaged Lavalink server: {true_or_false}.").format(
                        true_or_false=inline(_("Enabled") if not external else _("Disabled"))
                    ),
                )
            try:
                await lavalink.close(self.bot)
                self.lavalink_restart_connect(manual=True)
            except ProcessLookupError:
                await self.send_embed_msg(
                    ctx,
                    title=_("Failed To Shutdown Lavalink"),
                    description=_("Please reload Audio (`{prefix}reload audio`).").format(
                        prefix=ctx.prefix
                    ),
                )

    @command_llset.command(name="host")
    @has_unmanaged_server()
    async def command_llset_host(
        self, ctx: commands.Context, host: str = DEFAULT_LAVALINK_SETTINGS["host"]
    ):
        """Set the Lavalink node host.

        This command sets the connection host which Audio will use to connect to an unmanaged Lavalink node.
        """
        await self.config.host.set(host)
        await self.send_embed_msg(
            ctx,
            title=_("Setting Changed"),
            description=_(
                "Unmanaged Lavalink node host set to {host}. "
                "Run `{p}{cmd}` for it to take effect."
            ).format(
                host=inline(host), p=ctx.prefix, cmd=self.command_audioset_restart.qualified_name
            ),
        )

    @command_llset.command(name="password", aliases=["pass", "token"])
    @has_unmanaged_server()
    async def command_llset_password(
        self, ctx: commands.Context, *, password: str = DEFAULT_LAVALINK_SETTINGS["password"]
    ):
        """Set the Lavalink node password.

        This command sets the connection password which Audio will use to connect to an unmanaged Lavalink node.
        """

        await self.config.password.set(str(password))
        await self.send_embed_msg(
            ctx,
            title=_("Setting Changed"),
            description=_(
                "Unmanaged Lavalink node password set to {password}. "
                "Run `{p}{cmd}` for it to take effect."
            ).format(
                password=inline(password),
                p=ctx.prefix,
                cmd=self.command_audioset_restart.qualified_name,
            ),
        )

    @command_llset.command(name="port")
    @has_unmanaged_server()
    async def command_llset_wsport(
        self, ctx: commands.Context, port: int = DEFAULT_LAVALINK_SETTINGS["ws_port"]
    ):
        """Set the Lavalink node port.

        This command sets the connection port which Audio will use to connect to an unmanaged Lavalink node.
        Set port to -1 to disable the port and connect to the specified host via ports 80/443
        """
        if port < 0:
            port = None
        elif port > 65535:
            return await self.send_embed_msg(
                ctx,
                title=_("Setting Not Changed"),
                description=_("A port must be between 0 and 65535."),
            )
        await self.config.ws_port.set(port)
        await self.send_embed_msg(
            ctx,
            title=_("Setting Changed"),
            description=_(
                "Unmanaged Lavalink node port set to {port}. "
                "Run `{p}{cmd}` for it to take effect."
            ).format(
                port=inline(str(port)),
                p=ctx.prefix,
                cmd=self.command_audioset_restart.qualified_name,
            ),
        )

    @command_llset.command(name="secured", aliases=["wss"])
    @has_unmanaged_server()
    async def command_llset_secured(self, ctx: commands.Context):
        """Set the Lavalink node connection to secured.

        This toggle sets the connection type to secured or unsecured when connecting to an unmanaged Lavalink node.
        """
        state = await self.config.secured_ws()
        await self.config.secured_ws.set(not state)

        if not state:
            await self.send_embed_msg(
                ctx,
                title=_("Setting Changed"),
                description=_(
                    "Unmanaged Lavalink node will now connect using the secured {secured_protocol} protocol.\n\n"
                    "Run `{p}{cmd}` for it to take effect."
                ).format(
                    p=ctx.prefix,
                    cmd=self.command_audioset_restart.qualified_name,
                    secured_protocol=inline("wss://"),
                ),
            )
        else:
            await self.send_embed_msg(
                ctx,
                title=_("Setting Changed"),
                description=_(
                    "Unmanaged Lavalink node will no longer connect using the secured "
                    "{secured_protocol} protocol and will use {unsecured_protocol} instead.\n\n"
                    "Run `{p}{cmd}` for it to take effect."
                ).format(
                    p=ctx.prefix,
                    cmd=self.command_audioset_restart.qualified_name,
                    unsecured_protocol=inline("ws://"),
                    secured_protocol=inline("wss://"),
                ),
            )

    @command_llset.command(name="info", aliases=["settings"])
    async def command_llset_info(self, ctx: commands.Context):
        """Display Lavalink connection settings."""
        configs = await self.config.all()

        if configs["use_external_lavalink"]:
            msg = "----" + _("Connection Settings") + "----        \n"
            msg += _("Host:             [{host}]\n").format(host=configs["host"])
            msg += _("Port:             [{port}]\n").format(
                port=configs["ws_port"] or _("Default HTTP/HTTPS port")
            )
            msg += _("Password:         [{password}]\n").format(password=configs["password"])
            msg += _("Secured:          [{state}]\n").format(state=configs["secured_ws"])

        else:
            msg = "----" + _("Lavalink Node Settings") + "----        \n"
            msg += _("Host:             [{host}]\n").format(
                host=configs["yaml"]["server"]["address"]
            )
            msg += _("Port:             [{port}]\n").format(port=configs["yaml"]["server"]["port"])
            msg += _("Password:         [{password}]\n").format(
                password=configs["yaml"]["lavalink"]["server"]["password"]
            )
            msg += _("Initial Heapsize: [{xms}]\n").format(xms=configs["java"]["Xms"])
            msg += _("Max Heapsize:     [{xmx}]\n").format(xmx=configs["java"]["Xmx"])
            msg += _("Java exec:        [{java_exc_path}]\n").format(
                java_exc_path=configs["java_exc_path"]
            )

        try:
            await self.send_embed_msg(ctx.author, description=box(msg, lang="ini"))
            await ctx.tick()
        except discord.HTTPException:
            await ctx.send(_("I need to be able to DM you to send you this info."))

    @command_llset.command(name="yaml", aliases=["yml"])
    @has_managed_server()
    async def command_llset_yaml(self, ctx: commands.Context):
        """Uploads a copy of the application.yml file used by the managed Lavalink node."""
        configs = change_dict_naming_convention(await self.config.yaml.all())
        data = yaml.safe_dump(configs)
        playlist_data = data.encode("utf-8")
        to_write = BytesIO()
        to_write.write(playlist_data)
        to_write.seek(0)
        datapath = cog_data_path(raw_name="Audio")
        temp_file = datapath / f"application.dump.yaml"
        try:
            with temp_file.open("wb") as application_file:
                application_file.write(to_write.read())
            await ctx.author.send(
                file=discord.File(str(temp_file)),
            )
            await ctx.tick()
        except discord.HTTPException:
            await ctx.send(_("I need to be able to DM you to send you this info."))
        finally:
            temp_file.unlink()

    @command_llset.group(name="config", aliases=["conf"])
    @has_managed_server()
    async def command_llset_config(self, ctx: commands.Context):
        """Configure the managed Lavalink node runtime options.

        All settings under this group will likely cause Audio to malfunction if changed from their defaults, only change settings here if you have been advised to by support.
        """

    @command_llset_config.group(name="server")
    async def command_llset_config_server(self, ctx: commands.Context):
        """Configure the managed node authorization and connection settings."""

    @command_llset_config.command(name="bind", aliases=["host", "address"])
    async def command_llset_config_host(
        self, ctx: commands.Context, *, host: str = DEFAULT_LAVALINK_YAML["yaml__server__address"]
    ):
        """`Dangerous command` Set the managed Lavalink node's binding IP address.

        This value by default is `localhost` which will restrict the server to only localhost apps by default, changing this will likely break the managed Lavalink node if you don't know what you are doing.
        """

        await self.config.yaml.server.address.set(host)
        await self.send_embed_msg(
            ctx,
            title=_("Setting Changed"),
            description=_(
                "Managed node will now accept connection on {host}.\n\n"
                "Run `{p}{cmd}` for it to take effect."
            ).format(
                host=inline(host), p=ctx.prefix, cmd=self.command_audioset_restart.qualified_name
            ),
        )

    @command_llset_config.command(name="token", aliases=["password", "pass"])
    async def command_llset_config_token(
        self,
        ctx: commands.Context,
        *,
        password: str = DEFAULT_LAVALINK_YAML["yaml__lavalink__server__password"],
    ):
        """Set the managed Lavalink node's connection password.

        This is the password required for Audio to connect to the managed Lavalink node.
        The value by default is `youshallnotpass`.
        """
        await self.config.yaml.lavalink.server.password.set(password)
        await self.send_embed_msg(
            ctx,
            title=_("Setting Changed"),
            description=_(
                "Managed node will now accept {password} as the authorization token.\n\n"
                "Run `{p}{cmd}` for it to take effect."
            ).format(
                password=inline(password),
                p=ctx.prefix,
                cmd=self.command_audioset_restart.qualified_name,
            ),
        )

    @command_llset_config.command(name="port")
    async def command_llset_config_port(
        self, ctx: commands.Context, *, port: int = DEFAULT_LAVALINK_YAML["yaml__server__port"]
    ):
        """`Dangerous command` Set the managed Lavalink node's connection port.

        This port is the port the managed Lavalink node binds to, you should only change this if there is a conflict with the default port because you already have an application using port 2333 on this device.

        The value by default is `2333`.
        """
        if 1024 > port or port > 49151:
            return await self.send_embed_msg(
                ctx,
                title=_("Setting Not Changed"),
                description=_("The port must be between 1024 and 49151."),
            )

        await self.config.yaml.server.port.set(port)
        await self.send_embed_msg(
            ctx,
            title=_("Setting Changed"),
            description=_(
                "Managed node will now accept connections on {port}.\n\n"
                "Run `{p}{cmd}` for it to take effect."
            ).format(
                port=inline(str(port)),
                p=ctx.prefix,
                cmd=self.command_audioset_restart.qualified_name,
            ),
        )

    @command_llset_config.group(name="source")
    async def command_llset_config_source(self, ctx: commands.Context):
        """`Dangerous command` Toggle audio sources on/off.

        By default, all sources are enabled, you should only use commands here to disable a specific source if you have been advised to, disabling sources without background knowledge can cause Audio to break.
        """

    @command_llset_config_source.command(name="http")
    async def command_llset_config_source_http(self, ctx: commands.Context):
        """Toggle HTTP direct URL usage on or off.

        This source is used to allow playback from direct HTTP streams (this does not affect direct URL playback for the other sources).
        """
        state = await self.config.yaml.lavalink.server.sources.http()
        await self.config.yaml.lavalink.server.sources.http.set(not state)
        if not state:
            await self.send_embed_msg(
                ctx,
                title=_("Setting Changed"),
                description=_(
                    "Managed node will allow playback from direct URLs.\n\n"
                    "Run `{p}{cmd}` for it to take effect."
                ).format(p=ctx.prefix, cmd=self.command_audioset_restart.qualified_name),
            )
        else:
            await self.send_embed_msg(
                ctx,
                title=_("Setting Changed"),
                description=_(
                    "Managed node will not play from direct URLs anymore.\n\n"
                    "Run `{p}{cmd}` for it to take effect."
                ).format(p=ctx.prefix, cmd=self.command_audioset_restart.qualified_name),
            )

    @command_llset_config_source.command(name="bandcamp", aliases=["bc"])
    async def command_llset_config_source_bandcamp(self, ctx: commands.Context):
        """Toggle Bandcamp source on or off.

        This toggle controls the playback of all Bandcamp related content.
        """
        state = await self.config.yaml.bandcamp.http()
        await self.config.yaml.lavalink.server.sources.bandcamp.set(not state)
        if not state:
            await self.send_embed_msg(
                ctx,
                title=_("Setting Changed"),
                description=_(
                    "Managed node will allow playback from Bandcamp.\n\n"
                    "Run `{p}{cmd}` for it to take effect."
                ).format(p=ctx.prefix, cmd=self.command_audioset_restart.qualified_name),
            )
        else:
            await self.send_embed_msg(
                ctx,
                title=_("Setting Changed"),
                description=_(
                    "Managed node will not play from Bandcamp anymore.\n\n"
                    "Run `{p}{cmd}` for it to take effect."
                ).format(p=ctx.prefix, cmd=self.command_audioset_restart.qualified_name),
            )

    @command_llset_config_source.command(name="local")
    async def command_llset_config_source_local(self, ctx: commands.Context):
        """Toggle local file usage on or off.

        This toggle controls the playback of all local track content, usually found inside the `localtracks` folder.
        """
        state = await self.config.yaml.lavalink.server.sources.local()
        await self.config.yaml.lavalink.server.sources.local.set(not state)
        if not state:
            await self.send_embed_msg(
                ctx,
                title=_("Setting Changed"),
                description=_(
                    "Managed node will allow playback from local files.\n\n"
                    "Run `{p}{cmd}` for it to take effect."
                ).format(p=ctx.prefix, cmd=self.command_audioset_restart.qualified_name),
            )
        else:
            await self.send_embed_msg(
                ctx,
                title=_("Setting Changed"),
                description=_(
                    "Managed node will not play from local files anymore.\n\n"
                    "Run `{p}{cmd}` for it to take effect."
                ).format(p=ctx.prefix, cmd=self.command_audioset_restart.qualified_name),
            )

    @command_llset_config_source.command(name="soundcloud", aliases=["sc"])
    async def command_llset_config_source_soundcloud(self, ctx: commands.Context):
        """Toggle Soundcloud source on or off.

        This toggle controls the playback of all SoundCloud related content.
        """
        state = await self.config.yaml.lavalink.server.sources.soundcloud()
        await self.config.yaml.lavalink.server.sources.soundcloud.set(not state)
        if not state:
            await self.send_embed_msg(
                ctx,
                title=_("Setting Changed"),
                description=_(
                    "Managed node will allow playback from Soundcloud.\n\n"
                    "Run `{p}{cmd}` for it to take effect."
                ).format(p=ctx.prefix, cmd=self.command_audioset_restart.qualified_name),
            )
        else:
            await self.send_embed_msg(
                ctx,
                title=_("Setting Changed"),
                description=_(
                    "Managed node will not play from Soundcloud anymore.\n\n"
                    "Run `{p}{cmd}` for it to take effect."
                ).format(p=ctx.prefix, cmd=self.command_audioset_restart.qualified_name),
            )

    @command_llset_config_source.command(name="youtube", aliases=["yt"])
    async def command_llset_config_source_youtube(self, ctx: commands.Context):
        """`Dangerous command` Toggle YouTube source on or off (this includes Spotify).

        This toggle controls the playback of all YouTube and Spotify related content.
        """
        state = await self.config.yaml.lavalink.server.sources.youtube()
        await self.config.yaml.lavalink.server.sources.youtube.set(not state)
        if not state:
            await self.send_embed_msg(
                ctx,
                title=_("Setting Changed"),
                description=_(
                    "Managed node will allow playback from YouTube.\n\n"
                    "Run `{p}{cmd}` for it to take effect."
                ).format(p=ctx.prefix, cmd=self.command_audioset_restart.qualified_name),
            )
        else:
            await self.send_embed_msg(
                ctx,
                title=_("Setting Changed"),
                description=_(
                    "Managed node will not play from YouTube anymore.\n\n"
                    "Run `{p}{cmd}` for it to take effect."
                ).format(p=ctx.prefix, cmd=self.command_audioset_restart.qualified_name),
            )

    @command_llset_config_source.command(name="twitch")
    async def command_llset_config_source_twitch(self, ctx: commands.Context):
        """Toggle Twitch source on or off.

        This toggle controls the playback of all Twitch related content.
        """
        state = await self.config.yaml.lavalink.server.sources.twitch()
        await self.config.yaml.lavalink.server.sources.twitch.set(not state)
        if not state:
            await self.send_embed_msg(
                ctx,
                title=_("Setting Changed"),
                description=_(
                    "Managed node will allow playback from Twitch.\n\n"
                    "Run `{p}{cmd}` for it to take effect."
                ).format(p=ctx.prefix, cmd=self.command_audioset_restart.qualified_name),
            )
        else:
            await self.send_embed_msg(
                ctx,
                title=_("Setting Changed"),
                description=_(
                    "Managed node will not play from Twitch anymore.\n\n"
                    "Run `{p}{cmd}` for it to take effect."
                ).format(p=ctx.prefix, cmd=self.command_audioset_restart.qualified_name),
            )

    @command_llset_config_source.command(name="vimeo")
    async def command_llset_config_source_vimeo(self, ctx: commands.Context):
        """Toggle Vimeo source on or off.

        This toggle controls the playback of all Vimeo related content.
        """
        state = await self.config.yaml.lavalink.server.sources.vimeo()
        await self.config.yaml.lavalink.server.sources.vimeo.set(not state)
        if not state:
            await self.send_embed_msg(
                ctx,
                title=_("Setting Changed"),
                description=_(
                    "Managed node will allow playback from Vimeo.\n\n"
                    "Run `{p}{cmd}` for it to take effect."
                ).format(p=ctx.prefix, cmd=self.command_audioset_restart.qualified_name),
            )
        else:
            await self.send_embed_msg(
                ctx,
                title=_("Setting Changed"),
                description=_(
                    "Managed node will not play from Vimeo anymore.\n\n"
                    "Run `{p}{cmd}` for it to take effect."
                ).format(p=ctx.prefix, cmd=self.command_audioset_restart.qualified_name),
            )

    @command_llset_config_server.command(name="framebuffer", aliases=["fb", "frame"])
    async def command_llset_config_server_framebuffer(
        self,
        ctx: commands.Context,
        *,
        milliseconds: int = DEFAULT_LAVALINK_YAML["yaml__lavalink__server__frameBufferDurationMs"],
    ):
        """`Dangerous command` Set the managed Lavalink node framebuffer size.

        Only change this if you have been directly advised to, changing it can cause significant playback issues.
        """
        if milliseconds < 100:
            return await self.send_embed_msg(
                ctx,
                title=_("Setting Not Changed"),
                description=_("The lowest value the framebuffer can be set to is 100ms."),
            )
        await self.config.yaml.lavalink.server.frameBufferDurationMs.set(milliseconds)
        await self.send_embed_msg(
            ctx,
            title=_("Setting Changed"),
            description=_(
                "Managed node's bufferDurationMs set to {milliseconds}.\n\n"
                "Run `{p}{cmd}` for it to take effect."
            ).format(
                milliseconds=inline(str(milliseconds)),
                p=ctx.prefix,
                cmd=self.command_audioset_restart.qualified_name,
            ),
        )

    @command_llset_config_server.command(name="buffer", aliases=["b"])
    async def command_llset_config_server_buffer(
        self,
        ctx: commands.Context,
        *,
        milliseconds: int = DEFAULT_LAVALINK_YAML["yaml__lavalink__server__bufferDurationMs"],
    ):
        """`Dangerous command`  Set the managed Lavalink node JDA-NAS buffer size.

        Only change this if you have been directly advised to, changing it can cause significant playback issues.
        """
        if milliseconds < 100:
            return await self.send_embed_msg(
                ctx,
                title=_("Setting Not Changed"),
                description=_("The lowest value the buffer may be is 100ms."),
            )
        await self.config.yaml.lavalink.server.bufferDurationMs.set(milliseconds)
        await self.send_embed_msg(
            ctx,
            title=_("Setting Changed"),
            description=_(
                "Managed node's bufferDurationMs set to {milliseconds}.\n\n"
                "Run `{p}{cmd}` for it to take effect."
            ).format(
                milliseconds=inline(str(milliseconds)),
                p=ctx.prefix,
                cmd=self.command_audioset_restart.qualified_name,
            ),
        )

    @command_llset.command(name="reset")
    async def command_llset_reset(self, ctx: commands.Context):
        """Reset all `llset` changes back to their default values."""
        async with ctx.typing():
            async with self.config.all() as global_data:
                del global_data["yaml"]
                for key in (*DEFAULT_LAVALINK_SETTINGS.keys(), *DEFAULT_LAVALINK_YAML.keys()):
                    if key in global_data:
                        del global_data[key]
                del global_data["java"]
                del global_data["java_exc_path"]
                global_data["use_external_lavalink"] = False

            try:
                await lavalink.close(self.bot)
                self.lavalink_restart_connect(manual=True)
            except ProcessLookupError:
                await self.send_embed_msg(
                    ctx,
                    title=_("Failed To Shutdown Lavalink Node"),
                    description=_("Please reload Audio (`{prefix}reload audio`).").format(
                        prefix=ctx.prefix
                    ),
                )
