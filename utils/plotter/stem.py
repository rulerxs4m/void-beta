import datetime
import io
import numpy as np
from matplotlib import pyplot as plt
import matplotlib.ticker as ticker

import discord

import math, re
from discord.ext import commands as cmds
class Amount(cmds.Converter[int]):
    SUFFIXES = {
        "k": 1_000, "thousand": 1_000, "m": 1_000_000, "mil": 1_000_000, "million": 1_000_000,
        "b": 1_000_000_000, "bil": 1_000_000_000, "billion": 1_000_000_000, 
        "t": 1_000_000_000_000, "tril": 1_000_000_000_000, "trillion": 1_000_000_000_000
    }
    FORMAT_SUFFIXES = [(1_000_000_000_000, "T"), (1_000_000_000, "B"), (1_000_000, "M"), (1_000, "K")]
    CLEAN_TRAILING = re.compile(r'[^\w\d]+$')
    NUMBER_PATTERN = re.compile(r"^([\d,]+(?:\.\d+)?)([a-z]*)$", re.IGNORECASE)

    @staticmethod
    def format_2(amount: int, pos=None) -> str:
        for threshold, suffix in Amount.FORMAT_SUFFIXES:
            if amount >= threshold:
                truncated = amount / threshold
                formatted = f"{truncated:.2f}".rstrip('0').rstrip('.')
                return f"{formatted}{suffix}"
        return str(amount)


def datewise_plotter(dates: list[datetime.date], values: list[int], *, max_xticks: int = 15, filename: str = "plot.png"):

    x = np.arange(len(dates))
    y = np.array(values)

    fig = plt.figure(figsize=(10, 5))
    fig.patch.set_facecolor("black")

    # Stem plot
    markerline, stemlines, baseline = plt.stem(x, y, basefmt=" ")
    plt.setp(markerline, color="white", markerfacecolor="white", markersize=13)
    plt.setp(stemlines, color="white", linewidth=5)
    plt.grid(True)

    # Annotate stem tips
    for x_val, y_val in zip(x, y):
        plt.text(
            x_val, y_val + max(y) * 0.05,
            Amount.format_2(y_val),
            color="white",
            fontsize=12,
            fontweight="bold",
            ha='center',
            bbox=dict(
                facecolor='black',
                alpha=0.6,
                boxstyle='round,pad=0.2'
            )
        )

    ax = plt.gca()
    ax.set_facecolor("black")
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_ylim(0, max(y) * 1.15)
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(Amount.format_2))

    # X-ticks trimming logic
    n = len(x)
    if n > max_xticks:
        step = max(1, n // max_xticks)
        display_ticks = x[::step]
        display_labels = dates[::step]
    else:
        display_ticks = x
        display_labels = dates

    plt.xticks(
        ticks=display_ticks,
        labels=[d.strftime("%d %b %y") for d in display_labels],
        rotation=45,
        color="white",
        fontsize=16,
        ha="center"
    )
    plt.yticks(color="white", fontsize=14)
    plt.tight_layout()

    with io.BytesIO() as fp:
        plt.savefig(fp, format="png")
        plt.close()
        fp.seek(0)
        return discord.File(fp, filename=filename)
