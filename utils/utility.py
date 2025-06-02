from typing import Union
import discord
from discord.ext import commands as cmds

from utils import color

from . import redef

def generate_command_syntax(cmd: cmds.Command) -> str:
    return "```ansi\n" + f".{color.ansi(cmd.qualified_name, color.type.bold, color.fg.cyan, ansi=False)} " + " ".join([
        ( color.ansi(f"<{param.displayed_name if param.displayed_name else param.name}>", fg=color.fg.yellow, ansi=False) if param.required else color.ansi(f"[{param.displayed_name if param.displayed_name else param.name}]", fg=color.fg.gray, ansi=False) )
        for _, param in cmd.clean_params.items()
    ]) + "\n```"

def underdevelopment():
    def predicate(ctx):
        if ctx.author.id not in ctx.bot.owner_ids:
            return ctx.send(f"{ctx.bot.emoji.construction} | This command is under development.")
        return True
    return cmds.check(predicate)

def describe(**parameters: Union[str, str]):
    def decorator(inner):
        if isinstance(inner, cmds.Command):
            # _populate_descriptions
            for name, param in inner.params.items():
                description = parameters.pop(name, "...")
                if not isinstance(description, str):
                    raise TypeError("description must be a string")
                if isinstance(description, str):
                    param.description = discord.utils._shorten(description)
                else:
                    param.description = description
            if parameters:
                first = next(iter(parameters))
                raise TypeError(f"unknown parameter given: {first}")
        else:
            try: 
                inner.__discord_commands_param_description__.update(parameters)
            except AttributeError:
                inner.__discord_commands_param_description__ = parameters
        return inner
    return decorator

def rename(**parameters: Union[str, str]):
    def decorator(inner):
        if isinstance(inner, cmds.Command):
            # _populate_displayed_names
            for name, param in inner.params.items():
                displayed_name = parameters.pop(name, "...")
                if not isinstance(displayed_name, str):
                    raise TypeError("displayed_name must be a string")
                if isinstance(displayed_name, str):
                    param.displayed_name = discord.utils._shorten(displayed_name)
                else:
                    param.displayed_name = displayed_name
            if parameters:
                first = next(iter(parameters))
                raise TypeError(f"unknown parameter given: {first}")
        else:
            try: 
                inner.__discord_commands_param_displayed_name__.update(parameters)
            except AttributeError:
                inner.__discord_commands_param_displayed_name__ = parameters
        return inner
    return decorator

def command(name: str = None, *args, **kwargs):
    def decorator(func):
        cls = kwargs.pop("cls", redef.Command)
        return cmds.command(name=name, cls=cls, *args, **kwargs)(func)
    return decorator

def group(name: str = None, *args, **kwargs):
    def decorator(func):
        cls = kwargs.pop("cls", redef.Group)
        return cmds.group(name=name, cls=cls, *args, **kwargs)(func)
    return decorator