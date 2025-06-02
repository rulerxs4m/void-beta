import os
import re
import math
import asyncio
from typing import List, Union
from utils import (
    ghost_url,
    empty_char,
    embed_color,
    Bot,
    redef,
    utility as util,
    react
)

import discord
from discord.ext import commands as cmds

from utils.database import structs

class Context(cmds.Context):
    bot: Bot

coin = "⏣"

class DonoSetting(cmds.Converter[structs.dank_donation_settings]):
    async def convert(self, ctx: Context, argument: str) -> structs.dank_donation_settings:
        ctx.bot.db.cursor.execute("SELECT * FROM dank_donation_settings WHERE gid = ? AND bank_name = ?", (ctx.guild.id, argument))
        g_settings = ctx.bot.db.dank.donation_settings.parse(ctx.bot.db.cursor.fetchone())
        if not g_settings:
            try:
                channel = cmds.GuildChannelConverter._resolve_channel(ctx, argument, 'text_channels', discord.TextChannel)
                g_settings = ctx.bot.db.dank.donation_settings.fetchone((ctx.guild.id, channel.id))
            except cmds.ChannelNotFound:
                channel = None; g_settings = None
            if g_settings is None:
                await react(ctx.message, ctx.bot.emoji.x_mark)
                if channel is not None:
                    raise cmds.BadArgument(f"'{channel.name}' is not a donation channel.")
                raise cmds.BadArgument(f"No bank found: '{argument}'")
        if g_settings.manager_role:
            if ctx.author.get_role(g_settings.manager_role) == None:
                if ctx.guild.owner_id != ctx.author.id:
                    await react(ctx.message, ctx.bot.emoji.x_mark)
                    raise cmds.CheckFailure(f"You are not the manager of bank: '{g_settings.bank_name}'")
        return g_settings
    
class Amount(cmds.Converter):
    SUFFIXES = {
        "k": 1_000, "thousand": 1_000, "m": 1_000_000, "mil": 1_000_000, "million": 1_000_000,
        "b": 1_000_000_000, "bil": 1_000_000_000, "billion": 1_000_000_000, 
        "t": 1_000_000_000_000, "tril": 1_000_000_000_000, "trillion": 1_000_000_000_000
    }
    FORMAT_SUFFIXES = [(1_000_000_000_000, "T"), (1_000_000_000, "B"), (1_000_000, "M"), (1_000, "K")]
    CLEAN_TRAILING = re.compile(r'[^\w\d]+$')
    NUMBER_PATTERN = re.compile(r"^([\d,]+(?:\.\d+)?)([a-z]*)$", re.IGNORECASE)
    
    async def convert(self, ctx: Context, argument: str) -> int:
        argument = self.CLEAN_TRAILING.sub("", argument.replace(",", "").strip().lower())
        match = self.NUMBER_PATTERN.fullmatch(argument)
        if not match: raise cmds.BadArgument("Invalid format. Example: `1k`, `2.5mil`, `4billion`.")
        number_part, suffix = match.groups()
        multiplier = self.SUFFIXES.get(suffix, 1)
        try: number = float(number_part)
        except ValueError: raise cmds.BadArgument("Invalid number.")
        return int(number * multiplier)

    @staticmethod
    def format(amount: int) -> str:
        for threshold, suffix in Amount.FORMAT_SUFFIXES:
            if amount >= threshold:
                truncated = math.floor(amount / threshold * 100) / 100
                return f"{truncated:.2f}{suffix}"
        return str(amount)
    
