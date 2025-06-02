import datetime
from encodings import aliases
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

class mod_utility_purge_cog(cmds.Cog):
    def __init__(self, bot: Bot):
        super().__init__()
        self.bot: Bot = bot

    @cmds.group(
        name="purge",
        description="Purge messages from a channel.",
        aliases=["clear", "cu", "delete", "del"],
        invoke_without_command=True
    )
    @cmds.has_permissions(manage_messages=True)
    @cmds.bot_has_permissions(manage_messages=True)
    async def purge(self, ctx: cmds.Context, amount: int = 1, *, reason: str = "No reason provided."):
        if amount < 1 and amount > 1000:
            return await ctx.send("Please specify a number between 1 and 1000.")
        await ctx.message.delete()
        messages = await ctx.channel.purge(
            limit=amount,
            reason=f"Purged by {ctx.author.display_name} for reason: {reason}"
        )
        msgs = {}
        for m in messages:
            if m.author.mention not in msgs:
                msgs[m.author.mention] = 0
            msgs[m.author.mention] += 1
        embed = discord.Embed(title=f"{self.bot.emoji.tick} | Purged", color=embed_color)
        embed.description = "\n".join([f"- **{author} -** {count}" for author, count in msgs.items()])
        embed.set_footer(text=f"Purged {len(messages)} messages")
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
        embed.add_field(name="Reason", value=f"```{reason}```", inline=False)
        embed.timestamp = datetime.datetime.now()
        await ctx.send(ctx.author.mention, embed=embed, delete_after=10)

    @purge.command(name="all", description="Deletes and recreates the channel to delete all messages.")
    @cmds.has_permissions(manage_messages=True, manage_channels=True)
    @cmds.bot_has_permissions(manage_channels=True)
    async def purge_all(self, ctx: cmds.Context, *, reason: str = "No reason provided."):
        await ctx.reply(f"{self.bot.emoji.x_mark} | This command is disabled for now. Please use `.purge` instead.")
    
    @purge.command(name="user", description="Purge messages from a user.", aliases=["member", "u", "m"])
    @cmds.has_permissions(manage_messages=True)
    @cmds.bot_has_permissions(manage_messages=True)
    async def purge_user(self, ctx: cmds.Context, member: discord.Member, amount: int = 1, *, reason: str="No reason provided"):
        if amount < 1 and amount > 1000:
            return await ctx.send("Please specify a number between 1 and 1000.")
        messages = await ctx.channel.purge(
            limit=amount+1,
            check=lambda m: m.author.id == member.id,
            reason=f"Purged by {ctx.author.display_name} of user: {member.display_name} for reason: {reason}"
        )
        embed = discord.Embed(title=f"{self.bot.emoji.tick} | Purged", description=f"**User:** {len(messages)}", color=embed_color)
        embed.set_footer(text=f"Purged {len(messages)} messages")
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
        embed.timestamp = datetime.datetime.now()
        embed.add_field(name="Reason", value=f"```{reason}```", inline=False)
        await ctx.send(ctx.author.mention, embed=embed, delete_after=10)

async def setup(bot: Bot):
    #await bot.add_cog(mod_utility_purge_cog(bot))
    pass