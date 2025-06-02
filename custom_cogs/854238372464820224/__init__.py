import discord
from discord.ext import commands as cmds

from utils import (
    Bot,
    utility as util
)

class custom_854238372464820224(cmds.Cog):
    def __init__(self, bot: Bot):
        self.bot: Bot = bot
        self.pool_perms = 1200980690624323625
        self.dank_id = 270904126974590976
        self.guild_id = 854238372464820224
        self.q_role = 1278449490927292567
        
    @cmds.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if after.guild.id != self.guild_id: return
        if after.bot: return
        if after.get_role(self.pool_perms) is None: return
        if before.get_role(self.pool_perms): return
        if after.id in self.bot.owner_ids: return
        if after.id == after.guild.owner_id: return
        flag = False; doer = None
        async for entry in after.guild.audit_logs(limit = 5, action = discord.AuditLogAction.member_role_update):
            if entry.target.id != after.id: continue
            if entry.user_id == after.guild.owner_id: continue
            if entry.user_id in self.bot.owner_ids: continue
            if entry.user_id == self.dank_id: continue
            flag = True; doer = entry.user
        if not flag: return

        # The Member
        roles = after.roles
        roles.remove(after.guild.default_role) # @everyone
        await after.remove_roles(*roles, atomic=True,
            reason=f"Pool Perms role added by {doer} is not one of these -> Void Devs, Server Owner, Dank Memer"
        )
        await after.add_roles(
            discord.Object(self.q_role, type=discord.Role), atomic = True,
            reason=f"Pool Perms role added by {doer} is not one of these -> Void Devs, Server Owner, Dank Memer"
        )

        # The Doer
        roles = doer.roles
        roles.remove(after.guild.default_role) # @everyone
        await doer.remove_roles(*roles, atomic=True,
            reason=f"{doer} added pool perms to {after} & is not one of these -> Void Devs, Server Owner, Dank Memer"
        )
        await doer.add_roles(
            discord.Object(self.q_role, type=discord.Role), atomic = True,
            reason=f"{doer} added pool perms to {after} & is not one of these -> Void Devs, Server Owner, Dank Memer"
        )

async def setup(bot: Bot):
    await bot.add_cog(custom_854238372464820224(bot))