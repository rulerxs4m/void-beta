import os
import sys
import json
import flask
import logging
import asyncio
import requests
from threading import Thread
from ansi2html import Ansi2HTMLConverter

import utils
import utils.formatter
from utils import Bot
from utils import color
from utils import ghost_url
from utils import embed_color
from utils import utility as util
from utils.database import structs

import discord
from discord.ext import commands as cmds
from discord.ext import tasks
from discord.ext.commands import errors
from discord import app_commands as acmds

DEBUG = "--no-debug" not in sys.argv
FLASK_PORT = int(os.getenv("SERVER_PORT", 8080))

if DEBUG:
    TOKEN = "MTM2NDQ5MjI2NTY2NTQ2NjM5OQ.GtNXSW.Y3B-SfwG8gSRGsRiNXry_IF23fE6b0rYtVkGsc"  # The Void (Beta Tester)
else:
    with open(".bot_token", "r") as fp:
        TOKEN = fp.read()  # Actual Bot

bot: Bot = Bot(
    command_prefix = cmds.when_mentioned_or("?" if not DEBUG else "s-"),
    case_insensitive=True,
    debug=DEBUG,
    help_command=None,
    intents=discord.Intents.all(),
    database=utils.database.db(DEBUG),
    logs_channel_id=1189430261709013083,  # bot-logs (HtBPh)
    logger=utils.logger("Some Bot"),
    made_by="Ghost & Devils",
    owner_ids=[
        889384139134992425,  # Dark Devil
        904983826567139349,  # The Visible Ghost
        930323226771480627,  # Spig
        782838631626440734   # Sam
    ],
    owner_guilds=[
        discord.Object(id=925666996505415680),  # HtBPh
        discord.Object(id=854238372464820224),  # The Jedi
    ],
    status=discord.Status.idle,
    activity=discord.CustomActivity(name="Transcending Space-Time"),
    runner=dict(
        token=TOKEN,
        reconnect=True,
        log_handler=logging.StreamHandler(),
        log_formatter=utils.formatter.LogFormatter2("Some Bot"),
        log_level=11,
        root_logger=False
    ),
    logs_url="http://" + requests.get("https://api.ipify.org").text + f":{FLASK_PORT}/logs",
    ignore_errors=(
        errors.CommandNotFound,
    ),
    show_errors=(
        errors.CheckFailure,
        errors.MissingPermissions,
        errors.BotMissingPermissions,
        errors.ConversionError,
        errors.UserInputError,
        errors.CommandOnCooldown,
        errors.DisabledCommand,
    )
)

# === Import your cogs manually here ===
async def load_cogs():
    try:
        await bot.load_extension("cogs.dank.donations")
        await bot.load_extension("cogs.translator-cog")
        await bot.load_extension("cogs.afk")
        await bot.load_extension("cogs.random")
        await bot.load_extension("cogs.dank.auto_dono_roles")
        print("Cogs loaded successfully.")
    except Exception as e:
        print(f"Error loading cogs: {e}")
        await load_cogs()

slash = bot.slash

@bot.event
async def on_message(msg: discord.Message):
    if msg.author.bot:
        return
    await bot.process_commands(msg)

