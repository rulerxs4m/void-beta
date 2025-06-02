import discord
from discord.ext import commands
from discord import app_commands, Interaction
import sqlite3

class GiveawayCancel(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = sqlite3.connect("giveaway.db")
        self.db.row_factory = sqlite3.Row

    @app_commands.command(name="cancel", description="Cancel a giveaway")
    @app_commands.describe(message_id="The message ID of the giveaway to cancel")
    async def cancel(self, interaction: Interaction, message_id: str):
        await interaction.response.defer(thinking=True)
        message_id = int(message_id)
        cur = self.db.cursor()

        row = cur.execute("SELECT * FROM giveaways WHERE message_id = ? AND guild_id = ?", (message_id, interaction.guild.id)).fetchone()
        if not row:
            return await interaction.followup.send("Giveaway not found.", ephemeral=True)
        if row["ended"]:
            return await interaction.followup.send("That giveaway has already ended or been cancelled.", ephemeral=True)

        channel = interaction.guild.get_channel(row["channel_id"])
        try:
            msg = await channel.fetch_message(row["message_id"])
            await msg.delete()
        except:
            pass

        cur.execute("UPDATE giveaways SET ended = 1 WHERE id = ?", (row["id"],))
        self.db.commit()
        await interaction.followup.send("Giveaway cancelled successfully.", ephemeral=True)

async def setup(bot, giveaway_cog):
    await bot.add_cog(GiveawayCancel(bot))
    pass