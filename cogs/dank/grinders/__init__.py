import asyncio
import datetime
import io
import os
from typing import Union

from matplotlib import pyplot as plt
import numpy as np

from utils import (
    color,
    ghost_url,
    embed_color,
    Bot,
    react,
    redef,
    utility as util
)

from .. import Amount, coin

import discord
from discord import ui
from discord.ext import commands as cmds

class Context(cmds.Context):
    bot: Bot

class dank_grinder_cog(cmds.Cog):
    def __init__(self, bot: Bot):
        super().__init__()
        self.bot: Bot = bot

    @util.group(description="Manage dank memer grinders", invoke_without_commands=True, aliases=["grinders"])
    async def grinder(self, ctx: cmds.Context):
        if ctx.invoked_subcommand:
            if ctx.invoked_subcommand.name != "help": return
        embed = discord.Embed(
            title = "Grinders",
            color = embed_color,
            description = f"{self.bot.emoji.construction}"
        )
        embed.set_author(name=ctx.guild.name, icon_url=ctx.guild.icon.url if ctx.guild.icon else None)
        embed.set_footer(text=f"Made by: {self.bot.made_by}", icon_url=ghost_url)
        # embed.set_thumbnail(url=ctx.guild.icon.url if ctx.guild.icon else None)
        await ctx.reply(embed=embed)

    def is_grinder_manager():
        def predicate(ctx: Context):
            g_settings = ctx.bot.db.dank.grinder_settings.fetchone(ctx.guild.id)
            if g_settings is None:
                raise cmds.CheckFailure("Grinders are not yet setted up.")
            if ctx.author.get_role(g_settings.manager_role) == None:
                raise cmds.CheckFailure("You are not a grinder manager.")
            return True
        return cmds.check(predicate)

    @grinder.command(name="summary", description="Shows grinder summary.")
    @is_grinder_manager()
    async def grinder_summary(self, ctx: cmds.Context):
        self.bot.db.cursor.execute(f"SELECT COUNT(*) FROM dank_grinder WHERE gid = {ctx.guild.id}")
        total = self.bot.db.cursor.fetchone()
        total = total[0] if total else 0

        self.bot.db.cursor.execute(f"SELECT COUNT(*) FROM dank_grinder WHERE gid = {ctx.guild.id} AND next_pay > strftime('%s', 'now')")
        paid = self.bot.db.cursor.fetchone()
        paid = paid[0] if paid else 0
        
        self.bot.db.cursor.execute(f"SELECT COUNT(*) FROM dank_grinder WHERE gid = {ctx.guild.id} AND next_pay <= strftime('%s', 'now')")
        due = self.bot.db.cursor.fetchone()
        due = due[0] if due else 0
        
        self.bot.db.cursor.execute(f"SELECT COUNT(*) * dt.amount * 7 AS total FROM dank_grinder dg JOIN dank_grinder_tiers dt ON dg.tier = dt.role_id WHERE dg.gid = {ctx.guild.id} GROUP BY dg.tier")
        expected_amount = self.bot.db.cursor.fetchone()
        expected_amount = expected_amount[0] if expected_amount else 0
        
        self.bot.db.cursor.execute(f"SELECT COUNT(*) * dt.amount * 7 AS total FROM dank_grinder dg JOIN dank_grinder_tiers dt ON dg.tier = dt.role_id WHERE dg.gid = {ctx.guild.id} AND dg.next_pay > strftime('%s', 'now') GROUP BY dg.tier")
        actual_amount = self.bot.db.cursor.fetchone()
        actual_amount = actual_amount[0] if actual_amount else 0

        x = [paid, due]
        colors = plt.get_cmap("Dark2")(np.linspace(0.2, 0.7, 2))
        fig, ax = plt.subplots()
        ax.set(xlim=(0, 8), xticks=np.arange(1, 8),
                 ylim=(0, 8), yticks=np.arange(1, 8)) 
        ax.pie(x, colors=colors, radius=3, center=(4, 4), frame=True)
        ax.set_facecolor("black")
        fig.patch.set_facecolor("black")
        with io.BytesIO() as fp:
            fig.savefig(fp, format="png"); fp.seek(0)
            pie_chart = discord.File(fp, filename="pie_chart.png")
    
        embed = discord.Embed(
            title = "Grinder Summary",
            color = embed_color,
            timestamp = datetime.datetime.now()
        )
        embed.set_thumbnail(url="attachment://pie_chart.png")
        embed.add_field(
            name = "Grinders",
            value = (
                f"**Total:** `{total}`\n"
                f"**Paid:** `{paid}`\n"
                f"**Pending:** `{due}`\n"
            )
        )
        embed.add_field(
            name = "Weekly Amount",
            value = (
                f"**Expected:** {coin} {expected_amount:,}\n"
                f"**Actual:** {coin} {actual_amount:,}"
            )
        )
        embed.set_author(
            name=ctx.guild.name,
            icon_url=ctx.guild.icon.url if ctx.guild.icon else None
        )
        await ctx.reply(embed=embed, files=[pie_chart])

    @grinder.command(name="add", description="Appoint a user as a grinder.", aliases=["appoint"])
    @is_grinder_manager()
    @util.describe(
        member = "The member to appoint as a grinder",
        tier = "The tier to assign to the grinder. Can be a role or a name of the tier."
    )
    async def grinder_add(self, ctx: cmds.Context, member: discord.Member, *, tier: Union[discord.Role, str]):
        g_user = self.bot.db.dank.grinder.fetchone((ctx.guild.id, member.id))
        if g_user:
            await react(ctx.message, self.bot.emoji.x_mark)
            return await ctx.reply(f"{self.bot.emoji.x_mark} | {member.mention} is already a grinder.", delete_after=10)
        if isinstance(tier, str):
            self.bot.db.cursor.execute(
                "SELECT * FROM dank_grinder_tiers WHERE gid = ? AND name LIKE ?",
                (ctx.guild.id, tier)
            )
            tier_rec = self.bot.db.dank.grinder_tiers.parse(self.bot.db.cursor.fetchone())
        else: tier_rec = self.bot.db.dank.grinder_tiers.fetchone((ctx.guild.id, tier.id))
        if not tier_rec:
            await react(ctx.message, self.bot.emoji.x_mark)
            return await ctx.reply(f"{self.bot.emoji.x_mark} | No tier found: **`{tier}`**", delete_after=10)
        t = int(datetime.datetime.now().timestamp())
        g_settings = self.bot.db.dank.grinder_settings.fetchone(ctx.guild.id)
        await member.add_roles(
            discord.Object(g_settings.trial_role, type=discord.Role),
            reason = f"Appointed as grinder. by: {ctx.author}"
        )
        embed = discord.Embed(
            title="Grinder Appointed",
            timestamp = datetime.datetime.now()
        )
        embed.add_field(name="Grinder:", value=member.mention)
        embed.add_field(name="Appointed by:", value=ctx.author.mention)
        embed.set_author(name=ctx.guild.name, icon_url=ctx.guild.icon.url if ctx.guild.icon else None)
        self.bot.db.dank.grinder.insert(ctx.guild.id, member.id, tier_rec.role_id, 0, t, t, True, False)
        await ctx.guild.get_channel(g_settings.log_channel).send(embed=embed)
        embed.clear_fields()
        embed.description = f"You are appointed as a grinder **by:** `{ctx.author}`. For you to be accepted as a grinder you need to pay 1 week's worth of payment."
        embed.add_field(
            name="Payment Info:",
            value= (
                f"**Daily:** {coin} {tier_rec.amount:,}\n"
                f"**Weekly:** {coin} {(tier_rec.amount*7):,}"
            )
        )
        try:
            dm = await member.create_dm()
            await dm.send(embed=embed)
        except:
            await ctx.reply(f"{self.bot.emoji.warning} | Unable to DM `{member}`", delete_after=10)
        await react(ctx.message, self.bot.emoji.tick)
        await ctx.reply(f"{self.bot.emoji.tick} | Appointed {member.mention} as grinder. **Tier: {tier_rec.name}**", delete_after=10)

    @grinder.command(name="view", description="View details about a particular grinder", aliases=["stats", "bank"])
    @util.describe(member = "The member to view grinder stats of. (Default to you)")
    async def grinder_view(self, ctx: cmds.Context, member: discord.Member = cmds.Author):
        g_user = self.bot.db.dank.grinder.fetchone((ctx.guild.id, member.id))
        if not g_user:
            await react(ctx.message, self.bot.emoji.x_mark)
            return await ctx.reply(f"{self.bot.emoji.x_mark} | {member.mention} is not a grinder.", delete_after=10)
        tier = self.bot.db.dank.grinder_tiers.fetchone((ctx.guild.id, g_user.tier))
        current_time = int(datetime.datetime.now().timestamp())
        due_amount = int((current_time - g_user.next_pay) / (60 * 60 * 24)) * tier.amount
        embed = discord.Embed(title="Grinder Stats", color=embed_color)
        embed.set_author(name=member.display_name, icon_url=member.display_avatar.url)
        embed.set_footer(text=ctx.guild.name, icon_url=ctx.guild.icon.url if ctx.guild.icon else None)
        embed.add_field(name="Tier", value=tier.name)
        embed.add_field(name="Next payment", value=f"<t:{g_user.next_pay}:D>")
        embed.add_field(name="Grinder Since", value=f"<t:{g_user.grinder_since}:R>")
        embed.add_field(name="Amount per grind", value=f"Daily: {coin} {tier.amount:,}\nWeekly: {coin} {(tier.amount*7):,}")
        if g_user.next_pay < current_time and due_amount > 0:
            embed.add_field(name="Pending Amount", value=f"{coin} {due_amount:,}")
        embed.add_field(name="Grinder Bank", value=f"{coin} {g_user.total_paid:,}")
        if g_user.blacklisted: embed.add_field(name="Blacklisted", value="Yes")
        elif g_user.trial: embed.add_field(name="Trial Grinder", value="Yes")
        await ctx.reply(embed=embed)

    @grinder.command(name="remind", description="Send a reminder to a user about their pending grinder payment.", aliases=["alert"])
    @is_grinder_manager()
    @util.rename(user = "grinder")
    @util.describe(
        user = "The user to send a reminder to.",
        note = "A note to include in the reminder"
    )
    async def grinder_remind(self, ctx: cmds.Context, user: discord.User = None, *, note: str = ""):
        if user == None:
            await react(ctx.message, self.bot.emoji.x_mark)
            return await ctx.reply(f"{self.bot.emoji.x_mark} | Sending reminder to all users is currently not supported by the bot.", delete_after=10)
        grinder = self.bot.db.dank.grinder.fetchone((ctx.guild.id, user.id))
        if not grinder:
            await react(ctx.message, self.bot.emoji.x_mark)
            return await ctx.reply(f"{self.bot.emoji.x_mark} | **{user.mention}** is not a grinder.", delete_after=10)
        current_time = int(datetime.datetime.now().timestamp())
        due_days = int((current_time - grinder.next_pay) / (60 * 60 * 24))
        if due_days < 1:
            await react(ctx.message, self.bot.emoji.x_mark)
            return await ctx.reply(f"{self.bot.emoji.x_mark} | **{user.mention}** have no pending payments.", delete_after=10)
        tier = self.bot.db.dank.grinder_tiers.fetchone((ctx.guild.id, grinder.tier))
        g_settings = self.bot.db.dank.grinder_settings.fetchone(ctx.guild.id)
        embed = discord.Embed(
            title = "Grinder Reminder",
            color = embed_color,
            timestamp = datetime.datetime.now(),
            description = (
                f"**Sent by:** {ctx.author.display_name} (`{ctx.author}`)\n"
                f"Your __**Grinder Payments**__ are pending for  **{due_days} day{'s' if due_days > 1 else ''}**\n"
                f"Make sure to inform staff if you have any trouble with the donations.\n"
                f"**Amount due:** {coin} {(due_days * tier.amount):,}\n"
                + (f"**Note:** ```{note}```" if note else "")
            )
        )
        embed.set_footer(text=ctx.guild.name, icon_url=ctx.guild.icon.url if ctx.guild.icon else None)
        embed.set_author(name=user.global_name, icon_url=user.display_avatar.url)
        button = ui.Button(
            label = "Pay Here",
            url=f"https://discord.com/channels/{grinder.gid}/{g_settings.pay_channel}",
            emoji=self.bot.emoji.txt
        )
        view = ui.View(timeout=1); view.add_item(button)
        try:
            dm = await user.create_dm()
            await dm.send(embed=embed, view=view)
            await react(ctx.message, self.bot.emoji.tick)
            await ctx.reply(f"{self.bot.emoji.tick} | Sent a reminder to `{user}`", delete_after=10)
        except: 
            await react(ctx.message, self.bot.emoji.warning)
            await react(ctx.message, self.bot.emoji.tick)
            await ctx.guild.get_channel(g_settings.rem_channel).send(user.mention, embed=embed)
            await ctx.reply(f"{self.bot.emoji.x_mark} | Unable to DM `{user}`, reminded in <#{g_settings.rem_channel}>", delete_after=10)

    @grinder.command(name="blacklist", description="blacklist a grinder.", aliases=["bl"])
    @is_grinder_manager()
    @util.describe(
        user = "The user to grinder blacklist.",
        reason = "The reason for blacklisting the user."
    )
    async def grinder_blacklist(self, ctx: cmds.Context, user: discord.Member, *, reason: str = "No reason"):
        grinder = self.bot.db.dank.grinder.fetchone((ctx.guild.id, user.id))
        if not grinder:
            await react(ctx.message, self.bot.emoji.x_mark)
            return await ctx.reply(f"{self.bot.emoji.x_mark} | {user.mention} is not a grinder.", delete_after=10)
        if grinder.blacklisted:
            await react(ctx.message, self.bot.emoji.x_mark)
            return await ctx.reply(f"{self.bot.emoji.x_mark} | {user.mention} is already blacklisted", delete_after=10)
        g_settings = self.bot.db.dank.grinder_settings.fetchone(ctx.guild.id)
        await user.remove_roles(
            discord.Object(g_settings.trial_role, type=discord.Role),
            discord.Object(g_settings.paid_role, type=discord.Role),
            discord.Object(grinder.tier, type=discord.Role),
            reason = f"Grinder blacklisted by: {ctx.author} for reason: {reason}", atomic = True
        )
        await user.add_roles(
            discord.Object(g_settings.blacklisted_role, type=discord.Role),
            reason = f"Grinder blacklisted by: {ctx.author} for reason: {reason}", atomic = True
        )
        embed = discord.Embed(
            title = "Grinder Blacklisted",
            color = embed_color,
            timestamp = datetime.datetime.now(),
            description = (
                f"**Grinder:** {user.mention} (`{user}`)\n"
                f"**By:** {ctx.author.mention} (`{ctx.author}`)\n"
                f"**Reason:** ```{reason}```"
            )
        )
        embed.set_author(name=user.display_name, icon_url=user.display_avatar.url)
        embed.set_footer(text=ctx.guild.name, icon_url=ctx.guild.icon.url if ctx.guild.icon else None)
        grinder.blacklisted = True
        self.bot.db.dank.grinder.update_record(grinder)
        await ctx.guild.get_channel(g_settings.log_channel).send(embed=embed)
        try:
            dm = await user.create_dm()
            embed.description = (
                f"**__You were blacklisted from grinders.__**\n"
                f"**By:** `{ctx.author}`\n"
                f"**Reason:** ```{reason}```"
            )
            await dm.send(embed=embed)
        except: 
            await react(ctx.message, self.bot.emoji.warning)
            await ctx.reply(f"{self.bot.emoji.warning} | Unable to send DM to `{user.name}`", delete_after=10)
        await react(ctx.message, self.bot.emoji.tick)
        await ctx.reply(f"{self.bot.emoji.tick} | Grinder {user.mention} blacklisted for reason: ```{reason}```", delete_after=10)

    @grinder.command(name="removeblacklist", description="Un blacklist a grinder.", aliases=["rbl", "ubl", "unblacklist"])
    @is_grinder_manager()
    @util.describe(
        user = "The user to remove from grinder blacklist.",
        reason = "The reason for removing the blacklist."
    )
    async def grinder_remove_blacklist(self, ctx: cmds.Context, user: discord.Member, *, reason: str = "No reason"):
        grinder = self.bot.db.dank.grinder.fetchone((ctx.guild.id, user.id))
        if not grinder: 
            await react(ctx.message, self.bot.emoji.x_mark)
            return await ctx.reply(f"{self.bot.emoji.x_mark} | {user.mention} is not a grinder", delete_after=10)
        if not grinder.blacklisted: 
            await react(ctx.message, self.bot.emoji.x_mark)
            return await ctx.reply(f"{self.bot.emoji.x_mark} | {user.mention} is not blacklisted", delete_after=10)
        g_settings = self.bot.db.dank.grinder_settings.fetchone(ctx.guild.id)
        await user.remove_roles(
            discord.Object(g_settings.blacklisted_role, type=discord.Role),
            reason = f"Removed blacklist by: {ctx.author} for reason: {reason}", atomic=True
        )
        if grinder.trial:
            await user.add_roles(
                discord.Object(g_settings.trial_role, type=discord.Role),
                reason = f"Removed blacklist by: {ctx.author} for reason: {reason}", atomic=True
            )
        else:
            await user.add_roles(
                discord.Object(g_settings.paid_role, type=discord.Role),
                discord.Object(grinder.tier, type=discord.Role),
                reason = f"Removed blacklist by: {ctx.author} for reason: {reason}", atomic=True
            )
        embed = discord.Embed(
            title = "Un-blacklisted a grinder",
            color = embed_color,
            timestamp = datetime.datetime.now(),
            description = (
                f"**Grinder:** {user.mention} (`{user}`)\n"
                f"**By:** {ctx.author.mention} (`{ctx.author}`)\n"
                f"**Reason:** ```{reason}```"
            )
        )
        embed.set_author(name=user.display_name, icon_url=user.display_avatar.url)
        embed.set_footer(text=ctx.guild.name, icon_url=ctx.guild.icon.url if ctx.guild.icon else None)
        grinder.blacklisted = False; grinder.next_pay = int(datetime.datetime.now().timestamp())
        self.bot.db.dank.grinder.update_record(grinder)
        await ctx.guild.get_channel(g_settings.log_channel).send(embed=embed)
        try:
            dm = await user.create_dm()
            embed.description = (
                f"**__You are no longer blacklisted from grinders.__**\n"
                f"**By:** `{ctx.author}`\n"
                f"**Reason:** ```{reason}```"
            )
            await dm.send(embed=embed)
        except: 
            await react(ctx.message, self.bot.emoji.warning)
            await ctx.reply(f"{self.bot.emoji.warning} | Unable to send DM to `{user.name}`", delete_after=10)
        await react(ctx.message, self.bot.emoji.tick)
        await ctx.reply(f"{self.bot.emoji.tick} | Grinder {user.mention} is removed from the grinder blacklist for reason: ```{reason}```", delete_after=10)

    @grinder.command(name="remove", description="Remove a grinder.", aliases=["dismiss"])
    @is_grinder_manager()
    @util.rename(user = "grinder")
    @util.describe(
        user = "The grinder to dismiss/remove",
        reason = "The reason to dismiss the grinder"
    )
    async def grinder_remove(self, ctx: cmds.Context, user: discord.Member, *, reason="No Reason"):
        grinder = self.bot.db.dank.grinder.fetchone((ctx.guild.id, user.id))
        if not grinder:
            await react(ctx.message, self.bot.emoji.x_mark)
            return await ctx.reply(f"{self.bot.emoji.x_mark} | {user.mention} is not a grinder.")
        g_settings = self.bot.db.dank.grinder_settings.fetchone(ctx.guild.id)
        embed = discord.Embed(
            title = "Grinder dismissed",
            color = embed_color,
            timestamp = datetime.datetime.now(),
            description = (
                f"**Grinder:** {user.mention} (`{user}`)\n"
                f"**By:** {ctx.author.mention} (`{ctx.author}`)\n"
                f"**Grinder bank:** {coin} {grinder.total_paid:,}\n"
                f"**Reason:** ```{reason}```"
            )
        )
        embed.set_author(name=user.display_name, icon_url=user.display_avatar.url)
        embed.set_footer(text=ctx.guild.name, icon_url=ctx.guild.icon.url if ctx.guild.icon else None)
        await user.remove_roles(
            discord.Object(grinder.tier, type=discord.Role),
            discord.Object(g_settings.trial_role, type=discord.Role),
            discord.Object(g_settings.paid_role, type=discord.Role),
            reason = f"Grinder dismissed by: {ctx.author} for reason: {reason}", atomic= True
        )
        self.bot.db.dank.grinder.delete((ctx.guild.id, user.id))
        await ctx.guild.get_channel(g_settings.log_channel).send(embed=embed)
        try:
            dm = await user.create_dm()
            embed.description = (
                f"__**Unfortunately you were dismissed from the grinders.**__\n"
                f"Bank: {coin} {grinder.total_paid:,}\n"
                f"**By:** {ctx.author.mention} (`{ctx.author}`)\n"
                f"**Reason:** ```{reason}```\n"
                f"-# (bank is reset to 0 because you are dismissed.)"
            )
            await dm.send(embed=embed)
        except:
            await react(ctx.message, self.bot.emoji.warning)
            await ctx.reply(f"{self.bot.emoji.warning} | Failed to send DM to `{user}`", delete_after=10)
        await react(ctx.message, self.bot.emoji.tick)
        await ctx.reply(f"{self.bot.emoji.tick} | {user.mention} dismissed from grinders.", delete_after=10)

    @grinder.command(name="accept", description="Accept a trial grinder as a grinder")
    @is_grinder_manager()
    @util.rename(user = "grinder")
    @util.describe(
        user = "The trial grinder to promote as accepted grinder.",
        reason = "The reason for accepting the grinder."
    )
    async def grinder_accept(self, ctx: cmds.Context, user: discord.Member, *, reason="No Reason"):
        grinder = self.bot.db.dank.grinder.fetchone((ctx.guild.id, user.id))
        if not grinder:
            await react(ctx.message, self.bot.emoji.x_mark)
            return await ctx.reply(f"{self.bot.emoji.x_mark} | {user.mention} is not a grinder.", delete_after=10)
        g_settings = self.bot.db.dank.grinder_settings.fetchone(ctx.guild.id)
        tier = self.bot.db.dank.grinder_tiers.fetchone((ctx.guild.id, grinder.tier))
        grinder.trial = False
        self.bot.db.dank.grinder.update_record(grinder)
        await user.add_roles(
            discord.Object(grinder.tier, type=discord.Role),
            discord.Object(g_settings.paid_role, type=discord.Role),
            reason = f"Accepted grinder by: {ctx.author} reason: {reason}", atomic=True
        )
        await user.remove_roles(
            discord.Object(g_settings.trial_role, type=discord.Role),
            reason = f"Accepted grinder by: {ctx.author} reason: {reason}", atomic=True
        )
        ee = discord.Embed(
            title = "Congratulations !!! :tada: :tada:",
            description = (
                "You are now an accpeted grinder.\n"
                f"**Accepted By:** `{ctx.author}`"
            ),
            color = embed_color,
            timestamp = datetime.datetime.now()
        )
        ee.add_field(
            name = "Payments:",
            value = (
                f"**Daily:** {coin} {tier.amount:,}\n"
                f"**Weekly:** {coin} {(tier.amount*7):,}\n"
                f"-# (You can pay for any number of days)"
            )
        )
        ee.set_footer(text=ctx.guild.name, icon_url=ctx.guild.icon.url if ctx.guild.icon else None)
        ee.set_author(name=user.name, icon_url=user.display_avatar.url)
        try:
            dm = await user.create_dm()
            await dm.send(embed=ee)
        except:
            await react(ctx.message, self.bot.emoji.warning)
            await ctx.reply(f"{self.bot.emoji.warning} | Unable to DM {user.mention} (`{user.name}`)", delete_after=10)
        e = discord.Embed(
            title = "Accepted Grinder",
            description = f"{user.mention} has been accpeted as a grinder.",
            timestamp = datetime.datetime.now(),
            color = embed_color
        )
        e.set_footer(text=f"By: {ctx.author}", icon_url=ctx.author.display_avatar.url)
        e.set_author(name=user.display_name, icon_url=user.display_avatar.url)
        await ctx.guild.get_channel(g_settings.log_channel).send(embed=e)
        await react(ctx.message, self.bot.emoji.tick)
        await ctx.reply(f"{self.bot.emoji.tick} | Accepted {user.mention} as a grinder.", delete_after=10)

    @grinder.command(name="update", description="Change a grinder's tier.", aliases=["edit"])
    @is_grinder_manager()
    @util.rename(user="grinder")
    @util.describe(
        user = "The grinder to update the tier of",
        tier = "The tier to put to the grinder (can be both role or tier name)"
    )
    async def grinder_update(self, ctx: Context, user: discord.Member, *, tier: Union[discord.Role, str]):
        g_user = self.bot.db.dank.grinder.fetchone((ctx.guild.id, user.id))
        if not g_user:
            await react(ctx.message, self.bot.emoji.x_mark)
            return await ctx.reply(f"{self.bot.emoji.x_mark} | {user.mention} is not a grinder.", delete_after=10)
        if isinstance(tier, str):
            self.bot.db.cursor.execute(
                "SELECT * FROM dank_grinder_tiers WHERE gid = ? AND name LIKE ?",
                (ctx.guild.id, tier)
            )
            g_tier = self.bot.db.dank.grinder_tiers.parse(self.bot.db.cursor.fetchone())
        else: g_tier = self.bot.db.dank.grinder_tiers.fetchone((ctx.guild.id, tier.id))
        if not g_tier:
            await react(ctx.message, self.bot.emoji.x_mark)
            return await ctx.reply(f"{self.bot.emoji.x_mark} | No tier found: **`{tier}`**", delete_after=10)
        g_settings = self.bot.db.dank.grinder_settings.fetchone(ctx.guild.id)
        await user.remove_roles(
            discord.Object(g_user.tier, type=discord.Role),
            reason = f"{ctx.author} updated grinder {user} set tier: {tier}",
            atomic = True
        )
        await user.add_roles(
            discord.Object(g_tier.role_id, type=discord.Role),
            reason = f"{ctx.author} updated grinder {user} set tier: {tier}",
            atomic = True
        )
        g_user.tier = g_tier.role_id
        self.bot.db.dank.grinder.update_record(g_user)
        await ctx.guild.get_channel(g_settings.log_channel).send(f"{user.mention} (`{user}`) has been updated to tier: **{g_tier.name}**, by: {ctx.author.mention}")
        await react(ctx.message, self.bot.emoji.tick)
        await ctx.reply(f"{self.bot.emoji.tick} | Updated {user.mention}'s tier to **{g_tier.name}**", delete_after=10)

    @grinder.command(name="logdono", description="Manually log grinder payment for a user", aliases=["log-dono", "logpay", "log-pay", "ld", "lp", "log"])
    @is_grinder_manager()
    @util.rename(user="grinder")
    @util.describe(
        user = "The grinder to log the payment of",
        amount = "The amount to log into the payment"
    )
    async def grindr_logdono(self, ctx: cmds.Context, user: discord.Member, amount: Amount=None):
        if amount is None and ctx.message.reference is None:
            await react(ctx.message, self.bot.emoji.x_mark)
            return await ctx.reply(f"{self.bot.emoji.x_mark} | Either reply to dank's donation message or enter the amount manually.", delete_after=10)
        if amount is None:
            await react(ctx.message, self.bot.emoji.x_mark)
            return await ctx.reply(f"{self.bot.emoji.x_mark} | Contact devs. (Error: `020189`)", delete_after=20)
        grinder = self.bot.db.dank.grinder.fetchone((ctx.guild.id, user.id))
        if not grinder:
            await react(ctx.message, self.bot.emoji.x_mark)
            return await ctx.reply(f"{self.bot.emoji.x_mark} | {user.mention} is not a grinder.", delete_after=10)
        if grinder.trial:
            await react(ctx.message, self.bot.emoji.warning)
            await ctx.reply(f"{self.bot.emoji.warning} | {user.mention} is a trial grinder. use `.grinder accept @{user}` to accept", delete_after=10)
        g_settings = self.bot.db.dank.grinder_settings.fetchone(ctx.guild.id)
        g_tier = self.bot.db.dank.grinder_tiers.fetchone((ctx.guild.id, grinder.tier))
        days = int(amount / g_tier.amount)
        grinder.next_pay += int((amount / g_tier.amount) * 24 * 60 * 60)
        grinder.total_paid += amount
        self.bot.db.dank.grinder.update_record(grinder)
        embed = discord.Embed(
            title = "Amount Added",
            color = embed_color,
            timestamp = datetime.datetime.now(),
        )
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
        embed.set_footer(text=ctx.guild.name, icon_url=ctx.guild.icon.url if ctx.guild.icon else None)
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.add_field(name="Paid for", value=f"{days} day{'s' if days > 1 else ''}")
        embed.add_field(name="Amount", value=f"{coin} {amount:,}")
        embed.add_field(name="Credited to", value=user.mention)
        button = ui.Button(url=ctx.message.jump_url, label="Jump to message")
        view = ui.View(timeout=1); view.add_item(button)
        await ctx.guild.get_channel(g_settings.log_channel).send(embed=embed, view=view)
        await react(ctx.message, self.bot.emoji.tick)
        await ctx.reply(f"{self.bot.emoji.tick} | logged {coin} {amount:,} for {user.mention} ({days} day{'s' if days > 1 else ''})", delete_after=10)

async def setup(bot: Bot):

    await bot.add_cog(dank_grinder_cog(bot))

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