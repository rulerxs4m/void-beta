import time
import requests

from utils import Bot, color
from utils import utility as util
from utils import ghost_url, embed_color, empty_char

import discord
from discord.ext import commands as cmds

class general_cog(cmds.Cog):
    def __init__(self, bot):
        super().__init__()
        self.bot: Bot = bot

    @util.command(description="Show the latencies of the bot.")
    async def ping(self, ctx: cmds.Context):
        embed = discord.Embed(title="Pong!", color=embed_color)
        a = time.perf_counter()
        msg = await ctx.reply("🏓 Pinging...", mention_author=False)
        b = time.perf_counter()
        async with ctx.typing():
            msg_time = float(b - a) * 1000
            a = time.perf_counter()
            self.bot.db.cursor.execute("SELECT 1")
            b = time.perf_counter()
            db_time = float(b - a) * 1000
            ws_time = self.bot.latency * 1000
            discord_status = requests.get("https://discordstatus.com/api/v2/status.json").json()["status"]["description"]
            avg_time = (msg_time + db_time + ws_time) / 3

            msg_color = color.ansi(f"{msg_time:.2f}ms", format=color.type.bold,
                fg = (color.fg.green if msg_time < 250 else (
                    color.fg.yellow if msg_time < 500 else color.fg.red
                ))
            )

            db_color = color.ansi(f"{db_time:.2f}ms", format=color.type.bold,
                fg = (color.fg.green if db_time < 300 else (
                    color.fg.yellow if db_time < 600 else color.fg.red
                ))
            )

            ws_color = color.ansi(f"{ws_time:.2f}ms", format=color.type.bold,
                fg = (color.fg.green if ws_time < 150 else (
                    color.fg.yellow if ws_time < 400 else color.fg.red
                ))
            )

            avg_color = color.ansi(f"{avg_time:.2f}ms", format=color.type.bold,
                fg = (color.fg.green if avg_time < 300 else (
                    color.fg.yellow if avg_time < 600 else color.fg.red
                ))
            )

            dc_color = color.ansi(discord_status, format=color.type.bold,
                fg = (color.fg.green if discord_status == "All Systems Operational" else (
                    color.fg.yellow if "Partial" in discord_status else color.fg.red
                ))
            )

            embed.add_field(name="Bot Latency", value=msg_color)
            embed.add_field(name="WS Latency", value=ws_color)
            embed.add_field(name="DB Latency", value=db_color)

            embed.add_field(name="Avg. Latency", value=avg_color)
            embed.add_field(name="Discord Status", value=dc_color)
            
            embed.set_author(name=self.bot.user.display_name, icon_url=self.bot.user.display_avatar.url)
            embed.set_footer(text=f"Made by: {self.bot.made_by}", icon_url=ghost_url)
            embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        await msg.edit(content="", embed=embed)

async def setup(bot: Bot):
    await bot.add_cog(general_cog(bot))
