import logging
import socket
from typing import Optional

from django.conf import settings

from cbng_reviewer.libs.models.message import Message

logger = logging.getLogger(__name__)


class IrcRelay:
    def send_message(self, message: Message, channel: Optional[str] = None):
        target_channel = channel if channel else settings.IRC_RELAY_CHANNEL
        text = message.body.strip() if message.body else None

        if not target_channel or not text:
            logger.warning(f"Skipping irc message due to missing channel or text: {target_channel} / {text}")
            return

        payload = f"{channel}:{text}\n".encode("utf-8")
        logger.info(f"Sending to IRC Relay: {payload}")
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.sendto(payload, (settings.IRC_RELAY_HOST, settings.IRC_RELAY_PORT))
        except Exception as e:
            logger.warning(f"Failed to send to IRC Relay {payload}: {e}")
