from dataclasses import dataclass
from typing import Any, Dict
import datetime
from utils import Bot, color
from utils import utility as util
from utils import ghost_url, embed_color, empty_char

import discord
from discord import ui
from discord.ext import tasks
from discord.ext import commands as cmds

@dataclass()
class gtn_data:
    host: discord.Member
    number: int

class guess_the_number(cmds.Cog):
    def __init__(self, bot: Bot):
        self.bot: Bot = bot
        self.ongoing: Dict[int, gtn_data] = {}

    @cmds.Cog.listener()
    async def on_message(self, msg: discord.Message) -> None:
        if msg.channel.id not in self.ongoing: return
        content = discord.utils.remove_markdown(msg.content).strip().replace(",", "")
        if not content.isdigit(): return
        if int(content) != self.ongoing[msg.channel.id].number: return
        data = self.ongoing.pop(msg.channel.id)
        embed = discord.Embed(
            title = "Win !!! :tada: :tada:",
            color = embed_color,
            timestamp = datetime.datetime.now(),
            description = (
                f"**Winner:** {msg.author.mention} (`{msg.author}`)\n"
                f"**Number:** {data.number:,}\n"
                f"**Host:** {data.host.mention}\n"
            )
        )
        embed.set_author(name="Guess the number")
        embed.set_footer(text=f"By: {data.host}")
        await msg.reply(data.host.mention, embed=embed)

    @util.command(name="gtn", description="Start a guess the number game.")
    @util.describe(
        lower = "The lower limit of the range",
        upper = "The upper limit of the range"
    )
    async def gtn(self, ctx: cmds.Context, lower: int, upper: int) -> Any:
        await ctx.reply("Press the button below to set your number.", view=number_setter_button(self, ctx, self.bot, lower, upper))

class number_input_modal(ui.Modal):
    number_input = ui.TextInput(label="THE Number")

    def __init__(self, gtn: guess_the_number, lower: int, upper: int, msg: discord.Message, bot: Bot) -> None:
        self.gtn = gtn
        self.lower = lower
        self.upper = upper
        self.msg = msg
        self.bot = bot
        super().__init__(title='Enter THE Number')

    async def on_submit(self, i: discord.Interaction):
        value = self.number_input.value.strip().replace(",","")
        if not value.isdigit(): return await i.response.send_message(f"{value} is not a valid number", ephemeral=True)
        number = int(value)
        if number < self.lower or number > self.upper:
            return await i.response.send_message(f"{value:,} is not in range: {self.lower:,} to {self.upper:,}", ephemeral=True)
        embed = discord.Embed(
            title = "GAME STARTED",
            color = embed_color,
            timestamp = datetime.datetime.now(),
            description = (
                f"**Host:** {i.user.mention} (`{i.user}`)\n"
                f"**Range:** {self.lower:,} to {self.upper:,}\n"
            )
        )
        embed.set_author(name="Guess The Number")
        self.gtn.ongoing[i.channel_id] = gtn_data(i.user, number)
        await self.msg.edit(content=f"{self.bot.emoji.tick} | {i.user.mention} set ***__THE__*** Number", view=None)
        await i.response.send_message(embed=embed)

class number_setter_button(ui.View):
    def __init__(self, gtn: guess_the_number, ctx: cmds.Context, bot: Bot, lower: int, upper: int) -> None:
        self.gtn = gtn
        self.ctx = ctx
        self.bot = bot
        self.lower = lower
        self.upper = upper
        super().__init__()

    @ui.button(label="Set number", style=discord.ButtonStyle.blurple)
    async def set_number_button(self, i: discord.Interaction, button: ui.Button) -> None:
        if i.user.id != self.ctx.author.id: return await i.response.send_message(f"{self.bot.emoji.lock} | This is not for you.", ephemeral=True)
        await i.response.send_modal(number_input_modal(self.gtn, self.lower, self.upper, i.message, self.bot))
        await i.message.edit(content=f"*{i.user.mention} is setting **THE** Number*", view=self)

async def setup(bot: Bot):
    await bot.add_cog(guess_the_number(bot))