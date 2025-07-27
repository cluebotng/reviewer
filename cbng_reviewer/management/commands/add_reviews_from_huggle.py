import logging
from typing import Any

import requests
from django.core.management import BaseCommand
from django.core.management.base import CommandParser

from cbng_reviewer.models import User, Edit, Classification, TrainingData

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--edit-id")

    def _get_trusted_users(self):
        r = requests.get(
            "https://huggle.bena.rocks/?action=read&wp=en.wikipedia.org",
            timeout=10,
            headers={
                "User-Agent": "ClueBot NG Reviewer - Fetch User Whitelist",
            },
        )
        r.raise_for_status()
        return r.text.split("|")[0:-1]

    def handle(self, *args: Any, **options: Any) -> None:
        """Add reviews from huggle."""
        user, created = User.objects.get_or_create(username="Bot - Huggle")
        if created:
            user.is_bot = True
            user.is_reviewer = True
            user.save()

        trusted_users = self._get_trusted_users()
        our_classified_edits = Classification.objects.filter(user=user).values_list("edit__id", flat=True)

        for edit in (
            Edit.objects.filter(id=options["edit_id"])
            if options["edit_id"]
            else Edit.objects.exclude(status=2).exclude(deleted=True)
        ):
            try:
                training_data = TrainingData.objects.get(edit=edit)
            except TrainingData.DoesNotExist:
                # We will handle this after `import_training_data` has run
                continue

            if edit.id in our_classified_edits:
                # Cleanup bad entries
                if training_data.user not in trusted_users:
                    logger.info(f"Removing classification for non-trusted user {training_data.user}")
                    Classification.objects.filter(edit=edit, user=user, classification=1).delete()
                    continue

                # Make --edit-id more friendly
                logger.info(f"We have already processed {edit.id}")
                continue

            # Add an entry if we don't have one
            if training_data.user in trusted_users:
                logger.info(f"Leaving constructive review for {edit.id} by {user.username}")
                Classification.objects.create(edit=edit, user=user, classification=1, comment="Trusted User")
