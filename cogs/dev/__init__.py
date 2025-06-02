import os, sys

from utils import (
    color,
    ghost_url,
    embed_color,
    Bot, Context,
    utility as util
)

import discord
from discord.ext import commands as cmds

class style:
    class component:
        def __init__(self, **kwargs) -> None:
            for var, value in kwargs.items():
                self.__setattr__(var, value)
    def __init__(self, fmt: str) -> None:
        self.sep = style.component(
            rows=fmt[0], col=fmt[1],
            up=fmt[2], down=fmt[3],
            left=fmt[4], right=fmt[5],
            fields=fmt[6], f_rows=fmt[7]
        )
        self.bor = style.component(ver=fmt[8], hor=fmt[9])
        self.cor = style.component(
            tl=fmt[10], tr=fmt[11],
            bl=fmt[12], br=fmt[13]
        )

formats = [
    style("─│┬┴├┤│┼│─┌┐└┘"),
    style("─│╤╧╟╢│┼║═╔╗╚╝"),
    style("═║╦╩╠╣║╬║═╔╗╚╝"),
]

def format_table(output, f, description):
    fields_max = [len(max(x, key=len)) for x in [[description[i]] + [str(output[j][i]) for j in range(len(output))] for i in range(len(description))]]
    return (
        f"{(f.cor.tl + f.sep.up.join(f.bor.hor*(fields_max[index]+2) for index in range(len(description))) + f.cor.tr)}\n"
        f"{(f.bor.ver+ f.sep.fields.join(str(value).center(fields_max[index]+2) for index, value in enumerate(description)) + f.bor.ver)}\n"
        f"{(f.sep.left + f.sep.f_rows.join(f.sep.rows*(fields_max[index]+2) for index in range(len(description))) + f.sep.right)}\n"
        f"{('\n'.join((f.bor.ver + f.sep.col.join(str(value).center(fields_max[index]+2) for index, value in enumerate(row)) + f.bor.ver) for row in output))}\n"
        f"{(f.cor.bl + f.sep.down.join(f.bor.hor*(fields_max[index]+2) for index in range(len(description))) + f.cor.br)}"
    )

class dev_cog(cmds.Cog):
    def __init__(self, bot: Bot):
        super().__init__()
        self.bot: Bot = bot

    @cmds.command(name="exec")
    @cmds.is_owner()
    async def exec_code(self, ctx: cmds.Context, *, code: str):
        try:
            exec_globals = {
                '__name__': '__main__',
                '__file__': 'exec_code',
                'ctx': ctx,
                'bot': self.bot,
                'discord': discord,
                'os': os
            }
            exec_code = f"async def __exec_code():\n{'\n'.join(f'    {line}' for line in code.strip().splitlines())}"
            exec(exec_code, exec_globals)
            result = await exec_globals['__exec_code']()
            if result is not None: await ctx.send(f"Result: ```{result}```")
            await ctx.message.add_reaction(discord.PartialEmoji.from_str(self.bot.emoji.tick))
        except Exception as e:
            await ctx.send(f"Error: {color.ansi(e, fg=color.fg.red)}")

    @cmds.command(name="db")
    @cmds.is_owner()
    async def exec_db(self, ctx: cmds.Context, *, command: str):
        try:
            self.bot.db.cursor.execute(command)
            result = self.bot.db.cursor.fetchall()
            if result: await ctx.send(f"Result: ```\n{format_table(result, formats[1], [x[0] for x in self.bot.db.cursor.description])}\n```")
            await ctx.message.add_reaction(discord.PartialEmoji.from_str(self.bot.emoji.tick))
        except Exception as e:
            await ctx.send(f"Error: {color.ansi(e, fg=color.fg.red)}")

    @cmds.command(name="line_count")
    @cmds.is_owner()
    async def line_count(self, ctx: Context):
        line_count = 0
        EXCLUDE = {"__pycache__", ".git", ".local", ".config", ".cache", ".venv"}
        for dirpath, _, filenames in os.walk("."):
            for file in filenames:
                if any(x in file for x in EXCLUDE): continue
                if not file.endswith(".py"): continue
                full_path = os.path.join(dirpath, file)
                try:
                    with open(full_path, "r", encoding="utf-8") as fp:
                        for line in fp:
                            stripped = line.strip()
                            if not stripped or stripped.startswith("#"):
                                continue
                            line_count += 1
                except Exception as e:
                    print(f"Failed to read {full_path}: {e}")
        await ctx.reply(f"**Line Count:** {line_count:,}")

    @cmds.command(name="pull")
    @cmds.is_owner()
    async def git_pull(self, ctx: Context):
        await ctx.reply(f"```{os.popen("git pull").read()}```")

    # @cmds.command(name="reboot")
    # @cmds.is_owner()
    async def reboot(self, ctx: cmds.Context, *, reason: str = "No reason"):
        await self.bot.change_presence(status=discord.Status.dnd, activity=discord.CustomActivity("Rebooting ..."))
        await ctx.reply(os.popen("git pull").read())
        os.execv(sys.executable, [sys.executable] + sys.argv)

async def setup(bot: Bot):
    await bot.add_cog(dev_cog(bot))

    for sub_cog in os.listdir(os.path.dirname(__file__)):
        if sub_cog in ["__init__.py", "__pycache__"]: continue
        name = sub_cog.split(".")[0]
        await bot.load_extension(f"{__name__}.{name}")
        bot._all_cogs.add(f"{__name__}.{name}")

async def teardown(bot: Bot):
    for sub_cog in os.listdir(os.path.dirname(__file__)):
        if sub_cog in ["__init__.py", "__pycache__"]: continue
        name = sub_cog.split(".")[0]
        await bot.unload_extension(f"{__name__}.{name}")