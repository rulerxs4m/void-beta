import os
from typing import List
from utils import (
    Context,
    ghost_url,
    embed_color,
    Bot,
    utility as util
)

import discord
from discord.ext import commands as cmds

from utils.database import structs

class util_cog(cmds.Cog):
    def __init__(self, bot: Bot):
        super().__init__()
        self.bot: Bot = bot

    @util.command(name="avatar", description="Get a member's server avatar", aliases=["av", "ava"])
    @util.describe(member = "The member you want the avatar of (default: You)")
    async def avatar(self, ctx: Context, member: discord.Member = cmds.Author):
        embed = discord.Embed(color = embed_color)
        embed.set_image(url=member.display_avatar.url)
        embed.set_footer(text=f"Requested by: {ctx.author}")
        embed.set_author(name=f"{member.display_name}'s Avatar")
        await ctx.reply(embed=embed)

async def setup(bot: Bot):
    await bot.add_cog(util_cog(bot))

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