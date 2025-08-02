import logging
from typing import Any

from django.core.management import BaseCommand
from django.core.management.base import CommandParser
from social_django.models import UserSocialAuth

from cbng_reviewer.libs.irc import IrcRelay
from cbng_reviewer.libs.messages import Messages
from cbng_reviewer.libs.wikipedia.reader import WikipediaReader
from cbng_reviewer.models import User

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("username")
        parser.add_argument("--super", action="store_true")

    def handle(self, *args: Any, **options: Any) -> None:
        """Grant a user administrator rights, creating the user record if it does not exist."""
        messages = Messages()
        irc_relay = IrcRelay()

        try:
            user = User.objects.get(username=options["username"])
        except User.DoesNotExist:
            central_uid = WikipediaReader().get_central_auth_user_id(options["username"])
            if not central_uid:
                logger.error("Could not find user on wikipedia, aborting")
                return

            logger.info(f"No user record found for {options['username']}, creating entry ({central_uid})")
            user = User.objects.create(username=options["username"])
            UserSocialAuth.objects.create(provider="mediawiki", uid=central_uid, user_id=user.id)

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
