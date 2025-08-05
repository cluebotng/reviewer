import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from django.core.management import BaseCommand, CommandParser

from cbng_reviewer.libs.edit_set.utils import import_training_data
from cbng_reviewer.libs.wikipedia.reader import WikipediaReader
from cbng_reviewer.libs.wikipedia.training import WikipediaTraining
from cbng_reviewer.models import Edit

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def __init__(self, *args, **kwargs):
        self._wikipedia_reader = WikipediaReader()
        self._wikipedia_training = WikipediaTraining()
        super(Command, self).__init__(*args, **kwargs)

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--workers", type=int, default=5)
        parser.add_argument("--edit-id")
        parser.add_argument("--force", action="store_true")

    def _handle_edit(self, edit: Edit, force: bool):
        if not force and edit.has_training_data:
            logger.debug(f"Already have training data for {edit.id}")
            return

        if self._wikipedia_reader.has_revision_been_deleted(edit.id):
            logger.info(f"Found deleted revision, skipping training data and marking as deleted")
            edit.deleted = True
            edit.save()
            return

        wp_edit = self._wikipedia_training.build_wp_edit(edit)
        if wp_edit.has_complete_training_data:
            logger.info(f"Importing training data from {wp_edit}")
            import_training_data(edit, wp_edit)
        else:
            logger.warning(f"Failed to generate training data for {wp_edit}")

    def handle(self, *args: Any, **options: Any) -> None:
        """Import training data for edits."""

        with ThreadPoolExecutor(max_workers=options["workers"]) as executor:
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
