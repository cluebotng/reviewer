import logging
from typing import Any

from django.core.management import BaseCommand

from cbng_reviewer.libs.core import Core
from cbng_reviewer.libs.report_interface import ReportInterface
from cbng_reviewer.models import EditGroup, User, Classification

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def handle(self, *args: Any, **options: Any) -> None:
        """Add a review if this appears to be a bug driven false positive"""
        report_interface = ReportInterface()
        core = Core()

        user, created = User.objects.get_or_create(username="Bot - ClueBot NG")
        if created:
            user.is_bot = True
            user.is_reviewer = True
            user.save()

        our_classified_edits = Classification.objects.filter(user=user).values_list("edit__id", flat=True)
        edit_group = EditGroup.objects.get(name="2025 temp account bug")
        for edit in edit_group.edit_set.exclude(pk__in=our_classified_edits):
            if not edit.has_training_data:
                logger.warning(f"Missing training data for {edit.id}")
                continue

            logger.debug(f"Checking {edit.id}")
            reverted_score = report_interface.fetch_vandalism_score(edit.id)
            core_score = core.score_edit(edit)

            if reverted_score is None or core_score is None:
                logger.error(f'Failed to get score for {edit.id} ({reverted_score}, {core_score})')
                continue

            logger.debug(f"[{edit.id}] {reverted_score} vs {core_score}")
            if reverted_score > core_score and ((reverted_score - core_score) > 0.1 or core_score <= 0.85):
                logger.info(f"[{edit.id}] Leaving positive review ({reverted_score} vs {core_score})")
                Classification.objects.create(
                    edit=edit,
                    user=user,
                    classification=1,
                    comment="Significant difference in score for temporary account",
                )
