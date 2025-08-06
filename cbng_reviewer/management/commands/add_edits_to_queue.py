import logging
from datetime import datetime, timedelta
from typing import Any

from django.conf import settings
from django.core.management import BaseCommand, CommandParser

from cbng_reviewer import tasks
from cbng_reviewer.libs.wikipedia.reader import WikipediaReader
from cbng_reviewer.models import EditGroup, Edit

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--edit-id")

    def handle(self, *args: Any, **options: Any) -> None:
        """Add sampled edits for review."""
        if options["edit_id"]:
            edit, created = Edit.objects.get_or_create(id=options["edit_id"])
            logger.info(f"Created entry for {edit.id}")
            return

        wikipedia_reader = WikipediaReader()

        edit_group, created = EditGroup.objects.get_or_create(name=settings.CBNG_SAMPLED_EDITS_EDIT_SET)
        if created:
            logger.info(f"Created target edit group: {edit_group.name}")
            edit_group.weight = 40
            edit_group.save()

        current_time = datetime.now()
        for edit_id in wikipedia_reader.get_sampled_edits(
            settings.WIKIPEDIA_NAMESPACE_NAME_TO_ID["main"],
            current_time - timedelta(days=settings.CBNG_SAMPLED_EDITS_LOOKBACK_DAYS),
            current_time,
            settings.CBNG_SAMPLED_EDITS_QUANTITY,
        ):
            edit, created = Edit.objects.get_or_create(id=edit_id)
            if created:
                logger.info(f"Created entry for {edit.id}")
                edit.groups.add(edit_group)

                logger.info(f"Triggering fetch of training data for {edit.id}")
                tasks.import_training_data.apply_async([edit.id])
