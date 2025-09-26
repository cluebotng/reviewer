import logging
from typing import Any

from django.core.management.base import CommandParser

from cbng_reviewer.libs.auth.notifications import notify_user_review_rights_granted
from cbng_reviewer.libs.auth.utils import create_user
from cbng_reviewer.utils.command import CommandWithMetrics

logger = logging.getLogger(__name__)


class Command(CommandWithMetrics):
    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("username")

    def handle(self, *args: Any, **options: Any) -> None:
        """Grant a user reviewer rights, creating the user record if it does not exist."""
        if user := create_user(options["username"], auto_grant_rights=False):
            if user.is_reviewer:
                logger.info(f"{user.username} is already a reviewer")
            else:
                logger.info(f"Marked {user.username} as a reviewer")
                user.is_reviewer = True
                user.save()

                notify_user_review_rights_granted(user)
