import logging
from typing import Any

from django.core.management.base import CommandParser

from cbng_reviewer.libs.core import Core
from cbng_reviewer.models import User, Classification, EditGroup
from cbng_reviewer.utils.command import CommandWithMetrics

logger = logging.getLogger(__name__)


class Command(CommandWithMetrics):
    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("edit-group")

    def handle(self, *args: Any, **options: Any) -> None:
        """Add reviews from bot."""
        edit_group = EditGroup.objects.get(name=options["edit-group"])
        core = Core()
        user = User.objects.get(username="Bot - ClueBot NG")

        for edit in edit_group.edit_set.all():
            if edit.is_deleted or not edit.has_training_data:
                continue

            if Classification.objects.filter(edit=edit, user=user).exists():
                logger.debug(f"Already have classification from {user} on {edit.id}")
            else:
                is_vandalism, score = core.score_edit(edit)
                if is_vandalism is None or score is None:
                    logger.warning(f"Got no data from core for {edit.id}")
                    continue

                logger.info(f"Leaving review for {edit.id} by {user.username} ({score})")
                Classification.objects.create(
                    edit=edit,
                    user=user,
                    classification=0 if is_vandalism else 1,
                    comment=f"Core score: {score}",
                )
