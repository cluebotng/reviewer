import logging
from typing import Any

from django.core.management import BaseCommand
from django.core.management.base import CommandParser

from cbng_reviewer.libs.utils import notify_user_review_rights_granted, create_user_with_central_auth_mapping

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("username")

    def handle(self, *args: Any, **options: Any) -> None:
        """Grant a user reviewer rights, creating the user record if it does not exist."""
        if user := create_user_with_central_auth_mapping(options["username"]):
            if user.is_reviewer:
                logger.info(f"{user.username} is already a reviewer")
            else:
                logger.info(f"Marked {user.username} as a reviewer")
                user.is_reviewer = True
                user.save()

                notify_user_review_rights_granted(user)
