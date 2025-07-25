import logging
from typing import Any

from django.core.management import BaseCommand
from django.core.management.base import CommandParser
from social_django.models import UserSocialAuth

from cbng_reviewer.libs.wikipedia import Wikipedia
from cbng_reviewer.models import User

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("username")

    def handle(self, *args: Any, **options: Any) -> None:
        """Grant a user reviewer rights, creating the user record if it does not exist."""
        try:
            user = User.objects.get(username=options["username"])
        except User.DoesNotExist:
            central_uid = Wikipedia().fetch_user_central_id(options["username"])
            if not central_uid:
                logger.error("Could not find user on wikipedia, aborting")
                return

            logger.info(f"No user record found for {options['username']}, creating entry ({central_uid})")
            user = User.objects.create(username=options["username"])
            UserSocialAuth.objects.create(provider="mediawiki", uid=central_uid, user_id=user.id)

        if user.is_reviewer:
            logger.info(f"{user.username} is already a reviewer")
        else:
            logger.info(f"Marked {user.username} as a reviewer")
            user.is_reviewer = True
            user.save()
