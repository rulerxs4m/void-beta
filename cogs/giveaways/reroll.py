import discord
from discord.ext import commands
from discord import app_commands, Interaction
import sqlite3
import random

class GiveawayReroll(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = sqlite3.connect("giveaway.db")
        self.db.row_factory = sqlite3.Row

    @app_commands.command(name="reroll", description="Reroll winners for an ended giveaway")
    @app_commands.describe(message_id="The message ID of the ended giveaway")
    async def reroll(self, interaction: Interaction, message_id: str):
        await interaction.response.defer(thinking=True)
        message_id = int(message_id)
        cur = self.db.cursor()

        row = cur.execute("SELECT * FROM giveaways WHERE message_id = ? AND guild_id = ?", (message_id, interaction.guild.id)).fetchone()
        if not row:
            return await interaction.followup.send("Giveaway not found.", ephemeral=True)
        if not row["ended"]:
            return await interaction.followup.send("The giveaway hasn't ended yet.", ephemeral=True)

        entries = cur.execute("SELECT * FROM entries WHERE giveaway_id = ?", (row["id"],)).fetchall()
        if not entries:
            return await interaction.followup.send("No participants found to reroll from.", ephemeral=True)

        pool = [entry["user_id"] for entry in entries for _ in range(entry["entries"])]
        winners = random.sample(pool, min(row["winners_count"], len(pool)))
        winner_mentions = [f"<@{uid}>" for uid in winners]

        channel = interaction.guild.get_channel(row["channel_id"])
        await channel.send(f"🔁 Rerolled Winner(s) for **{row['prize']}**: {', '.join(winner_mentions)}")

        await interaction.followup.send("Reroll complete.", ephemeral=True)

async def setup(bot, giveaway_cog):
    await bot.add_cog(GiveawayReroll(bot))
    pass