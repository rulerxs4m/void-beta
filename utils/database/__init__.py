from .db import table, database
from . import structs

class db(database):
    def __init__(self, debug: bool = False):
        super().__init__(debug)

        self.user = user_db(self)
        self.guild = guild_db(self)
        self.dank = dank_db(self)
        self.dso = dso_db(self)

class dso_db:
    def __init__(self, db: database):
        self.report = table(db,
            name="dso_report",
            pkey = "report_id",
            data_cls = structs.dso_report
        )
        self.reported = table(db,
            name="dso_reported",
            pkey = "report_id",
            data_cls = structs.dso_reported
        )
        self.participants = table(db,
            name="dso_participants",
            pkey = "report_id",
            data_cls = structs.dso_participants
        )
        self.voters = table(db,
            name="dso_voters",
            pkey = "report_id",
            data_cls = structs.dso_voters
        )
        self.conclusion = table(db,
            name="dso_conclusion",
            pkey = "report_id",
            data_cls = structs.dso_conclusion
        )

class user_db:
    def __init__(self, db: database):
        self.afk = table(db,
            name = "user_afk",
            pkey = ("uid", "gid"),
            data_cls = structs.user_afk
        )
        self.prefixes = table(db,
            name = "user_prefixes",
            pkey = "uid",
            data_cls = structs.user_prefixes
        )
        self.afk_mentions = table(db,
            name = "user_afk_mentions",
            pkey = ("uid", "message_id"),
            data_cls = structs.user_afk_mentions
        )

class guild_db:
    def __init__(self, db: database):
        self.prefixes = table(db,
            name = "guild_prefixes",
            pkey = "gid",
            data_cls = structs.guild_prefixes
        )
        self.logging = table(db,
            name = "guild_logging",
            pkey = "gid",
            data_cls = structs.guild_logging
        )
        self.settings = table(db,
            name = "guild_settings",
            pkey = "gid",
            data_cls = structs.guild_settings
        )
        self.freezenick = table(db,
            name = "freezenick",
            pkey = ("gid", "uid"),
            data_cls = structs.freezenick
        )
        self.antinuke = table(db,
            name = "guild_antinuke",
            pkey = "gid",
            data_cls = structs.guild_antinuke
        )
        self.welcomer = table(db,
            name = "guild_welcomer",
            pkey = ("gid", "leave"),
            data_cls = structs.guild_welcomer
        )

class dank_db:
    def __init__(self, db: database):
        self.grinder = table(db,
            name = "dank_grinder",
            pkey = ("gid", "uid"),
            data_cls = structs.dank_grinder
        )
        self.grinder_tiers = table(db, 
            name = "dank_grinder_tiers",
            pkey = ("gid", "role_id"),
            data_cls = structs.dank_grinder_tiers
        )
        self.grinder_settings = table(db,
            name = "dank_grinder_settings",
            pkey = "gid",
            data_cls = structs.dank_grinder_settings
        )
        self.donations = table(db,
            name = "dank_donations",
            pkey = "id",
            data_cls = structs.dank_donation
        )
        self.donation_settings = table(db,
            name = "dank_donation_settings",
            pkey = ("gid", "donation_channel"),
            data_cls = structs.dank_donation_settings
        )