import sqlite3

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
