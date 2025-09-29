from dataclasses import dataclass
from typing import Optional

from django.conf import settings


@dataclass
class Message:
    body: str
    subject: Optional[str] = None
    channel: str = settings.IRC_RELAY_CHANNEL_ADMIN
