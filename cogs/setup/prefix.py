from utils import (
    ghost_url,
    embed_color,
    Bot,
    utility as util
)

import discord
from discord.ext import commands as cmds

from utils.database import structs

class prefix_cog(cmds.Cog):
    def __init__(self, bot: Bot):
        super().__init__()
        self.bot: Bot = bot

    @util.group(description="Setup Custom Prefixes for the server", aliases=["prefixes"], invoke_without_command=True)
    async def prefix(self, ctx: cmds.Context):
        if ctx.invoked_subcommand: return
        prefixes = self.bot.db.guild.prefixes.fetchone(ctx.guild.id)
        prefixes = prefixes.pref if prefixes else []
        embed = discord.Embed(title=f"Prefixes", description="Use `.prefix user [action] [prefix]` to manage your custom prefixes", color=embed_color)
        embed.add_field(name="Default prefixes", value="\n".join((f"- `{p}`" if "@" not in p else f"- {p}") for p in self.bot.command_prefix(self.bot, ctx.message) if "!" not in p))
        embed.add_field(name="Custom prefixes", value="\n".join(f"- `{p}`" for p in prefixes) if prefixes else "None")
        embed.set_author(name=ctx.guild.name, icon_url=ctx.guild.icon.url if ctx.guild.icon else None)
        embed.set_footer(text=f"Made by: {self.bot.made_by}", icon_url=ghost_url)
        embed.set_thumbnail(url=ctx.guild.icon.url if ctx.guild.icon else None)
        await ctx.reply(embed=embed)

    @prefix.command(name="add", description="Add a custom prefix to the server prefixes")
    @cmds.has_permissions(manage_guild=True)
    @util.describe(prefix="The prefix to add")
    async def prefix_add(self, ctx: cmds.Context, prefix: str):
        if not prefix or len(prefix) > 10:
            return await ctx.reply(f"{self.bot.emoji.x_mark} | Prefix must be between 1 and 10 characters long")
        record = self.bot.db.guild.prefixes.fetchone(ctx.guild.id)
        prefixes = record.pref if record else []
        if prefix in prefixes: return await ctx.reply(f"{self.bot.emoji.x_mark} | Custom prefix `{prefix}` already exists for **{ctx.guild.name}**")
        prefixes.append(prefix)
        if record: self.bot.db.guild.prefixes.update(ctx.guild.id, str(prefixes))
        else: self.bot.db.guild.prefixes.insert(ctx.guild.id, str(prefixes))
        await ctx.reply(f"{self.bot.emoji.tick} | Added custom prefix `{prefix}` for **{ctx.guild.name}**")

    @prefix.command(name="remove", description="Remove a custom prefix from server prefixes", aliases=["delete"])
    @cmds.has_permissions(manage_guild=True)
    @util.describe(prefix="The prefix to remove")
    async def prefix_remove(self, ctx: cmds.Context, prefix: str):
        if not prefix or len(prefix) > 10:
            return await ctx.reply(f"{self.bot.emoji.x_mark} | Prefix must be between 1 and 10 characters long")
        entry = self.bot.db.guild.prefixes.fetchone(ctx.guild.id)
        prefixes = entry.pref if entry else []
        if not prefixes or prefix not in prefixes:
            return await ctx.reply(f"{self.bot.emoji.x_mark} | Custom prefix `{prefix}` does not exist for **{ctx.guild.name}**")
        prefixes.remove(prefix)
        if not prefixes: self.bot.db.guild.prefixes.delete(ctx.guild.id)
        else: self.bot.db.guild.prefixes.update(ctx.guild.id, str(prefixes))
        await ctx.reply(f"{self.bot.emoji.tick} | Removed custom prefix `{prefix}` for **{ctx.guild.name}**")

    @prefix.command(name="update", description="Edit a server's custom prefix", aliases=["edit"])
    @cmds.has_permissions(manage_guild=True)
    @util.describe(old = "The old prefix", new = "The new prefix")
    async def prefix_update(self, ctx: cmds.Context, old: str, new: str):
        if not old or len(old) > 10 or not new or len(new) > 10:
            return await ctx.reply(f"{self.bot.emoji.x_mark} | Prefix must be between 1 and 10 characters long")
        entry = self.bot.db.guild.prefixes.fetchone(ctx.guild.id)
        prefixes = entry.pref if entry else []
        if not prefixes or old not in prefixes:
            return await ctx.reply(f"{self.bot.emoji.x_mark} | Custom prefix `{old}` does not exist for **{ctx.guild.name}**")
        if new in prefixes:
            return await ctx.reply(f"{self.bot.emoji.x_mark} | Custom prefix `{new}` already exists for **{ctx.guild.name}**")
        prefixes.remove(old)
        prefixes.append(new)
        if not prefixes: self.bot.db.guild.prefixes.delete(ctx.guild.id)
        else: self.bot.db.guild.prefixes.update(ctx.guild.id, str(prefixes))
        await ctx.reply(f"{self.bot.emoji.tick} | Updated custom prefix `{old}` to `{new}` for **{ctx.guild.name}**")

    @prefix.command(name="clear", description="Clear all custom prefixes of the server")
    @cmds.has_permissions(manage_guild=True)
    async def prefix_clear(self, ctx: cmds.Context):
        entry = self.bot.db.guild.prefixes.fetchone(ctx.guild.id)
        prefixes = entry.pref if entry else []
        if not prefixes: return await ctx.reply(f"{self.bot.emoji.x_mark} | No custom prefixes found for **{ctx.guild.name}**")
        self.bot.db.guild.prefixes.delete(ctx.guild.id)
        await ctx.reply(f"{self.bot.emoji.tick} | Cleared all custom prefixes for **{ctx.guild.name}**")

    @prefix.group(name="user", description="Setup custom prefixes for yourself", aliases=["users"], invoke_without_command=True)
    async def prefix_user(self, ctx: cmds.Context):
        if ctx.invoked_subcommand: return
        prefixes = self.bot.db.user.prefixes.fetchone(ctx.author.id)
        prefixes = prefixes.pref if prefixes else []
        embed = discord.Embed(title=f"Prefixes", description="Use `.prefix [action] [prefix]` to manage server's prefixes", color=embed_color)
        embed.add_field(name="Default prefixes", value="\n".join((f"- `{p}`" if "@" not in p else f"- {p}") for p in self.bot.command_prefix(self.bot, ctx.message) if "!" not in p))
        embed.add_field(name="Custom prefixes", value="\n".join(f"- `{p}`" for p in prefixes) if prefixes else "None")
        embed.set_author(name=ctx.author.global_name, icon_url=ctx.author.display_avatar.url)
        embed.set_footer(text=f"Made by: {self.bot.made_by}", icon_url=ghost_url)
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        await ctx.reply(embed=embed)

    @prefix_user.command(name="add", description="Add a custom user prefix")
    @util.describe(prefix="The prefix to add")
    async def prefix_user_add(self, ctx: cmds.Context, prefix: str):
        if not prefix or len(prefix) > 10:
            return await ctx.reply(f"{self.bot.emoji.x_mark} | prefix must be between 1 and 10 characters long")
        record = self.bot.db.user.prefixes.fetchone(ctx.author.id)
        prefixes = record.pref if record else []
        if prefix in prefixes: return await ctx.reply(f"{self.bot.emoji.x_mark} | You already have `{prefix}` in your custom prefixes.")
        prefixes.append(prefix)
        if record: self.bot.db.user.prefixes.update(ctx.author.id, str(prefixes))
        else: self.bot.db.user.prefixes.insert(ctx.author.id, str(prefixes))
        await ctx.reply(f"{self.bot.emoji.tick} | Added `{prefix}` in your custom prefixes.")

    @prefix_user.command(name="remove", description="Remove a custom user prefix.", aliases=["delete"])
    @util.describe(prefix="The prefix to remove")
    async def prefix_user_remove(self, ctx: cmds.Context, prefix: str):
        if not prefix or len(prefix) > 10:
            return await ctx.reply(f"{self.bot.emoji.x_mark} | Prefix must be between 1 and 10 characters long")
        entry = self.bot.db.user.prefixes.fetchone(ctx.author.id)
        prefixes = entry.pref if entry else []
        if not prefixes or prefix not in prefixes:
            return await ctx.reply(f"{self.bot.emoji.x_mark} | You do not have `{prefix}` in your custom prefixes.")
        prefixes.remove(prefix)
        if not prefixes: self.bot.db.user.prefixes.delete(ctx.author.id)
        else: self.bot.db.user.prefixes.update(ctx.author.id, str(prefixes))
        await ctx.reply(f"{self.bot.emoji.tick} | Removed `{prefix}` from your custom prefixes.")

    @prefix_user.command(name="update", description="Edit a custom prefix", aliases=["edit"])
    @util.describe(old="Old prefix", new="New prefix")
    async def prefix_user_update(self, ctx: cmds.Context, old: str, new: str):
        if not old or len(old) > 10 or not new or len(new) > 10:
            return await ctx.reply(f"{self.bot.emoji.x_mark} | Prefix must be between 1 and 10 characters long")
        entry = self.bot.db.user.prefixes.fetchone(ctx.author.id)
        prefixes = entry.pref if entry else []
        if not prefixes or old not in prefixes:
            return await ctx.reply(f"{self.bot.emoji.x_mark} | You do not have `{old}` in your custom prefixes.")
        if new in prefixes:
            return await ctx.reply(f"{self.bot.emoji.x_mark} | You already have `{new}` in your custom prefixes.")
        prefixes.remove(old)
        prefixes.append(new)
        if not prefixes: self.bot.db.user.prefixes.delete(ctx.author.id)
        else: self.bot.db.user.prefixes.update(ctx.author.id, str(prefixes))
        await ctx.reply(f"{self.bot.emoji.tick} | Updated your custom prefix `{old}` to `{new}`")

    @prefix_user.command(name="clear", description="Clear all custom prefixes")
    async def prefix_user_clear(self, ctx: cmds.Context):
        entry = self.bot.db.user.prefixes.fetchone(ctx.guild.id)
        prefixes = entry.pref if entry else []
        if not prefixes: return await ctx.reply(f"{self.bot.emoji.x_mark} | You dont have any custom prefixes")
        self.bot.db.user.prefixes.delete(ctx.guild.id)
        await ctx.reply(f"{self.bot.emoji.tick} | Cleared all your custom prefixes")

async def setup(bot: Bot):
    await bot.add_cog(prefix_cog(bot))
