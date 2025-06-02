import discord
from discord.ext import commands
from discord.ui import View, Button
import asyncio
from datetime import datetime
from utils.database import structs
import global_vars
from utils import (
    color,
    ghost_url,
    embed_color,
    Bot,
    utility as util
)

from cogs.mod_cog import check

KEY_PERMISSIONS = [
    "administrator",
    "manage_channels",
    "manage_roles",
    "ban_members",
    "kick_members",
    "moderate_members",
    "manage_guild",
    "mention_everyone",
    "manage_messages",
    "manage_webhooks",
    "manage_emojis"
]



class QuarantineButton(View):
    def __init__(self, bot, cog, executor: discord.Member, role: discord.Role):
        super().__init__(timeout=None)
        self.bot = bot
        self.cog = cog
        self.executor = executor
        self.role = role

    def is_authorized(self, user: discord.Member, target: discord.Member):
        if user == target.guild.owner:
            return True, None
        if user.id in self.bot.owner_ids:
            return True, None
        if user.top_role > target.top_role and user.guild_permissions.administrator:
            return True, None
        return False, "You do not have permissions to run this command."

    @discord.ui.button(label="Quarantine", style=discord.ButtonStyle.danger, custom_id="quarantine_button")
    async def quarantine_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        authorized, error = self.is_authorized(interaction.user, self.executor)
        if not authorized:
            return await interaction.response.send_message(error, ephemeral=True)
        await interaction.response.defer()  
        if self.executor.id in self.bot.owner_ids:
            await interaction.followup.send("Bot owners cannot be quarantined.")
            return
        await self.cog.trigger_quarantine(self.executor)
        await interaction.followup.send(f"{self.executor.mention} has been quarantined.")


    @discord.ui.button(label="Undo Changes", style=discord.ButtonStyle.danger, custom_id="undo_perm_escalation")
    async def undo_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("Only administrators can perform this action.", ephemeral=True)

        try:
            perms_dict = self.role.permissions.to_dict()
            for perm in self.cog.added_perms[self.role.id]:
                perms_dict[perm] = False
            await self.role.edit(permissions=discord.Permissions(**perms_dict), reason="Undo of dangerous permission escalation")
            await interaction.response.send_message(f"✅ Dangerous permissions removed from role `{self.role.name}`.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Failed to undo permissions: `{e}`", ephemeral=True)


    
            

class QuarantineButton2(View):
    def __init__(self, bot, cog, executor: discord.Member, target: discord.Member):
        super().__init__(timeout=None)
        self.bot = bot
        self.cog = cog
        self.executor = executor
        self.target = target

    def is_authorized(self, user: discord.Member, target: discord.Member):
        if user == target.guild.owner:
            return True, None
        if user.id in self.bot.owner_ids:
            return True, None
        if user.top_role > target.top_role and user.guild_permissions.administrator:
            return True, None
        return False, "You do not have permissions to run this command."

    @discord.ui.button(label="Quarantine Executor", style=discord.ButtonStyle.danger, custom_id="quarantine_executor")
    async def quarantine_executor_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        authorized, error = self.is_authorized(interaction.user, self.executor)
        if not authorized:
            return await interaction.response.send_message(error, ephemeral=True)
        await interaction.response.defer()  
        if self.executor.id in self.bot.owner_ids:
            await interaction.followup.send("Bot owners cannot be quarantined.")
            return  
        await self.cog.trigger_quarantine(self.executor)
        await interaction.followup.send(f"{self.executor.mention} has been quarantined.")

    @discord.ui.button(label="Quarantine Member", style=discord.ButtonStyle.danger, custom_id="quarantine_target")
    async def quarantine_target_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        authorized, error = self.is_authorized(interaction.user, self.target)
        if not authorized:
            return await interaction.response.send_message(error, ephemeral=True)
        await interaction.response.defer()  
        if self.executor.id in self.bot.owner_ids:
            await interaction.followup.send("Bot owners cannot be quarantined.")
            return
        await self.cog.trigger_quarantine(self.target)
        await interaction.followup.send(f"{self.target.mention} has been quarantined.")

