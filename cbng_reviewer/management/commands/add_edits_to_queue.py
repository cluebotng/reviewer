import logging
from datetime import datetime, timedelta
from typing import Any

from django.conf import settings
from django.core.management import BaseCommand
from django.core.management.base import CommandParser
from social_django.models import UserSocialAuth

from cbng_reviewer.libs.wikipedia import Wikipedia
from cbng_reviewer.models import User, EditGroup, Edit

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def handle(self, *args: Any, **options: Any) -> None:
        """Add sampled edits for review."""
        wikipedia = Wikipedia()

        edit_group, created = EditGroup.objects.get_or_create(name=settings.CBNG_SAMPLED_EDITS_EDIT_SET)
        if created:
            logger.info(f"Created target edit group: {edit_group.name}")
            edit_group.weight = 40
            edit_group.save()

        current_time = datetime.now()
        for edit_id in wikipedia.get_sampled_edits(
            settings.WIKIPEDIA_NAMESPACE_NAME_TO_ID["main"],
            current_time - timedelta(days=settings.CBNG_SAMPLED_EDITS_LOOKBACK_DAYS),
            current_time,
            settings.CBNG_SAMPLED_EDITS_QUANTITY,
        ):
            edit, created = Edit.objects.get_or_create(id=edit_id)
            if created:
                logger.info(f"Created entry for {edit.id}")
                edit.groups.add(edit_group)

                logger.info(f"Fetching training data for {edit.id}")
                wikipedia.create_training_data_for_edit(edit)
