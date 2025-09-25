import logging
from datetime import datetime, timedelta
from typing import Any

from django.conf import settings
from django.core.management import CommandParser

from cbng_reviewer.libs.wikipedia.reader import WikipediaReader
from cbng_reviewer.models import EditGroup, Edit
from cbng_reviewer.utils.command import CommandWithMetrics

logger = logging.getLogger(__name__)


class Command(CommandWithMetrics):
    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--edit-id")

    def _ensure_edit_exists(self, edit_group: EditGroup, edit_id: int) -> None:
        edit, created = Edit.objects.get_or_create(id=edit_id)
        if created:
            logger.info(f"Created entry for {edit.id}")

        if not edit.groups.filter(pk=edit_group.pk).exists():
            logger.info(f"Adding edit {edit.id} to {edit_group.name}")
            edit.groups.add(edit_group)
            edit.save()

    def handle(self, *args: Any, **options: Any) -> None:
        """Add sampled edits for review."""
        edit_group, created = EditGroup.objects.get_or_create(name=settings.CBNG_SAMPLED_EDITS_EDIT_SET)
        if created:
            logger.info(f"Created target edit group: {edit_group.name}")
            edit_group.weight = 40
            edit_group.save()

        if options["edit_id"]:
            self._ensure_edit_exists(edit_group, options["edit_id"])
            return

        end_time = datetime.now()
        start_time = end_time - timedelta(days=settings.CBNG_SAMPLED_EDITS_LOOKBACK_DAYS)
        namespace_id = settings.WIKIPEDIA_NAMESPACE_NAME_TO_ID["main"]
        quantity = settings.CBNG_SAMPLED_EDITS_QUANTITY

        logger.info(f"Sampling {quantity} edits from ns {namespace_id} between {start_time} and {end_time}")
        for edit_id in WikipediaReader().get_sampled_edits(namespace_id, start_time, end_time, quantity):
            self._ensure_edit_exists(edit_group, edit_id)
