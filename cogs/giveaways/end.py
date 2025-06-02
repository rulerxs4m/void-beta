import discord
import discord
import sqlite3
import random
from discord.ext import commands
from discord import app_commands, Interaction
from datetime import datetime
from discord import app_commands, Interaction
from datetime import datetime


class GiveawayEnd(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = sqlite3.connect("giveaway.db")
        self.db.row_factory = sqlite3.Row

    @app_commands.command(name="end", description="End an ongoing giveaway")
    @app_commands.describe(message_id="The message ID of the giveaway to end")
    async def end(self, interaction: Interaction, message_id: str):
        await interaction.response.defer(thinking=True)
        message_id = int(message_id)
        cur = self.db.cursor()

        row = cur.execute("SELECT * FROM giveaways WHERE message_id = ? AND guild_id = ?", (message_id, interaction.guild.id)).fetchone()
        if not row:
            return await interaction.followup.send("Giveaway not found.", ephemeral=True)
        if row["ended"]:
            return await interaction.followup.send("That giveaway has already ended.", ephemeral=True)

        entries = cur.execute("SELECT * FROM entries WHERE giveaway_id = ?", (row["id"],)).fetchall()
        if not entries:
            return await interaction.followup.send("No participants found to select winners.", ephemeral=True)

        pool = [entry["user_id"] for entry in entries for _ in range(entry["entries"])]
        winners = random.sample(pool, min(row["winners_count"], len(pool)))
        winner_mentions = [f"<@{uid}>" for uid in winners]

        channel = interaction.guild.get_channel(row["channel_id"])
        try:
            msg = await channel.fetch_message(row["message_id"])
        except:
            msg = None

        if msg:
            embed = msg.embeds[0]
            embed.description += f"🎉 **Winner(s):** {', '.join(winner_mentions)}"
            await msg.edit(embed=embed, view=None)
            await channel.send(f"🎉 Congratulations {', '.join(winner_mentions)}! You won **{row['prize']}**")
        else:
            await channel.send(f"🎉 Giveaway ended! Winner(s): {', '.join(winner_mentions)}")

        cur.execute("UPDATE giveaways SET ended = 1 WHERE id = ?", (row["id"],))
        self.db.commit()
        await interaction.followup.send("Giveaway ended successfully.", ephemeral=True)


async def setup(bot, giveaway_cog):
    await bot.add_cog(GiveawayEnd(bot))
    pass
