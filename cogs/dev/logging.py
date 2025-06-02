import datetime 
from utils import (
    ghost_url,
    embed_color,
    Bot,
    utility as util
)

import discord
from discord import ui
from discord.ext import commands as cmds

class dev_logging(cmds.Cog):
    def __init__(self, bot: Bot):
        super().__init__()
        self.bot: Bot = bot

    @cmds.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        embed = discord.Embed(
            title="Bot Added to Server",
            description=(
                f"**Server Name:** `{guild.name}`\n"
                f"**Owner:** `{guild.owner}` (`{guild.owner_id}`)\n"
                f"**Members:** `{guild.member_count}`\n"
                f"**Created At:** <t:{int(guild.created_at.timestamp())}:R> (<t:{int(guild.created_at.timestamp())}:f>)\n"
            ),
            color=embed_color,
            timestamp=datetime.datetime.now()
        )
        invite_link = guild.vanity_url if guild.vanity_url else None
        if not invite_link:
            try: invite_link = await guild.text_channels[0].create_invite(reason="Invite link for devs (just in case)")
            except: pass
        embed.set_thumbnail(url=guild.icon.url if guild.icon else ghost_url)
        embed.set_footer(text=f"Server ID: {guild.id}")
        embed.set_author(name=guild.name, icon_url=guild.icon.url if guild.icon else ghost_url, url=invite_link)
        inviter = None
        try:
            async for entry in guild.audit_logs(action=discord.AuditLogAction.bot_add, limit=10):
                if entry.target.id == self.bot.user.id:
                    inviter = entry.user; break
        except: pass
        if inviter: embed.description += f"**Invited By:** `{inviter}` (`{inviter.id}`)\n"
        await self.bot.logs_channel.send(embed=embed)
        
async def setup(bot: Bot):
    await bot.add_cog(dev_logging(bot))