class QuarantineButton3(View):
    def __init__(self, bot, cog, executor: discord.Member):
        super().__init__(timeout=None)
        self.bot = bot
        self.cog = cog
        self.executor = executor

    def is_authorized(self, user: discord.Member, target: discord.Member):
        if user == target.guild.owner:
            return True, None
        if user.id in self.bot.owner_ids:
            return True, None
        if user.top_role > target.top_role and user.guild_permissions.administrator:
            return True, None
        return False, "You do not have permissions to run this command."

    @discord.ui.button(label="Quarantine", style=discord.ButtonStyle.danger, custom_id="quarantine_for_channel_deletion")
    async def quarantine_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        authorized, error = self.is_authorized(interaction.user, self.executor)
        if not authorized:
            return await interaction.response.send_message(error, ephemeral=True)
        await interaction.response.defer()  
        if self.executor.id in self.bot.owner_ids:
            await interaction.followup.send("Bot owners cannot be quarantined.")
            return
        await self.cog.trigger_quarantine(self.executor)
        await interaction.followup.send(f"{self.executor.mention} has been quarantined.")



class LogButtonView(discord.ui.View):
    def __init__(self, view: discord.ui.View, timeout: float = 0.0):
        super().__init__(timeout=timeout)
        for label, url in buttons:
            self.add_item(discord.ui.Button(label=label, url=url))




