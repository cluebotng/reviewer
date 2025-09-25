import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from django.core.management import CommandParser

from cbng_reviewer.libs.edit_set.utils import mark_edit_as_deleted
from cbng_reviewer.libs.wikipedia.reader import WikipediaReader
from cbng_reviewer.models import (
    Edit,
    TrainingData,
    Classification,
    EditGroup,
    CurrentRevision,
    PreviousRevision,
)
from cbng_reviewer.utils.command import CommandWithMetrics

logger = logging.getLogger(__name__)


class Command(CommandWithMetrics):
    def __init__(self, *args, **kwargs):
        self._wikipedia_reader = WikipediaReader()
        self._review_groups = set(EditGroup.objects.filter(group_type=1).values_list("id", flat=True))
        super(Command, self).__init__(*args, **kwargs)

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--edit-id")
        parser.add_argument("--workers", type=int, default=20)

    def _handle_edit(self, edit: Edit):
        if not self._wikipedia_reader.has_revision_been_deleted(edit.id):
            logger.debug(f"Edit {edit.id} has not been deleted")
            return

        # If we are a completed edit and our training data exists,
        # then keep the data around - it can be used for training
        if edit.status == 2 and edit.has_training_data:
            logger.info(f"Keeping edit {edit.id} with local data")
            mark_edit_as_deleted(edit)
            return

        # We are an incomplete edit or are missing training data, we can never be used for training.
        # Cleanup any (partial) associated data
        Classification.objects.filter(edit=edit).delete()
        TrainingData.objects.filter(edit=edit).delete()
        CurrentRevision.objects.filter(edit=edit).delete()
        PreviousRevision.objects.filter(edit=edit).delete()

        # If we are in one of the review groups, then keep the 'meta' entry around for export/reporting purposes
        if set(edit.groups.values_list("id", flat=True)) & self._review_groups:
            logger.info(f"Keeping dangling edit {edit.id}")
            mark_edit_as_deleted(edit)
            return

        logger.info(f"Removing dangling edit {edit.id}")
        edit.delete()

    def handle(self, *args: Any, **options: Any) -> None:
        """Update edit deletion flag."""
        with ThreadPoolExecutor(max_workers=options["workers"]) as executor:
            futures = []
            for edit in (
                Edit.objects.filter(id=options["edit_id"])
                if options["edit_id"]
                else Edit.objects.filter(is_deleted=False)
            ):
                futures.append(executor.submit(self._handle_edit, edit))

            for future in futures:
                try:
                    future.result()
                except Exception as e:
                    logger.exception(e)

            executor.shutdown()
