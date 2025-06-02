import discord
from discord.ext import commands
from discord.ext.commands.cooldowns import BucketType
from datetime import timedelta
import re
from datetime import datetime, timezone
import asyncio
from typing import Union, Tuple
from utils.database import structs
import global_vars
from utils import (
    color,
    ghost_url,
    embed_color,
    Bot,
    utility as util
)

KEY_PERMISSIONS = [
    "administrator",
    "manage_channels",
    "manage_roles",
    "ban_members",
    "kick_members",
    "manage_guild",
    "mention_everyone",
    "manage_nicknames"
    "manage_messages",
    "manage_webhooks",
    "manage_emojis",
    "moderate_members"
]





async def check(ctx, member:discord.Member):
    em = discord.Embed(title="Imagine Triggering An Error", color=0x010101)
    em.set_footer(text=ctx.bot.made_by, icon_url=ctx.bot.user.avatar.url)
    em.set_thumbnail(url=ctx.bot.user.avatar.url)
    if ctx.author == ctx.guild.owner:
        return True
    if ctx.author.id in ctx.bot.owner_ids:
        return True
    if member.top_role.position > ctx.author.top_role.position:
        em.add_field(name="Hierarchy Error", value="```You can't manage someone who is above you.```")
        await ctx.reply(embed=em)
        return False
    if ctx.author == member:
        em.add_field(name="Self Harm Error", value="```You can't use moderation commands on yourself.```")
        await ctx.reply(embed=em)
        return False   
    if member.top_role.position == ctx.author.top_role.position:
        em.add_field(name="Hierarchy Error", value="```You can't manage someone who is at the same level as you```")
        await ctx.reply(embed=em)
        return False
    
    return True



