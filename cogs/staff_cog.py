import discord 
from discord.ext import commands 
import json 
import os 
from app import mod_perm, bot_admins
from utils import utility as util
import asyncio

STAFF_DATA_FILE = "staff_roles.json"
STAFF_BREAK_FILE = "staff_breaks.json"
STAFF_CONFIG_FILE = "staff_config.json"


def load_modperms():
    with open("mod_perms.json", "r") as f:
        return json.load(f)    

def mod_cmd():
    async def predicate(ctx):
        if ctx.author.id in bot_admins:
            return True
        if ctx.author.guild_permissions.administrator:
            return True
        perms = load_modperms()
        allowed_roles = perms.get(ctx.command.name, [])
        user_roles = [role.id for role in ctx.author.roles]
        if any(role_id in user_roles for role_id in allowed_roles):
            return True        
        msg = await ctx.reply("You don't have permission to use this command.")
        await asyncio.sleep(5)
        await msg.delete()
        return False
    return commands.check(predicate)





def is_bot_admin():
    def predicate(ctx):
        if ctx.author.id in bot_admins:
            return True
        return False
    return commands.check(predicate)

def load_json(filename):
    if not os.path.exists(filename):
        return {} 
    with open(filename, "r") as f:
        return json.load(f)

def save_json(filename, data):
    with open(filename, "w") as f:
        json.dump(data, f, indent=4)

