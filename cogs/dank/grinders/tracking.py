import datetime
from utils import Bot, color
from utils import utility as util
from utils import ghost_url, embed_color, empty_char

import discord
from discord import ui
from discord.ext import tasks
from discord.ext import commands as cmds
from discord import Interaction, app_commands as acmds
from discord import RawMessageUpdateEvent

from .. import dank_id, coin

class dank_grinder_tracking(cmds.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.manage.start()

    async def cog_unload(self):
        self.manage.cancel()
        return await super().cog_unload()
    
    @cmds.Cog.listener()
    async def on_raw_message_edit(self, event: RawMessageUpdateEvent):
        msg = event.message
        if msg.application_id != dank_id: return
        if not msg.interaction_metadata: return
        if msg.interaction_metadata.type != discord.InteractionType.application_command: return
        
        # if msg.interaction.name != "serverevents donate": return # deprecated
        # if msg.interaction_metadata.user.id not in self.bot.owner_ids: return

        if "components" not in event.data: return
        if len(event.data["components"]) == 0: return
        if "components" not in event.data["components"][0]: return
        if len(event.data["components"][0]["components"]) == 0: return
        if "content" not in event.data["components"][0]["components"][0]: return
        donated = discord.utils.remove_markdown(event.data["components"][0]["components"][0]["content"])
        if not donated.startswith("Successfully donated"): return
        g_settings = self.bot.db.dank.grinder_settings.fetchone(event.guild_id)
        if not g_settings: return
        if event.channel_id != g_settings.pay_channel: return
        amount = int(donated[23:].replace(",", ""))
        donator = msg.guild.get_member(msg.interaction_metadata.user.id)
        grinder = self.bot.db.dank.grinder.fetchone((event.guild_id, donator.id))
        if not grinder: return
        if grinder.blacklisted: return
        tier = self.bot.db.dank.grinder_tiers.fetchone((event.guild_id, grinder.tier))
        g_log_channel = msg.guild.get_channel(g_settings.log_channel)
        if not g_log_channel:
            try: g_log_channel = await msg.guild.fetch_channel(g_settings.log_channel)
            except: return
        pay_days = int(amount / tier.amount)
        grinder.next_pay += int((amount / tier.amount) * 24 * 60 * 60)
        grinder.total_paid += amount
        if grinder.trial and grinder.total_paid >= (tier.amount * 7):
            grinder.trial = False
            await donator.add_roles(
                discord.Object(grinder.tier, type=discord.Role),
                discord.Object(g_settings.paid_role, type=discord.Role),
                reason = "Accepted grinder", atomic=True
            )
            await donator.remove_roles(
                discord.Object(g_settings.trial_role, type=discord.Role),
                reason = "Accepted grinder", atomic=True
            )
            ee = discord.Embed(
                title = "Congratulations !!! :tada: :tada:",
                description = "You are now an accpeted grinder.",
                color = embed_color,
                timestamp = datetime.datetime.now()
            )
            ee.add_field(
                name = "Payments:",
                value = (
                    f"**Daily:** {coin} {tier.amount:,}\n"
                    f"**Weekly:** {coin} {(tier.amount*7):,}\n"
                    f"-# (You can pay for any number of days)"
                )
            )
            ee.set_footer(text=msg.guild.name, icon_url=msg.guild.icon.url if msg.guild.icon else None)
            ee.set_author(name=donator.name, icon_url=donator.display_avatar.url)
            dmed = False
            try:
                dm = await donator.create_dm()
                await dm.send(embed=ee)
                dmed = True
            except: dmed = False
            e = discord.Embed(
                title = "Accepted Grinder",
                description = (
                    f"{donator.mention} has been accpeted as a grinder.\n" +
                    (f"{self.bot.emoji.warning} | Unable to DM {donator.mention} (`{donator.name}`)" if not dmed else "")
                ),
                timestamp = datetime.datetime.now(),
                color = embed_color
            )
            e.set_footer(text="Auto-accept")
            e.set_author(name=donator.display_name, icon_url=donator.display_avatar.url)
            await msg.guild.get_channel(g_settings.log_channel).send(embed=e)
        self.bot.db.dank.grinder.update_record(grinder)
        embed = discord.Embed(
            title = "Amount Added",
            timestamp = datetime.datetime.now(),
            color = embed_color
        )
        embed.set_author(name=donator.display_name, icon_url=donator.display_avatar.url)
        embed.set_footer(text=msg.guild.name, icon_url=msg.guild.icon.url if msg.guild.icon else None)
        embed.set_thumbnail(url=donator.display_avatar.url)
        embed.add_field(name="Paid for", value=f"{pay_days} day{'s' if pay_days > 1 else ''}")
        embed.add_field(name="Amount", value=f"{coin} {amount:,}")
        embed.add_field(name="Credited to", value=donator.mention)
        button = ui.Button(url=msg.jump_url, label="Jump to message")
        view = ui.View(timeout=1); view.add_item(button)
        await g_log_channel.send(embed=embed, view=view)
        await msg.reply(f"{self.bot.emoji.tick} | {donator.mention} your pay {coin} {amount:,} has been logged.")

    @tasks.loop(
        # count = 1
        time=datetime.time(12, 0) # UTC midday
    )
    async def manage(self):
        current_time = int(datetime.datetime.now().timestamp())
        self.bot.db.cursor.execute(f"SELECT * FROM dank_grinder WHERE next_pay <= {current_time} AND blacklisted == 0")
        for row in self.bot.db.cursor.fetchall():
            grinder = self.bot.db.dank.grinder.parse(row)
            tier = self.bot.db.dank.grinder_tiers.fetchone((grinder.gid, grinder.tier))
            g_settings = self.bot.db.dank.grinder_settings.fetchone(grinder.gid)
            guild = self.bot.get_guild(grinder.gid)
            due_days = int((current_time - grinder.next_pay) / (60 * 60 * 24))
            embed = discord.Embed(
                title = "Grinder Reminder",
                color = embed_color,
                timestamp = datetime.datetime.now(),
                description = (
                    f"Your __**Grinder Payments**__ are pending for  **{due_days} day{'s' if due_days > 1 else ''}**\n"
                    f"Make sure to inform staff if you have any trouble with the donations.\n"
                    f"**Amount due:** {coin} {(due_days * tier.amount):,}\n"
                )
            )
            embed.set_footer(text=guild.name, icon_url=guild.icon.url if guild.icon else None)
            user = guild.get_member(grinder.uid)
            if not user:
                await guild.get_channel(g_settings.log_channel).send(f"{self.bot.emoji.x_mark} | `{grinder.uid}` not found, might have left the server.")
                continue
            embed.set_author(name=user.global_name, icon_url=user.display_avatar.url)
            button = ui.Button(
                label = "Pay Here",
                url=f"https://discord.com/channels/{grinder.gid}/{g_settings.pay_channel}",
                emoji=self.bot.emoji.txt
            )
            view = ui.View(timeout=1); view.add_item(button)
            if due_days < 1: continue
            elif due_days < 4:
                if grinder.trial:
                    if due_days > 2:
                        embed.title = "Kicked from Trial Grinders"
                        embed.description = (
                            "**Sadly you have been kicked from the grinders.**\n"
                            "**Reason:** You didnt pay your advance payment for 3 days\n"
                            f"At the time of dismiss you have: {coin} {grinder.total_paid:,}\n"
                        )
                        embed.set_footer(text=embed.footer.text + f" | {grinder.gid}", icon_url=embed.footer.icon_url)
                        await user.remove_roles(
                            discord.Object(grinder.tier, type=discord.Role),
                            discord.Object(g_settings.paid_role, type=discord.Role),
                            discord.Object(g_settings.trial_role, type=discord.Role),
                            reason = "Didnt pay their advance grinder fees for 3 days.", atomic=True
                        )
                        e = discord.Embed(
                            title = "Kicked from Trial Grinders.",
                            description = (
                                f"{user.mention} (`{user.name}`) has been kicked from trial Grinders.\n"
                                "**Reason:** didnt pay their trial grinder advance payment for 3 days.\n"
                                f"Their total pay: {coin} {grinder.total_paid:,}"
                            ),
                            color = embed_color,
                            timestamp = embed.timestamp
                        )
                        e.set_author(name=user.global_name, icon_url=user.display_avatar.url)
                        e.set_thumbnail(url=user.display_avatar.url)
                        e.set_footer(text="Autoremove")
                        await guild.get_channel(g_settings.log_channel).send(embed=e)
                        self.bot.db.dank.grinder.delete(grinder)
                        view = None
            elif due_days < 5:
                embed.title = "Demoted to Trial Grinder"
                embed.description += f"{self.bot.emoji.warning} You have **2 days** to grind else you will be dismissed from grinders. {self.bot.emoji.warning}"
                await user.remove_roles(
                    discord.Object(grinder.tier, type=discord.Role),
                    discord.Object(g_settings.paid_role, type=discord.Role),
                    reason = "Inactive for 4 days", atomic=True
                )
                await user.add_roles(
                    discord.Object(g_settings.trial_role, type=discord.Role),
                    reason = "Inactive for 4 days", atomic=True
                )
                grinder.trial = True
                e = discord.Embed(
                    title = "Demoted to Trial Grinder",
                    description = f"{user.mention} (`{user.name}`) has been demoted to Trial Grinder.",
                    color = embed_color,
                    timestamp = embed.timestamp
                )
                e.set_author(name=user.global_name, icon_url=user.display_avatar.url)
                e.set_footer(text="Autoremove")
                e.set_thumbnail(url=user.display_avatar.url)
                await guild.get_channel(g_settings.log_channel).send(embed=e)
                self.bot.db.dank.grinder.update_record(grinder)
            elif due_days < 6:
                embed.title = ":rotating_light: CRITICAL REMINDER :rotating_light:"
                embed.description += ":rotating_light: You have __**1 day**__ to grind else you will be kicked from grinders. :rotating_light:\n__**YOUR GRINDER BANK IS SET TO 0 IF YOU GET KICKED.**__"
                await user.remove_roles(
                    discord.Object(grinder.tier, type=discord.Role),
                    discord.Object(g_settings.paid_role, type=discord.Role),
                    reason = "Inactive for 5 days", atomic=True
                )
                await user.add_roles(
                    discord.Object(g_settings.trial_role, type=discord.Role),
                    reason = "Inactive for 5 days", atomic=True
                )
                grinder.trial = True
                self.bot.db.dank.grinder.update_record(grinder)
            else:
                embed.title = "Kicked from Grinders"
                embed.description = (
                    "**Unfortunately, you were kicked from the grinders.**\n"
                    "**Reason:** Inactive for 6+ days\n"
                    f"At the time of dismiss you have: {coin} {grinder.total_paid:,}\n"
                    "-# (This amount is reset to 0 as you are dismissed from grinders.)"
                )
                embed.set_footer(text=embed.footer.text + f" | {grinder.gid}", icon_url=embed.footer.icon_url)
                await user.remove_roles(
                    discord.Object(grinder.tier, type=discord.Role),
                    discord.Object(g_settings.paid_role, type=discord.Role),
                    discord.Object(g_settings.trial_role, type=discord.Role),
                    reason = "Inactive for 6+ days", atomic=True
                )
                e = discord.Embed(
                    title = "Kicked from Grinders.",
                    description = (
                        f"{user.mention} (`{user.name}`) has been kicked from Grinders.\n"
                        "**Reason:** Inactive for 6+ days\n"
                        f"Their total pay: {coin} {grinder.total_paid:,}"
                    ),
                    color = embed_color,
                    timestamp = embed.timestamp
                )
                e.set_author(name=user.global_name, icon_url=user.display_avatar.url)
                e.set_thumbnail(url=user.display_avatar.url)
                e.set_footer(text="Autoremove")
                await guild.get_channel(g_settings.log_channel).send(embed=e)
                self.bot.db.dank.grinder.delete(grinder)
                view = None
            try:
                dm = await user.create_dm()
                await dm.send(embed=embed, view=view)
            except:
                await guild.get_channel(g_settings.rem_channel).send(user.mention, embed=embed)


async def setup(bot: Bot):
    await bot.add_cog(dank_grinder_tracking(bot))
