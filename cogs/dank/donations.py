import asyncio
import datetime
from enum import Enum
import io
import time
from typing import Union

from utils import Bot, color, react, Context, structs
from utils import utility as util
from utils import ghost_url, embed_color, empty_char

import discord
from discord import ui, Interaction
from discord.ext import tasks
from discord.ext import commands as cmds
from discord import Interaction, app_commands as acmds
from discord import RawMessageUpdateEvent

from utils import plotter
from utils.redef import Command

from . import Amount, dank_id, coin

import base64

def int_to_base64(n: int) -> str:
    byte_length = (n.bit_length() + 7) // 8 or 1
    int_bytes = n.to_bytes(byte_length, 'big')
    b64 = base64.b64encode(int_bytes).decode('ascii')
    return b64.rstrip('=')

def base64_to_int(b64: str) -> int:
    # Add padding back if needed
    padding_needed = (4 - len(b64) % 4) % 4
    b64_padded = b64 + ('=' * padding_needed)
    int_bytes = base64.b64decode(b64_padded)
    return int.from_bytes(int_bytes, 'big')


class DonoSetting(cmds.Converter[structs.dank_donation_settings]):
    async def convert(self, ctx: Context, argument: str) -> structs.dank_donation_settings:
        ctx.bot.db.cursor.execute("SELECT * FROM dank_donation_settings WHERE gid = ? AND bank_name = ?", (ctx.guild.id, argument.lower()))
        g_settings = ctx.bot.db.dank.donation_settings.parse(ctx.bot.db.cursor.fetchone())
        if not g_settings:
            try: channel = cmds.GuildChannelConverter._resolve_channel(ctx, argument, 'text_channels', discord.TextChannel)
            except cmds.ChannelNotFound: channel = discord.Object(0)
            g_settings = ctx.bot.db.dank.donation_settings.fetchone((ctx.guild.id, channel.id))
            if g_settings is None:
                await react(ctx.message, ctx.bot.emoji.x_mark)
                if channel is not None:
                    raise cmds.BadArgument(f"'{channel.name}' is not a donation channel.")
                raise cmds.BadArgument(f"No bank found: '{argument.lower()}'")
        if not g_settings.manager_role:
            raise cmds.CheckFailure(f"Manager role for bank '{g_settings.bank_name}' was not set.")
        if ctx.author.get_role(g_settings.manager_role) == None:
            if ctx.guild.owner_id != ctx.author.id:
                await react(ctx.message, ctx.bot.emoji.x_mark)
                raise cmds.CheckFailure(f"You are not the manager of bank: '{g_settings.bank_name}'")
        return g_settings

class PlotType(Enum):
    Curve = plotter.curve
    Bar = plotter.bar
    Stem = plotter.stem
    Stairs = plotter.stairs
    Stack = plotter.stack