class ModCog(commands.Cog):
    def __init__(self, bot):
        self.bot: Bot = bot
        self.qq = {}

    async def mod_cmds_db(self, guild):
        r = self.bot.db.guild.settings.fetchone(guild.id)
        #q_role22 = r.q_role
        #print(q_role22)
        #self.qq["qrole"] = (q_role22)
        row: structs.guild_settings = self.bot.db.guild.settings.fetchone(guild.id)
        row2: structs.guild_logging = self.bot.db.guild.logging.fetchone(guild.id)
        if not row or not row2:
            em = discord.Embed(title="Imagine Triggering An Error", color=0x010101)
            em.add_field(name=f"Quarantine Role Not Set Up", value=f"Run : \n`.set quarantinerole <@role>` - To set a quarantine role \n `.set quarantinerole creat [name]` - To create a role automatically")
            return None
        q_role22 = r.q_role
        print(q_role22)
        q_role = await guild.fetch_role(row.q_role)
        print(q_role)
        muted_role = await guild.fetch_role(row.mute_role)
        #mod_log_channel = await guild.fetch_channel(row2.mod)

        return (q_role, q_role22, muted_role)#, mod_log_channel
    


     
    async def quarantine_member(self, member: discord.Member):
        print("iske neeche dekh")
        r = self.bot.db.guild.settings.fetchone(member.guild.id)
        qrole = r.q_role
        q_role = member.guild.get_role(qrole)
        
        embed = discord.Embed(title="Quarantine Report", color=0x010101)
        embed.set_author(name=member.name, icon_url=member.display_avatar.url)
        
        stripped_roles = []
        unstripped_roles = []

        if member not in global_vars.quarantined_roles:
            user_roles = []    
            for role in member.roles:
                if role.name != "@everyone":
                    try:
                        await member.remove_roles(role)
                        user_roles.append(role)
                        stripped_roles.append(role)
                    except Exception as e:
                        unstripped_roles.append(f"{role.mention} - {e}")
                        print(f"Error quarantining `{member.name}` : `{e}`")
            global_vars.quarantined_roles[member.id] = user_roles

            try:
                await member.add_roles(q_role)
                embed.add_field(name="Quarantine Role", value=f"✅ {q_role.name} applied", inline=False)
            except Exception as e:
                embed.add_field(name="Quarantine Role", value=f"❌ Failed to apply: `{e}`", inline=False)
                print(f"Error applying quarantine role to `{member.name}` : `{e}`")

            if stripped_roles:
                embed.add_field(name="Stripped Roles", value=", ".join([role.mention for role in stripped_roles]), inline=False)

            else:
                embed.add_field(name="Stripped Roles", value="❌ No roles were stripped", inline=False)

            if unstripped_roles:
                embed.add_field(name="Unstripped Roles", value="\n".join(unstripped_roles), inline=False)

            embed.set_footer(text="Quarantine process complete.")
            return embed

        
    async def unquarantine_member(self, member: discord.Member):
        r = self.bot.db.guild.settings.fetchone(member.guild.id)
        qrole = r.q_role
        q_role = member.guild.get_role(qrole)

        embed = discord.Embed(title="Unquarantine Report", color=0x02ad02)
        embed.set_author(name=member.name, icon_url=member.display_avatar.url)

        restored_roles = []
        failed_roles = []

        if member.id in global_vars.quarantined_roles:
            for role in global_vars.quarantined_roles[member.id]:
                try:
                    await member.add_roles(role)
                    restored_roles.append(role.mention)
                except Exception as e:
                    failed_roles.append(f"{role.mention} - {e}")
                    print(f"Error unquarantining `{member.name}` : `{e}`")

            try:
                await member.remove_roles(q_role)
                embed.add_field(name="Quarantine Role Removed", value=f"✅ {q_role.name} removed", inline=False)
            except Exception as e:
                embed.add_field(name="Quarantine Role Removed", value=f"❌ Failed to remove: `{e}`", inline=False)
                print(f"Error removing quarantine role from `{member.name}` : `{e}`")

            if restored_roles:
                embed.add_field(name="Restored Roles", value=", ".join(restored_roles), inline=False)
            else:
                embed.add_field(name="Restored Roles", value="❌ No roles restored", inline=False)

            if failed_roles:
                embed.add_field(name="Failed to Restore", value="\n".join(failed_roles), inline=False)

            embed.set_footer(text="Unquarantine process complete.")

            return embed



    @util.command(name="timeout", description="Timeout a member", aliases=["to", "tt"])
    @commands.has_permissions(moderate_members=True)
    @util.describe(
        member = "The member to timeout",
        duration = "The duration for which to timeout the member",
        reason = "The reason for timeout"
    )
    async def timeout(self, ctx, member: discord.Member, duration: str, *, reason=None):
        """
        Timeout a member. Example: ;timeout @user 10m or ;timeout @user 5sec
        """

        duration = duration.lower().strip()
        match = re.match(r"^(\d+)\s*(s|sec|secs|m|min|mins|h|hour|hours|d|day|days)$", duration)
        if not match:
            return await ctx.send("Invalid duration format. Use like `10m`, `5sec`, `2h`, `1day`, etc.")

        amount = int(match.group(1))
        unit = match.group(2)

        unit_to_seconds = {
            "s": 1, "sec": 1, "secs": 1,
            "m": 60, "min": 60, "mins": 60,
            "h": 3600, "hour": 3600, "hours": 3600,
            "d": 86400, "day": 86400, "days": 86400
        }

        seconds = amount * unit_to_seconds[unit]
        if seconds > 2419200:
            return await ctx.send("Timeout duration cannot exceed 28 days.")

        try:
            if reason == None:
                reason = f"Timeout initiated by {ctx.author.display_name} for {duration}"
            await member.timeout(timedelta(seconds=seconds), reason=reason)
            await ctx.send(f"{member.mention} has been timed out for {amount} {unit}.")
        except discord.Forbidden:
            await ctx.send("I don't have permission to timeout that member.")
        except Exception as e:
            await ctx.send(f"An error occurred: {e}")

    @util.command(name="untimeout", description="Remove timeout from a member", aliases=["rto", "uto", "rtt", "utt"])
    @commands.has_permissions(moderate_members=True)
    @util.describe(
        member = "The member to remove timeout from",
        reason = "The reason why you are removing the timeout"
    )
    async def untimeout(self, ctx, member: discord.Member, *, reason=None):
        """Remove timeout from a member."""
        try:
            if reason == None:
                reason = f"Untimeouted out by {ctx.author.display_name}"
            await member.timeout(None, reason=reason)
            await ctx.send(f"{member.mention} has been removed from timeout.")
        except discord.Forbidden:
            await ctx.send("I don't have permission to untimeout that member.")




    
    @util.command(name="mute", description="Mutes a user")
    @commands.cooldown(rate=5, per=60.0, type=BucketType.user)
    @commands.has_permissions(moderate_members=True)
    @util.describe(
        member = "The member to mute",
        duration = "The duration for mute",
        reason = "The reason for mute"
    )
    async def mute(self, ctx, member: discord.Member, duration: str = None, *, reason=None):
        muted_role, mod_log_channel = await self.mod_cmds_db(ctx.author.guild)
        temp_mute = []
        if not ctx.author.bot:
            muted_role = ctx.guild.get_role(1358668492496175145)
            if await check(ctx, member):
                if not muted_role:
                    return await ctx.send("Muted role not configured!")
        
                try:
                    if reason == None:
                        reason = f"Mute initiated by {ctx.author.display_name} for {duration}"
                    await member.add_roles(muted_role, reason=reason)
                    temp_mute.append(member.id)

                    embed = discord.Embed(title="Member Muted", description=f"{member.mention} has been muted for {duration}.", color=0x010101)
                    embed.add_field(name="Moderator", value=ctx.author.mention)
                    embed.add_field(name="Duration", value=duration if duration != None else "Indefinitely")
                    embed.add_field(name="Reason", value=reason)
                    embed.timestamp = datetime.now(timezone.utc)
                    
                    await mod_log_channel.send(embed=embed)
                    await ctx.send(f"{member.mention} has been muted.")
            
                    if duration:
                        time_units = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}
                        unit = duration[-1]
                        if unit in time_units:
                            seconds = int(duration[:-1]) * time_units[unit]
                            if member.id in temp_mute:
                                await asyncio.sleep(seconds)
                                temp_mute.remove(member.id)
                                if reason == None:
                                    reason = f"Temporary mute expired after {duration} (initiated by {ctx.author.display_name})"
                                await member.remove_roles(muted_role, reason=reason)
                                await ctx.send(f"{member.mention} has been unmuted after {duration}!")
                except discord.Forbidden:
                    await ctx.send("I don't have permission to mute this user!")
                except ValueError:
                    await ctx.send("Invalid duration format! Use examples: 1h, 30m, 2d")



    @util.command(name="unmute", description="Unmute a user")
    @commands.cooldown(rate=5, per=60.0, type=BucketType.user)
    @commands.has_permissions(moderate_members=True)
    @util.describe(
        member = "The member to unmute",
        reason = "The reason for unmuting"
    )
    async def unmute(self, ctx, member: discord.Member, *, reason=None):
        muted_role, mod_log_channel = self.mod_cmds_db(ctx.author.guild)
        if not ctx.author.bot:
            muted_role = ctx.guild.get_role(1358668492496175145)
            if await check(ctx, member):
                if not muted_role:
                    return await ctx.send("Muted role not configured!")
        
                try:
                    if reason == None:
                        reason = f"Unmute initiated by {ctx.author.display_name}"
                    await member.remove_roles(muted_role, reason=reason)
                    embed = discord.Embed(
                title="Member Unmuted",
                description=f"{member.mention} has been unmuted.",
                color=discord.Color.green()
                    )
                    embed.add_field(name="Moderator", value=ctx.author.mention)
                    embed.add_field(name="Reason", value=reason or "No reason provided")
                    embed.timestamp = datetime.now()
            
                    await mod_log_channel.send(embed=embed)
                    await ctx.send(f"{member.mention} has been unmuted.")
                except discord.Forbidden:
                    await ctx.send("I don't have permission to unmute this user!")



    @util.command(name="kick", description="Kick a user from the server")
    @commands.cooldown(rate=5, per=60.0, type=BucketType.user)
    @commands.has_permissions(kick_members=True)
    @util.describe(
        member = "The member to kick",
        reason = "The reason for kicking"
    )
    async def kick(self, ctx, member: discord.Member, *, reason=None):
        mod_log_channel = await self.mod_cmds_db(ctx.author.guild)
        if member == ctx.author:
            return await ctx.send("You can't kick yourself!")
        if await check(ctx, member):   
            try:
                if reason == None:
                    reason = f"Kick initiated by {ctx.author.display_name}"
                await member.kick(reason=reason)
                embed = discord.Embed(
                title="Member Kicked",
                description=f"{member.mention} has been kicked.",
                color=discord.Color.orange()
                )
                embed.add_field(name="Moderator", value=ctx.author.mention)
                embed.add_field(name="Reason", value=reason or "No reason provided")
                embed.timestamp = datetime.now()
            
                await mod_log_channel.send(embed=embed)
                await ctx.send(f"{member.mention} has been kicked.")
            except discord.Forbidden:
                await ctx.send("I don't have permission to kick this user!")
            except discord.HTTPException:
                await ctx.send("Failed to kick user!")



    @util.command(name="ban", description="Ban a user")
    @commands.cooldown(rate=5, per=60.0, type=BucketType.user)
    @commands.has_permissions(ban_members=True)
    @util.describe(
        member = "The member to ban",
        reason = "The reason for ban"
    )
    async def ban(self, ctx, member: discord.Member, *, reason=None):
        mod_log_channel = await self.mod_cmds_db(ctx.author.guild)
        if member == ctx.author:
            return await ctx.send("You can't ban yourself!")
        if await check(ctx, member):    
            try:
                if reason == None:
                    reason = f"Ban initiated by {ctx.author.display_name}"
                await ctx.guild.ban(member, reason=reason) 
                embed = discord.Embed(
                title="Member Banned",
                description=f"{member.mention} has been banned.",
                color=discord.Color.red()
                )
                embed.add_field(name="Moderator", value=ctx.author.mention)
                embed.add_field(name="Reason", value=reason or "No reason provided")
                embed.timestamp = datetime.now()
              
                await mod_log_channel.send(embed=embed)
                await ctx.send(f"{member.mention} has been banned.")
            except discord.Forbidden:
                await ctx.send("I don't have permission to ban this user!")
            except discord.HTTPException:
                await ctx.send("Failed to ban user!")
            except Exception as e:
                await ctx.send(f"An error occurred: {str(e)}")
            
    @util.command(name="unban", description="Unban a user")
    @commands.cooldown(rate=5, per=60.0, type=BucketType.user)
    @commands.has_permissions(ban_members=True)
    @util.describe(user_id = "The ID of the user to unban")
    async def unban(self, ctx, user_id: int):
        mod_log_channel = await self.mod_cmds_db(ctx.author.guild)
        if not ctx.author.bot:
            try:
                member = await self.bot.fetch_user(user_id)
                if reason == None:
                    reason = f"Ubanned by {ctx.author.display_name}"
                await ctx.guild.unban(member, reason=reason)
                embed = discord.Embed(
                title="Member Unbanned",
                description=f"{member.mention} has been unbanned.",
                color=discord.Color.green()
                )
                embed.add_field(name="Moderator", value=ctx.author.mention)
                embed.timestamp = datetime.now()
            
                await mod_log_channel.send(embed=embed)
                await ctx.send(f"`{member.name}` has been unbanned.")
            except discord.NotFound:
                await ctx.send("User not found in bans!")
            except discord.Forbidden:
                await ctx.send("I don't have permission to unban this user!")



    @util.command(description="dumps all the name of members in a role")
    @commands.has_permissions(moderate_members=True)
    @util.describe(role = "The role to dumb members.")
    async def dump(self, ctx, role:discord.Role):
        await ctx.reply("\n".join([member.display_name for member in role.members]))

    @util.group(invoke_without_command=True, aliases=["clean", "cu"], description="Deletes the amount of messages given in a channel (default 10)")
    @commands.has_permissions(manage_messages=True)
    @util.describe(
        amount = "The amount of messages to delete (default 10)",
        reason = "The reason for purging"
    )
    async def purge(self, ctx, amount: int = 10, *, reason=None):
        await ctx.message.delete()
        if reason is None:
            reason = f"Purge initiated by {ctx.author.display_name}"

        def allow_purge(msg):
            row = self.bot.db.guild.antinuke.fetchone(ctx.guild.id)
            log_channel_id = row.log_channel if row else None
            return not (msg.author.bot and msg.channel.id == log_channel_id)

        length = len(await ctx.channel.purge(limit=amount, check=allow_purge, reason=reason))
        msg = await ctx.channel.send(f"{self.bot.emoji.tick} purged {length} messages")
        await asyncio.sleep(3)
        await msg.delete()


    @purge.command(name="user", aliases=["u"], description="Purges a specific user's messages")
    @commands.has_permissions(manage_messages=True)
    @util.describe(
        member = "The user whose messages are to be purged",
        limit = "The limit of number of messages to delete (default 100)"
    )
    async def purge_user(self, ctx, member: discord.Member, limit: int = 100):
        if limit > 100:
            await ctx.reply("You can't delete more than 100 messages at once")
            return

        def allow_purge(msg):
            row = self.bot.db.guild.antinuke.fetchone(ctx.guild.id)
            log_channel_id = row.log_channel if row else None
            return msg.author == member and not (msg.author.bot and msg.channel.id == log_channel_id)

        length = len(await ctx.channel.purge(limit=limit, check=allow_purge, bulk=True))
        msg = await ctx.channel.send(f"{self.bot.emoji.tick} purged {length} messages")
        await asyncio.sleep(3)
        await msg.delete()


    @purge.command(name="after", description="Purges messages after a specific message", aliases=["a"])
    @commands.has_permissions(manage_messages=True)
    async def purge_after(self, ctx):
        reference = ctx.message.reference
        if not reference:
            await ctx.reply("You need to reply to a message to use this command.")
            return

        rmsg = await ctx.channel.fetch_message(reference.message_id)

        def allow_purge(msg):
            row = self.bot.db.guild.antinuke.fetchone(ctx.guild.id)
            log_channel_id = row.log_channel if row else None
            return not (msg.author.bot and msg.channel.id == log_channel_id)

        length = len(await ctx.channel.purge(after=rmsg, check=allow_purge, bulk=True))
        msg = await ctx.channel.send(f"{self.bot.emoji.tick} purged {length} messages")
        await asyncio.sleep(3)
        await msg.delete()


    @purge.command(name="between", description="Purges messages between two specific messages", aliases=["bt"])
    @commands.has_permissions(manage_messages=True)
    async def purge_between(self, ctx, after: discord.Message, before: discord.Message):
        def allow_purge(msg):
            row = self.bot.db.guild.antinuke.fetchone(ctx.guild.id)
            log_channel_id = row.log_channel if row else None
            return not (msg.author.bot and msg.channel.id == log_channel_id)

        length = len(await ctx.channel.purge(after=after, before=before, check=allow_purge, bulk=True))
        msg = await ctx.channel.send(f"{self.bot.emoji.tick} purged {length} messages")
        await asyncio.sleep(3)
        await msg.delete()



    @util.command(description="Freezes a users nickname")
    @commands.has_permissions(administrator=True)
    @util.describe(
        member = "The member whose nickname is to be freezed",
        freeze_nick = "The nickname to be put"
    )
    async def freezenick(self, ctx, member:discord.Member, *, freeze_nick:str):
        freezenick = self.bot.db.guild.freezenick.fetchone((ctx.guild.id, member.id))
        if await check(ctx, member):
            try:
                if not freezenick:
                    await member.edit(nick=freeze_nick)
                    await ctx.reply(f"{self.bot.emoji.tick} | Froze user's nickname.")
                    self.bot.db.guild.freezenick.insert(ctx.guild.id, member.id, freeze_nick)
                else: 
                    await member.edit(nick=freeze_nick)
                    await ctx.reply(f"{self.bot.emoji.tick} | Froze user's nickname, again.")
                    self.bot.db.guild.freezenick.update(ctx.guild.id, member.id, freeze_nick)
            except: 
                await ctx.reply(f"Unable to change nickname of `{member.name}`.")
    
    @util.command(description="UnFreezes a user's nickmame")
    @commands.has_permissions(administrator=True)
    @util.describe(member="The member whose nickname is to be un-freezed")
    async def unfreezenick(self, ctx, member:discord.Member):
        freezenick = self.bot.db.guild.freezenick.fetchone((ctx.guild.id, member.id))
        if await check(ctx, member):
            try:
                if freezenick:
                    await member.edit(nick=member.display_name)
                    await ctx.reply(f"{self.bot.emoji.tick} | Unfroze user's nickname.")
                    self.bot.db.guild.freezenick.delete((ctx.guild.id, member.id,))
                else: 
                    await ctx.reply(f"`{member.name}`'s nick is not frozen.")
                
            except: 
                await ctx.reply(f"Unable to change nickname of `{member.name}`.")



    @util.command(name="quarantine", description="Quarantine a member", aliases=["q"])
    @commands.has_permissions(administrator=True)
    @util.describe(member="The member to quarantine")
    async def q(self, ctx, member:discord.Member):
        if await check(ctx, member):
            embed = await self.quarantine_member(member)
            await ctx.send(embed=embed)


    @util.command(name="unquarantine", description="Un-Quarantine a member", aliases=["uq"])
    @commands.has_permissions(administrator=True)
    @util.describe(member="The member to un-quarantine")
    async def uq(self, ctx, member:discord.Member):
        if await check(ctx, member):
            embed = await self.unquarantine_member(member)
            await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(ModCog(bot))