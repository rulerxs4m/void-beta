from discord.ext import commands as cmds

class Command(cmds.Command):
    def __init__(self, func, /, **kwargs):
        super().__init__(func, **kwargs)
        _param_desc = getattr(func, "__discord_commands_param_description__", {})
        for name, param in self.params.items():
            param._description = _param_desc.get(name, param._description or "...")
        _param_names = getattr(func, "__discord_commands_param_names__", {})
        for name, param in self.params.items():
            param._displayed_name = _param_names.get(name, param.name)

class Group(cmds.Group):
    def __init__(self, func, /, **kwargs):
        super().__init__(func, **kwargs)
        _param_desc = getattr(func, "__discord_commands_param_description__", {})
        for name, param in self.params.items():
            param._description = _param_desc.get(name, param._description or "...")
        _param_names = getattr(func, "__discord_commands_param_names__", {})
        for name, param in self.params.items():
            param._displayed_name = _param_names.get(name, param.name)

    def command(self, name: str = None, *args, **kwargs):
        def decorator(func):
            cls = kwargs.pop("cls", Command)
            return super(cmds.Group, self).command(name=name, cls=cls, *args, **kwargs)(func)
        return decorator

    def group(self, name: str = None, *args, **kwargs):
        def decorator(func):
            cls = kwargs.pop("cls", Group)
            return super(cmds.Group, self).group(name=name, cls=cls, *args, **kwargs)(func)
        return decorator