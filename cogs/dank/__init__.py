import os
import re
import math

from utils import (
    color,
    ghost_url,
    embed_color,
    Bot, Context,
    utility as util
)

import discord
from discord.ext import commands as cmds

dank_id = 270904126974590976
coin = "⏣"

class Amount(cmds.Converter[int]):
    SUFFIXES = {
        "k": 1_000, "thousand": 1_000, "m": 1_000_000, "mil": 1_000_000, "million": 1_000_000,
        "b": 1_000_000_000, "bil": 1_000_000_000, "billion": 1_000_000_000, 
        "t": 1_000_000_000_000, "tril": 1_000_000_000_000, "trillion": 1_000_000_000_000
    }
    FORMAT_SUFFIXES = [(1_000_000_000_000, "T"), (1_000_000_000, "B"), (1_000_000, "M"), (1_000, "K")]
    CLEAN_TRAILING = re.compile(r'[^\w\d]+$')
    NUMBER_PATTERN = re.compile(r"^([\d,]+(?:\.\d+)?)([a-z]*)$", re.IGNORECASE)
    
    async def convert(self, ctx: Context, argument: str) -> int:
        argument = self.CLEAN_TRAILING.sub("", argument.replace(",", "").strip().lower())
        match = self.NUMBER_PATTERN.fullmatch(argument)
        if not match: raise cmds.BadArgument("Invalid format. Example: `1k`, `2.5mil`, `4billion`.")
        number_part, suffix = match.groups()
        multiplier = self.SUFFIXES.get(suffix, 1)
        try: number = float(number_part)
        except ValueError: raise cmds.BadArgument("Invalid number.")
        return int(number * multiplier)

    @staticmethod
    def format(amount: int, pos=None) -> str:
        for threshold, suffix in Amount.FORMAT_SUFFIXES:
            if amount >= threshold:
                truncated = math.floor(amount / threshold * 100) / 100
                return f"{truncated:.2f}{suffix}"
        return str(amount)

    @staticmethod
    def format_2(amount: int, pos=None) -> str:
        for threshold, suffix in Amount.FORMAT_SUFFIXES:
            if amount >= threshold:
                truncated = amount / threshold
                formatted = f"{truncated:.2f}".rstrip('0').rstrip('.')
                return f"{formatted}{suffix}"
        return str(amount)

class dank_cog(cmds.Cog):
    def __init__(self, bot: Bot):
        super().__init__()
        self.bot: Bot = bot

async def setup(bot: Bot):
    await bot.add_cog(dank_cog(bot))

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