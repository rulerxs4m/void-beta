import discord
import sqlite3
from discord.ext import commands
from datetime import datetime, timezone

DB_PATH = "giveaway.db"
BLACK = 0x000000

# Built-in emoji equivalents
ARROW = "➡️"
PRIZE = "🎁"
START_TIME = "⏰"
END_TIME = "📅"
HOST = "🙋"
CROWN = "👑"
ANNOUNCE = "📢"

class GiveawayLogger(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def send_log(
        self,
        guild: discord.Guild,
        actor: discord.Member,
        giveaway_message: discord.Message,
        prize: str,
        start_time: datetime,
        end_time: datetime,
        winner_count: int,
    ):
        try:
            with sqlite3.connect(DB_PATH) as db:
                c = db.cursor()
                c.execute("SELECT log_channel, log_enabled FROM config WHERE guild_id = ?", (guild.id,))
                result = c.fetchone()

                if not result or not result[0] or not int(result[1]):
                    return  # Logging not enabled or channel not set

                log_channel_id = int(result[0])
                log_channel = guild.get_channel(log_channel_id)
                if not log_channel:
                    return

                now = datetime.now(timezone.utc)

                embed = discord.Embed(
                    title=f"{ANNOUNCE} New Giveaway Started!",
                    color=BLACK,
                    timestamp=now
                )

                embed.add_field(name=f"{ARROW} Action taken by", value=f"{actor.mention} (`{actor.id}`)", inline=False)
                embed.add_field(name=f"{PRIZE} Prize", value=prize or "No prize", inline=True)

                embed.add_field(
                    name=f"{START_TIME} Started at",
                    value=f"{discord.utils.format_dt(start_time, 'R')}\n({discord.utils.format_dt(start_time, 'f')})",
                    inline=True,
                )

                embed.add_field(
                    name=f"{END_TIME} Ends at",
                    value=f"{discord.utils.format_dt(end_time, 'R')}\n({discord.utils.format_dt(end_time, 'f')})",
                    inline=True,
                )

                embed.add_field(name=f"{HOST} Host", value=actor.mention, inline=True)
                embed.add_field(name=f"{CROWN} Winner Count", value=str(winner_count), inline=True)

                embed.set_image(url=actor.display_avatar.url)
                embed.set_footer(text="Giveaway Log")

                view = discord.ui.View()
                view.add_item(
                    discord.ui.Button(
                        label="Jump to Giveaway",
                        url=giveaway_message.jump_url,
                        style=discord.ButtonStyle.link,
                    )
                )

                await log_channel.send(embed=embed, view=view)

        except Exception as e:
            print(f"[LOGGING ERROR] Failed to log giveaway: {e}")


async def setup(bot):
    await bot.add_cog(GiveawayLogger(bot))
    pass