class Staffcog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_staff_roles(self, guild):
        data = load_json(STAFF_DATA_FILE)
        return sorted(
            [guild.get_role(rid) for rid in data.get(str(guild.id), []) if guild.get_role(rid)],
            key=lambda r: r.position,
            reverse=True
        )

    def get_log_channel(self, guild):
        config = load_json(STAFF_CONFIG_FILE)
        log_id = config.get(str(guild.id), {}).get("log")
        return guild.get_channel(log_id) if log_id else None

    @util.group(name="staff", invoke_without_command=True)
    @mod_perm()
    async def staff(self, ctx):
        embed = discord.Embed(
            title="Staff Command Help",
            description="Here are the available `;staff` subcommands:",
            color=discord.Color.blue()
        )
        embed.add_field(name=";staff view", value="Shows all staff members organized by their highest staff role.", inline=False)
        embed.add_field(name=";staff promote @member [@role]", value="Promotes a member to the next staff role or to a specific one.", inline=False)
        embed.add_field(name=";staff demote @member [@role]", value="Demotes a member to the previous staff role or to a specific one.", inline=False)
        embed.add_field(name=";staff add @role", value="Adds a role to the staff system.", inline=False)
        embed.add_field(name=";staff remove @role", value="Removes a role from the staff system.", inline=False)
        embed.add_field(name=";staff fire @member", value="Removes all staff roles from a member.", inline=False)
        embed.add_field(name=";staff hire @member @role", value="Assigns a member to a staff role directly.", inline=False)
        embed.add_field(name=";staff break @member", value="Toggles staff break state. Saves/restores their staff roles.", inline=False)
        await ctx.send(embed=embed)

    @staff.command(name="view")
    @mod_perm()
    async def staff_view(self, ctx):
        guild = ctx.guild
        staff_roles = self.get_staff_roles(guild)
        exempt_roles = [1198741817068376114, 1198741978314178593]

        seen_members = set()
        embed = discord.Embed(title="Staff Members", color=discord.Color.green())
        
        for role in staff_roles:
            if role.id in exempt_roles:
                members = [f"{m.mention} - `({m.display_name})`" for m in ctx.guild.members if role in m.roles]
            else:
                members = [f"{m.mention} - `({m.display_name})`" for m in ctx.guild.members if role in m.roles and m.id not in seen_members]
                for m in ctx.guild.members:
                    if role in m.roles:
                        seen_members.add(m.id)
            value = "\n".join(members) if members else "No members."
            embed.add_field(name=role.name, value=value, inline=False)

        await ctx.send(embed=embed)

    @staff.command(name="add")
    @is_bot_admin()
    @util.describe(role="The role to add")
    async def staff_add(self, ctx, role: discord.Role):
        data = load_json(STAFF_DATA_FILE)
        guild_id = str(ctx.guild.id)
        log = self.get_log_channel(ctx.guild)

        if guild_id not in data:
            data[guild_id] = []

        if role.id in data[guild_id]:
            return await ctx.send(f"`{role.name}` is already a staff role.")

        data[guild_id].append(role.id)
        save_json(STAFF_DATA_FILE, data)
        await ctx.send(f"`{role.name}` has been added as a staff role.")
        if log:
            await log.send(f"{ctx.author.mention} added `{role.name}` as a staff role.")

    @staff.command(name="remove")
    @is_bot_admin()
    async def staff_remove(self, ctx, role: discord.Role):
        data = load_json(STAFF_DATA_FILE)
        guild_id = str(ctx.guild.id)
        log = self.get_log_channel(ctx.guild)

        if guild_id not in data or role.id not in data[guild_id]:
            return await ctx.send(f"`{role.name}` is not a registered staff role.")

        data[guild_id].remove(role.id)
        save_json(STAFF_DATA_FILE, data)
        await ctx.send(f"Removed `{role.name}` from the staff roles list.")
        if log:
            await log.send(f"{ctx.author.mention} removed `{role.name}` from staff roles.")

    @staff.command(name="promote")
    @is_bot_admin()
    async def staff_promote(self, ctx, member: discord.Member, role: discord.Role = None):
        roles = self.get_staff_roles(ctx.guild)
        log = self.get_log_channel(ctx.guild)

        if role:
            await member.add_roles(role, reason=f"Promoted by {ctx.author.name}")
            await ctx.send(f"{member.mention} has been promoted to `{role.name}`.")
            if log:
                await log.send(f"{ctx.author.mention} promoted {member.mention} to `{role.name}`.")
        else:
            current_index = next((i for i, r in enumerate(roles) if r in member.roles), None)
            if current_index is None or current_index + 1 >= len(roles):
                return await ctx.send(f"{member.mention} cannot be promoted.")

            await member.remove_roles(roles[current_index])
            await member.add_roles(roles[current_index + 1], reason=f"Promotion by {ctx.author.name}")
            await ctx.send(f"{member.mention} has been promoted to `{roles[current_index + 1].name}`.")
            if log:
                await log.send(f"{ctx.author.mention} promoted {member.mention} to `{roles[current_index + 1].name}`.")

    @staff.command(name="demote")
    @is_bot_admin()
    async def staff_demote(self, ctx, member: discord.Member, role: discord.Role = None):
     
        roles = self.get_staff_roles(ctx.guild)
        log = self.get_log_channel(ctx.guild)

        if role:
            await member.add_roles(role, reason=f"Demoted by {ctx.author.name}")
            await ctx.send(f"{member.mention} has been demoted to `{role.name}`.")
            if log:
                await log.send(f"{ctx.author.mention} demoted {member.mention} to `{role.name}`.")
        else:
            current_index = next((i for i, r in enumerate(roles) if r in member.roles), None)
            if current_index is None or current_index == 0:
                return await ctx.send(f"{member.mention} cannot be demoted.")

             
            await member.remove_roles(roles[current_index])
            await member.add_roles(roles[current_index - 1])
            await ctx.send(f"{member.mention} has been demoted to `{roles[current_index - 1].name}`.")
            if log:
                await log.send(f"{ctx.author.mention} demoted {member.mention} to `{roles[current_index - 1].name}`.")

    @staff.command(name="fire")
    @is_bot_admin()
    async def staff_fire(self, ctx, member: discord.Member):
        roles = self.get_staff_roles(ctx.guild)
        to_remove = [r for r in roles if r in member.roles]
        log = self.get_log_channel(ctx.guild)

        if not to_remove:
            return await ctx.send(f"{member.mention} has no staff roles.")

        await member.remove_roles(*to_remove)
        await ctx.send(f"{member.mention} has been fired from all staff roles.")
        if log:
            await log.send(f"{ctx.author.mention} fired {member.mention} from all staff roles.")

    @staff.command(name="hire")
    @is_bot_admin()
    async def staff_hire(self, ctx, member: discord.Member, role: discord.Role):
        log = self.get_log_channel(ctx.guild)
        if role not in self.get_staff_roles(ctx.guild):
            return await ctx.send(f"`{role.name}` is not a recognized staff role.")

        await member.add_roles(role, reason=f"Hired by {ctx.author.name}")
        await ctx.send(f"{member.mention} has been hired as `{role.name}`.")
        if log:
            await log.send(f"{ctx.author.mention} hired {member.mention} as `{role.name}`.")

    @staff.command(name="break")
    @is_bot_admin()
    async def staff_break(self, ctx, member: discord.Member):
        guild_id = str(ctx.guild.id)
        break_data = load_json(STAFF_BREAK_FILE)
        staff_roles = self.get_staff_roles(ctx.guild)
        break_role = discord.utils.get(ctx.guild.roles, name="On Break")
        log = self.get_log_channel(ctx.guild)

        if not break_role:
            break_role = await ctx.guild.create_role(name="On Break", reason="Break system initialization")

        member_data = break_data.get(guild_id, {}).get(str(member.id))

        if member_data:
            roles_to_restore = [ctx.guild.get_role(rid) for rid in member_data if ctx.guild.get_role(rid)]
            await member.add_roles(*roles_to_restore, reason="Returned from break")
            await member.remove_roles(break_role, reason="Break ended")
            del break_data[guild_id][str(member.id)]
            action = "returned from break"
        else:
            current_roles = [r.id for r in member.roles if r in staff_roles]
            if not current_roles:
                return await ctx.send(f"{member.mention} has no staff roles to go on break.")

            break_data.setdefault(guild_id, {})[str(member.id)] = current_roles
            await member.remove_roles(*[ctx.guild.get_role(rid) for rid in current_roles])
            await member.add_roles(break_role, reason="Staff on break")
            action = "put on break"

        save_json(STAFF_BREAK_FILE, break_data)
        await ctx.send(f"Break state toggled for {member.mention}.")
        if log:
            await log.send(f"{ctx.author.mention} {action} {member.mention}.")

async def setup(bot):
    await bot.add_cog(Staffcog(bot))

    