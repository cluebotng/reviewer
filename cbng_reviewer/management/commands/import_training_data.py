import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from django.core.management import BaseCommand, CommandParser

from cbng_reviewer.libs.wikipedia import Wikipedia
from cbng_reviewer.models import Edit, TrainingData

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--edit-id")
        parser.add_argument("--force", action="store_true")

    def _handle_edit(self, edit: Edit, force: bool):
        if edit.has_training_data and not force:
            logger.debug(f"Already have training data for {edit.id}")
            return

        logger.info(f"Fetching training data for {edit.id}")
        wikipedia = Wikipedia()
        wikipedia.create_training_data_for_edit(edit)

    def handle(self, *args: Any, **options: Any) -> None:
        """Import training data for edits."""

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = []
            for edit in (
                Edit.objects.filter(id=options["edit_id"]) if options["edit_id"] else Edit.objects.filter(deleted=False)
            ):
                futures.append(executor.submit(self._handle_edit, edit, options["force"]))

            for future in futures:
                try:
                    future.result()
                except Exception as e:
                    logger.exception(e)

            executor.shutdown()