@bot.event
async def on_guild_join(guild: discord.Guild):
    with open("blacklist.json", "r") as fp:
        blacklist: dict = json.load(fp)

    if str(guild.id) in blacklist["guilds"]:
        reason = blacklist["guilds"][str(guild.id)]
        embed = discord.Embed(
            title=f"{bot.emoji.x_mark} Blacklisted Server",
            description=f"**By:** `{reason['by']}`\n**Reason:** ```{reason['reason']}```",
            color=discord.Color.red()
        )
        embed.set_author(name=guild.name, icon_url=guild.icon.url if guild.icon else None)
        embed.set_footer(text="Contact bot owners to appeal this blacklist.")
        embed.set_thumbnail(url=bot.user.display_avatar.url)

        channel_name = reason.get("channel", "general")
        channels = [x for x in guild.text_channels if channel_name in x.name]
        for channel in channels:
            try:
                await channel.send(embed=embed)
            except:
                pass
            await asyncio.sleep(1)

        embed2 = discord.Embed(
            title="Left Blacklisted Server",
            description=(
                f"**Server Name:** `{guild.name}`\n"
                f"**Owner:** `{guild.owner}` (`{guild.owner_id}`)\n"
                f"**Members:** `{guild.member_count}`\n"
                f"**Created At:** <t:{int(guild.created_at.timestamp())}:R> (<t:{int(guild.created_at.timestamp())}:f>)\n"
            ),
            color=discord.Color.red()
        )
        embed2.set_author(name=guild.name, icon_url=guild.icon.url if guild.icon else ghost_url)
        embed2.set_thumbnail(url=guild.icon.url if guild.icon else ghost_url)
        embed2.set_footer(text=f"Server ID: {guild.id}")
        try:
            async for entry in guild.audit_logs(action=discord.AuditLogAction.bot_add, limit=10):
                if entry.target.id == bot.user.id:
                    embed2.description += f"**Invited By:** `{entry.user}` (`{entry.user.id}`)\n"
                    break
        except:
            pass

        embed2.description += (
            f"**Blacklisted By:** `{reason['by']}`\n"
            f"**Blacklist Reason:** ```{reason['reason']}```\n"
        )
        await bot.logs_channel.send(embed=embed2)
        await guild.leave()

@bot.command()
@cmds.is_owner()
async def clear_logs(ctx: cmds.Context):
    with open("discord_bot.log", "w") as fp:
        fp.write("")
    bot.logger.info(f"User: {color.color(ctx.author, (0, 255, 0))} ({color.color(ctx.author.id, (255, 255, 0))}) | Logs Cleared.")
    await ctx.reply(f"{bot.emoji.tick} Logs Cleared.")

@bot.event
async def on_command_error(ctx: cmds.Context, error: discord.DiscordException):
    if isinstance(error, bot.ignored_errors):
        return

    if isinstance(error, bot.shown_errors):
        embed = discord.Embed(
            title=f"{bot.emoji.x_mark} Uh-oh! An Error Occurred {bot.emoji.x_mark}",
            description=color.ansi(str(error), fg=color.fg.red),
            color=0xFF0000
        )
        if ctx.command:
            embed.add_field(name="Syntax", value=util.generate_command_syntax(ctx.command))
        embed.set_author(name=bot.user.display_name, icon_url=bot.user.display_avatar.url)
        embed.set_footer(
            text="If you think this is unexpected, please report it using .report",
            icon_url=bot.user.display_avatar.url
        )
        await ctx.reply(embed=embed)

    bot.logger.error(
        f"Command: {color.color(ctx.command.name if ctx.command else ctx.message.content.split()[0], (0, 255, 255))} | "
        f"Guild: {color.color(ctx.guild, (0, 255, 0))} ({color.color(ctx.guild.id if ctx.guild else None, (255, 255, 0))}) | "
        f"User: {color.color(ctx.author, (0, 255, 0))} ({color.color(ctx.author.id, (255, 255, 0))}) | "
        f"Exception: {color.color(str(error), (255, 0, 0))}"
    )

    if DEBUG:
        raise error

# Setup Flask log viewer
app = flask.Flask(__name__, template_folder="html")
if not DEBUG:
    logging.getLogger('werkzeug').setLevel(31)
    logging.getLogger('flask.app').setLevel(31)

conv = Ansi2HTMLConverter()

@app.route("/logs")
def web_logs():
    with open("discord_bot.log", "r") as fp:
        bot._log.info(f"Logs viewed by: {color.color(flask.request.remote_addr, (0, 0, 255), color.type.underline)}")
        bot.logger.info(f"Logs viewed by: {color.color(flask.request.remote_addr, (0, 0, 255), color.type.underline)}")
        return flask.render_template("log_viewer.html", logs=conv.convert(fp.read(), full=True), name=bot.name)

Thread(target=app.run, kwargs=dict(host="0.0.0.0", port=FLASK_PORT, use_reloader=False), daemon=True).start()

# Run bot
bot.run(
    token=bot.runner["token"],
    reconnect=bot.runner["reconnect"],
    log_handler=bot.runner["log_handler"],
    log_formatter=bot.runner["log_formatter"],
    log_level=bot.runner["log_level"],
    root_logger=bot.runner["root_logger"]
)
