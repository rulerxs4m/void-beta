from utils import (
    ghost_url,
    embed_color,
    Bot,
    utility as util
)

import discord
from discord.ext import commands as cmds

class cogs_cmds(cmds.Cog):
    def __init__(self, bot: Bot):
        super().__init__()
        self.bot: Bot = bot

    @cmds.group(invoke_without_command=True)
    @cmds.is_owner()
    async def cogs(self, ctx: cmds.Context):
        if ctx.invoked_subcommand: return
        embed = discord.Embed(title=f"Cogs - {self.bot.user.display_name}", color=embed_color)
        embed.add_field(name="Loaded", value = "\n".join([f"- `{name}`" for name in self.bot.extensions.keys()]))
        embed.add_field(name="Unloaded", value = "\n".join([f"- `{name}`" for name in self.bot._all_cogs if name not in self.bot.extensions.keys()]))
        for i, f in enumerate(embed.fields):
            if f.value == "": embed.remove_field(i)
        embed.set_author(name=self.bot.user.display_name, icon_url=self.bot.user.display_avatar.url)
        embed.set_footer(text=f"Made by {self.bot.made_by}", icon_url=ghost_url)
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        await ctx.reply(embed=embed)

    @cogs.command(name="load", aliases=["add"])
    @cmds.is_owner()
    async def cogs_load(self, ctx: cmds.Context, name: str):
        if name == "all":
            for cog in self.bot._all_cogs:
                if cog not in self.bot.extensions.keys():
                    try: await self.bot.load_extension(cog)
                    except Exception as e: await ctx.reply(f"{self.bot.emoji.x_mark} | Cog `{cog}` could not be loaded.\n```ansi\n\x1b[31m{e}\x1b[0m\n```")
            return await ctx.reply(f"{self.bot.emoji.tick} | All cogs loaded successfully.")
        if name in self.bot.extensions.keys():
            return await ctx.reply(f"{self.bot.emoji.x_mark} | Cog `{name}` is already loaded.")
        try:
            await self.bot.load_extension(name)
            await ctx.reply(f"{self.bot.emoji.tick} | Cog `{name}` loaded successfully.")
        except Exception as e:
            if self.bot.DEBUG: raise
            return await ctx.reply(f"{self.bot.emoji.x_mark} | Cog `{name}` could not be loaded.\n```ansi\n\x1b[31m{e}\x1b[0m\n```")

    @cogs.command(name="unload", aliases=["remove"])
    @cmds.is_owner()
    async def cogs_unload(self, ctx: cmds.Context, name: str):
        if name == "all":
            for cog in self.bot.extensions.keys():
                if "dev" in cog: continue
                try: await self.bot.unload_extension(cog)
                except Exception as e: await ctx.reply(f"{self.bot.emoji.x_mark} | Cog `{cog}` could not be loaded.\n```ansi\n\x1b[31m{e}\x1b[0m\n```")
            return await ctx.reply(f"{self.bot.emoji.tick} | All cogs unloaded successfully.")
        if name not in self.bot.extensions.keys():
            return await ctx.reply(f"{self.bot.emoji.x_mark} | Cog `{name}` is not loaded.")
        try:
            await self.bot.unload_extension(name)
            await ctx.reply(f"{self.bot.emoji.tick} | Cog `{name}` unloaded successfully.")
        except Exception as e:
            if self.bot.DEBUG: raise
            return await ctx.reply(f"{self.bot.emoji.x_mark} | Cog `{name}` could not be unloaded.\n```ansi\n\x1b[31m{e}\x1b[0m\n```")
        
    @cogs.command(name="reload")
    @cmds.is_owner()
    async def cogs_reload(self, ctx: cmds.Context, name: str):
        if name == "all":
            for cog in self.bot.extensions.keys():
                try: await self.bot.reload_extension(cog)
                except Exception as e: await ctx.reply(f"{self.bot.emoji.x_mark} | Cog `{cog}` could not be loaded.\n```ansi\n\x1b[31m{e}\x1b[0m\n```")
            return await ctx.reply(f"{self.bot.emoji.tick} | All cogs reloaded successfully.")
        if name not in self.bot.extensions.keys():
            return await ctx.reply(f"{self.bot.emoji.x_mark} | Cog `{name}` is not loaded.")
        try:
            await self.bot.reload_extension(name)
            await ctx.reply(f"{self.bot.emoji.tick} | Cog `{name}` reloaded successfully.")
        except Exception as e:
            if self.bot.DEBUG: raise
            return await ctx.reply(f"{self.bot.emoji.x_mark} | Cog `{name}` could not be reloaded.\n```ansi\n\x1b[31m{e}\x1b[0m\n```")
        
async def setup(bot: Bot):
    await bot.add_cog(cogs_cmds(bot))
