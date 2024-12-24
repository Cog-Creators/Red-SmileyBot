import datetime
from typing import List, Tuple, cast

import discord
from redbot.core import commands, i18n
from redbot.core.utils.chat_formatting import bold, pagify
from redbot.core.utils.common_filters import (
    filter_invites,
    filter_various_mentions,
    escape_spoilers_and_mass_mentions,
)
from redbot.core.utils.mod import get_audit_reason
from .abc import MixinMeta
from .utils import is_allowed_by_hierarchy

_ = i18n.Translator("Mod", __file__)


class ModInfo(MixinMeta):
    """
    Commands regarding names, userinfo, etc.
    """

    async def get_names(self, member: discord.Member) -> Tuple[List[str], List[str], List[str]]:
        user_data = await self.config.user(member).all()
        usernames, display_names = user_data["past_names"], user_data["past_display_names"]
        nicks = await self.config.member(member).past_nicks()
        usernames = list(map(escape_spoilers_and_mass_mentions, filter(None, usernames)))
        display_names = list(map(escape_spoilers_and_mass_mentions, filter(None, display_names)))
        nicks = list(map(escape_spoilers_and_mass_mentions, filter(None, nicks)))
        return usernames, display_names, nicks

    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(manage_nicknames=True)
    @commands.admin_or_permissions(manage_nicknames=True)
    async def rename(self, ctx: commands.Context, member: discord.Member, *, nickname: str = ""):
        """Change a member's server nickname.

        Leaving the nickname argument empty will remove it.
        """
        nickname = nickname.strip()
        me = cast(discord.Member, ctx.me)
        if not nickname:
            nickname = None
        elif not 2 <= len(nickname) <= 32:
            await ctx.send(_("Nicknames must be between 2 and 32 characters long."))
            return
        if not (
            (me.guild_permissions.manage_nicknames or me.guild_permissions.administrator)
            and me.top_role > member.top_role
            and member != ctx.guild.owner
        ):
            await ctx.send(
                _(
                    "I do not have permission to rename that member. They may be higher than or "
                    "equal to me in the role hierarchy."
                )
            )
        elif ctx.author != member and not await is_allowed_by_hierarchy(
            self.bot, self.config, ctx.guild, ctx.author, member
        ):
            await ctx.send(
                _(
                    "I cannot let you do that. You are "
                    "not higher than the user in the role "
                    "hierarchy."
                )
            )
        else:
            try:
                await member.edit(reason=get_audit_reason(ctx.author, None), nick=nickname)
            except discord.Forbidden:
                # Just in case we missed something in the permissions check above
                await ctx.send(_("I do not have permission to rename that member."))
            except discord.HTTPException as exc:
                if exc.status == 400:  # BAD REQUEST
                    await ctx.send(_("That nickname is invalid."))
                else:
                    await ctx.send(_("An unexpected error has occurred."))
            else:
                await ctx.send(_("Done."))

    def handle_custom(self, user):
        a = [c for c in user.activities if c.type == discord.ActivityType.custom]
        if not a:
            return None, discord.ActivityType.custom
        a = a[0]
        c_status = None
        if not a.name and not a.emoji:
            return None, discord.ActivityType.custom
        elif a.name and a.emoji:
            c_status = _("Custom: {emoji} {name}").format(emoji=a.emoji, name=a.name)
        elif a.emoji:
            c_status = _("Custom: {emoji}").format(emoji=a.emoji)
        elif a.name:
            c_status = _("Custom: {name}").format(name=a.name)
        return c_status, discord.ActivityType.custom

    def handle_playing(self, user):
        p_acts = [c for c in user.activities if c.type == discord.ActivityType.playing]
        if not p_acts:
            return None, discord.ActivityType.playing
        p_act = p_acts[0]
        act = _("Playing: {name}").format(name=p_act.name)
        return act, discord.ActivityType.playing

    def handle_streaming(self, user):
        s_acts = [c for c in user.activities if c.type == discord.ActivityType.streaming]
        if not s_acts:
            return None, discord.ActivityType.streaming
        s_act = s_acts[0]
        if isinstance(s_act, discord.Streaming):
            act = _("Streaming: [{name}{sep}{game}]({url})").format(
                name=discord.utils.escape_markdown(s_act.name),
                sep=" | " if s_act.game else "",
                game=discord.utils.escape_markdown(s_act.game) if s_act.game else "",
                url=s_act.url,
            )
        else:
            act = _("Streaming: {name}").format(name=s_act.name)
        return act, discord.ActivityType.streaming

    def handle_listening(self, user):
        l_acts = [c for c in user.activities if c.type == discord.ActivityType.listening]
        if not l_acts:
            return None, discord.ActivityType.listening
        l_act = l_acts[0]
        if isinstance(l_act, discord.Spotify):
            act = _("Listening: [{title}{sep}{artist}]({url})").format(
                title=discord.utils.escape_markdown(l_act.title),
                sep=" | " if l_act.artist else "",
                artist=discord.utils.escape_markdown(l_act.artist) if l_act.artist else "",
                url=f"https://open.spotify.com/track/{l_act.track_id}",
            )
        else:
            act = _("Listening: {title}").format(title=l_act.name)
        return act, discord.ActivityType.listening

    def handle_watching(self, user):
        w_acts = [c for c in user.activities if c.type == discord.ActivityType.watching]
        if not w_acts:
            return None, discord.ActivityType.watching
        w_act = w_acts[0]
        act = _("Watching: {name}").format(name=w_act.name)
        return act, discord.ActivityType.watching

    def handle_competing(self, user):
        w_acts = [c for c in user.activities if c.type == discord.ActivityType.competing]
        if not w_acts:
            return None, discord.ActivityType.competing
        w_act = w_acts[0]
        act = _("Competing in: {competing}").format(competing=w_act.name)
        return act, discord.ActivityType.competing

    def get_status_string(self, user):
        string = ""
        for a in [
            self.handle_custom(user),
            self.handle_playing(user),
            self.handle_listening(user),
            self.handle_streaming(user),
            self.handle_watching(user),
            self.handle_competing(user),
        ]:
            status_string, status_type = a
            if status_string is None:
                continue
            string += f"{status_string}\n"
        return string

    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    async def userinfo(self, ctx, *, member: discord.Member = None):
        """Show information about a member.

        This includes fields for status, discord join date, server
        join date, voice state and previous usernames/global display names/nicknames.

        If the member has no roles, previous usernames, global display names, or server nicknames,
        these fields will be omitted.
        """
        author = ctx.author
        guild = ctx.guild

        if not member:
            member = author

        #  A special case for a special someone :^)
        special_date = datetime.datetime(2016, 1, 10, 6, 8, 4, 443000, datetime.timezone.utc)
        is_special = member.id == 96130341705637888 and guild.id == 133049272517001216

        roles = member.roles[-1:0:-1]
        usernames, display_names, nicks = await self.get_names(member)

        if is_special:
            joined_at = special_date
        else:
            joined_at = member.joined_at
        voice_state = member.voice
        member_number = (
            sorted(guild.members, key=lambda m: m.joined_at or ctx.message.created_at).index(
                member
            )
            + 1
        )

        created_on = (
            f"{discord.utils.format_dt(member.created_at)}\n"
            f"{discord.utils.format_dt(member.created_at, 'R')}"
        )
        if joined_at is not None:
            joined_on = (
                f"{discord.utils.format_dt(joined_at)}\n"
                f"{discord.utils.format_dt(joined_at, 'R')}"
            )
        else:
            joined_on = _("Unknown")

        if any(a.type is discord.ActivityType.streaming for a in member.activities):
            statusemoji = "\N{LARGE PURPLE CIRCLE}"
        elif member.status.name == "online":
            statusemoji = "\N{LARGE GREEN CIRCLE}"
        elif member.status.name == "offline":
            statusemoji = "\N{MEDIUM WHITE CIRCLE}\N{VARIATION SELECTOR-16}"
        elif member.status.name == "dnd":
            statusemoji = "\N{LARGE RED CIRCLE}"
        elif member.status.name == "idle":
            statusemoji = "\N{LARGE ORANGE CIRCLE}"
        activity = _("Chilling in {} status").format(member.status)
        status_string = self.get_status_string(member)

        if roles:
            role_str = ", ".join([x.mention for x in roles])
            # 400 BAD REQUEST (error code: 50035): Invalid Form Body
            # In embed.fields.2.value: Must be 1024 or fewer in length.
            if len(role_str) > 1024:
                # Alternative string building time.
                # This is not the most optimal, but if you're hitting this, you are losing more time
                # to every single check running on users than the occasional user info invoke
                # We don't start by building this way, since the number of times we hit this should be
                # infinitesimally small compared to when we don't across all uses of Red.
                continuation_string = _(
                    "and {numeric_number} more roles not displayed due to embed limits."
                )
                available_length = 1024 - len(continuation_string)  # do not attempt to tweak, i18n

                role_chunks = []
                remaining_roles = 0

                for r in roles:
                    chunk = f"{r.mention}, "
                    chunk_size = len(chunk)

                    if chunk_size < available_length:
                        available_length -= chunk_size
                        role_chunks.append(chunk)
                    else:
                        remaining_roles += 1

                role_chunks.append(continuation_string.format(numeric_number=remaining_roles))

                role_str = "".join(role_chunks)

        else:
            role_str = None

        data = discord.Embed(description=status_string or activity, colour=member.colour)

        data.add_field(name=_("Joined Discord on"), value=created_on)
        data.add_field(name=_("Joined this server on"), value=joined_on)
        if role_str is not None:
            data.add_field(
                name=_("Roles") if len(roles) > 1 else _("Role"), value=role_str, inline=False
            )
        for single_form, plural_form, names in (
            (_("Previous Username"), _("Previous Usernames"), usernames),
            (_("Previous Global Display Name"), _("Previous Global Display Names"), display_names),
            (_("Previous Server Nickname"), _("Previous Server Nicknames"), nicks),
        ):
            if names:
                data.add_field(
                    name=plural_form if len(names) > 1 else single_form,
                    value=filter_invites(", ".join(names)),
                    inline=False,
                )
        if voice_state and voice_state.channel:
            data.add_field(
                name=_("Current voice channel"),
                value="{0.mention} ID: {0.id}".format(voice_state.channel),
                inline=False,
            )
        data.set_footer(text=_("Member #{} | User ID: {}").format(member_number, member.id))

        name = str(member)
        name = " ~ ".join((name, member.nick)) if member.nick else name
        name = filter_invites(name)

        avatar = member.display_avatar.replace(static_format="png")
        data.set_author(name=f"{statusemoji} {name}", url=avatar)
        data.set_thumbnail(url=avatar)

        await ctx.send(embed=data)

    @commands.command()
    async def names(self, ctx: commands.Context, *, member: discord.Member):
        """Show previous usernames, global display names, and server nicknames of a member."""
        usernames, display_names, nicks = await self.get_names(member)
        parts = []
        for header, names in (
            (_("Past 20 usernames:"), usernames),
            (_("Past 20 global display names:"), display_names),
            (_("Past 20 server nicknames:"), nicks),
        ):
            if names:
                parts.append(bold(header) + ", ".join(names))
        if parts:
            # each name can have 32 characters, we store 3*20 names which totals to
            # 60*32=1920 characters which is quite close to the message length limit
            for msg in pagify(filter_various_mentions("\n\n".join(parts))):
                await ctx.send(msg)
        else:
            await ctx.send(_("That member doesn't have any recorded name or nickname change."))
