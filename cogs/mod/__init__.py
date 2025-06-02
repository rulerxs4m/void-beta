import os
from typing import List
from utils import (
    ghost_url,
    embed_color,
    Bot,
    utility as util
)

import discord
from discord.ext import commands as cmds

from utils.database import structs

class mod_cog(cmds.Cog):
    def __init__(self, bot: Bot):
        super().__init__()
        self.bot: Bot = bot
        
async def setup(bot: Bot):
    await bot.add_cog(mod_cog(bot))

    for sub_cog in os.listdir(os.path.dirname(__file__)):
        if sub_cog in ["__init__.py", "__pycache__"]: continue
        name = sub_cog.split(".")[0]
        await bot.load_extension(f"{__name__}.{name}")
        bot._all_cogs.add(f"{__name__}.{name}")

async def teardown(bot: Bot):
    for sub_cog in os.listdir(os.path.dirname(__file__)):
        if sub_cog in ["__init__.py", "__pycache__"]: continue
        name = sub_cog.split(".")[0]
        await bot.unload_extension(f"{__name__}.{name}")