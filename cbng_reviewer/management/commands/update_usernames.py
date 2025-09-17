import logging
from typing import Any

from django.core.management import BaseCommand
from social_django.models import UserSocialAuth

from cbng_reviewer.libs.wikipedia.reader import WikipediaReader
from cbng_reviewer.models import User

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def handle(self, *args: Any, **options: Any) -> None:
        """Update user username's to match CentralAuth."""
        wikipedia_reader = WikipediaReader()
        for user in User.objects.filter(is_bot=False):
            try:
                central_uid = UserSocialAuth.objects.get(provider="mediawiki", user_id=user.id).uid
            except UserSocialAuth.DoesNotExist:
                logger.error(f"Missing mapping entry for {user.username}")
                continue

            expected_username = wikipedia_reader.get_username(central_uid)
            if not expected_username:
                logger.warning(f"Failed to get expected username for {user.username} ({central_uid})")
                continue

            if user.username == expected_username:
                logger.info(f"Username is correct for {user.username} ({central_uid})")
            else:
                logger.info(f"Updating {user.username} to {expected_username} ({central_uid})")
                user.username = expected_username
                user.save()
