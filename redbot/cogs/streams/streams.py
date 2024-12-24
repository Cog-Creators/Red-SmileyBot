import discord
from redbot.core.utils.chat_formatting import humanize_list
from redbot.core.bot import Red
from redbot.core import commands, Config
from redbot.core.i18n import cog_i18n, Translator, set_contextual_locales_from_guild
from redbot.core.utils._internal_utils import send_to_owners_with_prefix_replaced
from redbot.core.utils.chat_formatting import escape, inline, pagify

from .streamtypes import (
    PicartoStream,
    Stream,
    TwitchStream,
    YoutubeStream,
)
from .errors import (
    APIError,
    InvalidTwitchCredentials,
    InvalidYoutubeCredentials,
    OfflineStream,
    StreamNotFound,
    StreamsError,
    YoutubeQuotaExceeded,
)
from . import streamtypes as _streamtypes

import re
import logging
import asyncio
import aiohttp
import contextlib
from datetime import datetime
from collections import defaultdict
from typing import Optional, List, Tuple, Union, Dict

MAX_RETRY_COUNT = 10

_ = Translator("Streams", __file__)
log = logging.getLogger("red.core.cogs.Streams")


@cog_i18n(_)
class Streams(commands.Cog):
    """Various commands relating to streaming platforms.

    You can check if a Twitch, YouTube or Picarto stream is
    currently live.
    """

    global_defaults = {
        "refresh_timer": 300,
        "tokens": {},
        "streams": [],
        "notified_owner_missing_twitch_secret": False,
    }

    guild_defaults = {
        "autodelete": False,
        "mention_everyone": False,
        "mention_here": False,
        "live_message_mention": False,
        "live_message_nomention": False,
        "ignore_reruns": False,
        "ignore_schedule": False,
        "use_buttons": False,
    }

    role_defaults = {"mention": False}

    def __init__(self, bot: Red):
        super().__init__()
        self.config: Config = Config.get_conf(self, 26262626)
        self.ttv_bearer_cache: dict = {}
        self.config.register_global(**self.global_defaults)
        self.config.register_guild(**self.guild_defaults)
        self.config.register_role(**self.role_defaults)

        self.bot: Red = bot

        self.streams: List[Stream] = []
        self.task: Optional[asyncio.Task] = None

        self.yt_cid_pattern = re.compile("^UC[-_A-Za-z0-9]{21}[AQgw]$")

    async def red_delete_data_for_user(self, **kwargs):
        """Nothing to delete"""
        return

    def check_name_or_id(self, data: str) -> bool:
        matched = self.yt_cid_pattern.fullmatch(data)
        if matched is None:
            return True
        return False

    async def cog_load(self) -> None:
        """Should be called straight after cog instantiation."""
        try:
            await self.move_api_keys()
            await self.get_twitch_bearer_token()
            self.streams = await self.load_streams()
            self.task = asyncio.create_task(self._stream_alerts())
        except Exception as error:
            log.exception("Failed to initialize Streams cog:", exc_info=error)

    @commands.Cog.listener()
    async def on_red_api_tokens_update(self, service_name, api_tokens):
        if service_name == "twitch":
            await self.get_twitch_bearer_token(api_tokens)

    async def move_api_keys(self) -> None:
        """Move the API keys from cog stored config to core bot config if they exist."""
        tokens = await self.config.tokens()
        youtube = await self.bot.get_shared_api_tokens("youtube")
        twitch = await self.bot.get_shared_api_tokens("twitch")
        for token_type, token in tokens.items():
            if token_type == "YoutubeStream" and "api_key" not in youtube:
                await self.bot.set_shared_api_tokens("youtube", api_key=token)
            if token_type == "TwitchStream" and "client_id" not in twitch:
                # Don't need to check Community since they're set the same
                await self.bot.set_shared_api_tokens("twitch", client_id=token)
        await self.config.tokens.clear()

    async def _notify_owner_about_missing_twitch_secret(self) -> None:
        message = _(
            "You need a client secret key if you want to use the Twitch API on this cog.\n"
            "Follow these steps:\n"
            "1. Go to this page: {link}.\n"
            '2. Click "Manage" on your application.\n'
            '3. Click on "New secret".\n'
            "5. Copy your client ID and your client secret into:\n"
            "{command}"
            "\n\n"
            "Note: These tokens are sensitive and should only be used in a private channel "
            "or in DM with the bot."
        ).format(
            link="https://dev.twitch.tv/console/apps",
            command=inline(
                "[p]set api twitch client_id {} client_secret {}".format(
                    _("<your_client_id_here>"), _("<your_client_secret_here>")
                )
            ),
        )
        await send_to_owners_with_prefix_replaced(self.bot, message)
        await self.config.notified_owner_missing_twitch_secret.set(True)

    async def get_twitch_bearer_token(self, api_tokens: Optional[Dict] = None) -> None:
        tokens = (
            await self.bot.get_shared_api_tokens("twitch") if api_tokens is None else api_tokens
        )
        if tokens.get("client_id"):
            notified_owner_missing_twitch_secret = (
                await self.config.notified_owner_missing_twitch_secret()
            )
            try:
                tokens["client_secret"]
                if notified_owner_missing_twitch_secret is True:
                    await self.config.notified_owner_missing_twitch_secret.set(False)
            except KeyError:
                if notified_owner_missing_twitch_secret is False:
                    asyncio.create_task(self._notify_owner_about_missing_twitch_secret())
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://id.twitch.tv/oauth2/token",
                params={
                    "client_id": tokens.get("client_id", ""),
                    "client_secret": tokens.get("client_secret", ""),
                    "grant_type": "client_credentials",
                },
            ) as req:
                try:
                    data = await req.json()
                except aiohttp.ContentTypeError:
                    data = {}

                if req.status == 200:
                    pass
                elif req.status == 400 and data.get("message") == "invalid client":
                    log.error(
                        "Twitch API request failed authentication: set Client ID is invalid."
                    )
                elif req.status == 403 and data.get("message") == "invalid client secret":
                    log.error(
                        "Twitch API request failed authentication: set Client Secret is invalid."
                    )
                elif "message" in data:
                    log.error(
                        "Twitch OAuth2 API request failed with status code %s"
                        " and error message: %s",
                        req.status,
                        data["message"],
                    )
                else:
                    log.error("Twitch OAuth2 API request failed with status code %s", req.status)

                if req.status != 200:
                    return

        self.ttv_bearer_cache = data
        self.ttv_bearer_cache["expires_at"] = datetime.now().timestamp() + data.get("expires_in")

    async def maybe_renew_twitch_bearer_token(self) -> None:
        if self.ttv_bearer_cache:
            if self.ttv_bearer_cache["expires_at"] - datetime.now().timestamp() <= 60:
                await self.get_twitch_bearer_token()

    @commands.guild_only()
    @commands.command()
    async def twitchstream(self, ctx: commands.Context, channel_name: str):
        """Check if a Twitch channel is live."""
        await self.maybe_renew_twitch_bearer_token()
        token = (await self.bot.get_shared_api_tokens("twitch")).get("client_id")
        stream = TwitchStream(
            _bot=self.bot,
            name=channel_name,
            token=token,
            bearer=self.ttv_bearer_cache.get("access_token", None),
        )
        await self.check_online(ctx, stream)

    @commands.guild_only()
    @commands.command()
    @commands.cooldown(1, 30, commands.BucketType.guild)
    async def youtubestream(self, ctx: commands.Context, channel_id_or_name: str):
        """Check if a YouTube channel is live."""
        # TODO: Write up a custom check to look up cooldown set by botowner
        # This check is here to avoid people spamming this command and eating up quota
        apikey = await self.bot.get_shared_api_tokens("youtube")
        is_name = self.check_name_or_id(channel_id_or_name)
        if is_name:
            stream = YoutubeStream(
                _bot=self.bot, name=channel_id_or_name, token=apikey, config=self.config
            )
        else:
            stream = YoutubeStream(
                _bot=self.bot, id=channel_id_or_name, token=apikey, config=self.config
            )
        await self.check_online(ctx, stream)

    @commands.guild_only()
    @commands.command()
    async def picarto(self, ctx: commands.Context, channel_name: str):
        """Check if a Picarto channel is live."""
        stream = PicartoStream(_bot=self.bot, name=channel_name)
        await self.check_online(ctx, stream)

    async def check_online(
        self,
        ctx: commands.Context,
        stream: Union[PicartoStream, YoutubeStream, TwitchStream],
    ):
        try:
            info = await stream.is_online()
        except OfflineStream:
            await ctx.send(_("That user is offline."))
        except StreamNotFound:
            await ctx.send(_("That user doesn't seem to exist."))
        except InvalidTwitchCredentials:
            await ctx.send(
                _("The Twitch token is either invalid or has not been set. See {command}.").format(
                    command=inline(f"{ctx.clean_prefix}streamset twitchtoken")
                )
            )
        except InvalidYoutubeCredentials:
            await ctx.send(
                _(
                    "The YouTube API key is either invalid or has not been set. See {command}."
                ).format(command=inline(f"{ctx.clean_prefix}streamset youtubekey"))
            )
        except YoutubeQuotaExceeded:
            await ctx.send(
                _(
                    "YouTube quota has been exceeded."
                    " Try again later or contact the owner if this continues."
                )
            )
        except APIError as e:
            log.error(
                "Something went wrong whilst trying to contact the stream service's API.\n"
                "Raw response data:\n%r",
                e,
            )
            await ctx.send(
                _("Something went wrong whilst trying to contact the stream service's API.")
            )
        else:
            if isinstance(info, tuple):
                embed, is_rerun = info
                ignore_reruns = await self.config.guild(ctx.channel.guild).ignore_reruns()
                if ignore_reruns and is_rerun:
                    await ctx.send(_("That user is offline."))
                    return
            else:
                embed = info

            use_buttons: bool = await self.config.guild(ctx.channel.guild).use_buttons()
            view = None
            if use_buttons:
                stream_url = embed.url
                view = discord.ui.View()
                view.add_item(
                    discord.ui.Button(
                        label=_("Watch the stream"), style=discord.ButtonStyle.link, url=stream_url
                    )
                )
            await ctx.send(embed=embed, view=view)

    @commands.group()
    @commands.guild_only()
    @commands.mod_or_permissions(manage_channels=True)
    async def streamalert(self, ctx: commands.Context):
        """Manage automated stream alerts."""
        pass

    @streamalert.group(name="twitch", invoke_without_command=True)
    async def _twitch(
        self,
        ctx: commands.Context,
        channel_name: str,
        discord_channel: Union[
            discord.TextChannel, discord.VoiceChannel, discord.StageChannel
        ] = commands.CurrentChannel,
    ):
        """Manage Twitch stream notifications."""
        await ctx.invoke(self.twitch_alert_channel, channel_name, discord_channel)

    @_twitch.command(name="channel")
    async def twitch_alert_channel(
        self,
        ctx: commands.Context,
        channel_name: str,
        discord_channel: Union[
            discord.TextChannel, discord.VoiceChannel, discord.StageChannel
        ] = commands.CurrentChannel,
    ):
        """Toggle alerts in this or the given channel for a Twitch stream."""
        if re.fullmatch(r"<#\d+>", channel_name):
            await ctx.send(
                _("Please supply the name of a *Twitch* channel, not a Discord channel.")
            )
            return
        await self.stream_alert(ctx, TwitchStream, channel_name.lower(), discord_channel)

    @streamalert.command(name="youtube")
    async def youtube_alert(
        self,
        ctx: commands.Context,
        channel_name_or_id: str,
        discord_channel: Union[
            discord.TextChannel, discord.VoiceChannel, discord.StageChannel
        ] = commands.CurrentChannel,
    ):
        """Toggle alerts in this channel for a YouTube stream."""
        await self.stream_alert(ctx, YoutubeStream, channel_name_or_id, discord_channel)

    @streamalert.command(name="picarto")
    async def picarto_alert(
        self,
        ctx: commands.Context,
        channel_name: str,
        discord_channel: Union[
            discord.TextChannel, discord.VoiceChannel, discord.StageChannel
        ] = commands.CurrentChannel,
    ):
        """Toggle alerts in this channel for a Picarto stream."""
        await self.stream_alert(ctx, PicartoStream, channel_name, discord_channel)

    @streamalert.command(name="stop", usage="[disable_all=No]")
    async def streamalert_stop(self, ctx: commands.Context, _all: bool = False):
        """Disable all stream alerts in this channel or server.

        `[p]streamalert stop` will disable this channel's stream
        alerts.

        Do `[p]streamalert stop yes` to disable all stream alerts in
        this server.
        """
        streams = self.streams.copy()
        local_channel_ids = [c.id for c in ctx.guild.channels]
        to_remove = []

        for stream in streams:
            for channel_id in stream.channels:
                if channel_id == ctx.channel.id:
                    stream.channels.remove(channel_id)
                elif _all and ctx.channel.id in local_channel_ids:
                    if channel_id in stream.channels:
                        stream.channels.remove(channel_id)

            if not stream.channels:
                to_remove.append(stream)

        for stream in to_remove:
            streams.remove(stream)

        self.streams = streams
        await self.save_streams()

        if _all:
            msg = _("All the stream alerts in this server have been disabled.")
        else:
            msg = _("All the stream alerts in this channel have been disabled.")

        await ctx.send(msg)

    @streamalert.command(name="list")
    async def streamalert_list(self, ctx: commands.Context):
        """List all active stream alerts in this server."""
        streams_list = defaultdict(lambda: defaultdict(list))
        guild_channels_ids = [c.id for c in ctx.guild.channels]
        msg = _("Active alerts:\n\n")

        for stream in self.streams:
            for channel_id in stream.channels:
                if channel_id in guild_channels_ids:
                    streams_list[channel_id][stream.platform_name].append(stream.name.lower())

        if not streams_list:
            await ctx.send(_("There are no active alerts in this server."))
            return

        for channel_id, stream_platform in streams_list.items():
            msg += f"- {ctx.guild.get_channel(channel_id).mention}\n"
            for platform, streams in stream_platform.items():
                msg += f"  - **{platform}**\n"
                msg += f"    {humanize_list(streams)}\n"

        for page in pagify(msg):
            await ctx.send(page)

    async def stream_alert(self, ctx: commands.Context, _class, channel_name, discord_channel):
        if isinstance(discord_channel, discord.Thread):
            await ctx.send("Stream alerts cannot be set up in threads.")
            return
        stream = self.get_stream(_class, channel_name)
        if not stream:
            token = await self.bot.get_shared_api_tokens(_class.token_name)
            is_yt = _class.__name__ == "YoutubeStream"
            is_twitch = _class.__name__ == "TwitchStream"
            if is_yt and not self.check_name_or_id(channel_name):
                stream = _class(_bot=self.bot, id=channel_name, token=token, config=self.config)
            elif is_twitch:
                await self.maybe_renew_twitch_bearer_token()
                stream = _class(
                    _bot=self.bot,
                    name=channel_name,
                    token=token.get("client_id"),
                    bearer=self.ttv_bearer_cache.get("access_token", None),
                )
            else:
                if is_yt:
                    stream = _class(
                        _bot=self.bot, name=channel_name, token=token, config=self.config
                    )
                else:
                    stream = _class(_bot=self.bot, name=channel_name, token=token)
            try:
                exists = await self.check_exists(stream)
            except InvalidTwitchCredentials:
                await ctx.send(
                    _(
                        "The Twitch token is either invalid or has not been set. See {command}."
                    ).format(command=inline(f"{ctx.clean_prefix}streamset twitchtoken"))
                )
                return
            except InvalidYoutubeCredentials:
                await ctx.send(
                    _(
                        "The YouTube API key is either invalid or has not been set. See "
                        "{command}."
                    ).format(command=inline(f"{ctx.clean_prefix}streamset youtubekey"))
                )
                return
            except YoutubeQuotaExceeded:
                await ctx.send(
                    _(
                        "YouTube quota has been exceeded."
                        " Try again later or contact the owner if this continues."
                    )
                )
            except APIError as e:
                log.error(
                    "Something went wrong whilst trying to contact the stream service's API.\n"
                    "Raw response data:\n%r",
                    e,
                )
                await ctx.send(
                    _("Something went wrong whilst trying to contact the stream service's API.")
                )
                return
            else:
                if not exists:
                    await ctx.send(_("That user doesn't seem to exist."))
                    return

        await self.add_or_remove(ctx, stream, discord_channel)

    @commands.group()
    @commands.mod_or_permissions(manage_channels=True)
    async def streamset(self, ctx: commands.Context):
        """Manage stream alert settings."""
        pass

    @streamset.command(name="timer")
    @commands.is_owner()
    async def _streamset_refresh_timer(self, ctx: commands.Context, refresh_time: int):
        """Set stream check refresh time."""
        if refresh_time < 60:
            return await ctx.send(_("You cannot set the refresh timer to less than 60 seconds"))

        await self.config.refresh_timer.set(refresh_time)
        await ctx.send(
            _("Refresh timer set to {refresh_time} seconds".format(refresh_time=refresh_time))
        )

    @streamset.command()
    @commands.is_owner()
    async def twitchtoken(self, ctx: commands.Context):
        """Explain how to set the twitch token."""
        message = _(
            "To set the twitch API tokens, follow these steps:\n"
            "1. Go to this page: {link}.\n"
            "2. Click *Register Your Application*.\n"
            "3. Enter a name, set the OAuth Redirect URI to {localhost}, and "
            "select an Application Category of your choosing.\n"
            "4. Click *Register*.\n"
            "5. Copy your client ID and your client secret into:\n"
            "{command}"
            "\n\n"
            "Note: These tokens are sensitive and should only be used in a private channel\n"
            "or in DM with the bot.\n"
        ).format(
            link="https://dev.twitch.tv/dashboard/apps",
            localhost=inline("http://localhost"),
            command="`{}set api twitch client_id {} client_secret {}`".format(
                ctx.clean_prefix, _("<your_client_id_here>"), _("<your_client_secret_here>")
            ),
        )

        await ctx.maybe_send_embed(message)

    @streamset.command()
    @commands.is_owner()
    async def youtubekey(self, ctx: commands.Context):
        """Explain how to set the YouTube token."""

        message = _(
            "To get one, do the following:\n"
            "1. Create a project\n"
            "(see {link1} for details)\n"
            "2. Enable the YouTube Data API v3 \n"
            "(see {link2} for instructions)\n"
            "3. Set up your API key \n"
            "(see {link3} for instructions)\n"
            "4. Copy your API key and run the command "
            "{command}\n\n"
            "Note: These tokens are sensitive and should only be used in a private channel\n"
            "or in DM with the bot.\n"
        ).format(
            link1="https://support.google.com/googleapi/answer/6251787",
            link2="https://support.google.com/googleapi/answer/6158841",
            link3="https://support.google.com/googleapi/answer/6158862",
            command="`{}set api youtube api_key {}`".format(
                ctx.clean_prefix, _("<your_api_key_here>")
            ),
        )

        await ctx.maybe_send_embed(message)

    @streamset.group()
    @commands.guild_only()
    async def message(self, ctx: commands.Context):
        """Manage custom messages for stream alerts."""
        pass

    @message.command(name="mention")
    @commands.guild_only()
    async def with_mention(self, ctx: commands.Context, *, message: str):
        """Set stream alert message when mentions are enabled.

        Use `{mention}` in the message to insert the selected mentions.
        Use `{stream}` in the message to insert the channel or username.
        Use `{stream.display_name}` in the message to insert the channel's display name (on Twitch, this may be different from `{stream}`).

        For example: `[p]streamset message mention {mention}, {stream.display_name} is live!`
        """
        guild = ctx.guild
        await self.config.guild(guild).live_message_mention.set(message)
        await ctx.send(_("Stream alert message set!"))

    @message.command(name="nomention")
    @commands.guild_only()
    async def without_mention(self, ctx: commands.Context, *, message: str):
        """Set stream alert message when mentions are disabled.

        Use `{stream}` in the message to insert the channel or username.
        Use `{stream.display_name}` in the message to insert the channel's display name (on Twitch, this may be different from `{stream}`).

        For example: `[p]streamset message nomention {stream.display_name} is live!`
        """
        guild = ctx.guild
        await self.config.guild(guild).live_message_nomention.set(message)
        await ctx.send(_("Stream alert message set!"))

    @message.command(name="clear")
    @commands.guild_only()
    async def clear_message(self, ctx: commands.Context):
        """Reset the stream alert messages in this server."""
        guild = ctx.guild
        await self.config.guild(guild).live_message_mention.set(False)
        await self.config.guild(guild).live_message_nomention.set(False)
        await ctx.send(_("Stream alerts in this server will now use the default alert message."))

    @streamset.group()
    @commands.guild_only()
    async def mention(self, ctx: commands.Context):
        """Manage mention settings for stream alerts."""
        pass

    @mention.command(aliases=["everyone"])
    @commands.guild_only()
    async def all(self, ctx: commands.Context):
        """Toggle the `@\u200beveryone` mention."""
        guild = ctx.guild
        current_setting = await self.config.guild(guild).mention_everyone()
        if current_setting:
            await self.config.guild(guild).mention_everyone.set(False)
            await ctx.send(
                _("{everyone} will no longer be mentioned for stream alerts.").format(
                    everyone=inline("@\u200beveryone")
                )
            )
        else:
            await self.config.guild(guild).mention_everyone.set(True)
            await ctx.send(
                _("When a stream is live, {everyone} will be mentioned.").format(
                    everyone=inline("@\u200beveryone")
                )
            )

    @mention.command(aliases=["here"])
    @commands.guild_only()
    async def online(self, ctx: commands.Context):
        """Toggle the `@\u200bhere` mention."""
        guild = ctx.guild
        current_setting = await self.config.guild(guild).mention_here()
        if current_setting:
            await self.config.guild(guild).mention_here.set(False)
            await ctx.send(
                _("{here} will no longer be mentioned for stream alerts.").format(
                    here=inline("@\u200bhere")
                )
            )
        else:
            await self.config.guild(guild).mention_here.set(True)
            await ctx.send(
                _("When a stream is live, {here} will be mentioned.").format(
                    here=inline("@\u200bhere")
                )
            )

    @mention.command()
    @commands.guild_only()
    async def role(self, ctx: commands.Context, *, role: discord.Role):
        """Toggle a role mention."""
        current_setting = await self.config.role(role).mention()
        if current_setting:
            await self.config.role(role).mention.set(False)
            await ctx.send(
                _("{role} will no longer be mentioned for stream alerts.").format(
                    role=inline(f"@\u200b{role.name}")
                )
            )
        else:
            await self.config.role(role).mention.set(True)
            msg = _("When a stream or community is live, {role} will be mentioned.").format(
                role=inline(f"@\u200b{role.name}")
            )
            if not role.mentionable:
                msg += " " + _(
                    "Since the role is not mentionable, it will be momentarily made mentionable "
                    "when announcing a streamalert. Please make sure I have the correct "
                    "permissions to manage this role, or else members of this role won't receive "
                    "a notification."
                )
            await ctx.send(msg)

    @streamset.command()
    @commands.guild_only()
    async def autodelete(self, ctx: commands.Context, on_off: bool):
        """Toggle alert deletion for when streams go offline."""
        await self.config.guild(ctx.guild).autodelete.set(on_off)
        if on_off:
            await ctx.send(_("The notifications will be deleted once streams go offline."))
        else:
            await ctx.send(_("Notifications will no longer be deleted."))

    @streamset.command(name="ignorereruns")
    @commands.guild_only()
    async def ignore_reruns(self, ctx: commands.Context):
        """Toggle excluding rerun streams from alerts."""
        guild = ctx.guild
        current_setting = await self.config.guild(guild).ignore_reruns()
        if current_setting:
            await self.config.guild(guild).ignore_reruns.set(False)
            await ctx.send(_("Streams of type 'rerun' will be included in alerts."))
        else:
            await self.config.guild(guild).ignore_reruns.set(True)
            await ctx.send(_("Streams of type 'rerun' will no longer send an alert."))

    @streamset.command(name="ignoreschedule")
    @commands.guild_only()
    async def ignore_schedule(self, ctx: commands.Context):
        """Toggle excluding YouTube streams schedules from alerts."""
        guild = ctx.guild
        current_setting = await self.config.guild(guild).ignore_schedule()
        if current_setting:
            await self.config.guild(guild).ignore_schedule.set(False)
            await ctx.send(_("Streams schedules will be included in alerts."))
        else:
            await self.config.guild(guild).ignore_schedule.set(True)
            await ctx.send(_("Streams schedules will no longer send an alert."))

    @streamset.command(name="usebuttons")
    @commands.guild_only()
    async def use_buttons(self, ctx: commands.Context):
        """Toggle whether to use buttons for stream alerts."""
        guild = ctx.guild
        current_setting: bool = await self.config.guild(guild).use_buttons()
        if current_setting:
            await self.config.guild(guild).use_buttons.set(False)
            await ctx.send(_("I will no longer use buttons in stream alerts."))
        else:
            await self.config.guild(guild).use_buttons.set(True)
            await ctx.send(_("I will use buttons in stream alerts."))

    async def add_or_remove(self, ctx: commands.Context, stream, discord_channel):
        if discord_channel.id not in stream.channels:
            stream.channels.append(discord_channel.id)
            if stream not in self.streams:
                self.streams.append(stream)
            await ctx.send(
                _(
                    "I'll now send a notification in the {channel.mention} channel"
                    " when {stream.name} is live."
                ).format(stream=stream, channel=discord_channel)
            )
        else:
            stream.channels.remove(discord_channel.id)
            if not stream.channels:
                self.streams.remove(stream)
            await ctx.send(
                _(
                    "I won't send notifications about {stream.name}"
                    " in the {channel.mention} channel anymore"
                ).format(stream=stream, channel=discord_channel)
            )

        await self.save_streams()

    def get_stream(self, _class, name):
        for stream in self.streams:
            # if isinstance(stream, _class) and stream.name == name:
            #    return stream
            # Reloading this cog causes an issue with this check ^
            # isinstance will always return False
            # As a workaround, we'll compare the class' name instead.
            # Good enough.
            if _class.__name__ == "YoutubeStream" and stream.type == _class.__name__:
                # Because name could be a username or a channel id
                if self.check_name_or_id(name) and stream.name.lower() == name.lower():
                    return stream
                elif not self.check_name_or_id(name) and stream.id == name:
                    return stream
            elif stream.type == _class.__name__ and stream.name.lower() == name.lower():
                return stream

    @staticmethod
    async def check_exists(stream):
        try:
            await stream.is_online()
        except OfflineStream:
            pass
        except StreamNotFound:
            return False
        except StreamsError:
            raise
        return True

    async def _stream_alerts(self):
        await self.bot.wait_until_ready()
        while True:
            await self.check_streams()
            await asyncio.sleep(await self.config.refresh_timer())

    async def _send_stream_alert(
        self,
        stream,
        channel: Union[discord.TextChannel, discord.VoiceChannel, discord.StageChannel],
        embed: discord.Embed,
        content: str = None,
        *,
        is_schedule: bool = False,
    ):
        use_buttons: bool = await self.config.guild(channel.guild).use_buttons()
        view = None
        if use_buttons:
            stream_url = embed.url
            view = discord.ui.View()
            view.add_item(
                discord.ui.Button(
                    label=_("Watch the stream"), style=discord.ButtonStyle.link, url=stream_url
                )
            )
        m = await channel.send(
            content,
            embed=embed,
            allowed_mentions=discord.AllowedMentions(roles=True, everyone=True),
            view=view,
        )
        message_data = {"guild": m.guild.id, "channel": m.channel.id, "message": m.id}
        if is_schedule:
            message_data["is_schedule"] = True
        stream.messages.append(message_data)

    async def check_streams(self):
        to_remove = []
        for stream in self.streams:
            try:
                try:
                    is_rerun = False
                    is_schedule = False
                    if stream.__class__.__name__ == "TwitchStream":
                        await self.maybe_renew_twitch_bearer_token()
                        embed, is_rerun = await stream.is_online()

                    elif stream.__class__.__name__ == "YoutubeStream":
                        embed, is_schedule = await stream.is_online()

                    else:
                        embed = await stream.is_online()
                except StreamNotFound:
                    if stream.retry_count > MAX_RETRY_COUNT:
                        log.info("Stream with name %s no longer exists. Removing...", stream.name)
                        to_remove.append(stream)
                    else:
                        log.info(
                            "Stream with name %s seems to not exist, will retry later", stream.name
                        )
                        stream.retry_count += 1
                    continue
                except OfflineStream:
                    if not stream.messages:
                        continue

                    for msg_data in stream.iter_messages():
                        partial_msg = msg_data["partial_message"]
                        if partial_msg is None:
                            continue
                        if await self.bot.cog_disabled_in_guild(self, partial_msg.guild):
                            continue
                        if not await self.config.guild(partial_msg.guild).autodelete():
                            continue

                        with contextlib.suppress(discord.NotFound):
                            await partial_msg.delete()

                    stream.messages.clear()
                    await self.save_streams()
                except APIError as e:
                    log.error(
                        "Something went wrong whilst trying to contact the stream service's API.\n"
                        "Raw response data:\n%r",
                        e,
                    )
                    continue
                else:
                    if stream.messages:
                        continue
                    for channel_id in stream.channels:
                        channel = self.bot.get_channel(channel_id)
                        if not channel:
                            continue
                        if await self.bot.cog_disabled_in_guild(self, channel.guild):
                            continue

                        guild_data = await self.config.guild(channel.guild).all()
                        if guild_data["ignore_reruns"] and is_rerun:
                            continue
                        if guild_data["ignore_schedule"] and is_schedule:
                            continue
                        if is_schedule:
                            # skip messages and mentions
                            await self._send_stream_alert(stream, channel, embed, is_schedule=True)
                            await self.save_streams()
                            continue
                        await set_contextual_locales_from_guild(self.bot, channel.guild)

                        mention_str, edited_roles = await self._get_mention_str(
                            channel.guild, channel, guild_data
                        )

                        if mention_str:
                            if guild_data["live_message_mention"]:
                                # Stop bad things from happening here...
                                content = guild_data["live_message_mention"]
                                content = content.replace(
                                    "{stream.name}", str(stream.name)
                                )  # Backwards compatibility
                                content = content.replace(
                                    "{stream.display_name}", str(stream.display_name)
                                )
                                content = content.replace("{stream}", str(stream.name))
                                content = content.replace("{mention}", mention_str)
                            else:
                                content = _("{mention}, {display_name} is live!").format(
                                    mention=mention_str,
                                    display_name=escape(
                                        str(stream.display_name),
                                        mass_mentions=True,
                                        formatting=True,
                                    ),
                                )
                        else:
                            if guild_data["live_message_nomention"]:
                                # Stop bad things from happening here...
                                content = guild_data["live_message_nomention"]
                                content = content.replace(
                                    "{stream.name}", str(stream.name)
                                )  # Backwards compatibility
                                content = content.replace(
                                    "{stream.display_name}", str(stream.display_name)
                                )
                                content = content.replace("{stream}", str(stream.name))
                            else:
                                content = _("{display_name} is live!").format(
                                    display_name=escape(
                                        str(stream.display_name),
                                        mass_mentions=True,
                                        formatting=True,
                                    )
                                )
                        await self._send_stream_alert(stream, channel, embed, content)
                        if edited_roles:
                            for role in edited_roles:
                                await role.edit(mentionable=False)
                        await self.save_streams()
            except Exception as e:
                log.error("An error has occurred with Streams. Please report it.", exc_info=e)

        if to_remove:
            for stream in to_remove:
                self.streams.remove(stream)
            await self.save_streams()

    async def _get_mention_str(
        self,
        guild: discord.Guild,
        channel: Union[discord.TextChannel, discord.VoiceChannel, discord.StageChannel],
        guild_data: dict,
    ) -> Tuple[str, List[discord.Role]]:
        """Returns a 2-tuple with the string containing the mentions, and a list of
        all roles which need to have their `mentionable` property set back to False.
        """
        mentions = []
        edited_roles = []
        if guild_data["mention_everyone"]:
            mentions.append("@everyone")
        if guild_data["mention_here"]:
            mentions.append("@here")
        can_manage_roles = guild.me.guild_permissions.manage_roles
        can_mention_everyone = channel.permissions_for(guild.me).mention_everyone
        for role in guild.roles:
            if await self.config.role(role).mention():
                if not can_mention_everyone and can_manage_roles and not role.mentionable:
                    try:
                        await role.edit(mentionable=True)
                    except discord.Forbidden:
                        # Might still be unable to edit role based on hierarchy
                        pass
                    else:
                        edited_roles.append(role)
                mentions.append(role.mention)
        return " ".join(mentions), edited_roles

    async def filter_streams(
        self,
        streams: list,
        channel: Union[discord.TextChannel, discord.VoiceChannel, discord.StageChannel],
    ) -> list:
        filtered = []
        for stream in streams:
            tw_id = str(stream["channel"]["_id"])
            for alert in self.streams:
                if isinstance(alert, TwitchStream) and alert.id == tw_id:
                    if channel.id in alert.channels:
                        break
            else:
                filtered.append(stream)
        return filtered

    async def load_streams(self):
        streams = []
        for raw_stream in await self.config.streams():
            _class = getattr(_streamtypes, raw_stream["type"], None)
            if not _class:
                continue
            token = await self.bot.get_shared_api_tokens(_class.token_name)
            if token:
                if _class.__name__ == "TwitchStream":
                    raw_stream["token"] = token.get("client_id")
                    raw_stream["bearer"] = self.ttv_bearer_cache.get("access_token", None)
                else:
                    if _class.__name__ == "YoutubeStream":
                        raw_stream["config"] = self.config
                    raw_stream["token"] = token
            raw_stream["_bot"] = self.bot
            streams.append(_class(**raw_stream))

        return streams

    async def save_streams(self):
        raw_streams = []
        for stream in self.streams:
            raw_streams.append(stream.export())

        await self.config.streams.set(raw_streams)

    def cog_unload(self):
        if self.task:
            self.task.cancel()
