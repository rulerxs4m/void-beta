from utils import Bot, Context, color
from utils import utility as util
from utils import ghost_url, embed_color, empty_char

import io
from typing import Union
from PIL import Image, ImageDraw, ImageFont

import discord
from discord import ui
from discord.ext import tasks
from discord.ext import commands as cmds


async def generate_welcome_image(member):
    x, ava = 4, await member.display_avatar.to_file()
    image = Image.open("assets/imgs/space-1.jpg").resize((480*x, 120*x))
    draw = ImageDraw.Draw(image)
    draw.line(
        [
            ( 100 * x, 0 * x ),
            ( 120 * x, 60 * x),
            ( 100 * x, 120 * x )
        ],
        width = 15 * x,
        fill = "cyan",
        joint = "curve"
    )
    draw.text(
        ( 150 * x, 20 * x ),
        "WELCOME!",
        font = ImageFont.truetype(
            "assets/fonts/philosopher/bold-italic.ttf",
            size = 55*x
        ), fill = ( 255, 255, 255 )
    )
    draw.text(
        ( 157 * x, 75 * x ),
        member.display_name,
        font = ImageFont.truetype(
            "assets/fonts/philosopher/bold-italic.ttf",
            size = 25*x
        ), fill = ( 255, 255, 255 )
    )
    pfp = Image.open(ava.fp).resize(( 120 * x, 120 * x ))
    mask = Image.new("L", pfp.size, 0)
    draw_mask = ImageDraw.Draw(mask)
    draw_mask.polygon([
        ( 0 * x, 0 * x ),
        ( 100 * x, 0 * x ),
        ( 120 * x, 60 * x ),
        ( 100 * x, 120 * x ),
        ( 0 * x, 120 * x )
    ], fill=255)
    pfp.putalpha(mask)
    pfp_layer = Image.new('RGBA', image.size, (0,0,0,0))
    pfp_layer.paste(pfp, (0,0))
    result_image = Image.composite(pfp_layer, image, pfp_layer)
    with io.BytesIO() as fp:
        result_image.save(fp, format="JPEG"); fp.seek(0)
        return discord.File(fp, filename="welcome.jpg")
    
class welcome_cog(cmds.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @cmds.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.bot: return
        w_settings = self.bot.db.guild.welcomer.fetchone((member.guild.id, False))
        if not w_settings: return
        await member.guild.get_channel(w_settings.channel).send(
            w_settings.message.format_map({
                "MENTION": member,
                "NAME": member.display_name,
                "USERNAME": member.name,
                "SERVER_NAME": member.guild.name
            }),
            file = await generate_welcome_image(member),
            delete_after = w_settings.delete_after or None
        )

    @util.command(name="welcome", description="Welcome a new member with a welcome card")
    @util.describe(member="The member to welcome")
    async def welcome_cmd(self, ctx: Context, member: discord.Member):
        await ctx.message.delete()
        await ctx.send(
            f"**Welcome {member.mention} !!!** :tada: :tada:\n-# By: {ctx.author.mention}", 
            file = await generate_welcome_image(member)
        )

async def setup(bot: Bot):
    await bot.add_cog(welcome_cog(bot))