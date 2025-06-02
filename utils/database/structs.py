import ast
from typing import List
from dataclasses import dataclass

@dataclass(slots=True)
class dso_report:
    report_id: int = None
    reporter: int = None
    channel_id: int = None
    thread_id: int = None
    dso_staff: int = None
    global_ban: bool = False

@dataclass(slots=True)
class dso_reported:
    report_id: int = None
    user_id: int = None
    
@dataclass(slots=True)
class dso_participants:
    report_id: int = None
    user_id:int = None
    
@dataclass(slots=True)
class dso_voters:
    report_id: int = None
    user_id:int = None
    vote:int = None
    
@dataclass(slots=True)
class dso_conclusion:
    report_id: int = None
    reference_link: str = None

@dataclass(slots=True)
class user_afk:
    uid: int = None
    guild_id: int = None
    is_global: bool = None
    timestamp: int = None
    reason: str = None

@dataclass(slots=True)
class user_afk_mentions:
    uid: int = None
    guild_id: int = None
    channel_id: int = None
    message_id: int = None
    pinger_id: int = None
    timestamp: int = None

@dataclass(slots=True)
class guild_prefixes:
    gid: int = None
    prefixes: str = None

    @property
    def pref(self) -> List[str]:
        return ast.literal_eval(self.prefixes) if self.prefixes else []

@dataclass(slots=True)
class user_prefixes:
    uid: int = None
    prefixes: str = None

    @property
    def pref(self) -> List[str]:
        return ast.literal_eval(self.prefixes) if self.prefixes else []

@dataclass(slots=True)
class guild_logging:
    gid: int = None
    mod: int = None
    message: int = None
    join_leave: int = None
    member: int = None
    server: int = None
    ticket: int = None
    voice: int = None

@dataclass(slots=True)
class guild_settings:
    gid: int = None
    q_role: int = None
    mute_role: int = None

@dataclass(slots=True)
class freezenick:
    gid: int = None
    uid: int = None
    nick: str = None

@dataclass(slots=True)
class dank_grinder_settings:
    gid: int = None
    pay_channel: int = None
    log_channel: int = None
    rem_channel: int = None
    paid_role: int = None
    trial_role: int = None
    blacklisted_role: int = None
    manager_role: int = None

@dataclass(slots=True)
class dank_grinder_tiers:
    gid: int = None
    role_id: int = None
    amount: int = None
    name: str = None

@dataclass(slots=True)
class dank_grinder:
    gid: int = None
    uid: int = None
    tier: int = None
    total_paid: int = None
    next_pay: int = None
    grinder_since: int = None
    trial: bool = False
    blacklisted: bool = False

@dataclass(slots=True)
class guild_antinuke:
    gid: int = None
    q_others: bool = None
    log_channel: int = None

@dataclass(slots=True)
class dank_donation:
    id: int = None
    guild_id: int = None
    donor_id: int = None
    coin_value: int = None
    logged_by: int = None
    timestamp: int = None
    category: str = None

@dataclass(slots=True)
class dank_donation_settings:
    gid: int = None
    donation_channel: int = None
    log_channel: int = None
    bank_name: str = None
    manager_role: int = None

@dataclass(slots=True)
class guild_welcomer:
    gid: int
    leave: bool
    message: str
    channel: int
    delete_after: int
    card_enabled: bool