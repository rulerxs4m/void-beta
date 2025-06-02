
import discord
from discord.ext import commands
from discord import app_commands, Interaction
import sqlite3
from datetime import datetime, timedelta
import re

GIVEAWAY_EMOJI = "🎉"
JOIN_EMOJI = "✅"
LEAVE_EMOJI = "❌"
PARTICIPANTS_EMOJI = "👀"
EMBED_COLOR = 0x000000

class GiveawayStart(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.catched_giveaways = []
        self.db = sqlite3.connect("giveaway.db")
        self.create_tables()

    def create_tables(self):
        with self.db:
            self.db.execute("""
                CREATE TABLE IF NOT EXISTS giveaways (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER,
                    channel_id INTEGER,
                    message_id INTEGER,
                    prize TEXT,
                    start_time INTEGER,
                    end_time INTEGER,
                    winners_count INTEGER,
                    started_by INTEGER,
                    donor_id INTEGER,
                    donor_message TEXT,
                    required_roles TEXT,
                    bypass_roles TEXT,
                    extra_roles TEXT,
                    messages_required INTEGER,
                    message_channels TEXT,
                    blacklist_roles TEXT,
                    ping_everyone INTEGER,
                    ended INTEGER DEFAULT 0
                )
            """)
            self.db.execute("""
                CREATE TABLE IF NOT EXISTS entries (
                    giveaway_id INTEGER,
                    user_id INTEGER,
                    entries INTEGER,
                    PRIMARY KEY (giveaway_id, user_id)
                )
            """)

    def parse_duration(self, time_str: str) -> int:
        matches = re.findall(r'(\d+)([smhd])', time_str.lower())
        total_seconds = 0
        for val, unit in matches:
            if unit == 's':
                total_seconds += int(val)
            elif unit == 'm':
                total_seconds += int(val) * 60
            elif unit == 'h':
                total_seconds += int(val) * 3600
            elif unit == 'd':
                total_seconds += int(val) * 86400
        return total_seconds

    @app_commands.command(name="start", description="Start a giveaway")
    @app_commands.describe(
        prize="What is the prize?",
        duration="How long the giveaway lasts (e.g. 1h30m)",
        winners="Number of winners"
    )
    async def start(
        self,
        interaction: Interaction,
        prize: str,
        duration: str,
        winners: int
    ):
        await interaction.response.defer(thinking=True)
        guild = interaction.guild
        author = interaction.user
        channel = interaction.channel

        seconds = self.parse_duration(duration)
        if seconds < 10:
            return await interaction.followup.send("Duration must be at least 10 seconds.", ephemeral=True)
        if winners < 1:
            return await interaction.followup.send("You must have at least 1 winner.", ephemeral=True)

        start_time = datetime.utcnow()
        end_time = start_time + timedelta(seconds=seconds)

        embed = discord.Embed(
            title=f"{GIVEAWAY_EMOJI} {prize}",
            description=f"**Hosted by:** {author.mention}\n**Ends:** <t:{int(end_time.timestamp())}:R>",
            color=EMBED_COLOR,
        )
        embed.set_footer(text=f"{winners} winner(s) • Ends at")
        embed.timestamp = end_time

        view = GiveawayView(self.db)

        message = await channel.send(embed=embed, view=view)

        with self.db:
            self.db.execute("""
                INSERT INTO giveaways (
                    guild_id, channel_id, message_id, prize, start_time, end_time,
                    winners_count, started_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                guild.id, channel.id, message.id, prize,
                int(start_time.timestamp()), int(end_time.timestamp()),
                winners, author.id
            ))

        config = self.db.execute("SELECT log_channel, log_enabled FROM config WHERE guild_id = ?", (guild.id,)).fetchone()
        if config and config[1]:
            log_channel = guild.get_channel(config[0])
            if log_channel:
                log_embed = discord.Embed(
                    title="📢 New Giveaway Started!",
                    color=EMBED_COLOR,
                    description=f"**🎯 Prize:** {prize}\n"
                                f"**🕒 Started:** <t:{int(start_time.timestamp())}:R> (<t:{int(start_time.timestamp())}:f>)\n"
                                f"**⌛ Ends:** <t:{int(end_time.timestamp())}:R> (<t:{int(end_time.timestamp())}:f>)\n"
                                f"**👑 Host:** {author.mention}\n"
                                f"**🎉 Winner Count:** {winners}"
                )
                log_embed.set_thumbnail(url=author.display_avatar.url)
                log_embed.add_field(name="🔗 Jump to Giveaway", value=f"[Click here]({message.jump_url})", inline=False)
                await log_channel.send(embed=log_embed)

        await interaction.followup.send(f"Giveaway started in {channel.mention}!", ephemeral=True)


class GiveawayView(discord.ui.View):
    def __init__(self, db):
        super().__init__(timeout=None)
        self.db = db
        self.add_item(JoinButton(db))
        self.add_item(LeaveButton(db))
        self.add_item(ParticipantsButton(db))


class JoinButton(discord.ui.Button):
    def __init__(self, db):
        super().__init__(label="Join", emoji=JOIN_EMOJI, style=discord.ButtonStyle.green)
        self.db = db

    async def callback(self, interaction: Interaction):
        message_id = interaction.message.id
        giveaway = self.db.execute("SELECT id FROM giveaways WHERE message_id = ?", (message_id,)).fetchone()
        if not giveaway:
            return await interaction.response.send_message("Giveaway not found in database.", ephemeral=True)

        giveaway_id = giveaway[0]
        with self.db:
            self.db.execute("INSERT OR IGNORE INTO entries (giveaway_id, user_id, entries) VALUES (?, ?, ?)",
                            (giveaway_id, interaction.user.id, 1))
        await interaction.response.send_message("You joined the giveaway!", ephemeral=True)


class LeaveButton(discord.ui.Button):
    def __init__(self, db):
        super().__init__(label="Leave", emoji=LEAVE_EMOJI, style=discord.ButtonStyle.red)
        self.db = db

    async def callback(self, interaction: Interaction):
        message_id = interaction.message.id
        giveaway = self.db.execute("SELECT id FROM giveaways WHERE message_id = ?", (message_id,)).fetchone()
        if not giveaway:
            return await interaction.response.send_message("Giveaway not found in database.", ephemeral=True)

        giveaway_id = giveaway[0]
        with self.db:
            self.db.execute("DELETE FROM entries WHERE giveaway_id = ? AND user_id = ?", (giveaway_id, interaction.user.id))
        await interaction.response.send_message("You left the giveaway.", ephemeral=True)


class ParticipantsButton(discord.ui.Button):
    def __init__(self, db):
        super().__init__(label="Participants", emoji=PARTICIPANTS_EMOJI, style=discord.ButtonStyle.gray)
        self.db = db

    async def callback(self, interaction: Interaction):
        message_id = interaction.message.id
        giveaway = self.db.execute("SELECT id FROM giveaways WHERE message_id = ?", (message_id,)).fetchone()
        if not giveaway:
            return await interaction.response.send_message("Giveaway not found in database.", ephemeral=True)

        giveaway_id = giveaway[0]
        entries = self.db.execute("SELECT user_id, entries FROM entries WHERE giveaway_id = ?", (giveaway_id,)).fetchall()

        if not entries:
            return await interaction.response.send_message("No participants yet.", ephemeral=True)

        desc = "\n".join([f"<@{user_id}> — `{entry}` entries" for user_id, entry in entries])
        embed = discord.Embed(title="👀 Participants", description=desc, color=EMBED_COLOR)
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(GiveawayStart(bot))
    pass
