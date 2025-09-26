import logging
from typing import Any

from cbng_reviewer.libs.wikipedia.reader import WikipediaReader
from cbng_reviewer.models import User
from cbng_reviewer.utils.command import CommandWithMetrics

logger = logging.getLogger(__name__)


class Command(CommandWithMetrics):
    def handle(self, *args: Any, **options: Any) -> None:
        """Update user username's to match CentralAuth."""
        wikipedia_reader = WikipediaReader()
        for user in User.objects.filter(is_bot=False):
            if not user.central_user_id:
                logger.error(f"Missing central user id for {user.username}")
                continue

            central_user = wikipedia_reader.get_central_user(user_id=user.central_user_id)
            if not central_user:
                logger.warning(f"Failed to get central user for {user.central_user_id} ({user.username})")
                continue

            if user.username == central_user.username:
                logger.info(f"Username is correct for {user.username} ({central_user.id})")
            else:
                logger.info(f"Updating {user.username} to {central_user.username} ({central_user.id})")
                user.username = central_user.username
                user.save()
