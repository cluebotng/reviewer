from dataclasses import dataclass

from django.conf import settings


@dataclass
class Message:
    body: str
    subject: str | None = None
    channel: str = settings.IRC_RELAY_CHANNEL_ADMIN
