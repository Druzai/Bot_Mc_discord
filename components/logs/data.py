from dataclasses import dataclass
from datetime import datetime
from enum import Enum, auto
from typing import Optional, List

from discord import SyncWebhookMessage


class MessageType(Enum):
    PlayerMessage = auto()
    PlayerLogin = auto()
    PlayerLogout = auto()
    DeathMessage = auto()
    MessageBlockEnd = auto()


@dataclass
class LogMessage:
    type: MessageType
    player_nick: Optional[str] = None
    player_message: Optional[str] = None
    player_ip: Optional[str] = None
    player_reason: Optional[str] = None
    message_groups: Optional[List[str]] = None
    death_message_regex: Optional[str] = None


@dataclass
class DeathMessage:
    discord_message: Optional[SyncWebhookMessage]
    death_message: str
    count: int
    last_used_date: Optional[datetime]
    last_count: int = 0
