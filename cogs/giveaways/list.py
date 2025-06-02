import discord
from discord.ext import commands
from discord import app_commands, Interaction
import sqlite3
from datetime import datetime

class GiveawayList(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = sqlite3.connect("giveaway.db")
        self.db.row_factory = sqlite3.Row

    @app_commands.command(name="list", description="List all active giveaways")
    async def list(self, interaction: Interaction):
        await interaction.response.defer()
        cur = self.db.cursor()
        rows = cur.execute("SELECT * FROM giveaways WHERE guild_id = ? AND ended = 0", (interaction.guild.id,)).fetchall()

        if not rows:
            return await interaction.followup.send("No active giveaways found.", ephemeral=True)

        embed = discord.Embed(title="🎉 Active Giveaways", color=0x000000)
        for row in rows:
            end_ts = row["end_time"]
            end = f"<t:{end_ts}:R>"
            embed.add_field(
                name=f"🎁 {row['prize']}",
                value=(
                    f"**ID:** `{row['message_id']}`\n"
                    f"**Ends:** {end}\n"
                    f"**Channel:** <#{row['channel_id']}>"
                ),
            inline=False
    )
            await interaction.followup.send(embed=embed)

async def setup(bot, giveaway_cog):
    await bot.add_cog(GiveawayList(bot))
    pass
    