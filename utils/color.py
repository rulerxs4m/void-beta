from enum import Enum

class type:
    normal = "0;"
    bold = "1;"
    underline = "4;"

class fg:
    gray = "30m"
    grey = gray
    red = "31m"
    green = "32m"
    yellow = "33m"
    blue = "34m"
    pink = "35m"
    cyan = "36m"
    white = "37m"

class bg:
    dark_blue = "40;"
    orange = "41;"
    marble_blue = "42;"
    greyish_turq = "43;"
    grayish_turq = greyish_turq
    grey = "44;"
    gray = grey
    indigo = "45;"
    light_gray = "46;"
    light_grey = light_gray
    white = "47;"

def ansi(text:str, format:str="", fg:str="", bg:str="", ansi:bool=True) -> str: # type: ignore
    return f"```ansi\n\u001b[{format}{bg}{fg}{text}\u001b[0;0m\n```" if ansi else f"\u001b[{format}{bg}{fg}{text}\u001b[0;0m"

def color(text:str, rgb:tuple[int, int, int]=None, format:str="") -> str: # type: ignore
    if rgb is None: return f"\u001b[{format[:-1]}m{text}\u001b[0;0m"
    return f"\u001b[{format}38;2;{rgb[0]};{rgb[1]};{rgb[2]}m{text}\u001b[0;0m"