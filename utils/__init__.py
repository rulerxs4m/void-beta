import os
import pytz
import emojis
import logging
import datetime
from typing import List, Set

import discord
from discord.ext import commands as cmds

from utils.database import structs

from .logger import logger
from . import color
from . import formatter
from . import database
from . import redef
from . import utility
# from . import pager
from . import embeds

ghost_url = "https://media.discordapp.net/attachments/1120678105971957790/1129029032806187098/ghost.gif?size=2048?quality=lossless"
embed_color = 0x010101
empty_char = chr(173)

class emoji:
    warning = emojis.encode(":warning:")
    construction = emojis.encode(":construction:")
    link = emojis.encode(":link:")
    lock = emojis.encode(":lock:")
    tada = emojis.encode(":tada:")
    mega = emojis.encode(":mega:")
    first = emojis.encode(":rewind:")
    prev = emojis.encode(":arrow_left:")
    next = emojis.encode(":arrow_right:")
    last = emojis.encode(":fast_forward:")
    def encode(string:str):
        return emojis.encode(string)

class beta_emoji(emoji):
    tick = "<:tick:1364540875371315273>"
    x_mark = "<:x_mark:1364540852847775764>"
    txt = "<:txt:1364540895302651904>"
    bdot = "<:bdot:1370401822849765516>"
    commands = "<:commands:1364541014588784691>"

class prod_emoji(emoji):
    tick = "<:tick:1363902366201413873>"
    x_mark = "<:x_mark:1363902399978148073>"
    none = "<:none:1363902435818733700>"
    mem = "<:mem:1363902498410074284>"
    txt = "<:txt:1363902522766655599>"
    vc = "<:vc:1363902552311070871>"
    mod = "<:mod:1363902592115150879>"
    commands = "<:commands:1363902702467416245>"

async def react(msg: discord.Message, emoji: str):
    try: await msg.add_reaction(discord.PartialEmoji.from_str(emoji))
    except: pass

class Bot(cmds.AutoShardedBot):
    def __init__(self, **kwargs):
        self.name = kwargs.pop("name", "Some Bot")
        self.logs_url = kwargs.pop("logs_url", "[coming soon]")
        self.logger: logging.Logger = kwargs.pop("logger", logging.root)

        self.runner: dict = kwargs.pop("runner")
        self.made_by: str = kwargs.pop("made_by")

        self.logs_channel_id: list[int] = kwargs.pop("logs_channel_id")
        self.owner_guilds: list[discord.Object] = kwargs.pop("owner_guilds", [])

        self.ignored_errors: tuple[discord.DiscordException] = kwargs.pop("ignore_errors", [])
        self.shown_errors: tuple[discord.DiscordException]  = kwargs.pop("show_errors", [])

        self._db: database.db = kwargs.pop("database", None)
        self._cogs: Set[str] = kwargs.pop("cogs", set())
        self._all_cogs: Set[str] = set(self._cogs)
        self.DEBUG = kwargs.pop("debug", False)

        self.db = database.db = None

        if self.DEBUG: self.emoji = beta_emoji()
        else: self.emoji = prod_emoji()

        _hand = logging.StreamHandler()
        _hand.setFormatter(formatter.LogFormatter2(self.name))
        self._log = logging.getLogger(f"{self.name} - info")
        self._log.setLevel(11)
        self._log.addHandler(_hand)

        super().__init__(**kwargs)

    @property
    def owner(self):
        return self.get_user(self.owner_ids[0])

    def slash(self, **kwargs):
        if "extras" not in kwargs: kwargs["extras"] = {}
        kwargs["extras"]["category"] = kwargs.pop("category", "general")
        return self.tree.command(**kwargs)

    async def setup_hook(self):
        if self._db: self.db: database.db = self._db
        if self.DEBUG: await self.load_extension("cogs.dev")
        else:
            for ext in self._cogs: await self.load_extension(ext)
            for cc in set([
                f"custom_cogs.{srvr_id}"
                for srvr_id in os.listdir("custom_cogs")
                if srvr_id not in ["__pycache__", "__init__.py"]
                and not srvr_id.endswith(".off")
            ]): await self.load_extension(cc)

    async def on_ready(self):
        self.logs_channel = await self.fetch_channel(self.logs_channel_id)
        self.logger.info(
            f"Login: {color.color(self.user, (0, 255, 0))} ({color.color(self.user.id, (255, 255, 0))})"
            f" | {color.color('Bot Started', format=color.type.bold)}"
        )
        self._log.info(
            f"Login: {color.color(self.user, (0, 255, 0))} ({color.color(self.user.id, (255, 255, 0))})"
            f"\n\t| You can see bot logs at: {color.color(self.logs_url, (0, 0, 255), color.type.underline)}"
            f"\n\t| {color.color('Bot Started', format=color.type.bold)}" + (" | DEBUG MODE" if self.DEBUG else "")
        )

    def command(self, name: str = None, *args, **kwargs):
        def decorator(func):
            kwargs.setdefault("parent", self)
            cls = kwargs.pop("cls", redef.Command)
            result = cmds.command(name=name, cls=cls, *args, **kwargs)(func)
            self.add_command(result)
            return result
        return decorator
    
    async def get_prefix(self, msg: discord.Message) -> List[str]:
        if msg.guild is None:
            return self.command_prefix(self, msg)
        custom_prefixes = []
        custom_guild_prefixes: structs.guild_prefixes = self.db.guild.prefixes.fetchone(msg.guild.id)
        custom_user_prefixes: structs.user_prefixes = self.db.user.prefixes.fetchone(msg.author.id)
        if custom_guild_prefixes: custom_prefixes += custom_guild_prefixes.pref
        if custom_user_prefixes: custom_prefixes += custom_user_prefixes.pref
        return self.command_prefix(self, msg) + list(set(custom_prefixes))
    
    async def load_extension(self, name, *, package = None):
        if self.DEBUG: self._log.info(f"Loaded: {package if package else ''}{name}")
        return await super().load_extension(name, package=package)
    
    async def unload_extension(self, name, *, package = None):
        if self.DEBUG: self._log.info(f"Unloaded: {package if package else ''}{name}")
        return await super().unload_extension(name, package=package)
    
class Context(cmds.Context):
    bot: Bot