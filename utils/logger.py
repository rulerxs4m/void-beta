import logging
from . import formatter

def logger(name) -> logging.Logger:
    handler = logging.FileHandler("discord_bot.log")
    handler.setFormatter(formatter.LogFormatter(name))
    handler.setLevel(1)
    logger = logging.getLogger(name)
    logger.setLevel(1)
    logger.addHandler(handler)
    return logger