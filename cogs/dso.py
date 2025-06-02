import discord
from discord.ext import commands
from discord import ui
from typing import List
from utils import Bot

DSO_LOG_CHANNEL_ID = 1364883977500098611
DSO_GUILD_ID = 925666996505415680
REPORT_CHANNEL_ID = 1372145202365595740

OFFENSES = {
    "Minor Violation": -5,
    "Looting": -10,
    "Scamming": -15,
    "Raiding / Nuking": -20,
    "Multiple major reports": -999,
    "DSO Global Ban": 0
}

class OffenseSelect(ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label=label, description=f"{points} points")
            for label, points in OFFENSES.items()
        ]
        super().__init__(
            placeholder="Choose offenses...",
            min_values=1,
            max_values=len(options),
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        self.view.selected_offenses = self.values
        await interaction.response.defer()
        self.view.stop()

class MultiOffenseView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.selected_offenses = []
        self.add_item(OffenseSelect())

class OffenseModal(ui.Modal, title="Custom Offense"):
    name = ui.TextInput(label="Offense Name")
    points = ui.TextInput(label="Point Deduction", placeholder="Use negative values")

    async def on_submit(self, interaction: discord.Interaction):
        self.value = (self.name.value, int(self.points.value))
        await interaction.response.send_message("Custom offense recorded.", ephemeral=True)

class VoteView(ui.View):
    def __init__(self, bot: Bot, report_id: str, thread: discord.Thread):
        super().__init__(timeout=None)
        self.bot = bot
        self.report_id = report_id
        self.thread = thread
        self.votes = {}
        self.update_buttons()

    def update_buttons(self):
        approve_count = sum(1 for v in self.votes.values() if v == 'approve')
        reject_count = sum(1 for v in self.votes.values() if v == 'reject')
        self.clear_items()
        self.add_item(ui.Button(label=f"Approve ({approve_count})", style=discord.ButtonStyle.success, custom_id="vote_approve"))
        self.add_item(ui.Button(label=f"Reject ({reject_count})", style=discord.ButtonStyle.danger, custom_id="vote_reject"))
        self.add_item(ui.Button(label="End", style=discord.ButtonStyle.secondary, custom_id="vote_end"))

    @discord.ui.button(label="Approve", style=discord.ButtonStyle.success, custom_id="vote_approve")
    async def approve(self, interaction: discord.Interaction, button: ui.Button):
        self.votes[interaction.user.id] = 'approve'
        self.update_buttons()
        await interaction.response.edit_message(view=self)

    @discord.ui.button(label="Reject", style=discord.ButtonStyle.danger, custom_id="vote_reject")
    async def reject(self, interaction: discord.Interaction, button: ui.Button):
        self.votes[interaction.user.id] = 'reject'
        self.update_buttons()
        await interaction.response.edit_message(view=self)

    @discord.ui.button(label="End", style=discord.ButtonStyle.secondary, custom_id="vote_end")
    async def end(self, interaction: discord.Interaction, button: ui.Button):
        approve_count = sum(1 for v in self.votes.values() if v == 'approve')
        reject_count = sum(1 for v in self.votes.values() if v == 'reject')

        result = "Approved" if approve_count > reject_count else "Rejected"
        color = discord.Color.green() if result == "Approved" else discord.Color.red()

        embed = discord.Embed(title=f"Report {self.report_id} {result}", color=color)
        embed.add_field(name="Approve Votes", value=str(approve_count), inline=True)
        embed.add_field(name="Reject Votes", value=str(reject_count), inline=True)
        embed.set_footer(text="Please take appropriate action.")

        await self.thread.send(embed=embed)
        log_channel = self.bot.get_channel(DSO_LOG_CHANNEL_ID)
        if log_channel:
            await log_channel.send(embed=embed)

        report_id_int = int(self.report_id.lstrip("#"))
        self.bot.db.dso.report.update_final_vote(report_id_int, result)

        self.stop()

class DSO(commands.Cog):
    def __init__(self, bot):
        self.bot: Bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or message.channel.id != REPORT_CHANNEL_ID:
            return

        self.bot.db.cursor.execute(
            "INSERT INTO dso_report (reporter, channel_id, thread_id, dso_staff) VALUES (?, ?, ?, ?)",
            (message.author.id, message.channel.id, 0, 0)
        )
        next_id = self.bot.db.cursor.lastrowid
        report_id = f"#{next_id:04}"

        thread = await message.create_thread(name=f"Report {report_id}")

        self.bot.db.cursor.execute(
            "UPDATE dso_report SET thread_id = ? WHERE report_id = ?",
            (thread.id, next_id)
        )
        self.bot.db.commit()

        await message.channel.send(f"✅ Report {report_id} created by {message.author.mention}. Thread: {thread.mention}")

    @commands.command(name="conclude")
    async def conclude_report(self, ctx, report_id: str):
        if not report_id.startswith("#"):
            await ctx.send("Report ID must start with `#`.")
            return

        report_id_int = int(report_id.lstrip("#"))
        rec = self.bot.db.dso.report.fetchone(report_id_int)
        if not rec:
            self.bot.db.dso.report.insert(report_id_int, ctx.author.id, ctx.channel.id, 0, 0, False)
            rec = self.bot.db.dso.report.fetchone(report_id_int)

        await ctx.send("Please send the summary and proofs in one message.")
        summary_msg = await self.bot.wait_for("message", check=lambda m: m.author == ctx.author and m.channel == ctx.channel)
        summary = summary_msg.content

        await ctx.send("Send any additional reporters (mention or ID, space separated), or `none`.")
        add_reporters_msg = await self.bot.wait_for("message", check=lambda m: m.author == ctx.author and m.channel == ctx.channel)
        additional_reporters = [] if add_reporters_msg.content.lower() == "none" else [int(u.strip("<@!>")) for u in add_reporters_msg.content.split()]

        await ctx.send("Send user IDs of violators (space separated), or `none`.")
        users_msg = await self.bot.wait_for("message", check=lambda m: m.author == ctx.author and m.channel == ctx.channel)
        violators = [] if users_msg.content.lower() == "none" else [int(u.replace("<@","" ).replace(">","" ).replace("!","")) for u in users_msg.content.split()]

        await ctx.send("Send server ID, or `none`.")
        server_msg = await self.bot.wait_for("message", check=lambda m: m.author == ctx.author and m.channel == ctx.channel)
        server_id = None if server_msg.content.lower() == "none" else int(server_msg.content)

        thread = ctx.channel if isinstance(ctx.channel, discord.Thread) else ctx.channel.get_thread(rec.thread_id)
        participants = [m.author.id async for m in thread.history(limit=None) if not m.author.bot]
        unique_participants = list(set(participants))

        embed = discord.Embed(title=f"Report {report_id}", description=summary, color=discord.Color.orange())
        embed.add_field(name="Reporter", value=f"<@{rec.reporter}>", inline=False)
        if additional_reporters:
            embed.add_field(name="Additional Reporters", value=", ".join(f"<@{u}>" for u in additional_reporters), inline=False)
        if violators:
            embed.add_field(name="Reported Users", value=", ".join(f"<@{u}>" for u in violators), inline=False)
        if server_id:
            embed.add_field(name="Reported Server", value=f"`{server_id}`", inline=False)

        view = MultiOffenseView()
        await ctx.send("Select the offense(s) for this report:", embed=embed, view=view)
        await view.wait()

        selected_offenses = view.selected_offenses

        if not selected_offenses:
            modal = OffenseModal()
            await ctx.send("No predefined offense selected. Launching custom modal...")
            await ctx.send_modal(modal)
            await modal.wait()
            offense_name, points = modal.value
            offenses_str = f"{offense_name} ({points} points)"
        else:
            offenses_str = ", ".join(f"{offense} ({OFFENSES[offense]} pts)" for offense in selected_offenses)

        embed.add_field(name="Offenses", value=offenses_str, inline=False)
        embed.add_field(name="Participants", value=", ".join(f"<@{u}>" for u in unique_participants), inline=False)

        await ctx.send("Review the embed. Type `yes` to post and finalize, or `no` to cancel.")
        confirm_msg = await self.bot.wait_for("message", check=lambda m: m.author == ctx.author and m.channel == ctx.channel)
        if confirm_msg.content.lower() != "yes":
            await ctx.send("Cancelled.")
            return

        log_channel = self.bot.get_channel(DSO_LOG_CHANNEL_ID)
        await log_channel.send(embed=embed)
        await thread.send(embed=embed)
        await thread.edit(locked=True)

        for user_id in violators:
            self.bot.db.dso.reported.insert(report_id_int, user_id)

        for user_id in unique_participants:
            self.bot.db.dso.participants.insert(report_id_int, user_id)

        self.bot.db.dso.report.update(
            report_id_int,
            rec.reporter,
            rec.channel_id,
            rec.thread_id,
            ctx.author.id,
            True
        )

        await thread.send("Voting begins now:", view=VoteView(self.bot, report_id, thread))
        await ctx.send("Report finalized, logged, and sent for voting.")

async def setup(bot):
    await bot.add_cog(DSO(bot))
