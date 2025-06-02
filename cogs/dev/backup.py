import datetime
import time

import pytz
from utils import Bot, color, react, Context
from utils import utility as util
from utils import ghost_url, embed_color, empty_char


import io
from typing import Union

import discord
from discord.ext import tasks
from discord.ext import commands as cmds

class db_backup_cog(cmds.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @tasks.loop(time = [
        datetime.time(00, tzinfo=pytz.timezone("Asia/Kolkata")),
        datetime.time(6, tzinfo=pytz.timezone("Asia/Kolkata")),
        datetime.time(12, tzinfo=pytz.timezone("Asia/Kolkata")),
        datetime.time(18, tzinfo=pytz.timezone("Asia/Kolkata")),
    ])
    async def dB_backup_task(self):
        pass

    @cmds.command(name="backup_db")
    @cmds.is_owner()
    async def backup_db(self, ctx: Context):
        await ctx.author.send(
            f"## BACKUP AT: <t:{int(time.time())}:F>",
            file = discord.File("production.db" if not self.bot.DEBUG else "testing.db")
        )
        self.bot.logger.info(
            f"User: {color.color(ctx.author, (0, 255,0 ))} ({color.color(ctx.author.id, (255,255,0))}) | "
            f"Took database backup ( {self.bot.DEBUG = } )"
        )
        await react(ctx.message, self.bot.emoji.tick)

async def setup(bot: Bot):
    await bot.add_cog(db_backup_cog(bot))