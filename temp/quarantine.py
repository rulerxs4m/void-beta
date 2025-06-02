import discord, asyncio
from discord.ext import commands

quarantined_roles = {}       
async def quarantine_member(ctx, member: discord.Member):
    q = member.guild.get_role(1278449490927292567)
    user_roles = []    
    for role in member.roles:
        if role.name != "@everyone":
            try:
                await member.remove_roles(role)
                user_roles.append(role)
                quarantined_roles[member.id] = user_roles
            except Exception as e:
                await ctx.send(f"Error quarantining `{member.name}` : `{e}`")
    await member.add_roles(q)
    await ctx.send(f"Quarantined `{member.name}`")
        
      
            
    

async def unquarantine_member(ctx, member: discord.Member):
    q = member.guild.get_role(1278449490927292567)
    if member.id in quarantined_roles:
        for role in quarantined_roles[member.id]:
            try:
                await member.add_roles(role)
            except Exception as e:
                await ctx.send(f"Error unquarantining `{member.name}` : `{e}`")
        await member.remove_roles(q)
        await ctx.send(f"Unquarantined `{member.name}`")
            
     
        
        
        
        

user_heat = {}          
        
async def decay_heat(user_id):
    await asyncio.sleep(600)  # 10 minutes
    if user_id in user_heat:
        user_heat[user_id] = max(0, user_heat[user_id] - 1)
        
def keyroles(mem):
    keyperms = ['kick_members', 'ban_members', 'administrator', 'manage_channels', 'manage_messages', 'manage_roles', 'manage_guild', 'manage_nicknames', 'moderate_members']
    key_roles = []
    for role in mem.roles:
        for perm in keyperms:
            if getattr(role.permissions, perm, False):
                key_roles.append(role)
                break             
    return key_roles
            

# placeholders to remove yellow underlines 
@commands.command()
async def warn(): ...
@commands.command()
async def unwarn(): ...

             
striped_roles = []
error_roles = []
        
# Error handling
@warn.error
@unwarn.error
async def mod_command_error(ctx, error):
    user_id = ctx.author.id
    mem = ctx.author
    channel = ctx.guild.get_channel(1359469727566794943)
    key_roles = keyroles(ctx.author)
    if isinstance(error, commands.CommandOnCooldown):
    #    await ctx.message.add_reaction("<:alert:1359479587850944652>")
    #    msg = await ctx.send(f"You're on cooldown! Try again in {error.retry_after:.2f}s.")        
      #  await asyncio.sleep(7)
     #   await msg.delete()
        
        user_heat[user_id] = user_heat.get(user_id, 0) + 1
        heat = user_heat[user_id]
        if heat == 5:
            em = discord.Embed(title="Triggering mod limit", color=0x010101)
            em.add_field(name="Moderator", value=f"{ctx.author.mention}")
            em.add_field(name="Command", value=f"{ctx.message.content}")
            em.add_field(name="Action Taken", value="**Warned**")
            em.add_field(name="Message Link", value=f"{ctx.message.jump_url}")
            await channel.send("<@889384139134992425>", embed=em)
            msg = await ctx.send(f"{ctx.author.mention}, you're heating up! Slow down or face consequences.")
            await asyncio.sleep(7)
            await msg.delete()
        elif heat >= 7:
            try:
                for role in key_roles:
                    try:
                        await ctx.author.remove_roles(role)
                        striped_roles.append(role)
                    except Exception as e:
                        error_roles.append(role)           
            except Exception as e:
                await channel.send(e)
            em = discord.Embed(title="Triggering mod limit", color=0x010101)
            em.add_field(name="Moderator", value=f"{ctx.author.mention}")
            em.add_field(name="Action Taken", value="**Striped Roles** : ✅")
            if striped_roles:  
                em.add_field(name="Striped Roles With Key Perms", value="\n".join([f"{role.name} : ✅" for role in striped_roles]))
            if error_roles:
                em.add_field(
        name="Failed to Remove Roles",
        value="\n".join([f"{role.name} : ❌" for role in error_roles]), inline=False)
            try:                
                await quarantine_member(ctx, mem)
                em.add_field(name="Quarantine Status", value=" ✅ Successfully Quarantined")
            except Exception as e:
                em.add_field(name="Quarantine Status", value=f" ❌ Error While Quarantining : `{e}`")                
            em.add_field(name="Message Link", value=f"{ctx.message.jump_url}")
            em.set_thumbnail(url=ctx.author.avatar.url)        
            await channel.send(f"<@889384139134992425>, {heat}", embed=em)                       
    elif isinstance(error, commands.MissingRole):
        embed = discord.Embed(color=discord.Color.red())
        embed.title = "⛔ Permission Denied"
        embed.description = "You don't have permission to use this command!"
    elif isinstance(error, commands.MissingRequiredArgument):
        embed = discord.Embed(color=discord.Color.red())
        embed.title = "⚠️ Missing Arguments"
        embed.description = f"Please check command usage:\n" \
                           f"`;warn @user [reason]`\n" \
                           f"`;unwarn @user [warn_number]`"
        await ctx.send(embed=embed)
    else:
        embed = discord.Embed(color=discord.Color.red())
        embed.title = "⚠️ Error Occurred"
        embed.description = str(error)
        await ctx.send(embed=embed)
    asyncio.create_task(decay_heat(user_id))