class donation_summary_days(ui.View):
    def __init__(self, bot: Bot, context: Context) -> None:
        self.bot = bot
        self.user_id = context.author.id
        self.plot_type = PlotType.Curve
        self.days_back = 10
        self.banks = []
        self.msg = None
        super().__init__()
        self.bot.db.cursor.execute("select distinct category from dank_donations where guild_id = ?", (context.guild.id,))
        for (x,) in self.bot.db.cursor.fetchall():
            self.banks.append(x)
            self.banks_selection.add_option(label=x.replace("_", " ").title(), value=x)
        self.banks_selection.max_values = len(self.banks)
    
    async def on_timeout(self):
        if self.msg:
            b = ui.Button(label="Expired", disabled=True, style=discord.ButtonStyle.gray)
            expired = ui.View(timeout=1); expired.add_item(b)
            await self.msg.edit(view=expired)
        return await super().on_timeout()

    async def send_summary(self, ctx: Interaction) -> None:
        await ctx.response.defer()
        if not self.msg: self.msg = ctx.message
        today = datetime.date.today()
        offset = int(datetime.datetime.combine(today-datetime.timedelta(days=self.days_back), datetime.time(0, 0, 0, tzinfo=datetime.timezone.utc)).timestamp())
        if not self.banks:
            self.bot.db.cursor.execute(
                f"SELECT timestamp, SUM(coin_value) FROM dank_donations WHERE guild_id = ? AND timestamp >= ? GROUP BY DATE(timestamp, 'unixepoch') ORDER BY timestamp",
                (ctx.guild.id, offset)
            )
        else:
            self.bot.db.cursor.execute(
                f"SELECT timestamp, SUM(coin_value) FROM dank_donations WHERE guild_id = ? AND timestamp >= ? AND category IN ({', '.join(['?']*len(self.banks))}) GROUP BY DATE(timestamp, 'unixepoch') ORDER BY timestamp",
                (ctx.guild.id, offset) + tuple(self.banks)
            )
        rows = self.bot.db.cursor.fetchall()
        days = [(today - datetime.timedelta(days=i)) for i in range(self.days_back - 1, -1, -1)]
        coin_map = {day: 0 for day in days}
        for epoch_ts, coins in rows:
            date = datetime.datetime.fromtimestamp(epoch_ts, tz=datetime.timezone.utc).date()
            coin_map[date] = coins or 0
        dates_sorted = sorted(coin_map.keys())
        values_sorted = [coin_map[d] for d in dates_sorted]

        embed = discord.Embed(
            title = f"{self.days_back} Days - Donation Summary",
            timestamp=datetime.datetime.now(),
            color = embed_color
        )
        donations = len([x for x in rows if x[1]])
        embed.add_field(name="Total Amount", value=f"{coin} `{sum(coin_map.values()):,}`")
        embed.add_field(name="Average Amount", value=(
            f"**{self.days_back} days:** {coin} `{round(sum(coin_map.values())/len(coin_map)):,}`\n"
            f"**Donations:** {coin} `{round(sum(coin_map.values())/donations):,}`\n"
        ))
        embed.add_field(name="Donations", value=f"{donations:,}")
        embed.set_footer(text=f"Requested by: {ctx.user}", icon_url=ctx.user.display_avatar.url)
        embed.set_author(name=ctx.guild.name, icon_url=ctx.guild.icon.url if ctx.guild.icon else None)
        embed.set_image(url="attachment://dono_trend.png")

        self.msg = await ctx.edit_original_response(embed=embed, attachments=[self.plot_type.value.datewise_plotter(dates_sorted, values_sorted, filename="dono_trend.png")], view=self)

    @ui.select(
        options = [
            discord.SelectOption(label="Line Chart", value="line_chart", default=True),
            discord.SelectOption(label="Bar Chart", value="bar_chart"),
            discord.SelectOption(label="Stem Chart", value="stem_chart"),
            discord.SelectOption(label="Stair Chart", value="stairs_chart"),
            discord.SelectOption(label="Stack Chart", value="stack_chart")
        ],
        placeholder="Change graph type"
    )
    async def chart_selection(self, ctx: Interaction, slct: ui.Select):
        if ctx.user.id != self.user_id: return await ctx.response.send_message(f"{self.bot.emoji.lock} | This is not for you.", ephemeral=True)
        match slct.values[0]:
            case "line_chart":
                self.plot_type = PlotType.Curve
            case "bar_chart":
                self.plot_type = PlotType.Bar
            case "stem_chart":
                self.plot_type = PlotType.Stem
            case "stairs_chart":
                self.plot_type = PlotType.Stairs
            case "stack_chart":
                self.plot_type = PlotType.Stack
        for o in self.chart_selection.options:
            o.default = o.value == slct.values[0]
        await self.send_summary(ctx)

    @ui.select(placeholder="Choose Banks", min_values=0)
    async def banks_selection(self, ctx: Interaction, slct: ui.Select):
        if ctx.user.id != self.user_id: return await ctx.response.send_message(f"{self.bot.emoji.lock} | This is not for you.", ephemeral=True)
        self.banks = slct.values
        for o in self.banks_selection.options:
            o.default = o.value in self.banks 
        await self.send_summary(ctx)

    @ui.button(label="1 Week", style=discord.ButtonStyle.gray, row=2)
    async def week_1_dono_summary(self, ctx: Interaction, btn: ui.Button):
        if ctx.user.id != self.user_id: return await ctx.response.send_message(f"{self.bot.emoji.lock} | This is not for you.", ephemeral=True)
        self.days_back = 7
        await self.send_summary(ctx)

    @ui.button(label="2 Weeks", style=discord.ButtonStyle.gray, row=2)
    async def week_2_dono_summary(self, ctx: Interaction, btn: ui.Button):
        if ctx.user.id != self.user_id: return await ctx.response.send_message(f"{self.bot.emoji.lock} | This is not for you.", ephemeral=True)
        self.days_back = 14
        await self.send_summary(ctx)

    @ui.button(label="3 Weeks", style=discord.ButtonStyle.gray, row=2)
    async def week_3_dono_summary(self, ctx: Interaction, btn: ui.Button):
        if ctx.user.id != self.user_id: return await ctx.response.send_message(f"{self.bot.emoji.lock} | This is not for you.", ephemeral=True)
        self.days_back = 21
        await self.send_summary(ctx)

    @ui.button(label="4 Weeks", style=discord.ButtonStyle.gray, row=2)
    async def week_4_dono_summary(self, ctx: Interaction, btn: ui.Button):
        if ctx.user.id != self.user_id: return await ctx.response.send_message(f"{self.bot.emoji.lock} | This is not for you.", ephemeral=True)
        self.days_back = 28
        await self.send_summary(ctx)

    @ui.button(label="10 Days", style=discord.ButtonStyle.gray, row=3)
    async def days_10_dono_summary(self, ctx: Interaction, btn: ui.Button):
        if ctx.user.id != self.user_id: return await ctx.response.send_message(f"{self.bot.emoji.lock} | This is not for you.", ephemeral=True)
        self.days_back = 10
        await self.send_summary(ctx)

    @ui.button(label="20 Days", style=discord.ButtonStyle.gray, row=3)
    async def days_20_dono_summary(self, ctx: Interaction, btn: ui.Button):
        if ctx.user.id != self.user_id: return await ctx.response.send_message(f"{self.bot.emoji.lock} | This is not for you.", ephemeral=True)
        self.days_back = 20
        await self.send_summary(ctx)

    @ui.button(label="1 Month", style=discord.ButtonStyle.gray, row=3)
    async def days_30_dono_summary(self, ctx: Interaction, btn: ui.Button):
        if ctx.user.id != self.user_id: return await ctx.response.send_message(f"{self.bot.emoji.lock} | This is not for you.", ephemeral=True)
        self.days_back = 30
        await self.send_summary(ctx)

    @ui.button(label="Close", style=discord.ButtonStyle.gray, row=3)
    async def close(self, ctx: Interaction, btn: ui.Button):
        if ctx.user.id != self.user_id: return await ctx.response.send_message(f"{self.bot.emoji.lock} | This is not for you.", ephemeral=True)
        if ctx.message.reference.cached_message:
            await react(ctx.message.reference.cached_message, self.bot.emoji.tick)
        await ctx.message.delete()

