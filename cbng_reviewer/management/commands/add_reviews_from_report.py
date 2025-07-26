import logging
from typing import Any, Dict, List

import requests
from django.core.management import BaseCommand
from django.core.management.base import CommandParser

from cbng_reviewer.libs.wikipedia import Wikipedia
from cbng_reviewer.models import User, Edit, Classification

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--edit-id")

    def _get_reported_edits(self) -> Dict[str, List[str]]:
        r = requests.get(
            "https://cluebotng.toolforge.org/api/?action=review.export.users",
            timeout=10,
            headers={
                "User-Agent": "ClueBot NG Reviewer - Add Reviews From Report",
            },
        )
        r.raise_for_status()
        return r.json()

    def handle(self, *args: Any, **options: Any) -> None:
        """Add reviews from reports."""
        username_to_reviewers = {user.username: user for user in User.objects.filter(is_reviewer=True)}

        wikipedia = Wikipedia()
        for edit_id, usernames in self._get_reported_edits().items():
            if options["edit_id"] not in {None, edit_id}:
                continue

            edit, created = Edit.objects.get_or_create(id=edit_id)
            if created:
                logger.info(f"Created entry for {edit.id}, seeding training data")
                wikipedia.create_training_data_for_edit(edit)

            for username in usernames:
                # Most report admins are reviewers, but do not assume this
                if user := username_to_reviewers.get(username):
                    if Classification.objects.filter(edit=edit, user=user).exists():
                        logger.debug(f"Already have classification from {user} on {edit.id}")
                    else:
                        logger.info(f"Leaving constructive review for {edit.id} by {user.username}")
                        Classification.objects.create(
                            edit=edit, user=user, classification=1, comment="Imported From Report Interface"
                        )
                else:
                    logger.info(f"{username} is not a reviewer, ignoring for {edit.id}")
