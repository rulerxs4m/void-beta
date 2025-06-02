import sqlite3

class database:
    def __init__(self, guild_id: int) -> None:
        self.con = sqlite3.connect(f"custom_cogs/{guild_id}/database.db", check_same_thread=False)
        self.con.execute("PRAGMA foreign_keys = ON")
        self.cursor = self.con.cursor()

    def commit(self) -> None:
        self.con.commit()

    def close(self) -> None:
        self.cursor.close()
        self.con.close()