class AntiNuke(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.owner_ids = getattr(bot, "owner_ids", [])
        self.undo = {}
        self.hardcoded_whitelist_specials = {1063899809221709824, 880018759325204510}


    async def safe_log(
        self,
        content: str = None,
        embed: discord.Embed = None,
        view: discord.ui.View = None  
    ):
            
            owners = [await self.bot.fetch_user(owner_id) for owner_id in self.bot.owner_ids]

            for owner in owners:
                dm_content = content or "A log embed was attempted."
                await owner.send(content=dm_content, embed=embed, view=view)
        
            
        
    

    async def trigger_quarantine(self, member: discord.Member):
        mod_cog = self.bot.get_cog("ModCog")
        try:
            embed = await mod_cog.quarantine_member(member) 
            if embed:
                pass
                #await ctx.send(embed=embed)
            else:
                pass
               # await ctx.send("Quarantine process skipped or failed.")
        except Exception as e:
            raise

    async def quarantine_others(self, guild):
        row: structs.guild_settings = self.bot.db.guild.antinuke.fetchone(guild.id)
        q_others = row.q_others
        log_channel = await guild.fetch_channel(row.log_channel)
        return q_others, log_channel

    def build_embed(self, title, description, color=discord.Color.red()):
        embed = discord.Embed(title=title, description=description, color=color)
        embed.timestamp = datetime.utcnow()
        return embed

    def is_whitelisted(self, member: discord.Member):
        if member.id in self.owner_ids:
            return True
        if member.id in self.hardcoded_whitelist_specials:
            return True
        if member == member.guild.owner:
            return True
        return False



    @commands.Cog.listener()
    async def on_guild_role_update(self, before: discord.Role, after: discord.Role):
        try:
            q_others, log_channel = await self.quarantine_others(after.guild)
        except:
            pass
        added_perms = [
            perm for perm in KEY_PERMISSIONS
            if not getattr(before.permissions, perm) and getattr(after.permissions, perm)
        ]

        self.undo[after.id] = added_perms

        if added_perms:
            await asyncio.sleep(2.5)
            executor = None
            async for entry in after.guild.audit_logs(limit=5, action=discord.AuditLogAction.role_update):
                if entry.target.id == after.id:
                    executor = entry.user
                    break


            exec_act = "Pending..."

            if executor and self.is_whitelisted(executor):
                exec_act = "Whitelisted - No Action Taken"
            else:
                if not q_others:
                    exec_act = "Quarantine Feature Is Turned Off"
                else:
                    try:
                        await self.trigger_quarantine(executor)
                        exec_act = "Successfully Quarantined User"
                    except Exception as e:
                        exec_act = f"Error Putting Executor In Quarantine - `{e}`"

            embed = self.build_embed(
                    title="🔒 Role Permission Escalation Detected",
                    description=(
                        f"Role `{after.name}` was updated with dangerous permissions:\n"
                        f"**{', '.join(added_perms)}**\n"
                    )
                )
            embed.add_field(name="**Executor (Gave Role):**", value=f"{executor.mention if executor else 'Unknown'}")
            embed.add_field(name="**Action Taken:**", value=f"**Executor:** {exec_act}", inline=False)

            view = QuarantineButton(bot=self.bot, cog=self, executor=executor, role=after)
            try:  
                await log_channel.send(embed=embed, view=view)
            except Exception as e:
                await self.safe_log(e, embed, view)


    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        try:
            q_others, log_channel = await self.quarantine_others(after.guild)
        except:
            pass
        new_roles = [role for role in after.roles if role not in before.roles]
        flagged_roles = []
        for role in new_roles:
            if any(getattr(role.permissions, perm) for perm in KEY_PERMISSIONS):
                flagged_roles.append(role)

        if flagged_roles:
            await asyncio.sleep(2.5)  # Let audit log update

            executor = None
            async for entry in after.guild.audit_logs(limit=5, action=discord.AuditLogAction.member_role_update):
                if entry.target.id != after.id:
                    continue

                
                changed_roles = entry.changes.after.roles if hasattr(entry.changes.after, "roles") else []

                for flagged in flagged_roles:
                    if any(isinstance(r, discord.Role) and r.id == flagged.id for r in changed_roles):
                        executor = entry.user
                        break

                if executor:
                    break

            if executor:
                executor = after.guild.get_member(executor.id)
            

            roles_str = ', '.join(role.name for role in flagged_roles)

            exec_act = mem_act = "Pending..."

            if not executor == self.bot.user:
                if executor:
                    if self.is_whitelisted(executor) or executor == after.guild.owner:
                        exec_act = "Whitelisted - No Action Taken"
                        mem_act = "No Action Taken"
                    else:
                        if not q_others:
                            exec_act = "Quarantine Feature Is Turned Off"
                            mem_act = "Quarantine Feature Is Turned Off"
                        else:
                            try:
                                await self.trigger_quarantine(executor)
                                exec_act = "Successfully Quarantined User"
                            except Exception as e:
                                exec_act = f"Error Putting Executor In Quarantine - `{e}`"

                            try:
                                await self.trigger_quarantine(after)
                                mem_act = "Successfully Quarantined Member"
                            except Exception as e:
                                mem_act = f"Error Putting Member In Quarantine - `{e}`"

                    embed = self.build_embed(
                        title="⚠️ Dangerous Role Assigned",
                        description=(
                            f"User `{after.display_name}` was given the following role(s): **{roles_str}**\n"
                            f"These roles have sensitive permissions.\n"
                        )
                    )
                    embed.add_field(name="**Executor (Gave Role):**", value=f"{executor.mention if executor else 'Unknown'}")
                    embed.add_field(name="**Member (Got Role):**", value=f"{after.mention}")
                    embed.add_field(name="**Action Taken:**", value=f"**Executor:** {exec_act}\n**Member:** {mem_act}", inline=False)

                    view = QuarantineButton2(bot=self.bot, cog=self, executor=executor, target=after)  
                    try:  
                        await log_channel.send(embed=embed, view=view)
                    except Exception as e:
                        await self.safe_log(e, embed, view)


    


    
    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        row = self.bot.db.guild.antinuke.fetchone(channel.guild.id)
        q_others = row.q_others if row else None
        log_channel = row.log_channel

        if log_channel == channel.id:
            await asyncio.sleep(2.5)

            executor = None
            async for entry in channel.guild.audit_logs(limit=5, action=discord.AuditLogAction.channel_delete):
                if entry.target.id == channel.id:
                    executor = entry.user
                    break
            gld = channel.guild
            overwrites = {
                gld.default_role: discord.PermissionOverwrite(read_messages=False),
               gld.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
            }
            try:
                new_channel = await gld.create_text_channel("antinuke-logs", overwrites=overwrites)
            except Exception as e:
                print(e)
            rec = self.bot.db.guild.antinuke.fetchone(channel.guild.id)
            rec.log_channel = new_channel.id
            self.bot.db.guild.antinuke.update_record(rec)


            exec_act = "Pending..."

            if executor and executor != self.bot.user:
                if self.is_whitelisted(executor):
                    exec_act = "Whitelisted - No Action Taken"
                #elif not q_others:
                    #exec_act = "Quarantine Feature Is Turned Off"
                else:
                    try:
                        await self.trigger_quarantine(executor)
                        exec_act = "Successfully Quarantined User"
                    except Exception as e:
                        exec_act = f"Error Putting Executor In Quarantine - `{e}`"

            embed = self.build_embed(
                title="🚨 Log Channel Deleted",
                description=(
                    f"Channel `{channel}` in **{channel.guild.name}** was deleted.\n"
                    f"**Executor:** {executor.mention if executor else 'Unknown'}\n"
                    f"**Channel Creation:** {new_channel if new_channel else 'None'}\n"
                ),
                color=embed_color
            )
            embed.add_field(name="**Action Taken:**", value=exec_act, inline=False)

            view = QuarantineButton3(bot=self.bot, cog=self, executor=executor)

            try:
                await new_channel.send(embed=embed, view=view)
            except Exception as e:
                await self.safe_log(e, embed, view)


    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if message.guild is None or message.author.bot:
            return

        row = self.bot.db.guild.antinuke.fetchone(message.guild.id)
        if not row:
            return

        log_channel = message.guild.get_channel(row.log_channel)
        q_others = row.q_others

       
        if not log_channel or message.channel.id != log_channel.id:
            return

        await asyncio.sleep(2.5)  

        executor = None
        async for entry in message.guild.audit_logs(limit=5, action=discord.AuditLogAction.message_delete):
            if entry.target.id == message.author.id and entry.extra.channel.id == message.channel.id:
                executor = entry.user
                break

        exec_act = "Pending..."

        if executor and executor != self.bot.user:
            if self.is_whitelisted(executor):
                exec_act = "Whitelisted - No Action Taken"
            #elif not q_others:
               # exec_act = "Quarantine Feature Is Turned Off"
            else:
                try:
                    await self.trigger_quarantine(executor)
                    exec_act = "Successfully Quarantined User"
                except Exception as e:
                    exec_act = f"Error Putting Executor In Quarantine - `{e}`"

        embed = self.build_embed(
            title="🚨 Log Message Deleted",
            description=(
                f"A message in the log channel `{message.channel}` was deleted in **{message.guild.name}**.\n"
                f"**Executor:** {executor.mention if executor else 'Unknown'}\n"
                f"**Deleted Message Author:** {message.author.mention}\n"
                f"**Content:**\n```{message.content or '[No Content]'}```"
            ),
            color=embed_color
        )
        embed.add_field(name="**Action Taken:**", value=exec_act, inline=False)

        view = QuarantineButton3(bot=self.bot, cog=self, executor=executor)

        
        new_log_channel = message.guild.get_channel(row.log_channel)
        try:
            await new_log_channel.send(embed=embed, view=view)
        except Exception as e:
            await self.safe_log(e, embed, view)


async def setup(bot):
    await bot.add_cog(AntiNuke(bot))
