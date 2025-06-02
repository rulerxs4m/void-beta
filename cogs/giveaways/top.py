import discord
from discord.ext import commands
from discord import app_commands, Interaction
import sqlite3

class GiveawayTop(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = sqlite3.connect("giveaway.db")
        self.db.row_factory = sqlite3.Row

    @app_commands.command(name="top", description="Top giveaway hosts in this server")
    async def top(self, interaction: Interaction):
        await interaction.response.defer()
        cur = self.db.cursor()
        stats = cur.execute("SELECT host_id, count FROM stats WHERE guild_id = ? ORDER BY count DESC", (interaction.guild.id,)).fetchall()

        if not stats:
            return await interaction.followup.send("No giveaway host data found.", ephemeral=True)

        embed = discord.Embed(title="👑 Top Giveaway Hosts", color=0x000000)
        for i, row in enumerate(stats[:10]):
            embed.add_field(name=f"{i + 1}. <@{row['host_id']}>", value=f"Giveaways: {row['count']}", inline=False)
        await interaction.followup.send(embed=embed)

async def setup(bot, giveaway_cog):
    await bot.add_cog(GiveawayTop(bot))
    pass