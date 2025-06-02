import datetime
from typing import Dict, List
import asyncio
import time

from utils import (
    ghost_url,
    embed_color,
    empty_char,
    Bot,
    Context,
    react,
    utility as util,
    structs,
    pager
)

import discord
from discord import Interaction, ui
from discord.ext import commands as cmds

class afk_scope_buttons(ui.View):
    def __init__(self, ctx: Context, bot: Bot, reason: str):
        self.msg = ctx.message
        self.bot = bot
        self.user_id = ctx.author.id
        self.reason = reason
        super().__init__()
    
    @ui.button(label="Global", style=discord.ButtonStyle.gray, emoji="🌐")
    async def global_afk_btn(self, ctx: Interaction, btn: ui.Button):
        if ctx.user.id != self.user_id:
            return await ctx.response.send_message(f"{self.bot.emoji.lock} | This is not for you.", ephemeral=True)
        await ctx.response.defer(ephemeral=True)
        await self.set_afk(ctx, "global")
        self.stop()

    @ui.button(label="Server", style=discord.ButtonStyle.gray, emoji="😈")
    async def server_afk_btn(self, ctx: Interaction, btn: ui.Button):
        if ctx.user.id != self.user_id:
            return await ctx.response.send_message(f"{self.bot.emoji.lock} | This is not for you.", ephemeral=True)
        await ctx.response.defer(ephemeral=True)
        await self.set_afk(ctx, "server")
        self.stop()

    async def on_timeout(self):
        await react(self.message, ":stopwatch:")
        await self.message.edit(content=":stopwatch: | AFK setup cancelled (no selection for too long).", view=None)
        return await super().on_timeout()

    async def set_afk(self, ctx: Interaction, scope: str):
        if not ctx.user.display_name.startswith("[AFK]"):
            try: await ctx.user.edit(nick="[AFK] "+ ctx.user.display_name)
            except: pass
        self.bot.db.user.afk.insert(
            ctx.user.id,
            ctx.guild.id,
            scope == "global",
            int(time.time()),
            self.reason
        )
        embed = discord.Embed(
            title = f"Set you to afk",
            description = (
                f"- **AFK Scope:** {'Global' if scope == 'global' else 'Server'}\n"
                f"- **Reason:** {self.reason or 'No Reason'}"
            ),
            color = embed_color,
            timestamp = datetime.datetime.now()
        )
        embed.set_thumbnail(url=ctx.user.display_avatar.url)
        embed.set_author(
            name = ctx.user.display_name,
            icon_url = ctx.user.display_avatar.url
        )
        await react(self.msg, self.bot.emoji.tick)
        msg = await ctx.edit_original_response(content=None, embed=embed, view=None)
        await asyncio.sleep(10)
        await msg.delete()

class afk_pings_view(ui.View):
    def __init__(self, bot: Bot, msg: discord.Message, pings: List[structs.user_afk_mentions]):
        self.bot: Bot = bot
        self.msg: discord.Message = msg
        self.pings: List[structs.user_afk_mentions] = pings
        super().__init__(timeout=20)

    @ui.button(label="Pings", style=discord.ButtonStyle.gray)
    async def pings_btn(self, ctx: Interaction, btn: ui.Button):
        if self.msg.author.id != ctx.user.id:
            return await ctx.response.send_message(f"{self.bot.emoji.lock} | This is not for you.", ephemeral=True)
        if self.pings == []:
            return await ctx.response.send_message(f":pensive: | No one pinged you.", ephemeral=True)
        embed = pager.Page(
            items = [
                dict(
                    name = f"Ping (<t:{ping.timestamp}:R>)",
                    value = (
                        f"**Date & Time:** <t:{ping.timestamp}:F>\n"
                        f"**Pinged By:** <@{ping.uid}>\n"
                        f"**Link:** https://discord.com/channels/{ping.guild_id}/{ping.channel_id}/{ping.message_id}\n"
                        + empty_char
                    ), inline = False
                ) for ping in self.pings
            ], c = 5, user = ctx.user
        )
        await ctx.response.send_message(embed=embed, view=pager.prev_next_btns(embed), ephemeral=True)

