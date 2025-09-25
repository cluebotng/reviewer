import logging
from typing import Any

import requests
from django.core.management.base import CommandParser
from django.db.models import Q

from cbng_reviewer.models import User, Edit, Classification, TrainingData
from cbng_reviewer.utils.command import CommandWithMetrics

logger = logging.getLogger(__name__)


class Command(CommandWithMetrics):
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

        if options["edit_id"]:
            edits = Edit.objects.filter(id=options["edit_id"])
        else:
            edits = Edit.objects.filter(
                ~Q(status=2) & ~Q(pk__in=our_classified_edits) & ~Q(is_deleted=True) & ~Q(has_training_data=False)
            )

        for edit in edits:
            if edit.id in our_classified_edits:
                logger.info(f"We have already processed {edit.id}")  # make --edit-id more friendly
                continue

            try:
                training_data = TrainingData.objects.get(edit=edit)
            except TrainingData.DoesNotExist:
                # We will handle this after `import_training_data` has run
                continue

            if training_data.user in trusted_users:
                logger.info(f"Leaving constructive review for {edit.id} by {user.username}")
                Classification.objects.create(edit=edit, user=user, classification=1, comment="Trusted User")
