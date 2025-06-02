import discord
from discord.ext import commands
from discord.ui import View, Button
import asyncio
from datetime import datetime
from utils.database import structs
import global_vars
from utils import (
    color,
    ghost_url,
    embed_color,
    Bot,
    utility as util
)


class SettingsCog(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot: Bot = bot

    def owner_or_not_dev():
        async def predicate(ctx):
            if ctx.author.id == ctx.guild.owner_id:
                return True
            if ctx.author.id in ctx.bot.owner_ids:
                return True
            try:
                await ctx.send("You do not have permission to use this command.")
            except discord.Forbidden:
                pass
            return False
        return commands.check(predicate)


    async def antinuke_db(self, guild):
        row: structs.guild_settings = self.bot.db.guild.antinuke.fetchone(guild.id)
        if row:
            try:
                q_others = row.q_others
            except Exception as e:
                q_others = None

            try:
                log_channel = await self.bot.fetch_channel(row.log_channel)
            except Exception as e:
                log_channel = None
            return q_others, log_channel
        return None, None, 

    async def guild_settings_db(self, guild):
        row: structs.guild_settings = self.bot.db.guild.settings.fetchone(guild.id)
        try:
            q_role = await guild.fetch_role(row.q_role)
        except Exception as e:
            q_role = None

        try:
            mute_role = await guild.fetch_role(row.mute_role)
        except Exception as e:
            mute_role = None
        return q_role, mute_role
    

    @util.group(name='set', aliases=["s"], invoke_without_command=True)
    @owner_or_not_dev()
    async def set(self, ctx):
        """Base command for setting configurations."""
        em = discord.Embed(
            title="🛠️ Settings Configuration",
            description=(
                "Use one of the following categories to configure your server settings:\n\n"
                "🔐 **AntiNuke Settings**\n"
                "`→ .set antinuke` - Configure quarantine role, auto-quarantine, and log channel.\n\n"
                "📝 **Logging Settings**\n"
                "`→ .set log` - Set channels for moderation, messages, joins/leaves, and more.\n\n"
                "⚡ **AutoLog Setup**\n"
                "`→ .set autolog` - Automatically creates all log channels in a category and saves them."
            ),
            color=embed_color
        )
        em.set_footer(text="Example: .set antinuke")
        await ctx.send(embed=em)

    @set.group(name='antinuke', aliases=["a"], invoke_without_command=True)
    @owner_or_not_dev()
    async def set_antinuke(self, ctx):
        q_role, _ = await self.guild_settings_db(ctx.guild)
        q_others, log_channel = await self.antinuke_db(ctx.guild)
        em = discord.Embed(title="AntiNuke Settings", description=(
            f"__**Quarantine Role**__ : {q_role.mention if q_role is not None else 'None'}\n"
            f"-# `.set antinuke quarantinerole <@role>`\n\n"
            f"__**Automatic Quarantine On Triggering AntiNuke**__ : {'True' if q_others == 1 else 'False' if q_others == 0 else 'None'}\n"
            f"-# `.set antinuke autoquarantine True/False`\n\n"
            f"__**AntiNuke Log Channel**__ : {log_channel.mention if log_channel is not None else 'None'}\n"
            f"-# `.set antinuke logchannel <#channel>`\n"
        ), color=embed_color)
        em.set_footer(text=ctx.guild.name, icon_url=ctx.guild.icon.url if ctx.guild.icon else None)
        await ctx.send(embed=em)

    @set_antinuke.command(name='autoquarantine', aliases=["aq"])
    @owner_or_not_dev()
    async def set_antinuke_autoquarantine(self, ctx, tr: bool):
        """Set the quarantine role for anti-nuke."""
        if tr == False:
            rec = self.bot.db.guild.antinuke.fetchone(ctx.guild.id)
            if not rec:
                self.bot.db.guild.antinuke.insert(ctx.guild.id, tr, None)
            rec.q_others = tr
            self.bot.db.guild.antinuke.update_record(rec)
            await ctx.send(f"Auto Quarantine Turned Off.")
        elif tr == True:
            rec = self.bot.db.guild.antinuke.fetchone(ctx.guild.id)
            if not rec:
                self.bot.db.guild.antinuke.insert(ctx.guild.id, tr, None)
            rec.q_others = tr
            self.bot.db.guild.antinuke.update_record(rec)
            await ctx.send(f"Auto Quarantine Turned On.")

    @set_antinuke.command(name='quarantinerole', aliases=["qr"])
    @owner_or_not_dev()
    @util.describe(role="The role to be set as quarantine role")
    async def set_antinuke_quarantinerole(self, ctx, role: discord.Role):
        """Set the quarantine role for anti-nuke."""
        rec = self.bot.db.guild.settings.fetchone(ctx.guild.id)
        if not rec:
            self.bot.db.guild.settings.insert(ctx.guild.id, role.id, None)
        else:
            rec.q_role = role.id
            self.bot.db.guild.settings.update_record(rec)
        await ctx.send(f'Quarantine role set to `{role.name}`')
        

    @set_antinuke.command(name='logchannel', aliases=["log"])
    @owner_or_not_dev()
    @util.describe(channel="The channel to set as log channel")
    async def set_antinuke_logchannel(self, ctx, channel: discord.TextChannel):
        """Set the log channel for anti-nuke events."""
        rec = self.bot.db.guild.antinuke.fetchone(ctx.guild.id)
        if not rec:
            self.bot.db.guild.antinuke.insert(ctx.guild.id, False, channel.id)
        rec.log_channel = channel.id
        self.bot.db.guild.antinuke.update_record(rec)
        await ctx.send(f'Log channel for anti-nuke set to {channel.mention}')
        
  
    @set.group(name='log', invoke_without_command=True)
    @owner_or_not_dev()
    async def set_log(self, ctx):
        """Base log config command."""
        rec = self.bot.db.guild.logging.fetchone(ctx.guild.id)
        if not rec:
            rec = self.bot.db.guild.logging.insert(ctx.guild.id, None, None, None, None, None, None, None)

        def safe_mention(channel_id):
            try:
                ch = ctx.guild.get_channel(channel_id)
                return ch.mention
            except Exception as e:
                return 'None'

        em = discord.Embed(title="Logging Configuration", description=(
            f"__**Mod Logs**__: {safe_mention(rec.mod) if rec else 'None'}\n"
            f"-# `.set log mod <#channel>`\n\n"
            f"__**Message Logs**__: {safe_mention(rec.message) if rec else 'None'}\n"
            f"-# `.set log message <#channel>`\n\n"
            f"__**Join/Leave Logs**__: {safe_mention(rec.join_leave) if rec else 'None'}\n"
            f"-# `.set log joinleave <#channel>`\n\n"
            f"__**Member Logs**__: {safe_mention(rec.member) if rec else 'None'}\n"
            f"-# `.set log member <#channel>`\n\n"
            f"__**Server Logs**__: {safe_mention(rec.server) if rec else 'None'}\n"
            f"-# `.set log server <#channel>`\n\n"
            f"__**Ticket Logs**__: {safe_mention(rec.ticket) if rec else 'None'}\n"
            f"-# `.set log ticket <#channel>`\n\n"
            f"__**Voice Logs**__: {safe_mention(rec.voice) if rec else 'None'}\n"
            f"-# `.set log voice <#channel>`\n"
        ), color=embed_color)
        em.set_footer(text=ctx.guild.name, icon_url=ctx.guild.icon.url if ctx.guild.icon else None)

        await ctx.send(embed=em)


    @set_log.command(name='mod')
    @owner_or_not_dev()
    @util.describe(channel="The channel to set for mod logs")
    async def set_log_mod(self, ctx, channel: discord.TextChannel):
        rec = self.bot.db.guild.logging.fetchone(ctx.guild.id)
        if not rec:
            rec = self.bot.db.guild.logging.insert(ctx.guild.id)
            rec.mod = channel.id
            self.bot.db.guild.logging.insert(rec)
        else:
            rec.mod = channel.id
            self.bot.db.guild.logging.update_record(rec)
        await ctx.send(f'Mod logs set to {channel.mention}')

    @set_log.command(name='message')
    @owner_or_not_dev()
    @util.describe(channel="The channel to set for message logs")
    async def set_log_message(self, ctx, channel: discord.TextChannel):
        rec = self.bot.db.guild.logging.fetchone(ctx.guild.id)
        if not rec:
            rec = self.bot.db.guild.logging.insert(ctx.guild.id)
            rec.message = channel.id
            self.bot.db.guild.logging.insert(rec)
        else:
            rec.message = channel.id
            self.bot.db.guild.logging.update_record(rec)
        await ctx.send(f'Message logs set to {channel.mention}')

    @set_log.command(name='joinleave', aliases=["jl"])
    @owner_or_not_dev()
    @util.describe(channel="The channel to set for join/leave logs")
    async def set_log_joinleave(self, ctx, channel: discord.TextChannel):
        rec = self.bot.db.guild.logging.fetchone(ctx.guild.id)
        if not rec:
            rec = self.bot.db.guild.logging.insert(ctx.guild.id)
            rec.join_leave = channel.id
            self.bot.db.guild.logging.insert(rec)
        else:
            rec.join_leave = channel.id
            self.bot.db.guild.logging.update_record(rec)
        await ctx.send(f'Join/Leave logs set to {channel.mention}')

    @set_log.command(name='member')
    @owner_or_not_dev()
    @util.describe(channel="The channel to set for member logs")
    async def set_log_member(self, ctx, channel: discord.TextChannel):
        rec = self.bot.db.guild.logging.fetchone(ctx.guild.id)
        if not rec:
            rec = self.bot.db.guild.logging.insert(ctx.guild.id)
            rec.member = channel.id
            self.bot.db.guild.logging.insert(rec)
        else:
            rec.member = channel.id
            self.bot.db.guild.logging.update_record(rec)
        await ctx.send(f'Member logs set to {channel.mention}')

    @set_log.command(name='server')
    @owner_or_not_dev()
    @util.describe(channel="The channel to set for server logs")
    async def set_log_server(self, ctx, channel: discord.TextChannel):
        rec = self.bot.db.guild.logging.fetchone(ctx.guild.id)
        if not rec:
            rec = self.bot.db.guild.logging.insert(ctx.guild.id)
            rec.server = channel.id
            self.bot.db.guild.logging.insert(rec)
        else:
            rec.server = channel.id
            self.bot.db.guild.logging.update_record(rec)
        await ctx.send(f'Server logs set to {channel.mention}')

    @set_log.command(name='ticket')
    @owner_or_not_dev()
    @util.describe(channel="The channel to set for ticket logs")
    async def set_log_ticket(self, ctx, channel: discord.TextChannel):
        rec = self.bot.db.guild.logging.fetchone(ctx.guild.id)
        if not rec:
            rec = self.bot.db.guild.logging.insert(ctx.guild.id)
            rec.ticket = channel.id
            self.bot.db.guild.logging.insert(rec)
        else:
            rec.ticket = channel.id
            self.bot.db.guild.logging.update_record(rec)
        await ctx.send(f'Ticket logs set to {channel.mention}')

    @set_log.command(name='voice')
    @owner_or_not_dev()
    @util.describe(channel="The channel to set for voice logs")
    async def set_log_voice(self, ctx, channel: discord.TextChannel):
        rec = self.bot.db.guild.logging.fetchone(ctx.guild.id)
        if not rec:
            rec = self.bot.db.guild.logging.insert(ctx.guild.id)
            rec.voice = channel.id
            self.bot.db.guild.logging.insert(rec)
        else:
            rec.voice = channel.id
            self.bot.db.guild.logging.update_record(rec)
        await ctx.send(f'Voice logs set to {channel.mention}')


    @set.command(name='autolog')
    @owner_or_not_dev()
    async def set_autolog(self, ctx):
        guild = ctx.guild

        category = await guild.create_category("The Void Logs")

        mod = await guild.create_text_channel("mod-logs", category=category)
        await asyncio.sleep(1)
        message = await guild.create_text_channel("message-logs", category=category)
        await asyncio.sleep(1)
        join_leave = await guild.create_text_channel("join-leave-logs", category=category)
        await asyncio.sleep(1)
        member = await guild.create_text_channel("member-logs", category=category)
        await asyncio.sleep(1)
        server = await guild.create_text_channel("server-logs", category=category)
        await asyncio.sleep(1)
        ticket = await guild.create_text_channel("ticket-logs", category=category)
        await asyncio.sleep(1)
        voice = await guild.create_text_channel("voice-logs", category=category)
        await asyncio.sleep(1)

        rec = self.bot.db.guild.logging.fetchone(guild.id)
        if not rec:
            self.bot.db.guild.logging.insert(guild.id, mod.id, message.id, join_leave.id, member.id, server.id, ticket.id, voice.id)
        else:
            rec.mod = mod.id
            rec.message = message.id
            rec.join_leave = join_leave.id
            rec.member = member.id
            rec.server = server.id
            rec.ticket = ticket.id
            rec.voice = voice.id
            self.bot.db.guild.logging.update_record(rec)

        await ctx.send(f"✅ All log channels created in `{category.name}` and saved.")




async def setup(bot):
    await bot.add_cog(SettingsCog(bot))