class afk_cog(cmds.Cog):
    def __init__(self, bot: Bot):
        super().__init__()
        self.bot: Bot = bot

    async def self_afk(self, msg: discord.Message):
        self.bot.db.cursor.execute(
            "SELECT * FROM user_afk WHERE uid = ? AND (gid = ? OR is_global = 1) LIMIT 1",
            (msg.author.id, msg.guild.id)
        )
        data = self.bot.db.user.afk.parse(self.bot.db.cursor.fetchone())
        if not data: return
        if not data.is_global:
            self.bot.db.cursor.execute(
                "SELECT * FROM user_afk_mentions WHERE uid = ? AND guild_id = ?",
                (msg.author.id, msg.guild.id)
            )
            pings_raw = self.bot.db.cursor.fetchall()
            self.bot.db.cursor.execute(
                "DELETE FROM user_afk_mentions WHERE uid = ? AND guild_id = ?",
                (msg.author.id, msg.guild.id)
            )
            self.bot.db.cursor.execute(
                "DELETE FROM user_afk WHERE uid = ? AND is_global = 0 AND gid = ?",
                (msg.author.id, msg.guild.id)
            )
        elif data.is_global:
            self.bot.db.cursor.execute(
                "SELECT * FROM user_afk_mentions WHERE uid = ?",
                (msg.author.id,)
            )
            pings_raw = self.bot.db.cursor.fetchall()
            self.bot.db.cursor.execute(
                "DELETE FROM user_afk_mentions WHERE uid = ?",
                (msg.author.id,)
            )
            self.bot.db.cursor.execute(
                "DELETE FROM user_afk WHERE uid = ? AND is_global = 1",
                (msg.author.id,)
            )
        self.bot.db.commit()
        pings = [self.bot.db.user.afk_mentions.parse(x) for x in pings_raw]
        embed = discord.Embed(
            title = "Welcome Back",
            description = (
                f"- **AFK Since:** <t:{data.timestamp}:f>\n"
                f"- **AFK Scope:** {'Global' if data.is_global else 'Server'}\n"
                f"- **No. Of Pings:** `{len(pings):,}`\n"
                f"- **Reason:** {data.reason}"
            ),
            color = embed_color,
            timestamp = datetime.datetime.now()
        )
        embed.set_author(name=msg.author.display_name, icon_url=msg.author.display_avatar.url)
        embed.set_footer(text="Removed you from afk")
        try: await msg.author.edit(nick=msg.user.display_name.replace("[AFK] ", ""))
        except: pass
        return await msg.reply(embed=embed, view=afk_pings_view(self.bot, msg, pings), delete_after=20)

    async def mentions(self, msg: discord.Message):
        for m in msg.mentions:
            self.bot.db.cursor.execute(
                "SELECT * FROM user_afk WHERE uid = ? AND (gid = ? OR is_global = 1) LIMIT 1",
                (m.id, msg.guild.id)
            )
            data = self.bot.db.user.afk.parse(self.bot.db.cursor.fetchone())
            if not data: continue
            self.bot.db.cursor.execute(
                "INSERT INTO user_afk_mentions "
                "(uid, guild_id, channel_id, message_id, pinger_id, timestamp) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (m.id, msg.guild.id, msg.channel.id, msg.id, msg.author.id, int(msg.created_at.timestamp()))
            )
            self.bot.db.commit()
            embed = discord.Embed(
                title = "User is AFK",
                description = (
                    f"- **AFK Since:** <t:{data.timestamp}:R>\n"
                    f"- **Reason:** {data.reason}\n"
                ),
                color = embed_color
            )
            embed.set_author(name=m.display_name, icon_url=m.display_avatar.url)
            embed.set_thumbnail(url=m.display_avatar.url)
            await msg.reply(embed=embed, delete_after=10)

    @cmds.Cog.listener()
    async def on_message(self, msg: discord.Message):
        if msg.author.bot: return
        await self.self_afk(msg)
        if not msg.mentions: return
        await self.mentions(msg)

    @util.command(description="Set you to AFK")
    @util.describe(reason = "The reason for going AFK. (Optional)")
    async def afk(self, ctx: cmds.Context, *, reason: str=None):
        view = afk_scope_buttons(ctx, self.bot, reason)
        prompt = await ctx.reply("Choose AFK scope:", view=view)
        view.message = prompt

async def setup(bot: Bot):
    await bot.add_cog(afk_cog(bot))