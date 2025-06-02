import discord
from discord.ext import commands, tasks
from discord import app_commands, Interaction
import sqlite3
from datetime import datetime, timedelta
import asyncio
import random
from typing import Optional
import sqlite3

GIVEAWAY_EMOJI = "🎉"
JOIN_EMOJI = "✅"
LEAVE_EMOJI = "❌"
PARTICIPANTS_EMOJI = "👀"
TOP_EMOJI = "👑"
LOG_EMOJI = "📢"
EMBED_COLOR = 0x000000

# -----------------------------------
# DB Init Code
# -----------------------------------

def init_db():
    conn = sqlite3.connect("giveaway.db")
    
    with conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS config (
            guild_id INTEGER PRIMARY KEY,
            manager_roles TEXT,
            bypass_roles TEXT,
            blacklist_roles TEXT,
            extra_roles TEXT,
            log_channel INTEGER,
            log_enabled INTEGER
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS giveaways (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER,
                channel_id INTEGER,
                message_id INTEGER,
                prize TEXT,
                start_time INTEGER,
                end_time INTEGER,
                winners_count INTEGER,
                started_by INTEGER,
                donor_id INTEGER,
                donor_message TEXT,
                required_roles TEXT,
                bypass_roles TEXT,
                extra_roles TEXT,
                messages_required INTEGER,
                message_channels TEXT,
                blacklist_roles TEXT,
                ping_everyone INTEGER,
                ended INTEGER DEFAULT 0
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS entries (
                giveaway_id INTEGER,
                user_id INTEGER,
                entries INTEGER,
                PRIMARY KEY (giveaway_id, user_id)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS stats (
                guild_id INTEGER,
                host_id INTEGER,
                count INTEGER,
                PRIMARY KEY (guild_id, host_id)
            )
        """)
    
    print("✅ giveaway.db initialized.")

# -----------------------------------
# DB Init Code
# -----------------------------------

# -----------------------------------
# Config Code
# -----------------------------------

def parse_csv_roles(text: str) -> list[int]:
    """Parse CSV role IDs from string, return as list of ints."""
    if not text:
        return []
    return [int(r) for r in text.split(',') if r.strip().isdigit()]

def to_csv_roles(roles: list[int]) -> str:
    """Convert list of role IDs to CSV string."""
    return ','.join(str(r) for r in roles)

def bool_to_int(val: bool) -> int:
    return 1 if val else 0

def int_to_bool(val: int) -> bool:
    return val == 1

# -----------------------------------
# Config Code
# -----------------------------------

class Giveaway(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        init_db()
        self.db = sqlite3.connect('giveaway.db')
        self.db.row_factory = sqlite3.Row
        self.cursor = self.db.cursor()
        self.check_expired_giveaways.start()

    def cog_unload(self):
        self.check_expired_giveaways.cancel()
        self.db.close()

    # --- DB Config methods ---

    def get_config(self, guild_id: int) -> dict:
        self.cursor.execute("SELECT * FROM config WHERE guild_id = ?", (guild_id,))
        row = self.cursor.fetchone()
        if row is None:
            self.cursor.execute("INSERT INTO config (guild_id) VALUES (?)", (guild_id,))
            self.db.commit()
            self.cursor.execute("SELECT * FROM config WHERE guild_id = ?", (guild_id,))
            row = self.cursor.fetchone()
        return dict(row)

    def update_config(self, guild_id: int, column: str, value):
        if column in ('manager_roles', 'bypass_roles', 'blacklist_roles', 'extra_roles') and isinstance(value, list):
            value = to_csv_roles(value)
        if column == 'log_enabled' and isinstance(value, bool):
            value = bool_to_int(value)
        self.cursor.execute(f"UPDATE config SET {column} = ? WHERE guild_id = ?", (value, guild_id))
        self.db.commit()

    def parse_duration(self, time_str: str) -> int:
        import re
        matches = re.findall(r'(\d+)([smhd])', time_str.lower())
        total_seconds = 0
        for val, unit in matches:
            if unit == 's':
                total_seconds += int(val)
            elif unit == 'm':
                total_seconds += int(val) * 60
            elif unit == 'h':
                total_seconds += int(val) * 3600
            elif unit == 'd':
                total_seconds += int(val) * 86400
        return total_seconds

    async def _end_giveaway_by_row(self, giveaway_row: sqlite3.Row):
        guild = self.bot.get_guild(giveaway_row['guild_id'])
        if guild is None:
            return
        channel = guild.get_channel(giveaway_row['channel_id'])
        if channel is None:
            return

        try:
            message = await channel.fetch_message(giveaway_row['message_id'])
        except:
            message = None

        if giveaway_row['ended'] == 1:
            return

        self.cursor.execute("SELECT user_id, entries FROM entries WHERE giveaway_id = ?", (giveaway_row['id'],))
        entries = self.cursor.fetchall()
        if not entries:
            winners = []
        else:
            weighted_pool = []
            for entry in entries:
                weighted_pool.extend([entry['user_id']] * entry['entries'])
            winners = []
            count = giveaway_row['winners_count']
            pool_copy = weighted_pool.copy()
            while len(winners) < count and pool_copy:
                winner = random.choice(pool_copy)
                if winner not in winners:
                    winners.append(winner)
                    pool_copy = [uid for uid in pool_copy if uid != winner]

        self.cursor.execute("UPDATE giveaways SET ended = 1 WHERE id = ?", (giveaway_row['id'],))
        self.db.commit()

        self.cursor.execute("SELECT count FROM stats WHERE guild_id = ? AND host_id = ?", (giveaway_row['guild_id'], giveaway_row['started_by']))
        stat = self.cursor.fetchone()
        if stat:
            self.cursor.execute("UPDATE stats SET count = count + 1 WHERE guild_id = ? AND host_id = ?", (giveaway_row['guild_id'], giveaway_row['started_by']))
        else:
            self.cursor.execute("INSERT INTO stats (guild_id, host_id, count) VALUES (?, ?, 1)", (giveaway_row['guild_id'], giveaway_row['started_by']))
        self.db.commit()

        winner_mentions = ', '.join(f'<@{uid}>' for uid in winners) if winners else 'No winners :('
        embed = discord.Embed(
            title=f"{GIVEAWAY_EMOJI} Giveaway Ended!",
            description=f"**Prize:** {giveaway_row['prize']}\n**Winners:** {winner_mentions}",
            color=EMBED_COLOR,
            timestamp=datetime.utcnow(),
        )
        if message:
            embed.set_footer(text=f"Giveaway message ID: {message.id}")

        if channel:
            await channel.send(content=f"{winner_mentions} Congratulations!", embed=embed)

        config = self.get_config(giveaway_row['guild_id'])
        if config['log_enabled'] == 1 and config['log_channel']:
            log_channel = guild.get_channel(config['log_channel'])
            if log_channel:
                log_embed = discord.Embed(
                    title=f"{LOG_EMOJI} Giveaway Ended Log",
                    description=f"Prize: {giveaway_row['prize']}\nWinners: {winner_mentions}\nEnded by system",
                    color=EMBED_COLOR,
                    timestamp=datetime.utcnow()
                )
                await log_channel.send(embed=log_embed)

    @tasks.loop(seconds=30)
    async def check_expired_giveaways(self):
        now_ts = int(datetime.utcnow().timestamp())
        self.cursor.execute("SELECT * FROM giveaways WHERE ended = 0 AND end_time <= ?", (now_ts,))
        rows = self.cursor.fetchall()
        for row in rows:
            await self._end_giveaway_by_row(row)

    # ---- Slash Command Registration ----
    giveaway_group = app_commands.Group(name="giveaway", description="Manage giveaways")

    @giveaway_group.command(name="viewconfig", description="View the giveaway config for this server")
    async def view_config(self, interaction: Interaction):
        config = self.get_config(interaction.guild.id)
        manager_roles = parse_csv_roles(config['manager_roles'])
        bypass_roles = parse_csv_roles(config['bypass_roles'])
        blacklist_roles = parse_csv_roles(config['blacklist_roles'])
        extra_roles = parse_csv_roles(config['extra_roles'])
        log_channel_id = config['log_channel']
        log_enabled = int_to_bool(config['log_enabled'])

        def roles_to_mentions(ids):
            return ', '.join(f'<@&{r}>' for r in ids) if ids else 'None'

        embed = discord.Embed(title="Giveaway Config", color=EMBED_COLOR)
        embed.add_field(name="Manager Roles", value=roles_to_mentions(manager_roles), inline=False)
        embed.add_field(name="Bypass Roles", value=roles_to_mentions(bypass_roles), inline=False)
        embed.add_field(name="Blacklist Roles", value=roles_to_mentions(blacklist_roles), inline=False)
        embed.add_field(name="Extra Entry Roles", value=roles_to_mentions(extra_roles), inline=False)
        embed.add_field(name="Log Channel", value=f"<#{log_channel_id}>" if log_channel_id else "Not set", inline=False)
        embed.add_field(name="Logging Enabled", value=str(log_enabled), inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @giveaway_group.command(name="logs", description="Enable or disable giveaway logs")
    @app_commands.describe(enabled="Enable or disable logs")
    async def logs_toggle(self, interaction: Interaction, enabled: bool):
        if not await self._check_manage_permission(interaction):
            return await interaction.response.send_message("You don't have permission.", ephemeral=True)
        self.update_config(interaction.guild.id, 'log_enabled', enabled)
        await interaction.response.send_message(f"Logging {'enabled' if enabled else 'disabled'}.", ephemeral=True)

    @giveaway_group.command(name="logchannel", description="Set the giveaway log channel")
    @app_commands.describe(channel="Channel to send giveaway logs")
    async def logchannel_set(self, interaction: Interaction, channel: discord.TextChannel):
        if not await self._check_manage_permission(interaction):
            return await interaction.response.send_message("You don't have permission.", ephemeral=True)
        self.update_config(interaction.guild.id, 'log_channel', channel.id)
        await interaction.response.send_message(f"Log channel set to {channel.mention}.", ephemeral=True)

    @giveaway_group.command(name="resetconfig", description="Reset the giveaway configuration to default")
    @app_commands.describe(channel="Reset the current Server Config")
    async def reset_config(self, interaction: Interaction):
        if not await self._check_manage_permission(interaction):
            return await interaction.response.send_message("You don't have permission.", ephemeral=True)

        guild_id = interaction.guild.id
        self.cursor.execute("DELETE FROM config WHERE guild_id = ?", (guild_id,))
        self.cursor.execute("INSERT INTO config (guild_id) VALUES (?)", (guild_id,))
        self.db.commit()

        await interaction.response.send_message("Giveaway configuration has been reset to default.", ephemeral=True)


    # Slash subcommand group manually declared
    setup_group = app_commands.Group(name="setup", description="Configure giveaway roles", parent=giveaway_group)

    @setup_group.command(name="manager", description="Add or remove a giveaway manager role")
    @app_commands.describe(role="Role to add or remove", action="Add or Remove")
    async def setup_manager(self, interaction: Interaction, role: discord.Role, action: str):
        if not await self._check_manage_permission(interaction):
            return await interaction.response.send_message("You don't have permission.", ephemeral=True)
        await self._setup_role_helper(interaction, 'manager_roles', role, action)

    @setup_group.command(name="bypass", description="Add or remove a bypass role")
    @app_commands.describe(role="Role to add or remove", action="Add or Remove")
    async def setup_bypass(self, interaction: Interaction, role: discord.Role, action: str):
        if not await self._check_manage_permission(interaction):
            return await interaction.response.send_message("You don't have permission.", ephemeral=True)
        await self._setup_role_helper(interaction, 'bypass_roles', role, action)

    @setup_group.command(name="blacklist", description="Add or remove a blacklist role")
    @app_commands.describe(role="Role to add or remove", action="Add or Remove")
    async def setup_blacklist(self, interaction: Interaction, role: discord.Role, action: str):
        if not await self._check_manage_permission(interaction):
            return await interaction.response.send_message("You don't have permission.", ephemeral=True)
        await self._setup_role_helper(interaction, 'blacklist_roles', role, action)

    @setup_group.command(name="extra", description="Add or remove an extra entry role")
    @app_commands.describe(role="Role to add or remove", action="Add or Remove")
    async def setup_extra(self, interaction: Interaction, role: discord.Role, action: str):
        if not await self._check_manage_permission(interaction):
            return await interaction.response.send_message("You don't have permission.", ephemeral=True)
        await self._setup_role_helper(interaction, 'extra_roles', role, action)

    async def _setup_role_helper(self, interaction: Interaction, column: str, role: discord.Role, action: str):
        guild_id = interaction.guild.id
        config = self.get_config(guild_id)
        current_roles = parse_csv_roles(config[column])

        if action.lower() == "add":
            if role.id in current_roles:
                await interaction.response.send_message(f"Role {role.name} is already in {column}.", ephemeral=True)
                return
            current_roles.append(role.id)
            self.update_config(guild_id, column, current_roles)
            await interaction.response.send_message(f"Added role {role.name} to {column}.", ephemeral=True)
        elif action.lower() == "remove":
            if role.id not in current_roles:
                await interaction.response.send_message(f"Role {role.name} is not in {column}.", ephemeral=True)
                return
            current_roles.remove(role.id)
            self.update_config(guild_id, column, current_roles)
            await interaction.response.send_message(f"Removed role {role.name} from {column}.", ephemeral=True)
        else:
            await interaction.response.send_message("Invalid action. Use add or remove.", ephemeral=True)

    async def _check_manage_permission(self, interaction: Interaction) -> bool:
        if interaction.user.guild_permissions.manage_guild:
            return True
        config = self.get_config(interaction.guild.id)
        manager_roles = parse_csv_roles(config['manager_roles'])
        member_roles = [r.id for r in interaction.user.roles]
        return any(role in manager_roles for role in member_roles)

async def setup(bot):
    from start import setup as start_setup
    from end import setup as end_setup
    from reroll import setup as reroll_setup
    from cancel import setup as cancel_setup
    from list import setup as list_setup
    from top import setup as top_setup

    main_cog = Giveaway(bot)
    await bot.add_cog(main_cog)

    await start_setup(bot, main_cog)
    await end_setup(bot, main_cog)
    await reroll_setup(bot, main_cog)
    await cancel_setup(bot, main_cog)
    await list_setup(bot, main_cog)
    await top_setup(bot, main_cog)

    await bot.add_cog(Giveaway(bot))
    pass
