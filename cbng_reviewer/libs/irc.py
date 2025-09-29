import logging
import socket
from typing import Optional

import requests
from django.conf import settings

from cbng_reviewer.libs.models.message import Message

logger = logging.getLogger(__name__)


class IrcRelay:
    def send_message(self, message: Message, channel: Optional[str] = None) -> bool:
        target_channel = channel if channel else message.channel
        text = message.body.strip() if message.body else None

        if not target_channel or not text:
            logger.warning(f"Skipping irc message due to missing channel or text: {target_channel} / {text}")
            return False

        if not settings.CBNG_ENABLE_IRC_MESSAGING:
            logger.debug(f"Skipping sending message to {target_channel} ({text})")
            return False

        # HTTP
        if settings.IRC_RELAY_USE_HTTP:
            payload = {'channel': target_channel, 'string': text}
            logger.debug(f"Sending to IRC Relay (HTTP): {payload}")
            r = requests.put(f'http://{settings.IRC_RELAY_HOST}:{settings.IRC_RELAY_PORT}', json=payload, timeout=1)
            if r.status_code != 200:
                logger.error(f"Failed to send to IRC Relay (HTTP) {payload}: {r.status_code} / {r.content}")
            return True

        # UDP
        payload = f"{target_channel}:{text}\n".encode("utf-8")
        logger.debug(f"Sending to IRC Relay (UDP): {payload}")
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.sendto(payload, (settings.IRC_RELAY_HOST, settings.IRC_RELAY_PORT))
            return True
        except socket.gaierror as e:
            if e.errno == 8:
                logger.debug(f"Could not connect to IRC Relay {payload}: {e}")
        except Exception as e:
            logger.error(f"Failed to send to IRC Relay {payload}: {e}")
        return False
