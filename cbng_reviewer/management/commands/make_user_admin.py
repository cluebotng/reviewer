import logging
from typing import Any

from django.core.management.base import CommandParser

from cbng_reviewer.libs.irc import IrcRelay
from cbng_reviewer.libs.messages import Messages
from cbng_reviewer.libs.utils import create_user
from cbng_reviewer.utils.command import CommandWithMetrics

logger = logging.getLogger(__name__)


class Command(CommandWithMetrics):
    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("username")
        parser.add_argument("--super", action="store_true")

    def handle(self, *args: Any, **options: Any) -> None:
        """Grant a user administrator rights, creating the user record if it does not exist."""
        messages = Messages()
        irc_relay = IrcRelay()

        if user := create_user(options["username"], auto_grant_rights=False):
            if user.is_admin:
                logger.info(f"{user.username} is already an admin")
            else:
                logger.info(f"Marked {user.username} as an admin")
                user.is_admin = True
                user.save()
                irc_relay.send_message(messages.notify_irc_about_granted_admin_access(user))

            if options["super"]:
                if user.is_superuser:
                    logger.info(f"{user.username} is already a superuser")
                else:
                    logger.info(f"Marked {user.username} as a superuser")
                    user.is_staff = True
                    user.is_superuser = True
                    user.save()
                    irc_relay.send_message(messages.notify_irc_about_granted_super_access(user))