class setup_cog(cmds.Cog):
    def __init__(self, bot: Bot):
        super().__init__()
        self.bot: Bot = bot

    @util.group(name="setup", description="Setup the bot", invoke_without_command=True)
    async def stp(self, ctx: Context):
        if ctx.invoked_subcommand: return
        await ctx.reply(f"{self.bot.emoji.construction} | This bot is under development.")

    @stp.group(name="donations", description="Setup dank donations", invoke_without_command=True, aliases=["dono", "donation"])
    @cmds.has_permissions(administrator=True)
    async def setup_dono(self, ctx: Context, bank: DonoSetting=None):
        if ctx.invoked_subcommand: return
        bank: structs.dank_donation_settings = bank
        if not bank:
            self.bot.db.cursor.execute("SELECT * FROM dank_donation_settings WHERE gid = ?", (ctx.guild.id,))
            data = self.bot.db.cursor.fetchall()
            if not data:
                await react(ctx.message, self.bot.emoji.x_mark)
                return await ctx.reply(f"{self.bot.emoji.x_mark} | Donations are not setup. ( `.setup donations help` )", delete_after=10)
            data = [self.bot.db.dank.donation_settings.parse(x) for x in data]
            embed = discord.Embed(
                title = "Banks -",
                color = embed_color,
                description = "\n".join(
                    f"- `{x.bank_name}` - <#{x.donation_channel}>"
                    for x in data
                )
            )
            embed.set_footer(text=ctx.guild.name, icon_url=ctx.guild.icon.url if ctx.guild.icon else None)
            return await ctx.reply(embed=embed)
        embed = discord.Embed(
            title = f"Bank - {bank.bank_name}",
            color = embed_color,
        )
        embed.set_footer(text=ctx.guild.name, icon_url=ctx.guild.icon.url if ctx.guild.icon else None)
        embed.add_field(name="Donation Channel", value=f"<#{bank.donation_channel}>")
        embed.add_field(name="Log Channel", value=f"<#{bank.log_channel}>")
        embed.add_field(name="Manager Role", value=f"<@&{bank.manager_role}>")
        await react(ctx.message, self.bot.emoji.tick)
        await ctx.reply(embed=embed)

    @setup_dono.command(name="add", description="Add a bank in donation banks to auto-log the donations", aliases=["create"])
    @cmds.has_permissions(administrator=True)
    @util.describe(
        channel = "The channel for the donations",
        bank_name = "The name of the bank"
    )
    async def setup_dono_add(self, ctx: Context, channel: discord.TextChannel, bank_name: str):
        data = self.bot.db.dank.donation_settings.fetchone((ctx.guild.id, channel.id))
        if data:
            await react(ctx.message, self.bot.emoji.x_mark)
            return await ctx.reply(f"{self.bot.emoji.x_mark} | This channel is already registered with bank: `{data.bank_name}`", delete_after=10)
        self.bot.db.cursor.execute("SELECT * FROM dank_donation_settings WHERE gid = ? AND bank_name = ?", (ctx.guild.id, bank_name))
        data = self.bot.db.dank.donation_settings.parse(self.bot.db.cursor.fetchone())
        if data:
            await react(ctx.message, self.bot.emoji.x_mark)
            return await ctx.reply(f"{self.bot.emoji.x_mark} | The bank with name: `{data.bank_name}` already exists with channel: <#{data.donation_channel}>", delete_after=10)
        self.bot.db.dank.donation_settings.insert(ctx.guild.id, channel.id, None, bank_name, None)
        await react(ctx.message, self.bot.emoji.tick)
        await ctx.reply(f"{self.bot.emoji.tick} | Bank created in {channel.mention} with name: `{bank_name}`\nSetup manager via: `.setup dono manager <bank> <manager_role>`\nSetup log channel: `.setup dono log <bank> <log_channel>`", delete_after=15)

    @setup_dono.command(name="channel", description="Change/Set the donation channel for the bank", aliases=["donochannel"])
    @cmds.has_permissions(administrator=True)
    @util.describe(
        bank = "The bank to set the channel of (can be #channel or bank name)",
        channel = "The channel to set"
    )
    async def setup_dono_channel(self, ctx: Context, bank: DonoSetting, channel: discord.TextChannel):
        bank: structs.dank_donation_settings = bank
        data = self.bot.db.dank.donation_settings.fetchone((ctx.guild.id, channel.id))
        if data:
            await react(ctx.message, self.bot.emoji.x_mark)
            return await ctx.reply(f"{self.bot.emoji.x_mark} | This channel is already registered with bank: `{data.bank_name}`", delete_after=10)
        bank.donation_channel = channel
        if bank.log_channel:
            await ctx.guild.get_channel(bank.log_channel).send(f"Set donation channel of bank: `{bank.bank_name}` to: {channel.mention} (by: **{ctx.author}**)")
            await channel.send(f"Set donation channel of bank: `{bank.bank_name}` to: {channel.mention} (by: **{ctx.author.mention}**)")
        self.bot.db.dank.donation_settings.update_record(bank)
        await react(ctx.message, self.bot.emoji.tick)
        await ctx.reply(f"{self.bot.emoji.tick} | Set bank: `{bank.bank_name}` donation channel to: {channel.mention}", delete_after=10)

    @setup_dono.command(name="rename", description="Rename a bank (not channel)\n- NOTE: This does not change the bank name in the donations (for now)")
    @cmds.has_permissions(administrator=True)
    @util.describe(
        bank = "The bank to rename (can be #channel or bank name)",
        new_name = "The new name of the bank"
    )
    async def setup_dono_rename(self, ctx: Context, bank: DonoSetting, new_name: str):
        bank: structs.dank_donation_settings = bank
        self.bot.db.cursor.execute("SELECT * FROM dank_donation_settings WHERE gid = ? AND bank_name = ?", (ctx.guild.id, new_name))
        data = self.bot.db.dank.donation_settings.parse(self.bot.db.cursor.fetchone())
        if data:
            await react(ctx.message, self.bot.emoji.x_mark)
            return await ctx.reply(f"{self.bot.emoji.x_mark} | The bank with name: `{data.bank_name}` already exists with channel: <#{data.donation_channel}>", delete_after=10)
        if bank.log_channel:
            await ctx.guild.get_channel(bank.log_channel).send(f"Bank Renamed: `{bank.bank_name}` -> `{new_name}` by: {ctx.author.mention} (`{ctx.author.id}`)")
        old_name = f"{bank.bank_name}"
        bank.bank_name = new_name
        self.bot.db.dank.donation_settings.update_record(bank)
        await ctx.reply(f"{self.bot.emoji.tick} | Renamed bank: {old_name} to: {new_name}", delete_after=10)

    @setup_dono.command(name="manager", description="Set/Change the manager role of a particular bank", aliases=["mgr"])
    @cmds.has_permissions(administrator=True)
    @util.describe(
        bank = "The bank to set/change the manager of (can be #channel or bank name)",
        manager_role = "The Role to set as the bank manager"
    )
    async def setup_dono_manager(self, ctx: Context, bank: DonoSetting, manager_role: discord.Role):
        bank: structs.dank_donation_settings = bank
        bank.manager_role = manager_role.id
        self.bot.db.dank.donation_settings.update_record(bank)
        if bank.log_channel:
            await ctx.guild.get_channel(bank.log_channel).send(f"Set bank manager of bank: `{bank.bank_name}` to: **{manager_role.name}** (by: **{ctx.author}**)")
        await react(ctx.message, self.bot.emoji.tick)
        await ctx.reply(f"{self.bot.emoji.tick} | Set bank `{bank.bank_name}` manager to: **{manager_role.name}**", delete_after=10)

    @setup_dono.command(name="log", description="Set/Change the donation **__log__** channel of the bank", aliases=["log_channel", "logchannel", "logs"])
    @cmds.has_permissions(administrator=True)
    @util.describe(
        bank = "The bank of which to set the log channel (#channel or bank name)",
        channel = "The channel to set as the log channel"
    )
    async def setup_dono_log(self, ctx: Context, bank: DonoSetting, channel: discord.TextChannel):
        bank: structs.dank_donation_settings = bank
        if bank.log_channel:
            await ctx.guild.get_channel(bank.log_channel).send(f"Set log channel of bank: `{bank.bank_name}` to: {channel.mention} (by: **{ctx.author}**)")
            await channel.send(f"Set log channel of bank: `{bank.bank_name}` to: {channel.mention} (by: **{ctx.author.mention}**)")
        bank.log_channel = channel.id
        self.bot.db.dank.donation_settings.update_record(bank)
        await react(ctx.message, self.bot.emoji.tick)
        await ctx.reply(f"{self.bot.emoji.tick} | Set bank: `{bank.bank_name}` log channel to: {channel.mention}", delete_after=10)

    @setup_dono.command(name="remove", description="Delete a particular bank (this does not delete the donations & the channel)", aliases=["delete"])
    @cmds.has_permissions(administrator=True)
    @util.describe(bank="The bank to delete (#channel or bank name)")
    async def setup_dono_remove(self, ctx: Context, bank: DonoSetting):
        bank: structs.dank_donation_settings = bank
        if bank.log_channel:
            await ctx.guild.get_channel(bank.log_channel).send(f"Bank deleted: `{bank.bank_name}` by: {ctx.author.mention} (`{ctx.author}`)")
        self.bot.db.dank.donation_settings.delete(bank)
        await react(ctx.message, self.bot.emoji.tick)
        await ctx.reply(f"{self.bot.emoji.tick} | Bank: `{bank.bank_name}` deleted successfully", delete_after=10)

    @stp.group(name="grinder", description="Setup grinders", invoke_without_command=True, aliases=["grinders"])
    @cmds.has_permissions(administrator=True)
    async def setup_grinder(self, ctx: Context):
        if ctx.invoked_subcommand: return
        g_settings = self.bot.db.dank.grinder_settings.fetchone(ctx.guild.id)
        embed = discord.Embed(
            title = "Manage Dank Grinders",
            color = embed_color,
        )
        embed.set_footer(text=ctx.guild.name, icon_url=ctx.guild.icon.url if ctx.guild.icon else None)
        embed.set_author(name=self.bot.user.display_name, icon_url=self.bot.user.display_avatar.url)
        if not g_settings:
            embed.description = f"# {self.bot.emoji.x_mark} | Grinders are not setted up."
            embed.add_field(
                name = "Setup Grinder ~",
                value = (
                    f"**Payment Channel -** {util.generate_command_syntax(self.setup_grinder_channel)}\n"
                    f"**Logs Channel -** {util.generate_command_syntax(self.setup_grinder_logs)}\n"
                    f"**Reminder Channel -** {util.generate_command_syntax(self.setup_grinder_reminder)}\n"
                    f"**Grinder Role -** {util.generate_command_syntax(self.setup_grinder_paidrole)}\n"
                    f"**Trial Role -** {util.generate_command_syntax(self.setup_grinder_trialrole)}\n"
                    f"**Blacklisted Role -** {util.generate_command_syntax(self.setup_grinder_blacklistedrole)}\n"
                    f"**Manager Role -** {util.generate_command_syntax(self.setup_grinder_manager)}\n"
                    f"**Tiers -** {util.generate_command_syntax(self.setup_grinder_tiers)}\n"
                    f"**DISABLE GRINDERS -** {util.generate_command_syntax(self.setup_grinder_disable)}\n"
                )
            )
            embed.set_footer(text=embed.footer.text + "| use .setup grinders help to see how to setup grinders")
        else:
            embed.add_field(name="Payment Channel", value=f"<#{g_settings.pay_channel}>" if g_settings.pay_channel else "***`None`***")
            embed.add_field(name="Logs Channel", value=f"<#{g_settings.log_channel}>" if g_settings.log_channel else "***`None`***")
            embed.add_field(name="Reminder Channel", value=f"<#{g_settings.rem_channel}>" if g_settings.rem_channel else "***`None`***")
            embed.add_field(name="Grinder Role", value=f"<@&{g_settings.paid_role}>" if g_settings.paid_role else "***`None`***")
            embed.add_field(name="Trial Role", value=f"<@&{g_settings.trial_role}>" if g_settings.trial_role else "***`None`***")
            embed.add_field(name="Blacklisted Role", value=f"<@&{g_settings.blacklisted_role}>" if g_settings.blacklisted_role else "***`None`***")
            embed.add_field(name="Manager Role", value=f"<@&{g_settings.manager_role}>" if g_settings.manager_role else "***`None`***")
        await ctx.reply(embed=embed)

    @setup_grinder.command(name="channel", description="Set the grinder payments channel", aliases=["paymentchannel", "paychannel"])
    @cmds.has_permissions(administrator=True)
    @util.describe(channel="The channel to set as payment channel.")
    async def setup_grinder_channel(self, ctx: Context, channel: discord.TextChannel):
        g_settings = self.bot.db.dank.grinder_settings.fetchone(ctx.guild.id)
        if g_settings:
            g_settings.pay_channel = channel.id
            self.bot.db.dank.grinder_settings.update_record(g_settings)
            if g_settings.log_channel:
                await ctx.guild.get_channel(g_settings.log_channel).send(f"Set grinder payment channel: {channel.mention} by: {ctx.author.mention}")
        else:
            self.bot.db.dank.grinder_settings.insert(ctx.guild.id, channel.id, None, None, None, None, None, None)
        await react(ctx.message, self.bot.emoji.tick)
        await ctx.reply(f"{self.bot.emoji.tick} | Set grinder payment channel to {channel.mention}", delete_after=7)

    @setup_grinder.command(name="logchannel", description="Set the grinder logs channel", aliases=["logs", "log"])
    @cmds.has_permissions(administrator=True)
    @util.describe(channel="The channel to set as log channel")
    async def setup_grinder_logs(self, ctx: Context, channel: discord.TextChannel):
        g_settings = self.bot.db.dank.grinder_settings.fetchone(ctx.guild.id)
        if g_settings:
            if g_settings.log_channel:
                await ctx.guild.get_channel(g_settings.log_channel).send(f"Set grinder log channel: {channel.mention} by: {ctx.author.mention}")
            g_settings.log_channel = channel.id
            self.bot.db.dank.grinder_settings.update_record(g_settings)
        else:
            self.bot.db.dank.grinder_settings.insert(ctx.guild.id, None, channel.id, None, None, None, None, None)
        await channel.send(f"Set grinder log channel: {channel.mention} by: {ctx.author.mention}")
        await react(ctx.message, self.bot.emoji.tick)
        await ctx.reply(f"{self.bot.emoji.tick} | Set grinder logs channel to {channel.mention}", delete_after=7)

    @setup_grinder.command(
        name="reminders",
        description="Set the reminder fallback channel, if DM to the user fails the bot send's the reminder in this channel",
        aliases=["rem", "reminderchannel", "reminder", "remchannel", "reminderschannel", "remfall", "rfb", "reminderfallback", "remindersfallback", "remfallback", "remfb"]
    )
    @cmds.has_permissions(administrator=True)
    @util.describe(channel="The channel to set as reminder fallback channel")
    async def setup_grinder_reminder(self, ctx: Context, channel: discord.TextChannel):
        g_settings = self.bot.db.dank.grinder_settings.fetchone(ctx.guild.id)
        if g_settings:
            if g_settings.log_channel:
                await ctx.guild.get_channel(g_settings.log_channel).send(f"Set grinder reminder fallback channel: {channel.mention} by: {ctx.author.mention}")
            g_settings.rem_channel = channel.id
            self.bot.db.dank.grinder_settings.update_record(g_settings)
        else:
            self.bot.db.dank.grinder_settings.insert(ctx.guild.id, None, None, channel.id, None, None, None, None)
        await channel.send(f"Set grinder reminder fallback channel: {channel.mention} by: {ctx.author.mention}")
        await react(ctx.message, self.bot.emoji.tick)
        await ctx.reply(f"{self.bot.emoji.tick} | Set grinder reminder fallback channel to {channel.mention}", delete_after=7)

    @setup_grinder.command(name="paidrole", description="Sets the paid grinder role", aliases=["paidgrinder", "paid", "role"])
    @cmds.has_permissions(administrator=True)
    @util.describe(role="The role to set as paid grinder role")
    async def setup_grinder_paidrole(self, ctx: Context, role: discord.Role):
        g_settings = self.bot.db.dank.grinder_settings.fetchone(ctx.guild.id)
        if g_settings:
            g_settings.paid_role = role.id
            self.bot.db.dank.grinder_settings.update_record(g_settings)
            if g_settings.log_channel:
                await ctx.guild.get_channel(g_settings.log_channel).send(f"Set **{role}** as grinder paid role by: {ctx.author.mention}")
        else:
            self.bot.db.dank.grinder_settings.insert(ctx.guild.id, None, None, None, role.id, None, None, None)
        await react(ctx.message, self.bot.emoji.tick)
        await ctx.reply(f"{self.bot.emoji.tick} | Set grinder paid role to **{role}**", delete_after=7)

    @setup_grinder.command(name="trialrole", description="Set the trial grinder role", aliases=["trialgrinder", "trial"])
    @cmds.has_permissions(administrator=True)
    @util.describe(role="The role to set as trial grinder role")
    async def setup_grinder_trialrole(self, ctx: Context, role: discord.Role):
        g_settings = self.bot.db.dank.grinder_settings.fetchone(ctx.guild.id)
        if g_settings:
            g_settings.trial_role = role.id
            self.bot.db.dank.grinder_settings.update_record(g_settings)
            if g_settings.log_channel:
                await ctx.guild.get_channel(g_settings.log_channel).send(f"Set **{role}** as grinder trial role by: {ctx.author.mention}")
        else:
            self.bot.db.dank.grinder_settings.insert(ctx.guild.id, None, None, None, None, role.id, None, None)
        await react(ctx.message, self.bot.emoji.tick)
        await ctx.reply(f"{self.bot.emoji.tick} | Set grinder trial role to **{role}**", delete_after=7)

    @setup_grinder.command(name="blacklisted", description="Set the blacklisted grinder role", aliases=["blacklistedrole", "blr", "blacklistrole"])
    @cmds.has_permissions(administrator=True)
    @util.describe(role="The role to set as blacklisted grinder role")
    async def setup_grinder_blacklistedrole(self, ctx: Context, role: discord.Role):
        g_settings = self.bot.db.dank.grinder_settings.fetchone(ctx.guild.id)
        if g_settings:
            g_settings.blacklisted_role = role.id
            self.bot.db.dank.grinder_settings.update_record(g_settings)
            if g_settings.log_channel:
                await ctx.guild.get_channel(g_settings.log_channel).send(f"Set **{role}** as grinder blacklisted role by: {ctx.author.mention}")
        else:
            self.bot.db.dank.grinder_settings.insert(ctx.guild.id, None, None, None, None, None, role.id, None)
        await react(ctx.message, self.bot.emoji.tick)
        await ctx.reply(f"{self.bot.emoji.tick} | Set grinder blacklisted role to **{role}**", delete_after=7)

    @setup_grinder.command(name="manager", description="Set the grinder manager role", aliases=["mgr"])
    @cmds.has_permissions(administrator=True)
    @util.describe(role="The role to set as grinder manager role")
    async def setup_grinder_manager(self, ctx: Context, role: discord.Role):
        g_settings = self.bot.db.dank.grinder_settings.fetchone(ctx.guild.id)
        if g_settings:
            g_settings.manager_role = role.id
            self.bot.db.dank.grinder_settings.update_record(g_settings)
            if g_settings.log_channel:
                await ctx.guild.get_channel(g_settings.log_channel).send(f"Set **{role}** as grinder manager role by: {ctx.author.mention}")
        else:
            self.bot.db.dank.grinder_settings.insert(ctx.guild.id, None, None, None, None, None, None, role.id)
        await react(ctx.message, self.bot.emoji.tick)
        await ctx.reply(f"{self.bot.emoji.tick} | Set grinder manager role to **{role}**", delete_after=7)

    @setup_grinder.command(name="disable", description="Disable grinder system in this server", aliases=["unset", "off"])
    @cmds.has_permissions(administrator=True)
    async def setup_grinder_disable(self, ctx: Context):
        g_settings = self.bot.db.dank.grinder_settings.fetchone(ctx.guild.id)
        if not g_settings:
            await react(ctx.message, self.bot.emoji.x_mark)
            return await ctx.reply(f"{self.bot.emoji.x_mark} | Grinders are not yet setted up.", delete_after=7)
        if g_settings.log_channel:
            await ctx.guild.get_channel(g_settings.log_channel).send(f"## Grinders are disabled. by: {ctx.author.mention}")
        self.bot.db.dank.grinder_settings.delete(ctx.guild.id)
        await react(ctx.message, self.bot.emoji.tick)
        await ctx.reply(f"{self.bot.emoji.tick} | Disabled grinders.", delete_after=7)

    @setup_grinder.group(name="tiers", description="Setup grinder tiers", aliases=["tier"], invoke_without_command=True, cls=redef.Group)
    @cmds.has_permissions(administrator=True)
    @util.describe(tier="The tier to view details of (@role or tier name)")
    async def setup_grinder_tiers(self, ctx: Context, *, tier: Union[discord.Role, str]=None):
        if ctx.invoked_subcommand: return
        g_settings = self.bot.db.dank.grinder_settings.fetchone(ctx.guild.id)
        embed = discord.Embed(
            title = "Manage Dank Grinder Tiers",
            color = embed_color,
        )
        embed.set_footer(text=ctx.guild.name, icon_url=ctx.guild.icon.url if ctx.guild.icon else None)
        embed.set_author(name=self.bot.user.display_name, icon_url=self.bot.user.display_avatar.url)
        embed.set_footer(text=embed.footer.text + "| use .setup grinders tiers help to see how to setup grinder tiers.")
        if not g_settings:
            embed.description = f"## {self.bot.emoji.x_mark} | Grinders are not setted up."
        else:
            if tier:
                if isinstance(tier, str):
                    self.bot.db.cursor.execute(
                        "SELECT * FROM dank_grinder_tiers WHERE gid = ? AND name LIKE ?",
                        (ctx.guild.id, tier)
                    )
                    g_tier = self.bot.db.dank.grinder_tiers.parse(self.bot.db.cursor.fetchone())
                else: g_tier = self.bot.db.dank.grinder_tiers.fetchone((ctx.guild.id, tier.id))
                if not g_tier: return await ctx.reply(f"{self.bot.emoji.x_mark} | No tier found: **`{tier}`**")
                self.bot.db.cursor.execute("SELECT COUNT(*) FROM dank_grinder WHERE gid = ? AND tier = ?", (ctx.guild.id, g_tier.role_id))
                embed.description = (
                    f"**Role:** <@&{g_tier.role_id}>\n"
                    f"**Daily:** {coin} {g_tier.amount:,}\n"
                    f"**Weekly:** {coin} {(g_tier.amount*7):,}\n"
                    f"**Grinders:** {self.bot.db.cursor.fetchone()[0]:,}"
                )
            else:
                self.bot.db.cursor.execute("SELECT * FROM dank_grinder_tiers WHERE gid = ?", (ctx.guild.id,))
                tiers = [self.bot.db.dank.grinder_tiers.parse(*row) for row in self.bot.db.cursor.fetchall()]
                if tiers:
                    for tier in tiers:
                        embed.add_field(
                            name = tier.name,
                            value = (
                                f"**Role:** <@&{tier.role_id}>\n"
                                f"**Daily:** {coin} {tier.amount:,}\n"
                                f"**Weekly:** {coin} {(tier.amount*7):,}"
                                "\n" + empty_char
                            )
                        )
                else:
                    embed.description = (
                        f"**Add tier -** {util.generate_command_syntax(self.setup_grinder_tiers_add)}\n"
                        f"**Delete tier -** {util.generate_command_syntax(self.setup_grinder_tiers_remove)}\n"
                        f"**Update tier -** {util.generate_command_syntax(self.setup_grinder_tiers_update)}\n"
                    )
        await ctx.reply(embed=embed)

    @setup_grinder_tiers.command(name="add", description="Add/Create a grinder tier", aliases=["create"])
    @cmds.has_permissions(administrator=True)
    @util.describe(
        role = "The grinder tier role",
        amount = "The **__daily__** amount of tier",
        name = "The name of grinder tier (default to role name)"
    )
    async def setup_grinder_tiers_add(self, ctx: Context, role: discord.Role, amount: Amount, *, name: str = None):
        g_settings = self.bot.db.dank.grinder_settings.fetchone(ctx.guild.id)
        if not g_settings: 
            await react(ctx.message, self.bot.emoji.x_mark)
            return await ctx.reply(f"{self.bot.emoji.x_mark} | Grinders are not setted up.", delete_after=7)
        g_tier = self.bot.db.dank.grinder_tiers.fetchone((ctx.guild.id, role.id))
        if g_tier: 
            await react(ctx.message, self.bot.emoji.x_mark)
            return await ctx.reply(f"{self.bot.emoji.x_mark} | Tier **{role}** already exists.", delete_after=7)
        name = name or role.name
        self.bot.db.dank.grinder_tiers.insert(ctx.guild.id, role.id, amount, name)
        if g_settings.log_channel:
            await ctx.guild.get_channel(g_settings.log_channel).send(f"Tier **{name}** added. Daily Amount: {coin} {amount:,} by: {ctx.author.mention}")
        react(ctx.message, self.bot.emoji.tick)
        await ctx.reply(f"{self.bot.emoji.tick} | Tier **{name}** added. (Daily Amount: {coin} {amount:,})", delete_after=7)

    @setup_grinder_tiers.command(name="delete", description="Delete a grinder tier.", aliases=["remove"])
    @cmds.has_permissions(administrator=True)
    @util.describe(tier="The tier to delete (@role or tier name)")
    async def setup_grinder_tiers_remove(self, ctx: Context, tier: Union[discord.Role, str]):
        g_settings = self.bot.db.dank.grinder_settings.fetchone(ctx.guild.id)
        if not g_settings: 
            await react(ctx.message, self.bot.emoji.x_mark)
            return await ctx.reply(f"{self.bot.emoji.x_mark} | Grinders are not setted up.", delete_after=7)
        if isinstance(tier, str):
            self.bot.db.cursor.execute(
                "SELECT * FROM dank_grinder_tiers WHERE gid = ? AND name LIKE ?",
                (ctx.guild.id, tier)
            )
            g_tier = self.bot.db.dank.grinder_tiers.parse(self.bot.db.cursor.fetchone())
        else: g_tier = self.bot.db.dank.grinder_tiers.fetchone((ctx.guild.id, tier.id))
        if not g_tier: 
            await react(ctx.message, self.bot.emoji.x_mark)
            return await ctx.reply(f"{self.bot.emoji.x_mark} | No tier found: **`{tier}`**", delete_after=7)
        self.bot.db.dank.grinder_tiers.delete((ctx.guild.id, g_tier.role_id))
        if g_settings.log_channel:
            await ctx.guild.get_channel(g_settings.log_channel).send(f"Tier **{g_tier.name}** deleted. ({coin} {g_tier.amount:,}) by: {ctx.author.mention}")
        react(ctx.message, self.bot.emoji.tick)
        await ctx.reply(f"{self.bot.emoji.tick} | Tier **{tier}** Deleted. ({coin} {g_tier.amount:,})", delete_after=7)

    @setup_grinder_tiers.command(name="edit", description="Update a tier's daily payment amount or rename a tier", aliases=["update"])
    @cmds.has_permissions(administrator=True)
    @util.describe(
        tier = "The tier to update amount or rename",
        amount = "The daily amount of the tier",
        name = "The new name of the tier (optional)"
    )
    async def setup_grinder_tiers_update(self, ctx: Context, tier: Union[discord.Role, str], amount: Amount, *, name: str = None):
        g_settings = self.bot.db.dank.grinder_settings.fetchone(ctx.guild.id)
        if not g_settings: 
            await react(ctx.message, self.bot.emoji.x_mark)
            return await ctx.reply(f"{self.bot.emoji.x_mark} | Grinders are not setted up.", delete_after=7)
        if isinstance(tier, str):
            self.bot.db.cursor.execute(
                "SELECT * FROM dank_grinder_tiers WHERE gid = ? AND name LIKE ?",
                (ctx.guild.id, tier)
            )
            g_tier = self.bot.db.dank.grinder_tiers.parse(self.bot.db.cursor.fetchone())
        else: g_tier = self.bot.db.dank.grinder_tiers.fetchone((ctx.guild.id, tier.id))
        if not g_tier: 
            await react(ctx.message, self.bot.emoji.x_mark)
            return await ctx.reply(f"{self.bot.emoji.x_mark} | No tier found: **`{tier}`**", delete_after=7)
        g_tier.amount = amount
        g_tier.name = name or g_tier.name
        self.bot.db.dank.grinder_tiers.update_record(g_tier)
        if g_settings.log_channel:
            await ctx.guild.get_channel(g_settings.log_channel).send(f"Tier **{tier}** > **{g_tier.name}** updated. ({coin} {g_tier.amount:,}) by: {ctx.author.mention}")
        react(ctx.message, self.bot.emoji.tick)
        m = await ctx.reply(f"{self.bot.emoji.tick} | Tier **{g_tier.name}** Update. ({coin} {g_tier.amount:,}) (old name: **{tier}**)", delete_after=7)

async def setup(bot: Bot):
    await bot.add_cog(setup_cog(bot))

    for sub_cog in os.listdir(os.path.dirname(__file__)):
        if sub_cog in ["__init__.py", "__pycache__"]: continue
        name = sub_cog.split(".")[0]
        await bot.load_extension(f"{__name__}.{name}")
        bot._all_cogs.add(f"{__name__}.{name}")

async def teardown(bot: Bot):
    for sub_cog in os.listdir(os.path.dirname(__file__)):
        if sub_cog in ["__init__.py", "__pycache__"]: continue
        name = sub_cog.split(".")[0]
        await bot.unload_extension(f"{__name__}.{name}")