import logging
from typing import Any

import requests
from django.core.management import BaseCommand
from django.core.management.base import CommandParser

from cbng_reviewer.libs.wikipedia import Wikipedia
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
            user.save()

        trusted_users = self._get_trusted_users()
        our_classified_edits = Classification.objects.filter(user=user).values_list("edit__id", flat=True)

        wikipedia = Wikipedia()
        for edit in (
            Edit.objects.filter(id=options["edit_id"])
            if options["edit_id"]
            else Edit.objects.exclude(status=2).exclude(pk__in=our_classified_edits)
        ):
            if edit.id in our_classified_edits:
                logger.info(f"We have already processed {edit.id}")  # make --edit-id more friendly
                continue

            try:
                training_data = TrainingData.objects.get(edit=edit)
            except TrainingData.DoesNotExist:
                logger.info(f"Fetching training data for {edit.id}")
                wikipedia.create_training_data_for_edit(edit)
                try:
                    training_data = TrainingData.objects.get(edit=edit)
                except TrainingData.DoesNotExist:
                    logger.info(f"Skipping edit due to no training data: {edit.id}")
                    continue

            if training_data.user in trusted_users:
                logger.info(f"Leaving constructive review for {edit.id} by {user.username}")
                Classification.objects.create(edit=edit, user=user, classification=1, comment="Trusted User")