class dank_donation_tracking(cmds.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @cmds.Cog.listener()
    async def on_raw_message_edit(self, event: RawMessageUpdateEvent):
        msg = event.message
        if msg.application_id != dank_id: return
        if not msg.interaction_metadata: return
        if msg.interaction_metadata.type != discord.InteractionType.application_command: return
        
        # if msg.interaction.name != "serverevents donate": return # deprecated
        # if msg.interaction_metadata.user.id not in self.bot.owner_ids: return

        if "components" not in event.data: return
        if len(event.data["components"]) == 0: return
        if "components" not in event.data["components"][0]: return
        if len(event.data["components"][0]["components"]) == 0: return
        if "content" not in event.data["components"][0]["components"][0]: return
        donated = discord.utils.remove_markdown(event.data["components"][0]["components"][0]["content"])
        if not donated.startswith("Successfully donated"): return

        g_settings = self.bot.db.dank.donation_settings.fetchone((event.guild_id, event.channel_id))
        if g_settings is None: return

        donor = msg.interaction_metadata.user
        data = donated[21:].split(" ", 2)
        if len(data) == 2:
            if data[0] == coin:
                amount = int(data[1].replace(",", ""))
                description = (
                    f"**Amount:** {coin} {amount:,}\n"
                    f"**Donor:** {donor.mention}\n"
                    f"**Bank:** `{g_settings.bank_name}`\n"
                    f"**Logged:** *Automatically*"
                )
            donation = f"{coin} {amount:,}"
        elif len(data) == 3:
            def wait_for_check(m: discord.Message):
                if m.channel.id != msg.channel.id: return False
                if m.author.id != dank_id: return False
                if m.interaction_metadata:
                    if m.interaction_metadata.type == discord.InteractionType.application_command:
                        if m.interaction_metadata.user.id != donor.id: return False
                        if not m.embeds: return False
                        if not m.embeds[0].title: return False
                        if m.embeds[0].title != data[2]: return False
                        if not m.embeds[0].fields: return False
                        if m.embeds[0].fields[1].name != "Market": return False
                        return True
                if m.reference != None:
                    if m.reference.cached_message.author.id != donor.id: return False
                    if not m.embeds: return False
                    if not m.embeds[0].title: return False
                    if m.embeds[0].title != data[2]: return False
                    if not m.embeds[0].fields: return False
                    if m.embeds[0].fields[1].name != "Market": return False
                    return True
                return False

            await msg.reply(f"{donor.mention}, now please run this command to log your donation `/item {data[2]}` OR `pls item {data[2]}` under 30 seconds.", delete_after=30)
            try: item_info: discord.Message = await self.bot.wait_for("message", check=wait_for_check, timeout=30)
            except TimeoutError:
                await msg.add_reaction(discord.PartialEmoji.from_str(self.bot.emoji.x_mark))
                await msg.reply(content=f"{self.bot.emoji.x_mark} | {donor.mention} too slow, timedout. Ask a mod to log your donation.", delete_after=10)
                return 
            coin_val = int(item_info.embeds[0].fields[1].value.splitlines()[0][17:].replace(",", ""))
            if item_info.reference: await item_info.reference.cached_message.delete()
            await item_info.delete()
            quantity = int(data[0].replace(",", ""))
            amount = coin_val * quantity
            description = (
                f"**Item:** {data[2]}\n"
                f"**Quantity:** {quantity:,}\n"
                f"**Value:** {coin} {amount:,}\n"
                f"**Donor:** {donor.mention}\n"
                f"**Bank:** `{g_settings.bank_name}`\n"
                f"**Logged:** *Automatically*"
            )
            donation = f"{quantity:,} {data[2]} ({coin} {amount:,})"
        embed = discord.Embed(
            title = "Donated to Server",
            color = embed_color,
            timestamp = datetime.datetime.now(),
            description = description
        )
        embed.set_thumbnail(url=donor.display_avatar.url)
        embed.set_author(name=donor.name, icon_url=donor.display_avatar.url)
        embed.set_footer(text=msg.guild.name, icon_url=msg.guild.icon.url if msg.guild.icon else None)
        button = ui.Button(url=msg.jump_url, label="Jump to message")
        view = ui.View(timeout=1); view.add_item(button)
        self.bot.db.cursor.execute(
            "INSERT INTO dank_donations "
            "(guild_id, donor_id, coin_value, logged_by, timestamp, category) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (msg.guild.id, donor.id, amount, self.bot.user.id, int(time.time()), g_settings.bank_name)
        )
        embed.description += f"\n**Donation ID:** `{self.bot.db.cursor.lastrowid}`"
        self.bot.db.commit()
        await msg.guild.get_channel(g_settings.log_channel).send(embed=embed, view=view)
        try: await msg.add_reaction(discord.PartialEmoji.from_str(self.bot.emoji.tick))
        except: pass
        await msg.reply(f"{self.bot.emoji.tick} | {donor.mention} your donation **{donation}** has been logged. Thank you for the donations.", delete_after=10)

    def is_donation_manager():
        async def predicate(ctx: Context):
            if not ctx.guild: raise cmds.NoPrivateMessage()
            if ctx.guild.owner_id == ctx.author.id: return True
            g_settings = ctx.bot.db.dank.donation_settings.fetchone((ctx.guild.id, ctx.channel.id))
            if not g_settings:
                ctx.bot.db.cursor.execute("SELECT manager_role FROM dank_donation_settings WHERE gid = ?", (ctx.guild.id,))
                data = ctx.bot.db.cursor.fetchall()
                if any(ctx.author.get_role(role_id) is not None for (role_id,) in data): return True
                await react(ctx.message, ctx.bot.emoji.x_mark)
                raise cmds.CheckFailure("1. Donations are not setup in this channel.\n2. You are not in any donation managers")
            if ctx.author.get_role(g_settings.manager_role) != None: return True
            try:
                if await cmds.has_permissions(administrator=True).predicate(ctx): return True
            except cmds.MissingPermissions:
                await react(ctx.message, ctx.bot.emoji.x_mark)
                raise cmds.CheckFailure("You are not a donation manager.")
        return cmds.check(predicate)

    @util.group(name="donation", description="Dank donations logger", invoke_without_command=True, aliases=["dono", "donations"])
    async def donation(self, ctx: cmds.Context):
        await ctx.reply("Use `.donation help` to list all commands\nUse `.setup donation` to setup donations for this server")

    @donation.command(name="add", description="Manually log a user's donation", aliases=["log"])
    @util.describe(
        donor = "The user who donated",
        bank = "The bank to log the donation in (default: current channel's bank)",
        amount = "The amount of coins/items donated",
        item = "(Optional) The item donated"
    )
    @is_donation_manager()
    async def donation_add(self, ctx: cmds.Context, donor: discord.Member, bank: DonoSetting,  amount: Amount, *, item: str = None):
        bank: structs.dank_donation_settings = bank
        if item:
            item = item.title()
            def wait_for_check(m: discord.Message):
                if m.channel.id != ctx.channel.id: return False
                if m.author.id != dank_id: return False
                if m.interaction_metadata:
                    if m.interaction_metadata.type == discord.InteractionType.application_command:
                        if m.interaction_metadata.user.id != ctx.author.id: return False
                        if not m.embeds: return False
                        if not m.embeds[0].fields: return False
                        if m.embeds[0].fields[1].name != "Market": return False
                        return True
                if m.reference != None:
                    if m.reference.cached_message.author.id != ctx.author.id: return False
                    if not m.embeds: return False
                    if not m.embeds[0].fields: return False
                    if m.embeds[0].fields[1].name != "Market": return False
                    return True
                return False

            m = await ctx.reply(f"{ctx.author.mention}, now please run this command to log your donation `/item {item}` OR `pls item {item}` under 30 seconds.", delete_after=30)
            try: item_info: discord.Message = await self.bot.wait_for("message", check=wait_for_check, timeout=30)
            except TimeoutError:
                await ctx.message.add_reaction(discord.PartialEmoji.from_str(self.bot.emoji.x_mark))
                await m.reply(content=f"{self.bot.emoji.x_mark} | {donor.mention} too slow, timedout. Ask a mod to log your donation.", delete_after=10)
                return 
            coin_val = int(item_info.embeds[0].fields[1].value.splitlines()[0][17:].replace(",", ""))
            if item_info.reference: await item_info.reference.cached_message.delete()
            await item_info.delete(); await m.delete()
            donation = f"{amount:,} {item} ({coin} {(amount*coin_val):,})"
        else:
            coin_val = 1
            donation = f"{coin} {amount:,}"
        self.bot.db.cursor.execute(
            "INSERT INTO dank_donations "
            "(guild_id, donor_id, coin_value, logged_by, timestamp, category) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (ctx.guild.id, donor.id, amount, ctx.author.id, int(time.time()), bank.bank_name)
        )
        embed = discord.Embed(
            title = "Donated to server",
            color = embed_color,
            timestamp = datetime.datetime.now(),
            description = (
                (f"**Item:** {item}\n" if item else "") +
                (f"**Quantity:** {amount:,}\n" if item else "") +
                f"**Value:** {coin} {(amount*coin_val):,}\n"
                f"**Bank:** `{bank.bank_name}`\n"
                f"**Donor:** {donor.mention}\n"
                f"**Logged by:** {ctx.author.mention}\n"
                f"**Donation ID:** `{self.bot.db.cursor.lastrowid}`"
            )
        )
        embed.set_thumbnail(url=donor.display_avatar.url)
        embed.set_author(name=donor.name, icon_url=donor.display_avatar.url)
        embed.set_footer(text=ctx.guild.name, icon_url=ctx.guild.icon.url if ctx.guild.icon else None)
        button = ui.Button(url=ctx.message.jump_url, label="Jump to message")
        view = ui.View(timeout=1); view.add_item(button)
        await ctx.guild.get_channel(bank.log_channel).send(embed=embed, view=view)
        self.bot.db.commit()
        try: await ctx.message.add_reaction(discord.PartialEmoji.from_str(self.bot.emoji.tick))
        except: pass
        await ctx.reply(f"{self.bot.emoji.tick} | {donor.mention}'s donation **{donation}** has been logged. (by: {ctx.author.mention})", delete_after=10)
        
    @donation.command(name="remove", description="Remove a user's donation", aliases=["rem", "delete", "del"])
    @util.describe(id = "The ID of the donation to remove")
    @is_donation_manager()
    async def donation_remove(self, ctx: cmds.Context, id: int):
        self.bot.db.cursor.execute("SELECT * FROM dank_donations WHERE id = ? AND guild_id = ?", (id, ctx.guild.id))
        donation = self.bot.db.dank.donations.parse(self.bot.db.cursor.fetchone())
        if not donation:
            await react(ctx.message, ctx.bot.emoji.x_mark)
            return await ctx.reply(f"{self.bot.emoji.x_mark} | Donation with **ID:** `{id}` not found.", delete_after=10)
        self.bot.db.cursor.execute("SELECT * FROM dank_donation_settings WHERE gid = ? AND bank_name = ?", (ctx.guild.id, donation.category))
        g_settings = self.bot.db.dank.donation_settings.parse(self.bot.db.cursor.fetchone())
        if not g_settings:
            await react(ctx.message, ctx.bot.emoji.x_mark)
            return await ctx.reply(f"{self.bot.emoji.x_mark} | The donation was logged in bank: `{donation.category}` that was either deleted/renamed or doesn't exists.", delete_after=10) 
        if not ctx.author.get_role(g_settings.manager_role):
            if ctx.guild.owner_id != ctx.author.id:
                await react(ctx.message, ctx.bot.emoji.x_mark)
                return await ctx.reply(f"{self.bot.emoji.x_mark} | You are not the manager of bank: `{donation.category}`", delete_after=10)
        embed = discord.Embed(
            title = "Donation removed",
            color = embed_color,
            timestamp = datetime.datetime.now(),
            description = (
                f"**Donation ID:** `{donation.id}`\n"
                f"**Donor:** <@{donation.donor_id}>\n"
                f"**Value:** {coin} {donation.coin_value}\n"
                f"**Bank:** `{donation.category}`\n"
                f"**Logged By:** <@{donation.logged_by}>\n"
                f"**Donated At:** <t:{donation.timestamp}:f>\n"
                f"**Deleted by:** {ctx.author.mention}"
            )
        )
        embed.set_author(name=f"{ctx.author}", icon_url=ctx.author.display_avatar.url)
        embed.set_footer(text=ctx.guild.name, icon_url=ctx.guild.icon.url if ctx.guild.icon else None)
        button = ui.Button(url=ctx.message.jump_url, label="Jump to message")
        view = ui.View(timeout=1); view.add_item(button)
        await ctx.guild.get_channel(g_settings.log_channel).send(embed=embed, view=view)
        self.bot.db.dank.donations.delete(id)
        await ctx.message.add_reaction(discord.PartialEmoji.from_str(self.bot.emoji.tick))
        await ctx.reply(f"{self.bot.emoji.tick} | Donation **ID:** {id} deleted.", delete_after=10)

    @donation.command(name="view", description="View a user's donation history")
    @util.describe(
        user = "The user to view donation history for (default: you)",
        bank = "The bank to view donation history for (default: all)"
    )
    async def donation_view(self, ctx: Context, user: discord.Member=cmds.Author, bank: DonoSetting = None):
        await react(ctx.message, self.bot.emoji.warning)
        await ctx.reply(f"{self.bot.emoji.warning} | This command will be updated to show more info very soon.", mention_author=False, delete_after=10)
        if user.id != ctx.author.id: 
            await react(ctx.message, self.bot.emoji.x_mark)
            return await ctx.reply("Currently not supported, will be added soon.", delete_after=10)
        self.bot.db.cursor.execute(
            "select count(*) as donations, sum(coin_value) as total_value from dank_donations where guild_id = ? AND donor_id = ?",
            (ctx.guild.id, user.id)
        )
        data = self.bot.db.cursor.fetchone()
        if not data: 
            await react(ctx.message, self.bot.emoji.x_mark)
            return await ctx.reply(f"{self.bot.emoji.x_mark} | There are no donations by {user.mention}")
        donation_count = data[0]
        donation_amount = data[1]
        embed = discord.Embed(
            title = "Donation Summary",
            color = 0x010101,
            description = (
                f"**Donations:** {donation_count:,}\n"
                f"**Total Amount:** {coin} {donation_amount:,}"
            )
        )
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
        embed.set_footer(text=ctx.guild.name + " | Will show more info soon.", icon_url=ctx.guild.icon.url if ctx.guild.icon else None)
        await react(ctx.message, self.bot.emoji.tick)
        await ctx.reply(embed=embed)

    @donation.command(name="summary", description="Get donation summary")
    @is_donation_manager()
    async def donation_summary(self, ctx: Context):
        days_back = 10
        today = datetime.date.today()
        offset = int(datetime.datetime.combine(today-datetime.timedelta(days=days_back), datetime.time(0, 0, 0, tzinfo=datetime.timezone.utc)).timestamp())
        self.bot.db.cursor.execute(
            f"""
            SELECT
                timestamp,
                SUM(coin_value)
            FROM dank_donations
            WHERE
                guild_id = ?
                AND timestamp >= ?
            GROUP BY DATE(timestamp, 'unixepoch')
            ORDER BY timestamp
            """,
            (ctx.guild.id, offset)
        )
        rows = self.bot.db.cursor.fetchall()

        # Prepare list of last `days_back` days in "dd MMM yy"
        days = [(today - datetime.timedelta(days=i)) for i in range(days_back - 1, -1, -1)]
        coin_map = {day: 0 for day in days}

        for epoch_ts, coins in rows:
            date = datetime.datetime.fromtimestamp(epoch_ts, tz=datetime.timezone.utc).date()
            coin_map[date] = coins or 0

        # Sorted x and y values
        dates_sorted = sorted(coin_map.keys())
        values_sorted = [coin_map[d] for d in dates_sorted]

        embed = discord.Embed(
            title = f"{days_back} Days - Donation Summary",
            timestamp=datetime.datetime.now(),
            color = embed_color
        )
        embed.add_field(name="Total Amount", value=f"{coin} `{sum(coin_map.values()):,}`")
        embed.add_field(name="Average Amount", value=f"{coin} `{round(sum(coin_map.values())/len([x for x in rows if x[1]])):,}`")
        embed.add_field(name="Donations", value=f"{len([x for x in rows if x[1]]):,}")
        embed.set_footer(text=f"Requested by: {ctx.author}", icon_url=ctx.author.display_avatar.url)
        embed.set_author(name=ctx.guild.name, icon_url=ctx.guild.icon.url if ctx.guild.icon else None)
        embed.set_image(url="attachment://dono_trend.png")

        await ctx.reply(embed=embed, file=plotter.curve.datewise_plotter(dates_sorted, values_sorted, filename="dono_trend.png"), view=donation_summary_days(self.bot, ctx))

async def setup(bot: Bot):
    await bot.add_cog(dank_donation_tracking(bot))
