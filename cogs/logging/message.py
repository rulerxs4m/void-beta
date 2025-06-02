from utils import (
    ghost_url,
    embed_color,
    Bot,
    utility as util
)

import discord
from discord.ext import commands as cmds

from discord import (
    RawMessageUpdateEvent,
    RawMessageDeleteEvent,
    RawBulkMessageDeleteEvent
)

from utils.embeds.message_logs import (
    message_edit_embed,
    message_delete_embed,
    message_bulk_delete_embed
)

class message_logs(cmds.Cog):
    def __init__(self, bot: Bot):
        super().__init__()
        self.bot: Bot = bot
    
    @cmds.Cog.listener()
    async def on_raw_message_edit(self, event: RawMessageUpdateEvent):
        if event.message.author.bot or not event.guild_id: return
        if (rec := self.bot.db.guild.logging.fetchone(event.guild_id)) == None: return
        if not rec.message: return
        try: webhook = await self.bot.fetch_webhook(rec.message)
        except (discord.NotFound, discord.Forbidden): return
        await webhook.send(
            embed = message_edit_embed(event),
            username = self.bot.user.display_name + " Logs",
            avatar_url = self.bot.user.display_avatar.url
        )

    @cmds.Cog.listener()
    async def on_raw_message_delete(self, event: RawMessageDeleteEvent):
        if event.cached_message:
            if event.cached_message.author.bot: return
        if not event.guild_id: return
        if (rec := self.bot.db.guild.logging.fetchone(event.guild_id)) == None: return
        if not rec.message: return
        try: webhook = await self.bot.fetch_webhook(rec.message)
        except (discord.NotFound, discord.Forbidden): return
        await webhook.send(
            embed = message_delete_embed(event),
            username = self.bot.user.display_name + " Logs",
            avatar_url = self.bot.user.display_avatar.url
        )
        

    @cmds.Cog.listener()
    async def on_raw_bulk_message_delete(self, event: RawBulkMessageDeleteEvent):
        if not event.guild_id: return
        if (rec := self.bot.db.guild.logging.fetchone(event.guild_id)) == None: return
        if not rec.message: return
        try: webhook = await self.bot.fetch_webhook(rec.message)
        except (discord.NotFound, discord.Forbidden): return
        embed = message_bulk_delete_embed(event)
        try:
            guild = self.bot.get_guild(event.guild_id)
            embed.set_author(
                name = guild.name,
                icon_url = guild.icon.url if guild.icon else None
            )
        except: pass
        await webhook.send(
            embed = embed,
            username = self.bot.user.display_name + " Logs",
            avatar_url = self.bot.user.display_avatar.url
        )


async def setup(bot: Bot):
    await bot.add_cog(message_logs(bot))