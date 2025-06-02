import asyncio
import datetime
import time
from typing import Union
from xml.etree.ElementTree import QName
from utils import Bot, color, react
from utils import utility as util
from utils import ghost_url, embed_color, empty_char

import discord
from discord import ui
from discord.ext import tasks
from discord.ext import commands as cmds
from discord import Interaction, app_commands as acmds

from utils import pager

class Context(cmds.Context):
    bot: Bot

class help_group_view(ui.View):
    def __init__(self, ctx: Context, bot: Bot, cmd: cmds.Group):
        self.org_ctx = ctx
        self.bot = bot
        self.user_id = ctx.author.id
        self.group = cmd
        super().__init__()

    @ui.button(label="Show Subcommands", style=discord.ButtonStyle.gray)
    async def show_subcommands(self, ctx: Interaction, button: ui.Button):
        if ctx.user.id != self.user_id: return await ctx.response.send_message(f"{self.bot.emoji.lock} | This is not for you.", ephemeral=True)
        embed = discord.Embed(
            title = f"Subcommands of {self.group.qualified_name.title()}",
            color = embed_color
        )
        embed.set_author(
            name = f"{self.bot.user.display_name}'s Help Menu",
            icon_url = self.bot.user.display_avatar.url
        )
        embed.set_footer(
            text = f"Made by: {self.bot.made_by}",
            icon_url = ghost_url
        )
        pages = pager.Page(
            items = [
                dict(
                    name = cmd.name.title(),
                    value = (
                        f"**More Info:** `.help {cmd.qualified_name}`\n"
                        f"**Description:** {cmd.description or '...'}\n"
                        + empty_char
                    ), inline = False
                ) for cmd in self.group.commands
            ], c=5, user=ctx.user, em=embed
        )
        await ctx.response.send_message(embed=pages, view=pager.prev_next_btns(pages), ephemeral=True)

class help_cog(cmds.Cog):
    def __init__(self, bot: Bot):
        self. bot = bot

    @util.command(name="help", description="Get help on a command or category")
    @util.describe(command="The command to get the help for.")
    async def help(self, ctx: Context, *, command: str = None):
        if command:
            command = command.lower()
            cmd = self.bot.get_command(command)
        else: cmd = ctx.command

        embed = discord.Embed(
            title = f"{self.bot.emoji.commands} {cmd.qualified_name.title()}",
            description = cmd.description, # + f"\n{empty_char}",
            color = embed_color
        )
        embed.set_author(
            name = f"{self.bot.user.display_name}'s Help Menu",
            icon_url = self.bot.user.display_avatar.url
        )
        embed.set_footer(
            text = f"Made by: {self.bot.made_by}",
            icon_url = ghost_url
        )
        if cmd.aliases:
            embed.add_field(
                name = "Aliases",
                value = "**,** ".join(f"`{alias}`" for alias in cmd.aliases), # + f"\n{empty_char}",
                inline = False
            )
        if cmd.params:
            embed.add_field(
                name = "Parameters",
                value = "\n".join(
                    f"{self.bot.emoji.bdot} **`{name}`:** {param.description}"
                    for name, param in cmd.clean_params.items()
                )
            )
        embed.add_field(
            name = "Syntax",
            value = util.generate_command_syntax(cmd),
            inline = False
        )
        view = help_group_view(ctx, self.bot, cmd) if isinstance(cmd, cmds.Group) else None
        await ctx.reply(embed=embed, view=view)

async def setup(bot: Bot):
    await bot.add_cog(help_cog(bot))